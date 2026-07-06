from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportRequest:
    input_path: Path
    output_dir: Path
    profile: str = "minimal"
    overwrite: bool = True

    @classmethod
    def from_paths(cls, *, input_path: str | Path, output_dir: str | Path, profile: str = "minimal") -> "ExportRequest":
        return cls(input_path=Path(input_path), output_dir=Path(output_dir), profile=profile)
