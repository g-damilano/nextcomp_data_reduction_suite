from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from html_renderer.context_models import MtdaFinalizationSectionContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_mtda_finalization_section
from mtda_finalization.finalization_service import (
    _inject_html_notice,
    _legacy_mtda_finalization_section,
    _mtda_finalization_section,
    _mtda_finalization_section_context,
)


def test_mtda_finalization_section_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _mtda_finalization_section("Report <Finalization>", 'Applied & "reviewed"')

    assert html == _legacy_mtda_finalization_section("Report <Finalization>", 'Applied & "reviewed"')
    assert html == (
        '<section class="mtda-finalization"><h2>Report &lt;Finalization&gt;</h2>'
        '<p>Applied &amp; "reviewed"</p></section>'
    )


def test_mtda_finalization_section_keeps_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _mtda_finalization_section("Selection Finalization", "Final report runs: 3") == (
        _legacy_mtda_finalization_section("Selection Finalization", "Final report runs: 3")
    )


def test_mtda_finalization_section_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.MTDA_FINALIZATION_SECTION)
    assert projection.context_model == "MtdaFinalizationSectionContext"
    assert projection.template_name == "sections/shared/finalization_section.html.j2"
    assert projection.projection_planes == (ProjectionPlane.TEST, ProjectionPlane.AUDIT)

    test_context = _mtda_finalization_section_context("Report Finalization", "Applied & reviewed")
    assert test_context.projection_plane is ProjectionPlane.TEST
    assert test_context.recipe_result_kind is RecipeResultKind.MTDA_FINALIZATION_SECTION
    assert test_context.title_html == Markup("Report Finalization")
    assert test_context.body_html == Markup("Applied &amp; reviewed")

    audit_context = _mtda_finalization_section_context(
        "MTDA Finalization",
        "Finalized by operator",
        projection_plane=ProjectionPlane.AUDIT,
    )
    assert audit_context.projection_plane is ProjectionPlane.AUDIT
    assert render_mtda_finalization_section(audit_context) == (
        '<section class="mtda-finalization"><h2>MTDA Finalization</h2>'
        "<p>Finalized by operator</p></section>"
    )


def test_mtda_finalization_section_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.MTDA_FINALIZATION_SECTION,
        title_html=Markup("Report Finalization"),
        body_html=Markup("Applied"),
    )

    with pytest.raises(ValueError, match="test or audit projection planes"):
        MtdaFinalizationSectionContext(**{**kwargs, "projection_plane": ProjectionPlane.EXPORT_BUNDLE})

    with pytest.raises(ValueError, match="mtda_finalization_section"):
        MtdaFinalizationSectionContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.EXPORT_README})

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        MtdaFinalizationSectionContext(**{**kwargs, "title_html": "Report Finalization"})

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        MtdaFinalizationSectionContext(**{**kwargs, "body_html": "Applied"})


def test_inject_html_notice_preserves_insertion_points(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    files = {
        "report.html": b"<html><body><main><p>Existing</p></main></body></html>",
        "audit.html": b"<html><body><p>Existing</p></body></html>",
        "plain.html": b"<p>Existing</p>",
    }

    _inject_html_notice(files, "report.html", "Report Finalization", "Applied <metadata>")
    _inject_html_notice(
        files,
        "audit.html",
        "MTDA Finalization",
        "Finalized & checked",
        projection_plane=ProjectionPlane.AUDIT,
    )
    _inject_html_notice(files, "plain.html", "Selection Finalization", "Final report runs: 2")
    _inject_html_notice(files, "missing.html", "Ignored", "Ignored")

    assert files["report.html"].decode("utf-8") == (
        '<html><body><main><p>Existing</p><section class="mtda-finalization">'
        "<h2>Report Finalization</h2><p>Applied &lt;metadata&gt;</p></section></main></body></html>"
    )
    assert files["audit.html"].decode("utf-8") == (
        '<html><body><p>Existing</p><section class="mtda-finalization">'
        "<h2>MTDA Finalization</h2><p>Finalized &amp; checked</p></section></body></html>"
    )
    assert files["plain.html"].decode("utf-8").endswith(
        '<section class="mtda-finalization"><h2>Selection Finalization</h2>'
        "<p>Final report runs: 2</p></section>"
    )
