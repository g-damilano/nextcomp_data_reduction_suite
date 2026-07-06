from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"
REMOVED_DATASET_PAGE = "dataset/03_aggregate/" + "dataset_" + "report.html"
REMOVED_RUN_PAGE = "dataset/02_processed/run_001_" + "summary.html"
REMOVED_DATASET_KEY = "dataset_" + "report"


def _run_method(output: Path, *, renderer: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if renderer is None:
        env.pop("MTDA_HTML_RENDERER", None)
    else:
        env["MTDA_HTML_RENDERER"] = renderer
    return subprocess.run(
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
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def _html_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if name.endswith(".html") and not name.endswith("/")
        }


def _normalize_html_for_renderer_parity(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    text = re.sub(
        r'"createdAt": "20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00"',
        '"createdAt": "<createdAt>"',
        text,
    )
    return text.encode("utf-8")


def test_aligned_mtda_surface_navigation_reports_plots_and_manifest(tmp_path: Path) -> None:
    output = tmp_path / "analysis.mtda"
    completed = _run_method(output)

    assert "Wrote" in completed.stdout

    with zipfile.ZipFile(output) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {name.split("/", 1)[0] for name in names} <= {"index.html", "dataset", "metadata"}
        assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
        assert not any(member in names for member in MTDAAlignedLayout.removed_standard_members)

        required = {
            "index.html",
            "dataset/02_processed/run_001_browser.html",
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
            "dataset/03_aggregate/bending_summary_table.csv",
            "dataset/04_reports/test_report.html",
            "dataset/04_reports/test_report_shell.html",
            "dataset/04_reports/test_report.pdf",
            "dataset/04_reports/test_report.json",
            "dataset/04_reports/audit_report.html",
            "dataset/04_reports/audit_report_shell.html",
            "dataset/04_reports/audit_report.csv",
            "dataset/04_reports/audit_report.json",
            "metadata/surface_manifest.json",
            "metadata/checksums.json",
        }
        assert required <= names
        assert not any("_plot_data/" in name for name in names)
        assert not any(name.endswith(".vl.json") for name in names)

        surface = json.loads(archive.read("metadata/surface_manifest.json"))
        assert surface["layout_version"] == MTDAAlignedLayout.name
        assert REMOVED_DATASET_KEY not in surface["surfaces"]
        assert surface["surfaces"]["dataset_plot"]["html_member"] == "dataset/03_aggregate/dataset_plot.html"
        assert surface["surfaces"]["dataset_plot"]["plot_package_member"] == "dataset/03_aggregate/dataset_plot.plot_package.json"
        assert surface["surfaces"]["dataset_plot"]["projection_recipe"]["projection_id"] == "mtda_dataset_aggregate_compact_package"
        assert surface["surfaces"]["dataset_plot"]["export_semantics"]["data_only"] == "dataset_plot.{dataset_id}.data_only.csv"
        assert surface["surfaces"]["test_report"]["html_member"] == "dataset/04_reports/test_report_shell.html"
        assert surface["surfaces"]["test_report"]["raw_html_member"] == "dataset/04_reports/test_report.html"
        assert surface["surfaces"]["audit_report"]["html_member"] == "dataset/04_reports/audit_report_shell.html"
        assert surface["surfaces"]["audit_report"]["raw_html_member"] == "dataset/04_reports/audit_report.html"
        assert surface["run_surfaces"][0]["browser_html_member"] == "dataset/02_processed/run_001_browser.html"
        assert surface["run_surfaces"][0]["plot_html_member"] == "dataset/02_processed/run_001_plot.html"
        assert surface["run_surfaces"][0]["plot_package_member"] == "dataset/02_processed/run_001_plot.plot_package.json"
        assert surface["run_surfaces"][0]["projection_recipe"]["projection_id"] == "mtda_run_compact_stress_strain_evidence"
        for value in _string_values(surface):
            assert not value.startswith(("report/", "audit/", "software/", "dataset/05_plots/", "interactive_report/"))
            assert "dataset/04_aggregate/" not in value
            assert "dataset/03_processed/" not in value

        package = json.loads(archive.read("dataset/03_aggregate/dataset_plot.plot_package.json"))
        assert package["projection_id"] == "mtda_dataset_aggregate_compact_package"
        assert package["recipe_version"] == "0.1.0"
        assert package["recipe_schema_version"] == "plot_projection_recipe.v0_1"
        assert package["golden_id"] == "golden_mtda_dataset_aggregate_compact_package"
        assert package["production_state"] == "production"
        assert package["projection_contracts"]["staleness_contract"]["stale_if_source_checksum_mismatch"] is True
        assert package["data_mode"] == "archive_view"
        assert package["view_data_mode"] == "runtime_resolved"
        assert package["plot_data_materialization"] == "none"
        assert package["template"]["data"]["__compact_dataset_ref__"] == "dataset_001"
        assert package["embedded_datasets"] == []
        views = {view["dataset_id"]: view for view in package["plot_data_views"]}
        assert views["dataset_001"]["transform_id"] == "aggregate.all_runs_resampled_curve_family.v1"
        assert views["stress_aggregate"]["transform_id"] == "aggregate.stress_band_from_run_grid.v1"
        assert views["bending_summary"]["transform_id"] == "aggregate.bending_summary_passthrough.v1"
        assert views["fmax_distribution"]["transform_id"] == "aggregate.fmax_distribution.v1"
        stress_dataset = next(dataset for dataset in package["datasets"] if dataset["dataset_id"] == "stress_aggregate")
        assert stress_dataset["role"] == "stress_aggregate"
        assert stress_dataset["view_ref"] == "stress_aggregate"
        assert stress_dataset["transform_id"] == "aggregate.stress_band_from_run_grid.v1"
        assert stress_dataset["fields"] == [
            "x_common",
            "mean_stress_MPa",
            "min_stress_MPa",
            "max_stress_MPa",
            "std_stress_MPa",
            "lo_stress_MPa",
            "hi_stress_MPa",
            "run_count",
        ]
        bending_dataset = next(dataset for dataset in package["datasets"] if dataset["dataset_id"] == "bending_summary")
        assert bending_dataset["role"] == "bending_summary"
        assert bending_dataset["view_ref"] == "bending_summary"
        assert bending_dataset["transform_id"] == "aggregate.bending_summary_passthrough.v1"
        assert "dataset/03_aggregate/bending_summary_table.csv" in package["source_refs"]
        bending_csv = archive.read("dataset/03_aggregate/bending_summary_table.csv").decode("utf-8")
        assert "min_bending_percent" in bending_csv
        assert "q1_bending_percent" in bending_csv
        assert "q3_bending_percent" in bending_csv
        assert "max_bending_percent" in bending_csv
        for row in csv.DictReader(io.StringIO(bending_csv)):
            values = [
                float(row["min_bending_percent"]),
                float(row["q1_bending_percent"]),
                float(row["median_bending_percent"]),
                float(row["q3_bending_percent"]),
                float(row["max_bending_percent"]),
            ]
            assert values == sorted(values)
        run_bending_csv = archive.read("dataset/02_processed/run_001_bending.csv").decode("utf-8")
        run_bending_rows = list(csv.DictReader(io.StringIO(run_bending_csv)))
        assert "bending_percent" in run_bending_rows[0]
        assert any(float(row["bending_percent"] or 0) > 0 for row in run_bending_rows)
        fmax_dataset = next(dataset for dataset in package["datasets"] if dataset["dataset_id"] == "fmax_distribution")
        assert fmax_dataset["role"] == "fmax_distribution"
        assert fmax_dataset["view_ref"] == "fmax_distribution"
        assert fmax_dataset["transform_id"] == "aggregate.fmax_distribution.v1"
        assert fmax_dataset["fields"] == [
            "x_position",
            "label",
            "min_strength_MPa",
            "q1_strength_MPa",
            "median_strength_MPa",
            "q3_strength_MPa",
            "max_strength_MPa",
            "mean_strength_MPa",
            "std_strength_MPa",
            "run_count",
        ]

        index_html = archive.read("index.html").decode("utf-8")
        assert "MTDA aligned archive" not in index_html
        assert '<script src="metadata/ui/support.js"></script>' in index_html
        assert "window.MTDA_DATA =" in index_html
        assert "window.MTDA_INDEX =" in index_html
        assert '"layout": "mtda.aligned.v1"' in index_html
        assert "HTML pages are generated views" in index_html
        assert "Data & metadata" in index_html
        assert REMOVED_DATASET_PAGE not in index_html
        assert "dataset/03_aggregate/dataset_plot.html" in index_html
        assert "dataset/04_reports/test_report_shell.html" in index_html
        assert "dataset/04_reports/audit_report_shell.html" in index_html
        assert "window.MTDA_PAGE_SPEC =" in index_html
        assert '"kind": "mtda.archive.index"' in index_html
        assert '"hrefPattern": "dataset/02_processed/{run_id}_browser.html"' in index_html
        assert REMOVED_RUN_PAGE not in index_html
        assert "dataset/02_processed/run_002_stress_strain.csv" in archive.namelist()
        if '"runCurves": {' in index_html:
            assert '"run_001": {' in index_html
            assert '"run_002": {' in index_html
            assert "activateRun(run)" in index_html
            assert "on: () => { window.location.href = 'dataset/02_processed/' + r.id + '_browser.html'; }" in index_html
            assert "prototype: run_001 only" not in index_html
            assert "This prototype builds run_001 in full" not in index_html
            assert "r.id === 'run_001'" not in index_html
            assert "datasetReportSummary" in index_html
            assert "all ten curves" not in index_html
            assert "This run has no hydrated curve payload" in index_html
            assert "dataset/00_raw" in index_html
            assert "dataset/01_normalized" in index_html
            assert "dataset/02_processed" in index_html
            assert "runStressHref" in index_html
            assert "finalIncluded" in index_html
            assert "validitySource" in index_html
            assert "max=\"1.8\"" in index_html
            assert "S.scale = this.cleanScale(e.target.value)" in index_html
            assert "Auto blank spot" in index_html
            assert "markerLabelPlacement(m, pos, xScale, yScale, values, markerLabelBoxes, S)" in index_html
            assert "baseline: labelPlace.baseline" in index_html
            assert "<sc-for list=\"{{ layerGroups }}\" as=\"lg\"" in index_html
            assert "defaultLayerGroups()" in index_html
            assert "moveLayerGroup(from, to)" in index_html
            assert "this.sortLayers(layers, 'summary')" in index_html
            assert "this.sortLayers(layers, 'bending')" in index_html
            assert "layergroup:" in index_html

        run_browser_html = archive.read("dataset/02_processed/run_001_browser.html").decode("utf-8")
        assert '<script src="../../metadata/ui/support.js"></script>' in run_browser_html
        assert "window.MTDA_PAGE_SPEC =" in run_browser_html
        assert '"kind": "mtda.run.browser"' in run_browser_html
        assert '"route": "dataset/02_processed/run_001_browser.html"' in run_browser_html
        assert 'window.MTDA_INITIAL_STATE = {"page": "run", "runId": "run_001"};' in run_browser_html
        assert "window.location.href = '../../index.html';" in run_browser_html
        assert "window.location.href = '../03_aggregate/dataset_plot.html';" in run_browser_html
        assert "runStressHref: this.runStressFile()" in run_browser_html
        assert "runStressHref: 'dataset/02_processed/'" not in run_browser_html

        assert REMOVED_DATASET_PAGE not in names

        dataset_plot_html = archive.read("dataset/03_aggregate/dataset_plot.html").decode("utf-8")
        if "<x-dc>" in dataset_plot_html:
            assert "class Component extends DCLogic" in dataset_plot_html
            assert 'data-screen-label="Dataset aggregate studio"' in dataset_plot_html
            assert "window.MTDA_DATA =" in dataset_plot_html
            assert "window.MTDA_BENDING_DIST =" in dataset_plot_html
            assert 'src="data/archive_data.js"' not in dataset_plot_html
            assert "Stress–strain" in dataset_plot_html
            assert "Bending candle" in dataset_plot_html
            assert "CAG-CF-Modied-ULV20 — aggregate compressive stress–strain" in dataset_plot_html
            assert "CAG-CF-Modied-ULV20 — aggregate bending by run" in dataset_plot_html
            assert "8552-IM7 — aggregate compressive stress–strain" not in dataset_plot_html
            assert "Saved looks" in dataset_plot_html
            assert "Export" in dataset_plot_html
            assert "Open data table" in dataset_plot_html
            assert "Open spec editor" in dataset_plot_html
            assert "Titles &amp; labels" in dataset_plot_html
            assert "Axis &amp; range" in dataset_plot_html
            assert "Type · sizes in pt" in dataset_plot_html
            assert "Axes, ticks &amp; grid" in dataset_plot_html
            assert "stress_strain_aligned.csv" in dataset_plot_html
            assert "characteristic_points.csv" in dataset_plot_html
            assert "statistics.csv" in dataset_plot_html
            assert "data/stress_strain_aligned.csv" not in dataset_plot_html
            assert "window.location.href = '../../index.html';" in dataset_plot_html
            assert "const fmaxX = 100;" in dataset_plot_html
            assert "const xMaxDefault = 100;" in dataset_plot_html
            assert "xOffset: { value: -this.spx(8, S) }" not in dataset_plot_html
            assert "name: 'layer_fmax_min_max'" in dataset_plot_html
            assert "name: 'layer_fmax_q1_q3'" in dataset_plot_html
            assert "name: 'layer_fmax_median'" in dataset_plot_html
            assert "mark: { type: 'bar', clip: false" in dataset_plot_html
            assert "name: 'layer_bending_min_max'" in dataset_plot_html
            assert "name: 'layer_bending_q1_q3'" in dataset_plot_html
            assert "name: 'layer_bending_background_hatch'" not in dataset_plot_html
            assert "Threshold background" in dataset_plot_html
            assert "layer_bending_background_fill" in dataset_plot_html
            assert "data: { values: [{ lo: th, hi: yScale.domain[1] }] }" in dataset_plot_html
            assert "hatchDefs()" in dataset_plot_html
            assert "updateHatchOverlay()" in dataset_plot_html
            assert "Hatch is a visual texture over the solid above-threshold assessment fill" in dataset_plot_html
            assert "Hatch settings" in dataset_plot_html
            assert "hatchSettingsOpen" in dataset_plot_html
            assert "hatchOpacity" in dataset_plot_html
            assert "hatchGap" in dataset_plot_html
            assert "hatchWidth" in dataset_plot_html
            assert "hatchAngle" in dataset_plot_html
            assert "hatchScale" in dataset_plot_html
            assert "hatchOffset" in dataset_plot_html
            assert "clipMode" in dataset_plot_html
            assert "mixBlendMode" in dataset_plot_html
            assert "renderer: 'svg'" in dataset_plot_html
            assert "svgHatchPattern" in dataset_plot_html
            assert "data-mtda-hatch-overlay" in dataset_plot_html
            assert "Forward diagonal" in dataset_plot_html
            assert "Dense grid" in dataset_plot_html
            assert "bendingTextureRows(" not in dataset_plot_html
            assert "strokeDash: this.dashArray(L.threshold.dash) ||" not in dataset_plot_html
            assert "finalIncluded" in dataset_plot_html
            assert "this.runIncluded[id] = true" in dataset_plot_html
            assert "onIncluded: e => this.toggleRunIncluded(r.id, e.target.checked)" in dataset_plot_html
            assert "mainRunGroups" in dataset_plot_html
            assert "moveRunGroup(from, to)" in dataset_plot_html
            assert "moveRunToGroup(run, targetGroup)" in dataset_plot_html
            assert "bendingPatternFor(next, this.bendThreshold)" in dataset_plot_html
            assert "colorMode: 'pattern'" in dataset_plot_html
            assert "isBendFig && id === 'box'" in dataset_plot_html
            assert "L[id].colorMode = 'fixed'" in dataset_plot_html
            assert "boxMark.color = L.box.color" in dataset_plot_html
            assert 'draggable="true"' in dataset_plot_html
            assert "moveLayer(from, to)" in dataset_plot_html
            assert "moveLayerGroup(from, to)" in dataset_plot_html
            assert "layergroup:" in dataset_plot_html
            assert "rungroup:" in dataset_plot_html
            assert 'data-drag-token="{{ lc.dragToken }}"' in dataset_plot_html
            assert 'data-drop-token="{{ lc.dropToken }}"' in dataset_plot_html
            assert "setupDragDelegates()" in dataset_plot_html
            assert "applyDragToken(from, to)" in dataset_plot_html
            assert "e.stopPropagation(); e.dataTransfer.setData('text/plain', 'layer:' + id)" in dataset_plot_html
            assert "e.stopPropagation(); e.dataTransfer.setData('text/plain', 'run:' + r.id)" in dataset_plot_html
            assert "defaultLayerGroups()" in dataset_plot_html
            assert "refThreshold: isBendFig && id === 'threshold'" in dataset_plot_html
            assert "refTexture: isBendFig && id === 'hatch'" in dataset_plot_html
            assert "this.bendThreshold = v" in dataset_plot_html
            assert "max=\"1.8\"" in dataset_plot_html
            assert "S.scale = this.cleanScale(e.target.value)" in dataset_plot_html
        else:
            assert 'class="plot-studio"' in dataset_plot_html
            assert "dataset_plot.plot_package.json" in dataset_plot_html
            assert "../../index.html" in dataset_plot_html

        assert REMOVED_RUN_PAGE not in names

        plot_html = archive.read("dataset/02_processed/run_001_plot.html").decode("utf-8")
        assert 'class="mtda-workbench-v14 refined"' in plot_html
        assert 'id="packageSummary"' in plot_html
        assert 'id="layerControls"' in plot_html
        assert 'id="dataFilter"' in plot_html
        assert 'id="importProfile"' in plot_html
        assert 'id="downloadSvg"' in plot_html
        assert 'id="downloadPng"' in plot_html
        assert 'id="downloadSpecExport"' in plot_html
        assert "external CSV data" in plot_html
        assert "settings-only profiles" in plot_html
        assert "MTDA package mode" in plot_html
        assert "settings only" in plot_html
        assert "data only" in plot_html
        assert "plot spec + hydrated data" in plot_html
        assert "compact plot package + data" in plot_html
        assert "Invalid cell value" in plot_html
        assert "run_001_plot.plot_package.json" in plot_html
        assert 'href="../../index.html"' in plot_html

        profile_payload = plot_html[plot_html.index('profile_type:"vega-workbench-plot-profile"'):]
        assert 'schema_version:"0.3"' in profile_payload
        assert "data.values" not in profile_payload

        run_package = json.loads(archive.read("dataset/02_processed/run_001_plot.plot_package.json"))
        run_template = json.loads(archive.read("dataset/02_processed/run_001_plot.template.json"))
        assert run_package["projection_id"] == "mtda_run_compact_stress_strain_evidence"
        assert run_package["recipe_version"] == "0.1.0"
        assert run_package["recipe_schema_version"] == "plot_projection_recipe.v0_1"
        assert run_package["golden_id"] == "golden_mtda_run_compact_stress_strain_evidence"
        assert run_package["production_state"] == "production"
        assert run_package["state_model"]["originalPackage"]
        assert run_package["state_model"]["workingPackage"]
        assert run_package["state_model"]["currentSpec"]
        assert run_package["data_mode"] == "archive_view"
        assert run_package["embedded_datasets"] == []
        assert run_package["datasets"][0]["view_ref"] == "dataset_001"
        assert run_package["datasets"][0]["source_members"] == [
            "dataset/02_processed/run_001_stress_strain_experiment_bound.csv"
        ]
        assert "__compact_dataset_ref__" in json.dumps(run_template)
        assert '"values"' not in json.dumps(run_template)

        report = json.loads(archive.read("dataset/04_reports/test_report.json"))
        assert report["artifacts"] == [
            "dataset/04_reports/test_report.html",
            "dataset/04_reports/test_report.pdf",
            "dataset/04_reports/test_report.json",
        ]
        assert _removed_standard_references(report) == []

        audit = json.loads(archive.read("dataset/04_reports/audit_report.json"))
        assert audit["artifact_links"]["test_report"] == "dataset/04_reports/test_report.html"
        assert REMOVED_DATASET_KEY not in audit["artifact_links"]
        assert audit["artifact_links"]["dataset_plot"] == "dataset/03_aggregate/dataset_plot.html"
        assert audit["artifact_links"]["audit_report"] == "dataset/04_reports/audit_report.html"
        assert audit["artifact_links"]["surface_manifest"] == "metadata/surface_manifest.json"
        assert _removed_standard_references(audit) == []

        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert set(checksums["files"]) == names - {"metadata/checksums.json"}


def test_jinja_production_mtda_html_matches_legacy_archive_bytes(tmp_path: Path) -> None:
    jinja_output = tmp_path / "jinja.mtda"
    legacy_output = tmp_path / "legacy.mtda"

    _run_method(jinja_output)
    _run_method(legacy_output, renderer="legacy")

    jinja_html = _html_members(jinja_output)
    legacy_html = _html_members(legacy_output)

    assert jinja_html.keys() == legacy_html.keys()
    assert jinja_html, "production MTDA archive did not contain HTML members"
    for member, jinja_bytes in sorted(jinja_html.items()):
        assert _normalize_html_for_renderer_parity(jinja_bytes) == _normalize_html_for_renderer_parity(
            legacy_html[member]
        ), f"Jinja HTML diverged from legacy for {member}"


def _removed_standard_references(value: Any, path: str = "$") -> list[tuple[str, str]]:
    removed_prefixes = (
        "report/",
        "audit/",
        "software/",
        "workbench/",
        "interactive_report/",
        "acceptance/",
        "method_outputs/",
        "validation/",
        "readiness/",
    )
    removed_relative = tuple(f"../{prefix}" for prefix in removed_prefixes)
    if isinstance(value, str):
        if value.startswith(removed_prefixes) or value.startswith(removed_relative):
            return [(path, value)]
        return []
    if isinstance(value, list):
        return [
            item
            for index, entry in enumerate(value)
            for item in _removed_standard_references(entry, f"{path}[{index}]")
        ]
    if isinstance(value, dict):
        return [
            item
            for key, entry in value.items()
            for item in _removed_standard_references(entry, f"{path}.{key}")
        ]
    return []


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in _string_values(entry)]
    if isinstance(value, dict):
        return [item for entry in value.values() for item in _string_values(entry)]
    return []
