from __future__ import annotations

from markupsafe import Markup

from html_renderer.context_models import (
    AuditAggregatePacketContext,
    AuditAcceptanceSummaryContext,
    AuditArtifactLinksContext,
    AuditBlockAnalysisComparisonContext,
    AuditBlockDetailsContext,
    AuditBlockFieldValueTableContext,
    AuditBlockInlineNoteContext,
    AuditBlockParagraphContext,
    AuditBlockPlotPanelContext,
    AuditBlockSummaryPanelContext,
    AuditBlockTableContext,
    AuditBlockTechnicalTraceContext,
    AuditBlockTitledFragmentContext,
    AuditChartComponentContext,
    AuditComponentContext,
    AuditComponentMicrocopyContext,
    AuditDecisionRegisterContext,
    AuditEvidenceAppendicesContext,
    AuditEvidenceTableContext,
    AuditGroupedSectionsContext,
    AuditEvidenceReportContext,
    AuditInspectionLogComponentContext,
    AuditOperationLogComponentContext,
    AuditProcessSectionsContext,
    AuditProcessSummarySentenceContext,
    AuditProcessOverviewContext,
    AuditRawEvidenceNoteContext,
    AuditReadinessSummaryContext,
    AuditRunIndexContext,
    AuditRunPacketsContext,
    AuditTechnicalAppendixContext,
    AuditTrackerContext,
    AuditValidationSummaryContext,
    CompactPlotWrapperContext,
    DatasetPlotStudioContext,
    ExportHtmlPageContext,
    ExportReadmeContext,
    ExportVegaHtmlContext,
    FormalReportAggregateSvgContext,
    FormalReportBooleanBadgeContext,
    FormalReportBlockContext,
    FormalReportDataUseDeviationsContext,
    FormalReportDeviationsSectionContext,
    FormalReportDetailBlockContext,
    FormalReportDimensionHeaderContext,
    FormalReportEvidenceTableContext,
    FormalReportFailureBendingSvgContext,
    FormalReportFieldValueTableContext,
    FormalReportFragmentStackContext,
    FormalReportMissingDataContext,
    FormalReportParagraphContext,
    FormalReportPlotBlockContext,
    FormalReportPlotLegendContext,
    FormalReportPlotNoteContext,
    FormalReportRawEvidenceNoteContext,
    FormalReportRemarksContext,
    FormalReportReviewSectionContext,
    FormalReportSectionPillContext,
    FormalReportTableSectionContext,
    FormalMethodReportContext,
    FormalReportSectionsContext,
    FormalReportStateCardContext,
    FormalReportTableContext,
    FormalReportTrackerContext,
    MtdaFinalizationSectionContext,
    MtdaHandoffPageContext,
    PlotWrapperContext,
    ReportContainerBlockContext,
    ReportDetailsPanelContext,
    ReportHeadingFragmentContext,
    ReportMethodsAppendixContext,
    ReportBodyFragmentContext,
    ReportMessagePanelContext,
    ReportNoteAsideContext,
    ReportNoteMarkerContext,
    ReportParagraphContext,
    ReportRawEvidenceNoteContext,
    ReportShellContext,
    SimpleReportContext,
)
from html_renderer.environment import jinja_environment
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for


def render_report_shell(context: ReportShellContext) -> str:
    return _render_context(context)


