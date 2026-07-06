from __future__ import annotations

from collections.abc import Mapping
from math import isclose
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


class MaxPointOperation(Operation):
    operation_id = "max_point"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        series_key = str(step.get("y"))
        output_value = str(step.get("output_value"))
        output_index = str(step.get("output_index"))
        mode = str(step.get("mode", "max"))
        index_from = step.get("index_from")
        index_key = str(index_from) if index_from is not None else ""
        index_series_key = str(step.get("index_series") or step.get("point_index_series") or "")
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            series = run.series.get(series_key)
            selected: tuple[int, float] | None = None
            if series is None:
                warnings.append(f"Series '{series_key}' is missing.")
            elif index_key:
                selected = _select_at_anchor(
                    series,
                    anchor_value=run.scalars.get(index_key),
                    index_series=run.series.get(index_series_key) if index_series_key else None,
                    warnings=warnings,
                    series_key=series_key,
                    index_key=index_key,
                    index_series_key=index_series_key,
                )
            else:
                values = [(index, value) for index, value in enumerate(series) if value is not None]
                if not values:
                    warnings.append(f"Series '{series_key}' has no numeric values.")
                elif mode == "absolute_max":
                    selected = _select_last_tied_max(values, absolute=True)
                else:
                    selected = _select_last_tied_max(values, absolute=False)
            if selected is not None:
                run.scalars[output_index] = selected[0]
                run.scalars[output_value] = selected[1]
                run.units[output_value] = run.units.get(series_key)
                run.units[output_index] = "index"
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="max_point",
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"series": series_key},
                    parameters={
                        "mode": mode,
                        "index_from": index_key or None,
                        "index_series": index_series_key or None,
                    },
                    outputs={
                        output_value: selected[1] if selected else None,
                        output_index: selected[0] if selected else None,
                    },
                    units={output_value: run.units.get(series_key), output_index: "index"},
                    evidence={
                        "selected_index": selected[0] if selected else None,
                        "selected_value": selected[1] if selected else None,
                    },
                    audit_view_hint="max_strength_marker",
                    warnings=tuple(warnings),
                )
            )
        return results


class AcceptedPeakPointOperation(MaxPointOperation):
    operation_id = "accepted_peak_point"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        anchored_step = dict(step)
        anchored_step.setdefault("index_from", "accepted_failure_peak_index")
        anchored_step.setdefault("index_series", "point_index_bounded")
        return super().run(context, anchored_step)


def _select_at_anchor(
    series: list[Any],
    *,
    anchor_value: Any,
    index_series: list[Any] | None,
    warnings: list[str],
    series_key: str,
    index_key: str,
    index_series_key: str,
) -> tuple[int, Any] | None:
    index = _anchor_to_series_index(
        anchor_value,
        series_length=len(series),
        index_series=index_series,
    )
    if index is None:
        if index_series_key:
            warnings.append(
                f"Index scalar '{index_key}' could not be resolved through index series '{index_series_key}'."
            )
        else:
            warnings.append(f"Index scalar '{index_key}' is missing or outside series '{series_key}'.")
        return None
    value = series[index]
    if value is None:
        warnings.append(f"Anchored index {index} in series '{series_key}' has no numeric value.")
        return None
    return index, value


def _anchor_to_series_index(
    anchor_value: Any,
    *,
    series_length: int,
    index_series: list[Any] | None,
) -> int | None:
    if index_series is not None:
        anchor = _as_float(anchor_value)
        if anchor is None:
            return None
        for index, value in enumerate(index_series):
            numeric = _as_float(value)
            if numeric is not None and isclose(numeric, anchor, rel_tol=1e-12, abs_tol=1e-12):
                return index if 0 <= index < series_length else None
        return None
    try:
        index = int(anchor_value)
    except (TypeError, ValueError):
        return None
    return index if 0 <= index < series_length else None


def _select_last_tied_max(values: list[tuple[int, Any]], *, absolute: bool) -> tuple[int, Any]:
    selected_index, selected_value = values[0]
    selected_numeric = abs(float(selected_value)) if absolute else float(selected_value)
    for index, value in values[1:]:
        numeric = abs(float(value)) if absolute else float(value)
        if numeric > selected_numeric or isclose(numeric, selected_numeric, rel_tol=1e-12, abs_tol=1e-12):
            selected_index = index
            selected_value = value
            selected_numeric = numeric
    return selected_index, selected_value


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
