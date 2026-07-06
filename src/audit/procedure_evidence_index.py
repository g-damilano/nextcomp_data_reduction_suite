from __future__ import annotations

from collections import defaultdict
from typing import Any

from methods.core.method_result import MethodRunResult
from operations.core.evidence_contract import (
    get_operation_evidence_contract,
    operation_evidence_contract_records,
)


SCHEMA_VERSION = "0.1.0"


RUN_BLOCK_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "block_role": "run_identity_disposition",
        "title": "Run Identity and Disposition",
        "purpose": "Bind source identity, specimen geometry, and run-level disposition before method evidence is interpreted.",
        "artifact_refs": [
            "mapping/mapping_profile_used.json",
            "method_outputs/specimen_results.csv",
            "acceptance/final_report_runs.csv",
        ],
    },
    {
        "block_role": "run_stress_strain_reduction",
        "title": "Stress-strain reduction evidence",
        "purpose": "Group the operation evidence that constructs the bounded stress-strain method outputs.",
        "expected_operation_types": [
            "resolve_experiment_boundaries",
            "construct_mean_series",
            "derive_stress",
            "max_point",
            "value_at_max",
            "chord_slope",
        ],
        "artifact_refs": [
            "audit/boundary_resolution.json",
            "method_outputs/boundaries.csv",
            "method_outputs/curves/stress_strain_family_bounded.csv",
            "audit/operation_log.json",
        ],
    },
    {
        "block_role": "run_bending_evidence",
        "title": "Bending evidence",
        "purpose": "Keep bending diagnostics separate from stress-strain reduction so it remains an acceptance/quality cue.",
        "expected_operation_types": ["bending_diagnostic"],
        "artifact_refs": ["audit/operation_log.json", "audit/inspections.json"],
    },
    {
        "block_role": "run_validation_warning_evidence",
        "title": "Validation and Warning Evidence",
        "purpose": "Summarize validation checks, warnings, and review triggers for this run.",
        "artifact_refs": [
            "validation/validation_report.json",
            "validation/deviations.csv",
            "audit/warnings.json",
        ],
    },
    {
        "block_role": "run_selection_consequence",
        "title": "Selection Consequence",
        "purpose": "Show whether the run is included, reviewed, discharged, or overridden for final reporting.",
        "artifact_refs": [
            "acceptance/acceptance_report.json",
            "acceptance/run_flags.csv",
            "acceptance/final_report_runs.csv",
            "acceptance/discharged_runs.csv",
        ],
    },
)


AGGREGATE_BLOCK_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "block_role": "aggregate_final_selected_run_set",
        "title": "Final Selected Run Set",
        "purpose": "Record the run set used by formal aggregate results after machine acceptance and human decisions.",
        "artifact_refs": [
            "acceptance/selection_sets_final.json",
            "acceptance/final_report_runs.csv",
            "acceptance/selection_membership_final.csv",
        ],
    },
    {
        "block_role": "aggregate_curve_family_statistics",
        "title": "Aggregate Curve-Family and Statistical Evidence",
        "purpose": "Trace the boundary-aligned aggregate curves, statistics, and curve-family assessment.",
        "artifact_refs": [
            "report/aligned_curves.csv",
            "report/aggregate_statistics.csv",
            "report/vega_specs/aggregate_stress_strain_mean_variability.json",
            "acceptance/curve_family/curve_family_report.json",
            "acceptance/curve_family/aligned_curve_family.csv",
        ],
    },
    {
        "block_role": "aggregate_finalization_trace",
        "title": "Final Override and Finalization Trace",
        "purpose": "Keep report-only amendments, selection overrides, and archive finalization visible without changing calculations.",
        "artifact_refs": [
            "acceptance/human_decisions.json",
            "acceptance/override_ledger.json",
            "report/report_field_overrides.json",
            "finalization/archive_state.json",
            "finalization/amendment_ledger.json",
        ],
    },
)


