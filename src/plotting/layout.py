from __future__ import annotations

from typing import Any


def should_suppress_visible_labels(values: list[dict[str, Any]], *, max_visible_labels: int = 3) -> tuple[bool, str]:
    if len(values) > max_visible_labels:
        return True, "visible annotation labels suppressed; values available in tooltip"
    return False, ""


def downsample(rows: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    if len(rows) <= max_rows:
        return rows
    if max_rows <= 0:
        return []
    if max_rows == 1:
        return [rows[0]]
    if max_rows == 2:
        return [rows[0], rows[-1]]

    interior_budget = max_rows - 2
    interior = rows[1:-1]
    stride = max(1, (len(interior) + interior_budget - 1) // interior_budget)
    sampled = [rows[0], *interior[::stride], rows[-1]]
    if len(sampled) > max_rows:
        sampled = [sampled[0], *sampled[1:-1][:interior_budget], sampled[-1]]
    return sampled
