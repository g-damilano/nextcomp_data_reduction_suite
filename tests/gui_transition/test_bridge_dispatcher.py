from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from threading import Event


os.environ.setdefault("MTDP_QT_API", "PySide6")

ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ROOT = (
    ROOT
    / "prototyping"
    / "compression_gui_react_seed_validated"
    / "compression_gui_react_seed_validated"
    / "desktop"
)
SRC_ROOT = ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_ROOT))

from bridge_dispatcher import BridgeDispatcher  # noqa: E402
from gui_bridge.services.analysis_session import AnalysisSessionService  # noqa: E402
from gui_bridge.services.method_editor_session import MethodEditorSessionService  # noqa: E402
from methods.core.method_package import MethodPackage  # noqa: E402
from methods.core.method_run_service import MethodRunServiceResult  # noqa: E402
from PySide6.QtCore import QCoreApplication, QMimeData, QObject, QPoint, QUrl  # noqa: E402
from run_pyside6_shell import CompressionBridge, MainWindow, _local_paths_from_mime_data  # noqa: E402
from operations.core.operation_context import OperationCancelled  # noqa: E402
from ui.method_run_wizard.method_registry import MethodRegistry  # noqa: E402


def golden_package_path() -> Path:
    return (
        ROOT
        / "tests"
        / "fixtures"
        / "mtdp"
        / "golden_compression_group"
        / "expected"
        / "golden_compression_group.mtdp"
    )


def golden_source_folder() -> Path:
    return ROOT / "tests" / "fixtures" / "mtdp" / "golden_compression_group" / "source"


def test_pyside_shell_extracts_unique_local_source_drop_paths(tmp_path: Path) -> None:
    source = tmp_path / "drop.csv"
    sidecar = tmp_path / "drop.yaml"
    source.write_text("time,load\n0,0\n", encoding="utf-8")
    sidecar.write_text("operator: tester\n", encoding="utf-8")
    mime_data = QMimeData()
    mime_data.setUrls(
        [
            QUrl.fromLocalFile(str(source)),
            QUrl.fromLocalFile(str(sidecar)),
            QUrl.fromLocalFile(str(source)),
            QUrl("https://example.invalid/not-local.csv"),
        ]
    )

    assert [Path(path) for path in _local_paths_from_mime_data(mime_data)] == [source, sidecar]


def write_temp_method_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "method_registry.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "methods:",
                "  - method_id: iso14126_2023",
                "    label: ISO 14126 Compression",
                "    version: 0.1.0",
                "    status: active",
                "    analysis_type: mechanical.compression",
                f"    method_path: {(ROOT / 'src' / 'methods' / 'iso14126').as_posix()}",
                f"    default_mapping_path: {(ROOT / 'mappings' / 'iso14126_manual.json').as_posix()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return registry_path


