from __future__ import annotations

import sys
from pathlib import Path

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audit.audit_block_renderers import (
    _analysis_comparison,
    _audit_block_paragraph,
    _details,
    _inline_note_markup,
    _legacy_analysis_comparison,
    _legacy_audit_block_paragraph,
    _legacy_details,
    _legacy_inline_note_markup,
    _legacy_plot_panel,
    _legacy_plot_unavailable,
    _legacy_render_field_value_table,
    _legacy_render_table,
    _legacy_summary_card,
    _legacy_technical_trace,
    _legacy_titled_fragment,
    _plot_panel,
    _plot_unavailable,
    _residual_detail_plot,
    _summary_card,
    _technical_trace,
    _titled_fragment,
    render_field_value_table,
    render_table,
)
from html_renderer.context_models import (
    AuditBlockAnalysisComparisonContext,
    AuditBlockDetailsContext,
    AuditBlockFieldValueRowContext,
    AuditBlockFieldValueTableContext,
    AuditBlockInlineNoteContext,
    AuditBlockParagraphContext,
    AuditBlockPlotPanelContext,
    AuditBlockSummaryPanelContext,
    AuditBlockTableContext,
    AuditBlockTechnicalTraceContext,
    AuditBlockTitledFragmentContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_audit_block_analysis_comparison,
    render_audit_block_details,
    render_audit_block_field_value_table,
    render_audit_block_inline_note,
    render_audit_block_paragraph,
    render_audit_block_plot_panel,
    render_audit_block_summary_panel,
    render_audit_block_technical_trace,
    render_audit_block_titled_fragment,
)
from plotting.models import PlotResult
from reporting.renderers.formatting_standard import note_html, note_text


def test_audit_block_table_helpers_jinja_match_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    rows = [
        {"run_id": "run_001", "status": "PASS", "technical_payload": {"b": 2, "a": 1}},
        {"run_id": "run_002", "status": "WARN_TRANSIENT_BENDING"},
    ]
    field_rows = [("Run #", "run_001"), ("Bending evidence", "PASS_WITH_SPIKES"), ("Empty", "")]

    assert render_table(rows, fields=["run_id", "status"]) == _legacy_render_table(
        rows,
        fields=["run_id", "status"],
    )
    assert render_table(rows, technical=True) == _legacy_render_table(rows, technical=True)
    assert render_table([]) == _legacy_render_table([])
    assert render_field_value_table(field_rows) == _legacy_render_field_value_table(field_rows)


def test_audit_block_shell_helpers_jinja_match_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    block = {
        "block_id": "aggregate_curve_family",
        "block_type": "aggregate_curve_family",
        "title": "Aggregate Curve Family",
        "purpose": "Explain the aggregate curve.",
        "status": "recorded",
    }
    note_parts = [note_text("method", "Method note."), note_html("figure", "<strong>Figure note.</strong>")]
    trace_block = {
        "operation_refs": [{"sequence": 1, "operation_type": "reduce", "run_id": "run_001"}],
        "evidence_refs": {"aggregate/statistics.csv": "statistics"},
        "links": {"workbench": "workbench/index.html"},
    }

    assert _inline_note_markup(note_parts) == _legacy_inline_note_markup(note_parts)
    assert _details(block, body="<p>Body</p>", default_open=True, note_parts=note_parts) == _legacy_details(
        block,
        body="<p>Body</p>",
        default_open=True,
        note_parts=note_parts,
    )
    assert _summary_card("Evidence conclusion", {"run_id": "run_001", "status": "PASS"}) == _legacy_summary_card(
        "Evidence conclusion",
        {"run_id": "run_001", "status": "PASS"},
    )
    assert _technical_trace(trace_block, extra_rows=[{"payload": {"z": 1}}]) == _legacy_technical_trace(
        trace_block,
        extra_rows=[{"payload": {"z": 1}}],
    )
    assert _technical_trace({}, extra_rows=[]) == _legacy_technical_trace({}, extra_rows=[])
    assert "No traceability rows." in _technical_trace({}, extra_rows=[])


