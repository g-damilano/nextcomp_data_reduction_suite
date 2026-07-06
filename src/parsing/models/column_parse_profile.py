from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ColumnExpectedKind = Literal["numeric", "text", "id", "timestamp", "boolean", "unknown"]


@dataclass(slots=True)
class ColumnParseProfile:
    source_column_index: int
    original_name: str
    family: str
    expected_kind: ColumnExpectedKind
    declared_unit: str | None
    canonical_unit: str | None
    numeric_policy_id: str | None
    decimal_separator: str | None
    thousands_separator: str | None
    missing_tokens: tuple[str, ...]
    strict_numeric: bool
    allow_unit_suffix: bool
    confidence: float
    evidence: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
