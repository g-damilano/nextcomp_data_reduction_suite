from __future__ import annotations

import time
import uuid
import shutil
import tempfile
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from threading import RLock
from typing import Any

from archives.core.layouts import MTDAAlignedLayout
from mapping import normalize_mapping_profile, write_mapping_profile
from operations.core.operation_context import OperationCancelled
from methods.core.method_run_service import MethodRunRequest, MethodRunService, load_mapping
from mtda_finalization import AmendmentRequest, MTDAFinalizationService
from reporting.completion.report_override import normalize_report_overrides
from ui.method_run_wizard.service_adapter import EXECUTION_PHASES, summarize_service_result
from ui.method_run_wizard.method_registry import MethodRegistry
from ui.method_run_wizard.view_models.mapping_preview import mapping_preview_view_model
from ui.method_run_wizard.view_models.package_preview import package_preview_view_model


class AnalysisSessionError(Exception):
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


class AnalysisRunCancelled(Exception):
    def __init__(self, phase: str, message: str = "Method run cancelled by operator.") -> None:
        super().__init__(message)
        self.phase = phase
        self.message = message


@dataclass(slots=True)
class AnalysisSession:
    session_id: str
    created_at: float
    package_path: Path | None = None
    package_preview: dict[str, Any] | None = None
    output_path: Path | None = None
    selected_method_id: str | None = None
    method_summary: dict[str, Any] | None = None
    mapping_summary: dict[str, Any] | None = None
    mapping_confirmed: bool = False
    readiness_report: dict[str, Any] | None = None
    run_state: dict[str, Any] | None = None
    acceptance_decisions: dict[str, Any] | None = None
    review_state: dict[str, Any] | None = None
    finalization_state: dict[str, Any] | None = None
    report_amendment_state: dict[str, Any] | None = None
    messages: list[str] | None = None


