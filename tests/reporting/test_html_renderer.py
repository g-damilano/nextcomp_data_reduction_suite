from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.core.report_document import ReportBlockDocument, ReportDocument, ReportSectionDocument
from markupsafe import Markup

from html_renderer.context_models import (
    FormalReportAggregateSvgContext,
    FormalReportBooleanBadgeContext,
    FormalReportBlockContext,
    FormalReportDataUseDeviationsContext,
    FormalReportDeviationsSectionContext,
    FormalReportDetailBlockContext,
    FormalReportDimensionHeaderContext,
    FormalReportEvidenceTableContext,
    FormalReportFailureBendingSvgContext,
    FormalReportFieldValueRowContext,
    FormalReportFieldValueTableContext,
    FormalReportFragmentStackContext,
    FormalMethodReportContext,
    FormalReportMissingDataContext,
    FormalReportParagraphContext,
    FormalReportPlotBlockContext,
    FormalReportPlotLegendContext,
    FormalReportPlotNoteContext,
    FormalReportRawEvidenceNoteContext,
    FormalReportRemarksContext,
    FormalReportReviewSectionContext,
    FormalReportSectionContext,
    FormalReportSectionPillContext,
    FormalReportSectionsContext,
    FormalReportStateCardContext,
    FormalReportTableCellContext,
    FormalReportTableContext,
    FormalReportTableRowContext,
    FormalReportTableSectionContext,
    FormalReportTrackerContext,
    FormalReportTrackerLinkContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_formal_report_aggregate_svg,
    render_formal_report_boolean_badge,
    render_formal_report_data_use_deviations,
    render_formal_report_deviations_section,
    render_formal_report_dimension_header,
    render_formal_report_failure_bending_svg,
    render_formal_report_missing_data,
    render_formal_report_plot_block,
    render_formal_report_plot_legend,
    render_formal_report_plot_note,
    render_formal_report_section_pill,
)
from reporting.renderers.formatting_standard import ReportNoteCollector, render_methods_appendix
from reporting.renderers.html_renderer import (
    HtmlRenderer,
    _aggregate_svg,
    _data_use_deviations_table,
    _details,
    _aggregate_statistics_formal,
    _aggregate_statistics_review,
    _deviations_section,
    _deviations_review,
    _field_value_table,
    _failure_analysis_review,
    _failure_bending_svg,
    _feature_lines_review,
    _formal_field_table,
    _formal_report_boolean_badge_context,
    _formal_report_dimension_header_context,
    _formal_report_evidence_table_context,
    _formal_report_block,
    _formal_report_aggregate_svg_context,
    _formal_report_paragraph,
    _formal_report_failure_bending_svg_context,
    _formal_report_plot_block_context,
    _formal_report_plot_legend_context,
    _formal_report_plot_note_context,
    _formal_report_section_pill_context,
    _formal_report_state_card_context,
    _individual_results_table,
    _legacy_aggregate_statistics_formal,
    _legacy_formal_method_report_html,
    _legacy_formal_report_paragraph,
    _legacy_details,
    _legacy_dimension_header,
    _legacy_field_value_table,
    _legacy_failure_bending_svg,
    _legacy_formal_field_table,
    _legacy_formal_report_block,
    _legacy_individual_results_table,
    _legacy_data_use_deviations_table,
    _legacy_deviations_section,
    _legacy_missing_data_table,
    _legacy_raw_evidence_details,
    _legacy_remarks_section,
    _legacy_report_state_card,
    _legacy_report_tracker,
    _legacy_sections,
    _legacy_specimen_geometry_table,
    _legacy_table,
    _legacy_plot_legend,
    _legacy_aggregate_svg,
    _legacy_vega_plot_block,
    _legacy_section_pill,
    _legacy_yes_no,
    _missing_data_table,
    _missing_fields_review,
    _characteristic_points_review,
    _report_state_card,
    _report_tracker,
    _plot_legend,
    _raw_evidence_details,
    _remarks_section,
    _formal_report_review_section_context,
    _sections,
    _specimen_geometry_table,
    _specimen_geometry_table_section_context,
    _table,
    _vega_plot_block,
    _dimension_header,
    _section_pill,
    _yes_no,
)


def test_html_renderer_renders_generic_report_document() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={"method_name": "Demo Method", "selection_set": "selected"},
        sections=[
            ReportSectionDocument(
                id="summary",
                title="Summary",
                blocks=[
                    ReportBlockDocument(
                        id="values",
                        type="field_table",
                        title="Values",
                        provider="report_values",
                        data=[{"label": "Operator", "value": "Ada"}],
                    )
                ],
            )
        ],
    )

    html = HtmlRenderer().render(document)

    assert "<title>Demo Report</title>" in html
    assert "Demo Method" in html
    assert 'class="report-state-card"' in html
    assert 'class="report-tracker"' in html
    assert "Summary" in html
    assert "Operator" in html


def test_formal_report_jinja_frame_matches_legacy_renderer_bytes() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={"method_name": "Demo Method", "selection_set": "selected"},
        sections=[
            ReportSectionDocument(
                id="summary",
                title="Summary",
                blocks=[
                    ReportBlockDocument(
                        id="values",
                        type="field_table",
                        title="Values",
                        provider="report_values",
                        data=[{"label": "Operator", "value": "Ada"}],
                    )
                ],
            )
        ],
    )
    payload = document.to_dict()
    sections = payload.get("sections", [])
    metadata = payload.get("metadata", {})
    note_collector = ReportNoteCollector()
    sections_html = _legacy_sections(sections, metadata, note_collector=note_collector)
    appendix_html = render_methods_appendix(note_collector)

    jinja_html = HtmlRenderer().render(document)
    legacy_html = _legacy_formal_method_report_html(
        payload=payload,
        metadata=metadata,
        sections=sections,
        sections_html=sections_html,
        appendix_html=appendix_html,
    )

    assert jinja_html == legacy_html
    assert '<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>' in jinja_html
    assert 'class="report-state-card"' in jinja_html
    assert 'class="report-tracker"' in jinja_html
    assert '<main class="report-content">' in jinja_html


def test_formal_report_renderer_keeps_legacy_fallback(monkeypatch) -> None:
    document = ReportDocument(report_id="demo", title="Demo Report", metadata={}, sections=[])
    payload = document.to_dict()
    note_collector = ReportNoteCollector()
    sections_html = _legacy_sections([], {}, note_collector=note_collector)
    appendix_html = render_methods_appendix(note_collector)

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert HtmlRenderer().render(document) == _legacy_formal_method_report_html(
        payload=payload,
        metadata={},
        sections=[],
        sections_html=sections_html,
        appendix_html=appendix_html,
    )


def test_formal_report_state_card_and_tracker_jinja_components_match_legacy(monkeypatch) -> None:
    payload = {"title": "Demo 'Report' & <Review>"}
    metadata = {
        "method_name": "Demo Method",
        "standard_reference": "ISO 14126",
        "method_boundary_note": "Bounded window shown from start marker to endpoint.",
        "report_completion_status": "COMPLETE_WITH_WARNINGS",
        "report_quality_gate_status": "RC_WITH_WARNINGS",
        "required_missing_count": 0,
        "recommended_missing_count": 2,
        "selected_run_count": 1,
        "section_statuses": [
            {"section_id": "test_identification", "status": "complete", "missing_recommended_count": 0},
            {"section_id": "deviations_from_standard", "status": "complete_with_warnings", "missing_recommended_count": 2},
        ],
    }
    sections = [
        {"id": "test_identification", "title": "Test Identification", "blocks": []},
        {
            "id": "individual_test_results",
            "title": "Individual Test Results",
            "blocks": [{"id": "individual_results_table", "data": [{"run_id": "run_001"}, {"run_id": "run_002"}]}],
        },
        {"id": "deviations_from_standard", "title": "Deviations from Standard", "blocks": []},
    ]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    state_card = _report_state_card(payload, metadata, sections)
    tracker = _report_tracker(sections, metadata)
    state_context = _formal_report_state_card_context(payload, metadata, sections)

    assert state_card == _legacy_report_state_card(payload, metadata, sections)
    assert tracker == _legacy_report_tracker(sections, metadata)
    assert state_context.lede_html == Markup(
        '<p class="report-state-note">Formal method results and report-ready evidence.</p>'
    )
    assert state_context.method_context_html == Markup(
        '<p class="report-state-note">Demo Method | ISO 14126</p>'
    )
    assert state_context.method_boundary_html == Markup(
        '<p class="report-state-note">Bounded window shown from start marker to endpoint.</p>'
    )
    assert 'id="report-state"' in state_card
    assert "Demo &#x27;Report&#x27; &amp; &lt;Review&gt;" in state_card
    assert 'href="#section-deviations_from_standard"' in tracker
    assert '<em class="pill warn">Review</em>' in tracker


def test_formal_report_component_renderers_keep_legacy_fallback(monkeypatch) -> None:
    payload = {"title": "Demo Report"}
    metadata = {}
    sections = [{"id": "summary", "title": "Summary", "blocks": []}]

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _report_state_card(payload, metadata, sections) == _legacy_report_state_card(payload, metadata, sections)
    assert _report_tracker(sections, metadata) == _legacy_report_tracker(sections, metadata)


def test_formal_report_sections_jinja_shell_matches_legacy_renderer_bytes(monkeypatch) -> None:
    metadata = {
        "recommended_missing_count": 1,
        "section_statuses": [
            {"section_id": "test_identification", "status": "complete", "missing_recommended_count": 0},
            {"section_id": "remarks", "status": "complete", "missing_recommended_count": 0},
            {"section_id": "deviations_from_standard", "status": "complete_with_warnings", "missing_recommended_count": 1},
        ],
    }
    sections = [
        {
            "id": "test_identification",
            "title": "Test Identification",
            "blocks": [
                {
                    "id": "test_identification_fields",
                    "type": "field_table",
                    "title": "Test fields",
                    "data": [{"label": "Laboratory", "value": "NextComp"}],
                }
            ],
        },
        {
            "id": "remarks",
            "title": "Remarks",
            "blocks": [{"id": "remarks_text", "type": "text", "data": {"text": "No remarks."}}],
        },
        {"id": "deviations_from_standard", "title": "Deviations from Standard", "blocks": []},
    ]
    note_collector = ReportNoteCollector()
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    sections_html = _sections(sections, metadata, note_collector=note_collector)
    legacy_html = _legacy_sections(sections, metadata, note_collector=ReportNoteCollector())

    assert sections_html == legacy_html
    assert '<section class="report-section" id="section-test_identification">' in sections_html
    assert "<h2>1. Test Identification</h2>" in sections_html
    assert '<section class="report-section" id="section-deviations_from_standard">' in sections_html
    assert '<em class="pill warn">Review</em>' in sections_html


def test_formal_report_sections_keep_legacy_fallback(monkeypatch) -> None:
    sections = [{"id": "summary", "title": "Summary", "blocks": []}]
    metadata = {}

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _sections(sections, metadata, note_collector=ReportNoteCollector()) == _legacy_sections(
        sections,
        metadata,
        note_collector=ReportNoteCollector(),
    )


