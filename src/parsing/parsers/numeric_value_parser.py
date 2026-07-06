from __future__ import annotations

import math
import re

from parsing.models import ColumnParseProfile, ParsedCellRecord


_EN_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?([eE][+-]?\d+)?$")
_EU_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+(,\d+)?([eE][+-]?\d+)?$")
_PLAIN_DOT_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_PLAIN_COMMA_RE = re.compile(r"^[+-]?\d+,\d+([eE][+-]?\d+)?$")
_UNIT_SUFFIX_RE = re.compile(r"^(?P<number>.+?)(?P<unit>[A-Za-z%][A-Za-z0-9%/^\-]*)$")


def parse_cell_value(
    raw_value: str,
    *,
    source_row_index: int,
    data_row_index: int,
    source_column_index: int,
    original_name: str,
    family: str,
    profile: ColumnParseProfile,
) -> ParsedCellRecord:
    raw = raw_value
    text = raw.strip().strip('"').strip("'").replace(chr(0x00A0), " ").replace("\u202f", " ")
    text = text.replace("\u2212", "-")

    if text in profile.missing_tokens or text.casefold() in {item.casefold() for item in profile.missing_tokens}:
        return _record(
            raw,
            None,
            None,
            "missing",
            "numeric.missing",
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code="missing_token",
            diagnostic_message="Cell matched the configured missing-token policy.",
        )

    if profile.expected_kind != "numeric":
        return _record(
            raw,
            text,
            text,
            "ok",
            "text.preserved",
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
        )

    numeric_text, detected_unit, unit_error = _split_unit_suffix(text, profile)
    if unit_error is not None:
        return _record(
            raw,
            None,
            None,
            "invalid",
            profile.numeric_policy_id or "numeric.unresolved",
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code=unit_error,
            diagnostic_message="Cell has a unit suffix that is not allowed or not compatible.",
            detected_unit=detected_unit,
        )

    compact = numeric_text.replace(" ", "") if profile.thousands_separator != " " else numeric_text
    if not compact:
        return _record(
            raw,
            None,
            None,
            "missing",
            "numeric.missing",
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code="missing_token",
        )

    normalized, rule_id, decimal, thousands, diagnostic = _normalize_numeric_text(compact, profile)
    if diagnostic is not None:
        status = "ambiguous" if diagnostic == "ambiguous_separator_role" else "invalid"
        candidates = (
            {"profile": "comma_thousands", "normalized_text": compact.replace(",", "")},
            {"profile": "comma_decimal", "normalized_text": compact.replace(",", ".")},
        ) if diagnostic == "ambiguous_separator_role" and "," in compact and "." not in compact else ()
        return _record(
            raw,
            None,
            None,
            status,
            rule_id,
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code=diagnostic,
            diagnostic_message=_diagnostic_message(diagnostic),
            detected_decimal_separator=decimal,
            detected_thousands_separator=thousands,
            detected_unit=detected_unit,
            candidate_interpretations=candidates,
        )

    try:
        value = float(normalized)
    except (TypeError, ValueError):
        return _record(
            raw,
            None,
            None,
            "invalid",
            rule_id,
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code="text_in_numeric_column",
            diagnostic_message="Cell text could not be converted after policy normalization.",
            detected_decimal_separator=decimal,
            detected_thousands_separator=thousands,
            detected_unit=detected_unit,
        )

    if not math.isfinite(value):
        return _record(
            raw,
            None,
            None,
            "invalid",
            rule_id,
            source_row_index,
            data_row_index,
            source_column_index,
            original_name,
            family,
            profile,
            diagnostic_code="nonfinite_numeric_value",
            diagnostic_message="Cell converted to a non-finite numeric value.",
            detected_decimal_separator=decimal,
            detected_thousands_separator=thousands,
            detected_unit=detected_unit,
        )

    return _record(
        raw,
        normalized,
        value,
        "ok",
        rule_id,
        source_row_index,
        data_row_index,
        source_column_index,
        original_name,
        family,
        profile,
        detected_decimal_separator=decimal,
        detected_thousands_separator=thousands,
        detected_unit=detected_unit,
    )