def build_procedure_evidence_index(result: MethodRunResult) -> dict[str, Any]:
    """Index operation evidence once, then point surfaces at it.

    The operation log remains the stored evidence source. This index is a
    semantic map that tells Audit, Workbench, Wizard, and Test Report which
    operation results belong to which role.
    """

    run_ids = [str(run_id) for run_id in result.source.run_ids]
    runs: dict[str, dict[str, Any]] = {run_id: {"steps": []} for run_id in run_ids}
    aggregate_steps: list[dict[str, Any]] = []

    for row in result.operation_log:
        if not isinstance(row, dict):
            continue
        operation_type = str(row.get("operation_type") or row.get("operation") or "")
        contract = get_operation_evidence_contract(operation_type)
        run_id = str(row.get("run_id") or "")
        entry = _procedure_entry(row, contract.to_dict())
        if run_id:
            runs.setdefault(run_id, {"steps": []}).setdefault("steps", []).append(entry)
        else:
            aggregate_steps.append(entry)

    for payload in runs.values():
        steps = payload.get("steps", [])
        if isinstance(steps, list):
            steps.sort(key=_sequence_key)
    aggregate_steps.sort(key=_sequence_key)
    aggregate_steps.append(_virtual_curve_diagnostic_entry())

    return {
        "schema_id": "audit.procedure_evidence_index.v0_1",
        "schema_version": SCHEMA_VERSION,
        "method_id": result.method_package.method_id,
        "method_version": result.method_package.version,
        "source_package": str(result.source.path),
        "run_count": len(run_ids),
        "operation_count": sum(len(payload.get("steps", [])) for payload in runs.values()) + len(aggregate_steps),
        "operation_contracts": operation_evidence_contract_records(),
        "runs": runs,
        "aggregate_steps": aggregate_steps,
        "dataset_level_steps": aggregate_steps,
        "surface_roles": {
            "wizard": "action_decision_repair",
            "audit_report": "evidence_traceability",
            "test_report": "formal_result",
            "method_development_workbench": "operation_debug",
            "mtda": "archive_backing_store",
        },
    }


def _virtual_curve_diagnostic_entry() -> dict[str, Any]:
    contract = get_operation_evidence_contract("curve_family_diagnostic").to_dict()
    return {
        "procedure_step_id": "acceptance.curve_family_diagnostic",
        "step_id": "acceptance.curve_family_diagnostic",
        "step_label": "Curve-family diagnostic",
        "phase": "method_acceptance",
        "operation_type": "curve_family_diagnostic",
        "operation_result_ref": "acceptance/curve_family/curve_diagnostic_report.json",
        "operation_id": "curve_family_diagnostic",
        "operation_sequence": 0,
        "evidence_contract_id": contract.get("contract_id", ""),
        "evidence_role": contract.get("evidence_role", ""),
        "default_audit_block": contract.get("default_audit_block", ""),
        "audit_block_id": contract.get("default_audit_block", ""),
        "default_audit_view": contract.get("default_audit_view", ""),
        "audit_view_type": contract.get("default_audit_view", ""),
        "report_roles": [],
        "report_role": "",
        "workbench_link": "workbench/index.html#tab=acceptance&context=curve_family_diagnostic",
        "workbench_ref": "workbench/operation_trace.json#/diagnostics/curve_family",
        "workbench_view": contract.get("workbench_view") or "",
        "workbench_view_type": contract.get("workbench_view") or "",
        "evidence_refs": {
            "report": "acceptance/curve_family/curve_diagnostic_report.json",
            "scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
            "reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
            "residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
            "policy": "acceptance/curve_family/curve_diagnostic_policy.json",
        },
        "artifact_refs": [
            "acceptance/curve_family/curve_diagnostic_report.json",
            "acceptance/curve_family/curve_diagnostic_scores.csv",
            "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
            "acceptance/curve_family/curve_diagnostic_residuals.csv",
            "acceptance/curve_family/curve_diagnostic_policy.json",
        ],
        "status": "recorded",
        "warnings": [],
        "input_schema": contract.get("input_schema", {}),
        "output_schema": contract.get("output_schema", {}),
        "surface_policy_snapshot": {"audit_report": "primary_audit_block", "workbench": "detailed"},
    }


