from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class PreambleToken:
    source_line_index: int
    raw_key: str
    raw_value: str
    raw_unit: Optional[str]
    normalized_key: Optional[str] = None
    coerced_value_text: Optional[str] = None
    parse_warning: Optional[str] = None
