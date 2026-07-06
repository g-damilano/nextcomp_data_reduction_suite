from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class TableLayoutRecord:
    header_row_index: int
    units_row_index: Optional[int]
    data_start_row_index: int
    detected_column_count: int
    notes: tuple[str, ...] = ()
