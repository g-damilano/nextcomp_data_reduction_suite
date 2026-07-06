from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.renderers.vega_static_renderer import _export_vega_html_context, _legacy_vega_html, vega_html
from html_renderer.context_models import ExportVegaHtmlContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_export_vega_html


def test_export_vega_html_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Stress <strain> & aggregate",
        "datasets": {"aggregate": [{"analysis_progress_percent": 100.0, "mean": 240.0, "n": 3}]},
        "mark": "line",
    }

    page = vega_html(spec, title="Aggregate <Stress> & Strain")

    assert page == _legacy_vega_html(spec, title="Aggregate <Stress> & Strain")
    html = page.decode("utf-8")
    assert "<title>Aggregate &lt;Stress&gt; &amp; Strain</title>" in html
    assert '<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>' in html
    assert '<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>' in html
    assert '<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>' in html
    assert '<div id="aggregate-stress-strain"></div>' in html
    assert "vegaEmbed('#aggregate-stress-strain', spec, {actions: true});" in html
    assert f"    const spec = {json.dumps(spec, indent=2, sort_keys=True)};" in html


def test_export_vega_html_renderer_keeps_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = {"mark": "line", "data": {"values": [{"x": 0, "y": 1}]}}
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert vega_html(spec, title="Aggregate") == _legacy_vega_html(spec, title="Aggregate")


def test_export_vega_html_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.EXPORT_VEGA_HTML)
    assert projection.context_model == "ExportVegaHtmlContext"
    assert projection.template_name == "pages/export_vega_html.html.j2"
    assert projection.projection_planes == (ProjectionPlane.EXPORT_BUNDLE,)

    spec = {"mark": "line", "encoding": {"x": {"field": "strain"}}}
    context = _export_vega_html_context(spec, title="Aggregate <Stress>")

    assert context.projection_plane is ProjectionPlane.EXPORT_BUNDLE
    assert context.recipe_result_kind is RecipeResultKind.EXPORT_VEGA_HTML
    assert context.title_html == Markup("Aggregate &lt;Stress&gt;")
    assert context.spec_json == Markup(json.dumps(spec, indent=2, sort_keys=True))

    html = render_export_vega_html(context)
    assert html.startswith("<!doctype html>\n<html lang=\"en\">")
    assert "<h1>Aggregate &lt;Stress&gt;</h1>" in html
    assert "Standalone operator evidence figure exported from the MTDA." in html
    assert "const spec = {\n  \"encoding\"" in html


def test_export_vega_html_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    kwargs = dict(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_VEGA_HTML,
        title_html=Markup("Aggregate"),
        spec_json=Markup('{"mark":"line"}'),
    )

    with pytest.raises(ValueError, match="export_bundle projection plane"):
        ExportVegaHtmlContext(**{**kwargs, "projection_plane": ProjectionPlane.TEST})

    with pytest.raises(ValueError, match="export_vega_html"):
        ExportVegaHtmlContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.EXPORT_HTML_PAGE})

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        ExportVegaHtmlContext(**{**kwargs, "title_html": "Aggregate"})

    with pytest.raises(ValueError, match="spec_json must be an HTML-safe Markup fragment"):
        ExportVegaHtmlContext(**{**kwargs, "spec_json": '{"mark":"line"}'})