class EventPageDispatcherStub:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def dispatch(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(request)
        payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
        return {
            "status": "ok",
            "data": {
                "schema_id": "gui_bridge.analysis_events.v0_1",
                "session_id": payload.get("session_id"),
                "run_id": "run-webchannel-001",
                "cursor": payload.get("cursor", 0),
                "next_cursor": 1,
                "event_count": 1,
                "has_more": False,
                "events": [
                    {
                        "event_id": "evt-webchannel-001",
                        "event": "runProgress",
                        "data": {
                            "phase": "reduce_runs",
                            "status": "running",
                            "progress_percent": 42,
                            "message": "Streaming through WebChannel",
                        },
                    }
                ],
            },
            "warnings": [],
        }


class SlowCancellableMethodRunService:
    def __init__(self) -> None:
        self.started = Event()
        self.release_next_progress = Event()
        self.completed = False
        self.cancel_requested_called = False

    def run(
        self,
        request: object,
        *,
        progress_callback: object = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> MethodRunServiceResult:
        if callable(progress_callback):
            progress_callback(
                {
                    "phase": "method_resolve",
                    "message": "Fake method resolving inputs",
                    "status": "running",
                }
            )
        self.started.set()
        if not self.release_next_progress.wait(5):
            raise AssertionError("Timed out waiting for cancellation test release.")
        if cancel_requested is not None and cancel_requested():
            self.cancel_requested_called = True
            raise OperationCancelled("Method run cancelled by operator.")
        if callable(progress_callback):
            progress_callback(
                {
                    "phase": "method_reduce",
                    "message": "Fake method reducing outputs",
                    "status": "running",
                }
            )
        self.completed = True
        return MethodRunServiceResult(
            status="completed",
            readiness_status="READY",
            output_path=getattr(request, "output_path", None),
        )


class NoProgressCancellableMethodRunService:
    def __init__(self) -> None:
        self.started = Event()
        self.completed = False
        self.cancelled = False

    def run(
        self,
        request: object,
        *,
        progress_callback: object = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> MethodRunServiceResult:
        del request
        del progress_callback
        self.started.set()
        deadline = time.time() + 5
        while time.time() < deadline:
            if cancel_requested is not None and cancel_requested():
                self.cancelled = True
                raise OperationCancelled("Method run cancelled by operator.")
            time.sleep(0.01)
        raise AssertionError("Timed out waiting for cancellation request in no-progress service.")


class WindowMoveHandle:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.calls = 0

    def startSystemMove(self) -> bool:
        self.calls += 1
        return self.accepted


class DragWebStub:
    def mapToGlobal(self, point: QPoint) -> QPoint:
        return QPoint(point.x() + 100, point.y() + 200)


class DragWindowStub(QObject):
    start_window_drag = MainWindow.start_window_drag
    _stop_manual_drag = MainWindow._stop_manual_drag

    def __init__(self, handle: WindowMoveHandle) -> None:
        super().__init__()
        self._handle = handle
        self._manual_drag_timer = None
        self._manual_drag_cursor_start = QPoint()
        self._manual_drag_window_start = QPoint()
        self._manual_drag_last_cursor = QPoint()
        self._manual_drag_idle_ticks = 0
        self._manual_drag_total_ticks = 0
        self._manual_drag_active = False
        self._system_drag_guard_active = False
        self.web = DragWebStub()

    def isMaximized(self) -> bool:
        return False

    def isFullScreen(self) -> bool:
        return False

    def windowHandle(self) -> WindowMoveHandle:
        return self._handle

    def pos(self) -> QPoint:
        return QPoint(20, 30)

    def _manual_drag_tick(self) -> None:
        pass

    def _clear_system_drag_guard(self) -> None:
        self._system_drag_guard_active = False


def test_pyside_shell_uses_native_window_move_without_parallel_manual_drag() -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])

    native_window = DragWindowStub(WindowMoveHandle(accepted=True))
    native_result = native_window.start_window_drag({"source": "native-event", "globalX": 5, "globalY": 6})
    assert native_result == {"ok": True, "mode": "system"}
    assert native_window._handle.calls == 1
    assert native_window._manual_drag_active is False
    assert native_window._manual_drag_timer is None
    assert native_window._system_drag_guard_active is True
    guarded_result = native_window.start_window_drag({"source": "browser-event", "clientX": 5, "clientY": 6})
    assert guarded_result == {"ok": True, "mode": "system-guard"}
    assert native_window._handle.calls == 1

    fallback_window = DragWindowStub(WindowMoveHandle(accepted=False))
    fallback_result = fallback_window.start_window_drag({"source": "browser-event", "clientX": 5, "clientY": 6})
    assert fallback_result == {"ok": True, "mode": "manual"}
    assert fallback_window._handle.calls == 1
    assert fallback_window._manual_drag_active is True
    assert fallback_window._manual_drag_timer is not None
    fallback_window._stop_manual_drag()

def test_pyside_bridge_emits_analysis_event_pages_for_subscription() -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    bridge = CompressionBridge(QObject())
    dispatcher = EventPageDispatcherStub()
    bridge._dispatcher = dispatcher
    emitted: list[dict[str, object]] = []
    bridge.analysisEvent.connect(lambda raw: emitted.append(json.loads(raw)))

    response = json.loads(
        bridge.subscribeAnalysisEvents(
            json.dumps(
                {
                    "session_id": "analysis-session-webchannel",
                    "cursor": 0,
                    "limit": 5,
                }
            )
        )
    )

    assert response["status"] == "ok"
    assert response["data"]["session_id"] == "analysis-session-webchannel"
    assert dispatcher.requests[0]["namespace"] == "analysis"
    assert dispatcher.requests[0]["command"] == "getEvents"
    assert dispatcher.requests[0]["payload"] == {
        "session_id": "analysis-session-webchannel",
        "cursor": 0,
        "limit": 5,
    }
    assert emitted
    assert emitted[0]["status"] == "ok"
    assert emitted[0]["event"] == "analysisEvents"
    assert emitted[0]["data"]["events"][0]["event"] == "runProgress"
    assert bridge._analysis_event_subscriptions["analysis-session-webchannel"]["cursor"] == 1

    unsubscribed = json.loads(
        bridge.unsubscribeAnalysisEvents(json.dumps({"session_id": "analysis-session-webchannel"}))
    )
    assert unsubscribed["status"] == "ok"
    assert unsubscribed["data"]["active_subscriptions"] == 0


def test_pyside_bridge_legacy_methods_return_structured_unsupported_errors() -> None:
    _app = QCoreApplication.instance() or QCoreApplication([])
    bridge = CompressionBridge(QObject())

    calls = [
        ("loadProject", bridge.loadProject()),
        ("saveProject", bridge.saveProject(json.dumps({"path": "ignored.mtdp"}))),
        ("validate", bridge.validate(json.dumps({"group": "ignored"}))),
        ("exportPackage", bridge.exportPackage(json.dumps({"path": "ignored.mtdp"}))),
    ]

    for method, raw_response in calls:
        response = json.loads(raw_response)
        assert response["status"] == "error"
        assert response["error_type"] == "Unsupported"
        assert response["recoverable"] is True
        assert response["details"]["method"] == method
        assert "recommended_command" in response["details"]
        assert "not-wired" not in json.dumps(response)
        assert "ignored" not in json.dumps(response)


class PackageDialogStub:
    def __init__(
        self,
        selected_path: Path | None = None,
        selected_sources: list[Path] | None = None,
        save_path: Path | None = None,
        export_dir: Path | None = None,
        mapping_path: Path | None = None,
        mapping_save_path: Path | None = None,
        method_package_path: Path | None = None,
        method_package_save_path: Path | None = None,
    ) -> None:
        self.selected_path = selected_path
        self.selected_sources = selected_sources
        self.save_path = save_path
        self.export_dir = export_dir
        self.mapping_path = mapping_path
        self.mapping_save_path = mapping_save_path
        self.method_package_path = method_package_path
        self.method_package_save_path = method_package_save_path
        self.initial_dir: str | None = None
        self.analysis_initial_dir: str | None = None
        self.source_kind: str | None = None
        self.source_initial_dir: str | None = None
        self.export_default_name: str | None = None
        self.export_initial_dir: str | None = None
        self.export_directory_initial_dir: str | None = None
        self.mapping_initial_dir: str | None = None
        self.mapping_save_default_name: str | None = None
        self.mapping_save_initial_dir: str | None = None
        self.method_package_initial_dir: str | None = None
        self.method_package_save_default_name: str | None = None
        self.method_package_save_initial_dir: str | None = None

    def open_package_path(self, initial_dir: str | None = None) -> str | None:
        self.initial_dir = initial_dir
        return str(self.selected_path) if self.selected_path is not None else None

    def open_analysis_package_path(self, initial_dir: str | None = None) -> str | None:
        self.analysis_initial_dir = initial_dir
        return str(self.selected_path) if self.selected_path is not None else None

    def open_sources_paths(self, kind: str = "folder", initial_dir: str | None = None) -> list[str] | None:
        self.source_kind = kind
        self.source_initial_dir = initial_dir
        if self.selected_sources is None:
            return None
        return [str(path) for path in self.selected_sources]

    def save_export_path(self, default_name: str | None = None, initial_dir: str | None = None) -> str | None:
        self.export_default_name = default_name
        self.export_initial_dir = initial_dir
        return str(self.save_path) if self.save_path is not None else None

    def open_export_directory(self, initial_dir: str | None = None) -> str | None:
        self.export_directory_initial_dir = initial_dir
        return str(self.export_dir) if self.export_dir is not None else None

    def open_mapping_profile_path(self, initial_dir: str | None = None) -> str | None:
        self.mapping_initial_dir = initial_dir
        return str(self.mapping_path) if self.mapping_path is not None else None

    def save_mapping_profile_path(self, default_name: str | None = None, initial_dir: str | None = None) -> str | None:
        self.mapping_save_default_name = default_name
        self.mapping_save_initial_dir = initial_dir
        return str(self.mapping_save_path) if self.mapping_save_path is not None else None

    def open_method_package_path(self, initial_dir: str | None = None) -> str | None:
        self.method_package_initial_dir = initial_dir
        return str(self.method_package_path) if self.method_package_path is not None else None

    def save_method_package_path(self, default_name: str | None = None, initial_dir: str | None = None) -> str | None:
        self.method_package_save_default_name = default_name
        self.method_package_save_initial_dir = initial_dir
        return str(self.method_package_save_path) if self.method_package_save_path is not None else None


def completed_analysis_run(
    dispatcher: BridgeDispatcher,
    tmp_path: Path,
    *,
    output_name: str = "bridge_analysis_run.mtda",
) -> tuple[str, Path, dict[str, object]]:
    package_path = golden_package_path()
    output_path = tmp_path / output_name
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )
    ready = dispatcher.dispatch(
        {
            "id": "analysis-check-readiness",
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"], "output_path": str(output_path)},
        }
    )
    assert ready["status"] == "ok"
    assert ready["data"]["run_enabled"] is True
    started = dispatcher.dispatch(
        {
            "id": "analysis-start-run",
            "namespace": "analysis",
            "command": "startRun",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
                "overwrite": True,
                "generate_workbench": False,
            },
        }
    )
    assert started["status"] == "ok"

    deadline = time.time() + 60
    current = started
    while time.time() < deadline:
        current = dispatcher.dispatch(
            {
                "id": "analysis-get-session",
                "namespace": "analysis",
                "command": "getSession",
                "payload": {"session_id": selected["data"]["session_id"]},
            }
        )
        run = current["data"]["run"]
        if run["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)

    assert current["status"] == "ok"
    assert current["data"]["run"]["status"] == "completed", current["data"]["run"]
    assert output_path.is_file()
    return str(selected["data"]["session_id"]), output_path, current


def test_bridge_dispatcher_lists_packaging_schemas() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = json.loads(
        dispatcher.dispatch_json(
            json.dumps(
                {
                    "id": "schema-smoke",
                    "namespace": "packaging",
                    "command": "listSchemas",
                    "payload": {},
                }
            )
        )
    )

    assert response["id"] == "schema-smoke"
    assert response["status"] == "ok"
    assert response["warnings"] == []
    assert response["data"]["count"] >= 1
    assert any(
        item["schema"] == "mechanical.compression"
        for item in response["data"]["schemas"]
    )
    assert dispatcher.event_log[-1]["status"] == "ok"


def test_bridge_dispatcher_creates_packaging_session_and_loads_package_fixture() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    package_path = golden_package_path()

    created = dispatcher.dispatch(
        {
            "id": "create-packaging-session",
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    session_id = created["data"]["session_id"]
    response = dispatcher.dispatch(
        {
            "id": "load-package",
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {"session_id": session_id, "path": str(package_path)},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "package_loaded"
    assert response["data"]["bundle"]["schemaLabel"] == "Compression"
    assert response["data"]["bundle"]["groups"]
    assert response["data"]["bundle"]["groups"][0]["runs"]
    assert response["data"]["source_summary"]["package_path"] == str(package_path)


def test_bridge_dispatcher_returns_schema_form_model_and_regenerates_after_schema_change() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    package_path = golden_package_path()

    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    session_id = created["data"]["session_id"]
    assert created["data"]["schemaForm"]["source"] == "SchemaRegistry"
    assert created["data"]["schemaForm"]["datasetSections"]
    assert created["data"]["schemaForm"]["runSections"]

    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {"session_id": session_id, "path": str(package_path)},
        }
    )
    assert loaded["status"] == "ok"
    compression_form = loaded["data"]["bundle"]["schemaForm"]
    compression_fields = {
        field["id"]
        for section in compression_form["runSections"]
        for field in section["fields"]
    }
    assert {"width", "thickness", "gauge_length"}.issubset(compression_fields)

    changed = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "setSchema",
            "payload": {
                "session_id": session_id,
                "schema_id": "flexural-0.1.0",
            },
        }
    )

    assert changed["status"] == "ok"
    form = changed["data"]["bundle"]["schemaForm"]
    run_fields = {
        field["id"]
        for section in form["runSections"]
        for field in section["fields"]
    }
    assert form["schema"] == "mechanical.flexural"
    assert form["version"] == "0.1.0"
    assert "span_length" in run_fields
    assert "gauge_length" not in run_fields
    assert any(section["label"] == "Run analysis inputs" for section in form["runSections"])
    assert any(family["id"] == "load" for family in form["channelFamilies"])


def test_bridge_dispatcher_open_package_dialog_loads_selected_package() -> None:
    package_path = golden_package_path()
    dialog = PackageDialogStub(package_path)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "open-package-dialog",
            "namespace": "packaging",
            "command": "openPackageDialog",
            "payload": {
                "session_id": created["data"]["session_id"],
                "initial_dir": str(package_path.parent),
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "package_loaded"
    assert response["data"]["source_summary"]["package_path"] == str(package_path)
    assert dialog.initial_dir == str(package_path.parent)


def test_bridge_dispatcher_open_package_dialog_reports_cancelled() -> None:
    dialog = PackageDialogStub(None)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "cancel-open-package",
            "namespace": "packaging",
            "command": "openPackageDialog",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "Cancelled"
    assert response["recoverable"] is True


def test_bridge_dispatcher_open_sources_dialog_loads_selected_folder() -> None:
    source_folder = golden_source_folder()
    dialog = PackageDialogStub(selected_sources=[source_folder])
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "open-sources-dialog",
            "namespace": "packaging",
            "command": "openSourcesDialog",
            "payload": {
                "session_id": created["data"]["session_id"],
                "kind": "folder",
                "initial_dir": str(source_folder.parent),
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "sources_loaded"
    assert response["data"]["source_summary"]["source_count"] >= 1
    assert response["data"]["bundle"]["groups"]
    assert response["data"]["bundle"]["groups"][0]["runs"]
    assert dialog.source_kind == "folder"
    assert dialog.source_initial_dir == str(source_folder.parent)


def test_bridge_dispatcher_load_sources_loads_dropped_paths() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "load-dropped-sources",
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "sources_loaded"
    assert response["data"]["source_summary"]["source_count"] >= 1
    assert response["data"]["bundle"]["groups"]
    assert response["data"]["bundle"]["groups"][0]["runs"]


def test_bridge_dispatcher_set_schema_updates_packaging_session_schema() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )
    current_schema_id = loaded["data"]["bundle"]["schemaId"]
    target = next(
        item
        for item in loaded["data"]["schemas"]
        if item["id"] != current_schema_id
    )

    response = dispatcher.dispatch(
        {
            "id": "set-schema",
            "namespace": "packaging",
            "command": "setSchema",
            "payload": {
                "session_id": created["data"]["session_id"],
                "schema_id": target["id"],
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["schema"]["id"] == target["id"]
    assert response["data"]["bundle"]["schemaId"] == target["id"]
    assert response["data"]["bundle"]["schemaLabel"] == target["label"]
    assert response["data"]["bundle"]["schemaOverridden"] is True
    assert response["data"]["bundle"]["groups"][0]["runs"]


def test_bridge_dispatcher_set_schema_reports_unknown_schema() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "bad-schema",
            "namespace": "packaging",
            "command": "setSchema",
            "payload": {
                "session_id": created["data"]["session_id"],
                "schema_id": "not-a-real-schema",
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "NotFound"
    assert response["recoverable"] is True
    assert response["details"]["schema_id"] == "not-a-real-schema"


def test_bridge_dispatcher_validate_group_returns_backend_validation_report() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )
    group_id = loaded["data"]["bundle"]["groups"][0]["id"]

    response = dispatcher.dispatch(
        {
            "id": "validate-group",
            "namespace": "packaging",
            "command": "validateGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group_id,
            },
        }
    )

    assert response["status"] == "ok"
    validation = response["data"]["bundle"]["backendValidation"]
    assert validation["source"] == "backend"
    assert validation["group_id"] == group_id
    assert validation["total_runs"] >= 1
    assert validation["error_count"] >= 1
    assert any(issue["code"] == "required" for issue in validation["issues"])


def test_bridge_dispatcher_validate_group_requires_loaded_group() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "validate-empty",
            "namespace": "packaging",
            "command": "validateGroup",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert response["message"] == "No packaging group is loaded."


def test_bridge_dispatcher_exports_selected_group_to_mtdp(tmp_path: Path) -> None:
    output_path = tmp_path / "bridge_exported_group.mtdp"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]

    exported = dispatcher.dispatch(
        {
            "id": "export-group",
            "namespace": "packaging",
            "command": "exportGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "output_path": str(output_path),
            },
        }
    )

    assert exported["status"] == "ok"
    assert output_path.is_file()
    assert exported["data"]["export"]["path"] == str(output_path)
    assert exported["data"]["export"]["runCount"] == len(group["runs"])
    assert exported["data"]["bundle"]["backendValidation"]["ok"] is True
    with zipfile.ZipFile(output_path) as archive:
        members = set(archive.namelist())
    assert "metadata/manifest.json" in members
    assert "metadata/dataset.json" in members
    assert "metadata/provenance.json" in members
    assert any(member.startswith("dataset/raw/") for member in members)
    assert any(member.startswith("dataset/normalized/") for member in members)


def test_bridge_dispatcher_export_group_uses_native_save_dialog(tmp_path: Path) -> None:
    output_path = tmp_path / "dialog_exported_group.mtdp"
    dialog = PackageDialogStub(save_path=output_path)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]

    response = dispatcher.dispatch(
        {
            "id": "export-dialog",
            "namespace": "packaging",
            "command": "exportGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "default_name": "dialog_default.mtdp",
                "initial_dir": str(tmp_path),
            },
        }
    )

    assert response["status"] == "ok"
    assert output_path.is_file()
    assert dialog.export_default_name == "dialog_default.mtdp"
    assert dialog.export_initial_dir == str(tmp_path)


