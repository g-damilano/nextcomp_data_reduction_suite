from __future__ import annotations


def first_last_indices(indices: list[int]) -> tuple[int | None, int | None]:
    if not indices:
        return None, None
    return indices[0], indices[-1]