class AnalysisSessionService:
    """Read-only analysis setup facade for the React/PySide bridge."""

    def __init__(
        self,
        *,
        method_run_service: MethodRunService | None = None,
        registry: MethodRegistry | None = None,
    ) -> None:
        self.method_run_service = method_run_service or MethodRunService()
        self.registry = registry or MethodRegistry.load()
        self._sessions: dict[str, AnalysisSession] = {}
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analysis-run")
        self._futures: dict[str, Future[Any]] = {}

    def create_session(self, initial_package_path: str | Path | None = None) -> dict[str, Any]:
        session = AnalysisSession(
            session_id=f"analysis-{uuid.uuid4()}",
            created_at=time.time(),
            messages=[],
        )
        self._sessions[session.session_id] = session
        if initial_package_path:
            self._load_package_into_session(session, initial_package_path)
        return self._view_model(session)

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._view_model(self._require_session(session_id))

    def get_events(self, session_id: str, cursor: int | str | None = 0, limit: int | str | None = 200) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = session.run_state
        events = list((run_state or {}).get("events") or [])
        start = _bounded_int(cursor, default=0, lower=0, upper=len(events))
        max_count = _bounded_int(limit, default=200, lower=1, upper=500)
        selected = [dict(event) for event in events[start : start + max_count] if isinstance(event, dict)]
        next_cursor = start + len(selected)
        return {
            "schema_id": "gui_bridge.analysis_events.v0_1",
            "session_id": session.session_id,
            "run_id": (run_state or {}).get("run_id"),
            "cursor": start,
            "next_cursor": next_cursor,
            "event_count": len(events),
            "events": selected,
            "has_more": next_cursor < len(events),
        }

    def load_package(self, session_id: str, path: str | Path) -> dict[str, Any]:
        session = self._require_session(session_id)
        self._load_package_into_session(session, path)
        return self._view_model(session)

    def list_methods(self) -> dict[str, Any]:
        methods = [entry.to_dict() for entry in self.registry.active_entries()]
        return {
            "methods": methods,
            "count": len(methods),
            "registry_path": str(self.registry.path),
            "source": "MethodRegistry.active_entries",
        }

    def select_method(self, session_id: str, method_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.package_preview:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.selectMethod requires a loaded package.",
                details={"session_id": session_id},
            )
        if not method_id:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.selectMethod requires payload.method_id.",
                details={"session_id": session_id},
            )
        entry = self._eligible_method_entry(session, method_id)
        session.selected_method_id = entry.method_id
        session.method_summary = self._method_summary(entry)
        session.mapping_summary = self._mapping_summary(entry, session)
        session.mapping_confirmed = False
        session.readiness_report = None
        session.run_state = None
        session.acceptance_decisions = None
        session.review_state = None
        session.finalization_state = None
        session.report_amendment_state = None
        session.messages = [
            *(session.messages or []),
            f"Selected method {entry.label}.",
        ]
        return self._view_model(session)

    def load_mapping(self, session_id: str, path: str | Path) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.method_summary:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.loadMapping requires a selected method.",
                details={"session_id": session_id},
            )
        mapping_path = _resolve_workspace_path(path, self.registry.path.parent.parent)
        if not mapping_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"Analysis mapping profile does not exist: {mapping_path}",
                details={"path": str(mapping_path)},
            )
        method_path = Path(str(session.method_summary.get("method_path") or ""))
        session.mapping_summary = self._mapping_summary_for_path(
            mapping_path,
            method_path=method_path,
            package_path=session.package_path,
        )
        session.mapping_confirmed = False
        session.readiness_report = None
        session.run_state = None
        session.acceptance_decisions = None
        session.review_state = None
        session.finalization_state = None
        session.report_amendment_state = None
        session.messages = [
            *(session.messages or []),
            f"Loaded mapping {mapping_path.name}.",
        ]
        return self._view_model(session)

    def confirm_mapping(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.mapping_summary:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.confirmMapping requires a selected mapping.",
                details={"session_id": session_id},
            )
        session.mapping_confirmed = True
        session.messages = [
            *(session.messages or []),
            f"Confirmed mapping {session.mapping_summary.get('mapping_name') or 'profile'}.",
        ]
        return self._view_model(session)

    def apply_mapping_patch(
        self,
        session_id: str,
        bindings: list[dict[str, Any]],
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        if not session.method_summary:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.applyMappingPatch requires a selected method.",
                details={"session_id": session_id},
            )
        if not session.mapping_summary or not session.mapping_summary.get("path"):
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.applyMappingPatch requires a selected mapping.",
                details={"session_id": session_id},
            )
        if not isinstance(bindings, list) or not bindings:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.applyMappingPatch requires a non-empty bindings list.",
                details={"session_id": session_id},
            )
        current_path = Path(str(session.mapping_summary["path"]))
        if not current_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"Selected mapping path does not exist: {current_path}",
                details={"path": str(current_path)},
            )
        payload = load_mapping(current_path)
        for binding in bindings:
            if isinstance(binding, dict):
                _apply_mapping_binding(payload, binding)
        target_path = Path(output_path).expanduser() if output_path else _default_edited_mapping_path(current_path)
        mapping_id = str(payload.get("mapping_id") or target_path.stem)
        if target_path != current_path and not mapping_id.endswith("_wizard_edit"):
            payload["mapping_id"] = f"{mapping_id}_wizard_edit"
        saved_path = write_mapping_profile(normalize_mapping_profile(payload), target_path)
        method_path = Path(str(session.method_summary.get("method_path") or ""))
        session.mapping_summary = self._mapping_summary_for_path(
            saved_path,
            method_path=method_path,
            package_path=session.package_path,
            method_id=session.selected_method_id,
        )
        session.mapping_confirmed = True
        session.readiness_report = None
        session.run_state = None
        session.acceptance_decisions = None
        session.review_state = None
        session.finalization_state = None
        session.report_amendment_state = None
        session.messages = [
            *(session.messages or []),
            f"Saved mapping edits to {saved_path.name}.",
        ]
        return self._view_model(session)

    def check_readiness(self, session_id: str, output_path: str | Path | None = None) -> dict[str, Any]:
        session = self._require_session(session_id)
        request = self._readiness_request(session, output_path=output_path)
        try:
            report = self.method_run_service.check_readiness(request)
        except Exception as exc:  # pragma: no cover - surfaced as bridge error.
            raise AnalysisSessionError(
                "ValidationError",
                f"Could not check readiness: {exc}",
                details={"session_id": session_id},
            ) from exc
        session.output_path = request.output_path
        session.readiness_report = report.to_dict()
        session.messages = [
            *(session.messages or []),
            f"Readiness check complete: {session.readiness_report.get('status')}.",
        ]
        return self._view_model(session)

    def start_run(
        self,
        session_id: str,
        output_path: str | Path | None = None,
        *,
        overwrite: bool = True,
        generate_workbench: bool = True,
        human_decisions: list[dict[str, Any]] | None = None,
        report_overrides: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        base_request = self._readiness_request(session, output_path=output_path)
        readiness_checker = getattr(self.method_run_service, "check_readiness", None)
        if callable(readiness_checker):
            try:
                report = readiness_checker(base_request)
            except Exception as exc:  # pragma: no cover - surfaced as bridge error.
                raise AnalysisSessionError(
                    "ValidationError",
                    f"Could not check readiness before method run: {exc}",
                    details={"session_id": session_id},
                ) from exc
            session.output_path = base_request.output_path
            session.readiness_report = report.to_dict()
            session.messages = [
                *(session.messages or []),
                f"Readiness check complete: {session.readiness_report.get('status')}.",
            ]
        else:
            session.output_path = base_request.output_path
        readiness_status = str((session.readiness_report or {}).get("status") or "")
        if readiness_status not in {"READY", "READY_WITH_WARNINGS"}:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.startRun requires a READY or READY_WITH_WARNINGS readiness state.",
                details={"session_id": session_id, "readiness_status": readiness_status or None},
            )
        if _run_is_active(session.run_state):
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.startRun cannot start while a run is already active.",
                details={"session_id": session_id, "run_id": (session.run_state or {}).get("run_id")},
            )
        request = MethodRunRequest(
            input_package_path=base_request.input_package_path,
            method_path=base_request.method_path,
            mapping_path=base_request.mapping_path,
            output_path=base_request.output_path,
            overwrite=bool(overwrite),
            generate_workbench=bool(generate_workbench),
            human_decisions=tuple(dict(item) for item in human_decisions or [] if isinstance(item, dict)),
            report_overrides=tuple(dict(item) for item in report_overrides or [] if isinstance(item, dict)),
        )
        if request.output_path.exists() and not request.overwrite:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.startRun output already exists. Choose a different output path or enable overwrite.",
                details={
                    "session_id": session_id,
                    "output_path": str(request.output_path),
                    "overwrite": False,
                },
            )
        run_id = f"run-{uuid.uuid4()}"
        session.output_path = request.output_path
        session.run_state = _new_run_state(run_id, request.output_path)
        session.acceptance_decisions = None
        session.review_state = None
        session.finalization_state = None
        session.report_amendment_state = None
        session.messages = [
            *(session.messages or []),
            f"Started method run {run_id}.",
        ]
        future = self._executor.submit(self._execute_run, session.session_id, run_id, request)
        self._futures[run_id] = future
        return self._view_model(session)

    def update_acceptance_decision(
        self,
        session_id: str,
        decision_patch: dict[str, Any],
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = _require_completed_run(session, "analysis.updateAcceptanceDecision")
        record = _normalize_acceptance_decision(decision_patch, run_state)
        with self._lock:
            session.acceptance_decisions = _merge_acceptance_record(
                session.acceptance_decisions,
                record,
                run_state,
            )
            session.review_state = _review_state_from_acceptance(
                session.acceptance_decisions,
                run_state,
                status="in_review",
            )
            _store_review_payload_on_run(run_state, session.acceptance_decisions, session.review_state)
            _append_run_event(
                run_state,
                session_id=session.session_id,
                event="reviewDecisionUpdated",
                data={
                    "task": "review",
                    "phase": "acceptance_review",
                    "status": "in_review",
                    "run_id": record["run_id"],
                    "final_included": record["final_included"],
                    "message": f"Acceptance decision updated for {record['run_id']}.",
                },
            )
            session.messages = [
                *(session.messages or []),
                f"Acceptance decision updated for {record['run_id']}.",
            ]
        return self._view_model(session)

    def confirm_review(
        self,
        session_id: str,
        decisions: Any = None,
        *,
        reviewer: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = _require_completed_run(session, "analysis.confirmReview")
        with self._lock:
            if decisions is None:
                payload = session.acceptance_decisions or _acceptance_decisions_payload([], run_state)
            else:
                records = [
                    _normalize_acceptance_decision(item, run_state)
                    for item in _decision_records(decisions, "analysis.confirmReview")
                ]
                payload = _acceptance_decisions_payload(records, run_state)
            missing_reasons = _missing_required_review_reasons(payload)
            if missing_reasons:
                raise AnalysisSessionError(
                    "ValidationError",
                    "analysis.confirmReview requires a reason for every kept run that the acceptance policy marked for removal.",
                    details={"run_ids": missing_reasons},
                )
            review_state = _review_state_from_acceptance(
                payload,
                run_state,
                status="confirmed",
                reviewer=reviewer,
                note=note,
            )
            session.acceptance_decisions = payload
            session.review_state = review_state
            _store_review_payload_on_run(run_state, payload, review_state)
            _append_run_event(
                run_state,
                session_id=session.session_id,
                event="reviewConfirmed",
                data={
                    "task": "review",
                    "phase": "acceptance_review",
                    "status": "confirmed",
                    "decision_count": review_state["decision_count"],
                    "override_count": review_state["override_count"],
                    "final_run_count": review_state["final_run_count"],
                    "message": "Acceptance review confirmed.",
                },
            )
            session.messages = [
                *(session.messages or []),
                f"Acceptance review confirmed: {review_state['final_run_count']} final run(s).",
            ]
        return self._view_model(session)

    def finalize_mtda(
        self,
        session_id: str,
        *,
        reviewer: str = "",
        note: str = "",
        reason_kind: str = "",
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = _require_completed_run(session, "analysis.finalizeMtda")
        note = note.strip()
        if not note:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.finalizeMtda requires a finalization note.",
                details={"session_id": session_id},
            )
        review_state = session.review_state or run_state.get("review")
        if not isinstance(review_state, dict) or str(review_state.get("status") or "") != "confirmed":
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.finalizeMtda requires a confirmed acceptance review.",
                details={"session_id": session_id, "review_status": (review_state or {}).get("status") if isinstance(review_state, dict) else None},
            )
        input_path = _session_output_path(session, run_state)
        if input_path is None:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.finalizeMtda requires an MTDA output path.",
                details={"session_id": session_id},
            )
        if not input_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"MTDA output path does not exist: {input_path}",
                details={"path": str(input_path)},
            )

        human_decisions = tuple(_human_decisions_for_finalization(session.acceptance_decisions))
        target_path = Path(output_path).expanduser() if output_path else _default_finalized_output_path(input_path)
        result = MTDAFinalizationService().finalize(
            input_path=input_path,
            output_path=target_path,
            request=AmendmentRequest(
                human_decisions=human_decisions,
                reviewer=reviewer.strip(),
                reason=note,
                reviewer_notes=(note,),
                source_surface="method_run_wizard.finalize_spotlight",
            ),
        )
        payload = _finalization_result_payload(
            result,
            reviewer=reviewer,
            note=note,
            reason_kind=reason_kind,
            human_decision_count=len(human_decisions),
        )
        with self._lock:
            session.finalization_state = payload
            run_state["finalization"] = payload
            if result.status != "finalized":
                raise AnalysisSessionError(
                    "ValidationError",
                    "analysis.finalizeMtda could not finalize the MTDA without a new run.",
                    details=payload,
                )
            assert result.output_path is not None
            session.output_path = result.output_path
            run_state["output_path"] = str(result.output_path)
            result_payload = run_state.get("result")
            if isinstance(result_payload, dict):
                result_payload["output_path"] = str(result.output_path)
                result_payload["mtda_path"] = str(result.output_path)
                result_payload["finalization"] = payload
            _append_run_event(
                run_state,
                session_id=session.session_id,
                event="mtdaFinalized",
                data={
                    "task": "finalization",
                    "phase": "finalize",
                    "status": "finalized",
                    "output_path": str(result.output_path),
                    "artifact_count": len(payload["artifacts_updated"]),
                    "human_decision_count": len(human_decisions),
                    "message": "MTDA finalized.",
                },
            )
            session.messages = [
                *(session.messages or []),
                f"MTDA finalized: {result.output_path.name}.",
            ]
        return self._view_model(session)

    def apply_report_amendments(
        self,
        session_id: str,
        report_overrides: list[dict[str, Any]],
        *,
        reviewer: str = "",
        reason: str = "",
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = _require_completed_run(session, "analysis.applyReportAmendments")
        normalized_overrides = _normalize_report_amendments(
            report_overrides,
            reviewer=reviewer,
            reason=reason,
            command="analysis.applyReportAmendments",
        )
        input_path = _session_output_path(session, run_state)
        if input_path is None:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.applyReportAmendments requires an MTDA output path.",
                details={"session_id": session_id},
            )
        if not input_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"MTDA output path does not exist: {input_path}",
                details={"path": str(input_path)},
            )

        reason_text = reason.strip() or _first_non_empty([row.get("reason") for row in normalized_overrides])
        target_path = Path(output_path).expanduser() if output_path else _default_finalized_output_path(input_path)
        result = MTDAFinalizationService().finalize(
            input_path=input_path,
            output_path=target_path,
            request=AmendmentRequest(
                report_overrides=tuple(normalized_overrides),
                reviewer=reviewer.strip(),
                reason=reason_text,
                reviewer_notes=(reason_text,),
                source_surface="method_run_wizard.report_completion_editor",
            ),
        )
        finalization_payload = _finalization_result_payload(
            result,
            reviewer=reviewer,
            note=reason_text,
            reason_kind="report_completion",
            human_decision_count=0,
            report_override_count=len(normalized_overrides),
        )
        report_payload = _report_amendment_payload(
            finalization_payload,
            report_overrides=normalized_overrides,
            reviewer=reviewer,
            reason=reason_text,
        )
        with self._lock:
            session.finalization_state = finalization_payload
            session.report_amendment_state = report_payload
            run_state["finalization"] = finalization_payload
            run_state["report_amendments"] = report_payload
            if result.status != "finalized":
                raise AnalysisSessionError(
                    "ValidationError",
                    "analysis.applyReportAmendments could not apply report-only amendments.",
                    details=report_payload,
                )
            assert result.output_path is not None
            session.output_path = result.output_path
            run_state["output_path"] = str(result.output_path)
            result_payload = run_state.get("result")
            if isinstance(result_payload, dict):
                result_payload["output_path"] = str(result.output_path)
                result_payload["mtda_path"] = str(result.output_path)
                result_payload["finalization"] = finalization_payload
                result_payload["report_amendments"] = report_payload
            _append_run_event(
                run_state,
                session_id=session.session_id,
                event="reportAmendmentsApplied",
                data={
                    "task": "finalization",
                    "phase": "report_completion",
                    "status": "finalized",
                    "output_path": str(result.output_path),
                    "override_count": len(normalized_overrides),
                    "field_keys": [str(row.get("field_key") or "") for row in normalized_overrides],
                    "message": "Report-only amendments applied.",
                },
            )
            session.messages = [
                *(session.messages or []),
                f"Report amendments applied: {len(normalized_overrides)} field(s).",
            ]
        return self._view_model(session)

    def copy_output_path(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        path = _session_output_path(session, session.run_state)
        if path is None:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.copyOutputPath requires an MTDA output path.",
                details={"session_id": session_id},
            )
        return {
            "schema_id": "gui_bridge.analysis_output_path.v0_1",
            "path": str(path),
            "output_path": str(path),
            "exists": path.exists(),
            "clipboard_owner": "frontend",
            "source": "analysis.session",
        }

    def open_artifact(self, session_id: str, artifact_kind: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        kind = _normalize_artifact_kind(artifact_kind)
        if not kind:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.openArtifact requires payload.artifact_kind.",
                details={"artifact_kind": artifact_kind},
            )
        path = _session_output_path(session, session.run_state)
        if path is None:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.openArtifact requires an MTDA output path.",
                details={"session_id": session_id, "artifact_kind": artifact_kind},
            )
        if kind == "output_folder":
            if not path.parent.exists():
                raise AnalysisSessionError(
                    "NotFound",
                    f"MTDA output folder does not exist: {path.parent}",
                    details={"path": str(path.parent), "artifact_kind": kind},
                )
            return _local_artifact_payload(kind, path.parent, artifact_kind=artifact_kind, source_path=path)
        if not path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"MTDA output path does not exist: {path}",
                details={"path": str(path), "artifact_kind": kind},
            )
        if kind == "open_mtda":
            browser_index = _extract_mtda_browser_index(path)
            if browser_index is None:
                raise AnalysisSessionError(
                    "ValidationError",
                    "MTDA output is not a readable archive with an index.html entry point.",
                    details={"path": str(path), "artifact_kind": kind},
                )
            return _local_artifact_payload(kind, browser_index, artifact_kind=artifact_kind, source_path=path, archive_member=MTDAAlignedLayout.index)
        if kind == "workbench":
            workbench = _run_result_value(session.run_state, "workbench_path")
            if workbench:
                workbench_path = Path(str(workbench))
                target = workbench_path / "index.html" if workbench_path.is_dir() else workbench_path
                if target.exists():
                    return _local_artifact_payload(kind, target, artifact_kind=artifact_kind, source_path=path)
        resolved = _resolve_archive_artifact(path, kind)
        if resolved is None:
            raise AnalysisSessionError(
                "NotFound",
                f"No generated artifact is available for {artifact_kind}.",
                details={"path": str(path), "artifact_kind": artifact_kind, "normalized_kind": kind},
            )
        target, archive_member = resolved
        return _local_artifact_payload(kind, target, artifact_kind=artifact_kind, source_path=path, archive_member=archive_member)

    def cancel_run(self, session_id: str) -> dict[str, Any]:
        session = self._require_session(session_id)
        run_state = session.run_state
        if not _run_is_active(run_state):
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.cancelRun requires an active run.",
                details={"session_id": session_id, "run_status": (run_state or {}).get("status")},
            )
        assert run_state is not None
        with self._lock:
            run_state["cancel_requested"] = True
            run_state["status"] = "cancelling"
            run_state["message"] = "Cancellation requested by operator."
            _append_run_event(
                run_state,
                session_id=session.session_id,
                event="cancelRequested",
                data={
                    "task": "execution",
                    "phase": run_state.get("phase") or "execution",
                    "status": "cancelling",
                    "message": "Cancellation requested by operator.",
                },
            )
            session.messages = [
                *(session.messages or []),
                "Cancellation requested for active method run.",
            ]
        return self._view_model(session)

    def _execute_run(self, session_id: str, run_id: str, request: MethodRunRequest) -> None:
        def _cancel_requested() -> bool:
            session = self._sessions.get(session_id)
            run_state = session.run_state if session else None
            return bool(run_state and run_state.get("cancel_requested"))
        try:
            result = self.method_run_service.run(
                request,
                progress_callback=lambda event: self._record_run_progress(session_id, run_id, event),
                cancel_requested=_cancel_requested,
            )
        except AnalysisRunCancelled as exc:
            with self._lock:
                session = self._sessions.get(session_id)
                run_state = session.run_state if session else None
                if run_state is None or run_state.get("run_id") != run_id:
                    return
                run_state.update(
                    {
                        "status": "cancelled",
                        "phase": exc.phase or run_state.get("phase") or "execution",
                        "message": exc.message,
                        "completed_at": time.time(),
                    }
                )
                _append_run_event(
                    run_state,
                    session_id=session_id,
                    event="cancelled",
                    data={
                        "task": "execution",
                        "phase": run_state["phase"],
                        "status": "cancelled",
                        "message": exc.message,
                    },
                )
                if session:
                    session.messages = [*(session.messages or []), exc.message]
            return
        except OperationCancelled as exc:
            with self._lock:
                session = self._sessions.get(session_id)
                run_state = session.run_state if session else None
                if run_state is None or run_state.get("run_id") != run_id:
                    return
                message = str(exc) or "Method run cancelled by operator."
                run_state.update(
                    {
                        "status": "cancelled",
                        "phase": run_state.get("phase") or "execution",
                        "message": message,
                        "completed_at": time.time(),
                    }
                )
                _append_run_event(
                    run_state,
                    session_id=session_id,
                    event="cancelled",
                    data={
                        "task": "execution",
                        "phase": run_state["phase"],
                        "status": "cancelled",
                        "message": message,
                    },
                )
                if session:
                    session.messages = [*(session.messages or []), message]
            return
        except Exception as exc:  # pragma: no cover - bridge surfaces structured run failure.
            with self._lock:
                session = self._sessions.get(session_id)
                run_state = session.run_state if session else None
                if run_state is None or run_state.get("run_id") != run_id:
                    return
                run_state.update(
                    {
                        "status": "failed",
                        "phase": run_state.get("phase") or "execution",
                        "message": str(exc),
                        "completed_at": time.time(),
                        "errors": [str(exc)],
                    }
                )
                _append_run_event(
                    run_state,
                    session_id=session_id,
                    event="runFailed",
                    data={"task": "execution", "phase": run_state["phase"], "status": "failed", "message": str(exc)},
                )
            return

        result_payload = summarize_service_result(result)
        with self._lock:
            session = self._sessions.get(session_id)
            run_state = session.run_state if session else None
            if run_state is None or run_state.get("run_id") != run_id:
                return
            if run_state.get("cancel_requested"):
                run_state.update(
                    {
                        "status": "cancelled",
                        "phase": "complete",
                        "message": "Method run cancelled by operator.",
                        "completed_at": time.time(),
                    }
                )
                _append_run_event(
                    run_state,
                    session_id=session_id,
                    event="cancelled",
                    data={"task": "execution", "phase": "complete", "status": "cancelled", "message": run_state["message"]},
                )
                return
            status = "completed" if result_payload.get("status") == "completed" else "failed"
            run_state.update(
                {
                    "status": status,
                    "phase": "complete",
                    "message": "Method run complete" if status == "completed" else "Method run failed",
                    "completed_at": time.time(),
                    "progress_current": len(EXECUTION_PHASES),
                    "progress_total": len(EXECUTION_PHASES),
                    "progress_percent": 100 if status == "completed" else run_state.get("progress_percent", 0),
                    "output_path": result_payload.get("output_path") or str(request.output_path),
                    "result": result_payload,
                    "warnings": result_payload.get("warnings") or [],
                    "errors": result_payload.get("errors") or [],
                }
            )
            if session:
                session.output_path = Path(str(run_state["output_path"])) if run_state.get("output_path") else request.output_path
                if status == "completed":
                    session.messages = [*(session.messages or []), f"Method run complete: {Path(str(session.output_path)).name}."]
                else:
                    session.messages = [*(session.messages or []), "Method run failed."]
            _append_run_event(
                run_state,
                session_id=session_id,
                event="runCompleted" if status == "completed" else "runFailed",
                data={"task": "execution", "phase": "complete", "status": status, "message": run_state["message"]},
            )

    def _record_run_progress(self, session_id: str, run_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            run_state = session.run_state if session else None
            if run_state is None or run_state.get("run_id") != run_id:
                return
            phase = str(event.get("phase") or run_state.get("phase") or "execution")
            if run_state.get("cancel_requested"):
                raise AnalysisRunCancelled(phase)
            progress_current = int(event.get("progress_current") or _execution_phase_index(phase))
            progress_total = int(event.get("progress_total") or len(EXECUTION_PHASES))
            message = str(event.get("message") or phase.replace("_", " ").title())
            status = str(event.get("status") or "running")
            run_state.update(
                {
                    "status": "running",
                    "phase": phase,
                    "message": message,
                    "progress_current": progress_current,
                    "progress_total": progress_total,
                    "progress_percent": int(round((progress_current / max(progress_total, 1)) * 100)),
                }
            )
            runs = event.get("runs")
            if isinstance(runs, dict):
                run_state["run_status"] = {str(key): str(value) for key, value in runs.items()}
            _append_run_event(
                run_state,
                session_id=session_id,
                event="runProgress",
                data={
                    "task": "execution",
                    "phase": phase,
                    "status": status,
                    "message": message,
                    "progress_current": progress_current,
                    "progress_total": progress_total,
                    "progress_percent": run_state["progress_percent"],
                },
            )

    def _load_package_into_session(self, session: AnalysisSession, path: str | Path) -> None:
        package_path = Path(path).expanduser()
        if not package_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"Analysis package does not exist: {package_path}",
                details={"path": str(package_path)},
            )
        if package_path.suffix.lower() != ".mtdp":
            raise AnalysisSessionError(
                "ValidationError",
                f"Expected an .mtdp package, got: {package_path.name}",
                details={"path": str(package_path)},
            )
        try:
            preview = package_preview_view_model(self.method_run_service.load_package(package_path))
        except AnalysisSessionError:
            raise
        except Exception as exc:  # pragma: no cover - backend error message is validated at bridge boundary.
            raise AnalysisSessionError(
                "ValidationError",
                f"Could not load analysis package: {exc}",
                details={"path": str(package_path)},
            ) from exc
        session.package_path = package_path
        session.package_preview = preview
        session.output_path = _default_output_path(package_path)
        session.selected_method_id = None
        session.method_summary = None
        session.mapping_summary = None
        session.mapping_confirmed = False
        session.readiness_report = None
        session.run_state = None
        session.acceptance_decisions = None
        session.review_state = None
        session.finalization_state = None
        session.report_amendment_state = None
        session.messages = [f"Loaded package {package_path.name} for analysis."]

    def _eligible_method_entry(self, session: AnalysisSession, method_id: str) -> Any:
        entries = self._eligible_method_entries(session)
        for entry in entries:
            if entry.method_id == method_id:
                return entry
        raise AnalysisSessionError(
            "NotFound",
            f"Method is not available for the loaded package: {method_id}",
            details={
                "method_id": method_id,
                "eligible_method_ids": [entry.method_id for entry in entries],
            },
        )

    def _eligible_method_entries(self, session: AnalysisSession) -> list[Any]:
        analysis_type = ""
        if isinstance(session.package_preview, dict):
            analysis_type = str(
                session.package_preview.get("schema_id")
                or session.package_preview.get("analysis_type")
                or ""
            )
        return self.registry.defaults_for_analysis_type(analysis_type)

    def _method_summary(self, entry: Any) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "method_id": entry.method_id,
            "method_name": entry.label,
            "label": entry.label,
            "version": entry.version,
            "analysis_type": entry.analysis_type,
            "method_path": str(entry.method_path),
            "default_mapping_path": str(entry.default_mapping_path) if entry.default_mapping_path else None,
        }
        if not entry.method_path.exists():
            summary["load_error"] = f"Method path does not exist: {entry.method_path}"
            return summary
        try:
            result = self.method_run_service.load_method(entry.method_path)
        except Exception as exc:  # pragma: no cover - bridge tests cover structured response shape.
            summary["load_error"] = str(exc)
            return summary
        summary.update(
            {
                "method_id": result.method_id,
                "method_name": result.method_name,
                "label": result.method_name,
                "version": result.version,
                "analysis_type": result.analysis_type,
                "standard_reference": result.standard_reference,
                "method_path": str(result.path),
                "has_method_inputs": result.has_method_inputs,
                "expected_outputs": list(result.expected_outputs),
                "required_inputs": list(result.required_inputs),
                "recipe_steps": list(result.recipe_steps),
                "phases": list(result.phases),
                "limitations": list(result.limitations),
            }
        )
        return summary

    def _mapping_summary(self, entry: Any, session: AnalysisSession) -> dict[str, Any] | None:
        if entry.default_mapping_path is None:
            return None
        return self._mapping_summary_for_path(
            entry.default_mapping_path,
            method_path=entry.method_path,
            package_path=session.package_path,
            method_id=entry.method_id,
        )

    def _mapping_summary_for_path(
        self,
        path: Path,
        *,
        method_path: Path,
        package_path: Path | None,
        method_id: str | None = None,
    ) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "path": str(path),
            "mapping_name": path.name,
            "method_id": method_id or "",
        }
        if not path.exists():
            summary["load_error"] = f"Mapping path does not exist: {path}"
            return summary
        try:
            result = self.method_run_service.load_mapping(
                path,
                method_path=method_path,
                package_path=package_path,
            )
        except Exception as exc:  # pragma: no cover - surfaced through structured summary.
            summary["load_error"] = str(exc)
            return summary
        critical_mapped = int(result.summary.get("execution_critical_mapped", 0) or 0)
        critical_total = int(result.summary.get("execution_critical_total", 0) or 0)
        report_missing = int(result.summary.get("report_fields_missing", 0) or 0)
        summary.update(
            {
                "mapping_id": result.mapping_id,
                "method_id": result.method_id or entry.method_id,
                "status": result.status,
                "bound_count": critical_mapped,
                "critical_total": critical_total,
                "critical_missing_count": int(result.summary.get("execution_critical_missing", 0) or 0),
                "ambiguous_count": int(result.summary.get("ambiguous", 0) or 0),
                "report_mapped_count": int(result.summary.get("report_fields_mapped", 0) or 0),
                "report_total": int(result.summary.get("report_fields_total", 0) or 0),
                "missing_report_field_count": report_missing,
                "label": f"{result.path.name} · {critical_mapped}/{critical_total} critical inputs bound",
                "mapped_fields": list(result.mapped_fields),
                "preview": mapping_preview_view_model(result),
                "compatibility_status": str(
                    (result.compatibility_report.get("summary", {}) if isinstance(result.compatibility_report, dict) else {}).get("status")
                    or ""
                ),
            }
        )
        return summary

    def _readiness_request(
        self,
        session: AnalysisSession,
        *,
        output_path: str | Path | None = None,
    ) -> MethodRunRequest:
        if session.package_path is None or not session.package_preview:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.checkReadiness requires a loaded package.",
                details={"session_id": session.session_id},
            )
        if not session.method_summary:
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.checkReadiness requires a selected method.",
                details={"session_id": session.session_id},
            )
        if not session.mapping_summary or not session.mapping_summary.get("path"):
            raise AnalysisSessionError(
                "ValidationError",
                "analysis.checkReadiness requires a selected mapping.",
                details={"session_id": session.session_id},
            )
        method_path = Path(str(session.method_summary.get("method_path") or ""))
        mapping_path = Path(str(session.mapping_summary.get("path") or ""))
        if not method_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"Selected method path does not exist: {method_path}",
                details={"method_path": str(method_path)},
            )
        if not mapping_path.exists():
            raise AnalysisSessionError(
                "NotFound",
                f"Selected mapping path does not exist: {mapping_path}",
                details={"mapping_path": str(mapping_path)},
            )
        target_output = Path(output_path).expanduser() if output_path else session.output_path or _default_output_path(session.package_path)
        return MethodRunRequest(
            input_package_path=session.package_path,
            method_path=method_path,
            mapping_path=mapping_path,
            output_path=target_output,
            overwrite=True,
        )

    def _require_session(self, session_id: str) -> AnalysisSession:
        if not session_id:
            raise AnalysisSessionError("ValidationError", "analysis session_id is required.")
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise AnalysisSessionError(
                "NotFound",
                f"Unknown analysis session: {session_id}",
                details={"session_id": session_id},
            ) from exc

    def _view_model(self, session: AnalysisSession) -> dict[str, Any]:
        methods = self.list_methods()
        eligible_methods = [entry.to_dict() for entry in self._eligible_method_entries(session)]
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "status": "package_loaded" if session.package_preview else "empty",
            "package_path": str(session.package_path) if session.package_path else None,
            "output_path": str(session.output_path) if session.output_path else None,
            "package": session.package_preview,
            "methods": methods["methods"],
            "method_count": methods["count"],
            "eligible_methods": eligible_methods,
            "eligible_method_count": len(eligible_methods),
            "selected_method_id": session.selected_method_id,
            "selected_method": session.method_summary,
            "mapping": session.mapping_summary,
            "mapping_confirmed": session.mapping_confirmed,
            "readiness": session.readiness_report,
            "readiness_status": (session.readiness_report or {}).get("status") if session.readiness_report else None,
            "run_enabled": (session.readiness_report or {}).get("status") in {"READY", "READY_WITH_WARNINGS"} if session.readiness_report else False,
            "run": _run_view(session.run_state),
            "acceptance_decisions": dict(session.acceptance_decisions or {}) if session.acceptance_decisions else None,
            "review": dict(session.review_state or {}) if session.review_state else None,
            "finalization": dict(session.finalization_state or {}) if session.finalization_state else None,
            "report_amendments": dict(session.report_amendment_state or {}) if session.report_amendment_state else None,
            "messages": list(session.messages or []),
        }


