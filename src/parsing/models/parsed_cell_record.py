from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ParsedCellStatus = Literal["ok", "missing", "ambiguous", "invalid", "unsupported"]


@dataclass(slots=True)
class ParsedCellRecord:
    source_row_index: int
    data_row_index: int
    source_column_index: int
    original_name: str
    family: str
    raw_value: str
    normalized_text: str | None
    value: float | str | None
    status: ParsedCellStatus
    parse_rule_id: str
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None
    expected_kind: str | None = None
    detected_decimal_separator: str | None = None
    detected_thousands_separator: str | None = None
    detected_unit: str | None = None
    candidate_interpretations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
