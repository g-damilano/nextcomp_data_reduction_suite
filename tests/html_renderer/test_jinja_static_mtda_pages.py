from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from markupsafe import Markup

from archives.core.layouts import MTDAAlignedLayout
from archives.mtda.writer import (
    _aligned_audit_report_html,
    _aligned_test_report_html,
    _legacy_aligned_audit_report_html,
    _legacy_aligned_test_report_html,
    _handoff_html,
    _handoff_page_spec,
    _handoff_path,
)
from html_renderer.context_models import MtdaHandoffPageContext
from html_renderer.mtda_page_spec import MtdaPageSpec, _SVG_DATA_POINTS_SYNC_SCRIPT, _adapt_handoff_archive_run_studio
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RECIPE_PROJECTIONS, RecipeResultKind, projection_for
from html_renderer.render import render_mtda_handoff_page


def _result() -> SimpleNamespace:
    runs = [SimpleNamespace(run_id="A"), SimpleNamespace(run_id="B")]
    return SimpleNamespace(
        source=SimpleNamespace(
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            runs=runs,
        ),
        method_package=SimpleNamespace(method_id="iso14126_2023", version="0.1.0"),
        specimen_results=[
            {
                "run_id": "A",
                "specimen": "s1",
                "compressive_strength_MPa": 233.03,
                "validity": "accepted",
                "boundary_end_index": 245,
            },
            {
                "run_id": "B",
                "specimen": "s2",
                "compressive_strength_MPa": 203.31,
                "validity": "rejected",
                "boundary_end_policy": "peak_decline_non_recovery",
            },
        ],
    )


def test_static_mtda_archive_pages_are_byte_equivalent_to_legacy_renderers() -> None:
    result = _result()
    test_payload = {"summary": {"strength": 233.03, "validity": "accepted"}}
    audit_payload = {"readiness": {"status": "pass"}}

    assert _aligned_test_report_html(result, test_payload) == _legacy_aligned_test_report_html(result, test_payload)
    assert _aligned_audit_report_html(result, audit_payload) == _legacy_aligned_audit_report_html(result, audit_payload)


