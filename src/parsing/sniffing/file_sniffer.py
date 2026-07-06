from __future__ import annotations

import csv
from pathlib import Path

from parsing.columns.family_classifier import classify_channel_family
from parsing.models import FileSniffResult


class FileSniffPass:
    """Pass P1: determine the basic file reading strategy."""

    def run(self, file_path: str | Path) -> FileSniffResult:
        path = Path(file_path)
        encoding, text = _read_text(path)
        lines = text.splitlines()
        sample = "\n".join(lines[:25])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";"])
            delimiter = dialect.delimiter
            quotechar = dialect.quotechar or '"'
        except csv.Error:
            delimiter = ","
            quotechar = '"'

        likely_header = None
        candidate_delimiters = _unique_delimiters((delimiter, ",", "\t", ";"))
        for idx, line in enumerate(lines):
            for candidate_delimiter in candidate_delimiters:
                cells = next(csv.reader([line], delimiter=candidate_delimiter, quotechar=quotechar))
                if _looks_like_header(cells):
                    likely_header = idx
                    delimiter = candidate_delimiter
                    break
            if likely_header is not None:
                break

        return FileSniffResult(
            file_path=path,
            delimiter=delimiter,
            encoding=encoding,
            has_preamble=likely_header is not None and likely_header > 0,
            likely_header_row_index=likely_header,
            total_lines=len(lines),
            quotechar=quotechar,
        )


def _read_text(path: Path) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return encoding, path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return "utf-8-sig", path.read_text(encoding="utf-8-sig", errors="replace")


def _unique_delimiters(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def _looks_like_header(cells: list[str]) -> bool:
    if len(cells) < 2:
        return False
    families = [classify_channel_family(cell) for cell in cells]
    measurement = {
        family
        for family in families
        if family in {"load", "extension", "displacement", "strain", "stress", "time"}
    }
    if len(measurement) < 2:
        return False
    has_load_or_stress = bool(measurement & {"load", "stress"})
    has_deformation = bool(measurement & {"extension", "displacement", "strain"})
    if has_load_or_stress and has_deformation:
        return True
    return "stress" in measurement and "strain" in measurement
