from __future__ import annotations

from collections.abc import Mapping
from statistics import pstdev
from typing import Any

from acceptance.acceptance_flag import (
    AcceptanceFlag,
    severity_rank,
    state_from_flags,
)
from acceptance.acceptance_recipe import AcceptanceRecipe
from acceptance.acceptance_report import AcceptanceReport, membership_rows
from acceptance.curve_family import CurveFamilyEngine
from acceptance.discharge_report import build_discharge_report
from acceptance.selection_set import SelectionSet
from acceptance.statistical_screening import robust_scalar_outliers
from diagnostics.curves import CurveFamilyDiagnostic


FIELD_RECIPE_STEPS: dict[str, str] = {
    "specimen_name": "resolve.map_specimen_name",
    "sample_id": "resolve.map_sample_id",
    "width_mm": "resolve.map_width",
    "thickness_mm": "resolve.map_thickness",
    "area_mm2": "resolve.derive_area",
    "max_load_N": "reduce.max_load",
    "compressive_strength_MPa": "reduce.max_stress",
    "compressive_failure_strain": "reduce.failure_strain",
    "compressive_modulus_MPa": "reduce.chord_modulus",
    "bending_max_percent": "reduce.bending_diagnostic",
    "bending_mean_percent": "reduce.bending_diagnostic",
    "bending_p95_percent": "reduce.bending_diagnostic",
    "bending_p99_percent": "reduce.bending_diagnostic",
    "bending_points_above_threshold": "reduce.bending_diagnostic",
    "bending_fraction_above_threshold": "reduce.bending_diagnostic",
    "bending_pattern": "reduce.bending_diagnostic",
    "experiment_signal_gate_status": "resolve.gate_experiment_signal",
    "experiment_signal_gate_confidence": "resolve.gate_experiment_signal",
    "experiment_signal_gate_report_routing_state": "resolve.gate_experiment_signal",
    "experiment_signal_gate_report_routing_severity": "resolve.gate_experiment_signal",
    "signal_window_load_scale_routing_severity": "resolve.experiment_boundaries",
    "validity": "resolve.map_validity",
    "failure_mode": "resolve.map_failure_mode",
    "requires_review": "resolve.map_requires_review",
}

METRIC_UNITS: dict[str, str] = {
    "max_load_N": "N",
    "compressive_strength_MPa": "MPa",
    "compressive_failure_strain": "mm/mm",
    "compressive_modulus_MPa": "MPa",
    "bending_max_percent": "%",
    "bending_mean_percent": "%",
    "bending_p95_percent": "%",
    "bending_p99_percent": "%",
    "bending_fraction_above_threshold": "fraction",
}


