from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import audit.audit_report_builder as audit_report_builder
from audit.audit_report_builder import (
    _artifact_links_section,
    _legacy_artifact_links_section,
    _legacy_render_recipe_sections,
    _legacy_technical_appendix,
    _render_recipe_sections,
    _technical_appendix,
)
from html_renderer.context_models import (
    AuditAppendixDetailContext,
    AuditArtifactLinksContext,
    AuditEvidenceAppendicesContext,
    AuditTechnicalAppendixContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_audit_artifact_links,
    render_audit_evidence_appendices,
    render_audit_technical_appendix,
)


def test_audit_evidence_appendices_jinja_matches_legacy_renderer_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = SimpleNamespace(warnings=[{"message": "calibration required", "severity": "warn"}])
    recipe = {
        "views": [
            {
                "id": "curve_review",
                "title": "Curve review",
                "components": [{"id": "component_panel", "type": "stub"}],
            }
        ]
    }

    def fake_render_component(result, component, curve_rows, specs):  # noqa: ANN001
        specs[str(component["id"])] = {"source": "fake"}
        return '<h3>Component panel</h3><div id="component_panel" class="chart"></div>'

    monkeypatch.setattr(audit_report_builder, "_render_component", fake_render_component)
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    jinja_specs: dict[str, dict[str, str]] = {}
    legacy_specs: dict[str, dict[str, str]] = {}
    html = _render_recipe_sections(result, recipe, [], jinja_specs)
    legacy_html = _legacy_render_recipe_sections(result, recipe, [], legacy_specs)
    context = audit_report_builder._audit_evidence_appendices_context(result, recipe, [], {})

    assert html == legacy_html
    assert context.section_heading_html == Markup("<h2>Evidence Appendices</h2>")
    assert context.note_html == Markup(
        '<p class="appendix-note">These appendices preserve the raw method evidence for traceability. '
        "Use the Method Development Workbench for operation-by-operation replay and graph inspection.</p>"
    )
    assert context.details[0].detail_html == Markup(
        '<details class="audit-details" id="curve_review"><summary>Curve review</summary>'
        '<div><h3>Component panel</h3><div id="component_panel" class="chart"></div></div></details>'
    )
    assert jinja_specs == legacy_specs == {"component_panel": {"source": "fake"}}
    assert '<section id="audit_evidence_appendices">' in html
    assert '<details class="audit-details" id="curve_review">' in html
    assert '<summary>Warnings</summary><div><div class="table-wrap"><table>' in html


def test_audit_artifact_links_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "artifact_links": {
            "test_report": "test_report.html",
            "method_development_workbench": "workbench/index.html",
        }
    }

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _artifact_links_section(payload)
    context = audit_report_builder._audit_artifact_links_context(payload)

    assert html == _legacy_artifact_links_section(payload)
    assert context.section_heading_html == Markup("<h2>Artifact Links</h2>")
    assert html.startswith('<section id="artifact_links"><h2>Artifact Links</h2>')
    assert "Method Development Workbench" in html
    assert "workbench/index.html" in html


def test_audit_technical_appendix_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    process_sections = '<section id="process"><h2>Process</h2></section>'
    evidence_sections = '<section id="evidence"><h2>Evidence</h2></section>'

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _technical_appendix(process_sections, evidence_sections)
    context = audit_report_builder._audit_technical_appendix_context(process_sections, evidence_sections)

    assert html == _legacy_technical_appendix(process_sections, evidence_sections)
    assert context.section_heading_html == Markup("<h2>Artifact Links / Technical Appendix</h2>")
    assert context.process_detail_html == Markup(
        '<details class="audit-details technical-trace"><summary>Legacy process-verification appendix</summary>'
        '<div><section id="process"><h2>Process</h2></section></div></details>'
    )
    assert 'id="artifact_links_technical_appendix"' in html
    assert '<details class="audit-details technical-trace">' in html
    assert process_sections in html
    assert evidence_sections in html


def test_audit_appendix_renderers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SimpleNamespace(warnings=[])
    recipe = {"views": [{"id": "empty_view", "title": "Empty view", "components": []}]}
    payload = {"artifact_links": {"test_report": "test_report.html"}}

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _render_recipe_sections(result, recipe, [], {}) == _legacy_render_recipe_sections(result, recipe, [], {})
    assert _artifact_links_section(payload) == _legacy_artifact_links_section(payload)
    assert _technical_appendix("<p>process</p>", "<p>evidence</p>") == _legacy_technical_appendix(
        "<p>process</p>",
        "<p>evidence</p>",
    )


