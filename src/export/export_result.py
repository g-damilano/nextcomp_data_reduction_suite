from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportResult:
    status: str
    output_dir: Path
    manifest_path: Path
    profile: str
    artifacts: tuple[str, ...]
    warnings: tuple[str, ...] = ()
