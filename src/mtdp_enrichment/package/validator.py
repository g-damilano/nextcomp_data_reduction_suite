from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from archives.core.layouts import MTDPAlignedLayout, MTDPLayout, MTDPLegacyLayout, detect_mtdp_layout
from mtdp_enrichment.models import ValidationResult
from mtdp_enrichment.package.checksums import sha256_bytes
from mtdp_enrichment.package.manifest import DISALLOWED_MANIFEST_FIELDS, PACKAGE_FORMAT
from mtdp_enrichment.package.schema import MTDPSchema


REQUIRED_PACKAGE_FILES = {
    "manifest.json",
    "schema.json",
    "dataset.json",
    "provenance.json",
    "checksums.json",
}
REQUIRED_ALIGNED_PACKAGE_FILES = {
    "metadata/manifest.json",
    "metadata/schema.json",
    "metadata/dataset.json",
    "metadata/provenance.json",
    "metadata/checksums.json",
}
CHECKSUM_MEMBERS = {
    "checksums.json",
    "metadata/checksums.json",
    "software/checksums.json",
}


def _required_package_files(layout: type[MTDPLayout]) -> set[str]:
    if layout is MTDPAlignedLayout:
        return set(REQUIRED_ALIGNED_PACKAGE_FILES)
    if layout is MTDPLegacyLayout:
        return set(REQUIRED_PACKAGE_FILES)
    return {layout.manifest, layout.schema, layout.dataset, layout.provenance, layout.checksums}


