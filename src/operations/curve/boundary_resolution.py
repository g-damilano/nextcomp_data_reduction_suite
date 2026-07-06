from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isclose, isfinite
from typing import Any

from methods.core.boundaries import (
    ExperimentBoundaryEvent,
    ExperimentBoundaryPoint,
    ExperimentBoundaryRecord,
)
from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


SUPPORTED_END_POLICIES = {"max_abs_load", "slope_break_pre_negative", "peak_decline_non_recovery"}
_RECOVERY_SLOPE_FRACTION = 0.75
_DEFAULT_MIN_CANDIDATE_PEAK_FRACTION_OF_GATE_MAX = 0.05
_DEFAULT_MIN_GATE_PEAK_FRACTION_OF_FULL_RUN_MAX = 0.10


class ResolveExperimentBoundariesOperation(Operation):
    operation_id = "resolve_experiment_boundaries"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        inputs = _inputs(step)
        parameters = step.get("parameters", {})
        parameters = parameters if isinstance(parameters, Mapping) else {}
        start_policy = str(parameters.get("start_policy") or step.get("start_policy") or "first_point")
        end_policy = str(parameters.get("end_policy") or step.get("end_policy") or "max_abs_load")
        include_endpoint = _bool(parameters.get("include_endpoint", step.get("include_endpoint", True)))
        output = str(step.get("output") or "experiment_boundaries")
        sustained_config = parameters.get("sustained_decline", {})
        sustained_config = sustained_config if isinstance(sustained_config, Mapping) else {}
        slope_config = parameters.get("slope_break", {})
        slope_config = slope_config if isinstance(slope_config, Mapping) else {}
        start_config = parameters.get("start", {})
        start_config = start_config if isinstance(start_config, Mapping) else {}
        results: list[OperationResult] = []

        for run_id, run in context.runs.items():
            warnings: list[str] = []
            load_key = str(inputs.get("load") or "load_N")
            time_key = str(inputs.get("time") or "time_s")
            strain_key = str(inputs.get("strain") or "mean_strain")
            gate_key = str(inputs.get("gate") or "")
            load = run.series.get(load_key)
            time = run.series.get(time_key)
            strain = run.series.get(strain_key)
            gate_record = _gate_record(run, gate_key)
            gate_window = _gate_window(gate_record, series_length=_series_length(load, strain, time))
            signal_window_scale = _signal_window_load_scale(
                load=load,
                gate_window=gate_window,
                gate_record=gate_record,
                config=sustained_config,
            )
            if end_policy not in SUPPORTED_END_POLICIES:
                warnings.append(f"Unsupported end_policy '{end_policy}'.")

            max_point = _max_abs_point(load)
            start_resolution = _resolve_start_boundary(
                load=load,
                time=time,
                strain=strain,
                start_policy=start_policy,
                config=start_config,
                fallback_config=slope_config,
            )
            start_index = start_resolution.start_index
            if gate_window and start_index is not None:
                start_index = max(start_index, int(gate_window["start_index"]))
            end_resolution = _resolve_end_boundary(
                load=load,
                strain=strain,
                start_index=start_index,
                run_id=run_id,
                end_policy=end_policy,
                slope_config=slope_config,
                sustained_config=sustained_config,
                gate_window=gate_window,
                gate_record=gate_record,
            )
            end_index = end_resolution.end_index
            if load is None:
                warnings.append(f"Load series '{load_key}' is missing.")
            elif max_point is None:
                warnings.append(f"Load series '{load_key}' has no numeric values.")
            warnings.extend(start_resolution.warnings)
            warnings.extend(end_resolution.warnings)
            if signal_window_scale.get("routing_severity") == "review":
                warnings.append(str(signal_window_scale["reason"]))
            if start_index is not None and end_index is not None and end_index < start_index:
                warnings.append("Resolved end_index precedes start_index.")

            domain, start_domain_value, end_domain_value = _domain_values(
                time_key=time_key,
                time=time,
                strain_key=strain_key,
                strain=strain,
                start_index=start_index,
                end_index=end_index,
            )
            method_max_point = _max_abs_point_in_interval(
                load,
                start_index=start_index,
                end_index=end_index,
                include_endpoint=include_endpoint,
            )
            accepted_failure_peak_index = (
                end_resolution.accepted_failure_peak_index
                if end_resolution.accepted_failure_peak_index is not None
                else end_index
            )
            max_within_interval_index = method_max_point[0] if method_max_point is not None else None
            reported_strength_index = (
                end_resolution.reported_strength_index
                if end_resolution.reported_strength_index is not None
                else accepted_failure_peak_index
            )
            source_refs = {
                "load": {"series": load_key, "unit": run.units.get(load_key), "point_count": len(load or [])},
                "time": {"series": time_key, "unit": run.units.get(time_key), "point_count": len(time or [])},
                "strain": {"series": strain_key, "unit": run.units.get(strain_key), "point_count": len(strain or [])},
            }
            events: list[ExperimentBoundaryEvent] = []
            events.append(
                ExperimentBoundaryEvent(
                    event_id="analysis_start",
                    index=start_index,
                    value=_value_at(load, start_index),
                    unit=run.units.get(load_key),
                    domain=domain,
                    domain_value=start_domain_value,
                    diagnostic_only=False,
                    notes=tuple(
                        item
                        for item in (
                            f"start_policy={start_policy}",
                            f"min_load_fraction_of_max={start_resolution.min_load_fraction_of_max}"
                            if start_resolution.min_load_fraction_of_max is not None
                            else "",
                            f"threshold_abs_load={start_resolution.threshold_load}"
                            if start_resolution.threshold_load is not None
                            else "",
                            f"excluded_leading_points={start_resolution.excluded_points}",
                            start_resolution.reason,
                        )
                        if item
                    ),
                )
            )
            if method_max_point is not None:
                events.append(
                    ExperimentBoundaryEvent(
                        event_id="max_abs_load",
                        index=method_max_point[0],
                        value=method_max_point[1],
                        unit=run.units.get(load_key),
                        domain=domain,
                        domain_value=_domain_value_for_index(domain, time_key, time, strain_key, strain, method_max_point[0]),
                        diagnostic_only=False,
                        notes=(
                            "Maximum absolute load point constrained to the resolved experiment interval.",
                            f"analysis_interval={start_index}:{end_index}",
                            f"include_endpoint={include_endpoint}",
                        ),
                    )
                )
            if max_point is not None and method_max_point is not None and max_point[0] != method_max_point[0]:
                events.append(
                    ExperimentBoundaryEvent(
                        event_id="raw_machine_max_abs_load",
                        index=max_point[0],
                        value=max_point[1],
                        unit=run.units.get(load_key),
                        domain=domain,
                        domain_value=_domain_value_for_index(domain, time_key, time, strain_key, strain, max_point[0]),
                        diagnostic_only=True,
                        notes=(
                            "Raw machine-file maximum absolute load lies outside the resolved method interval.",
                            "Preserved for audit only; not used for method reduction.",
                        ),
                    )
                )
            events.extend(
                _slope_break_events(
                    resolution=end_resolution,
                    load=load,
                    unit=run.units.get(load_key),
                    domain=domain,
                    time_key=time_key,
                    time=time,
                    strain_key=strain_key,
                    strain=strain,
                )
            )
            events.append(
                ExperimentBoundaryEvent(
                    event_id="analysis_end",
                    index=end_index,
                    value=_value_at(load, end_index),
                    unit=run.units.get(load_key),
                    domain=domain,
                    domain_value=end_domain_value,
                    diagnostic_only=False,
                    notes=(f"end_policy={end_policy}", f"include_endpoint={include_endpoint}"),
                )
            )
            if end_resolution.sustained_decline is None and end_policy != "peak_decline_non_recovery":
                sustained_event = _sustained_decline_event(
                    load=load,
                    end_index=end_index,
                    max_load=method_max_point[1] if method_max_point else None,
                    unit=run.units.get(load_key),
                    domain=domain,
                    domain_series=time if domain == time_key else strain if domain == strain_key else None,
                    config=sustained_config,
                )
                if sustained_event is not None:
                    events.append(sustained_event)

            confidence = "high" if not warnings and start_index is not None and end_index is not None else "low"
            reason = (
                f"{start_resolution.reason}; {end_resolution.reason}"
                if confidence == "high"
                else "Boundary resolution completed with warnings."
            )
            record = ExperimentBoundaryRecord(
                run_id=run_id,
                start_index=start_index,
                end_index=end_index,
                include_endpoint=include_endpoint,
                start_policy=start_policy,
                end_policy=end_policy,
                confidence=confidence,
                reason=reason,
                domain=domain,
                domain_value=end_domain_value,
                events=tuple(events),
                warnings=tuple(warnings),
                source_series_refs=source_refs,
                start=ExperimentBoundaryPoint(
                    index=start_index,
                    policy=start_policy,
                    confidence=confidence,
                    reason=start_resolution.reason,
                    domain=domain,
                    domain_value=start_domain_value,
                ),
                end=ExperimentBoundaryPoint(
                    index=end_index,
                    policy=end_policy,
                    confidence=confidence,
                    reason=end_resolution.reason,
                    domain=domain,
                    domain_value=end_domain_value,
                ),
            )
            record_payload = record.to_dict()
            record_payload["resolution_policy"] = {
                "schema_id": "method.experiment_boundary_policy.v0_1",
                "start_policy": start_policy,
                "end_policy": end_policy,
                "include_endpoint": include_endpoint,
                "slope_break": dict(slope_config),
                "start": dict(start_config),
                "sustained_decline": dict(sustained_config),
                "endpoint_detection": end_resolution.resolved_endpoint_policy,
                "signature": _policy_signature(
                    start_policy=start_policy,
                    end_policy=end_policy,
                    include_endpoint=include_endpoint,
                    start_config=start_config,
                    slope_config=slope_config,
                    sustained_config=sustained_config,
                ),
            }
            record_payload["accepted_failure_peak_index"] = accepted_failure_peak_index
            record_payload["max_within_interval_index"] = max_within_interval_index
            record_payload["reported_strength_index"] = reported_strength_index
            record_payload["selected_endpoint_candidate"] = end_resolution.selected_candidate
            record_payload["endpoint_candidate_diagnostics"] = list(end_resolution.candidate_diagnostics)
            if gate_record is not None:
                record_payload["experiment_signal_gate"] = gate_record
                record_payload["signal_window_report_routing"] = gate_record.get("report_routing")
                record_payload["signal_window_load_scale"] = signal_window_scale
                record_payload["resolution_policy"]["signal_gate"] = {
                    "input": gate_key,
                    "coherent_window": gate_window,
                    "confidence": gate_record.get("confidence"),
                    "classifications": gate_record.get("classifications", []),
                    "report_routing": gate_record.get("report_routing"),
                    "load_scale": signal_window_scale,
                }
            if start_index is not None and end_index is not None and end_index >= start_index:
                bounded_refs = _materialize_bounded_series(run, start_index, end_index, include_endpoint)
            else:
                bounded_refs = {}
            record_payload["bounded_series_refs"] = bounded_refs
            run.scalars[output] = record_payload
            run.scalars["analysis_interval_start_index"] = start_index
            run.scalars["analysis_interval_end_index"] = end_index
            run.scalars["analysis_interval_include_endpoint"] = include_endpoint
            run.scalars["accepted_failure_peak_index"] = accepted_failure_peak_index
            run.scalars["max_within_interval_index"] = max_within_interval_index
            run.scalars["reported_strength_index"] = reported_strength_index
            run.scalars["boundary_start_policy"] = start_policy
            run.scalars["boundary_end_policy"] = end_policy
            run.metadata["experiment_boundaries"] = record_payload
            run.metadata["analysis_interval"] = record_payload["analysis_interval"]
            run.metadata["bounded_series_refs"] = bounded_refs
            run.units["analysis_interval_start_index"] = "index"
            run.units["analysis_interval_end_index"] = "index"
            run.units["accepted_failure_peak_index"] = "index"
            run.units["max_within_interval_index"] = "index"
            run.units["reported_strength_index"] = "index"

            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type=self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"load": load_key, "time": time_key, "strain": strain_key, "gate": gate_key or None},
                    parameters={
                        "start_policy": start_policy,
                        "end_policy": end_policy,
                        "include_endpoint": include_endpoint,
                        "start": dict(start_config),
                        "sustained_decline": dict(sustained_config),
                        "slope_break": dict(slope_config),
                    },
                    outputs={output: record_payload},
                    units={output: None},
                    evidence={
                        "boundary_record": record_payload,
                        "max_load_event": _event_payload(events, "max_abs_load"),
                        "raw_machine_max_load_event": _event_payload(events, "raw_machine_max_abs_load"),
                        "first_negative_slope_event": _event_payload(events, "first_negative_slope"),
                        "prebreak_curvature_event": _event_payload(events, "prebreak_curvature"),
                        "sustained_decline_event": _event_payload(events, "sustained_post_peak_decline"),
                        "resolved_endpoint_policy": end_resolution.resolved_endpoint_policy,
                        "selected_endpoint_candidate": end_resolution.selected_candidate,
                        "endpoint_candidate_diagnostics": list(end_resolution.candidate_diagnostics),
                        "experiment_signal_gate": gate_record,
                        "source_series_refs": source_refs,
                        "bounded_series_refs": bounded_refs,
                        "analysis_interval": record_payload["analysis_interval"],
                    },
                    audit_view_hint="experiment_boundary_resolution",
                    warnings=tuple(warnings),
                )
            )
        return results