def _default_output_path(package_path: Path) -> Path:
    return package_path.with_suffix(".mtda")


def _resolve_workspace_path(raw: str | Path, workspace_root: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute() or path.exists():
        return path
    return (workspace_root / path).resolve()


def _apply_mapping_binding(payload: dict[str, Any], binding: dict[str, Any]) -> None:
    source_role = _binding_source_role(binding)
    if not source_role:
        return
    mapped_source = str(binding.get("mapped_source") or binding.get("binding") or "").strip()
    status = str(binding.get("status") or "").casefold()
    if not mapped_source or status in {"unmapped", "missing", "fail", "clear"}:
        _remove_mapping_for_role(payload, source_role)
        return
    source_kind = str(binding.get("source_kind") or binding.get("kind") or "").casefold()
    section = "channels" if source_kind in {"channel", "channels"} else "fields"
    _remove_mapping_for_role(payload, source_role)
    target = payload.setdefault(section, {})
    if isinstance(target, dict):
        target[source_role] = mapped_source


def _binding_source_role(binding: dict[str, Any]) -> str:
    for key in ("source_role", "role"):
        value = str(binding.get(key) or "").strip()
        if value:
            return value
    backend_row = binding.get("backendRow") or binding.get("backend_row")
    if isinstance(backend_row, dict):
        value = str(backend_row.get("source_role") or "").strip()
        if value:
            return value
    method_field = str(binding.get("method_field") or binding.get("input") or "").strip()
    return method_field.rsplit(".", 1)[-1] if method_field else ""


def _remove_mapping_for_role(payload: dict[str, Any], source_role: str) -> None:
    for section in ("channels", "fields", "tokens"):
        values = payload.get(section)
        if isinstance(values, dict):
            values.pop(source_role, None)


def _default_edited_mapping_path(current_path: Path) -> Path:
    parent = current_path.parent
    stem = current_path.stem
    candidate = parent / f"{stem}_wizard_edit.json"
    suffix = 2
    while candidate.exists() and candidate != current_path:
        candidate = parent / f"{stem}_wizard_edit_{suffix}.json"
        suffix += 1
    return candidate


def _default_finalized_output_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.stem}_finalized{path.suffix}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_finalized_{index}{path.suffix}")
        index += 1
    return candidate


