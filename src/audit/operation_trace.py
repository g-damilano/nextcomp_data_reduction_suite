from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from mapping import MappingCandidateDiscovery, build_mapping_resolution_report
from methods.core.method_result import MethodRunResult


OPERATION_SOURCE_PATHS: dict[str, str] = {
    "map_channel": "src/operations/curve/derive_series.py",
    "map_scalar": "src/operations/curve/derive_series.py",
    "derive_area": "src/operations/curve/derive_series.py",
    "orient_strain_channels": "src/operations/curve/orient_strain_channels.py",
    "construct_mean_series": "src/operations/curve/derive_series.py",
    "gate_experiment_signal": "src/operations/curve/gate_experiment_signal.py",
    "resolve_experiment_boundaries": "src/operations/curve/boundary_resolution.py",
    "derive_stress": "src/operations/curve/derive_series.py",
    "derive_series_by_scalar": "src/operations/curve/derive_series.py",
    "max_point": "src/operations/curve/max_point.py",
    "value_at_index": "src/operations/curve/value_at.py",
    "value_at_max": "src/operations/curve/value_at.py",
    "chord_slope": "src/operations/curve/chord_slope.py",
    "bending_diagnostic": "src/operations/diagnostics/bending.py",
}


def build_operation_trace(result: MethodRunResult) -> dict[str, Any]:
    """Build a UI-oriented trace payload from a method-run result.

    The trace is intentionally derived from existing MethodRunResult evidence. It does not
    re-run or mutate the method; it packages operation logs, curve rows, summaries, and
    recipe text into a single payload that a development workbench can replay visually.
    """
    curve_rows_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.curve_family:
        curve_rows_by_run[str(row.get("run_id"))].append(row)
    full_curve_rows_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.full_curve_family or []:
        full_curve_rows_by_run[str(row.get("run_id"))].append(row)

    operation_rows: list[dict[str, Any]] = []
    validation_by_operation = _validation_by_key(result, "operation_id")
    validation_by_step = _validation_by_key(result, "recipe_step_id")
    for row in result.operation_log:
        operation_type = str(row.get("operation_type") or row.get("operation") or "")
        record = dict(row)
        record["implementation_path"] = OPERATION_SOURCE_PATHS.get(operation_type, "")
        record["workbench_view"] = row.get("workbench_view") or row.get("audit_view_hint") or _default_view_type(operation_type)
        record["view_type"] = row.get("audit_view_hint") or record["workbench_view"]
        operation_checks = list(validation_by_operation.get(str(row.get("operation_id")), []))
        operation_checks.extend(validation_by_step.get(str(row.get("recipe_step_id")), []))
        record["validation_checks"] = operation_checks
        record["validation_status"] = _validation_status(operation_checks)
        operation_rows.append(record)

    mapping_candidate_report = MappingCandidateDiscovery().discover(
        source=result.source,
        method_package=result.method_package,
    )
    mapping_resolution_report = build_mapping_resolution_report(
        mapping=result.mapping,
        candidate_report=mapping_candidate_report,
    )

    return {
        "trace_format": "method_development_trace",
        "trace_version": "0.1.0",
        "source": {
            "path": str(result.source.path),
            "run_ids": list(result.source.run_ids),
            "schema_id": result.source.manifest.get("schema_id"),
            "schema_version": result.source.manifest.get("schema_version"),
        },
        "method": {
            "method_id": result.method_package.method_id,
            "name": result.method_package.name,
            "version": result.method_package.version,
            "root": str(result.method_package.root),
        },
        "mapping": result.mapping,
        "mapping_candidate_report": mapping_candidate_report,
        "mapping_resolution_report": mapping_resolution_report,
        "operation_input_mapping": _operation_input_mapping(result, mapping_resolution_report),
        "readiness": result.readiness_report,
        "readiness_summary": result.readiness_summary,
        "resolved_inputs": result.resolved_inputs,
        "missing_inputs": result.missing_inputs,
        "recipes": {
            "resolve": result.method_package.resolve_recipe,
            "reduce": result.method_package.reduce_recipe,
            "audit": result.method_package.audit_recipe,
            "acceptance": result.method_package.acceptance_recipe,
            "method_inputs": result.method_package.method_inputs,
            "resolve_text": _read_recipe_text(result.method_package.root / "resolve_recipe.yaml"),
            "reduce_text": _read_recipe_text(result.method_package.root / "reduce_recipe.yaml"),
            "acceptance_text": _read_recipe_text(result.method_package.root / "acceptance_recipe.yaml"),
            "curve_family_acceptance": result.method_package.curve_family_acceptance_recipe,
            "curve_family_acceptance_text": _read_recipe_text(result.method_package.root / "curve_family_acceptance_recipe.yaml"),
            "method_inputs_text": _read_recipe_text(result.method_package.root / "method_inputs.yaml"),
        },
        "runs": _build_run_cards(result),
        "operations": operation_rows,
        "curve_rows_by_run": dict(curve_rows_by_run),
        "full_curve_rows_by_run": dict(full_curve_rows_by_run),
        "experiment_boundaries": result.experiment_boundaries or [],
        "specimen_results": result.specimen_results,
        "dataset_summary": result.dataset_summary,
        "dataset_summary_by_selection": result.dataset_summary_by_selection,
        "validation": result.validation_report,
        "validation_summary": result.validation_summary,
        "validation_deviations": result.validation_deviations,
        "acceptance": result.acceptance_report,
        "acceptance_summary": result.acceptance_summary,
        "run_flags": result.run_flags,
        "selection_sets": result.selection_sets,
        "selection_membership": result.selection_membership,
        "human_decisions": result.human_decisions or {},
        "override_ledger": result.override_ledger or {},
        "selection_sets_final": result.selection_sets_final or {},
        "selection_membership_final": result.selection_membership_final or [],
        "final_report_runs": result.final_report_runs or [],
        "report_completion": {},
        "report_values_used": [],
        "missing_report_fields": [],
        "report_overrides": {"overrides": list(result.report_overrides or ())},
        "report_override_ledger": {},
        "finalization": {},
        "curve_family_assessment": result.curve_family_assessment or {},
        "curve_family_scores": result.curve_family_scores or [],
        "curve_family_flags": result.curve_family_flags or [],
        "curve_family_reference_rows": result.curve_family_reference_rows or [],
        "curve_family_aligned_rows": result.curve_family_aligned_rows or [],
        "curve_family_residual_rows": result.curve_family_residual_rows or [],
        "discharge_report": result.discharge_report,
        "discharged_runs": result.discharged_runs,
        "inspections": result.inspections,
        "warnings": result.warnings,
    }


