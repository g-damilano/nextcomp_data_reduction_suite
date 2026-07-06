from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import yaml
from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import.canonical_yaml import (
    build_document,
    canonical_import_items,
    extract_value_and_unit,
    image_references,
    iter_value_items,
)
from mtdp_enrichment.enrichment_import.mapping_profile import YamlMappingProfile, load_profiles
from mtdp_enrichment.enrichment_import.models import (
    FieldConflict,
    ImportedFieldCandidate,
    SupplementalImportResult,
)
from mtdp_enrichment.enrichment_import.value_normalizers import extract_unit_from_key, transform_value_for_field
from mtdp_enrichment.models import EnrichedFieldValue, FieldDefinition
from mtdp_enrichment.units import default_unit_normaliser

if TYPE_CHECKING:
    from mtdp_enrichment.package.schema import MTDPSchema


class SidecarYamlImporter:
    """Load same-stem YAML enrichment as schema-mapped candidate values."""

    def __init__(self, mapping_profiles: Sequence[YamlMappingProfile] | None = None) -> None:
        self.mapping_profiles: list[YamlMappingProfile] = list(mapping_profiles or ())

    def load_mapping_profiles(self, directory: str | Path) -> None:
        known = {(profile.mapping_profile_id, profile.structure_signature) for profile in self.mapping_profiles}
        for profile in load_profiles(directory):
            key = (profile.mapping_profile_id, profile.structure_signature)
            if key not in known:
                self.mapping_profiles.append(profile)
                known.add(key)

    def add_mapping_profile(self, profile: YamlMappingProfile) -> None:
        self.mapping_profiles = [
            item
            for item in self.mapping_profiles
            if (item.mapping_profile_id, item.structure_signature)
            != (profile.mapping_profile_id, profile.structure_signature)
        ]
        self.mapping_profiles.append(profile)

    def detect_same_stem(self, source_file: str | Path, schema: MTDPSchema) -> Path | None:
        config = schema.sidecar_import_config()
        if config and not config.get("enabled", True):
            return None
        path = Path(source_file)
        extensions = tuple(config.get("accepted_extensions", (".yaml", ".yml")) or (".yaml", ".yml"))
        for extension in extensions:
            candidate = path.with_suffix(str(extension))
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def import_for_run(
        self,
        source_file: str | Path,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        *,
        existing_values: Mapping[str, EnrichedFieldValue] | None = None,
        mapping_profile: YamlMappingProfile | None = None,
    ) -> SupplementalImportResult:
        sidecar = self.detect_same_stem(source_file, schema)
        if sidecar is None:
            return SupplementalImportResult(None, {}, (), (), False, None, None, ())
        return self.import_file(sidecar, parsed, schema, existing_values=existing_values, mapping_profile=mapping_profile)

    def import_file(
        self,
        sidecar_path: str | Path,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        *,
        existing_values: Mapping[str, EnrichedFieldValue] | None = None,
        mapping_profile: YamlMappingProfile | None = None,
    ) -> SupplementalImportResult:
        path = Path(sidecar_path)
        warnings: list[str] = []
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return SupplementalImportResult(None, {}, (), (), False, None, None, (f"Could not load supplemental YAML: {exc}",))

        if payload is None:
            document = build_document(path, {})
            return SupplementalImportResult(document, {}, (), (), False, None, None, ("Supplemental YAML is empty.",))
        if not isinstance(payload, dict):
            return SupplementalImportResult(None, {}, (), (), False, None, None, ("Supplemental YAML must contain a mapping.",))

        document = build_document(path, payload)
        profile = mapping_profile or self._matching_profile(schema, document)
        if profile is not None:
            mapped_fields, ignored, profile_warnings = profile.apply(document, schema)
            warnings.extend(profile_warnings)
            return self._finalize_result(
                document=document,
                schema=schema,
                parsed=parsed,
                imported=mapped_fields,
                unknown_keys=ignored,
                warnings=tuple(warnings),
                existing_values=existing_values,
                mapping_profile_id=profile.mapping_profile_id,
                mapping_profile_path=profile.source_path,
                source_format="mapped_supplemental_yaml",
            )

        items = tuple(canonical_import_items(payload) if document.is_canonical else iter_value_items(payload))
        imported: dict[str, ImportedFieldCandidate] = {}
        unknown_keys: list[str] = []

        for source_key, raw_value in items:
            normalized_key, key_unit, _unit_status = extract_unit_from_key(source_key)
            field = self._field_for_source_key(schema, normalized_key)
            if field is None:
                if not self._is_ignorable_key(source_key):
                    unknown_keys.append(source_key)
                continue

            value, unit = extract_value_and_unit(raw_value)
            unit = unit or key_unit
            if value in (None, ""):
                continue
            transformed = transform_value_for_field(
                source_key=source_key,
                raw_value=value,
                raw_unit=unit,
                field=field,
                selected_unit=unit,
            )
            if transformed is not None:
                value = transformed.canonical_value
                unit = transformed.canonical_unit
            imported[field.field_id] = ImportedFieldCandidate(
                field_id=field.field_id,
                value=value,
                unit=unit,
                source_path=path,
                source_key=source_key,
                source_format="canonical_supplemental_yaml" if document.is_canonical else "alias_supplemental_yaml",
            )

        requires_mapping = self._requires_mapping(document, imported, unknown_keys, schema)
        if unknown_keys and schema.sidecar_import_config().get("unknown_keys", "warn") == "warn":
            warnings.append(f"Unknown supplemental key(s): {', '.join(sorted(unknown_keys))}.")

        return self._finalize_result(
            document=document,
            schema=schema,
            parsed=parsed,
            imported=imported,
            unknown_keys=tuple(sorted(set(unknown_keys))),
            warnings=tuple(warnings),
            existing_values=existing_values,
            requires_mapping=requires_mapping,
            source_format="canonical_supplemental_yaml" if document.is_canonical else "alias_supplemental_yaml",
        )

    def _finalize_result(
        self,
        *,
        document,
        schema: MTDPSchema,
        parsed: ParsedSampleRecord,
        imported: dict[str, ImportedFieldCandidate],
        unknown_keys: tuple[str, ...],
        warnings: tuple[str, ...],
        existing_values: Mapping[str, EnrichedFieldValue] | None,
        requires_mapping: bool = False,
        mapping_profile_id: str | None = None,
        mapping_profile_path: Path | None = None,
        source_format: str = "supplemental_yaml",
    ) -> SupplementalImportResult:
        parser_values = self._parser_values(parsed, schema)
        combined_existing = dict(parser_values)
        if existing_values:
            combined_existing.update(existing_values)

        conflicts = self._conflicts_for_imported(schema, imported, combined_existing, source_format)
        image_refs = image_references(document.raw_payload, document.source_path)
        return SupplementalImportResult(
            document=document,
            imported_fields=imported,
            conflicts=tuple(conflicts),
            unknown_keys=unknown_keys,
            requires_mapping=requires_mapping,
            mapping_profile_id=mapping_profile_id,
            mapping_profile_path=mapping_profile_path,
            warnings=warnings,
            image_references=image_refs,
        )

    def _field_for_source_key(self, schema: MTDPSchema, source_key: str) -> FieldDefinition | None:
        candidates = [source_key]
        if source_key.startswith("run."):
            candidates.append(source_key.removeprefix("run."))
        if source_key.startswith("dataset."):
            candidates.append(source_key.removeprefix("dataset."))
        for prefix in ("run.metrology.", "run.acquisition.", "run.review.", "metrology.", "acquisition.", "review."):
            if source_key.startswith(prefix):
                candidates.append(source_key.removeprefix(prefix))
        candidates.append(source_key.split(".")[-1])
        for candidate in candidates:
            field = schema.field_by_import_alias(candidate)
            if field is not None:
                return field
        return None

    def _matching_profile(self, schema: MTDPSchema, document) -> YamlMappingProfile | None:
        for profile in self.mapping_profiles:
            if profile.applies_to(schema, document):
                return profile
        return None

    def _requires_mapping(
        self,
        document,
        imported: Mapping[str, ImportedFieldCandidate],
        unknown_keys: Sequence[str],
        schema: MTDPSchema,
    ) -> bool:
        config = schema.sidecar_import_config()
        if document.is_canonical:
            return False
        if config.get("unknown_keys") != "prompt_mapping":
            return False
        key_count = max(1, len([key for key in document.key_paths if not self._is_ignorable_key(key)]))
        unknown_ratio = len(unknown_keys) / key_count
        return not imported or unknown_ratio >= 0.5

    def _conflicts_for_imported(
        self,
        schema: MTDPSchema,
        imported: Mapping[str, ImportedFieldCandidate],
        existing_values: Mapping[str, EnrichedFieldValue],
        source_format: str,
    ) -> list[FieldConflict]:
        conflicts: list[FieldConflict] = []
        conflict_policy = schema.sidecar_import_config().get("conflict_policy", "prefer_sidecar")
        for candidate in imported.values():
            field = schema.field_by_id(candidate.field_id)
            if field is None:
                continue
            existing = existing_values.get(candidate.field_id)
            if field.accepted_units and candidate.unit in (None, ""):
                conflicts.append(
                    FieldConflict(
                        field_id=field.field_id,
                        existing_value=existing.value if existing is not None else None,
                        existing_unit=existing.unit if existing is not None else None,
                        imported_value=candidate.value,
                        imported_unit=None,
                        existing_source=existing.source if existing is not None else "schema",
                        imported_source=source_format,
                        message=(
                            f"{field.label} was imported from supplemental YAML without a unit; "
                            "confirm the unit before export."
                        ),
                    )
                )
            if (
                existing is not None
                and conflict_policy not in {"prefer_sidecar", "prefer_sidecar_silently"}
                and not self._same_field_value(existing.value, existing.unit, candidate.value, candidate.unit)
            ):
                conflicts.append(
                    FieldConflict(
                        field_id=field.field_id,
                        existing_value=existing.value,
                        existing_unit=existing.unit,
                        imported_value=candidate.value,
                        imported_unit=candidate.unit,
                        existing_source=existing.source,
                        imported_source=source_format,
                        message=(
                            f"{field.label} differs between {existing.source} "
                            f"and supplemental YAML key '{candidate.source_key}'."
                        ),
                    )
                )
        return conflicts

    def _parser_values(self, parsed: ParsedSampleRecord, schema: MTDPSchema) -> dict[str, EnrichedFieldValue]:
        values: dict[str, EnrichedFieldValue] = {}
        for token in parsed.preamble_tokens:
            field = schema.field_by_token(token.raw_key)
            if field is None and token.normalized_key:
                field = schema.field_by_id(token.normalized_key)
            if field is None:
                continue
            values[field.field_id] = EnrichedFieldValue(
                token.coerced_value_text or token.raw_value,
                token.raw_unit,
                "parser_token",
            )
        return values

    def _is_ignorable_key(self, source_key: str) -> bool:
        return source_key in {
            "mtdp_supplemental_version",
            "scope",
            "schema_hint.schema_id",
            "schema_hint.schema_version",
            "notes",
            "images",
        } or source_key.startswith("images.")

    def _same_field_value(
        self,
        existing_value: Any,
        existing_unit: str | None,
        imported_value: Any,
        imported_unit: str | None,
    ) -> bool:
        if _normalize_unit_text(existing_unit) != _normalize_unit_text(imported_unit):
            if existing_unit or imported_unit:
                return False
        existing_number = self._as_float(existing_value)
        imported_number = self._as_float(imported_value)
        if existing_number is not None and imported_number is not None:
            return math.isclose(existing_number, imported_number, rel_tol=1e-9, abs_tol=1e-9)
        return str(existing_value).strip() == str(imported_value).strip()

    def _as_float(self, value: Any) -> float | None:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None


def _normalize_unit_text(unit: str | None) -> str | None:
    return default_unit_normaliser.normalize_unit_text(unit)
