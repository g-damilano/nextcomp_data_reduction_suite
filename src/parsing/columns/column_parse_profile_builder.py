from __future__ import annotations

import re

from parsing.models import ColumnDescriptor, ColumnParseProfile


_NUMERIC_FAMILIES = {"load", "extension", "displacement", "strain", "stress", "time", "temperature"}
_ID_FAMILIES = {"record_id"}
_TIMESTAMP_FAMILIES = {"timestamp"}
_MISSING_TOKENS = ("", "NA", "N/A", "NULL", "null", "—", "-")
_EN_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?([eE][+-]?\d+)?$")
_EU_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+(,\d+)?([eE][+-]?\d+)?$")
_COMMA_DECIMAL_RE = re.compile(r"^[+-]?\d+,\d+([eE][+-]?\d+)?$")
_DOT_DECIMAL_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


class ColumnParseProfileBuilder:
    def build(
        self,
        descriptor: ColumnDescriptor,
        sample_cells: list[str],
        *,
        delimiter: str,
    ) -> ColumnParseProfile:
        expected_kind = _expected_kind(descriptor.family)
        evidence: list[str] = []
        notes: list[str] = []
        decimal_separator: str | None = None
        thousands_separator: str | None = None
        policy_id: str | None = None
        confidence = 0.6
        strict_numeric = expected_kind == "numeric"

        if expected_kind == "numeric":
            conventions = {_classify_numeric_convention(cell) for cell in sample_cells if _has_content(cell)}
            conventions.discard("missing")
            conventions.discard("text")
            if "en_grouped" in conventions and conventions <= {"en_grouped", "plain_dot", "plain_integer"}:
                decimal_separator = "."
                thousands_separator = ","
                policy_id = "numeric.en.comma_thousands_dot_decimal"
                confidence = 0.95
                evidence.append("sample values use comma thousands with dot decimal")
            elif "eu_grouped" in conventions and conventions <= {"eu_grouped", "comma_decimal", "plain_integer"}:
                decimal_separator = ","
                thousands_separator = "."
                policy_id = "numeric.eu.dot_thousands_comma_decimal"
                confidence = 0.95
                evidence.append("sample values use dot thousands with comma decimal")
            elif "comma_decimal" in conventions and delimiter != "," and conventions <= {"comma_decimal", "plain_integer"}:
                decimal_separator = ","
                thousands_separator = None
                policy_id = "numeric.comma_decimal"
                confidence = 0.9
                evidence.append("sample values use comma decimal and structural delimiter is not comma")
            elif conventions and conventions <= {"plain_dot", "plain_integer"}:
                decimal_separator = "."
                thousands_separator = None
                policy_id = "numeric.plain_dot_decimal"
                confidence = 0.85
                evidence.append("sample values use plain dot-decimal or integer values")
            elif not conventions:
                decimal_separator = "."
                thousands_separator = None
                policy_id = "numeric.plain_dot_decimal"
                confidence = 0.5
                notes.append("no numeric sample evidence; using conservative plain dot-decimal policy")
            else:
                policy_id = "numeric.mixed.unresolved"
                confidence = 0.2
                notes.append("mixed_numeric_conventions")

        return ColumnParseProfile(
            source_column_index=descriptor.column_index,
            original_name=descriptor.original_name,
            family=descriptor.family,
            expected_kind=expected_kind,
            declared_unit=descriptor.original_unit_text,
            canonical_unit=descriptor.canonical_unit,
            numeric_policy_id=policy_id,
            decimal_separator=decimal_separator,
            thousands_separator=thousands_separator,
            missing_tokens=_MISSING_TOKENS,
            strict_numeric=strict_numeric,
            allow_unit_suffix=False,
            confidence=confidence,
            evidence=tuple(evidence),
            notes=tuple(notes),
        )


def _expected_kind(family: str) -> str:
    if family in _NUMERIC_FAMILIES:
        return "numeric"
    if family in _ID_FAMILIES:
        return "id"
    if family in _TIMESTAMP_FAMILIES:
        return "timestamp"
    if family == "unknown":
        return "unknown"
    return "text"


def _has_content(cell: str) -> bool:
    text = cell.strip().strip('"').strip("'")
    return bool(text) and text.casefold() not in {item.casefold() for item in _MISSING_TOKENS}


def _classify_numeric_convention(cell: str) -> str:
    text = cell.strip().strip('"').strip("'").replace(chr(0x00A0), " ").replace("\u202f", " ")
    text = text.replace("\u2212", "-").replace(" ", "")
    if not text:
        return "missing"
    if _COMMA_DECIMAL_RE.fullmatch(text):
        return "comma_decimal"
    if _DOT_DECIMAL_RE.fullmatch(text):
        return "plain_dot" if "." in text else "plain_integer"
    if _EN_GROUPED_RE.fullmatch(text):
        return "en_grouped"
    if _EU_GROUPED_RE.fullmatch(text):
        return "eu_grouped"
    return "text"
