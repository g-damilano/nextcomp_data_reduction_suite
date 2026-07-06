from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


DEFAULT_POLICY: dict[str, Any] = {
    "schema_id": "method.experiment_signal_gate_policy.v0_1",
    "min_coherent_numeric_points": 4,
    "min_peak_fraction_of_series_max": 0.05,
    "post_drop_scan_points": 8,
    "min_drop_fraction_of_peak": 0.005,
    "later_higher_relative_tolerance": 0.0001,
    "domain_reversal_min_delta": 1e-9,
    "invalid_cluster_min_points": 2,
    "implausible_tail_jump_fraction_of_peak": 2.0,
    "artificial_plateau_min_points": 3,
    "loading_onset_fraction_of_peak": 0.05,
    "low_load_tail_fraction_of_peak": 0.20,
    "low_load_tail_min_points": 3,
    "low_load_tail_min_reference_peak_fraction_of_full_run_max": 0.10,
    "domain_jump_step_multiplier": 8.0,
    "domain_jump_span_fraction": 0.20,
    "disconnected_fragment_load_fraction_of_peak": 0.50,
    "disconnected_fragment_min_points": 5,
    "late_restart_jump_fraction_of_peak": 0.05,
    "late_restart_lookback_points": 15,
}


class GateExperimentSignalOperation(Operation):
    operation_id = "gate_experiment_signal"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        inputs = step.get("inputs", {})
        inputs = inputs if isinstance(inputs, Mapping) else {}
        parameters = step.get("parameters", {})
        parameters = parameters if isinstance(parameters, Mapping) else {}
        output = str(step.get("output") or "experiment_signal_gate")
        load_key = str(inputs.get("load") or "load_N")
        time_key = str(inputs.get("time") or "time_s")
        strain_key = str(inputs.get("strain") or "mean_strain")
        policy = _policy(parameters)
        results: list[OperationResult] = []

        for run_id, run in context.runs.items():
            load = run.series.get(load_key)
            time = run.series.get(time_key)
            strain = run.series.get(strain_key)
            record = build_experiment_signal_gate(
                run_id=run_id,
                load=load,
                time=time,
                strain=strain,
                load_key=load_key,
                time_key=time_key,
                strain_key=strain_key,
                policy=policy,
            )
            run.scalars[output] = record
            window = record["coherent_window"]
            routing = record.get("report_routing") if isinstance(record.get("report_routing"), Mapping) else {}
            run.scalars[f"{output}_start_index"] = window["start_index"]
            run.scalars[f"{output}_end_index"] = window["end_index"]
            run.scalars[f"{output}_status"] = record.get("status")
            run.scalars[f"{output}_confidence"] = record.get("confidence")
            run.scalars[f"{output}_classifications"] = ";".join(str(item) for item in record.get("classifications", []) or [])
            run.scalars[f"{output}_excluded_region_count"] = len(record.get("excluded_regions", []) or [])
            run.scalars[f"{output}_report_routing_state"] = routing.get("state")
            run.scalars[f"{output}_report_routing_severity"] = routing.get("severity")
            run.scalars[f"{output}_report_routing_reason"] = routing.get("reason")
            run.metadata[output] = record
            run.units[f"{output}_start_index"] = "index"
            run.units[f"{output}_end_index"] = "index"
            warnings = tuple(str(item) for item in record.get("warnings", ()))
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type=self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"load": load_key, "time": time_key, "strain": strain_key},
                    parameters={"policy": policy},
                    outputs={output: record},
                    units={output: None},
                    evidence={
                        "signal_gate_record": record,
                        "coherent_window": record["coherent_window"],
                        "excluded_regions": record["excluded_regions"],
                        "diagnostics": record["diagnostics"],
                        "diagnostic_markers": record["diagnostic_markers"],
                        "classifications": record["classifications"],
                        "source_series_refs": record["source_series_refs"],
                        "policy": policy,
                    },
                    audit_view_hint="experiment_signal_gate",
                    warnings=warnings,
                )
            )
        return results