def test_audit_block_body_fragments_jinja_match_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _titled_fragment("Curve-shape <method>", "<p>Body</p>") == _legacy_titled_fragment(
        "Curve-shape <method>",
        "<p>Body</p>",
    )
    assert _audit_block_paragraph("No evidence flags were recorded.") == _legacy_audit_block_paragraph(
        "No evidence flags were recorded."
    )
    assert _audit_block_paragraph("Missing rows.", paragraph_class="plot-unavailable") == _legacy_audit_block_paragraph(
        "Missing rows.",
        paragraph_class="plot-unavailable",
    )
    assert _analysis_comparison("Curve residual detail", "<p>Body</p>") == _legacy_analysis_comparison(
        "Curve residual detail",
        "<p>Body</p>",
    )
    assert _residual_detail_plot(result=object(), specs={}) == (
        '<div class="analysis-comparison"><h4>Curve residual detail</h4>'
        '<p class="plot-unavailable">Curve residual detail unavailable: missing '
        "acceptance/curve_family/curve_diagnostic_residuals.csv. Review the archived residual evidence if needed.</p>"
        "</div>"
    )


def test_audit_block_plot_wrappers_jinja_match_legacy_and_keep_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    spec = {"mark": "line", "usermeta": {"caption": "Aggregate caption"}}
    plot = PlotResult(
        plot_id="aggregate_plot",
        plot_type="aggregate_curve_family",
        status="rendered",
        spec=spec,
        warnings=["low sample count"],
    )
    fallback = PlotResult(
        plot_id="missing_plot",
        plot_type="aggregate_curve_family",
        status="unavailable",
        fallback_message="Missing aggregate rows.",
    )
    jinja_specs: dict[str, dict[str, object]] = {}
    legacy_specs: dict[str, dict[str, object]] = {}

    assert _plot_panel(plot, specs=jinja_specs, audit_plot_type="aggregate_curve_family") == _legacy_plot_panel(
        plot,
        specs=legacy_specs,
        audit_plot_type="aggregate_curve_family",
    )
    assert jinja_specs == legacy_specs == {"aggregate_plot": spec}
    assert _plot_panel(fallback, specs={}, audit_plot_type="aggregate_curve_family") == _legacy_plot_panel(
        fallback,
        specs={},
        audit_plot_type="aggregate_curve_family",
    )
    assert _plot_unavailable("report/aligned_curves.csv") == _legacy_plot_unavailable("report/aligned_curves.csv")


def test_audit_block_helpers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    rows = [{"run_id": "run_001", "status": "PASS"}]
    block = {"block_id": "block", "block_type": "aggregate", "title": "Block", "purpose": "Purpose"}

    assert render_table(rows) == _legacy_render_table(rows)
    assert render_field_value_table([("Run #", "run_001")]) == _legacy_render_field_value_table([("Run #", "run_001")])
    assert _details(block, body="<p>Body</p>", default_open=False) == _legacy_details(
        block,
        body="<p>Body</p>",
        default_open=False,
    )
    assert _plot_unavailable("missing.csv") == _legacy_plot_unavailable("missing.csv")


def test_audit_block_recipe_projections_are_explicit() -> None:
    expectations = {
        RecipeResultKind.AUDIT_BLOCK_TABLE: (
            "AuditBlockTableContext",
            "components/tables/optional_report_table.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE: (
            "AuditBlockFieldValueTableContext",
            "components/tables/key_value_table.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_DETAILS: ("AuditBlockDetailsContext", "sections/audit/block_details.html.j2"),
        RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE: (
            "AuditBlockInlineNoteContext",
            "components/notes/audit_inline_note.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL: (
            "AuditBlockSummaryPanelContext",
            "components/panels/titled_panel.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE: (
            "AuditBlockTechnicalTraceContext",
            "sections/audit/technical_trace.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT: (
            "AuditBlockTitledFragmentContext",
            "components/typography/heading_fragment.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_PARAGRAPH: (
            "AuditBlockParagraphContext",
            "components/typography/paragraph.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON: (
            "AuditBlockAnalysisComparisonContext",
            "components/panels/titled_panel.html.j2",
        ),
        RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL: (
            "AuditBlockPlotPanelContext",
            "components/plots/audit_plot_panel.html.j2",
        ),
    }

    for kind, (context_model, template_name) in expectations.items():
        projection = projection_for(kind)
        assert projection.context_model == context_model
        assert projection.template_name == template_name
        assert projection.projection_planes == (ProjectionPlane.AUDIT,)


def test_audit_block_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditBlockTableContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TABLE,
            table=None,
            empty_message_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="audit_block_field_value_table"):
        AuditBlockFieldValueTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TABLE,
            rows=(),
            empty_message_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="rows must contain AuditBlockFieldValueRowContext values"):
        AuditBlockFieldValueTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE,
            rows=(Markup("bad"),),
            empty_message_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        AuditBlockDetailsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_DETAILS,
            classes_html=Markup("audit-block"),
            block_id_html=Markup("block"),
            block_type_html=Markup("aggregate"),
            title_html=Markup("Title"),
            marker_html=Markup(""),
            purpose_html=Markup(""),
            body_html="<p>Body</p>",
            note_html=Markup(""),
        )

    with pytest.raises(ValueError, match="paragraphs_html must be a non-empty tuple"):
        AuditBlockInlineNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE,
            label_html=Markup("Method"),
            paragraphs_html=(),
        )

    with pytest.raises(ValueError, match="has_spec must be a boolean"):
        AuditBlockPlotPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
            has_spec="yes",
            audit_plot_type_html=Markup("plot"),
            plot_id_html=Markup("plot"),
            caption_html=Markup(""),
            warning_html=Markup(""),
            fallback_message_html=Markup(""),
        )

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        AuditBlockTitledFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT,
            title_html="Title",
            body_html=Markup("<p>Body</p>"),
        )

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        AuditBlockParagraphContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
            body_html="Body",
        )

    with pytest.raises(ValueError, match="audit_block_analysis_comparison"):
        AuditBlockAnalysisComparisonContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
            title_html=Markup("Title"),
            body_html=Markup("<p>Body</p>"),
        )


