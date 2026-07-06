from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from html_renderer.projection_planes import ProjectionPlane


class RecipeResultKind(StrEnum):
    REPORT_SHELL = "report_shell"
    REPORT_BODY_FRAGMENT = "report_body_fragment"
    REPORT_PARAGRAPH = "report_paragraph"
    REPORT_HEADING_FRAGMENT = "report_heading_fragment"
    REPORT_CONTAINER_BLOCK = "report_container_block"
    REPORT_DETAILS_PANEL = "report_details_panel"
    REPORT_MESSAGE_PANEL = "report_message_panel"
    REPORT_RAW_EVIDENCE_NOTE = "report_raw_evidence_note"
    TEST_REPORT = "test_report"
    FORMAL_METHOD_REPORT = "formal_method_report"
    REPORT_NOTE_MARKER = "report_note_marker"
    REPORT_NOTE_ASIDE = "report_note_aside"
    REPORT_METHODS_APPENDIX = "report_methods_appendix"
    FORMAL_REPORT_STATE_CARD = "formal_report_state_card"
    FORMAL_REPORT_TRACKER = "formal_report_tracker"
    FORMAL_REPORT_SECTIONS = "formal_report_sections"
    FORMAL_REPORT_SECTION_PILL = "formal_report_section_pill"
    FORMAL_REPORT_BOOLEAN_BADGE = "formal_report_boolean_badge"
    FORMAL_REPORT_DIMENSION_HEADER = "formal_report_dimension_header"
    FORMAL_REPORT_BLOCK = "formal_report_block"
    FORMAL_REPORT_TABLE = "formal_report_table"
    FORMAL_REPORT_EVIDENCE_TABLE = "formal_report_evidence_table"
    FORMAL_REPORT_FIELD_VALUE_TABLE = "formal_report_field_value_table"
    FORMAL_REPORT_DETAIL_BLOCK = "formal_report_detail_block"
    FORMAL_REPORT_FRAGMENT_STACK = "formal_report_fragment_stack"
    FORMAL_REPORT_TABLE_SECTION = "formal_report_table_section"
    FORMAL_REPORT_REVIEW_SECTION = "formal_report_review_section"
    FORMAL_REPORT_PARAGRAPH = "formal_report_paragraph"
    FORMAL_REPORT_RAW_EVIDENCE_NOTE = "formal_report_raw_evidence_note"
    FORMAL_REPORT_REMARKS = "formal_report_remarks"
    FORMAL_REPORT_MISSING_DATA = "formal_report_missing_data"
    FORMAL_REPORT_DATA_USE_DEVIATIONS = "formal_report_data_use_deviations"
    FORMAL_REPORT_DEVIATIONS_SECTION = "formal_report_deviations_section"
    FORMAL_REPORT_PLOT_LEGEND = "formal_report_plot_legend"
    FORMAL_REPORT_PLOT_BLOCK = "formal_report_plot_block"
    FORMAL_REPORT_AGGREGATE_SVG = "formal_report_aggregate_svg"
    FORMAL_REPORT_FAILURE_BENDING_SVG = "formal_report_failure_bending_svg"
    FORMAL_REPORT_PLOT_NOTE = "formal_report_plot_note"
    AUDIT_REPORT = "audit_report"
    AUDIT_EVIDENCE_REPORT = "audit_evidence_report"
    AUDIT_RUN_INDEX = "audit_run_index"
    AUDIT_RUN_PACKETS = "audit_run_packets"
    AUDIT_AGGREGATE_PACKET = "audit_aggregate_packet"
    AUDIT_TRACKER = "audit_tracker"
    AUDIT_PROCESS_OVERVIEW = "audit_process_overview"
    AUDIT_PROCESS_SUMMARY_SENTENCE = "audit_process_summary_sentence"
    AUDIT_PROCESS_SECTIONS = "audit_process_sections"
    AUDIT_DECISION_REGISTER = "audit_decision_register"
    AUDIT_GROUPED_SECTIONS = "audit_grouped_sections"
    AUDIT_TABLE = "audit_table"
    AUDIT_RAW_EVIDENCE_NOTE = "audit_raw_evidence_note"
    AUDIT_EVIDENCE_APPENDICES = "audit_evidence_appendices"
    AUDIT_ARTIFACT_LINKS = "audit_artifact_links"
    AUDIT_TECHNICAL_APPENDIX = "audit_technical_appendix"
    AUDIT_COMPONENT = "audit_component"
    AUDIT_COMPONENT_MICROCOPY = "audit_component_microcopy"
    AUDIT_VALIDATION_SUMMARY = "audit_validation_summary"
    AUDIT_READINESS_SUMMARY = "audit_readiness_summary"
    AUDIT_ACCEPTANCE_SUMMARY = "audit_acceptance_summary"
    AUDIT_OPERATION_LOG_COMPONENT = "audit_operation_log_component"
    AUDIT_INSPECTION_LOG_COMPONENT = "audit_inspection_log_component"
    AUDIT_CHART_COMPONENT = "audit_chart_component"
    AUDIT_BLOCK_TABLE = "audit_block_table"
    AUDIT_BLOCK_FIELD_VALUE_TABLE = "audit_block_field_value_table"
    AUDIT_BLOCK_DETAILS = "audit_block_details"
    AUDIT_BLOCK_INLINE_NOTE = "audit_block_inline_note"
    AUDIT_BLOCK_SUMMARY_PANEL = "audit_block_summary_panel"
    AUDIT_BLOCK_TECHNICAL_TRACE = "audit_block_technical_trace"
    AUDIT_BLOCK_TITLED_FRAGMENT = "audit_block_titled_fragment"
    AUDIT_BLOCK_PARAGRAPH = "audit_block_paragraph"
    AUDIT_BLOCK_ANALYSIS_COMPARISON = "audit_block_analysis_comparison"
    AUDIT_BLOCK_PLOT_PANEL = "audit_block_plot_panel"
    MTDA_FINALIZATION_SECTION = "mtda_finalization_section"
    MTDA_HANDOFF_PAGE = "mtda_handoff_page"
    MTDA_PLOT_WRAPPER = "mtda_plot_wrapper"
    MTDA_COMPACT_PLOT_WRAPPER = "mtda_compact_plot_wrapper"
    MTDA_DATASET_PLOT_STUDIO = "mtda_dataset_plot_studio"
    METADATA_BLOCK = "metadata_block"
    WARNING_BLOCK = "warning_block"
    DIAGNOSTIC_BLOCK = "diagnostic_block"
    AUDIT_EVIDENCE_BLOCK = "audit_evidence_block"
    VALIDATION_BLOCK = "validation_block"
    EXPORT_CONTROLS = "export_controls"
    EXPORT_README = "export_readme"
    EXPORT_HTML_PAGE = "export_html_page"
    EXPORT_VEGA_HTML = "export_vega_html"
    RUNTIME_BOOTSTRAP = "runtime_bootstrap"