def test_formal_report_table_jinja_wrapper_matches_legacy_renderer_bytes(monkeypatch) -> None:
    rows = [
        {"field": "A&B", "value": "<danger>", "status": '<em class="pill ok">OK</em>'},
        {"field": "Width", "value": 12.3456, "status": '<em class="pill warn">Review</em>'},
        ["not", "a", "row"],
    ]
    kwargs = dict(
        columns=["field", "value", "status"],
        headers=["Field", "Value <small>raw</small>", "Status"],
        table_class='results-table "wide"',
        raw_html_columns={"status"},
    )
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _table(rows, **kwargs)

    assert html == _legacy_table(rows, **kwargs)
    assert '<table class="results-table &quot;wide&quot;">' in html
    assert "<td>&lt;danger&gt;</td>" in html
    assert '<td><em class="pill ok">OK</em></td>' in html


def test_formal_report_table_keeps_legacy_fallback(monkeypatch) -> None:
    rows = [{"field": "A&B", "value": "<danger>"}]
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _table(rows) == _legacy_table(rows)


def test_formal_report_detail_block_jinja_wrapper_matches_legacy_renderer_bytes(monkeypatch) -> None:
    kwargs = dict(row_count=2, block_type="table", note_collector=ReportNoteCollector())
    legacy_kwargs = dict(row_count=2, block_type="table", note_collector=ReportNoteCollector())
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _details(
        "failure_analysis_table",
        "Failure <strong>Analysis</strong>",
        "<p>Already rendered body</p>",
        **kwargs,
    )
    legacy_html = _legacy_details(
        "failure_analysis_table",
        "Failure <strong>Analysis</strong>",
        "<p>Already rendered body</p>",
        **legacy_kwargs,
    )

    assert html == legacy_html
    assert '<details class="detail-block audit-block note-anchor" id="failure_analysis_table" open>' in html
    assert '<summary>Failure <strong>Analysis</strong><button type="button" class="note-marker"' in html
    assert '<p class="detail-purpose">' not in html


def test_formal_report_detail_block_keeps_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _details("block", "Title", "<p>Body</p>", row_count=1) == _legacy_details(
        "block",
        "Title",
        "<p>Body</p>",
        row_count=1,
    )


def test_formal_report_detail_purpose_note_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _details("deviations_table", "Deviations", "<p>Rendered body</p>", row_count=3)
    legacy_html = _legacy_details("deviations_table", "Deviations", "<p>Rendered body</p>", row_count=3)

    assert html == legacy_html
    assert '<p class="detail-purpose"><strong>Report review detail.</strong>' in html


def test_formal_report_block_shell_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _formal_report_block("block <id>", "Title <strong>safe</strong>", "<p>Rendered body</p>")

    assert html == _legacy_formal_report_block("block <id>", "Title <strong>safe</strong>", "<p>Rendered body</p>")
    assert '<div class="block" id="block &lt;id&gt;">' in html
    assert "<h3>Title <strong>safe</strong></h3><p>Rendered body</p>" in html


def test_formal_report_block_shell_keeps_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _formal_report_block("block", "Title", "<p>Body</p>") == _legacy_formal_report_block(
        "block",
        "Title",
        "<p>Body</p>",
    )


def test_formal_report_paragraph_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _formal_report_paragraph('Body <a href="#x">link</a>', paragraph_class="muted")

    assert html == _legacy_formal_report_paragraph('Body <a href="#x">link</a>', paragraph_class="muted")
    assert html == '<p class="muted">Body <a href="#x">link</a></p>'
    assert _formal_report_paragraph("Plain body") == "<p>Plain body</p>"


def test_formal_report_paragraph_keeps_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _formal_report_paragraph("Body", paragraph_class="empty-note") == _legacy_formal_report_paragraph(
        "Body",
        paragraph_class="empty-note",
    )


