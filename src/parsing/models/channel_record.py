from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .bad_cell_record import BadCellRecord
from .column_parse_profile import ColumnParseProfile
from .column_descriptor import ColumnDescriptor
from .parsed_cell_record import ParsedCellRecord


@dataclass(slots=True)
class ChannelRecord:
    descriptor: ColumnDescriptor
    values: list[float | None]
    source_column_index: int
    non_null_count: int
    null_count: int
    original_unit_text: Optional[str] = None
    canonical_unit: Optional[str] = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    bad_cells: tuple[BadCellRecord, ...] = field(default_factory=tuple)
    parsed_cells: tuple[ParsedCellRecord, ...] = field(default_factory=tuple)
    parse_profile: ColumnParseProfile | None = None
