from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ColumnDescriptor:
    column_index: int
    original_name: str
    original_unit_text: Optional[str]
    family: str
    ordinal: int
    canonical_name: str
    alias: Optional[str] = None
    canonical_unit: Optional[str] = None
    source_notes: tuple[str, ...] = ()
