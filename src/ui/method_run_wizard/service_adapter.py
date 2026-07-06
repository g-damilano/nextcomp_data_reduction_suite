from __future__ import annotations

import traceback as traceback_module
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from mtda_finalization import AmendmentRequest, MTDAFinalizationService
from methods.core.method_run_service import MethodRunRequest, MethodRunServiceResult
from methods.core.method_run_service import MethodRunService


READINESS_PHASES = ("load_input_package", "load_method_package", "load_mapping", "readiness_check")
EXECUTION_PHASES = (
    "load_input_package",
    "load_method_package",
    "load_mapping",
    "readiness_check",
    "method_resolve",
    "method_reduce",
    "validation",
    "acceptance",
    "write_mtda",
    "build_audit_report",
    "build_workbench_optional",
    "complete",
)


class MethodRunServiceQtAdapter:
    """Plain-data boundary between MethodRunService and the Qt wizard."""

    def request_to_payload(self, request: MethodRunRequest) -> dict[str, Any]:
        return {
            "input_package_path": str(request.input_package_path),
            "method_path": str(request.method_path),
            "mapping_path": str(request.mapping_path),
            "output_path": str(request.output_path),
            "overwrite": bool(request.overwrite),
            "generate_workbench": bool(request.generate_workbench),
            "human_decisions": _plain_data(request.human_decisions),
            "report_overrides": _plain_data(request.report_overrides),
        }

    def request_from_payload(self, payload: Mapping[str, Any]) -> MethodRunRequest:
        return MethodRunRequest(
            input_package_path=Path(str(payload["input_package_path"])),
            method_path=Path(str(payload["method_path"])),
            mapping_path=Path(str(payload["mapping_path"])),
            output_path=Path(str(payload["output_path"])),
            overwrite=bool(payload.get("overwrite", False)),
            generate_workbench=bool(payload.get("generate_workbench", False)),
            human_decisions=tuple(
                dict(item) for item in payload.get("human_decisions", ()) or () if isinstance(item, Mapping)
            ),
            report_overrides=tuple(
                dict(item) for item in payload.get("report_overrides", ()) or () if isinstance(item, Mapping)
            ),
        )

    def progress_event(
        self,
        *,
        task: str,
        phase: str,
        status: str,
        message: str,
        progress_current: int,
        progress_total: int,
    ) -> dict[str, Any]:
        return {
            "task": task,
            "phase": phase,
            "status": status,
            "message": message,
            "progress_current": progress_current,
            "progress_total": progress_total,
            "progress_percent": int(round((progress_current / max(progress_total, 1)) * 100)),
        }

    def readiness_payload(self, report: Any, *, message: str = "Readiness check complete") -> dict[str, Any]:
        readiness = _plain_data(report.to_dict() if hasattr(report, "to_dict") else report)
        return {
            "task": "readiness",
            "status": "completed",
            "phase": "readiness_check",
            "message": message,
            "readiness": readiness,
            "readiness_status": readiness.get("status") if isinstance(readiness, dict) else None,
        }

    def run_payload(self, result: MethodRunServiceResult | Mapping[str, Any], *, message: str = "Method run complete") -> dict[str, Any]:
        result_payload = summarize_service_result(result)
        return {
            "task": "execution",
            "status": result_payload.get("status", "completed"),
            "phase": "complete",
            "message": message,
            "result": result_payload,
        }

    def failure_payload(
        self,
        error: BaseException | str,
        *,
        task: str,
        phase: str,
        recoverable: bool = True,
        include_traceback: bool = False,
        result: MethodRunServiceResult | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(error, BaseException):
            error_type = type(error).__name__
            message = str(error)
            trace = traceback_module.format_exc() if include_traceback else None
        else:
            error_type = "MethodRunError"
            message = str(error)
            trace = None
        payload: dict[str, Any] = {
            "task": task,
            "status": "failed",
            "phase": phase,
            "error_type": error_type,
            "message": message,
            "recoverable": recoverable,
            "action": _recoverable_action(task, phase),
        }
        if trace:
            payload["traceback"] = trace
        if result is not None:
            payload["result"] = summarize_service_result(result)
        return payload

    def cancelled_payload(self, *, task: str, phase: str, message: str) -> dict[str, Any]:
        return {
            "task": task,
            "status": "cancelled",
            "phase": phase,
            "message": message,
            "recoverable": True,
        }


def summarize_service_result(result: MethodRunServiceResult | Mapping[str, Any]) -> dict[str, Any]:
    payload = _plain_data(result)
    if not isinstance(payload, dict):
        payload = {}
    output_path = payload.get("output_path")
    archive_members = payload.get("archive_members") or []
    return {
        "status": payload.get("status"),
        "readiness_status": payload.get("readiness_status"),
        "output_path": output_path,
        "mtda_path": output_path,
        "audit_report_path": payload.get("audit_report_path"),
        "workbench_path": payload.get("workbench_path"),
        "validation_summary": payload.get("validation_summary") or {},
        "acceptance_summary": payload.get("acceptance_summary") or {},
        "acceptance_report": payload.get("acceptance_report") or {},
        "readiness_summary": payload.get("readiness_summary") or {},
        "report_summary": payload.get("report_summary") or {},
        "report_override_count": (payload.get("report_summary") or {}).get("override_count", 0),
        "report_artifacts": list(payload.get("report_artifacts") or []),
        "warnings": payload.get("warnings") or [],
        "errors": payload.get("errors") or [],
        "archive_members": list(archive_members),
        "archive_member_count": len(archive_members),
        "artifacts": _artifact_rows(payload),
    }


def persist_acceptance(state: Any) -> dict[str, Any]:
    """Persist review decisions until the service owns this Prompt 9 hook."""
    keep = dict(getattr(state, "acceptance_keep", {}) or {})
    reasons = dict(getattr(state, "acceptance_override_reason", {}) or {})
    defects = {
        str(run_id): [str(label) for label in labels or [] if str(label).strip()]
        for run_id, labels in dict(getattr(state, "acceptance_override_defects", {}) or {}).items()
    }
    payload = {
        "acceptance_keep": keep,
        "acceptance_override_reason": reasons,
        "acceptance_override_defects": defects,
        "acceptance_override_records": [
            {
                "run_id": str(run_id),
                "final_included": bool(final_included),
                "reason": str(reasons.get(run_id) or ""),
                "defects": list(defects.get(str(run_id), ())),
            }
            for run_id, final_included in keep.items()
            if final_included is True
        ],
    }
    service_result = getattr(state, "service_result", None)
    if isinstance(service_result, dict):
        service_result["acceptance_decisions"] = payload
    return payload


def finalize_mtda(state: Any, *, reviewer: str, note: str) -> dict[str, Any]:
    path = _state_mtda_path(state)
    if path is None:
        return {"status": "failed", "errors": ["No MTDA output path is available."]}
    result = MTDAFinalizationService().finalize(
        input_path=path,
        output_path=_default_finalized_path(path),
        request=AmendmentRequest(
            reviewer=reviewer,
            reason=note,
            reviewer_notes=(note,),
            source_surface="method_run_wizard.finalize_spotlight",
        ),
    )
    payload = _plain_data(result)
    if isinstance(payload, dict) and result.output_path is not None:
        setattr(state, "output_path", result.output_path)
        service_result = getattr(state, "service_result", None)
        if isinstance(service_result, dict):
            service_result["output_path"] = str(result.output_path)
            service_result["mtda_path"] = str(result.output_path)
    return payload if isinstance(payload, dict) else {"status": str(payload)}


def run_method_async(
    state: Any,
    *,
    service: MethodRunService | None = None,
    parent: Any | None = None,
) -> Any | None:
    """Create and start a worker for a method run when all required paths are known."""
    from mtdp_enrichment.ui.qt_compat import QtCore

    input_package_path = getattr(state, "input_package_path", None)
    method_path = getattr(state, "method_path", None)
    mapping_path = getattr(state, "mapping_path", None)
    output_path = getattr(state, "output_path", None)
    if not (input_package_path and method_path and mapping_path and output_path):
        return None

    from ui.method_run_wizard.worker import MethodRunWorker

    request = MethodRunRequest(
        input_package_path=Path(input_package_path),
        method_path=Path(method_path),
        mapping_path=Path(mapping_path),
        output_path=Path(output_path),
        overwrite=True,
        generate_workbench=True,
        report_overrides=tuple(getattr(state, "report_overrides", ()) or ()),
    )
    thread = QtCore.QThread(parent)
    worker = MethodRunWorker(service=service or MethodRunService(), request=request, task="execution")
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    worker._thread = thread  # type: ignore[attr-defined]
    QtCore.QTimer.singleShot(0, thread.start)
    return worker


def check_readiness_async(
    state: Any,
    *,
    service: MethodRunService | None = None,
    parent: Any | None = None,
) -> Any | None:
    """Create and start a readiness worker when all required input paths are known."""
    from mtdp_enrichment.ui.qt_compat import QtCore

    input_package_path = getattr(state, "input_package_path", None)
    method_path = getattr(state, "method_path", None)
    mapping_path = getattr(state, "mapping_path", None)
    output_path = getattr(state, "output_path", None)
    if not (input_package_path and method_path and mapping_path and output_path):
        return None

    from ui.method_run_wizard.worker import MethodRunWorker

    request = MethodRunRequest(
        input_package_path=Path(input_package_path),
        method_path=Path(method_path),
        mapping_path=Path(mapping_path),
        output_path=Path(output_path),
        overwrite=True,
        generate_workbench=True,
        report_overrides=tuple(getattr(state, "report_overrides", ()) or ()),
    )
    thread = QtCore.QThread(parent)
    worker = MethodRunWorker(service=service or MethodRunService(), request=request, task="readiness")
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    worker._thread = thread  # type: ignore[attr-defined]
    QtCore.QTimer.singleShot(0, thread.start)
    return worker


def _state_mtda_path(state: Any) -> Path | None:
    output_path = getattr(state, "output_path", None)
    if output_path:
        return Path(output_path)
    service_result = getattr(state, "service_result", None)
    if isinstance(service_result, Mapping):
        value = service_result.get("mtda_path") or service_result.get("output_path")
        if value:
            return Path(str(value))
    return None


def _default_finalized_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.stem}_finalized{path.suffix}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_finalized_{index}{path.suffix}")
        index += 1
    return candidate


def _artifact_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if payload.get("output_path"):
        rows.append({"kind": "mtda", "path": payload["output_path"]})
    if payload.get("audit_report_path"):
        rows.append({"kind": "audit_report_member", "path": payload["audit_report_path"]})
    if payload.get("workbench_path"):
        rows.append({"kind": "workbench", "path": payload["workbench_path"]})
    for member in payload.get("report_artifacts") or []:
        rows.append({"kind": "report_member", "path": member})
    return rows


def _plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _plain_data(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain_data(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_data(item) for item in value]
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if hasattr(value, "to_dict"):
        return _plain_data(value.to_dict())
    return str(value)


def _recoverable_action(task: str, phase: str) -> str:
    if task == "readiness":
        return "Review the package, method, and mapping selections, then run readiness again."
    if phase == "write_mtda":
        return "Choose a different output path or enable overwrite, then run again."
    return "Review the error details and rerun after correcting the selected inputs."
