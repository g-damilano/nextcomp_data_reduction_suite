from __future__ import annotations

import csv
import io
import json
import math
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from archives.mtda.plot_views import parse_csv_rows, resolve_plot_data_view
from archives.mtda.plot_views import TRANSFORM_VERSIONS


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


def test_archive_view_plot_data_reproduces_legacy_plot_csvs(tmp_path: Path) -> None:
    compatibility = _generate(tmp_path / "compatibility.mtda", "compatibility")
    archive_view = _generate(tmp_path / "archive_view.mtda", "none")

    with zipfile.ZipFile(compatibility) as golden, zipfile.ZipFile(archive_view) as reworked:
        reworked_names = {name for name in reworked.namelist() if not name.endswith("/")}
        assert not any("plot_data/" in name and name.endswith(".csv") for name in reworked_names)
        checksums = json.loads(reworked.read("metadata/checksums.json"))
        checksum_members = set(checksums.get("files", checksums).keys()) if isinstance(checksums, dict) else set()
        assert not any("plot_data/" in member and member.endswith(".csv") for member in checksum_members)

        for member in _canonical_csv_members(golden):
            assert reworked.read(member) == golden.read(member), member

        for package_member in _plot_package_members(golden):
            golden_package = json.loads(golden.read(package_member))
            reworked_package = json.loads(reworked.read(package_member))

            assert reworked_package["data_mode"] == "archive_view"
            assert reworked_package["view_data_mode"] == "runtime_resolved"
            assert reworked_package["embedded_datasets"] == []
            assert reworked_package["plot_data_materialization"] == "none"
            assert reworked_package["template"] == golden_package["template"]
            assert reworked_package["semantic_layers"] == golden_package["semantic_layers"]
            assert reworked_package["projection_id"] == golden_package["projection_id"]
            assert reworked_package["recipe_version"] == golden_package["recipe_version"]
            assert reworked_package["recipe_schema_version"] == golden_package["recipe_schema_version"]
            assert reworked_package["golden_id"] == golden_package["golden_id"]
            assert reworked_package["production_state"] == "production"
            assert reworked_package["projection_contracts"] == golden_package["projection_contracts"]

            source_rows = {
                member: parse_csv_rows(reworked.read(member))
                for view in reworked_package["plot_data_views"]
                for member in view["source_members"]
            }
            golden_datasets = {dataset["dataset_id"]: dataset for dataset in golden_package["datasets"]}
            for view in reworked_package["plot_data_views"]:
                dataset_id = view["dataset_id"]
                golden_dataset = golden_datasets[dataset_id]
                expected_rows = _csv_member(golden, golden_dataset["member"])
                virtual_rows = resolve_plot_data_view(view, source_rows)
                assert view["fields"] == golden_dataset["fields"]
                assert view["data_view_schema_version"] == "mtda.plot_data_view.v0_1"
                assert view["data_view_version"] == TRANSFORM_VERSIONS[view["transform_id"]]
                assert view["transform_version"] == TRANSFORM_VERSIONS[view["transform_id"]]
                assert len(virtual_rows) == len(expected_rows), (package_member, dataset_id)
                _assert_rows_equivalent(expected_rows, virtual_rows, view["fields"], context=f"{package_member}:{dataset_id}")


def test_archive_view_surface_manifest_lists_recipes_not_plot_data_members(tmp_path: Path) -> None:
    archive_path = _generate(tmp_path / "archive_view.mtda", "none")
    with zipfile.ZipFile(archive_path) as archive:
        surface = json.loads(archive.read("metadata/surface_manifest.json"))
        dataset_surface = surface["surfaces"]["dataset_plot"]
        assert dataset_surface["plot_data_members"] == []
        assert dataset_surface["projection_recipe"]["projection_id"] == "mtda_dataset_aggregate_compact_package"
        assert dataset_surface["projection_recipe"]["recipe_version"] == "0.1.0"
        assert dataset_surface["projection_recipe"]["production_state"] == "production"
        assert {view["transform_id"] for view in dataset_surface["plot_data_views"]} == {
            "aggregate.all_runs_resampled_curve_family.v1",
            "aggregate.stress_band_from_run_grid.v1",
            "aggregate.bending_summary_passthrough.v1",
            "aggregate.fmax_distribution.v1",
        }
        for run_surface in surface["run_surfaces"]:
            assert run_surface["plot_data_members"] == []
            assert run_surface["projection_recipe"]["projection_id"] == "mtda_run_compact_stress_strain_evidence"
            assert run_surface["projection_recipe"]["recipe_version"] == "0.1.0"
            assert run_surface["projection_recipe"]["production_state"] == "production"
            assert [view["transform_id"] for view in run_surface["plot_data_views"]] == [
                "run.front_rear_strain_envelope.v1",
                "run.front_rear_strain_traces.v1",
                "run.bounded_average_curve.v1",
                "run.empty_chord_line.v1",
                "run.empty_chord_points.v1",
                "run.analysis_markers.v1",
            ]


def _generate(output: Path, mode: str) -> Path:
    env = os.environ.copy()
    env["MTDA_PLOT_DATA_MATERIALIZATION"] = mode
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--input",
            str(INPUT),
            "--method",
            str(METHOD),
            "--mapping",
            str(MAPPING),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return output


def _plot_package_members(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.endswith(".plot_package.json") and ("/dataset_plot." in name or "/run_" in name)
    )


def _canonical_csv_members(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.endswith(".csv")
        and "plot_data/" not in name
        and not name.endswith("_plot_manifest.csv")
        and not name.endswith("dataset_plot_manifest.csv")
    )


def _csv_member(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _assert_rows_equivalent(
    expected_rows: list[dict[str, str]],
    actual_rows: list[dict[str, Any]],
    fields: list[str],
    *,
    context: str,
) -> None:
    for row_index, (expected, actual) in enumerate(zip(expected_rows, actual_rows, strict=True)):
        for field in fields:
            expected_value = expected.get(field, "")
            actual_value = actual.get(field, "")
            if isinstance(actual_value, (int, float)) and expected_value != "":
                assert math.isclose(
                    float(expected_value),
                    float(actual_value),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ), f"{context} row {row_index} field {field}: {expected_value!r} != {actual_value!r}"
            else:
                assert str(expected_value) == str(actual_value), (
                    f"{context} row {row_index} field {field}: {expected_value!r} != {actual_value!r}"
                )