def _build_run_cards(result: MethodRunResult) -> list[dict[str, Any]]:
    result_by_run = {str(row.get("run_id")): row for row in result.specimen_results}
    validation_by_run: dict[str, list[dict[str, Any]]] = {}
    for check in result.validation_report.get("checks", []):
        if isinstance(check, dict):
            validation_by_run.setdefault(str(check.get("run_id")), []).append(check)
    acceptance_flags_by_run: dict[str, list[dict[str, Any]]] = {}
    for flag in result.run_flags:
        acceptance_flags_by_run.setdefault(str(flag.get("run_id")), []).append(flag)
    default_selection = str(result.acceptance_report.get("default_selection_set") or "")
    default_members = {
        str(row.get("run_id"))
        for row in result.selection_membership
        if row.get("selection_set") == default_selection and row.get("included") in {True, "True", "true", "1", 1}
    }
    final_by_run = {
        str(row.get("run_id")): row
        for row in (result.final_report_runs or [])
        if isinstance(row, dict) and row.get("run_id")
    }
    curve_by_run = {
        str(row.get("run_id")): row
        for row in (result.curve_family_scores or [])
        if isinstance(row, dict) and row.get("run_id")
    }
    run_states = result.acceptance_report.get("run_states", {})
    run_states = run_states if isinstance(run_states, dict) else {}
    cards: list[dict[str, Any]] = []
    for run_id in result.source.run_ids:
        row = result_by_run.get(run_id, {})
        validation_checks = validation_by_run.get(run_id, [])
        flags = acceptance_flags_by_run.get(run_id, [])
        cards.append(
            {
                "run_id": run_id,
                "specimen_name": row.get("specimen_name"),
                "validity": row.get("validity"),
                "failure_mode": row.get("failure_mode"),
                "warnings": row.get("warnings"),
                "compressive_strength_MPa": row.get("compressive_strength_MPa"),
                "compressive_modulus_MPa": row.get("compressive_modulus_MPa"),
                "bending_max_percent": row.get("bending_max_percent"),
                "bending_pattern": row.get("bending_pattern"),
                "validation_status": _validation_status(validation_checks),
                "validation_checks": len(validation_checks),
                "acceptance_state": run_states.get(run_id, "accepted"),
                "acceptance_flags": len(flags),
                "included_in_default": run_id in default_members,
                "human_decision": final_by_run.get(run_id, {}).get("human_decision", ""),
                "final_included": final_by_run.get(run_id, {}).get("final_included", run_id in default_members),
                "curve_family_classification": curve_by_run.get(run_id, {}).get("classification", ""),
                "curve_family_normalized_rmse": curve_by_run.get(run_id, {}).get("normalized_rmse", ""),
            }
        )
    return cards


