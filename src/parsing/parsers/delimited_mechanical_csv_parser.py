from __future__ import annotations

import csv
from pathlib import Path

from parsing.columns.column_descriptor_builder import ColumnClassificationPass
from parsing.layout.table_layout_detector import TableLayoutDetectionPass
from parsing.models import ParsedSampleRecord
from parsing.parsers.base_parser import BaseParser
from parsing.preamble.token_extractor import PreambleExtractionPass
from parsing.readers.delimited_numeric_reader import NumericIngestionPass, diagnostics_from_channels
from parsing.sniffing.file_sniffer import FileSniffPass


class DelimitedMechanicalCsvParser(BaseParser):
    parser_name = "delimited_mechanical_csv"

    def __init__(self, file_path: str | Path):
        super().__init__(file_path)
        self.sniff_pass = FileSniffPass()
        self.preamble_pass = PreambleExtractionPass()
        self.layout_pass = TableLayoutDetectionPass()
        self.column_pass = ColumnClassificationPass()
        self.numeric_pass = NumericIngestionPass()

    @classmethod
    def can_parse(cls, file_path: str | Path, text_snippet: str | None = None) -> bool:
        suffix = Path(file_path).suffix.lower()
        return suffix in {".csv", ".txt", ".dat"}

    def parse(self) -> ParsedSampleRecord:
        sniff = self.sniff_pass.run(self.file_path)
        lines = Path(self.file_path).read_text(encoding=sniff.encoding).splitlines()
        preamble_tokens = self.preamble_pass.run(lines, sniff)
        layout = self.layout_pass.run(lines, sniff)

        header = next(csv.reader([lines[layout.header_row_index]], delimiter=sniff.delimiter, quotechar=sniff.quotechar))
        units = None
        if layout.units_row_index is not None:
            units = next(csv.reader([lines[layout.units_row_index]], delimiter=sniff.delimiter, quotechar=sniff.quotechar))

        descriptors = self.column_pass.run(header, units, layout)
        channels = self.numeric_pass.run(
            self.file_path,
            layout,
            descriptors,
            delimiter=sniff.delimiter,
            quotechar=sniff.quotechar,
            encoding=sniff.encoding,
        )
        column_parse_profiles = tuple(
            channel.parse_profile for channel in channels.all_channels() if channel.parse_profile is not None
        )
        cell_diagnostics = diagnostics_from_channels(channels)

        sample_id = None
        validity_hint = None
        validity_source = None
        for token in preamble_tokens:
            if token.normalized_key in {"specimen_name", "sample_id", "specimen_id"} and token.coerced_value_text:
                sample_id = token.coerced_value_text
            if token.normalized_key == "failure_mode":
                value = (token.coerced_value_text or token.raw_value).strip().lower()
                if value in {"valid", "acceptable", "accepted", "pass", "passed"}:
                    validity_hint = True
                elif value in {"invalid", "not valid", "failed", "fail", "rejected"}:
                    validity_hint = False
                validity_source = token.raw_key

        return ParsedSampleRecord(
            source_file=Path(self.file_path),
            sample_id=sample_id,
            file_sniff=sniff,
            preamble_tokens=preamble_tokens,
            table_layout=layout,
            channels=channels,
            raw_header=tuple(header),
            raw_units_row=tuple(units) if units is not None else None,
            column_parse_profiles=column_parse_profiles,
            cell_diagnostics=cell_diagnostics,
            parser_policy_snapshot={
                "parser_name": self.parser_name,
                "numeric_policy_ids": sorted(
                    {
                        profile.numeric_policy_id
                        for profile in column_parse_profiles
                        if profile.numeric_policy_id
                    }
                ),
            },
            validity_hint=validity_hint,
            validity_hint_source=validity_source,
        )
