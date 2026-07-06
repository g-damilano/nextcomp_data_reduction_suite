from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"
REMOVED_RUN_PAGE = "dataset/02_processed/run_001_" + "summary.html"


def test_mtda_writer_emits_aligned_self_contained_layout(tmp_path: Path) -> None:
    before = _sha256(INPUT)
    output = tmp_path / "analysis.mtda"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--input",
            str(INPUT),
            "--method",
            str(METHOD),
            "--mapping",
            str(MAPPING),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Wrote" in completed.stdout
    assert _sha256(INPUT) == before

    with zipfile.ZipFile(output) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {name.split("/", 1)[0] for name in names} <= {"index.html", "dataset", "metadata"}
        assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
        assert not any(member in names for member in MTDAAlignedLayout.removed_standard_members)

        required = {
            "index.html",
            "metadata/manifest.json",
            "metadata/schema.json",
            "metadata/dataset.json",
            "metadata/provenance.json",
            "metadata/surface_manifest.json",
            "metadata/software/validation.json",
            "metadata/software/readiness.json",
            "metadata/software/method_outputs.json",
            "metadata/checksums.json",
            "dataset/00_raw/run_001_raw.csv",
            "dataset/01_normalized/run_001_normalized.csv",
            "dataset/02_processed/run_001_browser.html",
            "dataset/02_processed/run_001_stress_strain.csv",
            "dataset/02_processed/run_001_stress_strain_experiment_bound.csv",
            "dataset/02_processed/run_001_bending.csv",
            "dataset/02_processed/run_001_plot.html",
            "dataset/02_processed/run_001_plot.plot_package.json",
            "dataset/02_processed/run_001_plot.template.json",
            "dataset/02_processed/run_001_plot_manifest.csv",
            "dataset/03_aggregate/dataset_plot.html",
            "dataset/03_aggregate/dataset_plot.plot_package.json",
            "dataset/03_aggregate/dataset_plot.template.json",
            "dataset/03_aggregate/dataset_plot_manifest.csv",
            "dataset/03_aggregate/results_table.csv",
            "dataset/03_aggregate/statistics.csv",
            "dataset/03_aggregate/stress_strain_aligned.csv",
            "dataset/04_reports/test_report.html",
            "dataset/04_reports/test_report_shell.html",
            "dataset/04_reports/test_report.pdf",
            "dataset/04_reports/test_report.json",
            "dataset/04_reports/audit_report.html",
            "dataset/04_reports/audit_report_shell.html",
            "dataset/04_reports/audit_report.csv",
            "dataset/04_reports/audit_report.json",
        }
        assert required <= names
        assert not any("_plot_data/" in name for name in names)
        assert not any(name.endswith(".vl.json") for name in names)

        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert checksums["algorithm"] == "sha256"
        assert checksums["checksum_member"] == "metadata/checksums.json"
        assert set(checksums["files"]) == names - {"metadata/checksums.json"}

        manifest = json.loads(archive.read("metadata/manifest.json"))
        assert manifest["layout_version"] == MTDAAlignedLayout.name
        assert manifest["artifact_surfaces"] == {
            "home": "index.html",
            "dataset_plot": "dataset/03_aggregate/dataset_plot.html",
            "test_report": "dataset/04_reports/test_report_shell.html",
            "audit_report": "dataset/04_reports/audit_report_shell.html",
            "test_report_raw": "dataset/04_reports/test_report.html",
            "audit_report_raw": "dataset/04_reports/audit_report.html",
            "surface_manifest": "metadata/surface_manifest.json",
            "validation": "metadata/software/validation.json",
            "readiness": "metadata/software/readiness.json",
            "method_outputs": "metadata/software/method_outputs.json",
        }

        surface = json.loads(archive.read("metadata/surface_manifest.json"))
        assert surface["layout_version"] == MTDAAlignedLayout.name
        assert set(surface["surfaces"]) == {
            "home",
            "dataset_plot",
            "processed_data",
            "test_report",
            "audit_report",
            "metadata",
        }
        assert surface["surfaces"]["metadata"]["checksums_member"] == "metadata/checksums.json"
        assert surface["surfaces"]["dataset_plot"]["html_member"] == "dataset/03_aggregate/dataset_plot.html"
        assert surface["surfaces"]["dataset_plot"]["plot_package_member"] == "dataset/03_aggregate/dataset_plot.plot_package.json"
        assert surface["surfaces"]["dataset_plot"]["plot_template_member"] == "dataset/03_aggregate/dataset_plot.template.json"
        assert surface["surfaces"]["dataset_plot"]["projection_recipe"]["projection_id"] == "mtda_dataset_aggregate_compact_package"
        assert surface["surfaces"]["test_report"]["html_member"] == "dataset/04_reports/test_report_shell.html"
        assert surface["surfaces"]["test_report"]["raw_html_member"] == "dataset/04_reports/test_report.html"
        assert surface["surfaces"]["audit_report"]["html_member"] == "dataset/04_reports/audit_report_shell.html"
        assert surface["surfaces"]["audit_report"]["raw_html_member"] == "dataset/04_reports/audit_report.html"

        validation = json.loads(archive.read("metadata/software/validation.json"))
        readiness = json.loads(archive.read("metadata/software/readiness.json"))
        method_outputs = json.loads(archive.read("metadata/software/method_outputs.json"))
        assert validation["layout_version"] == MTDAAlignedLayout.name
        assert readiness["layout_version"] == MTDAAlignedLayout.name
        assert method_outputs["layout_version"] == MTDAAlignedLayout.name
        assert method_outputs["legacy_member_count"] > 0
        assert "operation_trace" in method_outputs

        assert REMOVED_RUN_PAGE not in names
        run_browser_html = archive.read("dataset/02_processed/run_001_browser.html").decode("utf-8")
        assert "run_001_plot.html" in run_browser_html
        assert "dataset/05_plots/" not in run_browser_html


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
