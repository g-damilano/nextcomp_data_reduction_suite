from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

from mtdp_enrichment.models import AliasEntry
from mtdp_enrichment.package.schema import MTDPSchema, normalize_import_alias
from mtdp_enrichment.units import FieldUnitPolicyResolver, UnitNormaliser


@dataclass(frozen=True, slots=True)
class SchemaLintIssue:
    code: str
    message: str
    field: str | None = None


@dataclass(slots=True)
class SchemaLintResult:
    errors: list[SchemaLintIssue] = field(default_factory=list)
    warnings: list[SchemaLintIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, code: str, message: str, field: str | None = None) -> None:
        self.errors.append(SchemaLintIssue(code, message, field))

    def add_warning(self, code: str, message: str, field: str | None = None) -> None:
        self.warnings.append(SchemaLintIssue(code, message, field))

    def raise_for_errors(self, *, schema_label: str) -> None:
        if self.ok:
            return
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in self.errors)
        raise ValueError(f"Schema {schema_label} failed MTDP schema lint: {details}")


class SchemaLinter:
    """Validate that a schema is a usable MTDP contract."""

    FIELD_TYPES = {"string", "float", "int", "date", "enum", "bool", "path", "file"}
    STORAGE_LOCATIONS = {"token_preamble", "dataset_json", "provenance"}
    DATE_FORMATS = {
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "d/M/yyyy",
        "dd-MM-yyyy",
        "d-M-yyyy",
        "dd.MM.yyyy",
        "d.M.yyyy",
        "MM/dd/yyyy",
    }

    def __init__(self, unit_normaliser: UnitNormaliser | None = None) -> None:
        self.unit_normaliser = unit_normaliser or UnitNormaliser(prefer_pint=False)
        self.policy_resolver = FieldUnitPolicyResolver(self.unit_normaliser)

    def lint(self, schema: MTDPSchema) -> SchemaLintResult:
        result = SchemaLintResult()
        if not schema.schema_id:
            result.add_error("missing_schema_id", "schema_id is required.")
        if not schema.schema_version:
            result.add_error("missing_schema_version", "schema_version is required.")
        if schema.status not in {"active", "deprecated", "experimental", "legacy_read_only"}:
            result.add_error("invalid_status", f"Unsupported schema status '{schema.status}'.")

        fields = tuple(schema.dataset_fields + schema.run_fields)
        self._lint_fields(schema, fields, result)
        self._lint_import_aliases(fields, result)
        self._lint_table(schema, result)
        self._lint_image_policy(schema, result)
        self._lint_supplemental_policy(schema, result)
        self._lint_metadata_sections(schema, fields, result)
        self._lint_semantic_drift(schema, fields, result)
        return result

    def _lint_fields(self, schema: MTDPSchema, fields: Iterable[object], result: SchemaLintResult) -> None:
        seen_ids: dict[str, str] = {}
        groups = set(schema.ui.get("groups", ()) or ())
        for field in fields:
            field_id = field.field_id
            if field_id in seen_ids:
                result.add_error("duplicate_field_id", f"Field id '{field_id}' is defined more than once.", field_id)
            seen_ids[field_id] = field_id

            field_type = str(field.type).lower()
            if not field_type:
                result.add_error("missing_field_type", f"{field.label} does not define a type.", field_id)
            elif field_type not in self.FIELD_TYPES:
                result.add_error("unsupported_field_type", f"{field.label} has unsupported type '{field.type}'.", field_id)
            if field_type == "enum" and not field.allowed_values:
                result.add_error("enum_without_values", f"{field.label} is an enum without allowed_values.", field_id)
            self._lint_date_formats(field, result)
            self._lint_value_map(field, result)

            if groups and field.ui_group not in groups:
                result.add_error(
                    "unknown_ui_group",
                    f"{field.label} uses UI group '{field.ui_group}', which is not listed in ui.groups.",
                    field_id,
                )

            self._lint_storage(field, result)
            self._lint_units(schema, field, result)

    def _lint_storage(self, field: object, result: SchemaLintResult) -> None:
        storage = field.storage
        if storage.location not in self.STORAGE_LOCATIONS:
            result.add_error(
                "invalid_storage_location",
                f"{field.label} uses unsupported storage location '{storage.location}'.",
                field.field_id,
            )
            return
        if storage.location == "token_preamble" and not storage.token:
            result.add_error("missing_storage_token", f"{field.label} stores to token preamble without a token.", field.field_id)
        if storage.location in {"dataset_json", "provenance"} and not storage.path:
            result.add_error("missing_storage_path", f"{field.label} stores to {storage.location} without a path.", field.field_id)
        if field.field_id in {"sample_type", "treatment", "material_label"} and storage.location != "dataset_json":
            result.add_error(
                "dataset_identity_not_dataset_scoped",
                f"{field.label} is dataset identity but is not stored in dataset.json.",
                field.field_id,
            )

    def _lint_units(self, schema: MTDPSchema, field: object, result: SchemaLintResult) -> None:
        if not (field.accepted_units or field.standard_unit or field.unit_dimension):
            return
        policy = self.policy_resolver.resolve_field(schema, field)
        if policy.dimension is None:
            result.add_error("unknown_unit_dimension", f"{field.label} unit dimension could not be resolved.", field.field_id)
            return
        if field.unit_dimension and field.unit_dimension != policy.dimension:
            result.add_error(
                "unit_dimension_mismatch",
                f"{field.label} declares {field.unit_dimension} but resolves as {policy.dimension}.",
                field.field_id,
            )
        if policy.standard_unit and not self.unit_normaliser.dimensions.compatible(
            policy.standard_unit, policy.standard_unit, policy.dimension
        ):
            result.add_error(
                "invalid_standard_unit",
                f"{field.label} standard unit '{policy.standard_unit}' is not compatible with {policy.dimension}.",
                field.field_id,
            )
        for unit in policy.accepted_units:
            if not self.unit_normaliser.dimensions.compatible(unit, policy.standard_unit or unit, policy.dimension):
                result.add_error(
                    "invalid_accepted_unit",
                    f"{field.label} accepted unit '{unit}' is not compatible with {policy.dimension}.",
                    field.field_id,
                )

    def _lint_import_aliases(self, fields: Iterable[object], result: SchemaLintResult) -> None:
        aliases: dict[str, str] = {}
        weak_aliases: dict[str, str] = {}
        for field in fields:
            for entry in getattr(field, "import_alias_entries", ()) or ():
                if not isinstance(entry, AliasEntry):
                    continue
                if entry.kind not in {
                    "canonical_path",
                    "local_path",
                    "field_id",
                    "source_specific",
                    "legacy_key",
                    "weak_key",
                    "unit_encoded_key",
                    "deprecated",
                }:
                    result.add_error(
                        "invalid_import_alias_kind",
                        f"Import alias '{entry.alias}' has unsupported kind '{entry.kind}'.",
                        field.field_id,
                    )
                normalized = normalize_import_alias(entry.alias)
                if entry.kind == "weak_key" and normalized:
                    previous = weak_aliases.get(normalized)
                    if previous and previous != field.field_id:
                        result.add_error(
                            "weak_import_alias_collision",
                            f"Weak import alias '{entry.alias}' is shared by '{previous}' and '{field.field_id}'.",
                            field.field_id,
                        )
                    weak_aliases[normalized] = field.field_id

            for alias in (field.field_id, *field.import_aliases):
                normalized = normalize_import_alias(alias)
                if not normalized:
                    continue
                previous = aliases.get(normalized)
                if previous and previous != field.field_id:
                    result.add_error(
                        "import_alias_collision",
                        f"Import alias '{alias}' maps to both '{previous}' and '{field.field_id}'.",
                        field.field_id,
                    )
                else:
                    aliases[normalized] = field.field_id

    def _lint_date_formats(self, field: object, result: SchemaLintResult) -> None:
        if not getattr(field, "date_formats", None):
            return
        if str(field.type).lower() != "date":
            result.add_error("date_formats_on_non_date", f"{field.label} defines date_formats but is not a date field.", field.field_id)
            return
        accepted = field.date_formats.get("accepted", ()) or ()
        canonical = field.date_formats.get("canonical")
        for item in accepted:
            if str(item) not in self.DATE_FORMATS:
                result.add_error("unsupported_date_format", f"{field.label} accepts unsupported date format '{item}'.", field.field_id)
        if canonical and canonical not in self.DATE_FORMATS:
            result.add_error("unsupported_canonical_date_format", f"{field.label} uses unsupported canonical date format '{canonical}'.", field.field_id)

    def _lint_value_map(self, field: object, result: SchemaLintResult) -> None:
        if not getattr(field, "value_map", None):
            return
        field_type = str(field.type).lower()
        if field_type not in {"enum", "bool", "date", "string"}:
            result.add_error("value_map_on_unsupported_type", f"{field.label} defines value_map for type '{field.type}'.", field.field_id)
        if field_type == "enum":
            allowed = set(field.allowed_values)
            for source, target in field.value_map.items():
                if target not in allowed:
                    result.add_error(
                        "value_map_target_outside_enum",
                        f"{field.label} maps '{source}' to '{target}', which is not in allowed_values.",
                        field.field_id,
                    )
        if field_type == "bool":
            for source, target in field.value_map.items():
                if not isinstance(target, bool):
                    result.add_error(
                        "value_map_target_not_bool",
                        f"{field.label} maps '{source}' to non-boolean value '{target}'.",
                        field.field_id,
                    )
        if field_type == "date":
            for source, target in field.value_map.items():
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(target)):
                    result.add_error(
                        "value_map_target_not_iso_date",
                        f"{field.label} maps '{source}' to non-ISO date '{target}'.",
                        field.field_id,
                    )

    def _lint_table(self, schema: MTDPSchema, result: SchemaLintResult) -> None:
        families: set[str] = set()
        for column in schema.expected_table:
            if not column.family:
                result.add_error("missing_table_family", "Data-table column definition is missing family.")
                continue
            if column.family in families:
                result.add_error("duplicate_table_family", f"Data-table family '{column.family}' is defined more than once.")
            families.add(column.family)
            if column.accepted_units or column.standard_unit or column.unit_dimension:
                policy = self.policy_resolver.resolve_table_column(schema, column)
                if policy.dimension is None:
                    result.add_error(
                        "unknown_table_unit_dimension",
                        f"Data-table family '{column.family}' unit dimension could not be resolved.",
                        column.family,
                    )
                    continue
                for unit in policy.accepted_units:
                    if not self.unit_normaliser.dimensions.compatible(unit, policy.standard_unit or unit, policy.dimension):
                        result.add_error(
                            "invalid_table_unit",
                            f"Data-table family '{column.family}' accepts incompatible unit '{unit}'.",
                            column.family,
                        )

    def _lint_image_policy(self, schema: MTDPSchema, result: SchemaLintResult) -> None:
        config = schema.image_evidence or {}
        if not config:
            return
        if not isinstance(config.get("enabled", True), bool):
            result.add_error("invalid_image_policy", "image_evidence.enabled must be boolean.")
        formats = config.get("accepted_formats", ()) or ()
        for item in formats:
            if not str(item).startswith("."):
                result.add_error("invalid_image_extension", f"Image accepted format must start with '.': {item}")
        seen_views: set[str] = set()
        for view in config.get("views", ()) or ():
            if not isinstance(view, dict):
                result.add_error("invalid_image_view", "image_evidence.views entries must be mappings.")
                continue
            view_id = str(view.get("id", "")).strip()
            if not view_id:
                result.add_error("missing_image_view_id", "image_evidence view is missing id.")
            if view_id in seen_views:
                result.add_error("duplicate_image_view", f"Duplicate image view id '{view_id}'.")
            seen_views.add(view_id)

    def _lint_supplemental_policy(self, schema: MTDPSchema, result: SchemaLintResult) -> None:
        config = getattr(schema, "supplemental_files", {}) or {}
        if not config:
            return
        if not isinstance(config.get("enabled", True), bool):
            result.add_error("invalid_supplemental_policy", "supplemental_files.enabled must be boolean.")
        scopes = config.get("accepted_scopes", ()) or ()
        if config.get("enabled", True) and not scopes:
            result.add_error("missing_supplemental_scopes", "supplemental_files.enabled requires accepted_scopes.")

    def _lint_metadata_sections(self, schema: MTDPSchema, fields: Iterable[object], result: SchemaLintResult) -> None:
        by_id = {field.field_id for field in fields}
        seen_sections: set[str] = set()
        self._lint_metadata_section_source_contract(schema, result)
        for section in getattr(schema, "metadata_sections", ()) or ():
            if section.scope not in {"dataset", "run"}:
                result.add_error("invalid_metadata_section_scope", f"Metadata section '{section.id}' has invalid scope '{section.scope}'.")
            if section.id in seen_sections:
                result.add_error("duplicate_metadata_section", f"Metadata section '{section.id}' is defined more than once.")
            seen_sections.add(section.id)
            for field in section.fields:
                if field.field_id not in by_id:
                    result.add_error(
                        "metadata_section_unknown_field",
                        f"Metadata section '{section.id}' references unknown field '{field.field_id}'.",
                        field.field_id,
                    )
                importance = getattr(field, "report_importance", None)
                if importance and importance not in {"required", "required_for_accepted_runs", "recommended", "optional", "none"}:
                    result.add_error(
                        "invalid_report_importance",
                        f"{field.label} uses unsupported report_importance '{importance}'.",
                        field.field_id,
                    )

    def _lint_metadata_section_source_contract(self, schema: MTDPSchema, result: SchemaLintResult) -> None:
        sections = schema.raw.get("metadata_sections", ()) if isinstance(schema.raw, dict) else ()
        if not isinstance(sections, list):
            return
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("id") or section.get("label") or "metadata_section")
            for field_payload in section.get("fields", ()) or ():
                if isinstance(field_payload, str):
                    continue
                if not isinstance(field_payload, dict):
                    continue
                keys = set(field_payload)
                if keys == {"field_ref"}:
                    continue
                if "field_ref" in field_payload:
                    result.add_warning(
                        "metadata_section_ref_has_overrides",
                        f"Metadata section '{section_id}' should keep field_ref entries free of duplicated field metadata.",
                        str(field_payload.get("field_ref") or ""),
                    )
                    continue
                if {"key", "field_id"} & keys:
                    result.add_warning(
                        "metadata_section_inline_field_definition",
                        f"Metadata section '{section_id}' defines field metadata inline; prefer a canonical field plus field_ref.",
                        str(field_payload.get("field_id") or field_payload.get("key") or ""),
                    )

    def _lint_semantic_drift(self, schema: MTDPSchema, fields: Iterable[object], result: SchemaLintResult) -> None:
        by_id = {field.field_id: field for field in fields}
        if schema.status == "active" and "instrument_model" in by_id:
            for legacy_id in ("instrument", "machine"):
                if legacy_id in by_id:
                    result.add_error(
                        "instrument_field_duplication",
                        f"Active schema should use instrument_model/instrument_id/instrument_location; '{legacy_id}' must be an alias only.",
                        legacy_id,
                    )
        failure = by_id.get("failure_mode")
        validity = by_id.get("validity")
        if schema.status == "active" and failure and validity:
            failure_aliases = {normalize_import_alias(alias) for alias in failure.import_aliases}
            if {"valid", "validity"} & failure_aliases:
                result.add_error(
                    "validity_failure_mode_alias_overlap",
                    "Boolean validity aliases must map to validity, not failure_mode.",
                    "failure_mode",
                )
            if str(failure.type).lower() == "enum" and set(failure.allowed_values) & {"Valid", "Invalid"}:
                result.add_error(
                    "validity_failure_mode_duplication",
                    "failure_mode should describe failure details; validity owns accepted/rejected review state.",
                    "failure_mode",
                )


def lint_schema(schema: MTDPSchema) -> SchemaLintResult:
    return SchemaLinter().lint(schema)