class AcceptanceEngine:
    """Evaluate acceptance flags and selection sets after validation."""

    def evaluate(
        self,
        *,
        method_id: str,
        recipe_payload: Mapping[str, Any] | None,
        specimen_results: list[dict[str, Any]],
        curve_family: list[dict[str, Any]],
        operation_log: list[dict[str, Any]],
        inspections: list[dict[str, Any]],
        validation_report: Mapping[str, Any],
        dataset: Mapping[str, Any],
        curve_family_recipe_payload: Mapping[str, Any] | None = None,
    ) -> AcceptanceReport:
        recipe = AcceptanceRecipe.from_method_recipe(recipe_payload)
        run_ids = [str(row.get("run_id")) for row in specimen_results if row.get("run_id")]
        specimen_by_run = {str(row.get("run_id")): row for row in specimen_results if row.get("run_id")}
        flags = self._evaluate_rules(
            recipe=recipe,
            specimen_results=specimen_results,
            operation_log=operation_log,
            inspections=inspections,
            validation_report=validation_report,
        )
        flags.extend(
            self._evaluate_statistical_screening(
                recipe=recipe,
                specimen_results=specimen_results,
                operation_log=operation_log,
            )
        )
        preliminary_flags_by_run = _flags_by_run(flags)
        preliminary_states = {
            run_id: state_from_flags(preliminary_flags_by_run.get(run_id, []))
            for run_id in run_ids
        }
        preliminary_sets = _build_selection_sets(
            recipe=recipe,
            run_ids=run_ids,
            flags_by_run=preliminary_flags_by_run,
            run_states=preliminary_states,
        )
        curve_family_assessment = CurveFamilyEngine().evaluate(
            recipe_payload=dict(curve_family_recipe_payload or {}),
            curve_family_rows=curve_family,
            selection_run_ids_by_context={
                selection.selection_id: set(selection.run_ids)
                for selection in preliminary_sets
            },
        )
        curve_shape_diagnostic = CurveFamilyDiagnostic().evaluate(
            curve_rows=curve_family,
            specimen_results=specimen_results,
            policy_payload=_curve_shape_diagnostic_policy_payload(curve_family_recipe_payload),
        )
        flags.extend(_acceptance_flags_from_curve_family(curve_family_assessment.flags))
        flags.extend(_acceptance_flags_from_curve_shape_diagnostic(curve_shape_diagnostic.flags))
        flags_by_run = _flags_by_run(flags)
        run_states = {run_id: state_from_flags(flags_by_run.get(run_id, [])) for run_id in run_ids}
        selection_sets = _build_selection_sets(
            recipe=recipe,
            run_ids=run_ids,
            flags_by_run=flags_by_run,
            run_states=run_states,
        )
        default_run_ids = _selection_run_ids(selection_sets, recipe.default_selection_set)
        discharge_report = build_discharge_report(
            method_id=method_id,
            default_selection_set=recipe.default_selection_set,
            run_states=run_states,
            flags_by_run=flags_by_run,
            default_run_ids=default_run_ids,
            specimen_by_run=specimen_by_run,
        )
        dataset_summary_by_selection = _dataset_summary_by_selection(
            selection_sets=selection_sets,
            specimen_by_run=specimen_by_run,
            dataset=dataset,
        )
        return AcceptanceReport(
            method_id=method_id,
            recipe_id=recipe.recipe_id,
            default_selection_set=recipe.default_selection_set,
            run_states=run_states,
            flags=tuple(flags),
            selection_sets=tuple(selection_sets),
            selection_membership=tuple(
                membership_rows(
                    run_ids=run_ids,
                    run_states=run_states,
                    flags_by_run=flags_by_run,
                    selection_sets=selection_sets,
                )
            ),
            discharge_report=discharge_report,
            dataset_summary_by_selection=tuple(dataset_summary_by_selection),
            curve_family_assessment=curve_family_assessment.report,
            curve_family_scores=tuple(curve_family_assessment.scores),
            curve_family_flags=tuple(curve_family_assessment.flags),
            curve_family_reference_rows=tuple(curve_family_assessment.reference_rows),
            curve_family_aligned_rows=tuple(curve_family_assessment.aligned_rows),
            curve_family_residual_rows=tuple(curve_family_assessment.residual_rows),
            curve_family_policy_resolved=curve_family_assessment.policy_resolved,
            curve_shape_diagnostic_report=curve_shape_diagnostic.report,
            curve_shape_diagnostic_scores=tuple(curve_shape_diagnostic.scores),
            curve_shape_diagnostic_reference_rows=tuple(curve_shape_diagnostic.reference_rows),
            curve_shape_diagnostic_residual_rows=tuple(curve_shape_diagnostic.residual_rows),
            curve_shape_diagnostic_policy_resolved=curve_shape_diagnostic.policy_resolved,
            curve_shape_diagnostic_flags=tuple(curve_shape_diagnostic.flags),
        )

    def _evaluate_rules(
        self,
        *,
        recipe: AcceptanceRecipe,
        specimen_results: list[dict[str, Any]],
        operation_log: list[dict[str, Any]],
        inspections: list[dict[str, Any]],
        validation_report: Mapping[str, Any],
    ) -> list[AcceptanceFlag]:
        flags: list[AcceptanceFlag] = []
        for rule in recipe.flags:
            source = str(rule.get("source") or "").strip()
            if source == "specimen_results":
                flags.extend(
                    _evaluate_specimen_rule(
                        rule=rule,
                        specimen_results=specimen_results,
                        operation_log=operation_log,
                    )
                )
            elif source == "validation_report":
                flags.extend(
                    _evaluate_validation_rule(
                        rule=rule,
                        validation_report=validation_report,
                        operation_log=operation_log,
                        inspections=inspections,
                    )
                )
        return flags

    def _evaluate_statistical_screening(
        self,
        *,
        recipe: AcceptanceRecipe,
        specimen_results: list[dict[str, Any]],
        operation_log: list[dict[str, Any]],
    ) -> list[AcceptanceFlag]:
        config = recipe.statistical_screening
        fields = config.get("scalar_fields", [])
        if not isinstance(fields, list):
            return []
        threshold = _as_float(config.get("robust_z_threshold")) or 3.5
        severity = str(config.get("severity") or "review")
        flags: list[AcceptanceFlag] = []
        for finding in robust_scalar_outliers(
            specimen_results,
            fields=[str(field) for field in fields],
            threshold=threshold,
        ):
            run_id = str(finding.get("run_id"))
            field = str(finding.get("field"))
            operation_ids = _operation_ids_for_field(operation_log, run_id, field)
            flags.append(
                AcceptanceFlag(
                    flag_id=f"statistical_outlier_{field}:{run_id}",
                    rule_id=f"statistical_outlier_{field}",
                    run_id=run_id,
                    source="statistical_screening",
                    severity=severity,
                    category="statistical_screening",
                    message=f"{field} is a robust scalar outlier.",
                    evidence_refs=(f"specimen_results:{run_id}:{field}",),
                    operation_ids=operation_ids,
                    selection_effect=_selection_effect(severity),
                    value=finding.get("value"),
                    threshold=finding.get("threshold"),
                )
            )
        return flags


