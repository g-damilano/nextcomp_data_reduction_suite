from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NumericParsePolicy:
    policy_id: str
    decimal_separator: str | None
    thousands_separator: str | None
    allow_sign: bool = True
    allow_unicode_minus: bool = True
    allow_scientific_notation: bool = True
    allow_embedded_spaces: bool = False
    allow_unit_suffix: bool = False
    missing_tokens: tuple[str, ...] = ("", "NA", "N/A", "NULL", "null", "—", "-")
    strict_grouping: bool = True
