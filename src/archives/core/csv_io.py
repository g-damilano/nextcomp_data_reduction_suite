from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedTokenizedCsv:
    tokens: dict[str, tuple[str, str | None]]
    channels: dict[str, tuple[str | None, list[float | None]]]


def parse_tokenized_csv(text: str) -> ParsedTokenizedCsv:
    rows = list(csv.reader(io.StringIO(text)))
    blank_index = _first_blank_index(rows)
    token_rows = rows[:blank_index]
    table_rows = rows[blank_index + 1 :] if blank_index is not None else []

    tokens: dict[str, tuple[str, str | None]] = {}
    for row in token_rows:
        if len(row) < 2 or not row[0].strip():
            continue
        value = row[1].strip()
        unit = row[2].strip() if len(row) > 2 and row[2].strip() else None
        tokens[row[0].strip()] = (value, unit)

    if len(table_rows) < 2:
        return ParsedTokenizedCsv(tokens=tokens, channels={})

    headers = _unique_headers([cell.strip() for cell in table_rows[0]])
    units = [_clean_unit(cell) for cell in table_rows[1]]
    values: dict[str, list[float | None]] = {header: [] for header in headers}
    for row in table_rows[2:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        for index, header in enumerate(headers):
            values[header].append(_to_float(row[index]) if index < len(row) else None)

    channels = {
        header: (units[index] if index < len(units) else None, series)
        for index, (header, series) in enumerate(values.items())
    }
    return ParsedTokenizedCsv(tokens=tokens, channels=channels)


def write_dict_rows(rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str] | None = None) -> str:
    if fieldnames is None:
        fieldnames = _fieldnames_from_rows(rows)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fieldnames), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
    return buffer.getvalue()


def _first_blank_index(rows: Sequence[Sequence[str]]) -> int | None:
    for index, row in enumerate(rows):
        if not row or not any(cell.strip() for cell in row):
            return index
    return None


def _unique_headers(headers: Iterable[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique: list[str] = []
    for header in headers:
        base = header or "Column"
        counts[base] = counts.get(base, 0) + 1
        unique.append(base if counts[base] == 1 else f"{base} {counts[base]}")
    return unique


def _clean_unit(value: str) -> str | None:
    unit = value.strip()
    if unit.startswith("(") and unit.endswith(")"):
        unit = unit[1:-1].strip()
    return unit or None


def _to_float(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _fieldnames_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.15g}"
    return value