def _evaluate_specimen_rule(
    *,
    rule: Mapping[str, Any],
    specimen_results: list[dict[str, Any]],
    operation_log: list[dict[str, Any]],
) -> list[AcceptanceFlag]:
    field = str(rule.get("field") or "").strip()
    if not field:
        return []
    flags: list[AcceptanceFlag] = []
    rule_id = str(rule.get("id") or field)
    severity = str(rule.get("severity") or "review")
    for row in specimen_results:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        value = row.get(field)
        if not _condition_matches(value, rule):
            continue
        operation_ids = _operation_ids_for_field(operation_log, run_id, field)
        flags.append(
            AcceptanceFlag(
                flag_id=f"{rule_id}:{run_id}",
                rule_id=rule_id,
                run_id=run_id,
                source="specimen_results",
                severity=severity,
                category=str(rule.get("category") or "acceptance"),
                message=str(rule.get("message") or f"{field} triggered acceptance rule."),
                evidence_refs=(f"specimen_results:{run_id}:{field}",),
                operation_ids=operation_ids,
                inspection_ids=_inspection_ids_for_operations(operation_log, run_id, operation_ids),
                selection_effect=_selection_effect(severity),
                value=value,
                threshold=rule.get("threshold"),
            )
        )
    return flags


def _evaluate_validation_rule(
    *,
    rule: Mapping[str, Any],
    validation_report: Mapping[str, Any],
    operation_log: list[dict[str, Any]],
    inspections: list[dict[str, Any]],
) -> list[AcceptanceFlag]:
    if str(rule.get("condition") or "") != "check_status_equals_fail":
        return []
    checks = validation_report.get("checks", [])
    if not isinstance(checks, list):
        return []
    failed_by_run: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        if isinstance(check, dict) and check.get("status") == "fail":
            failed_by_run.setdefault(str(check.get("run_id")), []).append(check)
    flags: list[AcceptanceFlag] = []
    rule_id = str(rule.get("id") or "validation_failed")
    severity = str(rule.get("severity") or "review")
    inspection_ids_by_operation = _inspection_ids_by_operation(operation_log)
    known_inspection_ids = {str(item.get("inspection_id")) for item in inspections if isinstance(item, dict)}
    for run_id, run_checks in failed_by_run.items():
        operation_ids = tuple(
            sorted(
                {
                    str(check.get("operation_id"))
                    for check in run_checks
                    if check.get("operation_id")
                }
            )
        )
        inspection_ids = tuple(
            sorted(
                {
                    inspection_id
                    for operation_id in operation_ids
                    for inspection_id in inspection_ids_by_operation.get(operation_id, ())
                    if not known_inspection_ids or inspection_id in known_inspection_ids
                }
            )
        )
        flags.append(
            AcceptanceFlag(
                flag_id=f"{rule_id}:{run_id}",
                rule_id=rule_id,
                run_id=run_id,
                source="validation_report",
                severity=severity,
                category=str(rule.get("category") or "validation"),
                message=str(rule.get("message") or "One or more validation checks failed."),
                evidence_refs=tuple(f"validation:{check.get('check_id')}" for check in run_checks),
                operation_ids=operation_ids,
                validation_check_ids=tuple(str(check.get("check_id")) for check in run_checks if check.get("check_id")),
                inspection_ids=inspection_ids,
                selection_effect=_selection_effect(severity),
                value=len(run_checks),
            )
        )
    return flags


