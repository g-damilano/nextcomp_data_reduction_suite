from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BadCellRecord:
    source_row_index: int
    data_row_index: int
    source_column_index: int
    original_name: str
    family: str
    raw_value: str
    reason: str
    diagnostic_code: str = "invalid_cell"
    severity: str = "error"
    expected_kind: str | None = None
    parse_rule_id: str | None = None
    detected_decimal_separator: str | None = None
    detected_thousands_separator: str | None = None
    detected_unit: str | None = None
