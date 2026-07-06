from __future__ import annotations

from typing import Any

from diagnostics.curves.models import CurveAlignmentPolicy, CurveSeries


def align_curves(
    curves: list[CurveSeries],
    policy: CurveAlignmentPolicy,
) -> tuple[list[float], dict[str, list[float]], list[dict[str, Any]]]:
    points = max(3, int(policy.resample_points or 250))
    x_grid = [index / (points - 1) for index in range(points)]
    aligned: dict[str, list[float]] = {}
    rows: list[dict[str, Any]] = []
    for curve in curves:
        values = _resample(curve.x, curve.y, x_grid)
        if values is None:
            continue
        aligned[curve.run_id] = values
        for x_common, y_value in zip(x_grid, values, strict=False):
            rows.append(
                {
                    "run_id": curve.run_id,
                    "cohort_id": curve.metadata.get("cohort_id", ""),
                    "x_common": x_common,
                    "x_domain": policy.domain,
                    "y_aligned": y_value,
                }
            )
    return x_grid, aligned, rows


def _resample(x_values: tuple[float, ...], y_values: tuple[float, ...], x_grid: list[float]) -> list[float] | None:
    pairs = sorted(
        (float(x), float(y))
        for x, y in zip(x_values, y_values, strict=False)
        if x is not None and y is not None
    )
    if len(pairs) < 2:
        return None
    x_min = pairs[0][0]
    x_max = pairs[-1][0]
    if x_max == x_min:
        return None
    normalized = [((x - x_min) / (x_max - x_min), y) for x, y in pairs]
    out: list[float] = []
    cursor = 0
    for target in x_grid:
        while cursor < len(normalized) - 2 and normalized[cursor + 1][0] < target:
            cursor += 1
        left_x, left_y = normalized[cursor]
        right_x, right_y = normalized[min(cursor + 1, len(normalized) - 1)]
        if right_x == left_x:
            out.append(left_y)
            continue
        ratio = (target - left_x) / (right_x - left_x)
        out.append(left_y + ratio * (right_y - left_y))
    return out

