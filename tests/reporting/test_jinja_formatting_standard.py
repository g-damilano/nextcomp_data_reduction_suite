from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from html_renderer.context_models import (
    ReportMethodsAppendixContext,
    ReportMethodsAppendixItemContext,
    ReportNoteAsideContext,
    ReportNoteMarkerContext,
    ReportNoteParagraphContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_report_methods_appendix,
    render_report_note_aside,
    render_report_note_marker,
)
from reporting.renderers.formatting_standard import (
    CollectedNote,
    ReportNoteCollector,
    _legacy_render_methods_appendix,
    _legacy_render_note_aside,
    _legacy_render_note_marker,
    note_html,
    note_text,
    render_methods_appendix,
    render_note_aside,
    render_note_marker,
)


def _note() -> CollectedNote:
    return CollectedNote(
        title="Reduction & window",
        label="Method & Figure",
        paragraphs=(
            note_text("method", "Clamp the reduction window."),
            note_html("figure", "<strong>Figure detail.</strong>"),
        ),
    )


def _collector() -> ReportNoteCollector:
    collector = ReportNoteCollector()
    collector.add(
        title="Reduction & window",
        paragraphs=[
            note_text("method", "Clamp the reduction window."),
            note_html("figure", "<strong>Figure detail.</strong>"),
        ],
    )
    return collector


@pytest.mark.parametrize("projection_plane", [ProjectionPlane.TEST, ProjectionPlane.AUDIT])
def test_report_note_marker_jinja_matches_legacy_bytes(projection_plane: ProjectionPlane) -> None:
    assert render_note_marker(projection_plane=projection_plane) == _legacy_render_note_marker()


@pytest.mark.parametrize("projection_plane", [ProjectionPlane.TEST, ProjectionPlane.AUDIT])
def test_report_note_aside_jinja_matches_legacy_bytes(projection_plane: ProjectionPlane) -> None:
    note = _note()

    assert render_note_aside(note, projection_plane=projection_plane) == _legacy_render_note_aside(note)


@pytest.mark.parametrize("projection_plane", [ProjectionPlane.TEST, ProjectionPlane.AUDIT])
def test_report_methods_appendix_jinja_matches_legacy_bytes(projection_plane: ProjectionPlane) -> None:
    collector = _collector()
    legacy_collector = _collector()

    assert render_methods_appendix(collector, projection_plane=projection_plane) == _legacy_render_methods_appendix(
        legacy_collector
    )


def test_report_note_helpers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    note = _note()
    collector = _collector()
    legacy_collector = _collector()
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert render_note_marker(projection_plane=ProjectionPlane.AUDIT) == _legacy_render_note_marker()
    assert render_note_aside(note, projection_plane=ProjectionPlane.AUDIT) == _legacy_render_note_aside(note)
    assert render_methods_appendix(collector, projection_plane=ProjectionPlane.AUDIT) == _legacy_render_methods_appendix(
        legacy_collector
    )


def test_report_note_recipe_projections_are_explicit() -> None:
    marker_projection = projection_for(RecipeResultKind.REPORT_NOTE_MARKER)
    aside_projection = projection_for(RecipeResultKind.REPORT_NOTE_ASIDE)
    appendix_projection = projection_for(RecipeResultKind.REPORT_METHODS_APPENDIX)

    assert marker_projection.context_model == "ReportNoteMarkerContext"
    assert marker_projection.template_name == "components/notes/note_marker.html.j2"
    assert marker_projection.projection_planes == (
        ProjectionPlane.TEST,
        ProjectionPlane.AUDIT,
    )
    assert aside_projection.context_model == "ReportNoteAsideContext"
    assert aside_projection.template_name == "components/notes/note_aside.html.j2"
    assert aside_projection.projection_planes == (
        ProjectionPlane.TEST,
        ProjectionPlane.AUDIT,
    )
    assert appendix_projection.context_model == "ReportMethodsAppendixContext"
    assert appendix_projection.template_name == "sections/shared/methods_appendix.html.j2"
    assert appendix_projection.projection_planes == (
        ProjectionPlane.TEST,
        ProjectionPlane.AUDIT,
    )


def test_report_note_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="TEST or AUDIT"):
        ReportNoteCollector(projection_plane=ProjectionPlane.EXPORT_BUNDLE)
    with pytest.raises(ValueError, match="report_note_marker"):
        ReportNoteMarkerContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_ASIDE,
        )
    with pytest.raises(ValueError, match="TEST or AUDIT"):
        ReportNoteMarkerContext(
            projection_plane=ProjectionPlane.EXPORT_BUNDLE,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_MARKER,
        )
    with pytest.raises(ValueError, match="paragraphs must not be empty"):
        ReportNoteAsideContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_ASIDE,
            label_html=Markup("Method"),
            paragraphs=(),
        )
    with pytest.raises(ValueError, match="items must contain"):
        ReportMethodsAppendixContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_METHODS_APPENDIX,
            heading_html=Markup("Heading"),
            lede_html=Markup("Lede"),
            items=(object(),),  # type: ignore[arg-type]
        )


def test_report_note_render_functions_emit_expected_shells() -> None:
    paragraph = ReportNoteParagraphContext(html=Markup("Body"))

    assert "note-marker" in render_report_note_marker(
        ReportNoteMarkerContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_MARKER,
        )
    )
    assert '<aside class="note" role="note">' in render_report_note_aside(
        ReportNoteAsideContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_NOTE_ASIDE,
            label_html=Markup("Method"),
            paragraphs=(paragraph,),
        )
    )
    assert "methods-appendix" in render_report_methods_appendix(
        ReportMethodsAppendixContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_METHODS_APPENDIX,
            heading_html=Markup("Heading"),
            lede_html=Markup("Lede"),
            items=(
                ReportMethodsAppendixItemContext(
                    title_html=Markup("Title"),
                    label_html=Markup("method"),
                    paragraphs=(paragraph,),
                ),
            ),
        )
    )
