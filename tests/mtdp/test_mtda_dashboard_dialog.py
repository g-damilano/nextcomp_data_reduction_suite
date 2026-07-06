from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_mtda_dashboard_extracts_and_lists_archive_surfaces(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.mtda_dashboard_dialog import MTDADashboardDialog
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    archive_path = tmp_path / "example.mtda"
    _write_mtda_with_surfaces(archive_path)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    package = window._extract_mtda_surface_package(archive_path)
    assert package is not None

    entries = {entry.surface_id: entry for entry in package.entries}
    for surface_id in ("test_report", "audit_report", "method_development_workbench", "surface_manifest"):
        assert entries[surface_id].available
        assert entries[surface_id].local_path is not None
        assert entries[surface_id].local_path.exists()

    dialog = MTDADashboardDialog(package, window)
    assert dialog.summary_table.rowCount() >= 4
    assert dialog.surface_buttons["test_report"].text() == "Open Test Report"
    assert dialog.surface_buttons["audit_report"].text() == "Open Audit Report"
    assert dialog.surface_buttons["method_development_workbench"].text() == "Open Method Development Workbench"

    dialog.close()
    window.close()
    app.quit()


def test_open_mtda_action_shows_dashboard_instead_of_audit_report(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui import main_window as main_window_module
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtGui, QtWidgets

    archive_path = tmp_path / "example.mtda"
    _write_mtda_with_surfaces(archive_path)
    captured: dict[str, object] = {}
    opened_urls: list[object] = []

    class FakeDashboard:
        def __init__(self, package, parent=None):
            captured["package"] = package
            captured["parent"] = parent

        def exec(self):
            captured["exec"] = True
            return 0

    monkeypatch.setattr(main_window_module, "MTDADashboardDialog", FakeDashboard)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(archive_path), "MTDA archives and reports (*.mtda *.html *.json)"),
    )
    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", lambda url: opened_urls.append(url))

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    window.open_mtda_archive_or_report()

    assert captured["parent"] is window
    assert captured["exec"] is True
    package = captured["package"]
    assert {entry.surface_id for entry in package.entries if entry.available} >= {
        "test_report",
        "audit_report",
        "method_development_workbench",
    }
    assert opened_urls == []

    window.close()
    app.quit()


def _write_mtda_with_surfaces(path: Path) -> None:
    manifest = {
        "schema_id": "mtda.surface_manifest.v0_1",
        "surfaces": {
            "test_report": {
                "label": "Test Report",
                "role": "Formal method/result report.",
                "html_member": "report/test_report.html",
                "status": "available",
                "rc_status": "RC_READY",
            },
            "audit_report": {
                "label": "Audit Report",
                "role": "Grouped analysis evidence and traceability report.",
                "html_member": "audit/audit_report.html",
                "status": "available",
                "rc_status": "RC_READY",
            },
            "method_development_workbench": {
                "label": "Method Development Workbench",
                "role": "Operation-level replay and debugging surface.",
                "html_member": "workbench/index.html",
                "status": "available",
            },
        },
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("surface_manifest.json", json.dumps(manifest))
        archive.writestr("manifest.json", json.dumps({"artifact_surfaces": {}}))
        archive.writestr("report/test_report.html", "<html><body>Test Report</body></html>")
        archive.writestr("audit/audit_report.html", "<html><body>Audit Report</body></html>")
        archive.writestr("workbench/index.html", "<html><body>Workbench</body></html>")
        archive.writestr("report/report_quality_gate.json", json.dumps({"surfaces": {}}))
