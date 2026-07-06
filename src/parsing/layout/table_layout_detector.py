from __future__ import annotations

import csv

from parsing.columns.family_classifier import looks_like_unit_text
from parsing.models import FileSniffResult, TableLayoutRecord


class TableLayoutDetectionPass:
    """Pass P3: locate header row, units row, and data start row."""

    def run(self, lines: list[str], sniff: FileSniffResult) -> TableLayoutRecord:
        if sniff.likely_header_row_index is None:
            raise ValueError("Could not locate a likely table header row.")

        header_idx = sniff.likely_header_row_index
        header = next(csv.reader([lines[header_idx]], delimiter=sniff.delimiter, quotechar=sniff.quotechar))
        detected_cols = len(header)

        units_idx = None
        data_start = header_idx + 1
        if data_start < len(lines):
            candidate = next(csv.reader([lines[data_start]], delimiter=sniff.delimiter, quotechar=sniff.quotechar))
            stripped = [c.strip() for c in candidate]
            if _looks_like_units_row(stripped):
                units_idx = data_start
                data_start += 1

        return TableLayoutRecord(
            header_row_index=header_idx,
            units_row_index=units_idx,
            data_start_row_index=data_start,
            detected_column_count=detected_cols,
        )


def _looks_like_units_row(cells: list[str]) -> bool:
    non_empty = [cell for cell in cells if cell.strip()]
    if not non_empty:
        return False
    if any(_looks_numeric(cell) for cell in non_empty):
        return False
    unit_count = sum(1 for cell in non_empty if looks_like_unit_text(cell))
    return unit_count >= max(1, len(non_empty) - 1)


def _looks_numeric(text: str) -> bool:
    value = text.strip().strip('"').strip("'")
    if not value:
        return False
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    try:
        float(value)
    except ValueError:
        return False
    return True