def test_formal_report_inline_fragments_jinja_match_legacy_renderer_bytes(monkeypatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _section_pill(
        "deviations_from_standard",
        {"status": "complete_with_warnings"},
    ) == _legacy_section_pill(
        "deviations_from_standard",
        {"status": "complete_with_warnings"},
    )
    assert _section_pill("summary", {"missing_recommended_count": 2}, tracker=True) == _legacy_section_pill(
        "summary",
        {"missing_recommended_count": 2},
        tracker=True,
    )
    assert _section_pill("summary", {"status": "incomplete"}) == _legacy_section_pill(
        "summary",
        {"status": "incomplete"},
    )
    assert _yes_no(True) == _legacy_yes_no(True)
    assert _yes_no(False) == _legacy_yes_no(False)
    assert _dimension_header("Strength <max>", "MPa & psi") == _legacy_dimension_header(
        "Strength <max>",
        "MPa & psi",
    )

    pill_context = _formal_report_section_pill_context(
        "summary",
        {"missing_recommended_count": 2},
        tracker=True,
    )
    assert pill_context.projection_plane is ProjectionPlane.TEST
    assert pill_context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_SECTION_PILL
    assert pill_context.pill_class == "warn"
    assert pill_context.label_html == Markup("2 missing")
    assert _formal_report_boolean_badge_context(False).label_html == Markup("No")
    assert _formal_report_dimension_header_context("Strength <max>", "MPa & psi").label_html == Markup(
        "Strength &lt;max&gt;"
    )
    assert _formal_report_dimension_header_context("Strength <max>", "MPa & psi").unit_html == Markup(
        "MPa &amp; psi"
    )


def test_formal_report_inline_fragments_keep_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _section_pill("summary", {"status": "complete"}, tracker=True) == _legacy_section_pill(
        "summary",
        {"status": "complete"},
        tracker=True,
    )
    assert _yes_no(True) == _legacy_yes_no(True)
    assert _dimension_header("Max load", "N") == _legacy_dimension_header("Max load", "N")


def test_formal_report_fallback_svgs_jinja_match_legacy_renderer_bytes(monkeypatch) -> None:
    vega_spec = {
        "data": {
            "values": [
                {"analysis_progress_percent": 0.0, "mean": 100.0, "min": 90.0, "max": 110.0, "n": 2},
                {"analysis_progress_percent": 50.0, "mean": 160.0, "min": 140.0, "max": 180.0, "n": 3},
                {"analysis_progress_percent": 100.0, "mean": 240.0, "min": 220.0, "max": 260.0, "n": "4 < 5"},
            ]
        }
    }
    bending_spec = {
        "summary": [
            {
                "run_label": "Run <1>",
                "min_bending_percent": 2.0,
                "q1_bending_percent": 4.0,
                "median_bending_percent": 6.0,
                "q3_bending_percent": 8.0,
                "max_bending_percent": 11.0,
                "bending_pattern": "warn_sustained",
            },
            {
                "run_label": "Run 2",
                "min_bending_percent": 3.0,
                "median_bending_percent": 7.0,
                "max_bending_percent": 14.0,
                "bending_pattern": "fail_localized",
            },
        ]
    }

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    aggregate_html = _aggregate_svg(vega_spec, {})
    bending_html = _failure_bending_svg(bending_spec)
    unavailable_html = _failure_bending_svg({"unavailable_message": "No <plot> & payload"})
    empty_html = _failure_bending_svg({})

    assert aggregate_html == _legacy_aggregate_svg(vega_spec, {})
    assert bending_html == _legacy_failure_bending_svg(bending_spec)
    assert unavailable_html == _legacy_failure_bending_svg({"unavailable_message": "No <plot> & payload"})
    assert empty_html == _legacy_failure_bending_svg({})
    assert 'points="52.0,270.0 356.0,176.6 660.0,52.0"' in aggregate_html
    assert "observations: 4 &lt; 5" in aggregate_html
    assert "Run &lt;1&gt;" in bending_html
    assert unavailable_html == '<p class="plot-note">No &lt;plot&gt; &amp; payload</p>'

    aggregate_context = _formal_report_aggregate_svg_context(vega_spec, {})
    assert aggregate_context.projection_plane is ProjectionPlane.TEST
    assert aggregate_context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG
    assert aggregate_context.n_label_html == Markup("observations: 4 &lt; 5")

    bending_context = _formal_report_failure_bending_svg_context(bending_spec)
    assert isinstance(bending_context, FormalReportFailureBendingSvgContext)
    assert bending_context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG
    assert bending_context.threshold_label_x == 552
    assert "Run &lt;1&gt;" in bending_context.labels_html

    note_context = _formal_report_failure_bending_svg_context({"unavailable_message": "No <plot> & payload"})
    assert isinstance(note_context, FormalReportPlotNoteContext)
    assert note_context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_PLOT_NOTE
    assert note_context.message_html == Markup("No &lt;plot&gt; &amp; payload")


def test_formal_report_fallback_svgs_keep_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    vega_spec = {"data": {"values": [{"analysis_progress_percent": 0.0, "mean": 1.0, "min": 0.5, "max": 1.5}]}}
    bending_spec = {"summary": [{"run_label": "Run 1", "median_bending_percent": 5.0, "max_bending_percent": 9.0}]}

    assert _aggregate_svg(vega_spec, {}) == _legacy_aggregate_svg(vega_spec, {})
    assert _failure_bending_svg(bending_spec) == _legacy_failure_bending_svg(bending_spec)
    assert _failure_bending_svg({"unavailable_message": "offline"}) == _legacy_failure_bending_svg(
        {"unavailable_message": "offline"}
    )


def test_formal_report_static_note_tranche_matches_legacy_renderer_bytes(monkeypatch) -> None:
    geometry_rows = [
        {
            "run_id": "run_001",
            "specimen_name": "specimen_001",
            "sample_id": "sample_a",
            "width_mm": 9.91,
            "thickness_mm": 2.23,
            "area_mm2": 22.0993,
        }
    ]
    empty_sections = [{"id": "test_conditions", "title": "Test Conditions", "blocks": []}]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_outputs = (
        _formal_field_table([]),
        _specimen_geometry_table(geometry_rows),
        _missing_data_table([], [], {}),
        _sections(empty_sections, {}, note_collector=ReportNoteCollector()),
    )
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_outputs = (
        _formal_field_table([]),
        _specimen_geometry_table(geometry_rows),
        _missing_data_table([], [], {}),
        _sections(empty_sections, {}, note_collector=ReportNoteCollector()),
    )

    assert jinja_outputs == legacy_outputs
    assert jinja_outputs[0] == '<p class="empty-note">No report-ready values were supplied for this section.</p>'
    assert jinja_outputs[2] == '<p class="empty-note">No report metadata gaps were recorded.</p>'
    assert '<p class="muted">Geometry check confirms width, thickness, and calculated area are present ' in jinja_outputs[1]


def test_formal_report_field_value_table_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    rows = [
        {"Field": "Operator", "Value": "Ada & Bob", "Unit": "", "_state": "present"},
        {"Field": "Speed", "Value": "<missing>", "Unit": "mm/min", "_state": "missing"},
    ]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _field_value_table(rows)

    assert html == _legacy_field_value_table(rows)
    assert '<tr class="report-row--present">' in html
    assert '<span class="state-dot state-dot--missing" title="Missing report value"' in html
    assert "&lt;missing&gt;" in html


def test_formal_report_field_value_table_keeps_legacy_fallback(monkeypatch) -> None:
    rows = [{"Field": "Operator", "Value": "Ada", "Unit": "", "_state": "present"}]
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _field_value_table(rows) == _legacy_field_value_table(rows)


def test_formal_report_table_body_adapters_jinja_match_legacy_renderer_bytes(monkeypatch) -> None:
    field_rows = [
        {"label": "Operator", "value": "Ada", "_state": "present"},
        {"label": "Conditioning", "value": "", "_state": "missing"},
    ]
    specimen_rows = [
        {
            "run_id": "run_001",
            "specimen_name": "S1",
            "sample_id": "A1",
            "width_mm": 10.0,
            "thickness_mm": 2.0,
            "area_mm2": 20.0,
            "tab_length_mm": 4.5,
        },
        {
            "run_id": "run_002",
            "specimen_name": "S2",
            "sample_id": "A2",
            "width_mm": 9.9,
            "thickness_mm": "",
            "area_mm2": 19.8,
        },
    ]
    result_rows = [
        {
            "run_id": "run_001",
            "specimen_name": "S1",
            "sample_id": "A1",
            "include_in_report": True,
            "validity": "accepted",
            "max_load_N": 5200,
            "compressive_strength_MPa": 233.034,
            "compressive_modulus_MPa": 54527.92,
            "failure_strain_percent": 0.52723,
            "primary_failure_mode": "end_brooming",
            "acceptance_state": "accepted",
        }
    ]
    aggregate_rows = [
        {
            "metric": "compressive_strength",
            "unit": "MPa",
            "n": 3,
            "mean": 240.0,
            "std": 2.1,
            "ci95_low": 236.5,
            "ci95_high": 243.5,
            "min": 233.0,
            "max": 244.0,
        }
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_outputs = (
        _formal_field_table(field_rows),
        _formal_field_table([{"label": "Missing only", "value": "", "_state": "missing"}]),
        _specimen_geometry_table(specimen_rows),
        _individual_results_table(result_rows),
        _aggregate_statistics_formal(aggregate_rows),
    )
    legacy_outputs = (
        _legacy_formal_field_table(field_rows),
        _legacy_formal_field_table([{"label": "Missing only", "value": "", "_state": "missing"}]),
        _legacy_specimen_geometry_table(specimen_rows),
        _legacy_individual_results_table(result_rows),
        _legacy_aggregate_statistics_formal(aggregate_rows),
    )

    assert jinja_outputs == legacy_outputs
    assert '<table class="compact">' in jinja_outputs[0]
    assert jinja_outputs[1] == '<p class="empty-note">No report-ready values were supplied for this section.</p>'
    assert "Geometry check confirms width, thickness" in jinja_outputs[2]
    assert "area = width x thickness within rounding tolerance" in jinja_outputs[2]
    assert "<th>Valid</th>" in jinja_outputs[3]
    assert "<td>Compressive Strength</td>" in jinja_outputs[4]


def test_specimen_geometry_table_section_uses_typed_jinja_context_and_matches_legacy(monkeypatch) -> None:
    rows = [
        {
            "run_id": "run_001",
            "specimen_name": "Specimen A",
            "sample_id": "Panel 1",
            "width_mm": 9.81234,
            "thickness_mm": 2.23678,
            "area_mm2": 21.94567,
            "distance_between_end_tabs_mm": 30.1254,
        }
    ]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    context = _specimen_geometry_table_section_context(rows)
    html = _specimen_geometry_table(rows)

    assert context.projection_plane is ProjectionPlane.TEST
    assert context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_TABLE_SECTION
    assert context.table is not None
    assert context.table.table_class == "results-table"
    assert context.table.headers[-2].html == Markup("Distance between end tabs / unsupported length / mm")
    assert html == _legacy_specimen_geometry_table(rows)
    assert "Geometry check confirms width, thickness" in html
    assert "<td>9.812</td>" in html


def test_specimen_geometry_table_section_preserves_empty_table_legacy_bytes(monkeypatch) -> None:
    rows = ["not a dict"]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    context = _specimen_geometry_table_section_context(rows)
    html = _specimen_geometry_table(rows)

    assert context.table is None
    assert html == _legacy_specimen_geometry_table(rows)
    assert html.endswith('<p class="muted">No rows.</p>')


def test_formal_report_table_body_adapters_keep_legacy_fallback(monkeypatch) -> None:
    rows = [{"label": "Operator", "value": "Ada", "_state": "present"}]
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _formal_field_table(rows) == _legacy_formal_field_table(rows)
    assert _specimen_geometry_table(rows) == _legacy_specimen_geometry_table(rows)
    assert _individual_results_table(rows) == _legacy_individual_results_table(rows)
    assert _aggregate_statistics_formal(rows) == _legacy_aggregate_statistics_formal(rows)


def test_formal_report_raw_evidence_note_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    title = "Raw <Evidence>"
    rows = [{"run_id": "run_001"}, {"run_id": "run_002"}]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _raw_evidence_details(title, rows)

    assert html == _legacy_raw_evidence_details(title, rows)
    assert "Raw &lt;Evidence&gt;" in html
    assert "(2 rows)" in html


def test_formal_report_raw_evidence_note_keeps_legacy_fallback(monkeypatch) -> None:
    rows = [{"run_id": "run_001"}]
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _raw_evidence_details("Raw evidence", rows) == _legacy_raw_evidence_details("Raw evidence", rows)


def test_formal_report_remarks_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    section = {
        "blocks": [
            {"data": "  Keep <operator> note.  "},
            {"data": ""},
            {"data": {"text": "not accepted by this legacy path"}},
            "not a block",
        ]
    }
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _remarks_section(section)

    assert html == _legacy_remarks_section(section)
    assert "<p>Keep &lt;operator&gt; note.</p>" in html


def test_formal_report_remarks_empty_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    section = {"blocks": [{"data": ""}, {"data": {"text": "not accepted by this legacy path"}}]}
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _remarks_section(section)

    assert html == _legacy_remarks_section(section)
    assert html == '<p class="empty-note">No remarks were supplied in the report data.</p>'


def test_formal_report_remarks_keeps_legacy_fallback(monkeypatch) -> None:
    section = {"blocks": [{"data": "Legacy path"}]}
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _remarks_section(section) == _legacy_remarks_section(section)


def test_formal_report_deviations_tranche_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    missing_rows = [
        {"section_id": "test_identification", "field": "operator", "missing_count": 1},
        {
            "section_id": "test_identification",
            "label": "conditioning",
            "affected_run_ids": ["run_001", "run_002"],
        },
    ]
    deviations_rows = [
        {
            "source": "validation",
            "status": "warn",
            "severity": "warning",
            "run_id": "run_001",
            "message": "Bending review remains visible.",
        },
        {"source": "report_completeness", "status": "warn", "field": "operator", "message": "report field missing"},
    ]
    failure_rows = [
        {"run_id": "run_002", "final_included": False},
        {"run_id": "run_003", "final_included": True, "requires_review": True},
    ]
    deviations_section = {
        "id": "deviations_from_standard",
        "title": "Deviations from Standard",
        "blocks": [
            {"id": "missing_report_fields", "data": missing_rows},
            {"id": "deviations_table", "data": deviations_rows},
        ],
    }
    failure_section = {
        "id": "failure_analysis",
        "title": "Failure Analysis",
        "blocks": [{"id": "invalid_specimen_summary", "data": failure_rows}],
    }
    all_sections = [
        {"id": "test_identification", "title": "Test Identification", "blocks": []},
        deviations_section,
        failure_section,
    ]
    section_numbers = {"test_identification": 1, "deviations_from_standard": 11, "failure_analysis": 9}
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _deviations_section(deviations_section, all_sections, section_numbers)

    assert html == _legacy_deviations_section(deviations_section, all_sections, section_numbers)
    assert _missing_data_table(missing_rows, all_sections, section_numbers) == _legacy_missing_data_table(
        missing_rows,
        all_sections,
        section_numbers,
    )
    assert _data_use_deviations_table(deviations_rows, failure_rows) == _legacy_data_use_deviations_table(
        deviations_rows,
        failure_rows,
    )
    assert "<h3>11.1 Missing data</h3>" in html
    assert "Test Identification" in html
    assert "conditioning (#1, #2)" in html
    assert "Review-required included runs" in html


def test_formal_report_deviations_standard_basis_branch_matches_legacy(monkeypatch) -> None:
    standard_rows = [
        {
            "Category": "Geometry",
            "Standard basis": "ASTM D3410",
            "Affected item": "run_001",
            "Status/consequence": "warn",
            "Report treatment": "Reported with operator review.",
        }
    ]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _data_use_deviations_table(standard_rows, [])

    assert html == _legacy_data_use_deviations_table(standard_rows, [])
    assert "<th>Standard basis</th>" in html
    assert "<td>#1</td>" in html


def test_formal_report_deviations_empty_edges_match_legacy(monkeypatch) -> None:
    orphan_missing_rows = [{"section_id": "test_identification"}]
    sections = [{"id": "test_identification", "title": "Test Identification", "blocks": []}]
    section_numbers = {"test_identification": 1}
    failure_rows = [{"run_id": "run_002", "final_included": False}]
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _missing_data_table([], [], {}) == _legacy_missing_data_table([], [], {})
    assert _data_use_deviations_table([], []) == _legacy_data_use_deviations_table([], [])
    assert _data_use_deviations_table([], failure_rows) == _legacy_data_use_deviations_table([], failure_rows)
    assert _missing_data_table(orphan_missing_rows, sections, section_numbers) == _legacy_missing_data_table(
        orphan_missing_rows,
        sections,
        section_numbers,
    )


def test_formal_report_deviations_tranche_keeps_legacy_fallback(monkeypatch) -> None:
    missing_rows = [{"section_id": "test_identification", "field": "operator"}]
    deviations_rows = [{"source": "validation", "status": "warn", "run_id": "run_001"}]
    failure_rows = [{"run_id": "run_002", "final_included": False}]
    deviations_section = {
        "id": "deviations_from_standard",
        "blocks": [
            {"id": "missing_report_fields", "data": missing_rows},
            {"id": "deviations_table", "data": deviations_rows},
        ],
    }
    all_sections = [
        {"id": "test_identification", "title": "Test Identification", "blocks": []},
        deviations_section,
        {"id": "failure_analysis", "blocks": [{"id": "invalid_specimen_summary", "data": failure_rows}]},
    ]
    section_numbers = {"test_identification": 1, "deviations_from_standard": 11}
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _deviations_section(deviations_section, all_sections, section_numbers) == _legacy_deviations_section(
        deviations_section,
        all_sections,
        section_numbers,
    )
    assert _missing_data_table(missing_rows, all_sections, section_numbers) == _legacy_missing_data_table(
        missing_rows,
        all_sections,
        section_numbers,
    )
    assert _data_use_deviations_table(deviations_rows, failure_rows) == _legacy_data_use_deviations_table(
        deviations_rows,
        failure_rows,
    )


def test_formal_report_review_paragraph_tranche_matches_legacy_renderer_bytes(monkeypatch) -> None:
    missing_rows = [
        {"section_title": "Identification", "report_importance": "required", "label": "Operator"},
        {"section_title": "Identification", "report_importance": "recommended", "label": "Conditioning"},
    ]
    aggregate_rows = [
        {
            "metric": "compressive_strength",
            "n": 3,
            "unit": "MPa",
            "mean": 241.1234,
            "std": 2.2,
            "std_err": 1.27,
            "ci95_low": 238.1,
            "ci95_high": 244.1,
            "min": 239,
            "max": 243,
        }
    ]
    deviation_rows = [
        {"status": "pass", "check": "geometry"},
        {"status": "warn", "check": "report field completeness", "message": "report field missing"},
    ]
    failure_rows = [
        {
            "run_id": "run_001",
            "include_in_report": True,
            "validity": "accepted",
            "bending_pattern": "PASS",
            "bending_points_above_threshold": 0,
        }
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_outputs = (
        _missing_fields_review(missing_rows),
        _missing_fields_review([]),
        _aggregate_statistics_review(aggregate_rows),
        _deviations_review(deviation_rows),
        _failure_analysis_review(failure_rows),
    )
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_outputs = (
        _missing_fields_review(missing_rows),
        _missing_fields_review([]),
        _aggregate_statistics_review(aggregate_rows),
        _deviations_review(deviation_rows),
        _failure_analysis_review(failure_rows),
    )

    assert jinja_outputs == legacy_outputs
    assert '<p class="muted">1 required, 1 recommended, and 0 optional report fields' in jinja_outputs[0]
    assert jinja_outputs[1] == "<p>No missing report fields.</p>"
    assert '<a href="#missing_report_fields">Missing report fields</a>' in jinja_outputs[3]


def test_formal_report_review_section_uses_typed_jinja_context(monkeypatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    context = _formal_report_review_section_context(
        "Review intro",
        [{"Metric": "Strength", "n": 3}],
        raw_evidence_title="Raw review evidence",
        raw_rows=[{"run_id": "run_001"}, {"run_id": "run_002"}],
    )

    assert context.projection_plane is ProjectionPlane.TEST
    assert context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION
    assert context.paragraph_class == "muted"
    assert context.intro_paragraph_html == Markup('<p class="muted">Review intro</p>')
    assert context.table is not None
    assert context.table.headers[0].html == Markup("Metric")
    assert context.raw_evidence_note.title_html == Markup("Raw review evidence")
    assert context.raw_evidence_note.row_count == 2


def test_formal_report_evidence_table_tranche_matches_legacy_renderer_bytes(monkeypatch) -> None:
    feature_rows = [
        {
            "axis": "x",
            "metric": "compressive_strength_MPa",
            "value": 233.0345,
            "unit": "MPa",
            "n": 7,
        }
    ]
    point_rows = [
        {
            "point_id": "fmax",
            "scope": "aggregate",
            "run_id": "",
            "x_value": 100.0,
            "x_unit": "%",
            "y_value": 233.0345,
            "y_unit": "MPa",
        }
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_outputs = (
        _feature_lines_review(feature_rows),
        _characteristic_points_review(point_rows),
    )
    context = _formal_report_evidence_table_context(
        [{"Feature": "Fmax", "Role": "report marker"}]
    )
    assert context.projection_plane is ProjectionPlane.TEST
    assert context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_outputs = (
        _feature_lines_review(feature_rows),
        _characteristic_points_review(point_rows),
    )

    assert jinja_outputs == legacy_outputs


def test_formal_report_recipe_projection_and_context_are_explicit() -> None:
    projection = projection_for(RecipeResultKind.FORMAL_METHOD_REPORT)

    assert projection.context_model == "FormalMethodReportContext"
    assert projection.template_name == "layouts/report_page.html.j2"
    assert projection.projection_planes == (ProjectionPlane.TEST,)

    context = FormalMethodReportContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_METHOD_REPORT,
        page_title="Demo Report",
        report_state_card_html=Markup("<div></div>"),
        report_tracker_html=Markup("<nav></nav>"),
        sections_html=Markup("<section></section>"),
        appendix_html=Markup(""),
        formatting_css=Markup(""),
        formatting_script=Markup(""),
    )
    assert context.projection_plane is ProjectionPlane.TEST


def test_formal_report_component_recipe_projection_and_contexts_are_explicit() -> None:
    state_projection = projection_for(RecipeResultKind.FORMAL_REPORT_STATE_CARD)
    tracker_projection = projection_for(RecipeResultKind.FORMAL_REPORT_TRACKER)
    sections_projection = projection_for(RecipeResultKind.FORMAL_REPORT_SECTIONS)
    section_pill_projection = projection_for(RecipeResultKind.FORMAL_REPORT_SECTION_PILL)
    boolean_badge_projection = projection_for(RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE)
    dimension_header_projection = projection_for(RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER)

    assert state_projection.context_model == "FormalReportStateCardContext"
    assert state_projection.template_name == "sections/formal/state_card.html.j2"
    assert state_projection.projection_planes == (ProjectionPlane.TEST,)
    assert tracker_projection.context_model == "FormalReportTrackerContext"
    assert tracker_projection.template_name == "components/trackers/formal_report_tracker.html.j2"
    assert tracker_projection.projection_planes == (ProjectionPlane.TEST,)
    assert sections_projection.context_model == "FormalReportSectionsContext"
    assert sections_projection.template_name == "sections/formal/sections.html.j2"
    assert sections_projection.projection_planes == (ProjectionPlane.TEST,)
    assert section_pill_projection.context_model == "FormalReportSectionPillContext"
    assert section_pill_projection.template_name == "components/badges/section_pill.html.j2"
    assert section_pill_projection.projection_planes == (ProjectionPlane.TEST,)
    assert boolean_badge_projection.context_model == "FormalReportBooleanBadgeContext"
    assert boolean_badge_projection.template_name == "components/badges/boolean_badge.html.j2"
    assert boolean_badge_projection.projection_planes == (ProjectionPlane.TEST,)
    assert dimension_header_projection.context_model == "FormalReportDimensionHeaderContext"
    assert dimension_header_projection.template_name == "components/tables/dimension_header.html.j2"
    assert dimension_header_projection.projection_planes == (ProjectionPlane.TEST,)

    link = FormalReportTrackerLinkContext(
        section_id_html=Markup("summary"),
        number=1,
        title_html=Markup("Summary"),
        pill_html=Markup('<em class="pill ok">OK</em>'),
    )
    context = FormalReportTrackerContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TRACKER,
        links=(link,),
    )
    assert context.links == (link,)

    section = FormalReportSectionContext(
        section_class="report-section",
        section_id_html=Markup("summary"),
        number=1,
        title_html=Markup("Summary"),
        pill_html=Markup('<em class="pill ok">Complete</em>'),
        body_html=Markup("<p>Body</p>"),
    )
    section_context = FormalReportSectionsContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTIONS,
        sections=(section,),
    )
    assert section_context.sections == (section,)

    section_pill_context = FormalReportSectionPillContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTION_PILL,
        pill_class="warn",
        label_html=Markup("Review"),
    )
    assert render_formal_report_section_pill(section_pill_context) == '<em class="pill warn">Review</em>'

    boolean_badge_context = FormalReportBooleanBadgeContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE,
        badge_class="yes",
        label_html=Markup("Yes"),
    )
    assert render_formal_report_boolean_badge(boolean_badge_context) == '<span class="yes">Yes</span>'

    dimension_header_context = FormalReportDimensionHeaderContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER,
        label_html=Markup("Strength"),
        unit_html=Markup("MPa"),
    )
    assert render_formal_report_dimension_header(dimension_header_context) == (
        '<span class="dimension-label">Strength</span> / <span class="unit-label">MPa</span>'
    )

    table_projection = projection_for(RecipeResultKind.FORMAL_REPORT_TABLE)
    detail_projection = projection_for(RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK)
    assert table_projection.context_model == "FormalReportTableContext"
    assert table_projection.template_name == "components/tables/report_table.html.j2"
    assert table_projection.projection_planes == (ProjectionPlane.TEST,)
    assert detail_projection.context_model == "FormalReportDetailBlockContext"
    assert detail_projection.template_name == "components/panels/formal_detail_block.html.j2"
    assert detail_projection.projection_planes == (ProjectionPlane.TEST,)

    cell = FormalReportTableCellContext(html=Markup("Value"))
    table_context = FormalReportTableContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE,
        table_class="results-table",
        headers=(cell,),
        rows=(FormalReportTableRowContext(cells=(cell,)),),
    )
    assert table_context.rows[0].cells == (cell,)

    detail_context = FormalReportDetailBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
        classes="detail-block",
        block_id_html=Markup("block"),
        title_html=Markup("Title"),
        marker_html=Markup(""),
        row_count=1,
        body_note_html=Markup("<p>Purpose</p>"),
        content_html=Markup("<p>Body</p>"),
        note_html=Markup(""),
    )
    assert detail_context.row_count == 1

    block_projection = projection_for(RecipeResultKind.FORMAL_REPORT_BLOCK)
    field_value_projection = projection_for(RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE)
    fragment_stack_projection = projection_for(RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK)
    table_section_projection = projection_for(RecipeResultKind.FORMAL_REPORT_TABLE_SECTION)
    review_section_projection = projection_for(RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION)
    raw_evidence_projection = projection_for(RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE)
    remarks_projection = projection_for(RecipeResultKind.FORMAL_REPORT_REMARKS)
    missing_data_projection = projection_for(RecipeResultKind.FORMAL_REPORT_MISSING_DATA)
    data_use_deviations_projection = projection_for(RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS)
    deviations_section_projection = projection_for(RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION)
    plot_block_projection = projection_for(RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK)
    plot_legend_projection = projection_for(RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND)
    aggregate_svg_projection = projection_for(RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG)
    failure_bending_svg_projection = projection_for(RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG)
    plot_note_projection = projection_for(RecipeResultKind.FORMAL_REPORT_PLOT_NOTE)
    paragraph_projection = projection_for(RecipeResultKind.FORMAL_REPORT_PARAGRAPH)
    assert block_projection.context_model == "FormalReportBlockContext"
    assert block_projection.template_name == "components/panels/report_block.html.j2"
    assert block_projection.projection_planes == (ProjectionPlane.TEST,)
    assert field_value_projection.context_model == "FormalReportFieldValueTableContext"
    assert field_value_projection.template_name == "components/tables/formal_field_value_table.html.j2"
    assert field_value_projection.projection_planes == (ProjectionPlane.TEST,)
    assert fragment_stack_projection.context_model == "FormalReportFragmentStackContext"
    assert fragment_stack_projection.template_name == "components/panels/fragment_stack.html.j2"
    assert fragment_stack_projection.projection_planes == (ProjectionPlane.TEST,)
    assert table_section_projection.context_model == "FormalReportTableSectionContext"
    assert table_section_projection.template_name == "components/tables/optional_report_table.html.j2"
    assert table_section_projection.projection_planes == (ProjectionPlane.TEST,)
    assert review_section_projection.context_model == "FormalReportReviewSectionContext"
    assert review_section_projection.template_name == "sections/formal/review_section.html.j2"
    assert review_section_projection.projection_planes == (ProjectionPlane.TEST,)
    assert paragraph_projection.context_model == "FormalReportParagraphContext"
    assert paragraph_projection.template_name == "components/typography/paragraph.html.j2"
    assert paragraph_projection.projection_planes == (ProjectionPlane.TEST,)
    assert raw_evidence_projection.context_model == "FormalReportRawEvidenceNoteContext"
    assert raw_evidence_projection.template_name == "components/notes/raw_evidence_note.html.j2"
    assert raw_evidence_projection.projection_planes == (ProjectionPlane.TEST,)
    assert remarks_projection.context_model == "FormalReportRemarksContext"
    assert remarks_projection.template_name == "sections/formal/remarks.html.j2"
    assert remarks_projection.projection_planes == (ProjectionPlane.TEST,)
    assert missing_data_projection.context_model == "FormalReportMissingDataContext"
    assert missing_data_projection.template_name == "components/tables/optional_report_table.html.j2"
    assert missing_data_projection.projection_planes == (ProjectionPlane.TEST,)
    assert data_use_deviations_projection.context_model == "FormalReportDataUseDeviationsContext"
    assert data_use_deviations_projection.template_name == "components/tables/optional_report_table.html.j2"
    assert data_use_deviations_projection.projection_planes == (ProjectionPlane.TEST,)
    assert deviations_section_projection.context_model == "FormalReportDeviationsSectionContext"
    assert deviations_section_projection.template_name == "sections/formal/deviations_section.html.j2"
    assert deviations_section_projection.projection_planes == (ProjectionPlane.TEST,)
    assert plot_block_projection.context_model == "FormalReportPlotBlockContext"
    assert plot_block_projection.template_name == "components/plots/formal_plot_block.html.j2"
    assert plot_block_projection.projection_planes == (ProjectionPlane.TEST,)
    assert plot_legend_projection.context_model == "FormalReportPlotLegendContext"
    assert plot_legend_projection.template_name == "components/plots/formal_plot_legend.html.j2"
    assert plot_legend_projection.projection_planes == (ProjectionPlane.TEST,)
    assert aggregate_svg_projection.context_model == "FormalReportAggregateSvgContext"
    assert aggregate_svg_projection.template_name == "components/plots/aggregate_svg.html.j2"
    assert aggregate_svg_projection.projection_planes == (ProjectionPlane.TEST,)
    assert failure_bending_svg_projection.context_model == "FormalReportFailureBendingSvgContext"
    assert failure_bending_svg_projection.template_name == "components/plots/failure_bending_svg.html.j2"
    assert failure_bending_svg_projection.projection_planes == (ProjectionPlane.TEST,)
    assert plot_note_projection.context_model == "FormalReportPlotNoteContext"
    assert plot_note_projection.template_name == "components/typography/plot_note.html.j2"
    assert plot_note_projection.projection_planes == (ProjectionPlane.TEST,)

    block_context = FormalReportBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BLOCK,
        block_id_html=Markup("block"),
        title_html=Markup("Title"),
        content_html=Markup("<p>Body</p>"),
    )
    assert block_context.block_id_html == Markup("block")

    row_context = FormalReportFieldValueRowContext(
        row_class="report-row--present",
        field_html=Markup("Operator"),
        value_html=Markup("Ada"),
        unit_html=Markup(""),
    )
    field_value_context = FormalReportFieldValueTableContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE,
        rows=(row_context,),
    )
    assert field_value_context.rows == (row_context,)

    fragment_stack_context = FormalReportFragmentStackContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK,
        fragments=(Markup("<p>Body</p>"),),
    )
    assert fragment_stack_context.fragments == (Markup("<p>Body</p>"),)

    table_section_context = FormalReportTableSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
        paragraph_class="muted",
        intro_html=Markup("Body"),
        intro_paragraph_html=Markup('<p class="muted">Body</p>'),
        table=table_context,
        empty_table_html=Markup('<p class="muted">No rows.</p>'),
    )
    assert table_section_context.table is table_context
    assert table_section_context.empty_message_html == table_section_context.empty_table_html
    assert table_section_context.optional_table_prefix_html == table_section_context.intro_paragraph_html

    raw_evidence_context = FormalReportRawEvidenceNoteContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
        title_html=Markup("Raw evidence"),
        row_count=2,
    )
    assert raw_evidence_context.row_count == 2
    assert raw_evidence_context.artifact_scope_html == Markup("MTDA report CSV/JSON artifacts")
    assert raw_evidence_context.row_suffix_html == Markup("")
    assert raw_evidence_context.paragraph_class == "muted"

    review_section_context = FormalReportReviewSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION,
        paragraph_class="muted",
        intro_html=Markup("Body"),
        intro_paragraph_html=Markup('<p class="muted">Body</p>'),
        table=table_context,
        empty_message_html=Markup(""),
        raw_evidence_note=raw_evidence_context,
    )
    assert review_section_context.raw_evidence_note is raw_evidence_context

    paragraph_context = FormalReportParagraphContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
        paragraph_class="muted",
        body_html=Markup("Body"),
    )
    assert paragraph_context.paragraph_class == "muted"

    remarks_context = FormalReportRemarksContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REMARKS,
        paragraphs=(Markup("Remark"),),
        empty_message_html=Markup("No remarks."),
    )
    assert remarks_context.paragraphs == (Markup("Remark"),)

    missing_data_context = FormalReportMissingDataContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
        table=table_context,
        empty_message_html=Markup('<p class="empty-note">No gaps.</p>'),
    )
    assert "results-table" in render_formal_report_missing_data(missing_data_context)
    assert missing_data_context.optional_table_prefix_html == Markup("")

    data_use_deviations_context = FormalReportDataUseDeviationsContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
        prefix_html=Markup("<p>prefix</p>"),
        table=table_context,
        empty_message_html=Markup("<p>empty</p>"),
    )
    assert data_use_deviations_context.optional_table_prefix_html == data_use_deviations_context.prefix_html
    assert render_formal_report_data_use_deviations(data_use_deviations_context).startswith("<p>prefix</p>")

    deviations_section_context = FormalReportDeviationsSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION,
        section_number=11,
        missing_heading_html=Markup("<h3>11.1 Missing data</h3>"),
        missing_data_html=Markup("<p>missing</p>"),
        data_deviations_heading_html=Markup("<h3>11.2 Data deviations / standard-facing deviations</h3>"),
        data_deviations_html=Markup("<p>data</p>"),
    )
    assert render_formal_report_deviations_section(deviations_section_context) == (
        "<h3>11.1 Missing data</h3><p>missing</p>"
        "<h3>11.2 Data deviations / standard-facing deviations</h3><p>data</p>"
    )

    plot_context = FormalReportPlotBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK,
        block_id_html=Markup("vega-demo"),
        label_html=Markup("Aggregate plot"),
        fallback_html=Markup("<svg></svg>"),
        legend_html=Markup("<div>Legend</div>"),
        spec_json=Markup('{"mark":"line"}'),
    )
    assert render_formal_report_plot_block(plot_context) == (
        '<div class="plot" data-vega-block="vega-demo">\n'
        '  <div class="vega-fallback"><svg></svg></div>\n'
        '  <div id="vega-demo" class="vega-chart" aria-label="Aggregate plot"></div>\n'
        '  <div>Legend</div>\n'
        '  <script type="application/json" id="vega-demo-spec">{"mark":"line"}</script>\n'
        "</div>"
    )

    plot_legend_context = FormalReportPlotLegendContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND,
        sd_label_html=Markup("mean +/- 1 SD"),
        range_label_html=Markup("observed range"),
    )
    assert render_formal_report_plot_legend(plot_legend_context) == (
        '<div class="plot-legend" aria-label="Aggregate stress-strain plot legend">\n'
        "    <strong>Legend</strong>\n"
        '    <span class="plot-legend-item"><span class="plot-legend-swatch replicate"></span>individual replicate</span>\n'
        '    <span class="plot-legend-item"><span class="plot-legend-swatch"></span>mean curve</span>\n'
        '    <span class="plot-legend-item"><span class="plot-legend-swatch band"></span>mean +/- 1 SD</span>\n'
        '    <span class="plot-legend-item"><span class="plot-legend-swatch envelope"></span>observed range</span>\n'
        '    <span class="plot-legend-ci">95% CI = 95% confidence interval for the aggregate metric mean in the table above; it is not the shaded curve band.</span>\n'
        "  </div>"
    )

    aggregate_svg_context = FormalReportAggregateSvgContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
        min_path="52,270 660,120",
        max_path="52,230 660,52",
        mean_path="52,250 660,84",
        n_label_html=Markup("observations: 3"),
    )
    assert '<polyline fill="none" stroke="#2477b3" stroke-width="3" points="52,250 660,84"/>' in (
        render_formal_report_aggregate_svg(aggregate_svg_context)
    )

    failure_bending_svg_context = FormalReportFailureBendingSvgContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG,
        width=700,
        height=280,
        left=52,
        top=26,
        bottom=230,
        plot_width=600,
        right=652,
        threshold_fill_height="60.0",
        threshold_y="86.0",
        threshold_label_x=552,
        threshold_label_y="80.0",
        boxes_html=Markup('<line x1="10" y1="20" x2="10" y2="30"/>'),
        labels_html=Markup('<text x="10" y="252">Run 1</text>'),
    )
    assert '<text x="552" y="80.0" font-size="12" fill="#b85f56">10% threshold</text>' in (
        render_formal_report_failure_bending_svg(failure_bending_svg_context)
    )

    plot_note_context = FormalReportPlotNoteContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
        message_html=Markup("Offline"),
    )
    assert render_formal_report_plot_note(plot_note_context) == '<p class="plot-note">Offline</p>'