def test_bridge_dispatcher_export_group_reports_cancelled() -> None:
    dialog = PackageDialogStub(save_path=None)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]

    response = dispatcher.dispatch(
        {
            "id": "cancel-export",
            "namespace": "packaging",
            "command": "exportGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "Cancelled"
    assert response["recoverable"] is True


def test_bridge_dispatcher_export_group_blocks_invalid_group(tmp_path: Path) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(golden_source_folder())],
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]

    response = dispatcher.dispatch(
        {
            "id": "blocked-export",
            "namespace": "packaging",
            "command": "exportGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "output_path": str(tmp_path / "blocked.mtdp"),
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["details"]["validation"]["ok"] is False
    assert not (tmp_path / "blocked.mtdp").exists()


def test_bridge_dispatcher_exports_all_ready_groups_to_directory(tmp_path: Path) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "export-all-ready",
            "namespace": "packaging",
            "command": "exportAllReady",
            "payload": {
                "session_id": created["data"]["session_id"],
                "output_dir": str(tmp_path),
            },
        }
    )

    assert response["status"] == "ok"
    summary = response["data"]["exportAll"]
    assert summary["exportedCount"] == 1
    assert summary["skippedCount"] == 0
    assert summary["failedCount"] == 0
    exported_path = Path(summary["exports"][0]["path"])
    assert exported_path.parent == tmp_path
    assert exported_path.is_file()
    assert exported_path.name.endswith("_revised.mtdp")
    with zipfile.ZipFile(exported_path) as archive:
        members = set(archive.namelist())
    assert "metadata/manifest.json" in members
    assert "metadata/dataset.json" in members


def test_bridge_dispatcher_export_all_ready_skips_invalid_groups(tmp_path: Path) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(golden_source_folder())],
            },
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "export-all-invalid",
            "namespace": "packaging",
            "command": "exportAllReady",
            "payload": {
                "session_id": created["data"]["session_id"],
                "output_dir": str(tmp_path),
            },
        }
    )

    assert response["status"] == "ok"
    summary = response["data"]["exportAll"]
    assert summary["exportedCount"] == 0
    assert summary["skippedCount"] == len(loaded["data"]["bundle"]["groups"])
    assert summary["skipped"][0]["validation"]["ok"] is False
    assert not list(tmp_path.glob("*.mtdp"))


def test_bridge_dispatcher_export_all_ready_uses_native_directory_dialog(tmp_path: Path) -> None:
    dialog = PackageDialogStub(export_dir=tmp_path)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "export-all-dialog",
            "namespace": "packaging",
            "command": "exportAllReady",
            "payload": {
                "session_id": created["data"]["session_id"],
                "initial_dir": str(tmp_path.parent),
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["exportAll"]["exportedCount"] == 1
    assert dialog.export_directory_initial_dir == str(tmp_path.parent)


def test_bridge_dispatcher_export_all_ready_reports_cancelled() -> None:
    dialog = PackageDialogStub(export_dir=None)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "cancel-export-all",
            "namespace": "packaging",
            "command": "exportAllReady",
            "payload": {
                "session_id": created["data"]["session_id"],
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "Cancelled"
    assert response["recoverable"] is True


def test_bridge_dispatcher_updates_dataset_and_run_metadata_fields() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    run = group["runs"][0]
    validated = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "validateGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
            },
        }
    )
    assert validated["data"]["bundle"]["backendValidation"]["source"] == "backend"

    dataset_response = dispatcher.dispatch(
        {
            "id": "update-dataset-fields",
            "namespace": "packaging",
            "command": "updateDatasetFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "patch": {
                    "sample_type": "Edited backend sample",
                    "laboratory": "",
                },
            },
        }
    )

    assert dataset_response["status"] == "ok"
    assert dataset_response["data"]["bundle"]["backendValidation"] is None
    assert dataset_response["data"]["bundle"]["dataset"]["values"]["sample_type"] == "Edited backend sample"
    assert "laboratory" not in dataset_response["data"]["bundle"]["dataset"]["values"]

    run_response = dispatcher.dispatch(
        {
            "id": "update-run-fields",
            "namespace": "packaging",
            "command": "updateRunFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "patch": {
                    "width": "12.5",
                    "width__unit": "mm",
                },
            },
        }
    )

    assert run_response["status"] == "ok"
    updated_run = run_response["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["values"]["width"] == "12.5"
    assert updated_run["values"]["width__unit"] == "mm"

    unit_removal_response = dispatcher.dispatch(
        {
            "id": "remove-run-field-unit",
            "namespace": "packaging",
            "command": "updateRunFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "patch": {
                    "width": "13.0",
                    "width__unit": "",
                },
            },
        }
    )

    assert unit_removal_response["status"] == "ok"
    updated_run = unit_removal_response["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["values"]["width"] == "13.0"
    assert "width__unit" not in updated_run["values"]


def test_bridge_dispatcher_update_metadata_requires_patch_object() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "bad-metadata-patch",
            "namespace": "packaging",
            "command": "updateDatasetFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "patch": ["sample_type", "wrong-shape"],
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert response["details"]["patch_type"] == "list"


def test_bridge_dispatcher_updates_group_run_fields_and_grid_matrix() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    run_ids = [run["id"] for run in group["runs"]]

    bulk_response = dispatcher.dispatch(
        {
            "id": "bulk-run-field",
            "namespace": "packaging",
            "command": "updateGroupRunFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "patch": {"operator": "Bulk operator"},
            },
        }
    )

    assert bulk_response["status"] == "ok"
    assert {
        run["values"]["operator"]
        for run in bulk_response["data"]["bundle"]["groups"][0]["runs"]
    } == {"Bulk operator"}

    updates = [
        {"run_id": run_ids[0], "patch": {"width": "10.0"}},
        {"run_id": run_ids[-1], "patch": {"width": "11.0"}},
    ]
    matrix_response = dispatcher.dispatch(
        {
            "id": "grid-matrix",
            "namespace": "packaging",
            "command": "updateRunFieldMatrix",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "updates": updates,
            },
        }
    )

    assert matrix_response["status"] == "ok"
    runs = {
        run["id"]: run["values"]["width"]
        for run in matrix_response["data"]["bundle"]["groups"][0]["runs"]
    }
    assert runs[run_ids[0]] == "10.0"
    assert runs[run_ids[-1]] == "11.0"


def test_bridge_dispatcher_sets_group_run_unit_with_backend_conversion() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    prepared = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "updateGroupRunFields",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "patch": {"width": "10.0", "width__unit": "mm"},
            },
        }
    )
    assert prepared["status"] == "ok"

    response = dispatcher.dispatch(
        {
            "id": "unit-policy",
            "namespace": "packaging",
            "command": "setGroupRunUnit",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "field_id": "width",
                "unit": "cm",
                "convert": True,
            },
        }
    )

    assert response["status"] == "ok"
    updated_group = response["data"]["bundle"]["groups"][0]
    assert updated_group["units"]["width"] == "cm"
    assert {
        (run["values"]["width"], run["values"]["width__unit"])
        for run in updated_group["runs"]
    } == {("1", "cm")}


def test_bridge_dispatcher_rejects_invalid_group_unit() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]

    response = dispatcher.dispatch(
        {
            "id": "bad-unit",
            "namespace": "packaging",
            "command": "setGroupRunUnit",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "field_id": "width",
                "unit": "parsec",
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert response["details"]["field_id"] == "width"


def test_bridge_dispatcher_creates_renames_moves_and_deletes_packaging_groups() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(golden_package_path()),
            },
        }
    )
    source_group = loaded["data"]["bundle"]["groups"][0]
    run_id = source_group["runs"][0]["id"]

    created_group = dispatcher.dispatch(
        {
            "id": "create-group",
            "namespace": "packaging",
            "command": "createGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "name": "Backend Group B",
            },
        }
    )

    assert created_group["status"] == "ok"
    groups = created_group["data"]["bundle"]["groups"]
    target_group = groups[-1]
    assert target_group["name"] == "Backend Group B"
    assert target_group["runs"] == []

    renamed = dispatcher.dispatch(
        {
            "id": "rename-group",
            "namespace": "packaging",
            "command": "renameGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": target_group["id"],
                "name": "Renamed Backend Group",
            },
        }
    )

    assert renamed["status"] == "ok"
    renamed_group = renamed["data"]["bundle"]["groups"][-1]
    assert renamed_group["id"] == target_group["id"]
    assert renamed_group["name"] == "Renamed Backend Group"

    moved = dispatcher.dispatch(
        {
            "id": "move-run",
            "namespace": "packaging",
            "command": "moveRun",
            "payload": {
                "session_id": created["data"]["session_id"],
                "run_id": run_id,
                "from_group_id": source_group["id"],
                "target_group_id": target_group["id"],
            },
        }
    )

    assert moved["status"] == "ok"
    by_group = {
        group["id"]: [run["id"] for run in group["runs"]]
        for group in moved["data"]["bundle"]["groups"]
    }
    assert run_id not in by_group[source_group["id"]]
    assert run_id in by_group[target_group["id"]]

    deleted = dispatcher.dispatch(
        {
            "id": "delete-group",
            "namespace": "packaging",
            "command": "deleteGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": target_group["id"],
            },
        }
    )

    assert deleted["status"] == "ok"
    assert target_group["id"] not in {group["id"] for group in deleted["data"]["bundle"]["groups"]}
    assert run_id in {run["id"] for run in deleted["data"]["bundle"]["unassigned"]}


def test_bridge_dispatcher_proposes_and_applies_backend_grouping() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(golden_source_folder())],
            },
        }
    )
    source_group = loaded["data"]["bundle"]["groups"][0]
    run_id = source_group["runs"][0]["id"]
    created_group = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "name": "Temporary manual split",
            },
        }
    )
    manual_group = created_group["data"]["bundle"]["groups"][-1]
    moved = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "moveRun",
            "payload": {
                "session_id": created["data"]["session_id"],
                "run_id": run_id,
                "from_group_id": source_group["id"],
                "target_group_id": manual_group["id"],
            },
        }
    )
    assert moved["status"] == "ok"

    proposed = dispatcher.dispatch(
        {
            "id": "propose-groups",
            "namespace": "packaging",
            "command": "proposeGroups",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert proposed["status"] == "ok"
    proposal = proposed["data"]["proposals"][0]
    assert proposal["source"] == "backend"
    assert proposal["engine"] == "SampleTypeGrouper"
    assert proposal["groups"]
    assert proposal["run_count"] >= 1

    applied = dispatcher.dispatch(
        {
            "id": "apply-grouping-proposal",
            "namespace": "packaging",
            "command": "applyGroupingProposal",
            "payload": {
                "session_id": created["data"]["session_id"],
                "proposal_id": proposal["id"],
            },
        }
    )

    assert applied["status"] == "ok"
    groups = applied["data"]["bundle"]["groups"]
    assert manual_group["id"] not in {group["id"] for group in groups}
    assert run_id in {run["id"] for group in groups for run in group["runs"]}
    assert applied["data"]["messages"] == [
        f"Applied grouping proposal: {len(groups)} group(s), {len(applied['data']['bundle']['unassigned'])} unassigned run(s)."
    ]


def test_bridge_dispatcher_manages_image_evidence_and_supplemental_files() -> None:
    source_folder = golden_source_folder()
    image_path = source_folder / "run_001_front.jpg"
    notes_path = source_folder / "operator_notes.txt"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    run = group["runs"][0]

    added_image = dispatcher.dispatch(
        {
            "id": "add-image",
            "namespace": "packaging",
            "command": "addImageEvidence",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "paths": [str(image_path)],
                "view": "front",
            },
        }
    )

    assert added_image["status"] == "ok"
    updated_run = added_image["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["evidence"][0]["name"] == image_path.name
    assert updated_run["evidence"][0]["view"] == "front"

    removed_image = dispatcher.dispatch(
        {
            "id": "remove-image",
            "namespace": "packaging",
            "command": "removeImageEvidence",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "index": 0,
            },
        }
    )

    assert removed_image["status"] == "ok"
    assert removed_image["data"]["bundle"]["groups"][0]["runs"][0]["evidence"] == []

    added_dataset_supplemental = dispatcher.dispatch(
        {
            "id": "add-dataset-supplemental",
            "namespace": "packaging",
            "command": "addSupplementalFiles",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "paths": [str(notes_path)],
                "scope": "dataset",
                "notes": "Operator notes",
            },
        }
    )

    assert added_dataset_supplemental["status"] == "ok"
    supplemental = added_dataset_supplemental["data"]["bundle"]["supplemental"]
    assert supplemental[0]["name"] == notes_path.name
    assert supplemental[0]["scope"] == "dataset"
    assert supplemental[0]["role"] == "documents"

    added_run_supplemental = dispatcher.dispatch(
        {
            "id": "add-run-supplemental",
            "namespace": "packaging",
            "command": "addSupplementalFiles",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "paths": [str(notes_path)],
                "scope": "run",
            },
        }
    )

    assert added_run_supplemental["status"] == "ok"
    updated_run = added_run_supplemental["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["supplemental"][0]["name"] == notes_path.name
    assert updated_run["supplemental"][0]["scope"] == "run"
    assert updated_run["supplemental"][0]["runId"] == run["id"]

    removed_run_supplemental = dispatcher.dispatch(
        {
            "id": "remove-run-supplemental",
            "namespace": "packaging",
            "command": "removeSupplementalFile",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "index": 1,
            },
        }
    )

    assert removed_run_supplemental["status"] == "ok"
    assert removed_run_supplemental["data"]["bundle"]["groups"][0]["runs"][0]["supplemental"] == []

    removed_dataset_supplemental = dispatcher.dispatch(
        {
            "id": "remove-dataset-supplemental",
            "namespace": "packaging",
            "command": "removeSupplementalFile",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "index": 0,
            },
        }
    )

    assert removed_dataset_supplemental["status"] == "ok"
    assert removed_dataset_supplemental["data"]["bundle"]["supplemental"] == []


