from __future__ import annotations

import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.artifact_collector import MTDAArtifactCollector
from export.report_exporter import ReportExporter


def test_report_exporter_copies_test_report_and_full_html_surfaces(tmp_path: Path) -> None:
    archive_path = tmp_path / "input.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("dataset/04_reports/test_report.html", "<html>test</html>")
        archive.writestr("dataset/04_reports/test_report.json", "{}")
        archive.writestr("dataset/04_reports/audit_report.html", "<html>audit</html>")

    minimal = ReportExporter().export(MTDAArtifactCollector(archive_path), profile="minimal")
    full = ReportExporter().export(MTDAArtifactCollector(archive_path), profile="full_html")

    assert set(minimal) == {"reports/test_report.html", "reports/test_report.json"}
    assert "reports/audit_report.html" in full


def test_report_exporter_keeps_legacy_workbench_fallback(tmp_path: Path) -> None:
    archive_path = tmp_path / "legacy.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("report/test_report.html", "<html>test</html>")
        archive.writestr("audit/audit_report.html", "<html>audit</html>")
        archive.writestr("workbench/index.html", "<html>workbench</html>")

    full = ReportExporter().export(MTDAArtifactCollector(archive_path), profile="full_html")

    assert full["reports/test_report.html"] == b"<html>test</html>"
    assert "workbench/index.html" in full
