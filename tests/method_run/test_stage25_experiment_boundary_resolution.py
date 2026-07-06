from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from methods.core.method_run_service import MethodRunRequest, MethodRunService
from operations.core.operation_registry import default_operation_registry


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
BZ_INPUT = ROOT / "datasets" / "BZ_Compression_20250325" / "8552-IM7.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
BZ_MAPPING = ROOT / "mappings" / "iso14126_manual_wizard_edit_14.json"


@pytest.fixture(scope="module")
def boundary_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage25_boundaries") / "CAG-CF-Modied-ULV20.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output


@pytest.fixture(scope="module")
def bz_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("bz_boundaries") / "8552-IM7.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=BZ_INPUT,
            method_path=METHOD,
            mapping_path=BZ_MAPPING,
            output_path=output,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output


def test_boundary_operation_is_registered() -> None:
    registry = default_operation_registry()
    assert "resolve_experiment_boundaries" in registry._operations


def test_run006_endpoint_uses_slope_break_pre_negative_and_reduction_is_bounded(boundary_mtda: Path) -> None:
    boundaries = _csv_member(boundary_mtda, "method_outputs/boundaries.csv")
    specimen_rows = _csv_member(boundary_mtda, "method_outputs/specimen_results.csv")
    bounded_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family.csv"))["run_006"]
    full_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family_full.csv"))["run_006"]
    events = _csv_member(boundary_mtda, "audit/boundary_events.csv")

    boundary = next(row for row in boundaries if row["run_id"] == "run_006")
    specimen = next(row for row in specimen_rows if row["run_id"] == "run_006")
    run006_events = [row for row in events if row["run_id"] == "run_006"]
    first_negative = next(row for row in run006_events if row["event_id"] == "first_negative_slope")
    max_load = next(row for row in run006_events if row["event_id"] == "max_abs_load")

    assert boundary["end_policy"] == "slope_break_pre_negative"
    assert boundary["start_policy"] == "first_point"
    assert boundary["start_min_load_fraction_of_max"] == ""
    assert boundary["slope_domain"] == "strain"
    assert "domain=strain" in boundary["policy_signature"]
    assert "lookback=8" in boundary["policy_signature"]
    assert "min_negative_domain_step=" in boundary["policy_signature"]
    assert "sustained_use_as=endpoint" in boundary["policy_signature"]
    assert int(first_negative["index"]) == 289
    assert "negative_slope_trigger=load_drop" in first_negative["reason"]
    assert not any(row["event_id"] == "prebreak_curvature" for row in run006_events)
    assert not any(row["event_id"] == "raw_machine_max_abs_load" for row in run006_events)
    assert int(max_load["index"]) == 289
    assert max_load["diagnostic_only"] == "False"
    assert int(boundary["start_index"]) == 0
    assert int(boundary["end_index"]) == 289
    assert int(boundary["end_index"]) == int(float(specimen["max_load_index"]))
    assert int(float(specimen["max_load_point_index"])) == 289
    assert float(specimen["max_load_N"]) == pytest.approx(4953.57)
    assert float(specimen["compressive_failure_strain"]) == pytest.approx(float(bounded_rows[-1]["mean_strain"]))
    assert bounded_rows[0]["point_index"] == "0"
    assert bounded_rows[-1]["point_index"] == "289"
    assert len(full_rows) > len(bounded_rows)
    assert any(int(row["point_index"]) > 289 for row in full_rows)
    assert all(int(row["point_index"]) >= 0 for row in bounded_rows)
    assert all(int(row["point_index"]) <= 289 for row in bounded_rows)


def test_run002_boundary_excludes_pre_failure_strain_spike(boundary_mtda: Path) -> None:
    boundaries = _csv_member(boundary_mtda, "method_outputs/boundaries.csv")
    bounded_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family.csv"))["run_002"]
    full_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family_full.csv"))["run_002"]
    events = _csv_member(boundary_mtda, "audit/boundary_events.csv")

    boundary = next(row for row in boundaries if row["run_id"] == "run_002")
    run_events = [row for row in events if row["run_id"] == "run_002"]
    first_negative = next(row for row in run_events if row["event_id"] == "first_negative_slope")

    assert boundary["end_policy"] == "slope_break_pre_negative"
    assert boundary["start_policy"] == "first_point"
    assert "lookback=8" in boundary["policy_signature"]
    assert "min_negative_domain_step=" in boundary["policy_signature"]
    assert int(first_negative["index"]) == 171
    assert "negative_slope_trigger=domain_reversal" in first_negative["reason"]
    assert not any(row["event_id"] == "prebreak_curvature" for row in run_events)
    assert int(boundary["start_index"]) == 0
    assert int(boundary["end_index"]) == 171
    assert bounded_rows[0]["point_index"] == "0"
    assert bounded_rows[-1]["point_index"] == "171"
    assert float(bounded_rows[-1]["mean_strain"]) * 100.0 == pytest.approx(0.336677034, abs=1e-6)
    assert max(float(row["mean_strain"]) for row in bounded_rows) < 0.006
    assert any(float(row["mean_strain"]) > 0.01 for row in full_rows)