def test_formal_report_context_rejects_wrong_plane_kind_and_loose_fragments() -> None:
    kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_METHOD_REPORT,
        page_title="Demo Report",
        report_state_card_html=Markup("<div></div>"),
        report_tracker_html=Markup("<nav></nav>"),
        sections_html=Markup("<section></section>"),
        appendix_html=Markup(""),
        formatting_css=Markup(""),
        formatting_script=Markup(""),
    )

    try:
        FormalMethodReportContext(**{**kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalMethodReportContext accepted the wrong projection plane")

    try:
        FormalMethodReportContext(**{**kwargs, "recipe_result_kind": RecipeResultKind.TEST_REPORT})
    except ValueError as exc:
        assert "formal_method_report" in str(exc)
    else:
        raise AssertionError("FormalMethodReportContext accepted the wrong recipe/result kind")

    try:
        FormalMethodReportContext(**{**kwargs, "sections_html": "<section></section>"})
    except ValueError as exc:
        assert "sections_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalMethodReportContext accepted a loose HTML string")


def test_formal_report_component_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    state_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_STATE_CARD,
        title_html=Markup("Demo"),
        lede_html=Markup('<p class="report-state-note">Formal method results and report-ready evidence.</p>'),
        method_context_html=Markup(""),
        method_boundary_html=Markup(""),
        status_class="ok",
        quality_label_html=Markup("Complete"),
        completion_label_html=Markup("Complete"),
        required_state_html=Markup("<span>Complete</span>"),
        required_location_html=Markup("Required report content complete."),
        recommended_state_html=Markup("<span>Complete</span>"),
        recommended_location_html=Markup("No recommended metadata missing."),
        data_state_html=Markup("<span>All runs included</span>"),
        aggregate_basis_html=Markup("No selected runs recorded"),
    )

    try:
        FormalReportStateCardContext(**{**state_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportStateCardContext accepted the wrong projection plane")

    try:
        FormalReportStateCardContext(**{**state_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_METHOD_REPORT})
    except ValueError as exc:
        assert "formal_report_state_card" in str(exc)
    else:
        raise AssertionError("FormalReportStateCardContext accepted the wrong recipe/result kind")

    try:
        FormalReportStateCardContext(**{**state_kwargs, "title_html": "Demo"})
    except ValueError as exc:
        assert "title_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportStateCardContext accepted loose title HTML")

    try:
        FormalReportStateCardContext(**{**state_kwargs, "lede_html": "<p>Report evidence.</p>"})
    except ValueError as exc:
        assert "lede_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportStateCardContext accepted loose lede HTML")

    try:
        FormalReportTrackerLinkContext(
            section_id_html=Markup("summary"),
            number=0,
            title_html=Markup("Summary"),
            pill_html=Markup('<em class="pill ok">OK</em>'),
        )
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("FormalReportTrackerLinkContext accepted an invalid number")

    try:
        FormalReportTrackerContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TRACKER,
            links=(),
        )
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportTrackerContext accepted the wrong projection plane")

    try:
        FormalReportSectionContext(
            section_class="report-section",
            section_id_html=Markup("summary"),
            number=0,
            title_html=Markup("Summary"),
            pill_html=Markup('<em class="pill ok">Complete</em>'),
            body_html=Markup("<p>Body</p>"),
        )
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("FormalReportSectionContext accepted an invalid number")

    try:
        FormalReportSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTIONS,
            sections=(),
        )
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportSectionsContext accepted the wrong projection plane")

    section_pill_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTION_PILL,
        pill_class="warn",
        label_html=Markup("Review"),
    )
    try:
        FormalReportSectionPillContext(**{**section_pill_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportSectionPillContext accepted the wrong projection plane")

    try:
        FormalReportSectionPillContext(
            **{**section_pill_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_TRACKER}
        )
    except ValueError as exc:
        assert "formal_report_section_pill" in str(exc)
    else:
        raise AssertionError("FormalReportSectionPillContext accepted the wrong recipe/result kind")

    try:
        FormalReportSectionPillContext(**{**section_pill_kwargs, "label_html": "Review"})
    except ValueError as exc:
        assert "label_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportSectionPillContext accepted loose label HTML")

    boolean_badge_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE,
        badge_class="yes",
        label_html=Markup("Yes"),
    )
    try:
        FormalReportBooleanBadgeContext(**{**boolean_badge_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportBooleanBadgeContext accepted the wrong projection plane")

    try:
        FormalReportBooleanBadgeContext(
            **{**boolean_badge_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_SECTION_PILL}
        )
    except ValueError as exc:
        assert "formal_report_boolean_badge" in str(exc)
    else:
        raise AssertionError("FormalReportBooleanBadgeContext accepted the wrong recipe/result kind")

    try:
        FormalReportBooleanBadgeContext(**{**boolean_badge_kwargs, "label_html": "Yes"})
    except ValueError as exc:
        assert "label_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportBooleanBadgeContext accepted loose label HTML")

    dimension_header_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER,
        label_html=Markup("Strength"),
        unit_html=Markup("MPa"),
    )
    try:
        FormalReportDimensionHeaderContext(**{**dimension_header_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportDimensionHeaderContext accepted the wrong projection plane")

    try:
        FormalReportDimensionHeaderContext(
            **{**dimension_header_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_SECTION_PILL}
        )
    except ValueError as exc:
        assert "formal_report_dimension_header" in str(exc)
    else:
        raise AssertionError("FormalReportDimensionHeaderContext accepted the wrong recipe/result kind")

    try:
        FormalReportDimensionHeaderContext(**{**dimension_header_kwargs, "unit_html": "MPa"})
    except ValueError as exc:
        assert "unit_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportDimensionHeaderContext accepted loose unit HTML")

    cell = FormalReportTableCellContext(html=Markup("Value"))
    table_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE,
        table_class="",
        headers=(cell,),
        rows=(FormalReportTableRowContext(cells=(cell,)),),
    )
    try:
        FormalReportTableContext(**{**table_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportTableContext accepted the wrong projection plane")

    try:
        FormalReportTableCellContext(html="Value")
    except ValueError as exc:
        assert "html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportTableCellContext accepted a loose HTML string")

    detail_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
        classes="detail-block",
        block_id_html=Markup("block"),
        title_html=Markup("Title"),
        marker_html=Markup(""),
        row_count=1,
        body_note_html=Markup("<p>Purpose</p>"),
        content_html=Markup("<p>Body</p>"),
        note_html=Markup(""),
    )
    try:
        FormalReportDetailBlockContext(**{**detail_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_TABLE})
    except ValueError as exc:
        assert "formal_report_detail_block" in str(exc)
    else:
        raise AssertionError("FormalReportDetailBlockContext accepted the wrong recipe/result kind")

    try:
        FormalReportDetailBlockContext(**{**detail_kwargs, "content_html": "<p>Body</p>"})
    except ValueError as exc:
        assert "content_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportDetailBlockContext accepted loose content HTML")

    block_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BLOCK,
        block_id_html=Markup("block"),
        title_html=Markup("Title"),
        content_html=Markup("<p>Body</p>"),
    )
    try:
        FormalReportBlockContext(**{**block_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportBlockContext accepted the wrong projection plane")

    try:
        FormalReportBlockContext(**{**block_kwargs, "content_html": "<p>Body</p>"})
    except ValueError as exc:
        assert "content_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportBlockContext accepted loose content HTML")

    field_row = FormalReportFieldValueRowContext(
        row_class="report-row--present",
        field_html=Markup("Operator"),
        value_html=Markup("Ada"),
        unit_html=Markup(""),
    )
    field_value_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE,
        rows=(field_row,),
    )
    try:
        FormalReportFieldValueTableContext(**{**field_value_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_TABLE})
    except ValueError as exc:
        assert "formal_report_field_value_table" in str(exc)
    else:
        raise AssertionError("FormalReportFieldValueTableContext accepted the wrong recipe/result kind")

    try:
        FormalReportFieldValueRowContext(
            row_class="report-row--present",
            field_html="Operator",
            value_html=Markup("Ada"),
            unit_html=Markup(""),
        )
    except ValueError as exc:
        assert "field_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportFieldValueRowContext accepted loose field HTML")

    fragment_stack_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK,
        fragments=(Markup("<p>Body</p>"),),
    )
    try:
        FormalReportFragmentStackContext(**{**fragment_stack_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportFragmentStackContext accepted the wrong projection plane")

    try:
        FormalReportFragmentStackContext(
            **{**fragment_stack_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_TABLE}
        )
    except ValueError as exc:
        assert "formal_report_fragment_stack" in str(exc)
    else:
        raise AssertionError("FormalReportFragmentStackContext accepted the wrong recipe/result kind")

    try:
        FormalReportFragmentStackContext(**{**fragment_stack_kwargs, "fragments": ("<p>Body</p>",)})
    except ValueError as exc:
        assert "fragments must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportFragmentStackContext accepted loose fragment HTML")

    table_section_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
        paragraph_class="muted",
        intro_html=Markup("Intro"),
        intro_paragraph_html=Markup('<p class="muted">Intro</p>'),
        table=FormalReportTableContext(**table_kwargs),
        empty_table_html=Markup('<p class="muted">No rows.</p>'),
    )
    try:
        FormalReportTableSectionContext(**{**table_section_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportTableSectionContext accepted the wrong projection plane")

    try:
        FormalReportTableSectionContext(
            **{**table_section_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK}
        )
    except ValueError as exc:
        assert "formal_report_table_section" in str(exc)
    else:
        raise AssertionError("FormalReportTableSectionContext accepted the wrong recipe/result kind")

    try:
        FormalReportTableSectionContext(**{**table_section_kwargs, "intro_html": "Intro"})
    except ValueError as exc:
        assert "intro_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportTableSectionContext accepted loose intro HTML")

    try:
        FormalReportTableSectionContext(**{**table_section_kwargs, "intro_paragraph_html": "<p>Intro</p>"})
    except ValueError as exc:
        assert "intro_paragraph_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportTableSectionContext accepted loose intro paragraph HTML")

    try:
        FormalReportTableSectionContext(**{**table_section_kwargs, "table": "not a table"})
    except ValueError as exc:
        assert "table must be a FormalReportTableContext or None" in str(exc)
    else:
        raise AssertionError("FormalReportTableSectionContext accepted a loose table")

    paragraph_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
        paragraph_class="muted",
        body_html=Markup("Body"),
    )
    try:
        FormalReportParagraphContext(**{**paragraph_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportParagraphContext accepted the wrong projection plane")

    try:
        FormalReportParagraphContext(
            **{**paragraph_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_BLOCK}
        )
    except ValueError as exc:
        assert "formal_report_paragraph" in str(exc)
    else:
        raise AssertionError("FormalReportParagraphContext accepted the wrong recipe/result kind")

    try:
        FormalReportParagraphContext(**{**paragraph_kwargs, "body_html": "Body"})
    except ValueError as exc:
        assert "body_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportParagraphContext accepted loose body HTML")

    raw_evidence_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
        title_html=Markup("Raw evidence"),
        row_count=1,
    )
    try:
        FormalReportRawEvidenceNoteContext(**{**raw_evidence_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportRawEvidenceNoteContext accepted the wrong projection plane")

    try:
        FormalReportRawEvidenceNoteContext(**{**raw_evidence_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_BLOCK})
    except ValueError as exc:
        assert "formal_report_raw_evidence_note" in str(exc)
    else:
        raise AssertionError("FormalReportRawEvidenceNoteContext accepted the wrong recipe/result kind")

    try:
        FormalReportRawEvidenceNoteContext(**{**raw_evidence_kwargs, "title_html": "Raw evidence"})
    except ValueError as exc:
        assert "title_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportRawEvidenceNoteContext accepted loose title HTML")

    review_section_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION,
        paragraph_class="muted",
        intro_html=Markup("Intro"),
        intro_paragraph_html=Markup('<p class="muted">Intro</p>'),
        table=FormalReportTableContext(**table_kwargs),
        empty_message_html=Markup(""),
        raw_evidence_note=FormalReportRawEvidenceNoteContext(**raw_evidence_kwargs),
    )
    try:
        FormalReportReviewSectionContext(**{**review_section_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportReviewSectionContext accepted the wrong projection plane")

    try:
        FormalReportReviewSectionContext(
            **{**review_section_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_TABLE_SECTION}
        )
    except ValueError as exc:
        assert "formal_report_review_section" in str(exc)
    else:
        raise AssertionError("FormalReportReviewSectionContext accepted the wrong recipe/result kind")

    try:
        FormalReportReviewSectionContext(**{**review_section_kwargs, "intro_html": "Intro"})
    except ValueError as exc:
        assert "intro_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportReviewSectionContext accepted loose intro HTML")

    try:
        FormalReportReviewSectionContext(**{**review_section_kwargs, "intro_paragraph_html": "<p>Intro</p>"})
    except ValueError as exc:
        assert "intro_paragraph_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportReviewSectionContext accepted loose intro paragraph HTML")

    try:
        FormalReportReviewSectionContext(**{**review_section_kwargs, "raw_evidence_note": "not a note"})
    except ValueError as exc:
        assert "raw_evidence_note must be a FormalReportRawEvidenceNoteContext" in str(exc)
    else:
        raise AssertionError("FormalReportReviewSectionContext accepted a loose raw-evidence note")

    remarks_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REMARKS,
        paragraphs=(Markup("Remark"),),
        empty_message_html=Markup("No remarks."),
    )
    try:
        FormalReportRemarksContext(**{**remarks_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportRemarksContext accepted the wrong projection plane")

    try:
        FormalReportRemarksContext(**{**remarks_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_BLOCK})
    except ValueError as exc:
        assert "formal_report_remarks" in str(exc)
    else:
        raise AssertionError("FormalReportRemarksContext accepted the wrong recipe/result kind")

    try:
        FormalReportRemarksContext(**{**remarks_kwargs, "paragraphs": ("Remark",)})
    except ValueError as exc:
        assert "paragraphs must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportRemarksContext accepted loose paragraph HTML")

    missing_data_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
        table=FormalReportTableContext(**table_kwargs),
        empty_message_html=Markup('<p class="empty-note">No gaps.</p>'),
    )
    try:
        FormalReportMissingDataContext(**{**missing_data_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportMissingDataContext accepted the wrong projection plane")

    try:
        FormalReportMissingDataContext(
            **{**missing_data_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_REMARKS}
        )
    except ValueError as exc:
        assert "formal_report_missing_data" in str(exc)
    else:
        raise AssertionError("FormalReportMissingDataContext accepted the wrong recipe/result kind")

    try:
        FormalReportMissingDataContext(**{**missing_data_kwargs, "empty_message_html": "<p>No gaps.</p>"})
    except ValueError as exc:
        assert "empty_message_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportMissingDataContext accepted loose empty-message HTML")

    data_use_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
        prefix_html=Markup("<p>prefix</p>"),
        table=FormalReportTableContext(**table_kwargs),
        empty_message_html=Markup("<p>empty</p>"),
    )
    try:
        FormalReportDataUseDeviationsContext(**{**data_use_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportDataUseDeviationsContext accepted the wrong projection plane")

    try:
        FormalReportDataUseDeviationsContext(
            **{**data_use_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_REMARKS}
        )
    except ValueError as exc:
        assert "formal_report_data_use_deviations" in str(exc)
    else:
        raise AssertionError("FormalReportDataUseDeviationsContext accepted the wrong recipe/result kind")

    try:
        FormalReportDataUseDeviationsContext(**{**data_use_kwargs, "prefix_html": "<p>prefix</p>"})
    except ValueError as exc:
        assert "prefix_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportDataUseDeviationsContext accepted loose prefix HTML")

    deviations_section_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION,
        section_number=11,
        missing_heading_html=Markup("<h3>11.1 Missing data</h3>"),
        missing_data_html=Markup("<p>missing</p>"),
        data_deviations_heading_html=Markup("<h3>11.2 Data deviations / standard-facing deviations</h3>"),
        data_deviations_html=Markup("<p>data</p>"),
    )
    try:
        FormalReportDeviationsSectionContext(
            **{**deviations_section_kwargs, "projection_plane": ProjectionPlane.AUDIT}
        )
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportDeviationsSectionContext accepted the wrong projection plane")

    try:
        FormalReportDeviationsSectionContext(
            **{**deviations_section_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_REMARKS}
        )
    except ValueError as exc:
        assert "formal_report_deviations_section" in str(exc)
    else:
        raise AssertionError("FormalReportDeviationsSectionContext accepted the wrong recipe/result kind")

    try:
        FormalReportDeviationsSectionContext(**{**deviations_section_kwargs, "section_number": 0})
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("FormalReportDeviationsSectionContext accepted an invalid section number")

    try:
        FormalReportDeviationsSectionContext(
            **{**deviations_section_kwargs, "missing_heading_html": "<h3>11.1 Missing data</h3>"}
        )
    except ValueError as exc:
        assert "missing_heading_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportDeviationsSectionContext accepted loose missing heading HTML")

    try:
        FormalReportDeviationsSectionContext(**{**deviations_section_kwargs, "missing_data_html": "<p>missing</p>"})
    except ValueError as exc:
        assert "missing_data_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportDeviationsSectionContext accepted loose missing-data HTML")

    plot_block_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK,
        block_id_html=Markup("vega-demo"),
        label_html=Markup("Aggregate plot"),
        fallback_html=Markup("<svg></svg>"),
        legend_html=Markup("<div>Legend</div>"),
        spec_json=Markup('{"mark":"line"}'),
    )
    try:
        FormalReportPlotBlockContext(**{**plot_block_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportPlotBlockContext accepted the wrong projection plane")

    try:
        FormalReportPlotBlockContext(
            **{**plot_block_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION}
        )
    except ValueError as exc:
        assert "formal_report_plot_block" in str(exc)
    else:
        raise AssertionError("FormalReportPlotBlockContext accepted the wrong recipe/result kind")

    try:
        FormalReportPlotBlockContext(**{**plot_block_kwargs, "fallback_html": "<svg></svg>"})
    except ValueError as exc:
        assert "fallback_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportPlotBlockContext accepted loose fallback HTML")

    try:
        FormalReportPlotBlockContext(**{**plot_block_kwargs, "spec_json": '{"mark":"line"}'})
    except ValueError as exc:
        assert "spec_json must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportPlotBlockContext accepted loose spec JSON")

    plot_legend_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND,
        sd_label_html=Markup("mean +/- 1 SD"),
        range_label_html=Markup("observed range"),
    )
    try:
        FormalReportPlotLegendContext(**{**plot_legend_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportPlotLegendContext accepted the wrong projection plane")

    try:
        FormalReportPlotLegendContext(
            **{**plot_legend_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK}
        )
    except ValueError as exc:
        assert "formal_report_plot_legend" in str(exc)
    else:
        raise AssertionError("FormalReportPlotLegendContext accepted the wrong recipe/result kind")

    try:
        FormalReportPlotLegendContext(**{**plot_legend_kwargs, "sd_label_html": "mean +/- 1 SD"})
    except ValueError as exc:
        assert "sd_label_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportPlotLegendContext accepted loose SD-label HTML")

    try:
        FormalReportPlotLegendContext(**{**plot_legend_kwargs, "range_label_html": "observed range"})
    except ValueError as exc:
        assert "range_label_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportPlotLegendContext accepted loose range-label HTML")

    aggregate_svg_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
        min_path="52,270 660,120",
        max_path="52,230 660,52",
        mean_path="52,250 660,84",
        n_label_html=Markup("observations: 3"),
    )
    try:
        FormalReportAggregateSvgContext(**{**aggregate_svg_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportAggregateSvgContext accepted the wrong projection plane")

    try:
        FormalReportAggregateSvgContext(
            **{**aggregate_svg_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK}
        )
    except ValueError as exc:
        assert "formal_report_aggregate_svg" in str(exc)
    else:
        raise AssertionError("FormalReportAggregateSvgContext accepted the wrong recipe/result kind")

    try:
        FormalReportAggregateSvgContext(**{**aggregate_svg_kwargs, "mean_path": ""})
    except ValueError as exc:
        assert "mean_path must be a non-empty string" in str(exc)
    else:
        raise AssertionError("FormalReportAggregateSvgContext accepted an empty mean path")

    try:
        FormalReportAggregateSvgContext(**{**aggregate_svg_kwargs, "n_label_html": "observations: 3"})
    except ValueError as exc:
        assert "n_label_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportAggregateSvgContext accepted loose label HTML")

    failure_bending_svg_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG,
        width=700,
        height=280,
        left=52,
        top=26,
        bottom=230,
        plot_width=600,
        right=652,
        threshold_fill_height="60.0",
        threshold_y="86.0",
        threshold_label_x=552,
        threshold_label_y="80.0",
        boxes_html=Markup("<line/>"),
        labels_html=Markup("<text>Run 1</text>"),
    )
    try:
        FormalReportFailureBendingSvgContext(
            **{**failure_bending_svg_kwargs, "projection_plane": ProjectionPlane.AUDIT}
        )
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportFailureBendingSvgContext accepted the wrong projection plane")

    try:
        FormalReportFailureBendingSvgContext(
            **{
                **failure_bending_svg_kwargs,
                "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
            }
        )
    except ValueError as exc:
        assert "formal_report_failure_bending_svg" in str(exc)
    else:
        raise AssertionError("FormalReportFailureBendingSvgContext accepted the wrong recipe/result kind")

    try:
        FormalReportFailureBendingSvgContext(**{**failure_bending_svg_kwargs, "height": -1})
    except ValueError as exc:
        assert "height must be a non-negative integer" in str(exc)
    else:
        raise AssertionError("FormalReportFailureBendingSvgContext accepted a negative height")

    try:
        FormalReportFailureBendingSvgContext(**{**failure_bending_svg_kwargs, "boxes_html": "<line/>"})
    except ValueError as exc:
        assert "boxes_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportFailureBendingSvgContext accepted loose boxes HTML")

    plot_note_kwargs = dict(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
        message_html=Markup("Offline"),
    )
    try:
        FormalReportPlotNoteContext(**{**plot_note_kwargs, "projection_plane": ProjectionPlane.AUDIT})
    except ValueError as exc:
        assert "test projection plane" in str(exc)
    else:
        raise AssertionError("FormalReportPlotNoteContext accepted the wrong projection plane")

    try:
        FormalReportPlotNoteContext(
            **{**plot_note_kwargs, "recipe_result_kind": RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND}
        )
    except ValueError as exc:
        assert "formal_report_plot_note" in str(exc)
    else:
        raise AssertionError("FormalReportPlotNoteContext accepted the wrong recipe/result kind")

    try:
        FormalReportPlotNoteContext(**{**plot_note_kwargs, "message_html": "Offline"})
    except ValueError as exc:
        assert "message_html must be an HTML-safe Markup fragment" in str(exc)
    else:
        raise AssertionError("FormalReportPlotNoteContext accepted loose message HTML")


