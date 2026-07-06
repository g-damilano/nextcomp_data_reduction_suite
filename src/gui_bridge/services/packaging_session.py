from __future__ import annotations

import time
import uuid
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mtdp_enrichment.enrichment_import import SidecarYamlImporter, SupplementalImportResult
from mtdp_enrichment.enrichment_import.canonical_yaml import extract_value_and_unit
from mtdp_enrichment.enrichment_import.empirical_matcher import EmpiricalYamlMatcher
from mtdp_enrichment.enrichment_import.mapping_profile import (
    MappingRule,
    get_dotted_value,
    profile_for_mapping,
    profile_id_from_signature,
)
from mtdp_enrichment.enrichment_import.value_normalizers import (
    extract_unit_from_key,
    storage_preview,
    transform_value_for_field,
)
from mtdp_enrichment.grouping import GroupingInput, GroupingProposal, SampleTypeGrouper
from mtdp_enrichment.image_gateway import ImageEvidenceImporter, RunImageEvidence
from mtdp_enrichment.models import EnrichedFieldValue, ValidationResult
from mtdp_enrichment.package import MTDPPackageValidator, MTDPSchema
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaInference, SchemaRegistry
from mtdp_enrichment.services import GroupExporter, GroupLoader, ValidationService
from mtdp_enrichment.services.group_state import GroupState, RunState
from mtdp_enrichment.supplemental import SupplementalFile
from mtdp_enrichment.units import UnitValidationError, default_unit_normaliser