def test_audit_appendix_recipe_projections_are_explicit() -> None:
    appendices_projection = projection_for(RecipeResultKind.AUDIT_EVIDENCE_APPENDICES)
    links_projection = projection_for(RecipeResultKind.AUDIT_ARTIFACT_LINKS)
    technical_projection = projection_for(RecipeResultKind.AUDIT_TECHNICAL_APPENDIX)

    assert appendices_projection.context_model == "AuditEvidenceAppendicesContext"
    assert appendices_projection.template_name == "sections/audit/evidence_appendices.html.j2"
    assert appendices_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert links_projection.context_model == "AuditArtifactLinksContext"
    assert links_projection.template_name == "sections/audit/artifact_links.html.j2"
    assert technical_projection.context_model == "AuditTechnicalAppendixContext"

    appendices_html = render_audit_evidence_appendices(
        AuditEvidenceAppendicesContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_APPENDICES,
            section_heading_html=Markup("<h2>Evidence Appendices</h2>"),
            note_html=Markup("<p>Note</p>"),
            details=(
                AuditAppendixDetailContext(
                    detail_class="audit-details",
                    detail_id_html=Markup("view"),
                    summary_html=Markup("View"),
                    body_html=Markup("<p>Body</p>"),
                    detail_html=Markup(
                        '<details class="audit-details" id="view"><summary>View</summary>'
                        "<div><p>Body</p></div></details>"
                    ),
                ),
            ),
        )
    )
    links_html = render_audit_artifact_links(
        AuditArtifactLinksContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_ARTIFACT_LINKS,
            section_heading_html=Markup("<h2>Artifact Links</h2>"),
            table_html=Markup("<p>links</p>"),
        )
    )
    technical_html = render_audit_technical_appendix(
        AuditTechnicalAppendixContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
            section_heading_html=Markup("<h2>Technical</h2>"),
            purpose_html=Markup("<p>purpose</p>"),
            process_sections_html=Markup("<p>process</p>"),
            evidence_sections_html=Markup("<p>evidence</p>"),
            process_detail_html=Markup(
                '<details class="audit-details technical-trace"><summary>Legacy process-verification appendix</summary>'
                "<div><p>process</p></div></details>"
            ),
            evidence_detail_html=Markup(
                '<details class="audit-details technical-trace"><summary>Operation evidence appendices</summary>'
                "<div><p>evidence</p></div></details>"
            ),
        )
    )

    assert '<details class="audit-details" id="view">' in appendices_html
    assert '<section id="artifact_links"><h2>Artifact Links</h2><p>links</p></section>' == links_html
    assert '<summary>Operation evidence appendices</summary><div><p>evidence</p></div>' in technical_html


def test_audit_appendix_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditEvidenceAppendicesContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_APPENDICES,
            section_heading_html=Markup(""),
            note_html=Markup(""),
            details=(),
        )

    with pytest.raises(ValueError, match="audit_artifact_links"):
        AuditArtifactLinksContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            section_heading_html=Markup(""),
            table_html=Markup("<p>links</p>"),
        )

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        AuditAppendixDetailContext(
            detail_class="audit-details",
            summary_html=Markup("View"),
            body_html="<p>Body</p>",
            detail_html=Markup(""),
        )

    with pytest.raises(ValueError, match="detail_html must be an HTML-safe Markup fragment"):
        AuditAppendixDetailContext(
            detail_class="audit-details",
            summary_html=Markup("View"),
            body_html=Markup("<p>Body</p>"),
            detail_html="<details></details>",
        )

    with pytest.raises(ValueError, match="table_html must be an HTML-safe Markup fragment"):
        AuditArtifactLinksContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_ARTIFACT_LINKS,
            section_heading_html=Markup(""),
            table_html="<p>links</p>",
        )

    with pytest.raises(ValueError, match="process_sections_html must be an HTML-safe Markup fragment"):
        AuditTechnicalAppendixContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
            section_heading_html=Markup(""),
            purpose_html=Markup("<p>purpose</p>"),
            process_sections_html="<p>process</p>",
            evidence_sections_html=Markup("<p>evidence</p>"),
            process_detail_html=Markup(""),
            evidence_detail_html=Markup(""),
        )

    with pytest.raises(ValueError, match="purpose_html must be an HTML-safe Markup fragment"):
        AuditTechnicalAppendixContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
            section_heading_html=Markup(""),
            purpose_html="<p>purpose</p>",
            process_sections_html=Markup("<p>process</p>"),
            evidence_sections_html=Markup("<p>evidence</p>"),
            process_detail_html=Markup(""),
            evidence_detail_html=Markup(""),
        )