def test_bridge_dispatcher_imports_and_rematches_yaml_sidecars() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )

    assert loaded["status"] == "ok"
    group = loaded["data"]["bundle"]["groups"][0]
    assert group["runs"]
    first_run = group["runs"][0]
    assert first_run["sidecarStatus"] == "YAML imported"
    assert first_run["values"]["sample_type"] == "Golden untreated compression"

    rematched = dispatcher.dispatch(
        {
            "id": "rematch-yaml",
            "namespace": "packaging",
            "command": "rematchYamlSidecars",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "apply_all": True,
            },
        }
    )

    assert rematched["status"] == "ok"
    summary = rematched["data"]["yamlRematch"]
    assert summary["source"] == "backend"
    assert summary["rule"] == "same_stem"
    assert summary["runCount"] == len(group["runs"])
    assert summary["pairedCount"] == summary["runCount"]
    assert summary["requiresMappingCount"] == 0
    assert all(pair["yaml"] and pair["yaml"].endswith(".yaml") for pair in summary["pairs"])
    updated_run = rematched["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["sidecarStatus"] == "YAML imported"
    assert updated_run["values"]["specimen_name"].startswith("CAG-CF-ER-Comp-E")


def test_bridge_dispatcher_reviews_and_applies_yaml_mapping_profile(tmp_path: Path) -> None:
    source_root = tmp_path / "mapping_source"
    source_root.mkdir()
    shutil.copy2(golden_source_folder() / "golden_run_001.csv", source_root / "legacy_comp_001.csv")
    (source_root / "legacy_comp_001.yaml").write_text(
        "\n".join(
            [
                "legacy:",
                "  tester: Mapping Tester",
                "geometry:",
                "  dimension_a:",
                "    value: 9.8",
                "    unit: mm",
                "  dimension_b:",
                "    value: 2.3",
                "    unit: mm",
                "status:",
                "  valid: true",
            ]
        ),
        encoding="utf-8",
    )
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_root)],
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    run = group["runs"][0]
    assert run["sidecarStatus"] == "YAML needs review"

    reviewed = dispatcher.dispatch(
        {
            "id": "review-yaml-mapping",
            "namespace": "packaging",
            "command": "reviewYamlMapping",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
            },
        }
    )

    assert reviewed["status"] == "ok"
    review = reviewed["data"]["yamlMappingReview"]
    rows_by_key = {row["sourceKey"]: row for row in review["rows"]}
    assert rows_by_key["legacy.tester"]["mapping"]["target_field_id"] == "operator"
    assert rows_by_key["geometry.dimension_a"]["mapping"]["target_field_id"] == "width"
    assert rows_by_key["geometry.dimension_b"]["mapping"]["target_field_id"] == "thickness"
    assert rows_by_key["status.valid"]["mapping"]["target_field_id"] == "validity"

    applied = dispatcher.dispatch(
        {
            "id": "apply-yaml-mapping",
            "namespace": "packaging",
            "command": "applyYamlMappingProfile",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
                "profile_id": review["profileId"],
                "mappings": [row["mapping"] for row in review["rows"]],
                "apply_all": True,
            },
        }
    )

    assert applied["status"] == "ok"
    summary = applied["data"]["yamlMapping"]
    assert summary["profileId"] == review["profileId"]
    assert summary["appliedCount"] == 1
    assert Path(summary["profilePath"]).is_file()
    updated_run = applied["data"]["bundle"]["groups"][0]["runs"][0]
    assert updated_run["sidecarStatus"] == "Mapping applied"
    assert updated_run["values"]["operator"] == "Mapping Tester"
    assert updated_run["values"]["width"] == 9.8
    assert updated_run["values"]["width__unit"] == "mm"
    assert updated_run["values"]["thickness"] == 2.3
    assert updated_run["values"]["validity"] == "accepted"


def test_bridge_dispatcher_apply_yaml_mapping_profile_requires_mappings() -> None:
    source_folder = golden_source_folder()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )
    loaded = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "loadSources",
            "payload": {
                "session_id": created["data"]["session_id"],
                "paths": [str(source_folder)],
            },
        }
    )
    group = loaded["data"]["bundle"]["groups"][0]
    run = group["runs"][0]

    response = dispatcher.dispatch(
        {
            "id": "bad-yaml-mapping",
            "namespace": "packaging",
            "command": "applyYamlMappingProfile",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "run_id": run["id"],
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["message"] == "packaging.applyYamlMappingProfile requires payload.mappings to be a list."


def test_bridge_dispatcher_create_group_requires_loaded_package_or_sources() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "packaging",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "create-before-load",
            "namespace": "packaging",
            "command": "createGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "name": "Too soon",
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert response["message"] == "A package or source batch must be loaded before creating groups."


def test_bridge_dispatcher_requires_packaging_session_id_for_session_commands() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = dispatcher.dispatch(
        {
            "id": "missing-session",
            "namespace": "packaging",
            "command": "getSession",
            "payload": {},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert response["message"] == "A packaging session_id is required."


def test_bridge_dispatcher_lists_analysis_methods() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = dispatcher.dispatch(
        {
            "id": "method-smoke",
            "namespace": "analysis",
            "command": "listMethods",
            "payload": {},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["count"] >= 1
    assert all(item["method_id"] for item in response["data"]["methods"])
    assert response["data"]["registry_path"].endswith("method_registry.yaml")


def test_bridge_dispatcher_method_editor_lists_and_loads_methods() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    listed = dispatcher.dispatch(
        {
            "id": "method-editor-list",
            "namespace": "methodEditor",
            "command": "listMethods",
            "payload": {},
        }
    )

    assert listed["status"] == "ok"
    assert listed["data"]["method_count"] >= 1
    assert listed["data"]["methods"][0]["method_id"] == "iso14126_2023"
    assert listed["data"]["methods"][0]["canonical"] is True

    loaded = dispatcher.dispatch(
        {
            "id": "method-editor-load",
            "namespace": "methodEditor",
            "command": "loadMethod",
            "payload": {"method_id": "iso14126_2023"},
        }
    )

    assert loaded["status"] == "ok"
    assert loaded["data"]["method"]["method_id"] == "iso14126_2023"
    assert loaded["data"]["method"]["canonical"] is True
    assert loaded["data"]["recipe_file_count"] >= 10
    assert loaded["data"]["method"]["manifest"]["method_id"] == "iso14126_2023"


def test_bridge_dispatcher_method_editor_creates_loadable_draft_without_mutating_canonical_method(
    tmp_path: Path,
) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        generated_root=tmp_path / "generated"
    )
    canonical_package = MethodPackage.load(ROOT / "src" / "methods" / "iso14126")
    before_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }

    response = dispatcher.dispatch(
        {
            "id": "method-editor-create-draft",
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {
                "methodId": "iso14126_2023",
                "draftLabel": "ISO 14126 GUI transition draft",
            },
        }
    )

    assert response["status"] == "ok"
    draft = response["data"]["draft"]
    draft_path = Path(draft["draft_path"])
    assert draft_path.is_dir()
    assert draft_path.is_relative_to(tmp_path / "generated")
    assert draft["base_method_id"] == "iso14126_2023"
    assert draft["loadable"] is True
    assert draft["copied_file_count"] == len(before_hashes)
    assert (draft_path / "method_manifest.yaml").is_file()
    assert (draft_path / "method_editor" / "edit_record.json").is_file()
    assert (draft_path / "method_editor" / "edit_summary.md").is_file()

    loaded_draft = MethodPackage.load(draft_path)
    assert loaded_draft.method_id == canonical_package.method_id
    assert loaded_draft.version == canonical_package.version

    after_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }
    assert after_hashes == before_hashes
    assert not (canonical_package.root / "method_editor").exists()


def test_bridge_dispatcher_method_editor_updates_and_validates_controlled_draft(
    tmp_path: Path,
) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        generated_root=tmp_path / "generated"
    )
    canonical_package = MethodPackage.load(ROOT / "src" / "methods" / "iso14126")
    before_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }
    created = dispatcher.dispatch(
        {
            "id": "method-editor-create-draft",
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {"methodId": "iso14126_2023"},
        }
    )
    assert created["status"] == "ok"
    draft = created["data"]["draft"]

    updated = dispatcher.dispatch(
        {
            "id": "method-editor-update-draft",
            "namespace": "methodEditor",
            "command": "updateDraft",
            "payload": {
                "draft_id": draft["draft_id"],
                "patch": {
                    "parameter_group": "modulus_chord_strain_window",
                    "values": {
                        "start_strain": 0.0006,
                        "end_strain": 0.0026,
                    },
                    "reason": "GUI transition controlled edit test",
                },
            },
        }
    )
    assert updated["status"] == "ok"
    assert updated["data"]["edit"]["controlled_group"] == "modulus_chord_strain_window"
    assert updated["data"]["validation"]["status"] == "valid"
    assert updated["data"]["draft"]["edit_count"] == 1

    draft_package = MethodPackage.load(Path(draft["draft_path"]))
    chord_step = next(
        step
        for step in draft_package.reduce_recipe["reduce"]
        if step.get("id") == "reduce.chord_modulus"
    )
    assert chord_step["x1"] == 0.0006
    assert chord_step["x2"] == 0.0026

    edit_record = json.loads((Path(draft["draft_path"]) / "method_editor" / "edit_record.json").read_text())
    assert edit_record["applied_edits"][0]["fields"]["x1"]["new"] == 0.0006
    assert edit_record["validation_summary"]["loadable"] is True

    validated = dispatcher.dispatch(
        {
            "id": "method-editor-validate-draft",
            "namespace": "methodEditor",
            "command": "validateDraft",
            "payload": {"draft_path": draft["draft_path"]},
        }
    )
    assert validated["status"] == "ok"
    assert validated["data"]["validation"]["loadable"] is True

    after_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }
    assert after_hashes == before_hashes


