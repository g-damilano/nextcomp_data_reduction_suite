from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export import ExportRequest, ExportService


def test_export_service_minimal_profile_from_small_mtda(tmp_path: Path) -> None:
    import zipfile

    archive_path = tmp_path / "input.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata/manifest.json", json.dumps({"method_id": "iso14126_2023", "method_version": "0.1.0"}))
        archive.writestr("metadata/provenance.json", json.dumps({"source_mtdp": {"path": "input.mtdp", "checksum": "abc"}}))
        archive.writestr("dataset/04_reports/test_report.html", "<html>test report</html>")
        archive.writestr("dataset/04_reports/test_report.json", "{}")
        archive.writestr(
            "dataset/03_aggregate/run_decision_registry.csv",
            "run_id,included,selection_set,selection_source\nrun_001,True,final_report_runs,human_final\n",
        )

    output = tmp_path / "export"
    result = ExportService().export(ExportRequest(archive_path, output, "minimal"))
    manifest = json.loads((output / "export_manifest.json").read_text(encoding="utf-8"))

    assert result.status == "exported"
    assert (output / "reports" / "test_report.html").exists()
    assert (output / "tables" / "final_report_runs.csv").exists()
    assert not (output / "figures" / "aggregate_stress_strain.html").exists()
    assert manifest["selection"]["selected_run_ids"] == ["run_001"]
    assert manifest["source_mtdp"]["path"] == "input.mtdp"
    assert manifest["warnings"]


def test_export_service_full_html_readme_is_operator_handoff(tmp_path: Path) -> None:
    import zipfile

    archive_path = tmp_path / "input.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata/manifest.json", json.dumps({"method_id": "iso14126_2023", "method_version": "0.1.0"}))
        archive.writestr("metadata/provenance.json", json.dumps({"source_mtdp": {"path": "input.mtdp", "checksum": "abc"}}))
        archive.writestr("dataset/04_reports/test_report.html", "<html>test report</html>")
        archive.writestr(
            "dataset/04_reports/test_report.json",
            json.dumps({"report_completion_status": {"status": "COMPLETE_WITH_WARNINGS"}}),
        )
        archive.writestr("dataset/04_reports/audit_report.html", "<html>audit report</html>")
        archive.writestr(
            "dataset/03_aggregate/run_decision_registry.csv",
            "run_id,included,selection_set,selection_source\nrun_001,True,final_report_runs,human_final\nrun_002,False,final_report_runs,human_final\n",
        )

    output = tmp_path / "export"
    result = ExportService().export(ExportRequest(archive_path, output, "full_html"))
    readme = (output / "README.html").read_text(encoding="utf-8")

    assert result.status == "exported"
    assert "Export handoff" in readme
    assert "Loaded" in readme
    assert "Mapped" in readme
    assert "Checked" in readme
    assert "Accepted" in readme
    assert "Completed" in readme
    assert "Exported" in readme
    assert "Final report runs" in readme
    assert "Complete with warnings" in readme
    assert "Draft / not finalized" in readme
    assert "Human final" in readme
    assert "method calculations were not rerun" in readme
