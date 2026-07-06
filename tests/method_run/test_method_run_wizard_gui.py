from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_run_service import MethodRunRequest, MethodRunServiceResult
from ui.method_run_wizard.method_registry import MethodRegistry


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_method_registry_loads_iso14126_default() -> None:
    registry = MethodRegistry.load()

    entry = registry.by_id("iso14126_2023")

    assert entry.label == "ISO 14126 Compression"
    assert entry.analysis_type == "mechanical.compression"
    assert entry.method_path == METHOD
    assert entry.default_mapping_path == MAPPING


def test_method_run_worker_emits_success_and_failure(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")

    from readiness.readiness_models import ReadinessStatus
    from readiness.readiness_report import ReadinessReport
    from ui.method_run_wizard.worker import MethodRunWorker

    request = MethodRunRequest(INPUT, METHOD, MAPPING, tmp_path / "out.mtda")
    service = _FakeService()
    readiness_events: list[object] = []
    run_events: list[object] = []
    failed_events: list[object] = []

    readiness_worker = MethodRunWorker(service=service, request=request, task="readiness")
    readiness_worker.completed.connect(readiness_events.append)
    readiness_worker.run()

    assert readiness_events
    json.dumps(readiness_events[0])
    assert readiness_events[0]["readiness"]["status"] == ReadinessStatus.READY_WITH_WARNINGS.value

    run_worker = MethodRunWorker(service=service, request=request, task="execution")
    run_worker.completed.connect(run_events.append)
    run_worker.run()

    assert run_events
    json.dumps(run_events[0])
    assert run_events[0]["result"]["status"] == "completed"

    failing_worker = MethodRunWorker(service=_FakeService(fail=True), request=request, task="execution")
    failing_worker.failed.connect(failed_events.append)
    failing_worker.run()

    assert failed_events
    json.dumps(failed_events[0])
    assert "blocked" in failed_events[0]["message"]


def test_qt_adapter_preserves_report_overrides(tmp_path: Path) -> None:
    from ui.method_run_wizard.service_adapter import MethodRunServiceQtAdapter

    request = MethodRunRequest(
        INPUT,
        METHOD,
        MAPPING,
        tmp_path / "out.mtda",
        report_overrides=(
            {
                "field_key": "loading_method",
                "value": "fixture-guided compression",
                "reason": "Report authoring review",
            },
        ),
    )
    adapter = MethodRunServiceQtAdapter()

    payload = adapter.request_to_payload(request)
    restored = adapter.request_from_payload(payload)

    assert payload["report_overrides"][0]["field_key"] == "loading_method"
    assert restored.report_overrides[0]["reason"] == "Report authoring review"


def test_method_run_worker_exception_payload_is_plain(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")

    from ui.method_run_wizard.worker import MethodRunWorker

    request = MethodRunRequest(INPUT, METHOD, MAPPING, tmp_path / "out.mtda")
    failed_events: list[dict[str, object]] = []
    worker = MethodRunWorker(service=_FakeService(raise_error=True), request=request, task="execution")
    worker.failed.connect(failed_events.append)

    worker.run()

    assert failed_events
    json.dumps(failed_events[0])
    assert failed_events[0]["error_type"] == "RuntimeError"
    assert failed_events[0]["phase"] == "method_resolve"


def test_worker_source_has_no_forbidden_qt_widget_imports() -> None:
    source = (SRC / "ui" / "method_run_wizard" / "worker.py").read_text(encoding="utf-8")

    for forbidden in ("QtWidgets", "QWidget", "QTextDocument", "QTextEdit", "QPlainTextEdit", "QMessageBox", "QLabel"):
        assert forbidden not in source


def test_qt_wizard_shim_exposes_new_window(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.qt_wizard import MethodRunWizardDialog
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = MethodRunWizardDialog(service=_FakeService(), package_path=None)

    assert isinstance(dialog, MethodRunWindow)
    assert dialog.controller.state.readiness_status is None
    assert dialog.controller.state.input_package_path is None
    assert dialog.action_bars[dialog.controller.state.scenario]._label.text() == "Choose package"
    assert dialog.findChild(QtWidgets.QFrame, "spotlight") is not None
    assert dialog.exec() == 0
    dialog.close()
    app.quit()


def test_launcher_routes_to_packaging_and_method_wizard(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui import launcher_window as launcher_module
    from mtdp_enrichment.ui.launcher_window import LauncherWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    captured: dict[str, object] = {}

    class FakePackaging:
        def show(self):
            captured["packaging_show"] = True

        def raise_(self):
            captured["packaging_raise"] = True

        def activateWindow(self):
            captured["packaging_activate"] = True

    class FakeMethodWindow:
        def show(self):
            captured["method_show"] = True

        def raise_(self):
            captured["method_raise"] = True

        def activateWindow(self):
            captured["method_activate"] = True

    class FakeController:
        def __init__(self, window, state=None):
            captured["controller_window"] = window
            captured["state"] = state

    monkeypatch.setattr(launcher_module, "MainWindow", FakePackaging, raising=False)
    monkeypatch.setattr(launcher_module, "MethodRunWindow", FakeMethodWindow)
    monkeypatch.setattr(launcher_module, "MethodRunController", FakeController)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = LauncherWindow()

    assert window.dataset_tile.isEnabled()
    assert window.dataset_tile.accessibleName() == "Dataset"
    assert not window.method_tile.isEnabled()
    assert window.method_tile.accessibleName() == "Method"
    assert window.analysis_tile.isEnabled()
    assert window.analysis_tile.accessibleName() == "Analysis"
    assert window.method_tile.action_button.text() == "Unavailable"

    window.open_packaging_interface()
    window.open_method_wizard()

    assert captured["packaging_show"] is True
    assert captured["packaging_raise"] is True
    assert captured["packaging_activate"] is True
    assert captured["method_show"] is True
    assert captured["method_raise"] is True
    assert captured["method_activate"] is True
    assert captured["controller_window"] is window._child_windows[-1]

    window.close()
    app.quit()


def test_packaging_menu_is_scoped_to_packaging_workflow(monkeypatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    assert "tools_run_method" not in window.actions
    assert "tools_open_mtda" not in window.actions
    assert "create_bundle" in window.actions
    assert "delete_empty_bundle" in window.actions
    assert "remove_bundle" in window.actions

    window.close()
    app.quit()


class _FakeService:
    def __init__(self, *, fail: bool = False, raise_error: bool = False) -> None:
        self.fail = fail
        self.raise_error = raise_error

    def check_readiness(self, request):
        from readiness.readiness_models import ReadinessStatus
        from readiness.readiness_report import ReadinessReport

        return ReadinessReport(
            status=ReadinessStatus.READY_WITH_WARNINGS,
            method_id="iso14126_2023",
            schema_id="mechanical.compression",
            mapping_id="fake_mapping",
            requirements=(),
            warnings=("report-only warning",),
        )

    def run(self, request):
        if self.raise_error:
            raise RuntimeError("synthetic worker failure")
        if self.fail:
            return MethodRunServiceResult(
                status="not_ready",
                readiness_status="NOT_READY",
                output_path=None,
                errors=["blocked by fake readiness"],
            )
        return MethodRunServiceResult(
            status="completed",
            readiness_status="READY_WITH_WARNINGS",
            output_path=request.output_path,
            validation_summary={"status": "pass"},
            acceptance_summary={"accepted": 1},
            archive_members=("manifest.json",),
        )
