from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


class ChordSlopeOperation(Operation):
    operation_id = "chord_slope"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        x_key = str(step.get("x"))
        y_key = str(step.get("y"))
        x1 = float(step.get("x1"))
        x2 = float(step.get("x2"))
        output = str(step.get("output"))
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            x_values = run.series.get(x_key)
            y_values = run.series.get(y_key)
            slope = None
            evidence: dict[str, Any] = {"x1": x1, "x2": x2}
            if x_values is None or y_values is None:
                warnings.append("Chord slope input series are missing.")
            elif x1 == x2:
                warnings.append("Chord slope endpoints must not be equal.")
            else:
                inspection = context.inspector.inspect_range(
                    x_values,
                    y_values,
                    min(x1, x2),
                    max(x1, x2),
                    scope=f"{run_id}:{output}",
                    inspection_id=f"inspect_{run_id}_modulus_window",
                    curve_id=f"{run_id}_stress_strain",
                    run_id=run_id,
                    x_channel=x_key,
                    y_channel=y_key,
                )
                inspection_ref = context.record_inspection(inspection)
                warnings.extend(inspection.warnings)
                try:
                    y1 = _interpolate(x_values, y_values, x1)
                    y2 = _interpolate(x_values, y_values, x2)
                    slope = (y2 - y1) / (x2 - x1)
                    run.scalars[output] = slope
                    run.units[output] = str(step.get("unit", "")) or run.units.get(y_key)
                    evidence["left_anchor"] = {"x": x1, "y": y1, "source": "interpolated"}
                    evidence["right_anchor"] = {"x": x2, "y": y2, "source": "interpolated"}
                except ValueError as exc:
                    warnings.append(str(exc))
            if x_values is None or y_values is None or x1 == x2:
                inspection_ref = None
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="chord_slope",
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"x": x_key, "y": y_key},
                    parameters={"x1": x1, "x2": x2, "mode": "chord"},
                    outputs={output: slope},
                    units={output: run.units.get(output)},
                    evidence=evidence,
                    inspection_refs=(inspection_ref,) if inspection_ref else (),
                    audit_view_hint="modulus_window_overlay",
                    warnings=tuple(warnings),
                )
            )
        return results


def _interpolate(
    x_values: list[float | None],
    y_values: list[float | None],
    target: float,
) -> float:
    pairs = sorted(
        (float(x), float(y))
        for x, y in zip(x_values, y_values)
        if x is not None and y is not None
    )
    if not pairs:
        raise ValueError("Cannot interpolate because no valid x/y pairs exist.")
    if target < pairs[0][0] or target > pairs[-1][0]:
        raise ValueError(f"Interpolation target {target} is outside available x range.")
    for index, (x_value, y_value) in enumerate(pairs):
        if x_value == target:
            return y_value
        if x_value > target and index > 0:
            x0, y0 = pairs[index - 1]
            if x_value == x0:
                return y_value
            ratio = (target - x0) / (x_value - x0)
            return y0 + ratio * (y_value - y0)
    return pairs[-1][1]
