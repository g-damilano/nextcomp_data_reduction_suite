from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audit.audit_report_builder import (
    _legacy_raw_evidence_details,
    _legacy_table,
    _raw_evidence_details,
    _table,
)
from html_renderer.context_models import (
    AuditEvidenceTableContext,
    AuditRawEvidenceNoteContext,
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_audit_raw_evidence_note, render_audit_table


def test_audit_table_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "run_id": "run_001",
            "status": "pass",
            "evidence_link": {"href": "#packet-run_001", "label": "Run evidence"},
            "long_text": "x" * 220,
        },
        {"run_id": "run_002", "status": "warn", "extra_field": "added later"},
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _table(rows)

    assert html == _legacy_table(rows)
    assert '<div class="table-wrap"><table>' in html
    assert '<th>Run #</th>' in html
    assert '<a href="#packet-run_001">Run evidence</a>' in html
    assert '<span title="' in html


def test_audit_table_empty_state_jinja_matches_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _table([]) == _legacy_table([])
    assert _table([]) == "<p>No rows.</p>"


def test_audit_raw_evidence_note_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"sequence": 1}, {"sequence": 2}]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _raw_evidence_details("Raw <operation> evidence", rows)

    assert html == _legacy_raw_evidence_details("Raw <operation> evidence", rows)
    assert "Raw &lt;operation&gt; evidence is preserved" in html
    assert "(2 rows archived)" in html


def test_audit_fragment_renderers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"run_id": "run_001", "status": "pass"}]

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _table(rows) == _legacy_table(rows)
    assert _raw_evidence_details("Raw evidence", rows) == _legacy_raw_evidence_details("Raw evidence", rows)


def test_audit_fragment_recipe_projections_are_explicit() -> None:
    table_projection = projection_for(RecipeResultKind.AUDIT_TABLE)
    note_projection = projection_for(RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE)

    assert table_projection.context_model == "AuditEvidenceTableContext"
    assert table_projection.template_name == "components/tables/optional_report_table.html.j2"
    assert table_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert note_projection.context_model == "AuditRawEvidenceNoteContext"
    assert note_projection.template_name == "components/notes/raw_evidence_note.html.j2"
    assert note_projection.projection_planes == (ProjectionPlane.AUDIT,)

    table_html = render_audit_table(
        AuditEvidenceTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            table=AuditTableContext(
                table_class="",
                headers=(AuditTableCellContext(html=Markup("Run #")),),
                rows=(
                    AuditTableRowContext(
                        cells=(AuditTableCellContext(html=Markup("Run 1")),),
                    ),
                ),
            ),
            empty_message_html=Markup("<p>No rows.</p>"),
        )
    )
    note_html = render_audit_raw_evidence_note(
        note_context := AuditRawEvidenceNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
            title_html=Markup("Raw evidence"),
            row_count=3,
        )
    )

    assert '<div class="table-wrap"><table>' in table_html
    assert note_context.artifact_scope_html == Markup("MTDA audit/workbench artifacts")
    assert note_context.row_suffix_html == Markup(" archived")
    assert note_context.paragraph_class == "muted"
    assert "Raw evidence is preserved" in note_html


def test_audit_fragment_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditEvidenceTableContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            table=None,
            empty_message_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="audit_table"):
        AuditEvidenceTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            table=None,
            empty_message_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="empty_message_html must be an HTML-safe Markup fragment"):
        AuditEvidenceTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            table=None,
            empty_message_html="<p>No rows.</p>",
        )

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        AuditRawEvidenceNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
            title_html="Raw evidence",
            row_count=1,
        )

    with pytest.raises(ValueError, match="row_count must be a non-negative integer"):
        AuditRawEvidenceNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
            title_html=Markup("Raw evidence"),
            row_count=-1,
        )
