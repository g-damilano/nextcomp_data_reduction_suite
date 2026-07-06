from __future__ import annotations

import inspect
from typing import Any, Literal, Mapping

from mtdp_enrichment.ui.qt_compat import QtCore
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from ui.method_run_wizard.service_adapter import (
    EXECUTION_PHASES,
    READINESS_PHASES,
    MethodRunServiceQtAdapter,
)


WorkerTask = Literal["readiness", "execution"]


class MethodRunWorker(QtCore.QObject):
    """Runs backend method work and emits only plain payloads."""

    started = QtCore.pyqtSignal(dict)
    progress = QtCore.pyqtSignal(dict)
    log = QtCore.pyqtSignal(str)
    phase_changed = QtCore.pyqtSignal(str)
    run_status = QtCore.pyqtSignal(dict)
    log_line = QtCore.pyqtSignal(str)
    warning = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(dict)
    completed = QtCore.pyqtSignal(dict)
    cancelled = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        service: MethodRunService,
        request: MethodRunRequest | Mapping[str, Any],
        task: WorkerTask,
        include_traceback: bool = False,
        adapter: MethodRunServiceQtAdapter | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.adapter = adapter or MethodRunServiceQtAdapter()
        self.request_payload = (
            self.adapter.request_to_payload(request)
            if isinstance(request, MethodRunRequest)
            else dict(request)
        )
        self.task = task
        self.include_traceback = include_traceback
        self._cancel_requested = False
        self._current_phase = "readiness_check" if task == "readiness" else "load_input_package"

    def cancel(self) -> None:
        self._cancel_requested = True

    def request_cancel(self) -> None:
        self.cancel()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        phase = self._current_phase
        self.started.emit({"task": self.task, "status": "started", "phase": phase, "message": f"Starting {self.task}"})
        try:
            if self._cancel_requested:
                self.cancelled.emit(
                    self.adapter.cancelled_payload(task=self.task, phase=phase, message=f"Cancelled {self.task} before start")
                )
                return
            if self.task == "readiness":
                self._run_readiness()
            elif self.task == "execution":
                self._run_execution()
            else:
                raise ValueError(f"Unknown method-run task: {self.task}")
        except Exception as exc:  # pragma: no cover - exercised with fake service tests
            self.failed.emit(
                self.adapter.failure_payload(
                    exc,
                    task=self.task,
                    phase=self._current_phase or phase,
                    include_traceback=self.include_traceback,
                )
            )
        finally:
            self.finished.emit()

    def _request(self) -> MethodRunRequest:
        return self.adapter.request_from_payload(self.request_payload)

    def _run_readiness(self) -> None:
        request = self._request()
        self._emit_phase("readiness", "load_input_package", 1, len(READINESS_PHASES), "Loading MTDP package")
        self._emit_phase("readiness", "load_method_package", 2, len(READINESS_PHASES), "Loading method package")
        self._emit_phase("readiness", "load_mapping", 3, len(READINESS_PHASES), "Loading mapping profile")
        self._emit_phase("readiness", "readiness_check", 4, len(READINESS_PHASES), "Checking package readiness")
        report = self.service.check_readiness(request)
        if self._cancel_requested:
            self.cancelled.emit(
                self.adapter.cancelled_payload(task="readiness", phase="readiness_check", message="Cancelled readiness check")
            )
            return
        for message in getattr(report, "warnings", ()):
            self.warning.emit({"task": "readiness", "phase": "readiness_check", "message": str(message)})
        self.completed.emit(self.adapter.readiness_payload(report))

    def _run_execution(self) -> None:
        request = self._request()
        emits_service_progress = _accepts_progress_callback(self.service.run)
        if not emits_service_progress:
            service_start_index = EXECUTION_PHASES.index("method_resolve") + 1
            for index, phase in enumerate(EXECUTION_PHASES[:service_start_index], start=1):
                self._emit_phase("execution", phase, index, len(EXECUTION_PHASES), _phase_message(phase))
            result = self.service.run(request)
        else:
            result = self.service.run(request, progress_callback=self._service_progress)
        if self._cancel_requested:
            self.cancelled.emit(
                self.adapter.cancelled_payload(task="execution", phase="complete", message="Cancelled method execution")
            )
            return
        for message in getattr(result, "warnings", ()):
            self.warning.emit({"task": "execution", "phase": "complete", "message": str(message)})
        if getattr(result, "status", None) != "completed":
            errors = getattr(result, "errors", ()) or ()
            self.failed.emit(
                self.adapter.failure_payload(
                    "; ".join(str(error) for error in errors) or f"Method run ended with status {getattr(result, 'status', 'unknown')}",
                    task="execution",
                    phase="complete",
                    result=result,
                )
            )
            return
        self._emit_phase("execution", "complete", len(EXECUTION_PHASES), len(EXECUTION_PHASES), "Method run complete")
        self.completed.emit(self.adapter.run_payload(result))

    def _service_progress(self, event: Mapping[str, Any]) -> None:
        if self._cancel_requested:
            return
        phase = str(event.get("phase") or self._current_phase or "method_resolve")
        message = str(event.get("message") or _phase_message(phase))
        progress_current = int(event.get("progress_current") or _phase_progress_index(phase))
        progress_total = int(event.get("progress_total") or len(EXECUTION_PHASES))
        status = str(event.get("status") or "running")
        self._current_phase = phase
        self.phase_changed.emit(message)
        self.log.emit(message)
        self.log_line.emit(message)
        self.progress.emit(
            self.adapter.progress_event(
                task="execution",
                phase=phase,
                status=status,
                message=message,
                progress_current=progress_current,
                progress_total=progress_total,
            )
        )
        payload: dict[str, Any] = {"task": "execution", "phase": phase, "status": status}
        runs = event.get("runs")
        notes = event.get("notes")
        if isinstance(runs, Mapping):
            payload["runs"] = dict(runs)
        if isinstance(notes, Mapping):
            payload["notes"] = dict(notes)
        self.run_status.emit(payload)

    def _emit_phase(
        self,
        task: str,
        phase: str,
        progress_current: int,
        progress_total: int,
        message: str,
    ) -> None:
        self._current_phase = phase
        self.phase_changed.emit(message)
        self.log.emit(message)
        self.log_line.emit(message)
        payload = self.adapter.progress_event(
            task=task,
            phase=phase,
            status="running",
            message=message,
            progress_current=progress_current,
            progress_total=progress_total,
        )
        self.progress.emit(payload)
        self.run_status.emit({"task": task, "phase": phase, "status": "running", "runs": {}})


def _phase_message(phase: str) -> str:
    return {
        "load_input_package": "Loading MTDP package",
        "load_method_package": "Loading method package",
        "load_mapping": "Loading mapping profile",
        "readiness_check": "Checking package readiness",
        "method_resolve": "Resolving method inputs",
        "method_reduce": "Reducing method outputs",
        "validation": "Running validation checks",
        "acceptance": "Evaluating acceptance and selection sets",
        "write_mtda": "Writing MTDA archive",
        "build_audit_report": "Building audit report",
        "build_workbench_optional": "Building Method Development Workbench if requested",
        "complete": "Method run complete",
    }.get(phase, phase.replace("_", " ").title())


def _phase_progress_index(phase: str) -> int:
    try:
        return EXECUTION_PHASES.index(phase) + 1
    except ValueError:
        return 1


def _accepts_progress_callback(callable_obj: Any) -> bool:
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return False
    return "progress_callback" in signature.parameters
