from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from archives.core.layouts import MTDPAlignedLayout, detect_mtdp_layout
from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import.models import FieldConflict
from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.models import EnrichedFieldValue, FieldDefinition, ValidationResult
from mtdp_enrichment.normalization import TokenizedCsvWriter, UnitNormalizer
from mtdp_enrichment.package.checksums import build_checksums
from mtdp_enrichment.package.manifest import build_manifest
from mtdp_enrichment.package.provenance import (
    grouping_confirmed_event,
    image_evidence_added_event,
    image_evidence_record,
    package_created_event,
    parsed_event,
    run_removed_event,
    sidecar_import_event,
    supplemental_file_added_event,
    supplemental_input_record,
    user_confirmation_event,
    yaml_mapping_profile_applied_event,
    yaml_reconciliation_confirmed_event,
)
from mtdp_enrichment.package.schema import MTDPSchema
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.source_identity import SourceIdentity, build_source_identities, common_source_root
from mtdp_enrichment.supplemental import SupplementalFile


class MTDPPackageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RunInput:
    run_id: str
    parsed: ParsedSampleRecord
    enrichment: Mapping[str, EnrichedFieldValue | Any] = field(default_factory=dict)
    field_units: Mapping[str, str | None] = field(default_factory=dict)
    supplemental_yaml: Path | None = None
    images: tuple[RunImageEvidence, ...] = ()
    import_conflicts: tuple[FieldConflict, ...] = ()
    unknown_supplemental_keys: tuple[str, ...] = ()
    supplemental_import_mode: str | None = None
    mapping_profile_id: str | None = None
    mapping_profile_path: Path | None = None
    supplemental_files: tuple[SupplementalFile, ...] = ()


@dataclass(frozen=True, slots=True)
class MTDPPackage:
    path: Path
    manifest: dict[str, Any]
    schema: dict[str, Any]
    provenance: dict[str, Any]
    dataset: dict[str, Any] = field(default_factory=dict)


