from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_run_service import MethodRunRequest, MethodRunService
from operations.diagnostics.bending_pattern import assess_bending_pattern
from ui.method_run_wizard.view_models.gate_summary import acceptance_gate_view_model
from ui.method_run_wizard.view_models.output_review import output_review_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def no_override_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _run_mtda(tmp_path_factory.mktemp("stage14_5_no_override") / "cluster_no_override.mtda")


@pytest.fixture(scope="module")
def remove_one_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _run_mtda(
        tmp_path_factory.mktemp("stage14_5_remove") / "cluster_remove.mtda",
        decisions=(
            {
                "run_id": "run_003",
                "decision_type": "remove",
                "reason": "Stage 14.5 cluster validation removal scenario",
                "reviewer": "cluster-validation",
                "source_surface": "test.cluster_validation",
            },
        ),
    )


@pytest.fixture(scope="module")
def restore_one_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _run_mtda(
        tmp_path_factory.mktemp("stage14_5_restore") / "cluster_restore.mtda",
        decisions=(
            {
                "run_id": "run_002",
                "decision_type": "restore",
                "reason": "Stage 14.5 cluster validation restore scenario",
                "reviewer": "cluster-validation",
                "source_surface": "test.cluster_validation",
            },
        ),
    )


@pytest.fixture(scope="module")
def strict_curve_family_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("stage14_5_strict_curve_family")
    method_copy = root / "iso14126_strict_curve_family"
    shutil.copytree(METHOD, method_copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (method_copy / "curve_family_acceptance_recipe.yaml").write_text(
        _strict_curve_family_recipe(),
        encoding="utf-8",
    )
    return _run_mtda(root / "cluster_strict_curve_family.mtda", method_path=method_copy)


def test_no_human_override_cluster_uses_final_selection_everywhere(no_override_mtda: Path) -> None:
    final_rows = _csv_member(no_override_mtda, "acceptance/final_report_runs.csv")
    final_sets = _json_member(no_override_mtda, "acceptance/selection_sets_final.json")
    human = _json_member(no_override_mtda, "acceptance/human_decisions.json")
    report = _json_member(no_override_mtda, "report/test_report.json")
    audit = _json_member(no_override_mtda, "audit/audit_report.json")
    plot_spec = _json_member(no_override_mtda, "report/aggregate_plot_spec.json")
    aggregate = _csv_member(no_override_mtda, "report/aggregate_statistics.csv")
    aligned = _csv_member(no_override_mtda, "report/aligned_curves.csv")

    final_run_ids = _included_final_run_ids(final_rows)
    machine_included_ids = {row["run_id"] for row in final_rows if _truthy(row.get("machine_included"))}

    assert final_sets["default_selection_set"] == "final_report_runs"
    assert final_sets["selection_source"] == "machine_default_confirmed"
    assert human["decisions"] == []
    assert final_run_ids == machine_included_ids

    assert report["selection_set"] == "final_report_runs"
    assert report["selection_source"] == "machine_default_confirmed"
    assert set(report["aggregate_plot_spec"]["selected_run_ids"]) == final_run_ids
    assert set(plot_spec["selected_run_ids"]) == final_run_ids
    assert {row["selection_set"] for row in aggregate} == {"final_report_runs"}
    assert {row["selection_set"] for row in aligned} == {"final_report_runs"}
    assert _aligned_run_ids(aligned) == final_run_ids
    assert _strength_n(aggregate) == len(final_run_ids)

    assert audit["human_overrides"]["decision_count"] == 0
    assert audit["acceptance"]["selection_source"] == "machine_default_confirmed"

    output_model = output_review_view_model(_output_payload(no_override_mtda))
    assert output_model["status_summary"]["final_selection_source"] == "machine_default_confirmed"
    assert output_model["surface_members"]["test_report"] == "report/test_report.html"


def test_human_remove_preserves_machine_selection_and_recomputes_reporting(remove_one_mtda: Path) -> None:
    final_rows = _csv_member(remove_one_mtda, "acceptance/final_report_runs.csv")
    ledger = _json_member(remove_one_mtda, "acceptance/override_ledger.json")
    report = _json_member(remove_one_mtda, "report/test_report.json")
    audit = _json_member(remove_one_mtda, "audit/audit_report.json")
    aggregate = _csv_member(remove_one_mtda, "report/aggregate_statistics.csv")
    aligned = _csv_member(remove_one_mtda, "report/aligned_curves.csv")
    machine_selection_sets = _json_member(remove_one_mtda, "acceptance/selection_sets.json")

    final_run_ids = _included_final_run_ids(final_rows)
    run_003 = next(row for row in final_rows if row["run_id"] == "run_003")

    assert run_003["machine_included"] == "True"
    assert run_003["final_included"] == "False"
    assert ledger["selection_source"] == "human_final"
    assert ledger["records"][0]["decision_type"] == "remove"
    assert ledger["records"][0]["run_id"] == "run_003"

    assert report["selection_set"] == "final_report_runs"
    assert report["selection_source"] == "human_final"
    assert "run_003" not in set(report["aggregate_plot_spec"]["selected_run_ids"])
    assert "run_003" not in _aligned_run_ids(aligned)
    assert _strength_n(aggregate) == len(final_run_ids)

    machine_sets = {item["selection_id"]: item for item in machine_selection_sets["selection_sets"]}
    assert "run_003" in machine_sets["user_valid_runs"]["run_ids"]
    assert audit["human_overrides"]["decision_count"] == 1
    assert audit["human_overrides"]["decisions"][0]["reason"] == "Stage 14.5 cluster validation removal scenario"


def test_human_restore_preserves_machine_discharge_reason_and_updates_report(restore_one_mtda: Path) -> None:
    final_rows = _csv_member(restore_one_mtda, "acceptance/final_report_runs.csv")
    discharge = _json_member(restore_one_mtda, "acceptance/discharge_report.json")
    report = _json_member(restore_one_mtda, "report/test_report.json")
    aggregate = _csv_member(restore_one_mtda, "report/aggregate_statistics.csv")
    aligned = _csv_member(restore_one_mtda, "report/aligned_curves.csv")
    audit = _json_member(restore_one_mtda, "audit/audit_report.json")

    run_002 = next(row for row in final_rows if row["run_id"] == "run_002")
    discharge_002 = next(record for record in discharge["records"] if record["run_id"] == "run_002")
    final_run_ids = _included_final_run_ids(final_rows)

    assert run_002["machine_state"] == "excluded"
    assert run_002["machine_included"] == "False"
    assert run_002["human_decision"] == "restore"
    assert run_002["final_included"] == "True"
    assert discharge_002["primary_reason"]
    assert any(flag["flag_id"] == "user_validity_invalid:run_002" for flag in discharge_002["flags"])

    assert report["selection_source"] == "human_final"
    assert "run_002" in set(report["aggregate_plot_spec"]["selected_run_ids"])
    assert "run_002" in _aligned_run_ids(aligned)
    assert _strength_n(aggregate) == len(final_run_ids)
    assert audit["human_overrides"]["decisions"][0]["decision_type"] == "restore"


def test_curve_family_flag_propagation_cluster(strict_curve_family_mtda: Path) -> None:
    acceptance = _json_member(strict_curve_family_mtda, "acceptance/acceptance_report.json")
    discharge = _json_member(strict_curve_family_mtda, "acceptance/discharge_report.json")
    audit = _json_member(strict_curve_family_mtda, "audit/audit_report.json")
    workbench_trace = _json_member(strict_curve_family_mtda, "workbench/operation_trace.json")
    workbench_html = _text_member(strict_curve_family_mtda, "workbench/index.html")
    report = _json_member(strict_curve_family_mtda, "report/test_report.json")
    scores = _csv_member(strict_curve_family_mtda, "acceptance/curve_family/curve_family_scores.csv")
    flags = _csv_member(strict_curve_family_mtda, "acceptance/curve_family/curve_family_flags.csv")

    acceptance_flags = [flag for flag in acceptance["flags"] if flag["source"] == "curve_family_assessment"]
    discharged_curve_flags = [
        flag
        for record in discharge["records"]
        for flag in record["flags"]
        if flag["source"] == "curve_family_assessment"
    ]

    assert scores
    assert flags
    assert acceptance_flags
    assert discharged_curve_flags
    assert audit["curve_family_assessment"]["flag_count"] == len(flags)
    assert workbench_trace["curve_family_scores"]
    assert "Curve-Family Assessment" in workbench_html
    assert "curveFamilyChart" in workbench_html
    assert any(row.get("curve_family_classification") for row in report["failure_analysis_run_evidence"])


def test_bending_classification_survives_acceptance_discharge_report_and_workbench(no_override_mtda: Path) -> None:
    spike_values = [5.0] * 100
    spike_values[20] = 12.0
    sustained_values = [5.0] * 100
    for index in range(40, 48):
        sustained_values[index] = 15.0
    spike = _assess_bending(spike_values)
    sustained = _assess_bending(sustained_values)
    assert spike["pattern"]["classification"] == "PASS_WITH_SPIKES"
    assert sustained["pattern"]["classification"] == "FAIL_SUSTAINED_BENDING"

    acceptance = _json_member(no_override_mtda, "acceptance/acceptance_report.json")
    discharge = _json_member(no_override_mtda, "acceptance/discharge_report.json")
    audit_html = _text_member(no_override_mtda, "audit/audit_report.html")
    workbench = _json_member(no_override_mtda, "workbench/operation_trace.json")
    report = _json_member(no_override_mtda, "report/test_report.json")
    acceptance_model = acceptance_gate_view_model(acceptance)

    bending_flags = [flag for flag in acceptance["flags"] if "bending" in flag["flag_id"]]
    assert bending_flags
    assert any(record["flags"] for record in discharge["records"])
    assert "Bending evidence" in audit_html
    assert "bending_diagnostic" in {operation.get("operation_type") for operation in workbench["operations"]}
    assert any(row.get("bending_pattern") for row in report["failure_analysis_run_evidence"])
    assert "bending_pattern_flags" in {group["group_id"] for group in acceptance_model["groups"]}


def test_required_stage14_5_artifacts_are_present(no_override_mtda: Path) -> None:
    with zipfile.ZipFile(no_override_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}

    assert {
        "acceptance/acceptance_report.json",
        "acceptance/selection_sets.json",
        "acceptance/selection_sets_final.json",
        "acceptance/final_report_runs.csv",
        "acceptance/discharge_report.json",
        "report/test_report.html",
        "report/aggregate_statistics.csv",
        "report/aligned_curves.csv",
        "audit/audit_report.html",
        "workbench/index.html",
    } <= names


def _run_mtda(
    output_path: Path,
    *,
    method_path: Path = METHOD,
    decisions: tuple[dict[str, Any], ...] = (),
) -> Path:
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=method_path,
            mapping_path=MAPPING,
            output_path=output_path,
            overwrite=True,
            human_decisions=decisions,
        )
    )
    assert result.status == "completed"
    return output_path