def test_run004_boundary_excludes_pre_failure_strain_spike(boundary_mtda: Path) -> None:
    boundaries = _csv_member(boundary_mtda, "method_outputs/boundaries.csv")
    bounded_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family.csv"))["run_004"]
    full_rows = _group_by_run(_csv_member(boundary_mtda, "method_outputs/curves/stress_strain_family_full.csv"))["run_004"]
    events = _csv_member(boundary_mtda, "audit/boundary_events.csv")

    boundary = next(row for row in boundaries if row["run_id"] == "run_004")
    run_events = [row for row in events if row["run_id"] == "run_004"]
    first_negative = next(row for row in run_events if row["event_id"] == "first_negative_slope")

    assert boundary["end_policy"] == "slope_break_pre_negative"
    assert boundary["start_policy"] == "first_point"
    assert "lookback=8" in boundary["policy_signature"]
    assert "min_negative_domain_step=" in boundary["policy_signature"]
    assert int(first_negative["index"]) == 179
    assert "negative_slope_trigger=domain_reversal" in first_negative["reason"]
    assert not any(row["event_id"] == "prebreak_curvature" for row in run_events)
    assert int(boundary["start_index"]) == 0
    assert int(boundary["end_index"]) == 179
    assert bounded_rows[0]["point_index"] == "0"
    assert bounded_rows[-1]["point_index"] == "179"
    assert all(int(row["point_index"]) >= 0 for row in bounded_rows)
    assert all(int(row["point_index"]) <= 179 for row in bounded_rows)
    assert max(float(row["mean_strain"]) for row in bounded_rows) < 0.006
    assert any(float(row["mean_strain"]) > 0.02 for row in full_rows)


def test_boundary_artifacts_surfaces_and_aggregation_are_written(boundary_mtda: Path) -> None:
    with zipfile.ZipFile(boundary_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        audit = json.loads(archive.read("audit/audit_report.json"))
        workbench = json.loads(archive.read("workbench/operation_trace.json"))
        workbench_html = archive.read("workbench/index.html").decode("utf-8")
        report = json.loads(archive.read("report/test_report.json"))

    assert {
        "audit/boundary_resolution.json",
        "audit/boundary_events.csv",
        "method_outputs/boundaries.csv",
        "method_outputs/curves/stress_strain_family_full.csv",
        "method_outputs/curves/stress_strain_family_bounded.csv",
        "report/plot_data_freshness.json",
    } <= names
    assert audit["experiment_boundary_resolution"]["bounded_reduction"] is True
    assert audit["experiment_boundary_resolution"]["boundary_aligned_aggregation"] is True
    assert workbench["experiment_boundaries"]
    assert any(op["audit_view_hint"] == "experiment_boundary_resolution" for op in workbench["operations"])
    assert "Experiment Boundary" in workbench_html
    assert report["summary"]["bounded_reduction"] is True
    assert report["plot_data_freshness"]["replicate_source"] == "boundary_aligned_curves"
    assert report["plot_data_freshness"]["boundary_aligned_replicates"] is True
    assert report["plot_data_freshness"]["status"] == "current"
    assert "domain=strain" in report["plot_data_freshness"]["policy_signatures"][0]

    aligned_rows = _csv_member(boundary_mtda, "report/aligned_curves.csv")
    assert aligned_rows[0]["alignment_domain"] == "experiment_progress"
    assert aligned_rows[0]["source_boundaries"] == "method_resolve.experiment_boundaries"


def test_bz_package_formal_stress_strain_curves_keep_first_point_start(bz_mtda: Path) -> None:
    boundaries = _csv_member(bz_mtda, "method_outputs/boundaries.csv")
    specimen_rows = _csv_member(bz_mtda, "method_outputs/specimen_results.csv")
    curves = _group_by_run(_csv_member(bz_mtda, "method_outputs/curves/stress_strain_family.csv"))
    full_curves = _group_by_run(_csv_member(bz_mtda, "method_outputs/curves/stress_strain_family_full.csv"))
    diagnostic_policy = _json_member(bz_mtda, "acceptance/curve_family/curve_diagnostic_policy.json")
    diagnostic_report = _json_member(bz_mtda, "acceptance/curve_family/curve_diagnostic_report.json")
    specimen_by_run = {row["run_id"]: row for row in specimen_rows}

    assert boundaries
    assert all(row["start_policy"] == "first_point" for row in boundaries)
    assert all(int(row["start_index"]) == 0 for row in boundaries)
    assert {row["run_id"]: row["end_index"] for row in boundaries} == {
        "run_001": "220",
        "run_002": "176",
        "run_003": "238",
        "run_004": "184",
        "run_005": "194",
        "run_006": "179",
        "run_007": "196",
        "run_008": "206",
        "run_009": "237",
        "run_010": "176",
    }
    assert all("detect_strain_collapse=True" in row["policy_signature"] for row in boundaries)
    assert diagnostic_policy["preprocessing"]["scope"] == "curve_shape_diagnostic_only"
    assert diagnostic_policy["preprocessing"]["start_policy"] == "load_fraction_of_max"
    assert diagnostic_report["preprocessing"]["runs_with_excluded_leading_points"] > 0

    for run_id, rows in curves.items():
        assert rows[0]["point_index"] == "0"
        assert len(rows) > 100
        assert len(full_curves[run_id]) >= len(rows)
        assert float(rows[0]["mean_strain"]) < 0.0001

    run_001 = curves["run_001"]
    assert run_001[-1]["point_index"] == "220"
    assert float(run_001[0]["mean_strain"]) < 0.0001
    assert curves["run_004"][-1]["point_index"] == "184"
    assert float(curves["run_004"][-1]["mean_strain"]) > 0.0009
    assert curves["run_009"][-1]["point_index"] == "237"
    assert float(curves["run_009"][-1]["mean_strain"]) > 0.0009
    assert specimen_by_run["run_009"]["max_load_point_index"] == "237"
    assert float(specimen_by_run["run_009"]["compressive_strength_MPa"]) == pytest.approx(150.0)
    assert float(specimen_by_run["run_009"]["compressive_failure_strain"]) == pytest.approx(
        float(curves["run_009"][-1]["mean_strain"])
    )


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _group_by_run(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["run_id"], []).append(row)
    return grouped