def render_report_body_fragment(context: ReportBodyFragmentContext) -> str:
    if context.fragment_kind == "block":
        return _render_context(
            ReportContainerBlockContext(
                projection_plane=context.projection_plane,
                recipe_result_kind=RecipeResultKind.REPORT_CONTAINER_BLOCK,
                wrapper_tag=context.wrapper_tag,
                wrapper_class=context.wrapper_class,
                fragment_id_html=context.fragment_id_html,
                heading_level=context.heading_level,
                title_html=context.title_html,
                body_html=context.body_html,
            )
        )
    if context.fragment_kind == "paragraph":
        return render_report_paragraph_fragment(
            projection_plane=context.projection_plane,
            body_html=context.body_html,
            paragraph_class=context.paragraph_class,
        )
    if context.fragment_kind == "titled_fragment":
        return render_report_heading_fragment(
            projection_plane=context.projection_plane,
            title_html=context.title_html,
            heading_level=context.heading_level,
            body_html=context.body_html,
        )
    if context.fragment_kind == "details_block":
        return render_report_details_fragment(
            projection_plane=context.projection_plane,
            title_html=context.title_html,
            body_html=context.body_html,
            wrapper_class=context.wrapper_class,
            fragment_id_html=context.fragment_id_html,
            marker_html=context.marker_html,
            purpose_html=context.purpose_html,
            note_html=context.note_html,
        )
    if context.fragment_kind == "open_details_block":
        return render_report_details_fragment(
            projection_plane=context.projection_plane,
            title_html=context.title_html,
            body_html=context.body_html,
            wrapper_class=context.wrapper_class,
            fragment_id_html=context.fragment_id_html,
            marker_html=context.marker_html,
            purpose_html=context.purpose_html,
            note_html=context.note_html,
            open_details=True,
        )
    if context.fragment_kind == "formal_detail":
        return _render_context(
            FormalReportDetailBlockContext(
                projection_plane=context.projection_plane,
                recipe_result_kind=RecipeResultKind.FORMAL_REPORT_DETAIL_BLOCK,
                classes=context.wrapper_class,
                block_id_html=context.fragment_id_html,
                title_html=context.title_html,
                marker_html=context.marker_html,
                row_count=context.row_count,
                body_note_html=context.purpose_html,
                content_html=context.body_html,
                note_html=context.note_html,
            )
        )
    if context.fragment_kind == "audit_detail":
        return _render_context(
            AuditBlockDetailsContext(
                projection_plane=context.projection_plane,
                recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_DETAILS,
                classes_html=Markup(context.wrapper_class),
                block_id_html=context.fragment_id_html,
                block_type_html=context.data_block_type_html,
                title_html=context.title_html,
                marker_html=context.marker_html,
                purpose_html=context.purpose_html,
                body_html=context.body_html,
                note_html=context.note_html,
            )
        )
    if context.fragment_kind == "message_block":
        return render_report_message_panel(
            projection_plane=context.projection_plane,
            wrapper_tag=context.wrapper_tag,
            wrapper_class=context.wrapper_class,
            fragment_id_html=context.fragment_id_html,
            body_html=context.body_html,
        )
    if context.fragment_kind == "raw_evidence_note":
        return _render_context(
            ReportRawEvidenceNoteContext(
                projection_plane=context.projection_plane,
                recipe_result_kind=RecipeResultKind.REPORT_RAW_EVIDENCE_NOTE,
                title_html=context.title_html,
                row_count=context.row_count,
                artifact_scope_html=context.body_html,
                row_suffix_html=context.marker_html,
                tail_html=context.note_html,
                paragraph_class=context.paragraph_class,
            )
        )
    return _render_context(context)


def render_report_paragraph_fragment(
    *,
    projection_plane: ProjectionPlane,
    body_html: Markup,
    paragraph_class: str = "",
) -> str:
    return _render_context(
        ReportParagraphContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_PARAGRAPH,
            body_html=body_html,
            paragraph_class=paragraph_class,
        )
    )


def render_report_heading_fragment(
    *,
    projection_plane: ProjectionPlane,
    title_html: Markup,
    heading_level: int,
    body_html: Markup = Markup(""),
) -> str:
    return _render_context(
        ReportHeadingFragmentContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_HEADING_FRAGMENT,
            heading_level=heading_level,
            title_html=title_html,
            body_html=body_html,
        )
    )


def render_report_details_fragment(
    *,
    projection_plane: ProjectionPlane,
    title_html: Markup,
    body_html: Markup,
    wrapper_class: str,
    fragment_id_html: Markup = Markup(""),
    marker_html: Markup = Markup(""),
    purpose_html: Markup = Markup(""),
    note_html: Markup = Markup(""),
    open_details: bool = False,
) -> str:
    return _render_context(
        ReportDetailsPanelContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_DETAILS_PANEL,
            wrapper_class=wrapper_class,
            fragment_id_html=fragment_id_html,
            title_html=title_html,
            body_html=body_html,
            marker_html=marker_html,
            purpose_html=purpose_html,
            note_html=note_html,
            open_details=open_details,
        )
    )


def render_report_message_panel(
    *,
    projection_plane: ProjectionPlane,
    wrapper_tag: str,
    wrapper_class: str,
    body_html: Markup,
    fragment_id_html: Markup = Markup(""),
) -> str:
    return _render_context(
        ReportMessagePanelContext(
            projection_plane=projection_plane,
            recipe_result_kind=RecipeResultKind.REPORT_MESSAGE_PANEL,
            wrapper_tag=wrapper_tag,
            wrapper_class=wrapper_class,
            fragment_id_html=fragment_id_html,
            body_html=body_html,
        )
    )


def render_report_empty_paragraph(
    *,
    projection_plane: ProjectionPlane,
    message_html: Markup = Markup("No rows."),
    paragraph_class: str = "muted",
) -> str:
    return render_report_paragraph_fragment(
        projection_plane=projection_plane,
        body_html=message_html,
        paragraph_class=paragraph_class,
    )


def render_plot_wrapper(context: PlotWrapperContext) -> str:
    return _render_context(context)


def render_compact_plot_wrapper(context: CompactPlotWrapperContext) -> str:
    return _render_context(context)


def render_dataset_plot_studio(context: DatasetPlotStudioContext) -> str:
    return _render_context(context)


def render_simple_report(context: SimpleReportContext) -> str:
    return _render_context(context)


def render_formal_method_report(context: FormalMethodReportContext) -> str:
    return _render_context(context) + "\n"


def render_report_note_marker(context: ReportNoteMarkerContext) -> str:
    return _render_context(context).rstrip("\n")


def render_report_note_aside(context: ReportNoteAsideContext) -> str:
    return _render_context(context).rstrip("\n")


def render_report_methods_appendix(context: ReportMethodsAppendixContext) -> str:
    return _render_context(context).rstrip("\n")


def render_formal_report_state_card(context: FormalReportStateCardContext) -> str:
    return _render_context(context)


def render_formal_report_tracker(context: FormalReportTrackerContext) -> str:
    return _render_context(context)


def render_formal_report_sections(context: FormalReportSectionsContext) -> str:
    return _render_context(context)


def render_formal_report_section_pill(context: FormalReportSectionPillContext) -> str:
    return _render_context(context)


def render_formal_report_boolean_badge(context: FormalReportBooleanBadgeContext) -> str:
    return _render_context(context)


def render_formal_report_dimension_header(context: FormalReportDimensionHeaderContext) -> str:
    return _render_context(context)


def render_formal_report_block(context: FormalReportBlockContext) -> str:
    return _render_context(context)


def render_formal_report_table(context: FormalReportTableContext) -> str:
    return _render_context(context)


def render_formal_report_evidence_table(context: FormalReportEvidenceTableContext) -> str:
    return _render_context(context)


def render_formal_report_field_value_table(context: FormalReportFieldValueTableContext) -> str:
    return _render_context(context)


def render_formal_report_detail_block(context: FormalReportDetailBlockContext) -> str:
    return _render_context(context)


def render_formal_report_fragment_stack(context: FormalReportFragmentStackContext) -> str:
    return _render_context(context)


def render_formal_report_table_section(context: FormalReportTableSectionContext) -> str:
    return _render_context(context)


def render_formal_report_review_section(context: FormalReportReviewSectionContext) -> str:
    return _render_context(context)


def render_formal_report_paragraph(context: FormalReportParagraphContext) -> str:
    return _render_context(context)


def render_formal_report_raw_evidence_note(context: FormalReportRawEvidenceNoteContext) -> str:
    return _render_context(context)


def render_formal_report_remarks(context: FormalReportRemarksContext) -> str:
    return _render_context(context)


def render_formal_report_missing_data(context: FormalReportMissingDataContext) -> str:
    return _render_context(context)


def render_formal_report_data_use_deviations(context: FormalReportDataUseDeviationsContext) -> str:
    return _render_context(context)


def render_formal_report_deviations_section(context: FormalReportDeviationsSectionContext) -> str:
    return _render_context(context)


