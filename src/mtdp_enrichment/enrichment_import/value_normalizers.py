from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from mtdp_enrichment.enrichment_import.models import ReconciledMappingRow, ValueTransformResult
from mtdp_enrichment.models import FieldDefinition
from mtdp_enrichment.units import default_unit_normaliser


DATE_FORMATS: tuple[tuple[str, str], ...] = (
    ("yyyy-MM-dd", "%Y-%m-%d"),
    ("dd/MM/yyyy", "%d/%m/%Y"),
    ("d/M/yyyy", "%d/%m/%Y"),
    ("dd-MM-yyyy", "%d-%m-%Y"),
    ("d-M-yyyy", "%d-%m-%Y"),
    ("dd.MM.yyyy", "%d.%m.%Y"),
    ("d.M.yyyy", "%d.%m.%Y"),
)

UNIT_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("mm_min", "mm/min"),
    ("mm_per_min", "mm/min"),
    ("kN", "kN"),
    ("kn", "kN"),
    ("mm2", "mm^2"),
    ("mm_2", "mm^2"),
    ("mm", "mm"),
    ("cm", "cm"),
    ("m", "m"),
    ("N", "N"),
    ("n", "N"),
    ("s", "s"),
)

VALIDITY_MAP = {
    "1": ("Valid", "accepted", False),
    "0": ("Invalid", "rejected", False),
    "true": ("Valid", "accepted", False),
    "false": ("Invalid", "rejected", False),
    "valid": ("Valid", "accepted", False),
    "invalid": ("Invalid", "rejected", False),
    "accepted": ("Valid", "accepted", False),
    "rejected": ("Invalid", "rejected", False),
    "requires_review": ("Requires review", "requires_review", True),
    "requires review": ("Requires review", "requires_review", True),
    "unknown": ("Unknown", "unknown", False),
}


@dataclass(frozen=True, slots=True)
class DateParseResult:
    raw_value: Any
    iso_value: str | None
    detected_format: str | None
    status: str
    requires_confirmation: bool
    warnings: tuple[str, ...] = ()


def parse_date_candidate(value: Any, preferred_locale: str = "en_GB") -> DateParseResult:
    text = str(value).strip()
    if not text:
        return DateParseResult(value, None, None, "requires_date_format", True, ("Empty date.",))
    warnings: list[str] = []
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", text):
        parsed = _parse_with_format(text, "%Y-%m-%d")
        if parsed:
            return DateParseResult(value, parsed.isoformat(), "yyyy-MM-dd", "canonical_mapped", False)
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", text):
        left, right, _year = [int(part) for part in text.split("/")]
        requires_confirmation = left <= 12 and right <= 12
        parsed = _parse_with_format(text, "%d/%m/%Y")
        if parsed:
            if requires_confirmation:
                warnings.append("Slash date is ambiguous; defaulted to dd/MM/yyyy.")
            return DateParseResult(
                value,
                parsed.isoformat(),
                "dd/MM/yyyy",
                "date_format_inferred",
                requires_confirmation,
                tuple(warnings),
            )
    for label, fmt in DATE_FORMATS[3:]:
        parsed = _parse_with_format(text, fmt)
        if parsed:
            return DateParseResult(value, parsed.isoformat(), label, "date_format_inferred", False)
    return DateParseResult(value, None, None, "requires_date_format", True, (f"Unsupported date format: {text}",))


def extract_unit_from_key(source_key: str) -> tuple[str, str | None, str | None]:
    pieces = source_key.split(".")
    leaf = pieces[-1]
    for suffix, unit in UNIT_SUFFIXES:
        for separator in ("_", "-"):
            token = f"{separator}{suffix}"
            if leaf.casefold().endswith(token.casefold()):
                base = leaf[: -len(token)]
                key = ".".join([*pieces[:-1], base])
                return key, default_unit_normaliser.normalize_unit_text(unit), "unit_inferred_from_key"
    return source_key, None, None