def test_html_renderer_demotes_process_summary_blocks_to_details() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={},
        sections=[
            ReportSectionDocument(
                id="failure_analysis",
                title="Failure Analysis",
                blocks=[
                    ReportBlockDocument(
                        id="acceptance_summary",
                        type="acceptance_summary",
                        title="Acceptance Summary",
                        provider="acceptance_summary",
                        data=[{"label": "final_selected_runs", "value": 6}],
                    ),
                    ReportBlockDocument(
                        id="curve_family_summary",
                        type="table",
                        title="Curve Family Summary",
                        provider="curve_family_summary",
                        data=[{"metric": "assessed_runs", "value": 6}],
                    ),
                ],
            )
        ],
    )

    html = HtmlRenderer().render(document)

    assert '<details class="detail-block audit-block note-anchor" id="acceptance_summary" open>' in html
    assert '<details class="detail-block audit-block note-anchor" id="curve_family_summary" open>' in html


def test_html_renderer_moves_detail_purpose_to_margin_note_and_appendix() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={},
        sections=[
            ReportSectionDocument(
                id="failure_analysis",
                title="Failure Analysis",
                blocks=[
                    ReportBlockDocument(
                        id="failure_analysis_table",
                        type="table",
                        title="Failure Analysis Summary",
                        provider="failure_analysis",
                        data=[{"Field": "Bending compliance", "Value": "4 of 7 within criterion"}],
                    ),
                ],
            )
        ],
    )

    html = HtmlRenderer().render(document)

    assert "GRAFTED: scrollspy nav + inline note popovers" in html
    assert ".audit-block.note-anchor" in html
    assert ".layout { grid-template-columns: 310px minmax(0, 1fr); }" in html
    assert "grid-template-columns: 310px minmax(0, 1fr) var(--note-col" not in html
    assert "left: calc(100% + 18px)" not in html
    assert ".note-anchor h3:hover ~ aside.note" in html
    assert ".report-tracker { display: none !important; }" in html
    assert '<details class="detail-block audit-block note-anchor" id="failure_analysis_table" open>' in html
    assert '<button type="button" class="note-marker" aria-label="Show method note" aria-expanded="false">i</button>' in html
    assert '<aside class="note" role="note"><div class="note-label">Method</div>' in html
    assert '<p class="detail-purpose">' not in html
    assert '<section class="methods-appendix" aria-hidden="true">' in html
    assert "Appendix A — Methods &amp; definitions" in html
    assert "A.1 Failure Analysis Summary" in html
    assert "Bending evidence" in html


def test_html_renderer_keeps_section_statuses_secondary_to_header_cards() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={
            "report_completion_status": "COMPLETE_WITH_WARNINGS",
            "section_statuses": [
                {"section_id": "test_identification", "title": "Test Identification", "status": "complete_with_warnings"},
                {"section_id": "results", "title": "Results", "status": "complete"},
            ],
        },
        sections=[],
    )

    html = HtmlRenderer().render(document)

    assert 'class="report-state-card"' in html
    assert 'aria-label="Report Completion Summary"' in html
    assert "Required report content" in html
    assert "Recommended metadata" in html


def test_specimen_geometry_table_uses_geometry_specific_check() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={},
        sections=[
            ReportSectionDocument(
                id="specimen_geometry",
                title="Specimen Geometry",
                blocks=[
                    ReportBlockDocument(
                        id="specimen_geometry_table",
                        type="table",
                        title="Specimen Geometry",
                        provider="individual_results",
                        data=[
                            {
                                "run_id": "run_001",
                                "specimen_name": "S1",
                                "sample_id": "A1",
                                "width_mm": 10.0,
                                "thickness_mm": 2.0,
                                "area_mm2": 20.0,
                                "acceptance_state": "excluded",
                            },
                            {
                                "run_id": "run_002",
                                "specimen_name": "S2",
                                "sample_id": "A2",
                                "width_mm": 10.0,
                                "thickness_mm": "",
                                "area_mm2": 20.0,
                            },
                        ],
                    )
                ],
            )
        ],
    )

    html = HtmlRenderer().render(document)

    assert "Geometry check" in html
    assert "<th>Valid</th>" not in html
    assert "area = width x thickness within rounding tolerance" in html
    assert "Complete" in html
    assert "Review: missing thickness" in html
    assert "Test validity and inclusion decisions are reported in Section 8." in html