_ARTIFACT_SPECS: dict[str, dict[str, Any]] = {
    "test_report": {
        "prefix": "report",
        "preferred_names": ("test_report.html", "iso14126_report.html"),
        "member_candidates": (
            "dataset/04_reports/test_report.html",
            "report/test_report.html",
            "report/iso14126_report.html",
        ),
    },
    "audit_report": {
        "prefix": "audit",
        "preferred_names": ("audit_report.html", "index.html"),
        "member_candidates": (
            "dataset/04_reports/audit_report.html",
            "audit/audit_report.html",
            "interactive_report/index.html",
        ),
    },
    "workbench": {
        "prefix": "workbench",
        "preferred_names": ("index.html",),
        "member_candidates": ("workbench/index.html",),
    },
}


def _normalize_artifact_kind(value: str) -> str:
    key = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "test": "test_report",
        "test_report": "test_report",
        "open_test_report": "test_report",
        "audit": "audit_report",
        "audit_report": "audit_report",
        "open_audit_report": "audit_report",
        "browser": "open_mtda",
        "mtda_browser": "open_mtda",
        "archive_browser": "open_mtda",
        "workbench": "workbench",
        "folder": "output_folder",
        "output_folder": "output_folder",
        "open_output_folder": "output_folder",
        "mtda": "open_mtda",
        "open_mtda": "open_mtda",
        "open_mtda_in_reader": "open_mtda",
    }
    return aliases.get(key, key if key in {"test_report", "audit_report", "workbench", "output_folder", "open_mtda"} else "")


