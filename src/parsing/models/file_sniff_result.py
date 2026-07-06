from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class FileSniffResult:
    file_path: Path
    delimiter: str
    encoding: str
    has_preamble: bool
    likely_header_row_index: Optional[int]
    total_lines: int
    quotechar: str = '"'
    notes: tuple[str, ...] = ()
