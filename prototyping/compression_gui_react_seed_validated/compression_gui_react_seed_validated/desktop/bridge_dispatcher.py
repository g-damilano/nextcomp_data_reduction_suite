from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


Handler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class BridgeContractError(Exception):
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


@dataclass
class BridgeDispatcher:
    """JSON command dispatcher for the React/PySide transition shell.

    This is intentionally pure Python so it can be contract-tested without
    importing PySide6 or starting a WebEngine window.
    """

    backend_root: Path | str | None = None
    dialog_service: Any | None = None
    log_path: Path | str | None = None
    event_log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        root = _find_backend_root(Path(self.backend_root).resolve() if self.backend_root else None)
        self.backend_root = root
        self.log_path = Path(self.log_path).expanduser() if self.log_path else None
        src_root = root / "src"
        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))
        from gui_bridge.services import (
            AnalysisSessionError,
            AnalysisSessionService,
            MethodEditorSessionError,
            MethodEditorSessionService,
            PackagingSessionError,
            PackagingSessionService,
        )

        self._analysis_error_type = AnalysisSessionError
        self._analysis_service = AnalysisSessionService()
        self._method_editor_error_type = MethodEditorSessionError
        self._method_editor_service = MethodEditorSessionService(
            generated_root=_generated_methods_root(root)
        )
        self._packaging_error_type = PackagingSessionError
        self._packaging_service = PackagingSessionService()
        self._handlers: dict[tuple[str, str], Handler] = {
            ("shell", "ping"): self._shell_ping,
            ("methodEditor", "listMethods"): self._method_editor_list_methods,
            ("methodEditor", "loadMethod"): self._method_editor_load_method,
            ("methodEditor", "createDraft"): self._method_editor_create_draft,
            ("methodEditor", "updateDraft"): self._method_editor_update_draft,
            ("methodEditor", "validateDraft"): self._method_editor_validate_draft,
            ("methodEditor", "generateVersion"): self._method_editor_generate_version,
            ("methodEditor", "registerGeneratedMethod"): self._method_editor_register_generated_method,
            ("methodEditor", "exportMethodPackage"): self._method_editor_export_method_package,
            ("methodEditor", "openMethodPackage"): self._method_editor_open_method_package,
            ("methodEditor", "renameMethod"): self._method_editor_rename_method,
            ("methodEditor", "deleteMethod"): self._method_editor_delete_method,
            ("packaging", "createSession"): self._packaging_create_session,
            ("packaging", "getSession"): self._packaging_get_session,
            ("packaging", "listSchemas"): self._packaging_list_schemas,
            ("packaging", "openPackageDialog"): self._packaging_open_package_dialog,
            ("packaging", "openSourcesDialog"): self._packaging_open_sources_dialog,
            ("packaging", "loadSources"): self._packaging_load_sources,
            ("packaging", "loadPackage"): self._packaging_load_package,
            ("packaging", "setSchema"): self._packaging_set_schema,
            ("packaging", "validateGroup"): self._packaging_validate_group,
            ("packaging", "exportGroup"): self._packaging_export_group,
            ("packaging", "exportAllReady"): self._packaging_export_all_ready,
            ("packaging", "updateDatasetFields"): self._packaging_update_dataset_fields,
            ("packaging", "updateRunFields"): self._packaging_update_run_fields,
            ("packaging", "updateGroupRunFields"): self._packaging_update_group_run_fields,
            ("packaging", "updateRunFieldMatrix"): self._packaging_update_run_field_matrix,
            ("packaging", "setGroupRunUnit"): self._packaging_set_group_run_unit,
            ("packaging", "proposeGroups"): self._packaging_propose_groups,
            ("packaging", "applyGroupingProposal"): self._packaging_apply_grouping_proposal,
            ("packaging", "addImageEvidence"): self._packaging_add_image_evidence,
            ("packaging", "removeImageEvidence"): self._packaging_remove_image_evidence,
            ("packaging", "addSupplementalFiles"): self._packaging_add_supplemental_files,
            ("packaging", "removeSupplementalFile"): self._packaging_remove_supplemental_file,
            ("packaging", "rematchYamlSidecars"): self._packaging_rematch_yaml_sidecars,
            ("packaging", "reviewYamlMapping"): self._packaging_review_yaml_mapping,
            ("packaging", "applyYamlMappingProfile"): self._packaging_apply_yaml_mapping_profile,
            ("packaging", "createGroup"): self._packaging_create_group,
            ("packaging", "renameGroup"): self._packaging_rename_group,
            ("packaging", "deleteGroup"): self._packaging_delete_group,
            ("packaging", "moveRun"): self._packaging_move_run,
            ("analysis", "createSession"): self._analysis_create_session,
            ("analysis", "getSession"): self._analysis_get_session,
            ("analysis", "getEvents"): self._analysis_get_events,
            ("analysis", "listRecentPackages"): self._analysis_list_recent_packages,
            ("analysis", "loadPackage"): self._analysis_load_package,
            ("analysis", "openPackageDialog"): self._analysis_open_package_dialog,
            ("analysis", "listMethods"): self._analysis_list_methods,
            ("analysis", "selectMethod"): self._analysis_select_method,
            ("analysis", "loadMapping"): self._analysis_load_mapping,
            ("analysis", "openMappingDialog"): self._analysis_open_mapping_dialog,
            ("analysis", "confirmMapping"): self._analysis_confirm_mapping,
            ("analysis", "applyMappingPatch"): self._analysis_apply_mapping_patch,
            ("analysis", "saveMappingDialog"): self._analysis_save_mapping_dialog,
            ("analysis", "checkReadiness"): self._analysis_check_readiness,
            ("analysis", "startRun"): self._analysis_start_run,
            ("analysis", "cancelRun"): self._analysis_cancel_run,
            ("analysis", "updateAcceptanceDecision"): self._analysis_update_acceptance_decision,
            ("analysis", "confirmReview"): self._analysis_confirm_review,
            ("analysis", "finalizeMtda"): self._analysis_finalize_mtda,
            ("analysis", "applyReportAmendments"): self._analysis_apply_report_amendments,
            ("analysis", "copyOutputPath"): self._analysis_copy_output_path,
            ("analysis", "openArtifact"): self._analysis_open_artifact,
        }

    def dispatch_json(self, raw_request: str | bytes | None) -> str:
        started_at = time.perf_counter()
        try:
            request = json.loads(raw_request or "{}")
        except json.JSONDecodeError as exc:
            response = self._error_response(
                "ValidationError",
                "Bridge request must be valid JSON.",
                details={"line": exc.lineno, "column": exc.colno},
            )
            self._record(
                str(uuid.uuid4()),
                "bridge",
                "dispatch_json",
                None,
                response["status"],
                duration_ms=_duration_ms(started_at),
                error_type=response.get("error_type"),
            )
            return self._response_json(response)
        return self._response_json(self.dispatch(request))

    def dispatch(self, request: Any) -> dict[str, Any]:
        started_at = time.perf_counter()
        if not isinstance(request, dict):
            response = self._error_response(
                "ValidationError",
                "Bridge request must be a JSON object.",
            )
            self._record(
                str(uuid.uuid4()),
                "bridge",
                "dispatch",
                None,
                response["status"],
                duration_ms=_duration_ms(started_at),
                error_type=response.get("error_type"),
            )
            return response

        request_id = str(request.get("id") or uuid.uuid4())
        namespace = str(request.get("namespace") or "").strip()
        command = str(request.get("command") or "").strip()
        session_id = request.get("session_id")
        payload = request.get("payload") or {}
        if session_id is None and isinstance(payload, dict):
            session_id = payload.get("session_id") or payload.get("sessionId")

        if not namespace or not command:
            response = self._error_response(
                "ValidationError",
                "Bridge request requires namespace and command.",
                request_id=request_id,
                details={"namespace": namespace, "command": command},
            )
            self._record(
                request_id,
                namespace,
                command,
                session_id,
                response["status"],
                duration_ms=_duration_ms(started_at),
                error_type=response.get("error_type"),
            )
            return response
        if not isinstance(payload, dict):
            response = self._error_response(
                "ValidationError",
                "Bridge payload must be a JSON object.",
                request_id=request_id,
                details={"namespace": namespace, "command": command},
            )
            self._record(
                request_id,
                namespace,
                command,
                session_id,
                response["status"],
                duration_ms=_duration_ms(started_at),
                error_type=response.get("error_type"),
            )
            return response

        handler = self._handlers.get((namespace, command))
        if handler is None:
            response = self._error_response(
                "UnsupportedCommand",
                f"Unsupported bridge command: {namespace}.{command}",
                request_id=request_id,
                details={"namespace": namespace, "command": command},
            )
            self._record(
                request_id,
                namespace,
                command,
                session_id,
                response["status"],
                duration_ms=_duration_ms(started_at),
                error_type=response.get("error_type"),
            )
            return response

        try:
            data = handler(payload, {"request_id": request_id, "session_id": session_id})
            response = {
                "id": request_id,
                "status": "ok",
                "data": _json_safe(data),
                "warnings": [],
            }
        except BridgeContractError as exc:
            response = self._error_response(
                exc.error_type,
                str(exc),
                request_id=request_id,
                recoverable=exc.recoverable,
                details=exc.details,
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            response = self._error_response(
                "InternalError",
                "Backend command failed inside the bridge dispatcher.",
                request_id=request_id,
                recoverable=True,
                details={"exception": exc.__class__.__name__},
            )

        self._record(
            request_id,
            namespace,
            command,
            session_id,
            response["status"],
            duration_ms=_duration_ms(started_at),
            error_type=response.get("error_type"),
        )
        return response

    def _shell_ping(self, _payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "bridge": "gui-transition",
            "backend_root": str(self.backend_root),
            "request_id": context["request_id"],
        }

    def _packaging_create_session(self, _payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        return self._packaging_call(self._packaging_service.create_session)

    def _packaging_get_session(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._packaging_call(self._packaging_service.get_session, session_id)

    def _packaging_list_schemas(self, _payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        return self._packaging_call(self._packaging_service.list_schemas)

    def _packaging_open_package_dialog(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        if self.dialog_service is None or not hasattr(self.dialog_service, "open_package_path"):
            raise BridgeContractError(
                "Unsupported",
                "Native open-package dialog is unavailable in this host.",
                details={"command": "packaging.openPackageDialog"},
            )
        selected_path = self.dialog_service.open_package_path(payload.get("initial_dir"))
        if not selected_path:
            raise BridgeContractError(
                "Cancelled",
                "Open MTDP package was cancelled.",
                details={"command": "packaging.openPackageDialog"},
            )
        return self._packaging_call(self._packaging_service.load_package, session_id, str(selected_path))

    def _packaging_open_sources_dialog(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        kind = str(payload.get("kind") or "folder").strip().lower()
        if kind not in {"folder", "files"}:
            raise BridgeContractError(
                "ValidationError",
                "packaging.openSourcesDialog requires kind to be 'folder' or 'files'.",
                details={"kind": kind},
            )
        if self.dialog_service is None or not hasattr(self.dialog_service, "open_sources_paths"):
            raise BridgeContractError(
                "Unsupported",
                "Native source-file dialog is unavailable in this host.",
                details={"command": "packaging.openSourcesDialog"},
            )
        selected_paths = self.dialog_service.open_sources_paths(kind, payload.get("initial_dir"))
        if not selected_paths:
            raise BridgeContractError(
                "Cancelled",
                "Open source files was cancelled.",
                details={"command": "packaging.openSourcesDialog", "kind": kind},
            )
        return self._packaging_call(self._packaging_service.load_sources, session_id, selected_paths)

    def _packaging_load_sources(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        paths = payload.get("paths") or []
        if not isinstance(paths, list):
            raise BridgeContractError(
                "ValidationError",
                "packaging.loadSources requires payload.paths to be a list.",
                details={"paths_type": type(paths).__name__},
            )
        return self._packaging_call(self._packaging_service.load_sources, session_id, paths)

    def _packaging_load_package(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        package_path = payload.get("path") or payload.get("package_path")
        if not package_path:
            raise BridgeContractError(
                "ValidationError",
                "packaging.loadPackage requires payload.path.",
            )
        return self._packaging_call(self._packaging_service.load_package, session_id, str(package_path))

    def _packaging_set_schema(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        schema_id = payload.get("schema_id") or payload.get("id")
        schema_key = payload.get("schema")
        schema_version = payload.get("schema_version") or payload.get("version")
        return self._packaging_call(
            self._packaging_service.set_schema,
            session_id,
            str(schema_id) if schema_id else None,
            schema_id=str(schema_key) if schema_key else None,
            schema_version=str(schema_version) if schema_version else None,
        )

    def _packaging_validate_group(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        return self._packaging_call(
            self._packaging_service.validate_group,
            session_id,
            str(group_id) if group_id else None,
        )

    def _packaging_export_group(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        output_path = payload.get("output_path") or payload.get("path")
        if not output_path:
            if self.dialog_service is None or not hasattr(self.dialog_service, "save_export_path"):
                raise BridgeContractError(
                    "Unsupported",
                    "Native save-export dialog is unavailable in this host.",
                    details={"command": "packaging.exportGroup"},
                )
            output_path = self.dialog_service.save_export_path(
                default_name=payload.get("default_name"),
                initial_dir=payload.get("initial_dir"),
            )
            if not output_path:
                raise BridgeContractError(
                    "Cancelled",
                    "Export MTDP package was cancelled.",
                    details={"command": "packaging.exportGroup"},
                )
        return self._packaging_call(
            self._packaging_service.export_group,
            session_id,
            str(group_id) if group_id else None,
            str(output_path),
        )

    def _packaging_export_all_ready(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        output_dir = payload.get("output_dir") or payload.get("directory")
        if not output_dir and self.dialog_service is not None and hasattr(self.dialog_service, "open_export_directory"):
            output_dir = self.dialog_service.open_export_directory(
                initial_dir=payload.get("initial_dir"),
            )
            if not output_dir:
                raise BridgeContractError(
                    "Cancelled",
                    "Export all ready groups was cancelled.",
                    details={"command": "packaging.exportAllReady"},
                )
        return self._packaging_call(
            self._packaging_service.export_all_ready,
            session_id,
            str(output_dir) if output_dir else None,
        )

    def _packaging_update_dataset_fields(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        patch = payload.get("patch")
        if not isinstance(patch, dict):
            raise BridgeContractError(
                "ValidationError",
                "packaging.updateDatasetFields requires payload.patch to be an object.",
                details={"patch_type": type(patch).__name__},
            )
        return self._packaging_call(
            self._packaging_service.update_dataset_fields,
            session_id,
            str(group_id) if group_id else None,
            patch,
        )

    def _packaging_update_run_fields(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        patch = payload.get("patch")
        if not isinstance(patch, dict):
            raise BridgeContractError(
                "ValidationError",
                "packaging.updateRunFields requires payload.patch to be an object.",
                details={"patch_type": type(patch).__name__},
            )
        return self._packaging_call(
            self._packaging_service.update_run_fields,
            session_id,
            str(group_id) if group_id else None,
            str(run_id or ""),
            patch,
        )

    def _packaging_update_group_run_fields(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        patch = payload.get("patch")
        run_ids = payload.get("run_ids")
        if not isinstance(patch, dict):
            raise BridgeContractError(
                "ValidationError",
                "packaging.updateGroupRunFields requires payload.patch to be an object.",
                details={"patch_type": type(patch).__name__},
            )
        if run_ids is not None and not isinstance(run_ids, list):
            raise BridgeContractError(
                "ValidationError",
                "packaging.updateGroupRunFields requires payload.run_ids to be a list when provided.",
                details={"run_ids_type": type(run_ids).__name__},
            )
        return self._packaging_call(
            self._packaging_service.update_group_run_fields,
            session_id,
            str(group_id) if group_id else None,
            patch,
            [str(run_id) for run_id in run_ids] if run_ids is not None else None,
        )

    def _packaging_update_run_field_matrix(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        updates = payload.get("updates")
        if not isinstance(updates, list):
            raise BridgeContractError(
                "ValidationError",
                "packaging.updateRunFieldMatrix requires payload.updates to be a list.",
                details={"updates_type": type(updates).__name__},
            )
        return self._packaging_call(
            self._packaging_service.update_run_field_matrix,
            session_id,
            str(group_id) if group_id else None,
            updates,
        )

    def _packaging_set_group_run_unit(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        field_id = payload.get("field_id")
        unit = payload.get("unit")
        convert = bool(payload.get("convert", False))
        return self._packaging_call(
            self._packaging_service.set_group_run_unit,
            session_id,
            str(group_id) if group_id else None,
            str(field_id or ""),
            str(unit or ""),
            convert=convert,
        )

    def _packaging_propose_groups(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._packaging_call(self._packaging_service.propose_groups, session_id)

    def _packaging_apply_grouping_proposal(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        proposal_id = payload.get("proposal_id") or payload.get("id")
        return self._packaging_call(
            self._packaging_service.apply_grouping_proposal,
            session_id,
            str(proposal_id) if proposal_id else None,
        )

    def _packaging_add_image_evidence(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        paths = self._paths_from_payload_or_dialog(
            payload,
            dialog_method="open_image_paths",
            command="packaging.addImageEvidence",
        )
        return self._packaging_call(
            self._packaging_service.add_image_evidence,
            session_id,
            str(group_id) if group_id else None,
            str(run_id or ""),
            paths,
            view=str(payload.get("view")) if payload.get("view") else None,
            role=str(payload.get("role") or "audit_evidence"),
            notes=str(payload.get("notes")) if payload.get("notes") else None,
        )

    def _packaging_remove_image_evidence(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        index = self._payload_index(payload, "packaging.removeImageEvidence")
        return self._packaging_call(
            self._packaging_service.remove_image_evidence,
            session_id,
            str(group_id) if group_id else None,
            str(run_id or ""),
            index,
        )

    def _packaging_add_supplemental_files(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        paths = self._paths_from_payload_or_dialog(
            payload,
            dialog_method="open_supplemental_paths",
            command="packaging.addSupplementalFiles",
        )
        return self._packaging_call(
            self._packaging_service.add_supplemental_files,
            session_id,
            str(group_id) if group_id else None,
            paths,
            scope=str(payload.get("scope") or "dataset"),
            run_id=str(payload.get("run_id")) if payload.get("run_id") else None,
            role=str(payload.get("role")) if payload.get("role") else None,
            notes=str(payload.get("notes")) if payload.get("notes") else None,
        )

    def _packaging_remove_supplemental_file(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        index = self._payload_index(payload, "packaging.removeSupplementalFile")
        return self._packaging_call(
            self._packaging_service.remove_supplemental_file,
            session_id,
            str(group_id) if group_id else None,
            index,
            run_id=str(payload.get("run_id")) if payload.get("run_id") else None,
        )

    def _packaging_rematch_yaml_sidecars(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        return self._packaging_call(
            self._packaging_service.rematch_yaml_sidecars,
            session_id,
            str(group_id) if group_id else None,
            run_id=str(run_id) if run_id else None,
            apply_all=bool(payload.get("apply_all", True)),
        )

    def _packaging_review_yaml_mapping(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        return self._packaging_call(
            self._packaging_service.review_yaml_mapping,
            session_id,
            str(group_id) if group_id else None,
            run_id=str(run_id) if run_id else None,
        )

    def _packaging_apply_yaml_mapping_profile(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        run_id = payload.get("run_id")
        mappings = payload.get("mappings")
        if not isinstance(mappings, list):
            raise BridgeContractError(
                "ValidationError",
                "packaging.applyYamlMappingProfile requires payload.mappings to be a list.",
                details={"mappings_type": type(mappings).__name__},
            )
        return self._packaging_call(
            self._packaging_service.apply_yaml_mapping_profile,
            session_id,
            str(group_id) if group_id else None,
            run_id=str(run_id) if run_id else None,
            profile_id=str(payload.get("profile_id") or payload.get("profileId") or ""),
            mappings=mappings,
            apply_all=bool(payload.get("apply_all", payload.get("applyAll", True))),
        )

    def _packaging_create_group(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        name = payload.get("name")
        return self._packaging_call(
            self._packaging_service.create_group,
            session_id,
            str(name) if name is not None else None,
        )

    def _packaging_rename_group(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        name = payload.get("name")
        return self._packaging_call(
            self._packaging_service.rename_group,
            session_id,
            str(group_id or ""),
            str(name or ""),
        )

    def _packaging_delete_group(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        group_id = payload.get("group_id") or payload.get("group_key")
        return self._packaging_call(
            self._packaging_service.delete_group,
            session_id,
            str(group_id or ""),
        )

    def _packaging_move_run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        run_id = payload.get("run_id")
        target_group_id = payload.get("target_group_id") or payload.get("target_group_key")
        from_group_id = payload.get("from_group_id") or payload.get("from_group_key")
        index = payload.get("index")
        if index is not None:
            try:
                index = int(index)
            except (TypeError, ValueError) as exc:
                raise BridgeContractError(
                    "ValidationError",
                    "packaging.moveRun requires payload.index to be an integer when provided.",
                    details={"index": index},
                ) from exc
        return self._packaging_call(
            self._packaging_service.move_run,
            session_id,
            str(run_id or ""),
            str(target_group_id or ""),
            from_group_id=str(from_group_id) if from_group_id else None,
            index=index,
        )

    def _paths_from_payload_or_dialog(
        self,
        payload: dict[str, Any],
        *,
        dialog_method: str,
        command: str,
    ) -> list[str]:
        raw_paths = payload.get("paths")
        if raw_paths is not None:
            if not isinstance(raw_paths, list):
                raise BridgeContractError(
                    "ValidationError",
                    f"{command} requires payload.paths to be a list when provided.",
                    details={"paths_type": type(raw_paths).__name__},
                )
            return [str(path) for path in raw_paths]
        if self.dialog_service is None or not hasattr(self.dialog_service, dialog_method):
            raise BridgeContractError(
                "Unsupported",
                f"Native file dialog is unavailable for {command}.",
                details={"command": command},
            )
        selected_paths = getattr(self.dialog_service, dialog_method)(payload.get("initial_dir"))
        if not selected_paths:
            raise BridgeContractError(
                "Cancelled",
                f"{command} was cancelled.",
                details={"command": command},
            )
        return [str(path) for path in selected_paths]

    def _payload_index(self, payload: dict[str, Any], command: str) -> int:
        try:
            return int(payload.get("index"))
        except (TypeError, ValueError) as exc:
            raise BridgeContractError(
                "ValidationError",
                f"{command} requires payload.index to be an integer.",
                details={"index": payload.get("index")},
            ) from exc

    def _analysis_create_session(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        initial_package_path = payload.get("initial_package_path") or payload.get("package_path")
        return self._analysis_call(
            self._analysis_service.create_session,
            str(initial_package_path) if initial_package_path else None,
        )

    def _analysis_get_session(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._analysis_call(self._analysis_service.get_session, session_id)

    def _analysis_get_events(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        cursor = payload.get("cursor")
        if cursor is None:
            cursor = payload.get("since")
        if cursor is None:
            cursor = payload.get("since_index")
        return self._analysis_call(
            self._analysis_service.get_events,
            session_id,
            cursor,
            payload.get("limit"),
        )

    def _analysis_list_recent_packages(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        limit = _positive_int(payload.get("limit"), default=12, upper=50)
        roots_payload = payload.get("roots")
        roots: list[Path] = []
        if isinstance(roots_payload, list):
            roots = [
                _resolve_bridge_path(root, self.backend_root)
                for root in roots_payload
                if str(root or "").strip()
            ]
        if not roots:
            roots = [
                self.backend_root / "datasets",
                self.backend_root / "tests" / "fixtures" / "mtdp",
            ]
        packages = _discover_recent_analysis_packages(roots, limit=limit)
        return {
            "schema_id": "gui_bridge.analysis_recent_packages.v0_1",
            "packages": packages,
            "count": len(packages),
            "roots": [str(root) for root in roots if root.exists()],
        }

    def _analysis_load_package(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        path = payload.get("path") or payload.get("package_path")
        if not path:
            raise BridgeContractError(
                "ValidationError",
                "analysis.loadPackage requires payload.path.",
            )
        return self._analysis_call(
            self._analysis_service.load_package,
            session_id,
            str(path),
        )

    def _analysis_open_package_dialog(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        if self.dialog_service is None or not (
            hasattr(self.dialog_service, "open_analysis_package_path")
            or hasattr(self.dialog_service, "open_package_path")
        ):
            raise BridgeContractError(
                "Unsupported",
                "Native analysis package dialog is unavailable in this host.",
                details={"command": "analysis.openPackageDialog"},
            )
        open_package = getattr(self.dialog_service, "open_analysis_package_path", None)
        if open_package is None:
            open_package = self.dialog_service.open_package_path
        selected_path = open_package(payload.get("initial_dir"))
        if not selected_path:
            raise BridgeContractError(
                "Cancelled",
                "Open analysis package was cancelled.",
                details={"command": "analysis.openPackageDialog"},
            )
        if session_id:
            return self._analysis_call(
                self._analysis_service.load_package,
                session_id,
                str(selected_path),
            )
        return self._analysis_call(
            self._analysis_service.create_session,
            str(selected_path),
        )

    def _analysis_list_methods(self, _payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        return self._analysis_call(self._analysis_service.list_methods)

    def _method_editor_list_methods(self, _payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        return self._method_editor_call(self._method_editor_service.list_methods)

    def _method_editor_load_method(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        method_id = str(payload.get("method_id") or payload.get("methodId") or "")
        return self._method_editor_call(self._method_editor_service.load_method, method_id)

    def _method_editor_create_draft(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        method_id = str(payload.get("method_id") or payload.get("methodId") or "")
        draft_label = payload.get("draft_label") or payload.get("draftLabel")
        return self._method_editor_call(
            self._method_editor_service.create_draft,
            method_id,
            draft_label=str(draft_label) if draft_label else None,
        )

    def _method_editor_update_draft(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        draft_id = payload.get("draft_id") or payload.get("draftId")
        draft_path = payload.get("draft_path") or payload.get("draftPath") or payload.get("path")
        patch = payload.get("patch")
        if not isinstance(patch, dict):
            raise BridgeContractError(
                "ValidationError",
                "methodEditor.updateDraft requires payload.patch to be an object.",
                details={"patch_type": type(patch).__name__},
            )
        return self._method_editor_call(
            self._method_editor_service.update_draft,
            draft_id=str(draft_id) if draft_id else None,
            draft_path=str(draft_path) if draft_path else None,
            patch=patch,
            reason=str(payload.get("reason") or ""),
        )

    def _method_editor_validate_draft(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        draft_id = payload.get("draft_id") or payload.get("draftId")
        draft_path = payload.get("draft_path") or payload.get("draftPath") or payload.get("path")
        return self._method_editor_call(
            self._method_editor_service.validate_draft,
            draft_id=str(draft_id) if draft_id else None,
            draft_path=str(draft_path) if draft_path else None,
        )

    def _method_editor_generate_version(self, payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        draft_id = payload.get("draft_id") or payload.get("draftId")
        draft_path = payload.get("draft_path") or payload.get("draftPath") or payload.get("path")
        target_version = payload.get("target_version") or payload.get("targetVersion") or payload.get("version")
        return self._method_editor_call(
            self._method_editor_service.generate_version,
            draft_id=str(draft_id) if draft_id else None,
            draft_path=str(draft_path) if draft_path else None,
            target_version=str(target_version) if target_version else None,
        )

    def _method_editor_register_generated_method(
        self,
        payload: dict[str, Any],
        _context: dict[str, Any],
    ) -> dict[str, Any]:
        method_path = payload.get("method_path") or payload.get("methodPath") or payload.get("path")
        return self._method_editor_call(
            self._method_editor_service.register_generated_method,
            str(method_path) if method_path else "",
        )

    def _method_editor_export_method_package(
        self,
        payload: dict[str, Any],
        _context: dict[str, Any],
    ) -> dict[str, Any]:
        method_path = payload.get("method_path") or payload.get("methodPath") or payload.get("path")
        output_path = (
            payload.get("output_path")
            or payload.get("outputPath")
            or payload.get("destination_path")
            or payload.get("destinationPath")
        )
        if not output_path and self.dialog_service is not None and hasattr(
            self.dialog_service,
            "save_method_package_path",
        ):
            output_path = self.dialog_service.save_method_package_path(
                default_name=payload.get("default_name") or payload.get("defaultName"),
                initial_dir=payload.get("initial_dir"),
            )
            if not output_path:
                raise BridgeContractError(
                    "Cancelled",
                    "Method Editor package export was cancelled.",
                    details={"command": "methodEditor.exportMethodPackage"},
                )
        return self._method_editor_call(
            self._method_editor_service.export_method_package,
            str(method_path) if method_path else "",
            output_path=str(output_path) if output_path else None,
            overwrite=bool(payload.get("overwrite")),
        )

    def _method_editor_open_method_package(
        self,
        payload: dict[str, Any],
        _context: dict[str, Any],
    ) -> dict[str, Any]:
        source_path = (
            payload.get("path")
            or payload.get("source_path")
            or payload.get("sourcePath")
            or payload.get("method_path")
            or payload.get("methodPath")
        )
        if not source_path:
            if self.dialog_service is None or not hasattr(self.dialog_service, "open_method_package_path"):
                raise BridgeContractError(
                    "Unsupported",
                    "Native Method Editor package open dialog is unavailable in this host.",
                    details={"command": "methodEditor.openMethodPackage"},
                )
            source_path = self.dialog_service.open_method_package_path(payload.get("initial_dir"))
            if not source_path:
                raise BridgeContractError(
                    "Cancelled",
                    "Method Editor package open was cancelled.",
                    details={"command": "methodEditor.openMethodPackage"},
                )
        return self._method_editor_call(
            self._method_editor_service.import_method_package,
            str(source_path),
            register=payload.get("register", True) is not False,
            overwrite=bool(payload.get("overwrite")),
        )

    def _method_editor_rename_method(
        self,
        payload: dict[str, Any],
        _context: dict[str, Any],
    ) -> dict[str, Any]:
        method_id = payload.get("method_id") or payload.get("methodId") or payload.get("id")
        method_path = payload.get("method_path") or payload.get("methodPath") or payload.get("path")
        label = payload.get("label") or payload.get("name") or payload.get("method_name") or payload.get("methodName")
        return self._method_editor_call(
            self._method_editor_service.rename_generated_method,
            method_id=str(method_id) if method_id else None,
            method_path=str(method_path) if method_path else None,
            label=str(label) if label is not None else "",
        )

    def _method_editor_delete_method(
        self,
        payload: dict[str, Any],
        _context: dict[str, Any],
    ) -> dict[str, Any]:
        method_id = payload.get("method_id") or payload.get("methodId") or payload.get("id")
        method_path = payload.get("method_path") or payload.get("methodPath") or payload.get("path")
        return self._method_editor_call(
            self._method_editor_service.delete_generated_method,
            method_id=str(method_id) if method_id else None,
            method_path=str(method_path) if method_path else None,
        )

    def _analysis_select_method(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        method_id = str(payload.get("method_id") or payload.get("methodId") or "")
        if not method_id:
            raise BridgeContractError(
                "ValidationError",
                "analysis.selectMethod requires payload.method_id.",
            )
        return self._analysis_call(
            self._analysis_service.select_method,
            session_id,
            method_id,
        )

    def _analysis_load_mapping(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        path = payload.get("path") or payload.get("mapping_path")
        if not path:
            raise BridgeContractError(
                "ValidationError",
                "analysis.loadMapping requires payload.path.",
            )
        return self._analysis_call(
            self._analysis_service.load_mapping,
            session_id,
            str(path),
        )

    def _analysis_open_mapping_dialog(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        if self.dialog_service is None or not hasattr(self.dialog_service, "open_mapping_profile_path"):
            raise BridgeContractError(
                "Unsupported",
                "Native mapping-profile open dialog is unavailable in this host.",
                details={"command": "analysis.openMappingDialog"},
            )
        selected_path = self.dialog_service.open_mapping_profile_path(payload.get("initial_dir"))
        if not selected_path:
            raise BridgeContractError(
                "Cancelled",
                "Choose method mapping profile was cancelled.",
                details={"command": "analysis.openMappingDialog"},
            )
        return self._analysis_call(
            self._analysis_service.load_mapping,
            session_id,
            str(selected_path),
        )

    def _analysis_confirm_mapping(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._analysis_call(
            self._analysis_service.confirm_mapping,
            session_id,
        )

    def _analysis_apply_mapping_patch(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        bindings = payload.get("bindings") or payload.get("mappings")
        if not isinstance(bindings, list) or not bindings:
            raise BridgeContractError(
                "ValidationError",
                "analysis.applyMappingPatch requires payload.bindings.",
            )
        output_path = payload.get("output_path") or payload.get("path")
        return self._analysis_call(
            self._analysis_service.apply_mapping_patch,
            session_id,
            bindings,
            str(output_path) if output_path else None,
        )

    def _analysis_save_mapping_dialog(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        bindings = payload.get("bindings") or payload.get("mappings")
        if not isinstance(bindings, list) or not bindings:
            raise BridgeContractError(
                "ValidationError",
                "analysis.saveMappingDialog requires payload.bindings.",
            )
        if self.dialog_service is None or not hasattr(self.dialog_service, "save_mapping_profile_path"):
            raise BridgeContractError(
                "Unsupported",
                "Native mapping-profile save dialog is unavailable in this host.",
                details={"command": "analysis.saveMappingDialog"},
            )
        output_path = self.dialog_service.save_mapping_profile_path(
            default_name=payload.get("default_name"),
            initial_dir=payload.get("initial_dir"),
        )
        if not output_path:
            raise BridgeContractError(
                "Cancelled",
                "Save repaired mapping profile was cancelled.",
                details={"command": "analysis.saveMappingDialog"},
            )
        return self._analysis_call(
            self._analysis_service.apply_mapping_patch,
            session_id,
            bindings,
            str(output_path),
        )

    def _analysis_check_readiness(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        output_path = payload.get("output_path") or payload.get("path")
        return self._analysis_call(
            self._analysis_service.check_readiness,
            session_id,
            str(output_path) if output_path else None,
        )

    def _analysis_start_run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        output_path = payload.get("output_path") or payload.get("path")
        human_decisions = payload.get("human_decisions") or []
        report_overrides = payload.get("report_overrides") or []
        if human_decisions is not None and not isinstance(human_decisions, list):
            raise BridgeContractError(
                "ValidationError",
                "analysis.startRun requires payload.human_decisions to be a list when provided.",
                details={"human_decisions_type": type(human_decisions).__name__},
            )
        if report_overrides is not None and not isinstance(report_overrides, list):
            raise BridgeContractError(
                "ValidationError",
                "analysis.startRun requires payload.report_overrides to be a list when provided.",
                details={"report_overrides_type": type(report_overrides).__name__},
            )
        return self._analysis_call(
            self._analysis_service.start_run,
            session_id,
            str(output_path) if output_path else None,
            overwrite=bool(payload.get("overwrite", True)),
            generate_workbench=bool(payload.get("generate_workbench", True)),
            human_decisions=human_decisions,
            report_overrides=report_overrides,
        )

    def _analysis_cancel_run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._analysis_call(
            self._analysis_service.cancel_run,
            session_id,
        )

    def _analysis_update_acceptance_decision(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        decision_patch = payload.get("decision_patch") or payload.get("decision")
        if decision_patch is None:
            decision_patch = {
                key: value
                for key, value in payload.items()
                if key not in {"session_id", "method_run_id"}
            }
        if not isinstance(decision_patch, dict):
            raise BridgeContractError(
                "ValidationError",
                "analysis.updateAcceptanceDecision requires payload.decision_patch to be an object.",
                details={"decision_patch_type": type(decision_patch).__name__},
            )
        return self._analysis_call(
            self._analysis_service.update_acceptance_decision,
            session_id,
            decision_patch,
        )

    def _analysis_confirm_review(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        decisions = payload.get("decisions")
        if decisions is None:
            decisions = payload.get("acceptance_decisions")
        if decisions is not None and not isinstance(decisions, (list, dict)):
            raise BridgeContractError(
                "ValidationError",
                "analysis.confirmReview requires payload.decisions to be a list when provided.",
                details={"decisions_type": type(decisions).__name__},
            )
        return self._analysis_call(
            self._analysis_service.confirm_review,
            session_id,
            decisions,
            reviewer=str(payload.get("reviewer") or ""),
            note=str(payload.get("note") or ""),
        )

    def _analysis_finalize_mtda(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        output_path = payload.get("output_path") or payload.get("path")
        return self._analysis_call(
            self._analysis_service.finalize_mtda,
            session_id,
            reviewer=str(payload.get("reviewer") or ""),
            note=str(payload.get("note") or ""),
            reason_kind=str(payload.get("reason_kind") or payload.get("reasonKind") or ""),
            output_path=str(output_path) if output_path else None,
        )

    def _analysis_apply_report_amendments(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        report_overrides = payload.get("report_overrides")
        if report_overrides is None:
            report_overrides = payload.get("overrides")
        if report_overrides is None:
            report_overrides = payload.get("records")
        if not isinstance(report_overrides, list) or not report_overrides:
            raise BridgeContractError(
                "ValidationError",
                "analysis.applyReportAmendments requires a non-empty payload.report_overrides list.",
                details={"report_overrides_type": type(report_overrides).__name__},
            )
        output_path = payload.get("output_path") or payload.get("path")
        return self._analysis_call(
            self._analysis_service.apply_report_amendments,
            session_id,
            report_overrides,
            reviewer=str(payload.get("reviewer") or ""),
            reason=str(payload.get("reason") or payload.get("note") or ""),
            output_path=str(output_path) if output_path else None,
        )

    def _analysis_copy_output_path(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        return self._analysis_call(
            self._analysis_service.copy_output_path,
            session_id,
        )

    def _analysis_open_artifact(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or context.get("session_id") or "")
        artifact_kind = payload.get("artifact_kind") or payload.get("kind") or payload.get("id") or payload.get("title")
        data = self._analysis_call(
            self._analysis_service.open_artifact,
            session_id,
            str(artifact_kind or ""),
        )
        should_open = bool(payload.get("open", True))
        if should_open and self.dialog_service is not None and hasattr(self.dialog_service, "open_artifact_path"):
            data["opened"] = bool(
                self.dialog_service.open_artifact_path(
                    str(data.get("path") or data.get("target_path") or ""),
                    artifact_kind=str(data.get("kind") or artifact_kind or ""),
                )
            )
        return data

    def _analysis_call(self, func: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except self._analysis_error_type as exc:
            raise BridgeContractError(
                exc.error_type,
                str(exc),
                recoverable=exc.recoverable,
                details=exc.details,
            ) from exc

    def _method_editor_call(self, func: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except self._method_editor_error_type as exc:
            raise BridgeContractError(
                exc.error_type,
                str(exc),
                recoverable=exc.recoverable,
                details=exc.details,
            ) from exc

    def _packaging_call(self, func: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except self._packaging_error_type as exc:
            raise BridgeContractError(
                exc.error_type,
                str(exc),
                recoverable=exc.recoverable,
                details=exc.details,
            ) from exc

    def _record(
        self,
        request_id: str,
        namespace: str,
        command: str,
        session_id: Any,
        status: str,
        *,
        duration_ms: float | None = None,
        error_type: str | None = None,
    ) -> None:
        record = {
            "timestamp": round(time.time(), 3),
            "id": request_id,
            "namespace": namespace,
            "command": command,
            "session_id": session_id,
            "status": status,
        }
        if duration_ms is not None:
            record["duration_ms"] = duration_ms
        if error_type:
            record["error_type"] = error_type
        self.event_log.append(record)
        self._write_persistent_record(record)

    def _write_persistent_record(self, record: dict[str, Any]) -> None:
        if self.log_path is None:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(_json_safe(record), sort_keys=True) + "\n")
        except OSError as exc:
            record["log_write_error"] = exc.__class__.__name__

    def _error_response(
        self,
        error_type: str,
        message: str,
        *,
        request_id: str | None = None,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "status": "error",
            "error_type": error_type,
            "message": message,
            "recoverable": recoverable,
            "details": _json_safe(details or {}),
        }
        if request_id is not None:
            response["id"] = request_id
        return response

    def _response_json(self, response: dict[str, Any]) -> str:
        return json.dumps(_json_safe(response), sort_keys=True)


def _find_backend_root(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    here = Path(__file__).resolve()
    candidates.extend([here.parent, *here.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents])

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "config" / "method_registry.yaml").exists() and (candidate / "src").is_dir():
            return candidate
    raise BridgeContractError(
        "SetupError",
        "Could not locate backend root containing config/method_registry.yaml and src/.",
        recoverable=False,
    )


def _generated_methods_root(backend_root: Path) -> Path:
    try:
        from runtime.resources import default_resolver

        return default_resolver().method_packages_root() / "generated"
    except Exception:
        return backend_root / "src" / "methods" / "generated"


def _duration_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def _positive_int(value: Any, *, default: int, upper: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(1, min(upper, number))


def _resolve_bridge_path(value: Any, backend_root: Path) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = backend_root / path
    return path.resolve()


def _discover_recent_analysis_packages(roots: list[Path], *, limit: int) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for package_path in root.rglob("*"):
            if not package_path.is_file() or package_path.suffix.lower() != ".mtdp":
                continue
            resolved = package_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                stat = resolved.stat()
            except OSError:
                continue
            modified = time.localtime(stat.st_mtime)
            rows.append(
                {
                    "name": resolved.name,
                    "path": str(resolved),
                    "parent": str(resolved.parent),
                    "extension": resolved.suffix.lower(),
                    "kind": "MTDP package",
                    "modified_timestamp": stat.st_mtime,
                    "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", modified),
                    "modified_label": time.strftime("%Y-%m-%d %H:%M", modified),
                    "size_bytes": stat.st_size,
                }
            )
    rows.sort(key=lambda item: (float(item["modified_timestamp"]), item["path"]), reverse=True)
    return rows[:limit]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)
