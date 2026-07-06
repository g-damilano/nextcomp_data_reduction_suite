from __future__ import annotations

import html
import json
import os
from typing import Any

from markupsafe import Markup

from audit.aggregate_packet_renderer import render_aggregate_packet
from audit.audit_block_builder import build_audit_block_index_from_blocks, build_audit_blocks
from audit.run_packet_renderer import render_run_index, render_run_packets
from audit.vega_specs import bending_spec, modulus_window_spec, stress_strain_family_spec
from audit.procedure_evidence_index import build_procedure_evidence_index
from acceptance.selection_editor import FINAL_SELECTION_ID
from compatibility import SchemaMethodCompatibilityChecker
from mapping import MappingCandidateDiscovery, build_mapping_resolution_report
from methods.core.method_result import MethodRunResult
from reporting.completion import ReportCompletionChecker
from reporting.renderers.formatting_standard import (
    REPORT_FORMATTING_CSS,
    REPORT_FORMATTING_SCRIPT,
    ReportNoteCollector,
    render_methods_appendix,
)
from reporting.run_labels import replace_run_ids_for_display, run_display_label, run_list_display
from html_renderer.context_models import (
    AuditAcceptanceSummaryContext,
    AuditAppendixDetailContext,
    AuditArtifactLinksContext,
    AuditBlockCardContext,
    AuditChartComponentContext,
    AuditComponentContext,
    AuditComponentMicrocopyContext,
    AuditDecisionRegisterContext,
    AuditEvidenceAppendicesContext,
    AuditEvidenceReportContext,
    AuditEvidenceTableContext,
    AuditGroupedRunPacketContext,
    AuditGroupedSectionsContext,
    AuditInspectionLogComponentContext,
    AuditOperationLogComponentContext,
    AuditProcessSectionContext,
    AuditProcessSectionsContext,
    AuditProcessSummarySentenceContext,
    AuditProcessOverviewContext,
    AuditRawEvidenceNoteContext,
    AuditReadinessSummaryContext,
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
    AuditTrackerContext,
    AuditTrackerLinkContext,
    AuditTrackerRunLinkContext,
    AuditTechnicalAppendixContext,
    AuditValidationSummaryContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_audit_acceptance_summary,
    render_audit_artifact_links,
    render_audit_chart_component,
    render_audit_component,
    render_audit_component_microcopy,
    render_audit_decision_register,
    render_audit_evidence_report,
    render_audit_evidence_appendices,
    render_audit_grouped_sections,
    render_audit_inspection_log_component,
    render_audit_operation_log_component,
    render_audit_process_overview,
    render_audit_process_sections,
    render_audit_process_summary_sentence,
    render_audit_raw_evidence_note,
    render_audit_readiness_summary,
    render_audit_table,
    render_audit_technical_appendix,
    render_audit_tracker,
    render_audit_validation_summary,
    render_report_details_fragment,
    render_report_empty_paragraph,
    render_report_heading_fragment,
    render_report_paragraph_fragment,
)


