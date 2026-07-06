from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.export_manifest import build_export_manifest


def test_export_manifest_records_source_mtda_and_mtdp(tmp_path: Path) -> None:
    source = tmp_path / "input.mtda"
    source.write_bytes(b"archive")

    manifest = build_export_manifest(
        source_mtda=source,
        profile="minimal",
        source_reference={"source_package": {"path": "input.mtdp", "checksum": "abc"}},
        manifest={"method_id": "iso14126_2023", "method_version": "0.1.0"},
        artifacts=[{"path": "reports/test_report.html", "kind": "html"}],
        selection={"selection_set": "final_report_runs", "selected_run_count": 3},
        warnings=["PDF/DOCX export is deferred"],
    )

    assert manifest["schema_id"] == "mtda.production_export_manifest.v0_1"
    assert manifest["profile"] == "minimal"
    assert manifest["source_mtda"]["checksum"]
    assert manifest["source_mtdp"]["path"] == "input.mtdp"
    assert manifest["selection"]["selection_set"] == "final_report_runs"
    assert manifest["deferred_formats"] == ["pdf", "docx"]
    assert manifest["mtda_mutated"] is False