def _assess_bending(values: list[float]) -> dict[str, Any]:
    return assess_bending_pattern(
        bending_series=values,
        load_series=[float(index) for index in range(len(values))],
        window_indices=range(len(values)),
        threshold_percent=10.0,
    )


def _strict_curve_family_recipe() -> str:
    return """curve_family_acceptance:
  id: iso14126_curve_family_acceptance_stage14_5_strict
  applies_to: iso14126_2023
  curve_families:
    - id: stress_strain_family
      source: method_outputs.curves.stress_strain_family
      run_id_column: run_id
      x: mean_strain
      y: stress_MPa
      selection_context: user_valid_runs
      alignment:
        mode: normalized_progress
        start_anchor: analysis_start
        end_anchor: max_stress_point
        x_common_points: 250
      reference:
        method: pointwise_median
        include_runs: selection_context
      metrics:
        - normalized_rmse
        - normalized_mae
        - integrated_absolute_residual
        - max_absolute_residual
        - curve_correlation
        - derivative_rmse
        - leave_one_out_mean_shift
      classification:
        review_if:
          normalized_rmse_gt: 0.001
        propose_remove_if:
          normalized_rmse_gt: 99.0
      outputs:
        scores_csv: acceptance/curve_family/curve_family_scores.csv
        flags_csv: acceptance/curve_family/curve_family_flags.csv
        reference_csv: acceptance/curve_family/reference_curves.csv
        aligned_curves_csv: acceptance/curve_family/aligned_curve_family.csv
        residuals_csv: acceptance/curve_family/residuals_long.csv
"""


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def _included_final_run_ids(rows: list[dict[str, str]]) -> set[str]:
    return {row["run_id"] for row in rows if _truthy(row.get("final_included") or row.get("included"))}


def _aligned_run_ids(rows: list[dict[str, str]]) -> set[str]:
    if not rows:
        return set()
    return {
        key.removesuffix("_stress_MPa")
        for key in rows[0]
        if key.endswith("_stress_MPa")
    }


def _strength_n(rows: list[dict[str, str]]) -> int:
    row = next(item for item in rows if item["metric"] == "compressive_strength_MPa")
    return int(row["n"])


def _output_payload(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        completion = json.loads(archive.read("report/report_completion_status.json"))
        validation = json.loads(archive.read("validation/validation_report.json"))
        final_sets = json.loads(archive.read("acceptance/selection_sets_final.json"))
        human = json.loads(archive.read("acceptance/human_decisions.json"))
        warnings = json.loads(archive.read("audit/warnings.json"))
    return {
        "output_path": str(path),
        "archive_members": members,
        "report_completion_status": completion.get("status", ""),
        "validation_status": validation.get("summary", {}).get("status", ""),
        "final_selection_source": final_sets.get("selection_source", ""),
        "warning_count": len(warnings) if isinstance(warnings, list) else 0,
        "human_override_count": len(human.get("decisions", [])),
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
