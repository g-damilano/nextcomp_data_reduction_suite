from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult
from operations.curve.window_select import select_window_by_series_range
from operations.diagnostics.bending_pattern import assess_bending_pattern


class BendingDiagnosticOperation(Operation):
    operation_id = "bending_diagnostic"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        strain_a_key = str(step.get("strain_a"))
        strain_b_key = str(step.get("strain_b"))
        load_key = str(step.get("load"))
        output = str(step.get("output", "bending_diagnostic"))
        window = [float(item) for item in step.get("window_percent_of_max_load", (10, 90))]
        lower_percent, upper_percent = min(window), max(window)
        policy = step.get("bending_assessment_policy", {})
        threshold_percent = step.get("threshold_percent")
        if threshold_percent is not None:
            threshold_percent = float(threshold_percent)
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            strain_a = run.series.get(strain_a_key)
            strain_b = run.series.get(strain_b_key)
            load = run.series.get(load_key)
            diagnostic: dict[str, Any] | None = None
            inspection_ref: str | None = None
            if strain_a is None or strain_b is None or load is None:
                warnings.append("Bending diagnostic input series are missing.")
            else:
                load_values = [abs(value) for value in load if value is not None]
                max_load = max(load_values) if load_values else None
                if max_load in (None, 0):
                    warnings.append("Bending diagnostic cannot find a non-zero maximum load.")
                else:
                    lower = max_load * lower_percent / 100.0
                    upper = max_load * upper_percent / 100.0
                    indices = select_window_by_series_range(load, lower, upper, absolute=True)
                    bending_series = [
                        _bending_percent(
                            strain_a[index] if index < len(strain_a) else None,
                            strain_b[index] if index < len(strain_b) else None,
                        )
                        for index in range(len(load))
                    ]
                    assessment = assess_bending_pattern(
                        bending_series=bending_series,
                        load_series=load,
                        window_indices=indices,
                        policy=policy if isinstance(policy, Mapping) else None,
                        threshold_percent=threshold_percent,
                    )
                    pointwise = assessment["pointwise"]
                    diagnostic = {
                        "max_load_basis_N": max_load,
                        "window_percent_of_max_load": [lower_percent, upper_percent],
                        "load_window_N": [lower, upper],
                        "window": {
                            "policy": "percent_of_max_load",
                            "max_load_N": max_load,
                            "lower_load_N": lower,
                            "upper_load_N": upper,
                            "point_count": pointwise["total_points"],
                        },
                        "pointwise": pointwise,
                        "segments": assessment["segments"],
                        "longest_segment": assessment["longest_segment"],
                        "pattern": assessment["pattern"],
                        "threshold_percent": pointwise["threshold_percent"],
                        "point_count": pointwise["total_points"],
                        "max_bending_percent": pointwise["max_bending_percent"],
                        "mean_bending_percent": pointwise["mean_bending_percent"],
                        "median_bending_percent": pointwise["median_bending_percent"],
                        "p95_bending_percent": pointwise["p95_bending_percent"],
                        "p99_bending_percent": pointwise["p99_bending_percent"],
                        "points_above_threshold": pointwise["points_above_threshold"],
                        "fraction_above_threshold": pointwise["fraction_above_threshold"],
                        "pattern_classification": assessment["pattern"]["classification"],
                        "pattern_confidence": assessment["pattern"]["confidence"],
                        "pattern_reason": assessment["pattern"]["reason"],
                    }
                    inspection = context.inspector.inspect_range(
                        load,
                        bending_series,
                        lower,
                        upper,
                        scope=f"{run_id}:{output}",
                        inspection_id=f"inspect_{run_id}_bending_window",
                        curve_id=f"{run_id}_bending_load",
                        run_id=run_id,
                        x_channel=load_key,
                        y_channel="bending_percent",
                    )
                    inspection_ref = context.record_inspection(inspection)
                    warnings.extend(inspection.warnings)
                    if pointwise["total_points"] == 0:
                        warnings.append("No valid opposite-face strain points in bending window.")
                    run.diagnostics[output] = diagnostic
                    run.scalars[output] = diagnostic
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="bending_diagnostic",
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"strain_a": strain_a_key, "strain_b": strain_b_key, "load": load_key},
                    parameters={
                        "window_percent_of_max_load": [lower_percent, upper_percent],
                        "threshold_percent": threshold_percent,
                        "bending_assessment_policy": policy if isinstance(policy, Mapping) else {},
                    },
                    outputs={output: diagnostic},
                    units={
                        "max_load_basis_N": "N",
                        "load_window_N": "N",
                        "max_bending_percent": "%",
                        "mean_bending_percent": "%",
                        "median_bending_percent": "%",
                        "p95_bending_percent": "%",
                        "p99_bending_percent": "%",
                        "threshold_percent": "%",
                    },
                    evidence={
                        "formula": "abs(compression_magnitude_a - compression_magnitude_b) / abs(compression_magnitude_a + compression_magnitude_b) * 100",
                        "window_basis": "10-90 percent of maximum absolute load unless recipe overrides values",
                        "strain_basis": "compression magnitude channels supplied by method_resolve",
                        "strict_evidence": {
                            "threshold_percent": diagnostic.get("threshold_percent") if diagnostic else threshold_percent,
                            "points_above_threshold": diagnostic.get("points_above_threshold") if diagnostic else None,
                            "fraction_above_threshold": diagnostic.get("fraction_above_threshold") if diagnostic else None,
                        },
                        "pattern_classification": diagnostic.get("pattern") if diagnostic else None,
                    },
                    inspection_refs=(inspection_ref,) if inspection_ref else (),
                    audit_view_hint="bending_pattern_assessment",
                    warnings=tuple(warnings),
                )
            )
        return results


def _bending_percent(strain_a: float | None, strain_b: float | None) -> float | None:
    if strain_a is None or strain_b is None:
        return None
    denominator = abs(strain_a + strain_b)
    if denominator == 0:
        return None
    return abs(strain_a - strain_b) / denominator * 100.0
