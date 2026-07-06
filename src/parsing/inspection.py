from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from parsing.models import ParsedSampleRecord


def to_standard_data_structure(value: Any) -> Any:
    """Recursively convert parser records into plain Python containers.

    The parser models are dataclasses with slots. This function keeps their
    field names and nested structure intact while translating them to standard
    dictionaries, lists, strings, numbers, booleans, and None.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_standard_data_structure(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            to_standard_data_structure(key): to_standard_data_structure(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_standard_data_structure(item) for item in value]
    return value


def _rows_from_record(record: ParsedSampleRecord, start: int, stop: int) -> list[dict[str, float | None]]:
    channels = sorted(record.channels.all_channels(), key=lambda ch: ch.source_column_index)
    rows: list[dict[str, float | None]] = []
    if not channels:
        return rows
    n_rows = max((len(ch.values) for ch in channels), default=0)
    start = max(0, start)
    stop = min(n_rows, stop)
    for row_idx in range(start, stop):
        row: dict[str, float | None] = {}
        for channel in channels:
            value = channel.values[row_idx] if row_idx < len(channel.values) else None
            row[channel.descriptor.canonical_name] = None if value is None else float(value)
        rows.append(row)
    return rows


def build_parser_inspection_report(record: ParsedSampleRecord, *, head: int = 5, tail: int = 5) -> dict[str, Any]:
    """Return an audit-friendly snapshot of what the parser currently detected.

    This is deliberately JSON-serialisable so it can be pasted into logs,
    attached to issues, or sent back for debugging.
    """
    channels = sorted(record.channels.all_channels(), key=lambda ch: ch.source_column_index)
    n_rows = max((len(ch.values) for ch in channels), default=0)

    header_flags = {
        token.normalized_key or token.raw_key: {
            "raw_key": token.raw_key,
            "value": token.coerced_value_text or token.raw_value,
            "unit": token.raw_unit,
            "source_line_index": token.source_line_index,
        }
        for token in record.preamble_tokens
    }

    channel_flags = [
        {
            "column_index": ch.descriptor.column_index,
            "original_name": ch.descriptor.original_name,
            "original_unit": ch.descriptor.original_unit_text,
            "family": ch.descriptor.family,
            "ordinal": ch.descriptor.ordinal,
            "canonical_name": ch.descriptor.canonical_name,
            "alias": ch.descriptor.alias,
            "canonical_unit": ch.canonical_unit,
            "non_null_count": ch.non_null_count,
            "null_count": ch.null_count,
            "notes": list(ch.notes),
            "bad_cells": [
                {
                    "source_row_index": bad.source_row_index,
                    "data_row_index": bad.data_row_index,
                    "source_column_index": bad.source_column_index,
                    "raw_value": bad.raw_value,
                    "reason": bad.reason,
                    "diagnostic_code": bad.diagnostic_code,
                    "severity": bad.severity,
                    "parse_rule_id": bad.parse_rule_id,
                    "detected_decimal_separator": bad.detected_decimal_separator,
                    "detected_thousands_separator": bad.detected_thousands_separator,
                }
                for bad in ch.bad_cells
            ],
            "parse_profile": None
            if ch.parse_profile is None
            else {
                "expected_kind": ch.parse_profile.expected_kind,
                "numeric_policy_id": ch.parse_profile.numeric_policy_id,
                "decimal_separator": ch.parse_profile.decimal_separator,
                "thousands_separator": ch.parse_profile.thousands_separator,
                "confidence": ch.parse_profile.confidence,
                "notes": list(ch.parse_profile.notes),
            },
            "parse_quality": _parse_quality(ch),
            "parsed_examples": [
                {
                    "raw_value": cell.raw_value,
                    "normalized_text": cell.normalized_text,
                    "value": cell.value,
                    "status": cell.status,
                    "parse_rule_id": cell.parse_rule_id,
                    "diagnostic_code": cell.diagnostic_code,
                }
                for cell in ch.parsed_cells[:3]
            ],
        }
        for ch in channels
    ]

    return {
        "source_file": str(record.source_file),
        "sample_id": record.sample_id,
        "validity_hint": record.validity_hint,
        "validity_hint_source": record.validity_hint_source,
        "sniff": {
            "delimiter": record.file_sniff.delimiter,
            "encoding": record.file_sniff.encoding,
            "has_preamble": record.file_sniff.has_preamble,
            "likely_header_row_index": record.file_sniff.likely_header_row_index,
            "total_lines": record.file_sniff.total_lines,
        },
        "layout": {
            "header_row_index": record.table_layout.header_row_index,
            "units_row_index": record.table_layout.units_row_index,
            "data_start_row_index": record.table_layout.data_start_row_index,
            "detected_column_count": record.table_layout.detected_column_count,
        },
        "header_flags": header_flags,
        "raw_header": list(record.raw_header),
        "raw_units_row": list(record.raw_units_row) if record.raw_units_row is not None else None,
        "channel_flags": channel_flags,
        "row_count": n_rows,
        "data_head": _rows_from_record(record, 0, head),
        "data_tail": _rows_from_record(record, max(0, n_rows - tail), n_rows),
        "parse_warnings": list(record.parse_warnings),
        "cell_diagnostics": [
            {
                "code": diagnostic.code,
                "severity": diagnostic.severity,
                "message": diagnostic.message,
                "source_row_index": diagnostic.source_row_index,
                "data_row_index": diagnostic.data_row_index,
                "source_column_index": diagnostic.source_column_index,
                "raw_value": diagnostic.raw_value,
                "parse_rule_id": diagnostic.parse_rule_id,
            }
            for diagnostic in record.cell_diagnostics
        ],
        "parser_policy_snapshot": record.parser_policy_snapshot,
    }


def _parse_quality(channel: Any) -> dict[str, int]:
    counts = {"ok": 0, "missing": 0, "ambiguous": 0, "invalid": 0, "unsupported": 0}
    for cell in channel.parsed_cells:
        counts[cell.status] = counts.get(cell.status, 0) + 1
    return counts
