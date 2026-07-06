from __future__ import annotations

from math import sqrt
from statistics import mean


def shape_metrics(
    y_values: tuple[float | None, ...],
    y_reference: tuple[float | None, ...],
) -> dict[str, float | None]:
    pairs = [
        (float(value), float(reference))
        for value, reference in zip(y_values, y_reference, strict=False)
        if value is not None and reference is not None
    ]
    return {
        "curve_correlation": _correlation([value for value, _ in pairs], [reference for _, reference in pairs]),
        "derivative_rmse": _derivative_rmse(y_values, y_reference),
    }


def _correlation(values: list[float], reference: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean_values = mean(values)
    mean_reference = mean(reference)
    numerator = sum((value - mean_values) * (ref - mean_reference) for value, ref in zip(values, reference, strict=True))
    left = sqrt(sum((value - mean_values) ** 2 for value in values))
    right = sqrt(sum((ref - mean_reference) ** 2 for ref in reference))
    if left == 0 or right == 0:
        return None
    return numerator / (left * right)


def _derivative_rmse(
    y_values: tuple[float | None, ...],
    y_reference: tuple[float | None, ...],
) -> float | None:
    y_diff = _diffs(y_values)
    ref_diff = _diffs(y_reference)
    pairs = [
        (float(value), float(reference))
        for value, reference in zip(y_diff, ref_diff, strict=False)
        if value is not None and reference is not None
    ]
    if not pairs:
        return None
    residuals = [value - reference for value, reference in pairs]
    scale = _scale([reference for _, reference in pairs])
    return sqrt(sum(residual * residual for residual in residuals) / len(residuals)) / scale


def _diffs(values: tuple[float | None, ...]) -> list[float | None]:
    diffs: list[float | None] = []
    for left, right in zip(values, values[1:], strict=False):
        diffs.append(None if left is None or right is None else right - left)
    return diffs


def _scale(values: list[float]) -> float:
    if not values:
        return 1.0
    span = max(values) - min(values)
    if abs(span) > 1e-12:
        return abs(span)
    magnitude = max(abs(value) for value in values)
    return magnitude if magnitude > 1e-12 else 1.0
