from __future__ import annotations

import csv
import re
from pathlib import Path

from parsing.columns.column_parse_profile_builder import ColumnParseProfileBuilder
from parsing.columns.family_classifier import normalize_unit_text
from parsing.models import (
    BadCellRecord,
    CellParseDiagnostic,
    ChannelBundle,
    ChannelRecord,
    ColumnDescriptor,
    ParsedCellRecord,
    TableLayoutRecord,
)
from parsing.parsers.numeric_value_parser import parse_cell_value


_NUMERIC_BAD_CELL_FAMILIES = {
    "load",
    "extension",
    "displacement",
    "strain",
    "stress",
    "time",
    "temperature",
}
def _unit_scale(descriptor: ColumnDescriptor) -> float:
    unit = normalize_unit_text(descriptor.original_unit_text)
    target = normalize_unit_text(descriptor.canonical_unit)
    if descriptor.family == "load" and unit == "kN" and target == "N":
        return 1000.0
    if descriptor.family == "strain" and unit == "usn" and target == "mm/mm":
        return 1e-6
    if descriptor.family == "strain" and unit == "%" and target == "mm/mm":
        return 0.01
    if descriptor.family == "stress" and unit == "Pa" and target == "MPa":
        return 1e-6
    if descriptor.family == "stress" and unit == "kPa" and target == "MPa":
        return 0.001
    if descriptor.family in {"extension", "displacement"} and unit == "in" and target == "mm":
        return 25.4
    return 1.0


