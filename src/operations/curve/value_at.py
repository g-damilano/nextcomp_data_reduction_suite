from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


class ValueAtIndexOperation(Operation):
    operation_id = "value_at_index"

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        series_key = str(step.get("series"))
        index_key = str(step.get("index_from"))
        output = str(step.get("output"))
        results: list[OperationResult] = []
        for run_id, run in context.runs.items():
            warnings: list[str] = []
            series = run.series.get(series_key)
            index_value = run.scalars.get(index_key)
            value = None
            try:
                index = int(index_value)
            except (TypeError, ValueError):
                index = -1
                warnings.append(f"Index scalar '{index_key}' is missing or not an integer.")
            if series is None:
                warnings.append(f"Series '{series_key}' is missing.")
            elif index < 0 or index >= len(series):
                warnings.append(f"Index {index} is outside series '{series_key}'.")
            else:
                value = series[index]
                run.scalars[output] = value
                run.units[output] = run.units.get(series_key)
            results.append(
                OperationResult(
                    operation_id=self.operation_id,
                    operation_type="value_at_max" if "max" in index_key else self.operation_id,
                    phase=context.phase,
                    run_id=run_id,
                    status="warning" if warnings else "ok",
                    inputs={"series": series_key, "index": index_key},
                    parameters={},
                    outputs={output: value},
                    units={output: run.units.get(series_key)},
                    evidence={"resolved_index": index, "index_source": index_key},
                    audit_view_hint="failure_strain_marker",
                    warnings=tuple(warnings),
                )
            )
        return results
