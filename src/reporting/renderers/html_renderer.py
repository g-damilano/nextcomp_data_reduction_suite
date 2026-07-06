from __future__ import annotations

import json
import math
import os
import re
from html import escape, unescape
from typing import Any

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
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_formal_report_aggregate_svg,
    render_formal_report_boolean_badge,
    render_formal_report_block,
    render_formal_report_data_use_deviations,
    render_formal_report_deviations_section,
    render_formal_report_detail_block,
    render_formal_report_dimension_header,
    render_formal_report_evidence_table,
    render_formal_report_failure_bending_svg,
    render_formal_report_field_value_table,
    render_formal_report_fragment_stack,
    render_formal_method_report,
    render_formal_report_missing_data,
    render_formal_report_paragraph,
    render_formal_report_plot_block,
    render_formal_report_plot_legend,
    render_formal_report_plot_note,
    render_formal_report_raw_evidence_note,
    render_formal_report_remarks,
    render_formal_report_review_section,
    render_formal_report_section_pill,
    render_formal_report_sections,
    render_formal_report_state_card,
    render_formal_report_table,
    render_formal_report_table_section,
    render_formal_report_tracker,
    render_report_empty_paragraph,
    render_report_heading_fragment,
    render_report_paragraph_fragment,
)
from reporting.core.report_document import ReportDocument
from reporting.renderers.formatting_standard import (
    REPORT_FORMATTING_CSS,
    REPORT_FORMATTING_SCRIPT,
    ReportNoteCollector,
    note_html,
    render_methods_appendix,
    render_note_marker,
)
from reporting.run_labels import replace_run_ids_for_display, run_display_label


class HtmlRenderer:
    renderer_id = "html"

    def render(self, document: ReportDocument) -> str:
        payload = document.to_dict()
        sections = payload.get("sections", [])
        metadata = payload.get("metadata", {})
        section_list = sections if isinstance(sections, list) else []
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        note_collector = ReportNoteCollector()
        sections_html = _sections(section_list, metadata_dict, note_collector=note_collector)
        appendix_html = render_methods_appendix(note_collector, projection_plane=ProjectionPlane.TEST)
        if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
            return _legacy_formal_method_report_html(
                payload=payload,
                metadata=metadata_dict,
                sections=section_list,
                sections_html=sections_html,
                appendix_html=appendix_html,
            )
        context = FormalMethodReportContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.FORMAL_METHOD_REPORT,
            page_title=str(payload.get("title", "Method Report")),
            report_state_card_html=Markup(_report_state_card(payload, metadata_dict, section_list)),
            report_tracker_html=Markup(_report_tracker(section_list, metadata_dict)),
            sections_html=Markup(sections_html),
            appendix_html=Markup(appendix_html),
            formatting_css=Markup(REPORT_FORMATTING_CSS),
            formatting_script=Markup(REPORT_FORMATTING_SCRIPT),
        )
        return render_formal_method_report(context)


