from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunImageEvidence:
    source_path: Path
    view: str
    role: str = "audit_evidence"
    used_for_metrology: bool = False
    notes: str | None = None
