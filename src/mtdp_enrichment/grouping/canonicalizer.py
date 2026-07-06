from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CanonicalName:
    display_name: str
    canonical_key: str


class SampleNameCanonicalizer:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def canonicalize(self, candidate: str) -> CanonicalName:
        display = str(candidate).strip()
        key = display
        if self.config.get("replace_separators_with_space", True):
            key = re.sub(r"[-_]+", " ", key)
        if self.config.get("casefold", True):
            key = key.casefold()
        if self.config.get("collapse_whitespace", True):
            key = re.sub(r"\s+", " ", key).strip()
        else:
            key = key.strip()
        return CanonicalName(display_name=display, canonical_key=key)

