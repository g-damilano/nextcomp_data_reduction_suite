from __future__ import annotations

import pytest

from parsing.models import ColumnParseProfile
from parsing.parsers.numeric_value_parser import parse_cell_value


def profile(
    *,
    policy_id: str = "numeric.en.comma_thousands_dot_decimal",
    decimal: str | None = ".",
    thousands: str | None = ",",
    allow_unit_suffix: bool = False,
) -> ColumnParseProfile:
    return ColumnParseProfile(
        source_column_index=1,
        original_name="Load",
        family="load",
        expected_kind="numeric",
        declared_unit="kN",
        canonical_unit="N",
        numeric_policy_id=policy_id,
        decimal_separator=decimal,
        thousands_separator=thousands,
        missing_tokens=("", "NA", "N/A", "NULL", "null", "—", "-"),
        strict_numeric=True,
        allow_unit_suffix=allow_unit_suffix,
        confidence=1.0,
    )


@pytest.mark.parametrize(
    ("raw", "normalized", "value"),
    [
        ("1234", "1234", 1234.0),
        ("1234.56", "1234.56", 1234.56),
        ("-1234.56", "-1234.56", -1234.56),
        ("+1234.56", "+1234.56", 1234.56),
        ("1.23E+04", "1.23E+04", 12300.0),
        ("1,234", "1234", 1234.0),
        ("1,234.56", "1234.56", 1234.56),
        ("1,234,567.89", "1234567.89", 1234567.89),
        ("−1,234.5", "-1234.5", -1234.5),
    ],
)
def test_numeric_parser_accepts_explicit_en_policy(raw: str, normalized: str, value: float) -> None:
    cell = parse_cell_value(
        raw,
        source_row_index=2,
        data_row_index=0,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(),
    )

    assert cell.status == "ok"
    assert cell.raw_value == raw
    assert cell.normalized_text == normalized
    assert cell.value == pytest.approx(value)
    assert cell.parse_rule_id == "numeric.en.comma_thousands_dot_decimal"


def test_numeric_parser_accepts_explicit_eu_policy() -> None:
    cell = parse_cell_value(
        "1.234,56",
        source_row_index=2,
        data_row_index=0,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(policy_id="numeric.eu.dot_thousands_comma_decimal", decimal=",", thousands="."),
    )

    assert cell.status == "ok"
    assert cell.normalized_text == "1234.56"
    assert cell.value == pytest.approx(1234.56)
    assert cell.detected_decimal_separator == ","
    assert cell.detected_thousands_separator == "."


def test_numeric_parser_rejects_malformed_grouping_under_en_policy() -> None:
    cell = parse_cell_value(
        "1,23,4",
        source_row_index=2,
        data_row_index=0,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(),
    )

    assert cell.status == "invalid"
    assert cell.diagnostic_code == "invalid_thousands_grouping"
    assert cell.value is None


def test_numeric_parser_marks_unprofiled_separator_role_ambiguous() -> None:
    cell = parse_cell_value(
        "1,234",
        source_row_index=2,
        data_row_index=0,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(policy_id="numeric.unresolved", decimal=None, thousands=None),
    )

    assert cell.status == "ambiguous"
    assert cell.diagnostic_code == "ambiguous_separator_role"
    assert cell.candidate_interpretations


def test_numeric_parser_distinguishes_missing_text_and_unit_suffixes() -> None:
    missing = parse_cell_value(
        "NA",
        source_row_index=2,
        data_row_index=0,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(),
    )
    text = parse_cell_value(
        "sensor error",
        source_row_index=3,
        data_row_index=1,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(),
    )
    unit = parse_cell_value(
        "12.3 kN",
        source_row_index=4,
        data_row_index=2,
        source_column_index=1,
        original_name="Load",
        family="load",
        profile=profile(policy_id="numeric.plain_dot_decimal", decimal=".", thousands=None, allow_unit_suffix=True),
    )

    assert missing.status == "missing"
    assert missing.diagnostic_code == "missing_token"
    assert text.status == "invalid"
    assert text.diagnostic_code == "text_in_numeric_column"
    assert unit.status == "ok"
    assert unit.detected_unit == "kN"
    assert unit.value == pytest.approx(12.3)