def _extract_mtda_browser_index(path: Path) -> Path | None:
    target = _extract_archive_prefix(path, "", target_key="mtda_browser")
    if target is None:
        return None
    index = target / MTDAAlignedLayout.index
    return index if index.exists() else None


def _resolve_archive_artifact(path: Path, kind: str) -> tuple[Path, str | None] | None:
    spec = _ARTIFACT_SPECS.get(kind)
    if not spec:
        return None
    for member in spec["member_candidates"]:
        candidate = _extract_archive_member_group(path, kind, str(member))
        if candidate is not None and candidate.exists():
            return candidate, str(member)
    target = _extract_archive_prefix(path, str(spec["prefix"]), target_key=kind)
    if target is None:
        return None
    for name in spec["preferred_names"]:
        candidate = target / str(name)
        if candidate.exists():
            return candidate, f"{spec['prefix']}/{name}"
    html_files = sorted(target.glob("*.html"))
    if html_files:
        return html_files[0], None
    return None


def _extract_archive_prefix(path: Path, prefix: str, *, target_key: str) -> Path | None:
    target = Path(tempfile.gettempdir()) / f"compression_module_{target_key}" / path.stem
    try:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            normalized_prefix = str(prefix).strip("/")
            member_prefix = f"{normalized_prefix}/" if normalized_prefix else ""
            for member in archive.namelist():
                if member.endswith("/") or (member_prefix and not member.startswith(member_prefix)):
                    continue
                relative = PurePosixPath(member[len(member_prefix):] if member_prefix else member)
                if not _safe_archive_relative_path(relative):
                    continue
                destination = target.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
    except (OSError, zipfile.BadZipFile):
        return None
    return target


