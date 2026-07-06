from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Mapping

from mtdp_enrichment.models import AliasEntry, EnrichedFieldValue, FieldDefinition, ValidationResult
from mtdp_enrichment.units import default_unit_normaliser


@dataclass(frozen=True, slots=True)
class TableColumnDefinition:
    family: str
    label: str
    required: bool = True
    repeatable: bool = False
    accepted_units: tuple[str, ...] = ()
    standard_unit: str | None = None
    aliases: tuple[str, ...] = ()
    unit_dimension: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TableColumnDefinition":
        return cls(
            family=str(payload["family"]),
            label=str(payload.get("label", payload["family"])),
            required=bool(payload.get("required", True)),
            repeatable=bool(payload.get("repeatable", False)),
            accepted_units=tuple(payload.get("accepted_units", ()) or ()),
            standard_unit=payload.get("standard_unit"),
            aliases=tuple(payload.get("aliases", ()) or ()),
            unit_dimension=payload.get("unit_dimension"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "family": self.family,
            "label": self.label,
            "required": self.required,
            "repeatable": self.repeatable,
        }
        if self.accepted_units:
            data["accepted_units"] = list(self.accepted_units)
        if self.standard_unit:
            data["standard_unit"] = self.standard_unit
        if self.aliases:
            data["aliases"] = list(self.aliases)
        if self.unit_dimension:
            data["unit_dimension"] = self.unit_dimension
        return data


@dataclass(frozen=True, slots=True)
class MetadataSection:
    id: str
    label: str
    scope: str
    ui_group: str
    report_section: str | None
    fields: tuple[FieldDefinition, ...]
    field_refs: tuple[str, ...] = ()

    @classmethod
    def from_resolved_fields(
        cls,
        payload: dict[str, Any],
        fields: tuple[FieldDefinition, ...],
        field_refs: tuple[str, ...] | None = None,
    ) -> "MetadataSection":
        section_id = str(payload.get("id") or payload.get("key") or "").strip()
        return cls(
            id=section_id,
            label=str(payload.get("label") or section_id),
            scope=str(payload.get("scope") or "dataset"),
            ui_group=str(payload.get("ui_group") or payload.get("label") or section_id or "Metadata"),
            report_section=None if payload.get("report_section") in (None, "") else str(payload.get("report_section")),
            fields=fields,
            field_refs=field_refs or tuple(field.field_id for field in fields),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "scope": self.scope,
            "ui_group": self.ui_group,
            "fields": [{"field_ref": field_ref} for field_ref in self.field_refs],
        }
        if self.report_section:
            data["report_section"] = self.report_section
        return data


@dataclass(frozen=True, slots=True)
class MTDPSchema:
    schema_id: str
    schema_version: str
    display_label: str
    status: str
    test_family: str
    test_mode: str
    dataset_fields: tuple[FieldDefinition, ...]
    run_fields: tuple[FieldDefinition, ...]
    expected_table: tuple[TableColumnDefinition, ...]
    metadata_sections: tuple[MetadataSection, ...] = ()
    package: dict[str, Any] = field(default_factory=dict)
    ui: dict[str, Any] = field(default_factory=dict)
    dataset_grouping: dict[str, Any] = field(default_factory=dict)
    sidecar_import: dict[str, Any] = field(default_factory=dict)
    image_evidence: dict[str, Any] = field(default_factory=dict)
    supplemental_files: dict[str, Any] = field(default_factory=dict)
    unit_system: str | None = None
    unit_systems: dict[str, Any] = field(default_factory=dict)
    unit_conversion_rules: dict[str, Any] = field(default_factory=dict)
    migration: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MTDPSchema":
        _validate_schema_payload(payload)
        expected = payload.get("data_table", {}).get(
            "columns",
            payload.get("expected_data_table", {}).get("columns", ()),
        )
        test = dict(payload.get("test", {}) or {})
        package = dict(payload.get("package", {}) or {})
        if not package:
            package = {
                "granularity": "dataset_with_runs",
                "raw_folder": "raw",
                "normalized_folder": "normalized",
                "normalized_extension": ".csv",
                "run_id_pattern": "run_{index:03d}",
            }
        dataset_fields = tuple(FieldDefinition.from_dict(item) for item in payload.get("dataset_fields", ()) or ())
        run_payload = payload.get("run_fields")
        if run_payload is None:
            run_payload = payload.get("fields", ())
        run_fields = tuple(FieldDefinition.from_dict(item) for item in run_payload or ())
        metadata_sections, dataset_fields, run_fields = _resolve_metadata_sections(
            payload.get("metadata_sections", ()) or (),
            dataset_fields,
            run_fields,
        )
        return cls(
            schema_id=str(payload["schema_id"]),
            schema_version=str(payload["schema_version"]),
            display_label=str(payload.get("label", payload["schema_id"])),
            status=str(payload.get("status", "active")),
            test_family=str(test.get("family", payload.get("test_family", ""))),
            test_mode=str(test.get("mode", payload.get("test_mode", ""))),
            dataset_fields=dataset_fields,
            run_fields=run_fields,
            expected_table=tuple(TableColumnDefinition.from_dict(item) for item in expected),
            metadata_sections=metadata_sections,
            package=package,
            ui=dict(payload.get("ui", {}) or {}),
            dataset_grouping=dict(payload.get("dataset_grouping", {}) or {}),
            sidecar_import=dict(payload.get("sidecar_import", {}) or {}),
            image_evidence=dict(payload.get("image_evidence", {}) or {}),
            supplemental_files=dict(payload.get("supplemental_files", {}) or {}),
            unit_system=payload.get("unit_system"),
            unit_systems=dict(payload.get("unit_systems", {}) or {}),
            unit_conversion_rules=dict(payload.get("unit_conversion_rules", {}) or {}),
            migration=dict(payload.get("migration", {}) or {}),
            raw=copy.deepcopy(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "label": self.display_label,
            "status": self.status,
            "test": {"family": self.test_family, "mode": self.test_mode},
            "package": copy.deepcopy(self.package),
            "ui": copy.deepcopy(self.ui),
            "dataset_grouping": copy.deepcopy(self.dataset_grouping),
            "sidecar_import": copy.deepcopy(self.sidecar_import),
            "image_evidence": copy.deepcopy(self.image_evidence),
            "supplemental_files": copy.deepcopy(self.supplemental_files),
            "unit_system": self.unit_system,
            "unit_systems": copy.deepcopy(self.unit_systems),
            "dataset_fields": [field.to_dict() for field in self.dataset_fields],
            "run_fields": [field.to_dict() for field in self.run_fields],
            "metadata_sections": [section.to_dict() for section in self.metadata_sections],
            "data_table": {
                "format": "tokenized_csv",
                "unit_row": True,
                "columns": [column.to_dict() for column in self.expected_table],
            },
            "unit_conversion_rules": copy.deepcopy(self.unit_conversion_rules),
            "migration": copy.deepcopy(self.migration),
        }

    @property
    def fields(self) -> tuple[FieldDefinition, ...]:
        """Compatibility alias for v0 single-run callers."""

        return self.run_fields

    def label(self) -> str:
        return f"{self.display_label} v{self.schema_version}"

    def selector_label(self) -> str:
        return f"{self.display_label} - v{self.schema_version} - {self.status}"

    def field_by_id(self, field_id: str) -> FieldDefinition | None:
        for item in self.dataset_fields + self.run_fields:
            if item.field_id == field_id:
                return item
        return None

    def metadata_sections_for_scope(self, scope: str) -> tuple[MetadataSection, ...]:
        normalized = str(scope).strip().casefold()
        return tuple(section for section in self.metadata_sections if section.scope.casefold() == normalized)

    def field_by_token(self, token: str) -> FieldDefinition | None:
        token_norm = token.strip().casefold()
        for item in self.run_fields:
            if item.storage.token and item.storage.token.strip().casefold() == token_norm:
                return item
        return None

    def import_alias_map(self) -> dict[str, FieldDefinition]:
        aliases: dict[str, FieldDefinition] = {}
        for item in self.dataset_fields + self.run_fields:
            candidates = [item.field_id, item.label, *(entry.alias for entry in item.import_alias_entries)]
            if item.storage.token:
                candidates.append(item.storage.token)
            for alias in candidates:
                normalized = normalize_import_alias(alias)
                if normalized:
                    aliases.setdefault(normalized, item)
        return aliases

    def import_alias_entry_map(self) -> dict[str, tuple[FieldDefinition, AliasEntry | None]]:
        aliases: dict[str, tuple[FieldDefinition, AliasEntry | None]] = {}
        for item in self.dataset_fields + self.run_fields:
            implicit = [
                (item.field_id, AliasEntry(item.field_id, "field_id", 0.95)),
                (item.label, AliasEntry(item.label, "legacy_key", 0.75)),
            ]
            if item.storage.token:
                implicit.append((item.storage.token, AliasEntry(item.storage.token, "legacy_key", 0.75)))
            for alias, entry in implicit:
                normalized = normalize_import_alias(alias)
                if normalized:
                    aliases.setdefault(normalized, (item, entry))
            for entry in item.import_alias_entries:
                normalized = normalize_import_alias(entry.alias)
                if normalized:
                    aliases.setdefault(normalized, (item, entry))
        return aliases

    def field_by_import_alias(self, alias: str) -> FieldDefinition | None:
        return self.import_alias_map().get(normalize_import_alias(alias))

    def alias_entry_for_import_alias(self, alias: str) -> tuple[FieldDefinition, AliasEntry | None] | None:
        return self.import_alias_entry_map().get(normalize_import_alias(alias))

    def sidecar_import_config(self) -> dict[str, Any]:
        return copy.deepcopy(self.sidecar_import)

    def image_evidence_config(self) -> dict[str, Any]:
        return copy.deepcopy(self.image_evidence)

    def table_definition_for_family(self, family: str) -> TableColumnDefinition | None:
        for item in self.expected_table:
            if item.family == family:
                return item
        return None

    def validate_enrichment(
        self,
        values: Mapping[str, EnrichedFieldValue | Any],
        *,
        existing_tokens: Mapping[str, EnrichedFieldValue] | None = None,
    ) -> tuple[dict[str, EnrichedFieldValue], ValidationResult]:
        existing_tokens = existing_tokens or {}
        return self.validate_field_set(self.run_fields, values, existing_values=existing_tokens)

    def validate_dataset_fields(
        self,
        values: Mapping[str, EnrichedFieldValue | Any],
    ) -> tuple[dict[str, EnrichedFieldValue], ValidationResult]:
        return self.validate_field_set(self.dataset_fields, values)

    def validate_run_fields(
        self,
        values: Mapping[str, EnrichedFieldValue | Any],
        *,
        existing_tokens: Mapping[str, EnrichedFieldValue] | None = None,
    ) -> tuple[dict[str, EnrichedFieldValue], ValidationResult]:
        return self.validate_field_set(self.run_fields, values, existing_values=existing_tokens)

    def validate_field_set(
        self,
        definitions: tuple[FieldDefinition, ...],
        values: Mapping[str, EnrichedFieldValue | Any],
        *,
        existing_values: Mapping[str, EnrichedFieldValue] | None = None,
    ) -> tuple[dict[str, EnrichedFieldValue], ValidationResult]:
        result = ValidationResult()
        normalized: dict[str, EnrichedFieldValue] = {}
        existing_values = existing_values or {}

        for definition in definitions:
            if definition.visible_when and not _condition_matches(definition.visible_when, values, normalized, existing_values):
                continue
            candidate = values.get(definition.field_id)
            if not isinstance(candidate, EnrichedFieldValue):
                if candidate is not None:
                    candidate = EnrichedFieldValue(candidate, source="user")
                elif definition.field_id in existing_values:
                    candidate = existing_values[definition.field_id]
                elif definition.default is not None:
                    candidate = EnrichedFieldValue(definition.default, definition.standard_unit, "schema_default")

            if candidate is None or candidate.value in (None, ""):
                if definition.required or _condition_matches(definition.required_when, values, normalized, existing_values):
                    result.add_error(
                        f"{definition.label} is required.",
                        field=definition.field_id,
                        code="required",
                    )
                continue

            coerced = self._coerce_field(definition, candidate, result)
            if coerced is not None:
                normalized[definition.field_id] = coerced

        return normalized, result

    def _coerce_field(
        self,
        definition: FieldDefinition,
        candidate: EnrichedFieldValue,
        result: ValidationResult,
    ) -> EnrichedFieldValue | None:
        value = candidate.value
        unit = candidate.unit or definition.standard_unit
        field_type = definition.type.lower()
        value = _mapped_value(definition, value)

        if definition.accepted_units and unit:
            accepted = {default_unit_normaliser.normalize_unit_text(item) for item in definition.accepted_units}
            if default_unit_normaliser.normalize_unit_text(unit) not in accepted:
                result.add_error(
                    f"{definition.label} unit '{unit}' is not accepted by schema {self.label()}.",
                    field=definition.field_id,
                    code="unsupported_unit",
                )
                return None

        try:
            if field_type == "float":
                number = float(str(value).strip())
                if definition.standard_unit and unit:
                    factor = default_unit_normaliser.conversion_factor(
                        unit,
                        definition.standard_unit,
                        dimension=definition.unit_dimension,
                    )
                    if factor is None:
                        result.add_error(
                            f"{definition.label} cannot be converted from {unit} to {definition.standard_unit}.",
                            field=definition.field_id,
                            code="unsupported_unit_conversion",
                        )
                        return None
                    number *= factor
                    unit = definition.standard_unit
                min_value = definition.validation.get("min")
                max_value = definition.validation.get("max")
                if min_value is not None and number < float(min_value):
                    result.add_error(
                        f"{definition.label} must be at least {min_value}.",
                        field=definition.field_id,
                        code="below_minimum",
                    )
                if max_value is not None and number > float(max_value):
                    result.add_error(
                        f"{definition.label} must be at most {max_value}.",
                        field=definition.field_id,
                        code="above_maximum",
                    )
                return EnrichedFieldValue(number, unit, candidate.source)
            if field_type == "date":
                text = str(value).strip()
                parsed = _parse_known_date(text)
                if parsed is None:
                    raise ValueError
                return EnrichedFieldValue(parsed, unit, candidate.source)
            if field_type == "bool":
                if isinstance(value, bool):
                    return EnrichedFieldValue(value, unit, candidate.source)
                text = str(value).strip().lower()
                if text in {"true", "yes", "y", "1", "valid"}:
                    return EnrichedFieldValue(True, unit, candidate.source)
                if text in {"false", "no", "n", "0", "invalid"}:
                    return EnrichedFieldValue(False, unit, candidate.source)
                raise ValueError
            if field_type == "enum":
                text = str(value).strip()
                if definition.allowed_values and text not in definition.allowed_values:
                    result.add_error(
                        f"{definition.label} must be one of: {', '.join(definition.allowed_values)}.",
                        field=definition.field_id,
                        code="invalid_enum",
                    )
                    return None
                return EnrichedFieldValue(text, unit, candidate.source)
        except ValueError:
            result.add_error(
                f"{definition.label} has invalid {field_type} input.",
                field=definition.field_id,
                code="invalid_type",
            )
            return None

        text = str(value).strip()
        pattern = definition.validation.get("pattern")
        if pattern and not re.fullmatch(str(pattern), text):
            result.add_error(
                f"{definition.label} does not match the schema character rules.",
                field=definition.field_id,
                code="pattern_mismatch",
            )
            return None
        return EnrichedFieldValue(text, unit, candidate.source)


def normalize_import_alias(alias: str | None) -> str:
    if alias is None:
        return ""
    text = str(alias).strip().casefold()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _condition_matches(
    condition: Mapping[str, Any] | None,
    values: Mapping[str, EnrichedFieldValue | Any],
    normalized: Mapping[str, EnrichedFieldValue],
    existing_values: Mapping[str, EnrichedFieldValue],
) -> bool:
    if not condition:
        return False
    field_id = str(condition.get("field") or condition.get("field_id") or "").strip()
    if not field_id:
        return False
    value = _condition_source_value(field_id, values, normalized, existing_values)
    if "equals" in condition:
        return _condition_text(value) == _condition_text(condition.get("equals"))
    if "in" in condition:
        raw_options = condition.get("in", ()) or ()
        options = (raw_options,) if isinstance(raw_options, str) else raw_options
        return _condition_text(value) in {_condition_text(item) for item in options}
    return bool(value not in (None, ""))


def _condition_source_value(
    field_id: str,
    values: Mapping[str, EnrichedFieldValue | Any],
    normalized: Mapping[str, EnrichedFieldValue],
    existing_values: Mapping[str, EnrichedFieldValue],
) -> Any:
    for source in (values, normalized, existing_values):
        if field_id not in source:
            continue
        value = source[field_id]
        return value.value if isinstance(value, EnrichedFieldValue) else value
    return None


def _condition_text(value: Any) -> str:
    return str(value or "").strip().casefold()


def normalize_unit_text(unit: str | None) -> str | None:
    """Compatibility wrapper only; new code must use units.UnitNormaliser."""

    return default_unit_normaliser.normalize_unit_text(unit)


def unit_conversion_factor(
    from_unit: str | None,
    to_unit: str | None,
    *,
    dimension: str | None = None,
) -> float | None:
    """Compatibility wrapper only; new code must use units.UnitNormaliser."""

    return default_unit_normaliser.conversion_factor(from_unit, to_unit, dimension=dimension)


def _resolve_metadata_sections(
    payload: Any,
    dataset_fields: tuple[FieldDefinition, ...],
    run_fields: tuple[FieldDefinition, ...],
) -> tuple[tuple[MetadataSection, ...], tuple[FieldDefinition, ...], tuple[FieldDefinition, ...]]:
    if not isinstance(payload, list):
        return (), dataset_fields, run_fields
    dataset_list = list(dataset_fields)
    run_list = list(run_fields)
    sections: list[MetadataSection] = []
    for section_payload in payload:
        if not isinstance(section_payload, dict):
            continue
        scope = str(section_payload.get("scope") or "dataset")
        section_fields: list[FieldDefinition] = []
        section_field_refs: list[str] = []
        for field_payload in section_payload.get("fields", ()) or ():
            if isinstance(field_payload, str):
                field_payload = {"field_ref": field_payload}
            if not isinstance(field_payload, dict):
                continue
            field_ref = _field_ref(field_payload)
            existing = _find_field(dataset_list if scope == "dataset" else run_list, field_payload)
            if existing is not None:
                field_def = _merge_section_field(existing, field_payload)
                if scope == "dataset":
                    dataset_list = _upsert_field(dataset_list, field_def)
                else:
                    run_list = _upsert_field(run_list, field_def)
            else:
                normalized = _section_field_payload(field_payload, section_payload)
                field_def = FieldDefinition.from_dict(normalized)
                if scope == "dataset":
                    dataset_list.append(field_def)
                else:
                    run_list.append(field_def)
            section_fields.append(field_def)
            section_field_refs.append(field_ref or field_def.field_id)
        sections.append(
            MetadataSection.from_resolved_fields(
                section_payload,
                tuple(section_fields),
                tuple(section_field_refs),
            )
        )
    return tuple(sections), tuple(dataset_list), tuple(run_list)


def _field_ref(payload: dict[str, Any]) -> str:
    return str(payload.get("field_ref") or payload.get("field_id") or payload.get("key") or "").strip()


def _find_field(fields: list[FieldDefinition], payload: dict[str, Any]) -> FieldDefinition | None:
    key = _field_ref(payload)
    if not key:
        return None
    return next((field for field in fields if field.field_id == key), None)


def _upsert_field(fields: list[FieldDefinition], field_def: FieldDefinition) -> list[FieldDefinition]:
    updated = list(fields)
    for index, existing in enumerate(updated):
        if existing.field_id == field_def.field_id:
            updated[index] = field_def
            return updated
    updated.append(field_def)
    return updated


def _merge_section_field(existing: FieldDefinition, payload: dict[str, Any]) -> FieldDefinition:
    allowed_values = payload.get("allowed_values", payload.get("choices"))
    kwargs: dict[str, Any] = {}
    if payload.get("report_role") not in (None, ""):
        kwargs["report_role"] = str(payload["report_role"])
    if payload.get("report_importance") not in (None, ""):
        kwargs["report_importance"] = str(payload["report_importance"])
    if payload.get("method_role") not in (None, ""):
        kwargs["method_role"] = str(payload["method_role"])
    if payload.get("description") not in (None, ""):
        kwargs["description"] = str(payload["description"])
    if allowed_values:
        kwargs["allowed_values"] = tuple(allowed_values)
    if payload.get("display_labels"):
        kwargs["display_labels"] = {str(key): str(value) for key, value in dict(payload.get("display_labels", {}) or {}).items()}
    if payload.get("visible_when"):
        kwargs["visible_when"] = dict(payload.get("visible_when", {}) or {})
    if payload.get("required_when"):
        kwargs["required_when"] = dict(payload.get("required_when", {}) or {})
    if payload.get("label") not in (None, ""):
        kwargs["label"] = str(payload["label"])
    return replace(existing, **kwargs) if kwargs else existing


def _section_field_payload(field_payload: dict[str, Any], section_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(field_payload)
    payload.setdefault("field_id", payload.get("field_ref") or payload.get("key"))
    payload.setdefault("label", payload.get("field_id") or payload.get("key"))
    payload.setdefault("role", payload.get("method_role") or payload.get("report_role") or "metadata")
    payload.setdefault("required", False)
    payload.setdefault("type", "string")
    payload.setdefault("ui_group", section_payload.get("ui_group") or section_payload.get("label") or "Metadata")
    if "choices" in payload and "allowed_values" not in payload:
        payload["allowed_values"] = payload["choices"]
    if "storage" not in payload:
        scope = str(section_payload.get("scope") or "dataset")
        if scope == "dataset":
            payload["storage"] = {"location": "dataset_json", "path": f"metadata.{payload['field_id']}"}
        else:
            payload["storage"] = {
                "location": "provenance",
                "path": f"runs.{{run_id}}.metadata.{payload['field_id']}",
            }
    return payload


def _mapped_value(definition: FieldDefinition, value: Any) -> Any:
    if not definition.value_map:
        return value
    for key in (str(value).strip(), str(value).strip().casefold()):
        if key in definition.value_map:
            return definition.value_map[key]
    return value


def _parse_known_date(text: str) -> str | None:
    from datetime import datetime

    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _validate_schema_payload(payload: dict[str, Any]) -> None:
    required = ("schema_id", "schema_version")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Schema payload is missing required keys: {', '.join(missing)}")
    if payload.get("status", "active") not in {"active", "deprecated", "experimental", "legacy_read_only"}:
        raise ValueError(f"Unsupported schema status: {payload.get('status')}")
    if not any(key in payload for key in ("run_fields", "fields")):
        raise ValueError("Schema payload must define run_fields or legacy fields.")
