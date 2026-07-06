from __future__ import annotations

from pathlib import Path

import pytest

from parsing.inspection import build_parser_inspection_report
from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parsing" / "numeric_formats"


def test_parser_preserves_raw_normalized_profile_and_diagnostics_for_every_cell() -> None:
    record = DelimitedMechanicalCsvParser(FIXTURES / "blank_and_missing_tokens.csv").parse()
    load = record.channels.load_channels[0]

    assert len(load.parsed_cells) == 3
    assert [cell.raw_value for cell in load.parsed_cells] == ["", "NA", "null"]
    assert [cell.status for cell in load.parsed_cells] == ["missing", "missing", "missing"]
    assert [cell.diagnostic_code for cell in load.parsed_cells] == [
        "missing_token",
        "missing_token",
        "missing_token",
    ]
    assert load.values == [None, None, None]
    assert load.parse_profile is not None
    assert record.column_parse_profiles
    assert len(record.cell_diagnostics) >= 3


def test_parser_records_text_and_malformed_numeric_cells_as_structured_bad_cells() -> None:
    text_record = DelimitedMechanicalCsvParser(FIXTURES / "text_in_numeric_column.csv").parse()
    malformed_record = DelimitedMechanicalCsvParser(FIXTURES / "malformed_grouping.csv").parse()

    text_load = text_record.channels.load_channels[0]
    malformed_load = malformed_record.channels.load_channels[0]

    assert [cell.status for cell in text_load.parsed_cells] == ["invalid", "invalid"]
    assert [cell.diagnostic_code for cell in text_load.parsed_cells] == [
        "text_in_numeric_column",
        "text_in_numeric_column",
    ]
    assert text_load.bad_cells[0].diagnostic_code == "text_in_numeric_column"
    assert [cell.status for cell in malformed_load.parsed_cells] == ["invalid", "invalid", "invalid"]
    assert {cell.diagnostic_code for cell in malformed_load.parsed_cells} == {
        "mixed_numeric_conventions"
    }


def test_inspection_report_exposes_parse_profiles_and_quality() -> None:
    record = DelimitedMechanicalCsvParser(FIXTURES / "mixed_locale_ambiguous.csv").parse()
    report = build_parser_inspection_report(record, head=2, tail=0)
    load_flag = next(item for item in report["channel_flags"] if item["canonical_name"] == "load_1")

    assert load_flag["parse_profile"]["numeric_policy_id"] == "numeric.mixed.unresolved"
    assert load_flag["parse_quality"]["invalid"] == 3
    assert {item["code"] for item in report["cell_diagnostics"]} == {"mixed_numeric_conventions"}


def test_unicode_minus_and_scientific_notation_remain_auditable() -> None:
    signed = DelimitedMechanicalCsvParser(FIXTURES / "signed_unicode_minus.csv").parse()
    scientific = DelimitedMechanicalCsvParser(FIXTURES / "scientific_notation.csv").parse()

    assert signed.channels.load_channels[0].values == pytest.approx([-1234500.0, 2345500.0])
    assert signed.channels.load_channels[0].parsed_cells[0].raw_value == "−1,234.5"
    assert signed.channels.load_channels[0].parsed_cells[0].normalized_text == "-1234.5"
    assert scientific.channels.load_channels[0].values == pytest.approx([12300000.0, -1000000.0])
