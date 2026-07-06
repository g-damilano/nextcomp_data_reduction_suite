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
REMOVED_DATASET_PAGE = "dataset/03_aggregate/" + "dataset_" + "report.html"
REMOVED_RUN_PAGE = "dataset/02_processed/run_001_" + "summary.html"
REMOVED_DATASET_PAGE_LINK = '<a href="../03_aggregate/' + "dataset_" + 'report.html">Dataset report</a>'


def test_mtda_writer_emits_aligned_backbone_layout(tmp_path: Path) -> None:
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
        roots = {name.split("/", 1)[0] for name in names}

        assert roots <= {"index.html", "dataset", "metadata"}
        assert not any(member in names for member in MTDAAlignedLayout.removed_standard_members)
        assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)

        required = {
            MTDAAlignedLayout.index,
            MTDAAlignedLayout.manifest,
            MTDAAlignedLayout.schema,
            MTDAAlignedLayout.dataset,
            MTDAAlignedLayout.provenance,
            MTDAAlignedLayout.surface_manifest,
            MTDAAlignedLayout.validation,
            MTDAAlignedLayout.readiness,
            MTDAAlignedLayout.method_outputs,
            MTDAAlignedLayout.checksums,
            f"{MTDAAlignedLayout.normalized_prefix}normalization_registry.csv",
            f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
            f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json",
            f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.template.json",
            f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot_manifest.csv",
            f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv",
            f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv",
            f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
            f"{MTDAAlignedLayout.reports_prefix}test_report.html",
            f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html",
            f"{MTDAAlignedLayout.reports_prefix}test_report.pdf",
            f"{MTDAAlignedLayout.reports_prefix}test_report.json",
            f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
            f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html",
            f"{MTDAAlignedLayout.reports_prefix}audit_report.csv",
            f"{MTDAAlignedLayout.reports_prefix}audit_report.json",
            f"{MTDAAlignedLayout.processed_prefix}run_001_browser.html",
            f"{MTDAAlignedLayout.processed_prefix}run_001_plot.html",
            f"{MTDAAlignedLayout.processed_prefix}run_001_plot.plot_package.json",
            f"{MTDAAlignedLayout.processed_prefix}run_001_plot.template.json",
            f"{MTDAAlignedLayout.processed_prefix}run_001_plot_manifest.csv",
        }
        assert required <= names
        assert not any("plot_data/" in name and name.endswith(".csv") for name in names)
        assert not any(name.endswith(".vl.json") for name in names)

        dataset = json.loads(archive.read(MTDAAlignedLayout.dataset))
        run_order = dataset["run_order"]
        assert run_order
        assert dataset["layout_version"] == MTDAAlignedLayout.name

        raw_members = sorted(name for name in names if name.startswith(MTDAAlignedLayout.raw_prefix))
        normalized_members = sorted(
            name
            for name in names
            if name.startswith(MTDAAlignedLayout.normalized_prefix) and name.endswith("_normalized.csv")
        )
        browser_members = sorted(
            name
            for name in names
            if name.startswith(MTDAAlignedLayout.processed_prefix) and name.endswith("_browser.html")
        )
        full_members = sorted(
            name
            for name in names
            if name.startswith(MTDAAlignedLayout.processed_prefix) and name.endswith("_stress_strain.csv")
        )
        bounded_members = sorted(
            name
            for name in names
            if name.startswith(MTDAAlignedLayout.processed_prefix) and name.endswith("_stress_strain_experiment_bound.csv")
        )
        bending_members = sorted(
            name
            for name in names
            if name.startswith(MTDAAlignedLayout.processed_prefix) and name.endswith("_bending.csv")
        )
        assert len(raw_members) == len(run_order)
        assert len(normalized_members) == len(run_order)
        assert len(browser_members) == len(run_order)
        assert len(full_members) == len(run_order)
        assert len(bounded_members) == len(run_order)
        assert len(bending_members) == len(run_order)

        manifest = json.loads(archive.read(MTDAAlignedLayout.manifest))
        assert manifest["package_format"] == "mtda"
        assert manifest["layout_version"] == MTDAAlignedLayout.name
        assert manifest["entrypoint"] == MTDAAlignedLayout.index
        assert "dataset_" + "report" not in manifest["artifact_surfaces"]
        assert manifest["artifact_surfaces"]["dataset_plot"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
        assert manifest["artifact_surfaces"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
        assert manifest["artifact_surfaces"]["audit_report"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
        assert manifest["artifact_surfaces"]["test_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
        assert manifest["artifact_surfaces"]["audit_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
        assert manifest["artifact_surfaces"]["surface_manifest"] == MTDAAlignedLayout.surface_manifest

        provenance = json.loads(archive.read(MTDAAlignedLayout.provenance))
        assert provenance["source_mtdp"]["checksum"]
        assert len(provenance["runs"]) == len(run_order)
        assert all(row["raw_archive_member"].startswith(MTDAAlignedLayout.raw_prefix) for row in provenance["runs"])
        assert all(row["normalized_archive_member"].startswith(MTDAAlignedLayout.normalized_prefix) for row in provenance["runs"])

        method_outputs = json.loads(archive.read(MTDAAlignedLayout.method_outputs))
        assert method_outputs["layout_version"] == MTDAAlignedLayout.name
        assert "operation_trace" in method_outputs

        surface = json.loads(archive.read(MTDAAlignedLayout.surface_manifest))
        assert surface["layout_version"] == MTDAAlignedLayout.name
        assert set(surface["surfaces"]) == {
            "home",
            "dataset_plot",
            "processed_data",
            "test_report",
            "audit_report",
            "metadata",
        }
        assert surface["surfaces"]["dataset_plot"]["html_member"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
        assert surface["surfaces"]["dataset_plot"]["plot_package_member"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json"
        assert surface["surfaces"]["dataset_plot"]["plot_template_member"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.template.json"
        assert surface["surfaces"]["dataset_plot"]["plot_data_members"] == []
        assert surface["surfaces"]["dataset_plot"]["plot_data_views"]
        assert surface["surfaces"]["dataset_plot"]["projection_recipe"]["projection_id"] == "mtda_dataset_aggregate_compact_package"
        assert surface["surfaces"]["dataset_plot"]["export_semantics"]["settings_only"] == "dataset_plot.settings_only.plot_profile.json"
        assert surface["surfaces"]["dataset_plot"]["export_semantics"]["plot_spec_hydrated_data"] == "dataset_plot.full_vegalite_spec_with_data.vl.json"
        assert surface["surfaces"]["test_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
        assert surface["surfaces"]["test_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
        assert surface["surfaces"]["audit_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
        assert surface["surfaces"]["audit_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
        assert surface["operator_handoff"]["open_test_report_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
        assert surface["operator_handoff"]["open_audit_report_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
        assert len(surface["run_surfaces"]) == len(run_order)
        assert surface["run_surfaces"][0]["browser_html_member"] == f"{MTDAAlignedLayout.processed_prefix}run_001_browser.html"
        assert surface["run_surfaces"][0]["plot_package_member"] == f"{MTDAAlignedLayout.processed_prefix}run_001_plot.plot_package.json"

        package = json.loads(archive.read(f"{MTDAAlignedLayout.processed_prefix}run_001_plot.plot_package.json"))
        template = json.loads(archive.read(f"{MTDAAlignedLayout.processed_prefix}run_001_plot.template.json"))
        assert package["package_type"] == "compact-vegalite-workbench"
        assert package["projection_id"] == "mtda_run_compact_stress_strain_evidence"
        assert package["recipe_version"] == "0.1.0"
        assert package["recipe_schema_version"] == "plot_projection_recipe.v0_1"
        assert package["golden_id"] == "golden_mtda_run_compact_stress_strain_evidence"
        assert package["production_state"] == "production"
        assert package["data_mode"] == "archive_view"
        assert package["view_data_mode"] == "runtime_resolved"
        assert package["embedded_datasets"] == []
        assert package["plot_data_views"]
        assert package["datasets"][0]["format"] == "csv"
        assert package["exports"]["settings_only"] == "run_001_plot.settings_only.plot_profile.json"
        assert package["exports"]["plot_spec_hydrated_data"] == "run_001_plot.full_vegalite_spec_with_data.vl.json"
        assert "values" not in json.dumps(template)

        index_html = archive.read(MTDAAlignedLayout.index).decode("utf-8")
        assert REMOVED_DATASET_PAGE not in index_html
        assert "dataset/03_aggregate/dataset_plot.html" in index_html
        assert "dataset/04_reports/test_report_shell.html" in index_html
        assert "dataset/04_reports/audit_report_shell.html" in index_html
        assert '"hrefPattern": "dataset/02_processed/{run_id}_browser.html"' in index_html
        assert REMOVED_RUN_PAGE not in index_html
        assert "report/" not in index_html
        assert "audit/" not in index_html
        assert "dataset/05_plots/" not in index_html

        run_browser_html = archive.read(f"{MTDAAlignedLayout.processed_prefix}run_001_browser.html").decode("utf-8")
        assert '"kind": "mtda.run.browser"' in run_browser_html
        assert 'window.MTDA_INITIAL_STATE = {"page": "run", "runId": "run_001"};' in run_browser_html
        assert "../../metadata/ui/support.js" in run_browser_html
        assert "run_001_stress_strain.csv" in run_browser_html

        test_report_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}test_report.html").decode("utf-8")
        assert "data-mtda-report-shell" not in test_report_html
        assert "<iframe" not in test_report_html

        audit_report_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}audit_report.html").decode("utf-8")
        assert "data-mtda-report-shell" not in audit_report_html
        assert "<iframe" not in audit_report_html

        test_shell_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html").decode("utf-8")
        assert 'data-mtda-report-shell="test_report"' in test_shell_html
        assert 'src="test_report.html"' in test_shell_html
        assert '<a href="../../index.html">&larr; Archive</a>' in test_shell_html
        assert REMOVED_DATASET_PAGE_LINK not in test_shell_html
        assert '<a href="audit_report_shell.html">Audit report</a>' in test_shell_html
        assert "@media print" in test_shell_html
        assert ".mtda-report-shell-banner{display:none!important}" in test_shell_html

        audit_shell_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html").decode("utf-8")
        assert 'data-mtda-report-shell="audit_report"' in audit_shell_html
        assert 'src="audit_report.html"' in audit_shell_html
        assert '<a href="../../index.html">&larr; Archive</a>' in audit_shell_html
        assert REMOVED_DATASET_PAGE_LINK not in audit_shell_html
        assert '<a href="test_report_shell.html">Test report</a>' in audit_shell_html


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