def _acceptance_flags_from_curve_family(rows: list[dict[str, Any]]) -> list[AcceptanceFlag]:
    flags: list[AcceptanceFlag] = []
    for row in rows:
        run_id = str(row.get("run_id") or "")
        flag_id = str(row.get("flag_id") or "")
        if not run_id or not flag_id:
            continue
        flags.append(
            AcceptanceFlag(
                flag_id=flag_id,
                rule_id=str(row.get("flag_type") or "curve_family_assessment"),
                run_id=run_id,
                source="curve_family_assessment",
                severity=str(row.get("severity") or "review"),
                category="curve_family",
                message=str(row.get("reason") or "Curve-family assessment requires review."),
                evidence_refs=(
                    f"acceptance/curve_family/curve_family_scores.csv:{run_id}",
                    f"acceptance/curve_family/residuals_long.csv:{run_id}",
                ),
                operation_ids=(),
                selection_effect="requires_review_excluded_from_default",
                value=row.get("value"),
                threshold=row.get("threshold"),
            )
        )
    return flags


def _acceptance_flags_from_curve_shape_diagnostic(rows: tuple[dict[str, Any], ...]) -> list[AcceptanceFlag]:
    flags: list[AcceptanceFlag] = []
    for row in rows:
        run_id = str(row.get("run_id") or "")
        flag_id = str(row.get("flag_id") or "")
        if not run_id or not flag_id:
            continue
        evidence_refs = row.get("evidence_refs")
        refs = tuple(str(ref) for ref in evidence_refs if ref) if isinstance(evidence_refs, list) else (
            f"acceptance/curve_family/curve_diagnostic_scores.csv:{run_id}",
            f"acceptance/curve_family/curve_diagnostic_residuals.csv:{run_id}",
        )
        flags.append(
            AcceptanceFlag(
                flag_id=flag_id,
                rule_id=str(row.get("flag_type") or "curve_family_diagnostic"),
                run_id=run_id,
                source="curve_family_diagnostic",
                severity=str(row.get("severity") or "review"),
                category="curve_shape_diagnostic",
                message=str(row.get("reason") or "Curve-shape diagnostic requires review."),
                evidence_refs=refs,
                operation_ids=(),
                selection_effect=_selection_effect(str(row.get("severity") or "review")),
                value=row.get("value"),
                threshold=row.get("threshold"),
            )
        )
    return flags


def _curve_shape_diagnostic_policy_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(payload or {})
    diagnostic = data.get("curve_family_diagnostic")
    if isinstance(diagnostic, dict):
        return dict(diagnostic)
    return {
        "curve_source": {"x": "experiment_progress", "y": "stress_MPa", "load": "load_N"},
        "preprocessing": {
            "start_policy": "none",
            "min_load_fraction_of_max": None,
            "scope": "resolved_experiment_interval",
        },
        "cohort_policy": {
            "group_by": [],
            "default_grouping": "whole_comparable_dataset",
            "minimum_evaluable_curves": 3,
        },
        "alignment_policy": {
            "domain": "resolved_experiment_interval",
            "resample_points": 250,
            "interpolation_mode": "linear",
        },
        "reference_policy": {"curve": "mean", "variability": "std"},
    }


def _condition_matches(value: Any, rule: Mapping[str, Any]) -> bool:
    condition = str(rule.get("condition") or "").strip().lower()
    threshold = rule.get("threshold")
    if condition == "equals_invalid":
        return _is_invalid_value(value)
    if condition == "equals_zero_or_invalid":
        return _is_invalid_value(value) or _as_float(value) == 0
    if condition == "greater_than":
        numeric = _as_float(value)
        limit = _as_float(threshold)
        return numeric is not None and limit is not None and numeric > limit
    if condition == "less_than":
        numeric = _as_float(value)
        limit = _as_float(threshold)
        return numeric is not None and limit is not None and numeric < limit
    if condition == "equals":
        return str(value).strip().lower() == str(rule.get("value") or threshold).strip().lower()
    if condition == "truthy":
        return str(value).strip().lower() in {"1", "true", "yes", "x", "review"}
    return False