def _legacy_formal_method_report_html(
    *,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    sections: list[Any],
    sections_html: str,
    appendix_html: str,
) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(payload.get("title", "Method Report")))}</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #5f6f80;
      --line: #d7dee8;
      --soft: #f7f9fb;
      --panel: #ffffff;
      --warn-bg: #fff7df;
      --warn-line: #e5bd48;
      --ok-bg: #edf8f0;
      --ok-line: #65a878;
      --bad-bg: #fdecec;
      --bad-line: #d56a6a;
      --brand: #185f8f;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: var(--ink); font-family: Arial, Helvetica, sans-serif; background: #f3f6f9; line-height: 1.45; }}
    .page {{ max-width: 1320px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; line-height: 1.2; }}
    h2 {{ margin: 0; font-size: 19px; line-height: 1.2; }}
    h3 {{ margin: 18px 0 8px; font-size: 15px; line-height: 1.2; }}
    p {{ line-height: 1.45; }}
    a {{ color: var(--brand); }}
    .muted, .section-note, .empty-note {{ color: var(--muted); }}
    .layout {{ display: grid; grid-template-columns: 310px minmax(0, 1fr); gap: 14px; align-items: start; }}
    .report-content {{ min-width: 0; }}
    .report-state-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px; margin-bottom: 16px; }}
    .report-state-top {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: start; border-bottom: 1px solid #eef2f6; padding-bottom: 12px; margin-bottom: 12px; }}
    .report-state-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin-bottom: 3px; }}
    .report-state-status {{ border-left: 4px solid var(--warn-line); background: var(--warn-bg); padding: 8px 12px; border-radius: 8px; min-width: 260px; }}
    .report-state-status.ok {{ border-left-color: var(--ok-line); background: var(--ok-bg); }}
    .report-state-status.bad {{ border-left-color: var(--bad-line); background: var(--bad-bg); }}
    .report-state-status strong {{ display: block; font-size: 14px; }}
    .report-state-status span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 2px; }}
    .report-state-table {{ margin-top: 8px; }}
    .report-state-table th:first-child, .report-state-table td:first-child {{ width: 210px; font-weight: 700; }}
    .report-state-table td:nth-child(2) {{ width: 245px; }}
    .state-text {{ font-weight: 700; }}
    .state-text.ok {{ color: #28663a; }}
    .state-text.warn {{ color: #8a6500; }}
    .state-text.bad {{ color: #9b2d2d; }}
    .report-state-note {{ color: var(--muted); font-size: 13px; margin: 10px 0 0; }}
    .report-state-links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
    .report-state-links a {{ border: 1px solid var(--line); border-radius: 6px; background: #fff; padding: 7px 9px; text-decoration: none; font-weight: 700; font-size: 13px; }}
    .report-tracker {{ position: sticky; top: 12px; width: 310px; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 8px; }}
    .report-tracker a {{ display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 6px; align-items: center; color: inherit; text-decoration: none; padding: 5px 6px; min-height: 30px; border-radius: 8px; border-bottom: 1px solid #eef2f6; }}
    .report-tracker a:last-child {{ border-bottom: 0; }}
    .report-tracker a:hover {{ background: var(--soft); }}
    .report-tracker b {{ font-size: 13px; }}
    .report-tracker span {{ font-size: 13px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .report-tracker em {{ justify-self: end; width: fit-content; margin-left: 4px; }}
    .report-section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; margin-bottom: 14px; }}
    .report-section header {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; border-bottom: 1px solid #eef2f6; padding-bottom: 10px; margin-bottom: 12px; }}
    .report-section--empty {{ padding: 12px 16px; }}
    .report-section--empty header {{ border-bottom: 0; margin-bottom: 0; padding-bottom: 0; }}
    .report-section--empty .empty-note {{ margin: 6px 0 0; font-size: 13px; }}
    .pill {{ display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 3px 8px; font-size: 11px; font-style: normal; white-space: nowrap; }}
    .pill.ok {{ background: var(--ok-bg); border-color: var(--ok-line); }}
    .pill.warn {{ background: var(--warn-bg); border-color: var(--warn-line); }}
    .pill.bad {{ background: var(--bad-bg); border-color: var(--bad-line); }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 5px 10px; font-weight: 700; font-size: 12px; letter-spacing: 0; background: var(--soft); color: var(--ink); }}
    .badge--ok {{ background: var(--ok-bg); color: #28663a; }}
    .badge--warn {{ background: var(--warn-bg); color: #8a6500; }}
    .badge--bad {{ background: var(--bad-bg); color: #9b2d2d; }}
    .block {{ margin-top: 16px; }}
    .detail-block {{ border: 1px solid var(--line); border-radius: 10px; background: #fcfdff; padding: 0; margin-top: 12px; }}
    details.detail-block > summary {{ cursor: pointer; list-style: none; padding: 12px 14px; font-weight: 700; }}
    details.detail-block > summary::-webkit-details-marker {{ display: none; }}
    details.detail-block > summary::after {{ content: "Show details"; float: right; color: var(--brand); font-weight: 700; }}
    details.detail-block[open] > summary::after {{ content: "Hide details"; }}
    .detail-body {{ padding: 0 14px 14px; }}
    .detail-purpose {{ color: var(--muted); margin: 0 0 10px; }}
    .table-wrap {{ width: 100%; overflow-x: auto; margin: 8px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 8px 0; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; word-break: normal; }}
    th {{ background: var(--soft); font-weight: 700; }}
    .compact {{ max-width: 100%; }}
    .results-table th .dimension-label {{ font-weight: 700; }}
    .results-table th .unit-label {{ font-weight: 500; color: var(--muted); white-space: nowrap; }}
    .report-row--missing td:first-child {{ border-left: 4px solid var(--warn-line); }}
    .report-row--missing td {{ background: #fffaf0; }}
    .report-row--present td:first-child {{ border-left: 4px solid var(--ok-line); }}
    .state-dot {{ display: inline-block; width: 0.65em; height: 0.65em; border-radius: 999px; margin-right: 0.45em; vertical-align: baseline; }}
    .state-dot--missing {{ background: var(--warn-line); }}
    .state-dot--present {{ background: var(--ok-line); }}
    .yes {{ font-weight: 700; }}
    .no {{ color: var(--muted); font-weight: 700; }}
    code {{ background: #eef2f6; padding: 1px 4px; border-radius: 4px; }}
    .plot {{ border: 1px solid var(--line); border-radius: 10px; padding: 12px; margin-top: 14px; background: #fcfdff; max-width: 100%; overflow: hidden; }}
    .plot-note {{ color: var(--muted); font-size: 13px; margin: 0 0 10px; }}
    .plot-legend {{ display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; color: var(--muted); font-size: 12px; margin: 10px 2px 0; }}
    .plot-legend strong {{ color: var(--ink); margin-right: 2px; }}
    .plot-legend-item {{ display: inline-flex; gap: 6px; align-items: center; }}
    .plot-legend-swatch {{ display: inline-block; width: 22px; height: 0; border-top: 3px solid #1f78b4; }}
    .plot-legend-swatch.replicate {{ border-top-color: #78aeda; opacity: .45; }}
    .plot-legend-swatch.band {{ height: 10px; border: 0; background: rgba(42, 127, 184, .28); }}
    .plot-legend-swatch.envelope {{ height: 10px; border: 0; background: rgba(123, 183, 223, .20); }}
    .plot-legend-ci {{ flex-basis: 100%; }}
    .vega-chart {{ min-height: 330px; width: 100%; max-width: 100%; overflow: hidden; }}
    .vega-chart .vega-embed, .vega-chart .vega-embed > div {{ max-width: 100%; }}
    .vega-chart svg {{ display: block; width: 100%; max-width: 100%; height: auto; }}
    .vega-chart canvas {{ max-width: 100%; height: auto; }}
    .vega-fallback {{ margin-bottom: 12px; width: 100%; max-width: 100%; overflow: hidden; }}
    .vega-fallback svg {{ display: block; width: 100%; max-width: 100%; height: auto; }}
    .vg-tooltip {{ max-width: 340px !important; white-space: normal !important; overflow-wrap: anywhere !important; pointer-events: none !important; }}
    .vg-tooltip table {{ width: auto !important; table-layout: auto !important; border-collapse: collapse !important; font-size: 12px !important; background: #fff !important; }}
    .vg-tooltip th, .vg-tooltip td {{ padding: 2px 6px !important; border: 0 !important; white-space: nowrap !important; overflow-wrap: normal !important; }}
    @media (max-width: 920px) {{
      .page {{ padding: 18px; }}
      .layout {{ display: block; }}
      .report-tracker {{ position: static; float: none; width: auto; margin-left: 0; margin-bottom: 14px; }}
      .report-state-top {{ grid-template-columns: 1fr; }}
      .report-state-status {{ min-width: 0; }}
    }}
    @media print {{
      body {{ background: white; }}
      .page {{ padding: 0; max-width: none; }}
      .layout {{ display: block; }}
      .report-tracker {{ position: static; float: none; width: auto; margin-left: 0; margin-bottom: 12px; page-break-after: avoid; }}
      .report-section, .report-state-card {{ break-inside: avoid; border-color: #999; }}
    }}
{REPORT_FORMATTING_CSS}
  </style>
  <script>
    document.addEventListener("DOMContentLoaded", function () {{
      if (!window.vegaEmbed) {{ return; }}
      document.querySelectorAll("[data-vega-block]").forEach(function (block) {{
        var target = block.querySelector(".vega-chart");
        var script = block.querySelector("script[type='application/json']");
        if (!target || !script) {{ return; }}
        try {{
          var spec = JSON.parse(script.textContent);
          window.vegaEmbed(target, spec, {{actions: false, renderer: "svg"}}).then(function () {{
            var fallback = block.querySelector(".vega-fallback");
            var graphic = target.querySelector("svg, canvas");
            var bounds = graphic ? graphic.getBoundingClientRect() : null;
            if (fallback && bounds && bounds.width > 10 && bounds.height > 10) {{
              fallback.style.display = "none";
            }}
          }});
        }} catch (error) {{
          console.warn("Could not render Vega block", error);
        }}
      }});
    }});
  </script>
</head>
<body>
  <div class="page">
    {_legacy_report_state_card(payload, metadata, sections)}
    <div class="layout">
      {_legacy_report_tracker(sections, metadata)}
      <main class="report-content">
        {sections_html}
        {appendix_html}
      </main>
    </div>
  </div>
  {REPORT_FORMATTING_SCRIPT}
</body>
</html>
"""


def _report_state_card(payload: dict[str, Any], metadata: dict[str, Any], sections: list[Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_report_state_card(payload, metadata, sections)
    return render_formal_report_state_card(_formal_report_state_card_context(payload, metadata, sections))


def _formal_report_state_card_context(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    sections: list[Any],
) -> FormalReportStateCardContext:
    completion = str(metadata.get("report_completion_status") or "")
    quality = str(metadata.get("report_quality_gate_status") or _quality_from_completion(completion))
    required_missing = _int_value(metadata.get("required_missing_count", 0))
    recommended_missing = _int_value(metadata.get("recommended_missing_count", 0))
    standard_required_missing = _int_value(metadata.get("standard_required_missing_count", 0))
    selected = _int_value(metadata.get("selected_run_count", 0))
    run_count = _run_count_from_sections(sections, selected)
    missing_section_count = _missing_section_count(metadata)
    method_context = " | ".join(
        str(value)
        for value in (
            metadata.get("method_name"),
            metadata.get("standard_reference"),
        )
        if value not in (None, "")
    )
    method_context_html = (
        _formal_report_paragraph_fragment(escape(method_context), paragraph_class="report-state-note")
        if method_context
        else Markup("")
    )
    method_boundary_note = str(metadata.get("method_boundary_note") or "")
    method_boundary_html = (
        _formal_report_paragraph_fragment(escape(method_boundary_note), paragraph_class="report-state-note")
        if method_boundary_note
        else Markup("")
    )
    status_class = _state_card_status_class(quality or completion)
    if required_missing:
        required_state = f"<span class=\"state-text bad\">{required_missing} required fields missing</span>"
    elif standard_required_missing:
        required_state = f"<span class=\"state-text warn\">{standard_required_missing} standard-required gaps recorded</span>"
    else:
        required_state = "<span class=\"state-text ok\">Complete</span>"
    recommended_state = (
        "<span class=\"state-text ok\">Complete</span>"
        if recommended_missing == 0
        else f"<span class=\"state-text warn\">{recommended_missing} fields missing across {missing_section_count} sections</span>"
    )
    data_state = (
        "<span class=\"state-text warn\">Review required</span>"
        if run_count and selected != run_count
        else "<span class=\"state-text ok\">All runs included</span>"
    )
    aggregate_basis = f"Included {selected} of {run_count or selected} runs" if selected else "No selected runs recorded"
    return FormalReportStateCardContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_STATE_CARD,
        title_html=Markup(escape(str(payload.get("title", "Method Report")))),
        lede_html=_formal_report_paragraph_fragment(
            "Formal method results and report-ready evidence.",
            paragraph_class="report-state-note",
        ),
        method_context_html=method_context_html,
        method_boundary_html=method_boundary_html,
        status_class=status_class,
        quality_label_html=Markup(escape(_human_value(quality or completion or "UNKNOWN"))),
        completion_label_html=Markup(escape(_human_value(completion or "completion unknown"))),
        required_state_html=Markup(required_state),
        required_location_html=Markup(_required_location(required_missing, standard_required_missing)),
        recommended_state_html=Markup(recommended_state),
        recommended_location_html=Markup(_recommended_location(recommended_missing)),
        data_state_html=Markup(data_state),
        aggregate_basis_html=Markup(escape(aggregate_basis)),
    )


def _legacy_report_state_card(payload: dict[str, Any], metadata: dict[str, Any], sections: list[Any]) -> str:
    context = _formal_report_state_card_context(payload, metadata, sections)
    return f"""<div aria-label="Report Completion Summary" class="report-state-card" id="report-state">
  <div class="report-state-top">
    <div>
      <div class="report-state-label">Test report</div>
      <h1 id="report-title">{context.title_html}</h1>
      {context.lede_html}
      {context.method_context_html}
      {context.method_boundary_html}
    </div>
    <div class="report-state-status {context.status_class}" data-key="report_completion_status">
      <strong>{context.quality_label_html}</strong>
      <span>{context.completion_label_html}</span>
    </div>
  </div>
  <div class="table-wrap">
    <table class="compact report-state-table">
      <thead><tr><th>Area</th><th>State</th><th>Location</th></tr></thead>
      <tbody>
        <tr data-key="required_missing_count"><td>Required report content</td><td>{context.required_state_html}</td><td>{context.required_location_html}</td></tr>
        <tr data-key="recommended_missing_count"><td>Recommended metadata</td><td>{context.recommended_state_html}</td><td>{context.recommended_location_html}</td></tr>
        <tr><td>Data use</td><td>{context.data_state_html}</td><td>Run inclusion is shown in <a href="#section-individual_test_results">Section 8</a> and summarised in <a href="#section-deviations_from_standard">Section 11.2</a>.</td></tr>
        <tr><td>Aggregate basis</td><td>{context.aggregate_basis_html}</td><td><a href="#section-aggregated_results">Section 9</a></td></tr>
      </tbody>
    </table>
  </div>
</div>"""


def _report_tracker(sections: list[Any], metadata: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_report_tracker(sections, metadata)
    return render_formal_report_tracker(_formal_report_tracker_context(sections, metadata))


def _formal_report_tracker_context(sections: list[Any], metadata: dict[str, Any]) -> FormalReportTrackerContext:
    visible = _formal_sections(sections)
    status_by_id = _status_by_id(metadata)
    deviations_need_review = _deviations_need_review(metadata, sections)
    links: list[FormalReportTrackerLinkContext] = []
    for number, section in enumerate(visible, start=1):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or "")
        title = str(section.get("title") or section_id or "Section")
        pill_html = _section_pill(
            section_id,
            status_by_id.get(section_id, {}),
            tracker=True,
            force_review=section_id == "deviations_from_standard" and deviations_need_review,
        )
        links.append(
            FormalReportTrackerLinkContext(
                section_id_html=Markup(escape(section_id)),
                number=number,
                title_html=Markup(escape(title)),
                pill_html=Markup(pill_html),
            )
        )
    return FormalReportTrackerContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TRACKER,
        links=tuple(links),
    )


def _legacy_report_tracker(sections: list[Any], metadata: dict[str, Any]) -> str:
    context = _formal_report_tracker_context(sections, metadata)
    links = [
        f"<a href=\"#section-{link.section_id_html}\"><b>{link.number}</b><span>{link.title_html}</span>{link.pill_html}</a>"
        for link in context.links
    ]
    return f"<nav aria-label=\"Report sections\" class=\"report-tracker\">{''.join(links)}</nav>"


def _formal_sections(sections: list[Any]) -> list[dict[str, Any]]:
    return [section for section in sections if isinstance(section, dict)]


def _status_by_id(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(status.get("section_id")): status
        for status in metadata.get("section_statuses", []) or []
        if isinstance(status, dict)
    }


def _missing_section_count(metadata: dict[str, Any]) -> int:
    count = 0
    for status in metadata.get("section_statuses", []) or []:
        if not isinstance(status, dict):
            continue
        missing = _section_missing_count(status)
        if missing:
            count += 1
    return count


def _section_missing_count(status: dict[str, Any]) -> int:
    return int(status.get("missing_required_count") or 0) + int(status.get("missing_recommended_count") or 0)


def _run_count_from_sections(sections: list[Any], fallback: int) -> int:
    for section in sections:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            if str(block.get("id") or "") != "individual_results_table":
                continue
            data = block.get("data")
            if isinstance(data, list):
                return len([row for row in data if isinstance(row, dict)])
    return fallback


def _state_card_status_class(status: str) -> str:
    normalized = str(status or "").casefold()
    if "blocked" in normalized or "incomplete" in normalized or "fail" in normalized:
        return "bad"
    if "warning" in normalized or "warn" in normalized or "review" in normalized:
        return ""
    if "ready" in normalized or "complete" in normalized:
        return "ok"
    return ""


def _required_location(required_missing: int, standard_required_missing: int = 0) -> str:
    if required_missing:
        return '<a href="#section-deviations_from_standard">Section 11.1</a>'
    if standard_required_missing:
        return '<a href="#section-deviations_from_standard">Section 11.2</a>'
    return "Required report content complete."


def _recommended_location(recommended_missing: int) -> str:
    if recommended_missing:
        return '<a href="#section-deviations_from_standard">Section 11.1</a>'
    return "No recommended metadata missing."


def _sections(
    sections: list[Any],
    metadata: dict[str, Any],
    *,
    note_collector: ReportNoteCollector,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_sections(sections, metadata, note_collector=note_collector)
    return render_formal_report_sections(_formal_report_sections_context(sections, metadata, note_collector=note_collector))


def _formal_report_sections_context(
    sections: list[Any],
    metadata: dict[str, Any],
    *,
    note_collector: ReportNoteCollector,
) -> FormalReportSectionsContext:
    rendered: list[FormalReportSectionContext] = []
    status_by_id = _status_by_id(metadata)
    all_sections = [section for section in sections if isinstance(section, dict)]
    deviations_need_review = _deviations_need_review(metadata, all_sections)
    section_numbers = {
        str(section.get("id") or ""): index
        for index, section in enumerate(_formal_sections(sections), start=1)
    }
    for section in _formal_sections(sections):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or section.get("title") or "section")
        section_status = status_by_id.get(str(section.get("id") or ""))
        number = section_numbers.get(section_id, len(rendered) + 1)
        title = str(section.get("title", section.get("id", "Section")))
        empty_section = _empty_metadata_section(section)
        section_class = "report-section report-section--empty" if empty_section else "report-section"
        if section_id == "deviations_from_standard":
            body_html = _deviations_section(section, all_sections, section_numbers)
        elif section_id == "remarks":
            body_html = _remarks_section(section)
        else:
            rendered_blocks = [
                _formal_block(block, section_id, note_collector=note_collector)
                for block in section.get("blocks", []) or []
                if isinstance(block, dict)
            ]
            rendered_blocks = [block for block in rendered_blocks if block]
            body_html = (
                "".join(rendered_blocks)
                if rendered_blocks
                else _formal_report_paragraph(
                    "No report-ready values were supplied for this section.",
                    paragraph_class="empty-note",
                )
            )
        rendered.append(
            FormalReportSectionContext(
                section_class=section_class,
                section_id_html=Markup(escape(section_id)),
                number=number,
                title_html=Markup(escape(title)),
                pill_html=Markup(
                    _section_pill(
                        section_id,
                        section_status or {},
                        force_review=section_id == "deviations_from_standard" and deviations_need_review,
                    )
                ),
                body_html=Markup(body_html),
            )
        )
    return FormalReportSectionsContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTIONS,
        sections=tuple(rendered),
    )


def _legacy_sections(
    sections: list[Any],
    metadata: dict[str, Any],
    *,
    note_collector: ReportNoteCollector,
) -> str:
    parts: list[str] = []
    status_by_id = _status_by_id(metadata)
    all_sections = [section for section in sections if isinstance(section, dict)]
    deviations_need_review = _deviations_need_review(metadata, all_sections)
    section_numbers = {
        str(section.get("id") or ""): index
        for index, section in enumerate(_formal_sections(sections), start=1)
    }
    for section in _formal_sections(sections):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or section.get("title") or "section")
        section_status = status_by_id.get(str(section.get("id") or ""))
        number = section_numbers.get(section_id, len(parts) + 1)
        title = str(section.get("title", section.get("id", "Section")))
        empty_section = _empty_metadata_section(section)
        section_class = "report-section report-section--empty" if empty_section else "report-section"
        parts.append(
            f"<section class=\"{section_class}\" id=\"section-{escape(section_id)}\">"
            f"<header><h2>{number}. {escape(title)}</h2>"
            f"{_section_pill(section_id, section_status or {}, force_review=section_id == 'deviations_from_standard' and deviations_need_review)}</header>"
        )
        if section_id == "deviations_from_standard":
            parts.append(_deviations_section(section, all_sections, section_numbers))
        elif section_id == "remarks":
            parts.append(_remarks_section(section))
        else:
            rendered_blocks = [
                _formal_block(block, section_id, note_collector=note_collector)
                for block in section.get("blocks", []) or []
                if isinstance(block, dict)
            ]
            rendered_blocks = [block for block in rendered_blocks if block]
            parts.append(
                "".join(rendered_blocks)
                if rendered_blocks
                else _formal_report_paragraph(
                    "No report-ready values were supplied for this section.",
                    paragraph_class="empty-note",
                )
            )
        parts.append("</section>")
    return "\n".join(parts)


def _section_pill(section_id: str, status: dict[str, Any], *, tracker: bool = False, force_review: bool = False) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_section_pill(section_id, status, tracker=tracker, force_review=force_review)
    return render_formal_report_section_pill(
        _formal_report_section_pill_context(section_id, status, tracker=tracker, force_review=force_review)
    )


def _legacy_section_pill(section_id: str, status: dict[str, Any], *, tracker: bool = False, force_review: bool = False) -> str:
    context = _formal_report_section_pill_context(
        section_id,
        status,
        tracker=tracker,
        force_review=force_review,
    )
    return f"<em class=\"pill {context.pill_class}\">{context.label_html}</em>"


def _formal_report_section_pill_context(
    section_id: str,
    status: dict[str, Any],
    *,
    tracker: bool = False,
    force_review: bool = False,
) -> FormalReportSectionPillContext:
    missing = _section_missing_count(status) if status else 0
    state = str(status.get("status") or "") if status else ""
    if section_id == "deviations_from_standard":
        label = "Review" if force_review or missing or state == "complete_with_warnings" else "OK"
        cls = "warn" if label == "Review" else "ok"
    elif missing:
        label = f"{missing} missing" if tracker else "Metadata incomplete"
        cls = "warn"
    elif state == "incomplete":
        label = "Incomplete"
        cls = "bad"
    else:
        label = "OK" if tracker else "Complete"
        cls = "ok"
    return FormalReportSectionPillContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_SECTION_PILL,
        pill_class=cls,
        label_html=Markup(escape(label)),
    )


def _deviations_need_review(metadata: dict[str, Any], sections: list[Any]) -> bool:
    if _int_value(metadata.get("required_missing_count")) or _int_value(metadata.get("recommended_missing_count")):
        return True
    if _int_value(metadata.get("standard_deviation_count")):
        return True
    selected = _int_value(metadata.get("selected_run_count", 0))
    run_count = _run_count_from_sections(sections, selected)
    return bool(run_count and selected != run_count)


def _empty_metadata_section(section: dict[str, Any]) -> bool:
    blocks = [block for block in section.get("blocks", []) or [] if isinstance(block, dict)]
    if not blocks:
        return False
    if any(str(block.get("type") or "") != "field_table" for block in blocks):
        return False
    for block in blocks:
        data = block.get("data")
        if not isinstance(data, list):
            return False
        if any(isinstance(row, dict) and _field_value_state(row) != "missing" for row in data):
            return False
    return True


def _formal_block(block: dict[str, Any], section_id: str, *, note_collector: ReportNoteCollector | None = None) -> str:
    raw_title = str(block.get("title") or block.get("id") or "Block")
    title = escape(_display_title(raw_title))
    block_type = str(block.get("type") or "")
    data = block.get("data")
    block_id = _html_id(str(block.get("id") or title)).replace("vega-", "")
    if block_type == "field_table":
        return _formal_field_table(data if isinstance(data, list) else [])
    if block_type == "vega_plot":
        return _formal_report_block(block_id, title, _vega_plot_block(block, data if isinstance(data, dict) else {}))
    if isinstance(data, list):
        if block_id == "specimen_geometry_table":
            return _specimen_geometry_table(data)
        if block_id == "individual_results_table":
            return _individual_results_table(data)
        if block_id == "aggregate_statistics_table":
            return _aggregate_statistics_formal(data)
        if block_id in {"characteristic_points_table", "feature_lines_table"}:
            return ""
        if block_id in {"failure_analysis_table", "acceptance_summary", "curve_family_summary"} and section_id == "failure_analysis":
            content = _block_table_content(block_id, block_type, data)
            return _supporting_detail(block_id, title, content, len(data), note_collector=note_collector)
        content = _block_table_content(block_id, block_type, data)
        if _should_collapse_block(block, data):
            return _details(block_id, title, content, row_count=len(data), block_type=block_type, note_collector=note_collector)
        return _formal_report_block(block_id, title, content)
    if isinstance(data, dict):
        return _formal_report_block(block_id, title, _table([data]))
    if data:
        return _formal_report_block(block_id, title, f"<p>{escape(str(data))}</p>")
    return _formal_report_block(block_id, title, "<p class=\"muted\">No report data.</p>")


def _formal_report_block(block_id: str, title_html: str, content_html: str) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_formal_report_block(block_id, title_html, content_html)
    return render_formal_report_block(_formal_report_block_context(block_id, title_html, content_html))


def _legacy_formal_report_block(block_id: str, title_html: str, content_html: str) -> str:
    return f"<div class=\"block\" id=\"{escape(block_id)}\"><h3>{title_html}</h3>{content_html}</div>"


def _formal_report_block_context(block_id: str, title_html: str, content_html: str) -> FormalReportBlockContext:
    return FormalReportBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BLOCK,
        block_id_html=Markup(escape(block_id)),
        title_html=Markup(title_html),
        content_html=Markup(content_html),
    )


def _block(block: dict[str, Any]) -> str:
    return _formal_block(block, "", note_collector=ReportNoteCollector())


def _formal_field_table(rows: list[Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_formal_field_table(rows)
    present_rows = _formal_field_table_rendered_rows(rows)
    if not present_rows:
        return _formal_report_paragraph(
            "No report-ready values were supplied for this section.",
            paragraph_class="empty-note",
        )
    return _render_formal_report_table_or_empty(present_rows, table_class="compact")


def _legacy_formal_field_table(rows: list[Any]) -> str:
    fragments = _formal_field_table_fragments(rows, legacy=True)
    return "".join(str(fragment) for fragment in fragments)


def _formal_field_table_fragments(rows: list[Any], *, legacy: bool = False) -> tuple[Markup, ...]:
    present_rows = _formal_field_table_rendered_rows(rows)
    if not present_rows:
        paragraph = (
            _legacy_formal_report_paragraph
            if legacy
            else _formal_report_paragraph
        )(
            "No report-ready values were supplied for this section.",
            paragraph_class="empty-note",
        )
        return (Markup(paragraph),)
    table = _legacy_table(present_rows, table_class="compact") if legacy else _table(present_rows, table_class="compact")
    return (Markup(table),)


def _formal_field_table_rendered_rows(rows: list[Any]) -> list[dict[str, Any]]:
    present_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _field_value_state(row) == "missing":
            continue
        present_rows.append(
            {
                "Field": row.get("label") or row.get("field") or row.get("key") or "",
                "Value": row.get("value", ""),
            }
        )
    return present_rows


def _specimen_geometry_table(rows: list[Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_specimen_geometry_table(rows)
    return render_formal_report_table_section(_specimen_geometry_table_section_context(rows))


def _legacy_specimen_geometry_table(rows: list[Any]) -> str:
    fragments = _specimen_geometry_fragments(rows, legacy=True)
    return "".join(str(fragment) for fragment in fragments)


def _specimen_geometry_fragments(rows: list[Any], *, legacy: bool = False) -> tuple[Markup, ...]:
    rendered = _specimen_geometry_rendered_rows(rows)
    paragraph = _legacy_formal_report_paragraph if legacy else _formal_report_paragraph
    table = _legacy_table if legacy else _table
    note = paragraph(_SPECIMEN_GEOMETRY_NOTE, paragraph_class="muted")
    return (Markup(note), Markup(table(rendered, table_class="results-table")))


_SPECIMEN_GEOMETRY_NOTE = (
    "Geometry check confirms width, thickness, and calculated area are present "
    "and internally consistent (area = width x thickness within rounding tolerance). Test validity "
    "and inclusion decisions are reported in Section 8."
)


def _specimen_geometry_rendered_rows(rows: list[Any]) -> list[dict[str, Any]]:
    optional_fields = [
        ("Distance between end tabs / unsupported length / mm", "distance_between_end_tabs_mm"),
        ("Tab length / mm", "tab_length_mm"),
        ("Tab thickness / mm", "tab_thickness_mm"),
    ]
    visible_optional = [
        (label, key)
        for label, key in optional_fields
        if any(isinstance(row, dict) and row.get(key) not in (None, "") for row in rows)
    ]
    rendered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rendered_row = {
            "Run #": run_display_label(row.get("run_id", "")),
            "Specimen": row.get("specimen_name", ""),
            "Sample": row.get("sample_id", ""),
            "Width / mm": _format_fixed(row.get("width_mm"), 3),
            "Thickness / mm": _format_fixed(row.get("thickness_mm"), 3),
            "Area / mm2": _format_fixed(row.get("area_mm2"), 2),
        }
        for label, key in visible_optional:
            rendered_row[label] = _format_fixed(row.get(key), 3)
        rendered_row["Geometry check"] = _geometry_check_label(row)
        rendered.append(rendered_row)
    return rendered


def _specimen_geometry_table_section_context(rows: list[Any]) -> FormalReportTableSectionContext:
    table = _formal_report_table_context(
        _specimen_geometry_rendered_rows(rows),
        table_class="results-table",
    )
    return FormalReportTableSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
        paragraph_class="muted",
        intro_html=Markup(_SPECIMEN_GEOMETRY_NOTE),
        intro_paragraph_html=_formal_report_paragraph_fragment(_SPECIMEN_GEOMETRY_NOTE, paragraph_class="muted"),
        table=table,
        empty_table_html=Markup(render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST)),
    )


def _individual_results_table(rows: list[Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_individual_results_table(rows)
    return _render_formal_report_table_or_empty(
        _individual_results_rendered_rows(rows),
        columns=_INDIVIDUAL_RESULTS_KEYS,
        headers=_individual_results_headers(),
        table_class="results-table",
        raw_html_columns={"Valid"},
    )


def _legacy_individual_results_table(rows: list[Any]) -> str:
    fragments = _individual_results_fragments(rows, legacy=True)
    return "".join(str(fragment) for fragment in fragments)


def _individual_results_fragments(rows: list[Any], *, legacy: bool = False) -> tuple[Markup, ...]:
    rendered = _individual_results_rendered_rows(rows)
    table = _legacy_table if legacy else _table
    return (
        Markup(
            table(
                rendered,
                columns=_INDIVIDUAL_RESULTS_KEYS,
                headers=_individual_results_headers(),
                table_class="results-table",
                raw_html_columns={"Valid"},
            )
        ),
    )


_INDIVIDUAL_RESULTS_KEYS = [
    "Run #",
    "Specimen",
    "Sample",
    "Valid",
    "Max load",
    "Strength",
    "Modulus",
    "Failure strain",
    "Failure mode",
    "Acceptance",
]


def _individual_results_headers() -> list[str]:
    return [
        "Run #",
        "Specimen",
        "Sample",
        "Valid",
        _dimension_header("Max load", "N"),
        _dimension_header("Strength", "MPa"),
        _dimension_header("Modulus", "MPa"),
        _dimension_header("Failure strain", "%"),
        "Failure mode",
        "Acceptance",
    ]


def _individual_results_rendered_rows(rows: list[Any]) -> list[dict[str, Any]]:
    rendered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rendered.append(
            {
                "Run #": run_display_label(row.get("run_id", "")),
                "Specimen": row.get("specimen_name", ""),
                "Sample": row.get("sample_id", ""),
                "Valid": _yes_no(_result_valid(row)),
                "Max load": _format_sig_or_missing(row.get("max_load_N"), 3, thousands=True),
                "Strength": _format_sig_or_missing(row.get("compressive_strength_MPa"), 3),
                "Modulus": _format_sig_or_missing(row.get("compressive_modulus_MPa"), 3, thousands=True),
                "Failure strain": _format_sig_or_missing(row.get("failure_strain_percent"), 2),
                "Failure mode": _failure_mode_display(row.get("primary_failure_mode") or row.get("failure_mode")),
                "Acceptance": _human_value(row.get("acceptance_state") or ""),
            }
        )
    return rendered


def _aggregate_statistics_formal(rows: list[Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_aggregate_statistics_formal(rows)
    return _render_formal_report_table_or_empty(
        _aggregate_statistics_formal_rendered_rows(rows),
        table_class="results-table",
    )


def _legacy_aggregate_statistics_formal(rows: list[Any]) -> str:
    fragments = _aggregate_statistics_formal_fragments(rows, legacy=True)
    return "".join(str(fragment) for fragment in fragments)


def _aggregate_statistics_formal_fragments(rows: list[Any], *, legacy: bool = False) -> tuple[Markup, ...]:
    rendered = _aggregate_statistics_formal_rendered_rows(rows)
    table = _legacy_table if legacy else _table
    return (Markup(table(rendered, table_class="results-table")),)


def _aggregate_statistics_formal_rendered_rows(rows: list[Any]) -> list[dict[str, Any]]:
    rendered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        display = _aggregate_display_row(row)
        rendered.append(
            {
                "Metric": _display_title(str(row.get("metric") or "")),
                "Unit": display["unit"],
                "n": row.get("n", ""),
                "Mean": display["mean"],
                "SD": display["std"],
                "95% CI": display["ci95"],
                "Min": display["min"],
                "Max": display["max"],
            }
        )
    return rendered


def _render_formal_report_table_or_empty(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> str:
    context = _formal_report_table_context(
        rows,
        columns=columns,
        headers=headers,
        table_class=table_class,
        raw_html_columns=raw_html_columns,
    )
    if context is None:
        return render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST)
    return render_formal_report_table(context)


def _formal_report_fragment_stack_context(fragments: tuple[Markup, ...]) -> FormalReportFragmentStackContext:
    return FormalReportFragmentStackContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK,
        fragments=fragments,
    )


def _supporting_detail(
    block_id: str,
    title: str,
    content: str,
    row_count: int,
    *,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    return _details(block_id, title, content, row_count=row_count, block_type="", note_collector=note_collector)


def _remarks_section(section: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_remarks_section(section)
    return render_formal_report_remarks(_formal_report_remarks_context(section))


def _legacy_remarks_section(section: dict[str, Any]) -> str:
    values = []
    for block in section.get("blocks", []) or []:
        if not isinstance(block, dict):
            continue
        data = block.get("data")
        if isinstance(data, str) and data.strip():
            values.append(f"<p>{escape(data.strip())}</p>")
    if values:
        return "".join(values)
    return "<p class=\"empty-note\">No remarks were supplied in the report data.</p>"


def _formal_report_remarks_context(section: dict[str, Any]) -> FormalReportRemarksContext:
    paragraphs = []
    for block in section.get("blocks", []) or []:
        if not isinstance(block, dict):
            continue
        data = block.get("data")
        if isinstance(data, str) and data.strip():
            paragraphs.append(
                Markup(
                    render_report_paragraph_fragment(
                        projection_plane=ProjectionPlane.TEST,
                        body_html=Markup(escape(data.strip())),
                    )
                )
            )
    return FormalReportRemarksContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REMARKS,
        paragraphs=tuple(paragraphs),
        empty_message_html=Markup(
            render_report_paragraph_fragment(
                projection_plane=ProjectionPlane.TEST,
                body_html=Markup(escape("No remarks were supplied in the report data.")),
                paragraph_class="empty-note",
            )
        ),
    )


def _deviations_section(section: dict[str, Any], all_sections: list[dict[str, Any]], section_numbers: dict[str, int]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_deviations_section(section, all_sections, section_numbers)
    return render_formal_report_deviations_section(
        _formal_report_deviations_section_context(section, all_sections, section_numbers)
    )


def _legacy_deviations_section(section: dict[str, Any], all_sections: list[dict[str, Any]], section_numbers: dict[str, int]) -> str:
    missing_rows = _section_block_rows(section, "missing_report_fields")
    deviations_rows = _section_block_rows(section, "deviations_table")
    failure_rows = _section_block_rows(_find_section(all_sections, "failure_analysis"), "invalid_specimen_summary")
    section_number = section_numbers.get(str(section.get("id") or ""), 11)
    return (
        f"<h3>{section_number}.1 Missing data</h3>"
        + _legacy_missing_data_table(missing_rows, all_sections, section_numbers)
        + f"<h3>{section_number}.2 Data deviations / standard-facing deviations</h3>"
        + _legacy_data_use_deviations_table(deviations_rows, failure_rows)
    )


def _formal_report_deviations_section_context(
    section: dict[str, Any],
    all_sections: list[dict[str, Any]],
    section_numbers: dict[str, int],
) -> FormalReportDeviationsSectionContext:
    missing_rows = _section_block_rows(section, "missing_report_fields")
    deviations_rows = _section_block_rows(section, "deviations_table")
    failure_rows = _section_block_rows(_find_section(all_sections, "failure_analysis"), "invalid_specimen_summary")
    section_number = section_numbers.get(str(section.get("id") or ""), 11)
    return FormalReportDeviationsSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION,
        section_number=section_number,
        missing_heading_html=_formal_report_heading_fragment(
            f"{section_number}.1 Missing data",
            heading_level=3,
        ),
        missing_data_html=Markup(_missing_data_table(missing_rows, all_sections, section_numbers)),
        data_deviations_heading_html=_formal_report_heading_fragment(
            f"{section_number}.2 Data deviations / standard-facing deviations",
            heading_level=3,
        ),
        data_deviations_html=Markup(_data_use_deviations_table(deviations_rows, failure_rows)),
    )


def _find_section(sections: list[dict[str, Any]], section_id: str) -> dict[str, Any]:
    for section in sections:
        if str(section.get("id") or "") == section_id:
            return section
    return {}


def _section_block_rows(section: dict[str, Any], block_id: str) -> list[dict[str, Any]]:
    for block in section.get("blocks", []) or []:
        if not isinstance(block, dict):
            continue
        if str(block.get("id") or "") != block_id:
            continue
        data = block.get("data")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


def _missing_data_table(rows: list[dict[str, Any]], sections: list[dict[str, Any]], section_numbers: dict[str, int]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_missing_data_table(rows, sections, section_numbers)
    return render_formal_report_missing_data(
        _formal_report_missing_data_context(rows, sections, section_numbers)
    )


def _legacy_missing_data_table(rows: list[dict[str, Any]], sections: list[dict[str, Any]], section_numbers: dict[str, int]) -> str:
    if not rows:
        return _legacy_formal_report_paragraph("No report metadata gaps were recorded.", paragraph_class="empty-note")
    rendered = _missing_data_rendered_rows(rows, sections, section_numbers)
    return _legacy_table(rendered, table_class="results-table")


def _formal_report_missing_data_context(
    rows: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    section_numbers: dict[str, int],
) -> FormalReportMissingDataContext:
    rendered = _missing_data_rendered_rows(rows, sections, section_numbers)
    empty_message = (
        _formal_report_paragraph("No report metadata gaps were recorded.", paragraph_class="empty-note")
        if not rows
        else "<p class=\"muted\">No rows.</p>"
    )
    return FormalReportMissingDataContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
        table=_formal_report_table_context(rendered, table_class="results-table"),
        empty_message_html=Markup(empty_message),
    )


def _missing_data_rendered_rows(
    rows: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    section_numbers: dict[str, int],
) -> list[dict[str, Any]]:
    section_titles = {
        str(section.get("id") or ""): str(section.get("title") or section.get("id") or "")
        for section in sections
    }
    grouped: dict[str, list[tuple[str, int]]] = {}
    for row in rows:
        section_id = str(row.get("section_id") or "")
        field = str(row.get("label") or row.get("field") or row.get("field_key") or "")
        if not field:
            continue
        display = _display_title(field)
        affected = row.get("affected_run_ids")
        if affected:
            run_text = ", ".join(run_display_label(run_id) for run_id in affected)
            display = f"{display} ({run_text})"
        grouped.setdefault(section_id, []).append((display, _missing_instance_count(row)))
    rendered = []
    for section_id, field_rows in grouped.items():
        title = section_titles.get(section_id) or _heading(section_id)
        number = section_numbers.get(section_id)
        label = f"{number}. {title}" if number else title
        rendered.append(
            {
                "Report section": label,
                "Missing count": sum(count for _display, count in field_rows),
                "Missing fields": "; ".join(display for display, _count in field_rows),
            }
        )
    return rendered


def _missing_instance_count(row: dict[str, Any]) -> int:
    value = row.get("missing_count")
    if value not in (None, ""):
        try:
            count = int(value)
            if count > 0:
                return count
        except (TypeError, ValueError):
            pass
    affected = row.get("affected_run_ids")
    if isinstance(affected, list) and affected:
        return len(affected)
    return 1


def _data_use_deviations_table(deviations_rows: list[dict[str, Any]], failure_rows: list[dict[str, Any]]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_data_use_deviations_table(deviations_rows, failure_rows)
    return render_formal_report_data_use_deviations(
        _formal_report_data_use_deviations_context(deviations_rows, failure_rows)
    )


def _legacy_data_use_deviations_table(deviations_rows: list[dict[str, Any]], failure_rows: list[dict[str, Any]]) -> str:
    if deviations_rows and all("Standard basis" in row for row in deviations_rows):
        columns = ["Category", "Standard basis", "Affected item", "Status/consequence", "Report treatment"]
        rendered = [
            {column: _display_deviation_cell(row.get(column, "")) for column in columns}
            for row in deviations_rows
        ]
        if not rendered:
            return "<p>No data deviations or standard-facing deviations were recorded.</p>"
        return _legacy_table(rendered, columns=columns, table_class="results-table")

    rendered, validation_rows = _data_use_deviations_rendered_rows(deviations_rows, failure_rows)
    if not rendered:
        return "<p>No validation deviations need operator review.</p>"
    prefix = ""
    if not validation_rows:
        prefix = "<p>No validation deviations need operator review.</p>"
    return prefix + _legacy_table(rendered, table_class="results-table")


def _formal_report_data_use_deviations_context(
    deviations_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> FormalReportDataUseDeviationsContext:
    prefix_html = Markup("")
    columns = None
    rendered: list[dict[str, Any]]
    if deviations_rows and all("Standard basis" in row for row in deviations_rows):
        columns = ["Category", "Standard basis", "Affected item", "Status/consequence", "Report treatment"]
        rendered = [
            {column: _display_deviation_cell(row.get(column, "")) for column in columns}
            for row in deviations_rows
        ]
        empty_message = "No data deviations or standard-facing deviations were recorded."
    else:
        rendered, validation_rows = _data_use_deviations_rendered_rows(deviations_rows, failure_rows)
        empty_message = "No validation deviations need operator review."
        if rendered and not validation_rows:
            prefix_html = Markup(
                render_report_paragraph_fragment(
                    projection_plane=ProjectionPlane.TEST,
                    body_html=Markup(escape("No validation deviations need operator review.")),
                    paragraph_class="",
                )
            )
    return FormalReportDataUseDeviationsContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
        prefix_html=prefix_html,
        table=_formal_report_table_context(rendered, columns=columns, table_class="results-table"),
        empty_message_html=Markup(
            render_report_paragraph_fragment(
                projection_plane=ProjectionPlane.TEST,
                body_html=Markup(escape(empty_message)),
                paragraph_class="",
            )
        ),
    )


def _data_use_deviations_rendered_rows(
    deviations_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validation_rows = [
        row
        for row in deviations_rows
        if str(row.get("source") or "") != "report_completeness" and str(row.get("status") or "").casefold() not in {"pass", "passed", "ok"}
    ]
    rendered = []
    excluded = [
        str(row.get("run_id"))
        for row in failure_rows
        if row.get("run_id") and not _truthy(row.get("final_included", row.get("included_in_selection")))
    ]
    review_required = [
        str(row.get("run_id"))
        for row in failure_rows
        if row.get("run_id")
        and _truthy(row.get("final_included", row.get("included_in_selection")))
        and (
            _truthy(row.get("requires_review"))
            or str(row.get("acceptance_state") or "").casefold() in {"review_required", "accepted_with_warning"}
            or str(row.get("bending_pattern") or "").casefold().startswith(("warn", "fail"))
        )
    ]
    if excluded:
        rendered.append(
            {
                "Category": "Excluded run",
                "Affected items": ", ".join(run_display_label(run_id) for run_id in excluded),
                "Report treatment": "Shown in specimen-level results; not used for aggregate values.",
            }
        )
    if review_required:
        rendered.append(
            {
                "Category": "Review-required included runs",
                "Affected items": ", ".join(run_display_label(run_id) for run_id in review_required),
                "Report treatment": "Included in aggregate values; review status remains visible in Section 8.",
            }
        )
    for row in validation_rows:
        rendered.append(
            {
                "Category": _human_value(row.get("severity") or row.get("status") or "Validation warning"),
                "Affected items": _display_deviation_cell(row.get("run_id") or row.get("field") or ""),
                "Report treatment": _display_deviation_cell(row.get("message") or "Validation evidence is retained in the Audit Report."),
            }
        )
    return rendered, validation_rows


def _display_deviation_cell(value: Any) -> str:
    return replace_run_ids_for_display(_human_value(value))


def _geometry_check_label(row: dict[str, Any]) -> str:
    width = _number(row.get("width_mm"))
    thickness = _number(row.get("thickness_mm"))
    area = _number(row.get("area_mm2"))
    missing = []
    if width is None or width <= 0:
        missing.append("width")
    if thickness is None or thickness <= 0:
        missing.append("thickness")
    if area is None or area <= 0:
        missing.append("area")
    if missing:
        return f"Review: missing {', '.join(missing)}"
    expected_area = width * thickness
    tolerance = max(0.05, abs(expected_area) * 0.002)
    if abs(area - expected_area) > tolerance:
        return "Review: area mismatch"
    return "Complete"


def _result_valid(row: dict[str, Any]) -> bool:
    if "valid" in row:
        return _truthy(row.get("valid"))
    validity = str(row.get("validity") or "").casefold()
    if validity in {"invalid", "rejected", "false", "0", "excluded"}:
        return False
    if str(row.get("acceptance_state") or "").casefold() == "excluded":
        return False
    return True


def _yes_no(value: bool) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_yes_no(value)
    return render_formal_report_boolean_badge(_formal_report_boolean_badge_context(value))


def _legacy_yes_no(value: bool) -> str:
    context = _formal_report_boolean_badge_context(value)
    return f"<span class=\"{context.badge_class}\">{context.label_html}</span>"


def _formal_report_boolean_badge_context(value: bool) -> FormalReportBooleanBadgeContext:
    return FormalReportBooleanBadgeContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE,
        badge_class="yes" if value else "no",
        label_html=Markup("Yes" if value else "No"),
    )


def _modulus_gpa(value: Any) -> float | None:
    numeric = _number(value)
    if numeric is None:
        return None
    return numeric / 1000.0


def _format_fixed(value: Any, places: int, *, thousands: bool = False) -> str:
    numeric = _number(value)
    if numeric is None:
        return ""
    pattern = f"{{:,.{places}f}}" if thousands else f"{{:.{places}f}}"
    text = pattern.format(numeric)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _format_fixed_or_missing(value: Any, places: int, *, thousands: bool = False) -> str:
    return _format_fixed(value, places, thousands=thousands) or "missing"


def _format_sig_or_missing(value: Any, sig_figs: int, *, thousands: bool = False) -> str:
    return _format_sig(value, sig_figs, thousands=thousands) or "missing"


def _format_sig(value: Any, sig_figs: int, *, thousands: bool = False) -> str:
    numeric = _number(value)
    if numeric is None:
        return ""
    if numeric == 0:
        return "0"
    magnitude = math.floor(math.log10(abs(numeric)))
    decimal_places = max(sig_figs - magnitude - 1, 0)
    rounded = round(numeric, sig_figs - magnitude - 1)
    pattern = f"{{:,.{decimal_places}f}}" if thousands else f"{{:.{decimal_places}f}}"
    text = pattern.format(rounded)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _failure_mode_display(value: Any) -> str:
    text = str(value or "").strip()
    normalized = text.casefold().replace("-", "_").replace(" ", "_")
    normalized = "_".join(part for part in normalized.split("_") if part)
    mapping = {
        "in_plane_shear": "in-plane shear",
        "inplaneshear": "in-plane shear",
        "complex": "complex",
        "through_thickness_shear": "through-thickness shear",
        "throughthicknessshear": "through-thickness shear",
        "splitting": "splitting",
        "delamination": "delamination",
    }
    return mapping.get(normalized, "missing")


def _dimension_header(label: str, unit: str) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_dimension_header(label, unit)
    return render_formal_report_dimension_header(_formal_report_dimension_header_context(label, unit))


def _legacy_dimension_header(label: str, unit: str) -> str:
    context = _formal_report_dimension_header_context(label, unit)
    return (
        f"<span class=\"dimension-label\">{context.label_html}</span> / "
        f"<span class=\"unit-label\">{context.unit_html}</span>"
    )


def _formal_report_dimension_header_context(label: str, unit: str) -> FormalReportDimensionHeaderContext:
    return FormalReportDimensionHeaderContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER,
        label_html=Markup(escape(label)),
        unit_html=Markup(escape(unit)),
    )


def _vega_plot_block(block: dict[str, Any], data: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_vega_plot_block(block, data)
    return render_formal_report_plot_block(_formal_report_plot_block_context(block, data))


def _legacy_vega_plot_block(block: dict[str, Any], data: dict[str, Any]) -> str:
    context = _formal_report_plot_block_context(block, data)
    return f"""<div class="plot" data-vega-block="{context.block_id_html}">
  <div class="vega-fallback">{context.fallback_html}</div>
  <div id="{context.block_id_html}" class="vega-chart" aria-label="{context.label_html}"></div>
  {context.legend_html}
  <script type="application/json" id="{context.block_id_html}-spec">{context.spec_json}</script>
</div>"""


def _formal_report_plot_block_context(block: dict[str, Any], data: dict[str, Any]) -> FormalReportPlotBlockContext:
    block_id = _html_id(str(block.get("id") or data.get("spec_id") or "vega_plot"))
    vega_lite_spec = data.get("vega_lite_spec") if isinstance(data.get("vega_lite_spec"), dict) else data
    source_spec = data.get("source_spec") if isinstance(data.get("source_spec"), dict) else data
    encoded_spec = json.dumps(vega_lite_spec, ensure_ascii=False).replace("</", "<\\/")
    spec_id = str(data.get("spec_id") or block.get("spec") or "")
    fallback = (
        _failure_bending_svg(source_spec)
        if spec_id == "failure_analysis_bending_distribution"
        else _aggregate_svg(vega_lite_spec, source_spec)
    )
    label = "Bending distribution plot" if spec_id == "failure_analysis_bending_distribution" else "Aggregate plot"
    legend = _plot_legend(spec_id, vega_lite_spec, source_spec)
    return FormalReportPlotBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK,
        block_id_html=Markup(escape(block_id)),
        label_html=Markup(escape(label)),
        fallback_html=Markup(fallback),
        legend_html=Markup(legend),
        spec_json=Markup(encoded_spec),
    )


def _plot_legend(spec_id: str, vega_spec: dict[str, Any] | None = None, source_spec: dict[str, Any] | None = None) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_plot_legend(spec_id, vega_spec, source_spec)
    context = _formal_report_plot_legend_context(spec_id, vega_spec, source_spec)
    return "" if context is None else render_formal_report_plot_legend(context)


def _legacy_plot_legend(spec_id: str, vega_spec: dict[str, Any] | None = None, source_spec: dict[str, Any] | None = None) -> str:
    context = _formal_report_plot_legend_context(spec_id, vega_spec, source_spec)
    if context is None:
        return ""
    return f"""<div class="plot-legend" aria-label="Aggregate stress-strain plot legend">
    <strong>Legend</strong>
    <span class="plot-legend-item"><span class="plot-legend-swatch replicate"></span>individual replicate</span>
    <span class="plot-legend-item"><span class="plot-legend-swatch"></span>mean curve</span>
    <span class="plot-legend-item"><span class="plot-legend-swatch band"></span>{context.sd_label_html}</span>
    <span class="plot-legend-item"><span class="plot-legend-swatch envelope"></span>{context.range_label_html}</span>
    <span class="plot-legend-ci">95% CI = 95% confidence interval for the aggregate metric mean in the table above; it is not the shaded curve band.</span>
  </div>"""


def _formal_report_plot_legend_context(
    spec_id: str,
    vega_spec: dict[str, Any] | None = None,
    source_spec: dict[str, Any] | None = None,
) -> FormalReportPlotLegendContext | None:
    if spec_id != "aggregate_stress_strain_mean_variability":
        return None
    sd_label = "mean +/- 1 SD"
    cv_label = _aggregate_strength_cv_label(vega_spec or {}, source_spec or {})
    if cv_label:
        sd_label = f"{sd_label} ({cv_label})"
    range_label = _aggregate_observed_range_label(vega_spec or {})
    return FormalReportPlotLegendContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND,
        sd_label_html=Markup(sd_label),
        range_label_html=Markup(range_label),
    )


def _aggregate_strength_cv_label(vega_spec: dict[str, Any], source_spec: dict[str, Any]) -> str:
    row = _aggregate_failure_row(vega_spec)
    mean_value = _number(row.get("mean"))
    std_value = _number(row.get("std"))
    if std_value is None:
        lower = _number(row.get("std_lower"))
        upper = _number(row.get("std_upper"))
        if lower is not None and upper is not None:
            std_value = abs(upper - lower) / 2.0
    if mean_value is None or mean_value <= 0 or std_value is None:
        return ""
    cv_percent = abs(std_value / mean_value) * 100.0
    return f"strength CV &asymp; {_format_sig(cv_percent, 2)} % at failure"


def _aggregate_observed_range_label(vega_spec: dict[str, Any]) -> str:
    row = _aggregate_failure_row(vega_spec)
    n_value = _number(row.get("n"))
    if n_value is None:
        return "observed range"
    return f"observed range (n = {int(round(n_value))})"


def _aggregate_failure_row(vega_spec: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in _first_dataset_values(vega_spec)
        if isinstance(row, dict) and _number(row.get("mean")) is not None
    ]
    if not rows:
        return {}
    return max(rows, key=lambda row: _number(row.get("analysis_progress_percent")) or _number(row.get("x")) or 0.0)


def _block_table_content(block_id: str, block_type: str, rows: list[Any]) -> str:
    if block_id == "aggregate_statistics_table":
        return _aggregate_statistics_review(rows)
    if block_id == "feature_lines_table":
        return _feature_lines_review(rows)
    if block_id == "characteristic_points_table":
        return _characteristic_points_review(rows)
    if block_id == "missing_report_fields" or block_type == "missing_fields_table":
        return _missing_fields_review(rows)
    if block_id == "deviations_table":
        return _deviations_review(rows)
    if block_id == "failure_analysis_table":
        return _failure_analysis_review(rows)
    if block_id.endswith("_fields") or block_id.endswith("-fields"):
        return _field_values_review(rows)
    return _table(rows)


def _table(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_table(
            rows,
            columns=columns,
            headers=headers,
            table_class=table_class,
            raw_html_columns=raw_html_columns,
    )
    context = _formal_report_table_context(
        rows,
        columns=columns,
        headers=headers,
        table_class=table_class,
        raw_html_columns=raw_html_columns,
    )
    if context is None:
        return render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST)
    return render_formal_report_table(context)


def _formal_report_evidence_table(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_table(
            rows,
            columns=columns,
            headers=headers,
            table_class=table_class,
            raw_html_columns=raw_html_columns,
        )
    return render_formal_report_evidence_table(
        _formal_report_evidence_table_context(
            rows,
            columns=columns,
            headers=headers,
            table_class=table_class,
            raw_html_columns=raw_html_columns,
        )
    )


def _formal_report_evidence_table_context(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> FormalReportEvidenceTableContext:
    return FormalReportEvidenceTableContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE,
        table=_formal_report_table_context(
            rows,
            columns=columns,
            headers=headers,
            table_class=table_class,
            raw_html_columns=raw_html_columns,
        ),
        empty_table_html=Markup(render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST)),
    )


def _legacy_table(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> str:
    rows = [row for row in rows if isinstance(row, dict)]
    if not rows:
        return "<p class=\"muted\">No rows.</p>"
    raw_html_columns = raw_html_columns or set()
    if columns is None:
        columns = []
        for row in rows[:100]:
            for key in row:
                if str(key) not in columns:
                    columns.append(str(key))
    headers = headers or [escape(_display_title(column)) for column in columns]
    header = "".join(f"<th>{header}</th>" for header in headers)
    body = []
    for row in rows[:200]:
        cells = []
        for column in columns:
            value = _format_cell(row.get(column))
            if column in raw_html_columns:
                cells.append(f"<td>{value}</td>")
            else:
                cells.append(f"<td>{escape(value)}</td>")
        body.append("".join(cells))
    class_attr = f" class=\"{escape(table_class)}\"" if table_class else ""
    return f"<div class=\"table-wrap\"><table{class_attr}><thead><tr>{header}</tr></thead><tbody>{''.join(f'<tr>{line}</tr>' for line in body)}</tbody></table></div>"


def _formal_report_table_context(
    rows: list[Any],
    *,
    columns: list[str] | None = None,
    headers: list[str] | None = None,
    table_class: str = "",
    raw_html_columns: set[str] | None = None,
) -> FormalReportTableContext | None:
    filtered_rows = [row for row in rows if isinstance(row, dict)]
    if not filtered_rows:
        return None
    raw_html_columns = raw_html_columns or set()
    if columns is None:
        columns = []
        for row in filtered_rows[:100]:
            for key in row:
                if str(key) not in columns:
                    columns.append(str(key))
    headers = headers or [escape(_display_title(column)) for column in columns]
    header_contexts = tuple(FormalReportTableCellContext(html=Markup(header)) for header in headers)
    row_contexts: list[FormalReportTableRowContext] = []
    for row in filtered_rows[:200]:
        cells = []
        for column in columns:
            value = _format_cell(row.get(column))
            cell_html = Markup(value) if column in raw_html_columns else Markup(escape(value))
            cells.append(FormalReportTableCellContext(html=cell_html))
        row_contexts.append(FormalReportTableRowContext(cells=tuple(cells)))
    return FormalReportTableContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_TABLE,
        table_class=Markup(escape(table_class)) if table_class else "",
        headers=header_contexts,
        rows=tuple(row_contexts),
    )


def _details(
    block_id: str,
    title: str,
    content: str,
    *,
    row_count: int,
    block_type: str = "",
    note_collector: ReportNoteCollector | None = None,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_details(
            block_id,
            title,
            content,
            row_count=row_count,
            block_type=block_type,
            note_collector=note_collector,
        )
    return render_formal_report_detail_block(
        _formal_report_detail_block_context(
            block_id,
            title,
            content,
            row_count=row_count,
            block_type=block_type,
            note_collector=note_collector,
        )
    )


def _legacy_details(
    block_id: str,
    title: str,
    content: str,
    *,
    row_count: int,
    block_type: str = "",
    note_collector: ReportNoteCollector | None = None,
) -> str:
    purpose = _detail_purpose_inner(block_id, block_type)
    note_markup = ""
    marker = ""
    classes = "detail-block audit-block note-anchor" if note_collector is not None else "detail-block"
    if note_collector is not None and purpose:
        marker = render_note_marker(projection_plane=ProjectionPlane.TEST)
        note_markup = note_collector.add(title=_strip_html(title), paragraphs=[note_html("method", purpose)])
    body_note = "" if note_markup else _legacy_formal_report_paragraph(purpose, paragraph_class="detail-purpose")
    return f"""<details class="{classes}" id="{escape(block_id)}" open>
  <summary>{title}{marker} <span class="muted">({row_count} rows)</span></summary>
  <div class="detail-body">{body_note}{content}{note_markup}</div>
</details>"""


def _formal_report_detail_block_context(
    block_id: str,
    title: str,
    content: str,
    *,
    row_count: int,
    block_type: str = "",
    note_collector: ReportNoteCollector | None = None,
) -> FormalReportDetailBlockContext:
    purpose = _detail_purpose_inner(block_id, block_type)
    note_markup = ""
    marker = ""
    classes = "detail-block audit-block note-anchor" if note_collector is not None else "detail-block"
    if note_collector is not None and purpose:
        marker = render_note_marker(projection_plane=ProjectionPlane.TEST)
        note_markup = note_collector.add(title=_strip_html(title), paragraphs=[note_html("method", purpose)])
    body_note = "" if note_markup else _formal_report_paragraph(purpose, paragraph_class="detail-purpose")
    return FormalReportDetailBlockContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
        classes=classes,
        block_id_html=Markup(escape(block_id)),
        title_html=Markup(title),
        marker_html=Markup(marker),
        row_count=row_count,
        body_note_html=Markup(body_note),
        content_html=Markup(content),
        note_html=Markup(note_markup),
    )


def _detail_purpose_inner(block_id: str, block_type: str) -> str:
    if block_id == "missing_report_fields" or block_type == "missing_fields_table":
        return (
            "<strong>Report-completion detail.</strong> These are report-only gaps, grouped by section so the operator can decide what to amend before final issue. "
            "<a href=\"../workbench/index.html#tab=evidence&context=report&field=missing_report_fields\">Open Workbench report evidence</a>."
        )
    if block_id == "deviations_table":
        return "<strong>Report review detail.</strong> These rows explain recorded deviations from the standard. Use the Workbench when an individual check needs operation-level evidence."
    if block_id == "failure_analysis_table":
        return "<strong>Result-quality detail.</strong> This section summarizes per-run failure, validity, and bending evidence. Raw analysis columns remain secondary."
    if block_id.endswith("_fields") or block_id.endswith("-fields"):
        return "<strong>Report field detail.</strong> Values shown here are the report-facing values and their completion state. Raw role keys are retained only in the MTDA evidence files."
    return "<strong>Supporting detail.</strong> This section provides the evidence behind the summary above."


def _strip_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", value)).strip()


def _field_values_review(rows: list[Any]) -> str:
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "Field": row.get("label") or row.get("field") or row.get("key") or "",
                "Value": row.get("value") if row.get("value") not in (None, "") else "Not recorded in source package",
                "Unit": row.get("unit") or row.get("standard_unit") or "",
                "_state": _field_value_state(row),
            }
        )
    return _field_value_table(normalized)


def _field_value_table(rows: list[dict[str, Any]]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_field_value_table(rows)
    context = _formal_report_field_value_table_context(rows)
    if context is None:
        return render_report_empty_paragraph(projection_plane=ProjectionPlane.TEST)
    return render_formal_report_field_value_table(context)


def _legacy_field_value_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class=\"muted\">No rows.</p>"
    body_rows = []
    for row in rows:
        state = str(row.get("_state") or "present")
        row_class = f"report-row--{escape(state)}"
        dot_class = "state-dot--missing" if state == "missing" else "state-dot--present"
        state_label = "Missing report value" if state == "missing" else "Report value present"
        value = escape(_format_cell(row.get("Value")))
        value_html = f"<span class=\"state-dot {dot_class}\" title=\"{escape(state_label)}\" aria-label=\"{escape(state_label)}\"></span>{value}"
        body_rows.append(
            "<tr class=\"{row_class}\">"
            "<td>{field}</td><td>{value}</td><td>{unit}</td>"
            "</tr>".format(
                row_class=row_class,
                field=escape(_format_cell(row.get("Field"))),
                value=value_html,
                unit=escape(_format_cell(row.get("Unit"))),
            )
        )
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        "<th>Field</th><th>Value</th><th>Unit</th>"
        f"</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _formal_report_field_value_table_context(
    rows: list[dict[str, Any]],
) -> FormalReportFieldValueTableContext | None:
    if not rows:
        return None
    row_contexts: list[FormalReportFieldValueRowContext] = []
    for row in rows:
        state = str(row.get("_state") or "present")
        row_class = f"report-row--{escape(state)}"
        dot_class = "state-dot--missing" if state == "missing" else "state-dot--present"
        state_label = "Missing report value" if state == "missing" else "Report value present"
        value = escape(_format_cell(row.get("Value")))
        value_html = f"<span class=\"state-dot {dot_class}\" title=\"{escape(state_label)}\" aria-label=\"{escape(state_label)}\"></span>{value}"
        row_contexts.append(
            FormalReportFieldValueRowContext(
                row_class=str(row_class),
                field_html=Markup(escape(_format_cell(row.get("Field")))),
                value_html=Markup(value_html),
                unit_html=Markup(escape(_format_cell(row.get("Unit")))),
            )
        )
    return FormalReportFieldValueTableContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE,
        rows=tuple(row_contexts),
    )


def _field_value_state(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "").casefold()
    source = str(row.get("source_type") or "").casefold()
    value = row.get("value")
    if status == "missing" or source == "missing" or value in (None, ""):
        return "missing"
    return "present"


def _missing_fields_review(rows: list[Any]) -> str:
    raw_rows = [row for row in rows if isinstance(row, dict)]
    if not raw_rows:
        return _formal_report_paragraph("No missing report fields.")

    grouped: dict[str, dict[str, list[str]]] = {}
    for row in raw_rows:
        section = str(row.get("section_title") or _heading(str(row.get("section_id") or "Unsectioned")) or "Unsectioned")
        importance = str(row.get("report_importance") or row.get("requirement_level") or "optional").casefold()
        field = str(row.get("label") or row.get("field") or row.get("field_key") or "")
        bucket = grouped.setdefault(section, {"required": [], "recommended": [], "optional": []})
        if importance not in bucket:
            importance = "optional"
        if field:
            bucket[importance].append(field)

    required_count = sum(len(group["required"]) for group in grouped.values())
    recommended_count = sum(len(group["recommended"]) for group in grouped.values())
    optional_count = sum(len(group["optional"]) for group in grouped.values())
    action = (
        "Required fields must be amended, marked not applicable, or otherwise resolved before final issue."
        if required_count
        else "Required report content is complete; recommended gaps can be completed if available or carried as final-report warnings."
    )
    review_rows = []
    for section, group in grouped.items():
        review_rows.append(
            {
                "Section": section,
                "Required missing": _field_list(group["required"]),
                "Recommended missing": _field_list(group["recommended"]),
                "Optional missing": _field_list(group["optional"]),
            }
        )
    return _formal_report_review_section(
        f"{required_count} required, {recommended_count} recommended, and {optional_count} optional report fields are currently not recorded. "
        f"{escape(action)}",
        review_rows,
        raw_evidence_title="Raw field-resolution evidence",
        raw_rows=raw_rows,
    )


def _aggregate_statistics_review(rows: list[Any]) -> str:
    raw_rows = [row for row in rows if isinstance(row, dict)]
    review_rows = []
    for row in raw_rows:
        metric = str(row.get("metric") or "")
        display = _aggregate_display_row(row)
        review_rows.append(
            {
                "Metric": _display_title(metric),
                "n": row.get("n", ""),
                "Unit": display["unit"],
                "Mean": display["mean"],
                "Std dev": display["std"],
                "Std error": _format_scaled_sig(row.get("std_err"), 100.0 if display["unit"] == "%" and "strain" in metric.casefold() else 1.0, 2 if "strain" in metric.casefold() else 3),
                "95% CI": display["ci95"],
                "Range": f"{display['min']} to {display['max']}" if display["min"] and display["max"] else "",
            }
        )
    return _formal_report_review_section(
        "Aggregate statistics use the final report runs. "
        "Mean describes the selected-run average; standard deviation and standard error show dataset variability and uncertainty of the mean.",
        review_rows,
        raw_evidence_title="Raw aggregate-statistics evidence",
        raw_rows=raw_rows,
    )


def _feature_lines_review(rows: list[Any]) -> str:
    raw_rows = [row for row in rows if isinstance(row, dict)]
    review_rows = []
    for row in raw_rows:
        axis = str(row.get("axis") or "")
        review_rows.append(
            {
                "Feature": _feature_line_label(row),
                "Role in report": _feature_line_role(axis),
                "Metric": _display_title(str(row.get("metric") or "")),
                "Value": _format_stat(row.get("value"), str(row.get("unit") or "")),
                "n": row.get("n", ""),
            }
        )
    return _formal_report_evidence_table(review_rows)


def _characteristic_points_review(rows: list[Any]) -> str:
    raw_rows = [row for row in rows if isinstance(row, dict)]
    review_rows = []
    for row in raw_rows:
        review_rows.append(
            {
                "Point": _display_title(str(row.get("point_id") or "")),
                "Scope": _human_value(row.get("scope") or ""),
                "Run": row.get("run_id") or "Aggregate",
                "X coordinate": _format_stat(row.get("x_value"), str(row.get("x_unit") or "")),
                "Y coordinate": _format_stat(row.get("y_value"), str(row.get("y_unit") or "")),
            }
        )
    return _formal_report_evidence_table(review_rows)


def _deviations_review(rows: list[Any]) -> str:
    raw_rows = [row for row in rows if isinstance(row, dict)]
    report_field_rows = [row for row in raw_rows if _is_report_field_warning(row)]
    validation_rows = [row for row in raw_rows if row not in report_field_rows]
    status_counts = _status_counts(validation_rows)
    review_rows = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in validation_rows:
        status = str(_first_present(row, ("status", "outcome", "severity")) or "").casefold()
        if status in {"pass", "passed", "ok", "success"}:
            continue
        rendered = {
            "Run or scope": _first_present(row, ("run_id", "scope", "specimen_name", "sample_id")),
            "Check": _first_present(row, ("check_label", "check", "check_id", "field", "metric")),
            "Status": _first_present(row, ("status", "outcome", "severity")),
            "Observed": _first_present(row, ("observed", "value", "actual", "measured_value")),
            "Reference": _first_present(row, ("reference", "expected", "limit", "reference_value")),
            "Meaning": _first_present(row, ("message", "reason", "description", "deviation")),
        }
        key = tuple(str(rendered.get(column, "")) for column in ("Run or scope", "Check", "Status", "Meaning"))
        if key in seen:
            continue
        seen.add(key)
        review_rows.append(rendered)
    summary_body = (
        f"Validation checks: {status_counts.get('pass', 0)} passed, "
        f"{status_counts.get('warn', 0)} warnings, {status_counts.get('fail', 0)} failures. "
    )
    if report_field_rows:
        summary_body += (
            f"{len(report_field_rows)} report-completion warning rows are summarized in "
            "<a href=\"#missing_report_fields\">Missing report fields</a> and are not duplicated here."
        )
    if not review_rows:
        return _formal_report_review_section(
            summary_body,
            review_rows,
            raw_evidence_title="Raw deviation evidence",
            raw_rows=raw_rows,
            empty_message="No validation deviations need operator review.",
        )
    return _formal_report_review_section(
        summary_body,
        review_rows,
        raw_evidence_title="Raw deviation evidence",
        raw_rows=raw_rows,
    )


def _is_report_field_warning(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(value)
        for value in (
            row.get("message"),
            row.get("reason"),
            row.get("description"),
            row.get("deviation"),
            row.get("field"),
            row.get("check"),
            row.get("check_id"),
        )
        if value not in (None, "")
    ).casefold()
    return "report field" in text or "not found in overrides" in text


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "other": 0}
    for row in rows:
        status = str(_first_present(row, ("status", "outcome", "severity")) or "").casefold()
        if status in {"pass", "passed", "ok", "success"}:
            counts["pass"] += 1
        elif status in {"warn", "warning", "review", "review_required"}:
            counts["warn"] += 1
        elif status in {"fail", "failed", "error", "blocked"}:
            counts["fail"] += 1
        else:
            counts["other"] += 1
    return counts


def _failure_analysis_review(rows: list[Any]) -> str:
    review_rows = []
    raw_rows = [row for row in rows if isinstance(row, dict)]
    for row in raw_rows:
        review_rows.append(
            {
                "Run": _first_present(row, ("run_id", "specimen_name", "sample_id")),
                "Report use": _report_use(row),
                "Test validity": _test_validity(row),
                "Bending evidence": _bending_review_label(row),
                "Extent above threshold": _bending_extent(row),
                "Curve-family check": _curve_family_summary(row),
                "Operator interpretation": _bending_interpretation(row),
            }
        )
    return _formal_report_review_section(
        "Bending evidence is graded by extent. Localized excursions and sustained exceedance are both visible here; the Workbench keeps the point-level trace.",
        review_rows,
        raw_evidence_title="Raw failure-analysis evidence",
        raw_rows=raw_rows,
    )


def _formal_report_review_section(
    intro_body_html: str,
    table_rows: list[dict[str, Any]],
    *,
    raw_evidence_title: str,
    raw_rows: list[dict[str, Any]],
    paragraph_class: str = "muted",
    empty_message: str = "",
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        empty_html = _legacy_formal_report_paragraph(empty_message) if empty_message else ""
        return (
            _legacy_formal_report_paragraph(intro_body_html, paragraph_class=paragraph_class)
            + (_legacy_table(table_rows) if table_rows else empty_html)
            + _legacy_raw_evidence_details(raw_evidence_title, raw_rows)
        )
    return render_formal_report_review_section(
        _formal_report_review_section_context(
            intro_body_html,
            table_rows,
            raw_evidence_title=raw_evidence_title,
            raw_rows=raw_rows,
            paragraph_class=paragraph_class,
            empty_message=empty_message,
        )
    )


def _formal_report_review_section_context(
    intro_body_html: str,
    table_rows: list[dict[str, Any]],
    *,
    raw_evidence_title: str,
    raw_rows: list[dict[str, Any]],
    paragraph_class: str = "muted",
    empty_message: str = "",
) -> FormalReportReviewSectionContext:
    table_context = _formal_report_table_context(table_rows)
    empty_message_html = (
        Markup(render_formal_report_paragraph(_formal_report_paragraph_context(empty_message)))
        if empty_message
        else Markup("")
    )
    return FormalReportReviewSectionContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION,
        paragraph_class=paragraph_class,
        intro_html=Markup(intro_body_html),
        intro_paragraph_html=_formal_report_paragraph_fragment(intro_body_html, paragraph_class=paragraph_class),
        table=table_context,
        empty_message_html=empty_message_html,
        raw_evidence_note=_formal_report_raw_evidence_note_context(raw_evidence_title, raw_rows),
    )


def _formal_report_paragraph(body_html: str, *, paragraph_class: str = "") -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_formal_report_paragraph(body_html, paragraph_class=paragraph_class)
    return render_formal_report_paragraph(_formal_report_paragraph_context(body_html, paragraph_class=paragraph_class))


def _legacy_formal_report_paragraph(body_html: str, *, paragraph_class: str = "") -> str:
    class_attr = f' class="{escape(paragraph_class)}"' if paragraph_class else ""
    return f"<p{class_attr}>{body_html}</p>"


def _formal_report_paragraph_fragment(body_html: str, *, paragraph_class: str = "") -> Markup:
    return Markup(render_formal_report_paragraph(_formal_report_paragraph_context(body_html, paragraph_class=paragraph_class)))


def _formal_report_heading_fragment(title: str, *, heading_level: int) -> Markup:
    return Markup(
        render_report_heading_fragment(
            projection_plane=ProjectionPlane.TEST,
            title_html=Markup(escape(title)),
            heading_level=heading_level,
        )
    )


def _formal_report_paragraph_context(body_html: str, *, paragraph_class: str = "") -> FormalReportParagraphContext:
    return FormalReportParagraphContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
        paragraph_class=paragraph_class,
        body_html=Markup(body_html),
    )


def _raw_evidence_details(title: str, rows: list[dict[str, Any]]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_raw_evidence_details(title, rows)
    return render_formal_report_raw_evidence_note(_formal_report_raw_evidence_note_context(title, rows))


def _legacy_raw_evidence_details(title: str, rows: list[dict[str, Any]]) -> str:
    return (
        f"<p class=\"muted\">{escape(title)} is preserved in the MTDA report CSV/JSON artifacts "
        f"({len(rows)} rows) and in the Workbench evidence view; it is not duplicated here as a raw debug table.</p>"
    )


def _formal_report_raw_evidence_note_context(title: str, rows: list[dict[str, Any]]) -> FormalReportRawEvidenceNoteContext:
    return FormalReportRawEvidenceNoteContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
        title_html=Markup(escape(title)),
        row_count=len(rows),
    )


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return ""


def _field_list(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


def _format_stat(value: Any, unit: str = "", *, include_unit: bool = True) -> str:
    numeric = _number(value)
    if numeric is None:
        return ""
    formatted = f"{numeric:.4g}"
    return f"{formatted} {unit}".strip() if include_unit else formatted


def _aggregate_display_row(row: dict[str, Any]) -> dict[str, str]:
    metric = str(row.get("metric") or "").casefold()
    unit = str(row.get("unit") or "")
    scale = 1.0
    sig_figs = 3
    if "strain" in metric:
        sig_figs = 2
        if unit.casefold() in {"strain", "mm/mm", "dimensionless", ""}:
            scale = 100.0
            unit = "%"
    elif "poisson" in metric:
        sig_figs = 2
    elif "strength" in metric or "modulus" in metric:
        sig_figs = 3
    return {
        "unit": unit,
        "mean": _format_scaled_sig(row.get("mean"), scale, sig_figs),
        "std": _format_scaled_sig(row.get("std"), scale, sig_figs),
        "ci95": _scaled_confidence_interval(row, scale, sig_figs),
        "min": _format_scaled_sig(row.get("min"), scale, sig_figs),
        "max": _format_scaled_sig(row.get("max"), scale, sig_figs),
    }


def _format_scaled_sig(value: Any, scale: float, sig_figs: int) -> str:
    numeric = _number(value)
    if numeric is None:
        return ""
    return _format_sig(numeric * scale, sig_figs, thousands=abs(numeric * scale) >= 1000)


def _scaled_confidence_interval(row: dict[str, Any], scale: float, sig_figs: int) -> str:
    low = _number(row.get("ci95_low"))
    high = _number(row.get("ci95_high"))
    if low is None or high is None:
        return ""
    return f"{_format_scaled_sig(low, scale, sig_figs)} to {_format_scaled_sig(high, scale, sig_figs)}"


def _confidence_interval(row: dict[str, Any], *, include_unit: bool = True) -> str:
    unit = str(row.get("unit") or "")
    low = _number(row.get("ci95_low"))
    high = _number(row.get("ci95_high"))
    if low is None or high is None:
        return ""
    value = f"{low:.4g} to {high:.4g}"
    return f"{value} {unit}".strip() if include_unit else value


def _range_text(row: dict[str, Any], unit: str = "", *, include_unit: bool = True) -> str:
    low = _number(row.get("min"))
    high = _number(row.get("max"))
    if low is None or high is None:
        return ""
    value = f"{low:.4g} to {high:.4g}"
    return f"{value} {unit}".strip() if include_unit else value


def _report_use(row: dict[str, Any]) -> str:
    return "Included in final report runs" if _truthy(row.get("final_included", row.get("included_in_selection"))) else "Excluded from final report runs"


def _test_validity(row: dict[str, Any]) -> str:
    validity = _first_present(row, ("validity", "failure_mode_observed"))
    failure_mode = str(row.get("failure_mode") or "").strip()
    if str(validity).casefold() in {"accepted", "valid", "true", "1"}:
        base = "Accepted test result"
    elif validity:
        base = _human_value(validity)
    else:
        base = "Validity not recorded"
    if failure_mode in {"0", "1"}:
        return base
    return f"{base}; {failure_mode}" if failure_mode else base


def _bending_review_label(row: dict[str, Any]) -> str:
    pattern = str(_first_present(row, ("bending_pattern", "bending_classification")) or "")
    fraction = _number(row.get("bending_fraction_above_threshold")) or 0.0
    p95 = _number(row.get("bending_p95_percent")) or 0.0
    if pattern == "PASS":
        return "Within bending threshold"
    if pattern == "PASS_WITH_SPIKES":
        return "Isolated bending spikes"
    if pattern == "WARN_TRANSIENT_BENDING":
        return "Transient bending exceedance"
    if pattern == "FAIL_SUSTAINED_BENDING":
        if fraction >= 0.6 or p95 >= 60.0:
            return "High sustained bending evidence"
        if fraction >= 0.2:
            return "Sustained bending evidence"
        return "Localized sustained-region evidence"
    return _human_value(pattern or "Bending evidence not classified")


def _bending_extent(row: dict[str, Any]) -> str:
    threshold = _number(row.get("bending_threshold_percent"))
    points = _number(row.get("bending_points_above_threshold"))
    total = _number(row.get("bending_point_count"))
    fraction = _number(row.get("bending_fraction_above_threshold"))
    longest = _number(row.get("bending_longest_segment_points"))
    p95 = _number(row.get("bending_p95_percent"))
    parts = []
    if points is not None:
        if total:
            parts.append(f"{int(points)} of {int(total)} points above threshold")
        else:
            parts.append(f"{int(points)} points above threshold")
    if fraction is not None:
        parts.append(f"{fraction * 100.0:.1f}% of assessment window")
    if longest is not None and longest > 0:
        parts.append(f"longest run {int(longest)} points")
    if p95 is not None:
        parts.append(f"p95 {p95:.1f}%")
    if threshold is not None:
        parts.append(f"threshold {threshold:.1f}%")
    return "; ".join(parts) if parts else "Extent not recorded"


def _curve_family_summary(row: dict[str, Any]) -> str:
    classification = _first_present(row, ("curve_family_classification", "curve_family_status"))
    rmse = _number(row.get("curve_family_normalized_rmse"))
    if not classification and rmse is None:
        return "Not assessed"
    suffix = f"; NRMSE {rmse:.3g}" if rmse is not None else ""
    return f"{_human_value(classification)}{suffix}"


def _bending_interpretation(row: dict[str, Any]) -> str:
    pattern = str(row.get("bending_pattern") or "")
    fraction = _number(row.get("bending_fraction_above_threshold")) or 0.0
    if pattern == "PASS":
        return "No bending review needed from this evidence."
    if pattern == "PASS_WITH_SPIKES":
        return "Short spikes are recorded but not treated as sustained bending."
    if pattern == "WARN_TRANSIENT_BENDING" or 0.0 < fraction < 0.2:
        return "Review the trace if this run drives a decision; evidence looks localized rather than persistent."
    if fraction >= 0.6:
        return "Large part of the assessment window is above threshold; review before accepting as representative."
    return "Review required; extent metrics distinguish localized excursions from broader sustained exceedance."


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "included"}


def _feature_line_label(row: dict[str, Any]) -> str:
    line_id = str(row.get("line_id") or "")
    if line_id == "mean_compressive_strength":
        return "Mean compressive strength line"
    if line_id == "mean_failure_strain":
        return "Mean failure-strain line"
    if line_id == "mean_compressive_modulus":
        return "Mean compressive modulus slope"
    return _display_title(line_id)


def _feature_line_role(axis: str) -> str:
    if axis == "x":
        return "Vertical reference marker on the aggregate plot"
    if axis == "y":
        return "Horizontal reference marker on the aggregate plot"
    if axis == "slope":
        return "Slope reference used to explain aggregate modulus"
    return "Aggregate plot reference evidence"


def _should_collapse_block(block: dict[str, Any], data: list[Any]) -> bool:
    block_id = str(block.get("id") or "").casefold()
    block_type = str(block.get("type") or "").casefold()
    if block_id.endswith("_fields") or block_id.endswith("-fields"):
        return True
    if block_id in {"missing_report_fields", "deviations_table"} or block_type == "missing_fields_table":
        return True
    if block_id in {"failure_analysis_table", "acceptance_summary", "curve_family_summary"}:
        return True
    if data and isinstance(data[0], dict) and len(data[0]) > 9:
        return True
    if len(data) > 24 and any(token in block_id for token in ("deviation", "missing", "values_used", "field_catalog")):
        return True
    return False


def _aggregate_svg(vega_spec: dict[str, Any], source_spec: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_aggregate_svg(vega_spec, source_spec)
    return render_formal_report_aggregate_svg(_formal_report_aggregate_svg_context(vega_spec, source_spec))


def _legacy_aggregate_svg(vega_spec: dict[str, Any], source_spec: dict[str, Any]) -> str:
    context = _formal_report_aggregate_svg_context(vega_spec, source_spec)
    return f"""<svg viewBox="0 0 700 320" width="100%" height="320" role="img" aria-label="Aggregate plot">
  <rect x="0" y="0" width="700" height="320" fill="#ffffff"/>
  <line x1="52" y1="270" x2="670" y2="270" stroke="#5b6775" stroke-width="1"/>
  <line x1="52" y1="270" x2="52" y2="38" stroke="#5b6775" stroke-width="1"/>
  <polyline fill="none" stroke="#b7d4e8" stroke-width="8" stroke-opacity="0.6" points="{context.min_path}"/>
  <polyline fill="none" stroke="#b7d4e8" stroke-width="8" stroke-opacity="0.6" points="{context.max_path}"/>
  <polyline fill="none" stroke="#2477b3" stroke-width="3" points="{context.mean_path}"/>
  <circle cx="640" cy="70" r="5" fill="#2477b3"/>
  <text x="360" y="302" text-anchor="middle" font-size="12">Normalised strain / %</text>
  <text x="18" y="158" transform="rotate(-90 18 158)" text-anchor="middle" font-size="12">Stress / MPa</text>
  <text x="560" y="24" font-size="12" fill="#5b6876">{context.n_label_html}</text>
</svg>"""


def _formal_report_aggregate_svg_context(
    vega_spec: dict[str, Any],
    source_spec: dict[str, Any],
) -> FormalReportAggregateSvgContext:
    # The full Vega JSON is archived separately; this compact inline view gives
    # operators a deterministic preview even when the browser is offline.
    values = _first_dataset_values(vega_spec)
    path = _polyline(values, "analysis_progress_percent", "mean")
    min_path = _polyline(values, "analysis_progress_percent", "min")
    max_path = _polyline(values, "analysis_progress_percent", "max")
    n_values = [row.get("n") for row in values if isinstance(row, dict) and row.get("n") not in (None, "")]
    n_label = f"observations: {escape(str(n_values[-1]))}" if n_values else "observations recorded"
    return FormalReportAggregateSvgContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
        min_path=min_path,
        max_path=max_path,
        mean_path=path,
        n_label_html=Markup(n_label),
    )


def _failure_bending_svg(source_spec: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_failure_bending_svg(source_spec)
    context = _formal_report_failure_bending_svg_context(source_spec)
    if isinstance(context, FormalReportPlotNoteContext):
        return render_formal_report_plot_note(context)
    return render_formal_report_failure_bending_svg(context)


def _legacy_failure_bending_svg(source_spec: dict[str, Any]) -> str:
    context = _formal_report_failure_bending_svg_context(source_spec)
    if isinstance(context, FormalReportPlotNoteContext):
        return f"<p class=\"plot-note\">{context.message_html}</p>"
    return f"""<svg viewBox="0 0 {context.width} {context.height}" width="100%" height="{context.height}" role="img" aria-label="Bending distribution preview">
  <rect x="0" y="0" width="{context.width}" height="{context.height}" fill="#ffffff"/>
  <rect x="{context.left}" y="{context.top}" width="{context.plot_width}" height="{context.threshold_fill_height}" fill="#f7dfdd" opacity="0.36"/>
  <line x1="{context.left}" y1="{context.bottom}" x2="{context.right}" y2="{context.bottom}" stroke="#5b6775" stroke-width="1"/>
  <line x1="{context.left}" y1="{context.bottom}" x2="{context.left}" y2="{context.top}" stroke="#5b6775" stroke-width="1"/>
  <line x1="{context.left}" y1="{context.threshold_y}" x2="{context.right}" y2="{context.threshold_y}" stroke="#d9786d" stroke-width="2" stroke-dasharray="6 4"/>
  <text x="{context.threshold_label_x}" y="{context.threshold_label_y}" font-size="12" fill="#b85f56">10% threshold</text>
  {context.boxes_html}
  {context.labels_html}
  <text x="350" y="274" text-anchor="middle" font-size="12">Run</text>
  <text x="18" y="138" transform="rotate(-90 18 138)" text-anchor="middle" font-size="12">Bending / %</text>
</svg>"""


def _formal_report_failure_bending_svg_context(
    source_spec: dict[str, Any],
) -> FormalReportFailureBendingSvgContext | FormalReportPlotNoteContext:
    message = str(source_spec.get("unavailable_message") or "")
    if message:
        return _formal_report_plot_note_context(message)
    summary = source_spec.get("summary") if isinstance(source_spec.get("summary"), list) else []
    rows = [row for row in summary if isinstance(row, dict)]
    if not rows:
        return _formal_report_plot_note_context(
            "Bending distribution plot unavailable: pointwise bending values are not present in the report payload."
        )
    width = 700
    height = 280
    left = 52
    top = 26
    bottom = 230
    plot_width = 600
    max_value = max(
        [
            _number(row.get("max_bending_percent")) or 0.0
            for row in rows
        ]
        + [10.0]
    )
    max_value = max(max_value * 1.15, 12.0)
    step = plot_width / max(len(rows), 1)
    boxes = []
    labels = []
    for index, row in enumerate(rows):
        x = left + step * (index + 0.5)
        color = _bending_pattern_svg_color(row.get("bending_pattern"))
        median = _number(row.get("median_bending_percent")) or 0.0
        minimum = _number(row.get("min_bending_percent")) or 0.0
        q1 = _number(row.get("q1_bending_percent"))
        q1 = median if q1 is None else q1
        q3 = _number(row.get("q3_bending_percent"))
        q3 = median if q3 is None else q3
        maximum = _number(row.get("max_bending_percent")) or median
        y_min = bottom - (minimum / max_value) * (bottom - top)
        y_q1 = bottom - (q1 / max_value) * (bottom - top)
        y_q3 = bottom - (q3 / max_value) * (bottom - top)
        y_median = bottom - (median / max_value) * (bottom - top)
        y_max = bottom - (maximum / max_value) * (bottom - top)
        boxes.append(
            f"<line x1=\"{x:.1f}\" y1=\"{y_max:.1f}\" x2=\"{x:.1f}\" y2=\"{y_min:.1f}\" stroke=\"#5b6775\" stroke-width=\"1.4\" opacity=\"0.75\"/>"
            f"<rect x=\"{x - 10:.1f}\" y=\"{y_q3:.1f}\" width=\"20\" height=\"{max(2, y_q1 - y_q3):.1f}\" fill=\"{color}\" opacity=\"0.72\" stroke=\"#5b6775\"/>"
            f"<line x1=\"{x - 15:.1f}\" y1=\"{y_median:.1f}\" x2=\"{x + 15:.1f}\" y2=\"{y_median:.1f}\" stroke=\"#1f2933\" stroke-width=\"2\"/>"
        )
        labels.append(f"<text x=\"{x:.1f}\" y=\"252\" text-anchor=\"middle\" font-size=\"11\">{escape(str(row.get('run_label') or ''))}</text>")
    threshold_y = bottom - (10.0 / max_value) * (bottom - top)
    return FormalReportFailureBendingSvgContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG,
        width=width,
        height=height,
        left=left,
        top=top,
        bottom=bottom,
        plot_width=plot_width,
        right=left + plot_width,
        threshold_fill_height=f"{threshold_y - top:.1f}",
        threshold_y=f"{threshold_y:.1f}",
        threshold_label_x=left + plot_width - 100,
        threshold_label_y=f"{threshold_y - 6:.1f}",
        boxes_html=Markup("".join(boxes)),
        labels_html=Markup("".join(labels)),
    )


def _formal_report_plot_note_context(message: str) -> FormalReportPlotNoteContext:
    return FormalReportPlotNoteContext(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
        message_html=Markup(escape(message)),
    )


def _bending_pattern_svg_color(pattern: Any) -> str:
    value = str(pattern or "").upper()
    if value.startswith("FAIL"):
        return "#d9786d"
    if value.startswith("WARN"):
        return "#e6b45a"
    return "#74b88b"


def _first_dataset_values(spec: dict[str, Any]) -> list[dict[str, Any]]:
    data = spec.get("data")
    if isinstance(data, dict) and isinstance(data.get("values"), list):
        return [row for row in data["values"] if isinstance(row, dict)]
    datasets = spec.get("datasets")
    if isinstance(datasets, dict):
        for rows in datasets.values():
            if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "mean" in rows[0]:
                return rows
    return []


def _polyline(rows: list[dict[str, Any]], x_key: str, y_key: str) -> str:
    if not rows:
        return "52,270 210,200 380,120 540,74 660,68"
    x_values = [_number(row.get(x_key)) for row in rows]
    y_values = [_number(row.get(y_key)) for row in rows]
    points = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
    if not points:
        return "52,270 210,200 380,120 540,74 660,68"
    xs, ys = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    sampled = points[:: max(1, len(points) // 160)]
    return " ".join(
        f"{52 + ((x - min_x) / span_x) * 608:.1f},{270 - ((y - min_y) / span_y) * 218:.1f}"
        for x, y in sampled
    )


def _number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _html_id(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-").lower()
    return f"vega-{value or 'plot'}"


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return ""
    if isinstance(value, str):
        return _human_value(value)
    return str(value)


def _display_title(value: str) -> str:
    text = str(value or "")
    replacements = {
        "test_identification_fields": "Test identification fields",
        "material_fields": "Material fields",
        "preparation_fields": "Specimen preparation fields",
        "fixture_fields": "Fixture fields",
        "test_conditions_fields": "Test condition fields",
        "measurement_fields": "Measurement method fields",
        "specimen_geometry_table": "Specimen geometry",
        "individual_results_table": "Individual test results",
        "aggregate_statistics_table": "Aggregate statistics",
        "characteristic_points_table": "Characteristic points",
        "feature_lines_table": "Feature lines",
        "failure_analysis_table": "Failure analysis",
        "deviations_table": "Deviations from standard",
        "missing_report_fields": "Missing report fields",
        "remarks_text": "Remarks",
        "max_load_N": "Maximum load",
        "compressive_strength_MPa": "Compressive strength",
        "compressive_modulus_MPa": "Compressive modulus",
        "compressive_failure_strain": "Compressive failure strain",
        "max_bending_percent": "Maximum bending",
        "mean_bending_percent": "Mean bending",
        "p95_bending_percent": "95th percentile bending",
        "p99_bending_percent": "99th percentile bending",
    }
    if text in replacements:
        return replacements[text]
    return text.replace("_", " ").strip().title() if "_" in text else text


def _heading(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _human_value(value: Any) -> str:
    text = str(value)
    if not text.startswith("#"):
        replaced = replace_run_ids_for_display(text)
        if replaced != text:
            text = replaced
    replacements = {
        "COMPLETE_WITH_WARNINGS": "Complete with warnings",
        "COMPLETE": "Complete",
        "INCOMPLETE": "Incomplete",
        "RC_WITH_WARNINGS": "RC with warnings",
        "RC_READY": "RC ready",
        "RC_BLOCKED": "RC blocked",
        "machine_default_confirmed": "Machine-selected report runs",
        "machine_acceptance": "Machine-selected report runs",
        "human_final": "Human-confirmed final report runs",
        "external_or_not_recorded": "Not exported from this MTDA yet",
        "not_finalized": "Draft, not finalized",
        "finalized": "Finalized",
        "final_report_runs": "Final report runs",
        "complete_with_warnings": "Complete with warnings",
        "complete": "Complete",
        "incomplete": "Incomplete",
    }
    return replacements.get(text, text.replace("_", " ") if "_" in text and len(text) < 40 else text)


def _completion_action(required_missing: Any, recommended_missing: Any) -> str:
    required = _int_value(required_missing)
    recommended = _int_value(recommended_missing)
    if required:
        return "Required report fields are missing. Review Missing Field Detail, then record report-only amendments or mark fields not applicable before final issue."
    if recommended:
        return "Recommended report fields are missing. Add report-only amendments when information is available, or finalize the MTDA with warnings."
    return "No report fields require completion before finalization."


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _quality_from_completion(status: str) -> str:
    if status == "COMPLETE":
        return "RC_READY"
    if status == "COMPLETE_WITH_WARNINGS":
        return "RC_WITH_WARNINGS"
    if status:
        return "RC_BLOCKED"
    return "UNKNOWN"


def _status_class(status: Any) -> str:
    value = str(status or "").upper()
    if value in {"COMPLETE", "READY", "RC_READY", "PASS", "PASSED"}:
        return "badge--ok"
    if value in {"COMPLETE_WITH_WARNINGS", "READY_WITH_WARNINGS", "RC_WITH_WARNINGS", "WARN", "WARNING"}:
        return "badge--warn"
    if value in {"INCOMPLETE", "NOT_READY", "RC_BLOCKED", "FAIL", "FAILED"}:
        return "badge--bad"
    if value in {"COMPLETE_WITH_WARNINGS".lower(), "complete_with_warnings"}:
        return "badge--warn"
    if value in {"complete", "rc_ready"}:
        return "badge--ok"
    if value in {"incomplete", "rc_blocked"}:
        return "badge--bad"
    return ""