class NumericIngestionPass:
    """Pass P5/P6: ingest numeric rows and build channel bundles."""

    def run(
        self,
        file_path: str | Path,
        layout: TableLayoutRecord,
        descriptors: list[ColumnDescriptor],
        *,
        delimiter: str = ",",
        quotechar: str = '"',
        encoding: str = "utf-8-sig",
    ) -> ChannelBundle:
        path = Path(file_path)
        rows: list[tuple[int, list[str], bool]] = []
        parsed_columns: list[list[ParsedCellRecord]] = [[] for _ in descriptors]
        bad_cells_by_column: list[list[BadCellRecord]] = [[] for _ in descriptors]
        with path.open("r", encoding=encoding, newline="") as fh:
            reader = csv.reader(fh, delimiter=delimiter, quotechar=quotechar)
            for idx, row in enumerate(reader):
                if idx < layout.data_start_row_index:
                    continue
                row = _split_numeric_row(row, expected_columns=len(descriptors))
                if not row or all(not cell.strip() for cell in row):
                    continue
                row_width_conflict = len(row) != len(descriptors)
                rows.append((idx, row, row_width_conflict))

        profile_builder = ColumnParseProfileBuilder()
        profiles = [
            profile_builder.build(
                descriptor,
                [
                    row[descriptor.column_index].strip()
                    for _idx, row, conflict in rows
                    if not conflict and descriptor.column_index < len(row)
                ],
                delimiter=delimiter,
            )
            for descriptor in descriptors
        ]

        for idx, row, row_width_conflict in rows:
            data_row_index = idx - layout.data_start_row_index
            for col_idx, descriptor in enumerate(descriptors):
                cell = row[col_idx].strip() if col_idx < len(row) else ""
                profile = profiles[col_idx]
                if row_width_conflict:
                    parsed_cell = ParsedCellRecord(
                        source_row_index=idx,
                        data_row_index=data_row_index,
                        source_column_index=descriptor.column_index,
                        original_name=descriptor.original_name,
                        family=descriptor.family,
                        raw_value=cell,
                        normalized_text=None,
                        value=None,
                        status="invalid",
                        parse_rule_id="row.structure",
                        diagnostic_code="row_width_inconsistent",
                        diagnostic_message="Row width did not match the detected table layout.",
                        expected_kind=profile.expected_kind,
                    )
                else:
                    parsed_cell = parse_cell_value(
                        cell,
                        source_row_index=idx,
                        data_row_index=data_row_index,
                        source_column_index=descriptor.column_index,
                        original_name=descriptor.original_name,
                        family=descriptor.family,
                        profile=profile,
                    )
                parsed_columns[col_idx].append(parsed_cell)

                if parsed_cell.status != "ok" and descriptor.family in _NUMERIC_BAD_CELL_FAMILIES:
                    bad_cells_by_column[col_idx].append(
                        BadCellRecord(
                            source_row_index=idx,
                            data_row_index=data_row_index,
                            source_column_index=descriptor.column_index,
                            original_name=descriptor.original_name,
                            family=descriptor.family,
                            raw_value=cell,
                            reason=parsed_cell.diagnostic_code or parsed_cell.status,
                            diagnostic_code=parsed_cell.diagnostic_code or parsed_cell.status,
                            severity="review_required" if parsed_cell.status == "ambiguous" else "error",
                            expected_kind=parsed_cell.expected_kind,
                            parse_rule_id=parsed_cell.parse_rule_id,
                            detected_decimal_separator=parsed_cell.detected_decimal_separator,
                            detected_thousands_separator=parsed_cell.detected_thousands_separator,
                            detected_unit=parsed_cell.detected_unit,
                        )
                    )

        bundle = ChannelBundle()
        for descriptor, parsed_cells, bad_cells, profile in zip(
            descriptors,
            parsed_columns,
            bad_cells_by_column,
            profiles,
        ):
            values = [
                None
                if cell.status != "ok" or not isinstance(cell.value, float)
                else cell.value * _unit_scale(descriptor)
                for cell in parsed_cells
            ]
            non_null_count = sum(value is not None for value in values)
            null_count = len(values) - non_null_count
            notes = ()
            if bad_cells:
                notes = (f"{len(bad_cells)} missing or unparseable numeric cell(s) retained as None.",)
            channel = ChannelRecord(
                descriptor=descriptor,
                values=values,
                source_column_index=descriptor.column_index,
                non_null_count=non_null_count,
                null_count=null_count,
                original_unit_text=descriptor.original_unit_text,
                canonical_unit=descriptor.canonical_unit,
                notes=notes,
                bad_cells=tuple(bad_cells),
                parsed_cells=tuple(parsed_cells),
                parse_profile=profile,
            )
            target_name = f"{descriptor.family}_channels"
            if hasattr(bundle, target_name):
                getattr(bundle, target_name).append(channel)
            else:
                bundle.unknown_channels.append(channel)
        return bundle


def diagnostics_from_channels(bundle: ChannelBundle) -> tuple[CellParseDiagnostic, ...]:
    diagnostics: list[CellParseDiagnostic] = []
    for channel in bundle.all_channels():
        for cell in channel.parsed_cells:
            if cell.status == "ok":
                continue
            diagnostics.append(
                CellParseDiagnostic(
                    code=cell.diagnostic_code or cell.status,
                    severity="review_required" if cell.status == "ambiguous" else "error",
                    message=cell.diagnostic_message or cell.status,
                    source_row_index=cell.source_row_index,
                    data_row_index=cell.data_row_index,
                    source_column_index=cell.source_column_index,
                    original_name=cell.original_name,
                    family=cell.family,
                    raw_value=cell.raw_value,
                    expected_kind=cell.expected_kind,
                    parse_rule_id=cell.parse_rule_id,
                    detected_decimal_separator=cell.detected_decimal_separator,
                    detected_thousands_separator=cell.detected_thousands_separator,
                    detected_unit=cell.detected_unit,
                )
            )
    return tuple(diagnostics)


def _split_numeric_row(row: list[str], *, expected_columns: int) -> list[str]:
    if len(row) != 1 or expected_columns <= 1:
        return row
    text = row[0].strip()
    if not text:
        return row
    parts = re.split(r"\s+", text)
    return parts if len(parts) >= expected_columns else row