def _is_invalid_value(value: Any) -> bool:
    text = str(value).strip().lower()
    if text in {"", "none", "null"}:
        return False
    return text in {"invalid", "false", "0", "no", "rejected", "reject", "failed", "fail"}


def _build_selection_sets(
    *,
    recipe: AcceptanceRecipe,
    run_ids: list[str],
    flags_by_run: dict[str, list[AcceptanceFlag]],
    run_states: dict[str, str],
) -> list[SelectionSet]:
    sets: list[SelectionSet] = []
    all_runs = set(run_ids)
    for config in recipe.selection_sets:
        selection_id = str(config.get("id") or "").strip()
        if not selection_id:
            continue
        selected = _select_runs(config, run_ids, flags_by_run, run_states)
        sets.append(
            SelectionSet(
                selection_id=selection_id,
                label=_selection_label(selection_id),
                description=_selection_description(selection_id),
                run_ids=tuple(run_id for run_id in run_ids if run_id in selected),
                excluded_run_ids=tuple(run_id for run_id in run_ids if run_id not in selected),
                policy_id=_selection_policy_id(config),
            )
        )
    seen = {selection.selection_id for selection in sets}
    if recipe.default_selection_set not in seen:
        sets.append(
            SelectionSet(
                selection_id=recipe.default_selection_set,
                label=_selection_label(recipe.default_selection_set),
                description="Default selection set added because the recipe did not define it.",
                run_ids=tuple(run_ids),
                excluded_run_ids=(),
                policy_id="fallback_all",
            )
        )
    if "all_runs" not in seen:
        sets.insert(
            0,
            SelectionSet(
                selection_id="all_runs",
                label=_selection_label("all_runs"),
                description=_selection_description("all_runs"),
                run_ids=tuple(run_ids),
                excluded_run_ids=(),
                policy_id="include_all",
            ),
        )
    return sets


def _select_runs(
    config: Mapping[str, Any],
    run_ids: list[str],
    flags_by_run: dict[str, list[AcceptanceFlag]],
    run_states: dict[str, str],
) -> set[str]:
    include = str(config.get("include") or "").strip().lower()
    if include == "all":
        return set(run_ids)
    if include == "none":
        return set()
    if isinstance(config.get("include_if_not_flagged_by"), list):
        blocked = {str(rule_id) for rule_id in config.get("include_if_not_flagged_by", [])}
        return {
            run_id
            for run_id in run_ids
            if not {flag.rule_id or flag.flag_id.split(":", 1)[0] for flag in flags_by_run.get(run_id, [])} & blocked
        }
    if config.get("include_if_max_severity_below") is not None:
        limit = severity_rank(str(config.get("include_if_max_severity_below")))
        return {run_id for run_id in run_ids if _max_severity_rank(flags_by_run.get(run_id, [])) < limit}
    if config.get("include_if_max_severity_equals") is not None:
        target = severity_rank(str(config.get("include_if_max_severity_equals")))
        return {run_id for run_id in run_ids if _max_severity_rank(flags_by_run.get(run_id, [])) == target}
    if config.get("include_if_state_equals") is not None:
        state = str(config.get("include_if_state_equals"))
        return {run_id for run_id in run_ids if run_states.get(run_id) == state}
    return set()