class MTDPPackageValidator:
    def validate(self, package_path: str | Path) -> ValidationResult:
        result = ValidationResult()
        path = Path(package_path)
        if not path.exists():
            result.add_error(f"Package does not exist: {path}", code="missing_package")
            return result
        if path.suffix.lower() != ".mtdp":
            result.add_warning(f"Package extension is not .mtdp: {path.name}", code="extension")

        try:
            with zipfile.ZipFile(path, "r") as archive:
                names = {name for name in archive.namelist() if not name.endswith("/")}
                try:
                    layout = detect_mtdp_layout(names)
                except ValueError as exc:
                    result.add_error(str(exc), code="missing_member")
                    return result
                missing = _required_package_files(layout) - names
                for item in sorted(missing):
                    result.add_error(f"Missing required package file: {item}", code="missing_member")
                if result.errors:
                    return result

                manifest = json.loads(archive.read(layout.manifest).decode("utf-8"))
                schema_payload = json.loads(archive.read(layout.schema).decode("utf-8"))
                dataset = json.loads(archive.read(layout.dataset).decode("utf-8"))
                provenance = json.loads(archive.read(layout.provenance).decode("utf-8"))
                schema = MTDPSchema.from_dict(schema_payload)

                self._validate_manifest(manifest, schema, result, layout)
                self._validate_embedded_schema(schema, result, layout)
                self._validate_run_pairing(names, result, layout)
                self._validate_schema_content(archive, names, schema, dataset, provenance, result, layout)
                self._validate_optional_evidence(archive, names, schema, provenance, result, layout)
                self._validate_provenance_events(provenance, result)
                self._validate_checksums(archive, names, result, layout)
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError, ValueError) as exc:
            result.add_error(f"Could not validate package: {exc}", code="package_read_error")

        return result

    def _validate_manifest(
        self,
        manifest: dict[str, object],
        schema: MTDPSchema,
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        if manifest.get("package_format") != PACKAGE_FORMAT:
            result.add_error(f"{layout.manifest} does not declare package_format=mtdp.", code="bad_manifest")
        for field in DISALLOWED_MANIFEST_FIELDS:
            if field in manifest:
                result.add_error(
                    f"{layout.manifest} includes redundant field '{field}'.",
                    field=field,
                    code="redundant_manifest_field",
                )
        if manifest.get("schema_id") != schema.schema_id:
            result.add_error("Manifest schema_id does not match schema.json.", code="schema_mismatch")
        if str(manifest.get("schema_version")) != schema.schema_version:
            result.add_error("Manifest schema_version does not match schema.json.", code="schema_mismatch")

    def _validate_embedded_schema(
        self,
        schema: MTDPSchema,
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        from mtdp_enrichment.schemas.linter import lint_schema

        lint = lint_schema(schema)
        for issue in lint.errors:
            result.add_error(
                f"{layout.schema} failed schema lint: {issue.message}",
                field=issue.field,
                code=issue.code,
            )
        for issue in lint.warnings:
            result.add_warning(
                f"{layout.schema} schema lint warning: {issue.message}",
                field=issue.field,
                code=issue.code,
            )

    def _validate_run_pairing(
        self,
        names: set[str],
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        raw_members = [name for name in names if name.startswith(layout.raw_prefix)]
        normalized_members = [name for name in names if name.startswith(layout.normalized_prefix) and name.endswith(".csv")]
        if not raw_members:
            result.add_error("Package does not contain preserved raw run files.", code="missing_raw")
        if not normalized_members:
            result.add_error("Package does not contain normalized run CSV files.", code="missing_normalized")
        raw_stems = {layout.run_stem(name) for name in raw_members}
        normalized_stems = {layout.run_stem(name) for name in normalized_members}
        for stem in sorted(normalized_stems - raw_stems):
            result.add_error(f"Normalized run {stem} has no matching raw run.", code="missing_raw_counterpart")
        for stem in sorted(raw_stems - normalized_stems):
            result.add_error(f"Raw run {stem} has no matching normalized run.", code="missing_normalized_counterpart")

    def _validate_schema_content(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        schema: MTDPSchema,
        dataset: dict[str, object],
        provenance: dict[str, object],
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        for field in schema.dataset_fields:
            if field.required and field.storage.location == "dataset_json" and field.storage.path:
                if _get_dotted_value(dataset, field.storage.path) in (None, ""):
                    result.add_error(f"{layout.dataset} is missing required field {field.field_id}.", code="missing_dataset_field")

        normalized_members = sorted(name for name in names if name.startswith(layout.normalized_prefix) and name.endswith(".csv"))
        provenance_runs = provenance.get("runs", {})
        if not isinstance(provenance_runs, dict):
            result.add_error(f"{layout.provenance} must contain a runs mapping.", code="bad_provenance")
            provenance_runs = {}
        for member in normalized_members:
            run_id = layout.run_stem(member)
            if run_id not in provenance_runs:
                result.add_error(f"{layout.provenance} is missing run entry {run_id}.", code="missing_run_provenance")
            tokens = _read_token_preamble(archive.read(member).decode("utf-8-sig"))
            for field in schema.run_fields:
                if not field.required:
                    continue
                if field.storage.location == "token_preamble" and field.storage.token:
                    if field.storage.token.casefold() not in tokens:
                        result.add_error(
                            f"{member} is missing required token {field.storage.token}.",
                            field=field.field_id,
                            code="missing_run_token",
                        )
                elif field.storage.location == "provenance" and field.storage.path:
                    path = field.storage.path.format(run_id=run_id)
                    prefix = f"runs.{run_id}."
                    if path.startswith(prefix):
                        path = path[len(prefix):]
                    run_payload = provenance_runs.get(run_id, {})
                    if _get_dotted_value(run_payload, path) in (None, ""):
                        result.add_error(
                            f"{layout.provenance} is missing required run field {field.field_id}.",
                            field=field.field_id,
                            code="missing_run_provenance_field",
                        )

    def _validate_checksums(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        checksums = json.loads(archive.read(layout.checksums).decode("utf-8"))
        if checksums.get("algorithm") != "sha256":
            result.add_error(f"{layout.checksums} must use sha256.", code="checksum_algorithm")
        recorded = checksums.get("files", {})
        for name, expected_hash in recorded.items():
            if name not in names:
                result.add_error(f"Checksum references missing file: {name}", code="checksum_missing_file")
                continue
            actual_hash = sha256_bytes(archive.read(name))
            if actual_hash != expected_hash:
                result.add_error(f"Checksum mismatch for {name}.", field=name, code="checksum_mismatch")
        for name in sorted(names - CHECKSUM_MEMBERS):
            if name.startswith("__MACOSX/"):
                continue
            if name not in recorded:
                result.add_warning(f"No checksum recorded for {name}.", field=name, code="checksum_absent")

    def _validate_optional_evidence(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        schema: MTDPSchema,
        provenance: dict[str, object],
        result: ValidationResult,
        layout: type[MTDPLayout],
    ) -> None:
        checksums = json.loads(archive.read(layout.checksums).decode("utf-8"))
        recorded_checksums = checksums.get("files", {})
        provenance_runs = provenance.get("runs", {})
        if not isinstance(provenance_runs, dict):
            return

        image_config = schema.image_evidence_config()
        accepted_formats = {str(item).lower() for item in image_config.get("accepted_formats", ())}
        if not accepted_formats:
            accepted_formats = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
        view_defs = image_config.get("views", ()) or ()
        accepted_views = {
            str(item.get("id", "")).strip()
            for item in view_defs
            if isinstance(item, dict) and item.get("id")
        }
        if not accepted_views:
            accepted_views = {"front", "side", "top", "failure", "scale_reference", "other"}
        required_views = {
            str(item.get("id", "")).strip()
            for item in view_defs
            if isinstance(item, dict) and item.get("id") and item.get("required")
        }

        dataset_events = provenance.get("dataset_events", ())
        dataset_supplemental = provenance.get("supplemental_files", ())
        if isinstance(dataset_supplemental, list):
            for record in dataset_supplemental:
                if not isinstance(record, dict):
                    continue
                package_path = record.get("package_path")
                if isinstance(package_path, str):
                    self._validate_referenced_member(package_path, names, recorded_checksums, result, "supplemental")
        if isinstance(dataset_events, list):
            for event in dataset_events:
                if not isinstance(event, dict):
                    continue
                mapping_profile_path = event.get("mapping_profile_path")
                if isinstance(mapping_profile_path, str):
                    self._validate_referenced_member(
                        mapping_profile_path,
                        names,
                        recorded_checksums,
                        result,
                        "mapping_profile",
                    )

        for run_id, run_payload in provenance_runs.items():
            if not isinstance(run_payload, dict):
                continue
            supplemental_inputs = run_payload.get("supplemental_inputs", ())
            if isinstance(supplemental_inputs, list):
                for record in supplemental_inputs:
                    if not isinstance(record, dict):
                        continue
                    package_path = record.get("package_path")
                    if isinstance(package_path, str):
                        self._validate_referenced_member(package_path, names, recorded_checksums, result, "supplemental")
                    mapping_profile_path = record.get("mapping_profile_path")
                    if isinstance(mapping_profile_path, str):
                        self._validate_referenced_member(
                            mapping_profile_path,
                            names,
                            recorded_checksums,
                            result,
                            "mapping_profile",
                        )

            images = run_payload.get("image_evidence", ())
            image_views: set[str] = set()
            if isinstance(images, list):
                for record in images:
                    if not isinstance(record, dict):
                        continue
                    package_path = record.get("package_path")
                    view = record.get("view")
                    if isinstance(package_path, str):
                        self._validate_referenced_member(package_path, names, recorded_checksums, result, "image")
                        if Path(package_path).suffix.lower() not in accepted_formats:
                            result.add_error(
                                f"Image evidence format is not accepted: {package_path}",
                                field=package_path,
                                code="unsupported_image_format",
                            )
                    if isinstance(view, str):
                        image_views.add(view)
                        if view not in accepted_views:
                            result.add_error(
                                f"Image evidence view is not accepted: {view}",
                                field=str(package_path or run_id),
                                code="unsupported_image_view",
                            )
            if image_config.get("required") and not image_views:
                result.add_error(f"{run_id} is missing required image evidence.", field=str(run_id), code="missing_image")
            for view in sorted(required_views - image_views):
                result.add_error(
                    f"{run_id} is missing required image view {view}.",
                    field=str(run_id),
                    code="missing_image_view",
                )

    def _validate_referenced_member(
        self,
        package_path: str,
        names: set[str],
        recorded_checksums: dict[str, object],
        result: ValidationResult,
        kind: str,
    ) -> None:
        if package_path not in names:
            result.add_error(f"{kind.title()} provenance references missing file: {package_path}", code=f"missing_{kind}")
        if package_path not in recorded_checksums:
            result.add_error(
                f"{kind.title()} file is not covered by checksums: {package_path}",
                field=package_path,
                code=f"{kind}_checksum_absent",
            )

    def _validate_provenance_events(self, provenance: dict[str, object], result: ValidationResult) -> None:
        from mtdp_enrichment.package.provenance_taxonomy import KNOWN_EVENTS, event_has_minimum_shape

        events: list[object] = []
        dataset_events = provenance.get("dataset_events", ())
        migration_events = provenance.get("migration_events", ())
        if isinstance(dataset_events, list):
            events.extend(dataset_events)
        if isinstance(migration_events, list):
            events.extend(migration_events)
        runs = provenance.get("runs", {})
        if isinstance(runs, dict):
            for run_payload in runs.values():
                if not isinstance(run_payload, dict):
                    continue
                processing_events = run_payload.get("processing_events", ())
                if isinstance(processing_events, list):
                    events.extend(processing_events)
        for event in events:
            if not event_has_minimum_shape(event):
                result.add_error("Provenance event is missing required event/timestamp fields.", code="bad_provenance_event")
                continue
            event_name = str(event.get("event")) if isinstance(event, dict) else ""
            if event_name not in KNOWN_EVENTS:
                result.add_warning(f"Unknown provenance event name: {event_name}", code="unknown_provenance_event")


def _read_token_preamble(text: str) -> dict[str, list[str]]:
    tokens: dict[str, list[str]] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row:
            break
        if row and row[0].strip():
            tokens[row[0].strip().casefold()] = row[1:]
    return tokens


def _get_dotted_value(payload: object, path: str) -> object:
    cursor = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor
