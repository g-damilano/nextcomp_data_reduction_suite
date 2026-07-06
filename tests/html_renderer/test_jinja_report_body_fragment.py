from __future__ import annotations

from pathlib import Path

import pytest
from markupsafe import Markup

from html_renderer.context_models import (
    AuditBlockAnalysisComparisonContext,
    AuditBlockDetailsContext,
    AuditBlockParagraphContext,
    AuditBlockPlotPanelContext,
    AuditBlockSummaryPanelContext,
    AuditBlockTechnicalTraceContext,
    AuditBlockTitledFragmentContext,
    AuditRawEvidenceNoteContext,
    FormalReportBlockContext,
    FormalReportDetailBlockContext,
    FormalReportParagraphContext,
    FormalReportPlotNoteContext,
    FormalReportRawEvidenceNoteContext,
    ReportBodyFragmentContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_audit_block_analysis_comparison,
    render_audit_block_details,
    render_audit_block_paragraph,
    render_audit_block_plot_panel,
    render_audit_block_summary_panel,
    render_audit_block_technical_trace,
    render_audit_block_titled_fragment,
    render_audit_raw_evidence_note,
    render_formal_report_block,
    render_formal_report_detail_block,
    render_formal_report_paragraph,
    render_formal_report_plot_note,
    render_formal_report_raw_evidence_note,
    render_report_body_fragment,
    render_report_empty_paragraph,
    render_report_paragraph_fragment,
)


def test_report_body_fragment_switchboard_has_no_active_template_projection() -> None:
    with pytest.raises(ValueError, match="No HTML projection registered"):
        projection_for(RecipeResultKind.REPORT_BODY_FRAGMENT)


def test_cross_plane_report_components_use_role_first_template_folders() -> None:
    templates_dir = Path(__file__).resolve().parents[2] / "src" / "html_renderer" / "templates"
    partials_dir = templates_dir / "partials"

    assert (templates_dir / "components" / "typography" / "paragraph.html.j2").is_file()
    assert (templates_dir / "components" / "typography" / "heading_fragment.html.j2").is_file()
    assert (templates_dir / "components" / "panels" / "details_panel.html.j2").is_file()
    assert (templates_dir / "components" / "panels" / "container_block.html.j2").is_file()
    assert (templates_dir / "components" / "panels" / "titled_panel.html.j2").is_file()
    assert (templates_dir / "components" / "notes" / "raw_evidence_note.html.j2").is_file()
    assert (templates_dir / "components" / "notes" / "note_marker.html.j2").is_file()
    assert (templates_dir / "components" / "notes" / "note_aside.html.j2").is_file()
    assert (templates_dir / "sections" / "shared" / "methods_appendix.html.j2").is_file()
    assert (templates_dir / "macros" / "tables.html.j2").is_file()
    assert (templates_dir / "macros" / "notes.html.j2").is_file()

    assert not (partials_dir / "shared" / "report_body_fragment.html.j2").exists()
    assert not (partials_dir / "shared" / "report_table_macro.html.j2").exists()
    assert not (partials_dir / "shared" / "report_raw_evidence_note_macro.html.j2").exists()
    assert not (partials_dir / "shared" / "report_note_marker.html.j2").exists()
    assert not (partials_dir / "shared" / "report_note_aside.html.j2").exists()
    assert not (partials_dir / "shared" / "report_methods_appendix.html.j2").exists()
    assert not (partials_dir / "formal_report_raw_evidence_note_macro.html.j2").exists()

    template_text = "\n".join(
        template_path.read_text(encoding="utf-8")
        for template_path in templates_dir.rglob("*.html.j2")
    )

    assert "partials/shared/report_table_macro.html.j2" not in template_text
    assert "partials/shared/report_raw_evidence_note_macro.html.j2" not in template_text
    assert "partials/shared/report_note_marker.html.j2" not in template_text
    assert "partials/shared/report_note_aside.html.j2" not in template_text
    assert "partials/shared/report_methods_appendix.html.j2" not in template_text
    assert "partials/formal_report_raw_evidence_note_macro.html.j2" not in template_text


def test_report_body_fragment_renders_common_block_title_and_paragraph_shapes() -> None:
    block_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="block",
            wrapper_tag="div",
            wrapper_class="block",
            fragment_id_html=Markup("section-id"),
            heading_level=3,
            title_html=Markup("Results"),
            body_html=Markup("<p>Body</p>"),
            paragraph_class="",
        )
    )
    titled_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="titled_fragment",
            wrapper_tag="",
            wrapper_class="",
            fragment_id_html=Markup(""),
            heading_level=4,
            title_html=Markup("Evidence"),
            body_html=Markup("<p>Rows</p>"),
            paragraph_class="",
        )
    )
    paragraph_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="paragraph",
            wrapper_tag="",
            wrapper_class="",
            fragment_id_html=Markup(""),
            heading_level=0,
            title_html=Markup(""),
            body_html=Markup("Missing rows."),
            paragraph_class="plot-unavailable",
        )
    )
    message_block_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="message_block",
            wrapper_tag="div",
            wrapper_class="plot-unavailable",
            fragment_id_html=Markup("missing-plot"),
            heading_level=0,
            title_html=Markup(""),
            body_html=Markup("Missing rows."),
            paragraph_class="",
        )
    )

    assert block_html == '<div class="block" id="section-id"><h3>Results</h3><p>Body</p></div>'
    assert titled_html == "<h4>Evidence</h4><p>Rows</p>"
    assert paragraph_html == '<p class="plot-unavailable">Missing rows.</p>'
    assert message_block_html == '<div class="plot-unavailable" id="missing-plot">Missing rows.</div>'
    assert (
        render_report_paragraph_fragment(
            projection_plane=ProjectionPlane.TEST,
            body_html=Markup("A formal remark."),
        )
        == "<p>A formal remark.</p>"
    )
    assert render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST) == '<p class="muted">No rows.</p>'
    assert (
        render_report_empty_paragraph(
            projection_plane=ProjectionPlane.AUDIT,
            message_html=Markup("No runs recorded."),
        )
        == '<p class="muted">No runs recorded.</p>'
    )
    assert (
        render_report_empty_paragraph(
            projection_plane=ProjectionPlane.TEST,
            message_html=Markup("No remarks were supplied in the report data."),
            paragraph_class="empty-note",
        )
        == '<p class="empty-note">No remarks were supplied in the report data.</p>'
    )
    assert (
        render_report_empty_paragraph(projection_plane=ProjectionPlane.AUDIT, paragraph_class="")
        == "<p>No rows.</p>"
    )


def test_report_body_fragment_renders_detail_wrapper_shapes() -> None:
    formal_detail_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="formal_detail",
            wrapper_tag="details",
            wrapper_class="detail-block",
            fragment_id_html=Markup("detail"),
            heading_level=0,
            title_html=Markup("Detail"),
            body_html=Markup("<p>Body</p>"),
            paragraph_class="",
            marker_html=Markup("<span>marker</span>"),
            purpose_html=Markup("<p>Purpose</p>"),
            note_html=Markup("<aside>Note</aside>"),
            row_count=2,
        )
    )
    audit_detail_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="audit_detail",
            wrapper_tag="div",
            wrapper_class="audit-block",
            fragment_id_html=Markup("block"),
            heading_level=0,
            title_html=Markup("Audit"),
            body_html=Markup("<p>Body</p>"),
            paragraph_class="",
            marker_html=Markup("<span>marker</span>"),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
            note_html=Markup("<aside>Note</aside>"),
            data_block_type_html=Markup("aggregate"),
        )
    )
    details_block_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="details_block",
            wrapper_tag="details",
            wrapper_class="audit-details",
            fragment_id_html=Markup(""),
            heading_level=0,
            title_html=Markup("Source MTDP"),
            body_html=Markup("<table></table>"),
            paragraph_class="",
            marker_html=Markup(" evidence detail"),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
        )
    )
    open_details_block_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="open_details_block",
            wrapper_tag="details",
            wrapper_class="audit-details",
            fragment_id_html=Markup("block"),
            heading_level=0,
            title_html=Markup("Audit block"),
            body_html=Markup("<table></table>"),
            paragraph_class="",
            marker_html=Markup(' <span class="muted">recorded</span>'),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
        )
    )

    assert formal_detail_html == (
        '<details class="detail-block" id="detail" open>\n'
        '  <summary>Detail<span>marker</span> <span class="muted">(2 rows)</span></summary>\n'
        '  <div class="detail-body"><p>Purpose</p><p>Body</p><aside>Note</aside></div>\n'
        "</details>"
    )
    assert audit_detail_html == (
        '<div class="audit-block" id="block" data-block-type="aggregate"><h3>Audit<span>marker</span></h3>'
        '<p class="audit-purpose">Purpose</p><p>Body</p><aside>Note</aside></div>'
    )
    assert details_block_html == (
        '<details class="audit-details"><summary>Source MTDP evidence detail</summary>'
        '<div><p class="audit-purpose">Purpose</p><table></table></div></details>'
    )
    assert open_details_block_html == (
        '<details class="audit-details" id="block" open>'
        '<summary>Audit block <span class="muted">recorded</span></summary>'
        '<div><p class="audit-purpose">Purpose</p><table></table></div></details>'
    )


def test_report_body_fragment_renders_raw_evidence_note_shapes() -> None:
    formal_note_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="raw_evidence_note",
            wrapper_tag="",
            wrapper_class="",
            fragment_id_html=Markup(""),
            heading_level=0,
            title_html=Markup("Raw evidence"),
            body_html=Markup("MTDA report CSV/JSON artifacts"),
            paragraph_class="muted",
            marker_html=Markup(""),
            note_html=Markup(
                " and in the Workbench evidence view; it is not duplicated here as a raw debug table."
            ),
            row_count=2,
        )
    )
    audit_note_html = render_report_body_fragment(
        ReportBodyFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.REPORT_BODY_FRAGMENT,
            fragment_kind="raw_evidence_note",
            wrapper_tag="",
            wrapper_class="",
            fragment_id_html=Markup(""),
            heading_level=0,
            title_html=Markup("Raw evidence"),
            body_html=Markup("MTDA audit/workbench artifacts"),
            paragraph_class="muted",
            marker_html=Markup(" archived"),
            note_html=Markup(". It is summarized here to keep the Audit Report reviewable."),
            row_count=3,
        )
    )

    assert formal_note_html == (
        '<p class="muted">Raw evidence is preserved in the MTDA report CSV/JSON artifacts (2 rows) '
        "and in the Workbench evidence view; it is not duplicated here as a raw debug table.</p>"
    )
    assert audit_note_html == (
        '<p class="muted">Raw evidence is preserved in the MTDA audit/workbench artifacts '
        "(3 rows archived). It is summarized here to keep the Audit Report reviewable.</p>"
    )


def test_formal_and_audit_body_fragment_renderers_delegate_to_shared_shape() -> None:
    assert render_formal_report_block(
        FormalReportBlockContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BLOCK,
            block_id_html=Markup("block"),
            title_html=Markup("Title"),
            content_html=Markup("<p>Body</p>"),
        )
    ) == '<div class="block" id="block"><h3>Title</h3><p>Body</p></div>'
    assert render_formal_report_paragraph(
        FormalReportParagraphContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
            paragraph_class="muted",
            body_html=Markup("No rows."),
        )
    ) == '<p class="muted">No rows.</p>'
    assert render_formal_report_plot_note(
        FormalReportPlotNoteContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
            message_html=Markup("Offline"),
        )
    ) == '<p class="plot-note">Offline</p>'
    assert render_formal_report_raw_evidence_note(
        FormalReportRawEvidenceNoteContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
            title_html=Markup("Raw evidence"),
            row_count=2,
        )
    ) == (
        '<p class="muted">Raw evidence is preserved in the MTDA report CSV/JSON artifacts (2 rows) '
        "and in the Workbench evidence view; it is not duplicated here as a raw debug table.</p>"
    )
    assert render_formal_report_detail_block(
        FormalReportDetailBlockContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
            classes="detail-block",
            block_id_html=Markup("detail"),
            title_html=Markup("Detail"),
            marker_html=Markup("<span>marker</span>"),
            row_count=2,
            body_note_html=Markup("<p>Purpose</p>"),
            content_html=Markup("<p>Body</p>"),
            note_html=Markup("<aside>Note</aside>"),
        )
    ) == (
        '<details class="detail-block" id="detail" open>\n'
        '  <summary>Detail<span>marker</span> <span class="muted">(2 rows)</span></summary>\n'
        '  <div class="detail-body"><p>Purpose</p><p>Body</p><aside>Note</aside></div>\n'
        "</details>"
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
    assert render_audit_raw_evidence_note(
        AuditRawEvidenceNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
            title_html=Markup("Raw evidence"),
            row_count=3,
        )
    ) == (
        '<p class="muted">Raw evidence is preserved in the MTDA audit/workbench artifacts '
        "(3 rows archived). It is summarized here to keep the Audit Report reviewable.</p>"
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
    assert render_audit_block_plot_panel(
        AuditBlockPlotPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
            has_spec=True,
            audit_plot_type_html=Markup("aggregate"),
            plot_id_html=Markup("plot"),
            caption_html=Markup("<p>Caption</p>"),
            warning_html=Markup("<p>Warning</p>"),
            fallback_message_html=Markup(""),
        )
    ) == (
        '<div class="plot-panel" data-audit-plot="aggregate"><div id="plot" class="chart audit-plot"></div>'
        "<p>Caption</p><p>Warning</p></div>"
    )
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
    assert render_audit_block_analysis_comparison(
        AuditBlockAnalysisComparisonContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
            title_html=Markup("Curve residual detail"),
            body_html=Markup("<p>Body</p>"),
        )
    ) == '<div class="analysis-comparison"><h4>Curve residual detail</h4><p>Body</p></div>'


def test_report_body_fragment_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    kwargs = {
        "projection_plane": ProjectionPlane.TEST,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "paragraph",
        "wrapper_tag": "",
        "wrapper_class": "",
        "fragment_id_html": Markup(""),
        "heading_level": 0,
        "title_html": Markup(""),
        "body_html": Markup("Body"),
        "paragraph_class": "",
    }

    with pytest.raises(ValueError, match="test or audit projection planes"):
        ReportBodyFragmentContext(**{**kwargs, "projection_plane": ProjectionPlane.EXPORT_BUNDLE})
    with pytest.raises(ValueError, match="report_body_fragment"):
        ReportBodyFragmentContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_PARAGRAPH})
    with pytest.raises(ValueError, match="known report body fragment variant"):
        ReportBodyFragmentContext(**{**kwargs, "fragment_kind": "surprise"})
    with pytest.raises(ValueError, match="wrapper_tag"):
        ReportBodyFragmentContext(**{**kwargs, "fragment_kind": "block", "wrapper_tag": ""})
    with pytest.raises(ValueError, match="heading_level"):
        ReportBodyFragmentContext(**{**kwargs, "fragment_kind": "titled_fragment", "heading_level": 0})
    with pytest.raises(ValueError, match="paragraph fragments"):
        ReportBodyFragmentContext(**{**kwargs, "heading_level": 3})
    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        ReportBodyFragmentContext(**{**kwargs, "body_html": "Body"})