@dataclass(frozen=True, slots=True)
class RecipeProjection:
    result_kind: RecipeResultKind
    context_model: str
    template_name: str
    projection_planes: tuple[ProjectionPlane, ...]


RECIPE_PROJECTIONS: dict[RecipeResultKind, RecipeProjection] = {
    RecipeResultKind.REPORT_PARAGRAPH: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_PARAGRAPH,
        context_model="ReportParagraphContext",
        template_name="components/typography/paragraph.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_HEADING_FRAGMENT: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_HEADING_FRAGMENT,
        context_model="ReportHeadingFragmentContext",
        template_name="components/typography/heading_fragment.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_CONTAINER_BLOCK: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_CONTAINER_BLOCK,
        context_model="ReportContainerBlockContext",
        template_name="components/panels/container_block.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_DETAILS_PANEL: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_DETAILS_PANEL,
        context_model="ReportDetailsPanelContext",
        template_name="components/panels/details_panel.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_MESSAGE_PANEL: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_MESSAGE_PANEL,
        context_model="ReportMessagePanelContext",
        template_name="components/panels/message_panel.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_RAW_EVIDENCE_NOTE: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_RAW_EVIDENCE_NOTE,
        context_model="ReportRawEvidenceNoteContext",
        template_name="components/notes/raw_evidence_note.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_SHELL: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_SHELL,
        context_model="ReportShellContext",
        template_name="pages/report_shell.html.j2",
        projection_planes=(ProjectionPlane.MTDA_BUNDLE_VIEWER,),
    ),
    RecipeResultKind.MTDA_HANDOFF_PAGE: RecipeProjection(
        result_kind=RecipeResultKind.MTDA_HANDOFF_PAGE,
        context_model="MtdaHandoffPageContext",
        template_name="pages/mtda/handoff_page.html.j2",
        projection_planes=(ProjectionPlane.MTDA_BUNDLE_VIEWER,),
    ),
    RecipeResultKind.MTDA_PLOT_WRAPPER: RecipeProjection(
        result_kind=RecipeResultKind.MTDA_PLOT_WRAPPER,
        context_model="PlotWrapperContext",
        template_name="pages/plots/plot_wrapper.html.j2",
        projection_planes=(ProjectionPlane.MTDA_BUNDLE_VIEWER,),
    ),
    RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER: RecipeProjection(
        result_kind=RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER,
        context_model="CompactPlotWrapperContext",
        template_name="pages/plots/compact_plot_wrapper.html.j2",
        projection_planes=(ProjectionPlane.MTDA_BUNDLE_VIEWER,),
    ),
    RecipeResultKind.MTDA_DATASET_PLOT_STUDIO: RecipeProjection(
        result_kind=RecipeResultKind.MTDA_DATASET_PLOT_STUDIO,
        context_model="DatasetPlotStudioContext",
        template_name="pages/plots/dataset_plot_studio.html.j2",
        projection_planes=(ProjectionPlane.MTDA_BUNDLE_VIEWER,),
    ),
    RecipeResultKind.TEST_REPORT: RecipeProjection(
        result_kind=RecipeResultKind.TEST_REPORT,
        context_model="SimpleReportContext",
        template_name="pages/simple_report.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_METHOD_REPORT: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_METHOD_REPORT,
        context_model="FormalMethodReportContext",
        template_name="layouts/report_page.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.REPORT_NOTE_MARKER: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_NOTE_MARKER,
        context_model="ReportNoteMarkerContext",
        template_name="components/notes/note_marker.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_NOTE_ASIDE: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_NOTE_ASIDE,
        context_model="ReportNoteAsideContext",
        template_name="components/notes/note_aside.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.REPORT_METHODS_APPENDIX: RecipeProjection(
        result_kind=RecipeResultKind.REPORT_METHODS_APPENDIX,
        context_model="ReportMethodsAppendixContext",
        template_name="sections/shared/methods_appendix.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.FORMAL_REPORT_STATE_CARD: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_STATE_CARD,
        context_model="FormalReportStateCardContext",
        template_name="sections/formal/state_card.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_TRACKER: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_TRACKER,
        context_model="FormalReportTrackerContext",
        template_name="components/trackers/formal_report_tracker.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_SECTIONS: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_SECTIONS,
        context_model="FormalReportSectionsContext",
        template_name="sections/formal/sections.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_SECTION_PILL: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_SECTION_PILL,
        context_model="FormalReportSectionPillContext",
        template_name="components/badges/section_pill.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_BOOLEAN_BADGE,
        context_model="FormalReportBooleanBadgeContext",
        template_name="components/badges/boolean_badge.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_DIMENSION_HEADER,
        context_model="FormalReportDimensionHeaderContext",
        template_name="components/tables/dimension_header.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_BLOCK: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_BLOCK,
        context_model="FormalReportBlockContext",
        template_name="components/panels/report_block.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_TABLE,
        context_model="FormalReportTableContext",
        template_name="components/tables/report_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE,
        context_model="FormalReportEvidenceTableContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_FIELD_VALUE_TABLE,
        context_model="FormalReportFieldValueTableContext",
        template_name="components/tables/formal_field_value_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
        context_model="FormalReportDetailBlockContext",
        template_name="components/panels/formal_detail_block.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_FRAGMENT_STACK,
        context_model="FormalReportFragmentStackContext",
        template_name="components/panels/fragment_stack.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_TABLE_SECTION: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
        context_model="FormalReportTableSectionContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_REVIEW_SECTION,
        context_model="FormalReportReviewSectionContext",
        template_name="sections/formal/review_section.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_PARAGRAPH: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_PARAGRAPH,
        context_model="FormalReportParagraphContext",
        template_name="components/typography/paragraph.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
        context_model="FormalReportRawEvidenceNoteContext",
        template_name="components/notes/raw_evidence_note.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_REMARKS: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_REMARKS,
        context_model="FormalReportRemarksContext",
        template_name="sections/formal/remarks.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_MISSING_DATA: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
        context_model="FormalReportMissingDataContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
        context_model="FormalReportDataUseDeviationsContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_DEVIATIONS_SECTION,
        context_model="FormalReportDeviationsSectionContext",
        template_name="sections/formal/deviations_section.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_BLOCK,
        context_model="FormalReportPlotBlockContext",
        template_name="components/plots/formal_plot_block.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_LEGEND,
        context_model="FormalReportPlotLegendContext",
        template_name="components/plots/formal_plot_legend.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_AGGREGATE_SVG,
        context_model="FormalReportAggregateSvgContext",
        template_name="components/plots/aggregate_svg.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_FAILURE_BENDING_SVG,
        context_model="FormalReportFailureBendingSvgContext",
        template_name="components/plots/failure_bending_svg.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.FORMAL_REPORT_PLOT_NOTE: RecipeProjection(
        result_kind=RecipeResultKind.FORMAL_REPORT_PLOT_NOTE,
        context_model="FormalReportPlotNoteContext",
        template_name="components/typography/plot_note.html.j2",
        projection_planes=(ProjectionPlane.TEST,),
    ),
    RecipeResultKind.AUDIT_EVIDENCE_REPORT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_EVIDENCE_REPORT,
        context_model="AuditEvidenceReportContext",
        template_name="layouts/report_page.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_RUN_INDEX: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
        context_model="AuditRunIndexContext",
        template_name="sections/audit/run_index.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_RUN_PACKETS: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_RUN_PACKETS,
        context_model="AuditRunPacketsContext",
        template_name="sections/audit/run_packets.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_AGGREGATE_PACKET: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_AGGREGATE_PACKET,
        context_model="AuditAggregatePacketContext",
        template_name="sections/audit/aggregate_packet.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_TRACKER: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_TRACKER,
        context_model="AuditTrackerContext",
        template_name="components/trackers/audit_report_tracker.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_PROCESS_OVERVIEW: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_PROCESS_OVERVIEW,
        context_model="AuditProcessOverviewContext",
        template_name="sections/audit/process_overview.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE,
        context_model="AuditProcessSummarySentenceContext",
        template_name="sections/audit/process_summary_sentence.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_PROCESS_SECTIONS: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_PROCESS_SECTIONS,
        context_model="AuditProcessSectionsContext",
        template_name="sections/audit/process_sections.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_DECISION_REGISTER: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_DECISION_REGISTER,
        context_model="AuditDecisionRegisterContext",
        template_name="sections/audit/decision_register.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_GROUPED_SECTIONS: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_GROUPED_SECTIONS,
        context_model="AuditGroupedSectionsContext",
        template_name="sections/audit/grouped_sections.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_TABLE,
        context_model="AuditEvidenceTableContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
        context_model="AuditRawEvidenceNoteContext",
        template_name="components/notes/raw_evidence_note.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_EVIDENCE_APPENDICES: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_EVIDENCE_APPENDICES,
        context_model="AuditEvidenceAppendicesContext",
        template_name="sections/audit/evidence_appendices.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_ARTIFACT_LINKS: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_ARTIFACT_LINKS,
        context_model="AuditArtifactLinksContext",
        template_name="sections/audit/artifact_links.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_TECHNICAL_APPENDIX: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_TECHNICAL_APPENDIX,
        context_model="AuditTechnicalAppendixContext",
        template_name="sections/audit/technical_appendix.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_COMPONENT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_COMPONENT,
        context_model="AuditComponentContext",
        template_name="components/typography/heading_fragment.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_COMPONENT_MICROCOPY: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
        context_model="AuditComponentMicrocopyContext",
        template_name="components/typography/audit_microcopy.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_VALIDATION_SUMMARY: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
        context_model="AuditValidationSummaryContext",
        template_name="sections/audit/validation_summary.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_READINESS_SUMMARY: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_READINESS_SUMMARY,
        context_model="AuditReadinessSummaryContext",
        template_name="sections/audit/readiness_summary.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY,
        context_model="AuditAcceptanceSummaryContext",
        template_name="sections/audit/acceptance_summary.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT,
        context_model="AuditOperationLogComponentContext",
        template_name="sections/audit/log_component.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT,
        context_model="AuditInspectionLogComponentContext",
        template_name="sections/audit/log_component.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_CHART_COMPONENT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_CHART_COMPONENT,
        context_model="AuditChartComponentContext",
        template_name="components/plots/audit_chart_component.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_TABLE,
        context_model="AuditBlockTableContext",
        template_name="components/tables/optional_report_table.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE,
        context_model="AuditBlockFieldValueTableContext",
        template_name="components/tables/key_value_table.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_DETAILS: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_DETAILS,
        context_model="AuditBlockDetailsContext",
        template_name="sections/audit/block_details.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE,
        context_model="AuditBlockInlineNoteContext",
        template_name="components/notes/audit_inline_note.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL,
        context_model="AuditBlockSummaryPanelContext",
        template_name="components/panels/titled_panel.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE,
        context_model="AuditBlockTechnicalTraceContext",
        template_name="sections/audit/technical_trace.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT,
        context_model="AuditBlockTitledFragmentContext",
        template_name="components/typography/heading_fragment.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_PARAGRAPH: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
        context_model="AuditBlockParagraphContext",
        template_name="components/typography/paragraph.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
        context_model="AuditBlockAnalysisComparisonContext",
        template_name="components/panels/titled_panel.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
        context_model="AuditBlockPlotPanelContext",
        template_name="components/plots/audit_plot_panel.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.AUDIT_REPORT: RecipeProjection(
        result_kind=RecipeResultKind.AUDIT_REPORT,
        context_model="SimpleReportContext",
        template_name="pages/simple_report.html.j2",
        projection_planes=(ProjectionPlane.AUDIT,),
    ),
    RecipeResultKind.MTDA_FINALIZATION_SECTION: RecipeProjection(
        result_kind=RecipeResultKind.MTDA_FINALIZATION_SECTION,
        context_model="MtdaFinalizationSectionContext",
        template_name="sections/shared/finalization_section.html.j2",
        projection_planes=(ProjectionPlane.TEST, ProjectionPlane.AUDIT),
    ),
    RecipeResultKind.EXPORT_HTML_PAGE: RecipeProjection(
        result_kind=RecipeResultKind.EXPORT_HTML_PAGE,
        context_model="ExportHtmlPageContext",
        template_name="pages/export_html_page.html.j2",
        projection_planes=(ProjectionPlane.EXPORT_BUNDLE,),
    ),
    RecipeResultKind.EXPORT_VEGA_HTML: RecipeProjection(
        result_kind=RecipeResultKind.EXPORT_VEGA_HTML,
        context_model="ExportVegaHtmlContext",
        template_name="pages/export_vega_html.html.j2",
        projection_planes=(ProjectionPlane.EXPORT_BUNDLE,),
    ),
    RecipeResultKind.EXPORT_README: RecipeProjection(
        result_kind=RecipeResultKind.EXPORT_README,
        context_model="ExportReadmeContext",
        template_name="pages/export_readme.html.j2",
        projection_planes=(ProjectionPlane.EXPORT_BUNDLE,),
    ),
}


def projection_for(kind: RecipeResultKind) -> RecipeProjection:
    try:
        return RECIPE_PROJECTIONS[kind]
    except KeyError as exc:
        raise ValueError(f"No HTML projection registered for recipe/result kind: {kind}") from exc
