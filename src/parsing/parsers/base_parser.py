from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from parsing.models import ParsedSampleRecord


class BaseParser(ABC):
    parser_name: ClassVar[str] = 'base'

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    @classmethod
    def can_parse(cls, file_path: str | Path, text_snippet: str | None = None) -> bool:
        return False

    @abstractmethod
    def parse(self) -> ParsedSampleRecord:
        raise NotImplementedError
