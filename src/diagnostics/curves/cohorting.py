from __future__ import annotations

from collections import defaultdict
from typing import Any

from diagnostics.curves.models import CurveCohortPolicy, CurveSeries


def cohort_key(curve: CurveSeries, policy: CurveCohortPolicy) -> tuple[str, ...]:
    if not policy.group_by:
        return ("whole_comparable_dataset",)
    values = []
    for field in policy.group_by:
        value = curve.metadata.get(field, "")
        values.append(f"{field}={value}")
    return tuple(values)


def cohort_id_from_key(key: tuple[str, ...]) -> str:
    safe = "__".join(item.replace(" ", "_").replace("/", "_") for item in key)
    return safe or "whole_comparable_dataset"


def cohort_label_from_key(key: tuple[str, ...]) -> str:
    if key == ("whole_comparable_dataset",):
        return "Whole comparable dataset"
    return ", ".join(key)


def group_curves(curves: list[CurveSeries], policy: CurveCohortPolicy) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[CurveSeries]] = defaultdict(list)
    for curve in curves:
        grouped[cohort_key(curve, policy)].append(curve)
    return {
        cohort_id_from_key(key): {
            "cohort_id": cohort_id_from_key(key),
            "cohort_label": cohort_label_from_key(key),
            "cohort_key": list(key),
            "curves": rows,
        }
        for key, rows in grouped.items()
    }

