from __future__ import annotations

import math
from statistics import mean


def standardized_residuals(
    values: list[float],
    reference: list[float],
    variability: list[float],
) -> list[float]:
    length = min(len(values), len(reference), len(variability))
    residuals: list[float] = []
    for index in range(length):
        scale = variability[index] if variability[index] > 0 else 1.0
        residuals.append((values[index] - reference[index]) / scale)
    return residuals


def rms(values: list[float]) -> float | None:
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def normalized_rmse(values: list[float], reference: list[float]) -> float | None:
    length = min(len(values), len(reference))
    if length == 0:
        return None
    residual = math.sqrt(sum((values[index] - reference[index]) ** 2 for index in range(length)) / length)
    span = max(reference[:length]) - min(reference[:length])
    return residual / span if span else residual


def normalized_mae(values: list[float], reference: list[float]) -> float | None:
    length = min(len(values), len(reference))
    if length == 0:
        return None
    residual = mean(abs(values[index] - reference[index]) for index in range(length))
    span = max(reference[:length]) - min(reference[:length])
    return residual / span if span else residual


def max_abs_residual(residuals: list[float]) -> float | None:
    return max((abs(value) for value in residuals), default=None)

