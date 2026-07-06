from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.renderers.html_bundle_renderer import _export_html_page_context, _legacy_html_page, html_page
from html_renderer.context_models import ExportHtmlPageContext, ExportHtmlPageMetadataRowContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_export_html_page


def test_export_html_page_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    metadata = {"profile <name>": "full_html & figures", "operator": 'Ada "A"'}
    body = '<section data-raw="yes"><h2>Export body</h2><p>Already-rendered HTML & text.</p></section>'

    page = html_page(title="Export <Bundle> & Report", body=body, metadata=metadata)

    assert page == _legacy_html_page(title="Export <Bundle> & Report", body=body, metadata=metadata)
    decoded = page.decode("utf-8")
    assert "<title>Export &lt;Bundle&gt; &amp; Report</title>" in decoded
    assert "<dt>profile &lt;name&gt;</dt><dd>full_html &amp; figures</dd>" in decoded
    assert '<dd>Ada "A"</dd>' in decoded
    assert body in decoded


def test_export_html_page_renderer_keeps_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert html_page(title="Export", body="<p>Body</p>", metadata={"count": 2}) == _legacy_html_page(
        title="Export",
        body="<p>Body</p>",
        metadata={"count": 2},
    )


def test_export_html_page_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.EXPORT_HTML_PAGE)
    assert projection.context_model == "ExportHtmlPageContext"
    assert projection.template_name == "pages/export_html_page.html.j2"
    assert projection.projection_planes == (ProjectionPlane.EXPORT_BUNDLE,)

    context = _export_html_page_context(title="Export <Bundle>", body="<p>Body</p>", metadata={"operator": "Ada & Bob"})
    assert context.projection_plane is ProjectionPlane.EXPORT_BUNDLE
    assert context.recipe_result_kind is RecipeResultKind.EXPORT_HTML_PAGE
    assert context.title_html == Markup("Export &lt;Bundle&gt;")
    assert context.metadata_rows[0].key_html == Markup("operator")
    assert context.metadata_rows[0].value_html == Markup("Ada &amp; Bob")
    assert context.body_html == Markup("<p>Body</p>")

    html = render_export_html_page(context)
    assert html.startswith("<!doctype html>\n<html lang=\"en\">")
    assert "<h1>Export &lt;Bundle&gt;</h1>" in html
    assert "<dl><dt>operator</dt><dd>Ada &amp; Bob</dd></dl>" in html
    assert "  <p>Body</p>\n</body>" in html


def test_export_html_page_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    row = ExportHtmlPageMetadataRowContext(key_html=Markup("operator"), value_html=Markup("Ada"))
    kwargs = dict(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_HTML_PAGE,
        title_html=Markup("Export"),
        metadata_rows=(row,),
        body_html=Markup("<p>Body</p>"),
    )

    with pytest.raises(ValueError, match="export_bundle projection plane"):
        ExportHtmlPageContext(**{**kwargs, "projection_plane": ProjectionPlane.TEST})

    with pytest.raises(ValueError, match="export_html_page"):
        ExportHtmlPageContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.EXPORT_README})

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        ExportHtmlPageContext(**{**kwargs, "title_html": "Export"})

    with pytest.raises(ValueError, match="metadata_rows must be a tuple"):
        ExportHtmlPageContext(**{**kwargs, "metadata_rows": [row]})

    with pytest.raises(ValueError, match="metadata_rows must contain ExportHtmlPageMetadataRowContext values"):
        ExportHtmlPageContext(**{**kwargs, "metadata_rows": (Markup("operator"),)})

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        ExportHtmlPageContext(**{**kwargs, "body_html": "<p>Body</p>"})

    with pytest.raises(ValueError, match="key_html must be an HTML-safe Markup fragment"):
        ExportHtmlPageMetadataRowContext(key_html="operator", value_html=Markup("Ada"))
