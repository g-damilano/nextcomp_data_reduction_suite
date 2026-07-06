from __future__ import annotations

from pathlib import Path

import pytest

from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parsing" / "numeric_formats"


@pytest.mark.parametrize(
    ("fixture_name", "expected_delimiter"),
    [
        ("comma_thousands_semicolon_delimited.csv", ";"),
        ("comma_thousands_tab_delimited.tsv", "\t"),
        ("comma_delimited_quoted_thousands.csv", ","),
    ],
)
def test_structural_delimiter_is_resolved_before_numeric_separator(
    fixture_name: str,
    expected_delimiter: str,
) -> None:
    record = DelimitedMechanicalCsvParser(FIXTURES / fixture_name).parse()
    load = record.channels.load_channels[0]

    assert record.file_sniff.delimiter == expected_delimiter
    assert load.values == pytest.approx([1234560.0, 2345670.0])
    assert load.parsed_cells[0].raw_value == "1,234.56"
    assert load.parsed_cells[0].normalized_text == "1234.56"
    assert load.parsed_cells[0].parse_rule_id == "numeric.en.comma_thousands_dot_decimal"
    assert load.parse_profile is not None
    assert load.parse_profile.thousands_separator == ","


def test_comma_delimited_unquoted_thousands_conflict_is_not_silently_reassembled() -> None:
    record = DelimitedMechanicalCsvParser(FIXTURES / "comma_delimited_unquoted_thousands_invalid.csv").parse()
    load = record.channels.load_channels[0]

    assert record.file_sniff.delimiter == ","
    assert load.values == [None]
    assert load.parsed_cells[0].status == "invalid"
    assert load.parsed_cells[0].diagnostic_code == "row_width_inconsistent"
    assert any(diagnostic.code == "row_width_inconsistent" for diagnostic in record.cell_diagnostics)


def test_decimal_comma_profile_parses_after_semicolon_delimiter() -> None:
    record = DelimitedMechanicalCsvParser(FIXTURES / "decimal_comma_eu.csv").parse()
    load = record.channels.load_channels[0]

    assert record.file_sniff.delimiter == ";"
    assert load.parse_profile is not None
    assert load.parse_profile.numeric_policy_id == "numeric.comma_decimal"
    assert load.parsed_cells[0].normalized_text == "1234.56"
    assert load.values == pytest.approx([1234560.0, 2345670.0])
