from __future__ import annotations


def test_running_worker_signals_update_spotlight(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)
    worker = _FakeWorker()

    assert isinstance(controller, QtCore.QObject)
    assert controller.thread() == app.thread()

    controller._enter_running()
    controller.attach_worker(worker)

    worker.phase_changed.emit("Resolving method inputs")
    worker.progress.emit(42)
    worker.run_status.emit(
        {
            "runs": {"run_001": "done", "run_002": "running", "run_003": "queued"},
            "notes": {"run_002": "reducing"},
        }
    )
    worker.log_line.emit("Reducing method outputs")

    assert window.running_spotlight._phase.text() == "Resolving method inputs"
    assert window.running_spotlight._bar.value() == 42
    assert window.running_spotlight._pct.text() == "42%"
    assert controller.state.per_run_status["run_002"] == "running"
    assert window.running_spotlight._table.rowCount() == 3
    assert window.running_spotlight._trace.count() >= 3
    assert "running" in window.running_spotlight._summary_values["runs"].text()
    assert window.running_spotlight._summary_values["event"].text() == "Reducing method outputs"
    assert len(controller.state.activity_log) >= 2

    worker.progress.emit(
        {
            "phase": "method_reduce",
            "message": "Reducing method outputs",
            "progress_percent": 50,
        }
    )

    assert window.running_spotlight._phase.text() == "Reducing method outputs"
    assert window.running_spotlight._stage_labels["method_resolve"].property("state") == "done"
    assert window.running_spotlight._stage_labels["method_reduce"].property("state") == "now"

    worker.failed.emit({"message": "synthetic failure"})

    assert controller.state.execution_status == "failed"
    assert not window.running_spotlight._error.isHidden()

    window.close()
    app.quit()


def test_running_completion_transitions_to_review(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)
    worker = _FakeWorker()
    controller._enter_running()
    controller.attach_worker(worker)

    worker.progress.emit(100)
    worker.completed.emit({"message": "complete", "result": {"status": "completed", "output_path": "out.mtda"}})

    QtTest.QTest.qWait(760)

    assert controller.state.service_result["status"] == "completed"
    assert window.spotlight.body.currentIndex() == window._scenario_index[WizardScenario.REVIEW]

    window.close()
    app.quit()


def test_running_cancel_transitions_to_setup(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)
    worker = _FakeWorker()
    controller._enter_running()
    controller.attach_worker(worker)

    window.action_bars[WizardScenario.RUNNING]._primary.click()

    assert worker.cancel_requested
    assert controller.state.execution_status == "cancelled"
    assert window.spotlight.body.currentIndex() == window._scenario_index[WizardScenario.SETUP]

    window.close()
    app.quit()


def test_method_run_worker_exposes_running_ui_signals() -> None:
    from ui.method_run_wizard.worker import MethodRunWorker

    for signal_name in ("phase_changed", "progress", "run_status", "log_line", "completed", "failed"):
        assert hasattr(MethodRunWorker, signal_name)


def test_method_run_worker_relays_service_progress_callback(tmp_path) -> None:
    from methods.core.method_run_service import MethodRunRequest
    from ui.method_run_wizard.worker import MethodRunWorker

    request = MethodRunRequest(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method",
        mapping_path=tmp_path / "mapping.json",
        output_path=tmp_path / "out.mtda",
    )
    worker = MethodRunWorker(service=_ProgressService(), request=request, task="execution")
    progress_events: list[dict[str, object]] = []
    run_status_events: list[dict[str, object]] = []

    worker.progress.connect(progress_events.append)
    worker.run_status.connect(run_status_events.append)
    worker.run()

    assert any(event.get("phase") == "method_reduce" for event in progress_events)
    assert any(event.get("runs") == {"run_001": "running"} for event in run_status_events)


class _ProgressService:
    def run(self, request, *, progress_callback=None):
        from methods.core.method_run_service import MethodRunServiceResult

        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "method_reduce",
                    "message": "Reducing method outputs",
                    "runs": {"run_001": "running"},
                    "notes": {"run_001": "computing per-run method outputs"},
                }
            )
        return MethodRunServiceResult(
            status="completed",
            readiness_status="READY",
            output_path=request.output_path,
        )


def _fake_worker_base():
    from mtdp_enrichment.ui.qt_compat import QtCore

    class FakeWorker(QtCore.QObject):
        phase_changed = QtCore.pyqtSignal(str)
        progress = QtCore.pyqtSignal(object)
        run_status = QtCore.pyqtSignal(dict)
        log_line = QtCore.pyqtSignal(str)
        completed = QtCore.pyqtSignal(dict)
        failed = QtCore.pyqtSignal(dict)
        cancelled = QtCore.pyqtSignal(dict)

        def __init__(self) -> None:
            super().__init__()
            self.cancel_requested = False

        def request_cancel(self) -> None:
            self.cancel_requested = True

    return FakeWorker


_FakeWorker = _fake_worker_base()