def test_static_mtda_pages_keep_legacy_fallback_path(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _result()
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _aligned_test_report_html(result, {"summary": {"strength": 233.03}}) == _legacy_aligned_test_report_html(
        result,
        {"summary": {"strength": 233.03}},
    )


def test_static_page_recipe_projection_mappings_are_explicit() -> None:
    assert projection_for(RecipeResultKind.MTDA_HANDOFF_PAGE).context_model == "MtdaHandoffPageContext"
    assert projection_for(RecipeResultKind.MTDA_HANDOFF_PAGE).projection_planes == (
        ProjectionPlane.MTDA_BUNDLE_VIEWER,
    )
    assert projection_for(RecipeResultKind.TEST_REPORT).projection_planes == (ProjectionPlane.TEST,)
    assert projection_for(RecipeResultKind.AUDIT_REPORT).projection_planes == (ProjectionPlane.AUDIT,)


def test_stale_dataset_and_run_pages_are_not_registered() -> None:
    registered_templates = {projection.template_name for projection in RECIPE_PROJECTIONS.values()}
    removed_dataset_template = "pages/" + "dataset_" + "report.html.j2"
    removed_run_template = "pages/run_" + "summary.html.j2"

    assert removed_dataset_template not in registered_templates
    assert removed_run_template not in registered_templates
    assert not Path("src/html_renderer/templates", removed_dataset_template).exists()
    assert not Path("src/html_renderer/templates", removed_run_template).exists()


def test_mtda_handoff_page_specs_are_complete_for_production_pages() -> None:
    MtdaPageSpec.from_mapping(_handoff_page_spec("archive"))
    MtdaPageSpec.from_mapping(_handoff_page_spec("dataset"))
    MtdaPageSpec.from_mapping(_handoff_page_spec("run", run_label="run_001"))

    incomplete = dict(_handoff_page_spec("archive"))
    incomplete["panels"] = [{"type": "archive_header"}]
    with pytest.raises(ValueError, match="missing required panels"):
        MtdaPageSpec.from_mapping(incomplete)


def test_mtda_handoff_spec_renderer_preserves_legacy_production_output() -> None:
    archive_globals = _handoff_globals("archive")
    dataset_globals = _handoff_globals("dataset")
    run_globals = _handoff_globals("run")

    assert _handoff_html("MTDA Archive.dc.html", page="archive", globals=archive_globals) == _legacy_handoff_html(
        "MTDA Archive.dc.html",
        page="archive",
        globals=archive_globals,
    )
    assert _handoff_html("MTDA Dataset.dc.html", page="dataset", globals=dataset_globals) == _legacy_handoff_html(
        "MTDA Dataset.dc.html",
        page="dataset",
        globals=dataset_globals,
    )
    assert _handoff_html("MTDA Archive.dc.html", page="run", globals=run_globals) == _legacy_handoff_html(
        "MTDA Archive.dc.html",
        page="run",
        globals=run_globals,
    )


def _handoff_globals(page: str) -> dict[str, object]:
    archive_data = {
        "meta": {"datasetName": "CAG-CF-Modied-ULV20"},
        "runs": [{"id": "run_001", "specimen": "CAG-CF-Modied-ULV20-E1", "boundaryEnd": 0}],
        "alignedSeries": [],
        "run001": {"boundaryEnd": 0, "curve": []},
        "runCurves": {"run_001": {"boundaryEnd": 0, "curve": []}},
    }
    archive_index = {"sections": []}
    if page == "dataset":
        return {
            "MTDA_DATA": archive_data,
            "MTDA_BENDING_DIST": [],
            "MTDA_PAGE_SPEC": _handoff_page_spec("dataset"),
        }
    if page == "run":
        return {
            "MTDA_DATA": archive_data,
            "MTDA_METADATA": {},
            "MTDA_INDEX": archive_index,
            "MTDA_PAGE_SPEC": _handoff_page_spec("run", run_label="run_001"),
            "MTDA_INITIAL_STATE": {"page": "run", "runId": "run_001"},
        }
    return {
        "MTDA_DATA": archive_data,
        "MTDA_METADATA": {},
        "MTDA_INDEX": archive_index,
        "MTDA_PAGE_SPEC": _handoff_page_spec("archive"),
    }


def _legacy_handoff_html(filename: str, *, page: str, globals: dict[str, object]) -> str:
    source = _handoff_path(filename).read_text(encoding="utf-8")
    support_path = "metadata/ui/support.js" if page == "archive" else "../../metadata/ui/support.js"
    dataset_name = str(((globals.get("MTDA_DATA") or {}).get("meta") or {}).get("datasetName") or "MTDA")
    globals_script = "\n".join(
        f"window.{name} = {json.dumps(_legacy_json_safe(payload), ensure_ascii=False)};"
        for name, payload in globals.items()
    )
    globals_script = f"{globals_script}\n{_SVG_DATA_POINTS_SYNC_SCRIPT}"
    source = re.sub(r'\n\s*<script src="data/[^"]+\.js"></script>', "", source)
    prefix, marker, suffix = source.partition('<script src="./support.js"></script>')
    assert marker
    source = render_mtda_handoff_page(
        MtdaHandoffPageContext(
            projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
            recipe_result_kind=RecipeResultKind.MTDA_HANDOFF_PAGE,
            prefix_html=Markup(prefix),
            support_path=support_path,
            globals_script=Markup(_legacy_script_safe(globals_script)),
            suffix_html=Markup(suffix),
        )
    )
    if page in {"archive", "run"}:
        aggregate_plot_href = "dataset/03_aggregate/dataset_plot.html" if page == "archive" else "../03_aggregate/dataset_plot.html"
        report_prefix = "dataset/04_reports" if page == "archive" else "../04_reports"
        run_member_prefix = "dataset/02_processed/" if page == "archive" else ""
        source = source.replace("dataset/01_raw", MTDAAlignedLayout.raw_prefix.rstrip("/"))
        source = source.replace("dataset/02_normalized", MTDAAlignedLayout.normalized_prefix.rstrip("/"))
        source = source.replace("dataset/03_processed", MTDAAlignedLayout.processed_prefix.rstrip("/"))
        source = source.replace("dataset/04_aggregate", MTDAAlignedLayout.aggregate_prefix.rstrip("/"))
        source = source.replace(
            "href: (id === 'dataset/03_aggregate' ? 'data/' : 'data/pkg/') + f.name",
            "href: f.href || (id + '/' + f.name)",
        )
        source = source.replace(
            '<div style="font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer;" style-hover="text-decoration: underline;">Test report ↗</div>',
            f'<a href="{report_prefix}/test_report_shell.html" style="display: block; font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer; text-decoration: none;" style-hover="text-decoration: underline;">Test report ↗</a>',
        )
        source = source.replace(
            '<div style="font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer;" style-hover="text-decoration: underline;">Audit report ↗</div>',
            f'<a href="{report_prefix}/audit_report_shell.html" style="display: block; font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer; text-decoration: none;" style-hover="text-decoration: underline;">Audit report ↗</a>',
        )
        source = source.replace("window.location.href = 'MTDA Dataset.dc.html';", f"window.location.href = '{aggregate_plot_href}';")
        for suffix in ("stress_strain.csv", "stress_strain_experiment_bound.csv", "bending.csv"):
            source = source.replace(f"data/run_001_{suffix}", f"{run_member_prefix}run_001_{suffix}")
        source = _adapt_handoff_archive_run_studio(source)
        if page == "archive":
            return source.replace(
                "on: () => this.activateRun(r)",
                "on: () => { window.location.href = 'dataset/02_processed/' + r.id + '_browser.html'; }",
            )
        source = source.replace(
            "on: () => this.activateRun(r)",
            "on: () => { window.location.href = r.id + '_browser.html'; }",
        )
        source = source.replace(
            "goHome: () => this.setState({ page: 'home', exportOpen: false, dataOpen: false, specOpen: false }),",
            "goHome: () => { window.location.href = '../../index.html'; },",
        )
        return source.replace(
            "runStressHref: 'dataset/02_processed/' + this.runStressFile(), runBoundHref: 'dataset/02_processed/' + this.runBoundFile(), runBendingHref: 'dataset/02_processed/' + this.runBendingFile(),",
            "runStressHref: this.runStressFile(), runBoundHref: this.runBoundFile(), runBendingHref: this.runBendingFile(),",
        )

    source = source.replace("8552-IM7 — dataset report · aggregate plot studio", f"{dataset_name} — dataset report · aggregate plot studio")
    source = source.replace("8552-IM7 — aggregate bending by run", f"{dataset_name} — aggregate bending by run")
    source = source.replace("8552-IM7 — aggregate compressive stress–strain", f"{dataset_name} — aggregate compressive stress–strain")
    source = source.replace("window.location.href = 'MTDA Archive.dc.html';", "window.location.href = '../../index.html';")
    for name in ("stress_strain_aligned.csv", "characteristic_points.csv", "statistics.csv"):
        source = source.replace(f"data/{name}", name)
    return source


def _legacy_script_safe(script: str) -> str:
    return script.replace("<script", "<\\x73cript").replace("</script>", "<\\/script>")


def _legacy_json_safe(value: object) -> object:
    import math

    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _legacy_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_legacy_json_safe(item) for item in value]
    return value