def test_bridge_dispatcher_method_editor_rejects_unsafe_draft_edit_group(
    tmp_path: Path,
) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        generated_root=tmp_path / "generated"
    )
    created = dispatcher.dispatch(
        {
            "id": "method-editor-create-draft",
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {"methodId": "iso14126_2023"},
        }
    )
    assert created["status"] == "ok"
    draft = created["data"]["draft"]

    rejected = dispatcher.dispatch(
        {
            "id": "method-editor-update-draft",
            "namespace": "methodEditor",
            "command": "updateDraft",
            "payload": {
                "draft_id": draft["draft_id"],
                "patch": {
                    "parameter_group": "arbitrary_recipe_edit",
                    "values": {"path": "acceptance_recipe.yaml", "value": "mutate anything"},
                },
            },
        }
    )
    assert rejected["status"] == "error"
    assert rejected["error_type"] == "Unsupported"
    assert "modulus_chord_strain_window" in rejected["details"]["supported_groups"]


def exported_generated_method_package(
    tmp_path: Path,
    output_path: Path,
    *,
    target_version: str = "0.2.0",
) -> tuple[Path, str]:
    registry_root = tmp_path / "source_registry"
    registry_root.mkdir()
    registry_path = write_temp_method_registry(registry_root)
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        registry_path=registry_path,
        generated_root=tmp_path / "source_generated",
    )

    created = dispatcher.dispatch(
        {
            "id": "method-editor-import-source-draft",
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {"methodId": "iso14126_2023"},
        }
    )
    assert created["status"] == "ok"
    draft = created["data"]["draft"]
    updated = dispatcher.dispatch(
        {
            "id": "method-editor-import-source-edit",
            "namespace": "methodEditor",
            "command": "updateDraft",
            "payload": {
                "draft_id": draft["draft_id"],
                "patch": {
                    "parameter_group": "modulus_chord_strain_window",
                    "values": {"start_strain": 0.0008, "end_strain": 0.0028},
                },
            },
        }
    )
    assert updated["status"] == "ok"
    generated = dispatcher.dispatch(
        {
            "id": "method-editor-import-source-generate",
            "namespace": "methodEditor",
            "command": "generateVersion",
            "payload": {"draft_id": draft["draft_id"], "targetVersion": target_version},
        }
    )
    assert generated["status"] == "ok"
    method_path = Path(generated["data"]["generated_method"]["method_path"])
    exported = dispatcher.dispatch(
        {
            "id": "method-editor-import-source-export",
            "namespace": "methodEditor",
            "command": "exportMethodPackage",
            "payload": {"method_path": str(method_path), "output_path": str(output_path)},
        }
    )
    assert exported["status"] == "ok"
    return Path(exported["data"]["export"]["export_path"]), generated["data"]["generated_method"]["method_id"]


def test_bridge_dispatcher_method_editor_opens_exported_generated_package(
    tmp_path: Path,
) -> None:
    export_zip, generated_id = exported_generated_method_package(
        tmp_path,
        tmp_path / "exports" / "generated_method.zip",
    )
    import_registry_root = tmp_path / "import_registry"
    import_registry_root.mkdir()
    registry_path = write_temp_method_registry(import_registry_root)
    imported_root = tmp_path / "imported_generated"
    dialog = PackageDialogStub(method_package_path=export_zip)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    dispatcher._method_editor_service = MethodEditorSessionService(
        registry_path=registry_path,
        generated_root=imported_root,
    )

    opened = dispatcher.dispatch(
        {
            "id": "method-editor-open-package",
            "namespace": "methodEditor",
            "command": "openMethodPackage",
            "payload": {"initial_dir": str(tmp_path)},
        }
    )

    assert opened["status"] == "ok"
    assert dialog.method_package_initial_dir == str(tmp_path)
    imported = opened["data"]["generated_method"]
    imported_path = Path(imported["method_path"])
    assert imported["method_id"] == generated_id
    assert imported["version"] == "0.2.0"
    assert imported_path == imported_root / "iso14126_2023" / "v0_2_0"
    assert opened["data"]["import"]["registered"] is True
    assert opened["data"]["registry"]["registered"] is True
    assert (imported_path / "method_editor" / "edit_record.json").is_file()
    imported_package = MethodPackage.load(imported_path)
    assert imported_package.method_id == generated_id
    chord_step = next(
        step
        for step in imported_package.reduce_recipe["reduce"]
        if step.get("id") == "reduce.chord_modulus"
    )
    assert chord_step["x1"] == 0.0008
    assert chord_step["x2"] == 0.0028

    registry = MethodRegistry.load(registry_path)
    assert generated_id in {entry.method_id for entry in registry.active_entries()}


def test_bridge_dispatcher_method_editor_open_package_rejects_reference_method(
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    registry_root.mkdir()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        registry_path=write_temp_method_registry(registry_root),
        generated_root=tmp_path / "generated",
    )

    rejected = dispatcher.dispatch(
        {
            "id": "method-editor-open-reference-rejected",
            "namespace": "methodEditor",
            "command": "openMethodPackage",
            "payload": {"path": str(ROOT / "src" / "methods" / "iso14126")},
        }
    )

    assert rejected["status"] == "error"
    assert rejected["error_type"] == "ValidationError"


def test_bridge_dispatcher_method_editor_generates_registers_and_selects_method(
    tmp_path: Path,
) -> None:
    registry_path = write_temp_method_registry(tmp_path)
    generated_root = tmp_path / "generated"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        registry_path=registry_path,
        generated_root=generated_root,
    )
    canonical_package = MethodPackage.load(ROOT / "src" / "methods" / "iso14126")
    before_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }

    created = dispatcher.dispatch(
        {
            "id": "method-editor-create-versioned-draft",
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {"methodId": "iso14126_2023"},
        }
    )
    assert created["status"] == "ok"
    draft = created["data"]["draft"]

    draft_registration = dispatcher.dispatch(
        {
            "id": "method-editor-register-draft",
            "namespace": "methodEditor",
            "command": "registerGeneratedMethod",
            "payload": {"method_path": draft["draft_path"]},
        }
    )
    assert draft_registration["status"] == "error"
    assert draft_registration["error_type"] == "ValidationError"

    updated = dispatcher.dispatch(
        {
            "id": "method-editor-update-versioned-draft",
            "namespace": "methodEditor",
            "command": "updateDraft",
            "payload": {
                "draft_id": draft["draft_id"],
                "patch": {
                    "parameter_group": "modulus_chord_strain_window",
                    "values": {"start_strain": 0.0007, "end_strain": 0.0027},
                },
            },
        }
    )
    assert updated["status"] == "ok"

    invalid_version = dispatcher.dispatch(
        {
            "id": "method-editor-generate-invalid-version",
            "namespace": "methodEditor",
            "command": "generateVersion",
            "payload": {"draft_id": draft["draft_id"], "target_version": "next"},
        }
    )
    assert invalid_version["status"] == "error"
    assert invalid_version["error_type"] == "ValidationError"

    generated = dispatcher.dispatch(
        {
            "id": "method-editor-generate-version",
            "namespace": "methodEditor",
            "command": "generateVersion",
            "payload": {"draft_id": draft["draft_id"], "targetVersion": "0.1.1"},
        }
    )
    assert generated["status"] == "ok"
    generated_method = generated["data"]["generated_method"]
    generated_path = Path(generated_method["method_path"])
    generated_id = "iso14126_2023_v0_1_1"
    assert generated_method["method_id"] == generated_id
    assert generated_method["version"] == "0.1.1"
    assert generated_path == generated_root / "iso14126_2023" / "v0_1_1"
    assert (generated_path / "method_editor" / "edit_record.json").is_file()
    assert (generated_path / "method_editor" / "edit_summary.md").is_file()

    generated_package = MethodPackage.load(generated_path)
    assert generated_package.method_id == generated_id
    assert generated_package.version == "0.1.1"
    assert generated_package.manifest["generated_from_method_id"] == "iso14126_2023"
    chord_step = next(
        step
        for step in generated_package.reduce_recipe["reduce"]
        if step.get("id") == "reduce.chord_modulus"
    )
    assert chord_step["x1"] == 0.0007
    assert chord_step["x2"] == 0.0027

    duplicate = dispatcher.dispatch(
        {
            "id": "method-editor-generate-duplicate-version",
            "namespace": "methodEditor",
            "command": "generateVersion",
            "payload": {"draft_id": draft["draft_id"], "target_version": "0.1.1"},
        }
    )
    assert duplicate["status"] == "error"
    assert duplicate["error_type"] == "ValidationError"

    registered = dispatcher.dispatch(
        {
            "id": "method-editor-register-generated-method",
            "namespace": "methodEditor",
            "command": "registerGeneratedMethod",
            "payload": {"methodPath": str(generated_path)},
        }
    )
    assert registered["status"] == "ok"
    assert registered["data"]["registered"] is True
    assert registered["data"]["registry_entry"]["method_id"] == generated_id

    registered_again = dispatcher.dispatch(
        {
            "id": "method-editor-register-generated-method-again",
            "namespace": "methodEditor",
            "command": "registerGeneratedMethod",
            "payload": {"method_path": str(generated_path)},
        }
    )
    assert registered_again["status"] == "ok"
    assert registered_again["data"]["already_registered"] is True

    renamed = dispatcher.dispatch(
        {
            "id": "method-editor-rename-generated-method",
            "namespace": "methodEditor",
            "command": "renameMethod",
            "payload": {
                "method_path": str(generated_path),
                "label": "Renamed generated compression method",
            },
        }
    )
    assert renamed["status"] == "ok"
    assert renamed["data"]["label"] == "Renamed generated compression method"
    assert renamed["data"]["registry_entry"]["label"] == "Renamed generated compression method"

    listed_after_register = dispatcher.dispatch(
        {
            "id": "method-editor-list-after-register",
            "namespace": "methodEditor",
            "command": "listMethods",
            "payload": {},
        }
    )
    assert listed_after_register["status"] == "ok"
    generated_entry = next(
        item for item in listed_after_register["data"]["methods"] if item["method_id"] == generated_id
    )
    reference_entry = next(
        item for item in listed_after_register["data"]["methods"] if item["method_id"] == "iso14126_2023"
    )
    assert generated_entry["canonical"] is False
    assert generated_entry["editable"] is True
    assert generated_entry["deletable"] is True
    assert generated_entry["label"] == "Renamed generated compression method"
    assert reference_entry["canonical"] is True
    assert reference_entry["editable"] is False
    assert reference_entry["deletable"] is False

    export_dir = tmp_path / "exports" / "iso14126_2023_v0_1_1"
    exported = dispatcher.dispatch(
        {
            "id": "method-editor-export-generated-method",
            "namespace": "methodEditor",
            "command": "exportMethodPackage",
            "payload": {
                "method_path": str(generated_path),
                "output_path": str(export_dir),
            },
        }
    )
    assert exported["status"] == "ok"
    export_payload = exported["data"]["export"]
    assert export_payload["method_id"] == generated_id
    assert export_payload["export_kind"] == "directory"
    assert Path(export_payload["export_path"]) == export_dir
    assert export_payload["file_count"] >= len(canonical_package.recipe_files())
    assert (export_dir / "method_manifest.yaml").is_file()
    assert (export_dir / "reduce_recipe.yaml").is_file()
    assert (export_dir / "method_editor" / "edit_record.json").is_file()
    assert (export_dir / "method_editor" / "edit_summary.md").is_file()
    exported_manifest = MethodPackage.load(export_dir)
    assert exported_manifest.method_id == generated_id
    exported_chord = next(
        step
        for step in exported_manifest.reduce_recipe["reduce"]
        if step.get("id") == "reduce.chord_modulus"
    )
    assert exported_chord["x1"] == 0.0007
    assert exported_chord["x2"] == 0.0027

    dialog_export_zip = tmp_path / "dialog_exports" / "renamed_generated.zip"
    dispatcher.dialog_service = PackageDialogStub(method_package_save_path=dialog_export_zip)
    dialog_exported = dispatcher.dispatch(
        {
            "id": "method-editor-export-generated-method-dialog",
            "namespace": "methodEditor",
            "command": "exportMethodPackage",
            "payload": {
                "method_path": str(generated_path),
                "default_name": "renamed_generated.zip",
                "initial_dir": str(tmp_path),
            },
        }
    )
    assert dialog_exported["status"] == "ok"
    assert Path(dialog_exported["data"]["export"]["export_path"]) == dialog_export_zip
    assert dialog_exported["data"]["export"]["export_kind"] == "zip"
    assert dispatcher.dialog_service.method_package_save_default_name == "renamed_generated.zip"
    assert dispatcher.dialog_service.method_package_save_initial_dir == str(tmp_path)

    draft_export = dispatcher.dispatch(
        {
            "id": "method-editor-export-draft-rejected",
            "namespace": "methodEditor",
            "command": "exportMethodPackage",
            "payload": {"method_path": draft["draft_path"]},
        }
    )
    assert draft_export["status"] == "error"
    assert draft_export["error_type"] == "ValidationError"

    dispatcher._analysis_service = AnalysisSessionService(registry=MethodRegistry.load(registry_path))
    analysis = dispatcher.dispatch(
        {
            "id": "analysis-session-generated-method",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(golden_package_path())},
        }
    )
    assert analysis["status"] == "ok"
    assert generated_id in {item["method_id"] for item in analysis["data"]["eligible_methods"]}

    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-generated-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": analysis["data"]["session_id"],
                "method_id": generated_id,
            },
        }
    )
    assert selected["status"] == "ok"
    assert selected["data"]["selected_method"]["method_id"] == generated_id

    ready = dispatcher.dispatch(
        {
            "id": "analysis-check-generated-method-readiness",
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"]},
        }
    )
    assert ready["status"] == "ok"
    assert ready["data"]["run_enabled"] is True
    assert ready["data"]["readiness"]["status"] in {"READY", "READY_WITH_WARNINGS"}

    reference_delete = dispatcher.dispatch(
        {
            "id": "method-editor-delete-reference-rejected",
            "namespace": "methodEditor",
            "command": "deleteMethod",
            "payload": {"method_id": "iso14126_2023"},
        }
    )
    assert reference_delete["status"] == "error"
    assert reference_delete["error_type"] == "ValidationError"

    reference_rename = dispatcher.dispatch(
        {
            "id": "method-editor-rename-reference-rejected",
            "namespace": "methodEditor",
            "command": "renameMethod",
            "payload": {"method_id": "iso14126_2023", "label": "Do not rename ISO"},
        }
    )
    assert reference_rename["status"] == "error"
    assert reference_rename["error_type"] == "ValidationError"

    deleted = dispatcher.dispatch(
        {
            "id": "method-editor-delete-generated-method",
            "namespace": "methodEditor",
            "command": "deleteMethod",
            "payload": {"method_path": str(generated_path)},
        }
    )
    assert deleted["status"] == "ok"
    assert deleted["data"]["deleted"] is True
    assert deleted["data"]["method_id"] == generated_id
    assert deleted["data"]["registry"]["deregistered"] is True
    assert not generated_path.exists()
    registry_after_delete = MethodRegistry.load(registry_path)
    assert generated_id not in {entry.method_id for entry in registry_after_delete.entries}

    after_hashes = {
        path.relative_to(canonical_package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in canonical_package.recipe_files()
    }
    assert after_hashes == before_hashes


def test_bridge_dispatcher_creates_analysis_session_with_initial_package() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "package_loaded"
    assert response["data"]["package_path"] == str(package_path)
    assert response["data"]["package"]["package_name"] == package_path.name
    assert response["data"]["package"]["run_count"] >= 1
    assert response["data"]["method_count"] >= 1
    assert response["data"]["messages"] == [
        f"Loaded package {package_path.name} for analysis."
    ]


def test_bridge_dispatcher_selects_analysis_method_and_default_mapping() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]

    response = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["selected_method_id"] == method_id
    assert response["data"]["selected_method"]["method_id"] == method_id
    assert response["data"]["selected_method"]["method_name"]
    assert response["data"]["selected_method"]["standard_reference"]
    assert response["data"]["mapping"]["mapping_name"] == "iso14126_manual.json"
    assert response["data"]["mapping"]["critical_total"] >= 1
    assert response["data"]["mapping"]["bound_count"] <= response["data"]["mapping"]["critical_total"]
    assert response["data"]["messages"][-1] == "Selected method ISO 14126 Compression."