def build_experiment_signal_gate(
    *,
    run_id: str,
    load: list[Any] | None,
    time: list[Any] | None = None,
    strain: list[Any] | None = None,
    load_key: str = "load_N",
    time_key: str = "time_s",
    strain_key: str = "mean_strain",
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy(policy)
    length = max((len(series) for series in (load, time, strain) if series is not None), default=0)
    source_refs = {
        "load": {"series": load_key, "point_count": len(load or [])},
        "time": {"series": time_key, "point_count": len(time or [])},
        "strain": {"series": strain_key, "point_count": len(strain or [])},
    }
    if length == 0 or load is None:
        return {
            "schema_id": "method.experiment_signal_gate.v0_1",
            "run_id": run_id,
            "status": "warning",
            "confidence": "low",
            "reason": "Signal gate could not evaluate because the load series is missing or empty.",
            "coherent_window": {"start_index": None, "end_index": None, "point_count": 0, "classification": "not_available"},
            "excluded_regions": [],
            "diagnostics": [],
            "diagnostic_markers": {},
            "classifications": ["not_available"],
            "source_series_refs": source_refs,
            "policy": resolved_policy,
            "report_routing": {
                "schema_id": "method.signal_window_report_routing.v0_1",
                "state": "review",
                "severity": "review",
                "reason": "Signal gate was not available; the run requires review before default reporting.",
                "selection_effect": "requires_review_excluded_from_default",
            },
            "warnings": ("Load series is required for gate_experiment_signal.",),
        }

    y = [_abs_float(value) for value in load]
    domain = _domain_series(strain, time)
    blunt_tail = _detect_post_experiment_tail(y=y, domain=domain, policy=resolved_policy)
    domain_tail_candidate = _detect_low_load_high_domain_tail(y=y, domain=domain, policy=resolved_policy)
    domain_tail = (
        domain_tail_candidate
        if domain_tail_candidate is not None and not domain_tail_candidate.get("diagnostic_only")
        else None
    )
    tail = _earliest_tail(blunt_tail, domain_tail)
    end_index = length - 1
    excluded_regions: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    diagnostic_markers: dict[str, Any] = {}
    classifications = ["coherent_experiment_signal"]
    status = "ok"
    confidence = "high"
    reason = "No blunt invalid-signal tail evidence was found; full raw scan remains available to boundary detection."
    warnings: list[str] = []

    if tail is not None:
        end_index = max(0, int(tail["tail_start_index"]) - 1)
        excluded_regions = _excluded_regions(
            tail_start=int(tail["tail_start_index"]),
            tail_end=length - 1,
            tail=tail,
            y=y,
            domain=domain,
        )
        classifications.extend(_unique(str(region["classification"]) for region in excluded_regions))
        confidence = "medium"
        reason = (
            "A coherent peak/drop was followed by blunt invalid-tail evidence; boundary detection should use the "
            "coherent window and preserve the excluded rows as audit evidence."
        )
        onset = _diagnostic_loading_onset(y=y, end_index=end_index, policy=resolved_policy)
        if onset is not None:
            diagnostic_markers["loading_onset"] = onset
            diagnostics.append(onset)
            classifications.append("diagnostic_loading_onset_not_used_for_truncation")
        if domain_tail is not None and tail is domain_tail:
            diagnostics.append(_false_clean_pass_prevented(domain_tail))
            classifications.append("false_clean_pass_prevented")

    if (
        domain_tail_candidate is not None
        and domain_tail_candidate.get("diagnostic_only")
        and tail is None
    ):
        diagnostic = _diagnostic_low_load_high_domain_discontinuity(domain_tail_candidate)
        diagnostics.append(diagnostic)
        classifications.append(str(diagnostic["classification"]))
        if str(diagnostic["classification"]) == "preload_scale_low_load_high_domain_discontinuity":
            confidence = "medium"
            reason = (
                "A low-load/high-domain discontinuity was detected before any material-scale loading; "
                "the gate preserves it as audit evidence and keeps the full coherent scan available."
            )
        else:
            status = "review"
            confidence = "low"
            reason = (
                "A low-load/high-domain discontinuity was detected, but the evidence is not allowed to "
                "truncate the coherent window; boundary detection receives the full scan with review evidence."
            )
            warnings.append("Low-load/high-domain discontinuity requires signal review.")

    reference_peak = _max_abs_in_range(y, start=0, end=end_index)
    disconnected_fragment = _detect_disconnected_high_load_fragment(
        y=y,
        scan_start=end_index + 1,
        reference_peak=reference_peak,
        policy=resolved_policy,
    )
    if disconnected_fragment is not None:
        diagnostics.append(disconnected_fragment)
        classifications.append("disconnected_high_load_fragment")
        status = "fail"
        confidence = "low"
        reason = (
            "A disconnected high-load fragment appears after the selected coherent window; the scan is not a single "
            "coherent experiment signal."
        )
        warnings.append("Disconnected high-load fragment after gate window requires signal review.")

    late_restart = _detect_late_restart_spike_before_peak(y=y, domain=domain, end_index=end_index, policy=resolved_policy)
    if late_restart is not None:
        diagnostics.append(late_restart)
        classifications.append("late_restart_spike_before_peak")
        if status != "fail":
            status = "review"
            confidence = "low"
            reason = "A late restart/spike before the selected peak makes the coherent signal window review-level evidence."
            warnings.append("Late restart/spike before selected peak requires signal review.")

    dominant_endpoint = _dominant_failure_endpoint_arbitration(
        y=y,
        domain=domain,
        end_index=end_index,
        excluded_regions=excluded_regions,
    )
    if dominant_endpoint is not None:
        previous_status = status
        previous_regions = list(excluded_regions)
        dominant_index = int(dominant_endpoint["index"])
        diagnostics.append(dominant_endpoint)
        classifications.append(str(dominant_endpoint["classification"]))
        if dominant_index > end_index:
            excluded_regions = []
            end_index = dominant_index
            if previous_status == "fail":
                status = "review"
            confidence = "medium"
            reason = (
                "A later dominant load-bearing region remains connected to the experiment signal; "
                "the gate keeps it inside the coherent window and preserves the earlier jagged evidence for audit."
            )
            warnings = [
                warning
                for warning in warnings
                if "Disconnected high-load fragment" not in warning
            ]
            dominant_endpoint["previous_excluded_regions"] = previous_regions

    classifications = _unique(classifications)
    report_routing = _report_routing(
        status=status,
        confidence=confidence,
        classifications=classifications,
        excluded_regions=excluded_regions,
        diagnostics=diagnostics,
    )

    window = {
        "start_index": 0,
        "end_index": end_index,
        "point_count": end_index + 1 if end_index >= 0 else 0,
        "classification": "coherent_experiment_signal",
    }
    return {
        "schema_id": "method.experiment_signal_gate.v0_1",
        "run_id": run_id,
        "status": status,
        "confidence": confidence,
        "reason": reason,
        "coherent_window": window,
        "excluded_regions": excluded_regions,
        "diagnostics": diagnostics,
        "diagnostic_markers": diagnostic_markers,
        "classifications": classifications,
        "source_series_refs": source_refs,
        "policy": resolved_policy,
        "report_routing": report_routing,
        "warnings": tuple(warnings),
    }


def _detect_post_experiment_tail(
    *,
    y: list[float | None],
    domain: list[float | None] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    min_points = int(policy["min_coherent_numeric_points"])
    scan_points = int(policy["post_drop_scan_points"])
    series_max = max((value for value in y if value is not None), default=0.0)
    for peak_index in range(1, max(1, len(y) - 1)):
        peak = y[peak_index]
        next_load = y[peak_index + 1] if peak_index + 1 < len(y) else None
        previous = y[peak_index - 1] if peak_index > 0 else None
        if peak is None or next_load is None or previous is None:
            continue
        if peak <= 0.0 or peak < series_max * float(policy["min_peak_fraction_of_series_max"]):
            continue
        if peak_index + 1 < min_points:
            continue
        if peak < previous:
            continue
        drop_threshold = max(0.0, float(peak) * float(policy["min_drop_fraction_of_peak"]))
        if next_load > peak - drop_threshold:
            continue
        scan_start = peak_index + 2
        scan_end = min(len(y) - 1, peak_index + scan_points)
        if scan_start > scan_end:
            continue
        domain_reversal = _first_domain_reversal(domain, scan_start=peak_index + 1, scan_end=scan_end, policy=policy)
        invalid_cluster = _first_invalid_cluster(y, scan_start=scan_start, scan_end=scan_end, policy=policy)
        later_higher = _first_later_higher(y, peak_index=peak_index, scan_start=scan_start, scan_end=scan_end, policy=policy)
        implausible_jump = _first_implausible_tail_jump(y, peak_load=peak, scan_start=scan_start, policy=policy)
        plateau = _first_artificial_plateau(y, peak_load=peak, scan_start=scan_start, policy=policy)
        decisive_evidence = [invalid_cluster, implausible_jump, plateau]
        if not any(item is not None for item in decisive_evidence):
            continue

        tail_start = min(
            _evidence_start_index(item)
            for item in (domain_reversal, invalid_cluster, implausible_jump, plateau)
            if item is not None
        )
        return {
            "peak_index": peak_index,
            "drop_index": peak_index + 1,
            "tail_start_index": tail_start,
            "evidence": {
                "post_peak_drop": {"peak_index": peak_index, "drop_index": peak_index + 1, "peak_load": peak, "drop_load": next_load},
                "domain_reset_or_reversal": domain_reversal,
                "non_numeric_cluster": invalid_cluster,
                "later_higher_after_drop": later_higher,
                "implausible_tail_jump": implausible_jump,
                "artificial_plateau_or_saturation": plateau,
            },
        }
    return None


def _earliest_tail(*tails: dict[str, Any] | None) -> dict[str, Any] | None:
    available = [tail for tail in tails if tail is not None]
    if not available:
        return None
    return min(available, key=lambda item: int(item["tail_start_index"]))


def _evidence_start_index(evidence: Mapping[str, Any]) -> int:
    start = _as_int(evidence.get("start_index"))
    if start is not None:
        return start
    index = _as_int(evidence.get("index"))
    return index if index is not None else 0


def _detect_low_load_high_domain_tail(
    *,
    y: list[float | None],
    domain: list[float | None] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    if domain is None:
        return None
    min_points = int(policy["min_coherent_numeric_points"])
    low_load_fraction = float(policy["low_load_tail_fraction_of_peak"])
    min_tail_points = int(policy["low_load_tail_min_points"])
    min_reference_fraction = float(policy["low_load_tail_min_reference_peak_fraction_of_full_run_max"])
    full_run_peak = _max_abs_point_in_range(y, start=0, end=len(y) - 1)
    full_run_peak_index = full_run_peak[0] if full_run_peak is not None else None
    full_run_peak_load = full_run_peak[1] if full_run_peak is not None else None
    for index in range(max(1, min_points), min(len(y), len(domain))):
        load_value = y[index]
        left_domain = domain[index - 1]
        right_domain = domain[index]
        if load_value is None or left_domain is None or right_domain is None:
            continue
        prior_peak = _max_abs_in_range(y, start=0, end=index - 1)
        if prior_peak is None or prior_peak <= 0.0:
            continue
        if load_value > prior_peak * low_load_fraction:
            continue
        domain_delta = right_domain - left_domain
        threshold = _domain_jump_threshold(domain=domain, end_index=index - 1, policy=policy)
        if domain_delta < threshold:
            continue
        peak_index, peak_load = _max_abs_point_in_range(y, start=0, end=index - 1) or (None, prior_peak)
        end_index = _terminal_low_load_end(y=y, start=index, peak_load=prior_peak, low_load_fraction=low_load_fraction)
        point_count = end_index - index + 1
        scale_floor = (
            abs(float(full_run_peak_load)) * min_reference_fraction
            if full_run_peak_load is not None
            else 0.0
        )
        scale_floor_pass = prior_peak >= scale_floor
        persistence_pass = point_count >= min_tail_points
        diagnostic_only_reasons = []
        if not persistence_pass:
            diagnostic_only_reasons.append("insufficient_terminal_persistence")
        if not scale_floor_pass:
            diagnostic_only_reasons.append("preload_reference_below_full_run_scale_floor")
        diagnostic_only = bool(diagnostic_only_reasons)
        low_load_tail = {
            "index": index,
            "start_index": index,
            "end_index": end_index,
            "point_count": point_count,
            "min_tail_points": min_tail_points,
            "diagnostic_only": diagnostic_only,
            "load": load_value,
            "reference_peak_index": peak_index,
            "reference_peak_load": peak_load,
            "full_run_peak_index": full_run_peak_index,
            "full_run_peak_load": full_run_peak_load,
            "reference_peak_full_run_fraction": (
                prior_peak / abs(float(full_run_peak_load))
                if full_run_peak_load not in (None, 0.0)
                else None
            ),
            "min_reference_peak_fraction_of_full_run_max": min_reference_fraction,
            "reference_peak_scale_floor": scale_floor,
            "reference_peak_scale_floor_pass": scale_floor_pass,
            "terminal_persistence_pass": persistence_pass,
            "diagnostic_only_reasons": diagnostic_only_reasons,
            "domain_delta": domain_delta,
            "domain_jump_threshold": threshold,
            "low_load_threshold": prior_peak * low_load_fraction,
            "reason": (
                "large positive domain discontinuity enters a low-load terminal state"
                if scale_floor_pass
                else "large positive domain discontinuity follows only preload-scale load evidence"
            ),
        }
        reset = _high_load_domain_reset_before_tail(
            y=y,
            domain=domain,
            tail_start=index,
            reference_peak=prior_peak,
            policy=policy,
        )
        evidence = {
            "low_load_high_domain_tail": low_load_tail,
            "high_load_domain_reset_before_tail": reset,
        }
        return {
            "peak_index": peak_index,
            "drop_index": index,
            "tail_start_index": index,
            "evidence": evidence,
            "diagnostic_only": diagnostic_only,
        }
    return None


def _diagnostic_low_load_high_domain_discontinuity(tail: Mapping[str, Any]) -> dict[str, Any]:
    evidence = tail.get("evidence") if isinstance(tail.get("evidence"), Mapping) else {}
    low_tail = evidence.get("low_load_high_domain_tail") if isinstance(evidence, Mapping) else {}
    low_tail = low_tail if isinstance(low_tail, Mapping) else {}
    reasons = low_tail.get("diagnostic_only_reasons")
    reason_values = [str(item) for item in reasons] if isinstance(reasons, list) else []
    preload_scale = "preload_reference_below_full_run_scale_floor" in reason_values
    classification = (
        "preload_scale_low_load_high_domain_discontinuity"
        if preload_scale
        else "borderline_low_load_high_domain_discontinuity"
    )
    return {
        "classification": classification,
        "index": low_tail.get("index"),
        "start_index": low_tail.get("start_index"),
        "end_index": low_tail.get("end_index"),
        "point_count": low_tail.get("point_count"),
        "min_tail_points": low_tail.get("min_tail_points"),
        "load": low_tail.get("load"),
        "reference_peak_index": low_tail.get("reference_peak_index"),
        "reference_peak_load": low_tail.get("reference_peak_load"),
        "full_run_peak_index": low_tail.get("full_run_peak_index"),
        "full_run_peak_load": low_tail.get("full_run_peak_load"),
        "reference_peak_full_run_fraction": low_tail.get("reference_peak_full_run_fraction"),
        "min_reference_peak_fraction_of_full_run_max": low_tail.get("min_reference_peak_fraction_of_full_run_max"),
        "reference_peak_scale_floor": low_tail.get("reference_peak_scale_floor"),
        "reference_peak_scale_floor_pass": low_tail.get("reference_peak_scale_floor_pass"),
        "terminal_persistence_pass": low_tail.get("terminal_persistence_pass"),
        "diagnostic_only_reasons": reason_values,
        "domain_delta": low_tail.get("domain_delta"),
        "domain_jump_threshold": low_tail.get("domain_jump_threshold"),
        "low_load_threshold": low_tail.get("low_load_threshold"),
        "reason": (
            "low-load/high-domain evidence is present but its prefix reference peak is below the full-run scale floor"
            if preload_scale
            else "low-load/high-domain evidence is present but too short for destructive gate truncation"
        ),
    }


def _report_routing(
    *,
    status: str,
    confidence: str,
    classifications: list[str],
    excluded_regions: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    review_classes = {
        "borderline_low_load_high_domain_discontinuity",
        "late_restart_spike_before_peak",
        "disconnected_high_load_fragment",
        "not_available",
    }
    audit_classes = {
        "preload_scale_low_load_high_domain_discontinuity",
    }
    observed = set(classifications)
    observed.update(
        str(item.get("classification"))
        for item in diagnostics
        if isinstance(item, Mapping) and item.get("classification")
    )
    if status in {"review", "fail"} or confidence == "low" or observed & review_classes:
        return {
            "schema_id": "method.signal_window_report_routing.v0_1",
            "state": "review",
            "severity": "review",
            "reason": "Signal-window evidence requires scientist review before default reporting.",
            "selection_effect": "requires_review_excluded_from_default",
        }
    if excluded_regions or observed & audit_classes:
        return {
            "schema_id": "method.signal_window_report_routing.v0_1",
            "state": "reportable_with_audit",
            "severity": "info",
            "reason": (
                "Signal gate preserved non-truncating diagnostic evidence for audit."
                if observed & audit_classes and not excluded_regions
                else "Signal gate shortened a malformed tail while preserving excluded raw rows as audit evidence."
            ),
            "selection_effect": "included_with_warning",
        }
    return {
        "schema_id": "method.signal_window_report_routing.v0_1",
        "state": "reportable",
        "severity": "none",
        "reason": "No signal-window review routing was required.",
        "selection_effect": "informational",
    }


def _high_load_domain_reset_before_tail(
    *,
    y: list[float | None],
    domain: list[float | None],
    tail_start: int,
    reference_peak: float,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    threshold = _domain_jump_threshold(domain=domain, end_index=max(1, tail_start - 1), policy=policy)
    high_load_threshold = reference_peak * float(policy["disconnected_fragment_load_fraction_of_peak"])
    start = max(1, tail_start - int(policy["late_restart_lookback_points"]))
    for index in range(start, min(tail_start, len(domain))):
        left_domain = domain[index - 1]
        right_domain = domain[index]
        left_load = y[index - 1] if index - 1 < len(y) else None
        right_load = y[index] if index < len(y) else None
        if left_domain is None or right_domain is None or left_load is None or right_load is None:
            continue
        if left_load < high_load_threshold or right_load < high_load_threshold:
            continue
        domain_delta = right_domain - left_domain
        if domain_delta < -float(policy["domain_reversal_min_delta"]) or abs(domain_delta) >= threshold:
            return {
                "index": index,
                "start_index": index - 1,
                "end_index": index,
                "load_start": left_load,
                "load_end": right_load,
                "domain_delta": domain_delta,
                "domain_jump_threshold": threshold,
                "high_load_threshold": high_load_threshold,
                "reason": "high-load domain reset or discontinuity occurs before malformed low-load tail",
            }
    return None


def _detect_disconnected_high_load_fragment(
    *,
    y: list[float | None],
    scan_start: int,
    reference_peak: float | None,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    if reference_peak is None or reference_peak <= 0.0:
        return None
    threshold = reference_peak * float(policy["disconnected_fragment_load_fraction_of_peak"])
    minimum = int(policy["disconnected_fragment_min_points"])
    index = max(0, scan_start)
    while index < len(y):
        value = y[index]
        if value is None or value < threshold:
            index += 1
            continue
        start = index
        while index + 1 < len(y) and y[index + 1] is not None and y[index + 1] >= threshold:
            index += 1
        end = index
        if end - start + 1 >= minimum:
            return {
                "classification": "disconnected_high_load_fragment",
                "index": start,
                "start_index": start,
                "end_index": end,
                "point_count": end - start + 1,
                "load_threshold": threshold,
                "reference_peak_load": reference_peak,
                "reason": "contiguous high-load fragment after the selected coherent window",
            }
        index += 1
    return None


def _detect_late_restart_spike_before_peak(
    *,
    y: list[float | None],
    domain: list[float | None] | None,
    end_index: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    peak_point = _max_abs_point_in_range(y, start=0, end=end_index)
    if peak_point is None:
        return None
    peak_index, peak_load = peak_point
    if peak_index <= 1 or peak_load <= 0.0:
        return None
    lookback = int(policy["late_restart_lookback_points"])
    threshold = peak_load * float(policy["late_restart_jump_fraction_of_peak"])
    start = max(1, peak_index - lookback)
    for index in range(start, peak_index + 1):
        previous = y[index - 1]
        current = y[index]
        if previous is None or current is None:
            continue
        jump = current - previous
        if jump < threshold:
            continue
        previous_window = [value for value in y[max(0, index - lookback) : index] if value is not None]
        if len(previous_window) < 3:
            continue
        prior_peak = max(previous_window)
        prior_trough = min(previous_window)
        if prior_peak < peak_load * 0.4:
            continue
        if prior_peak - prior_trough < threshold:
            continue
        if previous > prior_peak - threshold:
            continue
        return {
            "classification": "late_restart_spike_before_peak",
            "index": index,
            "start_index": index - 1,
            "end_index": peak_index,
            "jump_load": jump,
            "jump_threshold": threshold,
            "reference_peak_index": peak_index,
            "reference_peak_load": peak_load,
            "prior_peak_load": prior_peak,
            "prior_trough_load": prior_trough,
            "domain_start": domain[index - 1] if domain is not None and index - 1 < len(domain) else None,
            "domain_end": domain[peak_index] if domain is not None and peak_index < len(domain) else None,
            "reason": "selected peak is reached through an abrupt restart/spike after a local depression",
        }
    return None


def _diagnostic_loading_onset(
    *,
    y: list[float | None],
    end_index: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    peak = _max_abs_in_range(y, start=0, end=end_index)
    if peak is None or peak <= 0.0:
        return None
    threshold = peak * float(policy["loading_onset_fraction_of_peak"])
    for index in range(0, min(end_index, len(y) - 1) + 1):
        value = y[index]
        if value is not None and value >= threshold:
            return {
                "classification": "diagnostic_loading_onset_not_used_for_truncation",
                "index": index,
                "load": value,
                "threshold_load": threshold,
                "reason": "loading onset marker is diagnostic-only; coherent_window.start_index remains 0",
            }
    return None


def _false_clean_pass_prevented(tail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "classification": "false_clean_pass_prevented",
        "index": int(tail["tail_start_index"]),
        "start_index": int(tail["tail_start_index"]),
        "end_index": int(tail["tail_start_index"]),
        "reason": "domain-tail evidence prevents a high-confidence full-scan clean-pass record",
    }


def _excluded_regions(
    *,
    tail_start: int,
    tail_end: int,
    tail: Mapping[str, Any],
    y: list[float | None],
    domain: list[float | None] | None,
) -> list[dict[str, Any]]:
    evidence = tail.get("evidence") if isinstance(tail.get("evidence"), Mapping) else {}
    regions = [
        {
            "region_id": "post_experiment_invalid_tail",
            "classification": "post_experiment_invalid_tail",
            "start_index": tail_start,
            "end_index": tail_end,
            "reason": "Rows after the coherent peak/drop are not treated as experiment signal.",
            "evidence": evidence,
            "sample_points": _sample_points(y=y, domain=domain, start=tail_start, end=tail_end),
        }
    ]
    for key, classification in (
        ("domain_reset_or_reversal", "domain_reset_or_reversal"),
        ("non_numeric_cluster", "non_numeric_cluster"),
        ("implausible_tail_jump", "implausible_tail_jump"),
        ("artificial_plateau_or_saturation", "artificial_plateau_or_saturation"),
        ("low_load_high_domain_tail", "low_load_high_domain_tail"),
        ("high_load_domain_reset_before_tail", "high_load_domain_reset_before_tail"),
    ):
        item = evidence.get(key)
        if isinstance(item, Mapping):
            start = int(item.get("start_index", item.get("index", tail_start)))
            end = int(item.get("end_index", item.get("index", start)))
            regions.append(
                {
                    "region_id": classification,
                    "classification": classification,
                    "start_index": start,
                    "end_index": end,
                    "reason": str(item.get("reason") or classification),
                    "evidence": dict(item),
                    "sample_points": _sample_points(y=y, domain=domain, start=start, end=end),
                }
            )
    return regions


def _first_domain_reversal(
    domain: list[float | None] | None,
    *,
    scan_start: int,
    scan_end: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    if domain is None:
        return None
    min_delta = max(0.0, _as_float(policy.get("domain_reversal_min_delta")) or 0.0)
    for index in range(max(1, scan_start), min(scan_end, len(domain) - 1) + 1):
        left = domain[index - 1]
        right = domain[index]
        if left is None or right is None:
            continue
        delta = right - left
        if delta < -min_delta:
            return {
                "index": index,
                "start_index": index - 1,
                "end_index": index,
                "domain_delta": delta,
                "reason": "domain value decreases after a coherent peak/drop branch",
            }
    return None


def _first_invalid_cluster(
    y: list[float | None],
    *,
    scan_start: int,
    scan_end: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    minimum = int(policy["invalid_cluster_min_points"])
    index = scan_start
    while index <= min(scan_end, len(y) - 1):
        if y[index] is not None:
            index += 1
            continue
        start = index
        while index + 1 < len(y) and y[index + 1] is None:
            index += 1
        end = index
        if end - start + 1 >= minimum:
            return {
                "index": start,
                "start_index": start,
                "end_index": end,
                "point_count": end - start + 1,
                "reason": "cluster of non-numeric load values after coherent peak/drop",
            }
        index += 1
    return None


def _first_later_higher(
    y: list[float | None],
    *,
    peak_index: int,
    scan_start: int,
    scan_end: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    peak = y[peak_index]
    if peak is None:
        return None
    tolerance = abs(peak) * float(policy["later_higher_relative_tolerance"])
    for index in range(scan_start, min(scan_end, len(y) - 1) + 1):
        value = y[index]
        if value is not None and value > peak + tolerance:
            return {
                "index": index,
                "load": value,
                "reference_peak_index": peak_index,
                "reference_peak_load": peak,
                "reason": "load recovers above the coherent peak inside a region with blunt tail evidence",
            }
    return None


def _first_implausible_tail_jump(
    y: list[float | None],
    *,
    peak_load: float,
    scan_start: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    threshold = abs(peak_load) * float(policy["implausible_tail_jump_fraction_of_peak"])
    for index in range(scan_start, len(y)):
        value = y[index]
        if value is not None and value >= threshold:
            return {
                "index": index,
                "load": value,
                "threshold_load": threshold,
                "reason": "tail load is implausibly larger than the coherent experiment peak",
            }
    return None


def _first_artificial_plateau(
    y: list[float | None],
    *,
    peak_load: float,
    scan_start: int,
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    minimum = int(policy["artificial_plateau_min_points"])
    index = scan_start
    while index < len(y):
        value = y[index]
        if value is None:
            index += 1
            continue
        end = index
        while end + 1 < len(y) and y[end + 1] == value:
            end += 1
        if value >= peak_load and end - index + 1 >= minimum:
            return {
                "index": index,
                "start_index": index,
                "end_index": end,
                "load": value,
                "point_count": end - index + 1,
                "reason": "repeated identical high-load tail values indicate artificial plateau or saturation",
            }
        index = end + 1
    return None


def _sample_points(
    *,
    y: list[float | None],
    domain: list[float | None] | None,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    candidates = [start, start + 1, end - 1, end]
    samples: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index in candidates:
        if index < start or index > end or index in seen or index >= len(y):
            continue
        seen.add(index)
        samples.append(
            {
                "point_index": index,
                "abs_load": y[index],
                "domain_value": domain[index] if domain is not None and index < len(domain) else None,
            }
        )
    return samples


def _domain_jump_threshold(
    *,
    domain: list[float | None],
    end_index: int,
    policy: Mapping[str, Any],
) -> float:
    end = max(1, min(end_index, len(domain) - 1))
    positive_steps = [
        domain[index] - domain[index - 1]
        for index in range(1, end + 1)
        if domain[index] is not None and domain[index - 1] is not None and domain[index] > domain[index - 1]
    ]
    baseline_step = _median([float(step) for step in positive_steps if step is not None and step > 0.0])
    observed = [value for value in domain[: end + 1] if value is not None]
    span = max(observed) - min(observed) if observed else 0.0
    return max(
        float(policy["domain_reversal_min_delta"]),
        baseline_step * float(policy["domain_jump_step_multiplier"]),
        span * float(policy["domain_jump_span_fraction"]),
    )


def _terminal_low_load_end(
    *,
    y: list[float | None],
    start: int,
    peak_load: float,
    low_load_fraction: float,
) -> int:
    threshold = peak_load * low_load_fraction
    end = start
    while end + 1 < len(y):
        value = y[end + 1]
        if value is None or value > threshold:
            break
        end += 1
    return end


def _max_abs_in_range(y: list[float | None], *, start: int, end: int) -> float | None:
    point = _max_abs_point_in_range(y, start=start, end=end)
    return point[1] if point is not None else None


def _max_abs_point_in_range(y: list[float | None], *, start: int, end: int) -> tuple[int, float] | None:
    values: list[tuple[int, float]] = []
    for index in range(max(0, start), min(len(y) - 1, end) + 1):
        value = y[index]
        if value is not None:
            values.append((index, abs(float(value))))
    if not values:
        return None
    return max(values, key=lambda item: item[1])


def _domain_series(strain: list[Any] | None, time: list[Any] | None) -> list[float | None] | None:
    source = strain if strain is not None else time
    return [_as_float(value) for value in source] if source is not None else None


def _policy(parameters: Mapping[str, Any] | None) -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    if isinstance(parameters, Mapping):
        for key in policy:
            if key in parameters and key != "schema_id":
                policy[key] = parameters[key]
    policy["min_coherent_numeric_points"] = max(3, _as_int(policy["min_coherent_numeric_points"], default=4) or 4)
    policy["post_drop_scan_points"] = max(2, _as_int(policy["post_drop_scan_points"], default=8) or 8)
    policy["min_peak_fraction_of_series_max"] = max(
        0.0,
        min(1.0, _as_float(policy["min_peak_fraction_of_series_max"]) or 0.05),
    )
    policy["invalid_cluster_min_points"] = max(1, _as_int(policy["invalid_cluster_min_points"], default=2) or 2)
    policy["artificial_plateau_min_points"] = max(2, _as_int(policy["artificial_plateau_min_points"], default=3) or 3)
    policy["min_drop_fraction_of_peak"] = max(0.0, _as_float(policy["min_drop_fraction_of_peak"]) or 0.005)
    policy["later_higher_relative_tolerance"] = max(0.0, _as_float(policy["later_higher_relative_tolerance"]) or 0.0)
    policy["implausible_tail_jump_fraction_of_peak"] = max(
        1.0,
        _as_float(policy["implausible_tail_jump_fraction_of_peak"]) or 2.0,
    )
    policy["loading_onset_fraction_of_peak"] = max(0.0, _as_float(policy["loading_onset_fraction_of_peak"]) or 0.05)
    policy["low_load_tail_fraction_of_peak"] = max(
        0.0,
        min(1.0, _as_float(policy["low_load_tail_fraction_of_peak"]) or 0.20),
    )
    policy["low_load_tail_min_points"] = max(2, _as_int(policy["low_load_tail_min_points"], default=3) or 3)
    policy["low_load_tail_min_reference_peak_fraction_of_full_run_max"] = max(
        0.0,
        min(1.0, _as_float(policy["low_load_tail_min_reference_peak_fraction_of_full_run_max"]) or 0.10),
    )
    policy["domain_jump_step_multiplier"] = max(1.0, _as_float(policy["domain_jump_step_multiplier"]) or 8.0)
    policy["domain_jump_span_fraction"] = max(0.0, _as_float(policy["domain_jump_span_fraction"]) or 0.20)
    policy["disconnected_fragment_load_fraction_of_peak"] = max(
        0.0,
        min(1.0, _as_float(policy["disconnected_fragment_load_fraction_of_peak"]) or 0.50),
    )
    policy["disconnected_fragment_min_points"] = max(
        1,
        _as_int(policy["disconnected_fragment_min_points"], default=5) or 5,
    )
    policy["late_restart_jump_fraction_of_peak"] = max(
        0.0,
        _as_float(policy["late_restart_jump_fraction_of_peak"]) or 0.05,
    )
    policy["late_restart_lookback_points"] = max(3, _as_int(policy["late_restart_lookback_points"], default=15) or 15)
    return policy


def _dominant_failure_peak(y: list[float | None]) -> tuple[int, float] | None:
    values = [
        (index, abs(float(value)))
        for index, value in enumerate(y)
        if value is not None and isfinite(float(value))
    ]
    if not values:
        return None
    best = values[0]
    for item in values[1:]:
        if item[1] > best[1] or (abs(item[1] - best[1]) <= 1e-12 and item[0] > best[0]):
            best = item
    return best


def _dominant_failure_endpoint_arbitration(
    *,
    y: list[float | None],
    domain: list[float | None] | None,
    end_index: int,
    excluded_regions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    dominant_peak = _dominant_failure_peak(y)
    if dominant_peak is None:
        return None
    dominant_index, dominant_load = dominant_peak
    if dominant_index <= end_index:
        return None
    if dominant_index >= len(y) - 1:
        return None
    if _hard_invalid_tail_evidence_between(excluded_regions, start=end_index + 1, end=dominant_index):
        return None
    transition = _post_peak_transition_end(y, peak_index=dominant_index)
    return {
        "classification": "load_bearing_restart_after_jagged_region",
        "index": transition["end_index"],
        "start_index": end_index + 1,
        "end_index": transition["end_index"],
        "accepted_failure_peak_index": dominant_index,
        "post_peak_transition_end_index": transition["end_index"],
        "dominant_peak_load": dominant_load,
        "post_peak_transition": transition,
        "previous_gate_end_index": end_index,
        "reason": (
            "Later dominant load-bearing evidence is numeric, non-terminal, and not blocked by hard invalid-tail evidence; "
            "roughness is treated as audit evidence rather than an invalid tail."
        ),
    }


def _hard_invalid_tail_evidence_between(
    regions: list[dict[str, Any]],
    *,
    start: int,
    end: int,
) -> bool:
    hard_invalid = {
        "non_numeric_cluster",
        "artificial_plateau_or_saturation",
    }
    for region in regions:
        classification = str(region.get("classification") or "")
        if classification not in hard_invalid:
            continue
        region_start = _as_int(region.get("start_index"))
        region_end = _as_int(region.get("end_index"))
        if region_start is None:
            continue
        region_end = region_start if region_end is None else region_end
        if region_start <= end and region_end >= start:
            return True
    return False


def _post_peak_transition_end(y: list[float | None], *, peak_index: int) -> dict[str, Any]:
    peak_load = _abs_float(y[peak_index]) if 0 <= peak_index < len(y) else None
    if peak_load is None or peak_index >= len(y) - 2:
        return {
            "schema_id": "method.post_peak_transition.v0_1",
            "peak_index": peak_index,
            "end_index": peak_index,
            "basis": "no post-peak transition evidence available",
        }
    noise_floor = _local_step_noise_floor(y, center_index=peak_index)
    high_water_index = peak_index
    high_water_load = peak_load
    decline_run = 0
    decline_start: int | None = None
    transition_end = peak_index
    for index in range(peak_index + 1, len(y)):
        load = _abs_float(y[index])
        previous = _abs_float(y[index - 1])
        if load is None or previous is None:
            continue
        if load > high_water_load:
            high_water_load = load
            high_water_index = index
            transition_end = index
            decline_run = 0
            decline_start = None
            continue
        if high_water_load - load <= noise_floor:
            transition_end = index
        if previous - load > noise_floor:
            decline_run += 1
            if decline_start is None:
                decline_start = index
        elif load - previous > noise_floor:
            decline_run = 0
            decline_start = None
        if decline_run >= 2 and high_water_load - load > noise_floor * 2.0:
            if decline_start is not None:
                transition_end = max(transition_end, decline_start - 1)
            break
    return {
        "schema_id": "method.post_peak_transition.v0_1",
        "peak_index": peak_index,
        "peak_load": peak_load,
        "end_index": transition_end,
        "high_water_index": high_water_index,
        "high_water_load": high_water_load,
        "noise_floor_load": noise_floor,
        "basis": "last high-load transition point before sustained decline beyond local step noise",
    }


def _local_step_noise_floor(y: list[float | None], *, center_index: int) -> float:
    start = max(0, center_index - 16)
    steps: list[float] = []
    for index in range(start + 1, center_index + 1):
        left = _abs_float(y[index - 1])
        right = _abs_float(y[index])
        if left is None or right is None:
            continue
        steps.append(abs(right - left))
    positive = sorted(step for step in steps if step > 0.0 and isfinite(step))
    if not positive:
        return 1e-12
    middle = len(positive) // 2
    median = positive[middle] if len(positive) % 2 else (positive[middle - 1] + positive[middle]) / 2.0
    return max(median * 3.0, 1e-12)


def _abs_float(value: Any) -> float | None:
    numeric = _as_float(value)
    return abs(float(numeric)) if numeric is not None else None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if isfinite(numeric) else None


def _as_int(value: Any, *, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unique(items: Any) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            values.append(item)
    return values


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0
