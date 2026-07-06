from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from acceptance.acceptance_engine import AcceptanceEngine
from acceptance.selection_editor import SelectionEditor
from archives.mtdp.models import MTDPPackageInput
from methods.core.method_context import MethodRunContext
from methods.core.method_package import MethodPackage
from methods.core.method_result import MethodRunResult
from operations.core.operation_registry import OperationRegistry
from readiness import MethodReadinessError, ReadinessChecker
from validation.validation_engine import MethodValidationEngine


class MethodExecutor:
    """Generic resolve-then-reduce executor for method packages."""

    def __init__(self, registry: OperationRegistry | None = None) -> None:
        self.registry = registry

    def execute(
        self,
        source: MTDPPackageInput,
        method_package: MethodPackage,
        mapping: dict[str, Any],
        *,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> MethodRunResult:
        readiness_report = ReadinessChecker().check(
            source=source,
            method_package=method_package,
            mapping=mapping,
        )
        if readiness_report.blocks_execution:
            raise MethodReadinessError(readiness_report)

        context = MethodRunContext(
            source=source,
            method_package=method_package,
            mapping=mapping,
        )
        if self.registry is not None:
            context.registry = self.registry

        _emit_progress(
            progress_callback,
            phase="method_resolve",
            message="Resolving method inputs",
            source=source,
            status="running",
            note="binding source data to method inputs",
        )
        self._run_phase(context, "method_resolve", method_package.resolve_recipe.get("resolve", ()), cancel_requested=cancel_requested)
        resolve_summary = _build_resolve_summary(context)

        _emit_progress(
            progress_callback,
            phase="method_reduce",
            message="Reducing method outputs",
            source=source,
            status="running",
            note="computing per-run method outputs",
        )
        self._run_phase(context, "method_reduce", method_package.reduce_recipe.get("reduce", ()), cancel_requested=cancel_requested)
        reduce_summary = _build_reduce_summary(context)
        experiment_boundaries = _build_experiment_boundaries(context)
        boundary_events = _build_boundary_events(experiment_boundaries)
        specimen_results = _build_specimen_results(context)
        curve_family = _build_curve_family(context, bounded=True)
        full_curve_family = _build_curve_family(context, bounded=False)
        dataset_summary = _build_dataset_summary(specimen_results, source.dataset)
        _emit_progress(
            progress_callback,
            phase="validation",
            message="Running validation checks",
            source=source,
            status="running",
            note="checking outputs against reference policy",
        )
        validation_report = MethodValidationEngine().validate(
            source=source,
            method_package=method_package,
            mapping=mapping,
            specimen_results=specimen_results,
            curve_family=curve_family,
            operation_log=context.operation_log,
        )
        _emit_progress(
            progress_callback,
            phase="acceptance",
            message="Evaluating acceptance and selection sets",
            source=source,
            status="running",
            note="screening runs and building machine selection",
        )
        acceptance_report = AcceptanceEngine().evaluate(
            method_id=method_package.method_id,
            recipe_payload=method_package.acceptance_recipe,
            specimen_results=specimen_results,
            curve_family=curve_family,
            operation_log=context.operation_log,
            inspections=context.inspections,
            validation_report=validation_report.to_dict(),
            dataset=source.dataset,
            curve_family_recipe_payload=method_package.curve_family_acceptance_recipe,
        )
        final_selection = SelectionEditor().apply(
            specimen_results=specimen_results,
            acceptance_report=acceptance_report.to_dict(),
            machine_selection_sets=acceptance_report.selection_sets_payload(),
            machine_selection_membership=acceptance_report.selection_membership_rows(),
            decisions=(),
        )

        return MethodRunResult(
            source=source,
            method_package=method_package,
            mapping=mapping,
            readiness_report=readiness_report.to_dict(),
            readiness_summary=readiness_report.summary_rows(),
            resolved_inputs=readiness_report.resolved_rows(),
            missing_inputs=readiness_report.missing_rows(),
            specimen_results=specimen_results,
            dataset_summary=dataset_summary,
            dataset_summary_by_selection=list(acceptance_report.dataset_summary_by_selection),
            curve_family=curve_family,
            operation_log=context.operation_log,
            evidence=_build_evidence(context, specimen_results, dataset_summary, acceptance_report.to_dict()),
            inspections=context.inspections,
            resolve_summary=resolve_summary,
            reduce_summary=reduce_summary,
            warnings=context.warnings,
            validation_report=validation_report.to_dict(),
            validation_summary=validation_report.summary_rows(),
            validation_deviations=validation_report.deviation_rows(),
            reference_values_used=validation_report.reference_rows(),
            acceptance_report=acceptance_report.to_dict(),
            acceptance_summary=acceptance_report.summary_rows(),
            run_flags=acceptance_report.run_flag_rows(),
            selection_sets=acceptance_report.selection_sets_payload(),
            selection_membership=acceptance_report.selection_membership_rows(),
            discharged_runs=acceptance_report.discharged_rows(),
            discharge_report=acceptance_report.discharge_report,
            curve_family_assessment=acceptance_report.curve_family_assessment,
            curve_family_scores=list(acceptance_report.curve_family_scores),
            curve_family_flags=list(acceptance_report.curve_family_flags),
            curve_family_reference_rows=list(acceptance_report.curve_family_reference_rows),
            curve_family_aligned_rows=list(acceptance_report.curve_family_aligned_rows),
            curve_family_residual_rows=list(acceptance_report.curve_family_residual_rows),
            curve_family_policy_resolved=acceptance_report.curve_family_policy_resolved,
            curve_shape_diagnostic_report=acceptance_report.curve_shape_diagnostic_report,
            curve_shape_diagnostic_scores=list(acceptance_report.curve_shape_diagnostic_scores),
            curve_shape_diagnostic_reference_rows=list(acceptance_report.curve_shape_diagnostic_reference_rows),
            curve_shape_diagnostic_residual_rows=list(acceptance_report.curve_shape_diagnostic_residual_rows),
            curve_shape_diagnostic_policy_resolved=acceptance_report.curve_shape_diagnostic_policy_resolved,
            curve_shape_diagnostic_flags=list(acceptance_report.curve_shape_diagnostic_flags),
            experiment_boundaries=experiment_boundaries,
            boundary_events=boundary_events,
            bounded_curve_family=curve_family,
            full_curve_family=full_curve_family,
            human_decisions=final_selection.human_decisions,
            human_decision_rows=final_selection.human_decision_rows,
            override_ledger=final_selection.override_ledger,
            override_ledger_rows=final_selection.override_ledger_rows,
            selection_sets_final=final_selection.selection_sets_final,
            selection_membership_final=final_selection.selection_membership_final,
            final_report_runs=final_selection.final_report_runs,
        )

    def _run_phase(
        self,
        context: MethodRunContext,
        phase: str,
        steps: object,
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> None:
        if not isinstance(steps, list):
            raise ValueError(f"{phase}_recipe.yaml must contain a list under '{phase}'.")
        operation_context = context.operation_context(phase, cancel_requested=cancel_requested)
        operation_context.check_cancelled()
        for step in steps:
            if not isinstance(step, Mapping):
                raise ValueError(f"{phase} recipe step must be a mapping.")
            operation_context.check_cancelled()
            context.record(context.registry.run(operation_context, step))
            operation_context.check_cancelled()


def _emit_progress(
    callback: Callable[[dict[str, Any]], None] | None,
    *,
    phase: str,
    message: str,
    source: MTDPPackageInput,
    status: str,
    note: str,
) -> None:
    if callback is None:
        return
    runs = {run.run_id: status for run in source.runs}
    notes = {run.run_id: note for run in source.runs}
    callback({"phase": phase, "message": message, "status": status, "runs": runs, "notes": notes})


def _build_resolve_summary(context: MethodRunContext) -> dict[str, Any]:
    return {
        "method_id": context.method_package.method_id,
        "mapping_id": context.mapping.get("mapping_id"),
        "runs": {
            run_id: {
                "scalars": {
                    key: {"value": value, "unit": run.units.get(key)}
                    for key, value in sorted(run.scalars.items())
                    if not isinstance(value, dict)
                },
                "series": {
                    key: {"point_count": len(value), "unit": run.units.get(key)}
                    for key, value in sorted(run.series.items())
                },
                "source": run.metadata,
                "experiment_boundaries": run.metadata.get("experiment_boundaries"),
            }
            for run_id, run in context.runs.items()
        },
    }


def _build_reduce_summary(context: MethodRunContext) -> dict[str, Any]:
    return {
        "method_id": context.method_package.method_id,
        "runs": {
            run_id: {
                "outputs": {
                    key: {"value": value, "unit": run.units.get(key)}
                    for key, value in sorted(run.scalars.items())
                    if key
                    in {
                        "max_load_N",
                        "max_load_index",
                        "compressive_strength_MPa",
                        "max_stress_index",
                        "compressive_failure_strain",
                        "compressive_modulus_MPa",
                    }
                },
                "diagnostics": run.diagnostics,
                "analysis_interval": run.metadata.get("analysis_interval"),
                "bounded_reduction": bool(run.metadata.get("experiment_boundaries")),
            }
            for run_id, run in context.runs.items()
        },
    }


def _build_experiment_boundaries(context: MethodRunContext) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id, run in context.runs.items():
        record = run.metadata.get("experiment_boundaries")
        if isinstance(record, dict):
            rows.append(record)
        elif "experiment_boundaries" in run.scalars and isinstance(run.scalars["experiment_boundaries"], dict):
            rows.append(run.scalars["experiment_boundaries"])
    return rows


def _build_boundary_events(boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in boundaries:
        run_id = str(record.get("run_id") or "")
        for event in record.get("events", []) or []:
            if not isinstance(event, dict):
                continue
            event_id = str(event.get("event_id") or "")
            if event_id == "analysis_start":
                policy = record.get("start_policy")
            elif event_id in {"analysis_end", "max_abs_load"}:
                policy = record.get("end_policy")
            else:
                policy = ""
            rows.append(
                {
                    "run_id": run_id,
                    "event_id": event_id,
                    "index": event.get("index"),
                    "policy": policy,
                    "confidence": record.get("confidence"),
                    "reason": "; ".join(str(note) for note in event.get("notes", []) or []),
                    "domain": event.get("domain"),
                    "domain_value": event.get("domain_value"),
                    "value": event.get("value"),
                    "unit": event.get("unit"),
                    "diagnostic_only": event.get("diagnostic_only", False),
                }
            )
    return rows


def _build_specimen_results(context: MethodRunContext) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id, run in context.runs.items():
        bending = run.diagnostics.get("bending_diagnostic")
        if not isinstance(bending, dict):
            bending = {}
        boundary = run.metadata.get("experiment_boundaries")
        boundary = boundary if isinstance(boundary, dict) else {}
        signal_gate = run.metadata.get("experiment_signal_gate")
        if not isinstance(signal_gate, dict):
            scalar_gate = run.scalars.get("experiment_signal_gate")
            signal_gate = scalar_gate if isinstance(scalar_gate, dict) else {}
        signal_routing = signal_gate.get("report_routing") if isinstance(signal_gate.get("report_routing"), dict) else {}
        signal_window_scale = (
            boundary.get("signal_window_load_scale")
            if isinstance(boundary.get("signal_window_load_scale"), dict)
            else {}
        )
        interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
        longest_segment = bending.get("longest_segment") if isinstance(bending.get("longest_segment"), dict) else {}
        rows.append(
            {
                "run_id": run_id,
                "specimen_name": run.scalars.get("specimen_name"),
                "sample_id": run.scalars.get("sample_id"),
                "width_mm": run.scalars.get("width_mm"),
                "thickness_mm": run.scalars.get("thickness_mm"),
                "area_mm2": run.scalars.get("area_mm2"),
                "max_load_N": run.scalars.get("max_load_N"),
                "max_load_index": run.scalars.get("max_load_index"),
                "max_load_point_index": _bounded_point_index(run, run.scalars.get("max_load_index")),
                "compressive_strength_MPa": run.scalars.get("compressive_strength_MPa"),
                "max_stress_index": run.scalars.get("max_stress_index"),
                "max_stress_point_index": _bounded_point_index(run, run.scalars.get("max_stress_index")),
                "compressive_failure_strain": run.scalars.get("compressive_failure_strain"),
                "compressive_modulus_MPa": run.scalars.get("compressive_modulus_MPa"),
                "bending_max_percent": bending.get("max_bending_percent"),
                "bending_mean_percent": bending.get("mean_bending_percent"),
                "bending_median_percent": bending.get("median_bending_percent"),
                "bending_p95_percent": bending.get("p95_bending_percent"),
                "bending_p99_percent": bending.get("p99_bending_percent"),
                "bending_threshold_percent": bending.get("threshold_percent"),
                "bending_points_above_threshold": bending.get("points_above_threshold"),
                "bending_fraction_above_threshold": bending.get("fraction_above_threshold"),
                "bending_longest_segment_points": (
                    longest_segment.get("point_count")
                    if longest_segment
                    else None
                ),
                "bending_longest_segment_fraction": longest_segment.get("fraction_of_window"),
                "bending_longest_segment_classification": longest_segment.get("segment_classification"),
                "bending_pattern": bending.get("pattern_classification"),
                "bending_pattern_confidence": bending.get("pattern_confidence"),
                "bending_pattern_reason": bending.get("pattern_reason"),
                "bending_point_count": bending.get("point_count"),
                "boundary_start_index": interval.get("start_index", boundary.get("start_index")),
                "boundary_end_index": interval.get("end_index", boundary.get("end_index")),
                "boundary_include_endpoint": interval.get("include_endpoint", boundary.get("include_endpoint")),
                "accepted_failure_peak_index": boundary.get("accepted_failure_peak_index"),
                "max_within_interval_index": boundary.get("max_within_interval_index"),
                "reported_strength_index": boundary.get("reported_strength_index"),
                "boundary_start_policy": boundary.get("start_policy"),
                "boundary_end_policy": boundary.get("end_policy"),
                "boundary_confidence": boundary.get("confidence"),
                "boundary_reason": boundary.get("reason"),
                "bounded_reduction": bool(boundary),
                "experiment_signal_gate_status": signal_gate.get("status"),
                "experiment_signal_gate_confidence": signal_gate.get("confidence"),
                "experiment_signal_gate_reason": signal_gate.get("reason"),
                "experiment_signal_gate_classifications": ";".join(
                    str(item) for item in signal_gate.get("classifications", []) or []
                ),
                "experiment_signal_gate_excluded_region_count": len(signal_gate.get("excluded_regions", []) or []),
                "experiment_signal_gate_report_routing_state": signal_routing.get("state"),
                "experiment_signal_gate_report_routing_severity": signal_routing.get("severity"),
                "experiment_signal_gate_report_routing_reason": signal_routing.get("reason"),
                "signal_window_gate_to_full_run_peak_fraction": signal_window_scale.get("gate_to_full_run_peak_fraction"),
                "signal_window_raw_full_run_peak_load": signal_window_scale.get("raw_full_run_peak_load"),
                "signal_window_gate_window_peak_load": signal_window_scale.get("gate_window_peak_load"),
                "signal_window_load_scale_reason": signal_window_scale.get("reason"),
                "signal_window_load_scale_routing_severity": signal_window_scale.get("routing_severity"),
                "validity": run.scalars.get("validity"),
                "failure_mode": run.scalars.get("failure_mode"),
                "primary_failure_mode": run.scalars.get("primary_failure_mode"),
                "failure_location": run.scalars.get("failure_location"),
                "failure_observed": run.scalars.get("failure_observed"),
                "invalid_specimen_reason": run.scalars.get("invalid_specimen_reason"),
                "invalid_specimen_reason_other": run.scalars.get("invalid_specimen_reason_other"),
                "failure_analysis_notes": run.scalars.get("failure_analysis_notes"),
                "visible_buckling_or_bending_observation": run.scalars.get("visible_buckling_or_bending_observation"),
                "visible_buckling_or_bending_observation_other": run.scalars.get("visible_buckling_or_bending_observation_other"),
                "failure_image_reference": run.scalars.get("failure_image_reference"),
                "rejection_reason": run.scalars.get("rejection_reason"),
                "run_notes": run.scalars.get("run_notes"),
                "requires_review": run.scalars.get("requires_review"),
                "warnings": sum(1 for warning in context.warnings if warning.get("run_id") == run_id),
            }
        )
    return rows


def _build_curve_family(context: MethodRunContext, *, bounded: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id, run in context.runs.items():
        suffix = "_bounded" if bounded and run.metadata.get("experiment_boundaries") else ""
        mean_strain = _series_for_scope(run, "mean_strain", suffix)
        stress = _series_for_scope(run, "stress_MPa", suffix, full_fallback="stress_MPa_full")
        load = _series_for_scope(run, "load_N", suffix)
        raw_load = _series_for_scope(run, "load_N_raw", suffix)
        front_raw = _series_for_scope(run, "front_strain_raw", suffix)
        if not front_raw:
            front_raw = _series_for_scope(run, "front_strain", suffix)
        rear_raw = _series_for_scope(run, "rear_strain_raw", suffix)
        if not rear_raw:
            rear_raw = _series_for_scope(run, "rear_strain", suffix)
        front_abs = _series_for_scope(run, "front_strain_abs", suffix)
        rear_abs = _series_for_scope(run, "rear_strain_abs", suffix)
        front_oriented = _series_for_scope(run, "front_strain_oriented", suffix)
        rear_oriented = _series_for_scope(run, "rear_strain_oriented", suffix)
        time = _series_for_scope(run, "time_s", suffix)
        extension = _series_for_scope(run, "extension_mm", suffix)
        point_indices = run.series.get("point_index_bounded", []) if suffix else []
        max_len = max(
            len(mean_strain),
            len(stress),
            len(load),
            len(raw_load),
            len(front_raw),
            len(rear_raw),
            len(front_abs),
            len(rear_abs),
            len(front_oriented),
            len(rear_oriented),
            len(time),
            len(extension),
            len(point_indices),
            0,
        )
        boundary = run.metadata.get("experiment_boundaries")
        boundary = boundary if isinstance(boundary, dict) else {}
        interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
        start_index = _as_int(interval.get("start_index", boundary.get("start_index")))
        end_index = _as_int(interval.get("end_index", boundary.get("end_index")))
        for index in range(max_len):
            raw_index = _series_value(point_indices, index) if point_indices else index
            progress = _experiment_progress(raw_index, start_index, end_index)
            rows.append(
                {
                    "run_id": run_id,
                    "point_index": raw_index,
                    "curve_scope": "bounded" if bounded else "full",
                    "experiment_progress": progress,
                    "boundary_start_index": start_index,
                    "boundary_end_index": end_index,
                    "boundary_start_policy": boundary.get("start_policy"),
                    "boundary_end_policy": boundary.get("end_policy"),
                    "boundary_include_endpoint": interval.get("include_endpoint", boundary.get("include_endpoint")),
                    "mean_strain": _series_value(mean_strain, index),
                    "strain_mm_per_mm": _series_value(mean_strain, index),
                    "stress_MPa": _series_value(stress, index),
                    "load_N": _series_value(load, index),
                    "load_N_raw": _series_value(raw_load, index),
                    "front_strain": _series_value(front_raw, index),
                    "rear_strain": _series_value(rear_raw, index),
                    "front_strain_raw": _series_value(front_raw, index),
                    "rear_strain_raw": _series_value(rear_raw, index),
                    "front_strain_abs": _series_value(front_abs, index),
                    "rear_strain_abs": _series_value(rear_abs, index),
                    "front_strain_oriented": _series_value(front_oriented, index),
                    "rear_strain_oriented": _series_value(rear_oriented, index),
                    "extension_mm": _series_value(extension, index),
                    "time_s": _series_value(time, index),
                }
            )
    return rows


def _series_for_scope(run: Any, key: str, suffix: str, *, full_fallback: str | None = None) -> list[Any]:
    if suffix and f"{key}{suffix}" in run.series:
        return run.series.get(f"{key}{suffix}", [])
    if suffix:
        return run.series.get(key, []) if key in _ACTIVE_AFTER_BOUNDARY_KEYS else []
    if not suffix and full_fallback and full_fallback in run.series:
        return run.series.get(full_fallback, [])
    return run.series.get(key, [])


_ACTIVE_AFTER_BOUNDARY_KEYS = {"stress_MPa"}


def _bounded_point_index(run: Any, bounded_index: Any) -> Any:
    index = _as_int(bounded_index)
    if index is None:
        return None
    point_indices = run.series.get("point_index_bounded") if isinstance(run.series, dict) else None
    if point_indices and 0 <= index < len(point_indices):
        return point_indices[index]
    return index


def _series_value(series: list[Any], index: int) -> Any:
    return series[index] if index < len(series) else None


def _experiment_progress(raw_index: Any, start_index: int | None, end_index: int | None) -> float | None:
    try:
        point_index = int(raw_index)
    except (TypeError, ValueError):
        return None
    if start_index is None or end_index is None or end_index == start_index:
        return None
    return (point_index - start_index) / (end_index - start_index)


def _as_int(value: Any) -> int | None:
    try:
        return None if value in (None, "") else int(value)
    except (TypeError, ValueError):
        return None


def _build_dataset_summary(
    specimen_results: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "selection_set": "all_runs",
            "metric": "run_count",
            "value": len(specimen_results),
            "unit": "",
            "n": len(specimen_results),
            "sample_type": dataset.get("sample_type"),
        }
    ]
    metric_units = {
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
    for metric, unit in metric_units.items():
        values = [_as_float(row.get(metric)) for row in specimen_results]
        numeric_values = [value for value in values if value is not None]
        rows.append(
            {
                "metric": metric,
                "selection_set": "all_runs",
                "value": _mean(numeric_values),
                "unit": unit,
                "n": len(numeric_values),
                "min": min(numeric_values) if numeric_values else None,
                "max": max(numeric_values) if numeric_values else None,
                "sample_type": dataset.get("sample_type"),
            }
        )
    return rows


def _build_evidence(
    context: MethodRunContext,
    specimen_results: list[dict[str, Any]],
    dataset_summary: list[dict[str, Any]],
    acceptance_report: dict[str, Any],
) -> dict[str, Any]:
    output_operations: dict[str, list[str]] = {}
    for record in context.operation_log:
        operation_id = str(record.get("operation_id"))
        outputs = record.get("outputs", {})
        if isinstance(outputs, dict):
            for key in outputs:
                output_operations.setdefault(str(key), []).append(operation_id)
    return {
        "method_id": context.method_package.method_id,
        "mapping_id": context.mapping.get("mapping_id"),
        "operation_count": len(context.operation_log),
        "inspection_count": len(context.inspections),
        "warning_count": len(context.warnings),
        "output_operations": output_operations,
        "experiment_boundaries": _build_experiment_boundaries(context),
        "boundary_events": _build_boundary_events(_build_experiment_boundaries(context)),
        "specimen_results": specimen_results,
        "dataset_summary": dataset_summary,
        "acceptance_summary": acceptance_report.get("summary", {}),
        "operation_records": context.operation_log,
    }


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