def build_audit_block_index(
    result: MethodRunResult,
    procedure_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    procedure_index = procedure_index or build_procedure_evidence_index(result)
    run_packets: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []

    runs = procedure_index.get("runs") if isinstance(procedure_index.get("runs"), dict) else {}
    for run_id in [str(run_id) for run_id in result.source.run_ids]:
        payload = runs.get(run_id, {})
        raw_entries = payload.get("steps", []) if isinstance(payload, dict) else payload
        entries = [entry for entry in raw_entries if isinstance(entry, dict)] if isinstance(raw_entries, list) else []
        by_role = _entries_by_block_role(entries)
        packet_blocks: list[dict[str, Any]] = []
        for template in RUN_BLOCK_TEMPLATES:
            block = _run_block(run_id, template, by_role.get(str(template["block_role"]), []), result)
            packet_blocks.append(block)
            blocks.append(block)
        run_packets.append(
            {
                "scope": "run",
                "run_id": run_id,
                "packet_id": f"packet_{_safe_id(run_id)}",
                "title": f"Run-wise audit packet - {run_id}",
                "blocks": packet_blocks,
            }
        )

    aggregate_blocks = [_aggregate_block(template, result) for template in AGGREGATE_BLOCK_TEMPLATES]
    blocks.extend(aggregate_blocks)

    return {
        "schema_id": "audit.audit_block_index.v0_1",
        "schema_version": SCHEMA_VERSION,
        "method_id": result.method_package.method_id,
        "method_version": result.method_package.version,
        "source_index_member": "audit/procedure_evidence_index.json",
        "audit_overview": {
            "block_id": "audit_overview",
            "scope": "dataset",
            "title": "Audit Overview",
            "purpose": "Orient the reader to method execution, evidence grouping, and surface roles.",
            "artifact_refs": ["audit/audit_report.json", "surface_manifest.json"],
        },
        "run_packets": run_packets,
        "aggregate_packet": {
            "scope": "aggregate",
            "packet_id": "aggregate_audit_packet",
            "title": "Aggregate audit packet",
            "blocks": aggregate_blocks,
        },
        "blocks": blocks,
        "summary": {
            "run_packet_count": len(run_packets),
            "aggregate_block_count": len(aggregate_blocks),
            "block_count": len(blocks),
            "stress_strain_grouping": "experiment boundaries, mean strain, stress derivation, max/strength, failure strain, and chord modulus grouped per run",
            "bending_separate": True,
        },
    }


def _procedure_entry(row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    operation_id = str(row.get("operation_id") or "")
    sequence = row.get("sequence")
    operation_type = str(row.get("operation_type") or row.get("operation") or "")
    evidence_refs = row.get("evidence_refs") if isinstance(row.get("evidence_refs"), dict) else {}
    return {
        "procedure_step_id": str(row.get("procedure_step_id") or row.get("recipe_step_id") or operation_id or operation_type),
        "step_id": str(row.get("procedure_step_id") or row.get("recipe_step_id") or operation_id or operation_type),
        "step_label": str(row.get("recipe_step_label") or operation_type),
        "phase": str(row.get("phase") or ""),
        "operation_type": operation_type,
        "operation_result_ref": evidence_refs.get("operation_record") or f"audit/operation_log.json#/sequence/{sequence}",
        "operation_id": operation_id,
        "operation_sequence": sequence,
        "evidence_contract_id": row.get("evidence_contract_id") or contract.get("contract_id", ""),
        "evidence_role": row.get("evidence_role") or contract.get("evidence_role", ""),
        "default_audit_block": row.get("default_audit_block") or contract.get("default_audit_block", ""),
        "audit_block_id": row.get("default_audit_block") or contract.get("default_audit_block", ""),
        "default_audit_view": row.get("default_audit_view") or row.get("audit_view_hint") or contract.get("default_audit_view") or "",
        "audit_view_type": row.get("default_audit_view") or row.get("audit_view_hint") or contract.get("default_audit_view") or "",
        "report_roles": list(row.get("report_roles", []) or contract.get("report_roles", []) or []),
        "report_role": (row.get("report_roles", []) or contract.get("report_roles", []) or [""])[0],
        "workbench_link": f"workbench/index.html#operation-{_safe_id(operation_id)}",
        "workbench_ref": evidence_refs.get("workbench_record") or f"workbench/operation_trace.json#/operations/{sequence}",
        "workbench_view": row.get("workbench_view") or contract.get("workbench_view") or contract.get("default_workbench_view", ""),
        "workbench_view_type": row.get("workbench_view") or contract.get("workbench_view") or contract.get("default_workbench_view", ""),
        "evidence_refs": evidence_refs,
        "artifact_refs": _artifact_refs(contract),
        "status": str(row.get("status") or ""),
        "warnings": list(row.get("warnings", []) or []),
        "input_schema": contract.get("input_schema", {}),
        "output_schema": contract.get("output_schema", {}),
        "surface_policy_snapshot": row.get("surface_policy_snapshot", {}),
    }


def _run_block(
    run_id: str,
    template: dict[str, Any],
    entries: list[dict[str, Any]],
    result: MethodRunResult,
) -> dict[str, Any]:
    block_role = str(template["block_role"])
    expected = [str(item) for item in template.get("expected_operation_types", []) or []]
    operation_types = [str(entry.get("operation_type")) for entry in entries]
    block: dict[str, Any] = {
        "block_id": f"{_safe_id(run_id)}_{block_role}",
        "block_role": block_role,
        "scope": "run",
        "run_id": run_id,
        "title": str(template["title"]),
        "purpose": str(template["purpose"]),
        "expected_operation_types": expected,
        "operation_types": operation_types,
        "operation_refs": [entry.get("operation_result_ref") for entry in entries if entry.get("operation_result_ref")],
        "workbench_links": [entry.get("workbench_link") for entry in entries if entry.get("workbench_link")],
        "artifact_refs": list(template.get("artifact_refs", []) or []),
        "operations": [_operation_summary(entry) for entry in entries],
        "status": _block_status(entries),
    }
    if block_role == "run_validation_warning_evidence":
        block["validation_checks"] = _validation_rows_for_run(result, run_id)
        block["warnings"] = _warning_rows_for_run(result, run_id)
    if block_role == "run_selection_consequence":
        block["selection"] = _selection_for_run(result, run_id)
        block["flags"] = [row for row in result.run_flags if str(row.get("run_id") or "") == run_id]
    return block


def _aggregate_block(template: dict[str, Any], result: MethodRunResult) -> dict[str, Any]:
    block_role = str(template["block_role"])
    block: dict[str, Any] = {
        "block_id": block_role,
        "block_role": block_role,
        "scope": "aggregate",
        "title": str(template["title"]),
        "purpose": str(template["purpose"]),
        "artifact_refs": list(template.get("artifact_refs", []) or []),
        "status": "recorded",
    }
    if block_role == "aggregate_final_selected_run_set":
        block["selected_run_ids"] = _selected_run_ids(result)
    elif block_role == "aggregate_curve_family_statistics":
        block["boundary_aligned_aggregation"] = _aggregation_is_boundary_aligned(result)
        block["curve_family_flag_count"] = len(result.curve_family_flags or [])
    elif block_role == "aggregate_finalization_trace":
        block["human_decision_count"] = len(result.human_decision_rows or [])
        block["report_override_count"] = len(result.report_overrides or ())
    return block


def _entries_by_block_role(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[str(entry.get("audit_block_id") or "run_validation_warning_evidence")].append(entry)
    for rows in grouped.values():
        rows.sort(key=_sequence_key)
    return dict(grouped)


def _operation_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_id": entry.get("step_id", ""),
        "step_label": entry.get("step_label", ""),
        "operation_type": entry.get("operation_type", ""),
        "evidence_role": entry.get("evidence_role", ""),
        "report_role": entry.get("report_role", ""),
        "status": entry.get("status", ""),
        "audit_view_type": entry.get("audit_view_type", ""),
        "workbench_link": entry.get("workbench_link", ""),
        "warnings": len(entry.get("warnings", []) or []),
    }


def _artifact_refs(contract: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for requirement in contract.get("evidence_artifacts_required", []) or []:
        if isinstance(requirement, dict) and requirement.get("member"):
            refs.append(str(requirement["member"]))
    return refs


def _validation_rows_for_run(result: MethodRunResult, run_id: str) -> list[dict[str, Any]]:
    checks = result.validation_report.get("checks", [])
    return [row for row in checks if isinstance(row, dict) and str(row.get("run_id") or "") == run_id]


def _warning_rows_for_run(result: MethodRunResult, run_id: str) -> list[dict[str, Any]]:
    return [row for row in result.warnings if isinstance(row, dict) and str(row.get("run_id") or "") == run_id]


def _selection_for_run(result: MethodRunResult, run_id: str) -> dict[str, Any]:
    for row in result.final_report_runs or []:
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id:
            return dict(row)
    default_selection = str(result.acceptance_report.get("default_selection_set") or "")
    for row in result.selection_membership:
        if (
            isinstance(row, dict)
            and str(row.get("run_id") or "") == run_id
            and str(row.get("selection_set") or "") == default_selection
        ):
            return dict(row)
    return {"run_id": run_id, "selection_state": "not_recorded"}


def _selected_run_ids(result: MethodRunResult) -> list[str]:
    rows = result.final_report_runs or []
    selected: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _truthy(row.get("final_included", row.get("included", True))):
            selected.append(str(row.get("run_id") or ""))
    return [run_id for run_id in selected if run_id]


def _block_status(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "recorded"
    statuses = {str(entry.get("status") or "") for entry in entries}
    if "failed" in statuses or "fail" in statuses:
        return "fail"
    if any(status in {"pass_with_warning", "warning", "warn"} for status in statuses):
        return "warn"
    return "pass"


def _sequence_key(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("operation_sequence") if "operation_sequence" in entry else entry.get("sequence"))
    except (TypeError, ValueError):
        return 0


def _safe_id(value: object) -> str:
    text = str(value or "").strip()
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in text).strip("_") or "item"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _aggregation_is_boundary_aligned(result: MethodRunResult) -> bool:
    policy = result.method_package.curve_aggregation_policy
    if isinstance(policy, dict):
        curve_policy = policy.get("curve_aggregation") if isinstance(policy.get("curve_aggregation"), dict) else policy
        alignment = curve_policy.get("alignment") if isinstance(curve_policy, dict) else {}
        if isinstance(alignment, dict) and alignment.get("domain") == "experiment_progress":
            return True
    return any(
        isinstance(row, dict) and row.get("alignment_domain") == "experiment_progress"
        for row in result.curve_family_aligned_rows or []
    )