def test_bridge_dispatcher_checks_analysis_readiness_after_method_selection() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "analysis-check-readiness",
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"]},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["readiness_status"] == "READY_WITH_WARNINGS"
    assert response["data"]["run_enabled"] is True
    assert response["data"]["readiness"]["summary"]["execution_critical_missing"] == 0
    assert response["data"]["readiness"]["summary"]["report_missing_total"] >= 1
    assert response["data"]["messages"][-1] == "Readiness check complete: READY_WITH_WARNINGS."


def test_bridge_dispatcher_loads_confirms_and_patches_analysis_mapping_preview(tmp_path: Path) -> None:
    package_path = golden_package_path()
    mapping_path = ROOT / "mappings" / "iso14126_manual.json"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )

    loaded = dispatcher.dispatch(
        {
            "id": "analysis-load-mapping",
            "namespace": "analysis",
            "command": "loadMapping",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "path": str(mapping_path),
            },
        }
    )

    assert loaded["status"] == "ok"
    assert loaded["data"]["mapping"]["mapping_name"] == "iso14126_manual.json"
    assert loaded["data"]["mapping"]["preview"]["schema_name"] == "mapping_preview_view_model"
    assert loaded["data"]["mapping"]["preview"]["rows"]
    assert loaded["data"]["mapping_confirmed"] is False
    assert loaded["data"]["readiness"] is None

    edited_path = tmp_path / "iso14126_manual_wizard_edit.json"
    patched = dispatcher.dispatch(
        {
            "id": "analysis-apply-mapping-patch",
            "namespace": "analysis",
            "command": "applyMappingPatch",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(edited_path),
                "bindings": [
                    {
                        "method_field": "report.operator",
                        "source_role": "operator",
                        "source_kind": "field",
                        "mapped_source": "Operator Name",
                        "status": "manual",
                    }
                ],
            },
        }
    )

    assert patched["status"] == "ok"
    assert patched["data"]["mapping_confirmed"] is True
    assert patched["data"]["mapping"]["mapping_name"] == edited_path.name
    assert patched["data"]["mapping"]["path"] == str(edited_path)
    assert patched["data"]["readiness"] is None
    saved = json.loads(edited_path.read_text(encoding="utf-8"))
    assert saved["fields"]["operator"] == "Operator Name"
    assert saved["mapping_id"].endswith("_wizard_edit")
    assert patched["data"]["messages"][-1] == f"Saved mapping edits to {edited_path.name}."

    confirmed = dispatcher.dispatch(
        {
            "id": "analysis-confirm-mapping",
            "namespace": "analysis",
            "command": "confirmMapping",
            "payload": {"session_id": selected["data"]["session_id"]},
        }
    )

    assert confirmed["status"] == "ok"
    assert confirmed["data"]["mapping_confirmed"] is True
    assert confirmed["data"]["messages"][-1] == f"Confirmed mapping {edited_path.name}."


def test_bridge_dispatcher_analysis_mapping_native_dialogs_load_and_save(tmp_path: Path) -> None:
    package_path = golden_package_path()
    mapping_path = ROOT / "mappings" / "iso14126_manual.json"
    edited_path = tmp_path / "native_mapping_edit.json"
    dialog = PackageDialogStub(mapping_path=mapping_path, mapping_save_path=edited_path)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )

    opened = dispatcher.dispatch(
        {
            "id": "analysis-open-mapping-dialog",
            "namespace": "analysis",
            "command": "openMappingDialog",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "initial_dir": str(mapping_path.parent),
            },
        }
    )

    assert opened["status"] == "ok"
    assert dialog.mapping_initial_dir == str(mapping_path.parent)
    assert opened["data"]["mapping"]["mapping_name"] == mapping_path.name
    assert opened["data"]["mapping_confirmed"] is False

    saved = dispatcher.dispatch(
        {
            "id": "analysis-save-mapping-dialog",
            "namespace": "analysis",
            "command": "saveMappingDialog",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "default_name": "native_mapping_edit.json",
                "initial_dir": str(tmp_path),
                "bindings": [
                    {
                        "method_field": "report.operator",
                        "source_role": "operator",
                        "source_kind": "field",
                        "mapped_source": "Operator Name",
                        "status": "manual",
                    }
                ],
            },
        }
    )

    assert saved["status"] == "ok"
    assert dialog.mapping_save_default_name == "native_mapping_edit.json"
    assert dialog.mapping_save_initial_dir == str(tmp_path)
    assert saved["data"]["mapping_confirmed"] is True
    assert saved["data"]["mapping"]["path"] == str(edited_path)
    saved_payload = json.loads(edited_path.read_text(encoding="utf-8"))
    assert saved_payload["fields"]["operator"] == "Operator Name"


def test_bridge_dispatcher_starts_analysis_run_and_reports_completion(tmp_path: Path) -> None:
    package_path = golden_package_path()
    output_path = tmp_path / "bridge_analysis_run.mtda"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )
    ready = dispatcher.dispatch(
        {
            "id": "analysis-check-readiness",
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"], "output_path": str(output_path)},
        }
    )

    assert ready["status"] == "ok"
    assert ready["data"]["run_enabled"] is True

    started = dispatcher.dispatch(
        {
            "id": "analysis-start-run",
            "namespace": "analysis",
            "command": "startRun",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
                "overwrite": True,
                "generate_workbench": False,
            },
        }
    )

    assert started["status"] == "ok"
    assert started["data"]["run"]["status"] == "running"
    assert started["data"]["run"]["run_id"].startswith("run-")

    deadline = time.time() + 60
    current = started
    while time.time() < deadline:
        current = dispatcher.dispatch(
            {
                "id": "analysis-get-session",
                "namespace": "analysis",
                "command": "getSession",
                "payload": {"session_id": selected["data"]["session_id"]},
            }
        )
        run = current["data"]["run"]
        if run["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)

    assert current["status"] == "ok"
    run = current["data"]["run"]
    assert run["status"] == "completed", run
    assert output_path.is_file()
    assert run["result"]["output_path"] == str(output_path)
    assert run["result"]["archive_member_count"] > 0
    if run["result"]["acceptance_report"].get("flags"):
        review_rows = run["result"].get("review_rows")
        assert review_rows
        assert any(row.get("cockpits") for row in review_rows)
        assert any(
            cockpit.get("plot", {}).get("plot_kind") in {"bending_evidence", "curve_family"}
            for row in review_rows
            for cockpit in row.get("cockpits", [])
        )
    assert run["progress_percent"] == 100
    assert any(event["event"] == "runProgress" for event in run["events"])
    assert run["events"][-1]["event"] == "runCompleted"
    assert current["data"]["messages"][-1] == f"Method run complete: {output_path.name}."
    event_page = dispatcher.dispatch(
        {
            "id": "analysis-get-events",
            "namespace": "analysis",
            "command": "getEvents",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "cursor": 0,
                "limit": 2,
            },
        }
    )
    assert event_page["status"] == "ok"
    assert event_page["data"]["schema_id"] == "gui_bridge.analysis_events.v0_1"
    assert event_page["data"]["session_id"] == selected["data"]["session_id"]
    assert event_page["data"]["run_id"] == run["run_id"]
    assert event_page["data"]["event_count"] == len(run["events"])
    assert len(event_page["data"]["events"]) <= 2

    all_events = dispatcher.dispatch(
        {
            "id": "analysis-get-events-all",
            "namespace": "analysis",
            "command": "getEvents",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "cursor": 0,
                "limit": 500,
            },
        }
    )
    assert any(event["event"] == "runCompleted" for event in all_events["data"]["events"])
    tail = dispatcher.dispatch(
        {
            "id": "analysis-get-events-tail",
            "namespace": "analysis",
            "command": "getEvents",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "cursor": all_events["data"]["next_cursor"],
            },
        }
    )
    assert tail["status"] == "ok"
    assert tail["data"]["events"] == []
    assert tail["data"]["has_more"] is False


