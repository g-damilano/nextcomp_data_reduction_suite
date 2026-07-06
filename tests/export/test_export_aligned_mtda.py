from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.layouts import MTDAAlignedLayout
from export import ExportRequest, ExportService
from methods.core.method_run_service import MethodRunRequest, MethodRunService


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_export_service_consumes_current_aligned_mtda(tmp_path: Path) -> None:
    archive_path = tmp_path / "analysis.mtda"
    run = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=archive_path,
            overwrite=True,
        )
    )

    assert run.status == "completed"
    assert run.audit_report_path == "dataset/04_reports/audit_report.html"
    assert "dataset/04_reports/test_report.html" in run.report_artifacts
    assert run.report_summary["test_report_html"] is True
    assert run.report_summary["audit_report_html"] is True

    with zipfile.ZipFile(archive_path) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
    assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)

    output = tmp_path / "export"
    result = ExportService().export(ExportRequest(archive_path, output, "full_html"))
    manifest = json.loads((output / "export_manifest.json").read_text(encoding="utf-8"))

    assert result.status == "exported"
    assert (output / "reports" / "test_report.html").exists()
    assert (output / "reports" / "audit_report.html").exists()
    assert (output / "tables" / "final_report_runs.csv").exists()
    assert (output / "tables" / "individual_results.csv").exists()
    assert (output / "tables" / "aligned_curves.csv").exists()
    assert (output / "figures" / "aggregate_stress_strain.html").exists()
    assert (output / "figures" / "aggregate_stress_strain_vega.json").exists()
    assert (output / "figures" / "dataset_plot.full_vegalite_spec_with_data.vl.json").exists()
    assert not (output / "figures" / "dataset_plot.vl.json").exists()
    assert not (output / "workbench" / "index.html").exists()
    assert manifest["source_mtdp"]["checksum"]
    assert manifest["selection"]["selection_set"] == "final_report_runs"
    assert manifest["selection"]["selected_run_count"] > 0
