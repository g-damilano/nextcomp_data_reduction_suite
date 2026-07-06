from __future__ import annotations

import math
from statistics import median

from diagnostics.curves.models import CurveReferencePolicy


def reference_curve(
    aligned: dict[str, list[float]],
    policy: CurveReferencePolicy,
) -> tuple[list[float], list[float]]:
    if not aligned:
        return [], []
    length = min(len(values) for values in aligned.values())
    reference: list[float] = []
    variability: list[float] = []
    for index in range(length):
        values = [curve[index] for curve in aligned.values()]
        if policy.curve == "median":
            center = float(median(values))
        else:
            center = sum(values) / len(values)
        reference.append(center)
        variability.append(_variability(values, center, policy))
    floor = _std_floor(reference, variability)
    variability = [value if value > 0 else floor for value in variability]
    return reference, variability


def _variability(values: list[float], center: float, policy: CurveReferencePolicy) -> float:
    if len(values) < 2:
        return 0.0
    if policy.variability == "mad":
        deviations = [abs(value - center) for value in values]
        return float(median(deviations)) * 1.4826
    if policy.variability == "min_max":
        return (max(values) - min(values)) / 2.0
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def _std_floor(reference: list[float], variability: list[float]) -> float:
    positives = [value for value in variability if value > 0]
    if positives:
        return max(min(positives), 1e-9)
    if reference:
        span = max(reference) - min(reference)
        if span > 0:
            return max(span * 0.01, 1e-9)
    return 1.0

