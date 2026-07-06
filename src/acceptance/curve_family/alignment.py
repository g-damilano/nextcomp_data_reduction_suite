from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Any

from acceptance.curve_family.models import AlignedCurve


def align_curve_family(
    rows: list[dict[str, Any]],
    *,
    curve_family_id: str,
    run_ids: set[str] | None,
    x_field: str,
    y_field: str,
    mode: str,
    x_common_points: int,
) -> tuple[list[AlignedCurve], list[str]]:
    """Align reduced curve rows without mutating specimen-level curves."""

    grouped: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    selected = run_ids or {str(row.get("run_id")) for row in rows if row.get("run_id")}
    warnings: list[str] = []
    for row in rows:
        run_id = str(row.get("run_id") or "")
        if not run_id or run_id not in selected:
            continue
        x_value = _as_float(row.get(x_field))
        y_value = _as_float(row.get(y_field))
        if x_value is None or y_value is None:
            continue
        index = int(_as_float(row.get("point_index")) or len(grouped[run_id]))
        grouped[run_id].append((index, x_value, y_value))

    if not grouped:
        return [], ["No numeric curve rows were available for curve-family assessment."]

    point_count = max(2, int(x_common_points or 250))
    if mode == "experiment_progress":
        return _align_on_experiment_progress(grouped, curve_family_id, point_count), warnings
    if mode == "method_x_domain":
        return _align_on_method_domain(grouped, curve_family_id, point_count), warnings
    return _align_on_normalized_progress(grouped, curve_family_id, mode, point_count), warnings


def _align_on_experiment_progress(
    grouped: dict[str, list[tuple[int, float, float]]],
    curve_family_id: str,
    point_count: int,
) -> list[AlignedCurve]:
    x_common = _linspace(0.0, 1.0, point_count)
    aligned: list[AlignedCurve] = []
    for run_id, points in sorted(grouped.items()):
        by_progress = _dedupe_x(sorted((point[1], point[2]) for point in points))
        if len(by_progress) < 2:
            continue
        source_x = [point[0] for point in by_progress]
        source_y = [point[1] for point in by_progress]
        aligned.append(
            AlignedCurve(
                curve_family_id=curve_family_id,
                run_id=run_id,
                x_common=tuple(x_common),
                y_aligned=tuple(_interpolate(source_x, source_y, x_common)),
                alignment_mode="experiment_progress",
            )
        )
    return aligned


def _align_on_normalized_progress(
    grouped: dict[str, list[tuple[int, float, float]]],
    curve_family_id: str,
    mode: str,
    point_count: int,
) -> list[AlignedCurve]:
    x_common = _linspace(0.0, 1.0, point_count)
    aligned: list[AlignedCurve] = []
    for run_id, points in sorted(grouped.items()):
        selected = _through_max_y(points)
        if len(selected) < 2:
            continue
        source_x = _linspace(0.0, 1.0, len(selected))
        source_y = [point[2] for point in selected]
        aligned.append(
            AlignedCurve(
                curve_family_id=curve_family_id,
                run_id=run_id,
                x_common=tuple(x_common),
                y_aligned=tuple(_interpolate(source_x, source_y, x_common)),
                alignment_mode=mode or "normalized_progress",
            )
        )
    return aligned


def _align_on_method_domain(
    grouped: dict[str, list[tuple[int, float, float]]],
    curve_family_id: str,
    point_count: int,
) -> list[AlignedCurve]:
    domains: list[tuple[float, float]] = []
    sorted_points: dict[str, list[tuple[float, float]]] = {}
    for run_id, points in sorted(grouped.items()):
        by_x = sorted((point[1], point[2]) for point in points)
        deduped = _dedupe_x(by_x)
        if len(deduped) < 2:
            continue
        sorted_points[run_id] = deduped
        domains.append((deduped[0][0], deduped[-1][0]))
    if not domains:
        return []
    start = max(domain[0] for domain in domains)
    end = min(domain[1] for domain in domains)
    if not start < end:
        return []
    x_common = _linspace(start, end, point_count)
    return [
        AlignedCurve(
            curve_family_id=curve_family_id,
            run_id=run_id,
            x_common=tuple(x_common),
            y_aligned=tuple(_interpolate([x for x, _ in points], [y for _, y in points], x_common)),
            alignment_mode="method_x_domain",
        )
        for run_id, points in sorted_points.items()
    ]


def _through_max_y(points: list[tuple[int, float, float]]) -> list[tuple[int, float, float]]:
    ordered = sorted(points, key=lambda item: item[0])
    if not ordered:
        return []
    max_index = max(range(len(ordered)), key=lambda index: ordered[index][2])
    return ordered[: max_index + 1] if max_index > 0 else ordered


def _dedupe_x(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    seen: set[float] = set()
    for x_value, y_value in points:
        if x_value in seen:
            continue
        seen.add(x_value)
        deduped.append((x_value, y_value))
    return deduped


def _interpolate(source_x: list[float], source_y: list[float], target_x: list[float]) -> list[float | None]:
    if len(source_x) != len(source_y) or len(source_x) < 2:
        return [None for _ in target_x]
    values: list[float | None] = []
    cursor = 0
    for x_value in target_x:
        while cursor < len(source_x) - 2 and source_x[cursor + 1] < x_value:
            cursor += 1
        left_x = source_x[cursor]
        right_x = source_x[cursor + 1]
        left_y = source_y[cursor]
        right_y = source_y[cursor + 1]
        if right_x == left_x:
            values.append(left_y)
            continue
        ratio = (x_value - left_x) / (right_x - left_x)
        values.append(left_y + ratio * (right_y - left_y))
    return values


def _linspace(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None
