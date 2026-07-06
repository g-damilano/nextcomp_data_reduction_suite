from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SupplementalFile:
    source_path: Path
    scope: str = "dataset"
    role: str = "other"
    run_id: str | None = None
    notes: str | None = None


__all__ = ["SupplementalFile"]