def render_formal_report_plot_block(context: FormalReportPlotBlockContext) -> str:
    return _render_context(context)


def render_formal_report_plot_legend(context: FormalReportPlotLegendContext) -> str:
    return _render_context(context)


def render_formal_report_aggregate_svg(context: FormalReportAggregateSvgContext) -> str:
    return _render_context(context).rstrip("\n")


def render_formal_report_failure_bending_svg(context: FormalReportFailureBendingSvgContext) -> str:
    return _render_context(context).rstrip("\n")


def render_formal_report_plot_note(context: FormalReportPlotNoteContext) -> str:
    return _render_context(context)


def render_audit_evidence_report(context: AuditEvidenceReportContext) -> str:
    return _render_context(context) + "\n"


def render_audit_run_index(context: AuditRunIndexContext) -> str:
    return _render_context(context)


def render_audit_run_packets(context: AuditRunPacketsContext) -> str:
    return _render_context(context)


def render_audit_aggregate_packet(context: AuditAggregatePacketContext) -> str:
    return _render_context(context)


def render_audit_tracker(context: AuditTrackerContext) -> str:
    return _render_context(context)


def render_audit_process_overview(context: AuditProcessOverviewContext) -> str:
    return _render_context(context)


def render_audit_process_summary_sentence(context: AuditProcessSummarySentenceContext) -> str:
    return _render_context(context)


def render_audit_process_sections(context: AuditProcessSectionsContext) -> str:
    return _render_context(context)


def render_audit_decision_register(context: AuditDecisionRegisterContext) -> str:
    return _render_context(context)


def render_audit_grouped_sections(context: AuditGroupedSectionsContext) -> str:
    return _render_context(context)


def render_audit_table(context: AuditEvidenceTableContext) -> str:
    return _render_context(context)


def render_audit_raw_evidence_note(context: AuditRawEvidenceNoteContext) -> str:
    return _render_context(context)


def render_audit_evidence_appendices(context: AuditEvidenceAppendicesContext) -> str:
    return _render_context(context)


def render_audit_artifact_links(context: AuditArtifactLinksContext) -> str:
    return _render_context(context)


def render_audit_technical_appendix(context: AuditTechnicalAppendixContext) -> str:
    return _render_context(context)


def render_audit_component(context: AuditComponentContext) -> str:
    return _render_context(context)


def render_audit_component_microcopy(context: AuditComponentMicrocopyContext) -> str:
    return _render_context(context)


def render_audit_validation_summary(context: AuditValidationSummaryContext) -> str:
    return _render_context(context)


def render_audit_readiness_summary(context: AuditReadinessSummaryContext) -> str:
    return _render_context(context)


def render_audit_acceptance_summary(context: AuditAcceptanceSummaryContext) -> str:
    return _render_context(context)


def render_audit_operation_log_component(context: AuditOperationLogComponentContext) -> str:
    return _render_context(context)


def render_audit_inspection_log_component(context: AuditInspectionLogComponentContext) -> str:
    return _render_context(context)


def render_audit_chart_component(context: AuditChartComponentContext) -> str:
    return _render_context(context)


def render_audit_block_table(context: AuditBlockTableContext) -> str:
    return _render_context(context)


def render_audit_block_field_value_table(context: AuditBlockFieldValueTableContext) -> str:
    return _render_context(context)


def render_audit_block_details(context: AuditBlockDetailsContext) -> str:
    return _render_context(context)


def render_audit_block_inline_note(context: AuditBlockInlineNoteContext) -> str:
    return _render_context(context)


def render_audit_block_summary_panel(context: AuditBlockSummaryPanelContext) -> str:
    return _render_context(context)


def render_audit_block_technical_trace(context: AuditBlockTechnicalTraceContext) -> str:
    return _render_context(context)


def render_audit_block_titled_fragment(context: AuditBlockTitledFragmentContext) -> str:
    return _render_context(context)


def render_audit_block_paragraph(context: AuditBlockParagraphContext) -> str:
    return _render_context(context)


def render_audit_block_analysis_comparison(context: AuditBlockAnalysisComparisonContext) -> str:
    return _render_context(context)