def test_report_body_fragment_context_rejects_invalid_detail_fragments() -> None:
    formal_kwargs = {
        "projection_plane": ProjectionPlane.TEST,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "formal_detail",
        "wrapper_tag": "details",
        "wrapper_class": "detail-block",
        "fragment_id_html": Markup("detail"),
        "heading_level": 0,
        "title_html": Markup("Detail"),
        "body_html": Markup("<p>Body</p>"),
        "paragraph_class": "",
        "row_count": 1,
    }
    audit_kwargs = {
        "projection_plane": ProjectionPlane.AUDIT,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "audit_detail",
        "wrapper_tag": "div",
        "wrapper_class": "audit-block",
        "fragment_id_html": Markup("block"),
        "heading_level": 0,
        "title_html": Markup("Audit"),
        "body_html": Markup("<p>Body</p>"),
        "paragraph_class": "",
        "data_block_type_html": Markup("aggregate"),
    }
    details_kwargs = {
        "projection_plane": ProjectionPlane.AUDIT,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "details_block",
        "wrapper_tag": "details",
        "wrapper_class": "audit-details",
        "fragment_id_html": Markup(""),
        "heading_level": 0,
        "title_html": Markup("Source MTDP"),
        "body_html": Markup("<table></table>"),
        "paragraph_class": "",
    }

    with pytest.raises(ValueError, match="formal_detail fragments require details wrapper_tag"):
        ReportBodyFragmentContext(**{**formal_kwargs, "wrapper_tag": "div"})
    with pytest.raises(ValueError, match="audit_detail fragments require div wrapper_tag"):
        ReportBodyFragmentContext(**{**audit_kwargs, "wrapper_tag": "section"})
    with pytest.raises(ValueError, match="row_count must be a non-negative integer"):
        ReportBodyFragmentContext(**{**formal_kwargs, "row_count": -1})
    with pytest.raises(ValueError, match="data_block_type_html"):
        ReportBodyFragmentContext(**{**audit_kwargs, "data_block_type_html": Markup("")})
    with pytest.raises(ValueError, match="details block fragments require details wrapper_tag"):
        ReportBodyFragmentContext(**{**details_kwargs, "wrapper_tag": "div"})
    with pytest.raises(ValueError, match="details block fragments require title_html"):
        ReportBodyFragmentContext(**{**details_kwargs, "title_html": Markup("")})
    with pytest.raises(ValueError, match="details block fragments require body_html"):
        ReportBodyFragmentContext(**{**details_kwargs, "body_html": Markup("")})
    with pytest.raises(ValueError, match="marker_html must be an HTML-safe Markup fragment"):
        ReportBodyFragmentContext(**{**formal_kwargs, "marker_html": "<span>marker</span>"})


def test_report_body_fragment_context_rejects_invalid_raw_evidence_notes() -> None:
    kwargs = {
        "projection_plane": ProjectionPlane.TEST,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "raw_evidence_note",
        "wrapper_tag": "",
        "wrapper_class": "",
        "fragment_id_html": Markup(""),
        "heading_level": 0,
        "title_html": Markup("Raw evidence"),
        "body_html": Markup("MTDA report CSV/JSON artifacts"),
        "paragraph_class": "muted",
        "row_count": 2,
    }

    with pytest.raises(ValueError, match="raw evidence note fragments must use heading_level 0"):
        ReportBodyFragmentContext(**{**kwargs, "heading_level": 2})
    with pytest.raises(ValueError, match="raw evidence note fragments must not use wrapper_tag"):
        ReportBodyFragmentContext(**{**kwargs, "wrapper_tag": "div"})
    with pytest.raises(ValueError, match="raw evidence note fragments require title_html"):
        ReportBodyFragmentContext(**{**kwargs, "title_html": Markup("")})
    with pytest.raises(ValueError, match="raw evidence note fragments require body_html"):
        ReportBodyFragmentContext(**{**kwargs, "body_html": Markup("")})
    with pytest.raises(ValueError, match="note_html must be an HTML-safe Markup fragment"):
        ReportBodyFragmentContext(**{**kwargs, "note_html": "tail"})


def test_report_body_fragment_context_rejects_invalid_message_blocks() -> None:
    kwargs = {
        "projection_plane": ProjectionPlane.AUDIT,
        "recipe_result_kind": RecipeResultKind.REPORT_BODY_FRAGMENT,
        "fragment_kind": "message_block",
        "wrapper_tag": "div",
        "wrapper_class": "plot-unavailable",
        "fragment_id_html": Markup(""),
        "heading_level": 0,
        "title_html": Markup(""),
        "body_html": Markup("Missing rows."),
        "paragraph_class": "",
    }

    with pytest.raises(ValueError, match="message block fragments must use heading_level 0"):
        ReportBodyFragmentContext(**{**kwargs, "heading_level": 2})
    with pytest.raises(ValueError, match="message block fragments require a content wrapper_tag"):
        ReportBodyFragmentContext(**{**kwargs, "wrapper_tag": ""})
    with pytest.raises(ValueError, match="message block fragments require wrapper_class"):
        ReportBodyFragmentContext(**{**kwargs, "wrapper_class": ""})
    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        ReportBodyFragmentContext(**{**kwargs, "body_html": "Missing rows."})