def test_bridge_dispatcher_persists_and_confirms_analysis_review_decisions(tmp_path: Path) -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    session_id, output_path, current = completed_analysis_run(
        dispatcher,
        tmp_path,
        output_name="bridge_analysis_review.mtda",
    )
    run_states = current["data"]["run"]["result"]["acceptance_report"]["run_states"]
    specimen_run_id = next(iter(run_states))
    missing_reason = dispatcher.dispatch(
        {
            "id": "analysis-confirm-review-missing-reason",
            "namespace": "analysis",
            "command": "confirmReview",
            "payload": {
                "session_id": session_id,
                "decisions": [
                    {
                        "run_id": specimen_run_id,
                        "decision": "keep",
                        "final_included": True,
                        "default_included": False,
                        "reason": "",
                        "defects": ["bending"],
                    }
                ],
            },
        }
    )

    assert missing_reason["status"] == "error"
    assert missing_reason["error_type"] == "ValidationError"
    assert missing_reason["details"]["run_ids"] == [specimen_run_id]

    decision = {
        "run_id": specimen_run_id,
        "decision": "keep",
        "final_included": True,
        "default_included": False,
        "reason": "Operator review accepted the diagnostic deviation.",
        "defects": ["bending"],
        "reviewer": "QA",
    }
    updated = dispatcher.dispatch(
        {
            "id": "analysis-update-acceptance",
            "namespace": "analysis",
            "command": "updateAcceptanceDecision",
            "payload": {
                "session_id": session_id,
                "decision_patch": decision,
            },
        }
    )

    assert updated["status"] == "ok"
    assert updated["data"]["review"]["status"] == "in_review"
    assert updated["data"]["acceptance_decisions"]["acceptance_keep"][specimen_run_id] is True
    assert updated["data"]["acceptance_decisions"]["acceptance_override_reason"][specimen_run_id] == decision["reason"]
    assert updated["data"]["run"]["review"]["status"] == "in_review"
    assert updated["data"]["run"]["events"][-1]["event"] == "reviewDecisionUpdated"

    confirmed = dispatcher.dispatch(
        {
            "id": "analysis-confirm-review",
            "namespace": "analysis",
            "command": "confirmReview",
            "payload": {
                "session_id": session_id,
                "decisions": [decision],
                "reviewer": "QA",
                "note": "Review gate confirmed.",
            },
        }
    )

    assert confirmed["status"] == "ok"
    assert confirmed["data"]["review"]["status"] == "confirmed"
    assert confirmed["data"]["review"]["reviewer"] == "QA"
    assert confirmed["data"]["review"]["decision_count"] == 1
    assert confirmed["data"]["review"]["override_count"] == 1
    assert confirmed["data"]["review"]["missing_reason_count"] == 0
    assert specimen_run_id in confirmed["data"]["acceptance_decisions"]["final_selected_run_ids"]
    assert confirmed["data"]["run"]["review"]["status"] == "confirmed"
    assert confirmed["data"]["run"]["events"][-1]["event"] == "reviewConfirmed"
    assert confirmed["data"]["messages"][-1].startswith("Acceptance review confirmed:")

    missing_note = dispatcher.dispatch(
        {
            "id": "analysis-finalize-missing-note",
            "namespace": "analysis",
            "command": "finalizeMtda",
            "payload": {
                "session_id": session_id,
                "reviewer": "QA",
                "note": "",
            },
        }
    )

    assert missing_note["status"] == "error"
    assert missing_note["error_type"] == "ValidationError"
    assert "finalization note" in missing_note["message"]

    finalized = dispatcher.dispatch(
        {
            "id": "analysis-finalize-mtda",
            "namespace": "analysis",
            "command": "finalizeMtda",
            "payload": {
                "session_id": session_id,
                "reviewer": "QA",
                "note": "Review gate confirmed.",
                "reason_kind": "review_decisions",
            },
        }
    )

    assert finalized["status"] == "ok"
    finalization = finalized["data"]["finalization"]
    finalized_path = Path(finalization["output_path"])
    assert finalization["status"] == "finalized"
    assert finalization["reason_kind"] == "review_decisions"
    assert finalization["human_decision_count"] == 1
    assert finalized_path.is_file()
    assert finalized_path != output_path
    assert output_path.is_file()
    assert finalized["data"]["output_path"] == str(finalized_path)
    assert finalized["data"]["run"]["output_path"] == str(finalized_path)
    assert finalized["data"]["run"]["events"][-1]["event"] == "mtdaFinalized"
    assert finalized["data"]["messages"][-1] == f"MTDA finalized: {finalized_path.name}."
    with zipfile.ZipFile(finalized_path) as archive:
        members = set(archive.namelist())
    assert any(member.endswith("finalization/archive_state.json") for member in members)
    assert any(member.endswith("finalization/amendment_ledger.json") for member in members)

    amended = dispatcher.dispatch(
        {
            "id": "analysis-apply-report-amendments",
            "namespace": "analysis",
            "command": "applyReportAmendments",
            "payload": {
                "session_id": session_id,
                "reviewer": "QA",
                "reason": "Report metadata completed after review.",
                "report_overrides": [
                    {
                        "field_key": "loading_method",
                        "value": "fixture-guided compression",
                        "reason": "Report metadata completed after review.",
                        "reviewer": "QA",
                        "section": "test_identification",
                    }
                ],
            },
        }
    )

    assert amended["status"] == "ok"
    report_amendments = amended["data"]["report_amendments"]
    amended_path = Path(report_amendments["output_path"])
    assert report_amendments["status"] == "finalized"
    assert report_amendments["override_count"] == 1
    assert report_amendments["field_keys"] == ["loading_method"]
    assert report_amendments["finalization"]["reason_kind"] == "report_completion"
    assert amended_path.is_file()
    assert amended_path != finalized_path
    assert amended["data"]["output_path"] == str(amended_path)
    assert amended["data"]["run"]["output_path"] == str(amended_path)
    assert amended["data"]["run"]["events"][-1]["event"] == "reportAmendmentsApplied"
    assert amended["data"]["messages"][-1] == "Report amendments applied: 1 field(s)."
    with zipfile.ZipFile(amended_path) as archive:
        report_payload = json.loads(archive.read("dataset/04_reports/test_report.json").decode("utf-8"))
    report_override_rows = report_payload.get("report_field_overrides") or []
    assert any(row.get("field_key") == "loading_method" for row in report_override_rows)

    copied = dispatcher.dispatch(
        {
            "id": "analysis-copy-output-path",
            "namespace": "analysis",
            "command": "copyOutputPath",
            "payload": {"session_id": session_id},
        }
    )

    assert copied["status"] == "ok"
    assert copied["data"]["path"] == str(amended_path)
    assert copied["data"]["exists"] is True

    test_report = dispatcher.dispatch(
        {
            "id": "analysis-open-test-report",
            "namespace": "analysis",
            "command": "openArtifact",
            "payload": {"session_id": session_id, "artifact_kind": "test_report", "open": False},
        }
    )

    assert test_report["status"] == "ok"
    assert test_report["data"]["kind"] == "test_report"
    assert Path(test_report["data"]["path"]).is_file()
    assert test_report["data"]["archive_member"].endswith("test_report.html")
    assert test_report["data"]["opened"] is False

    audit_report = dispatcher.dispatch(
        {
            "id": "analysis-open-audit-report",
            "namespace": "analysis",
            "command": "openArtifact",
            "payload": {"session_id": session_id, "artifact_kind": "audit_report", "open": False},
        }
    )

    assert audit_report["status"] == "ok"
    assert audit_report["data"]["kind"] == "audit_report"
    assert Path(audit_report["data"]["path"]).is_file()
    assert audit_report["data"]["archive_member"].endswith("audit_report.html")

    output_folder = dispatcher.dispatch(
        {
            "id": "analysis-open-output-folder",
            "namespace": "analysis",
            "command": "openArtifact",
            "payload": {"session_id": session_id, "artifact_kind": "output_folder", "open": False},
        }
    )

    assert output_folder["status"] == "ok"
    assert output_folder["data"]["kind"] == "output_folder"
    assert Path(output_folder["data"]["path"]) == amended_path.parent
    assert output_folder["data"]["is_dir"] is True

    mtda_view = dispatcher.dispatch(
        {
            "id": "analysis-open-mtda",
            "namespace": "analysis",
            "command": "openArtifact",
            "payload": {"session_id": session_id, "artifact_kind": "open_mtda", "open": False},
        }
    )

    assert mtda_view["status"] == "ok"
    assert mtda_view["data"]["kind"] == "open_mtda"
    assert Path(mtda_view["data"]["path"]).is_file()
    assert Path(mtda_view["data"]["path"]).name == "index.html"
    assert mtda_view["data"]["archive_member"] == "index.html"


def test_bridge_dispatcher_analysis_start_run_requires_selected_method() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "analysis-start-run-not-ready",
            "namespace": "analysis",
            "command": "startRun",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert "selected method" in response["message"]


def test_bridge_dispatcher_analysis_start_run_auto_checks_readiness(tmp_path: Path) -> None:
    package_path = golden_package_path()
    output_path = tmp_path / "auto_readiness_analysis_output.mtda"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )

    started = dispatcher.dispatch(
        {
            "id": "analysis-start-run-auto-readiness",
            "namespace": "analysis",
            "command": "startRun",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
                "overwrite": True,
                "generate_workbench": False,
            },
        }
    )

    assert started["status"] == "ok"
    assert started["data"]["readiness_status"] in {"READY", "READY_WITH_WARNINGS"}
    assert started["data"]["run_enabled"] is True
    assert started["data"]["run"]["status"] in {"queued", "running", "completed"}


def test_bridge_dispatcher_analysis_start_run_blocks_existing_output_without_overwrite(tmp_path: Path) -> None:
    package_path = golden_package_path()
    output_path = tmp_path / "existing_analysis_output.mtda"
    output_path.write_text("do not replace", encoding="utf-8")
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )
    method_id = created["data"]["eligible_methods"][0]["method_id"]
    selected = dispatcher.dispatch(
        {
            "id": "analysis-select-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": method_id,
            },
        }
    )
    ready = dispatcher.dispatch(
        {
            "id": "analysis-check-readiness",
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"], "output_path": str(output_path)},
        }
    )
    assert ready["status"] == "ok"

    blocked = dispatcher.dispatch(
        {
            "id": "analysis-start-existing-output",
            "namespace": "analysis",
            "command": "startRun",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
                "overwrite": False,
                "generate_workbench": False,
            },
        }
    )

    assert blocked["status"] == "error"
    assert blocked["error_type"] == "ValidationError"
    assert "output already exists" in blocked["message"]
    assert blocked["details"]["output_path"] == str(output_path)
    assert output_path.read_text(encoding="utf-8") == "do not replace"

    current = dispatcher.dispatch(
        {
            "id": "analysis-get-session-after-blocked-output",
            "namespace": "analysis",
            "command": "getSession",
            "payload": {"session_id": selected["data"]["session_id"]},
        }
    )
    assert current["status"] == "ok"
    assert current["data"]["run"] is None


