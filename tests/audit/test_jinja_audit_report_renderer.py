from __future__ import annotations

import sys
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import audit.audit_report_builder as audit_builder_module
from audit.audit_report_builder import AuditReportBuilder
from html_renderer.context_models import AuditEvidenceReportContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_audit_evidence_report


def test_audit_report_jinja_frame_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    builder = _controlled_builder(monkeypatch)
    result = _minimal_result()
    kwargs = _minimal_build_inputs()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_html = builder.build(result, **kwargs)

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_html = builder.build(result, **kwargs)

    assert jinja_html == legacy_html
    assert '<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>' in jinja_html
    assert 'class="report-state-card audit-overview-card"' in jinja_html
    assert 'class="report-tracker"' in jinja_html
    assert '<main class="report-content">' in jinja_html
    assert "const specs = {\"demo_plot\": {\"mark\": \"line\"}};" in jinja_html


def test_audit_report_renderer_keeps_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    builder = _controlled_builder(monkeypatch)
    result = _minimal_result()
    kwargs = _minimal_build_inputs()

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_html = builder.build(result, **kwargs)
    monkeypatch.setenv("MTDA_HTML_RENDERER", "LEGACY")

    assert builder.build(result, **kwargs) == legacy_html


def test_audit_report_recipe_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.AUDIT_EVIDENCE_REPORT)

    assert projection.context_model == "AuditEvidenceReportContext"
    assert projection.template_name == "layouts/report_page.html.j2"
    assert projection.projection_planes == (ProjectionPlane.AUDIT,)

    context = _audit_context()
    html = render_audit_evidence_report(context)

    assert context.projection_plane is ProjectionPlane.AUDIT
    assert "<title>Audit Report</title>" in html
    assert '<nav aria-label="Audit report locations"' in html


def test_audit_report_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    kwargs = dict(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_REPORT,
        page_title="Audit Report",
        process_overview_html=Markup("<section></section>"),
        report_tracker_html=Markup("<nav></nav>"),
        grouped_sections_html=Markup("<section></section>"),
        appendix_html=Markup(""),
        vega_specs_json=Markup("{}"),
        formatting_css=Markup(""),
        formatting_script=Markup(""),
    )

    with pytest.raises(ValueError, match="audit projection plane"):
        AuditEvidenceReportContext(**{**kwargs, "projection_plane": ProjectionPlane.TEST})

    with pytest.raises(ValueError, match="audit_evidence_report"):
        AuditEvidenceReportContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.AUDIT_REPORT})

    with pytest.raises(ValueError, match="grouped_sections_html must be an HTML-safe Markup fragment"):
        AuditEvidenceReportContext(**{**kwargs, "grouped_sections_html": "<section></section>"})


def _controlled_builder(monkeypatch: pytest.MonkeyPatch) -> AuditReportBuilder:
    builder = AuditReportBuilder()

    def build_payload(self: AuditReportBuilder, *args: object, **kwargs: object) -> dict[str, object]:
        return {"surface": "audit_report"}

    builder.build_payload = MethodType(build_payload, builder)
    monkeypatch.setattr(
        audit_builder_module,
        "_process_overview",
        lambda payload: '<section id="audit_overview" class="report-state-card audit-overview-card"></section>',
    )
    monkeypatch.setattr(
        audit_builder_module,
        "render_run_index",
        lambda audit_blocks, *, result=None: '<section id="evidence_navigation_run_index"></section>',
    )
    monkeypatch.setattr(
        audit_builder_module,
        "render_run_packets",
        lambda audit_blocks, *, result=None, specs=None: _seed_specs(specs) + '<section id="run_wise_evidence_packets"></section>',
    )
    monkeypatch.setattr(
        audit_builder_module,
        "render_aggregate_packet",
        lambda audit_blocks, *, result=None, specs=None, note_collector=None: '<section id="aggregate_evidence_packet"></section>',
    )
    monkeypatch.setattr(
        audit_builder_module,
        "_decision_register_section",
        lambda result, payload: '<section id="decision_register"></section>',
    )
    monkeypatch.setattr(
        audit_builder_module,
        "render_methods_appendix",
        lambda note_collector, *, projection_plane=None: "",
    )
    monkeypatch.setattr(
        audit_builder_module,
        "_audit_tracker",
        lambda audit_blocks: '<nav aria-label="Audit report locations" class="report-tracker"></nav>',
    )
    monkeypatch.setattr(audit_builder_module, "REPORT_FORMATTING_CSS", "")
    monkeypatch.setattr(audit_builder_module, "REPORT_FORMATTING_SCRIPT", "")
    return builder


def _seed_specs(specs: dict[str, dict[str, object]] | None) -> str:
    if specs is not None:
        specs["demo_plot"] = {"mark": "line"}
    return ""


def _minimal_result() -> SimpleNamespace:
    return SimpleNamespace(source=SimpleNamespace(path=Path("sample.mtdp")))


def _minimal_build_inputs() -> dict[str, object]:
    audit_blocks = {"run_packets": [], "aggregate_packet": {"blocks": []}}
    return {
        "procedure_evidence_index": {"operation_count": 0},
        "audit_block_index": {"summary": {}},
        "audit_blocks": audit_blocks,
    }


def _audit_context() -> AuditEvidenceReportContext:
    return AuditEvidenceReportContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_REPORT,
        page_title="Audit Report",
        process_overview_html=Markup("<section></section>"),
        report_tracker_html=Markup('<nav aria-label="Audit report locations"></nav>'),
        grouped_sections_html=Markup("<section></section>"),
        appendix_html=Markup(""),
        vega_specs_json=Markup("{}"),
        formatting_css=Markup(""),
        formatting_script=Markup(""),
    )