@dataclass(frozen=True, slots=True)
class _EndResolution:
    end_index: int | None
    reason: str
    first_negative_slope: dict[str, Any] | None = None
    prebreak_curvature: dict[str, Any] | None = None
    sustained_decline: dict[str, Any] | None = None
    resolved_endpoint_policy: dict[str, Any] | None = None
    selected_candidate: dict[str, Any] | None = None
    candidate_diagnostics: tuple[dict[str, Any], ...] = ()
    accepted_failure_peak_index: int | None = None
    reported_strength_index: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _EndpointPolicy:
    min_drop_fraction_of_peak: float
    min_drop_absolute_load: float | None
    noise_floor_multiplier: float | None
    recovery_level_fraction_of_peak: float
    low_state_level_fraction_of_peak: float
    low_state_window_points: int
    low_state_min_fraction: float
    min_low_state_points: int
    local_recovery_window_multiplier: float
    min_recovery_window_points: int
    trough_to_recovery_window_points: int
    recovery_amplitude_decisive_fraction_of_peak: float
    recovery_slope_fraction: float
    later_higher_relative_tolerance: float
    later_higher_absolute_tolerance: float
    significant_recovery_requires_higher_or_slope: bool
    sign_state_audit_policy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.endpoint_detection_policy.v0_1",
            "min_drop_fraction_of_peak": self.min_drop_fraction_of_peak,
            "min_drop_absolute_load": self.min_drop_absolute_load,
            "noise_floor_multiplier": self.noise_floor_multiplier,
            "recovery_level_fraction_of_peak": self.recovery_level_fraction_of_peak,
            "low_state_level_fraction_of_peak": self.low_state_level_fraction_of_peak,
            "low_state_window_points": self.low_state_window_points,
            "low_state_min_fraction": self.low_state_min_fraction,
            "min_low_state_points": self.min_low_state_points,
            "local_recovery_window_multiplier": self.local_recovery_window_multiplier,
            "min_recovery_window_points": self.min_recovery_window_points,
            "trough_to_recovery_window_points": self.trough_to_recovery_window_points,
            "recovery_amplitude_decisive_fraction_of_peak": self.recovery_amplitude_decisive_fraction_of_peak,
            "recovery_slope_fraction": self.recovery_slope_fraction,
            "later_higher_relative_tolerance": self.later_higher_relative_tolerance,
            "later_higher_absolute_tolerance": self.later_higher_absolute_tolerance,
            "significant_recovery_requires_higher_or_slope": self.significant_recovery_requires_higher_or_slope,
            "sign_state_audit_policy": self.sign_state_audit_policy,
        }


@dataclass(frozen=True, slots=True)
class _StartResolution:
    start_index: int | None
    reason: str
    min_load_fraction_of_max: float | None = None
    threshold_load: float | None = None
    excluded_points: int = 0
    warnings: tuple[str, ...] = ()


def _inputs(step: Mapping[str, Any]) -> dict[str, Any]:
    raw = step.get("inputs", {})
    return dict(raw) if isinstance(raw, Mapping) else {}


def _policy_signature(
    *,
    start_policy: str,
    end_policy: str,
    include_endpoint: bool,
    start_config: Mapping[str, Any] | None,
    slope_config: Mapping[str, Any],
    sustained_config: Mapping[str, Any] | None = None,
) -> str:
    start_config = start_config if isinstance(start_config, Mapping) else {}
    start_min_load_fraction = start_config.get("min_load_fraction_of_max", slope_config.get("min_load_fraction_of_max", 0.1))
    start_min_load_fragment = (
        f":start_min_load_fraction={start_min_load_fraction}"
        if start_policy == "load_fraction_of_max"
        else ""
    )
    sustained_config = sustained_config if isinstance(sustained_config, Mapping) else {}
    sustained_min_points = sustained_config.get("min_points", 3)
    endpoint = "include_endpoint" if include_endpoint else "exclude_endpoint"
    if end_policy == "peak_decline_non_recovery":
        endpoint_policy = _endpoint_policy_from_config(sustained_config)
        return (
            f"{start_policy}->{end_policy}"
            f"{start_min_load_fragment}"
            f":abs_load_derivative=point_index"
            f":candidate_sources=sign_regime|start_peak|local_peak"
            f":candidate_order=earliest_accepted_failure"
            f":meaningful_drop_fraction={endpoint_policy.min_drop_fraction_of_peak}"
            f":recovery_level_fraction={endpoint_policy.recovery_level_fraction_of_peak}"
            f":low_state_level_fraction={endpoint_policy.low_state_level_fraction_of_peak}"
            f":low_state_window_points={endpoint_policy.low_state_window_points}"
            f":min_low_state_points={endpoint_policy.min_low_state_points}"
            f":low_state_min_fraction={endpoint_policy.low_state_min_fraction}"
            f":recovery_amplitude_decisive_fraction={endpoint_policy.recovery_amplitude_decisive_fraction_of_peak}"
            f":recovery_slope_fraction={endpoint_policy.recovery_slope_fraction}"
            f":later_higher_relative_tolerance={endpoint_policy.later_higher_relative_tolerance}"
            f":domain_evidence=diagnostic_with_point_index_fallback"
            f":non_recovery=meaningful_drop_plus_sustained_low_state_without_real_recovery"
            f":fallback=post_start_max_abs_load"
            f":{endpoint}"
        )
    slope_domain = str(slope_config.get("slope_domain") or "point_index")
    derivative_step = slope_config.get("derivative_step_points", 1)
    min_load_fraction = slope_config.get("min_load_fraction_of_max", 0.1)
    min_drop = slope_config.get("min_relative_load_drop", 0.0)
    min_negative_domain_step = slope_config.get("min_negative_domain_step", 0.0)
    detect_strain_collapse = _bool(slope_config.get("detect_strain_collapse", True))
    min_strain_before_collapse = slope_config.get("min_strain_before_collapse", 0.0002)
    min_relative_strain_collapse = slope_config.get("min_relative_strain_collapse", 0.25)
    min_curvature_change = slope_config.get("min_relative_curvature_change", 0.5)
    lookback = slope_config.get("prebreak_lookback_points", 8)
    curvature = _bool(slope_config.get("use_prebreak_curvature", True))
    sustained_enabled = _bool(sustained_config.get("enabled", False))
    sustained_use_as = sustained_config.get("use_as") or "diagnostic_only"
    sustained_min_drop = sustained_config.get("min_relative_drop", 0.005)
    return (
        f"{start_policy}->{end_policy}"
        f"{start_min_load_fragment}"
        f":domain={slope_domain}"
        f":step={derivative_step}"
        f":min_load_fraction={min_load_fraction}"
        f":min_relative_drop={min_drop}"
        f":min_negative_domain_step={min_negative_domain_step}"
        f":detect_strain_collapse={detect_strain_collapse}"
        f":min_strain_before_collapse={min_strain_before_collapse}"
        f":min_relative_strain_collapse={min_relative_strain_collapse}"
        f":min_relative_curvature_change={min_curvature_change}"
        f":lookback={lookback}"
        f":curvature={curvature}"
        f":sustained_enabled={sustained_enabled}"
        f":sustained_use_as={sustained_use_as}"
        f":sustained_min_points={sustained_min_points}"
        f":sustained_min_relative_drop={sustained_min_drop}"
        f":{endpoint}"
    )


def _resolve_start_boundary(
    *,
    load: list[Any] | None,
    time: list[Any] | None,
    strain: list[Any] | None,
    start_policy: str,
    config: Mapping[str, Any],
    fallback_config: Mapping[str, Any],
) -> _StartResolution:
    if start_policy == "first_point":
        reset_start = _preload_reset_start(load)
        if reset_start is not None:
            if reset_start.get("start_refinement") == "stable_low_load_seating_shelf":
                reason = (
                    "final stable low-load seating shelf after a preload reset selected as analysis start; "
                    "raw prefix remains available for audit."
                )
            else:
                reason = (
                    "last stable preload point before a reset/unload valley selected as analysis start; "
                    "raw prefix remains available for audit."
                )
            return _StartResolution(
                start_index=int(reset_start["start_index"]),
                reason=reason,
                excluded_points=int(reset_start["start_index"]),
            )
        relaxation_start = _initial_strain_relaxation_start(load=load, strain=strain)
        if relaxation_start is not None:
            return _StartResolution(
                start_index=int(relaxation_start["start_index"]),
                reason=(
                    "first point after an initial strain-relaxation minimum during rising load selected as analysis start; "
                    "raw prefix remains available for audit."
                ),
                excluded_points=int(relaxation_start["start_index"]),
            )
        toe_start = _low_stiffness_to_material_branch_start(load=load, strain=strain)
        if toe_start is not None:
            return _StartResolution(
                start_index=int(toe_start["start_index"]),
                reason=(
                    "first point before a low-stiffness toe enters the later material-stiffness branch selected as analysis start; "
                    "raw prefix remains available for audit."
                ),
                excluded_points=int(toe_start["start_index"]),
            )
        start_index = 0 if _series_length(load, strain, time) else None
        return _StartResolution(
            start_index=start_index,
            reason="first recorded point selected as analysis start.",
            excluded_points=0,
            warnings=() if start_index is not None else ("No series points were available for start boundary resolution.",),
        )
    if start_policy != "load_fraction_of_max":
        return _StartResolution(
            start_index=None,
            reason=f"unsupported start_policy={start_policy}.",
            warnings=(f"Unsupported start_policy '{start_policy}'.",),
        )
    max_point = _max_abs_point(load)
    if load is None:
        return _StartResolution(
            start_index=None,
            reason="load-fraction start could not be resolved.",
            warnings=("Load series is required for load_fraction_of_max start policy.",),
        )
    if max_point is None:
        return _StartResolution(
            start_index=None,
            reason="load-fraction start could not be resolved.",
            warnings=("Load series has no numeric values for load_fraction_of_max start policy.",),
        )
    max_load = abs(float(max_point[1]))
    if max_load <= 0:
        return _StartResolution(
            start_index=0 if _series_length(load, strain, time) else None,
            reason="first recorded point selected because maximum absolute load is zero.",
            min_load_fraction_of_max=0.0,
            threshold_load=0.0,
            excluded_points=0,
            warnings=("Load-fraction start fallback used because maximum absolute load is zero.",),
        )
    raw_fraction = _as_float(config.get("min_load_fraction_of_max"))
    if raw_fraction is None:
        raw_fraction = _as_float(fallback_config.get("min_load_fraction_of_max"))
    raw_fraction = 0.1 if raw_fraction is None else raw_fraction
    fraction = max(0.0, min(1.0, raw_fraction))
    warnings: list[str] = []
    if fraction != raw_fraction:
        warnings.append(
            f"Start min_load_fraction_of_max={raw_fraction} was outside [0, 1] and was clamped to {fraction}."
        )
    threshold = max_load * fraction
    start_index = None
    for index, value in enumerate(load):
        numeric = _as_float(value)
        if numeric is not None and abs(float(numeric)) >= threshold:
            start_index = index
            break
    if start_index is None:
        start_index = 0 if _series_length(load, strain, time) else None
        warnings.append("Load-fraction start fallback used because no point reached the threshold.")
    excluded_points = max(0, int(start_index or 0))
    return _StartResolution(
        start_index=start_index,
        reason=(
            f"first point reaching {fraction:g} of maximum absolute load selected as analysis start"
            if start_index is not None
            else "load-fraction start could not be resolved"
        ),
        min_load_fraction_of_max=fraction,
        threshold_load=threshold,
        excluded_points=excluded_points,
        warnings=tuple(warnings),
    )