class MTDPPackageWriter:
    def __init__(
        self,
        parser_adapter: ParserAdapter | None = None,
        normalizer: UnitNormalizer | None = None,
        csv_writer: TokenizedCsvWriter | None = None,
        validator: MTDPPackageValidator | None = None,
    ) -> None:
        self.parser_adapter = parser_adapter or ParserAdapter()
        self.normalizer = normalizer or UnitNormalizer()
        self.csv_writer = csv_writer or TokenizedCsvWriter()
        self.validator = validator or MTDPPackageValidator()

    def create_package(
        self,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        output_path: str | Path,
        enrichment: Mapping[str, EnrichedFieldValue | Any] | None = None,
        *,
        field_units: Mapping[str, str | None] | None = None,
    ) -> ValidationResult:
        enrichment = enrichment or {}
        field_units = field_units or {}
        dataset_values: dict[str, EnrichedFieldValue | Any] = {}
        run_values: dict[str, EnrichedFieldValue | Any] = {}
        dataset_ids = {field.field_id for field in schema.dataset_fields}
        for field_id, value in enrichment.items():
            if field_id in dataset_ids:
                dataset_values[field_id] = value
            else:
                run_values[field_id] = value
        if schema.dataset_fields and "sample_type" not in dataset_values:
            dataset_values["sample_type"] = parsed.sample_id or parsed.source_file.stem

        return self.create_dataset_package(
            [RunInput("run_001", parsed, run_values, field_units)],
            schema,
            output_path,
            dataset_values,
            dataset_field_units=field_units,
        )

    def create_dataset_package(
        self,
        runs: Sequence[RunInput],
        schema: MTDPSchema,
        output_path: str | Path,
        dataset_fields: Mapping[str, EnrichedFieldValue | Any],
        dataset_field_units: Mapping[str, str | None] | None = None,
        grouping_confirmation: Mapping[str, Any] | None = None,
        supplemental_files: Sequence[SupplementalFile] = (),
    ) -> ValidationResult:
        output_path = Path(output_path)
        result = ValidationResult()
        if not runs:
            result.add_error("At least one run is required.", code="missing_runs")
            return result
        run_ids = [run.run_id for run in runs]
        if len(set(run_ids)) != len(run_ids):
            result.add_error("Run IDs must be unique.", code="duplicate_run_id")
            return result

        normalized_dataset_input = self._coerce_user_values(dataset_fields, dataset_field_units or {})
        normalized_dataset_fields, dataset_validation = schema.validate_dataset_fields(normalized_dataset_input)
        if not dataset_validation.ok:
            return dataset_validation

        dataset_payload = self._build_dataset_json(schema, normalized_dataset_fields, run_ids)
        manifest = build_manifest(schema)
        schema_payload = schema.to_dict()
        provenance: dict[str, Any] = {
            "dataset_events": [package_created_event()],
            "runs": {},
            "migration_events": [],
        }
        source_root = common_source_root(run.parsed.source_file for run in runs)
        source_identities = build_source_identities(
            (run.parsed.source_file for run in runs),
            root=source_root,
        )
        if source_root is not None:
            provenance["source_identity"] = {
                "source_root": str(source_root),
                "identity_rule": "physical source files are identified by source_path/source_relative_path, not basename",
            }
        if grouping_confirmation is not None:
            provenance["dataset_events"].append(
                grouping_confirmed_event(
                    group_name=str(
                        grouping_confirmation.get(
                            "group_name",
                            grouping_confirmation.get("bundle_name", ""),
                        )
                    ),
                    run_count=int(grouping_confirmation.get("run_count", len(runs))),
                    manual_corrections=int(grouping_confirmation.get("manual_corrections", 0)),
                )
            )
            for removed in grouping_confirmation.get("removed_runs", ()) or ():
                if isinstance(removed, Mapping):
                    provenance["dataset_events"].append(
                        run_removed_event(
                            run_id=str(removed.get("run_id", "")),
                            original_filename=(
                                str(removed.get("original_filename"))
                                if removed.get("original_filename") is not None
                                else None
                            ),
                        )
                    )
        files: dict[str, bytes] = {
            MTDPAlignedLayout.manifest: _json_bytes(manifest),
            MTDPAlignedLayout.schema: _json_bytes(schema_payload),
            MTDPAlignedLayout.dataset: _json_bytes(dataset_payload),
        }

        for run in runs:
            identity = source_identities.get(Path(run.parsed.source_file).expanduser().resolve())
            run_validation = self._add_run(run, schema, files, provenance, source_identity=identity)
            if not run_validation.ok:
                return run_validation

        self._add_mapping_profile_events(runs, files, provenance)
        supplemental_validation = self._add_dataset_supplemental_files(supplemental_files, files, provenance)
        if not supplemental_validation.ok:
            return supplemental_validation

        files[MTDPAlignedLayout.provenance] = _json_bytes(provenance)
        files[MTDPAlignedLayout.checksums] = _json_bytes(
            build_checksums(files, checksum_member=MTDPAlignedLayout.checksums)
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for member, content in sorted(files.items()):
                archive.writestr(member, content)

        return self.validator.validate(output_path)

    def _add_run(
        self,
        run: RunInput,
        schema: MTDPSchema,
        files: dict[str, bytes],
        provenance: dict[str, Any],
        *,
        source_identity: SourceIdentity | None = None,
    ) -> ValidationResult:
        user_values = self._coerce_user_values(run.enrichment, run.field_units)
        existing_fields = self._existing_fields(run.parsed, schema)
        if "specimen_name" not in existing_fields and run.parsed.sample_id:
            existing_fields["specimen_name"] = EnrichedFieldValue(run.parsed.sample_id, source="parser_hint")

        normalized_fields, field_validation = schema.validate_run_fields(
            user_values,
            existing_tokens=existing_fields,
        )
        if not field_validation.ok:
            return field_validation

        table = self.normalizer.normalize(run.parsed, schema)
        if not table.validation.ok:
            return table.validation

        normalized_csv = self.csv_writer.write_string(run.parsed, schema, normalized_fields, table)
        raw_member = self._raw_member_name(schema, run)
        normalized_member = self._normalized_member_name(schema, run.run_id)
        files[raw_member] = run.parsed.source_file.read_bytes()
        files[normalized_member] = normalized_csv.encode("utf-8")

        identity = source_identity
        run_provenance: dict[str, Any] = {
            "original_filename": run.parsed.source_file.name,
            "source_path": str(identity.source_path if identity is not None else run.parsed.source_file),
            "source_relative_path": identity.source_relative_path if identity is not None else run.parsed.source_file.name,
            "source_basename": identity.source_basename if identity is not None else run.parsed.source_file.name,
            "parent_folder_name": identity.parent_folder_name if identity is not None else run.parsed.source_file.parent.name,
            "source_display_name": identity.source_display_name if identity is not None else run.parsed.source_file.name,
            "raw_package_path": raw_member,
            "normalized_package_path": normalized_member,
            "acquisition_context": {},
            "processing_events": [
                parsed_event(self.parser_adapter.parser_name, self.parser_adapter.parser_version)
            ],
        }
        confirmation = user_confirmation_event(
            field_id for field_id, value in normalized_fields.items() if value.source == "user"
        )
        if confirmation is not None:
            run_provenance["processing_events"].append(confirmation)
        run_provenance["processing_events"].extend(event.to_dict() for event in table.events)
        self._route_provenance_fields(schema, run.run_id, normalized_fields, run_provenance)
        optional_validation = self._add_optional_run_evidence(run, files, run_provenance)
        if not optional_validation.ok:
            return optional_validation
        provenance["runs"][run.run_id] = run_provenance
        return ValidationResult()

    def _add_optional_run_evidence(
        self,
        run: RunInput,
        files: dict[str, bytes],
        run_provenance: dict[str, Any],
    ) -> ValidationResult:
        result = ValidationResult()
        if run.supplemental_yaml is not None:
            sidecar = Path(run.supplemental_yaml)
            if not sidecar.exists():
                result.add_error(f"Supplemental YAML does not exist: {sidecar}", field=str(sidecar), code="missing_sidecar")
                return result
            member = self._supplemental_member_name(run.run_id)
            files[member] = sidecar.read_bytes()
            run_provenance.setdefault("supplemental_inputs", []).append(
                supplemental_input_record(
                    original_filename=sidecar.name,
                    package_path=member,
                    used_for_prefill=True,
                    conflicts=len(run.import_conflicts),
                    unknown_keys=run.unknown_supplemental_keys,
                    import_mode=run.supplemental_import_mode,
                    mapping_profile_id=run.mapping_profile_id,
                    mapping_profile_path=(
                        self._mapping_profile_member_name(run.mapping_profile_id)
                        if run.mapping_profile_id and run.mapping_profile_path
                        else None
                    ),
                )
            )
            imported_fields = [
                field_id
                for field_id, value in run.enrichment.items()
                if isinstance(value, EnrichedFieldValue) and "supplemental_yaml" in value.source
            ]
            run_provenance["processing_events"].append(
                sidecar_import_event(
                    package_path=member,
                    imported_fields=imported_fields,
                    unknown_keys=run.unknown_supplemental_keys,
                    import_mode=run.supplemental_import_mode,
                    mapping_profile_id=run.mapping_profile_id,
                )
            )
            reconciliation = self._reconciliation_event_for_run(run)
            if reconciliation is not None:
                run_provenance["processing_events"].append(reconciliation)

        image_records: list[dict[str, object]] = []
        image_events: list[dict[str, object]] = []
        for image in run.images:
            image_path = Path(image.source_path)
            if not image_path.exists():
                result.add_error(f"Image evidence does not exist: {image_path}", field=str(image_path), code="missing_image")
                return result
            member = self._image_member_name(files, run.run_id, image)
            files[member] = image_path.read_bytes()
            image_records.append(
                image_evidence_record(
                    package_path=member,
                    original_filename=image_path.name,
                    view=image.view,
                    role=image.role,
                    used_for_metrology=image.used_for_metrology,
                    notes=image.notes,
                )
            )
            image_events.append(
                image_evidence_added_event(
                    run_id=run.run_id,
                    package_path=member,
                    view=image.view,
                    role=image.role,
                )
            )
        if image_records:
            run_provenance["image_evidence"] = image_records
            run_provenance["processing_events"].extend(image_events)
        for supplemental in run.supplemental_files:
            supplemental_validation = self._add_general_supplemental_file(
                supplemental,
                files,
                run_provenance.setdefault("supplemental_inputs", []),
                run_id=run.run_id,
            )
            if not supplemental_validation.ok:
                return supplemental_validation
        return result

    def _add_dataset_supplemental_files(
        self,
        supplemental_files: Sequence[SupplementalFile],
        files: dict[str, bytes],
        provenance: dict[str, Any],
    ) -> ValidationResult:
        result = ValidationResult()
        records: list[dict[str, object]] = []
        for supplemental in supplemental_files:
            supplemental_result = self._add_general_supplemental_file(supplemental, files, records)
            if not supplemental_result.ok:
                return supplemental_result
        if records:
            provenance["supplemental_files"] = records
            provenance["dataset_events"].extend(
                supplemental_file_added_event(
                    package_path=str(record.get("package_path", "")),
                    scope=str(record.get("scope", "dataset")),
                    role=str(record.get("role", "other")),
                )
                for record in records
            )
        return result

    def _add_general_supplemental_file(
        self,
        supplemental: SupplementalFile,
        files: dict[str, bytes],
        records: list[dict[str, object]],
        *,
        run_id: str | None = None,
    ) -> ValidationResult:
        result = ValidationResult()
        path = Path(supplemental.source_path)
        if not path.exists():
            result.add_error(f"Supplemental file does not exist: {path}", field=str(path), code="missing_supplemental")
            return result
        member = self._supplemental_file_member_name(files, supplemental, run_id=run_id)
        files[member] = path.read_bytes()
        record: dict[str, object] = {
            "type": "supplemental_file",
            "scope": supplemental.scope,
            "role": supplemental.role,
            "original_filename": path.name,
            "package_path": member,
        }
        if run_id:
            record["run_id"] = run_id
        if supplemental.notes:
            record["notes"] = supplemental.notes
        records.append(record)
        return result

    def _reconciliation_event_for_run(self, run: RunInput) -> dict[str, object] | None:
        if not run.supplemental_yaml:
            return None
        date_transforms: list[dict[str, object]] = []
        value_transforms: list[dict[str, object]] = []
        unit_assumptions: list[dict[str, object]] = []
        if run.mapping_profile_path and Path(run.mapping_profile_path).exists():
            try:
                import yaml

                payload = yaml.safe_load(Path(run.mapping_profile_path).read_text(encoding="utf-8"))
            except Exception:
                payload = None
            if isinstance(payload, dict):
                for rule in payload.get("mappings", ()) or ():
                    if not isinstance(rule, dict) or rule.get("action") != "map":
                        continue
                    source_key = str(rule.get("source_key", ""))
                    field_id = str(rule.get("target_field_id", ""))
                    if rule.get("date_format"):
                        date_transforms.append(
                            {"source_key": source_key, "field_id": field_id, "format": str(rule.get("date_format"))}
                        )
                    if rule.get("value_transform"):
                        value_transforms.append(
                            {
                                "source_key": source_key,
                                "field_id": field_id,
                                "transform": str(rule.get("value_transform")),
                            }
                        )
                    if rule.get("unit"):
                        unit_assumptions.append(
                            {
                                "source_key": source_key,
                                "field_id": field_id,
                                "unit": str(rule.get("unit")),
                                "source": "mapping_profile",
                            }
                        )
        if not any((date_transforms, value_transforms, unit_assumptions, run.mapping_profile_id)):
            return None
        return yaml_reconciliation_confirmed_event(
            run_id=run.run_id,
            mapping_profile_id=run.mapping_profile_id,
            date_transforms=date_transforms,
            value_transforms=value_transforms,
            unit_assumptions=unit_assumptions,
            user_confirmed=True,
        )

    def _add_mapping_profile_events(
        self,
        runs: Sequence[RunInput],
        files: dict[str, bytes],
        provenance: dict[str, Any],
    ) -> None:
        applied: dict[str, tuple[str, Path, list[str]]] = {}
        for run in runs:
            if not run.mapping_profile_id or not run.mapping_profile_path:
                continue
            path = Path(run.mapping_profile_path)
            if not path.exists():
                continue
            member = self._mapping_profile_member_name(run.mapping_profile_id)
            files.setdefault(member, path.read_bytes())
            if run.mapping_profile_id not in applied:
                applied[run.mapping_profile_id] = (member, path, [])
            applied[run.mapping_profile_id][2].append(run.run_id)
        for profile_id, (member, _path, run_ids) in applied.items():
            provenance["dataset_events"].append(
                yaml_mapping_profile_applied_event(
                    mapping_profile_id=profile_id,
                    mapping_profile_path=member,
                    applied_to_runs=run_ids,
                )
            )

    def _coerce_user_values(
        self,
        enrichment: Mapping[str, EnrichedFieldValue | Any],
        field_units: Mapping[str, str | None],
    ) -> dict[str, EnrichedFieldValue]:
        values: dict[str, EnrichedFieldValue] = {}
        for field_id, value in enrichment.items():
            if isinstance(value, EnrichedFieldValue):
                values[field_id] = value
            else:
                values[field_id] = EnrichedFieldValue(value, field_units.get(field_id), source="user")
        return values

    def _existing_fields(self, parsed: ParsedSampleRecord, schema: MTDPSchema) -> dict[str, EnrichedFieldValue]:
        existing: dict[str, EnrichedFieldValue] = {}
        for token in parsed.preamble_tokens:
            field = schema.field_by_token(token.raw_key)
            if field is None and token.normalized_key:
                field = next(
                    (item for item in schema.run_fields if item.field_id == token.normalized_key),
                    None,
                )
            if field is None:
                continue
            existing[field.field_id] = EnrichedFieldValue(
                token.coerced_value_text or token.raw_value,
                token.raw_unit,
                "parser_token",
            )
        return existing

    def _build_dataset_json(
        self,
        schema: MTDPSchema,
        fields: Mapping[str, EnrichedFieldValue],
        run_ids: Sequence[str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for definition in schema.dataset_fields:
            value = fields.get(definition.field_id)
            if value is None or value.value in (None, ""):
                continue
            if definition.storage.location == "dataset_json" and definition.storage.path:
                _set_dotted_value(payload, definition.storage.path, _field_payload(value))
        if "sample_type" in payload and "sample_type_key" not in payload:
            payload["sample_type_key"] = _canonical_key(str(payload["sample_type"]))
        payload["run_order"] = list(run_ids)
        return payload

    def _route_provenance_fields(
        self,
        schema: MTDPSchema,
        run_id: str,
        fields: Mapping[str, EnrichedFieldValue],
        run_provenance: dict[str, Any],
    ) -> None:
        for definition in schema.run_fields:
            if definition.storage.location != "provenance" or not definition.storage.path:
                continue
            value = fields.get(definition.field_id)
            if value is None or value.value in (None, ""):
                continue
            path = definition.storage.path.format(run_id=run_id)
            prefix = f"runs.{run_id}."
            if path.startswith(prefix):
                path = path[len(prefix):]
            _set_dotted_value(run_provenance, path, _field_payload(value))

    def _raw_member_name(self, schema: MTDPSchema, run: RunInput) -> str:
        suffix = run.parsed.source_file.suffix or ".raw"
        return f"{MTDPAlignedLayout.raw_prefix}{run.run_id}_raw{suffix}"

    def _normalized_member_name(self, schema: MTDPSchema, run_id: str) -> str:
        normalized_extension = schema.package.get("normalized_extension", ".csv")
        return f"{MTDPAlignedLayout.normalized_prefix}{run_id}_normalized{normalized_extension}"

    def _supplemental_member_name(self, run_id: str) -> str:
        return f"supplemental/{run_id}.yaml"

    def _mapping_profile_member_name(self, mapping_profile_id: str | None) -> str:
        safe_id = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in str(mapping_profile_id or "mapping_profile")
        ).strip("_")
        return f"supplemental/mapping_profiles/{safe_id or 'mapping_profile'}.yaml"

    def _image_member_name(
        self,
        files: Mapping[str, bytes],
        run_id: str,
        image: RunImageEvidence,
    ) -> str:
        suffix = Path(image.source_path).suffix.lower() or ".img"
        view = "".join(char if char.isalnum() or char in "-_" else "_" for char in image.view).strip("_") or "image"
        base = f"images/{run_id}_{view}"
        candidate = f"{base}{suffix}"
        counter = 1
        while candidate in files:
            candidate = f"{base}_{counter:03d}{suffix}"
            counter += 1
        return candidate

    def _supplemental_file_member_name(
        self,
        files: Mapping[str, bytes],
        supplemental: SupplementalFile,
        *,
        run_id: str | None = None,
    ) -> str:
        source = Path(supplemental.source_path)
        safe_name = "".join(char if char.isalnum() or char in "-_." else "_" for char in source.name).strip("_")
        if supplemental.scope == "run" or run_id:
            folder = f"supplemental/runs/{run_id or supplemental.run_id or 'run'}"
        elif supplemental.role == "calibration":
            folder = "supplemental/calibration"
        elif supplemental.role == "mapping_support":
            folder = "supplemental/mapping_profiles"
        elif supplemental.role == "documents" or supplemental.scope == "dataset":
            folder = "supplemental/documents"
        else:
            folder = "supplemental/other"
        base = f"{folder}/{safe_name or 'supplemental_file'}"
        candidate = base
        counter = 1
        stem = Path(base).with_suffix("").as_posix()
        suffix = Path(base).suffix
        while candidate in files:
            candidate = f"{stem}_{counter:03d}{suffix}"
            counter += 1
        return candidate


class MTDPPackageReader:
    def inspect(self, package_path: str | Path) -> MTDPPackage:
        path = Path(package_path)
        with zipfile.ZipFile(path, "r") as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
            layout = detect_mtdp_layout(names)
            manifest = json.loads(archive.read(layout.manifest).decode("utf-8"))
            schema = json.loads(archive.read(layout.schema).decode("utf-8"))
            provenance = json.loads(archive.read(layout.provenance).decode("utf-8"))
            dataset = json.loads(archive.read(layout.dataset).decode("utf-8")) if layout.dataset in names else {}
        return MTDPPackage(path=path, manifest=manifest, schema=schema, provenance=provenance, dataset=dataset)

    def read_member(self, package_path: str | Path, member: str) -> bytes:
        with zipfile.ZipFile(package_path, "r") as archive:
            return archive.read(member)


class MTDPPackageUpdater:
    """Small coordination facade for read-validate-rewrite package workflows."""

    def __init__(
        self,
        reader: MTDPPackageReader | None = None,
        writer: MTDPPackageWriter | None = None,
        validator: MTDPPackageValidator | None = None,
    ) -> None:
        self.reader = reader or MTDPPackageReader()
        self.writer = writer or MTDPPackageWriter()
        self.validator = validator or MTDPPackageValidator()

    def inspect_for_update(self, package_path: str | Path) -> tuple[MTDPPackage, ValidationResult]:
        validation = self.validator.validate(package_path)
        package = self.reader.inspect(package_path) if validation.ok else MTDPPackage(
            path=Path(package_path),
            manifest={},
            schema={},
            provenance={},
            dataset={},
        )
        return package, validation


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _field_payload(value: EnrichedFieldValue) -> Any:
    if isinstance(value.value, float) and value.unit:
        return {"value": value.value, "unit": value.unit}
    if value.unit and not isinstance(value.value, str):
        return {"value": value.value, "unit": value.unit}
    if value.unit and _looks_numeric(value.value):
        return {"value": value.value, "unit": value.unit}
    return value.value


def _looks_numeric(value: Any) -> bool:
    try:
        float(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _set_dotted_value(payload: dict[str, Any], path: str, value: Any) -> None:
    cursor = payload
    parts = [part for part in path.split(".") if part]
    for part in parts[:-1]:
        next_value = cursor.setdefault(part, {})
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    if parts:
        cursor[parts[-1]] = value


def _canonical_key(value: str) -> str:
    import re

    return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", value).casefold()).strip()
