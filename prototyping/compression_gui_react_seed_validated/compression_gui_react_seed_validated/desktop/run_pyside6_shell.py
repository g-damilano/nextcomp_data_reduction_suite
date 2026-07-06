from __future__ import annotations

import json
import os
import platform
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

# Keep WebEngine crisp on high-DPI Windows displays. Qt 6 handles most scaling
# automatically, but these defaults reduce blurry rounding in embedded Chromium.
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")


def _append_chromium_flags(*flags: str) -> None:
    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    parts = existing.split()
    for flag in flags:
        prefix = flag.split("=", 1)[0]
        if flag not in parts and not any(part.startswith(prefix + "=") for part in parts):
            parts.append(flag)
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(parts).strip()


def _configure_windows_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
    except ImportError:
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


_configure_windows_dpi_awareness()
_append_chromium_flags("--high-dpi-support=1", "--enable-gpu-rasterization")

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QFont, QGuiApplication, QPainter, QPainterPath, QPixmap, QRegion
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QSplashScreen

try:
    from bridge_dispatcher import BridgeDispatcher
except ImportError:  # pragma: no cover - supports package-style imports in tests/tools
    from .bridge_dispatcher import BridgeDispatcher


SCREEN_CONFIG = {
    "home": {
        "title": "NextCOMP Data Reduction Suite",
        "width": 980,
        "height": 930,
        "minWidth": 980,
        "minHeight": 930,
        "zoom": 1.00,
    },
    "packaging": {
        "title": "Dataset Packaging",
        "width": 1480,
        "height": 960,
        "minWidth": 1360,
        "minHeight": 860,
        "zoom": 1.00,
    },
    "method-editor": {
        "title": "Analysis Method Editor",
        "width": 988,
        "height": 960,
        "minWidth": 988,
        "minHeight": 900,
        "zoom": 1.00,
    },
    "analysis": {
        "title": "Method Analysis",
        "width": 1460,
        "height": 940,
        "minWidth": 1280,
        "minHeight": 820,
        "zoom": 1.00,
    },
}

ALIASES = {
    "dataset": "packaging",
    "dataset-packaging": "packaging",
    "mtdp": "packaging",
    "mttp": "packaging",
    "method": "method-editor",
    "method-editor": "method-editor",
    "analysis": "analysis",
    "home": "home",
    "launcher": "home",
}

PRELOAD_SCREENS = ("packaging", "method-editor", "analysis")
NATIVE_SOURCE_DROP_EVENT = "mtdp:native-source-drop"


WINDOW_CHROME_JS = r"""
(() => {
  if (window.__compressionWindowChromeWired) return;
  window.__compressionWindowChromeWired = true;

  const interactiveSelector = [
    'button', 'a', 'input', 'select', 'textarea', 'summary',
    '[role="button"]', '[contenteditable="true"]',
    '[data-window-control]', '[data-window-action]', '.window-control',
    '.menu__btn', '.menu__item', '.menu-item', '.menubar__schema', '.desktop-window-control',
    '.menu__pop', '.menu-pop', '.pick', '.tile-link', '.chip-link', '.modal', '.drawer-scrim', '.scrim'
  ].join(',');

  function closestElement(target, selector) {
    return target && target.closest ? target.closest(selector) : null;
  }

  function eventPath(event) {
    return event.composedPath ? event.composedPath() : [event.target];
  }

  function pathHas(event, selector) {
    return eventPath(event).some((node) => node && node.nodeType === 1 && node.matches && node.matches(selector));
  }

  function actionFromControl(target, event) {
    const explicit = closestElement(target, '[data-window-control], [data-window-action], .window-control');
    if (explicit) {
      return explicit.getAttribute('data-window-control') || explicit.getAttribute('data-window-action') || explicit.dataset.action || '';
    }

    // The source mockups draw OS-style glyphs as spans. Treat only glyphs in the
    // top-right chrome band as controls; do not hijack body text containing dashes.
    if (!target || !target.textContent || event.clientY > 52) return '';
    const label = target.textContent.trim();
    const rect = target.getBoundingClientRect ? target.getBoundingClientRect() : null;
    if (!rect || rect.left < window.innerWidth - 140) return '';
    if (label === '−' || label === '—') return 'minimize';
    if (label === '□' || label === '▢' || label === '❐' || label === '') return 'maximize';
    if (label === '×' || label === '✕' || label === 'X') return 'close';
    return '';
  }

  function shadowRoots() {
    const roots = [document];
    document.querySelectorAll('*').forEach((node) => {
      if (node.shadowRoot) roots.push(node.shadowRoot);
    });
    return roots;
  }

  function syncWindowState(state) {
    const maximized = !!(state && state.maximized);
    document.documentElement.dataset.windowMaximized = maximized ? 'true' : 'false';
    shadowRoots().forEach((root) => {
      root.querySelectorAll?.('[data-window-control="maximize"], [data-window-action="maximize"], [data-window-action="toggle-maximize"]').forEach((button) => {
        button.dataset.windowStateSynced = 'true';
        button.dataset.windowMaximized = maximized ? 'true' : 'false';
        button.textContent = maximized ? '❐' : '▢';
        const label = maximized ? 'Restore window' : 'Maximize window';
        button.title = label;
        button.setAttribute('aria-label', label);
      });
    });
  }
  window.__compressionSyncWindowState = syncWindowState;

  function syncResizeState(resizing) {
    const value = !!resizing;
    document.documentElement.dataset.windowResizing = value ? 'true' : 'false';
    shadowRoots().forEach((root) => {
      if (root.host && root.host.dataset) {
        root.host.dataset.windowResizing = value ? 'true' : 'false';
      }
    });
  }
  window.__compressionSyncResizeState = syncResizeState;

  function syncFromAction(result) {
    Promise.resolve(result).then((state) => {
      if (state && typeof state === 'object') syncWindowState(state);
    }).catch(() => {});
  }

  function consumeShortcut(event) {
    event.preventDefault();
    event.stopPropagation();
    if (event.stopImmediatePropagation) event.stopImmediatePropagation();
  }

  function openSuiteModule(screen) {
    if (window.desktopApi?.openChildWindow) {
      window.desktopApi.openChildWindow({screen});
    } else if (window.__compressionSuiteOpenChild) {
      window.__compressionSuiteOpenChild(screen);
    }
  }

  function invokeWindowAction(action) {
    if (!action || !window.desktopApi) return;
    if (action === 'minimize') window.desktopApi.minimizeWindow?.();
    else if (action === 'maximize' || action === 'restore' || action === 'toggle-maximize') syncFromAction(window.desktopApi.toggleMaximizeWindow?.());
    else if (action === 'close') window.desktopApi.closeWindow?.();
    else if (action === 'quit' || action === 'exit') (window.desktopApi.quitApplication || window.desktopApi.closeWindow)?.();
  }

  function isInteractive(event) {
    const target = event.target;
    if (closestElement(target, interactiveSelector) || pathHas(event, interactiveSelector)) return true;
    for (const node of eventPath(event)) {
      if (!node || node.nodeType !== 1) continue;
      const cursor = window.getComputedStyle(node).cursor;
      if (cursor === 'pointer' || cursor === 'text') return true;
    }
    return false;
  }

  function isDragRegion(event) {
    const target = event.target;
    if (!target || !target.closest) return false;
    if (target.closest('[data-window-drag], .menubar__dragzone, .menubar__title') || pathHas(event, '[data-window-drag], .menubar__dragzone, .menubar__title')) return true;
    if (target.closest('.menu__pop, .modal, .drawer, .scrim') || pathHas(event, '.menu__pop, .modal, .drawer, .scrim')) return false;
    if (target.closest('.menubar--desktop, .menubar') || pathHas(event, '.menubar--desktop, .menubar')) return true;
    // Home and method DC mockups use inline title bars with no class names.
    return event.clientY >= 0 && event.clientY <= 30;
  }

  document.addEventListener('mousedown', (event) => {
    if (event.button !== 0) return;
    const action = actionFromControl(event.target, event);
    if (action) {
      event.preventDefault();
      event.stopPropagation();
    }
  }, true);

  document.addEventListener('click', (event) => {
    const action = actionFromControl(event.target, event);
    if (!action) return;
    event.preventDefault();
    event.stopPropagation();
    invokeWindowAction(action);
  }, true);

  document.addEventListener('contextmenu', (event) => {
    event.preventDefault();
    event.stopPropagation();
  }, true);

  document.addEventListener('dblclick', (event) => {
    if (isInteractive(event)) return;
    if (!isDragRegion(event)) return;
    event.preventDefault();
    syncFromAction(window.desktopApi?.toggleMaximizeWindow?.());
  }, true);

  document.addEventListener('keydown', (event) => {
    const target = event.target;
    if (target && target.closest && target.closest('input,textarea,select,[contenteditable="true"]')) return;

    const key = event.key.toLowerCase();
    if (event.key === 'F11' || (event.altKey && event.key === 'Enter')) {
      consumeShortcut(event);
      syncFromAction(window.desktopApi?.toggleMaximizeWindow?.());
      return;
    }
    if ((event.ctrlKey || event.metaKey) && key === 'w') {
      consumeShortcut(event);
      window.desktopApi?.closeWindow?.();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && key === 'q') {
      consumeShortcut(event);
      (window.desktopApi?.quitApplication || window.desktopApi?.closeWindow)?.();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && key === 'm') {
      consumeShortcut(event);
      window.desktopApi?.minimizeWindow?.();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && key === 'd') {
      consumeShortcut(event);
      openSuiteModule('packaging');
      return;
    }
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && key === 'm') {
      consumeShortcut(event);
      openSuiteModule('method-editor');
      return;
    }
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && key === 'a') {
      consumeShortcut(event);
      openSuiteModule('analysis');
    }
  }, true);
})();
"""