def _dataset_summary_by_selection(
    *,
    selection_sets: list[SelectionSet],
    specimen_by_run: Mapping[str, Mapping[str, Any]],
    dataset: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selection in selection_sets:
        selected_rows = [specimen_by_run[run_id] for run_id in selection.run_ids if run_id in specimen_by_run]
        rows.append(
            {
                "selection_set": selection.selection_id,
                "metric": "run_count",
                "value": len(selected_rows),
                "unit": "",
                "n": len(selected_rows),
                "min": len(selected_rows),
                "max": len(selected_rows),
                "std": 0.0,
                "sample_type": dataset.get("sample_type"),
            }
        )
        for metric, unit in METRIC_UNITS.items():
            numeric_values = [_as_float(row.get(metric)) for row in selected_rows]
            values = [value for value in numeric_values if value is not None]
            rows.append(
                {
                    "selection_set": selection.selection_id,
                    "metric": metric,
                    "value": _mean(values),
                    "unit": unit,
                    "n": len(values),
                    "min": min(values) if values else None,
                    "max": max(values) if values else None,
                    "std": pstdev(values) if len(values) > 1 else 0.0 if values else None,
                    "sample_type": dataset.get("sample_type"),
                }
            )
    return rows


def _flags_by_run(flags: list[AcceptanceFlag]) -> dict[str, list[AcceptanceFlag]]:
    grouped: dict[str, list[AcceptanceFlag]] = {}
    for flag in flags:
        grouped.setdefault(flag.run_id, []).append(flag)
    return grouped


def _selection_run_ids(selection_sets: list[SelectionSet], selection_id: str) -> set[str]:
    for selection in selection_sets:
        if selection.selection_id == selection_id:
            return set(selection.run_ids)
    return set()


def _max_severity_rank(flags: list[AcceptanceFlag]) -> int:
    return max((severity_rank(flag.severity) for flag in flags), default=0)


def _operation_ids_for_field(operation_log: list[dict[str, Any]], run_id: str, field: str) -> tuple[str, ...]:
    step_id = FIELD_RECIPE_STEPS.get(field)
    matches: list[str] = []
    for record in operation_log:
        if str(record.get("run_id")) != run_id:
            continue
        outputs = record.get("outputs")
        outputs_match = isinstance(outputs, Mapping) and field in outputs
        step_match = bool(step_id and record.get("recipe_step_id") == step_id)
        if outputs_match or step_match:
            operation_id = record.get("operation_id") or record.get("recipe_step_id")
            if operation_id:
                matches.append(str(operation_id))
    return tuple(dict.fromkeys(matches))


def _inspection_ids_for_operations(
    operation_log: list[dict[str, Any]],
    run_id: str,
    operation_ids: tuple[str, ...],
) -> tuple[str, ...]:
    selected = set(operation_ids)
    inspection_ids: list[str] = []
    for record in operation_log:
        if str(record.get("run_id")) != run_id:
            continue
        if str(record.get("operation_id")) not in selected and str(record.get("recipe_step_id")) not in selected:
            continue
        refs = record.get("inspection_refs", [])
        if isinstance(refs, list):
            inspection_ids.extend(str(ref) for ref in refs)
    return tuple(dict.fromkeys(inspection_ids))


def _inspection_ids_by_operation(operation_log: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, tuple[str, ...]] = {}
    for record in operation_log:
        operation_id = str(record.get("operation_id") or "")
        refs = record.get("inspection_refs", [])
        if operation_id and isinstance(refs, list):
            grouped[operation_id] = tuple(str(ref) for ref in refs)
    return grouped


def _selection_effect(severity: str) -> str:
    rank = severity_rank(severity)
    if rank >= 3:
        return "excluded_from_default"
    if rank == 2:
        return "requires_review_excluded_from_default"
    if rank == 1:
        return "included_with_warning"
    return "informational"


def _selection_label(selection_id: str) -> str:
    return selection_id.replace("_", " ").title()


def _selection_description(selection_id: str) -> str:
    descriptions = {
        "all_runs": "Every computed run, including review and excluded runs.",
        "user_valid_runs": "Runs not excluded by user/operator validity flags.",
        "auto_recommended_runs": "Runs with no review or exclude severity flags.",
        "review_required_runs": "Runs requiring human review before downstream inclusion.",
        "excluded_runs": "Runs excluded by acceptance policy from the default dataset selection.",
        "human_curated_runs": "Reserved placeholder for a future human-curated selection.",
    }
    return descriptions.get(selection_id, "Selection set generated by the acceptance recipe.")


def _selection_policy_id(config: Mapping[str, Any]) -> str:
    for key in (
        "include",
        "include_if_not_flagged_by",
        "include_if_max_severity_below",
        "include_if_max_severity_equals",
        "include_if_state_equals",
    ):
        if key in config:
            return key
    return "unspecified"


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
