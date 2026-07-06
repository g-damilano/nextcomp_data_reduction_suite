from __future__ import annotations

from statistics import median
from typing import Any


def robust_scalar_outliers(
    rows: list[dict[str, Any]],
    *,
    fields: list[str],
    threshold: float,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for field in fields:
        values = [(str(row.get("run_id")), _as_float(row.get(field))) for row in rows]
        numeric = [(run_id, value) for run_id, value in values if value is not None]
        if len(numeric) < 4:
            continue
        field_values = [value for _run_id, value in numeric]
        center = median(field_values)
        deviations = [abs(value - center) for value in field_values]
        mad = median(deviations)
        if mad == 0:
            continue
        for run_id, value in numeric:
            robust_z = 0.6745 * (value - center) / mad
            if abs(robust_z) > threshold:
                findings.append(
                    {
                        "run_id": run_id,
                        "field": field,
                        "value": value,
                        "median": center,
                        "mad": mad,
                        "robust_z": robust_z,
                        "threshold": threshold,
                    }
                )
    return findings


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
