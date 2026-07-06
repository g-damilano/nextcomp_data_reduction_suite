from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import subprocess
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


@pytest.fixture(scope="module")
def mtda_archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    before = _sha256(INPUT)
    output = tmp_path_factory.mktemp("method_run") / "CAG-CF-Modied-ULV20.mtda"
    completed = subprocess.run(
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
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Wrote" in completed.stdout
    assert _sha256(INPUT) == before
    return output


def test_stage2_mtda_archive_shape_and_checksums(mtda_archive: Path) -> None:
    with zipfile.ZipFile(mtda_archive) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {
            "manifest.json",
            "source_reference.json",
            "provenance.json",
            "checksums.json",
            "mapping_profile.json",
            "method_package/method_manifest.yaml",
            "method_package/resolve_recipe.yaml",
            "method_package/reduce_recipe.yaml",
            "method_package/audit_recipe.yaml",
            "method_package/validation_recipe.yaml",
            "method_package/acceptance_recipe.yaml",
            "method_package/method_inputs.yaml",
            "method_package/report_recipe.yaml",
            "method_package/curve_aggregation_policy.yaml",
            "method_outputs/specimen_results.csv",
            "method_outputs/dataset_summary.csv",
            "method_outputs/dataset_summary_by_selection.csv",
            "method_outputs/boundaries.csv",
            "method_outputs/curves/stress_strain_family.csv",
            "method_outputs/curves/stress_strain_family_bounded.csv",
            "method_outputs/curves/stress_strain_family_full.csv",
            "readiness/readiness_report.json",
            "readiness/readiness_summary.csv",
            "readiness/resolved_inputs.csv",
            "readiness/missing_inputs.csv",
            "validation/validation_report.json",
            "validation/validation_summary.csv",
            "validation/reference_values_used.csv",
            "validation/deviations.csv",
            "acceptance/acceptance_report.json",
            "acceptance/acceptance_summary.csv",
            "acceptance/run_flags.csv",
            "acceptance/selection_sets.json",
            "acceptance/selection_membership.csv",
            "acceptance/discharged_runs.csv",
            "acceptance/discharge_report.json",
            "acceptance/human_decisions.json",
            "acceptance/selection_sets_final.json",
            "acceptance/final_report_runs.csv",
            "report/test_report.html",
            "report/test_report.json",
            "report/iso14126_report.html",
            "report/iso14126_report.json",
            "report/report_completion_status.json",
            "report/report_values_used.csv",
            "report/missing_report_fields.csv",
            "report/individual_results.csv",
            "report/aggregate_statistics.csv",
            "report/characteristic_points.csv",
            "report/feature_lines.csv",
            "report/aligned_curves.csv",
            "audit/evidence.json",
            "audit/boundary_resolution.json",
            "audit/boundary_events.csv",
            "audit/operation_log.json",
            "audit/warnings.json",
            "audit/inspections.json",
            "audit/audit_report.html",
            "audit/audit_report.json",
            "workbench/index.html",
            "workbench/operation_trace.json",
            "interactive_report/index.html",
        } <= names
        assert not any(name.lower().endswith((".png", ".pdf")) for name in names)

        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["package_format"] == "mtda"
        assert manifest["method_id"] == "iso14126_2023"
        assert manifest["artifact_surfaces"]["test_report"] == "report/test_report.html"
        assert manifest["artifact_surfaces"]["audit_report"] == "audit/audit_report.html"
        assert manifest["artifact_surfaces"]["method_development_workbench"] == "workbench/index.html"

        mapping = json.loads(archive.read("mapping_profile.json"))
        assert mapping["mapping_id"] == "iso14126_manual_cag_cf_modied_ulv20_v0_1"

        source_reference = json.loads(archive.read("source_reference.json"))
        assert source_reference["source_package"]["checksum"] == _sha256(INPUT)

        readiness = json.loads(archive.read("readiness/readiness_report.json"))
        assert readiness["status"] == "READY_WITH_WARNINGS"
        assert readiness["blocks_execution"] is False
        assert readiness["summary"]["execution_critical_passed"] == readiness["summary"]["execution_critical_total"]

        checksums = json.loads(archive.read("checksums.json"))
        assert checksums["algorithm"] == "sha256"
        assert set(checksums["files"]) == names - {"checksums.json"}


def test_operation_evidence_has_stage2_shape(mtda_archive: Path) -> None:
    operation_log = _json_member(mtda_archive, "audit/operation_log.json")
    required = {
        "operation_id",
        "operation_type",
        "phase",
        "run_id",
        "status",
        "inputs",
        "parameters",
        "outputs",
        "units",
        "warnings",
        "evidence",
        "inspection_refs",
        "audit_view_hint",
    }
    assert operation_log
    assert all(required <= set(record) for record in operation_log)
    assert {record["phase"] for record in operation_log} == {"method_resolve", "method_reduce"}
    assert {
        "derive_area",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
        "bending_diagnostic",
        "resolve_experiment_boundaries",
    } <= {record["operation_type"] for record in operation_log}
    assert "orient_strain_channels" not in {record["operation_type"] for record in operation_log}
    assert all(record["status"] in {"pass", "pass_with_warning", "failed", "skipped", "not_applicable"} for record in operation_log)
    assert any(record["inspection_refs"] for record in operation_log if record["operation_type"] == "chord_slope")
    assert any(record["inspection_refs"] for record in operation_log if record["operation_type"] == "bending_diagnostic")

    mean = next(record for record in operation_log if record["operation_type"] == "construct_mean_series" and record["run_id"] == "run_006")
    assert mean["audit_view_hint"] == "mean_absolute_strain_construction"
    assert mean["parameters"]["mode"] == "mean_absolute"
    assert mean["inputs"]["series"] == ["front_strain_raw", "rear_strain_raw"]
    assert mean["outputs"]["front_strain_abs"]["point_count"] > 0
    assert mean["outputs"]["rear_strain_abs"]["point_count"] > 0
    assert mean["evidence"]["formula"] == "mean_strain = mean(abs(front_strain_raw), abs(rear_strain_raw))"
    assert mean["evidence"]["absolute_series_refs"] == ["front_strain_abs", "rear_strain_abs"]

    load_map = next(record for record in operation_log if record["recipe_step_id"] == "resolve.map_load" and record["run_id"] == "run_006")
    assert load_map["parameters"]["transform"] == "absolute"
    assert load_map["parameters"]["raw_output"] == "load_N_raw"
    assert set(load_map["outputs"]) == {"load_N", "load_N_raw"}
    assert load_map["evidence"]["formula"].startswith("load_N = abs(channel:")


def test_curve_inspections_are_recorded(mtda_archive: Path) -> None:
    inspections = _json_member(mtda_archive, "audit/inspections.json")
    assert len(inspections) >= 21
    required = {
        "inspection_id",
        "inspection_type",
        "curve_id",
        "run_id",
        "x_channel",
        "y_channel",
        "point_count",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "missing_x_count",
        "missing_y_count",
        "duplicate_x_count",
        "monotonic_x",
        "median_dx",
        "dx_variability_ratio",
        "notes",
    }
    assert all(required <= set(record) for record in inspections)
    assert any(record["inspection_id"] == "inspect_run_001_stress_strain_curve" for record in inspections)
    assert any(record["inspection_id"] == "inspect_run_001_modulus_window" for record in inspections)
    assert any(record["inspection_id"] == "inspect_run_001_bending_window" for record in inspections)


def test_audit_report_uses_recipe_title_and_components(mtda_archive: Path) -> None:
    with zipfile.ZipFile(mtda_archive) as archive:
        html = archive.read("interactive_report/index.html").decode("utf-8")
    assert "Audit Report" in html
    assert "Audit Overview" in html
    assert "Process Verification Overview" not in html
    assert "Formal result values are in" in html
    assert "../report/test_report.html" in html
    assert "Evidence Navigation / Run Evidence Index" in html
    assert "Run-wise Evidence Packets" in html
    assert "Aggregate Evidence Packet" in html
    assert "Data compliance evidence" not in html
    assert "Stress-strain reduction evidence" in html
    assert "Bending evidence" in html
    assert "tools/run_method_development.py" not in html
    assert "Curve Inspections" not in html


def test_validation_artifacts_lock_run006_reference_values(mtda_archive: Path) -> None:
    report = _json_member(mtda_archive, "validation/validation_report.json")
    summary_rows = _csv_member(mtda_archive, "validation/validation_summary.csv")
    references = _csv_member(mtda_archive, "validation/reference_values_used.csv")
    deviations = _csv_member(mtda_archive, "validation/deviations.csv")

    assert report["schema_id"] == "method.validation_report.v0_1"
    assert report["method_id"] == "iso14126_2023"
    assert report["summary"]["status"] == "pass"
    assert report["summary"]["total_checks"] == 12
    assert report["summary"]["failed"] == 0
    assert summary_rows[0]["status"] == "pass"
    assert len(references) == 12
    assert {row["run_id"] for row in references} == {"run_006"}
    assert deviations

    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["run_006:max_load_N"]["computed_value"] == pytest.approx(4953.57)
    assert checks["run_006:max_load_N"]["operation_id"]
    assert checks["run_006:mean_strain_microstrain:29"]["computed_value"] == pytest.approx(112.405015)
    assert checks["run_006:mean_strain_microstrain:29"]["recipe_step_id"] == "resolve.derive_mean_strain"
    assert checks["run_006:compressive_strength_MPa"]["status"] == "pass"
    assert checks["run_006:compressive_strength_MPa"]["difference_abs"] == pytest.approx(0.0, abs=1e-9)
    assert checks["run_006:compressive_modulus_GPa"]["computed_value"] == pytest.approx(56.041753732938425)
    assert checks["run_006:compressive_modulus_GPa"]["reference_value"] == pytest.approx(55.2770854)


def test_iso14126_report_and_aggregate_evidence_are_written(mtda_archive: Path) -> None:
    report = _json_member(mtda_archive, "report/test_report.json")
    aggregate_rows = _csv_member(mtda_archive, "report/aggregate_statistics.csv")
    aligned_rows = _csv_member(mtda_archive, "report/aligned_curves.csv")
    individual_rows = _csv_member(mtda_archive, "report/individual_results.csv")
    feature_rows = _csv_member(mtda_archive, "report/feature_lines.csv")
    characteristic_rows = _csv_member(mtda_archive, "report/characteristic_points.csv")

    assert report["schema_id"] == "method.iso14126_report.v0_1"
    assert report["surface"] == "test_report"
    assert report["selection_set"] == "final_report_runs"
    assert report["selection_source"] == "machine_default_confirmed"
    assert report["summary"]["selected_run_count"] == 3
    assert report["summary"]["bounded_reduction"] is True
    assert report["summary"]["boundary_aligned_aggregation"] is True
    assert report["summary"]["plot_data_status"] == "current"
    assert report["plot_data_freshness"]["replicate_source"] == "boundary_aligned_curves"
    assert report["plot_data_freshness"]["boundary_aligned_replicates"] is True
    assert "domain=strain" in report["plot_data_freshness"]["policy_signatures"][0]
    assert "report/plot_data_freshness.json" in report["artifacts"]
    assert report["alignment_policy"]["alignment_policy"] == "experiment_progress"
    assert report["alignment_policy"]["alignment"]["domain"] == "experiment_progress"
    assert "report/test_report.html" in report["artifacts"]
    assert "report/iso14126_report.html" in report["artifacts"]

    metrics = {row["metric"] for row in aggregate_rows}
    assert {"compressive_strength_MPa", "compressive_modulus_MPa", "compressive_failure_strain"} <= metrics
    strength = next(row for row in aggregate_rows if row["metric"] == "compressive_strength_MPa")
    assert int(strength["n"]) == 3
    assert float(strength["mean"]) > 200.0

    assert len(aligned_rows) == 500
    assert aligned_rows[0]["selection_set"] == "final_report_runs"
    assert aligned_rows[0]["alignment_policy"] == "experiment_progress"
    assert aligned_rows[0]["alignment_domain"] == "experiment_progress"
    assert aligned_rows[0]["source_boundaries"] == "method_resolve.experiment_boundaries"
    assert "mean" in aligned_rows[0]
    assert "std" in aligned_rows[0]

    by_run = {row["run_id"]: row for row in individual_rows}
    assert by_run["run_002"]["included_in_selection"] == "False"
    assert by_run["run_006"]["included_in_selection"] == "False"
    assert any(row["line_id"] == "mean_compressive_strength" for row in feature_rows)
    assert any(row["point_id"] == "mean_compressive_failure" for row in characteristic_rows)


def test_iso14126_specimen_outputs_and_flags_are_carried(mtda_archive: Path) -> None:
    rows = _csv_member(mtda_archive, "method_outputs/specimen_results.csv")
    expected = {
        "run_001": "CAG-CF-ER-Comp-E1",
        "run_002": "CAG-CF-ER-Comp-E2",
        "run_003": "CAG-CF-ER-Comp-E3",
        "run_004": "CAG-CF-ER-Comp-E4",
        "run_005": "CAG-CF-ER-Comp-E5",
        "run_006": "CAG-CF-ER-Comp--E6",
        "run_007": "CAG-CF-ER-Comp-E7",
    }
    assert {row["run_id"]: row["specimen_name"] for row in rows} == expected
    run_002 = next(row for row in rows if row["run_id"] == "run_002")
    assert run_002["failure_mode"] not in ("", None)
    assert run_002["failure_mode"] in {"0", "Invalid"}
    assert run_002["validity"] == "accepted"
    assert all(float(row["max_load_N"]) > 0 for row in rows)
    assert all(float(row["compressive_strength_MPa"]) > 0 for row in rows)
    assert all(float(row["compressive_modulus_MPa"]) > 0 for row in rows)


def test_iso14126_stress_strength_failure_and_modulus_regressions(mtda_archive: Path) -> None:
    specimen_rows = {row["run_id"]: row for row in _csv_member(mtda_archive, "method_outputs/specimen_results.csv")}
    curve_rows = _group_by_run(_csv_member(mtda_archive, "method_outputs/curves/stress_strain_family.csv"))

    for run_id, rows in curve_rows.items():
        specimen = specimen_rows[run_id]
        area = float(specimen["area_mm2"])
        sample_indices = [0, len(rows) // 2, len(rows) - 1]
        for index in sample_indices:
            load = _float(rows[index]["load_N"])
            raw_load = _float(rows[index]["load_N_raw"])
            stress = _float(rows[index]["stress_MPa"])
            if load is not None and raw_load is not None:
                assert load == pytest.approx(abs(raw_load), rel=1e-12)
            if load is not None and stress is not None:
                assert stress == pytest.approx(load / area, rel=1e-10)

        max_stress_index, max_stress = max(
            enumerate(rows),
            key=lambda item: _float(item[1]["stress_MPa"]) or -math.inf,
        )
        assert float(specimen["compressive_strength_MPa"]) == pytest.approx(float(max_stress["stress_MPa"]), rel=1e-10)
        assert float(specimen["compressive_failure_strain"]) == pytest.approx(
            float(rows[max_stress_index]["mean_strain"]),
            rel=1e-10,
        )
        slope = _chord_slope(rows, 0.0005, 0.0025)
        assert float(specimen["compressive_modulus_MPa"]) == pytest.approx(slope, rel=1e-10)


def test_run006_mean_strain_uses_mean_absolute_convention(mtda_archive: Path) -> None:
    rows = _group_by_run(_csv_member(mtda_archive, "method_outputs/curves/stress_strain_family.csv"))["run_006"]
    expected = {
        0: 0.00000072534,
        29: 0.000112405015,
        141: (0.00134874030 + 0.00188251084) / 2.0,
    }
    for index, expected_mean in expected.items():
        row = rows[index]
        front_raw = float(row["front_strain_raw"])
        rear_raw = float(row["rear_strain_raw"])
        front_abs = float(row["front_strain_abs"])
        rear_abs = float(row["rear_strain_abs"])
        signed_mean = (front_raw + rear_raw) / 2.0
        assert front_abs == pytest.approx(abs(front_raw), rel=1e-12, abs=1e-15)
        assert rear_abs == pytest.approx(abs(rear_raw), rel=1e-12, abs=1e-15)
        assert float(row["mean_strain"]) == pytest.approx(expected_mean, rel=1e-10, abs=1e-15)
        if front_abs != pytest.approx(front_raw, rel=1e-12, abs=1e-15) or rear_abs != pytest.approx(rear_raw, rel=1e-12, abs=1e-15):
            assert float(row["mean_strain"]) != pytest.approx(signed_mean, rel=1e-3, abs=1e-9)


def test_run006_tracks_excel_reference_values(mtda_archive: Path) -> None:
    specimen = next(row for row in _csv_member(mtda_archive, "method_outputs/specimen_results.csv") if row["run_id"] == "run_006")
    rows = _group_by_run(_csv_member(mtda_archive, "method_outputs/curves/stress_strain_family.csv"))["run_006"]

    assert float(specimen["width_mm"]) == pytest.approx(9.71)
    assert float(specimen["thickness_mm"]) == pytest.approx(2.18)
    assert float(specimen["max_load_N"]) == pytest.approx(4953.57)
    assert float(specimen["compressive_failure_strain"]) == pytest.approx(0.005052839175, rel=1e-12)

    max_row = rows[-1]
    assert max_row["point_index"] == "289"
    assert float(max_row["load_N"]) == pytest.approx(4953.57)
    assert float(max_row["load_N_raw"]) == pytest.approx(4953.57)
    assert float(max_row["mean_strain"]) == pytest.approx(0.005052839175, rel=1e-12)

    excel_like_load_strain_slope = _load_strain_slope_kN_per_microstrain(rows, 109, 219)
    assert excel_like_load_strain_slope == pytest.approx(0.001167904, rel=1e-7)


def test_iso14126_bending_diagnostic_uses_opposite_faces_and_10_90_window(mtda_archive: Path) -> None:
    specimen_rows = {row["run_id"]: row for row in _csv_member(mtda_archive, "method_outputs/specimen_results.csv")}
    curve_rows = _group_by_run(_csv_member(mtda_archive, "method_outputs/curves/stress_strain_family.csv"))
    operation_log = _json_member(mtda_archive, "audit/operation_log.json")

    for run_id, rows in curve_rows.items():
        loads = [_float(row["load_N"]) for row in rows]
        max_load = max(abs(value) for value in loads if value is not None)
        lower = max_load * 0.10
        upper = max_load * 0.90
        bending_values = []
        for row in rows:
            load = _float(row["load_N"])
            front = _float(row["front_strain_abs"])
            rear = _float(row["rear_strain_abs"])
            if load is None or front is None or rear is None:
                continue
            if lower <= abs(load) <= upper:
                denominator = abs(front + rear)
                if denominator:
                    bending_values.append(abs(front - rear) / denominator * 100.0)
        specimen = specimen_rows[run_id]
        assert int(float(specimen["bending_point_count"])) == len(bending_values)
        assert float(specimen["bending_max_percent"]) == pytest.approx(max(bending_values), rel=1e-10)
        assert float(specimen["bending_mean_percent"]) == pytest.approx(sum(bending_values) / len(bending_values), rel=1e-10)
        assert specimen["bending_pattern"]
        assert specimen["bending_p95_percent"]
        assert specimen["bending_points_above_threshold"] != ""

    bending_records = [record for record in operation_log if record["operation_type"] == "bending_diagnostic"]
    assert bending_records
    assert all(record["parameters"]["window_percent_of_max_load"] == [10.0, 90.0] for record in bending_records)
    assert all(record["audit_view_hint"] == "bending_pattern_assessment" for record in bending_records)
    assert all(record["outputs"]["bending_diagnostic"]["pattern"]["classification"] for record in bending_records)
    assert all("segments" in record["outputs"]["bending_diagnostic"] for record in bending_records)


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _group_by_run(rows: Iterable[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["run_id"], []).append(row)
    return grouped


def _chord_slope(rows: list[dict[str, str]], x1: float, x2: float) -> float:
    y1 = _interpolate(rows, x1)
    y2 = _interpolate(rows, x2)
    return (y2 - y1) / (x2 - x1)


def _load_strain_slope_kN_per_microstrain(rows: list[dict[str, str]], left_index: int, right_index: int) -> float:
    left = rows[left_index]
    right = rows[right_index]
    load_delta_kN = (float(right["load_N"]) - float(left["load_N"])) / 1000.0
    strain_delta_microstrain = (float(right["mean_strain"]) - float(left["mean_strain"])) * 1_000_000.0
    return load_delta_kN / strain_delta_microstrain


def _interpolate(rows: list[dict[str, str]], target: float) -> float:
    pairs = sorted(
        (float(row["mean_strain"]), float(row["stress_MPa"]))
        for row in rows
        if row["mean_strain"] and row["stress_MPa"]
    )
    for index, (x_value, y_value) in enumerate(pairs):
        if x_value == target:
            return y_value
        if x_value > target and index > 0:
            x0, y0 = pairs[index - 1]
            ratio = (target - x0) / (x_value - x0)
            return y0 + ratio * (y_value - y0)
    raise AssertionError(f"Could not interpolate target {target}")


def _float(value: str) -> float | None:
    return None if value in ("", None) else float(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