def _extract_archive_member_group(path: Path, target_key: str, member: str) -> Path | None:
    target = Path(tempfile.gettempdir()) / f"compression_module_{target_key}" / path.stem
    member_path = PurePosixPath(member)
    member_parent = str(member_path.parent)
    member_prefix = "" if member_parent == "." else f"{member_parent}/"
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if member not in names:
                return None
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                if name.endswith("/") or not name.startswith(member_prefix):
                    continue
                relative_name = name[len(member_prefix):] if member_prefix else name
                relative = PurePosixPath(relative_name)
                if not _safe_archive_relative_path(relative):
                    continue
                destination = target.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, destination.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
    except (OSError, zipfile.BadZipFile):
        return None
    candidate = target.joinpath(*PurePosixPath(member_path.name).parts)
    return candidate if candidate.exists() else None


def _mtda_zip_view_path(path: Path) -> Path | None:
    if not zipfile.is_zipfile(path):
        return None
    target = Path(tempfile.gettempdir()) / "compression_module_mtda_zip_view" / path.stem / f"{path.name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        try:
            target.chmod(0o666)
        except OSError:
            pass
        target.unlink()
    shutil.copy2(path, target)
    try:
        target.chmod(0o444)
    except OSError:
        pass
    return target


def _safe_archive_relative_path(path: PurePosixPath) -> bool:
    return bool(path.parts) and all(part not in {"", ".", ".."} for part in path.parts)


def _local_artifact_payload(
    kind: str,
    path: Path,
    *,
    artifact_kind: str,
    source_path: Path,
    archive_member: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_id": "gui_bridge.analysis_artifact.v0_1",
        "artifact_kind": artifact_kind,
        "kind": kind,
        "path": str(path),
        "target_path": str(path),
        "source_path": str(source_path),
        "archive_member": archive_member,
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "open_owner": "host",
        "opened": False,
    }


def _new_run_state(run_id: str, output_path: Path) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": "running",
        "phase": "queued",
        "message": "Method run queued.",
        "started_at": time.time(),
        "completed_at": None,
        "output_path": str(output_path),
        "progress_current": 0,
        "progress_total": len(EXECUTION_PHASES),
        "progress_percent": 0,
        "run_status": {},
        "events": [],
        "warnings": [],
        "errors": [],
        "result": None,
        "cancel_requested": False,
    }


