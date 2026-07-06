from __future__ import annotations

from math import sqrt


def distance_metrics(
    y_values: tuple[float | None, ...],
    y_reference: tuple[float | None, ...],
) -> dict[str, float | None]:
    pairs = _paired(y_values, y_reference)
    if not pairs:
        return {
            "normalized_rmse": None,
            "normalized_mae": None,
            "integrated_absolute_residual": None,
            "max_absolute_residual": None,
        }
    residuals = [y - reference for y, reference in pairs]
    abs_residuals = [abs(value) for value in residuals]
    scale = _reference_scale([reference for _, reference in pairs])
    rmse = sqrt(sum(value * value for value in residuals) / len(residuals))
    mae = sum(abs_residuals) / len(abs_residuals)
    return {
        "normalized_rmse": rmse / scale,
        "normalized_mae": mae / scale,
        "integrated_absolute_residual": mae / scale,
        "max_absolute_residual": max(abs_residuals) / scale,
    }


def residual_rows(
    y_values: tuple[float | None, ...],
    y_reference: tuple[float | None, ...],
) -> list[dict[str, float | None]]:
    scale = _reference_scale([value for value in y_reference if value is not None])
    rows: list[dict[str, float | None]] = []
    for y_value, reference in zip(y_values, y_reference, strict=False):
        if y_value is None or reference is None:
            rows.append({"residual": None, "absolute_residual": None, "standardized_residual": None})
            continue
        residual = y_value - reference
        rows.append(
            {
                "residual": residual,
                "absolute_residual": abs(residual),
                "standardized_residual": residual / scale,
            }
        )
    return rows


def _paired(
    y_values: tuple[float | None, ...],
    y_reference: tuple[float | None, ...],
) -> list[tuple[float, float]]:
    return [
        (float(value), float(reference))
        for value, reference in zip(y_values, y_reference, strict=False)
        if value is not None and reference is not None
    ]


def _reference_scale(values: list[float]) -> float:
    if not values:
        return 1.0
    span = max(values) - min(values)
    if abs(span) > 1e-12:
        return abs(span)
    magnitude = max(abs(value) for value in values)
    return magnitude if magnitude > 1e-12 else 1.0