def _normalize_numeric_text(text: str, profile: ColumnParseProfile) -> tuple[str | None, str, str | None, str | None, str | None]:
    policy_id = profile.numeric_policy_id or "numeric.unresolved"
    decimal = profile.decimal_separator
    thousands = profile.thousands_separator

    if policy_id == "numeric.mixed.unresolved":
        return None, policy_id, None, None, "mixed_numeric_conventions"

    if decimal == "." and thousands == ",":
        if "," in text and not _EN_GROUPED_RE.fullmatch(text):
            return None, policy_id, ".", ",", "invalid_thousands_grouping"
        normalized = text.replace(",", "")
        return normalized, policy_id, "." if "." in normalized else None, "," if "," in text else None, None

    if decimal == "," and thousands == ".":
        if "." in text and not _EU_GROUPED_RE.fullmatch(text):
            return None, policy_id, ",", ".", "invalid_thousands_grouping"
        normalized = text.replace(".", "").replace(",", ".")
        return normalized, policy_id, "," if "," in text else None, "." if "." in text else None, None

    if decimal == "," and thousands is None:
        if "." in text:
            return None, policy_id, ",", None, "unsupported_thousands_separator"
        if "," not in text or _PLAIN_COMMA_RE.fullmatch(text):
            return text.replace(",", "."), policy_id, "," if "," in text else None, None, None
        return None, policy_id, ",", None, "invalid_thousands_grouping"

    if decimal == "." and thousands is None:
        if "," in text:
            return None, policy_id, ".", None, "ambiguous_separator_role"
        if _PLAIN_DOT_RE.fullmatch(text):
            return text, policy_id, "." if "." in text else None, None, None
        return None, policy_id, ".", None, "text_in_numeric_column"

    if "," in text and "." in text:
        if text.rfind(",") < text.rfind(".") and _EN_GROUPED_RE.fullmatch(text):
            return text.replace(",", ""), "numeric.en.comma_thousands_dot_decimal", ".", ",", None
        if text.rfind(".") < text.rfind(",") and _EU_GROUPED_RE.fullmatch(text):
            return text.replace(".", "").replace(",", "."), "numeric.eu.dot_thousands_comma_decimal", ",", ".", None
        return None, "numeric.unresolved", None, None, "mixed_numeric_conventions"

    if "," in text:
        if _EN_GROUPED_RE.fullmatch(text) and _PLAIN_COMMA_RE.fullmatch(text):
            return None, "numeric.unresolved", None, None, "ambiguous_separator_role"
        if _EN_GROUPED_RE.fullmatch(text):
            return text.replace(",", ""), "numeric.en.comma_thousands_dot_decimal", None, ",", None
        if _PLAIN_COMMA_RE.fullmatch(text):
            return text.replace(",", "."), "numeric.comma_decimal", ",", None, None
        return None, "numeric.unresolved", None, ",", "invalid_thousands_grouping"

    if "." in text and _EU_GROUPED_RE.fullmatch(text):
        return None, "numeric.unresolved", None, None, "ambiguous_separator_role"

    if _PLAIN_DOT_RE.fullmatch(text):
        return text, "numeric.plain_dot_decimal", "." if "." in text else None, None, None

    return None, "numeric.unresolved", None, None, "text_in_numeric_column"


def _split_unit_suffix(text: str, profile: ColumnParseProfile) -> tuple[str, str | None, str | None]:
    if not text or text[-1].isdigit():
        return text, None, None
    match = _UNIT_SUFFIX_RE.fullmatch(text)
    if match is None:
        return text, None, None
    number = match.group("number").strip()
    unit = match.group("unit").strip()
    if not re.search(r"\d", number):
        return text, None, None
    if not unit:
        return text, None, None
    if not profile.allow_unit_suffix:
        return number, unit, "unit_suffix_not_allowed"
    allowed = {
        _normalize_unit_token(item)
        for item in (profile.declared_unit, profile.canonical_unit)
        if item
    }
    if allowed and _normalize_unit_token(unit) not in allowed:
        return number, unit, "unit_suffix_incompatible"
    if not allowed:
        return number, unit, "unit_suffix_unrecognized"
    return number, unit, None


def _normalize_unit_token(unit: str) -> str:
    return unit.strip().strip("()").casefold()


def _record(
    raw_value: str,
    normalized_text: str | None,
    value: float | str | None,
    status: str,
    parse_rule_id: str,
    source_row_index: int,
    data_row_index: int,
    source_column_index: int,
    original_name: str,
    family: str,
    profile: ColumnParseProfile,
    *,
    diagnostic_code: str | None = None,
    diagnostic_message: str | None = None,
    detected_decimal_separator: str | None = None,
    detected_thousands_separator: str | None = None,
    detected_unit: str | None = None,
    candidate_interpretations: tuple[dict[str, object], ...] = (),
) -> ParsedCellRecord:
    return ParsedCellRecord(
        source_row_index=source_row_index,
        data_row_index=data_row_index,
        source_column_index=source_column_index,
        original_name=original_name,
        family=family,
        raw_value=raw_value,
        normalized_text=normalized_text,
        value=value,
        status=status,  # type: ignore[arg-type]
        parse_rule_id=parse_rule_id,
        diagnostic_code=diagnostic_code,
        diagnostic_message=diagnostic_message,
        expected_kind=profile.expected_kind,
        detected_decimal_separator=detected_decimal_separator,
        detected_thousands_separator=detected_thousands_separator,
        detected_unit=detected_unit,
        candidate_interpretations=candidate_interpretations,  # type: ignore[arg-type]
    )


def _diagnostic_message(code: str) -> str:
    messages = {
        "ambiguous_separator_role": "Separator role is ambiguous under the active parse profile.",
        "invalid_thousands_grouping": "Thousands separators do not match strict grouping rules.",
        "mixed_numeric_conventions": "Column contains mixed numeric conventions.",
        "unsupported_thousands_separator": "The active parse profile does not support this thousands separator.",
        "text_in_numeric_column": "Text appeared where a numeric value was expected.",
    }
    return messages.get(code, code.replace("_", " "))