def render_audit_block_plot_panel(context: AuditBlockPlotPanelContext) -> str:
    return _render_context(context)


def render_export_readme(context: ExportReadmeContext) -> str:
    return _render_context(context) + "\n"


def render_mtda_finalization_section(context: MtdaFinalizationSectionContext) -> str:
    return _render_context(context)


def render_mtda_handoff_page(context: MtdaHandoffPageContext) -> str:
    return _render_context(context)


def render_export_html_page(context: ExportHtmlPageContext) -> str:
    return _render_context(context) + "\n"


def render_export_vega_html(context: ExportVegaHtmlContext) -> str:
    return _render_context(context) + "\n"


def _render_context(
    context: ReportShellContext
    | AuditAggregatePacketContext
    | AuditAcceptanceSummaryContext
    | AuditArtifactLinksContext
    | AuditBlockAnalysisComparisonContext
    | AuditBlockDetailsContext
    | AuditBlockFieldValueTableContext
    | AuditBlockInlineNoteContext
    | AuditBlockParagraphContext
    | AuditBlockPlotPanelContext
    | AuditBlockSummaryPanelContext
    | AuditBlockTableContext
    | AuditBlockTechnicalTraceContext
    | AuditBlockTitledFragmentContext
    | AuditChartComponentContext
    | AuditComponentContext
    | AuditComponentMicrocopyContext
    | AuditDecisionRegisterContext
    | AuditEvidenceAppendicesContext
    | AuditEvidenceTableContext
    | AuditGroupedSectionsContext
    | AuditEvidenceReportContext
    | AuditInspectionLogComponentContext
    | AuditOperationLogComponentContext
    | AuditProcessSectionsContext
    | AuditProcessSummarySentenceContext
    | AuditProcessOverviewContext
    | AuditRawEvidenceNoteContext
    | AuditReadinessSummaryContext
    | AuditRunIndexContext
    | AuditRunPacketsContext
    | AuditTechnicalAppendixContext
    | AuditTrackerContext
    | AuditValidationSummaryContext
    | ExportHtmlPageContext
    | ExportReadmeContext
    | ExportVegaHtmlContext
    | MtdaFinalizationSectionContext
    | MtdaHandoffPageContext
    | ReportContainerBlockContext
    | ReportDetailsPanelContext
    | ReportHeadingFragmentContext
    | ReportMethodsAppendixContext
    | ReportBodyFragmentContext
    | ReportMessagePanelContext
    | ReportNoteAsideContext
    | ReportNoteMarkerContext
    | ReportParagraphContext
    | ReportRawEvidenceNoteContext
    | SimpleReportContext
    | FormalReportAggregateSvgContext
    | FormalReportBooleanBadgeContext
    | FormalMethodReportContext
    | FormalReportBlockContext
    | FormalReportDataUseDeviationsContext
    | FormalReportDeviationsSectionContext
    | FormalReportDetailBlockContext
    | FormalReportDimensionHeaderContext
    | FormalReportEvidenceTableContext
    | FormalReportFailureBendingSvgContext
    | FormalReportFieldValueTableContext
    | FormalReportFragmentStackContext
    | FormalReportMissingDataContext
    | FormalReportParagraphContext
    | FormalReportPlotBlockContext
    | FormalReportPlotLegendContext
    | FormalReportPlotNoteContext
    | FormalReportRawEvidenceNoteContext
    | FormalReportRemarksContext
    | FormalReportReviewSectionContext
    | FormalReportSectionPillContext
    | FormalReportSectionsContext
    | FormalReportStateCardContext
    | FormalReportTableSectionContext
    | FormalReportTableContext
    | FormalReportTrackerContext
    | PlotWrapperContext
    | CompactPlotWrapperContext
    | DatasetPlotStudioContext
) -> str:
    projection = projection_for(context.recipe_result_kind)
    if context.projection_plane not in projection.projection_planes:
        raise ValueError(
            f"{context.recipe_result_kind} cannot be projected on {context.projection_plane}"
        )
    template = jinja_environment().get_template(projection.template_name)
    return template.render(page=context)