def _run_view(run_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if run_state is None:
        return None
    view = dict(run_state)
    view["events"] = list(run_state.get("events") or [])
    view["warnings"] = list(run_state.get("warnings") or [])
    view["errors"] = list(run_state.get("errors") or [])
    view["run_status"] = dict(run_state.get("run_status") or {})
    result = run_state.get("result")
    if isinstance(result, dict):
        result_view = dict(result)
        review_rows = _analysis_review_rows_payload(run_state, result_view)
        if review_rows:
            result_view["review_rows"] = review_rows
        view["result"] = result_view
    view.pop("cancel_requested", None)
    return view


def _analysis_review_rows_payload(run_state: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    report = result.get("acceptance_report")
    if not isinstance(report, dict):
        return []
    try:
        from ui.method_run_wizard.controller import (  # noqa: PLC0415
            _review_evidence_from_mtda,
            _row_models_from_acceptance_report,
        )
    except Exception:
        return []
    evidence_by_run: dict[str, dict[str, Any]] = {}
    path_value = result.get("output_path") or result.get("mtda_path") or run_state.get("output_path")
    path = Path(str(path_value)) if path_value else None
    if path is not None and path.exists():
        try:
            evidence_by_run = _review_evidence_from_mtda(path)
        except Exception:
            evidence_by_run = {}
    try:
        models = _row_models_from_acceptance_report(report, evidence_by_run=evidence_by_run)
    except Exception:
        return []
    payloads: list[dict[str, Any]] = []
    for model in models:
        try:
            payloads.append(_analysis_review_model_payload(model))
        except Exception:
            continue
    return payloads


def _analysis_review_model_payload(model: Any) -> dict[str, Any]:
    bending_assessment_window = list(getattr(model, "bending_assessment_window", (None, None)))

    def _as_float_values(values: list[Any]) -> list[float]:
        items: list[float] = []
        for value in values:
            try:
                items.append(float(value))
            except (TypeError, ValueError):
                continue
        return items
    has_bending_evidence = bool(
        getattr(model, "has_bending_evidence", False)
        or getattr(model, "bending_trace_points", ())
        or getattr(model, "bending_series", ())
        or getattr(model, "bending_peak", None) is not None
        or getattr(model, "bending_points_above_threshold", None) is not None
        or getattr(model, "bending_threshold", None) is not None
    )
    return {
        "run_id": str(getattr(model, "run_id", "")),
        "default_call": str(getattr(model, "default_call", "") or "Remove"),
        "reason": str(getattr(model, "reason", "") or "Acceptance flag requires review"),
        "is_excluded": bool(getattr(model, "is_excluded", False)),
        "defect_labels": [str(item) for item in getattr(model, "defect_labels", [])],
        "narrative_html": str(getattr(model, "narrative_html", "") or ""),
        "acceptance_flags": [dict(item) for item in getattr(model, "acceptance_flags", []) if isinstance(item, dict)],
        "bending_trace_points": [
            dict(point)
            for point in getattr(model, "bending_trace_points", [])
            if isinstance(point, dict)
        ],
        "bending_series": _as_float_values([value for value in getattr(model, "bending_series", []) if value is not None]),
        "bending_threshold": getattr(model, "bending_threshold", None),
        "bending_peak": getattr(model, "bending_peak", None),
        "bending_assessment_window": bending_assessment_window,
        "bending_exceedance_segments": [
            dict(segment)
            for segment in getattr(model, "bending_exceedance_segments", [])
            if isinstance(segment, dict)
        ],
        "bending_points_above_threshold": getattr(model, "bending_points_above_threshold", None),
        "bending_assessed_points": getattr(model, "bending_assessed_points", None),
        "curve_family_points": [
            dict(point)
            for point in getattr(model, "curve_family_points", [])
            if isinstance(point, dict)
        ],
        "curve_family_reference_points": [
            dict(point)
            for point in getattr(model, "curve_family_reference_points", [])
            if isinstance(point, dict)
        ],
        "curve_family_focus_run_id": str(getattr(model, "curve_family_focus_run_id", "") or ""),
        "curve_family_metric": str(getattr(model, "curve_family_metric", "") or ""),
        "curve_family_value": getattr(model, "curve_family_value", None),
        "curve_family_threshold": getattr(model, "curve_family_threshold", None),
        "curve_family_rank": str(getattr(model, "curve_family_rank", "") or ""),
        "curve_family_classification": str(getattr(model, "curve_family_classification", "") or ""),
        "has_bending_evidence": has_bending_evidence,
        "cockpits": [
            _analysis_cockpit_payload(cockpit, model)
            for cockpit in getattr(model, "diagnostic_cockpits", [])
        ],
    }


def _analysis_cockpit_payload(cockpit: Any, model: Any) -> dict[str, Any]:
    plot_contract = getattr(cockpit, "plot_contract", None)
    plot_kind = str(getattr(plot_contract, "plot_kind", "") or "")
    kind = "bending" if plot_kind == "bending_evidence" else "curve_family" if plot_kind == "curve_family" else "diagnostic"
    cards = [
        {
            "key": str(getattr(card, "evidence_key", "")),
            "label": str(getattr(card, "label", "")),
            "value": str(getattr(card, "value", "")),
            "sub": str(getattr(card, "subtext", "")),
            "level": str(getattr(card, "level", "")),
            "state": str(getattr(card, "state", "")),
        }
        for card in getattr(cockpit, "cards", ())
    ]
    payload = {
        "kind": kind,
        "tab": "Bending" if kind == "bending" else "Curve shape" if kind == "curve_family" else "Diagnostic",
        "title": str(getattr(plot_contract, "title", "") or "Diagnostic evidence"),
        "view_id": str(getattr(cockpit, "view_id", "") or ""),
        "cards": cards,
        "plot": {
            "plot_kind": plot_kind,
            "title": str(getattr(plot_contract, "title", "") or ""),
            "x_axis_label": str(getattr(plot_contract, "x_axis_label", "") or ""),
            "y_axis_label": str(getattr(plot_contract, "y_axis_label", "") or ""),
            "required_layers": [str(item) for item in getattr(plot_contract, "required_layers", ())],
            "semantic_layers": [str(item) for item in getattr(plot_contract, "semantic_layers", ())],
            "missing_required_keys": [str(item) for item in getattr(plot_contract, "missing_required_keys", ())],
        },
    }
    if kind == "bending":
        payload["plot"].update(
            {
                "series": [float(value) for value in getattr(model, "bending_series", [])],
                "trace_points": [
                    dict(point)
                    for point in getattr(model, "bending_trace_points", [])
                    if isinstance(point, dict)
                ],
                "threshold": getattr(model, "bending_threshold", None),
                "peak": getattr(model, "bending_peak", None),
                "assessment_window": list(getattr(model, "bending_assessment_window", (None, None))),
                "exceedance_segments": [
                    dict(segment)
                    for segment in getattr(model, "bending_exceedance_segments", [])
                    if isinstance(segment, dict)
                ],
            }
        )
    elif kind == "curve_family":
        payload["plot"].update(
            {
                "points": [
                    dict(point)
                    for point in getattr(model, "curve_family_points", [])
                    if isinstance(point, dict)
                ],
                "reference_points": [
                    dict(point)
                    for point in getattr(model, "curve_family_reference_points", [])
                    if isinstance(point, dict)
                ],
                "focus_run_id": str(getattr(model, "curve_family_focus_run_id", "") or getattr(model, "run_id", "")),
            }
        )
    return payload


def _run_is_active(run_state: dict[str, Any] | None) -> bool:
    return bool(run_state and str(run_state.get("status") or "") in {"queued", "running", "cancelling"})


def _bounded_int(value: int | str | None, *, default: int, lower: int, upper: int) -> int:
    try:
        number = int(value) if value is not None else default
    except (TypeError, ValueError):
        number = default
    return max(lower, min(number, upper))


def _append_run_event(
    run_state: dict[str, Any],
    *,
    session_id: str,
    event: str,
    data: dict[str, Any],
) -> None:
    events = run_state.setdefault("events", [])
    if isinstance(events, list):
        events.append(
            {
                "event_id": f"evt-{uuid.uuid4()}",
                "namespace": "analysis",
                "event": event,
                "session_id": session_id,
                "run_id": run_state.get("run_id"),
                "created_at": time.time(),
                "data": data,
            }
        )
        del events[:-200]


def _execution_phase_index(phase: str) -> int:
    try:
        return EXECUTION_PHASES.index(phase) + 1
    except ValueError:
        return 1


def _require_completed_run(session: AnalysisSession, command: str) -> dict[str, Any]:
    run_state = session.run_state
    if not run_state or str(run_state.get("status") or "") != "completed":
        raise AnalysisSessionError(
            "ValidationError",
            f"{command} requires a completed method run.",
            details={"session_id": session.session_id, "run_status": (run_state or {}).get("status")},
        )
    return run_state


def _session_output_path(session: AnalysisSession, run_state: dict[str, Any] | None) -> Path | None:
    if session.output_path:
        return Path(session.output_path)
    if isinstance(run_state, dict):
        for value in (
            run_state.get("output_path"),
            (run_state.get("result") or {}).get("output_path") if isinstance(run_state.get("result"), dict) else None,
            (run_state.get("result") or {}).get("mtda_path") if isinstance(run_state.get("result"), dict) else None,
        ):
            if value:
                return Path(str(value))
    return None


def _run_result_value(run_state: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(run_state, dict):
        return None
    result = run_state.get("result")
    if isinstance(result, dict):
        value = result.get(key)
        if value not in (None, ""):
            return value
    return run_state.get(key)


def _human_decisions_for_finalization(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("human_decision_candidates")
    if isinstance(candidates, dict):
        decisions = candidates.get("decisions")
        if isinstance(decisions, list):
            return [dict(item) for item in decisions if isinstance(item, dict)]
    records = payload.get("acceptance_override_records")
    if not isinstance(records, list):
        return []
    return [_human_decision_candidate(record) for record in records if isinstance(record, dict) and str(record.get("reason") or "").strip()]


def _finalization_result_payload(
    result: Any,
    *,
    reviewer: str,
    note: str,
    reason_kind: str,
    human_decision_count: int,
    report_override_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_id": "gui_bridge.analysis_finalization.v0_1",
        "status": str(getattr(result, "status", "")),
        "input_path": str(getattr(result, "input_path", "")),
        "output_path": str(getattr(result, "output_path", "") or ""),
        "amendment_classes": [str(item) for item in getattr(result, "amendment_classes", ())],
        "artifacts_updated": [str(item) for item in getattr(result, "artifacts_updated", ())],
        "errors": [str(item) for item in getattr(result, "errors", ())],
        "new_run_required": bool(getattr(result, "new_run_required", False)),
        "reviewer": reviewer.strip(),
        "note": note,
        "reason_kind": reason_kind,
        "human_decision_count": human_decision_count,
        "report_override_count": report_override_count,
        "finalized_at": time.time(),
    }


def _normalize_report_amendments(
    payload: Any,
    *,
    reviewer: str,
    reason: str,
    command: str,
) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("overrides") or payload.get("records") or []
    if not isinstance(payload, list) or not payload:
        raise AnalysisSessionError(
            "ValidationError",
            f"{command} requires a non-empty payload.report_overrides list.",
            details={"report_overrides_type": type(payload).__name__},
        )
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise AnalysisSessionError(
                "ValidationError",
                f"{command} requires every report override to be an object.",
            )
        row = dict(item)
        if "value" not in row and "override_value" in row:
            row["value"] = row.get("override_value")
        if not str(row.get("reason") or "").strip() and reason.strip():
            row["reason"] = reason.strip()
        if not str(row.get("reviewer") or "").strip() and reviewer.strip():
            row["reviewer"] = reviewer.strip()
        row.setdefault("source_surface", "method_run_wizard.report_completion_editor")
        rows.append(row)
    try:
        return [override.to_dict() for override in normalize_report_overrides(rows)]
    except ValueError as exc:
        raise AnalysisSessionError(
            "ValidationError",
            str(exc),
            details={"command": command},
        ) from exc


def _report_amendment_payload(
    finalization_payload: dict[str, Any],
    *,
    report_overrides: list[dict[str, Any]],
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_id": "gui_bridge.analysis_report_amendments.v0_1",
        "status": finalization_payload.get("status"),
        "input_path": finalization_payload.get("input_path"),
        "output_path": finalization_payload.get("output_path"),
        "override_count": len(report_overrides),
        "field_keys": [str(row.get("field_key") or "") for row in report_overrides],
        "report_overrides": [dict(row) for row in report_overrides],
        "artifacts_updated": list(finalization_payload.get("artifacts_updated") or []),
        "errors": list(finalization_payload.get("errors") or []),
        "new_run_required": bool(finalization_payload.get("new_run_required")),
        "reviewer": reviewer.strip(),
        "reason": reason,
        "finalization": dict(finalization_payload),
        "applied_at": time.time(),
    }


def _first_non_empty(values: list[Any]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _decision_records(payload: Any, command: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("records") or payload.get("decisions") or []
    if not isinstance(payload, list):
        raise AnalysisSessionError(
            "ValidationError",
            f"{command} requires payload.decisions to be a list.",
            details={"decisions_type": type(payload).__name__},
        )
    records = [item for item in payload if isinstance(item, dict)]
    if len(records) != len(payload):
        raise AnalysisSessionError(
            "ValidationError",
            f"{command} requires every decision record to be an object.",
        )
    return records


def _normalize_acceptance_decision(payload: dict[str, Any], run_state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AnalysisSessionError(
            "ValidationError",
            "Acceptance decision payload must be an object.",
        )
    run_id = str(payload.get("run_id") or payload.get("run") or payload.get("specimen_id") or "").strip()
    if not run_id:
        raise AnalysisSessionError(
            "ValidationError",
            "Acceptance decision payload requires run_id.",
        )
    final_included = payload.get("final_included")
    raw_decision = str(payload.get("decision") or payload.get("decision_type") or "").strip().casefold()
    if final_included is None:
        final_included = raw_decision in {"keep", "include", "included", "accept", "accepted", "restore", "confirm"}
    else:
        final_included = _truthy(final_included)
    if raw_decision in {"keep", "include", "included", "accept", "accepted"}:
        decision_type = "keep"
    elif raw_decision == "restore":
        decision_type = "restore"
    elif raw_decision == "clear_override":
        decision_type = "clear_override"
    elif raw_decision in {"remove", "exclude", "excluded", "reject", "rejected"}:
        decision_type = "remove"
    else:
        decision_type = "keep" if final_included else "remove"
    default_included = payload.get("default_included")
    if default_included is None:
        default_call = str(payload.get("default_call") or payload.get("defaultCall") or "").strip().casefold()
        if default_call:
            default_included = default_call in {"keep", "include", "included", "accept", "accepted"}
        else:
            default_included = run_id in _default_selected_run_ids(run_state)
    else:
        default_included = _truthy(default_included)
    defects = payload.get("defects") or payload.get("flags") or []
    if not isinstance(defects, list):
        defects = [defects]
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return {
        "run_id": run_id,
        "decision_type": decision_type,
        "final_included": bool(final_included),
        "default_included": bool(default_included),
        "default_call": "Keep" if default_included else "Remove",
        "reason": str(payload.get("reason") or payload.get("override_reason") or "").strip(),
        "defects": [str(item) for item in defects if str(item).strip()],
        "reviewer": str(payload.get("reviewer") or "").strip(),
        "source_surface": str(payload.get("source_surface") or "method_run_wizard.review_spotlight"),
        "ui_context": str(payload.get("ui_context") or "analysis.review"),
        "metadata": metadata,
        "updated_at": time.time(),
    }


def _merge_acceptance_record(
    current: dict[str, Any] | None,
    record: dict[str, Any],
    run_state: dict[str, Any],
) -> dict[str, Any]:
    records = [
        dict(item)
        for item in (current or {}).get("records", [])
        if isinstance(item, dict) and str(item.get("run_id") or "") != record["run_id"]
    ]
    records.append(record)
    return _acceptance_decisions_payload(records, run_state)


def _acceptance_decisions_payload(records: list[dict[str, Any]], run_state: dict[str, Any]) -> dict[str, Any]:
    by_run: dict[str, dict[str, Any]] = {}
    for record in records:
        run_id = str(record.get("run_id") or "").strip()
        if run_id:
            normalized = dict(record)
            normalized.setdefault("default_included", run_id in _default_selected_run_ids(run_state))
            normalized.setdefault("default_call", "Keep" if normalized["default_included"] else "Remove")
            normalized.setdefault("updated_at", time.time())
            by_run[run_id] = normalized
    ordered = list(by_run.values())
    final_selected = set(_default_selected_run_ids(run_state))
    for record in ordered:
        if record.get("final_included"):
            final_selected.add(str(record["run_id"]))
        else:
            final_selected.discard(str(record["run_id"]))
    reasons = {
        str(record["run_id"]): str(record.get("reason") or "")
        for record in ordered
        if str(record.get("reason") or "").strip()
    }
    defects = {
        str(record["run_id"]): [str(item) for item in record.get("defects", []) if str(item).strip()]
        for record in ordered
    }
    overrides = [
        _review_record(record)
        for record in ordered
        if bool(record.get("final_included")) != bool(record.get("default_included"))
    ]
    replayable = [
        _human_decision_candidate(record)
        for record in overrides
        if str(record.get("reason") or "").strip()
    ]
    return {
        "schema_id": "gui_bridge.analysis_acceptance_decisions.v0_1",
        "method_run_id": run_state.get("run_id"),
        "selection_source": "human_review" if overrides else "machine_default_confirmed",
        "records": [_review_record(record) for record in ordered],
        "acceptance_keep": {str(record["run_id"]): bool(record.get("final_included")) for record in ordered},
        "acceptance_override_reason": reasons,
        "acceptance_override_defects": defects,
        "acceptance_override_records": overrides,
        "human_decision_candidates": {
            "schema_id": "method.human_acceptance_decisions.v0_1",
            "selection_source": "human_review" if replayable else "machine_default_confirmed",
            "decisions": replayable,
        },
        "human_decision_replay_warning_count": max(0, len(overrides) - len(replayable)),
        "default_selected_run_ids": sorted(_default_selected_run_ids(run_state)),
        "final_selected_run_ids": sorted(final_selected),
        "final_run_count": len(final_selected),
        "total_run_count": _total_acceptance_run_count(run_state, fallback=len(final_selected)),
        "updated_at": time.time(),
    }


def _review_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": str(record.get("run_id") or ""),
        "decision_type": str(record.get("decision_type") or ""),
        "final_included": bool(record.get("final_included")),
        "default_included": bool(record.get("default_included")),
        "default_call": str(record.get("default_call") or ("Keep" if record.get("default_included") else "Remove")),
        "reason": str(record.get("reason") or ""),
        "defects": [str(item) for item in record.get("defects", []) if str(item).strip()],
        "reviewer": str(record.get("reviewer") or ""),
        "source_surface": str(record.get("source_surface") or "method_run_wizard.review_spotlight"),
        "ui_context": str(record.get("ui_context") or "analysis.review"),
        "metadata": dict(record.get("metadata") or {}),
        "updated_at": record.get("updated_at") or time.time(),
    }


def _human_decision_candidate(record: dict[str, Any]) -> dict[str, Any]:
    decision_type = "keep" if record.get("final_included") else "remove"
    return {
        "run_id": str(record.get("run_id") or ""),
        "decision_type": decision_type,
        "reason": str(record.get("reason") or ""),
        "reviewer": str(record.get("reviewer") or ""),
        "source_surface": str(record.get("source_surface") or "method_run_wizard.review_spotlight"),
        "ui_context": str(record.get("ui_context") or "analysis.review"),
        "metadata": dict(record.get("metadata") or {}),
    }


def _review_state_from_acceptance(
    payload: dict[str, Any],
    run_state: dict[str, Any],
    *,
    status: str,
    reviewer: str = "",
    note: str = "",
) -> dict[str, Any]:
    overrides = payload.get("acceptance_override_records") if isinstance(payload, dict) else []
    records = payload.get("records") if isinstance(payload, dict) else []
    missing_reasons = _missing_required_review_reasons(payload)
    state = {
        "schema_id": "gui_bridge.analysis_review_state.v0_1",
        "status": status,
        "method_run_id": run_state.get("run_id"),
        "decision_count": len(records) if isinstance(records, list) else 0,
        "override_count": len(overrides) if isinstance(overrides, list) else 0,
        "missing_reason_count": len(missing_reasons),
        "missing_reason_run_ids": missing_reasons,
        "final_run_count": int(payload.get("final_run_count") or 0),
        "total_run_count": int(payload.get("total_run_count") or 0),
        "selection_source": payload.get("selection_source") or "machine_default_confirmed",
        "reviewer": reviewer,
        "note": note,
        "updated_at": time.time(),
    }
    if status == "confirmed":
        state["confirmed_at"] = state["updated_at"]
    return state


def _store_review_payload_on_run(
    run_state: dict[str, Any],
    payload: dict[str, Any],
    review_state: dict[str, Any],
) -> None:
    run_state["acceptance_decisions"] = payload
    run_state["review"] = review_state
    result = run_state.get("result")
    if isinstance(result, dict):
        result["acceptance_decisions"] = payload
        result["review"] = review_state


def _missing_required_review_reasons(payload: dict[str, Any]) -> list[str]:
    records = payload.get("records") if isinstance(payload, dict) else []
    if not isinstance(records, list):
        return []
    return [
        str(record.get("run_id") or "")
        for record in records
        if record.get("final_included") is True
        and record.get("default_included") is False
        and not str(record.get("reason") or "").strip()
    ]


def _default_selected_run_ids(run_state: dict[str, Any]) -> set[str]:
    result = run_state.get("result") if isinstance(run_state, dict) else {}
    report = result.get("acceptance_report") if isinstance(result, dict) else {}
    if not isinstance(report, dict):
        return set()
    default_selection = str(
        report.get("default_selection_set")
        or (report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}).get("default_selection_set")
        or ""
    )
    selection_sets = report.get("selection_sets")
    if not isinstance(selection_sets, dict):
        return set()
    for selection in selection_sets.get("selection_sets", []):
        if isinstance(selection, dict) and str(selection.get("selection_id") or "") == default_selection:
            return {str(run_id) for run_id in selection.get("run_ids", [])}
    return set()


def _total_acceptance_run_count(run_state: dict[str, Any], *, fallback: int = 0) -> int:
    result = run_state.get("result") if isinstance(run_state, dict) else {}
    report = result.get("acceptance_report") if isinstance(result, dict) else {}
    summary = report.get("summary") if isinstance(report, dict) else {}
    try:
        return int((summary or {}).get("total_runs") or fallback)
    except (TypeError, ValueError):
        return fallback


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "keep", "include", "included", "accept", "accepted"}
