from __future__ import annotations

from statistics import median

from inspector.inspection_report import InspectionReport


class CurveInspector:
    """Read-only curve inspection service used by operations."""

    def inspect_curve(
        self,
        x: list[float | None],
        y: list[float | None],
        *,
        scope: str = "curve",
        inspection_id: str | None = None,
        curve_id: str | None = None,
        run_id: str | None = None,
        x_channel: str | None = None,
        y_channel: str | None = None,
    ) -> InspectionReport:
        pairs = _valid_pairs(x, y)
        warnings: list[str] = []
        if len(pairs) < 2:
            warnings.append("Curve has fewer than two valid x/y points.")
        xs = [item[0] for item in pairs]
        ys = [item[1] for item in pairs]
        spacings = [b - a for a, b in zip(xs, xs[1:])]
        positive_spacings = [value for value in spacings if value > 0]
        duplicate_count = len(spacings) - len(positive_spacings)
        if duplicate_count:
            warnings.append("Curve includes duplicate or non-increasing x values.")
        median_spacing = median(positive_spacings) if positive_spacings else None
        spacing_irregularity = None
        if median_spacing and positive_spacings:
            spacing_irregularity = max(positive_spacings) / median_spacing
            if spacing_irregularity > 5:
                warnings.append("Curve spacing is irregular.")
        missing_x_count = sum(1 for value in x if value is None)
        missing_y_count = sum(1 for value in y if value is None)
        metrics = {
            "point_count": len(pairs),
            "missing_x_count": missing_x_count,
            "missing_y_count": missing_y_count,
            "missing_pairs": max(len(x), len(y)) - len(pairs),
            "x_min": min(xs) if xs else None,
            "x_max": max(xs) if xs else None,
            "y_min": min(ys) if ys else None,
            "y_max": max(ys) if ys else None,
            "duplicate_x_count": duplicate_count,
            "monotonic_x": all(value >= 0 for value in spacings),
            "monotonic_y_direction": _monotonic_direction(ys),
            "median_dx": median_spacing,
            "dx_variability_ratio": spacing_irregularity,
            "nearest_left_gap": None,
            "nearest_right_gap": None,
        }
        return InspectionReport(
            inspection_id=inspection_id or _inspection_id(scope, run_id, "curve"),
            inspection_type="curve",
            curve_id=curve_id or scope,
            run_id=run_id,
            x_channel=x_channel,
            y_channel=y_channel,
            metrics=metrics,
            warnings=tuple(warnings),
        )

    def inspect_range(
        self,
        x: list[float | None],
        y: list[float | None],
        x_min: float,
        x_max: float,
        *,
        scope: str = "range",
        inspection_id: str | None = None,
        curve_id: str | None = None,
        run_id: str | None = None,
        x_channel: str | None = None,
        y_channel: str | None = None,
    ) -> InspectionReport:
        pairs = _valid_pairs(x, y)
        in_range = [(x_value, y_value) for x_value, y_value in pairs if x_min <= x_value <= x_max]
        warnings: list[str] = []
        if len(in_range) < 2:
            warnings.append("Range has fewer than two valid points.")
        xs = [item[0] for item in pairs]
        range_xs = [item[0] for item in in_range]
        range_ys = [item[1] for item in in_range]
        range_spacings = [b - a for a, b in zip(range_xs, range_xs[1:])]
        positive_range_spacings = [value for value in range_spacings if value > 0]
        nearest_low = min((abs(x_value - x_min) for x_value in xs), default=None)
        nearest_high = min((abs(x_value - x_max) for x_value in xs), default=None)
        if xs and (x_min < min(xs) or x_max > max(xs)):
            warnings.append("Requested range extends beyond available x data.")
        median_dx = median(positive_range_spacings) if positive_range_spacings else None
        dx_variability = None
        if median_dx and positive_range_spacings:
            dx_variability = max(positive_range_spacings) / median_dx
        metrics = {
            "requested_x_min": x_min,
            "requested_x_max": x_max,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": min(range_ys) if range_ys else None,
            "y_max": max(range_ys) if range_ys else None,
            "point_count": len(in_range),
            "point_count_in_range": len(in_range),
            "nearest_left_gap": nearest_low,
            "nearest_right_gap": nearest_high,
            "nearest_low_anchor_gap": nearest_low,
            "nearest_high_anchor_gap": nearest_high,
            "median_dx": median_dx,
            "median_dx_in_range": median_dx,
            "dx_variability_ratio": dx_variability,
            "dx_variability_ratio_in_range": dx_variability,
            "y_min_in_range": min(range_ys) if range_ys else None,
            "y_max_in_range": max(range_ys) if range_ys else None,
            "y_variability_estimate": (max(range_ys) - min(range_ys)) if range_ys else None,
            "available_x_min": min(xs) if xs else None,
            "available_x_max": max(xs) if xs else None,
            "missing_x_count": sum(1 for value in x if value is None),
            "missing_y_count": sum(1 for value in y if value is None),
            "duplicate_x_count": 0,
            "monotonic_x": all(value >= 0 for value in [b - a for a, b in zip(xs, xs[1:])]),
            "monotonic_y_direction": _monotonic_direction([item[1] for item in pairs]),
        }
        return InspectionReport(
            inspection_id=inspection_id or _inspection_id(scope, run_id, "range"),
            inspection_type="range",
            curve_id=curve_id or scope,
            run_id=run_id,
            x_channel=x_channel,
            y_channel=y_channel,
            metrics=metrics,
            warnings=tuple(warnings),
        )


def _valid_pairs(
    x: list[float | None],
    y: list[float | None],
) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for x_value, y_value in zip(x, y):
        if x_value is None or y_value is None:
            continue
        pairs.append((float(x_value), float(y_value)))
    return pairs


def _monotonic_direction(values: list[float]) -> str:
    if len(values) < 2:
        return "unknown"
    increases = all(b >= a for a, b in zip(values, values[1:]))
    decreases = all(b <= a for a, b in zip(values, values[1:]))
    if increases and not decreases:
        return "increasing"
    if decreases and not increases:
        return "decreasing"
    if increases and decreases:
        return "flat"
    return "mixed"


def _inspection_id(scope: str, run_id: str | None, inspection_type: str) -> str:
    safe_scope = "".join(char if char.isalnum() or char in "-_" else "_" for char in scope).strip("_")
    safe_run = "".join(char if char.isalnum() or char in "-_" else "_" for char in str(run_id or "dataset")).strip("_")
    return f"inspect_{safe_run}_{safe_scope or inspection_type}"
