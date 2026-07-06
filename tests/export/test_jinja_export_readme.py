from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.export_service import _legacy_readme_html, _operator_label, _readme_html
from html_renderer.context_models import ExportReadmeContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_export_readme


def test_export_readme_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = dict(
        selection={
            "selected_run_count": "2",
            "selection_source": "human_final",
            "selection_set": "final_report_runs",
        },
        warnings=["Figures are not included in this profile."],
        report_completion={"status": "complete_with_warnings"},
        archive_state={"state": "draft / not finalized"},
    )

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_html = _readme_html("full_html", **kwargs)

    legacy_html = _legacy_readme_html(
        profile_label="Full HTML",
        selected_count="2",
        selection_source=_operator_label("human_final"),
        completion_status=_operator_label("complete_with_warnings"),
        finalization_state=_operator_label("draft / not finalized"),
        selection_set=_operator_label("final_report_runs"),
        warning_count=1,
    )

    assert jinja_html == legacy_html
    assert b'<section class="handoff" aria-label="Export closure summary">' in jinja_html
    assert b'<a class="button" href="reports/test_report.html">Open Test Report</a>' in jinja_html
    assert b'<a class="button secondary" href="export_manifest.json">Export Manifest</a>' in jinja_html
    assert b"method calculations were not rerun" in jinja_html


def test_export_readme_renderer_keeps_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = dict(
        selection={"selected_run_count": "1"},
        warnings=[],
        report_completion={"status": "complete"},
        archive_state={},
    )

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_html = _readme_html("full_html", **kwargs)
    monkeypatch.setenv("MTDA_HTML_RENDERER", "LEGACY")

    assert _readme_html("full_html", **kwargs) == legacy_html


def test_export_readme_recipe_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.EXPORT_README)

    assert projection.context_model == "ExportReadmeContext"
    assert projection.template_name == "pages/export_readme.html.j2"
    assert projection.projection_planes == (ProjectionPlane.EXPORT_BUNDLE,)

    context = _export_context()
    html = render_export_readme(context)

    assert context.projection_plane is ProjectionPlane.EXPORT_BUNDLE
    assert "<title>MTDA Export Bundle</title>" in html
    assert 'href="reports/audit_report.html"' in html


def test_export_readme_context_rejects_wrong_plane_kind_loose_fragments_and_bad_count() -> None:
    kwargs = dict(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_README,
        page_title="MTDA Export Bundle",
        profile_label=Markup("Full HTML"),
        selected_count=Markup("1"),
        selection_source=Markup("Human final"),
        completion_status=Markup("Complete"),
        finalization_state=Markup("Draft / not finalized"),
        selection_set=Markup("Final report runs"),
        warning_count=0,
    )

    with pytest.raises(ValueError, match="export_bundle projection plane"):
        ExportReadmeContext(**{**kwargs, "projection_plane": ProjectionPlane.MTDA_BUNDLE_VIEWER})

    with pytest.raises(ValueError, match="export_readme"):
        ExportReadmeContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.EXPORT_CONTROLS})

    with pytest.raises(ValueError, match="profile_label must be an HTML-safe Markup fragment"):
        ExportReadmeContext(**{**kwargs, "profile_label": "Full HTML"})

    with pytest.raises(ValueError, match="warning_count must be a non-negative integer"):
        ExportReadmeContext(**{**kwargs, "warning_count": -1})


def _export_context() -> ExportReadmeContext:
    return ExportReadmeContext(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_README,
        page_title="MTDA Export Bundle",
        profile_label=Markup("Full HTML"),
        selected_count=Markup("1"),
        selection_source=Markup("Human final"),
        completion_status=Markup("Complete"),
        finalization_state=Markup("Draft / not finalized"),
        selection_set=Markup("Final report runs"),
        warning_count=0,
    )
