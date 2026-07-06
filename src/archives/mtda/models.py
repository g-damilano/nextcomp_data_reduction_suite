from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MTDAWriteResult:
    path: Path
    members: tuple[str, ...]