class AuditReportBuilder:
    def build_payload(
        self,
        result: MethodRunResult,
        *,
        procedure_evidence_index: dict[str, Any] | None = None,
        audit_block_index: dict[str, Any] | None = None,
        audit_blocks: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        procedure_evidence_index = procedure_evidence_index or build_procedure_evidence_index(result)
        audit_blocks = audit_blocks or build_audit_blocks(result, procedure_evidence_index)
        audit_block_index = audit_block_index or build_audit_block_index_from_blocks(audit_blocks)
        validation_summary = result.validation_report.get("summary", {})
        acceptance_summary = result.acceptance_report.get("summary", {})
        human_decisions = result.human_decisions if isinstance(result.human_decisions, dict) else {}
        decision_rows = human_decisions.get("decisions", [])
        final_sets = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
        curve_family = result.curve_family_assessment if isinstance(result.curve_family_assessment, dict) else {}
        curve_shape = result.curve_shape_diagnostic_report if isinstance(result.curve_shape_diagnostic_report, dict) else {}
        report_completion = _audit_report_completion(result)
        report_overrides = list(result.report_overrides or ())
        boundary_summary = _boundary_resolution_summary(result)
        compatibility = SchemaMethodCompatibilityChecker().check(source=result.source, method_package=result.method_package)
        candidate_report = MappingCandidateDiscovery().discover(source=result.source, method_package=result.method_package)
        resolution_report = build_mapping_resolution_report(mapping=result.mapping, candidate_report=candidate_report)
        return {
            "schema_id": "method.audit_report.v0_1",
            "surface": "audit_report",
            "purpose": "ISO 14126 analysis evidence and traceability report.",
            "source_mtdp": {
                "path": str(result.source.path),
                "schema_id": result.source.manifest.get("schema_id"),
                "schema_version": result.source.manifest.get("schema_version"),
                "run_count": len(result.source.runs),
            },
            "method_package": {
                "method_id": result.method_package.method_id,
                "name": result.method_package.name,
                "version": result.method_package.version,
                "standard_reference": result.method_package.manifest.get("standard_reference", "ISO 14126"),
            },
            "mapping_profile": {
                "mapping_id": result.mapping.get("mapping_id"),
                "method_id": result.mapping.get("method_id"),
                "channel_bindings": len(result.mapping.get("channels", {})) if isinstance(result.mapping.get("channels"), dict) else 0,
                "token_bindings": len(result.mapping.get("tokens", {})) if isinstance(result.mapping.get("tokens"), dict) else 0,
                "candidate_summary": candidate_report.get("summary", {}),
                "resolution_summary": resolution_report.get("summary", {}),
            },
            "schema_method_compatibility": compatibility.to_dict(),
            "readiness": {
                "status": result.readiness_report.get("status"),
                "summary": result.readiness_report.get("summary", {}),
                "warnings": result.readiness_report.get("warnings", []),
            },
            "method_execution": {
                "resolve_summary": result.resolve_summary,
                "reduce_summary": result.reduce_summary,
                "operation_count": len(result.operation_log),
                "inspection_count": len(result.inspections),
            },
            "procedure_evidence": {
                "artifact": "audit/procedure_evidence_index.json",
                "operation_count": procedure_evidence_index.get("operation_count", 0),
                "run_count": procedure_evidence_index.get("run_count", 0),
                "surface_roles": procedure_evidence_index.get("surface_roles", {}),
            },
            "audit_blocks": {
                "artifact": "audit/audit_blocks.json",
                "index_artifact": "audit/audit_block_index.json",
                "summary": audit_block_index.get("summary", {}),
                "run_packets": [
                    {
                        "run_id": packet.get("run_id"),
                        "packet_id": packet.get("packet_id"),
                        "block_count": len(packet.get("blocks", []) if isinstance(packet.get("blocks"), list) else []),
                    }
                    for packet in audit_block_index.get("run_packets", [])
                    if isinstance(packet, dict)
                ],
                "aggregate_packet": {
                    "packet_id": (audit_block_index.get("aggregate_packet", {}) or {}).get("packet_id", ""),
                    "block_count": len((audit_block_index.get("aggregate_packet", {}) or {}).get("blocks", []) or []),
                },
            },
            "experiment_boundary_resolution": boundary_summary,
            "validation": {
                "status": validation_summary.get("status"),
                "summary": validation_summary,
                "deviation_count": len(result.validation_deviations),
            },
            "acceptance": {
                "summary": acceptance_summary,
                "default_selection_set": result.acceptance_report.get("default_selection_set"),
                "final_selection_set": final_sets.get("default_selection_set"),
                "selection_source": final_sets.get("selection_source"),
                "flag_count": len(result.run_flags),
                "discharged_run_count": len(result.discharged_runs),
            },
            "curve_family_assessment": {
                "summary": curve_family.get("summary", {}),
                "flag_count": len(result.curve_family_flags or []),
                "score_count": len(result.curve_family_scores or []),
                "artifacts": {
                    "report": "acceptance/curve_family/curve_family_report.json",
                    "scores": "acceptance/curve_family/curve_family_scores.csv",
                    "residuals": "acceptance/curve_family/residuals_long.csv",
                },
            },
            "curve_shape_diagnostic": {
                "summary": curve_shape.get("summary", {}),
                "cohorts": curve_shape.get("cohorts", []),
                "flag_count": len(result.curve_shape_diagnostic_flags or []),
                "score_count": len(result.curve_shape_diagnostic_scores or []),
                "artifacts": {
                    "report": "acceptance/curve_family/curve_diagnostic_report.json",
                    "scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
                    "reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
                    "residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
                    "policy": "acceptance/curve_family/curve_diagnostic_policy.json",
                    "flags": "acceptance/curve_family/curve_diagnostic_flags.csv",
                },
            },
            "human_overrides": {
                "decision_count": len(decision_rows) if isinstance(decision_rows, list) else 0,
                "ledger_count": len(result.override_ledger_rows or []),
                "decisions": decision_rows if isinstance(decision_rows, list) else [],
            },
            "report_completion": {
                **report_completion,
                "override_count": len(report_overrides),
                "mtdp_mutated": False,
                "statement": "Report-only overrides are applied to report artifacts and do not mutate the source MTDP package.",
            },
            "report_overrides": {
                "override_count": len(report_overrides),
                "overrides": report_overrides,
                "ledger_artifact": "report/report_override_ledger.json",
                "mtdp_mutation": "not_mutated",
            },
            "mtda_finalization": {
                "status": "not_finalized",
                "mtdp_mutated": False,
                "statement": "No post-run MTDA finalization amendments are recorded for this archive.",
            },
            "warnings": {
                "count": len(result.warnings),
                "items": result.warnings,
            },
            "artifact_links": {
                "test_report": "report/test_report.html",
                "audit_report": "audit/audit_report.html",
                "method_development_workbench": "workbench/index.html",
                "surface_manifest": "surface_manifest.json",
            },
        }

    def build(
        self,
        result: MethodRunResult,
        *,
        procedure_evidence_index: dict[str, Any] | None = None,
        audit_block_index: dict[str, Any] | None = None,
        audit_blocks: dict[str, Any] | None = None,
    ) -> str:
        procedure_evidence_index = procedure_evidence_index or build_procedure_evidence_index(result)
        audit_blocks = audit_blocks or build_audit_blocks(result, procedure_evidence_index)
        audit_block_index = audit_block_index or build_audit_block_index_from_blocks(audit_blocks)
        audit_payload = self.build_payload(
            result,
            procedure_evidence_index=procedure_evidence_index,
            audit_block_index=audit_block_index,
            audit_blocks=audit_blocks,
        )
        specs: dict[str, dict[str, Any]] = {}
        title = "Audit Report"
        source_path = str(result.source.path)
        source_name = _basename(source_path)
        source_parent = _parent_basename(source_path)
        source_display = (
            f"{source_name} ({source_parent})"
            if source_name and source_parent
            else (source_name or _compact_text(source_path, limit=72))
        )
        process_overview = _process_overview(audit_payload)
        note_collector = ReportNoteCollector(projection_plane=ProjectionPlane.AUDIT)
        grouped_sections = (
            render_run_index(audit_blocks, result=result)
            + render_run_packets(audit_blocks, result=result, specs=specs)
            + render_aggregate_packet(audit_blocks, result=result, specs=specs, note_collector=note_collector)
            + _decision_register_section(result, audit_payload)
        )
        appendix = render_methods_appendix(note_collector, projection_plane=ProjectionPlane.AUDIT)
        tracker = _audit_tracker(audit_blocks)
        payload = json.dumps(specs)
        if os.environ.get("MTDA_HTML_RENDERER", "").casefold() != "legacy":
            return render_audit_evidence_report(
                AuditEvidenceReportContext(
                    projection_plane=ProjectionPlane.AUDIT,
                    recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_REPORT,
                    page_title=title,
                    process_overview_html=Markup(process_overview),
                    report_tracker_html=Markup(tracker),
                    grouped_sections_html=Markup(grouped_sections),
                    appendix_html=Markup(appendix),
                    vega_specs_json=Markup(payload),
                    formatting_css=Markup(REPORT_FORMATTING_CSS),
                    formatting_script=Markup(REPORT_FORMATTING_SCRIPT),
                )
            )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
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
    body {{ margin: 0; color: var(--ink); font-family: Arial, Helvetica, sans-serif; background: #f3f6f9; line-height: 1.45; overflow-x: hidden; }}
    .page {{ max-width: 1320px; margin: 0 auto; padding: 28px; }}
    main {{ min-width: 0; }}
    .layout {{ display: grid; grid-template-columns: 310px minmax(0, 1fr); gap: 14px; align-items: start; }}
    .report-content {{ min-width: 0; }}
    .report-tracker {{ position: sticky; top: 12px; width: 310px; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 8px; }}
    .report-tracker a {{ display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 6px; align-items: center; color: inherit; text-decoration: none; padding: 5px 6px; min-height: 30px; border-radius: 8px; border-bottom: 1px solid #eef2f6; }}
    .report-tracker a:last-child {{ border-bottom: 0; }}
    .report-tracker a:hover {{ background: var(--soft); }}
    .report-tracker b {{ font-size: 13px; }}
    .report-tracker span {{ font-size: 13px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .report-tracker em {{ justify-self: end; width: fit-content; margin-left: 4px; }}
    .report-tracker-sublist {{ margin: 2px 0 8px 30px; padding-left: 8px; border-left: 2px solid #e5ebf2; }}
    .report-tracker-sublist a {{ grid-template-columns: 22px minmax(0, 1fr); min-height: 25px; padding: 4px 6px; border-bottom: 0; color: var(--muted); }}
    .report-tracker-sublist b {{ font-size: 12px; }}
    .report-tracker-sublist span {{ font-size: 12px; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; margin: 0 0 14px; padding: 18px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; line-height: 1.2; }}
    h2 {{ margin: 0 0 12px; font-size: 19px; line-height: 1.2; }}
    h3 {{ margin: 18px 0 8px; font-size: 15px; line-height: 1.2; }}
    p {{ line-height: 1.45; }}
    a {{ color: var(--brand); }}
    .muted, .appendix-note, .audit-purpose {{ color: var(--muted); }}
    .report-state-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px; margin-bottom: 16px; }}
    .report-state-top {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: start; border-bottom: 1px solid #eef2f6; padding-bottom: 12px; margin-bottom: 12px; }}
    .report-state-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin-bottom: 3px; }}
    .report-state-status {{ border-left: 4px solid var(--brand); background: #eef7fc; padding: 8px 12px; border-radius: 8px; min-width: 230px; }}
    .report-state-status.ok {{ border-left-color: var(--ok-line); background: var(--ok-bg); }}
    .report-state-status.warn {{ border-left-color: var(--warn-line); background: var(--warn-bg); }}
    .report-state-status.bad {{ border-left-color: var(--bad-line); background: var(--bad-bg); }}
    .report-state-status strong {{ display: block; font-size: 14px; }}
    .report-state-status span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 2px; }}
    .report-state-note {{ color: var(--muted); font-size: 13px; margin: 7px 0 0; }}
    .table-wrap {{ width: 100%; overflow-x: auto; margin: 8px 0; }}
    .table-wrap table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; margin: 8px 0; }}
    .table-wrap th, .table-wrap td {{ border-bottom: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; word-break: normal; }}
    .table-wrap th {{ background: var(--soft); font-weight: 700; }}
    .chart {{ width: 100%; min-height: 330px; max-width: 100%; overflow: hidden; }}
    .chart .vega-embed, .chart .vega-embed > div {{ max-width: 100%; }}
    .chart svg {{ display: block; width: 100%; max-width: 100%; height: auto; }}
    .chart canvas {{ max-width: 100%; height: auto; }}
    .chart-hint {{ color: var(--muted); font-size: 13px; margin: 0 0 10px; }}
    .vg-tooltip {{ max-width: 340px !important; white-space: normal !important; overflow-wrap: anywhere !important; pointer-events: none !important; }}
    .vg-tooltip table {{ width: auto !important; table-layout: auto !important; border-collapse: collapse !important; font-size: 12px !important; }}
    .vg-tooltip th, .vg-tooltip td {{ padding: 2px 6px !important; border: 0 !important; white-space: nowrap !important; overflow-wrap: normal !important; }}
    code {{ background: #eef2f6; padding: 1px 4px; border-radius: 4px; }}
    .audit-block {{ border-top: 1px solid #eef2f6; margin: 18px 0 0; padding: 14px 0 0; }}
    .audit-block h3 {{ margin: 0 0 8px; font-size: 15px; }}
    .run-packet > header {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; border-bottom: 1px solid #eef2f6; padding-bottom: 9px; margin-bottom: 4px; }}
    .run-packet h3 {{ margin: 0; }}
    .audit-purpose {{ margin: 0 0 10px; }}
    .appendix-note {{ color: var(--muted); }}
    .status-pass {{ color: #28663a; font-weight: 700; }}
    .status-warn {{ color: #8a6500; font-weight: 700; }}
    .status-fail {{ color: #9b2d2d; font-weight: 700; }}
    .status-badge {{ display: inline-block; margin-left: 8px; border-radius: 999px; border: 1px solid var(--line); padding: 2px 7px; font-size: 12px; font-weight: 700; background: #fff; }}
    .status-badge.status-pass {{ border-color: var(--ok-line); background: var(--ok-bg); color: #28663a; }}
    .status-badge.status-warn {{ border-color: var(--warn-line); background: var(--warn-bg); color: #8a6500; }}
    .status-badge.status-fail {{ border-color: var(--bad-line); background: var(--bad-bg); color: #9b2d2d; }}
    .packet-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .audit-block-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }}
    .summary-panel {{ border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); background: #fff; padding: 10px 0; margin: 10px 0 14px; }}
    .summary-panel h4 {{ margin: 0 0 8px; }}
    .summary-panel .table-wrap {{ margin: 0; }}
    .plot-panel {{ border: 1px solid var(--line); border-radius: 8px; background: #fcfdff; padding: 12px; margin: 12px 0; overflow: hidden; }}
    .plot-caption {{ color: var(--muted); font-size: 12px; margin: 8px 2px 0; }}
    .plot-unavailable {{ border: 1px dashed var(--line); border-radius: 10px; background: #fff8e6; color: #735000; padding: 10px; margin: 10px 0 14px; }}
    .analysis-comparison {{ border-top: 1px solid #eef2f6; background: #fff; margin-top: 16px; padding-top: 10px; }}
    .run-packet {{ border-top: 1px solid var(--line); background: #fff; margin: 18px 0 0; padding: 16px 0 0; }}
    .run-index-table .table-wrap table {{ table-layout: auto; }}
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
      section, .report-state-card {{ break-inside: avoid; border-color: #999; }}
    }}
{REPORT_FORMATTING_CSS}
  </style>
</head>
<body>
  <div class="page">
    {process_overview}
    <div class="layout">
      {tracker}
      <main class="report-content">
        {grouped_sections}
        {appendix}
      </main>
    </div>
  </div>
  <script>
    const specs = {payload};
    const renderedSpecs = new Set();

    function auditPlotVisible(target) {{
      return Boolean(target && (target.offsetWidth || target.offsetHeight || target.getClientRects().length));
    }}

    function renderAuditPlot(id) {{
      const target = document.getElementById(id);
      const spec = specs[id];
      if (!target || !spec || renderedSpecs.has(id) || !auditPlotVisible(target)) {{
        return;
      }}
      window.vegaEmbed("#" + id, spec, {{actions: false, renderer: "svg"}})
        .then(function () {{
          renderedSpecs.add(id);
        }})
        .catch(function (error) {{
          console.warn("Could not render audit plot", id, error);
          target.innerHTML = '<div class="plot-unavailable">Plot unavailable: could not render chart. Review the archived analysis evidence.</div>';
        }});
    }}

    function renderVisibleAuditPlots() {{
      if (!window.vegaEmbed) {{
        return;
      }}
      Object.keys(specs).forEach(renderAuditPlot);
    }}

    function initializeAuditPlots() {{
      renderVisibleAuditPlots();
      window.addEventListener("resize", renderVisibleAuditPlots);
    }}

    if (document.readyState === "loading") {{
      document.addEventListener("DOMContentLoaded", initializeAuditPlots);
    }} else {{
      initializeAuditPlots();
    }}
  </script>
  {REPORT_FORMATTING_SCRIPT}
</body>
</html>
"""


def _report_recipe(result: MethodRunResult) -> dict[str, Any]:
    recipe = result.method_package.audit_recipe.get("audit_report")
    if isinstance(recipe, dict) and isinstance(recipe.get("views"), list):
        return recipe
    return {
        "title": f"{result.method_package.name} Audit Report",
        "views": [
            {
                "id": "result_view",
                "title": "Results",
                "components": [
                    {"type": "table", "id": "specimen_results", "title": "Specimen Results"},
                    {"type": "table", "id": "dataset_summary", "title": "Dataset Summary"},
                    {"type": "readiness_summary", "id": "readiness_summary", "title": "Package Readiness"},
                    {"type": "validation_summary", "id": "validation_summary", "title": "Validation Summary"},
                    {"type": "curve_family_plot", "id": "stress_strain_family", "title": "Stress-Strain Family"},
                ],
            },
            {
                "id": "dataset_acceptance",
                "title": "Dataset Acceptance",
                "components": [
                    {"type": "acceptance_summary", "id": "acceptance_summary", "title": "Acceptance Summary"},
                    {"type": "table", "id": "dataset_summary_by_selection", "title": "Dataset Summary By Selection", "source": "method_outputs/dataset_summary_by_selection.csv"},
                    {"type": "selection_set_table", "id": "selection_membership", "title": "Selection Membership"},
                    {"type": "discharge_report", "id": "discharge_report", "title": "Discharge Report"},
                ],
            },
            {
                "id": "reduction_evidence",
                "title": "Reduction Evidence",
                "components": [
                    {"type": "operation_log", "id": "operation_log", "title": "Operation Log"},
                    {"type": "inspection_log", "id": "inspections", "title": "Curve Inspections"},
                    {"type": "operation_overlay", "id": "modulus_window", "title": "Modulus Window", "operation_type": "chord_slope"},
                    {"type": "operation_overlay", "id": "bending_diagnostic", "title": "Bending Diagnostic", "operation_type": "bending_diagnostic"},
                ],
            },
        ],
    }


def _audit_tracker(audit_blocks: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_audit_tracker(audit_blocks)
    return render_audit_tracker(_audit_tracker_context(audit_blocks))


def _legacy_audit_tracker(audit_blocks: dict[str, Any]) -> str:
    run_packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    links = [
        ("1", "Evidence Navigation", "evidence_navigation_run_index", ""),
        ("2", "Run-wise Evidence Packets", "run_wise_evidence_packets", str(len(run_packets))),
        ("3", "Aggregate Evidence Packet", "aggregate_evidence_packet", ""),
        ("4", "Decision Register", "decision_register", ""),
    ]
    items = []
    for number, label, anchor, pill in links:
        pill_html = f'<em class="status-badge status-pass">{html.escape(pill)}</em>' if pill else ""
        items.append(
            f"<a href=\"#{html.escape(anchor)}\">"
            f"<b>{html.escape(number)}</b>"
            f"<span>{html.escape(label)}</span>"
            f"{pill_html}"
            "</a>"
        )
        if anchor == "run_wise_evidence_packets":
            run_items = []
            for index, packet in enumerate(run_packets, start=1):
                if not isinstance(packet, dict):
                    continue
                run_id = str(packet.get("run_id") or "")
                if not run_id:
                    continue
                run_items.append(
                    f"<a href=\"#packet-{html.escape(run_id)}\">"
                    f"<b>{index}</b><span>{html.escape(run_display_label(run_id))}</span></a>"
                )
            if run_items:
                items.append(f"<div class=\"report-tracker-sublist\">{''.join(run_items)}</div>")
    return f"<nav aria-label=\"Audit report locations\" class=\"report-tracker\">{''.join(items)}</nav>"


def _audit_tracker_context(audit_blocks: dict[str, Any]) -> AuditTrackerContext:
    run_packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    links = [
        ("1", "Evidence Navigation", "evidence_navigation_run_index", ""),
        ("2", "Run-wise Evidence Packets", "run_wise_evidence_packets", str(len(run_packets))),
        ("3", "Aggregate Evidence Packet", "aggregate_evidence_packet", ""),
        ("4", "Decision Register", "decision_register", ""),
    ]
    link_contexts = []
    for number, label, anchor, pill in links:
        run_links: tuple[AuditTrackerRunLinkContext, ...] = ()
        if anchor == "run_wise_evidence_packets":
            run_link_contexts = []
            for index, packet in enumerate(run_packets, start=1):
                if not isinstance(packet, dict):
                    continue
                run_id = str(packet.get("run_id") or "")
                if not run_id:
                    continue
                run_link_contexts.append(
                    AuditTrackerRunLinkContext(
                        anchor_html=Markup(html.escape(run_id)),
                        number=index,
                        label_html=Markup(html.escape(run_display_label(run_id))),
                    )
                )
            run_links = tuple(run_link_contexts)
        pill_html = f'<em class="status-badge status-pass">{html.escape(pill)}</em>' if pill else ""
        link_contexts.append(
            AuditTrackerLinkContext(
                number_html=Markup(html.escape(number)),
                label_html=Markup(html.escape(label)),
                anchor_html=Markup(html.escape(anchor)),
                pill_html=Markup(pill_html),
                run_links=run_links,
            )
        )
    return AuditTrackerContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
        links=tuple(link_contexts),
    )


def _audit_report_completion(result: MethodRunResult) -> dict[str, Any]:
    recipe = getattr(result.method_package, "report_recipe", {})
    if not isinstance(recipe, dict) or not recipe:
        return {
            "status": "",
            "missing_field_count": 0,
            "required_missing_count": 0,
            "recommended_missing_count": 0,
        }
    selection_set = _audit_selection_set(result, recipe)
    selection_source = "human_final" if selection_set == FINAL_SELECTION_ID else "machine_acceptance"
    completion = ReportCompletionChecker().check(
        result=result,
        recipe=recipe,
        selection_set=selection_set,
        selection_source=selection_source,
        overrides=result.report_overrides,
    )
    return {
        "status": completion.completion_status.get("status", ""),
        "missing_field_count": completion.completion_status.get("missing_field_count", 0),
        "required_missing_count": completion.completion_status.get("required_missing_count", 0),
        "recommended_missing_count": completion.completion_status.get("recommended_missing_count", 0),
        "selection_set": selection_set,
        "selection_source": selection_source,
    }


def _audit_selection_set(result: MethodRunResult, recipe: dict[str, Any]) -> str:
    if result.final_report_runs or result.selection_membership_final:
        return FINAL_SELECTION_ID
    recipe_selection = recipe.get("selection_set")
    if recipe_selection and recipe_selection != "selected":
        return str(recipe_selection)
    default = result.acceptance_report.get("default_selection_set")
    return str(default or "auto_recommended_runs")


def _boundary_resolution_summary(result: MethodRunResult) -> dict[str, Any]:
    records = result.experiment_boundaries or []
    warnings = [
        {"run_id": record.get("run_id"), "warnings": record.get("warnings", [])}
        for record in records
        if isinstance(record, dict) and record.get("warnings")
    ]
    endpoint_rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        interval = record.get("analysis_interval") if isinstance(record.get("analysis_interval"), dict) else {}
        policy = record.get("resolution_policy") if isinstance(record.get("resolution_policy"), dict) else {}
        start_policy_detail = policy.get("start") if isinstance(policy.get("start"), dict) else {}
        endpoint_rows.append(
            {
                "run_id": record.get("run_id"),
                "start_index": interval.get("start_index", record.get("start_index")),
                "end_index": interval.get("end_index", record.get("end_index")),
                "include_endpoint": interval.get("include_endpoint", record.get("include_endpoint")),
                "start_policy": record.get("start_policy"),
                "start_min_load_fraction_of_max": start_policy_detail.get("min_load_fraction_of_max"),
                "end_policy": record.get("end_policy"),
                "confidence": record.get("confidence"),
                "reason": record.get("reason"),
                "warnings": len(record.get("warnings", []) or []),
            }
        )
    start_policy = _first_record_value(records, "start_policy")
    end_policy = _first_record_value(records, "end_policy")
    aggregation_policy = result.method_package.curve_aggregation_policy
    curve_policy = aggregation_policy.get("curve_aggregation") if isinstance(aggregation_policy, dict) and isinstance(aggregation_policy.get("curve_aggregation"), dict) else aggregation_policy
    alignment = curve_policy.get("alignment") if isinstance(curve_policy, dict) else {}
    boundary_aligned = isinstance(alignment, dict) and alignment.get("domain") == "experiment_progress"
    return {
        "status": "resolved" if records else "not_recorded",
        "policy": {
            "start_policy": start_policy,
            "end_policy": end_policy,
            "include_endpoint": _first_record_interval_value(records, "include_endpoint"),
        },
        "summary": (
            f"{len(records)} runs resolved with start_policy={start_policy or 'unknown'} "
            f"and end_policy={end_policy or 'unknown'}."
        ),
        "bounded_reduction": bool(records),
        "boundary_aligned_aggregation": boundary_aligned,
        "warning_count": len(warnings),
        "warnings": warnings,
        "endpoints": endpoint_rows,
        "artifacts": {
            "boundary_resolution": "audit/boundary_resolution.json",
            "boundary_events": "audit/boundary_events.csv",
            "boundaries": "method_outputs/boundaries.csv",
        },
    }


def _first_record_value(records: list[dict[str, Any]], key: str) -> Any:
    for record in records:
        if isinstance(record, dict) and record.get(key) not in (None, ""):
            return record.get(key)
    return ""


def _first_record_interval_value(records: list[dict[str, Any]], key: str) -> Any:
    for record in records:
        if not isinstance(record, dict):
            continue
        interval = record.get("analysis_interval") if isinstance(record.get("analysis_interval"), dict) else {}
        if interval.get(key) not in (None, ""):
            return interval.get(key)
        if record.get(key) not in (None, ""):
            return record.get(key)
    return ""


def _render_recipe_sections(
    result: MethodRunResult,
    recipe: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_render_recipe_sections(result, recipe, curve_rows, specs)
    return render_audit_evidence_appendices(
        _audit_evidence_appendices_context(result, recipe, curve_rows, specs)
    )


def _legacy_render_recipe_sections(
    result: MethodRunResult,
    recipe: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> str:
    sections: list[str] = [
        "<section id=\"audit_evidence_appendices\"><h2>Evidence Appendices</h2>"
        "<p class=\"appendix-note\">These appendices preserve the raw method evidence for traceability. Use the Method Development Workbench for operation-by-operation replay and graph inspection.</p>"
    ]
    for view in recipe.get("views", ()) or ():
        if not isinstance(view, dict):
            continue
        components = []
        for component in view.get("components", ()) or ():
            if isinstance(component, dict):
                components.append(_render_component(result, component, curve_rows, specs))
        sections.append(
            f"<details class=\"audit-details\" id=\"{html.escape(str(view.get('id', 'view')))}\">"
            f"<summary>{html.escape(str(view.get('title', 'Audit View')))}</summary>"
            f"<div>{''.join(components)}</div></details>"
        )
    if result.warnings:
        sections.append(f"<details class=\"audit-details\"><summary>Warnings</summary><div>{_table(result.warnings)}</div></details>")
    sections.append("</section>")
    return "".join(sections)


def _audit_evidence_appendices_context(
    result: MethodRunResult,
    recipe: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> AuditEvidenceAppendicesContext:
    details: list[AuditAppendixDetailContext] = []
    for view in recipe.get("views", ()) or ():
        if not isinstance(view, dict):
            continue
        components = []
        for component in view.get("components", ()) or ():
            if isinstance(component, dict):
                components.append(_render_component(result, component, curve_rows, specs))
        details.append(
            AuditAppendixDetailContext(
                detail_class="audit-details",
                detail_id_html=Markup(html.escape(str(view.get("id", "view")))),
                summary_html=Markup(html.escape(str(view.get("title", "Audit View")))),
                body_html=Markup("".join(components)),
                detail_html=_audit_body_details(
                    title_html=Markup(html.escape(str(view.get("title", "Audit View")))),
                    body_html=Markup("".join(components)),
                    fragment_id_html=Markup(html.escape(str(view.get("id", "view")))),
                ),
            )
        )
    if result.warnings:
        warnings_table_html = Markup(_table(result.warnings))
        details.append(
            AuditAppendixDetailContext(
                detail_class="audit-details",
                summary_html=Markup("Warnings"),
                body_html=warnings_table_html,
                detail_html=_audit_body_details(title_html=Markup("Warnings"), body_html=warnings_table_html),
            )
        )
    return AuditEvidenceAppendicesContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_APPENDICES,
        section_heading_html=_audit_body_heading(Markup("Evidence Appendices"), heading_level=2),
        note_html=_audit_body_paragraph(
            Markup(
                "These appendices preserve the raw method evidence for traceability. Use the Method "
                "Development Workbench for operation-by-operation replay and graph inspection."
            ),
            paragraph_class="appendix-note",
        ),
        details=tuple(details),
    )


def _process_overview(payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_process_overview(payload)
    return render_audit_process_overview(_audit_process_overview_context(payload))


def _legacy_process_overview(payload: dict[str, Any]) -> str:
    summary_rows = _process_summary_rows(payload)
    context = _audit_process_overview_context(payload)
    return (
        "<section id=\"audit_overview\" class=\"report-state-card audit-overview-card\">"
        "<div class=\"report-state-top\">"
        "<div>"
        "<div class=\"report-state-label\">Audit report</div>"
        "<h1>Audit Report</h1>"
        f"{context.lede_html}"
        "</div>"
        "<div class=\"report-state-status\">"
        "<strong>Evidence surface</strong>"
        "<span>ISO 14126 audit evidence</span>"
        "</div>"
        "</div>"
        "<h2>Audit Overview</h2>"
        f"{context.overview_html}"
        f"<div class=\"table-wrap\"><table class=\"compact report-state-table\"><thead><tr><th>Area</th><th>State</th><th>Evidence</th></tr></thead><tbody>{_overview_table_rows(summary_rows)}</tbody></table></div>"
        "</section>"
    )


def _audit_process_overview_context(payload: dict[str, Any]) -> AuditProcessOverviewContext:
    rows = _process_summary_rows(payload)
    headers = tuple(
        AuditTableCellContext(html=Markup(label))
        for label in ("Area", "State", "Evidence")
    )
    table_rows = []
    for row in rows:
        state = _human_value(row.get("State"))
        table_rows.append(
            AuditTableRowContext(
                cells=(
                    AuditTableCellContext(html=Markup(html.escape(_human_value(row.get("Stage"))))),
                    AuditTableCellContext(html=Markup(html.escape(state))),
                    AuditTableCellContext(html=Markup(html.escape(_human_value(row.get("Evidence"))))),
                )
            )
        )
    return AuditProcessOverviewContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_OVERVIEW,
        lede_html=_audit_body_paragraph(
            Markup("Grouped human audit evidence and traceability."),
            paragraph_class="report-state-note",
        ),
        overview_html=_audit_body_paragraph(
            Markup(
                'ISO 14126 analysis evidence for experiment boundaries, reduction results, bending, '
                'curve-shape diagnostics, and validation state. Formal result values are in the '
                '<a href="../report/test_report.html">Test Report</a>.'
            )
        ),
        table=AuditTableContext(
            table_class="compact report-state-table",
            headers=headers,
            rows=tuple(table_rows),
        ),
    )


def _overview_table_rows(rows: list[dict[str, Any]]) -> str:
    html_rows = []
    for row in rows:
        state = _human_value(row.get("State"))
        html_rows.append(
            "<tr>"
            f"<td>{html.escape(_human_value(row.get('Stage')))}</td>"
            f"<td>{html.escape(state)}</td>"
            f"<td>{html.escape(_human_value(row.get('Evidence')))}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _process_sections(payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_process_sections(payload)
    return render_audit_process_sections(_audit_process_sections_context(payload))


def _legacy_process_sections(payload: dict[str, Any]) -> str:
    sections = [
        ("source_mtdp", "Source MTDP", payload.get("source_mtdp", {})),
        ("method_package", "Method Package", payload.get("method_package", {})),
        ("compatibility_mapping", "Compatibility and Mapping", {
            **_flatten(payload.get("schema_method_compatibility", {}), keys=("status", "blocks_mapping")),
            **{f"mapping_{key}": value for key, value in _flatten(payload.get("mapping_profile", {}), keys=("mapping_id", "method_id", "channel_bindings", "token_bindings")).items()},
        }),
        ("readiness", "Readiness", payload.get("readiness", {})),
        ("experiment_boundary_resolution", "Experiment Boundary Resolution", payload.get("experiment_boundary_resolution", {})),
        ("validation", "Validation", payload.get("validation", {})),
        ("acceptance_final_selection", "Acceptance and Final Selection", payload.get("acceptance", {})),
        ("finalization", "MTDA Finalization", payload.get("mtda_finalization", {})),
        ("warnings_residuals", "Warnings and Residuals", payload.get("warnings", {})),
        ("linked_artifacts", "Linked Artifacts", payload.get("artifact_links", {})),
    ]
    html_sections: list[str] = []
    for section_id, title, data in sections:
        rows = [data] if isinstance(data, dict) else []
        html_sections.append(
            f"<section id=\"audit_rc_{html.escape(section_id)}\">"
            f"<h2>{html.escape(title)}</h2>"
            f"{_legacy_summary_sentence(section_id, data)}"
            f"<details class=\"audit-details\"><summary>{html.escape(title)} evidence detail</summary><div>{_legacy_process_section_evidence_purpose()}{_legacy_table(rows)}</div></details>"
            "</section>"
        )
    return "".join(html_sections)


def _audit_process_sections_context(payload: dict[str, Any]) -> AuditProcessSectionsContext:
    sections = [
        ("source_mtdp", "Source MTDP", payload.get("source_mtdp", {})),
        ("method_package", "Method Package", payload.get("method_package", {})),
        ("compatibility_mapping", "Compatibility and Mapping", {
            **_flatten(payload.get("schema_method_compatibility", {}), keys=("status", "blocks_mapping")),
            **{f"mapping_{key}": value for key, value in _flatten(payload.get("mapping_profile", {}), keys=("mapping_id", "method_id", "channel_bindings", "token_bindings")).items()},
        }),
        ("readiness", "Readiness", payload.get("readiness", {})),
        ("experiment_boundary_resolution", "Experiment Boundary Resolution", payload.get("experiment_boundary_resolution", {})),
        ("validation", "Validation", payload.get("validation", {})),
        ("acceptance_final_selection", "Acceptance and Final Selection", payload.get("acceptance", {})),
        ("finalization", "MTDA Finalization", payload.get("mtda_finalization", {})),
        ("warnings_residuals", "Warnings and Residuals", payload.get("warnings", {})),
        ("linked_artifacts", "Linked Artifacts", payload.get("artifact_links", {})),
    ]
    contexts = []
    for section_id, title, data in sections:
        rows = [data] if isinstance(data, dict) else []
        title_html = Markup(html.escape(title))
        evidence_purpose_html = Markup(_process_section_evidence_purpose())
        table_html = Markup(_legacy_table(rows))
        contexts.append(
            AuditProcessSectionContext(
                section_id_html=Markup(html.escape(section_id)),
                title_html=title_html,
                summary_html=Markup(_summary_sentence(section_id, data)),
                evidence_purpose_html=evidence_purpose_html,
                table_html=table_html,
                evidence_detail_html=_audit_body_details(
                    title_html=title_html,
                    marker_html=Markup(" evidence detail"),
                    purpose_html=evidence_purpose_html,
                    body_html=table_html,
                ),
            )
        )
    return AuditProcessSectionsContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_SECTIONS,
        sections=tuple(contexts),
    )


def _decision_register_section(result: MethodRunResult, payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_decision_register_section(result, payload)
    return render_audit_decision_register(_audit_decision_register_context(result, payload))


def _legacy_decision_register_section(result: MethodRunResult, payload: dict[str, Any]) -> str:
    disposition_rows = _decision_rows(result)
    disposition_summary = _disposition_summary_rows(disposition_rows)
    human_overrides = result.human_decision_rows or []
    amendments = result.override_ledger_rows or []
    report_overrides = list(result.report_overrides or ())
    parts = [
        "<section id=\"decision_register\">"
        "<h2>Decision Register</h2>"
        "<h3>Final report run set summary</h3>"
        f"{_table(disposition_summary)}"
        "<h3>Run disposition register</h3>"
        f"{_table(disposition_rows)}"
    ]
    if human_overrides:
        parts.append("<h3>Human overrides</h3>")
        parts.append(_table(human_overrides))
    if amendments or report_overrides:
        parts.append("<h3>Finalization / report-only amendments</h3>")
        parts.append(_table(amendments or report_overrides))
    parts.append("</section>")
    return "".join(parts)


def _audit_decision_register_context(result: MethodRunResult, payload: dict[str, Any]) -> AuditDecisionRegisterContext:
    disposition_rows = _decision_rows(result)
    disposition_summary = _disposition_summary_rows(disposition_rows)
    human_overrides = result.human_decision_rows or []
    amendments = result.override_ledger_rows or []
    report_overrides = list(result.report_overrides or ())
    amendment_rows = amendments or report_overrides
    return AuditDecisionRegisterContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_DECISION_REGISTER,
        section_heading_html=_audit_body_heading(Markup("Decision Register"), heading_level=2),
        disposition_summary_heading_html=_audit_body_heading(
            Markup("Final report run set summary"), heading_level=3
        ),
        disposition_summary_table_html=Markup(_table(disposition_summary)),
        disposition_heading_html=_audit_body_heading(Markup("Run disposition register"), heading_level=3),
        disposition_table_html=Markup(_table(disposition_rows)),
        has_human_overrides=bool(human_overrides),
        human_overrides_heading_html=_audit_body_heading(Markup("Human overrides"), heading_level=3),
        human_overrides_table_html=Markup(_table(human_overrides) if human_overrides else ""),
        has_amendments=bool(amendment_rows),
        amendments_heading_html=_audit_body_heading(
            Markup("Finalization / report-only amendments"), heading_level=3
        ),
        amendments_table_html=Markup(_table(amendment_rows) if amendment_rows else ""),
    )


def _decision_flag_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows = []
    for flag in result.run_flags or []:
        if not isinstance(flag, dict):
            continue
        run_id = str(flag.get("run_id") or "")
        rows.append(
            {
                "run_id": run_id,
                "evidence_category": flag.get("category") or flag.get("source"),
                "evidence_anchor": _evidence_anchor(flag),
                "flag": flag.get("flag_id") or flag.get("rule_id"),
                "severity": flag.get("severity"),
                "reason": flag.get("message") or flag.get("reason"),
            }
        )
    return rows


def _decision_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows = []
    final_by_run = {
        str(row.get("run_id") or ""): row
        for row in result.final_report_runs or []
        if isinstance(row, dict)
    }
    discharged = {
        str(row.get("run_id") or ""): row
        for row in result.discharged_runs or []
        if isinstance(row, dict)
    }
    run_ids = [str(row.get("run_id") or "") for row in result.specimen_results if isinstance(row, dict)]
    for run_id in run_ids:
        final = final_by_run.get(run_id, {})
        discharge = discharged.get(run_id, {})
        flags = [row for row in result.run_flags or [] if isinstance(row, dict) and str(row.get("run_id") or "") == run_id]
        primary = flags[0] if flags else {}
        included = final.get("final_included", final.get("included", False))
        specimen = next((row for row in result.specimen_results if isinstance(row, dict) and str(row.get("run_id") or "") == run_id), {})
        final_status = _final_report_status(final, discharge, included)
        rows.append(
            {
                "run_label": run_display_label(run_id),
                "specimen": final.get("specimen_name") or specimen.get("specimen_name") or "",
                "final_report_status": final_status,
                "basis": _decision_reason(final, discharge, primary, final_status=final_status),
                "evidence_anchor": _evidence_link(primary, run_id),
                "override": _reviewer_override(final),
            }
        )
    return rows


def _disposition_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = [
        "Included",
        "Review required - held out",
        "Excluded",
        "Included by override",
        "Excluded by override",
    ]
    grouped: dict[str, list[str]] = {}
    for row in rows:
        status = str(row.get("final_report_status") or "")
        grouped.setdefault(status, []).append(str(row.get("run_label") or ""))
    summary = []
    for status in order:
        run_ids = [run_id for run_id in grouped.get(status, []) if run_id]
        if not run_ids:
            continue
        summary.append(
            {
                "status": status,
                "count": len(run_ids),
                "runs": "; ".join(run_ids),
            }
        )
    for status in sorted(set(grouped) - set(order)):
        run_ids = [run_id for run_id in grouped.get(status, []) if run_id]
        summary.append({"status": status, "count": len(run_ids), "runs": "; ".join(run_ids)})
    return summary


def _final_report_status(final: dict[str, Any], discharge: dict[str, Any], included: Any) -> str:
    human_decision = str(final.get("human_decision") or final.get("human_decision_type") or "").casefold()
    if _truthy(included):
        return "Included by override" if human_decision else "Included"
    if human_decision:
        return "Excluded by override"
    state = str(discharge.get("state") or final.get("machine_state") or final.get("acceptance_state") or "").casefold()
    if state == "review_required":
        return "Excluded"
    if state == "excluded":
        return "Excluded"
    return "Not included"


def _decision_evidence_category(flag: dict[str, Any]) -> str:
    if _is_failure_observation_flag(flag):
        return "failure observation"
    return str(flag.get("category") or flag.get("source") or "")


def _decision_reason(final: dict[str, Any], discharge: dict[str, Any], primary: dict[str, Any], *, final_status: str = "") -> str:
    explicit = final.get("reason")
    if explicit:
        return str(explicit)
    if _is_failure_observation_flag(primary):
        value = primary.get("value")
        if value not in (None, ""):
            return "Operator failure metadata records a failure flag; the run is not used in the final report run set."
        return "Operator failure metadata marks the run as not usable in the final report run set."
    reason = str(discharge.get("primary_reason") or primary.get("message") or "")
    if reason:
        return reason
    if final_status == "Included":
        return "Accepted by automated checks; no exclusion trigger recorded."
    if final_status == "Excluded":
        return "Excluded by recorded acceptance evidence."
    return ""


def _reviewer_override(final: dict[str, Any]) -> str:
    override = final.get("human_decision") or final.get("human_decision_type")
    reason = final.get("override_reason") or final.get("human_decision_reason")
    if override and reason:
        return f"{override}: {reason}"
    if override:
        return str(override)
    return "None"


def _is_failure_observation_flag(flag: dict[str, Any]) -> bool:
    rule = str(flag.get("rule_id") or flag.get("flag_id") or "")
    refs = " ".join(str(ref) for ref in flag.get("evidence_refs", []) if ref) if isinstance(flag.get("evidence_refs"), list) else ""
    return "user_validity_invalid" in rule or "failure_mode" in refs


def _final_report_run_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    specimen_by_run = {
        str(row.get("run_id") or ""): row
        for row in result.specimen_results or []
        if isinstance(row, dict)
    }
    rows = []
    for row in result.final_report_runs or []:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        specimen = specimen_by_run.get(run_id, {})
        override = row.get("human_decision") or row.get("human_decision_type") or row.get("override_reason") or row.get("human_decision_reason") or ""
        rows.append(
            {
                "run_id": run_id,
                "specimen": row.get("specimen_name") or specimen.get("specimen_name") or specimen.get("specimen") or "",
                "machine_state": row.get("machine_state") or row.get("acceptance_state") or "",
                "override": override,
                "final_inclusion": _final_report_use(row.get("final_included", row.get("included"))),
            }
        )
    return rows


def _final_report_use(value: Any) -> str:
    if str(value).strip().casefold() in {"1", "true", "yes", "included"}:
        return "Included"
    if str(value).strip().casefold() in {"0", "false", "no", "excluded"}:
        return "Not included"
    return str(value or "")


def _evidence_anchor(flag: dict[str, Any]) -> str:
    run_id = str(flag.get("run_id") or "")
    category = str(flag.get("category") or flag.get("source") or "").casefold()
    if "curve_shape" in category or "curve_family" in category:
        return f"#{run_id}:run_curve_shape_diagnostic"
    if "bending" in category:
        return f"#{run_id}:run_bending_evidence"
    if "validation" in category:
        return f"#{run_id}:run_validation_evidence"
    if "statistical" in category:
        return "#aggregate:aggregate_evidence_summary"
    return f"#{run_id}:run_identity_and_status" if run_id else "#aggregate:aggregate_evidence_summary"


def _evidence_link(flag: dict[str, Any], run_id: str) -> dict[str, str]:
    href = _evidence_anchor(flag) if flag else f"#packet-{run_id}"
    label = f"{run_display_label(run_id)} evidence" if run_id else "aggregate evidence"
    category = str(flag.get("category") or flag.get("source") or "").casefold() if flag else ""
    if "bending" in category:
        label = f"{run_display_label(run_id)} bending evidence"
    elif "curve_shape" in category or "curve_family" in category:
        label = f"{run_display_label(run_id)} curve-shape evidence"
    elif "validation" in category:
        label = f"{run_display_label(run_id)} validation evidence"
    elif run_id and not flag:
        label = f"{run_display_label(run_id)} run packet"
    return {"href": href, "label": label}


def _artifact_links_section(payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_artifact_links_section(payload)
    return render_audit_artifact_links(_audit_artifact_links_context(payload))


def _legacy_artifact_links_section(payload: dict[str, Any]) -> str:
    links = payload.get("artifact_links") if isinstance(payload.get("artifact_links"), dict) else {}
    rows = [
        {"Artifact": "Test Report", "Location": links.get("test_report")},
        {"Artifact": "Method Development Workbench", "Location": links.get("method_development_workbench")},
    ]
    return (
        "<section id=\"artifact_links\">"
        "<h2>Artifact Links</h2>"
        f"{_table(rows)}"
        "</section>"
    )


def _audit_artifact_links_context(payload: dict[str, Any]) -> AuditArtifactLinksContext:
    links = payload.get("artifact_links") if isinstance(payload.get("artifact_links"), dict) else {}
    rows = [
        {"Artifact": "Test Report", "Location": links.get("test_report")},
        {"Artifact": "Method Development Workbench", "Location": links.get("method_development_workbench")},
    ]
    return AuditArtifactLinksContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_ARTIFACT_LINKS,
        section_heading_html=_audit_body_heading(Markup("Artifact Links"), heading_level=2),
        table_html=Markup(_table(rows)),
    )


def _technical_appendix(process_sections: str, evidence_sections: str) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_technical_appendix(process_sections, evidence_sections)
    return render_audit_technical_appendix(
        _audit_technical_appendix_context(process_sections, evidence_sections)
    )


def _legacy_technical_appendix(process_sections: str, evidence_sections: str) -> str:
    return (
        "<section id=\"artifact_links_technical_appendix\">"
        "<h2>Artifact Links / Technical Appendix</h2>"
        f"{_legacy_technical_appendix_purpose()}"
        "<details class=\"audit-details technical-trace\">"
        "<summary>Legacy process-verification appendix</summary>"
        f"<div>{process_sections}</div></details>"
        "<details class=\"audit-details technical-trace\">"
        "<summary>Operation evidence appendices</summary>"
        f"<div>{evidence_sections}</div></details>"
        "</section>"
    )


def _audit_technical_appendix_context(process_sections: str, evidence_sections: str) -> AuditTechnicalAppendixContext:
    process_sections_html = Markup(process_sections)
    evidence_sections_html = Markup(evidence_sections)
    return AuditTechnicalAppendixContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
        section_heading_html=_audit_body_heading(Markup("Artifact Links / Technical Appendix"), heading_level=2),
        purpose_html=Markup(_technical_appendix_purpose()),
        process_sections_html=process_sections_html,
        evidence_sections_html=evidence_sections_html,
        process_detail_html=_audit_body_details(
            title_html=Markup("Legacy process-verification appendix"),
            body_html=process_sections_html,
            detail_class="audit-details technical-trace",
        ),
        evidence_detail_html=_audit_body_details(
            title_html=Markup("Operation evidence appendices"),
            body_html=evidence_sections_html,
            detail_class="audit-details technical-trace",
        ),
    )


def _grouped_audit_sections(block_index: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_grouped_audit_sections(block_index)
    context = _audit_grouped_sections_context(block_index)
    return "" if context is None else render_audit_grouped_sections(context)


def _legacy_grouped_audit_sections(block_index: dict[str, Any]) -> str:
    if not isinstance(block_index, dict) or not block_index:
        return ""
    overview = block_index.get("audit_overview", {}) if isinstance(block_index.get("audit_overview"), dict) else {}
    run_packets = [packet for packet in block_index.get("run_packets", []) if isinstance(packet, dict)]
    aggregate_packet = block_index.get("aggregate_packet", {}) if isinstance(block_index.get("aggregate_packet"), dict) else {}
    html_parts: list[str] = [
        "<section id=\"procedure_derived_audit_blocks\">",
        "<h2>Audit overview</h2>",
        _legacy_grouped_sections_intro(),
    ]
    if overview:
        html_parts.append(_legacy_block_card(overview, include_operations=False))
    html_parts.append("<h2>Per-run audit packets</h2>")
    for packet in run_packets:
        run_id = html.escape(str(packet.get("run_id") or "run"))
        html_parts.append(f"<h3><span class=\"packet-label\">Run-wise audit packet</span><br>{run_id}</h3>")
        for block in packet.get("blocks", []) or []:
            if isinstance(block, dict):
                html_parts.append(_legacy_block_card(block))
    html_parts.append("<h2>Aggregate audit packet</h2>")
    for block in aggregate_packet.get("blocks", []) or []:
        if isinstance(block, dict):
            html_parts.append(_legacy_block_card(block))
    html_parts.append("</section>")
    return "".join(html_parts)


def _audit_body_paragraph(body_html: Markup, *, paragraph_class: str = "") -> Markup:
    return Markup(
        render_report_paragraph_fragment(
            projection_plane=ProjectionPlane.AUDIT,
            body_html=body_html,
            paragraph_class=paragraph_class,
        )
    )


def _audit_body_heading(title_html: Markup, *, heading_level: int = 4) -> Markup:
    return Markup(
        render_report_heading_fragment(
            projection_plane=ProjectionPlane.AUDIT,
            title_html=title_html,
            heading_level=heading_level,
        )
    )


def _audit_grouped_packet_heading(run_id_html: Markup) -> Markup:
    return _audit_body_heading(
        Markup('<span class="packet-label">Run-wise audit packet</span><br>') + run_id_html,
        heading_level=3,
    )


def _audit_body_details(
    *,
    title_html: Markup,
    marker_html: Markup = Markup(""),
    purpose_html: Markup = Markup(""),
    body_html: Markup,
    detail_class: str = "audit-details",
    fragment_id_html: Markup = Markup(""),
    open_details: bool = False,
) -> Markup:
    return Markup(
        render_report_details_fragment(
            projection_plane=ProjectionPlane.AUDIT,
            title_html=title_html,
            marker_html=marker_html,
            purpose_html=purpose_html,
            body_html=body_html,
            wrapper_class=detail_class,
            fragment_id_html=fragment_id_html,
            open_details=open_details,
        )
    )


def _audit_grouped_sections_context(block_index: dict[str, Any]) -> AuditGroupedSectionsContext | None:
    if not isinstance(block_index, dict) or not block_index:
        return None
    overview = block_index.get("audit_overview", {}) if isinstance(block_index.get("audit_overview"), dict) else {}
    run_packets = [packet for packet in block_index.get("run_packets", []) if isinstance(packet, dict)]
    aggregate_packet = block_index.get("aggregate_packet", {}) if isinstance(block_index.get("aggregate_packet"), dict) else {}
    packet_contexts = []
    for packet in run_packets:
        blocks = tuple(
            _audit_block_card_context(block)
            for block in packet.get("blocks", []) or []
            if isinstance(block, dict)
        )
        packet_contexts.append(
            AuditGroupedRunPacketContext(
                run_id_html=Markup(html.escape(str(packet.get("run_id") or "run"))),
                packet_heading_html=_audit_grouped_packet_heading(
                    Markup(html.escape(str(packet.get("run_id") or "run")))
                ),
                blocks=blocks,
            )
        )
    aggregate_blocks = tuple(
        _audit_block_card_context(block)
        for block in aggregate_packet.get("blocks", []) or []
        if isinstance(block, dict)
    )
    return AuditGroupedSectionsContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_GROUPED_SECTIONS,
        overview_heading_html=_audit_body_heading(Markup("Audit overview"), heading_level=2),
        intro_html=Markup(_grouped_sections_intro()),
        overview=_audit_block_card_context(overview, include_operations=False) if overview else None,
        run_packets_heading_html=_audit_body_heading(Markup("Per-run audit packets"), heading_level=2),
        run_packets=tuple(packet_contexts),
        aggregate_heading_html=_audit_body_heading(Markup("Aggregate audit packet"), heading_level=2),
        aggregate_blocks=aggregate_blocks,
    )


def _block_card(block: dict[str, Any], *, include_operations: bool = True) -> str:
    return _legacy_block_card(block, include_operations=include_operations)


def _legacy_block_card(block: dict[str, Any], *, include_operations: bool = True) -> str:
    title = html.escape(str(block.get("title") or block.get("block_id") or "Audit block"))
    purpose = html.escape(str(block.get("purpose") or ""))
    status = html.escape(str(block.get("status") or "recorded"))
    block_id = html.escape(str(block.get("block_id") or title))
    pieces = [
        f"<details class=\"audit-details\" id=\"{block_id}\" open>",
        f"<summary>{title} <span class=\"muted\">{status}</span></summary>",
        f"<div><p class=\"audit-purpose\">{purpose}</p>",
    ]
    if include_operations:
        operations = block.get("operations", []) if isinstance(block.get("operations"), list) else []
        if operations:
            pieces.append(_table(operations))
        elif block.get("expected_operation_types"):
            pieces.append(
                "<p class=\"muted\">No operation rows were recorded for this block. "
                "The expected operation contract remains indexed for traceability.</p>"
            )
    validation_checks = block.get("validation_checks") if isinstance(block.get("validation_checks"), list) else []
    warnings = block.get("warnings") if isinstance(block.get("warnings"), list) else []
    flags = block.get("flags") if isinstance(block.get("flags"), list) else []
    selection = block.get("selection") if isinstance(block.get("selection"), dict) else {}
    if validation_checks:
        pieces.append("<h4>Validation checks</h4>")
        pieces.append(_table(validation_checks))
    if warnings:
        pieces.append("<h4>Warnings</h4>")
        pieces.append(_table(warnings))
    if selection:
        pieces.append("<h4>Report inclusion evidence</h4>")
        pieces.append(_table([selection]))
    if flags:
        pieces.append("<h4>Acceptance flags</h4>")
        pieces.append(_table(flags))
    aggregate_rows = _aggregate_block_rows(block)
    if aggregate_rows:
        pieces.append(_table(aggregate_rows))
    artifacts = block.get("artifact_refs") if isinstance(block.get("artifact_refs"), list) else []
    if artifacts:
        pieces.append("<h4>MTDA artifacts</h4>")
        pieces.append(_table([{"artifact": artifact} for artifact in artifacts]))
    pieces.append("</div></details>")
    return "".join(pieces)


def _audit_block_card_context(block: dict[str, Any], *, include_operations: bool = True) -> AuditBlockCardContext:
    title = html.escape(str(block.get("title") or block.get("block_id") or "Audit block"))
    purpose = html.escape(str(block.get("purpose") or ""))
    status = html.escape(str(block.get("status") or "recorded"))
    block_id = html.escape(str(block.get("block_id") or title))
    fragments: list[Markup] = []
    if include_operations:
        operations = block.get("operations", []) if isinstance(block.get("operations"), list) else []
        if operations:
            fragments.append(Markup(_table(operations)))
        elif block.get("expected_operation_types"):
            fragments.append(
                _audit_body_paragraph(
                    Markup(
                        "No operation rows were recorded for this block. "
                        "The expected operation contract remains indexed for traceability."
                    ),
                    paragraph_class="muted",
                )
            )
    validation_checks = block.get("validation_checks") if isinstance(block.get("validation_checks"), list) else []
    warnings = block.get("warnings") if isinstance(block.get("warnings"), list) else []
    flags = block.get("flags") if isinstance(block.get("flags"), list) else []
    selection = block.get("selection") if isinstance(block.get("selection"), dict) else {}
    if validation_checks:
        fragments.append(_audit_body_heading(Markup("Validation checks")))
        fragments.append(Markup(_table(validation_checks)))
    if warnings:
        fragments.append(_audit_body_heading(Markup("Warnings")))
        fragments.append(Markup(_table(warnings)))
    if selection:
        fragments.append(_audit_body_heading(Markup("Report inclusion evidence")))
        fragments.append(Markup(_table([selection])))
    if flags:
        fragments.append(_audit_body_heading(Markup("Acceptance flags")))
        fragments.append(Markup(_table(flags)))
    aggregate_rows = _aggregate_block_rows(block)
    if aggregate_rows:
        fragments.append(Markup(_table(aggregate_rows)))
    artifacts = block.get("artifact_refs") if isinstance(block.get("artifact_refs"), list) else []
    if artifacts:
        fragments.append(_audit_body_heading(Markup("MTDA artifacts")))
        fragments.append(Markup(_table([{"artifact": artifact} for artifact in artifacts])))
    purpose_html = _audit_body_paragraph(Markup(purpose), paragraph_class="audit-purpose")
    body_html = Markup("").join(fragments)
    marker_html = Markup(f' <span class="muted">{status}</span>')
    return AuditBlockCardContext(
        block_id_html=Markup(block_id),
        title_html=Markup(title),
        status_html=Markup(status),
        purpose_html=purpose_html,
        fragments=tuple(fragments),
        card_html=_audit_body_details(
            title_html=Markup(title),
            marker_html=marker_html,
            purpose_html=purpose_html,
            body_html=body_html,
            detail_class="audit-details",
            fragment_id_html=Markup(block_id),
            open_details=True,
        ),
    )


def _aggregate_block_rows(block: dict[str, Any]) -> list[dict[str, Any]]:
    scope = str(block.get("scope") or "")
    if scope != "aggregate":
        return []
    keys = [
        "selected_run_ids",
        "boundary_aligned_aggregation",
        "curve_family_flag_count",
        "human_decision_count",
        "report_override_count",
    ]
    rows = []
    for key in keys:
        if key in block:
            rows.append({"item": key, "value": block.get(key)})
    return rows


def _process_summary_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "Stage": "Source data",
            "State": _basename(_nested_text(payload, "source_mtdp", "path")) or "recorded",
            "Meaning": f"{_nested_text(payload, 'source_mtdp', 'run_count')} runs available for ISO 14126 assessment.",
            "Evidence": "Source acquisition package",
        },
        {
            "Stage": "Method",
            "State": _nested_text(payload, "method_package", "standard_reference") or _nested_text(payload, "method_package", "method_id"),
            "Meaning": _nested_text(payload, "method_package", "name"),
            "Evidence": "ISO 14126 reduction basis",
        },
        {
            "Stage": "Experiment boundary resolution",
            "State": _nested_text(payload, "experiment_boundary_resolution", "status"),
            "Meaning": _nested_text(payload, "experiment_boundary_resolution", "summary"),
            "Evidence": "Per-run start/end markers",
        },
        {
            "Stage": "Validation",
            "State": _nested_text(payload, "validation", "status"),
            "Meaning": f"{_nested_text(payload, 'validation', 'deviation_count')} deviations recorded for review.",
            "Evidence": "Validation and warning evidence",
        },
        {
            "Stage": "Curve-shape diagnostics",
            "State": f"{_nested_text(payload, 'curve_shape_diagnostic', 'score_count')} runs scored",
            "Meaning": "Whole comparable dataset curve-shape evidence.",
            "Evidence": "Curve-family diagnostic evidence",
        },
        {
            "Stage": "Report completion",
            "State": _nested_text(payload, "report_completion", "status"),
            "Meaning": f"{_nested_text(payload, 'report_completion', 'missing_field_count')} missing report fields; overrides: {_nested_text(payload, 'report_completion', 'override_count')}",
            "Evidence": "Formal report completeness",
        },
        {
            "Stage": "Warnings",
            "State": _nested_text(payload, "warnings", "count"),
            "Meaning": "Operator-relevant warnings are summarized in the relevant evidence blocks.",
            "Evidence": "Warnings and deviations",
        },
    ]


def _flatten(payload: Any, keys: tuple[str, ...] | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    selected = keys or tuple(str(key) for key in payload.keys())
    return {key: payload.get(key, "") for key in selected}


def _render_component(
    result: MethodRunResult,
    component: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_render_component(result, component, curve_rows, specs)
    context = _audit_component_context(result, component, curve_rows, specs)
    return _render_audit_component_context(context)


def _render_audit_component_context(
    context: AuditComponentContext
    | AuditOperationLogComponentContext
    | AuditInspectionLogComponentContext
    | AuditChartComponentContext,
) -> str:
    if isinstance(context, AuditComponentContext):
        return render_audit_component(context)
    if isinstance(context, AuditOperationLogComponentContext):
        return render_audit_operation_log_component(context)
    if isinstance(context, AuditInspectionLogComponentContext):
        return render_audit_inspection_log_component(context)
    if isinstance(context, AuditChartComponentContext):
        return render_audit_chart_component(context)
    raise TypeError(f"Unsupported audit component context: {type(context).__name__}")


def _audit_component_context(
    result: MethodRunResult,
    component: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> AuditComponentContext | AuditOperationLogComponentContext | AuditInspectionLogComponentContext | AuditChartComponentContext:
    component_type = str(component.get("type", ""))
    title_html = Markup(html.escape(str(component.get("title") or component.get("id") or component_type)))
    if component_type in {"table", "summary_table", "specimen_results_table"}:
        rows = _rows_for_source(result, str(component.get("source", "")), default="specimen_results")
        return _audit_component_fragment_context(title_html, Markup(_table(rows)))
    if component_type == "dataset_summary":
        return _audit_component_fragment_context(title_html, Markup(_table(result.dataset_summary)))
    if component_type == "readiness_summary":
        return _audit_component_fragment_context(title_html, Markup(_readiness_summary(result)))
    if component_type == "validation_summary":
        return _audit_component_fragment_context(title_html, Markup(_validation_summary(result)))
    if component_type == "validation_deviations":
        return _audit_component_fragment_context(title_html, Markup(_table(result.validation_deviations)))
    if component_type == "acceptance_summary":
        return _audit_component_fragment_context(title_html, Markup(_acceptance_summary(result)))
    if component_type == "selection_set_table":
        rows = result.selection_membership_final or result.selection_membership
        return _audit_component_fragment_context(title_html, Markup(_table(rows)))
    if component_type == "discharge_report":
        return _audit_component_fragment_context(title_html, Markup(_table(result.discharged_runs)))
    if component_type == "operation_log":
        rows = _operation_preview_rows(result.operation_log)
        summary_rows = _operation_summary_rows(result.operation_log)
        preview_rows = rows[:24]
        return AuditOperationLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT,
            title_html=title_html,
            purpose_html=Markup(_operation_log_appendix_purpose()),
            summary_table_html=Markup(_table(summary_rows)),
            preview_table_html=Markup(_table(preview_rows)),
            raw_evidence_note_html=Markup(_raw_evidence_details("Raw operation-log preview evidence", rows)),
        )
    if component_type == "inspection_log":
        raw_rows = result.inspections or []
        summary_rows = _inspection_summary_rows(raw_rows)
        rows = _inspection_preview_rows(raw_rows)
        return AuditInspectionLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT,
            title_html=title_html,
            purpose_html=Markup(_inspection_log_appendix_purpose()),
            summary_table_html=Markup(_table(summary_rows)),
            preview_table_html=Markup(_table(rows[:24])),
            raw_evidence_note_html=Markup(_raw_evidence_details("Raw inspection preview evidence", rows)),
        )
    if component_type == "curve_family_plot":
        chart_id = _safe_id(str(component.get("id", "stress_strain_family")))
        specs[chart_id] = stress_strain_family_spec(
            curve_rows,
            x_field=str(component.get("x") or "strain_mm_per_mm"),
            y_field=str(component.get("y") or "stress_MPa"),
            group_field=str(component.get("group") or "run_id"),
        )
        return _audit_chart_component_context(
            title_html=title_html,
            chart_id=chart_id,
            chart_hint_html=Markup(_chart_hint()),
        )
    if component_type == "operation_overlay":
        operation_type = str(component.get("operation_type", ""))
        chart_id = _safe_id(str(component.get("id") or operation_type or "operation_overlay"))
        if operation_type == "chord_slope":
            specs[chart_id] = modulus_window_spec(curve_rows)
            return _audit_chart_component_context(
                title_html=title_html,
                chart_id=chart_id,
                after_chart_html=Markup(
                    _chord_endpoint_note()
                ),
            )
        if operation_type == "bending_diagnostic":
            threshold = _first_numeric(result.specimen_results, "bending_threshold_percent", 10.0)
            specs[chart_id] = bending_spec(curve_rows, threshold_percent=threshold)
            pattern_rows = [
                {
                    "run_id": row.get("run_id"),
                    "pattern": row.get("bending_pattern"),
                    "confidence": row.get("bending_pattern_confidence"),
                    "points_above_threshold": row.get("bending_points_above_threshold"),
                    "fraction_above_threshold": row.get("bending_fraction_above_threshold"),
                    "p95_percent": row.get("bending_p95_percent"),
                    "reason": row.get("bending_pattern_reason"),
                }
                for row in result.specimen_results
            ]
            return _audit_chart_component_context(
                title_html=title_html,
                chart_id=chart_id,
                chart_hint_html=Markup(_chart_hint()),
                after_chart_html=Markup(_bending_pattern_heading() + _table(pattern_rows)),
            )
        rows = _operation_preview_rows([row for row in result.operation_log if row.get("operation_type") == operation_type])
        return _audit_component_fragment_context(title_html, Markup(_table(rows)))
    return _audit_component_fragment_context(
        title_html,
        Markup(_unsupported_component_note(component_type)),
    )


def _audit_component_fragment_context(title_html: Markup, body_html: Markup) -> AuditComponentContext:
    return AuditComponentContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT,
        title_html=title_html,
        body_html=body_html,
    )


def _audit_chart_component_context(
    *,
    title_html: Markup,
    chart_id: str,
    chart_hint_html: Markup = Markup(""),
    after_chart_html: Markup = Markup(""),
) -> AuditChartComponentContext:
    return AuditChartComponentContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_CHART_COMPONENT,
        title_html=title_html,
        chart_id_html=Markup(html.escape(chart_id)),
        chart_hint_html=chart_hint_html,
        after_chart_html=after_chart_html,
    )


def _legacy_render_component(
    result: MethodRunResult,
    component: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> str:
    component_type = str(component.get("type", ""))
    title = html.escape(str(component.get("title") or component.get("id") or component_type))
    if component_type in {"table", "summary_table", "specimen_results_table"}:
        rows = _rows_for_source(result, str(component.get("source", "")), default="specimen_results")
        return f"<h3>{title}</h3>{_legacy_table(rows)}"
    if component_type == "dataset_summary":
        return f"<h3>{title}</h3>{_legacy_table(result.dataset_summary)}"
    if component_type == "readiness_summary":
        return f"<h3>{title}</h3>{_legacy_readiness_summary(result)}"
    if component_type == "validation_summary":
        return f"<h3>{title}</h3>{_legacy_validation_summary(result)}"
    if component_type == "validation_deviations":
        return f"<h3>{title}</h3>{_legacy_table(result.validation_deviations)}"
    if component_type == "acceptance_summary":
        return f"<h3>{title}</h3>{_legacy_acceptance_summary(result)}"
    if component_type == "selection_set_table":
        rows = result.selection_membership_final or result.selection_membership
        return f"<h3>{title}</h3>{_legacy_table(rows)}"
    if component_type == "discharge_report":
        return f"<h3>{title}</h3>{_legacy_table(result.discharged_runs)}"
    if component_type == "curve_family_plot":
        chart_id = _safe_id(str(component.get("id", "stress_strain_family")))
        specs[chart_id] = stress_strain_family_spec(
            curve_rows,
            x_field=str(component.get("x") or "strain_mm_per_mm"),
            y_field=str(component.get("y") or "stress_MPa"),
            group_field=str(component.get("group") or "run_id"),
        )
        return f"<h3>{title}</h3>{_legacy_chart_hint()}<div id=\"{chart_id}\" class=\"chart\"></div>"
    if component_type == "operation_log":
        rows = _operation_preview_rows(result.operation_log)
        summary_rows = _operation_summary_rows(result.operation_log)
        preview_rows = rows[:24]
        return (
            f"<h3>{title}</h3>"
            f"{_legacy_operation_log_appendix_purpose()}"
            f"{_legacy_table(summary_rows)}"
            f"{_legacy_table(preview_rows)}"
            f"{_legacy_raw_evidence_details('Raw operation-log preview evidence', rows)}"
        )
    if component_type == "inspection_log":
        raw_rows = result.inspections or []
        summary_rows = _inspection_summary_rows(raw_rows)
        rows = _inspection_preview_rows(raw_rows)
        return (
            f"<h3>{title}</h3>"
            f"{_legacy_inspection_log_appendix_purpose()}"
            f"{_legacy_table(summary_rows)}"
            f"{_legacy_table(rows[:24])}"
            f"{_legacy_raw_evidence_details('Raw inspection preview evidence', rows)}"
        )
    if component_type == "operation_overlay":
        operation_type = str(component.get("operation_type", ""))
        chart_id = _safe_id(str(component.get("id") or operation_type or "operation_overlay"))
        if operation_type == "chord_slope":
            specs[chart_id] = modulus_window_spec(curve_rows)
            return f"<h3>{title}</h3><div id=\"{chart_id}\" class=\"chart\"></div>{_legacy_chord_endpoint_note()}"
        if operation_type == "bending_diagnostic":
            threshold = _first_numeric(result.specimen_results, "bending_threshold_percent", 10.0)
            specs[chart_id] = bending_spec(curve_rows, threshold_percent=threshold)
            pattern_rows = [
                {
                    "run_id": row.get("run_id"),
                    "pattern": row.get("bending_pattern"),
                    "confidence": row.get("bending_pattern_confidence"),
                    "points_above_threshold": row.get("bending_points_above_threshold"),
                    "fraction_above_threshold": row.get("bending_fraction_above_threshold"),
                    "p95_percent": row.get("bending_p95_percent"),
                    "reason": row.get("bending_pattern_reason"),
                }
                for row in result.specimen_results
            ]
            return (
                f"<h3>{title}</h3>{_legacy_chart_hint()}<div id=\"{chart_id}\" class=\"chart\"></div>"
                f"{_legacy_bending_pattern_heading()}{_legacy_table(pattern_rows)}"
            )
        rows = _operation_preview_rows([row for row in result.operation_log if row.get("operation_type") == operation_type])
        return f"<h3>{title}</h3>{_legacy_table(rows)}"
    return f"<h3>{title}</h3>{_legacy_unsupported_component_note(component_type)}"


def _chart_hint() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_chart_hint()
    return _render_audit_component_microcopy("chart_hint")


def _legacy_chart_hint() -> str:
    return (
        "<p class=\"chart-hint\">Hover for a compact value tooltip. "
        "Click run names in the legend to focus a curve; shift-click to build a multi-run focus set. "
        "Double-click the chart area to reset.</p>"
    )


def _chord_endpoint_note() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_chord_endpoint_note()
    return _render_audit_component_microcopy("chord_endpoint_note")


def _legacy_chord_endpoint_note() -> str:
    return "<p>Chord endpoints: <code>0.0005</code> and <code>0.0025</code> strain.</p>"


def _bending_pattern_heading() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_bending_pattern_heading()
    return _render_audit_component_microcopy("bending_pattern_heading")


def _legacy_bending_pattern_heading() -> str:
    return "<h4>Bending Pattern Interpretation</h4>"


def _operation_log_appendix_purpose() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_operation_log_appendix_purpose()
    return _render_audit_component_microcopy("operation_log_appendix_purpose")


def _legacy_operation_log_appendix_purpose() -> str:
    return (
        "<p class=\"audit-purpose\"><strong>Appendix detail.</strong> "
        "Operation-level replay belongs in the Workbench. "
        "This audit appendix summarizes operation status and shows a bounded preview.</p>"
    )


def _inspection_log_appendix_purpose() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_inspection_log_appendix_purpose()
    return _render_audit_component_microcopy("inspection_log_appendix_purpose")


def _legacy_inspection_log_appendix_purpose() -> str:
    return (
        "<p class=\"audit-purpose\"><strong>Appendix detail.</strong> "
        "Full inspection records remain in the MTDA and Workbench; "
        "this section shows a bounded review preview.</p>"
    )


def _process_section_evidence_purpose() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_process_section_evidence_purpose()
    return _render_audit_component_microcopy("process_section_evidence_purpose")


def _legacy_process_section_evidence_purpose() -> str:
    return (
        "<p class=\"audit-purpose\"><strong>Audit evidence.</strong> "
        "These fields verify this process stage. Use the Workbench for operation-level replay.</p>"
    )


def _technical_appendix_purpose() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_technical_appendix_purpose()
    return _render_audit_component_microcopy("technical_appendix_purpose")


def _legacy_technical_appendix_purpose() -> str:
    return (
        "<p class=\"audit-purpose\">Legacy process-verification and operation-by-operation appendices are preserved "
        "here for traceability without dominating the human audit read.</p>"
    )


def _grouped_sections_intro() -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_grouped_sections_intro()
    return _render_audit_component_microcopy("grouped_sections_intro")


def _legacy_grouped_sections_intro() -> str:
    return (
        "<p>This section groups operation evidence into review packets. "
        "Operation evidence is stored once in the operation log and indexed through "
        "<code>audit/procedure_evidence_index.json</code>; detailed operation replay stays in the "
        "Method Development Workbench.</p>"
    )


def _unsupported_component_note(component_type: str) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_unsupported_component_note(component_type)
    return _render_audit_component_microcopy(
        "unsupported_component_note",
        component_type_html=Markup(html.escape(component_type)),
    )


def _legacy_unsupported_component_note(component_type: str) -> str:
    return f"<p>Unsupported audit component: {html.escape(component_type)}</p>"


def _render_audit_component_microcopy(
    microcopy_kind: str,
    *,
    component_type_html: Markup = Markup(""),
) -> str:
    return render_audit_component_microcopy(
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            microcopy_kind=microcopy_kind,
            component_type_html=component_type_html,
            body_html=_audit_component_microcopy_html(
                microcopy_kind,
                component_type_html=component_type_html,
            ),
        )
    )


def _audit_component_microcopy_html(
    microcopy_kind: str,
    *,
    component_type_html: Markup = Markup(""),
) -> Markup:
    if microcopy_kind == "chart_hint":
        return _audit_body_paragraph(
            Markup(
                "Hover for a compact value tooltip. "
                "Click run names in the legend to focus a curve; shift-click to build a multi-run focus set. "
                "Double-click the chart area to reset."
            ),
            paragraph_class="chart-hint",
        )
    if microcopy_kind == "chord_endpoint_note":
        return _audit_body_paragraph(
            Markup("Chord endpoints: <code>0.0005</code> and <code>0.0025</code> strain.")
        )
    if microcopy_kind == "bending_pattern_heading":
        return _audit_body_heading(Markup("Bending Pattern Interpretation"))
    if microcopy_kind == "operation_log_appendix_purpose":
        return _audit_body_paragraph(
            Markup(
                "<strong>Appendix detail.</strong> "
                "Operation-level replay belongs in the Workbench. "
                "This audit appendix summarizes operation status and shows a bounded preview."
            ),
            paragraph_class="audit-purpose",
        )
    if microcopy_kind == "inspection_log_appendix_purpose":
        return _audit_body_paragraph(
            Markup(
                "<strong>Appendix detail.</strong> "
                "Full inspection records remain in the MTDA and Workbench; "
                "this section shows a bounded review preview."
            ),
            paragraph_class="audit-purpose",
        )
    if microcopy_kind == "process_section_evidence_purpose":
        return _audit_body_paragraph(
            Markup(
                "<strong>Audit evidence.</strong> "
                "These fields verify this process stage. Use the Workbench for operation-level replay."
            ),
            paragraph_class="audit-purpose",
        )
    if microcopy_kind == "technical_appendix_purpose":
        return _audit_body_paragraph(
            Markup(
                "Legacy process-verification and operation-by-operation appendices are preserved "
                "here for traceability without dominating the human audit read."
            ),
            paragraph_class="audit-purpose",
        )
    if microcopy_kind == "grouped_sections_intro":
        return _audit_body_paragraph(
            Markup(
                "This section groups operation evidence into review packets. "
                "Operation evidence is stored once in the operation log and indexed through "
                "<code>audit/procedure_evidence_index.json</code>; detailed operation replay stays in the "
                "Method Development Workbench."
            )
        )
    return _audit_body_paragraph(Markup("Unsupported audit component: ") + component_type_html)


def _rows_for_source(result: MethodRunResult, source: str, *, default: str) -> list[dict[str, Any]]:
    if source.endswith("dataset_summary.csv") or default == "dataset_summary":
        return result.dataset_summary
    if source.endswith("operation_log.json"):
        return result.operation_log
    if source.endswith("inspections.json"):
        return result.inspections
    if source.endswith("validation_summary.csv"):
        return result.validation_summary
    if source.endswith("deviations.csv"):
        return result.validation_deviations
    if source.endswith("dataset_summary_by_selection.csv"):
        return result.dataset_summary_by_selection
    if source.endswith("readiness_summary.csv"):
        return result.readiness_summary
    if source.endswith("resolved_inputs.csv"):
        return result.resolved_inputs
    if source.endswith("missing_inputs.csv"):
        return result.missing_inputs
    if source.endswith("acceptance_summary.csv"):
        return result.acceptance_summary
    if source.endswith("run_flags.csv"):
        return result.run_flags
    if source.endswith("selection_membership.csv"):
        return result.selection_membership
    if source.endswith("selection_membership_final.csv"):
        return result.selection_membership_final or []
    if source.endswith("final_report_runs.csv"):
        return result.final_report_runs or []
    if source.endswith("human_decisions.csv"):
        return result.human_decision_rows or []
    if source.endswith("discharged_runs.csv"):
        return result.discharged_runs
    return result.specimen_results


def _validation_summary(result: MethodRunResult) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_validation_summary(result)
    return render_audit_validation_summary(_audit_validation_summary_context(result))


def _legacy_validation_summary(result: MethodRunResult) -> str:
    if not result.validation_report.get("checks"):
        return "<p>No reference validation checks were executed.</p>"
    summary = result.validation_report.get("summary", {})
    status = html.escape(str(summary.get("status", "unknown")))
    deviations = result.validation_deviations[:12]
    return (
        f"<p>Validation status: <span class=\"status-{status}\">{status.upper()}</span>. "
        f"Checks: {html.escape(str(summary.get('total_checks', 0)))}; "
        f"passed: {html.escape(str(summary.get('passed', 0)))}; "
        f"warnings: {html.escape(str(summary.get('warnings', 0)))}; "
        f"failed: {html.escape(str(summary.get('failed', 0)))}.</p>"
        "<p>Deep inspection entry point: <code>tools/run_method_development.py</code>.</p>"
        f"{_legacy_table(deviations)}"
    )


def _audit_validation_summary_context(result: MethodRunResult) -> AuditValidationSummaryContext:
    checks = result.validation_report.get("checks")
    summary = result.validation_report.get("summary", {})
    status = html.escape(str(summary.get("status", "unknown")))
    status_class = f"status-{status}"
    status_html = Markup(status.upper())
    checks_html = Markup(html.escape(str(summary.get("total_checks", 0))))
    passed_html = Markup(html.escape(str(summary.get("passed", 0))))
    warnings_html = Markup(html.escape(str(summary.get("warnings", 0))))
    failed_html = Markup(html.escape(str(summary.get("failed", 0))))
    if checks:
        summary_html = _audit_body_paragraph(
            Markup('Validation status: <span class="')
            + Markup(status_class)
            + Markup('">')
            + status_html
            + Markup("</span>. Checks: ")
            + checks_html
            + Markup("; passed: ")
            + passed_html
            + Markup("; warnings: ")
            + warnings_html
            + Markup("; failed: ")
            + failed_html
            + Markup(".")
        ) + _audit_body_paragraph(Markup("Deep inspection entry point: <code>tools/run_method_development.py</code>."))
    else:
        summary_html = _audit_body_paragraph(Markup("No reference validation checks were executed."))
    return AuditValidationSummaryContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
        summary_html=summary_html,
        has_checks=bool(checks),
        status_html=status_html,
        status_class=status_class,
        checks_html=checks_html,
        passed_html=passed_html,
        warnings_html=warnings_html,
        failed_html=failed_html,
        deviations_table_html=Markup(_table(result.validation_deviations[:12])),
    )


def _readiness_summary(result: MethodRunResult) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_readiness_summary(result)
    return render_audit_readiness_summary(_audit_readiness_summary_context(result))


def _legacy_readiness_summary(result: MethodRunResult) -> str:
    summary = result.readiness_report.get("summary", {})
    status = html.escape(str(result.readiness_report.get("status", "UNKNOWN")))
    status_class = "status-pass" if status == "READY" else "status-warn" if status == "READY_WITH_WARNINGS" else "status-fail"
    missing_rows = result.missing_inputs[:12]
    return (
        f"<p>Readiness status: <span class=\"{status_class}\">{status}</span>. "
        f"Execution-critical passed: {html.escape(str(summary.get('execution_critical_passed', 0)))} / "
        f"{html.escape(str(summary.get('execution_critical_total', 0)))}; "
        f"missing inputs: {html.escape(str(summary.get('missing_total', 0)))}; "
        f"blocks execution: {html.escape(str(result.readiness_report.get('blocks_execution', False)))}.</p>"
        f"{_legacy_table(result.readiness_summary)}"
        f"<h4>Missing or Warning Inputs</h4>{_legacy_table(missing_rows)}"
    )


def _audit_readiness_summary_context(result: MethodRunResult) -> AuditReadinessSummaryContext:
    summary = result.readiness_report.get("summary", {})
    status = html.escape(str(result.readiness_report.get("status", "UNKNOWN")))
    status_class = "status-pass" if status == "READY" else "status-warn" if status == "READY_WITH_WARNINGS" else "status-fail"
    status_html = Markup(status)
    execution_critical_passed_html = Markup(html.escape(str(summary.get("execution_critical_passed", 0))))
    execution_critical_total_html = Markup(html.escape(str(summary.get("execution_critical_total", 0))))
    missing_total_html = Markup(html.escape(str(summary.get("missing_total", 0))))
    blocks_execution_html = Markup(html.escape(str(result.readiness_report.get("blocks_execution", False))))
    summary_html = _audit_body_paragraph(
        Markup('Readiness status: <span class="')
        + Markup(status_class)
        + Markup('">')
        + status_html
        + Markup("</span>. Execution-critical passed: ")
        + execution_critical_passed_html
        + Markup(" / ")
        + execution_critical_total_html
        + Markup("; missing inputs: ")
        + missing_total_html
        + Markup("; blocks execution: ")
        + blocks_execution_html
        + Markup(".")
    )
    return AuditReadinessSummaryContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_READINESS_SUMMARY,
        summary_html=summary_html,
        status_html=status_html,
        status_class=status_class,
        execution_critical_passed_html=execution_critical_passed_html,
        execution_critical_total_html=execution_critical_total_html,
        missing_total_html=missing_total_html,
        blocks_execution_html=blocks_execution_html,
        readiness_table_html=Markup(_table(result.readiness_summary)),
        missing_inputs_heading_html=_audit_body_heading(Markup("Missing or Warning Inputs")),
        missing_inputs_table_html=Markup(_table(result.missing_inputs[:12])),
    )


def _acceptance_summary(result: MethodRunResult) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_acceptance_summary(result)
    return render_audit_acceptance_summary(_audit_acceptance_summary_context(result))


def _legacy_acceptance_summary(result: MethodRunResult) -> str:
    summary = result.acceptance_report.get("summary", {})
    default_selection = html.escape(str(summary.get("default_selection_set") or result.acceptance_report.get("default_selection_set") or ""))
    final_sets = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
    final_selection = html.escape(str(final_sets.get("default_selection_set") or ""))
    selection_source = html.escape(str(final_sets.get("selection_source") or "machine_acceptance"))
    final_rows = result.final_report_runs or []
    final_included = sum(1 for row in final_rows if _truthy(row.get("final_included", row.get("included"))))
    human_decisions = result.human_decision_rows or []
    curve_summary = {}
    if isinstance(result.curve_family_assessment, dict):
        curve_summary = result.curve_family_assessment.get("summary", {})
        curve_summary = curve_summary if isinstance(curve_summary, dict) else {}
    return (
        f"<p>Default selection set: <code>{default_selection}</code>. "
        f"Runs: {html.escape(str(summary.get('total_runs', 0)))}; "
        f"accepted: {html.escape(str(summary.get('accepted', 0)))}; "
        f"warnings: {html.escape(str(summary.get('accepted_with_warning', 0)))}; "
        f"review: {html.escape(str(summary.get('review_required', 0)))}; "
        f"excluded: {html.escape(str(summary.get('excluded', 0)))}; "
        f"flags: {html.escape(str(summary.get('total_flags', 0)))}.</p>"
        f"<p>Final report selection: <code>{final_selection}</code>; "
        f"selection source: <code>{selection_source}</code>; "
        f"final included runs: {html.escape(str(final_included))}; "
        f"human decisions recorded: {html.escape(str(len(human_decisions)))}.</p>"
        "<p>Deep inspection entry point: <code>tools/run_method_development.py</code>.</p>"
        f"{_legacy_table(result.acceptance_summary)}"
        "<h4>Curve-Family Assessment</h4>"
        f"{_legacy_table([curve_summary] if curve_summary else [])}"
        f"{_legacy_table((result.curve_family_scores or [])[:20])}"
        "<h4>Final Report Runs</h4>"
        f"{_legacy_table(final_rows[:20])}"
        "<h4>Human Override Ledger</h4>"
        f"{_legacy_table(result.override_ledger_rows or [])}"
    )


def _audit_acceptance_summary_context(result: MethodRunResult) -> AuditAcceptanceSummaryContext:
    summary = result.acceptance_report.get("summary", {})
    final_sets = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
    final_rows = result.final_report_runs or []
    final_included = sum(1 for row in final_rows if _truthy(row.get("final_included", row.get("included"))))
    human_decisions = result.human_decision_rows or []
    curve_summary = {}
    if isinstance(result.curve_family_assessment, dict):
        curve_summary = result.curve_family_assessment.get("summary", {})
        curve_summary = curve_summary if isinstance(curve_summary, dict) else {}
    default_selection_html = Markup(
        html.escape(str(summary.get("default_selection_set") or result.acceptance_report.get("default_selection_set") or ""))
    )
    total_runs_html = Markup(html.escape(str(summary.get("total_runs", 0))))
    accepted_html = Markup(html.escape(str(summary.get("accepted", 0))))
    accepted_with_warning_html = Markup(html.escape(str(summary.get("accepted_with_warning", 0))))
    review_required_html = Markup(html.escape(str(summary.get("review_required", 0))))
    excluded_html = Markup(html.escape(str(summary.get("excluded", 0))))
    total_flags_html = Markup(html.escape(str(summary.get("total_flags", 0))))
    final_selection_html = Markup(html.escape(str(final_sets.get("default_selection_set") or "")))
    selection_source_html = Markup(html.escape(str(final_sets.get("selection_source") or "machine_acceptance")))
    final_included_html = Markup(html.escape(str(final_included)))
    human_decisions_html = Markup(html.escape(str(len(human_decisions))))
    summary_html = (
        _audit_body_paragraph(
            Markup("Default selection set: <code>")
            + default_selection_html
            + Markup("</code>. Runs: ")
            + total_runs_html
            + Markup("; accepted: ")
            + accepted_html
            + Markup("; warnings: ")
            + accepted_with_warning_html
            + Markup("; review: ")
            + review_required_html
            + Markup("; excluded: ")
            + excluded_html
            + Markup("; flags: ")
            + total_flags_html
            + Markup(".")
        )
        + _audit_body_paragraph(
            Markup("Final report selection: <code>")
            + final_selection_html
            + Markup("</code>; selection source: <code>")
            + selection_source_html
            + Markup("</code>; final included runs: ")
            + final_included_html
            + Markup("; human decisions recorded: ")
            + human_decisions_html
            + Markup(".")
        )
        + _audit_body_paragraph(Markup("Deep inspection entry point: <code>tools/run_method_development.py</code>."))
    )
    return AuditAcceptanceSummaryContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY,
        summary_html=summary_html,
        default_selection_html=default_selection_html,
        total_runs_html=total_runs_html,
        accepted_html=accepted_html,
        accepted_with_warning_html=accepted_with_warning_html,
        review_required_html=review_required_html,
        excluded_html=excluded_html,
        total_flags_html=total_flags_html,
        final_selection_html=final_selection_html,
        selection_source_html=selection_source_html,
        final_included_html=final_included_html,
        human_decisions_html=human_decisions_html,
        acceptance_table_html=Markup(_table(result.acceptance_summary)),
        curve_summary_heading_html=_audit_body_heading(Markup("Curve-Family Assessment")),
        curve_summary_table_html=Markup(_table([curve_summary] if curve_summary else [])),
        curve_scores_table_html=Markup(_table((result.curve_family_scores or [])[:20])),
        final_runs_heading_html=_audit_body_heading(Markup("Final Report Runs")),
        final_runs_table_html=Markup(_table(final_rows[:20])),
        override_ledger_heading_html=_audit_body_heading(Markup("Human Override Ledger")),
        override_ledger_table_html=Markup(_table(result.override_ledger_rows or [])),
    )


def _compact_curve_rows(rows: list[dict[str, Any]], max_rows_per_run: int = 900) -> list[dict[str, Any]]:
    by_run: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_run.setdefault(str(row.get("run_id")), []).append(row)
    compacted: list[dict[str, Any]] = []
    for run_rows in by_run.values():
        if len(run_rows) <= max_rows_per_run:
            compacted.extend(run_rows)
            continue
        stride = max(1, len(run_rows) // max_rows_per_run)
        compacted.extend(run_rows[::stride])
    return compacted


def _table(rows: list[dict[str, Any]]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_table(rows)
    return render_audit_table(_audit_table_context(rows))


def _legacy_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    header = "".join(f"<th>{html.escape(_heading(str(name)))}</th>" for name in fieldnames)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_cell_html(row.get(name))}</td>" for name in fieldnames)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def _audit_table_context(rows: list[dict[str, Any]]) -> AuditEvidenceTableContext:
    if not rows:
        return AuditEvidenceTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            table=None,
            empty_message_html=Markup(
                render_report_empty_paragraph(
                    projection_plane=ProjectionPlane.AUDIT,
                    paragraph_class="",
                )
            ),
        )
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    headers = tuple(
        AuditTableCellContext(html=Markup(html.escape(_heading(str(name)))))
        for name in fieldnames
    )
    table_rows = []
    for row in rows:
        cells = tuple(
            AuditTableCellContext(html=Markup(_cell_html(row.get(name))))
            for name in fieldnames
        )
        table_rows.append(AuditTableRowContext(cells=cells))
    return AuditEvidenceTableContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
        table=AuditTableContext(table_class="", headers=headers, rows=tuple(table_rows)),
        empty_message_html=Markup(
            render_report_empty_paragraph(
                projection_plane=ProjectionPlane.AUDIT,
                paragraph_class="",
            )
        ),
    )


def _raw_evidence_details(title: str, rows: list[dict[str, Any]]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_raw_evidence_details(title, rows)
    return render_audit_raw_evidence_note(_audit_raw_evidence_note_context(title, rows))


def _legacy_raw_evidence_details(title: str, rows: list[dict[str, Any]]) -> str:
    return (
        f"<p class=\"muted\">{html.escape(title)} is preserved in the MTDA audit/workbench artifacts "
        f"({len(rows)} rows archived). It is summarized here to keep the Audit Report reviewable.</p>"
    )


def _audit_raw_evidence_note_context(title: str, rows: list[dict[str, Any]]) -> AuditRawEvidenceNoteContext:
    return AuditRawEvidenceNoteContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
        title_html=Markup(html.escape(title)),
        row_count=len(rows),
    )


def _operation_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get("phase") or "unknown"), str(row.get("status") or "unknown"))
        buckets[key] = buckets.get(key, 0) + 1
    return [
        {"Phase": phase, "Status": status, "Operation count": count}
        for (phase, status), count in sorted(buckets.items())
    ]


def _operation_preview_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Sequence": row.get("sequence"),
            "Operation": row.get("recipe_step_label") or row.get("operation_type"),
            "Phase": row.get("phase"),
            "Run": row.get("run_id") or "dataset",
            "Status": row.get("status"),
            "Evidence": _operation_evidence_summary(row),
            "Warnings": len(row.get("warnings", ()) or ()),
        }
        for row in rows
    ]


def _operation_evidence_summary(row: dict[str, Any]) -> str:
    outputs = row.get("outputs") if isinstance(row.get("outputs"), dict) else {}
    if outputs:
        keys = list(outputs.keys())[:3]
        return "Outputs: " + ", ".join(str(key) for key in keys)
    refs = row.get("inspection_refs")
    if isinstance(refs, list) and refs:
        return f"{len(refs)} inspection references"
    return "Recorded in operation log"


def _inspection_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, int] = {}
    for row in rows:
        key = str(row.get("type") or row.get("inspection_type") or row.get("view") or "inspection")
        buckets[key] = buckets.get(key, 0) + 1
    return [{"Inspection type": kind, "Count": count} for kind, count in sorted(buckets.items())]


def _inspection_preview_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Inspection": row.get("inspection_id") or row.get("id") or row.get("view") or "inspection",
            "Run": row.get("run_id") or "dataset",
            "Type": row.get("type") or row.get("inspection_type") or row.get("view") or "",
            "Status": row.get("status") or "recorded",
            "Evidence": _inspection_evidence_summary(row),
        }
        for row in rows
    ]


def _inspection_evidence_summary(row: dict[str, Any]) -> str:
    point_count = row.get("point_count")
    if point_count not in (None, ""):
        return f"{point_count} points"
    bounds = []
    for key in ("x_min", "x_max", "y_min", "y_max"):
        if row.get(key) not in (None, ""):
            bounds.append(f"{key}={row.get(key)}")
    if bounds:
        return ", ".join(bounds[:3])
    return "Inspection artifact archived"


def _heading(name: str) -> str:
    replacements = {
        "95% CI": "95% CI",
        "Fmax": "Fmax / N",
        "Fmax_N": "Fmax / N",
        "area": "Area / mm2",
        "area_mm2": "Area / mm2",
        "max_bending_percent": "Max bending / %",
        "modulus": "Modulus / MPa",
        "modulus_MPa": "Modulus / MPa",
        "observed_value": "Observed value",
        "reference_value": "Reference value",
        "std": "SD",
        "std_err": "Standard error",
        "strength": "Strength / MPa",
        "strength_MPa": "Strength / MPa",
        "thickness": "Thickness / mm",
        "thickness_mm": "Thickness / mm",
        "threshold": "Threshold / %",
        "threshold_percent": "Threshold / %",
        "width": "Width / mm",
        "width_mm": "Width / mm",
        "run_id": "Run #",
        "run": "Run #",
        "run_label": "Run #",
        "method_id": "Method",
        "mapping_id": "Mapping profile",
        "schema_id": "Schema",
        "schema_version": "Schema version",
        "mtdp_mutated": "MTDP mutated",
        "selection_source": "Selection source",
        "final_selection_set": "Final selection set",
        "default_selection_set": "Default selection set",
        "final_report_status": "Final-report status",
        "override": "Override",
        "evidence_anchor": "Evidence",
    }
    if name in replacements:
        return replacements[name]
    for suffix, unit in (
        ("_MPa", "MPa"),
        ("_percent", "%"),
        ("_mm2", "mm2"),
        ("_mm", "mm"),
        ("_N", "N"),
    ):
        if name.endswith(suffix):
            return f"{name[: -len(suffix)].replace('_', ' ').title()} / {unit}"
    return name.replace("_", " ").title()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    text = str(value)
    if text.startswith("#"):
        return text
    return _human_value(text)


def _cell_html(value: Any) -> str:
    if isinstance(value, dict) and "href" in value and "label" in value:
        return f"<a href=\"{html.escape(str(value.get('href') or ''))}\">{html.escape(str(value.get('label') or ''))}</a>"
    text = _display(value)
    compact = _compact_text(text)
    if compact != text:
        return f"<span title=\"{html.escape(text)}\">{html.escape(compact)}</span>"
    return html.escape(text)


def _compact_text(text: str, limit: int = 180) -> str:
    text = text.replace("\\\\", "/")
    if len(text) <= limit:
        return text
    head = max(40, limit // 2 - 8)
    tail = max(40, limit - head - 5)
    return f"{text[:head]} ... {text[-tail:]}"


def _nested_text(payload: dict[str, Any], section: str, key: str) -> str:
    value = payload.get(section, {}) if isinstance(payload, dict) else {}
    if isinstance(value, dict):
        item = value.get(key, "")
        if isinstance(item, list):
            return str(len(item))
        return _compact_text(_display(item), limit=96)
    return ""


def _summary_sentence(section_id: str, data: Any) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_summary_sentence(section_id, data)
    return render_audit_process_summary_sentence(_audit_process_summary_sentence_context(section_id, data))


def _legacy_summary_sentence(section_id: str, data: Any) -> str:
    if not isinstance(data, dict):
        return "<p class=\"muted\">No summary data.</p>"
    if section_id == "readiness":
        return f"<p>Readiness status: <strong>{html.escape(_human_value(data.get('status', '')))}</strong>. Report-only warnings remain non-blocking; execution-critical blockers would stop before resolve.</p>"
    if section_id == "experiment_boundary_resolution":
        policy = data.get("policy", {}) if isinstance(data.get("policy"), dict) else {}
        return (
            f"<p>Boundary status: <strong>{html.escape(_human_value(data.get('status', '')))}</strong>. "
            f"Start policy: <code>{html.escape(str(policy.get('start_policy', '')))}</code>; "
            f"end policy: <code>{html.escape(str(policy.get('end_policy', '')))}</code>. "
            f"Bounded reduction: {html.escape(str(data.get('bounded_reduction', False)))}; "
            f"boundary-aligned aggregation: {html.escape(str(data.get('boundary_aligned_aggregation', False)))}.</p>"
            f"{_legacy_table(data.get('endpoints', []) if isinstance(data.get('endpoints'), list) else [])}"
        )
    if section_id == "validation":
        summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
        return f"<p>Validation status: <strong>{html.escape(str(data.get('status', '')))}</strong>; checks passed: {html.escape(str(summary.get('passed', '')))}, warnings: {html.escape(str(summary.get('warnings', '')))}, failed: {html.escape(str(summary.get('failed', '')))}.</p>"
    if section_id == "acceptance_final_selection":
        return f"<p>Final selection set: <strong>{html.escape(_human_value(data.get('final_selection_set', '')))}</strong>; selection source: <strong>{html.escape(_human_value(data.get('selection_source', '')))}</strong>; discharge report rows: {html.escape(str(data.get('discharged_run_count', '')))}.</p>"
    if section_id == "warnings_residuals":
        return f"<p>Warnings recorded: <strong>{html.escape(str(data.get('count', 0)))}</strong>.</p>"
    if section_id == "linked_artifacts":
        return "<p>Primary handoff links are listed here. Raw JSON and CSV evidence remains inside the MTDA archive.</p>"
    return "<p class=\"muted\">Process-verification evidence for this stage is available below.</p>"


def _audit_process_summary_sentence_context(section_id: str, data: Any) -> AuditProcessSummarySentenceContext:
    empty = Markup("")
    if not isinstance(data, dict):
        return _audit_process_summary_sentence_context_for_kind("no_summary")
    if section_id == "readiness":
        return _audit_process_summary_sentence_context_for_kind(
            "readiness",
            status_html=Markup(html.escape(_human_value(data.get("status", "")))),
        )
    if section_id == "experiment_boundary_resolution":
        policy = data.get("policy", {}) if isinstance(data.get("policy"), dict) else {}
        endpoints = data.get("endpoints", []) if isinstance(data.get("endpoints"), list) else []
        return _audit_process_summary_sentence_context_for_kind(
            "experiment_boundary_resolution",
            status_html=Markup(html.escape(_human_value(data.get("status", "")))),
            start_policy_html=Markup(html.escape(str(policy.get("start_policy", "")))),
            end_policy_html=Markup(html.escape(str(policy.get("end_policy", "")))),
            bounded_reduction_html=Markup(html.escape(str(data.get("bounded_reduction", False)))),
            boundary_aligned_aggregation_html=Markup(html.escape(str(data.get("boundary_aligned_aggregation", False)))),
            endpoints_table_html=Markup(_table(endpoints)),
        )
    if section_id == "validation":
        summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
        return _audit_process_summary_sentence_context_for_kind(
            "validation",
            status_html=Markup(html.escape(str(data.get("status", "")))),
            passed_html=Markup(html.escape(str(summary.get("passed", "")))),
            warnings_html=Markup(html.escape(str(summary.get("warnings", "")))),
            failed_html=Markup(html.escape(str(summary.get("failed", "")))),
        )
    if section_id == "acceptance_final_selection":
        return _audit_process_summary_sentence_context_for_kind(
            "acceptance_final_selection",
            final_selection_set_html=Markup(html.escape(_human_value(data.get("final_selection_set", "")))),
            selection_source_html=Markup(html.escape(_human_value(data.get("selection_source", "")))),
            discharged_run_count_html=Markup(html.escape(str(data.get("discharged_run_count", "")))),
        )
    if section_id == "warnings_residuals":
        return _audit_process_summary_sentence_context_for_kind(
            "warnings_residuals",
            warning_count_html=Markup(html.escape(str(data.get("count", 0)))),
        )
    if section_id == "linked_artifacts":
        return _audit_process_summary_sentence_context_for_kind("linked_artifacts")
    return _audit_process_summary_sentence_context_for_kind("default", status_html=empty)


def _audit_process_summary_paragraph(body_html: Markup, *, paragraph_class: str = "") -> Markup:
    return _audit_body_paragraph(body_html, paragraph_class=paragraph_class)


def _audit_process_summary_sentence_html(
    sentence_kind: str,
    *,
    status_html: Markup,
    start_policy_html: Markup,
    end_policy_html: Markup,
    bounded_reduction_html: Markup,
    boundary_aligned_aggregation_html: Markup,
    endpoints_table_html: Markup,
    passed_html: Markup,
    warnings_html: Markup,
    failed_html: Markup,
    final_selection_set_html: Markup,
    selection_source_html: Markup,
    discharged_run_count_html: Markup,
    warning_count_html: Markup,
) -> Markup:
    if sentence_kind == "no_summary":
        return _audit_process_summary_paragraph(Markup("No summary data."), paragraph_class="muted")
    if sentence_kind == "readiness":
        return _audit_process_summary_paragraph(
            Markup("Readiness status: <strong>")
            + status_html
            + Markup(
                "</strong>. Report-only warnings remain non-blocking; execution-critical blockers would stop before resolve."
            )
        )
    if sentence_kind == "experiment_boundary_resolution":
        paragraph_html = _audit_process_summary_paragraph(
            Markup("Boundary status: <strong>")
            + status_html
            + Markup("</strong>. Start policy: <code>")
            + start_policy_html
            + Markup("</code>; end policy: <code>")
            + end_policy_html
            + Markup("</code>. Bounded reduction: ")
            + bounded_reduction_html
            + Markup("; boundary-aligned aggregation: ")
            + boundary_aligned_aggregation_html
            + Markup(".")
        )
        return paragraph_html + endpoints_table_html
    if sentence_kind == "validation":
        return _audit_process_summary_paragraph(
            Markup("Validation status: <strong>")
            + status_html
            + Markup("</strong>; checks passed: ")
            + passed_html
            + Markup(", warnings: ")
            + warnings_html
            + Markup(", failed: ")
            + failed_html
            + Markup(".")
        )
    if sentence_kind == "acceptance_final_selection":
        return _audit_process_summary_paragraph(
            Markup("Final selection set: <strong>")
            + final_selection_set_html
            + Markup("</strong>; selection source: <strong>")
            + selection_source_html
            + Markup("</strong>; discharge report rows: ")
            + discharged_run_count_html
            + Markup(".")
        )
    if sentence_kind == "warnings_residuals":
        return _audit_process_summary_paragraph(
            Markup("Warnings recorded: <strong>") + warning_count_html + Markup("</strong>.")
        )
    if sentence_kind == "linked_artifacts":
        return _audit_process_summary_paragraph(
            Markup("Primary handoff links are listed here. Raw JSON and CSV evidence remains inside the MTDA archive.")
        )
    return _audit_process_summary_paragraph(
        Markup("Process-verification evidence for this stage is available below."),
        paragraph_class="muted",
    )


def _audit_process_summary_sentence_context_for_kind(
    sentence_kind: str,
    *,
    status_html: Markup = Markup(""),
    start_policy_html: Markup = Markup(""),
    end_policy_html: Markup = Markup(""),
    bounded_reduction_html: Markup = Markup(""),
    boundary_aligned_aggregation_html: Markup = Markup(""),
    endpoints_table_html: Markup = Markup(""),
    passed_html: Markup = Markup(""),
    warnings_html: Markup = Markup(""),
    failed_html: Markup = Markup(""),
    final_selection_set_html: Markup = Markup(""),
    selection_source_html: Markup = Markup(""),
    discharged_run_count_html: Markup = Markup(""),
    warning_count_html: Markup = Markup(""),
) -> AuditProcessSummarySentenceContext:
    sentence_html = _audit_process_summary_sentence_html(
        sentence_kind,
        status_html=status_html,
        start_policy_html=start_policy_html,
        end_policy_html=end_policy_html,
        bounded_reduction_html=bounded_reduction_html,
        boundary_aligned_aggregation_html=boundary_aligned_aggregation_html,
        endpoints_table_html=endpoints_table_html,
        passed_html=passed_html,
        warnings_html=warnings_html,
        failed_html=failed_html,
        final_selection_set_html=final_selection_set_html,
        selection_source_html=selection_source_html,
        discharged_run_count_html=discharged_run_count_html,
        warning_count_html=warning_count_html,
    )
    return AuditProcessSummarySentenceContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE,
        sentence_kind=sentence_kind,
        status_html=status_html,
        start_policy_html=start_policy_html,
        end_policy_html=end_policy_html,
        bounded_reduction_html=bounded_reduction_html,
        boundary_aligned_aggregation_html=boundary_aligned_aggregation_html,
        endpoints_table_html=endpoints_table_html,
        passed_html=passed_html,
        warnings_html=warnings_html,
        failed_html=failed_html,
        final_selection_set_html=final_selection_set_html,
        selection_source_html=selection_source_html,
        discharged_run_count_html=discharged_run_count_html,
        warning_count_html=warning_count_html,
        sentence_html=sentence_html,
    )


def _first_numeric(rows: list[dict[str, Any]], field: str, default: float) -> float:
    for row in rows:
        try:
            value = row.get(field)
            if value not in (None, ""):
                return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _human_value(value: Any) -> str:
    text = str(value)
    if not text.startswith("#"):
        replaced = replace_run_ids_for_display(text)
        if replaced != text:
            text = replaced
    replacements = {
        "READY_WITH_WARNINGS": "Ready with warnings",
        "READY": "Ready",
        "NOT_READY": "Not ready",
        "machine_default_confirmed": "Machine default confirmed",
        "machine_acceptance": "Machine acceptance",
        "final_report_runs": "Final report runs",
        "not_finalized": "Not finalized",
        "method_resolve": "Method resolve",
        "method_reduce": "Method reduce",
        "construct_mean_series": "Construct mean strain series",
        "chord_slope": "Chord slope",
        "max_point": "Maximum/failure point",
        "bending_diagnostic": "Bending diagnostic",
        "FAIL_SUSTAINED_BENDING": "Sustained bending exceeds limit",
        "accepted": "Accepted",
        "pass": "Pass",
    }
    return replacements.get(text, text.replace("_", " ") if "_" in text and len(text) < 44 else text)


def _basename(value: Any) -> str:
    text = str(value or "").replace("\\", "/").rstrip("/")
    if not text:
        return ""
    return text.rsplit("/", 1)[-1]


def _parent_basename(value: Any) -> str:
    text = str(value or "").replace("\\", "/").rstrip("/")
    if "/" not in text:
        return ""
    parent = text.rsplit("/", 1)[0].rstrip("/")
    return parent.rsplit("/", 1)[-1] if parent else ""


def _safe_id(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in value).strip("-")
    return safe or "chart"
