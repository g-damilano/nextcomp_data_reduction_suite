from __future__ import annotations

from parsing.columns.column_parse_profile_builder import ColumnParseProfileBuilder
from parsing.models import ColumnDescriptor


def descriptor(family: str = "load") -> ColumnDescriptor:
    return ColumnDescriptor(
        column_index=1,
        original_name="Load",
        original_unit_text="kN",
        family=family,
        ordinal=1,
        canonical_name="load_1",
        canonical_unit="N",
    )


def test_profile_builder_detects_stable_en_grouping() -> None:
    profile = ColumnParseProfileBuilder().build(
        descriptor(),
        ["1,234.5", "2,345.6", "3,456.7"],
        delimiter=";",
    )

    assert profile.expected_kind == "numeric"
    assert profile.numeric_policy_id == "numeric.en.comma_thousands_dot_decimal"
    assert profile.decimal_separator == "."
    assert profile.thousands_separator == ","
    assert profile.confidence >= 0.9


def test_profile_builder_detects_stable_eu_grouping() -> None:
    profile = ColumnParseProfileBuilder().build(
        descriptor(),
        ["1.234,5", "2.345,6", "3.456,7"],
        delimiter=";",
    )

    assert profile.numeric_policy_id == "numeric.eu.dot_thousands_comma_decimal"
    assert profile.decimal_separator == ","
    assert profile.thousands_separator == "."


def test_profile_builder_detects_decimal_comma_when_delimiter_is_not_comma() -> None:
    profile = ColumnParseProfileBuilder().build(
        descriptor(),
        ["1234,5", "2345,6", "3456,7"],
        delimiter="\t",
    )

    assert profile.numeric_policy_id == "numeric.comma_decimal"
    assert profile.decimal_separator == ","
    assert profile.thousands_separator is None


def test_profile_builder_marks_mixed_conventions_unresolved() -> None:
    profile = ColumnParseProfileBuilder().build(
        descriptor(),
        ["1,234.5", "2.345,6", "3456,7"],
        delimiter=";",
    )

    assert profile.numeric_policy_id == "numeric.mixed.unresolved"
    assert profile.confidence < 0.5
    assert "mixed_numeric_conventions" in profile.notes


def test_profile_builder_marks_record_id_as_non_numeric() -> None:
    profile = ColumnParseProfileBuilder().build(
        descriptor(family="record_id"),
        ["1", "2"],
        delimiter=",",
    )

    assert profile.expected_kind == "id"
    assert profile.numeric_policy_id is None
