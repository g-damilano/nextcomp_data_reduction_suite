from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .channel_bundle import ChannelBundle
from .cell_parse_diagnostic import CellParseDiagnostic
from .column_parse_profile import ColumnParseProfile
from .file_sniff_result import FileSniffResult
from .preamble_token import PreambleToken
from .table_layout_record import TableLayoutRecord


@dataclass(slots=True)
class ParsedSampleRecord:
    source_file: Path
    sample_id: Optional[str]
    file_sniff: FileSniffResult
    preamble_tokens: list[PreambleToken]
    table_layout: TableLayoutRecord
    channels: ChannelBundle
    raw_header: tuple[str, ...]
    raw_units_row: Optional[tuple[str, ...]]
    parse_warnings: tuple[str, ...] = ()
    column_parse_profiles: tuple[ColumnParseProfile, ...] = ()
    cell_diagnostics: tuple[CellParseDiagnostic, ...] = ()
    parser_policy_snapshot: dict[str, object] | None = None
    validity_hint: Optional[bool] = None
    validity_hint_source: Optional[str] = None

    def get_metadata_value(self, normalized_key: str) -> Optional[str]:
        for token in self.preamble_tokens:
            if token.normalized_key == normalized_key:
                return token.coerced_value_text or token.raw_value
        return None
