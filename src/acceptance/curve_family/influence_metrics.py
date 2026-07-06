from __future__ import annotations

from acceptance.curve_family.models import AlignedCurve


def leave_one_out_mean_shift(aligned_curves: list[AlignedCurve]) -> dict[str, float | None]:
    if len(aligned_curves) < 2:
        return {curve.run_id: None for curve in aligned_curves}
    mean_all = _pointwise_mean(aligned_curves)
    scale = _scale([value for value in mean_all if value is not None])
    shifts: dict[str, float | None] = {}
    for curve in aligned_curves:
        others = [candidate for candidate in aligned_curves if candidate.run_id != curve.run_id]
        mean_without = _pointwise_mean(others)
        diffs = [
            abs(float(left) - float(right))
            for left, right in zip(mean_all, mean_without, strict=False)
            if left is not None and right is not None
        ]
        shifts[curve.run_id] = (sum(diffs) / len(diffs) / scale) if diffs else None
    return shifts


def _pointwise_mean(curves: list[AlignedCurve]) -> list[float | None]:
    if not curves:
        return []
    count = len(curves[0].y_aligned)
    output: list[float | None] = []
    for index in range(count):
        values = [
            curve.y_aligned[index]
            for curve in curves
            if index < len(curve.y_aligned) and curve.y_aligned[index] is not None
        ]
        numeric = [float(value) for value in values if value is not None]
        output.append(sum(numeric) / len(numeric) if numeric else None)
    return output


def _scale(values: list[float]) -> float:
    if not values:
        return 1.0
    span = max(values) - min(values)
    if abs(span) > 1e-12:
        return abs(span)
    magnitude = max(abs(value) for value in values)
    return magnitude if magnitude > 1e-12 else 1.0
