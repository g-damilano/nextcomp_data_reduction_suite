from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DiagnosticSeverity = Literal["info", "warning", "review_required", "error"]


@dataclass(slots=True)
class CellParseDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    source_row_index: int
    data_row_index: int
    source_column_index: int
    original_name: str
    family: str
    raw_value: str
    expected_kind: str | None = None
    parse_rule_id: str | None = None
    detected_decimal_separator: str | None = None
    detected_thousands_separator: str | None = None
    detected_unit: str | None = None