def _validation_by_key(result: MethodRunResult, key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for check in result.validation_report.get("checks", []):
        if isinstance(check, dict) and check.get(key):
            grouped.setdefault(str(check.get(key)), []).append(check)
    return grouped


def _validation_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(check.get("status")) for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    if "pass" in statuses:
        return "pass"
    return "not_applicable"


def _operation_input_mapping(result: MethodRunResult, resolution_report: dict[str, Any]) -> list[dict[str, Any]]:
    resolution_by_role = {
        str(row.get("source_role")): row
        for row in resolution_report.get("resolutions", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    requirements = result.method_package.method_inputs.get("requirements", [])
    if not isinstance(requirements, list):
        return rows
    for item in requirements:
        if not isinstance(item, dict):
            continue
        source_role = str(item.get("source_role") or "")
        mapped_source, source_kind = _mapped_source_for_role(result.mapping, source_role)
        resolution = resolution_by_role.get(source_role, {})
        rows.append(
            {
                "requirement_id": item.get("requirement_id", ""),
                "method_field": item.get("method_field") or item.get("requirement_id", ""),
                "source_role": source_role,
                "severity": item.get("severity", ""),
                "mapped_source": mapped_source,
                "source_kind": source_kind,
                "resolution_status": resolution.get("status", "unmapped" if not mapped_source else "confirmed"),
                "confidence": resolution.get("confidence", ""),
                "candidate_count": resolution.get("candidate_count", ""),
            }
        )
    return rows


def _mapped_source_for_role(mapping: dict[str, Any], source_role: str) -> tuple[str, str]:
    for section in ("channels", "fields", "tokens"):
        payload = mapping.get(section)
        if not isinstance(payload, dict) or source_role not in payload:
            continue
        value = payload[source_role]
        if isinstance(value, dict):
            if str(value.get("status") or "").casefold() in {"ambiguous", "unresolved"}:
                return "", section.rstrip("s")
            value = value.get("source") or value.get("field") or value.get("name") or value.get("token") or value.get("channel")
        return str(value or ""), section.rstrip("s")
    return "", "missing"


def _read_recipe_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _default_view_type(operation_type: str) -> str:
    if operation_type in {"map_channel"}:
        return "mapped_channel_series"
    if operation_type in {"map_scalar", "derive_area"}:
        return "scalar_card"
    if operation_type == "construct_mean_series":
        return "mean_strain_construction"
    if operation_type == "gate_experiment_signal":
        return "experiment_signal_gate"
    if operation_type == "resolve_experiment_boundaries":
        return "experiment_boundary_resolution"
    if operation_type == "derive_stress":
        return "stress_construction"
    if operation_type == "max_point":
        return "max_point_marker"
    if operation_type == "value_at_max":
        return "failure_strain_marker"
    if operation_type == "chord_slope":
        return "modulus_window_overlay"
    if operation_type == "bending_diagnostic":
        return "bending_pattern_assessment"
    return "operation_table"
