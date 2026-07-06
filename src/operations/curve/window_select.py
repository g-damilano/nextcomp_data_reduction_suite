from __future__ import annotations


def select_window_by_series_range(
    values: list[float | None],
    lower: float,
    upper: float,
    *,
    absolute: bool = False,
) -> list[int]:
    indices: list[int] = []
    for index, value in enumerate(values):
        if value is None:
            continue
        comparable = abs(value) if absolute else value
        if lower <= comparable <= upper:
            indices.append(index)
    return indices