class PackagingSessionError(Exception):
    def __init__(
        self,
        error_type: str,
        message: str,
        *,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable
        self.details = details or {}


@dataclass(slots=True)
class PackagingSession:
    session_id: str
    created_at: float
    status: str = "empty"
    schema: MTDPSchema | None = None
    detected_schema: MTDPSchema | None = None
    schema_overridden: bool = False
    groups: list[GroupState] = field(default_factory=list)
    unassigned: list[RunState] = field(default_factory=list)
    source_paths: list[Path] = field(default_factory=list)
    package_path: Path | None = None
    messages: list[str] = field(default_factory=list)
    validation_by_group: dict[str, dict[str, Any]] = field(default_factory=dict)


class PackagingSessionService:
    """Backend-owned read-only packaging session facade for the GUI bridge."""

    def __init__(
        self,
        *,
        registry: SchemaRegistry | None = None,
        parser: ParserAdapter | None = None,
        grouper: SampleTypeGrouper | None = None,
        group_loader: GroupLoader | None = None,
        validator: MTDPPackageValidator | None = None,
        validation_service: ValidationService | None = None,
        group_exporter: GroupExporter | None = None,
        image_importer: ImageEvidenceImporter | None = None,
        sidecar_importer: SidecarYamlImporter | None = None,
        yaml_matcher: EmpiricalYamlMatcher | None = None,
    ) -> None:
        self.registry = registry or SchemaRegistry()
        self.parser = parser or ParserAdapter()
        self.grouper = grouper or SampleTypeGrouper()
        self.validator = validator or MTDPPackageValidator()
        self.group_loader = group_loader or GroupLoader(
            registry=self.registry,
            parser=self.parser,
            validator=self.validator,
        )
        self.validation_service = validation_service or ValidationService()
        self.group_exporter = group_exporter or GroupExporter()
        self.image_importer = image_importer or ImageEvidenceImporter()
        self.sidecar_importer = sidecar_importer or SidecarYamlImporter()
        self.yaml_matcher = yaml_matcher or EmpiricalYamlMatcher()
        self._sessions: dict[str, PackagingSession] = {}

    def create_session(self) -> dict[str, Any]:
        session = PackagingSession(session_id=f"pkg-{uuid.uuid4()}", created_at=time.time())
        self._sessions[session.session_id] = session
        return self._view_model(session)

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._view_model(self._require_session(session_id))

    def list_schemas(self) -> dict[str, Any]:
        schemas = [self._schema_candidate(schema, detected=False, confidence=0) for schema in self.registry.selectable()]
        return {"schemas": schemas, "count": len(schemas), "source": "SchemaRegistry.selectable"}

    def load_package(self, session_id: str, package_path: str | Path) -> dict[str, Any]:
        session = self._require_session(session_id)
        path = Path(package_path)
        if not path.exists():
            raise PackagingSessionError(
                "NotFound",
                f"MTDP package does not exist: {path}",
                details={"path": str(path)},
            )
        if path.suffix.lower() != ".mtdp":
            raise PackagingSessionError(
                "ValidationError",
                f"Expected an .mtdp package, got: {path.name}",
                details={"path": str(path)},
            )
        group = self.group_loader.load_package(path)
        session.status = "package_loaded"
        session.package_path = path
        session.schema = group.schema
        session.groups = [group]
        session.unassigned = []
        session.source_paths = [run.source_path for run in group.runs]
        session.messages = [f"Loaded package {path.name}."]
        session.detected_schema = group.schema
        session.schema_overridden = False
        session.validation_by_group = {}
        return self._view_model(session)

    def load_sources(self, session_id: str, paths: list[str | Path]) -> dict[str, Any]:
        session = self._require_session(session_id)
        source_paths = self._source_files(paths)
        if not source_paths:
            raise PackagingSessionError(
                "ValidationError",
                "No supported source files were found.",
                details={"supported_suffixes": list(self.parser.supported_suffixes())},
            )

        parsed_inputs: list[GroupingInput] = []
        first_inference: SchemaInference | None = None
        parse_messages: list[str] = []
        for source_path in source_paths:
            try:
                parsed = self.parser.parse(source_path)
            except Exception as exc:
                parse_messages.append(f"{source_path.name}: {exc}")
                continue
            inference = self.registry.infer(parsed, source_path)
            if first_inference is None:
                first_inference = inference
            parsed_inputs.append(GroupingInput(source_path=source_path, parsed=parsed, schema_inference=inference))

        if not parsed_inputs:
            raise PackagingSessionError(
                "ValidationError",
                "Source files were found, but none could be parsed.",
                details={"messages": parse_messages},
            )

        schema = first_inference.schema if first_inference is not None else self.registry.selectable()[0]
        grouping_inputs = [self._with_sidecar_import(item, schema) for item in parsed_inputs]
        proposal = self.grouper.propose(grouping_inputs, schema)
        groups: list[GroupState] = []
        input_by_path = {item.source_path: item for item in grouping_inputs}
        for bundle in proposal.bundles:
            group = GroupState(
                group_key=bundle.bundle_key,
                display_name=bundle.display_name,
                schema=schema,
            )
            for assignment in bundle.assignments:
                source_input = input_by_path.get(assignment.source_path)
                if source_input is None:
                    continue
                group.runs.append(self._run_from_grouping_input(group.runs, source_input))
            groups.append(group)

        session.status = "sources_loaded"
        session.schema = schema
        session.detected_schema = schema
        session.schema_overridden = False
        session.groups = groups
        session.unassigned = [
            self._run_from_grouping_input(groups[0].runs if groups else [], item, status="unassigned")
            for item in proposal.unassigned
        ]
        session.source_paths = source_paths
        session.package_path = None
        session.messages = [f"Loaded {len(grouping_inputs)} source file(s).", *parse_messages]
        session.validation_by_group = {}
        return self._view_model(session)

    def propose_groups(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        proposal = self._current_grouping_proposal(session)
        return {
            "session_id": session.session_id,
            "engine": self.grouper.engine_name,
            "engine_version": self.grouper.engine_version,
            "recommended_id": _proposal_id(self.grouper),
            "proposals": [self._proposal_view(proposal)],
            "warnings": [
                {
                    "source": "backend",
                    "text": f"{item.source_name} may belong with {item.target_name}.",
                    "similarity": item.similarity,
                    "reason": item.reason,
                }
                for item in proposal.suggested_merges
            ],
        }

    def apply_grouping_proposal(self, session_id: str, proposal_id: str | None = None) -> dict[str, Any]:
        session = self._require_session(session_id)
        schema = self._loaded_schema(session)
        expected_id = _proposal_id(self.grouper)
        if proposal_id and str(proposal_id) != expected_id:
            raise PackagingSessionError(
                "NotFound",
                f"Grouping proposal not found: {proposal_id}",
                details={"proposal_id": str(proposal_id), "available": [expected_id]},
            )
        proposal = self._current_grouping_proposal(session)
        runs_by_source = {
            _source_key(run.source_path): run
            for run in self._all_runs(session)
        }
        previous_group_by_key = {group.group_key: group for group in session.groups}
        previous_group_by_name = {group.display_name.casefold(): group for group in session.groups}
        previous_group_by_run = {
            _source_key(run.source_path): group
            for group in session.groups
            for run in group.runs
        }

        groups: list[GroupState] = []
        assigned_sources: set[str] = set()
        for bundle in proposal.bundles:
            group = GroupState(
                group_key=bundle.bundle_key,
                display_name=bundle.display_name,
                schema=schema,
            )
            source_keys = [_source_key(assignment.source_path) for assignment in bundle.assignments]
            source_group = (
                previous_group_by_key.get(bundle.bundle_key)
                or previous_group_by_name.get(bundle.display_name.casefold())
                or self._single_previous_group(source_keys, previous_group_by_run)
            )
            if source_group is not None:
                self._copy_group_metadata(source_group, group)
            for assignment in bundle.assignments:
                source_key = _source_key(assignment.source_path)
                run = runs_by_source.get(source_key)
                if run is None:
                    continue
                run.status = "parsed" if run.status == "unassigned" else run.status
                group.runs.append(run)
                assigned_sources.add(source_key)
            groups.append(group)

        unassigned: list[RunState] = []
        for item in proposal.unassigned:
            source_key = _source_key(item.source_path)
            run = runs_by_source.get(source_key)
            if run is None or source_key in assigned_sources:
                continue
            run.status = "unassigned"
            unassigned.append(run)
            assigned_sources.add(source_key)

        for source_key, run in runs_by_source.items():
            if source_key in assigned_sources:
                continue
            run.status = "unassigned"
            unassigned.append(run)

        session.groups = groups
        session.unassigned = unassigned
        session.validation_by_group = {}
        session.messages = [
            f"Applied grouping proposal: {len(groups)} group(s), {len(unassigned)} unassigned run(s)."
        ]
        return self._view_model(session)

    def create_group(self, session_id: str, name: str | None = None) -> dict[str, Any]:
        session = self._require_session(session_id)
        schema = session.schema
        if schema is None:
            raise PackagingSessionError(
                "ValidationError",
                "A package or source batch must be loaded before creating groups.",
            )
        display_name = str(name or "New group").strip() or "New group"
        key = self._unique_group_key(session, display_name)
        session.groups.append(
            GroupState(
                group_key=key,
                display_name=display_name,
                schema=schema,
                manual_corrections=1,
            )
        )
        session.messages = [f"Created group {display_name}."]
        return self._view_model(session)

    def rename_group(self, session_id: str, group_id: str, name: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        clean = str(name or "").strip()
        if not clean:
            raise PackagingSessionError(
                "ValidationError",
                "Group name is required.",
                details={"group_id": group.group_key},
            )
        group.display_name = clean
        group.manual_corrections += 1
        session.messages = [f"Renamed group to {clean}."]
        return self._view_model(session)

    def delete_group(self, session_id: str, group_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        session.groups.remove(group)
        moved = len(group.runs)
        for run in group.runs:
            run.status = "unassigned"
            session.unassigned.append(run)
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [
            (
                f"Deleted group {group.display_name}; moved {moved} run(s) to Unassigned."
                if moved
                else f"Deleted empty group {group.display_name}."
            )
        ]
        return self._view_model(session)

    def move_run(
        self,
        session_id: str,
        run_id: str,
        target_group_id: str,
        *,
        from_group_id: str | None = None,
        index: int | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        run, source_group = self._detach_run(session, run_id, from_group_id)
        target_label = "Unassigned"
        if target_group_id == "__unassigned":
            run.status = "unassigned"
            self._insert_run(session.unassigned, run, index)
        else:
            target = self._find_group(session, target_group_id)
            run.status = "parsed" if run.status == "unassigned" else run.status
            self._insert_run(target.runs, run, index)
            target.manual_corrections += 1
            target_label = target.display_name
            session.validation_by_group.pop(target.group_key, None)
        if source_group is not None:
            source_group.manual_corrections += 1
            session.validation_by_group.pop(source_group.group_key, None)
        session.messages = [f"Moved {run.run_id} to {target_label}."]
        return self._view_model(session)

    def add_image_evidence(
        self,
        session_id: str,
        group_id: str | None,
        run_id: str,
        paths: list[str | Path],
        *,
        view: str | None = None,
        role: str = "audit_evidence",
        notes: str | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id)
        source_paths = self._non_empty_paths(paths, "packaging.addImageEvidence")
        added = 0
        errors: list[str] = []
        for path in source_paths:
            evidence, validation = self.image_importer.make_evidence(
                path,
                group.schema,
                view=view,
                role=role,
                notes=notes,
            )
            if validation.ok and evidence is not None:
                run.images.append(evidence)
                added += 1
            else:
                errors.extend(validation.messages())
        if added == 0:
            raise PackagingSessionError(
                "ValidationError",
                "No image evidence file could be attached.",
                details={"errors": errors, "paths": [str(path) for path in source_paths]},
            )
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [
            f"Added {added} image evidence file(s) to {run.run_id}."
            + (f" Skipped {len(errors)} invalid file(s)." if errors else "")
        ]
        return self._view_model(session)

    def remove_image_evidence(
        self,
        session_id: str,
        group_id: str | None,
        run_id: str,
        index: int,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id)
        if index < 0 or index >= len(run.images):
            raise PackagingSessionError(
                "NotFound",
                f"Image evidence not found at index {index}.",
                details={"group_id": group.group_key, "run_id": run.run_id, "index": index},
            )
        removed = run.images.pop(index)
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Removed image evidence {Path(removed.source_path).name} from {run.run_id}."]
        return self._view_model(session)

    def add_supplemental_files(
        self,
        session_id: str,
        group_id: str | None,
        paths: list[str | Path],
        *,
        scope: str = "dataset",
        run_id: str | None = None,
        role: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        source_paths = self._non_empty_paths(paths, "packaging.addSupplementalFiles")
        clean_scope = _supplemental_scope(scope)
        target_run = self._find_run(group, run_id) if clean_scope == "run" else None
        if clean_scope == "run" and target_run is None:
            raise PackagingSessionError(
                "ValidationError",
                "Run-scoped supplemental files require run_id.",
                details={"group_id": group.group_key, "scope": clean_scope},
            )
        clean_role = str(role or _supplemental_role(clean_scope)).strip() or "other"
        clean_notes = str(notes).strip() if notes is not None and str(notes).strip() else None
        files = [
            SupplementalFile(
                source_path=path,
                scope=clean_scope,
                role=clean_role,
                run_id=target_run.run_id if target_run is not None else None,
                notes=clean_notes,
            )
            for path in source_paths
        ]
        if target_run is not None:
            target_run.supplemental_files.extend(files)
            target_label = target_run.run_id
        else:
            group.supplemental_files.extend(files)
            target_label = group.display_name
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Added {len(files)} supplemental file(s) to {target_label}."]
        return self._view_model(session)

    def remove_supplemental_file(
        self,
        session_id: str,
        group_id: str | None,
        index: int,
        *,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id) if run_id else None
        if index < 0:
            raise PackagingSessionError(
                "NotFound",
                f"Supplemental file not found at index {index}.",
                details={"group_id": group.group_key, "run_id": run_id, "index": index},
            )
        if index < len(group.supplemental_files):
            removed = group.supplemental_files.pop(index)
            target_label = group.display_name
        elif run is not None and index - len(group.supplemental_files) < len(run.supplemental_files):
            removed = run.supplemental_files.pop(index - len(group.supplemental_files))
            target_label = run.run_id
        else:
            raise PackagingSessionError(
                "NotFound",
                f"Supplemental file not found at index {index}.",
                details={"group_id": group.group_key, "run_id": run_id, "index": index},
            )
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Removed supplemental file {Path(removed.source_path).name} from {target_label}."]
        return self._view_model(session)

    def rematch_yaml_sidecars(
        self,
        session_id: str,
        group_id: str | None = None,
        *,
        run_id: str | None = None,
        apply_all: bool = True,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        runs = list(group.runs) if apply_all or not run_id else [self._find_run(group, run_id)]
        if not runs:
            raise PackagingSessionError(
                "ValidationError",
                "No runs are available for YAML sidecar matching.",
                details={"group_id": group.group_key},
            )

        paired = 0
        updated = 0
        requires_mapping = 0
        warnings: list[str] = []
        pairs: list[dict[str, Any]] = []
        for run in runs:
            result = self.sidecar_importer.import_for_run(
                run.source_path,
                run.parsed,
                group.schema,
                existing_values=run.enrichment,
            )
            before_values = _field_values(run.enrichment)
            self._apply_sidecar_result_to_run(run, result)
            after_values = _field_values(run.enrichment)
            if result.source_path is not None:
                paired += 1
            if before_values != after_values or result.source_path is not None:
                updated += 1
            if result.requires_mapping:
                requires_mapping += 1
            warnings.extend(result.warnings)
            pairs.append(_sidecar_pair_view(run, result))

        summary = {
            "source": "backend",
            "rule": "same_stem",
            "groupId": group.group_key,
            "runCount": len(runs),
            "pairedCount": paired,
            "updatedCount": updated,
            "requiresMappingCount": requires_mapping,
            "warningCount": len(warnings),
            "warnings": warnings,
            "pairs": pairs,
        }
        session.validation_by_group.pop(group.group_key, None)
        message = f"Re-matched YAML sidecars: {paired}/{len(runs)} paired by base name."
        if requires_mapping:
            message += f" {requires_mapping} run(s) still require mapping review."
        session.messages = [message]
        view = self._view_model(session)
        view["yamlRematch"] = summary
        view["yaml_rematch"] = summary
        return view

    def review_yaml_mapping(
        self,
        session_id: str,
        group_id: str | None = None,
        *,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id) if run_id else self._first_run_with_sidecar(group)
        result = self._sidecar_document_result(group, run)
        document = result.document
        if document is None:
            raise PackagingSessionError(
                "ValidationError",
                "Selected run has no readable supplemental YAML document.",
                details={"group_id": group.group_key, "run_id": run.run_id},
            )
        rows = [
            self._yaml_mapping_review_row(group.schema, document, key)
            for key in document.key_paths
            if _is_yaml_review_key(key)
        ]
        review = {
            "source": "backend",
            "groupId": group.group_key,
            "runId": run.run_id,
            "yamlPath": str(document.source_path),
            "profileId": profile_id_from_signature("supplemental_yaml", document.structure_signature),
            "structureSignature": document.structure_signature,
            "applyAllDefault": True,
            "requiresMapping": result.requires_mapping,
            "unknownKeys": list(result.unknown_keys),
            "conflicts": [_field_conflict_view(conflict) for conflict in result.conflicts],
            "warnings": list(result.warnings),
            "fieldOptions": [_field_option(field) for field in group.schema.dataset_fields + group.schema.run_fields],
            "rows": rows,
            "summary": {
                "rowCount": len(rows),
                "mappedCount": sum(1 for row in rows if row["mapping"]["action"] == "map"),
                "reviewCount": sum(1 for row in rows if row["requiresConfirmation"]),
                "unknownCount": len(result.unknown_keys),
                "conflictCount": len(result.conflicts),
            },
        }
        return {
            "session_id": session.session_id,
            "status": session.status,
            "yamlMappingReview": review,
            "yaml_mapping_review": review,
        }

    def apply_yaml_mapping_profile(
        self,
        session_id: str,
        group_id: str | None = None,
        *,
        run_id: str | None = None,
        profile_id: str | None = None,
        mappings: list[dict[str, Any]] | None = None,
        apply_all: bool = True,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id) if run_id else self._first_run_with_sidecar(group)
        result = self._sidecar_document_result(group, run)
        document = result.document
        if document is None:
            raise PackagingSessionError(
                "ValidationError",
                "Selected run has no readable supplemental YAML document.",
                details={"group_id": group.group_key, "run_id": run.run_id},
            )
        if not isinstance(mappings, list) or not mappings:
            raise PackagingSessionError(
                "ValidationError",
                "YAML mapping profile application requires a non-empty mappings list.",
                details={"mappings_type": type(mappings).__name__},
            )
        rules = tuple(self._mapping_rule_from_payload(group.schema, item) for item in mappings)
        clean_profile_id = str(profile_id or "").strip() or profile_id_from_signature(
            "supplemental_yaml",
            document.structure_signature,
        )
        profile = profile_for_mapping(
            profile_id=clean_profile_id,
            schema=group.schema,
            payload=document.raw_payload,
            mappings=rules,
        )
        saved_path = profile.save(self._mapping_profile_root(session, run) / f"{profile.mapping_profile_id}.yaml")
        profile = type(profile).load(saved_path)
        self.sidecar_importer.add_mapping_profile(profile)

        targets = self._same_structure_yaml_runs(session, group.schema, document.structure_signature) if apply_all else [run]
        applied: list[dict[str, Any]] = []
        for target in targets:
            if target.sidecar_path is None:
                continue
            mapped = self.sidecar_importer.import_file(
                target.sidecar_path,
                target.parsed,
                group.schema,
                existing_values=target.enrichment,
                mapping_profile=profile,
            )
            self._apply_sidecar_result_to_run(target, mapped)
            applied.append(
                {
                    "runId": target.run_id,
                    "yamlPath": str(target.sidecar_path),
                    "importedFieldCount": len(mapped.imported_fields),
                    "unknownKeyCount": len(mapped.unknown_keys),
                    "conflictCount": len(mapped.conflicts),
                    "status": target.sidecar_import_status,
                }
            )

        session.validation_by_group = {}
        session.messages = [
            f"Applied YAML mapping profile {profile.mapping_profile_id} to {len(applied)} run(s)."
        ]
        summary = {
            "source": "backend",
            "profileId": profile.mapping_profile_id,
            "profilePath": str(saved_path),
            "structureSignature": document.structure_signature,
            "appliedCount": len(applied),
            "applyAll": bool(apply_all),
            "runs": applied,
        }
        view = self._view_model(session)
        view["yamlMapping"] = summary
        view["yaml_mapping"] = summary
        return view

    def set_schema(
        self,
        session_id: str,
        schema_candidate_id: str | None = None,
        *,
        schema_id: str | None = None,
        schema_version: str | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        schema = self._resolve_schema(
            schema_candidate_id,
            schema_id=schema_id,
            schema_version=schema_version,
        )
        detected = session.detected_schema
        session.schema = schema
        session.schema_overridden = not _same_schema(schema, detected)
        for group in session.groups:
            group.schema = schema
        session.messages = [
            f"Selected schema {schema.schema_id} v{schema.schema_version}.",
        ]
        session.validation_by_group = {}
        return self._view_model(session)

    def validate_group(self, session_id: str, group_id: str | None = None) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        report = self._validation_report(group)
        session.validation_by_group[group.group_key] = report
        session.messages = [
            (
                f"Validated {group.display_name}: export-ready."
                if report["ok"]
                else f"Validated {group.display_name}: {report['error_count']} blocking issue(s)."
            )
        ]
        return self._view_model(session)

    def export_group(self, session_id: str, group_id: str | None, output_path: str | Path) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        if not output_path:
            raise PackagingSessionError(
                "ValidationError",
                "packaging.exportGroup requires an output path.",
                details={"group_id": group.group_key},
            )
        output = Path(output_path).expanduser()
        if output.suffix.lower() != ".mtdp":
            output = output.with_suffix(".mtdp")

        report = self._validation_report(group)
        session.validation_by_group[group.group_key] = report
        if not report["ok"]:
            session.messages = [
                f"Export blocked for {group.display_name}: {report['error_count']} blocking issue(s)."
            ]
            raise PackagingSessionError(
                "ValidationError",
                f"Export blocked for {group.display_name}: group is not export-ready.",
                details={"group_id": group.group_key, "validation": report},
            )

        validation = self.group_exporter.export_group(group, output)
        if not validation.ok:
            messages = validation.messages()
            session.messages = [f"Export failed for {group.display_name}.", *messages]
            raise PackagingSessionError(
                "ValidationError",
                "Package export failed validation.",
                details={"group_id": group.group_key, "path": str(output), "messages": messages},
            )

        for run in group.runs:
            run.status = "packaged"
        summary = {
            "source": "backend",
            "groupId": group.group_key,
            "groupName": group.display_name,
            "path": str(output),
            "fileName": output.name,
            "bytes": output.stat().st_size if output.exists() else 0,
            "runCount": len(group.runs),
            "validation": report,
        }
        session.messages = [
            f"Wrote and validated {output.name}. Use Analysis to process it through the Method Wizard."
        ]
        view = self._view_model(session)
        view["export"] = summary
        return view

    def export_all_ready(self, session_id: str, output_dir: str | Path | None = None) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.groups:
            raise PackagingSessionError(
                "ValidationError",
                "No packaging groups are loaded.",
            )
        directory = Path(output_dir).expanduser() if output_dir else None
        if directory is not None:
            if directory.exists() and not directory.is_dir():
                raise PackagingSessionError(
                    "ValidationError",
                    "packaging.exportAllReady output_dir must be a folder.",
                    details={"output_dir": str(directory)},
                )
            directory.mkdir(parents=True, exist_ok=True)

        exported: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        used_paths: set[Path] = set()
        for group in list(session.groups):
            report = self._validation_report(group)
            session.validation_by_group[group.group_key] = report
            if not report["ok"]:
                skipped.append(
                    {
                        "groupId": group.group_key,
                        "groupName": group.display_name,
                        "errorCount": report["error_count"],
                        "warningCount": report["warning_count"],
                        "validation": report,
                    }
                )
                continue
            output = self._export_all_output_path(session, group, directory, used_paths)
            used_paths.add(output)
            validation = self.group_exporter.export_group(group, output)
            if validation.ok:
                for run in group.runs:
                    run.status = "packaged"
                exported.append(
                    {
                        "source": "backend",
                        "groupId": group.group_key,
                        "groupName": group.display_name,
                        "path": str(output),
                        "fileName": output.name,
                        "bytes": output.stat().st_size if output.exists() else 0,
                        "runCount": len(group.runs),
                        "validation": report,
                    }
                )
            else:
                failed.append(
                    {
                        "groupId": group.group_key,
                        "groupName": group.display_name,
                        "path": str(output),
                        "messages": validation.messages(),
                    }
                )

        message = f"Exported {len(exported)} ready group(s)."
        if skipped:
            message += f" Skipped {len(skipped)} group(s) with blocking validation issues."
        if failed:
            message += f" {len(failed)} ready group(s) failed package validation after writing."
        session.messages = [message]
        summary = {
            "source": "backend",
            "outputDir": str(directory) if directory is not None else None,
            "exportedCount": len(exported),
            "skippedCount": len(skipped),
            "failedCount": len(failed),
            "exports": exported,
            "skipped": skipped,
            "failed": failed,
        }
        view = self._view_model(session)
        view["exportAll"] = summary
        view["export_all"] = summary
        return view

    def update_dataset_fields(
        self,
        session_id: str,
        group_id: str | None,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        self._apply_field_patch(group.dataset_enrichment, group.dataset_units, patch)
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Updated dataset metadata for {group.display_name}."]
        return self._view_model(session)

    def update_run_fields(
        self,
        session_id: str,
        group_id: str | None,
        run_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        run = self._find_run(group, run_id)
        self._apply_field_patch(run.enrichment, run.field_units, patch)
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Updated run metadata for {run.run_id}."]
        return self._view_model(session)

    def update_group_run_fields(
        self,
        session_id: str,
        group_id: str | None,
        patch: dict[str, Any],
        run_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        runs = self._select_runs(group, run_ids)
        for run in runs:
            self._apply_field_patch(run.enrichment, run.field_units, patch)
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Updated {len(runs)} run(s) in {group.display_name}."]
        return self._view_model(session)

    def update_run_field_matrix(
        self,
        session_id: str,
        group_id: str | None,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        if not isinstance(updates, list) or not updates:
            raise PackagingSessionError(
                "ValidationError",
                "Run field matrix update requires a non-empty updates list.",
                details={"updates_type": type(updates).__name__},
            )
        changed = 0
        for item in updates:
            if not isinstance(item, dict):
                raise PackagingSessionError(
                    "ValidationError",
                    "Each run field matrix update must be a JSON object.",
                    details={"update_type": type(item).__name__},
                )
            run = self._find_run(group, str(item.get("run_id") or ""))
            patch = item.get("patch")
            if not isinstance(patch, dict):
                raise PackagingSessionError(
                    "ValidationError",
                    "Each run field matrix update requires a patch object.",
                    details={"patch_type": type(patch).__name__},
                )
            self._apply_field_patch(run.enrichment, run.field_units, patch)
            changed += 1
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [f"Updated {changed} run field patch(es) in {group.display_name}."]
        return self._view_model(session)

    def set_group_run_unit(
        self,
        session_id: str,
        group_id: str | None,
        field_id: str,
        unit: str,
        *,
        convert: bool = False,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        group = self._find_group(session, group_id)
        field = self._run_field(group, field_id)
        target_unit = default_unit_normaliser.normalize_unit_text(unit)
        if not target_unit:
            raise PackagingSessionError(
                "ValidationError",
                "packaging.setGroupRunUnit requires a target unit.",
                details={"field_id": field.field_id},
            )
        accepted = {
            normalized
            for normalized in (default_unit_normaliser.normalize_unit_text(item) for item in field.accepted_units)
            if normalized
        }
        if accepted and target_unit not in accepted:
            raise PackagingSessionError(
                "ValidationError",
                f"{target_unit} is not an accepted unit for {field.label}.",
                details={"field_id": field.field_id, "accepted_units": sorted(accepted)},
            )
        source_unit = (
            group.run_units.get(field.field_id)
            or field.standard_unit
            or next(iter(accepted), None)
        )
        if not source_unit:
            raise PackagingSessionError(
                "ValidationError",
                f"{field.label} does not define a unit policy.",
                details={"field_id": field.field_id},
            )
        dimension = field.unit_dimension or default_unit_normaliser.dimensions.dimension_for_unit(source_unit)
        converted = 0
        for run in group.runs:
            current = run.enrichment.get(field.field_id)
            from_unit = run.field_units.get(field.field_id) or source_unit
            if convert and current is not None and current.value not in (None, "") and from_unit != target_unit:
                try:
                    result = default_unit_normaliser.convert(
                        value=current.value,
                        from_unit=from_unit,
                        to_unit=target_unit,
                        dimension=dimension or "",
                    )
                except (TypeError, ValueError, UnitValidationError) as exc:
                    raise PackagingSessionError(
                        "ValidationError",
                        f"Could not convert {field.label} from {from_unit} to {target_unit}.",
                        details={"field_id": field.field_id, "run_id": run.run_id, "reason": str(exc)},
                    ) from exc
                run.enrichment[field.field_id] = EnrichedFieldValue(
                    _format_numeric(result.canonical_value),
                    target_unit,
                    current.source,
                )
                converted += 1
            elif current is not None:
                run.enrichment[field.field_id] = EnrichedFieldValue(current.value, target_unit, current.source)
            run.field_units[field.field_id] = target_unit

        group.run_units[field.field_id] = target_unit
        session.validation_by_group.pop(group.group_key, None)
        session.messages = [
            (
                f"Converted {converted} value(s) for {field.label} to {target_unit}."
                if convert
                else f"Relabelled {field.label} as {target_unit}."
            )
        ]
        return self._view_model(session)

    def _loaded_schema(self, session: PackagingSession) -> MTDPSchema:
        if session.schema is None:
            raise PackagingSessionError(
                "ValidationError",
                "A package or source batch must be loaded before proposing groups.",
            )
        return session.schema

    def _all_runs(self, session: PackagingSession) -> list[RunState]:
        return [run for group in session.groups for run in group.runs] + list(session.unassigned)

    def _current_grouping_proposal(self, session: PackagingSession) -> GroupingProposal:
        schema = self._loaded_schema(session)
        runs = self._all_runs(session)
        if not runs:
            raise PackagingSessionError(
                "ValidationError",
                "At least one parsed run is required before proposing groups.",
            )
        inputs = [
            GroupingInput(
                source_path=run.source_path,
                parsed=run.parsed,
                schema_inference=self.registry.infer(run.parsed, run.source_path),
            )
            for run in runs
        ]
        return self.grouper.propose(inputs, schema)

    def _proposal_view(self, proposal: GroupingProposal) -> dict[str, Any]:
        assignments = [assignment for bundle in proposal.bundles for assignment in bundle.assignments]
        confidence = int(round(sum(item.confidence for item in assignments) / len(assignments) * 100)) if assignments else 0
        group_count = len(proposal.bundles)
        run_count = len(assignments)
        return {
            "id": _proposal_id(self.grouper),
            "source": "backend",
            "engine": self.grouper.engine_name,
            "engine_version": self.grouper.engine_version,
            "conf": confidence,
            "confidence": confidence,
            "title": f"{group_count} group{'s' if group_count != 1 else ''} - backend sample-type proposal",
            "description": (
                f"{self.grouper.engine_name} proposed {group_count} group(s) "
                f"from {run_count} run(s); {len(proposal.unassigned)} run(s) need manual grouping."
            ),
            "group_count": group_count,
            "run_count": run_count,
            "unassigned_count": len(proposal.unassigned),
            "groups": [
                {
                    "id": bundle.bundle_key,
                    "name": bundle.display_name,
                    "run_count": len(bundle.assignments),
                    "confidence": int(round(sum(item.confidence for item in bundle.assignments) / len(bundle.assignments) * 100))
                    if bundle.assignments
                    else 0,
                    "reason": bundle.assignments[0].reason if bundle.assignments else "manual required",
                    "evidence": sorted({evidence for item in bundle.assignments for evidence in item.evidence}),
                    "runs": [
                        {
                            "source_path": str(item.source_path),
                            "fileLabel": item.source_path.name,
                            "confidence": int(round(item.confidence * 100)),
                            "reason": item.reason,
                            "evidence": list(item.evidence),
                        }
                        for item in bundle.assignments
                    ],
                    "warnings": list(bundle.warnings),
                }
                for bundle in proposal.bundles
            ],
            "unassigned": [
                {
                    "source_path": str(item.source_path),
                    "fileLabel": item.source_path.name,
                }
                for item in proposal.unassigned
            ],
            "suggested_merges": [
                {
                    "source_key": item.source_key,
                    "target_key": item.target_key,
                    "source_name": item.source_name,
                    "target_name": item.target_name,
                    "similarity": item.similarity,
                    "reason": item.reason,
                }
                for item in proposal.suggested_merges
            ],
        }

    def _single_previous_group(
        self,
        source_keys: list[str],
        previous_group_by_run: dict[str, GroupState],
    ) -> GroupState | None:
        groups: list[GroupState] = []
        seen: set[int] = set()
        for source_key in source_keys:
            group = previous_group_by_run.get(source_key)
            if group is None or id(group) in seen:
                continue
            groups.append(group)
            seen.add(id(group))
        if len(groups) == 1:
            return groups[0]
        return None

    def _copy_group_metadata(self, source: GroupState, target: GroupState) -> None:
        target.dataset_enrichment = dict(source.dataset_enrichment)
        target.dataset_units = dict(source.dataset_units)
        target.run_units = dict(source.run_units)
        target.supplemental_files = list(source.supplemental_files)
        target.removed_runs = list(source.removed_runs)
        target.manual_corrections = source.manual_corrections
        target.source_package_path = source.source_package_path
        target.workspace = source.workspace

    def _with_sidecar_import(self, item: GroupingInput, schema: MTDPSchema) -> GroupingInput:
        result = self.sidecar_importer.import_for_run(item.source_path, item.parsed, schema)
        return GroupingInput(
            source_path=item.source_path,
            parsed=item.parsed,
            schema_inference=item.schema_inference,
            supplemental_import=result,
        )

    def _run_from_grouping_input(
        self,
        existing_runs: list[RunState],
        item: GroupingInput,
        *,
        status: str = "parsed",
    ) -> RunState:
        run = RunState(
            run_id=_run_id_for(existing_runs, item.source_path),
            source_path=item.source_path,
            parsed=item.parsed,
            status=status,
        )
        if item.supplemental_import is not None:
            self._apply_sidecar_result_to_run(run, item.supplemental_import)
        return run

    def _apply_sidecar_result_to_run(self, run: RunState, result: SupplementalImportResult) -> None:
        for field_id, candidate in result.imported_fields.items():
            run.enrichment[field_id] = EnrichedFieldValue(
                candidate.value,
                candidate.unit,
                candidate.source_format,
            )
            run.field_units[field_id] = candidate.unit
        run.sidecar_path = result.source_path or run.sidecar_path
        run.sidecar_conflicts = list(result.conflicts)
        run.sidecar_unknown_keys = list(result.unknown_keys)
        run.sidecar_mapping_profile_id = result.mapping_profile_id
        run.sidecar_mapping_profile_path = result.mapping_profile_path
        if result.mapping_profile_id:
            run.sidecar_import_mode = "mapping_profile"
        elif result.document is not None and result.document.is_canonical:
            run.sidecar_import_mode = "canonical"
        elif result.requires_mapping:
            run.sidecar_import_mode = "mapping_required"
        elif result.source_path:
            run.sidecar_import_mode = "alias"
        else:
            run.sidecar_import_mode = None
        if result.mapping_profile_id:
            run.sidecar_import_status = "Mapping applied"
        elif result.conflicts:
            run.sidecar_import_status = "YAML needs review"
        elif result.requires_mapping:
            run.sidecar_import_status = "YAML needs review"
        elif result.imported_fields:
            run.sidecar_import_status = "YAML imported"
        elif result.source_path:
            run.sidecar_import_status = "YAML detected"
        else:
            run.sidecar_import_status = "No YAML"
        if result.image_references:
            known = {Path(image.source_path) for image in run.images}
            for item in result.image_references:
                if item.path in known:
                    continue
                run.images.append(
                    RunImageEvidence(
                        source_path=item.path,
                        view=item.view,
                        role=item.role,
                        used_for_metrology=item.used_for_metrology,
                        notes=item.notes,
                    )
                )
                known.add(item.path)

    def _first_run_with_sidecar(self, group: GroupState) -> RunState:
        for run in group.runs:
            if run.sidecar_path is not None:
                return run
        raise PackagingSessionError(
            "ValidationError",
            "No run with supplemental YAML is available for mapping review.",
            details={"group_id": group.group_key},
        )

    def _sidecar_document_result(self, group: GroupState, run: RunState) -> SupplementalImportResult:
        if run.sidecar_path is None:
            raise PackagingSessionError(
                "ValidationError",
                "Selected run has no supplemental YAML sidecar.",
                details={"group_id": group.group_key, "run_id": run.run_id},
            )
        result = self.sidecar_importer.import_file(
            run.sidecar_path,
            run.parsed,
            group.schema,
            existing_values=run.enrichment,
        )
        if result.document is None:
            raise PackagingSessionError(
                "ValidationError",
                "Could not load supplemental YAML sidecar.",
                details={"group_id": group.group_key, "run_id": run.run_id, "warnings": list(result.warnings)},
            )
        return result

    def _yaml_mapping_review_row(self, schema: MTDPSchema, document, source_key: str) -> dict[str, Any]:
        raw_value = get_dotted_value(document.raw_payload, source_key)
        value, raw_unit = extract_value_and_unit(raw_value)
        _normalized_key, inferred_unit, unit_status = extract_unit_from_key(source_key)
        match = self.yaml_matcher.propose(source_key=source_key, source_value=raw_value, schema=schema)
        field = schema.field_by_id(match.target_field_id) if match.target_field_id else None
        selected_unit = raw_unit or match.unit_candidate or inferred_unit
        transformed = transform_value_for_field(
            source_key=source_key,
            raw_value=value,
            raw_unit=raw_unit or inferred_unit,
            field=field,
            selected_unit=selected_unit,
        )
        status = _yaml_mapping_status(field, transformed, unit_status, document.is_canonical, match.requires_confirmation)
        action = "map" if field is not None else "ignore"
        mapping = {
            "source_key": source_key,
            "action": action,
            "target_field_id": field.field_id if field is not None else None,
            "value_path": source_key,
            "unit": selected_unit if action == "map" else None,
            "date_format": None,
            "value_transform": _value_transform_name(transformed),
            "status": status,
            "user_corrected": False,
        }
        return {
            "sourceKey": source_key,
            "rawValue": raw_value,
            "rawText": _json_text(raw_value),
            "detectedValue": value,
            "detectedUnit": selected_unit,
            "suggestedFieldId": field.field_id if field is not None else None,
            "suggestedFieldLabel": field.label if field is not None else "",
            "fieldType": field.type if field is not None else "",
            "acceptedUnits": list(field.accepted_units) if field is not None else [],
            "allowedValues": list(field.allowed_values) if field is not None else [],
            "targetUnit": field.standard_unit if field is not None else "",
            "storage": storage_preview(field),
            "transform": transformed.transform_name if transformed is not None else "",
            "status": status,
            "action": action,
            "resultPreview": "" if transformed is None else f"{transformed.canonical_value} {transformed.canonical_unit or ''}".strip(),
            "confidence": match.confidence,
            "requiresConfirmation": bool(match.requires_confirmation or (transformed and transformed.requires_confirmation)),
            "evidence": list(match.evidence),
            "warnings": list(match.warnings) + (list(transformed.warnings) if transformed is not None else []),
            "mapping": mapping,
        }

    def _mapping_rule_from_payload(self, schema: MTDPSchema, payload: dict[str, Any]) -> MappingRule:
        if not isinstance(payload, dict):
            raise PackagingSessionError(
                "ValidationError",
                "Each YAML mapping rule must be a JSON object.",
                details={"mapping_type": type(payload).__name__},
            )
        source_key = str(payload.get("source_key") or payload.get("sourceKey") or "").strip()
        if not source_key:
            raise PackagingSessionError("ValidationError", "YAML mapping rule requires source_key.")
        action = str(payload.get("action") or "map").strip()
        if action not in {"map", "ignore", "defer"}:
            raise PackagingSessionError(
                "ValidationError",
                f"Unsupported YAML mapping action: {action}",
                details={"source_key": source_key, "action": action},
            )
        target_field_id = payload.get("target_field_id") or payload.get("targetFieldId")
        target_field_id = None if target_field_id in (None, "") else str(target_field_id)
        if action == "map":
            if not target_field_id:
                raise PackagingSessionError(
                    "ValidationError",
                    "Mapped YAML rules require target_field_id.",
                    details={"source_key": source_key},
                )
            if schema.field_by_id(target_field_id) is None:
                raise PackagingSessionError(
                    "NotFound",
                    f"YAML mapping target field not found: {target_field_id}",
                    details={"source_key": source_key, "target_field_id": target_field_id},
                )
        return MappingRule(
            source_key=source_key,
            action=action,
            target_field_id=target_field_id if action == "map" else None,
            value_path=str(payload.get("value_path") or payload.get("valuePath") or source_key),
            unit=None if payload.get("unit") in (None, "") else str(payload.get("unit")),
            date_format=None if payload.get("date_format") in (None, "") else str(payload.get("date_format")),
            value_transform=None if payload.get("value_transform") in (None, "") else str(payload.get("value_transform")),
            status=None if payload.get("status") in (None, "") else str(payload.get("status")),
            user_corrected=bool(payload.get("user_corrected") or payload.get("userCorrected")),
        )

    def _mapping_profile_root(self, session: PackagingSession, run: RunState) -> Path:
        if session.package_path is not None:
            return session.package_path.parent / ".mtdp_mapping_profiles"
        if run.sidecar_path is not None:
            return run.sidecar_path.parent / ".mtdp_mapping_profiles"
        if session.source_paths:
            return session.source_paths[0].parent / ".mtdp_mapping_profiles"
        return Path.cwd() / ".mtdp_mapping_profiles"

    def _same_structure_yaml_runs(
        self,
        session: PackagingSession,
        schema: MTDPSchema,
        structure_signature: str,
    ) -> list[RunState]:
        targets: list[RunState] = []
        for candidate in self._all_runs(session):
            if candidate.sidecar_path is None:
                continue
            result = self.sidecar_importer.import_file(candidate.sidecar_path, candidate.parsed, schema)
            if result.document is not None and result.document.structure_signature == structure_signature:
                targets.append(candidate)
        return targets

    def _require_session(self, session_id: str) -> PackagingSession:
        if not session_id:
            raise PackagingSessionError(
                "ValidationError",
                "A packaging session_id is required.",
            )
        try:
            return self._sessions[str(session_id)]
        except KeyError as exc:
            raise PackagingSessionError(
                "NotFound",
                f"Packaging session not found: {session_id}",
                details={"session_id": str(session_id)},
            ) from exc

    def _source_files(self, paths: list[str | Path]) -> list[Path]:
        supported = {suffix.casefold() for suffix in self.parser.supported_suffixes()}
        found: list[Path] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                found.extend(
                    item
                    for item in sorted(path.rglob("*"))
                    if item.is_file() and item.suffix.casefold() in supported and self.parser.can_parse(item)
                )
            elif path.is_file() and path.suffix.casefold() in supported and self.parser.can_parse(path):
                found.append(path)
        return _dedupe_paths(found)

    def _non_empty_paths(self, paths: list[str | Path], command: str) -> list[Path]:
        if not isinstance(paths, list) or not paths:
            raise PackagingSessionError(
                "ValidationError",
                f"{command} requires payload.paths to be a non-empty list.",
                details={"paths_type": type(paths).__name__},
            )
        result = [Path(path) for path in paths]
        missing = [str(path) for path in result if not path.is_file()]
        if missing:
            raise PackagingSessionError(
                "NotFound",
                f"{command} received missing file path(s).",
                details={"paths": missing},
            )
        return result

    def _resolve_schema(
        self,
        schema_candidate_id: str | None = None,
        *,
        schema_id: str | None = None,
        schema_version: str | None = None,
    ) -> MTDPSchema:
        if schema_id:
            try:
                return self.registry.get(str(schema_id), str(schema_version) if schema_version else None)
            except KeyError as exc:
                raise PackagingSessionError(
                    "NotFound",
                    f"Schema not found: {schema_id}" + (f" v{schema_version}" if schema_version else ""),
                    details={"schema_id": str(schema_id), "schema_version": schema_version},
                ) from exc

        candidate_id = str(schema_candidate_id or "").strip()
        if not candidate_id:
            raise PackagingSessionError(
                "ValidationError",
                "packaging.setSchema requires schema_id.",
            )
        for schema in self.registry.all():
            if _schema_candidate_id(schema) == candidate_id:
                return schema
        raise PackagingSessionError(
            "NotFound",
            f"Schema not found: {candidate_id}",
            details={"schema_id": candidate_id},
        )

    def _find_group(self, session: PackagingSession, group_id: str | None = None) -> GroupState:
        if not session.groups:
            raise PackagingSessionError(
                "ValidationError",
                "No packaging group is loaded.",
            )
        if not group_id:
            return session.groups[0]
        for group in session.groups:
            if group.group_key == group_id:
                return group
        raise PackagingSessionError(
            "NotFound",
            f"Packaging group not found: {group_id}",
            details={"group_id": str(group_id)},
        )

    def _find_run(self, group: GroupState, run_id: str) -> RunState:
        if not run_id:
            raise PackagingSessionError(
                "ValidationError",
                "A run_id is required.",
            )
        for run in group.runs:
            if run.run_id == run_id:
                return run
        raise PackagingSessionError(
            "NotFound",
            f"Run not found: {run_id}",
            details={"group_id": group.group_key, "run_id": str(run_id)},
        )

    def _detach_run(
        self,
        session: PackagingSession,
        run_id: str,
        from_group_id: str | None = None,
    ) -> tuple[RunState, GroupState | None]:
        if not run_id:
            raise PackagingSessionError(
                "ValidationError",
                "A run_id is required.",
            )
        containers: list[tuple[list[RunState], GroupState | None]]
        if from_group_id == "__unassigned":
            containers = [(session.unassigned, None)]
        elif from_group_id:
            group = self._find_group(session, from_group_id)
            containers = [(group.runs, group)]
        else:
            containers = [(group.runs, group) for group in session.groups]
            containers.append((session.unassigned, None))
        for runs, group in containers:
            for run in list(runs):
                if run.run_id == run_id:
                    runs.remove(run)
                    return run, group
        raise PackagingSessionError(
            "NotFound",
            f"Run not found: {run_id}",
            details={"run_id": str(run_id), "from_group_id": from_group_id},
        )

    def _insert_run(self, runs: list[RunState], run: RunState, index: int | None = None) -> None:
        if index is None:
            runs.append(run)
            return
        position = max(0, min(int(index), len(runs)))
        runs.insert(position, run)

    def _unique_group_key(self, session: PackagingSession, name: str) -> str:
        base = _slug(name) or "group"
        existing = {group.group_key for group in session.groups}
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def _select_runs(self, group: GroupState, run_ids: list[str] | None = None) -> list[RunState]:
        if run_ids is None:
            return list(group.runs)
        if not isinstance(run_ids, list):
            raise PackagingSessionError(
                "ValidationError",
                "run_ids must be a JSON list when provided.",
                details={"run_ids_type": type(run_ids).__name__},
            )
        return [self._find_run(group, str(run_id)) for run_id in run_ids]

    def _run_field(self, group: GroupState, field_id: str):
        key = str(field_id or "").strip()
        if not key:
            raise PackagingSessionError(
                "ValidationError",
                "A run field_id is required.",
            )
        for field in group.schema.run_fields:
            if field.field_id == key:
                return field
        raise PackagingSessionError(
            "NotFound",
            f"Run field not found: {key}",
            details={"group_id": group.group_key, "field_id": key},
        )

    def _apply_field_patch(
        self,
        values: dict[str, EnrichedFieldValue],
        units: dict[str, str | None],
        patch: dict[str, Any],
    ) -> None:
        if not isinstance(patch, dict):
            raise PackagingSessionError(
                "ValidationError",
                "Metadata update patch must be a JSON object.",
                details={"patch_type": type(patch).__name__},
            )
        unit_patch: dict[str, str | None] = {}
        value_patch: dict[str, Any] = {}
        for key, value in patch.items():
            field_id = str(key)
            if field_id.endswith("__unit"):
                unit_patch[field_id[:-6]] = None if value in (None, "") else str(value)
            else:
                value_patch[field_id] = value

        for field_id, raw_value in value_patch.items():
            if raw_value in (None, ""):
                values.pop(field_id, None)
                units.pop(field_id, None)
                continue
            unit = unit_patch.get(field_id, units.get(field_id))
            values[field_id] = EnrichedFieldValue(raw_value, unit, "user")
            if unit is not None:
                units[field_id] = unit
            else:
                units.pop(field_id, None)

        for field_id, unit in unit_patch.items():
            if field_id in value_patch:
                continue
            current = values.get(field_id)
            if current is None:
                continue
            values[field_id] = EnrichedFieldValue(current.value, unit, current.source)
            if unit is None:
                units.pop(field_id, None)
            else:
                units[field_id] = unit

    def _validation_report(self, group: GroupState) -> dict[str, Any]:
        schema = group.schema
        writer = self.validation_service.writer
        issues: list[dict[str, Any]] = []

        _, dataset_validation = schema.validate_dataset_fields(group.dataset_enrichment)
        self._append_validation_issues(
            issues,
            dataset_validation,
            scope="dataset",
            group_id=group.group_key,
            category="metadata",
        )

        if not group.runs:
            issues.append(
                {
                    "severity": "error",
                    "scope": "group",
                    "group_id": group.group_key,
                    "category": "group",
                    "code": "missing_runs",
                    "message": "Group has no included runs.",
                    "text": "Group has no included runs.",
                    "target": {"type": "dataset", "groupId": group.group_key},
                }
            )

        ready_runs = 0
        for run in group.runs:
            existing = writer._existing_fields(run.parsed, schema)
            _, run_validation = schema.validate_run_fields(run.enrichment, existing_tokens=existing)
            table_validation = writer.normalizer.normalize(run.parsed, schema).validation
            for conflict in run.sidecar_conflicts:
                run_validation.add_error(
                    conflict.message,
                    field=str(run.source_path),
                    code="sidecar_requires_confirmation",
                )

            self._append_validation_issues(
                issues,
                run_validation,
                scope="run",
                group_id=group.group_key,
                run_id=run.run_id,
                category="metadata",
            )
            self._append_validation_issues(
                issues,
                table_validation,
                scope="run",
                group_id=group.group_key,
                run_id=run.run_id,
                category="data_table",
            )
            run.status = "ready" if run_validation.ok and table_validation.ok else "needs input"
            if run.status == "ready" and dataset_validation.ok:
                ready_runs += 1

        error_count = sum(1 for issue in issues if issue["severity"] == "error")
        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
        return {
            "source": "backend",
            "group_id": group.group_key,
            "group_name": group.display_name,
            "schema_id": schema.schema_id,
            "schema_version": schema.schema_version,
            "ok": error_count == 0,
            "error_count": error_count,
            "warning_count": warning_count,
            "ready_runs": ready_runs,
            "total_runs": len(group.runs),
            "issues": issues,
            "passed": [
                {"text": f"Schema {schema.schema_id} v{schema.schema_version} field validation ran in backend."},
                {"text": f"Data table normalization checked {len(group.runs)} run(s)."},
            ],
            "skipped": [
                {
                    "text": "Metadata edit synchronization",
                    "detail": "Only backend session values are validated in this Phase 2 slice.",
                }
            ],
        }

    def _append_validation_issues(
        self,
        target: list[dict[str, Any]],
        validation: ValidationResult,
        *,
        scope: str,
        group_id: str,
        category: str,
        run_id: str | None = None,
    ) -> None:
        for severity, items in (("error", validation.errors), ("warning", validation.warnings)):
            for issue in items:
                target.append(
                    {
                        "severity": severity,
                        "scope": scope,
                        "group_id": group_id,
                        "run_id": run_id,
                        "category": category,
                        "field": issue.field,
                        "code": issue.code,
                        "message": issue.message,
                        "text": self._issue_text(issue.message, scope=scope, run_id=run_id),
                        "target": self._issue_target(scope, group_id, run_id, issue.field),
                    }
                )

    def _issue_text(self, message: str, *, scope: str, run_id: str | None = None) -> str:
        if scope == "dataset":
            return f"Dataset · {message}"
        if run_id:
            return f"{run_id} · {message}"
        return message

    def _issue_target(
        self,
        scope: str,
        group_id: str,
        run_id: str | None,
        field_id: str | None,
    ) -> dict[str, Any]:
        if scope == "run":
            return {"type": "run", "groupId": group_id, "runId": run_id, "fieldId": field_id}
        return {"type": "dataset", "groupId": group_id, "fieldId": field_id}

    def _view_model(self, session: PackagingSession) -> dict[str, Any]:
        schema = session.schema or self.registry.selectable()[0]
        detected_schema = session.detected_schema or schema
        schemas = [
            self._schema_candidate(
                item,
                detected=_same_schema(item, detected_schema),
                confidence=100 if _same_schema(item, detected_schema) else 0,
            )
            for item in self.registry.selectable()
        ]
        return {
            "session_id": session.session_id,
            "status": session.status,
            "created_at": session.created_at,
            "schema": self._schema_summary(schema),
            "schemaForm": _schema_form_view(schema),
            "schema_form": _schema_form_view(schema),
            "schema_overridden": session.schema_overridden,
            "schemas": schemas,
            "bundle": self._bundle_view(session, schema),
            "source_summary": {
                "source_count": len(session.source_paths),
                "package_path": str(session.package_path) if session.package_path else None,
                "paths": [str(path) for path in session.source_paths],
            },
            "messages": list(session.messages),
        }

    def _bundle_view(self, session: PackagingSession, schema: MTDPSchema) -> dict[str, Any] | None:
        if not session.groups and not session.unassigned:
            return None
        groups = [self._group_view(group) for group in session.groups]
        first_group = session.groups[0] if session.groups else None
        return {
            "name": first_group.display_name if first_group is not None else (session.package_path.stem if session.package_path else "Packaging session"),
            "schemaId": _schema_candidate_id(schema),
            "schemaLabel": schema.display_label,
            "schemaVersion": schema.schema_version,
            "schemaOverridden": session.schema_overridden,
            "schemaForm": _schema_form_view(schema),
            "schema_form": _schema_form_view(schema),
            "detectConfidence": 100,
            "dataset": {"values": _field_values(first_group.dataset_enrichment) if first_group is not None else {}},
            "groups": groups,
            "unassigned": [self._run_view(run) for run in session.unassigned],
            "sourcePairs": [
                {"csv": path.name, "yaml": str(path.with_suffix(".yaml").name)}
                for path in session.source_paths
            ],
            "supplemental": [_supplemental_view(item) for item in first_group.supplemental_files] if first_group is not None else [],
            "backendValidation": session.validation_by_group.get(first_group.group_key) if first_group is not None else None,
        }

    def _group_view(self, group: GroupState) -> dict[str, Any]:
        return {
            "id": group.group_key,
            "name": group.display_name,
            "units": dict(group.run_units),
            "supplemental": [_supplemental_view(item) for item in group.supplemental_files],
            "runs": [self._run_view(run) for run in group.runs],
        }

    def _export_all_output_path(
        self,
        session: PackagingSession,
        group: GroupState,
        output_dir: Path | None,
        used_paths: set[Path],
    ) -> Path:
        if output_dir is not None:
            folder = output_dir
        elif session.package_path is not None:
            folder = session.package_path.parent
        elif group.runs:
            folder = group.runs[0].source_path.parent
        else:
            folder = Path.cwd()

        if session.package_path is not None and len(session.groups) == 1:
            stem = f"{session.package_path.stem}_revised"
        else:
            stem = _safe_file_stem(group.display_name) or _safe_file_stem(group.group_key) or "mtdp_dataset"
        candidate = folder / f"{stem}.mtdp"
        if candidate not in used_paths:
            return candidate
        index = 2
        while True:
            next_candidate = folder / f"{stem}_{index}.mtdp"
            if next_candidate not in used_paths:
                return next_candidate
            index += 1

    def _run_view(self, run: RunState) -> dict[str, Any]:
        return {
            "id": run.run_id,
            "fileLabel": run.source_path.name,
            "channels": [_channel_view(channel) for channel in run.parsed.channels.all_channels()],
            "evidence": [_evidence_view(item) for item in run.images],
            "supplemental": [_supplemental_view(item) for item in run.supplemental_files],
            "values": _field_values(run.enrichment),
            "sidecarStatus": run.sidecar_import_status,
        }

    def _schema_candidate(self, schema: MTDPSchema, *, detected: bool, confidence: int) -> dict[str, Any]:
        return {
            "id": _schema_candidate_id(schema),
            "schema": schema.schema_id,
            "version": schema.schema_version,
            "label": schema.display_label,
            "conf": confidence,
            "detected": detected,
            "hint": f"Loaded from backend schema registry; status={self.registry.effective_status(schema)}.",
            "status": schema.status,
            "effective_status": self.registry.effective_status(schema),
            "dataset_field_count": len(schema.dataset_fields),
            "run_field_count": len(schema.run_fields),
            "metadata_section_count": len(schema.metadata_sections),
            "schemaForm": _schema_form_view(schema),
            "schema_form": _schema_form_view(schema),
        }

    def _schema_summary(self, schema: MTDPSchema) -> dict[str, Any]:
        return {
            "id": _schema_candidate_id(schema),
            "schema_id": schema.schema_id,
            "schema_version": schema.schema_version,
            "display_label": schema.display_label,
            "status": schema.status,
            "effective_status": self.registry.effective_status(schema),
            "test_family": schema.test_family,
            "test_mode": schema.test_mode,
            "form": _schema_form_view(schema),
        }


def _schema_candidate_id(schema: MTDPSchema) -> str:
    leaf = schema.schema_id.rsplit(".", 1)[-1].replace("_", "-")
    return f"{leaf}-{schema.schema_version}"


def _schema_form_view(schema: MTDPSchema) -> dict[str, Any]:
    dataset_fields = [_schema_field_view(field, scope="dataset") for field in schema.dataset_fields]
    run_fields = [_schema_field_view(field, scope="run") for field in schema.run_fields]
    fields_by_id = {field["id"]: field for field in [*dataset_fields, *run_fields]}
    channel_families = [_schema_channel_family_view(column) for column in schema.expected_table]
    if "ignore" not in {family["id"] for family in channel_families}:
        channel_families.append(
            {
                "id": "ignore",
                "label": "Ignore - not exported",
                "required": False,
                "repeatable": True,
                "units": ["-"],
                "std": "-",
                "dim": None,
            }
        )
    return {
        "source": "SchemaRegistry",
        "schemaId": _schema_candidate_id(schema),
        "schema": schema.schema_id,
        "version": schema.schema_version,
        "label": schema.display_label,
        "unitSystem": schema.unit_system,
        "datasetFields": dataset_fields,
        "runFields": run_fields,
        "fieldsById": fields_by_id,
        "datasetSections": _schema_section_views(schema, scope="dataset", fallback_fields=schema.dataset_fields),
        "runSections": _schema_section_views(schema, scope="run", fallback_fields=schema.run_fields),
        "channelFamilies": channel_families,
        "unitFactors": _schema_unit_factors(schema),
        "imageViews": _schema_image_views(schema),
        "supplementalScopes": _schema_supplemental_scopes(schema),
    }


def _schema_field_view(field: Any, *, scope: str) -> dict[str, Any]:
    importance = field.report_importance or ("required" if field.required else "optional")
    validation = dict(field.validation or {})
    options = [
        {
            "v": value,
            "label": field.display_labels.get(value, _enum_display_label(value)),
            "deviation": value in set(field.deviation_values or ()),
        }
        for value in field.allowed_values
    ]
    result: dict[str, Any] = {
        "id": field.field_id,
        "fieldId": field.field_id,
        "label": field.label,
        "type": field.type,
        "scope": scope,
        "role": field.role,
        "hardRequired": bool(field.required),
        "importance": importance,
        "uiGroup": field.ui_group,
        "group": field.ui_group,
        "desc": field.description or "",
        "description": field.description or "",
        "reportRole": field.report_role or "",
        "methodRole": field.method_role or "",
        "default": field.default,
        "storage": field.storage.to_dict(),
    }
    if options:
        result["options"] = options
        result["allowedValues"] = list(field.allowed_values)
    if field.accepted_units:
        result["units"] = list(field.accepted_units)
        result["stdUnit"] = field.standard_unit or field.accepted_units[0]
        result["dim"] = field.unit_dimension
        result["unitInline"] = scope == "dataset"
    if "min" in validation:
        result["min"] = validation["min"]
    if "max" in validation:
        result["max"] = validation["max"]
    if "pattern" in validation:
        result["pattern"] = validation["pattern"]
    if field.visible_when:
        result["visibleWhen"] = _condition_view(field.visible_when)
    if field.required_when:
        result["requiredWhen"] = _condition_view(field.required_when)
    if field.type == "enum" and "not_recorded" in set(field.allowed_values or ()):
        result["notRecorded"] = "not_recorded"
    return result


def _schema_section_views(schema: MTDPSchema, *, scope: str, fallback_fields: tuple[Any, ...]) -> list[dict[str, Any]]:
    sections = schema.metadata_sections_for_scope(scope)
    if sections:
        return [
            {
                "id": section.id,
                "label": section.label,
                "scope": section.scope,
                "uiGroup": section.ui_group,
                "reportSection": section.report_section or "",
                "fields": [_schema_field_view(field, scope=scope) for field in section.fields],
                "fieldIds": [field.field_id for field in section.fields],
            }
            for section in sections
        ]

    grouped: dict[str, list[Any]] = {}
    for field in fallback_fields:
        grouped.setdefault(field.ui_group or "General", []).append(field)
    return [
        {
            "id": _slug(group),
            "label": group,
            "scope": scope,
            "uiGroup": group,
            "reportSection": "",
            "fields": [_schema_field_view(field, scope=scope) for field in fields],
            "fieldIds": [field.field_id for field in fields],
        }
        for group, fields in grouped.items()
    ]


def _schema_channel_family_view(column: Any) -> dict[str, Any]:
    return {
        "id": column.family,
        "label": column.label,
        "required": bool(column.required),
        "repeatable": bool(column.repeatable),
        "units": list(column.accepted_units),
        "std": column.standard_unit,
        "dim": column.unit_dimension,
    }


def _schema_unit_factors(schema: MTDPSchema) -> dict[str, dict[str, float]]:
    factors: dict[str, dict[str, float]] = {}
    rules = dict(schema.unit_conversion_rules or {})
    candidates = [
        *[
            (field.unit_dimension, field.standard_unit, field.accepted_units)
            for field in [*schema.dataset_fields, *schema.run_fields]
            if field.unit_dimension and field.standard_unit and field.accepted_units
        ],
        *[
            (column.unit_dimension, column.standard_unit, column.accepted_units)
            for column in schema.expected_table
            if column.unit_dimension and column.standard_unit and column.accepted_units
        ],
    ]
    for dimension, standard, units in candidates:
        if not dimension or not standard:
            continue
        bucket = factors.setdefault(str(dimension), {str(standard): 1.0})
        for unit in units:
            unit_text = str(unit)
            if unit_text == standard:
                bucket[unit_text] = 1.0
                continue
            direct = rules.get(f"{unit_text}->{standard}")
            inverse = rules.get(f"{standard}->{unit_text}")
            if direct is not None:
                bucket[unit_text] = float(direct)
            elif inverse not in (None, 0):
                bucket[unit_text] = 1.0 / float(inverse)
    return factors


def _schema_image_views(schema: MTDPSchema) -> list[dict[str, Any]]:
    views = schema.image_evidence.get("views", []) if isinstance(schema.image_evidence, dict) else []
    return [
        {
            "id": str(item.get("id") or "other"),
            "label": str(item.get("label") or item.get("id") or "Other image"),
            "required": bool(item.get("required", False)),
            "purpose": list(item.get("purpose", []) or []),
        }
        for item in views
        if isinstance(item, dict)
    ]


def _schema_supplemental_scopes(schema: MTDPSchema) -> list[str]:
    scopes = schema.supplemental_files.get("accepted_scopes", []) if isinstance(schema.supplemental_files, dict) else []
    return [str(scope) for scope in scopes] or ["dataset", "run", "other"]


def _condition_view(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "field": payload.get("field") or payload.get("field_id"),
        "equals": payload.get("equals") if "equals" in payload else payload.get("value"),
    }


def _enum_display_label(value: Any) -> str:
    text = str(value)
    if not text:
        return ""
    return text.replace("_", " ").replace("-", " ").title()


def _same_schema(left: MTDPSchema | None, right: MTDPSchema | None) -> bool:
    if left is None or right is None:
        return False
    return left.schema_id == right.schema_id and left.schema_version == right.schema_version


def _field_values(values: dict[str, EnrichedFieldValue]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field_id, item in values.items():
        result[field_id] = item.value
        if item.unit:
            result[f"{field_id}__unit"] = item.unit
    return result


def _format_numeric(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "group"


def _safe_file_stem(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_")


def _proposal_id(grouper: SampleTypeGrouper) -> str:
    return f"{grouper.engine_name}:{grouper.engine_version}"


def _source_key(path: Path) -> str:
    try:
        return str(path.expanduser().resolve()).casefold()
    except OSError:
        return str(path).casefold()


def _channel_view(channel: Any) -> dict[str, Any]:
    descriptor = channel.descriptor
    family = descriptor.family or None
    return {
        "header": descriptor.original_name,
        "family": family,
        "unit": channel.canonical_unit or channel.original_unit_text,
        "status": "matched" if family and family != "unknown" else "unmatched",
        "note": "; ".join(channel.notes),
    }


def _evidence_view(item: Any) -> dict[str, Any]:
    return {
        "name": Path(str(item.source_path)).name,
        "path": str(item.source_path),
        "view": getattr(item, "view", "other"),
        "role": getattr(item, "role", "audit_evidence"),
        "usedForMetrology": bool(getattr(item, "used_for_metrology", False)),
        "notes": getattr(item, "notes", None),
    }


def _supplemental_view(item: SupplementalFile) -> dict[str, Any]:
    return {
        "name": Path(item.source_path).name,
        "path": str(item.source_path),
        "scope": item.scope,
        "role": item.role,
        "runId": item.run_id,
        "notes": item.notes,
    }


def _sidecar_pair_view(run: RunState, result: SupplementalImportResult) -> dict[str, Any]:
    return {
        "runId": run.run_id,
        "csv": run.source_path.name,
        "csvPath": str(run.source_path),
        "yaml": result.source_path.name if result.source_path is not None else None,
        "yamlPath": str(result.source_path) if result.source_path is not None else None,
        "status": run.sidecar_import_status,
        "paired": result.source_path is not None,
        "importedFieldCount": len(result.imported_fields),
        "unknownKeyCount": len(result.unknown_keys),
        "conflictCount": len(result.conflicts),
        "requiresMapping": result.requires_mapping,
        "mappingProfileId": result.mapping_profile_id,
        "warnings": list(result.warnings),
    }


def _is_yaml_review_key(key: str) -> bool:
    if not key:
        return False
    return key not in {
        "mtdp_supplemental_version",
        "scope",
        "schema_hint.schema_id",
        "schema_hint.schema_version",
        "notes",
        "images",
    } and not key.startswith("images.")


def _field_option(field: Any) -> dict[str, Any]:
    return {
        "id": field.field_id,
        "label": field.label,
        "scope": field.role,
        "type": field.type,
        "required": bool(field.required),
        "acceptedUnits": list(field.accepted_units),
        "standardUnit": field.standard_unit,
        "allowedValues": list(field.allowed_values),
    }


def _field_conflict_view(conflict: Any) -> dict[str, Any]:
    return {
        "fieldId": conflict.field_id,
        "existingValue": conflict.existing_value,
        "existingUnit": conflict.existing_unit,
        "importedValue": conflict.imported_value,
        "importedUnit": conflict.imported_unit,
        "existingSource": conflict.existing_source,
        "importedSource": conflict.imported_source,
        "message": conflict.message,
    }


def _yaml_mapping_status(
    field: Any,
    transformed: Any,
    unit_status: str | None,
    canonical: bool,
    requires_confirmation: bool,
) -> str:
    if field is None:
        return "unmapped"
    if requires_confirmation:
        return "ambiguous"
    if transformed is not None and transformed.requires_confirmation:
        if transformed.transform_name == "date_unresolved":
            return "requires_date_format"
        if transformed.warnings and any("Unit" in warning for warning in transformed.warnings):
            return "requires_unit"
        return "requires_confirmation"
    if unit_status:
        return unit_status
    if transformed is not None and transformed.transform_name == "bool_validity_map":
        return "value_transformed"
    if transformed is not None and "ISO" in transformed.transform_name:
        return "date_format_inferred"
    return "canonical_mapped" if canonical else "alias_mapped"


def _value_transform_name(transformed: Any) -> str | None:
    if transformed is None:
        return None
    return transformed.transform_name if transformed.transform_name in {"bool_validity_map", "value_map"} else None


def _json_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        try:
            import json

            return json.dumps(value, sort_keys=True)
        except TypeError:
            return str(value)
    return "" if value is None else str(value)


def _supplemental_scope(raw: str) -> str:
    value = str(raw or "dataset").strip().lower().replace("/", "_").replace(" ", "_").replace("-", "_")
    aliases = {
        "schema_mapping_support": "schema_mapping",
        "schema_mapping": "schema_mapping",
        "schema__mapping_support": "schema_mapping",
        "calibration_equipment_evidence": "calibration",
        "equipment_evidence": "equipment_evidence",
    }
    value = aliases.get(value, value)
    allowed = {"dataset", "run", "schema_mapping", "calibration", "equipment_evidence", "other"}
    return value if value in allowed else "other"


def _supplemental_role(scope: str) -> str:
    return {
        "dataset": "documents",
        "run": "run_evidence",
        "schema_mapping": "mapping_support",
        "calibration": "calibration",
        "equipment_evidence": "calibration",
        "other": "other",
    }.get(scope, "other")


def _run_id_for(existing_runs: list[RunState], source_path: Path) -> str:
    stem = source_path.stem.strip() or f"run_{len(existing_runs) + 1:03d}"
    candidate = stem
    used = {run.run_id for run in existing_runs}
    counter = 1
    while candidate in used:
        counter += 1
        candidate = f"{stem}_{counter}"
    return candidate


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result