def test_audit_block_render_functions_emit_expected_shells() -> None:
    assert render_audit_block_field_value_table(
        AuditBlockFieldValueTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE,
            rows=(AuditBlockFieldValueRowContext(label_html=Markup("Run #"), value_html=Markup("#1")),),
            empty_message_html=Markup("<p>No rows.</p>"),
        )
    ) == (
        '<div class="table-wrap field-value-table"><table><tbody><tr><th scope="row">Run #</th>'
        "<td>#1</td></tr></tbody></table></div>"
    )
    assert render_audit_block_details(
        AuditBlockDetailsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_DETAILS,
            classes_html=Markup("audit-block"),
            block_id_html=Markup("block"),
            block_type_html=Markup("aggregate"),
            title_html=Markup("Title"),
            marker_html=Markup(""),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
            body_html=Markup("<p>Body</p>"),
            note_html=Markup(""),
        )
    ) == (
        '<div class="audit-block" id="block" data-block-type="aggregate"><h3>Title</h3>'
        '<p class="audit-purpose">Purpose</p><p>Body</p></div>'
    )
    assert render_audit_block_inline_note(
        AuditBlockInlineNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE,
            label_html=Markup("Method"),
            paragraphs_html=(Markup("A note."),),
        )
    ) == '<aside class="note" role="note"><div class="note-label">Method</div><p>A note.</p></aside>'
    assert render_audit_block_summary_panel(
        AuditBlockSummaryPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL,
            title_html=Markup("Evidence"),
            table_html=Markup("<p>Table</p>"),
        )
    ) == '<div class="summary-panel"><h4>Evidence</h4><p>Table</p></div>'
    assert render_audit_block_technical_trace(
        AuditBlockTechnicalTraceContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE,
            body_html=Markup("<p>Rows</p>"),
        )
    ) == (
        '<div class="technical-trace"><h4>Technical trace: operation records and artifact links</h4>'
        "<p>Rows</p></div>"
    )
    assert render_audit_block_titled_fragment(
        AuditBlockTitledFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT,
            title_html=Markup("Evidence"),
            body_html=Markup("<p>Rows</p>"),
        )
    ) == "<h4>Evidence</h4><p>Rows</p>"
    assert render_audit_block_paragraph(
        AuditBlockParagraphContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
            body_html=Markup("Missing rows."),
            paragraph_class="plot-unavailable",
        )
    ) == '<p class="plot-unavailable">Missing rows.</p>'
    assert render_audit_block_analysis_comparison(
        AuditBlockAnalysisComparisonContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
            title_html=Markup("Curve residual detail"),
            body_html=Markup("<p>Body</p>"),
        )
    ) == '<div class="analysis-comparison"><h4>Curve residual detail</h4><p>Body</p></div>'
    assert render_audit_block_plot_panel(
        AuditBlockPlotPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
            has_spec=False,
            audit_plot_type_html=Markup(""),
            plot_id_html=Markup(""),
            caption_html=Markup(""),
            warning_html=Markup(""),
            fallback_message_html=Markup("Missing rows."),
        )
    ) == '<div class="plot-unavailable">Missing rows.</div>'