def test_analysis_session_cancels_run_at_progress_checkpoint(tmp_path: Path) -> None:
    fake_service = SlowCancellableMethodRunService()
    service = AnalysisSessionService(method_run_service=fake_service)
    session_view = service.create_session()
    session_id = str(session_view["session_id"])
    package_path = tmp_path / "input.mtdp"
    method_path = tmp_path / "method"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "cancelled-output.mtda"
    package_path.write_text("placeholder package", encoding="utf-8")
    method_path.mkdir()
    mapping_path.write_text("{}", encoding="utf-8")

    session = service._sessions[session_id]
    session.package_path = package_path
    session.package_preview = {"schema_id": "mechanical.compression", "run_count": 1}
    session.output_path = output_path
    session.selected_method_id = "fake-method"
    session.method_summary = {"method_id": "fake-method", "method_path": str(method_path)}
    session.mapping_summary = {"path": str(mapping_path), "mapping_name": mapping_path.name}
    session.mapping_confirmed = True
    session.readiness_report = {"status": "READY"}

    try:
        started = service.start_run(session_id, output_path=output_path, generate_workbench=False)
        assert started["run"]["status"] == "running"
        assert fake_service.started.wait(5)

        cancelling = service.cancel_run(session_id)
        assert cancelling["run"]["status"] == "cancelling"
        assert cancelling["run"]["events"][-1]["event"] == "cancelRequested"

        fake_service.release_next_progress.set()
        deadline = time.time() + 5
        current = cancelling
        while time.time() < deadline:
            current = service.get_session(session_id)
            if current["run"]["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)

        run = current["run"]
        assert run["status"] == "cancelled"
        assert run["phase"] == "method_resolve"
        assert run["message"] == "Method run cancelled by operator."
        assert run["result"] is None
        assert fake_service.completed is False
        assert not output_path.exists()
        assert [event["event"] for event in run["events"]][-2:] == ["cancelRequested", "cancelled"]
        assert fake_service.cancel_requested_called is True
    finally:
        service._executor.shutdown(wait=True, cancel_futures=True)


def test_analysis_session_cancels_run_without_progress_checkpoints(tmp_path: Path) -> None:
    fake_service = NoProgressCancellableMethodRunService()
    service = AnalysisSessionService(method_run_service=fake_service)
    session_view = service.create_session()
    session_id = str(session_view["session_id"])
    package_path = tmp_path / "input.mtdp"
    method_path = tmp_path / "method"
    mapping_path = tmp_path / "mapping.json"
    output_path = tmp_path / "cancelled-output.mtda"
    package_path.write_text("placeholder package", encoding="utf-8")
    method_path.mkdir()
    mapping_path.write_text("{}", encoding="utf-8")

    session = service._sessions[session_id]
    session.package_path = package_path
    session.package_preview = {"schema_id": "mechanical.compression", "run_count": 1}
    session.output_path = output_path
    session.selected_method_id = "fake-method"
    session.method_summary = {"method_id": "fake-method", "method_path": str(method_path)}
    session.mapping_summary = {"path": str(mapping_path), "mapping_name": mapping_path.name}
    session.mapping_confirmed = True
    session.readiness_report = {"status": "READY"}

    try:
        started = service.start_run(session_id, output_path=output_path, generate_workbench=False)
        assert started["run"]["status"] == "running"
        assert fake_service.started.wait(5)

        cancelling = service.cancel_run(session_id)
        assert cancelling["run"]["status"] == "cancelling"
        assert cancelling["run"]["events"][-1]["event"] == "cancelRequested"

        deadline = time.time() + 5
        current = cancelling
        while time.time() < deadline:
            current = service.get_session(session_id)
            if current["run"]["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)

        run = current["run"]
        assert run["status"] == "cancelled"
        assert run["phase"] == "queued"
        assert run["message"] == "Method run cancelled by operator."
        assert run["result"] is None
        assert [entry["event"] for entry in run["events"]][-2:] == ["cancelRequested", "cancelled"]
        assert fake_service.cancelled is True
        assert not output_path.exists()
    finally:
        service._executor.shutdown(wait=True, cancel_futures=True)


def test_bridge_dispatcher_analysis_cancel_run_requires_active_run() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "analysis-cancel-run-idle",
            "namespace": "analysis",
            "command": "cancelRun",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert "active run" in response["message"]


def test_bridge_dispatcher_analysis_select_method_rejects_unknown_method() -> None:
    package_path = golden_package_path()
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "id": "analysis-session",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(package_path)},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "analysis-select-unknown-method",
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": created["data"]["session_id"],
                "method_id": "not_registered",
            },
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "NotFound"
    assert response["recoverable"] is True
    assert response["details"]["method_id"] == "not_registered"
    assert created["data"]["eligible_methods"][0]["method_id"] in response["details"]["eligible_method_ids"]


def test_bridge_dispatcher_analysis_load_package_requires_path() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    created = dispatcher.dispatch(
        {
            "namespace": "analysis",
            "command": "createSession",
            "payload": {},
        }
    )

    response = dispatcher.dispatch(
        {
            "id": "analysis-missing-path",
            "namespace": "analysis",
            "command": "loadPackage",
            "payload": {"session_id": created["data"]["session_id"]},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["message"] == "analysis.loadPackage requires payload.path."
    assert response["recoverable"] is True


def test_bridge_dispatcher_analysis_lists_recent_packages(tmp_path: Path) -> None:
    old_package = tmp_path / "old_input.mtdp"
    recent_package = tmp_path / "recent_input.mtdp"
    ignored_archive = tmp_path / "recent_output.mtda"
    ignored = tmp_path / "not_a_package.txt"
    old_package.write_text("old", encoding="utf-8")
    recent_package.write_text("recent", encoding="utf-8")
    ignored_archive.write_text("ignored archive", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")
    os.utime(old_package, (1000, 1000))
    os.utime(recent_package, (2000, 2000))
    os.utime(ignored_archive, (3000, 3000))

    dispatcher = BridgeDispatcher(backend_root=ROOT)
    response = dispatcher.dispatch(
        {
            "id": "analysis-list-recent-packages",
            "namespace": "analysis",
            "command": "listRecentPackages",
            "payload": {"roots": [str(tmp_path)], "limit": 1},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["schema_id"] == "gui_bridge.analysis_recent_packages.v0_1"
    assert response["data"]["count"] == 1
    assert response["data"]["packages"][0]["name"] == "recent_input.mtdp"
    assert response["data"]["packages"][0]["path"] == str(recent_package)


def test_bridge_dispatcher_analysis_open_package_dialog_creates_session() -> None:
    package_path = golden_package_path()
    dialog = PackageDialogStub(package_path)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)

    response = dispatcher.dispatch(
        {
            "id": "analysis-open-package-dialog",
            "namespace": "analysis",
            "command": "openPackageDialog",
            "payload": {"initial_dir": str(package_path.parent)},
        }
    )

    assert response["status"] == "ok"
    assert response["data"]["status"] == "package_loaded"
    assert response["data"]["package_path"] == str(package_path)
    assert response["data"]["package"]["package_path"] == str(package_path)
    assert dialog.analysis_initial_dir == str(package_path.parent)


def test_bridge_dispatcher_analysis_open_package_dialog_reports_cancelled() -> None:
    dialog = PackageDialogStub(None)
    dispatcher = BridgeDispatcher(backend_root=ROOT, dialog_service=dialog)

    response = dispatcher.dispatch(
        {
            "id": "analysis-cancel-open-package",
            "namespace": "analysis",
            "command": "openPackageDialog",
            "payload": {},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "Cancelled"
    assert response["recoverable"] is True


def test_bridge_dispatcher_analysis_session_reports_missing_initial_package() -> None:
    missing_path = ROOT / "tests" / "fixtures" / "mtdp" / "missing_export.mtdp"
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = dispatcher.dispatch(
        {
            "id": "analysis-missing-initial",
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(missing_path)},
        }
    )

    assert response["status"] == "error"
    assert response["error_type"] == "NotFound"
    assert response["recoverable"] is True
    assert response["details"] == {"path": str(missing_path)}


def test_bridge_dispatcher_returns_structured_error_for_unknown_command() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = json.loads(
        dispatcher.dispatch_json(
            json.dumps(
                {
                    "id": "bad-command",
                    "namespace": "packaging",
                    "command": "overwriteEverything",
                    "payload": {},
                }
            )
        )
    )

    assert response == {
        "details": {
            "command": "overwriteEverything",
            "namespace": "packaging",
        },
        "error_type": "UnsupportedCommand",
        "id": "bad-command",
        "message": "Unsupported bridge command: packaging.overwriteEverything",
        "recoverable": True,
        "status": "error",
    }
    assert dispatcher.event_log[-1]["status"] == "error"


def test_bridge_dispatcher_writes_persistent_traceback_safe_jsonl_log(tmp_path: Path) -> None:
    log_path = tmp_path / "bridge_events.jsonl"
    dispatcher = BridgeDispatcher(backend_root=ROOT, log_path=log_path)

    ok_response = dispatcher.dispatch(
        {
            "id": "log-ok",
            "namespace": "shell",
            "command": "ping",
            "session_id": "session-top-level",
            "payload": {},
        }
    )
    error_response = dispatcher.dispatch(
        {
            "id": "log-error",
            "namespace": "analysis",
            "command": "missingCommand",
            "payload": {"session_id": "session-from-payload"},
        }
    )

    assert ok_response["status"] == "ok"
    assert error_response["status"] == "error"
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["id"] == "log-ok"
    assert lines[0]["namespace"] == "shell"
    assert lines[0]["command"] == "ping"
    assert lines[0]["session_id"] == "session-top-level"
    assert lines[0]["status"] == "ok"
    assert lines[0]["duration_ms"] >= 0
    assert lines[1]["id"] == "log-error"
    assert lines[1]["namespace"] == "analysis"
    assert lines[1]["command"] == "missingCommand"
    assert lines[1]["session_id"] == "session-from-payload"
    assert lines[1]["status"] == "error"
    assert lines[1]["error_type"] == "UnsupportedCommand"
    assert "payload" not in lines[1]
    assert "details" not in lines[1]
    assert "traceback" not in json.dumps(lines[1]).lower()


def test_bridge_dispatcher_logs_invalid_json_without_traceback(tmp_path: Path) -> None:
    log_path = tmp_path / "bridge_events.jsonl"
    dispatcher = BridgeDispatcher(backend_root=ROOT, log_path=log_path)

    response = json.loads(dispatcher.dispatch_json("{not-json"))

    assert response["status"] == "error"
    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["namespace"] == "bridge"
    assert logged["command"] == "dispatch_json"
    assert logged["status"] == "error"
    assert logged["error_type"] == "ValidationError"
    assert "payload" not in logged
    assert "details" not in logged
    assert "traceback" not in json.dumps(logged).lower()


def test_bridge_dispatcher_returns_structured_error_for_invalid_json() -> None:
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    response = json.loads(dispatcher.dispatch_json("{not-json"))

    assert response["status"] == "error"
    assert response["error_type"] == "ValidationError"
    assert response["recoverable"] is True
    assert "line" in response["details"]
