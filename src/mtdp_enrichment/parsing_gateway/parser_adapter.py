from __future__ import annotations

from pathlib import Path
from typing import Iterable

from parsing.models import ParsedSampleRecord
from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser


class ParserError(RuntimeError):
    pass


class ParserAdapter:
    """Thin gateway to the external parsing suite.

    This class deliberately delegates parsing to parser classes under
    ``parsing.parsers``. The enrichment tool consumes the resulting structured
    ``ParsedSampleRecord`` and does not inspect raw files itself.
    """

    parser_name = "external_parsing_suite"
    parser_version = "0.1.0"

    def __init__(self, parsers: Iterable[type[DelimitedMechanicalCsvParser]] | None = None) -> None:
        self.parsers = tuple(parsers or (DelimitedMechanicalCsvParser,))

    def supported_suffixes(self) -> tuple[str, ...]:
        return (".csv", ".txt", ".dat")

    def can_parse(self, path: str | Path) -> bool:
        return any(parser.can_parse(path) for parser in self.parsers)

    def parse(self, input_file: str | Path) -> ParsedSampleRecord:
        path = Path(input_file)
        for parser_class in self.parsers:
            if parser_class.can_parse(path):
                return parser_class(path).parse()
        raise ParserError(f"No configured parser can parse {path}")