def test_formal_report_plot_block_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    block = {"id": "aggregate_stress_strain_plot"}
    data = {
        "spec_id": "aggregate_stress_strain_mean_variability",
        "source_spec": {},
        "vega_lite_spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "</script><p>unsafe</p>",
            "datasets": {
                "aggregate": [
                    {
                        "analysis_progress_percent": 0,
                        "mean": 0,
                        "std_lower": 0,
                        "std_upper": 0,
                        "min": 0,
                        "max": 0,
                        "n": 4,
                    },
                    {
                        "analysis_progress_percent": 100,
                        "mean": 233,
                        "std_lower": 196.3,
                        "std_upper": 269.7,
                        "min": 193,
                        "max": 282,
                        "n": 4,
                    },
                ]
            },
            "mark": "line",
        },
    }
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _vega_plot_block(block, data)
    context = _formal_report_plot_block_context(block, data)
    expected_json = json.dumps(data["vega_lite_spec"], ensure_ascii=False).replace("</", "<\\/")

    assert html == _legacy_vega_plot_block(block, data)
    assert context.projection_plane is ProjectionPlane.TEST
    assert context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK
    assert context.spec_json == Markup(expected_json)
    assert 'data-vega-block="vega-aggregate_stress_strain_plot"' in html
    assert 'id="vega-aggregate_stress_strain_plot" class="vega-chart" aria-label="Aggregate plot"' in html
    assert f'<script type="application/json" id="vega-aggregate_stress_strain_plot-spec">{expected_json}</script>' in html
    assert "<\\/script><p>unsafe<\\/p>" in html
    assert "Aggregate stress-strain plot legend" in html
    assert "mean +/- 1 SD (strength CV &asymp; 16 % at failure)" in html


