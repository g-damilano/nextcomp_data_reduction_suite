from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout
from operations.core.evidence_contract import operation_evidence_contract_records


def test_every_output_affecting_iso_operation_has_evidence_contract() -> None:
    contracts = operation_evidence_contract_records()
    expected = {
        "resolve_experiment_boundaries",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
        "bending_diagnostic",
        "validation_summary",
        "final_selection",
        "aggregate_curve_family",
        "aggregate_statistics",
    }

    assert expected <= set(contracts)
    for operation_type in expected:
        contract = contracts[operation_type]
        assert contract["operation_type"] == operation_type
        assert contract["evidence_role"] in {
            "primary_audit_block",
            "supporting_evidence",
            "hidden_by_default",
            "workbench_only",
            "test_report_value",
        }
        assert contract["default_audit_view"]
        assert contract["default_workbench_view"] or operation_type in {"validation_summary", "final_selection", "aggregate_curve_family", "aggregate_statistics"}


def test_procedure_evidence_summary_and_operation_trace_are_written_to_aligned_mtda(stage26_canonical_mtda: Path) -> None:
    audit = _json_member(stage26_canonical_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    method_outputs = _json_member(stage26_canonical_mtda, MTDAAlignedLayout.method_outputs)

    procedure = audit["procedure_evidence"]
    assert procedure["artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#procedure_evidence"
    assert procedure["run_count"] == 7
    assert procedure["operation_count"] > 0

    trace = method_outputs["operation_trace"]
    assert trace["method"]["method_id"] == "iso14126_2023"
    operations = trace["operations"]
    assert any(row["run_id"] == "run_006" for row in operations)

    chord = next(row for row in operations if row["operation_type"] == "chord_slope" and row["run_id"] == "run_006")
    assert chord["procedure_step_id"] == "reduce.chord_modulus"
    assert chord["evidence_contract_id"].endswith(":chord_slope:v0.1.0")
    assert chord["default_audit_block"] == "run_stress_strain_reduction"
    assert chord["default_audit_view"] == "chord_slope_overlay"
    assert chord["workbench_view"] == "chord_slope_view"
    assert chord["report_roles"] == ["compressive_modulus"]
    assert chord["evidence_refs"]["operation_record"].startswith("audit/operation_log.json#")
    assert chord["surface_policy_snapshot"]["test_report"] == "formal_result"


def test_operation_log_carries_surface_contract_fields(stage26_canonical_mtda: Path) -> None:
    operation_trace = _json_member(stage26_canonical_mtda, MTDAAlignedLayout.method_outputs)["operation_trace"]
    records = operation_trace["operations"]
    record = next(row for row in records if row["operation_type"] == "resolve_experiment_boundaries" and row["run_id"] == "run_006")

    assert record["procedure_step_id"] == "resolve.experiment_boundaries"
    assert record["evidence_contract_id"].endswith(":resolve_experiment_boundaries:v0.1.0")
    assert record["evidence_role"] == "supporting_evidence"
    assert record["default_audit_block"] == "run_stress_strain_reduction"
    assert record["default_audit_view"] == "boundary_markers_overlay"
    assert record["workbench_view"] == "boundary_resolution_view"
    assert "evidence_refs" in record


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))
