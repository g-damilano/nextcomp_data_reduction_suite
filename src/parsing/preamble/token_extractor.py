from __future__ import annotations

import csv
from typing import Any

from parsing.models import FileSniffResult, PreambleToken
from parsing.preamble.token_normalizer import coerce_metadata_value, normalise_metadata_key


class PreambleExtractionPass:
    """Pass P2: extract metadata tokens from the pre-table region."""

    def run(self, lines: list[str], sniff: FileSniffResult) -> list[PreambleToken]:
        header_idx = sniff.likely_header_row_index if sniff.likely_header_row_index is not None else len(lines)
        tokens: list[PreambleToken] = []
        for idx, line in enumerate(lines[:header_idx]):
            if not line.strip():
                continue
            cells = next(csv.reader([line], delimiter=sniff.delimiter, quotechar=sniff.quotechar))
            cells = [c.strip() for c in cells]
            if not cells or not cells[0]:
                continue
            raw_key = cells[0]
            raw_value = cells[1] if len(cells) > 1 else ""
            raw_unit = cells[2] if len(cells) > 2 and cells[2] else None
            tokens.append(
                PreambleToken(
                    source_line_index=idx,
                    raw_key=raw_key,
                    raw_value=raw_value,
                    raw_unit=raw_unit,
                    normalized_key=normalise_metadata_key(raw_key),
                    coerced_value_text=coerce_metadata_value(raw_value),
                )
            )
        return tokens
