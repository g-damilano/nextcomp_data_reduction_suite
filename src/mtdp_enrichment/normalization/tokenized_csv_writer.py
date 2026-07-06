from __future__ import annotations

import csv
import io
from collections import OrderedDict
from typing import Mapping

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.normalization.unit_normalizer import NormalizationResult
from mtdp_enrichment.package.schema import MTDPSchema


class TokenizedCsvWriter:
    """Write normalized parser output plus enrichment fields as tokenized CSV."""

    def write_string(
        self,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        normalized_fields: Mapping[str, EnrichedFieldValue],
        normalized_table: NormalizationResult,
    ) -> str:
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")

        for row in self._token_rows(parsed, schema, normalized_fields):
            writer.writerow(row)
        writer.writerow([])

        writer.writerow([column.header for column in normalized_table.columns])
        writer.writerow([f"({column.unit})" if column.unit else "" for column in normalized_table.columns])

        data_writer = csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_ALL)
        row_count = normalized_table.row_count
        for row_index in range(row_count):
            row: list[str] = []
            for column in normalized_table.columns:
                value = column.values[row_index] if row_index < len(column.values) else None
                row.append("" if value is None else _format_number(value))
            data_writer.writerow(row)

        return buffer.getvalue()

    def _token_rows(
        self,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        normalized_fields: Mapping[str, EnrichedFieldValue],
    ) -> list[list[str]]:
        rows: "OrderedDict[str, list[str]]" = OrderedDict()

        for token in parsed.preamble_tokens:
            key = token.raw_key.strip()
            if not key:
                continue
            field = schema.field_by_token(key)
            if field is not None and field.storage.location != "token_preamble":
                continue
            row = [token.raw_key, token.coerced_value_text or token.raw_value]
            if token.raw_unit:
                row.append(token.raw_unit)
            rows[key.casefold()] = row

        for definition in schema.fields:
            if definition.field_id not in normalized_fields:
                continue
            if definition.storage.location != "token_preamble" or not definition.storage.token:
                continue

            field_value = normalized_fields[definition.field_id]
            value = field_value.value
            if value in (None, ""):
                continue
            row = [definition.storage.token, _format_token_value(value)]
            if field_value.unit:
                row.append(field_value.unit)
            rows[definition.storage.token.casefold()] = row

        return list(rows.values())


def _format_token_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return _format_number(value)
    return str(value)


def _format_number(value: float) -> str:
    text = f"{value:.15g}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