def test_formal_report_plot_block_keeps_legacy_fallback(monkeypatch) -> None:
    block = {"id": "aggregate_stress_strain_plot"}
    data = {
        "spec_id": "aggregate_stress_strain_mean_variability",
        "source_spec": {},
        "vega_lite_spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "datasets": {"aggregate": [{"analysis_progress_percent": 100, "mean": 10, "std": 1, "n": 2}]},
            "mark": "line",
        },
    }
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _vega_plot_block(block, data) == _legacy_vega_plot_block(block, data)


def test_formal_report_plot_legend_jinja_matches_legacy_renderer_bytes(monkeypatch) -> None:
    vega_spec = {
        "datasets": {
            "aggregate": [
                {"analysis_progress_percent": 0, "mean": 0, "std_lower": 0, "std_upper": 0, "min": 0, "max": 0, "n": 4},
                {
                    "analysis_progress_percent": 100,
                    "mean": 233,
                    "std_lower": 196.3,
                    "std_upper": 269.7,
                    "min": 193,
                    "max": 282,
                    "n": 4,
                },
            ]
        }
    }
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    html = _plot_legend("aggregate_stress_strain_mean_variability", vega_spec, {})
    context = _formal_report_plot_legend_context("aggregate_stress_strain_mean_variability", vega_spec, {})

    assert html == _legacy_plot_legend("aggregate_stress_strain_mean_variability", vega_spec, {})
    assert context is not None
    assert context.projection_plane is ProjectionPlane.TEST
    assert context.recipe_result_kind is RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND
    assert context.sd_label_html == Markup("mean +/- 1 SD (strength CV &asymp; 16 % at failure)")
    assert context.range_label_html == Markup("observed range (n = 4)")
    assert 'class="plot-legend"' in html
    assert "individual replicate" in html
    assert "mean +/- 1 SD (strength CV &asymp; 16 % at failure)" in html
    assert "observed range (n = 4)" in html


def test_formal_report_plot_legend_empty_and_legacy_fallback(monkeypatch) -> None:
    vega_spec = {"datasets": {"aggregate": [{"analysis_progress_percent": 100, "mean": 10, "std": 1, "n": 2}]}}
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _plot_legend("failure_analysis_bending_distribution", vega_spec, {}) == ""
    assert _plot_legend("failure_analysis_bending_distribution", vega_spec, {}) == _legacy_plot_legend(
        "failure_analysis_bending_distribution",
        vega_spec,
        {},
    )

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    assert _plot_legend("aggregate_stress_strain_mean_variability", vega_spec, {}) == _legacy_plot_legend(
        "aggregate_stress_strain_mean_variability",
        vega_spec,
        {},
    )


def test_aggregate_plot_renders_curve_and_ci_legend_below_plot() -> None:
    document = ReportDocument(
        report_id="demo",
        title="Demo Report",
        metadata={},
        sections=[
            ReportSectionDocument(
                id="aggregate_results",
                title="Aggregated Results",
                blocks=[
                    ReportBlockDocument(
                        id="aggregate_stress_strain_plot",
                        type="vega_plot",
                        title="Stress-strain aggregate",
                        provider="aggregate_plot_spec",
                        data={
                            "spec_id": "aggregate_stress_strain_mean_variability",
                            "source_spec": {},
                            "vega_lite_spec": {
                                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                                "datasets": {
                                    "aggregate": [
                                        {
                                            "analysis_progress_percent": 0,
                                            "mean": 0,
                                            "std_lower": 0,
                                            "std_upper": 0,
                                            "min": 0,
                                            "max": 0,
                                            "n": 4,
                                        },
                                        {
                                            "analysis_progress_percent": 100,
                                            "mean": 233,
                                            "std_lower": 196.3,
                                            "std_upper": 269.7,
                                            "min": 193,
                                            "max": 282,
                                            "n": 4,
                                        },
                                    ]
                                },
                                "mark": "line",
                            },
                        },
                    )
                ],
            )
        ],
    )

    html = HtmlRenderer().render(document)

    assert "Aggregate stress-strain plot legend" in html
    assert "individual replicate" in html
    assert "mean +/- 1 SD (strength CV &asymp; 16 % at failure)" in html
    assert "observed range (n = 4)" in html
    assert "min-max envelope" not in html
    assert "95% CI = 95% confidence interval for the aggregate metric mean" in html