class StaticHandler(SimpleHTTPRequestHandler):
    """Serve the Vite dist folder to WebEngine instead of using fragile file:// URLs."""

    def log_message(self, fmt: str, *args) -> None:
        # Keep the terminal useful: only failures are printed by WebPage console logging.
        pass


class StaticServer:
    def __init__(self, directory: Path) -> None:
        handler = partial(StaticHandler, directory=str(directory))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._server.server_port}/index.html"

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message:
            print(f"[JS] {source_id}:{line_number} :: {message}")


class PackagingDialogService:
    def __init__(self, window: "MainWindow") -> None:
        self._window = window

    def open_package_path(self, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self._window,
            "Open MTDP package",
            str(start),
            "MTDP packages (*.mtdp)",
        )
        return path or None

    def open_analysis_package_path(self, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self._window,
            "Open MTDP package",
            str(start),
            "MTDP packages (*.mtdp)",
        )
        return path or None

    def open_sources_paths(self, kind: str = "folder", initial_dir: str | None = None) -> list[str] | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        if kind == "files":
            paths, _selected_filter = QFileDialog.getOpenFileNames(
                self._window,
                "Open source files",
                str(start),
                "Source files (*.csv *.tsv *.txt *.dat *.yaml *.yml);;All files (*)",
            )
            return paths or None
        folder = QFileDialog.getExistingDirectory(
            self._window,
            "Open source folder",
            str(start),
        )
        return [folder] if folder else None

    def open_image_paths(self, initial_dir: str | None = None) -> list[str] | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self._window,
            "Add image evidence",
            str(start),
            "Images (*.jpg *.jpeg *.png *.tif *.tiff);;All files (*)",
        )
        return paths or None

    def open_supplemental_paths(self, initial_dir: str | None = None) -> list[str] | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self._window,
            "Add supplemental file",
            str(start),
            "All files (*)",
        )
        return paths or None

    def save_export_path(self, default_name: str | None = None, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        clean_name = str(default_name or "mtdp_dataset.mtdp").strip() or "mtdp_dataset.mtdp"
        if Path(clean_name).suffix.lower() != ".mtdp":
            clean_name = f"{clean_name}.mtdp"
        default_path = start / clean_name
        path, _selected_filter = QFileDialog.getSaveFileName(
            self._window,
            "Export MTDP package",
            str(default_path),
            "MTDP packages (*.mtdp)",
        )
        return path or None

    def open_export_directory(self, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        folder = QFileDialog.getExistingDirectory(
            self._window,
            "Export all ready groups",
            str(start),
        )
        return folder or None

    def open_mapping_profile_path(self, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self._window,
            "Choose method mapping profile",
            str(start),
            "Mapping profiles (*.json *.yaml *.yml);;All files (*)",
        )
        return path or None

    def save_mapping_profile_path(
        self,
        default_name: str | None = None,
        initial_dir: str | None = None,
    ) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        clean_name = str(default_name or "mapping_profile_wizard_edit.json").strip()
        if not clean_name:
            clean_name = "mapping_profile_wizard_edit.json"
        if Path(clean_name).suffix.lower() not in {".json", ".yaml", ".yml"}:
            clean_name = f"{clean_name}.json"
        default_path = start / clean_name
        path, _selected_filter = QFileDialog.getSaveFileName(
            self._window,
            "Save repaired mapping profile",
            str(default_path),
            "Mapping profiles (*.json *.yaml *.yml);;All files (*)",
        )
        return path or None

    def open_method_package_path(self, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self._window,
            "Open Method Editor package",
            str(start),
            "Method packages (*.zip method_manifest.yaml);;Method manifest (method_manifest.yaml);;All files (*)",
        )
        return path or None

    def save_method_package_path(self, default_name: str | None = None, initial_dir: str | None = None) -> str | None:
        start = Path(initial_dir).expanduser() if initial_dir else Path.cwd()
        clean_name = str(default_name or "method_package.zip").strip() or "method_package.zip"
        if Path(clean_name).suffix.lower() != ".zip":
            clean_name = f"{clean_name}.zip"
        default_path = start / clean_name
        path, _selected_filter = QFileDialog.getSaveFileName(
            self._window,
            "Export Method Editor package",
            str(default_path),
            "Method package archives (*.zip);;All files (*)",
        )
        return path or None

    def open_artifact_path(self, path: str, artifact_kind: str | None = None) -> bool:
        if not path:
            return False
        target = Path(path).expanduser()
        if target.suffix.lower() in {".html", ".htm"} and hasattr(self._window, "open_html_artifact"):
            return bool(self._window.open_html_artifact(target, artifact_kind=artifact_kind))
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


def _env_flag(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in {"0", "false", "no", "off"}


def _bridge_log_path() -> Path | None:
    configured = os.environ.get("MTDP_BRIDGE_LOG_PATH")
    if configured is not None:
        value = configured.strip()
        if value.lower() in {"", "0", "false", "no", "off"}:
            return None
        return Path(value).expanduser()
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".nextcomp")
    return base / "NextCOMP" / "bridge_events.jsonl"


def _local_paths_from_mime_data(mime_data) -> list[str]:
    paths: list[str] = []
    if mime_data is None or not mime_data.hasUrls():
        return paths
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        path = url.toLocalFile()
        if path and path not in paths:
            paths.append(path)
    return paths


def create_startup_splash(project_root: Path) -> QSplashScreen | None:
    if not _env_flag("MTDP_STARTUP_SPLASH", "1"):
        return None

    width, height = 520, 292
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#0f5132"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.fillRect(0, 0, width, height, QColor("#0f5132"))
    painter.fillRect(0, height - 56, width, 56, QColor("#0b3f28"))

    logo_path = next(
        (
            path
            for path in (
                project_root / "public" / "assets" / "nextcomp-logo.png",
                project_root / "dist" / "assets" / "nextcomp-logo.png",
            )
            if path.exists()
        ),
        None,
    )
    if logo_path is not None:
        logo = QPixmap(str(logo_path))
        if not logo.isNull():
            logo = logo.scaled(
                108,
                108,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap((width - logo.width()) // 2, 36, logo)

    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 22, QFont.Weight.DemiBold))
    painter.drawText(QRectF(0, 148, width, 40), Qt.AlignmentFlag.AlignCenter, "NextCOMP")
    painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
    painter.drawText(QRectF(0, 188, width, 28), Qt.AlignmentFlag.AlignCenter, "Data Reduction Suite")
    painter.setPen(QColor("#b7dec8"))
    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
    painter.drawText(QRectF(0, 238, width, 28), Qt.AlignmentFlag.AlignCenter, "Loading interface...")
    painter.end()

    flags = (
        Qt.WindowType.SplashScreen
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    return QSplashScreen(pixmap, flags)


class CompressionBridge(QObject):
    """Bridge used by the React shell for window chrome and future backend calls."""

    analysisEvent = Signal(str)

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self._window = window
        self._dispatcher = BridgeDispatcher(
            dialog_service=PackagingDialogService(window),
            log_path=_bridge_log_path(),
        )
        self._analysis_event_subscriptions: dict[str, dict[str, int]] = {}
        self._analysis_event_timer = QTimer(self)
        self._analysis_event_timer.setInterval(int(os.environ.get("MTDP_ANALYSIS_EVENT_POLL_MS", "300")))
        self._analysis_event_timer.timeout.connect(self._poll_analysis_event_subscriptions)

    def _json(self, payload: dict) -> str:
        return json.dumps(payload)

    def _bridge_error(
        self,
        error_type: str,
        message: str,
        *,
        details: dict | None = None,
        recoverable: bool = True,
    ) -> str:
        return self._json(
            {
                "status": "error",
                "error_type": error_type,
                "message": message,
                "recoverable": recoverable,
                "details": details or {},
            }
        )

    def _legacy_method_error(self, method: str, recommended: str) -> str:
        return self._bridge_error(
            "Unsupported",
            f"Legacy bridge method {method} is not wired. Use {recommended}.",
            details={
                "method": method,
                "recommended_command": recommended,
            },
        )

    def _subscription_payload(self, payload: str) -> dict | None:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _bounded_subscription_int(self, value, *, default: int, lower: int, upper: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return min(max(parsed, lower), upper)

    @Slot(result=str)
    def ping(self) -> str:
        return self._json({"ok": True, "source": "PySide6 bridge"})

    @Slot(str, result=str)
    def dispatch(self, payload: str) -> str:
        return self._dispatcher.dispatch_json(payload)

    @Slot(str, result=str)
    def subscribeAnalysisEvents(self, payload: str) -> str:
        data = self._subscription_payload(payload)
        if data is None:
            return self._bridge_error("ValidationError", "Analysis event subscription payload must be a JSON object.")
        session_id = str(data.get("session_id") or data.get("sessionId") or "").strip()
        if not session_id:
            return self._bridge_error("ValidationError", "Analysis event subscription requires session_id.")
        cursor = self._bounded_subscription_int(data.get("cursor", data.get("since", 0)), default=0, lower=0, upper=1_000_000)
        limit = self._bounded_subscription_int(data.get("limit"), default=100, lower=1, upper=500)
        self._analysis_event_subscriptions[session_id] = {"cursor": cursor, "limit": limit}
        if not self._analysis_event_timer.isActive():
            self._analysis_event_timer.start()
        self._poll_analysis_event_subscriptions()
        return self._json(
            {
                "status": "ok",
                "data": {
                    "session_id": session_id,
                    "cursor": cursor,
                    "interval_ms": self._analysis_event_timer.interval(),
                },
                "warnings": [],
            }
        )

    @Slot(str, result=str)
    def unsubscribeAnalysisEvents(self, payload: str) -> str:
        data = self._subscription_payload(payload)
        if data is None:
            return self._bridge_error("ValidationError", "Analysis event unsubscribe payload must be a JSON object.")
        session_id = str(data.get("session_id") or data.get("sessionId") or "").strip()
        if session_id:
            self._analysis_event_subscriptions.pop(session_id, None)
        else:
            self._analysis_event_subscriptions.clear()
        if not self._analysis_event_subscriptions and self._analysis_event_timer.isActive():
            self._analysis_event_timer.stop()
        return self._json(
            {
                "status": "ok",
                "data": {
                    "session_id": session_id or None,
                    "active_subscriptions": len(self._analysis_event_subscriptions),
                },
                "warnings": [],
            }
        )

    def _poll_analysis_event_subscriptions(self) -> None:
        for session_id, subscription in list(self._analysis_event_subscriptions.items()):
            response = self._dispatcher.dispatch(
                {
                    "namespace": "analysis",
                    "command": "getEvents",
                    "payload": {
                        "session_id": session_id,
                        "cursor": subscription.get("cursor", 0),
                        "limit": subscription.get("limit", 100),
                    },
                }
            )
            if response.get("status") != "ok":
                self._analysis_event_subscriptions.pop(session_id, None)
                self.analysisEvent.emit(
                    self._json(
                        {
                            "status": "error",
                            "error_type": response.get("error_type") or "RuntimeError",
                            "message": response.get("message") or "Could not read analysis events.",
                            "recoverable": bool(response.get("recoverable", True)),
                            "details": {
                                **(response.get("details") or {}),
                                "session_id": session_id,
                            },
                        }
                    )
                )
                continue
            data = response.get("data") or {}
            subscription["cursor"] = self._bounded_subscription_int(
                data.get("next_cursor"),
                default=subscription.get("cursor", 0),
                lower=0,
                upper=1_000_000,
            )
            if data.get("events"):
                self.analysisEvent.emit(
                    self._json(
                        {
                            "status": "ok",
                            "namespace": "analysis",
                            "event": "analysisEvents",
                            "session_id": session_id,
                            "data": data,
                            "warnings": response.get("warnings") or [],
                        }
                    )
                )
        if not self._analysis_event_subscriptions and self._analysis_event_timer.isActive():
            self._analysis_event_timer.stop()

    @Slot(str, result=str)
    def openChildWindow(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            data = {}
        return self._json(self._window.open_child_window(data))

    @Slot(result=str)
    def loadProject(self) -> str:
        return self._legacy_method_error("loadProject", "packaging.openPackageDialog or analysis.loadPackage")

    @Slot(str, result=str)
    def saveProject(self, payload: str) -> str:
        return self._legacy_method_error("saveProject", "packaging.exportGroup or methodEditor.exportMethodPackage")

    @Slot(str, result=str)
    def validate(self, payload: str) -> str:
        return self._legacy_method_error("validate", "packaging.validateGroup or analysis.checkReadiness")

    @Slot(str, result=str)
    def exportPackage(self, payload: str) -> str:
        return self._legacy_method_error("exportPackage", "packaging.exportGroup or packaging.exportAllReady")

    @Slot(str, result=str)
    def startWindowDrag(self, payload: str) -> str:
        try:
            data = json.loads(payload or "{}")
        except json.JSONDecodeError:
            data = {}
        result = self._window.start_window_drag(data)
        return self._json(result)

    @Slot(result=str)
    def minimizeWindow(self) -> str:
        self._window._stop_manual_drag()
        self._window.showMinimized()
        self._window._sync_window_state_to_page(force=True)
        return self._json(self._window._window_state_payload({"ok": True, "state": "minimized"}))

    @Slot(result=str)
    def toggleMaximizeWindow(self) -> str:
        self._window._stop_manual_drag()
        if self._window.isMaximized():
            self._window.showNormal()
            self._window._apply_rounded_mask()
            state = "normal"
        else:
            self._window.clearMask()
            self._window.showMaximized()
            state = "maximized"
        self._window._sync_window_state_to_page(force=True)
        return self._json(self._window._window_state_payload({"ok": True, "state": state}))

    @Slot(result=str)
    def closeWindow(self) -> str:
        self._window._stop_manual_drag()
        self._window.close()
        return self._json({"ok": True})

    @Slot(result=str)
    def quitApplication(self) -> str:
        app = QApplication.instance()
        if app is not None:
            app.quit()
        return self._json({"ok": True})


class ArtifactHtmlWindow(QMainWindow):
    def __init__(self, path: Path, *, artifact_kind: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._path = Path(path).expanduser()
        self.setWindowTitle("MTDA · analysed dataset archive")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1180, 820)
        self.setMinimumSize(760, 520)

        self.web = QWebEngineView(self)
        self.web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setCentralWidget(self.web)
        settings = self.web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)
        self.web.load(QUrl.fromLocalFile(str(self._path.resolve())))


class MainWindow(QMainWindow):
    def __init__(
        self,
        base_url: str,
        *,
        screen: str = "home",
        mode: str = "launcher",
        initial_payload: dict | None = None,
    ) -> None:
        super().__init__()
        self._base_url = base_url
        self._screen = self._normalise_screen(screen)
        self._mode = "child" if mode == "child" else "launcher"
        self._initial_payload = dict(initial_payload or {})
        self._child_windows: list[MainWindow] = []
        self._warm_child_windows: dict[str, MainWindow] = {}
        self._artifact_windows: list[ArtifactHtmlWindow] = []
        self._preload_started = False
        self._startup_splash: QSplashScreen | None = None
        self._corner_radius = int(os.environ.get("MTDP_WINDOW_RADIUS", "16"))
        self._mount_deadline_ms = int(os.environ.get("MTDP_MOUNT_TIMEOUT_MS", "9000"))
        self._closing = False
        self._mount_ready = False
        self._mount_failed = False
        self._last_mask_size: tuple[int, int] | None = None
        self._last_window_state_payload = ""
        self._resize_active = False
        self._last_resize_state_payload = ""
        self._manual_drag_timer: QTimer | None = None
        self._manual_drag_cursor_start = QPoint()
        self._manual_drag_window_start = QPoint()
        self._manual_drag_last_cursor = QPoint()
        self._manual_drag_idle_ticks = 0
        self._manual_drag_total_ticks = 0
        self._manual_drag_active = False
        self._system_drag_guard_active = False
        self._resize_mask_timer = QTimer(self)
        self._resize_mask_timer.setSingleShot(True)
        self._resize_mask_timer.setInterval(int(os.environ.get("MTDP_RESIZE_MASK_DELAY_MS", "45")))
        self._resize_mask_timer.timeout.connect(self._apply_rounded_mask)
        self._resize_state_timer = QTimer(self)
        self._resize_state_timer.setSingleShot(True)
        self._resize_state_timer.setInterval(int(os.environ.get("MTDP_RESIZE_STATE_DELAY_MS", "90")))
        self._resize_state_timer.timeout.connect(self._sync_window_state_to_page)
        self._resize_end_timer = QTimer(self)
        self._resize_end_timer.setSingleShot(True)
        self._resize_end_timer.setInterval(int(os.environ.get("MTDP_RESIZE_END_DELAY_MS", "140")))
        self._resize_end_timer.timeout.connect(self._finish_resize)
        self._geometry_stabilize_timer = QTimer(self)
        self._geometry_stabilize_timer.setSingleShot(True)
        self._geometry_stabilize_timer.setInterval(int(os.environ.get("MTDP_GEOMETRY_STABILIZE_DELAY_MS", "80")))
        self._geometry_stabilize_timer.timeout.connect(self._stabilize_window_geometry)

        config = SCREEN_CONFIG[self._screen]
        initial_geometry = self._initial_window_geometry(config)
        self.setWindowTitle(config["title"])
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, self._mode == "child")
        self.setMinimumSize(initial_geometry["minWidth"], initial_geometry["minHeight"])
        self.resize(initial_geometry["width"], initial_geometry["height"])

        self.web = QWebEngineView(self)
        self.web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web.installEventFilter(self)
        self.setAcceptDrops(True)
        self.web.setAcceptDrops(True)
        self.page = WebPage(self.web)
        self.page.setBackgroundColor(QColor(0, 0, 0, 0))
        self.web.setPage(self.page)
        self.web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCentralWidget(self.web)

        settings = self.web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True)

        self.web.setZoomFactor(float(os.environ.get("MTDP_WEB_ZOOM", str(config.get("zoom", 1.0)))))

        self.bridge = CompressionBridge(self)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("mtdpBridge", self.bridge)
        self.page.setWebChannel(self.channel)

        self.web.loadFinished.connect(self._on_load_finished)
        self.web.load(self._app_url())
        QTimer.singleShot(0, self._apply_rounded_mask)
        QTimer.singleShot(0, self._center_on_available_screen)
        QTimer.singleShot(120, self._stabilize_window_geometry)

    def _normalise_screen(self, screen: str) -> str:
        key = ALIASES.get(str(screen or "").strip(), str(screen or "").strip())
        return key if key in SCREEN_CONFIG else "home"

    def _app_url(self) -> QUrl:
        query_params = {"mode": self._mode, "screen": self._screen}
        package_path = self._initial_payload.get("initial_package_path") or self._initial_payload.get("package_path")
        if package_path:
            query_params["initial_package_path"] = str(package_path)
        query = urlencode(query_params)
        joiner = "&" if "?" in self._base_url else "?"
        return QUrl(f"{self._base_url}{joiner}{query}")

    def _available_geometry(self):
        handle = self.windowHandle()
        screen = handle.screen() if handle is not None else None
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _initial_window_geometry(self, config: dict) -> dict:
        available = self._available_geometry()
        margin = int(os.environ.get("MTDP_WINDOW_SCREEN_MARGIN", "32"))
        if available is None:
            max_width = int(config["width"])
            max_height = int(config["height"])
        else:
            max_width = max(720, available.width() - margin)
            max_height = max(560, available.height() - margin)

        width = min(int(config["width"]), max_width)
        height = min(int(config["height"]), max_height)
        min_width = min(int(config["minWidth"]), width)
        min_height = min(int(config["minHeight"]), height)

        return {
            "width": width,
            "height": height,
            "minWidth": min_width,
            "minHeight": min_height,
        }

    def _center_on_available_screen(self) -> None:
        available = self._available_geometry()
        if available is None:
            return
        x = available.x() + max(0, (available.width() - self.width()) // 2)
        y = available.y() + max(0, (available.height() - self.height()) // 2)
        self.move(x, y)

    def _stabilize_window_geometry(self) -> None:
        if self._closing or self.isMaximized() or self.isFullScreen():
            return
        available = self._available_geometry()
        if available is None:
            return
        margin = int(os.environ.get("MTDP_WINDOW_SCREEN_MARGIN", "32"))
        max_width = max(self.minimumWidth(), available.width() - margin)
        max_height = max(self.minimumHeight(), available.height() - margin)
        width = min(max(self.width(), self.minimumWidth()), max_width)
        height = min(max(self.height(), self.minimumHeight()), max_height)
        if width != self.width() or height != self.height():
            self.resize(width, height)
        self._move_within_available_screen(self.x(), self.y())

    def _finish_startup_splash(self) -> None:
        splash = self._startup_splash
        self._startup_splash = None
        if not self.isVisible():
            self.show()
        self.setWindowOpacity(1.0)
        if splash is not None:
            try:
                splash.finish(self)
            except RuntimeError:
                splash.close()
        self._present_on_top()

    def _expire_startup_splash(self) -> None:
        if self._startup_splash is None:
            return
        if self._mount_ready:
            self._finish_startup_splash()
            return
        self._show_mount_failure(
            "React did not report a completed interface before the startup splash timeout. "
            "Check the JavaScript console lines printed in this terminal."
        )

    def _move_within_available_screen(self, x: int, y: int) -> None:
        available = self._available_geometry()
        if available is None:
            self.move(x, y)
            return
        clamped_x = available.left() if self.width() >= available.width() else min(max(x, available.left()), available.right() - self.width() + 1)
        clamped_y = available.top() if self.height() >= available.height() else min(max(y, available.top()), available.bottom() - self.height() + 1)
        self.move(clamped_x, clamped_y)

    def start_window_drag(self, _payload: dict | None = None) -> dict:
        if self.isMaximized() or self.isFullScreen():
            return {"ok": False, "mode": "blocked-maximized"}

        payload = _payload or {}
        source = str(payload.get("source") or "")
        from_native_event = source == "native-event"
        from_browser_event = source == "browser-event"
        if from_browser_event and self._system_drag_guard_active:
            return {"ok": True, "mode": "system-guard"}
        if not (from_native_event or from_browser_event) and not (QGuiApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._stop_manual_drag()
            return {"ok": False, "mode": "no-button"}

        system_move_started = False
        handle = self.windowHandle()
        if handle is not None and hasattr(handle, "startSystemMove"):
            try:
                system_move_started = bool(handle.startSystemMove())
            except RuntimeError:
                pass
        if system_move_started:
            self._system_drag_guard_active = True
            QTimer.singleShot(300, self._clear_system_drag_guard)
            self._stop_manual_drag()
            return {"ok": True, "mode": "system"}

        if isinstance(payload.get("globalX"), (int, float)) and isinstance(payload.get("globalY"), (int, float)):
            self._manual_drag_cursor_start = QPoint(int(payload["globalX"]), int(payload["globalY"]))
        elif isinstance(payload.get("clientX"), (int, float)) and isinstance(payload.get("clientY"), (int, float)):
            self._manual_drag_cursor_start = self.web.mapToGlobal(QPoint(int(payload["clientX"]), int(payload["clientY"])))
        else:
            self._manual_drag_cursor_start = QCursor.pos()
        self._manual_drag_last_cursor = self._manual_drag_cursor_start
        self._manual_drag_window_start = self.pos()
        self._manual_drag_idle_ticks = 0
        self._manual_drag_total_ticks = 0
        self._manual_drag_active = True
        if self._manual_drag_timer is None:
            self._manual_drag_timer = QTimer(self)
            self._manual_drag_timer.setInterval(16)
            self._manual_drag_timer.timeout.connect(self._manual_drag_tick)
        self._manual_drag_timer.start()
        return {"ok": True, "mode": "manual"}

    def _clear_system_drag_guard(self) -> None:
        self._system_drag_guard_active = False

    def _stop_manual_drag(self) -> None:
        if self._manual_drag_timer is not None:
            self._manual_drag_timer.stop()
        self._manual_drag_idle_ticks = 0
        self._manual_drag_total_ticks = 0
        self._manual_drag_active = False

    def _manual_drag_move_to(self, cursor: QPoint) -> None:
        if not self._manual_drag_active:
            return
        delta = cursor - self._manual_drag_cursor_start
        self._move_within_available_screen(
            self._manual_drag_window_start.x() + delta.x(),
            self._manual_drag_window_start.y() + delta.y(),
        )

    def _manual_drag_tick(self) -> None:
        if not (QGuiApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._stop_manual_drag()
            return

        self._manual_drag_total_ticks += 1
        cursor = QCursor.pos()
        if cursor == self._manual_drag_last_cursor:
            self._manual_drag_idle_ticks += 1
        else:
            self._manual_drag_idle_ticks = 0
            self._manual_drag_last_cursor = cursor

        if self._manual_drag_total_ticks > 240:
            self._stop_manual_drag()
            return

        self._manual_drag_move_to(cursor)

    def open_child_window(self, data: dict) -> dict:
        screen = self._normalise_screen(str(data.get("screen") or "packaging"))
        if screen == "home":
            screen = "packaging"
        package_path = data.get("initial_package_path") or data.get("package_path")
        child, preloaded = (None, False) if package_path else self._take_warm_child(screen)
        if child is None:
            child = MainWindow(
                self._base_url,
                screen=screen,
                mode="child",
                initial_payload={"initial_package_path": package_path} if package_path else None,
            )

        # Stagger child windows slightly relative to the launching window.
        offset = 36 + (len(self._child_windows) % 6) * 18
        child._move_within_available_screen(self.x() + offset, self.y() + offset)
        child.show()
        child._present_on_top(pulse=True)
        self._child_windows.append(child)
        child.destroyed.connect(lambda *_args, w=child: self._forget_child(w))
        if self._mode == "launcher" and self._preload_enabled():
            QTimer.singleShot(500, lambda s=screen: self._ensure_warm_child(s))
        config = SCREEN_CONFIG[screen]
        return {
            "status": "opened",
            "screen": screen,
            "title": config["title"],
            "preloaded": preloaded,
            "initial_package_path": str(package_path) if package_path else None,
            "width": child.width(),
            "height": child.height(),
            "minWidth": child.minimumWidth(),
            "minHeight": child.minimumHeight(),
        }

    def open_html_artifact(self, path: Path, *, artifact_kind: str | None = None) -> bool:
        target = Path(path).expanduser()
        if not target.exists() or target.suffix.lower() not in {".html", ".htm"}:
            return False
        viewer = ArtifactHtmlWindow(target, artifact_kind=artifact_kind, parent=self)
        offset = 54 + (len(self._artifact_windows) % 6) * 18
        viewer.move(self.x() + offset, self.y() + offset)
        viewer.show()
        viewer.raise_()
        viewer.activateWindow()
        self._artifact_windows.append(viewer)
        viewer.destroyed.connect(lambda *_args, w=viewer: self._forget_artifact_window(w))
        return True

    def _forget_artifact_window(self, window: ArtifactHtmlWindow) -> None:
        self._artifact_windows = [item for item in self._artifact_windows if item is not window]

    def _present_on_top(self, *, pulse: bool = False) -> None:
        if self.isMinimized():
            self.showNormal()
        if pulse:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.show()
        self.raise_()
        self.activateWindow()
        handle = self.windowHandle()
        if handle is not None:
            handle.requestActivate()

        if platform.system() == "Windows":
            try:
                import ctypes

                hwnd = int(self.winId())
                ctypes.windll.user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL
                ctypes.windll.user32.BringWindowToTop(hwnd)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

        if pulse:
            QTimer.singleShot(180, self._release_on_top_pulse)
        QTimer.singleShot(40, self.raise_)
        QTimer.singleShot(80, self.activateWindow)
        QTimer.singleShot(180, self.raise_)

    def _release_on_top_pulse(self) -> None:
        if self._closing:
            return
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()
        self.raise_()
        self.activateWindow()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.web and self._screen == "packaging" and event.type() in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
        ):
            if _local_paths_from_mime_data(event.mimeData()):
                event.acceptProposedAction()
                return True

        if watched is self.web and self._screen == "packaging" and event.type() == QEvent.Type.Drop:
            paths = _local_paths_from_mime_data(event.mimeData())
            if paths:
                event.acceptProposedAction()
                self._dispatch_native_source_drop(paths)
                return True

        if watched is self.web and event.type() == QEvent.Type.ContextMenu:
            return True

        if watched is self.web and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
            if key == Qt.Key.Key_F11 or (alt and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)):
                self.bridge.toggleMaximizeWindow()
                return True
            if ctrl and key == Qt.Key.Key_W:
                self.bridge.closeWindow()
                return True
            if ctrl and key == Qt.Key.Key_Q:
                self.bridge.quitApplication()
                return True
            if ctrl and shift and key == Qt.Key.Key_M:
                self.bridge.minimizeWindow()
                return True

        if watched is self.web and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton and self._is_native_drag_region(event.position().toPoint()):
                global_pos = event.globalPosition().toPoint()
                self.start_window_drag({"source": "native-event", "globalX": global_pos.x(), "globalY": global_pos.y()})
                return True
        if watched is self.web and event.type() == QEvent.Type.MouseMove and self._manual_drag_active:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._manual_drag_move_to(event.globalPosition().toPoint())
                return True
            self._stop_manual_drag()
        if watched is self.web and event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self._stop_manual_drag()
        if watched is self.web and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton and self._is_native_drag_region(event.position().toPoint()):
                self.bridge.toggleMaximizeWindow()
                return True
        if watched is self.web and event.type() in (QEvent.Type.Leave, QEvent.Type.FocusOut):
            self._stop_manual_drag()
        return super().eventFilter(watched, event)

    def _is_native_drag_region(self, pos: QPoint) -> bool:
        if pos.y() < 0 or pos.y() > 30:
            return False

        width = max(1, self.web.width())
        x = pos.x()
        if x >= width - 132:
            return False

        if self._screen == "home":
            return x < 214 or 330 < x < width - 150
        if self._screen == "packaging":
            return x < 126 or 650 < x < width - 190
        if self._screen == "method-editor":
            return x < 116 or 440 < x < width - 390
        if self._screen == "analysis":
            return x < 96 or 330 < x < width - 210
        return x < 160

    def _dispatch_native_source_drop(self, paths: list[str]) -> None:
        if not paths:
            return
        detail = json.dumps({"paths": paths})
        event_name = json.dumps(NATIVE_SOURCE_DROP_EVENT)
        self.page.runJavaScript(
            f"""
            (() => {{
              window.dispatchEvent(new CustomEvent({event_name}, {{ detail: {detail} }}));
            }})();
            """
        )

    def _preload_enabled(self) -> bool:
        return _env_flag("MTDP_PRELOAD_CHILDREN", "1")

    def preload_child_windows(self) -> None:
        if self._mode != "launcher" or self._closing or self._preload_started:
            return
        if not self._preload_enabled():
            return
        self._preload_started = True
        for index, screen in enumerate(PRELOAD_SCREENS):
            QTimer.singleShot(140 * index, lambda s=screen: self._ensure_warm_child(s))

    def _ensure_warm_child(self, screen: str) -> None:
        if self._mode != "launcher" or self._closing or not self._preload_enabled():
            return
        screen = self._normalise_screen(screen)
        if screen == "home":
            return
        existing = self._warm_child_windows.get(screen)
        if existing is not None and not existing._closing and not existing._mount_failed:
            return
        if existing is not None:
            existing.close()

        child = MainWindow(self._base_url, screen=screen, mode="child")
        self._warm_child_windows[screen] = child
        child.destroyed.connect(lambda *_args, s=screen, w=child: self._forget_warm_child(s, w))

    def _take_warm_child(self, screen: str) -> tuple["MainWindow | None", bool]:
        if self._mode != "launcher":
            return None, False
        child = self._warm_child_windows.pop(screen, None)
        if child is None:
            return None, False
        if child._closing or child._mount_failed:
            child.close()
            return None, False
        return child, bool(child._mount_ready)

    def _forget_warm_child(self, screen: str, child: "MainWindow") -> None:
        if self._warm_child_windows.get(screen) is child:
            self._warm_child_windows.pop(screen, None)

    def _forget_child(self, child: "MainWindow") -> None:
        self._child_windows = [w for w in self._child_windows if w is not child]

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._resize_active:
            self._resize_active = True
            self._sync_resize_state_to_page(True)
        if self.isMaximized() or self.isFullScreen():
            self.clearMask()
            self._last_mask_size = None
        self._resize_mask_timer.start()
        self._resize_state_timer.start()
        self._resize_end_timer.start()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.WindowStateChange, QEvent.Type.ActivationChange):
            if event.type() == QEvent.Type.WindowStateChange:
                self._stop_manual_drag()
            if not self.isMaximized() and not self.isFullScreen():
                self._geometry_stabilize_timer.start()
            self._sync_window_state_to_page(force=True)

    def closeEvent(self, event) -> None:
        self._closing = True
        self._stop_manual_drag()
        if self._startup_splash is not None:
            self._startup_splash.close()
            self._startup_splash = None
        for viewer in list(self._artifact_windows):
            viewer.close()
        self._artifact_windows.clear()
        if self._mode == "launcher":
            for child in list(self._child_windows):
                child.close()
            self._child_windows.clear()
            for child in list(self._warm_child_windows.values()):
                child.close()
            self._warm_child_windows.clear()
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, app.quit)
        super().closeEvent(event)

    def _apply_rounded_mask(self) -> None:
        if self.isMaximized() or self.isFullScreen():
            self.clearMask()
            self._last_mask_size = None
            return
        size = (self.width(), self.height())
        if self._last_mask_size == size:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._corner_radius, self._corner_radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        self._last_mask_size = size

    def _window_state_payload(self, extra: dict | None = None) -> dict:
        payload = {
            "maximized": self.isMaximized(),
            "minimized": self.isMinimized(),
            "fullscreen": self.isFullScreen(),
            "normal": not self.isMaximized() and not self.isMinimized() and not self.isFullScreen(),
        }
        if extra:
            payload.update(extra)
        return payload

    def _sync_window_state_to_page(self, *, force: bool = False) -> None:
        if self._closing or not hasattr(self, "page"):
            return
        payload = json.dumps(self._window_state_payload(), sort_keys=True)
        if not force and payload == self._last_window_state_payload:
            return
        self._last_window_state_payload = payload
        try:
            self.page.runJavaScript(f"window.__compressionSyncWindowState?.({payload});")
        except RuntimeError:
            return

    def _sync_resize_state_to_page(self, resizing: bool, *, force: bool = False) -> None:
        if self._closing or not hasattr(self, "page"):
            return
        payload = "true" if resizing else "false"
        if not force and payload == self._last_resize_state_payload:
            return
        self._last_resize_state_payload = payload
        try:
            self.page.runJavaScript(f"window.__compressionSyncResizeState?.({payload});")
        except RuntimeError:
            return

    def _finish_resize(self) -> None:
        self._resize_active = False
        self._sync_resize_state_to_page(False)
        self._apply_rounded_mask()
        self._sync_window_state_to_page()

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            print("[QWebEngine] load failed", self._app_url().toString())
            return
        QTimer.singleShot(50, self._inject_window_chrome)
        self._mount_check_started = QTimer()
        QTimer.singleShot(250, lambda: self._poll_mount(0))

    def _inject_window_chrome(self) -> None:
        if self._closing:
            return
        try:
            self.page.runJavaScript(WINDOW_CHROME_JS)
            QTimer.singleShot(80, lambda: self._sync_window_state_to_page(force=True))
            QTimer.singleShot(80, lambda: self._sync_resize_state_to_page(self._resize_active, force=True))
        except RuntimeError:
            return

    def _poll_mount(self, elapsed_ms: int) -> None:
        if self._closing:
            return
        try:
            self.page.runJavaScript(
                """
                JSON.stringify((() => {
                  const root = document.getElementById('root');
                  return {
                    state: window.__COMPRESSION_GUI_MOUNT_STATE || 'unknown',
                    hasRoot: !!root,
                    marked: !!(root && root.dataset && root.dataset.compressionGuiMounted === 'true'),
                    textLength: root && root.innerText ? root.innerText.trim().length : 0,
                    error: window.__COMPRESSION_GUI_BOOT_ERROR || null,
                    url: location.href
                  };
                })())
                """,
                lambda result: self._handle_mount_check(result, elapsed_ms),
            )
        except RuntimeError:
            return

    def _mount_result_dict(self, result: object) -> dict:
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}
        return {}

    def _handle_mount_check(self, result: object, elapsed_ms: int) -> None:
        if self._closing:
            return
        data = self._mount_result_dict(result)
        if data.get("marked") or data.get("state") == "mounted":
            self._mount_ready = True
            self._mount_failed = False
            if self._mode == "launcher":
                self._finish_startup_splash()
                QTimer.singleShot(250, self.preload_child_windows)
            return
        if data.get("state") == "error":
            self._show_mount_failure(data.get("error") or "React boot failed.")
            return
        if elapsed_ms < self._mount_deadline_ms:
            QTimer.singleShot(250, lambda: self._poll_mount(elapsed_ms + 250))
            return
        self._show_mount_failure(
            "React did not report a completed mount before timeout. "
            "Check the JavaScript console lines printed in this terminal."
        )

    def _show_mount_failure(self, reason: str) -> None:
        self._mount_failed = True
        safe_reason = json.dumps(str(reason))
        script = f"""
            (() => {{
              const reason = {safe_reason};
              document.body.innerHTML = `
                <div style="font-family: Segoe UI, Arial; padding: 28px; color: #111827; background:#eef0f2; height:100vh;">
                  <h2>Compression GUI React shell did not mount</h2>
                  <p>Open the terminal used to launch this window; JavaScript errors are printed there.</p>
                  <pre id="compression-gui-mount-reason" style="white-space:pre-wrap;background:#fff;border:1px solid #d1d5db;border-radius:8px;padding:12px;"></pre>
                </div>`;
              const pre = document.getElementById('compression-gui-mount-reason');
              if (pre) pre.textContent = reason;
            }})();
            """
        try:
            self.page.runJavaScript(
                script,
                lambda _result=None: self._finish_startup_splash() if self._mode == "launcher" else None,
            )
        except RuntimeError:
            if self._mode == "launcher":
                self._finish_startup_splash()


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    here = Path(__file__).resolve().parent
    initialize_runtime_resources(here)
    dist = here.parent / "dist"
    index_html = dist / "index.html"
    if not index_html.exists():
        raise SystemExit(
            "dist/index.html not found. Run `npm install` and `npm run build` "
            "from the compression_gui_react_seed project root first."
        )

    server = StaticServer(dist)
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(server.shutdown)
    splash = create_startup_splash(here.parent)
    if splash is not None:
        splash.show()
        app.processEvents()
    window = MainWindow(server.url, screen="home", mode="launcher")
    window._startup_splash = splash
    if splash is None:
        window.show()
        window._present_on_top()
    else:
        window.setWindowOpacity(0.0)
        window.show()
        window.lower()
        splash.raise_()
        app.processEvents()
    QTimer.singleShot(int(os.environ.get("MTDP_SPLASH_MAX_MS", "12000")), window._expire_startup_splash)
    return app.exec()


def initialize_runtime_resources(shell_dir: Path) -> None:
    backend_root = _locate_backend_root(shell_dir)
    if backend_root is None:
        return
    src_root = str(backend_root / "src")
    if src_root not in sys.path:
        sys.path.insert(0, src_root)
    try:
        from runtime.resources import default_resolver

        default_resolver().materialize_external_resources()
    except Exception:
        # Startup must still show a useful interface if a controlled deployment
        # provides read-only resources and defers writable setup.
        return


def _locate_backend_root(start: Path) -> Path | None:
    candidates = [start, *start.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "config" / "method_registry.yaml").exists() and (candidate / "src").is_dir():
            return candidate
    return None


if __name__ == "__main__":
    raise SystemExit(main())