def _preload_reset_start(load: list[Any] | None) -> dict[str, Any] | None:
    if load is None or len(load) < 24:
        return None
    y = [_as_abs_float(value) for value in load]
    numeric_count = sum(1 for value in y if value is not None)
    if numeric_count < 24:
        return None
    search_end = max(12, min(len(y) - 6, len(y) // 3))
    for index in range(8, search_end):
        prefix = [value for value in y[max(0, index - 32) : index] if value is not None and isfinite(float(value))]
        if len(prefix) < 8:
            continue
        prefix_steps = [
            abs(prefix[step] - prefix[step - 1])
            for step in range(1, len(prefix))
            if prefix[step] is not None and prefix[step - 1] is not None
        ]
        step_floor = _median_positive_float(prefix_steps) or 1e-12
        prefix_median = _median_float(prefix)
        prefix_range = max(prefix) - min(prefix)
        stability_floor = max(step_floor * 4.0, abs(prefix_median) * 0.25, 1e-12)
        if prefix_range > stability_floor:
            continue
        drop_floor = max(step_floor * 3.0, prefix_range * 1.5, 1e-12)
        current = y[index]
        previous = y[index - 1] if index > 0 else None
        if current is None or previous is None:
            continue
        if current >= prefix_median - drop_floor or current > previous:
            continue
        valley_window = [value for value in y[index : min(len(y), index + 12)] if value is not None]
        future_window = [value for value in y[index : min(len(y), index + 36)] if value is not None]
        if len(valley_window) < 4 or len(future_window) < 8:
            continue
        valley = min(valley_window)
        future_peak = max(future_window)
        if valley > prefix_median - drop_floor:
            continue
        if future_peak < prefix_median + drop_floor:
            continue
        if not _sustained_growth_after_valley(future_window, floor=step_floor):
            continue
        result: dict[str, Any] = {
            "start_index": max(0, index - 1),
            "drop_index": index,
            "prefix_median_load": prefix_median,
            "prefix_range_load": prefix_range,
            "step_noise_floor": step_floor,
            "valley_load": valley,
            "future_peak_load": future_peak,
        }
        seating_start = _stable_low_load_seating_start(
            load=load,
            current_start=int(result["start_index"]),
        )
        if seating_start is not None:
            result = {
                **result,
                **seating_start,
                "reset_start_index": result["start_index"],
                "start_refinement": "stable_low_load_seating_shelf",
            }
        return result
    low_plateau_start = _signed_low_plateau_before_loading_start(load)
    if low_plateau_start is None:
        return None
    seating_start = _stable_low_load_seating_start(
        load=load,
        current_start=int(low_plateau_start["start_index"]),
    )
    if seating_start is None:
        return low_plateau_start
    return {
        **low_plateau_start,
        **seating_start,
        "pre_refinement_start_index": low_plateau_start["start_index"],
        "start_refinement": "stable_low_load_seating_shelf",
    }


def _stable_low_load_seating_start(
    *,
    load: list[Any],
    current_start: int,
) -> dict[str, Any] | None:
    signed = [_as_float(value) for value in load]
    if current_start < 0 or current_start >= len(signed):
        return None
    machine_floor = _machine_discreteness_floor(signed)
    current_load = signed[current_start]
    if current_load is None or abs(float(current_load)) > max(machine_floor * 2.5, 1e-12):
        return None
    search_end = max(12, min(len(signed) - 8, len(signed) // 3))
    candidates: list[dict[str, Any]] = []
    for index in range(current_start + 1, search_end):
        for width in range(5, 18):
            end = index + width
            if end >= len(signed):
                continue
            plateau = [
                float(value)
                for value in signed[index:end]
                if value is not None and isfinite(float(value))
            ]
            if len(plateau) < width - 1:
                continue
            plateau_median = _median_float(plateau)
            plateau_range = max(plateau) - min(plateau)
            if abs(plateau_median) > machine_floor * 40.0:
                continue
            if plateau_range > machine_floor * 12.0:
                continue
            future = [
                float(value)
                for value in signed[end : min(len(signed), end + 42)]
                if value is not None and isfinite(float(value))
            ]
            if len(future) < 8:
                continue
            required_excursion = max(
                machine_floor * 12.0,
                plateau_range * 3.0,
                abs(plateau_median) * 0.5,
                1e-12,
            )
            if max(abs(value - plateau_median) for value in future) < required_excursion:
                continue
            if not _signed_loading_moves_away_from_plateau(
                future,
                plateau_median=plateau_median,
                floor=machine_floor,
            ):
                continue
            start_index = min(end - 1, index + ((width - 1) * 3) // 5)
            candidates.append(
                {
                    "start_index": start_index,
                    "plateau_start_index": index,
                    "plateau_end_index": end - 1,
                    "plateau_width_points": width,
                    "plateau_median_load": plateau_median,
                    "plateau_range_load": plateau_range,
                    "machine_discreteness_floor": machine_floor,
                    "future_load_excursion": max(abs(value - plateau_median) for value in future),
                }
            )
    if not candidates:
        return None

    selected = max(
        candidates,
        key=lambda candidate: (
            int(candidate["plateau_width_points"]),
            int(candidate["start_index"]),
        ),
    )
    if abs(float(selected["plateau_median_load"])) < machine_floor * 0.5:
        nonzero_low_shelves = [
            candidate
            for candidate in candidates
            if abs(float(candidate["plateau_median_load"])) > machine_floor
            and abs(float(candidate["plateau_median_load"])) <= machine_floor * 20.0
            and int(candidate["plateau_width_points"]) >= 7
        ]
        if nonzero_low_shelves:
            selected = max(
                nonzero_low_shelves,
                key=lambda candidate: (
                    abs(float(candidate["plateau_median_load"])),
                    int(candidate["plateau_width_points"]),
                    -int(candidate["start_index"]),
                ),
            )
    if int(selected["start_index"]) <= current_start:
        return None
    return selected


def _machine_discreteness_floor(values: list[float | None]) -> float:
    numeric = [float(value) for value in values if value is not None and isfinite(float(value))]
    steps = sorted(
        abs(numeric[index] - numeric[index - 1])
        for index in range(1, len(numeric))
        if abs(numeric[index] - numeric[index - 1]) > 0.0
    )
    if not steps:
        return 1e-12
    return max(float(steps[0]), 1e-12)


def _initial_strain_relaxation_start(
    *,
    load: list[Any] | None,
    strain: list[Any] | None,
) -> dict[str, Any] | None:
    if load is None or strain is None or len(load) < 32 or len(strain) < 32:
        return None
    scan_end = min(32, len(load), len(strain))
    strain_values = [
        (index, value)
        for index in range(scan_end)
        if (value := _as_float(strain[index])) is not None
    ]
    if len(strain_values) < 12:
        return None
    minimum_index, minimum_strain = min(strain_values, key=lambda item: item[1])
    initial_strain = strain_values[0][1]
    if minimum_index < 10:
        return None
    relaxation_steps = [
        abs(strain_values[index][1] - strain_values[index - 1][1])
        for index in range(1, min(len(strain_values), minimum_index + 1))
    ]
    strain_floor = _median_positive_float(relaxation_steps) or 1e-12
    if initial_strain - minimum_strain <= max(strain_floor * 4.0, 1e-12):
        return None
    load_steps = [
        abs(float(current) - float(previous))
        for index in range(1, minimum_index + 1)
        if (current := _as_float(load[index])) is not None
        and (previous := _as_float(load[index - 1])) is not None
    ]
    load_floor = _median_positive_float(load_steps) or 1e-12
    directional_steps = 0
    rising_steps = 0
    for index in range(1, minimum_index + 1):
        current = _as_float(load[index])
        previous = _as_float(load[index - 1])
        if current is None or previous is None:
            continue
        delta = float(current) - float(previous)
        if abs(delta) <= load_floor:
            continue
        directional_steps += 1
        if delta > 0.0:
            rising_steps += 1
    if directional_steps < 4 or rising_steps / directional_steps < 0.7:
        return None
    tail = [
        value
        for index in range(minimum_index, min(minimum_index + 6, len(strain)))
        if (value := _as_float(strain[index])) is not None
    ]
    if len(tail) < 4 or min(tail[1:]) < minimum_strain - strain_floor:
        return None
    return {
        "start_index": minimum_index + 1 if minimum_index + 1 < len(strain) else minimum_index,
        "strain_relaxation_minimum_index": minimum_index,
        "initial_strain": initial_strain,
        "minimum_strain": minimum_strain,
        "strain_step_noise_floor": strain_floor,
        "load_step_noise_floor": load_floor,
    }


def _low_stiffness_to_material_branch_start(
    *,
    load: list[Any] | None,
    strain: list[Any] | None,
) -> dict[str, Any] | None:
    if load is None or strain is None:
        return None
    length = min(len(load), len(strain))
    if length < 80:
        return None
    y = [_as_float(value) for value in load[:length]]
    domain = [_as_float(value) for value in strain[:length]]
    window = max(5, min(12, int(length**0.5) // 2))
    scan_end = min(length - window, length // 3)
    stiffness: list[tuple[int, float]] = []
    for index in range(0, scan_end):
        if y[index] is None or y[index + window] is None:
            continue
        if domain[index] is None or domain[index + window] is None:
            continue
        load_delta = float(y[index + window]) - float(y[index])
        domain_delta = float(domain[index + window]) - float(domain[index])
        if load_delta <= 0.0 or domain_delta <= 0.0:
            continue
        stiffness.append((index, load_delta / domain_delta))
    if len(stiffness) < 12:
        return None

    early_values = [value for _, value in stiffness[: max(8, len(stiffness) // 5)]]
    later_values = [value for _, value in stiffness[len(stiffness) // 2 :]]
    later_values = later_values or [value for _, value in stiffness]
    early_centre = _median_float(early_values)
    later_centre = _median_float(later_values)
    if early_centre <= 0.0 or later_centre <= early_centre:
        return None
    early_mad = _median_absolute_deviation(early_values, centre=early_centre)
    later_mad = _median_absolute_deviation(later_values, centre=later_centre)
    separation_floor = max(early_mad, later_mad, 1e-12) * 6.0
    if later_centre - early_centre <= separation_floor:
        return None
    if later_centre / early_centre < 4.0:
        return None

    ordered_later = sorted(later_values)
    material_stiffness_floor = ordered_later[len(ordered_later) // 4]
    for index, value in stiffness:
        if value < material_stiffness_floor:
            continue
        start_index = max(0, index - window)
        if start_index == 0:
            return None
        return {
            "start_index": start_index,
            "material_stiffness_window_start_index": index,
            "stiffness_window_points": window,
            "early_stiffness": early_centre,
            "later_stiffness": later_centre,
            "material_stiffness_floor": material_stiffness_floor,
        }
    return None


def _signed_low_plateau_before_loading_start(load: list[Any]) -> dict[str, Any] | None:
    signed = [_as_float(value) for value in load]
    search_end = max(12, min(len(signed) - 8, len(signed) // 3))
    for index in range(4, search_end):
        for width in range(5, 13):
            end = index + width
            if end >= len(signed):
                continue
            plateau = [
                float(value)
                for value in signed[index:end]
                if value is not None and isfinite(float(value))
            ]
            if len(plateau) < width - 1:
                continue
            plateau_median = _median_float(plateau)
            if plateau_median > 0.0:
                continue
            steps = [abs(plateau[step] - plateau[step - 1]) for step in range(1, len(plateau))]
            step_floor = _median_positive_float(steps) or 1e-12
            plateau_range = max(plateau) - min(plateau)
            stability_floor = max(step_floor * 3.0, abs(plateau_median) * 0.25, 1e-12)
            if plateau_range > stability_floor:
                continue
            future = [
                float(value)
                for value in signed[end : min(len(signed), end + 36)]
                if value is not None and isfinite(float(value))
            ]
            if len(future) < 8:
                continue
            future_abs_peak = max(abs(value) for value in future)
            growth_floor = max(step_floor * 4.0, plateau_range * 2.0, 1e-12)
            if future_abs_peak < abs(plateau_median) + growth_floor:
                continue
            if not _signed_loading_moves_away_from_plateau(future, plateau_median=plateau_median, floor=step_floor):
                continue
            return {
                "start_index": index + (width - 1) // 2,
                "plateau_start_index": index,
                "plateau_end_index": end - 1,
                "plateau_median_load": plateau_median,
                "plateau_range_load": plateau_range,
                "step_noise_floor": step_floor,
                "future_abs_peak_load": future_abs_peak,
            }
    return None


def _signed_loading_moves_away_from_plateau(
    values: list[float],
    *,
    plateau_median: float,
    floor: float,
) -> bool:
    if len(values) < 6:
        return False
    direction = -1.0 if plateau_median <= 0.0 else 1.0
    total = 0
    moving_away = 0
    for index in range(1, min(len(values), 12)):
        delta = values[index] - values[index - 1]
        if abs(delta) <= floor:
            continue
        total += 1
        if delta * direction > 0.0:
            moving_away += 1
    if total == 0:
        return False
    return moving_away / total >= 0.6 and abs(values[-1]) > abs(plateau_median) + floor


def _sustained_growth_after_valley(values: list[float], *, floor: float) -> bool:
    if len(values) < 6:
        return False
    valley_index = min(range(len(values)), key=lambda index: values[index])
    tail = values[valley_index:]
    if len(tail) < 5:
        return False
    positive = 0
    total = 0
    for index in range(1, min(len(tail), 10)):
        delta = tail[index] - tail[index - 1]
        if abs(delta) <= floor:
            continue
        total += 1
        if delta > 0.0:
            positive += 1
    return total > 0 and positive / total >= 0.6 and tail[-1] > tail[0] + floor


def _median_float(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values if isfinite(float(value)))
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (float(ordered[middle - 1]) + float(ordered[middle])) / 2.0


def _median_positive_float(values: list[float]) -> float | None:
    ordered = sorted(float(value) for value in values if value > 0.0 and isfinite(float(value)))
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (float(ordered[middle - 1]) + float(ordered[middle])) / 2.0


def _median_absolute_deviation(values: list[float], *, centre: float) -> float:
    return _median_float([abs(float(value) - centre) for value in values if isfinite(float(value))])


def _resolve_end_boundary(
    *,
    load: list[Any] | None,
    strain: list[Any] | None,
    start_index: int | None,
    run_id: str | None = None,
    end_policy: str,
    slope_config: Mapping[str, Any],
    sustained_config: Mapping[str, Any],
    gate_window: Mapping[str, Any] | None = None,
    gate_record: Mapping[str, Any] | None = None,
) -> _EndResolution:
    max_point = _max_abs_point(load)
    gate_end_index = _gate_end_index(gate_window)
    if end_policy == "max_abs_load":
        gated_max_point = (
            _max_abs_point_in_interval(
                load,
                start_index=start_index,
                end_index=gate_end_index,
                include_endpoint=True,
            )
            if gate_end_index is not None
            else max_point
        )
        return _EndResolution(
            end_index=gated_max_point[0] if gated_max_point else None,
            reason=(
                "maximum absolute load inside the experiment signal gate selected as analysis endpoint."
                if gate_end_index is not None
                else "maximum absolute load selected as analysis endpoint."
            ),
            warnings=() if gated_max_point else ("max_abs_load endpoint could not be resolved.",),
        )
    if end_policy == "peak_decline_non_recovery":
        return _peak_decline_non_recovery_resolution(
            load=load,
            strain=strain,
            start_index=start_index,
            run_id=run_id,
            sustained_config=sustained_config,
            gate_end_index=gate_end_index,
            gate_record=gate_record,
        )
    if end_policy != "slope_break_pre_negative":
        return _EndResolution(
            end_index=None,
            reason=f"unsupported end_policy={end_policy}.",
            warnings=(f"Unsupported end_policy '{end_policy}'.",),
        )
    return _slope_break_pre_negative_resolution(
        load=load,
        strain=strain,
        config=slope_config,
        sustained_config=sustained_config,
    )


def _peak_decline_non_recovery_resolution(
    *,
    load: list[Any] | None,
    start_index: int | None,
    strain: list[Any] | None = None,
    run_id: str | None = None,
    sustained_config: Mapping[str, Any] | None = None,
    gate_end_index: int | None = None,
    gate_record: Mapping[str, Any] | None = None,
) -> _EndResolution:
    policy = _endpoint_policy_from_config(sustained_config)
    if load is None:
        return _EndResolution(
            end_index=None,
            reason="peak-decline endpoint could not be resolved.",
            resolved_endpoint_policy=policy.to_dict(),
            warnings=("Load series is required for peak_decline_non_recovery endpoint policy.",),
        )
    if start_index is None:
        return _EndResolution(
            end_index=None,
            reason="peak-decline endpoint could not be resolved.",
            resolved_endpoint_policy=policy.to_dict(),
            warnings=("Resolved start_index is required for peak_decline_non_recovery endpoint policy.",),
        )

    start = max(0, int(start_index))
    end_limit = _series_end_limit(load, start_index=start, gate_end_index=gate_end_index)
    if start >= len(load):
        return _EndResolution(
            end_index=None,
            reason="peak-decline endpoint could not be resolved.",
            resolved_endpoint_policy=policy.to_dict(),
            warnings=("Resolved start_index is outside the load series for peak_decline_non_recovery endpoint policy.",),
        )

    y = [_abs_float(value) for value in load]
    raw = [_as_float(value) for value in load]
    domain = [_as_float(value) for value in strain] if strain is not None else None
    raw_full_run_peak = _max_abs_point_from(y, start_index=start, end_index=len(y) - 1)
    y_windowed = _windowed_values(y, start_index=start, end_index=end_limit)
    raw_windowed = _windowed_values(raw, start_index=start, end_index=end_limit)
    domain_windowed = _windowed_values(domain, start_index=start, end_index=end_limit) if domain is not None else None
    fallback = _max_abs_point_from(y_windowed, start_index=start, end_index=end_limit)
    if fallback is None:
        return _EndResolution(
            end_index=None,
            reason="peak-decline endpoint could not be resolved.",
            resolved_endpoint_policy=policy.to_dict(),
            warnings=("Load series has no numeric values at or after start_index for peak_decline_non_recovery endpoint policy.",),
        )

    blocks = _post_start_regime_blocks(y_windowed, domain=domain_windowed, start_index=start)
    candidates = _endpoint_peak_candidates(y_windowed, blocks, start_index=start)
    diagnostics = tuple(
        _evaluate_endpoint_candidate(
            y=y_windowed,
            raw=raw_windowed,
            domain=domain_windowed,
            blocks=blocks,
            candidate=candidate,
            policy=policy,
            start_index=start,
            run_id=run_id,
            candidate_number=position + 1,
        )
        for position, candidate in enumerate(candidates)
    )
    accepted = [
        diagnostic for diagnostic in diagnostics
        if diagnostic.get("candidate_final_decision") == "accepted"
    ]
    candidate_floor = _candidate_peak_load_floor(
        fallback_peak_load=fallback[1],
        full_run_peak_load=raw_full_run_peak[1] if raw_full_run_peak is not None else None,
        gate_end_index=gate_end_index,
        config=sustained_config,
    )
    accepted_above_floor = [
        diagnostic for diagnostic in accepted
        if _candidate_peak_load(diagnostic) >= candidate_floor
    ]
    if accepted_above_floor:
        selected = max(
            accepted_above_floor,
            key=lambda diagnostic: (
                _candidate_peak_load(diagnostic),
                int(diagnostic["candidate_peak_index"]),
            ),
        )
        peak_index = int(selected["candidate_peak_index"])
        dominant_gated_peak = _dominant_gated_peak_before_selected(
            fallback=fallback,
            selected=selected,
            y=y_windowed,
            end_limit=end_limit,
            policy=policy,
        )
        if dominant_gated_peak is not None:
            peak_index = int(dominant_gated_peak["candidate_peak_index"])
            selected = {**selected, **dominant_gated_peak}
        promoted_gate_endpoint = _promoted_gate_endpoint(
            selected=selected,
            gate_end_index=gate_end_index,
            gate_record=gate_record,
            y=y_windowed,
            domain=domain_windowed,
        )
        if promoted_gate_endpoint is not None:
            peak_index = promoted_gate_endpoint["candidate_peak_index"]
            selected = {**selected, **promoted_gate_endpoint}
        transition_endpoint = _gate_post_peak_transition_endpoint(
            selected=selected,
            gate_end_index=gate_end_index,
            gate_record=gate_record,
            y=y_windowed,
        )
        analysis_end_index = (
            int(transition_endpoint["analysis_end_index"])
            if transition_endpoint is not None
            else peak_index
        )
        if transition_endpoint is not None:
            selected = {**selected, **transition_endpoint}
        candidate_pattern = str(selected.get("candidate_pattern") or "")
        selected_summary = {
            "candidate_id": selected.get("candidate_id"),
            "candidate_peak_index": peak_index,
            "candidate_peak_load": selected.get("candidate_peak_load"),
            "candidate_pattern": candidate_pattern,
            "first_drop_index": selected.get("first_drop_index"),
            "trough_index": selected.get("trough_index"),
            "candidate_final_decision": selected.get("candidate_final_decision"),
            "candidate_rejection_reason": selected.get("candidate_rejection_reason"),
            "candidate_peak_load_floor": candidate_floor,
            "endpoint_arbitration": selected.get("endpoint_arbitration"),
            "endpoint_promotion": selected.get("endpoint_promotion"),
            "post_peak_transition": selected.get("post_peak_transition"),
        }
        return _EndResolution(
            end_index=analysis_end_index,
            reason=(
                "strongest accepted post-start peak inside the experiment signal gate and above the gated load-scale floor followed by meaningful non-recovering decline selected as analysis endpoint."
                if gate_end_index is not None
                else "strongest accepted post-start peak followed by meaningful non-recovering decline selected as analysis endpoint."
            ),
            sustained_decline={
                "endpoint_index": peak_index,
                "event_index": selected.get("first_drop_index"),
                "peak_index": peak_index,
                "peak_load": y_windowed[peak_index],
                "min_points": policy.min_low_state_points,
                "use_as": "endpoint",
                "selection": "peak_decline_non_recovery",
                "candidate_pattern": candidate_pattern,
                "decline_start_index": selected.get("first_drop_index"),
                "decline_end_index": selected.get("low_state_window_end_index"),
                "recovery_check": "meaningful_drop_plus_sustained_non_recovered_state_without_real_recovery",
                "drop_fraction": selected.get("drop_fraction"),
                "recovery_level_load": selected.get("recovery_level_load"),
                "candidate_peak_load_floor": candidate_floor,
                "endpoint_arbitration": selected.get("endpoint_arbitration"),
                "endpoint_promotion": selected.get("endpoint_promotion"),
                "post_peak_transition": selected.get("post_peak_transition"),
            },
            resolved_endpoint_policy=policy.to_dict(),
            selected_candidate=selected_summary,
            candidate_diagnostics=diagnostics,
            accepted_failure_peak_index=peak_index,
            reported_strength_index=peak_index,
        )

    warnings: tuple[str, ...] = ()
    if accepted and gate_end_index is not None and candidate_floor > 0.0:
        warnings = (
            "peak_decline_non_recovery ignored accepted preload-scale candidates below the gated load-scale floor and used the gated maximum fallback.",
        )

    fallback_summary = {
        "candidate_final_decision": "fallback",
        "candidate_peak_index": fallback[0],
        "candidate_peak_load": fallback[1],
        "candidate_pattern": "gated_max_abs_load",
        "candidate_peak_load_floor": candidate_floor,
        "rejected_accepted_candidate_count_below_floor": len(accepted),
    }
    transition_endpoint = _gate_post_peak_transition_endpoint(
        selected=fallback_summary,
        gate_end_index=gate_end_index,
        gate_record=gate_record,
        y=y_windowed,
    )
    analysis_end_index = (
        int(transition_endpoint["analysis_end_index"])
        if transition_endpoint is not None
        else int(fallback[0])
    )
    if transition_endpoint is not None:
        fallback_summary = {**fallback_summary, **transition_endpoint}
    return _EndResolution(
        end_index=analysis_end_index,
        reason=(
            "post-peak transition endpoint from the experiment signal gate selected as analysis endpoint while the gated maximum remains the accepted failure peak."
            if transition_endpoint is not None
            else
            "maximum absolute load inside the experiment signal gate selected because no accepted non-recovering candidate cleared the gated load-scale floor."
            if gate_end_index is not None and accepted
            else "maximum absolute load inside the experiment signal gate selected because no non-recovering post-peak decline was detected."
            if gate_end_index is not None
            else "maximum absolute load at or after start_index selected because no non-recovering post-peak decline was detected."
        ),
        resolved_endpoint_policy=policy.to_dict(),
        selected_candidate=fallback_summary if gate_end_index is not None else None,
        candidate_diagnostics=diagnostics,
        accepted_failure_peak_index=fallback[0],
        reported_strength_index=fallback[0],
        warnings=warnings or ("peak_decline_non_recovery fallback used because no candidate peak entered non-recovering decline.",),
    )


def _candidate_peak_load_floor(
    *,
    fallback_peak_load: float,
    full_run_peak_load: float | None,
    gate_end_index: int | None,
    config: Mapping[str, Any] | None,
) -> float:
    if gate_end_index is None:
        return 0.0
    config = config if isinstance(config, Mapping) else {}
    raw = _as_float(config.get("min_candidate_peak_fraction_of_gate_max"))
    fraction = _DEFAULT_MIN_CANDIDATE_PEAK_FRACTION_OF_GATE_MAX if raw is None else max(0.0, min(1.0, raw))
    full_raw = _as_float(config.get("min_gate_peak_fraction_of_full_run_max"))
    full_fraction = (
        _DEFAULT_MIN_GATE_PEAK_FRACTION_OF_FULL_RUN_MAX
        if full_raw is None
        else max(0.0, min(1.0, full_raw))
    )
    gate_floor = abs(float(fallback_peak_load)) * fraction
    full_floor = abs(float(full_run_peak_load)) * full_fraction if full_run_peak_load is not None else 0.0
    return max(gate_floor, full_floor)


def _candidate_peak_load(diagnostic: Mapping[str, Any]) -> float:
    value = _as_float(diagnostic.get("candidate_peak_load"))
    return abs(float(value)) if value is not None else 0.0


def _dominant_gated_peak_before_selected(
    *,
    fallback: tuple[int, float],
    selected: Mapping[str, Any],
    y: list[float | None],
    end_limit: int,
    policy: _EndpointPolicy,
) -> dict[str, Any] | None:
    fallback_index = int(fallback[0])
    selected_index = _as_int(selected.get("candidate_peak_index"))
    if selected_index is None or fallback_index >= selected_index or fallback_index >= end_limit:
        return None
    fallback_load = abs(float(fallback[1]))
    selected_load = _candidate_peak_load(selected)
    if fallback_load <= selected_load:
        return None
    bridge_minimum = _minimum_load_between(y, start_index=fallback_index, end_index=selected_index)
    if (
        bridge_minimum is not None
        and fallback_load > 0.0
        and bridge_minimum / fallback_load < policy.recovery_level_fraction_of_peak
    ):
        return None
    decline = _meaningful_decline_after_peak(
        y=y,
        peak_index=fallback_index,
        scan_end=min(end_limit, selected_index),
        peak_load=fallback_load,
        policy=policy,
    )
    if decline is None:
        return None
    return {
        "candidate_peak_index": fallback_index,
        "candidate_peak_load": fallback_load,
        "candidate_pattern": "dominant_gated_max_before_later_decline",
        "candidate_final_decision": "accepted",
        "first_drop_index": decline["first_drop_index"],
        "trough_index": decline["trough_index"],
        "drop_fraction": decline["drop_fraction"],
        "endpoint_arbitration": {
            "schema_id": "method.endpoint_arbitration.v0_1",
            "from_candidate_peak_index": selected_index,
            "to_dominant_peak_index": fallback_index,
            "from_candidate_peak_load": selected_load,
            "to_dominant_peak_load": fallback_load,
            "intervening_minimum_load": bridge_minimum,
            "intervening_minimum_fraction_of_peak": (
                bridge_minimum / fallback_load
                if bridge_minimum is not None and fallback_load > 0.0
                else None
            ),
            "minimum_continuous_plateau_fraction": policy.recovery_level_fraction_of_peak,
            "first_drop_index": decline["first_drop_index"],
            "trough_index": decline["trough_index"],
            "drop_fraction": decline["drop_fraction"],
            "reason": "Earlier gated maximum carries the dominant failure load and is followed by a meaningful decline before the later lower-load candidate.",
        },
    }


def _meaningful_decline_after_peak(
    *,
    y: list[float | None],
    peak_index: int,
    scan_end: int,
    peak_load: float,
    policy: _EndpointPolicy,
) -> dict[str, Any] | None:
    if peak_index < 0 or scan_end <= peak_index or peak_load <= 0.0:
        return None
    threshold = max(policy.min_drop_absolute_load or 0.0, peak_load * policy.min_drop_fraction_of_peak)
    trough_index: int | None = None
    trough_load: float | None = None
    for index in range(peak_index + 1, min(scan_end, len(y) - 1) + 1):
        value = y[index]
        if value is None:
            continue
        load = abs(float(value))
        if trough_load is None or load < trough_load:
            trough_load = load
            trough_index = index
        if peak_load - load >= threshold:
            return {
                "first_drop_index": index,
                "trough_index": trough_index if trough_index is not None else index,
                "drop_fraction": (peak_load - load) / peak_load,
            }
    return None


def _minimum_load_between(
    y: list[float | None],
    *,
    start_index: int,
    end_index: int,
) -> float | None:
    values = [
        abs(float(value))
        for value in y[start_index : end_index + 1]
        if value is not None and isfinite(float(value))
    ]
    return min(values) if values else None


def _promoted_gate_endpoint(
    *,
    selected: Mapping[str, Any],
    gate_end_index: int | None,
    gate_record: Mapping[str, Any] | None,
    y: list[float | None],
    domain: list[float | None] | None,
) -> dict[str, Any] | None:
    if gate_end_index is None:
        return None
    rescued_later_branch = _gate_rescued_later_load_bearing_branch(gate_record)
    coherent_dominant_endpoint = _coherent_gate_dominant_endpoint(gate_record)
    if not rescued_later_branch and not coherent_dominant_endpoint:
        return None
    selected_index = _as_int(selected.get("candidate_peak_index"))
    if selected_index is None or gate_end_index <= selected_index or gate_end_index >= len(y):
        return None
    selected_load = _candidate_peak_load(selected)
    gate_load = y[gate_end_index]
    if gate_load is None or abs(float(gate_load)) <= selected_load:
        return None
    if coherent_dominant_endpoint and not _later_gate_gain_exceeds_candidate_drop(
        selected=selected,
        y=y,
        selected_load=selected_load,
        gate_load=abs(float(gate_load)),
    ):
        return None
    path_evidence = _same_domain_loading_path_evidence(
        domain,
        start_index=selected_index,
        end_index=gate_end_index,
    )
    if rescued_later_branch and path_evidence is not None and not bool(path_evidence["same_loading_path"]):
        return None
    reason = (
        "Later dominant gate endpoint is load-bearing and intervening jaggedness lacks a material domain reset."
        if rescued_later_branch
        else "High-confidence coherent gate contains a later dominant maximum after an earlier local decline."
    )
    return {
        "candidate_peak_index": gate_end_index,
        "candidate_peak_load": abs(float(gate_load)),
        "candidate_pattern": (
            "promoted_gate_dominant_peak"
            if rescued_later_branch
            else "promoted_coherent_gate_dominant_peak"
        ),
        "candidate_final_decision": "accepted",
        "endpoint_promotion": {
            "schema_id": "method.endpoint_promotion.v0_1",
            "from_candidate_peak_index": selected_index,
            "to_gate_end_index": gate_end_index,
            "from_candidate_peak_load": selected_load,
            "to_gate_end_load": abs(float(gate_load)),
            "domain_path_evidence": path_evidence,
            "reason": reason,
        },
    }


def _later_gate_gain_exceeds_candidate_drop(
    *,
    selected: Mapping[str, Any],
    y: list[float | None],
    selected_load: float,
    gate_load: float,
) -> bool:
    first_drop_index = _as_int(selected.get("first_drop_index"))
    if first_drop_index is None or first_drop_index < 0 or first_drop_index >= len(y):
        return False
    first_drop_load = y[first_drop_index]
    if first_drop_load is None:
        return False
    candidate_drop = selected_load - abs(float(first_drop_load))
    later_gain = gate_load - selected_load
    return candidate_drop > 0.0 and later_gain > candidate_drop


def _coherent_gate_dominant_endpoint(gate_record: Mapping[str, Any] | None) -> bool:
    if not isinstance(gate_record, Mapping):
        return False
    if str(gate_record.get("status") or "") != "ok":
        return False
    if str(gate_record.get("confidence") or "") != "high":
        return False
    coherent_window = gate_record.get("coherent_window")
    if not isinstance(coherent_window, Mapping):
        return False
    if str(coherent_window.get("classification") or "") != "coherent_experiment_signal":
        return False
    excluded_regions = gate_record.get("excluded_regions")
    return not isinstance(excluded_regions, (list, tuple)) or not excluded_regions


def _gate_post_peak_transition_endpoint(
    *,
    selected: Mapping[str, Any],
    gate_end_index: int | None,
    gate_record: Mapping[str, Any] | None,
    y: list[float | None],
) -> dict[str, Any] | None:
    if gate_end_index is None or gate_record is None:
        return None
    peak_index = _as_int(selected.get("candidate_peak_index"))
    if peak_index is None or gate_end_index <= peak_index or gate_end_index >= len(y):
        return None
    transition = _gate_transition_for_peak(gate_record, peak_index=peak_index)
    if transition is None:
        return None
    transition_end = _as_int(transition.get("end_index"))
    if transition_end is None or transition_end != gate_end_index:
        return None
    gate_load = y[gate_end_index]
    peak_load = y[peak_index]
    if gate_load is None or peak_load is None:
        return None
    if abs(float(gate_load)) > abs(float(peak_load)):
        return None
    return {
        "analysis_end_index": gate_end_index,
        "post_peak_transition": {
            "schema_id": "method.boundary_post_peak_transition.v0_1",
            "accepted_failure_peak_index": peak_index,
            "analysis_end_index": gate_end_index,
            "gate_transition": transition,
            "reason": "Gate evidence separates the accepted failure peak from a short high-load post-peak transition before sustained collapse.",
        },
    }


def _gate_transition_for_peak(gate_record: Mapping[str, Any], *, peak_index: int) -> Mapping[str, Any] | None:
    diagnostics = gate_record.get("diagnostics")
    if not isinstance(diagnostics, (list, tuple)):
        return None
    for item in diagnostics:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("classification") or "") != "load_bearing_restart_after_jagged_region":
            continue
        accepted_peak = _as_int(item.get("accepted_failure_peak_index"))
        if accepted_peak != peak_index:
            continue
        transition = item.get("post_peak_transition")
        if isinstance(transition, Mapping):
            return transition
    return None


def _gate_rescued_later_load_bearing_branch(gate_record: Mapping[str, Any] | None) -> bool:
    if not isinstance(gate_record, Mapping):
        return False
    classifications = gate_record.get("classifications")
    if isinstance(classifications, str):
        return "load_bearing_restart_after_jagged_region" in classifications
    if isinstance(classifications, (list, tuple, set)):
        return any(str(item) == "load_bearing_restart_after_jagged_region" for item in classifications)
    diagnostics = gate_record.get("diagnostics")
    if isinstance(diagnostics, (list, tuple)):
        return any(
            isinstance(item, Mapping)
            and str(item.get("classification") or "") == "load_bearing_restart_after_jagged_region"
            for item in diagnostics
        )
    return False


def _same_domain_loading_path_evidence(
    domain: list[float | None] | None,
    *,
    start_index: int,
    end_index: int,
) -> dict[str, Any] | None:
    if domain is None or start_index < 0 or end_index >= len(domain) or start_index >= end_index:
        return None
    values = [float(value) for value in domain[start_index : end_index + 1] if value is not None and isfinite(float(value))]
    if len(values) < 3:
        return None
    span = max(values) - min(values)
    net = values[-1] - values[0]
    negative_steps = [values[index - 1] - values[index] for index in range(1, len(values)) if values[index] < values[index - 1]]
    largest_reverse_step = max(negative_steps, default=0.0)
    same_path = span <= 0.0 or (net >= 0.0 and largest_reverse_step <= span)
    return {
        "schema_id": "method.domain_loading_path_evidence.v0_1",
        "start_domain": values[0],
        "end_domain": values[-1],
        "domain_span": span,
        "net_domain_delta": net,
        "largest_reverse_step": largest_reverse_step,
        "same_loading_path": same_path,
        "basis": "largest reverse step compared with observed local domain span",
    }


def _post_start_regime_blocks(
    y: list[float | None],
    *,
    domain: list[float | None] | None,
    start_index: int,
) -> list[dict[str, float | int | str | None]]:
    blocks: list[dict[str, float | int | str | None]] = []
    current_regime: str | None = None
    current_start: int | None = None
    current_end: int | None = None
    current_delta = 0.0
    current_net_domain_delta = 0.0
    current_domain_edges = 0
    current_positive_domain_edges = 0
    current_edges = 0

    def flush() -> None:
        nonlocal current_regime, current_start, current_end, current_delta
        nonlocal current_net_domain_delta, current_domain_edges
        nonlocal current_positive_domain_edges, current_edges
        if current_regime is not None and current_start is not None and current_end is not None:
            point_slope = current_delta / current_edges if current_edges else None
            domain_slope = (
                current_delta / current_net_domain_delta
                if (
                    current_regime == "+"
                    and current_net_domain_delta > 0.0
                    and current_domain_edges > 0
                    and current_positive_domain_edges >= max(1, (current_domain_edges + 1) // 2)
                )
                else None
            )
            blocks.append(
                {
                    "regime": current_regime,
                    "start_index": current_start,
                    "end_index": current_end,
                    "edge_count": current_edges,
                    "delta": current_delta,
                    "point_slope": point_slope,
                    "domain_slope": domain_slope,
                    "domain_edge_count": current_domain_edges,
                    "net_domain_delta": current_net_domain_delta,
                    "positive_domain_edges": current_positive_domain_edges,
                }
            )
        current_regime = None
        current_start = None
        current_end = None
        current_delta = 0.0
        current_net_domain_delta = 0.0
        current_domain_edges = 0
        current_positive_domain_edges = 0
        current_edges = 0

    for index in range(max(0, start_index), len(y) - 1):
        delta = _abs_delta(y, index)
        if delta is None:
            flush()
            continue
        regime = _delta_regime(delta)
        if current_regime is None:
            current_regime = regime
            current_start = index
            current_end = index + 1
            current_delta = delta
            domain_delta = _domain_delta(domain, index)
            current_net_domain_delta = domain_delta if domain_delta is not None else 0.0
            current_domain_edges = 1 if domain_delta is not None else 0
            current_positive_domain_edges = 1 if domain_delta is not None and domain_delta > 0.0 else 0
            current_edges = 1
            continue
        if regime != current_regime:
            flush()
            current_regime = regime
            current_start = index
            current_end = index + 1
            current_delta = delta
            domain_delta = _domain_delta(domain, index)
            current_net_domain_delta = domain_delta if domain_delta is not None else 0.0
            current_domain_edges = 1 if domain_delta is not None else 0
            current_positive_domain_edges = 1 if domain_delta is not None and domain_delta > 0.0 else 0
            current_edges = 1
            continue
        current_end = index + 1
        current_delta += delta
        domain_delta = _domain_delta(domain, index)
        if domain_delta is not None:
            current_net_domain_delta += domain_delta
            current_domain_edges += 1
        if domain_delta is not None and domain_delta > 0.0:
            current_positive_domain_edges += 1
        current_edges += 1
    flush()
    return blocks


def _post_start_peak_candidates(
    blocks: list[dict[str, float | int | str | None]],
    *,
    min_points: int,
) -> list[dict[str, float | int | str | None]]:
    candidates: list[dict[str, float | int | str | None]] = []
    seen: set[int] = set()
    for position, block in enumerate(blocks):
        if block.get("regime") != "+":
            continue
        next_block = blocks[position + 1] if position + 1 < len(blocks) else None
        if not _blocks_touch(block, next_block):
            continue
        if next_block and next_block.get("regime") == "-":
            peak_index = int(block["end_index"])
            if peak_index not in seen:
                candidates.append(
                    {
                        "peak_index": peak_index,
                        "pattern": "+ -",
                        "rising_block_position": position,
                        "decline_block_position": position + 1,
                        "decline_start_index": int(next_block["start_index"]),
                        "decline_end_index": int(next_block["end_index"]),
                    }
                )
                seen.add(peak_index)
            continue
        plateau_block = next_block
        decline_block = blocks[position + 2] if position + 2 < len(blocks) else None
        if (
            plateau_block
            and plateau_block.get("regime") == "0"
            and _blocks_touch(plateau_block, decline_block)
            and decline_block
            and decline_block.get("regime") == "-"
        ):
            peak_index = int(plateau_block["end_index"])
            if peak_index not in seen:
                candidates.append(
                    {
                        "peak_index": peak_index,
                        "pattern": "+ 0 -",
                        "rising_block_position": position,
                        "decline_block_position": position + 2,
                        "decline_start_index": int(decline_block["start_index"]),
                        "decline_end_index": int(decline_block["end_index"]),
                    }
                )
                seen.add(peak_index)
    return candidates


def _endpoint_policy_from_config(config: Mapping[str, Any] | None) -> _EndpointPolicy:
    config = config if isinstance(config, Mapping) else {}
    min_points = max(1, _as_int(config.get("min_points"), default=3) or 3)
    low_state_window = max(1, _as_int(config.get("low_state_window_points"), default=min_points) or min_points)
    return _EndpointPolicy(
        min_drop_fraction_of_peak=max(
            0.0,
            _as_float(config.get("min_drop_fraction_of_peak", config.get("min_relative_drop"))) or 0.005,
        ),
        min_drop_absolute_load=_none_or_nonnegative_float(config.get("min_drop_absolute_load")),
        noise_floor_multiplier=_none_or_nonnegative_float(config.get("noise_floor_multiplier")),
        recovery_level_fraction_of_peak=_clamp_float(
            config.get("recovery_level_fraction_of_peak"),
            default=0.9,
            lower=0.0,
            upper=1.0,
        ),
        low_state_level_fraction_of_peak=_clamp_float(
            config.get("low_state_level_fraction_of_peak"),
            default=0.99,
            lower=0.0,
            upper=1.0,
        ),
        low_state_window_points=low_state_window,
        low_state_min_fraction=_clamp_float(
            config.get("low_state_min_fraction"),
            default=0.5,
            lower=0.0,
            upper=1.0,
        ),
        min_low_state_points=max(1, _as_int(config.get("min_low_state_points"), default=1) or 1),
        local_recovery_window_multiplier=max(
            1.0,
            _as_float(config.get("local_recovery_window_multiplier")) or 2.0,
        ),
        min_recovery_window_points=max(
            1,
            _as_int(config.get("min_recovery_window_points"), default=max(5, min_points)) or max(5, min_points),
        ),
        trough_to_recovery_window_points=max(
            1,
            _as_int(config.get("trough_to_recovery_window_points"), default=max(3, min_points * 2))
            or max(3, min_points * 2),
        ),
        recovery_amplitude_decisive_fraction_of_peak=_clamp_float(
            config.get("recovery_amplitude_decisive_fraction_of_peak"),
            default=0.95,
            lower=0.0,
            upper=1.0,
        ),
        recovery_slope_fraction=max(
            0.0,
            _as_float(config.get("recovery_slope_fraction")) or _RECOVERY_SLOPE_FRACTION,
        ),
        later_higher_relative_tolerance=max(
            0.0,
            _as_float(config.get("later_higher_relative_tolerance")) or 1e-4,
        ),
        later_higher_absolute_tolerance=max(
            0.0,
            _as_float(config.get("later_higher_absolute_tolerance")) or 0.0,
        ),
        significant_recovery_requires_higher_or_slope=_bool(
            config.get("significant_recovery_requires_higher_or_slope", True)
        ),
        sign_state_audit_policy=str(config.get("sign_state_audit_policy") or "diagnostic_veto_recovery"),
    )


def _endpoint_peak_candidates(
    y: list[float | None],
    blocks: list[dict[str, float | int | str | None]],
    *,
    start_index: int,
) -> list[dict[str, float | int | str | None]]:
    candidates: list[dict[str, float | int | str | None]] = []
    seen: set[int] = set()

    def add(candidate: dict[str, float | int | str | None]) -> None:
        peak = _as_int(candidate.get("peak_index"))
        if peak is None or peak in seen or peak < start_index or peak >= len(y):
            return
        if y[peak] is None:
            return
        candidates.append(candidate)
        seen.add(peak)

    for candidate in _post_start_peak_candidates(blocks, min_points=1):
        copy = dict(candidate)
        copy.setdefault("candidate_source", "sign_regime")
        add(copy)

    if start_index + 1 < len(y):
        start_value = y[start_index]
        next_value = y[start_index + 1]
        if start_value is not None and next_value is not None and next_value < start_value:
            add(
                {
                    "peak_index": start_index,
                    "pattern": "start -> -",
                    "candidate_source": "start_peak",
                    "decline_start_index": start_index,
                    "decline_end_index": start_index + 1,
                }
            )

    index = start_index + 1
    while index < len(y) - 1:
        current = y[index]
        if current is None:
            index += 1
            continue
        plateau_end = index
        while plateau_end + 1 < len(y) and _same_level(y[plateau_end + 1], current):
            plateau_end += 1
        next_value = y[plateau_end + 1] if plateau_end + 1 < len(y) else None
        previous_value = y[index - 1] if index - 1 >= 0 else None
        if (
            next_value is not None
            and next_value < current
            and (previous_value is None or current >= previous_value or _same_level(current, previous_value))
        ):
            add(
                {
                    "peak_index": plateau_end,
                    "pattern": "local_plateau_decline" if plateau_end > index else "local_peak_decline",
                    "candidate_source": "local_peak",
                    "decline_start_index": plateau_end,
                    "decline_end_index": plateau_end + 1,
                }
            )
        index = plateau_end + 1
    return sorted(candidates, key=lambda candidate: int(candidate["peak_index"]))


def _evaluate_endpoint_candidate(
    *,
    y: list[float | None],
    raw: list[float | None],
    domain: list[float | None] | None,
    blocks: list[dict[str, float | int | str | None]],
    candidate: dict[str, float | int | str | None],
    policy: _EndpointPolicy,
    start_index: int,
    run_id: str | None,
    candidate_number: int,
) -> dict[str, Any]:
    peak_index = int(candidate["peak_index"])
    peak_load = y[peak_index]
    candidate_id = f"{run_id or 'run'}:endpoint_candidate:{candidate_number:03d}"
    reference_block = _reference_block(blocks, candidate)
    domain_evidence = _domain_evidence(reference_block)
    reference_slope = domain_evidence["reference_rising_slope"]
    robust, robustness_reason = _candidate_peak_robust(y, peak_index, reference_block=reference_block)
    drop_threshold = _drop_threshold(peak_load, policy)
    first_drop_index = _first_drop_index(y, peak_index=peak_index, drop_threshold=drop_threshold)
    first_drop_load = y[first_drop_index] if first_drop_index is not None else None
    drop_abs = (
        float(peak_load) - float(first_drop_load)
        if peak_load is not None and first_drop_load is not None
        else None
    )
    drop_fraction = (
        drop_abs / float(peak_load)
        if drop_abs is not None and peak_load not in (None, 0.0)
        else None
    )
    recovery_level = float(peak_load or 0.0) * policy.recovery_level_fraction_of_peak
    low_state_level = float(peak_load or 0.0) * policy.low_state_level_fraction_of_peak
    low_state = _low_state_diagnostic(
        y,
        first_drop_index=first_drop_index,
        low_state_level=low_state_level,
        policy=policy,
    )
    trough_index, trough_load = _trough_after(y, start=first_drop_index)
    recovery = _recovery_diagnostic(
        y,
        peak_index=peak_index,
        first_drop_index=first_drop_index,
        trough_index=trough_index,
        trough_load=trough_load,
        recovery_level=recovery_level,
        reference_slope=reference_slope,
        policy=policy,
        start_index=start_index,
        peak_load=peak_load,
    )
    later_higher_index = _later_significant_higher_index(y, peak_index=peak_index, policy=policy)
    sign_state = _sign_state_diagnostic(raw, peak_index=peak_index, start_index=start_index)
    real_recovery = (
        bool(recovery["recovery_amplitude_seen"])
        and bool(recovery["recovery_locality_pass"])
        and bool(recovery["same_event_continuity_pass"])
        and (
            not policy.significant_recovery_requires_higher_or_slope
            or bool(recovery["recovery_slope_pass"])
            or bool(recovery["recovery_amplitude_decisive"])
            or later_higher_index is not None
        )
        and not (
            sign_state["sign_reversal_after_peak_seen"]
            and policy.sign_state_audit_policy == "diagnostic_veto_recovery"
        )
    )

    if not robust:
        decision = "review"
        reason = robustness_reason
    elif first_drop_index is None:
        decision = "rejected"
        reason = "no_meaningful_post_peak_drop"
    elif not low_state["sustained_non_recovered_state"]:
        decision = "rejected"
        reason = "drop_not_sustained_non_recovered"
    elif real_recovery:
        decision = "rejected"
        reason = "local_continuous_recovery_near_candidate_peak"
    else:
        decision = "accepted"
        if recovery["recovery_amplitude_seen"] and not recovery["recovery_locality_pass"]:
            reason = "accepted_later_recovery_too_far_or_unrelated"
        elif recovery["recovery_amplitude_seen"] and not recovery["same_event_continuity_pass"]:
            reason = "accepted_recovery_discontinuous_from_drop_event"
        elif recovery["recovery_amplitude_seen"]:
            reason = "accepted_recovery_not_significant_by_slope_or_higher_tolerance"
        else:
            reason = "accepted_no_recovery_amplitude_return"

    return {
        "candidate_id": candidate_id,
        "run_id": run_id,
        "candidate_peak_index": peak_index,
        "candidate_peak_load": peak_load,
        "candidate_pattern": candidate.get("pattern"),
        "candidate_source": candidate.get("candidate_source"),
        "candidate_peak_robust": robust,
        "peak_robustness_reason": robustness_reason,
        "domain_evidence_quality": domain_evidence["domain_evidence_quality"],
        "domain_evidence_reason": domain_evidence["domain_evidence_reason"],
        "meaningful_drop_seen": first_drop_index is not None,
        "first_drop_index": first_drop_index,
        "first_drop_load": first_drop_load,
        "drop_abs": drop_abs,
        "drop_fraction": drop_fraction,
        "drop_threshold": drop_threshold,
        "recovery_level_load": recovery_level,
        "low_state_level_load": low_state_level,
        **low_state,
        **recovery,
        "reference_rising_slope": reference_slope,
        "later_significant_higher_peak_seen": later_higher_index is not None,
        "later_significant_higher_peak_index": later_higher_index,
        "sign_state_diagnostic": sign_state,
        "candidate_final_decision": decision,
        "candidate_rejection_reason": reason,
    }


def _reference_block(
    blocks: list[dict[str, float | int | str | None]],
    candidate: dict[str, float | int | str | None],
) -> dict[str, float | int | str | None] | None:
    position = _as_int(candidate.get("rising_block_position"))
    if position is not None and 0 <= position < len(blocks):
        return blocks[position]
    peak_index = _as_int(candidate.get("peak_index"))
    if peak_index is None:
        return None
    for block in reversed(blocks):
        if block.get("regime") == "+" and _as_int(block.get("end_index")) == peak_index:
            return block
    return None


def _domain_evidence(block: dict[str, float | int | str | None] | None) -> dict[str, Any]:
    if block is None:
        return {
            "reference_rising_slope": None,
            "domain_evidence_quality": "not_available",
            "domain_evidence_reason": "candidate has no preceding rising block.",
        }
    domain_slope = _as_float(block.get("domain_slope"))
    point_slope = _as_float(block.get("point_slope"))
    domain_edges = _as_int(block.get("domain_edge_count"), default=0) or 0
    if domain_slope is not None and domain_slope > 0.0:
        return {
            "reference_rising_slope": domain_slope,
            "domain_evidence_quality": "valid_domain_slope",
            "domain_evidence_reason": "positive strain-domain slope used for reference loading branch.",
        }
    if point_slope is not None and point_slope > 0.0:
        reason = (
            "strain-domain evidence was present but not monotonic enough; point-index load slope used."
            if domain_edges > 0
            else "no strain-domain edges were available; point-index load slope used."
        )
        return {
            "reference_rising_slope": point_slope,
            "domain_evidence_quality": "point_index_fallback",
            "domain_evidence_reason": reason,
        }
    return {
        "reference_rising_slope": None,
        "domain_evidence_quality": "invalid",
        "domain_evidence_reason": "no positive reference loading slope was available.",
    }


def _candidate_peak_robust(
    y: list[float | None],
    peak_index: int,
    *,
    reference_block: dict[str, float | int | str | None] | None,
) -> tuple[bool, str]:
    peak = y[peak_index] if 0 <= peak_index < len(y) else None
    if peak is None:
        return False, "candidate peak has no numeric load."
    edge_count = _as_int(reference_block.get("edge_count"), default=0) if reference_block is not None else 0
    if edge_count is not None and edge_count >= 2:
        return True, "candidate has multi-edge loading-branch support."
    previous_value = y[peak_index - 1] if peak_index > 0 else None
    next_value = y[peak_index + 1] if peak_index + 1 < len(y) else None
    if previous_value is None:
        return True, "start-of-interval peak; robustness judged from post-peak evidence."
    if next_value is None:
        return False, "candidate peak has no post-peak point."
    if previous_value <= peak * 0.5 and next_value <= peak * 0.5:
        return False, "isolated spike: adjacent points are both below half the candidate peak."
    return True, "candidate has local support outside isolated-spike bounds."


def _drop_threshold(peak_load: float | None, policy: _EndpointPolicy) -> float:
    peak = max(0.0, float(peak_load or 0.0))
    values = [peak * policy.min_drop_fraction_of_peak]
    if policy.min_drop_absolute_load is not None:
        values.append(policy.min_drop_absolute_load)
    return max(values)


def _first_drop_index(
    y: list[float | None],
    *,
    peak_index: int,
    drop_threshold: float,
) -> int | None:
    peak = y[peak_index] if 0 <= peak_index < len(y) else None
    if peak is None:
        return None
    for index in range(peak_index + 1, len(y)):
        value = y[index]
        if value is not None and value <= peak - drop_threshold:
            return index
    return None


def _low_state_diagnostic(
    y: list[float | None],
    *,
    first_drop_index: int | None,
    low_state_level: float,
    policy: _EndpointPolicy,
) -> dict[str, Any]:
    if first_drop_index is None:
        return {
            "low_state_window_start_index": None,
            "low_state_window_end_index": None,
            "non_recovered_point_count": 0,
            "non_recovered_fraction": 0.0,
            "sustained_non_recovered_state": False,
        }
    window_end = min(len(y) - 1, first_drop_index + policy.low_state_window_points - 1)
    window = [value for value in y[first_drop_index:window_end + 1] if value is not None]
    count = sum(1 for value in window if float(value) < low_state_level)
    fraction = count / len(window) if window else 0.0
    sustained = count >= policy.min_low_state_points and fraction >= policy.low_state_min_fraction
    return {
        "low_state_window_start_index": first_drop_index,
        "low_state_window_end_index": window_end,
        "non_recovered_point_count": count,
        "non_recovered_fraction": fraction,
        "sustained_non_recovered_state": sustained,
    }


def _trough_after(y: list[float | None], *, start: int | None) -> tuple[int | None, float | None]:
    if start is None:
        return None, None
    best_index: int | None = None
    best_value: float | None = None
    for index in range(start, len(y)):
        value = y[index]
        if value is None:
            continue
        if best_value is None or value < best_value:
            best_index = index
            best_value = value
    return best_index, best_value


def _recovery_diagnostic(
    y: list[float | None],
    *,
    peak_index: int,
    peak_load: float | None,
    first_drop_index: int | None,
    trough_index: int | None,
    trough_load: float | None,
    recovery_level: float,
    reference_slope: float | None,
    policy: _EndpointPolicy,
    start_index: int,
) -> dict[str, Any]:
    below_recovery_index = None
    if first_drop_index is not None:
        for index in range(first_drop_index, len(y)):
            value = y[index]
            if value is not None and value < recovery_level:
                below_recovery_index = index
                break
    first_recovery_index = None
    first_recovery_load = None
    if below_recovery_index is not None:
        for index in range(below_recovery_index + 1, len(y)):
            value = y[index]
            if value is not None and value >= recovery_level:
                first_recovery_index = index
                first_recovery_load = value
                break
    if below_recovery_index is not None:
        trough_search_end = first_recovery_index if first_recovery_index is not None else len(y) - 1
        trough_index = None
        trough_load = None
        for index in range(below_recovery_index, trough_search_end + 1):
            value = y[index]
            if value is None:
                continue
            if trough_load is None or value < trough_load:
                trough_index = index
                trough_load = value
    max_recovery_distance = max(
        policy.min_recovery_window_points,
        _ceil_int(policy.local_recovery_window_multiplier * max(1, peak_index - start_index)),
    )
    peak_distance = (
        first_recovery_index - peak_index
        if first_recovery_index is not None
        else None
    )
    trough_distance = (
        first_recovery_index - trough_index
        if first_recovery_index is not None and trough_index is not None
        else None
    )
    recovery_slope = (
        (float(first_recovery_load) - float(trough_load)) / float(trough_distance)
        if first_recovery_load is not None
        and trough_load is not None
        and trough_distance not in (None, 0)
        else None
    )
    slope_threshold = (
        reference_slope * policy.recovery_slope_fraction
        if reference_slope is not None
        else None
    )
    slope_pass = (
        recovery_slope is not None
        and slope_threshold is not None
        and recovery_slope >= slope_threshold
    )
    decisive_amplitude = (
        first_recovery_load is not None
        and peak_load is not None
        and first_recovery_load < peak_load
        and first_recovery_load >= peak_load * policy.recovery_amplitude_decisive_fraction_of_peak
    )
    return {
        "recovery_amplitude_seen": first_recovery_index is not None,
        "first_recovery_index": first_recovery_index,
        "first_recovery_load": first_recovery_load,
        "recovery_distance_from_peak_points": peak_distance,
        "max_recovery_distance_points": max_recovery_distance,
        "recovery_locality_pass": peak_distance is not None and peak_distance <= max_recovery_distance,
        "trough_index": trough_index,
        "trough_load": trough_load,
        "recovery_distance_from_trough_points": trough_distance,
        "same_event_continuity_pass": (
            trough_distance is not None and trough_distance <= policy.trough_to_recovery_window_points
        ),
        "recovery_slope": recovery_slope,
        "recovery_slope_threshold": slope_threshold,
        "recovery_slope_pass": slope_pass,
        "recovery_amplitude_decisive": decisive_amplitude,
    }


def _later_significant_higher_index(
    y: list[float | None],
    *,
    peak_index: int,
    policy: _EndpointPolicy,
) -> int | None:
    peak = y[peak_index] if 0 <= peak_index < len(y) else None
    if peak is None:
        return None
    tolerance = max(
        policy.later_higher_absolute_tolerance,
        abs(float(peak)) * policy.later_higher_relative_tolerance,
    )
    for index in range(peak_index + 1, len(y)):
        value = y[index]
        if value is not None and value > peak + tolerance:
            return index
    return None


def _sign_state_diagnostic(
    raw: list[float | None],
    *,
    peak_index: int,
    start_index: int,
) -> dict[str, Any]:
    peak_sign = _sign(raw[peak_index]) if 0 <= peak_index < len(raw) else 0
    first_reversal = None
    for index in range(max(start_index, peak_index + 1), len(raw)):
        sign = _sign(raw[index])
        if peak_sign and sign and sign != peak_sign:
            first_reversal = index
            break
    return {
        "peak_sign": peak_sign,
        "sign_reversal_after_peak_seen": first_reversal is not None,
        "first_sign_reversal_index": first_reversal,
    }


def _none_or_nonnegative_float(value: Any) -> float | None:
    numeric = _as_float(value)
    return max(0.0, numeric) if numeric is not None else None


def _clamp_float(value: Any, *, default: float, lower: float, upper: float) -> float:
    numeric = _as_float(value)
    if numeric is None:
        numeric = default
    return max(lower, min(upper, numeric))


def _ceil_int(value: float) -> int:
    integer = int(value)
    return integer if value == integer else integer + 1


def _sign(value: float | None) -> int:
    if value is None or value == 0:
        return 0
    return 1 if value > 0 else -1


def _candidate_has_non_recovering_decline(
    y: list[float | None],
    blocks: list[dict[str, float | int | str | None]],
    *,
    candidate: dict[str, float | int | str | None],
    min_points: int,
) -> bool:
    peak_index = int(candidate["peak_index"])
    if _later_exceeds_peak(y, peak_index=peak_index):
        return False
    decline_position = int(candidate["decline_block_position"])
    reference_block = blocks[int(candidate["rising_block_position"])]
    if _block_positive_slope(reference_block) is None:
        return False
    sustained_fall_seen = False
    for block in blocks[decline_position:]:
        if block.get("regime") == "-" and int(block["edge_count"]) >= min_points:
            sustained_fall_seen = True
            break
    if not sustained_fall_seen:
        return False
    for block in blocks[decline_position + 1 :]:
        if (
            block.get("regime") == "+"
            and int(block["edge_count"]) >= min_points
            and _is_comparable_recovery_slope(reference_block, block)
        ):
            return False
    return True


def _later_exceeds_peak(y: list[float | None], *, peak_index: int) -> bool:
    peak = y[peak_index] if 0 <= peak_index < len(y) else None
    if peak is None:
        return False
    for value in y[peak_index + 1 :]:
        if value is not None and value > peak and not _same_level(value, peak):
            return True
    return False


def _is_comparable_recovery_slope(
    reference_block: dict[str, float | int | str | None],
    recovery_block: dict[str, float | int | str | None],
) -> bool:
    reference_slope = _block_positive_slope(reference_block)
    recovery_slope = _block_positive_slope(recovery_block)
    if reference_slope is None or recovery_slope is None:
        return False
    return recovery_slope >= reference_slope * _RECOVERY_SLOPE_FRACTION


def _block_positive_slope(block: dict[str, float | int | str | None]) -> float | None:
    domain_slope = _as_float(block.get("domain_slope"))
    if domain_slope is not None and domain_slope > 0.0:
        return domain_slope
    domain_edges = _as_int(block.get("domain_edge_count"), default=0) or 0
    if domain_edges > 0:
        return None
    point_slope = _as_float(block.get("point_slope"))
    if point_slope is not None and point_slope > 0.0:
        return point_slope
    return None


def _blocks_touch(
    left: dict[str, float | int | str | None] | None,
    right: dict[str, float | int | str | None] | None,
) -> bool:
    if left is None or right is None:
        return False
    return int(left["end_index"]) == int(right["start_index"])


def _delta_regime(delta: float) -> str:
    if isclose(delta, 0.0, rel_tol=1e-12, abs_tol=1e-12):
        return "0"
    return "+" if delta > 0 else "-"


def _max_abs_point_from(
    y: list[float | None],
    *,
    start_index: int,
    end_index: int | None = None,
) -> tuple[int, float] | None:
    best: tuple[int, float] | None = None
    stop = min(len(y) - 1, end_index) if end_index is not None else len(y) - 1
    for index in range(start_index, stop + 1):
        value = y[index]
        if value is None:
            continue
        if best is None or value > best[1]:
            best = (index, value)
    return best


def _abs_delta(y: list[float | None], index: int) -> float | None:
    if index < 0 or index + 1 >= len(y):
        return None
    current = y[index]
    next_value = y[index + 1]
    if current is None or next_value is None:
        return None
    return next_value - current


def _domain_delta(domain: list[float | None] | None, index: int) -> float | None:
    if domain is None or index < 0 or index + 1 >= len(domain):
        return None
    current = domain[index]
    next_value = domain[index + 1]
    if current is None or next_value is None:
        return None
    return next_value - current


def _abs_float(value: Any) -> float | None:
    numeric = _as_float(value)
    return abs(float(numeric)) if numeric is not None else None


def _same_level(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    return left == right or isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _slope_break_pre_negative_resolution(
    *,
    load: list[Any] | None,
    strain: list[Any] | None,
    config: Mapping[str, Any],
    sustained_config: Mapping[str, Any] | None = None,
) -> _EndResolution:
    warnings: list[str] = []
    max_point = _max_abs_point(load)
    if load is None or max_point is None:
        return _EndResolution(
            end_index=None,
            reason="slope-break endpoint could not be resolved.",
            warnings=("Load series is required for slope_break_pre_negative endpoint policy.",),
        )
    max_load = abs(float(max_point[1]))
    if max_load == 0:
        return _EndResolution(
            end_index=max_point[0],
            reason="maximum absolute load selected because slope-break search has zero load scale.",
            warnings=("Slope-break endpoint fallback used because maximum absolute load is zero.",),
        )

    slope_domain = str(config.get("slope_domain") or "point_index")
    min_load_fraction = _as_float(config.get("min_load_fraction_of_max"))
    min_load_fraction = 0.1 if min_load_fraction is None else max(0.0, min_load_fraction)
    min_relative_drop = _as_float(config.get("min_relative_load_drop"))
    min_relative_drop = 0.0 if min_relative_drop is None else max(0.0, min_relative_drop)
    drop_threshold = max_load * min_relative_drop
    min_negative_domain_step = _as_float(config.get("min_negative_domain_step"))
    min_negative_domain_step = 0.0 if min_negative_domain_step is None else max(0.0, min_negative_domain_step)
    detect_strain_collapse = _bool(config.get("detect_strain_collapse", True))
    min_strain_before_collapse = _as_float(config.get("min_strain_before_collapse"))
    min_strain_before_collapse = 0.0002 if min_strain_before_collapse is None else max(0.0, min_strain_before_collapse)
    min_relative_strain_collapse = _as_float(config.get("min_relative_strain_collapse"))
    min_relative_strain_collapse = (
        0.25
        if min_relative_strain_collapse is None
        else max(0.0, min(1.0, min_relative_strain_collapse))
    )
    min_relative_curvature_change = _as_float(config.get("min_relative_curvature_change"))
    min_relative_curvature_change = (
        0.5
        if min_relative_curvature_change is None
        else max(0.0, min(1.0, min_relative_curvature_change))
    )
    pre_reversal_domain_jump_multiplier = _as_float(config.get("pre_reversal_domain_jump_multiplier"))
    pre_reversal_domain_jump_multiplier = (
        5.0
        if pre_reversal_domain_jump_multiplier is None
        else max(1.0, pre_reversal_domain_jump_multiplier)
    )
    lookback_points = _as_int(config.get("prebreak_lookback_points"), default=8)
    lookback_points = max(1, lookback_points)
    use_prebreak_curvature = _bool(config.get("use_prebreak_curvature", True))

    segments = _slope_segments(load=load, strain=strain, slope_domain=slope_domain)
    if not segments and slope_domain != "point_index":
        warnings.append(f"Slope domain '{slope_domain}' had no usable one-step segments; falling back to point_index.")
        slope_domain = "point_index"
        segments = _slope_segments(load=load, strain=strain, slope_domain=slope_domain)
    if not segments:
        return _EndResolution(
            end_index=max_point[0],
            reason="maximum absolute load selected because no one-step slope segments were usable.",
            warnings=tuple(warnings + ["Slope-break endpoint fallback used because no slopes were usable."]),
        )

    strain_collapse = _strain_collapse_segment(
        segments=segments,
        enabled=detect_strain_collapse,
        min_strain_before_collapse=min_strain_before_collapse,
        min_relative_strain_collapse=min_relative_strain_collapse,
        min_negative_domain_step=min_negative_domain_step,
    )
    sustained = _sustained_decline_resolution(
        load=load,
        max_load=max_load,
        min_load_fraction=min_load_fraction,
        config=sustained_config or {},
    )

    first_negative = None
    minimum_start_load = max_load * min_load_fraction
    for segment in segments:
        start_load = abs(float(segment["load_start"]))
        if start_load < minimum_start_load:
            continue
        trigger = _negative_slope_trigger(
            segment,
            slope_domain=slope_domain,
            drop_threshold=drop_threshold,
            min_negative_domain_step=min_negative_domain_step,
        )
        if trigger:
            first_negative = dict(segment)
            first_negative["negative_slope_trigger"] = trigger
            break
    if strain_collapse is not None and (
        first_negative is None or int(strain_collapse["start_index"]) <= int(first_negative["start_index"])
    ):
        first_negative = strain_collapse
    if first_negative is None:
        if sustained is not None:
            return _EndResolution(
                end_index=int(sustained["endpoint_index"]),
                reason="sustained post-peak decline selected as analysis endpoint.",
                sustained_decline=sustained,
                warnings=tuple(warnings),
            )
        return _EndResolution(
            end_index=max_point[0],
            reason="maximum absolute load selected because no significant negative one-step slope was detected.",
            warnings=tuple(warnings + ["Slope-break endpoint fallback used because no significant negative slope was detected."]),
        )

    if sustained is not None and int(sustained["event_index"]) < int(first_negative["start_index"]):
        return _EndResolution(
            end_index=int(sustained["endpoint_index"]),
            reason="sustained post-peak decline selected as analysis endpoint.",
            sustained_decline=sustained,
            warnings=tuple(warnings),
        )

    negative_trigger = str(first_negative.get("negative_slope_trigger") or "")
    preceding_domain_jump = (
        _preceding_positive_domain_step(
            segments=segments,
            first_negative=first_negative,
            min_domain_step=min_negative_domain_step,
            jump_multiplier=pre_reversal_domain_jump_multiplier,
        )
        if negative_trigger == "domain_reversal"
        else None
    )
    use_curvature_for_endpoint = use_prebreak_curvature and negative_trigger not in {"load_drop", "strain_collapse"} and (
        negative_trigger != "domain_reversal" or preceding_domain_jump is not None
    )
    include_trigger_in_curvature = False
    curvature = _prebreak_curvature_segment(
        segments=segments,
        first_negative=first_negative,
        lookback_points=lookback_points,
        min_relative_change=min_relative_curvature_change,
        include_first_negative=include_trigger_in_curvature,
    ) if use_curvature_for_endpoint or include_trigger_in_curvature else None
    if curvature:
        end_index = int(curvature["start_index"])
        reason = (
            "slope-break endpoint selected from the largest negative one-step slope change "
            "before the first significant negative force slope."
        )
    elif preceding_domain_jump is not None:
        end_index = int(preceding_domain_jump["start_index"])
        reason = "endpoint selected before a large positive strain-domain jump followed by reversal."
    elif negative_trigger == "load_drop":
        end_index = int(first_negative["start_index"])
        reason = "first significant one-step load drop selected as analysis endpoint."
    elif negative_trigger == "domain_reversal":
        end_index = int(first_negative["start_index"])
        reason = "first significant negative strain-domain reversal selected as analysis endpoint."
    elif negative_trigger == "strain_collapse":
        end_index = int(first_negative["start_index"])
        reason = "first major strain-domain collapse selected as analysis endpoint."
    else:
        end_index = int(first_negative["start_index"])
        reason = "first significant negative one-step force slope selected as analysis endpoint."
    first_negative_event_index = (
        first_negative["start_index"]
    )
    return _EndResolution(
        end_index=end_index,
        reason=reason,
        first_negative_slope={
            "index": first_negative_event_index,
            "segment_start_index": first_negative["start_index"],
            "segment_end_index": first_negative["end_index"],
            "slope": first_negative["slope"],
            "delta_load": first_negative["delta_load"],
            "domain_delta": first_negative.get("domain_delta"),
            "negative_slope_trigger": negative_trigger,
            "slope_domain": slope_domain,
            "min_load_fraction_of_max": min_load_fraction,
            "min_relative_load_drop": min_relative_drop,
            "min_negative_domain_step": min_negative_domain_step,
            "min_strain_before_collapse": first_negative.get("min_strain_before_collapse"),
            "min_relative_strain_collapse": first_negative.get("min_relative_strain_collapse"),
        },
        prebreak_curvature={
            "index": curvature["start_index"],
            "segment_end_index": curvature["end_index"],
            "slope": curvature["slope"],
            "slope_change": curvature["slope_change"],
            "slope_domain": slope_domain,
            "lookback_points": lookback_points,
            "min_relative_curvature_change": min_relative_curvature_change,
            "selection": curvature.get("selection"),
        } if curvature else None,
        warnings=tuple(warnings),
    )


def _slope_segments(
    *,
    load: list[Any] | None,
    strain: list[Any] | None,
    slope_domain: str,
) -> list[dict[str, Any]]:
    if load is None:
        return []
    segments: list[dict[str, Any]] = []
    for index in range(0, max(0, len(load) - 1)):
        y0 = _as_float(load[index])
        y1 = _as_float(load[index + 1])
        if y0 is None or y1 is None:
            continue
        force0 = abs(y0)
        force1 = abs(y1)
        if slope_domain == "strain":
            x0 = _value_at(strain, index)
            x1 = _value_at(strain, index + 1)
            if x0 is None or x1 is None:
                continue
            dx = x1 - x0
        else:
            x0 = float(index)
            x1 = float(index + 1)
            dx = 1.0
        if dx == 0:
            continue
        delta_load = force1 - force0
        segments.append(
            {
                "position": len(segments),
                "start_index": index,
                "end_index": index + 1,
                "load_start": y0,
                "load_end": y1,
                "force_start": force0,
                "force_end": force1,
                "delta_load": delta_load,
                "slope": delta_load / dx,
                "domain_start": x0,
                "domain_end": x1,
                "domain_delta": dx,
            }
        )
    return segments


def _strain_collapse_segment(
    *,
    segments: list[dict[str, Any]],
    enabled: bool,
    min_strain_before_collapse: float,
    min_relative_strain_collapse: float,
    min_negative_domain_step: float,
) -> dict[str, Any] | None:
    if not enabled:
        return None
    for segment in segments:
        domain_start = _as_float(segment.get("domain_start"))
        domain_delta = _as_float(segment.get("domain_delta"))
        if domain_start is None or domain_delta is None:
            continue
        if domain_start < min_strain_before_collapse or domain_delta >= 0:
            continue
        drop = abs(domain_delta)
        threshold = max(min_negative_domain_step, abs(domain_start) * min_relative_strain_collapse)
        if drop < threshold:
            continue
        selected = dict(segment)
        selected["negative_slope_trigger"] = "strain_collapse"
        selected["strain_drop"] = drop
        selected["strain_drop_threshold"] = threshold
        selected["min_strain_before_collapse"] = min_strain_before_collapse
        selected["min_relative_strain_collapse"] = min_relative_strain_collapse
        return selected
    return None


def _negative_slope_trigger(
    segment: dict[str, Any],
    *,
    slope_domain: str,
    drop_threshold: float,
    min_negative_domain_step: float,
) -> str | None:
    delta_load = float(segment["delta_load"])
    if delta_load <= -drop_threshold:
        return "load_drop"
    if slope_domain != "point_index":
        domain_delta = float(segment.get("domain_delta") or 0.0)
        if domain_delta < 0 and abs(domain_delta) >= min_negative_domain_step:
            return "domain_reversal"
    return None


def _preceding_positive_domain_step(
    *,
    segments: list[dict[str, Any]],
    first_negative: dict[str, Any],
    min_domain_step: float,
    jump_multiplier: float,
) -> dict[str, Any] | None:
    position = int(first_negative["position"])
    if position <= 0:
        return None
    previous = segments[position - 1]
    domain_delta = float(previous.get("domain_delta") or 0.0)
    if domain_delta <= 0 or abs(domain_delta) < min_domain_step:
        return None
    recent_positive_steps = [
        abs(float(segment.get("domain_delta") or 0.0))
        for segment in segments[max(0, position - 8) : position - 1]
        if float(segment.get("domain_delta") or 0.0) > 0
    ]
    if not recent_positive_steps:
        return None
    baseline = _median(recent_positive_steps)
    if baseline > 0 and abs(domain_delta) >= max(min_domain_step, baseline * jump_multiplier):
        return previous
    return None


def _prebreak_curvature_segment(
    *,
    segments: list[dict[str, Any]],
    first_negative: dict[str, Any],
    lookback_points: int,
    min_relative_change: float = 0.5,
    include_first_negative: bool = False,
) -> dict[str, Any] | None:
    position = int(first_negative["position"])
    start = max(1, position - lookback_points)
    candidates: list[dict[str, Any]] = []
    stop = position + 1 if include_first_negative else position
    for current_position in range(start, stop):
        current = dict(segments[current_position])
        previous = segments[current_position - 1]
        current["slope_change"] = float(current["slope"]) - float(previous["slope"])
        candidates.append(current)
    negative_changes = [candidate for candidate in candidates if float(candidate["slope_change"]) < 0]
    if negative_changes:
        max_negative_change = max(abs(float(item["slope_change"])) for item in negative_changes)
        threshold = max_negative_change * min_relative_change
        substantial = [
            item for item in negative_changes
            if abs(float(item["slope_change"])) >= threshold
        ]
        selected = max(substantial or negative_changes, key=lambda item: int(item["start_index"]))
        selected["selection"] = "latest_substantial_negative_slope_change"
        selected["max_negative_slope_change"] = max_negative_change
        selected["min_relative_curvature_change"] = min_relative_change
        return selected
    if not candidates:
        return None
    selected = max(candidates, key=lambda item: abs(float(item["slope_change"])))
    selected["selection"] = "largest_available_slope_change"
    selected["min_relative_curvature_change"] = min_relative_change
    return selected


def _slope_break_events(
    *,
    resolution: _EndResolution,
    load: list[Any] | None,
    unit: str | None,
    domain: str,
    time_key: str,
    time: list[Any] | None,
    strain_key: str,
    strain: list[Any] | None,
) -> list[ExperimentBoundaryEvent]:
    events: list[ExperimentBoundaryEvent] = []
    first_negative = resolution.first_negative_slope
    if first_negative:
        index = _as_int(first_negative.get("index"))
        trigger = str(first_negative.get("negative_slope_trigger") or "")
        first_note = (
            "First major strain-domain collapse."
            if trigger == "strain_collapse"
            else "First significant negative one-step force slope."
        )
        events.append(
            ExperimentBoundaryEvent(
                event_id="first_negative_slope",
                index=index,
                value=_value_at(load, index),
                unit=unit,
                domain=domain,
                domain_value=_domain_value_for_index(domain, time_key, time, strain_key, strain, index),
                diagnostic_only=False,
                notes=(
                    first_note,
                    f"slope={first_negative.get('slope')}",
                    f"delta_load={first_negative.get('delta_load')}",
                    f"domain_delta={first_negative.get('domain_delta')}",
                    f"negative_slope_trigger={first_negative.get('negative_slope_trigger')}",
                    f"slope_domain={first_negative.get('slope_domain')}",
                    f"min_relative_load_drop={first_negative.get('min_relative_load_drop')}",
                    f"min_negative_domain_step={first_negative.get('min_negative_domain_step')}",
                    f"min_strain_before_collapse={first_negative.get('min_strain_before_collapse')}",
                    f"min_relative_strain_collapse={first_negative.get('min_relative_strain_collapse')}",
                ),
            )
        )
    curvature = resolution.prebreak_curvature
    if curvature:
        index = _as_int(curvature.get("index"))
        events.append(
            ExperimentBoundaryEvent(
                event_id="prebreak_curvature",
                index=index,
                value=_value_at(load, index),
                unit=unit,
                domain=domain,
                domain_value=_domain_value_for_index(domain, time_key, time, strain_key, strain, index),
                diagnostic_only=False,
                notes=(
                    "Largest negative one-step slope change before first significant negative slope.",
                    f"slope_change={curvature.get('slope_change')}",
                    f"slope={curvature.get('slope')}",
                    f"slope_domain={curvature.get('slope_domain')}",
                    f"lookback_points={curvature.get('lookback_points')}",
                    f"selection={curvature.get('selection')}",
                    f"min_relative_curvature_change={curvature.get('min_relative_curvature_change')}",
                ),
            )
        )
    sustained = resolution.sustained_decline
    if sustained:
        index = _as_int(sustained.get("event_index"))
        notes = tuple(
            item
            for item in (
                "Sustained post-peak load decline selected the analysis endpoint.",
                f"endpoint_index={sustained.get('endpoint_index')}",
                f"peak_index={sustained.get('peak_index')}",
                f"peak_load={sustained.get('peak_load')}",
                f"min_points={sustained.get('min_points')}",
                f"min_relative_drop={sustained.get('min_relative_drop')}"
                if sustained.get("min_relative_drop") is not None
                else "",
                f"use_as={sustained.get('use_as')}",
                f"selection={sustained.get('selection')}" if sustained.get("selection") else "",
                f"decline_start_index={sustained.get('decline_start_index')}"
                if sustained.get("decline_start_index") is not None
                else "",
                f"decline_end_index={sustained.get('decline_end_index')}"
                if sustained.get("decline_end_index") is not None
                else "",
                f"recovery_check={sustained.get('recovery_check')}" if sustained.get("recovery_check") else "",
            )
            if item
        )
        events.append(
            ExperimentBoundaryEvent(
                event_id="sustained_post_peak_decline",
                index=index,
                value=_value_at(load, index),
                unit=unit,
                domain=domain,
                domain_value=_domain_value_for_index(domain, time_key, time, strain_key, strain, index),
                diagnostic_only=False,
                notes=notes,
            )
        )
    return events


def _series_length(*series_items: list[Any] | None) -> int:
    return max((len(series) for series in series_items if series is not None), default=0)


def _signal_window_load_scale(
    *,
    load: list[Any] | None,
    gate_window: Mapping[str, Any] | None,
    gate_record: Mapping[str, Any] | None,
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    routing = gate_record.get("report_routing") if isinstance(gate_record, Mapping) else None
    routing = routing if isinstance(routing, Mapping) else {}
    payload: dict[str, Any] = {
        "schema_id": "method.signal_window_load_scale.v0_1",
        "gate_present": gate_record is not None,
        "gate_window_present": gate_window is not None,
        "gate_routing_state": routing.get("state"),
        "gate_routing_severity": routing.get("severity"),
        "routing_severity": routing.get("severity") or "none",
        "reason": routing.get("reason") or "No signal-window load-scale guard was required.",
    }
    if load is None or gate_window is None:
        return payload
    raw_peak = _max_abs_point(load)
    gate_peak = _max_abs_point_in_interval(
        load,
        start_index=_as_int(gate_window.get("start_index")),
        end_index=_as_int(gate_window.get("end_index")),
        include_endpoint=True,
    )
    config = config if isinstance(config, Mapping) else {}
    raw_fraction = _as_float(config.get("min_gate_peak_fraction_of_full_run_max"))
    min_fraction = (
        _DEFAULT_MIN_GATE_PEAK_FRACTION_OF_FULL_RUN_MAX
        if raw_fraction is None
        else max(0.0, min(1.0, raw_fraction))
    )
    raw_load = abs(float(raw_peak[1])) if raw_peak is not None else None
    gate_load = abs(float(gate_peak[1])) if gate_peak is not None else None
    ratio = gate_load / raw_load if raw_load not in (None, 0.0) and gate_load is not None else None
    payload.update(
        {
            "raw_full_run_peak_index": raw_peak[0] if raw_peak is not None else None,
            "raw_full_run_peak_load": raw_load,
            "gate_window_peak_index": gate_peak[0] if gate_peak is not None else None,
            "gate_window_peak_load": gate_load,
            "gate_to_full_run_peak_fraction": ratio,
            "min_gate_peak_fraction_of_full_run_max": min_fraction,
            "gate_peak_scale_floor": raw_load * min_fraction if raw_load is not None else None,
        }
    )
    if ratio is not None and ratio < min_fraction:
        payload["routing_severity"] = "review"
        payload["reason"] = (
            "Signal gate window peak is below the configured full-run load-scale floor; "
            "boundary output requires scientist review."
        )
    return payload


def _gate_record(run: Any, key: str) -> dict[str, Any] | None:
    if not key:
        return None
    value = run.scalars.get(key)
    if value is None:
        value = run.metadata.get(key)
    return dict(value) if isinstance(value, Mapping) else None


def _gate_window(gate_record: Mapping[str, Any] | None, *, series_length: int) -> dict[str, int] | None:
    if not isinstance(gate_record, Mapping):
        return None
    window = gate_record.get("coherent_window")
    if not isinstance(window, Mapping):
        return None
    start = _as_int(window.get("start_index"))
    end = _as_int(window.get("end_index"))
    if start is None or end is None or series_length <= 0:
        return None
    start = max(0, min(series_length - 1, start))
    end = max(start, min(series_length - 1, end))
    return {"start_index": start, "end_index": end}


def _gate_end_index(gate_window: Mapping[str, Any] | None) -> int | None:
    if not isinstance(gate_window, Mapping):
        return None
    return _as_int(gate_window.get("end_index"))


def _series_end_limit(series: list[Any], *, start_index: int, gate_end_index: int | None) -> int:
    default_end = len(series) - 1
    if gate_end_index is None:
        return default_end
    return max(start_index, min(default_end, int(gate_end_index)))


def _windowed_values(
    values: list[float | None] | None,
    *,
    start_index: int,
    end_index: int,
) -> list[float | None]:
    if values is None:
        return []
    return [
        value if start_index <= index <= end_index else None
        for index, value in enumerate(values)
    ]


def _max_abs_point(series: list[Any] | None) -> tuple[int, float] | None:
    if series is None:
        return None
    values: list[tuple[int, float]] = []
    for index, value in enumerate(series):
        numeric = _as_float(value)
        if numeric is not None:
            values.append((index, numeric))
    if not values:
        return None
    return max(values, key=lambda item: abs(item[1]))


def _max_abs_point_in_interval(
    series: list[Any] | None,
    *,
    start_index: int | None,
    end_index: int | None,
    include_endpoint: bool,
) -> tuple[int, float] | None:
    if series is None or start_index is None or end_index is None:
        return None
    stop = end_index + 1 if include_endpoint else end_index
    start = max(0, start_index)
    stop = min(len(series), max(start, stop))
    values: list[tuple[int, float]] = []
    for index in range(start, stop):
        numeric = _as_float(series[index])
        if numeric is not None:
            values.append((index, numeric))
    if not values:
        return None
    best = values[0]
    for item in values[1:]:
        current_abs = abs(item[1])
        best_abs = abs(best[1])
        if current_abs > best_abs or isclose(current_abs, best_abs, rel_tol=1e-12, abs_tol=1e-12):
            best = item
    return best


def _domain_values(
    *,
    time_key: str,
    time: list[Any] | None,
    strain_key: str,
    strain: list[Any] | None,
    start_index: int | None,
    end_index: int | None,
) -> tuple[str, float | None, float | None]:
    if time:
        return time_key, _value_at(time, start_index), _value_at(time, end_index)
    if strain:
        return strain_key, _value_at(strain, start_index), _value_at(strain, end_index)
    return "point_index", _as_float(start_index), _as_float(end_index)


def _domain_value_for_index(
    domain: str,
    time_key: str,
    time: list[Any] | None,
    strain_key: str,
    strain: list[Any] | None,
    index: int | None,
) -> float | None:
    if domain == time_key:
        return _value_at(time, index)
    if domain == strain_key:
        return _value_at(strain, index)
    return _as_float(index)


def _value_at(series: list[Any] | None, index: int | None) -> float | None:
    if series is None or index is None or index < 0 or index >= len(series):
        return None
    return _as_float(series[index])


def _sustained_decline_resolution(
    *,
    load: list[Any] | None,
    max_load: float,
    min_load_fraction: float,
    config: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not _bool(config.get("enabled", False)):
        return None
    use_as = str(config.get("use_as") or "diagnostic_only")
    if use_as not in {"endpoint", "analysis_endpoint", "terminal_event"}:
        return None
    if load is None or max_load == 0:
        return None
    min_points = max(1, _as_int(config.get("min_points")) or 3)
    min_relative_drop = _as_float(config.get("min_relative_drop"))
    min_relative_drop = 0.005 if min_relative_drop is None else max(0.0, min_relative_drop)
    minimum_peak = abs(max_load) * max(0.0, min_load_fraction)
    peak_index: int | None = None
    peak_load = 0.0
    numeric = [_as_float(value) for value in load]
    for index, value in enumerate(numeric):
        if value is None:
            continue
        abs_value = abs(float(value))
        if peak_index is None or abs_value > peak_load:
            peak_index = index
            peak_load = abs_value
        if peak_index is None or peak_load < minimum_peak or index <= peak_index:
            continue
        window = numeric[index : index + min_points]
        if len(window) < min_points or any(item is None for item in window):
            continue
        threshold = peak_load * (1.0 - min_relative_drop)
        if all(abs(float(item)) <= threshold for item in window if item is not None):
            return {
                "endpoint_index": peak_index,
                "event_index": index,
                "peak_index": peak_index,
                "peak_load": peak_load,
                "min_points": min_points,
                "min_relative_drop": min_relative_drop,
                "use_as": use_as,
            }
    return None


def _sustained_decline_event(
    *,
    load: list[Any] | None,
    end_index: int | None,
    max_load: float | None,
    unit: str | None,
    domain: str,
    domain_series: list[Any] | None,
    config: Mapping[str, Any],
) -> ExperimentBoundaryEvent | None:
    if not _bool(config.get("enabled", False)):
        return None
    if load is None or end_index is None or max_load in (None, 0):
        return None
    min_points = max(1, int(config.get("min_points") or 3))
    min_relative_drop = float(config.get("min_relative_drop") or 0.005)
    threshold = abs(float(max_load)) * (1.0 - min_relative_drop)
    for index in range(end_index + 1, max(end_index + 1, len(load) - min_points + 1)):
        window = [_as_float(value) for value in load[index : index + min_points]]
        if len(window) < min_points or any(value is None for value in window):
            continue
        if all(abs(float(value)) <= threshold for value in window if value is not None):
            return ExperimentBoundaryEvent(
                event_id="sustained_post_peak_decline",
                index=index,
                value=_as_float(load[index]),
                unit=unit,
                domain=domain,
                domain_value=_value_at(domain_series, index),
                diagnostic_only=True,
                notes=(
                    "Sustained post-peak load decline detected.",
                    f"min_points={min_points}",
                    f"min_relative_drop={min_relative_drop}",
                    f"use_as={config.get('use_as') or 'diagnostic_only'}",
                ),
            )
    return None


def _materialize_bounded_series(
    run: Any,
    start_index: int,
    end_index: int,
    include_endpoint: bool,
) -> dict[str, str]:
    stop = end_index + 1 if include_endpoint else end_index
    stop = max(start_index, stop)
    refs: dict[str, str] = {}
    existing = list(run.series.items())
    for name, values in existing:
        if name.endswith("_bounded") or name == "point_index_bounded":
            continue
        bounded_name = f"{name}_bounded"
        run.series[bounded_name] = list(values[start_index:stop])
        run.units[bounded_name] = run.units.get(name)
        refs[name] = bounded_name
    run.series["point_index_bounded"] = list(range(start_index, stop))
    run.units["point_index_bounded"] = "index"
    refs["point_index"] = "point_index_bounded"
    return refs


def _event_payload(events: list[ExperimentBoundaryEvent], event_id: str) -> dict[str, Any] | None:
    for event in events:
        if event.event_id == event_id:
            return event.to_dict()
    return None


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _as_abs_float(value: Any) -> float | None:
    number = _as_float(value)
    return abs(float(number)) if number is not None else None


def _as_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