def transform_value_for_field(
    *,
    source_key: str,
    raw_value: Any,
    raw_unit: str | None,
    field: FieldDefinition | None,
    selected_unit: str | None = None,
    date_format: str | None = None,
    value_transform: str | None = None,
) -> ValueTransformResult | None:
    if field is None:
        return None
    unit = default_unit_normaliser.normalize_unit_text(selected_unit or raw_unit)
    warnings: list[str] = []
    transform_name = "direct"
    confidence = 0.95
    requires_confirmation = False
    canonical_value = raw_value

    if field.value_map:
        mapped = field.value_map.get(str(raw_value).strip())
        if mapped is None:
            mapped = field.value_map.get(str(raw_value).strip().casefold())
        if mapped is not None:
            canonical_value = mapped
            transform_name = value_transform or "value_map"
            requires_confirmation = True
    elif field.field_id in {"validity", "requires_review"}:
        mapped = validity_value_for_field(raw_value, field.field_id)
        if mapped is not None:
            canonical_value = mapped
            transform_name = "bool_validity_map"
            requires_confirmation = True

    if field.type == "date":
        parsed = parse_date_candidate(raw_value)
        if parsed.iso_value is None:
            warnings.extend(parsed.warnings)
            return ValueTransformResult(
                raw_value,
                raw_value,
                unit,
                None,
                "date_unresolved",
                0.2,
                True,
                tuple(warnings),
            )
        canonical_value = parsed.iso_value
        transform_name = f"{parsed.detected_format} -> ISO"
        requires_confirmation = parsed.requires_confirmation
        warnings.extend(parsed.warnings)

    if field.accepted_units:
        accepted = {default_unit_normaliser.normalize_unit_text(item) for item in field.accepted_units}
        if unit is None:
            requires_confirmation = True
            warnings.append("Unit must be confirmed.")
        elif unit not in accepted:
            warnings.append(f"Unsupported unit: {unit}.")
            requires_confirmation = True
        if selected_unit and raw_unit is None:
            transform_name = "unit_selected"
        elif raw_unit and raw_unit == unit and "unit_inferred" in source_key:
            transform_name = "unit_inferred_from_key"

    canonical_unit = unit
    return ValueTransformResult(
        raw_value=raw_value,
        canonical_value=canonical_value,
        raw_unit=raw_unit,
        canonical_unit=canonical_unit,
        transform_name=transform_name,
        confidence=confidence,
        requires_confirmation=requires_confirmation,
        warnings=tuple(warnings),
    )


def validity_value_for_field(raw_value: Any, field_id: str) -> Any | None:
    key = "unknown" if raw_value is None else str(raw_value).strip().casefold()
    key = key.replace("-", "_")
    mapped = VALIDITY_MAP.get(key)
    if mapped is None:
        return None
    _failure_mode, validity, requires_review = mapped
    if field_id == "validity":
        return validity
    if field_id == "requires_review":
        return requires_review
    return None


def storage_preview(field: FieldDefinition | None) -> str | None:
    if field is None:
        return None
    if field.storage.location == "token_preamble":
        return f"token_preamble / {field.storage.token or field.field_id}"
    if field.storage.location == "provenance":
        return f"provenance / {field.storage.path or field.field_id}"
    if field.storage.location == "dataset_json":
        return f"dataset.json / {field.storage.path or field.field_id}"
    return field.storage.location


def conversion_preview(value: Any, unit: str | None, field: FieldDefinition | None) -> str:
    if field is None:
        return ""
    if not field.accepted_units:
        return str(value)
    if not unit:
        return f"{value} [unit needed]"
    target = field.standard_unit or unit
    factor = default_unit_normaliser.conversion_factor(unit, target, dimension=field.unit_dimension)
    if factor is None:
        return f"{value} {unit} -> unsupported"
    try:
        numeric = float(str(value))
        converted = numeric * factor
        return f"{value} {unit} -> {converted:g} {target}"
    except (TypeError, ValueError):
        return f"{value} {unit} -> {target}"


def _parse_with_format(text: str, fmt: str) -> date | None:
    try:
        return datetime.strptime(text, fmt).date()
    except ValueError:
        return None
