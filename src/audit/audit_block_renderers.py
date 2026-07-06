from __future__ import annotations

import html
import json
import math
import os
from statistics import mean
from typing import Any

from markupsafe import Markup

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
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_audit_block_analysis_comparison,
    render_audit_block_details,
    render_audit_block_field_value_table,
    render_audit_block_inline_note,
    render_audit_block_paragraph,
    render_audit_block_plot_panel,
    render_audit_block_summary_panel,
    render_audit_block_table,
    render_audit_block_technical_trace,
    render_audit_block_titled_fragment,
    render_report_empty_paragraph,
    render_report_paragraph_fragment,
)
from plotting.evidence_adapters import (
    aggregate_curve_family_request,
    bending_evidence_request,
    curve_shape_distance_ranking_request,
    curve_shape_residuals_request,
    stress_strain_reduction_request,
)
from plotting.models import PlotResult
from plotting.plots.stress_strain_reduction import (
    END_MARKER_LABEL,
    END_MAX_FAILURE_MARKER_LABEL,
    MAX_FAILURE_MARKER_LABEL,
    START_MARKER_LABEL,
)
from plotting.registry import plot_registry
from reporting.renderers.formatting_standard import (
    NoteParagraph,
    ReportNoteCollector,
    note_html,
    note_label,
    note_text,
    render_note_marker,
)
from reporting.run_labels import replace_run_ids_for_display, run_display_label


def _legacy_renderer_enabled() -> bool:
    return os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy"


def render_block(
    block: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
    force_open: bool = False,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    block_type = str(block.get("block_type") or "")
    if block_type == "run_identity_and_status":
        return _render_identity_block(block, force_open=force_open)
    if block_type == "run_stress_strain_reduction":
        return _render_stress_strain_block(block, result=result, specs=specs, force_open=force_open)
    if block_type == "run_bending_evidence":
        return _render_bending_block(block, result=result, specs=specs, force_open=force_open)
    if block_type == "run_curve_shape_diagnostic":
        return _render_curve_shape_block(block, force_open=force_open)
    if block_type == "run_validation_evidence":
        return _render_validation_block(block, force_open=force_open)
    if block_type == "run_technical_trace_links":
        return _render_technical_trace_block(block, force_open=force_open)
    if block_type == "run_selection_consequence":
        return _render_selection_block(block, force_open=force_open)
    if block_type == "aggregate_dataset_cohort_population":
        return _render_aggregate_dataset_cohort(block, note_collector=note_collector)
    if block_type == "aggregate_curve_family":
        return _render_aggregate_curve_family(block, result=result, specs=specs, note_collector=note_collector)
    if block_type == "aggregate_curve_shape_diagnostics":
        return _render_aggregate_curve_shape_diagnostics(block, result=result, specs=specs, note_collector=note_collector)
    if block_type == "aggregate_evidence_summary":
        return _render_aggregate_evidence_summary(block)
    return _render_generic_block(block, force_open=force_open)


def render_table(rows: list[dict[str, Any]], *, technical: bool = False, fields: list[str] | None = None) -> str:
    if _legacy_renderer_enabled():
        return _legacy_render_table(rows, technical=technical, fields=fields)
    return render_audit_block_table(_audit_block_table_context(rows, technical=technical, fields=fields))


def _legacy_render_table(rows: list[dict[str, Any]], *, technical: bool = False, fields: list[str] | None = None) -> str:
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if not clean_rows:
        return "<p class=\"muted\">No rows.</p>"
    fieldnames = list(fields or [])
    if not fieldnames:
        for row in clean_rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    header = "".join(f"<th>{html.escape(_header_label(str(name)))}</th>" for name in fieldnames)
    body = []
    for row in clean_rows:
        cells = "".join(f"<td>{_cell(row.get(name), technical=technical, field=str(name))}</td>" for name in fieldnames)
        body.append(f"<tr>{cells}</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def _audit_block_table_context(
    rows: list[dict[str, Any]],
    *,
    technical: bool = False,
    fields: list[str] | None = None,
) -> AuditBlockTableContext:
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if not clean_rows:
        return AuditBlockTableContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TABLE,
            table=None,
            empty_message_html=Markup(render_report_empty_paragraph(projection_plane=ProjectionPlane.AUDIT)),
        )
    fieldnames = list(fields or [])
    if not fieldnames:
        for row in clean_rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    return AuditBlockTableContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TABLE,
        table=AuditTableContext(
            table_class="",
            headers=tuple(
                AuditTableCellContext(html=Markup(html.escape(_header_label(str(name)))))
                for name in fieldnames
            ),
            rows=tuple(
                AuditTableRowContext(
                    cells=tuple(
                        AuditTableCellContext(html=Markup(_cell(row.get(name), technical=technical, field=str(name))))
                        for name in fieldnames
                    )
                )
                for row in clean_rows
            ),
        ),
        empty_message_html=Markup(render_report_empty_paragraph(projection_plane=ProjectionPlane.AUDIT)),
    )


def render_field_value_table(rows: list[tuple[str, Any]]) -> str:
    if _legacy_renderer_enabled():
        return _legacy_render_field_value_table(rows)
    return render_audit_block_field_value_table(_audit_block_field_value_table_context(rows))


def _legacy_render_field_value_table(rows: list[tuple[str, Any]]) -> str:
    clean_rows = [(label, value) for label, value in rows if value not in (None, "")]
    if not clean_rows:
        return "<p class=\"muted\">No rows.</p>"
    body = "".join(
        "<tr>"
        f"<th scope=\"row\">{html.escape(_field_label(label))}</th>"
        f"<td>{_cell(value, field=label)}</td>"
        "</tr>"
        for label, value in clean_rows
    )
    return f"<div class=\"table-wrap field-value-table\"><table><tbody>{body}</tbody></table></div>"


def _audit_block_field_value_table_context(rows: list[tuple[str, Any]]) -> AuditBlockFieldValueTableContext:
    clean_rows = [(label, value) for label, value in rows if value not in (None, "")]
    return AuditBlockFieldValueTableContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_FIELD_VALUE_TABLE,
        rows=tuple(
            AuditBlockFieldValueRowContext(
                label_html=Markup(html.escape(_field_label(label))),
                value_html=Markup(_cell(value, field=label)),
            )
            for label, value in clean_rows
        ),
        empty_message_html=Markup(render_report_empty_paragraph(projection_plane=ProjectionPlane.AUDIT)),
    )


def _titled_fragment(title: str, body: str) -> str:
    if _legacy_renderer_enabled():
        return _legacy_titled_fragment(title, body)
    return render_audit_block_titled_fragment(
        AuditBlockTitledFragmentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT,
            title_html=Markup(html.escape(title)),
            body_html=Markup(body),
        )
    )


def _legacy_titled_fragment(title: str, body: str) -> str:
    return f"<h4>{html.escape(title)}</h4>{body}"


def _audit_block_paragraph(body: str, *, paragraph_class: str = "") -> str:
    if _legacy_renderer_enabled():
        return _legacy_audit_block_paragraph(body, paragraph_class=paragraph_class)
    return render_audit_block_paragraph(
        AuditBlockParagraphContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PARAGRAPH,
            body_html=Markup(body),
            paragraph_class=paragraph_class,
        )
    )


def _legacy_audit_block_paragraph(body: str, *, paragraph_class: str = "") -> str:
    class_attr = f" class=\"{html.escape(paragraph_class)}\"" if paragraph_class else ""
    return f"<p{class_attr}>{body}</p>"


def _analysis_comparison(title: str, body: str) -> str:
    if _legacy_renderer_enabled():
        return _legacy_analysis_comparison(title, body)
    return render_audit_block_analysis_comparison(
        AuditBlockAnalysisComparisonContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
            title_html=Markup(html.escape(title)),
            body_html=Markup(body),
        )
    )


def _legacy_analysis_comparison(title: str, body: str) -> str:
    return f"<div class=\"analysis-comparison\"><h4>{html.escape(title)}</h4>{body}</div>"


def _render_identity_block(block: dict[str, Any], *, force_open: bool) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    geometry = _first_table_row(block, "geometry")
    failure_observation = _first_table_row(block, "failure_observation")
    rows = [
        ("Run #", block.get("run_id")),
        ("Specimen name", summary.get("specimen_name")),
        ("Sample ID", summary.get("sample_id")),
        ("Source file", summary.get("source_file", "")),
        ("Width / mm", geometry.get("width_mm")),
        ("Thickness / mm", geometry.get("thickness_mm")),
        ("Area / mm2", geometry.get("area_mm2")),
        ("Data validity", _human_operator_validity(summary.get("validity"))),
        ("Experimental failure", _human_failure_observation(summary.get("failure_mode"))),
    ]
    failure_rows = [
        ("Failure mode", failure_observation.get("Failure mode")),
        ("Failure location", failure_observation.get("Failure location")),
        ("Invalid specimen reason", failure_observation.get("Invalid specimen reason")),
        ("Bending/failure observation", failure_observation.get("Bending/failure observation")),
        ("Bending evidence", failure_observation.get("Bending evidence")),
        ("Notes", failure_observation.get("Notes")),
    ]
    body = render_field_value_table(rows)
    if failure_observation:
        body += _titled_fragment("Failure observation evidence", render_field_value_table(failure_rows))
    return _details(
        block,
        force_open=force_open,
        default_open=force_open,
        body=body,
    )


def _render_stress_strain_block(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    force_open: bool,
) -> str:
    calculation = _first_table_row(block, "calculation")
    compact = {
        "Fmax": calculation.get("Fmax_N"),
        "strength": calculation.get("strength_MPa"),
        "failure_strain": calculation.get("failure_strain"),
        "modulus": calculation.get("modulus_MPa"),
        "stress_at_0_0005": calculation.get("chord_stress_at_0_0005_MPa"),
        "stress_at_0_0025": calculation.get("chord_stress_at_0_0025_MPa"),
    }
    body = _stress_strain_plot(block, result=result, specs=specs) + _titled_fragment(
        "Reduction results",
        render_table([compact]),
    )
    return _details(
        block,
        force_open=force_open,
        default_open=force_open,
        body=body,
        extra_class="visual-first",
    )


def _render_bending_block(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    force_open: bool,
) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    row = _first_table_row(block, "summary")
    compact = {
        "classification": summary.get("classification") or row.get("classification"),
        "threshold_percent": row.get("threshold_percent"),
        "max_bending_percent": row.get("max_bending_percent"),
        "points_above_threshold": row.get("points_above_threshold"),
        "fraction_above_threshold": row.get("fraction_above_threshold"),
        "longest_segment_points": row.get("longest_segment_points"),
        "longest_segment_fraction": _longest_segment_fraction(block),
        "segment_type": _longest_segment_type(block),
        "diagnostic_consequence": _bending_evidence_consequence(summary),
    }
    is_problem = str(compact.get("classification") or "").strip() not in {"", "PASS"}
    bending_rows = [
        ("Bending result", _human_curve_state(compact.get("classification"))),
        ("Threshold / %", compact.get("threshold_percent")),
        ("Max bending / %", compact.get("max_bending_percent")),
    ]
    if is_problem:
        bending_rows.append(("Above-threshold extent", _bending_extent_sentence(compact)))
    body = _bending_plot(block, result=result, specs=specs) + _titled_fragment(
        "Bending evidence summary",
        render_field_value_table(bending_rows),
    )
    return _details(
        block,
        force_open=force_open,
        default_open=force_open or is_problem,
        body=body,
        extra_class="visual-first",
    )


def _render_curve_shape_block(block: dict[str, Any], *, force_open: bool) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    classification = str(summary.get("curve_shape_classification") or "")
    threshold_method = str(summary.get("threshold_method") or "")
    rows = [
        ("Curve-shape result", _human_curve_state(summary.get("curve_shape_classification"))),
        ("Difference score (distance_rms)", summary.get("distance_rms")),
        ("Rank within cohort (distance_rank)", _display_or_dash(summary.get("distance_rank"))),
    ]
    if threshold_method == "robust_mad_zscore":
        rows.extend(
            [
                ("Upper-tail MAD score", _display_or_dash(summary.get("mad_upper_z") or summary.get("z_mad_upper"))),
                ("Signed MAD z-score (z_mad)", _display_or_dash(summary.get("robust_z") or summary.get("z_mad"))),
                ("Upper-tail MAD cutoff (z_crit)", _display_or_dash(summary.get("threshold_value"))),
            ]
        )
    elif threshold_method == "dixon_high_outlier_q_test":
        rows.append(("Observed Dixon Q (Qexp)", _display_or_dash(summary.get("Qexp"))))
        rows.append(("Dixon decision", _display_or_dash(summary.get("dixon_decision"))))
        if summary.get("secondary_threshold_method"):
            rows.extend(
                [
                    ("Companion MAD score", _display_or_dash(summary.get("mad_upper_z") or summary.get("z_mad_upper"))),
                    ("Companion flag", _yes_no(summary.get("masking_companion_flag"))),
                    ("Masking risk", _yes_no(summary.get("masking_risk"))),
                ]
            )
    else:
        rows.append(("Observed Dixon Q (Qexp)", _display_or_dash(summary.get("Qexp"))))
    rows.extend(
        [
            ("Threshold rule", _human_threshold_method(threshold_method)),
            ("Outlier", _curve_shape_outlier_text(summary)),
        ]
    )
    body = render_field_value_table(rows)
    open_for_alert = classification in {"CURVE_SHAPE_OUTLIER", "INSUFFICIENT_CURVE_DATA", "INSUFFICIENT_COHORT_SIZE", "CURVE_SHAPE_NOT_ASSESSED"}
    return _details(
        block,
        force_open=force_open,
        default_open=force_open or open_for_alert,
        body=body,
    )


def _render_validation_block(block: dict[str, Any], *, force_open: bool) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    details = _table_rows(block, "details")
    problem_rows = [
        row for row in details
        if str(row.get("status") or "").casefold() in {"warn", "warning", "fail", "failed"}
    ]
    clean = not problem_rows and int(summary.get("failed") or 0) == 0 and int(summary.get("warnings") or 0) == 0
    if clean:
        body = render_table(
            [
                {
                    "evidence_item": "ISO 14126 reference values",
                    "deviation_state": "No deviations or warnings recorded",
                    "run_effect": "No validation alert; bending and curve-shape evidence are reviewed separately",
                }
            ]
        )
    else:
        body = _titled_fragment("Deviation evidence", render_table(_validation_evidence_rows(problem_rows)))
    return _details(block, force_open=force_open, default_open=force_open or not clean, body=body)


def _render_technical_trace_block(block: dict[str, Any], *, force_open: bool) -> str:
    return _details(block, force_open=force_open, default_open=False, body=_technical_trace(block))


def _render_selection_block(block: dict[str, Any], *, force_open: bool) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    selection = _first_table_row(block, "selection")
    flags = _table_rows(block, "flags")
    compact = _report_inclusion_evidence(summary, selection, flags)
    body = render_table([compact])
    if flags:
        body += _titled_fragment("Data flags affecting inclusion", render_table(_compact_flag_rows(flags)))
    return _details(
        block,
        force_open=force_open,
        default_open=force_open or _is_problematic_selection(selection) or bool(flags),
        body=body,
    )


def _render_aggregate_dataset_cohort(
    block: dict[str, Any],
    *,
    note_collector: ReportNoteCollector | None,
) -> str:
    cohorts = _table_rows(block, "cohorts")
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    body = (
        render_table([summary])
        if summary
        else _audit_block_paragraph(
            "Curve-shape diagnostic evidence unavailable: missing acceptance/curve_family/curve_diagnostic_report.json.",
            paragraph_class="plot-unavailable",
        )
    )
    if cohorts:
        body += _titled_fragment("Cohort population", render_table(cohorts))
    return _details(
        block,
        force_open=True,
        default_open=True,
        body=body,
        note_parts=_block_purpose_note(block, role="definition"),
        note_collector=note_collector,
    )


def _render_aggregate_curve_family(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    note_collector: ReportNoteCollector | None,
) -> str:
    figure_notes: list[NoteParagraph] = []
    body = (
        _aggregate_curve_plot(block, result=result, specs=specs, figure_notes=figure_notes)
    )
    return _details(
        block,
        force_open=True,
        default_open=True,
        body=body,
        extra_class="visual-first",
        note_parts=_block_purpose_note(block, role="method") + figure_notes,
        note_collector=note_collector,
    )


def _render_aggregate_curve_shape_diagnostics(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    note_collector: ReportNoteCollector | None,
) -> str:
    scores = _table_rows(block, "scores")
    cohorts = _table_rows(block, "cohorts")
    threshold_method = _curve_shape_threshold_method(scores, cohorts)
    explanation_inner = _curve_shape_method_note(scores, cohorts, threshold_method)
    figure_notes: list[NoteParagraph] = []
    if not scores:
        body = _plot_unavailable("acceptance/curve_family/curve_diagnostic_scores.csv")
    else:
        result_fields = _curve_shape_result_fields(threshold_method)
        body = (
            _titled_fragment(
                "Curve-shape method",
                render_field_value_table(_curve_shape_method_rows(scores, cohorts, threshold_method=threshold_method)),
            )
            + _curve_shape_distance_plot(block, result=result, specs=specs, figure_notes=figure_notes)
            + _titled_fragment(
                "Curve-shape results",
                render_table(
                    _curve_shape_result_rows(scores, threshold_method=threshold_method),
                    fields=result_fields,
                ),
            )
        )
    return _details(
        block,
        force_open=True,
        default_open=True,
        body=body,
        extra_class="visual-first",
        note_parts=_block_purpose_note(block, role="method") + [note_html("method", explanation_inner)] + figure_notes,
        note_collector=note_collector,
    )


def _render_aggregate_evidence_summary(block: dict[str, Any]) -> str:
    rows = _table_rows(block, "evidence_flags")
    body = render_table(rows) if rows else _audit_block_paragraph("No evidence flags were recorded.")
    body += _audit_block_paragraph(
        "Run inclusion, exclusion, discharge, and final report use are reported in the Decision Register."
    )
    return _details(block, force_open=True, default_open=True, body=body)


def _render_generic_block(block: dict[str, Any], *, force_open: bool) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    tables = block.get("tables") if isinstance(block.get("tables"), dict) else {}
    body = _summary_card("Evidence conclusion", summary)
    for title, rows in tables.items():
        if isinstance(rows, list) and rows:
            body += _titled_fragment(_title(str(title)), render_table([row for row in rows if isinstance(row, dict)]))
    return _details(block, force_open=force_open, default_open=force_open, body=body)


def _stress_strain_plot(block: dict[str, Any], *, result: Any, specs: dict[str, dict[str, Any]] | None) -> str:
    run_id = str(block.get("run_id") or "")
    bounded_rows = _rows_for_run(getattr(result, "bounded_curve_family", None) or [], run_id)
    if not bounded_rows:
        return _plot_unavailable(f"method_outputs/curves/{_safe_id(run_id)}_stress_strain_bounded.csv")
    spec_id = _safe_id(f"run_{run_id}_stress_strain_reduction_plot")
    plot_result = plot_registry.build(
        stress_strain_reduction_request(
            plot_id=spec_id,
            run_id=run_id,
            bounded_rows=bounded_rows,
            block=block,
        )
    )
    return _plot_panel(plot_result, specs=specs, audit_plot_type="run_stress_strain_reduction")


def _bending_plot(block: dict[str, Any], *, result: Any, specs: dict[str, dict[str, Any]] | None) -> str:
    run_id = str(block.get("run_id") or "")
    rows = _rows_for_run(getattr(result, "bounded_curve_family", None) or [], run_id)
    bending_rows = _bending_rows(rows)
    if not bending_rows:
        return _plot_unavailable(f"method_outputs/curves/{_safe_id(run_id)}_stress_strain_bounded.csv")
    spec_id = _safe_id(f"run_{run_id}_bending_evidence_plot")
    plot_result = plot_registry.build(
        bending_evidence_request(
            plot_id=spec_id,
            run_id=run_id,
            bounded_rows=rows,
            block=block,
        )
    )
    return _plot_panel(plot_result, specs=specs, audit_plot_type="run_bending_evidence")


def _aggregate_curve_plot(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    figure_notes: list[NoteParagraph] | None = None,
) -> str:
    if result is None:
        return _plot_unavailable("report/aligned_curves.csv")
    aligned_source, aligned = _aggregate_curve_aligned_rows(result)
    raw_reference = getattr(result, "curve_shape_diagnostic_reference_rows", None) or getattr(result, "curve_family_reference_rows", None) or []
    reference = _analysis_window_rows(raw_reference)
    scores = getattr(result, "curve_shape_diagnostic_scores", None) or []
    fallback_curves = _aggregate_fallback_curve_rows(result)
    if not aligned and not fallback_curves:
        return _plot_unavailable("report/aligned_curves.csv")
    freshness = _aggregate_curve_plot_freshness(
        result,
        aligned_rows=aligned,
        fallback_curves=fallback_curves,
        source=aligned_source if aligned else "bounded_curve_family",
    )
    spec_id = "aggregate_curve_family_plot"
    plot_result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id=spec_id,
            aligned_rows=aligned,
            reference_rows=reference,
            fallback_curves=fallback_curves,
            diagnostic_scores=scores,
            plot_data_freshness=freshness,
            block=block,
        )
    )
    if figure_notes is not None:
        _capture_plot_caption(plot_result, figure_notes)
    return _plot_panel(
        plot_result,
        specs=specs,
        audit_plot_type="aggregate_curve_family",
        emit_caption=figure_notes is None,
    )


def _aggregate_curve_aligned_rows(result: Any) -> tuple[str, list[dict[str, Any]]]:
    residuals = getattr(result, "curve_shape_diagnostic_residual_rows", None) or []
    rows = _analysis_window_rows(residuals)
    if rows:
        return "curve_shape_diagnostic_residual_rows", rows
    aligned = getattr(result, "curve_family_aligned_rows", None) or []
    return "curve_family_aligned_rows", _analysis_window_rows(aligned)


def _analysis_window_rows(rows: Any) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        x_value = _analysis_x_percent(row)
        if x_value is not None and not (-1e-9 <= x_value <= 100.0 + 1e-9):
            continue
        copy = dict(row)
        copy.setdefault("alignment_domain", "experiment_progress")
        copy.setdefault("source_boundaries", "method_resolve.experiment_boundaries")
        copy.setdefault("curve_scope", "boundary_aligned")
        if x_value is not None:
            _set_analysis_window_coordinate(copy, x_value)
        clean.append(copy)
    return clean


def _aggregate_fallback_curve_rows(result: Any) -> list[dict[str, Any]]:
    rows = getattr(result, "bounded_curve_family", None) or []
    clean: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        x_value = _analysis_x_percent(row)
        point_index = _as_float(row.get("point_index"))
        start_index = _as_float(row.get("boundary_start_index"))
        end_index = _as_float(row.get("boundary_end_index"))
        if x_value is not None and not (-1e-9 <= x_value <= 100.0 + 1e-9):
            continue
        if point_index is not None and start_index is not None and point_index < start_index:
            continue
        if point_index is not None and end_index is not None and point_index > end_index:
            continue
        clean.append(row)
    return clean


def _aggregate_curve_plot_freshness(
    result: Any,
    *,
    aligned_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]],
    source: str,
) -> dict[str, Any]:
    boundary_by_run = _audit_boundary_by_run(getattr(result, "experiment_boundaries", None) or [])
    run_ids = sorted(
        {
            str(row.get("run_id") or "")
            for row in [*aligned_rows, *fallback_curves]
            if isinstance(row, dict) and row.get("run_id")
        }
    )
    reasons: list[str] = []
    leaks = _analysis_window_leaks([*aligned_rows, *fallback_curves])
    if leaks:
        reasons.append(
            "Aggregate curve-family plot contains points outside the resolved experiment analysis window for "
            + ", ".join(leaks)
            + "."
        )
    if boundary_by_run and not run_ids:
        reasons.append("No aggregate curve-family plot rows were available for boundary-resolved runs.")
    policy_signatures = sorted(
        {
            str(_audit_boundary_policy_signature(boundary).get("signature") or "")
            for boundary in boundary_by_run.values()
            if _audit_boundary_policy_signature(boundary).get("signature")
        }
    )
    endpoint_by_run = {
        run_id: _audit_boundary_index(boundary, "end_index")
        for run_id, boundary in sorted(boundary_by_run.items())
        if not run_ids or run_id in run_ids
    }
    return {
        "schema_id": "report.plot_data_freshness.v0_1",
        "status": "stale" if reasons else "current",
        "replicate_source": source,
        "bounded_replicates": bool(aligned_rows or fallback_curves),
        "boundary_aligned_replicates": bool(aligned_rows),
        "boundary_aligned_aggregation": bool(aligned_rows),
        "alignment_domain": "experiment_progress",
        "source_boundaries": "method_resolve.experiment_boundaries",
        "selected_run_count": len(run_ids),
        "boundary_resolved_run_count": len(set(run_ids) & set(boundary_by_run)) if run_ids else len(boundary_by_run),
        "aggregate_row_count": len(aligned_rows) or len(fallback_curves),
        "replicate_row_count": len(aligned_rows) or len(fallback_curves),
        "endpoint_by_run": endpoint_by_run,
        "policy_signatures": policy_signatures,
        "reasons": reasons,
    }


def _analysis_window_leaks(rows: list[dict[str, Any]]) -> list[str]:
    leaks: set[str] = set()
    for row in rows:
        run_id = str(row.get("run_id") or "")
        x_value = _analysis_x_percent(row)
        point_index = _as_float(row.get("point_index"))
        start_index = _as_float(row.get("boundary_start_index"))
        end_index = _as_float(row.get("boundary_end_index"))
        if x_value is not None and (x_value < -1e-9 or x_value > 100.0 + 1e-9):
            leaks.add(run_id)
        if point_index is not None and start_index is not None and point_index < start_index:
            leaks.add(run_id)
        if point_index is not None and end_index is not None and point_index > end_index:
            leaks.add(run_id)
    return sorted(value for value in leaks if value)


def _analysis_x_percent(row: dict[str, Any]) -> float | None:
    point_index = _as_float(row.get("point_index"))
    start_index = _as_float(row.get("boundary_start_index"))
    end_index = _as_float(row.get("boundary_end_index"))
    if point_index is not None and start_index is not None and end_index not in (None, start_index):
        x_value = (point_index - start_index) / (end_index - start_index) * 100.0
        if -1e-9 <= x_value <= 100.0 + 1e-9:
            return max(0.0, min(100.0, x_value))
    percent = _first_float(row, "analysis_progress_percent", "analysis_window_progress_percent")
    if percent is not None:
        return percent
    value = _first_float(row, "analysis_progress", "experiment_progress", "x_common", "x_normalized")
    if value is None:
        return None
    return value * 100.0 if value <= 1.5 else value


def _set_analysis_window_coordinate(row: dict[str, Any], percent: float) -> None:
    bounded_percent = max(0.0, min(100.0, float(percent)))
    fraction = bounded_percent / 100.0
    row["analysis_progress_percent"] = bounded_percent
    row["analysis_progress"] = fraction
    row["experiment_progress"] = fraction
    row["x_normalized"] = fraction
    row["x_common"] = fraction


def _first_float(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _as_float(row.get(key))
        if value is not None:
            return value
    return None


def _audit_boundary_by_run(boundary_records: Any) -> dict[str, dict[str, Any]]:
    records = boundary_records if isinstance(boundary_records, list) else []
    return {
        str(record.get("run_id")): record
        for record in records
        if isinstance(record, dict) and record.get("run_id")
    }


def _audit_boundary_index(boundary: dict[str, Any], key: str) -> float | None:
    interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
    return _as_float(interval.get(key, boundary.get(key)))


def _audit_boundary_policy_signature(boundary: dict[str, Any]) -> dict[str, Any]:
    policy = boundary.get("resolution_policy") if isinstance(boundary.get("resolution_policy"), dict) else {}
    slope = policy.get("slope_break") if isinstance(policy.get("slope_break"), dict) else {}
    return {
        "end_policy": policy.get("end_policy") or boundary.get("end_policy"),
        "slope_domain": slope.get("slope_domain"),
        "signature": policy.get("signature") or boundary.get("policy_signature"),
    }


def _curve_shape_distance_plot(
    block: dict[str, Any],
    *,
    result: Any,
    specs: dict[str, dict[str, Any]] | None,
    figure_notes: list[NoteParagraph] | None = None,
) -> str:
    scores = getattr(result, "curve_shape_diagnostic_scores", None) or []
    if not scores:
        return _plot_unavailable("acceptance/curve_family/curve_diagnostic_scores.csv")
    spec_id = "curve_shape_distance_ranking_plot"
    plot_result = plot_registry.build(
        curve_shape_distance_ranking_request(
            plot_id=spec_id,
            scores=scores,
            block=block,
        )
    )
    if figure_notes is not None:
        _capture_plot_caption(plot_result, figure_notes)
    return _plot_panel(
        plot_result,
        specs=specs,
        audit_plot_type="curve_shape_distance_ranking",
        emit_caption=figure_notes is None,
    )


def _residual_detail_plot(*, result: Any, specs: dict[str, dict[str, Any]] | None) -> str:
    residuals = getattr(result, "curve_shape_diagnostic_residual_rows", None) or []
    if not residuals:
        return _analysis_comparison(
            "Curve residual detail",
            _audit_block_paragraph(
                "Curve residual detail unavailable: missing acceptance/curve_family/curve_diagnostic_residuals.csv. Review the archived residual evidence if needed.",
                paragraph_class="plot-unavailable",
            ),
        )
    spec_id = "curve_shape_residual_detail_plot"
    plot_result = plot_registry.build(
        curve_shape_residuals_request(
            plot_id=spec_id,
            residuals=residuals,
            scores=getattr(result, "curve_shape_diagnostic_scores", None) or [],
        )
    )
    return _analysis_comparison(
        "Curve residual detail",
        _plot_panel(plot_result, specs=specs, audit_plot_type="curve_shape_residual_detail"),
    )


def _plot_panel(
    result: PlotResult,
    *,
    specs: dict[str, dict[str, Any]] | None,
    audit_plot_type: str,
    emit_caption: bool = True,
) -> str:
    if _legacy_renderer_enabled():
        return _legacy_plot_panel(result, specs=specs, audit_plot_type=audit_plot_type, emit_caption=emit_caption)
    if result.spec:
        if specs is not None:
            specs[result.plot_id] = result.spec
        warning_html = ""
        if result.warnings:
            warning_html = "<p class=\"plot-warning\">" + html.escape("; ".join(result.warnings)) + "</p>"
        usermeta = result.spec.get("usermeta") if isinstance(result.spec, dict) else {}
        caption = str(usermeta.get("caption") or "") if isinstance(usermeta, dict) else ""
        caption_html = f"<p class=\"plot-caption\">{html.escape(caption)}</p>" if caption and emit_caption else ""
        return render_audit_block_plot_panel(
            AuditBlockPlotPanelContext(
                projection_plane=ProjectionPlane.AUDIT,
                recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
                has_spec=True,
                audit_plot_type_html=Markup(html.escape(audit_plot_type)),
                plot_id_html=Markup(html.escape(result.plot_id)),
                caption_html=Markup(caption_html),
                warning_html=Markup(warning_html),
                fallback_message_html=Markup(""),
            )
        )
    return render_audit_block_plot_panel(
        AuditBlockPlotPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
            has_spec=False,
            audit_plot_type_html=Markup(""),
            plot_id_html=Markup(""),
            caption_html=Markup(""),
            warning_html=Markup(""),
            fallback_message_html=Markup(
                html.escape(result.fallback_message or "Plot unavailable. Review the archived analysis evidence.")
            ),
        )
    )


def _legacy_plot_panel(
    result: PlotResult,
    *,
    specs: dict[str, dict[str, Any]] | None,
    audit_plot_type: str,
    emit_caption: bool = True,
) -> str:
    if result.spec:
        if specs is not None:
            specs[result.plot_id] = result.spec
        warning_html = ""
        if result.warnings:
            warning_html = "<p class=\"plot-warning\">" + html.escape("; ".join(result.warnings)) + "</p>"
        usermeta = result.spec.get("usermeta") if isinstance(result.spec, dict) else {}
        caption = str(usermeta.get("caption") or "") if isinstance(usermeta, dict) else ""
        caption_html = f"<p class=\"plot-caption\">{html.escape(caption)}</p>" if caption and emit_caption else ""
        return (
            f"<div class=\"plot-panel\" data-audit-plot=\"{html.escape(audit_plot_type)}\">"
            f"<div id=\"{html.escape(result.plot_id)}\" class=\"chart audit-plot\"></div>"
            f"{caption_html}{warning_html}</div>"
        )
    return (
        "<div class=\"plot-unavailable\">"
        f"{html.escape(result.fallback_message or 'Plot unavailable. Review the archived analysis evidence.')}"
        "</div>"
    )


def _capture_plot_caption(result: PlotResult, figure_notes: list[NoteParagraph]) -> None:
    usermeta = result.spec.get("usermeta") if isinstance(result.spec, dict) else {}
    caption = str(usermeta.get("caption") or "").strip() if isinstance(usermeta, dict) else ""
    if caption:
        figure_notes.append(note_text("figure", caption))


def _stress_strain_spec(
    block: dict[str, Any],
    *,
    bounded_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    bounded_values = _curve_values(bounded_rows, "average strain curve", max_rows=650)
    gauge_trace_values = _front_rear_trace_values(bounded_rows, max_rows=650)
    strain_envelope_values = _strain_envelope_values(bounded_rows, max_rows=650)
    markers = _stress_markers(block, bounded_rows)
    chord = _chord_line_values(block)
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "run_stress_strain_reduction: front strain, rear strain, average strain bounded curve, strain agreement envelope, analysis markers, chord points, chord line",
        "width": "container",
        "height": 300,
        "layer": [
            {
                "name": "front rear strain agreement envelope",
                "data": {"values": strain_envelope_values},
                "mark": {"type": "area", "clip": True, "color": "#78aeda", "opacity": 0.16},
                "encoding": {
                    "x": {"field": "strain_min", "type": "quantitative", "title": "Strain / %"},
                    "x2": {"field": "strain_max"},
                    "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
                    "tooltip": [
                        {"field": "series", "type": "nominal", "title": "Evidence"},
                        {"field": "strain_min", "type": "quantitative", "title": "Lower gauge strain / %", "format": ".4f"},
                        {"field": "strain_max", "type": "quantitative", "title": "Upper gauge strain / %", "format": ".4f"},
                        {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
                        {"field": "point_index", "type": "quantitative", "title": "Point index"},
                    ],
                },
            },
            {
                "name": "front rear strain traces",
                "data": {"values": gauge_trace_values},
                "mark": {"type": "line", "clip": True, "strokeWidth": 1.1, "opacity": 0.5},
                "encoding": _gauge_trace_encoding(),
            },
            {
                "name": "bounded curve",
                "data": {"values": bounded_values},
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.4},
                "encoding": _average_curve_encoding(),
            },
            {
                "name": "chord line",
                "data": {"values": chord},
                "mark": {"type": "line", "strokeWidth": 2, "strokeDash": [6, 4], "color": "#207245"},
                "encoding": _curve_encoding(),
            },
            {
                "name": "chord points",
                "data": {"values": [row for row in chord if row.get("stress") is not None]},
                "mark": {"type": "point", "filled": True, "size": 70, "color": "#207245"},
                "encoding": _point_encoding("label"),
            },
            {
                "name": "analysis markers",
                "data": {"values": markers},
                "mark": {"type": "point", "filled": True, "size": 82, "color": "#c45f20"},
                "encoding": {
                    **_point_encoding("marker"),
                    "shape": {"field": "marker", "type": "nominal", "title": "Analysis markers"},
                },
            },
        ],
        "config": _plot_config(),
    }


def _bending_spec(block: dict[str, Any], bending_rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    threshold = _as_float(summary.get("threshold_percent") or _nested(block, "markers", "threshold_line", "bending_percent")) or 10.0
    window = _nested(block, "markers", "assessment_window_10_90_fmax", "load_window_N") or []
    lower = _as_float(window[0]) if isinstance(window, list) and len(window) > 0 else _as_float(_nested(block, "markers", "assessment_window_10_90_fmax", "lower_load_N"))
    upper = _as_float(window[1]) if isinstance(window, list) and len(window) > 1 else _as_float(_nested(block, "markers", "assessment_window_10_90_fmax", "upper_load_N"))
    max_y = max([row["bending_percent"] for row in bending_rows if row.get("bending_percent") is not None] + [threshold])
    exceedances = [row for row in bending_rows if _as_float(row.get("bending_percent")) is not None and float(row["bending_percent"]) > threshold]
    segments = _segment_values(block, max_y=max_y)
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "run_bending_evidence: threshold line, 10-90% window, exceedance segments, classification",
        "usermeta": {"classification": summary.get("classification", "")},
        "width": "container",
        "height": 280,
        "layer": [
            {
                "name": "10-90% window",
                "data": {"values": [{"x1": lower, "x2": upper, "y1": 0.0, "y2": max_y * 1.08}] if lower is not None and upper is not None else []},
                "mark": {"type": "rect", "color": "#7d8794", "opacity": 0.12},
                "encoding": {
                    "x": {"field": "x1", "type": "quantitative", "title": "Load / N"},
                    "x2": {"field": "x2"},
                    "y": {"field": "y1", "type": "quantitative", "title": "Bending / %"},
                    "y2": {"field": "y2"},
                },
            },
            {
                "name": "exceedance segments",
                "data": {"values": segments},
                "mark": {"type": "rect", "color": "#d95f5f", "opacity": 0.18},
                "encoding": {
                    "x": {"field": "start_load_N", "type": "quantitative"},
                    "x2": {"field": "end_load_N"},
                    "y": {"field": "y1", "type": "quantitative"},
                    "y2": {"field": "y2"},
                    "tooltip": [{"field": "segment_classification", "type": "nominal", "title": "Segment"}],
                },
            },
            {
                "name": "bending percent series",
                "data": {"values": _downsample(bending_rows, 700)},
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.2, "color": "#1f78b4"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "title": "Load / N"},
                    "y": {"field": "bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "tooltip": [
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                    ],
                },
            },
            {
                "name": "exceedance points",
                "data": {"values": exceedances},
                "mark": {"type": "point", "filled": True, "size": 42, "color": "#a12626"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative"},
                    "y": {"field": "bending_percent", "type": "quantitative"},
                },
            },
            {
                "name": "threshold line",
                "data": {"values": [{"threshold": threshold}]},
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#a12626"},
                "encoding": {"y": {"field": "threshold", "type": "quantitative"}},
            },
        ],
        "config": _plot_config(),
    }


def _aggregate_curve_spec(
    aligned_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]],
    diagnostic_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    curves, stats = _aggregate_curve_values(aligned_rows, fallback_curves, diagnostic_scores)
    reference = [
        {
            "x": _x_common_percent(row),
            "stress": _as_float(row.get("y_reference")),
            "series": "mean or median curve",
            "std_lower": _as_float(row.get("y_lower")),
            "std_upper": _as_float(row.get("y_upper")),
            "n": row.get("support_n", ""),
        }
        for row in reference_rows
        if _as_float(row.get("y_reference")) is not None
    ]
    band = [
        {
            "x": row["x"],
            "std_lower": row.get("std_lower", row.get("stress")),
            "std_upper": row.get("std_upper", row.get("stress")),
            "n": row.get("n", ""),
        }
        for row in reference
    ] or stats
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "aggregate_curve_family: all evaluable curves, cohort reference mean curve, variability band, curve-shape outlier diagnostic classification",
        "width": "container",
        "height": 320,
        "layer": [
            {
                "name": "cohort variability band",
                "data": {"values": band},
                "mark": {"type": "area", "opacity": 0.22, "color": "#2a7fb8"},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": "Normalised strain / %"},
                    "y": {"field": "std_lower", "type": "quantitative", "title": "Stress / MPa"},
                    "y2": {"field": "std_upper"},
                    "tooltip": [{"field": "n", "type": "quantitative", "title": "Observation count"}],
                },
            },
            {
                "name": "all evaluable curves by curve-shape state",
                "data": {"values": curves},
                "mark": {"type": "line", "strokeWidth": 1.4, "opacity": 0.34},
                "encoding": _aggregate_curve_encoding(detail=True),
            },
            {
                "name": "mean or median curve",
                "data": {"values": reference or stats},
                "mark": {"type": "line", "strokeWidth": 3, "color": "#1f78b4"},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": "Normalised strain / %"},
                    "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
                },
            },
        ],
        "config": _plot_config(),
    }


def _distance_ranking_spec(scores: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        row for row in scores
        if isinstance(row, dict) and _as_float(row.get("distance_rms")) is not None
    ]
    threshold_values = []
    dixon_rows = [row for row in values if str(row.get("threshold_method") or "") == "dixon_high_outlier_q_test"]
    if dixon_rows:
        candidate = max(dixon_rows, key=lambda row: _as_float(row.get("distance_rms")) or 0.0)
        threshold_values.append(
            {
                "distance_rank": candidate.get("distance_rank"),
                "distance_rms": candidate.get("distance_rms"),
                "label": f"candidate highest distance; Qexp={candidate.get('Qexp', '')}, Qcrit_95={candidate.get('Qcrit_95', '')}",
            }
        )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "curve-shape distance ranking plot: distance_rms, distance_rank, Qexp, Qcrit_95, threshold_method, classification",
        "width": "container",
        "height": 280,
        "layer": [
            {
                "name": "distance_rms by distance_rank",
                "data": {"values": values},
                "mark": {"type": "bar"},
                "encoding": {
                    "x": {"field": "distance_rank", "type": "ordinal", "title": "Distance rank"},
                    "y": {"field": "distance_rms", "type": "quantitative", "title": "distance_rms"},
                    "color": {
                        "field": "diagnostic_classification",
                        "type": "nominal",
                        "title": "Curve-shape classification",
                        "scale": _curve_shape_color_scale(),
                    },
                    "tooltip": [
                        {"field": "run_id", "type": "nominal", "title": "Run"},
                        {"field": "specimen", "type": "nominal", "title": "Specimen"},
                        {"field": "distance_rms", "type": "quantitative", "title": "distance_rms", "format": ".4f"},
                        {"field": "Qexp", "type": "nominal", "title": "Qexp"},
                        {"field": "Qcrit_95", "type": "nominal", "title": "Qcrit_95"},
                        {"field": "threshold_method", "type": "nominal", "title": "Threshold method"},
                        {"field": "diagnostic_classification", "type": "nominal", "title": "Classification"},
                    ],
                },
            },
            {
                "name": "Dixon candidate annotation",
                "data": {"values": threshold_values},
                "mark": {"type": "text", "dy": -8, "fontSize": 11, "color": "#6b5200"},
                "encoding": {
                    "x": {"field": "distance_rank", "type": "ordinal"},
                    "y": {"field": "distance_rms", "type": "quantitative"},
                    "text": {"field": "label"},
                },
            },
        ],
        "config": _plot_config(),
    }


def _residual_spec(residuals: list[dict[str, Any]], scores: list[dict[str, Any]]) -> dict[str, Any]:
    classification_by_run = {
        str(row.get("run_id") or ""): str(row.get("diagnostic_classification") or "")
        for row in scores
        if isinstance(row, dict)
    }
    values = []
    for row in _downsample([row for row in residuals if isinstance(row, dict)], 1600):
        x_value = _x_common_percent(row)
        z_value = _as_float(row.get("standardized_residual"))
        run_id = str(row.get("run_id") or "")
        if x_value is None or z_value is None or not run_id:
            continue
        values.append(
            {
                "run_id": run_id,
                "x": x_value,
                "standardized_residual": z_value,
                "diagnostic_classification": classification_by_run.get(run_id, row.get("diagnostic_classification", "")),
            }
        )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Curve residual detail: standardized residual z(x) by run.",
        "width": "container",
        "height": 260,
        "data": {"values": values},
        "mark": {"type": "line", "strokeWidth": 1.2, "opacity": 0.45},
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "title": "Normalised strain / %"},
            "y": {"field": "standardized_residual", "type": "quantitative", "title": "standardized residual z(x)"},
            "detail": {"field": "run_id"},
            "color": {
                "field": "diagnostic_classification",
                "type": "nominal",
                "scale": _curve_shape_color_scale(),
            },
            "tooltip": [
                {"field": "run_id", "type": "nominal", "title": "Run"},
                {"field": "x", "type": "quantitative", "title": "Normalised strain / %", "format": ".2f"},
                {"field": "standardized_residual", "type": "quantitative", "title": "z(x)", "format": ".3f"},
                {"field": "diagnostic_classification", "type": "nominal", "title": "Classification"},
            ],
        },
        "config": _plot_config(),
    }


def _details(
    block: dict[str, Any],
    *,
    body: str,
    default_open: bool,
    force_open: bool = False,
    extra_class: str = "",
    note_parts: list[NoteParagraph] | None = None,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    if _legacy_renderer_enabled():
        return _legacy_details(
            block,
            body=body,
            default_open=default_open,
            force_open=force_open,
            extra_class=extra_class,
            note_parts=note_parts,
            note_collector=note_collector,
        )
    block_id = html.escape(str(block.get("block_id") or "audit-block"))
    block_type = html.escape(str(block.get("block_type") or "audit-block"))
    raw_title = str(block.get("title") or block.get("block_type") or "Audit block")
    title = html.escape(raw_title)
    status = html.escape(str(block.get("status") or "recorded"))
    klass = f"audit-block {block_type} {extra_class}".strip()
    purpose = html.escape(str(block.get("purpose") or ""))
    note_html_markup = ""
    marker_html = ""
    if note_parts and note_collector is not None:
        klass = f"{klass} note-anchor"
        marker_html = render_note_marker(projection_plane=ProjectionPlane.AUDIT)
        note_html_markup = note_collector.add(title=raw_title, paragraphs=note_parts)
    elif note_parts:
        klass = f"{klass} note-anchor"
        marker_html = render_note_marker(projection_plane=ProjectionPlane.AUDIT)
        note_html_markup = _inline_note_markup(note_parts)
    purpose_html = (
        render_report_paragraph_fragment(
            projection_plane=ProjectionPlane.AUDIT,
            body_html=Markup(purpose),
            paragraph_class="audit-purpose",
        )
        if purpose and not block_type.startswith("run_") and not note_html_markup
        else ""
    )
    return render_audit_block_details(
        AuditBlockDetailsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_DETAILS,
            classes_html=Markup(klass),
            block_id_html=Markup(block_id),
            block_type_html=Markup(block_type),
            title_html=Markup(title),
            marker_html=Markup(marker_html),
            purpose_html=Markup(purpose_html),
            body_html=Markup(body),
            note_html=Markup(note_html_markup),
        )
    )


def _legacy_details(
    block: dict[str, Any],
    *,
    body: str,
    default_open: bool,
    force_open: bool = False,
    extra_class: str = "",
    note_parts: list[NoteParagraph] | None = None,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    block_id = html.escape(str(block.get("block_id") or "audit-block"))
    block_type = html.escape(str(block.get("block_type") or "audit-block"))
    raw_title = str(block.get("title") or block.get("block_type") or "Audit block")
    title = html.escape(raw_title)
    status = html.escape(str(block.get("status") or "recorded"))
    klass = f"audit-block {block_type} {extra_class}".strip()
    purpose = html.escape(str(block.get("purpose") or ""))
    note_html_markup = ""
    marker_html = ""
    if note_parts and note_collector is not None:
        klass = f"{klass} note-anchor"
        marker_html = render_note_marker(projection_plane=ProjectionPlane.AUDIT)
        note_html_markup = note_collector.add(title=raw_title, paragraphs=note_parts)
    elif note_parts:
        klass = f"{klass} note-anchor"
        marker_html = render_note_marker(projection_plane=ProjectionPlane.AUDIT)
        note_html_markup = _legacy_inline_note_markup(note_parts)
    purpose_html = (
        f'<p class="audit-purpose">{purpose}</p>'
        if purpose and not block_type.startswith("run_") and not note_html_markup
        else ""
    )
    return (
        f"<div class=\"{klass}\" id=\"{block_id}\" data-block-type=\"{block_type}\">"
        f"<h3>{title}{marker_html}</h3>"
        f"{purpose_html}{body}{note_html_markup}"
        "</div>"
    )


def _block_purpose_note(block: dict[str, Any], *, role: str) -> list[NoteParagraph]:
    purpose = str(block.get("purpose") or "").strip()
    return [note_text(role, purpose)] if purpose else []


def _inline_note_markup(note_parts: list[NoteParagraph]) -> str:
    if _legacy_renderer_enabled():
        return _legacy_inline_note_markup(note_parts)
    clean = [part for part in note_parts if part.html.strip()]
    if not clean:
        return ""
    return render_audit_block_inline_note(
        AuditBlockInlineNoteContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_INLINE_NOTE,
            label_html=Markup(html.escape(note_label(clean))),
            paragraphs_html=tuple(Markup(part.html) for part in clean),
        )
    )


def _legacy_inline_note_markup(note_parts: list[NoteParagraph]) -> str:
    clean = [part for part in note_parts if part.html.strip()]
    if not clean:
        return ""
    paragraphs = "".join(f"<p>{part.html}</p>" for part in clean)
    return (
        '<aside class="note" role="note">'
        f'<div class="note-label">{html.escape(note_label(clean))}</div>'
        f"{paragraphs}</aside>"
    )


def _summary_card(title: str, row: dict[str, Any]) -> str:
    if _legacy_renderer_enabled():
        return _legacy_summary_card(title, row)
    if not row:
        return ""
    visible = {key: value for key, value in row.items() if value not in (None, "")}
    if not visible:
        return ""
    return render_audit_block_summary_panel(
        AuditBlockSummaryPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL,
            title_html=Markup(html.escape(title)),
            table_html=Markup(render_table([visible])),
        )
    )


def _legacy_summary_card(title: str, row: dict[str, Any]) -> str:
    if not row:
        return ""
    visible = {key: value for key, value in row.items() if value not in (None, "")}
    if not visible:
        return ""
    return (
        f"<div class=\"summary-panel\"><h4>{html.escape(title)}</h4>"
        f"{_legacy_render_table([visible])}</div>"
    )


def _technical_trace(block: dict[str, Any], *, extra_rows: list[dict[str, Any]] | None = None) -> str:
    if _legacy_renderer_enabled():
        return _legacy_technical_trace(block, extra_rows=extra_rows)
    operation_refs = block.get("operation_refs") if isinstance(block.get("operation_refs"), list) else []
    evidence_refs = block.get("evidence_refs") if isinstance(block.get("evidence_refs"), dict) else {}
    links = block.get("links") if isinstance(block.get("links"), dict) else {}
    technical_rows = [row for row in (extra_rows or []) if isinstance(row, dict)]
    if extra_rows:
        technical_rows = [row for row in extra_rows if isinstance(row, dict)]
    body = ""
    if operation_refs:
        body += _titled_fragment(
            "Operations included",
            render_table([row for row in operation_refs if isinstance(row, dict)], technical=True),
        )
    if evidence_refs:
        body += _titled_fragment(
            "Artifact and evidence references",
            render_table(_mapping_rows(evidence_refs), technical=True),
        )
    if links:
        body += _titled_fragment("Workbench links", render_table(_mapping_rows(links), technical=True))
    if technical_rows:
        body += _titled_fragment("Additional technical payloads", render_table(technical_rows, technical=True))
    body_html = body or render_report_paragraph_fragment(
        projection_plane=ProjectionPlane.AUDIT,
        body_html=Markup("No traceability rows."),
        paragraph_class="muted",
    )
    return render_audit_block_technical_trace(
        AuditBlockTechnicalTraceContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_TECHNICAL_TRACE,
            body_html=Markup(body_html),
        )
    )


def _legacy_technical_trace(block: dict[str, Any], *, extra_rows: list[dict[str, Any]] | None = None) -> str:
    operation_refs = block.get("operation_refs") if isinstance(block.get("operation_refs"), list) else []
    evidence_refs = block.get("evidence_refs") if isinstance(block.get("evidence_refs"), dict) else {}
    links = block.get("links") if isinstance(block.get("links"), dict) else {}
    technical_rows = [row for row in (extra_rows or []) if isinstance(row, dict)]
    if extra_rows:
        technical_rows = [row for row in extra_rows if isinstance(row, dict)]
    body = ""
    if operation_refs:
        body += "<h4>Operations included</h4>" + _legacy_render_table(
            [row for row in operation_refs if isinstance(row, dict)],
            technical=True,
        )
    if evidence_refs:
        body += "<h4>Artifact and evidence references</h4>" + _legacy_render_table(
            _mapping_rows(evidence_refs),
            technical=True,
        )
    if links:
        body += "<h4>Workbench links</h4>" + _legacy_render_table(_mapping_rows(links), technical=True)
    if technical_rows:
        body += "<h4>Additional technical payloads</h4>" + _legacy_render_table(technical_rows, technical=True)
    body_html = body or '<p class="muted">No traceability rows.</p>'
    return (
        "<div class=\"technical-trace\">"
        "<h4>Technical trace: operation records and artifact links</h4>"
        f"{body_html}</div>"
    )


def _plot_unavailable(path: str) -> str:
    if _legacy_renderer_enabled():
        return _legacy_plot_unavailable(path)
    return render_audit_block_plot_panel(
        AuditBlockPlotPanelContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_BLOCK_PLOT_PANEL,
            has_spec=False,
            audit_plot_type_html=Markup(""),
            plot_id_html=Markup(""),
            caption_html=Markup(""),
            warning_html=Markup(""),
            fallback_message_html=Markup(
                f"Plot unavailable: missing {html.escape(path)}. Review the archived analysis evidence."
            ),
        )
    )


def _legacy_plot_unavailable(path: str) -> str:
    return (
        "<div class=\"plot-unavailable\">"
        f"Plot unavailable: missing {html.escape(path)}. "
        "Review the archived analysis evidence."
        "</div>"
    )


def _curve_values(rows: list[dict[str, Any]], series: str, *, max_rows: int) -> list[dict[str, Any]]:
    values = []
    for row in _downsample(rows, max_rows):
        strain = _as_float(row.get("mean_strain") or row.get("strain_mm_per_mm"))
        stress = _as_float(row.get("stress_MPa"))
        if strain is None or stress is None:
            continue
        values.append(
            {
                "strain": strain * 100.0,
                "stress": stress,
                "point_index": _as_float(row.get("point_index")),
                "series": series,
            }
        )
    return values


def _front_rear_trace_values(rows: list[dict[str, Any]], *, max_rows: int) -> list[dict[str, Any]]:
    values = []
    for row in _downsample(rows, max_rows):
        stress = _as_float(row.get("stress_MPa"))
        front = _as_float(row.get("front_strain_abs") or row.get("front_strain"))
        rear = _as_float(row.get("rear_strain_abs") or row.get("rear_strain"))
        point_index = _as_float(row.get("point_index"))
        if stress is None:
            continue
        for series, strain in (("front strain", front), ("rear strain", rear)):
            if strain is None:
                continue
            values.append(
                {
                    "gauge_strain": strain * 100.0,
                    "stress": stress,
                    "point_index": point_index,
                    "series": series,
                }
            )
    return values


def _strain_envelope_values(rows: list[dict[str, Any]], *, max_rows: int) -> list[dict[str, Any]]:
    values = []
    for row in _downsample(rows, max_rows):
        stress = _as_float(row.get("stress_MPa"))
        front = _as_float(row.get("front_strain_abs") or row.get("front_strain"))
        rear = _as_float(row.get("rear_strain_abs") or row.get("rear_strain"))
        if stress is None or front is None or rear is None:
            continue
        lower = min(front, rear) * 100.0
        upper = max(front, rear) * 100.0
        values.append(
            {
                "strain_min": lower,
                "strain_max": upper,
                "stress": stress,
                "point_index": _as_float(row.get("point_index")),
                "series": "front/rear strain agreement envelope",
            }
        )
    return values


def _stress_markers(
    block: dict[str, Any],
    bounded_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    markers = block.get("markers") if isinstance(block.get("markers"), dict) else {}
    start_index = _as_float(_nested(markers, "experiment_start", "index"))
    end_index = _as_float(_nested(markers, "experiment_end", "index"))
    max_index = _as_float(_nested(markers, "max_load_strength", "index"))
    rows = bounded_rows
    start = _row_at_index(rows, start_index) or (bounded_rows[0] if bounded_rows else {})
    end = _row_at_index(rows, end_index) or (bounded_rows[-1] if bounded_rows else {})
    max_row = _row_at_index(rows, max_index) or end
    out = []
    marker_specs: list[tuple[str, dict[str, Any], float | None]] = [
        (START_MARKER_LABEL, start, start_index),
    ]
    if _same_index(end_index, max_index):
        marker_specs.append((END_MAX_FAILURE_MARKER_LABEL, max_row or end, max_index if max_index is not None else end_index))
    else:
        marker_specs.extend(
            [
                (END_MARKER_LABEL, end, end_index),
                (MAX_FAILURE_MARKER_LABEL, max_row, max_index),
            ]
        )
    for label, row, marker_index in marker_specs:
        strain = _as_float(row.get("mean_strain") or row.get("strain_mm_per_mm"))
        stress = _as_float(row.get("stress_MPa")) or _as_float(_nested(markers, "max_load_strength", "stress_MPa"))
        if strain is None or stress is None:
            continue
        out.append({"marker": label, "strain": strain * 100.0, "stress": stress, "point_index": marker_index})
    return out


def _same_index(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and abs(left - right) <= 1e-9


def _chord_line_values(block: dict[str, Any]) -> list[dict[str, Any]]:
    line = _nested(block, "markers", "chord_line") or {}
    points = [
        ("chord start 0.0005", _as_float(line.get("x_start")), _as_float(line.get("y_start"))),
        ("chord end 0.0025", _as_float(line.get("x_end")), _as_float(line.get("y_end"))),
    ]
    return [
        {"label": label, "strain": x * 100.0, "stress": y, "series": "chord line"}
        for label, x, y in points
        if x is not None and y is not None
    ]


def _bending_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        front = _as_float(row.get("front_strain_abs") or row.get("front_strain"))
        rear = _as_float(row.get("rear_strain_abs") or row.get("rear_strain"))
        load = _as_float(row.get("load_N"))
        if front is None or rear is None or load is None:
            continue
        denominator = abs(front + rear)
        if denominator == 0:
            continue
        out.append(
            {
                "point_index": _as_float(row.get("point_index")),
                "load_N": abs(load),
                "bending_percent": abs(front - rear) / denominator * 100.0,
            }
        )
    return out


def _segment_values(block: dict[str, Any], *, max_y: float) -> list[dict[str, Any]]:
    segments = _nested(block, "markers", "exceedance_segments")
    if not isinstance(segments, list):
        return []
    rows = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = _as_float(segment.get("start_load_N"))
        end = _as_float(segment.get("end_load_N"))
        if start is None or end is None:
            continue
        rows.append(
            {
                "start_load_N": min(start, end),
                "end_load_N": max(start, end),
                "y1": 0.0,
                "y2": max_y * 1.08,
                "segment_classification": segment.get("segment_classification", ""),
            }
        )
    return rows


def _aggregate_curve_values(
    aligned_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]],
    diagnostic_scores: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    classification_by_run = {
        str(row.get("run_id") or ""): str(row.get("diagnostic_classification") or "CURVE_SHAPE_NOT_ASSESSED")
        for row in diagnostic_scores
        if isinstance(row, dict)
    }
    curves = []
    grouped: dict[float, list[float]] = {}
    if aligned_rows:
        for row in aligned_rows:
            run_id = str(row.get("run_id") or "")
            stress = _as_float(row.get("y_observed", row.get("y_aligned")))
            x_value = _x_common_percent(row)
            if stress is None or x_value is None:
                continue
            curves.append(
                {
                    "x": x_value,
                    "stress": stress,
                    "run_id": run_id,
                    "diagnostic_classification": classification_by_run.get(run_id, "CURVE_SHAPE_NOT_ASSESSED"),
                    **_score_tooltip_fields(diagnostic_scores, run_id),
                }
            )
            grouped.setdefault(round(float(x_value), 8), []).append(stress)
    else:
        for row in fallback_curves:
            run_id = str(row.get("run_id") or "")
            stress = _as_float(row.get("stress_MPa"))
            x_value = _x_common_percent(row)
            if x_value is None or stress is None:
                continue
            curves.append(
                {
                    "x": x_value,
                    "stress": stress,
                    "run_id": run_id,
                    "diagnostic_classification": classification_by_run.get(run_id, "CURVE_SHAPE_NOT_ASSESSED"),
                    **_score_tooltip_fields(diagnostic_scores, run_id),
                }
            )
            grouped.setdefault(round(float(x_value), 8), []).append(stress)
    stats = []
    for x_value, stresses in sorted(grouped.items()):
        avg = mean(stresses)
        std = _stddev(stresses)
        stats.append(
            {
                "x": x_value,
                "stress": avg,
                "std_lower": avg - std,
                "std_upper": avg + std,
                "n": len(stresses),
            }
        )
    return curves, stats


def _aggregate_curve_encoding(*, detail: bool = False) -> dict[str, Any]:
    encoding: dict[str, Any] = {
        "x": {"field": "x", "type": "quantitative", "title": "Normalised strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "color": {
            "field": "diagnostic_classification",
            "type": "nominal",
            "title": "Curve-shape state",
            "scale": _curve_shape_color_scale(),
        },
        "tooltip": [
            {"field": "run_id", "type": "nominal", "title": "Run"},
            {"field": "x", "type": "quantitative", "title": "Normalised strain / %", "format": ".2f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "distance_rms", "type": "quantitative", "title": "distance_rms", "format": ".4f"},
            {"field": "distance_rank", "type": "nominal", "title": "distance_rank"},
            {"field": "Qexp", "type": "nominal", "title": "Qexp"},
            {"field": "Qcrit_95", "type": "nominal", "title": "Qcrit_95"},
            {"field": "threshold_method", "type": "nominal", "title": "threshold_method"},
            {"field": "diagnostic_classification", "type": "nominal", "title": "classification"},
        ],
    }
    if detail:
        encoding["detail"] = {"field": "run_id"}
    return encoding


def _average_curve_encoding() -> dict[str, Any]:
    encoding = _curve_encoding(preserve_point_order=True)
    encoding["color"] = _strain_trace_color_encoding()
    return encoding


def _curve_encoding(*, preserve_point_order: bool = False) -> dict[str, Any]:
    encoding = {
        "x": {"field": "strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "tooltip": [
            {"field": "series", "type": "nominal", "title": "Evidence"},
            {"field": "strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "point_index", "type": "quantitative", "title": "Point index"},
        ],
    }
    if preserve_point_order:
        encoding["order"] = {"field": "point_index", "type": "quantitative"}
    return encoding


def _gauge_trace_encoding() -> dict[str, Any]:
    return {
        "x": {"field": "gauge_strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "order": {"field": "point_index", "type": "quantitative"},
        "color": _strain_trace_color_encoding(),
        "tooltip": [
            {"field": "series", "type": "nominal", "title": "Evidence"},
            {"field": "gauge_strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "point_index", "type": "quantitative", "title": "Point index"},
        ],
    }


def _strain_trace_color_encoding() -> dict[str, Any]:
    return {
        "field": "series",
        "type": "nominal",
        "title": "Strain traces",
        "scale": {
            "domain": ["average strain curve", "front strain", "rear strain"],
            "range": ["#1f78b4", "#8aa8c4", "#b1bfd0"],
        },
    }


def _point_encoding(label_field: str) -> dict[str, Any]:
    return {
        "x": {"field": "strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "tooltip": [
            {"field": label_field, "type": "nominal", "title": "Marker"},
            {"field": "strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
        ],
    }


def _plot_config() -> dict[str, Any]:
    return {
        "axis": {"labelFontSize": 11, "titleFontSize": 12},
        "legend": {"labelLimit": 160, "titleFontSize": 12, "labelFontSize": 11},
        "view": {"stroke": "#d7dde5"},
    }


def _outlier_review_discharge_rows(result: Any) -> list[dict[str, Any]]:
    flags = getattr(result, "run_flags", None) or []
    discharged = getattr(result, "discharged_runs", None) or []
    rows = []
    for row in flags:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "run_id": row.get("run_id"),
                "reason": row.get("reason") or row.get("message") or row.get("description"),
                "category": row.get("category") or row.get("source"),
                "data_consequence": row.get("consequence") or row.get("state") or "",
                "final_report_consequence": "",
            }
        )
    for row in discharged:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "run_id": row.get("run_id"),
                "reason": row.get("reason"),
                "category": row.get("category", "discharge"),
                "data_consequence": row.get("state", row.get("machine_consequence", "")),
                "final_report_consequence": row.get("final_consequence") or "not in final report runs",
            }
        )
    return rows


def _compact_flag_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "flag": row.get("flag_id") or row.get("rule_id") or row.get("source"),
            "category": row.get("category"),
            "reason": row.get("reason") or row.get("message") or row.get("description"),
            "consequence": row.get("consequence") or row.get("state"),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def _validation_evidence_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        evidence_rows.append(
            {
                "evidence_item": row.get("label") or row.get("metric") or row.get("check_id") or row.get("field") or "validation item",
                "deviation_state": row.get("status") or row.get("state") or "",
                "observed_value": row.get("observed") or row.get("actual") or row.get("value") or row.get("measured_value") or "",
                "reference_value": row.get("expected") or row.get("reference") or row.get("reference_value") or "",
                "limit": row.get("limit") or row.get("tolerance") or "",
                "meaning": row.get("message") or row.get("reason") or row.get("description") or "",
            }
        )
    return evidence_rows


def _report_inclusion_evidence(
    summary: dict[str, Any],
    selection: dict[str, Any],
    flags: list[dict[str, Any]],
) -> dict[str, Any]:
    included = summary.get("final_included")
    if included in (None, ""):
        included = _final_included(selection, summary)
    included_recorded = included not in (None, "")
    included_bool = _truthy(included) if included_recorded else False
    reason = _selection_reason(selection) or summary.get("reason") or _primary_flag_reason(flags)
    evidence_state = _machine_state(selection)
    if evidence_state in (None, ""):
        evidence_state = "accepted" if included_bool else "excluded"
    row = {
        "run_id": selection.get("run_id") or summary.get("run_id"),
        "data_evidence_state": evidence_state,
        "final_report_use": "Included" if included_bool else "Excluded" if included_recorded else "Not recorded",
        "reason": reason,
        "aggregate_effect": "Used in aggregate statistics" if included_bool else "Not used in aggregate statistics" if included_recorded else "No aggregate use recorded",
    }
    decision = summary.get("human_decision") or selection.get("human_decision") or selection.get("human_decision_type")
    if decision:
        row["operator_record"] = decision
    return row


def _primary_flag_reason(flags: list[dict[str, Any]]) -> str:
    for row in flags:
        if not isinstance(row, dict):
            continue
        reason = row.get("reason") or row.get("message") or row.get("description")
        if reason:
            return str(reason)
    return ""


def _stress_conclusion(summary: dict[str, Any], compact: dict[str, Any]) -> dict[str, Any]:
    return {
        "bounded_reduction": summary.get("bounded_reduction"),
        "boundary_policy": compact.get("boundary_policy"),
        "strength": compact.get("strength"),
        "failure_strain": compact.get("failure_strain"),
        "modulus": compact.get("modulus"),
    }


def _stress_technical_rows(block: dict[str, Any]) -> list[dict[str, Any]]:
    markers = block.get("markers") if isinstance(block.get("markers"), dict) else {}
    return [
        {"technical_item": "chord_anchors", "value": markers.get("chord_anchors")},
        {"technical_item": "chord_line", "value": markers.get("chord_line")},
    ]


def _bending_technical_rows(block: dict[str, Any]) -> list[dict[str, Any]]:
    segments = _nested(block, "markers", "exceedance_segments")
    return [{"technical_item": "raw_exceedance_segments", "value": segments}]


def _bending_evidence_consequence(summary: dict[str, Any]) -> str:
    classification = str(summary.get("classification") or "")
    if classification.startswith("FAIL"):
        return "bending evidence flag"
    if classification.startswith("WARN"):
        return "review evidence"
    if classification == "PASS_WITH_SPIKES":
        return "spike evidence recorded"
    return "no bending alert"


def _human_bending_consequence(compact: dict[str, Any]) -> str:
    classification = str(compact.get("classification") or "")
    if classification == "PASS":
        return "Bending stayed within the limit for this run."
    if classification == "PASS_WITH_SPIKES":
        return "Brief bending spikes were recorded; review the plot for context."
    if classification.startswith("WARN"):
        return "Bending evidence should be reviewed before accepting the run."
    if classification.startswith("FAIL"):
        return "Bending exceeded the sustained limit and is evidence for review."
    consequence = str(compact.get("diagnostic_consequence") or "")
    return consequence.replace("_", " ") if consequence else "No bending interpretation recorded."


def _human_operator_validity(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Not recorded"
    return text.replace("_", " ").capitalize()


def _human_failure_observation(value: Any) -> str:
    text = str(value or "").strip()
    normalized = text.casefold()
    if not normalized:
        return "Not recorded"
    if normalized in {"1", "true", "valid", "accepted", "pass", "none", "no"}:
        return "No"
    if normalized in {"0", "false", "invalid", "rejected", "fail", "failure", "yes"}:
        return "Yes"
    return f"Detail: {text}"


def _bending_segment_sentence(compact: dict[str, Any]) -> str:
    points = compact.get("longest_segment_points")
    fraction = compact.get("longest_segment_fraction")
    segment_type = str(compact.get("segment_type") or "")
    if points in (None, "") and fraction in (None, "") and not segment_type:
        return "No continuous above-threshold segment."
    pieces = []
    if points not in (None, ""):
        pieces.append(f"{_display(points)} points")
    if fraction not in (None, ""):
        pieces.append(f"{_display(_fraction_to_percent(fraction))}% of assessed window")
    if segment_type:
        pieces.append(segment_type.replace("_", " "))
    return "; ".join(pieces)


def _bending_extent_sentence(compact: dict[str, Any]) -> str:
    points = compact.get("points_above_threshold")
    fraction = compact.get("fraction_above_threshold")
    segment = _bending_segment_sentence(compact)
    pieces = []
    if points not in (None, ""):
        pieces.append(f"{_display(points)} points above limit")
    if fraction not in (None, ""):
        pieces.append(f"{_display(_fraction_to_percent(fraction))}% of assessed window")
    if segment and segment != "No continuous above-threshold segment.":
        segment_parts = [
            part
            for part in segment.split("; ")
            if "points" not in part and "% of assessed window" not in part
        ]
        pieces.extend(segment_parts)
    return "; ".join(pieces) if pieces else "No above-threshold points."


def _human_curve_state(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "PASS": "Pass",
        "PASS_WITH_SPIKES": "Pass with brief spikes",
        "FAIL_SUSTAINED_BENDING": "Sustained bending above limit",
        "WARN_TRANSIENT": "Transient bending warning",
        "CURVE_SHAPE_NORMAL": "Curve shape matches the cohort",
        "CURVE_SHAPE_OUTLIER": "Curve shape differs from the cohort",
        "INSUFFICIENT_CURVE_DATA": "Not enough curve data for this run",
        "INSUFFICIENT_COHORT_SIZE": "Not enough comparable runs",
        "CURVE_SHAPE_NOT_ASSESSED": "Curve shape not assessed",
    }
    return replacements.get(text, text.replace("_", " ").title() if text else "")


def _human_threshold_method(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "dixon_high_outlier_q_test": "Dixon high-outlier Q-test (threshold_method)",
        "robust_mad_zscore": "Upper-tail robust MAD z-score (threshold_method)",
        "insufficient_cohort_size": "Insufficient cohort size (threshold_method)",
    }
    return replacements.get(text, text.replace("_", " ") if text else "")


def _cohort_threshold_description(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "dixon_high_outlier_q_test": "Dixon high-outlier Q-test at 95% confidence (dixon_high_outlier_q_test)",
        "robust_mad_zscore": "Upper-tail robust MAD z-score (robust_mad_zscore)",
        "insufficient_cohort_size": "Insufficient cohort size (insufficient_cohort_size)",
        "not_assessed": "Not assessed",
    }
    return replacements.get(text, text.replace("_", " ") if text else "-")


def _curve_shape_threshold_method(scores: list[dict[str, Any]], cohorts: list[dict[str, Any]]) -> str:
    return str(
        _first_value(scores, "threshold_method")
        or _first_value(cohorts, "threshold_branch_used")
        or _first_value(cohorts, "threshold_method")
        or ""
    )


def _curve_shape_method_note(scores: list[dict[str, Any]], cohorts: list[dict[str, Any]], threshold_method: str) -> str:
    n = (
        _first_value(scores, "effective_sample_size")
        or _first_value(cohorts, "evaluable_curves")
        or _first_value(cohorts, "effective_sample_size")
        or "-"
    )
    base = (
        "Each reduced stress-strain curve is compared against the cohort reference curve. "
        "The score is the RMS of local standardized residuals: "
        "<code>z(x) = [stress_run(x) - cohort_mean(x)] / cohort_std(x)</code>; "
        "<code>distance_rms = sqrt(mean(z(x)^2))</code>. "
    )
    if threshold_method == "robust_mad_zscore":
        return (
            base
            + f"This cohort has n={html.escape(str(n))} comparable curves, so the large-cohort branch reports "
            "a modified MAD screening score from the signed value "
            "<code>z_mad = (distance_rms - median(distance_rms)) / scaled_MAD</code>. "
            "Because <code>distance_rms</code> is already a non-negative difference score, the decision is one-sided: "
            "only unusually high distances are outlier evidence. The bar chart therefore shows "
            "<code>max(0, z_mad)</code> against the positive upper cutoff <code>z_crit</code>. "
            "This is a robust screening rule; if <code>MAD=0</code> the statistic is marked undefined instead of "
            "being forced with an artificial epsilon."
        )
    if threshold_method == "dixon_high_outlier_q_test":
        return (
            base
            + f"This cohort has n={html.escape(str(n))} comparable curves, so the small-cohort branch reports "
            "the Dixon high-outlier Q-test at 95% confidence. Dixon is applied only to the single most distant "
            "run-level distance score and is not repeated sequentially to remove multiple runs. "
            "A companion upper-tail MAD screen is reported on the same run-level distance scores to surface "
            "multiple high-distance candidates that can mask Dixon; it is a robust review flag, not a formal "
            "deletion test."
        )
    return base + "The cohort is marked insufficient when fewer than 3 comparable curves are available."


def _curve_shape_method_rows(
    scores: list[dict[str, Any]],
    cohorts: list[dict[str, Any]],
    *,
    threshold_method: str | None = None,
) -> list[tuple[str, Any]]:
    first_score = _first_with_value(scores, "cohort_id") or (scores[0] if scores else {})
    first_cohort = _first_with_value(cohorts, "cohort_id") or (cohorts[0] if cohorts else {})
    threshold_method = threshold_method or _curve_shape_threshold_method(scores, cohorts)
    rows = [
        ("Cohort ID", first_cohort.get("cohort_id") or first_score.get("cohort_id") or "-"),
        (
            "Comparable curves assessed (n)",
            _first_value(scores, "effective_sample_size")
            or first_cohort.get("evaluable_curves")
            or first_cohort.get("effective_sample_size")
            or "-",
        ),
        ("Distance metric", "RMS standardized residual distance (distance_rms)"),
        ("Threshold rule", _cohort_threshold_description(threshold_method)),
        ("Observation unit", "One distance_rms feature per run; raw curve points are not pooled"),
        ("Automatic exclusion", "No - statistical flags require operator/metrology review"),
    ]
    if threshold_method == "robust_mad_zscore":
        summary = _first_threshold_summary(cohorts)
        rows.extend(
            [
                (
                    "Upper-tail MAD cutoff (z_crit)",
                    _format_float(
                        _first_value(scores, "threshold_value")
                        or summary.get("threshold_value")
                        or summary.get("robust_z_threshold"),
                        3,
                    ),
                ),
                (
                    "Cohort median distance",
                    _format_float(_first_value(scores, "robust_center") or summary.get("robust_center"), 4),
                ),
                (
                    "Scaled MAD distance",
                    _format_float(_first_value(scores, "robust_scaled_mad") or summary.get("robust_scaled_mad"), 4),
                ),
                (
                    "MAD edge-case policy",
                    "MAD=0 is marked not assessed; use robust alternatives or residual review",
                ),
            ]
        )
    else:
        summary = _first_threshold_summary(cohorts)
        rows.append(
            (
                "Critical Q at 95% (Qcrit_95)",
                _format_float(_first_value(scores, "Qcrit_95") or summary.get("Qcrit_95"), 3),
            )
        )
        rows.extend(
            [
                ("Dixon variant", _first_value(scores, "dixon_variant") or summary.get("dixon_variant") or "-"),
                ("Dixon numerator gap", _format_float(_first_value(scores, "dixon_gap") or summary.get("dixon_gap"), 4)),
                (
                    "Dixon denominator",
                    _format_float(_first_value(scores, "dixon_denominator") or summary.get("dixon_denominator"), 4),
                ),
                ("Dixon scope", "Single highest distance only; no sequential retesting"),
                (
                    "Companion screen",
                    "Upper-tail modified MAD masking screen on distance_rms; soft review evidence",
                ),
                (
                    "Companion MAD cutoff (z_crit)",
                    _format_float(
                        _first_value(scores, "threshold_value")
                        or summary.get("threshold_value")
                        or summary.get("robust_z_threshold"),
                        3,
                    ),
                ),
                (
                    "Companion flags",
                    summary.get("masking_companion_flag_count", _first_value(scores, "masking_companion_flag_count") or 0),
                ),
                ("Masking risk", _yes_no(summary.get("masking_risk"))),
            ]
        )
    return rows


def _curve_shape_result_fields(threshold_method: str) -> list[str]:
    fields = ["run_id", "specimen", "distance_rms", "distance_rank"]
    if threshold_method == "robust_mad_zscore":
        fields.extend(["mad_upper_z", "robust_z", "threshold_value"])
    else:
        fields.extend(["dixon_variant", "dixon_gap", "dixon_denominator", "Qexp", "dixon_decision"])
        fields.extend(["mad_upper_z", "masking_companion_flag"])
    fields.extend(["is_curve_shape_outlier", "diagnostic_classification"])
    return fields


def _curve_shape_result_rows(scores: list[dict[str, Any]], *, threshold_method: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scores:
        result_row = {
            "run_id": row.get("run_id"),
            "specimen": row.get("specimen"),
            "distance_rms": _format_float(row.get("distance_rms"), 4),
            "distance_rank": _display_or_dash(row.get("distance_rank")),
            "is_curve_shape_outlier": _yes_no(row.get("is_curve_shape_outlier")),
            "diagnostic_classification": row.get("diagnostic_classification"),
        }
        if threshold_method == "robust_mad_zscore":
            result_row["mad_upper_z"] = _format_float(row.get("mad_upper_z", row.get("z_mad_upper")), 3)
            result_row["robust_z"] = _format_float(row.get("robust_z", row.get("z_mad")), 3)
            result_row["threshold_value"] = _format_float(row.get("threshold_value"), 3)
        else:
            result_row["dixon_variant"] = row.get("dixon_variant")
            result_row["dixon_gap"] = _format_float(row.get("dixon_gap"), 4)
            result_row["dixon_denominator"] = _format_float(row.get("dixon_denominator"), 4)
            result_row["Qexp"] = _format_float(row.get("Qexp"), 3)
            result_row["dixon_decision"] = _display_or_dash(row.get("dixon_decision"))
            result_row["mad_upper_z"] = _format_float(row.get("mad_upper_z", row.get("z_mad_upper")), 3)
            result_row["masking_companion_flag"] = _yes_no(row.get("masking_companion_flag"))
        rows.append(result_row)
    return rows


def _first_threshold_summary(cohorts: list[dict[str, Any]]) -> dict[str, Any]:
    for row in cohorts:
        value = row.get("threshold_summary")
        if isinstance(value, dict):
            return value
    return {}


def _first_with_value(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) not in (None, ""):
            return row
    return {}


def _first_value(rows: list[dict[str, Any]], key: str) -> Any:
    for row in rows:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def _display_or_dash(value: Any) -> Any:
    return "-" if value in (None, "") else value


def _format_float(value: Any, digits: int) -> Any:
    number = _as_float(value)
    if number is None:
        return "-"
    return f"{number:.{digits}g}"


def _fraction_to_percent(value: Any) -> Any:
    number = _as_float(value)
    if number is None:
        return value
    return number * 100.0 if abs(number) <= 1.0 else number


def _curve_shape_outlier_text(summary: dict[str, Any]) -> str:
    if "is_curve_shape_outlier" in summary:
        return _yes_no(summary.get("is_curve_shape_outlier"))
    return "Yes" if str(summary.get("curve_shape_classification") or "") == "CURVE_SHAPE_OUTLIER" else "No"


def _curve_shape_interpretation(summary: dict[str, Any]) -> str:
    classification = str(summary.get("curve_shape_classification") or "")
    note = str(summary.get("distance_note") or "").strip()
    if classification == "CURVE_SHAPE_NORMAL":
        return "The reduced curve shape is consistent with the comparable cohort."
    if classification == "CURVE_SHAPE_OUTLIER":
        return "The reduced curve shape is a statistical shape outlier and should be reviewed."
    if classification == "INSUFFICIENT_CURVE_DATA":
        return "The run did not provide enough reduced-curve data for shape comparison."
    if classification == "INSUFFICIENT_COHORT_SIZE":
        return "The cohort is too small for a curve-shape threshold."
    return note or "No curve-shape interpretation recorded."


def _yes_no(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value).strip().casefold()
    if text in {"1", "true", "yes", "y"}:
        return "Yes"
    if text in {"0", "false", "no", "n"}:
        return "No"
    return str(value or "")


def _longest_segment_fraction(block: dict[str, Any]) -> Any:
    segments = _nested(block, "markers", "exceedance_segments")
    if not isinstance(segments, list) or not segments:
        return ""
    return max((_as_float(row.get("fraction_of_window")) or 0.0 for row in segments if isinstance(row, dict)), default="")


def _longest_segment_type(block: dict[str, Any]) -> Any:
    segments = _nested(block, "markers", "exceedance_segments")
    if not isinstance(segments, list) or not segments:
        return ""
    longest = max(
        (row for row in segments if isinstance(row, dict)),
        key=lambda row: _as_float(row.get("point_count")) or 0,
        default={},
    )
    return longest.get("segment_classification", "")


def _machine_state(selection: dict[str, Any]) -> Any:
    return selection.get("machine_state") or selection.get("acceptance_state") or selection.get("state") or selection.get("included", "")


def _score_tooltip_fields(scores: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    for row in scores:
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id:
            return {
                "specimen": row.get("specimen", ""),
                "distance_rms": row.get("distance_rms", ""),
                "distance_rank": row.get("distance_rank", ""),
                "Qexp": row.get("Qexp", ""),
                "Qcrit_95": row.get("Qcrit_95", ""),
                "threshold_method": row.get("threshold_method", ""),
            }
    return {}


def _curve_shape_color_scale() -> dict[str, Any]:
    return {
        "domain": [
            "CURVE_SHAPE_NORMAL",
            "CURVE_SHAPE_OUTLIER",
            "INSUFFICIENT_CURVE_DATA",
            "INSUFFICIENT_COHORT_SIZE",
            "CURVE_SHAPE_NOT_ASSESSED",
        ],
        "range": ["#78aeda", "#c83f49", "#8a6500", "#9a7fd1", "#7d8794"],
    }


def _final_included(selection: dict[str, Any], summary: dict[str, Any]) -> Any:
    return selection.get("final_included", selection.get("included", summary.get("final_included", "")))


def _final_report_use(value: Any) -> str:
    if str(value).strip().casefold() in {"1", "true", "yes", "included"}:
        return "Included"
    if str(value).strip().casefold() in {"0", "false", "no", "excluded"}:
        return "Excluded"
    return str(value or "")


def _selection_reason(selection: dict[str, Any]) -> Any:
    return selection.get("human_decision_reason") or selection.get("override_reason") or selection.get("reason") or ""


def _is_problematic_selection(selection: dict[str, Any]) -> bool:
    if not selection:
        return False
    if not _truthy(selection.get("final_included", selection.get("included", True))):
        return True
    text = " ".join(str(selection.get(key, "")) for key in ("machine_state", "human_decision", "reason", "state")).casefold()
    return any(token in text for token in ("review", "exclude", "remove", "warning", "fail"))


def _rows_for_run(rows: Any, run_id: str) -> list[dict[str, Any]]:
    return [row for row in rows or [] if isinstance(row, dict) and str(row.get("run_id") or "") == run_id]


def _row_at_index(rows: list[dict[str, Any]], point_index: float | None) -> dict[str, Any] | None:
    if point_index is None:
        return None
    for row in rows:
        value = _as_float(row.get("point_index"))
        if value is not None and abs(value - point_index) < 0.5:
            return row
    return None


def _first_table_row(block: dict[str, Any], table_name: str) -> dict[str, Any]:
    rows = _table_rows(block, table_name)
    return rows[0] if rows else {}


def _table_rows(block: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    tables = block.get("tables") if isinstance(block.get("tables"), dict) else {}
    rows = tables.get(table_name, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _mapping_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [{"item": key, "value": value} for key, value in payload.items()]


def _downsample(rows: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    if len(rows) <= max_rows:
        return rows
    stride = max(1, math.ceil(len(rows) / max_rows))
    return rows[::stride]


def _x_common_percent(row: dict[str, Any]) -> float | None:
    for key in ("analysis_progress", "experiment_progress", "x_common", "x_normalized"):
        value = _as_float(row.get(key))
        if value is not None:
            return value * 100.0 if value <= 1.5 else value
    return None


def _nested(payload: Any, *keys: str) -> Any:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _cell(value: Any, *, technical: bool = False, field: str = "") -> str:
    return html.escape(_display(value, technical=technical, field=field))


def _display(value: Any, *, technical: bool = False, field: str = "") -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True) if technical else "technical trace"
    text = str(value)
    if _is_run_field(field):
        return run_display_label(text)
    if not text.startswith("#"):
        text = replace_run_ids_for_display(text)
    return _display_label(text) if not technical else text


def _is_run_field(field: str) -> bool:
    return str(field or "").strip().casefold() in {"run", "run #", "run_id", "run id"}


def _field_label(label: str) -> str:
    return "Run #" if _is_run_field(label) else label


def _display_label(text: str) -> str:
    labels = {
        "PASS": "Within limit",
        "PASS_WITH_SPIKES": "Within limit with short spikes",
        "WARN_TRANSIENT_BENDING": "Transient bending above limit",
        "FAIL_SUSTAINED_BENDING": "Sustained bending above limit",
        "CURVE_SHAPE_NORMAL": "Matches cohort",
        "CURVE_SHAPE_OUTLIER": "Curve-shape outlier",
        "INSUFFICIENT_CURVE_DATA": "Insufficient curve data",
        "INSUFFICIENT_COHORT_SIZE": "Insufficient cohort size",
        "CURVE_SHAPE_NOT_ASSESSED": "Not assessed",
        "dixon_high_outlier_q_test": "Dixon high-outlier Q-test",
        "robust_mad_zscore": "Upper-tail robust MAD z-score",
        "insufficient_cohort_size": "Insufficient cohort size",
        "whole_comparable_dataset": "Whole comparable dataset",
        "review_required": "Review required",
        "accepted": "Accepted",
        "excluded": "Excluded",
        "recorded": "Available",
        "not_recorded": "Not recorded",
    }
    if text in labels:
        return labels[text]
    return text.replace("_", " ") if "_" in text and len(text) < 60 else text


def _title(value: str) -> str:
    return value.replace("_", " ").title()


_HEADER_LABELS = {
    "95% CI": "95% CI",
    "Fmax": "Fmax / N",
    "Fmax_N": "Fmax / N",
    "area": "Area / mm2",
    "area_mm2": "Area / mm2",
    "boundary_policy": "Boundary policy",
    "data_evidence_state": "Data evidence state",
    "diagnostic_classification": "Curve-shape result",
    "distance_note": "Distance note",
    "distance_rank": "Rank within cohort (distance_rank)",
    "distance_rms": "Curve difference score (distance_rms)",
    "deviation_state": "Deviation state",
    "endpoint_index": "Endpoint index",
    "effective_sample_size": "Comparable curves assessed",
    "failure_strain": "Failure strain",
    "final_report_run_count": "Final report run count",
    "final_report_use": "Final report use",
    "max_bending_percent": "Max bending / %",
    "modulus": "Modulus / MPa",
    "modulus_MPa": "Modulus / MPa",
    "n": "n",
    "observed_value": "Observed value",
    "points_above_threshold": "Points above threshold",
    "Qcrit_95": "95% threshold (Qcrit_95)",
    "Qcrit_note": "Threshold note",
    "Qexp": "Observed Dixon Q (Qexp)",
    "dixon_decision": "Dixon decision",
    "dixon_denominator": "Dixon denominator",
    "dixon_gap": "Dixon numerator gap",
    "dixon_variant": "Dixon variant",
    "masking_companion_flag": "Companion MAD flag",
    "masking_risk": "Masking risk",
    "reference_value": "Reference value",
    "robust_center": "Cohort median distance",
    "robust_scaled_mad": "Scaled MAD distance",
    "robust_z": "Signed MAD z-score (z_mad)",
    "mad_upper_z": "Upper-tail MAD score",
    "z_mad_upper": "Upper-tail MAD score",
    "std": "SD",
    "std_err": "Standard error",
    "strength": "Strength / MPa",
    "strength_MPa": "Strength / MPa",
    "stress_at_0_0005": "Stress at 0.0005 / MPa",
    "stress_at_0_0025": "Stress at 0.0025 / MPa",
    "thickness": "Thickness / mm",
    "thickness_mm": "Thickness / mm",
    "threshold": "Threshold / %",
    "threshold_decision_sources": "Decision evidence source",
    "threshold_value": "Upper-tail MAD cutoff (z_crit)",
    "threshold_method": "Threshold rule (threshold_method)",
    "threshold_percent": "Threshold / %",
    "width": "Width / mm",
    "width_mm": "Width / mm",
    "run": "Run #",
    "run_id": "Run #",
}


def _header_label(value: str) -> str:
    if value in _HEADER_LABELS:
        return _HEADER_LABELS[value]
    for suffix, unit in (
        ("_MPa", "MPa"),
        ("_percent", "%"),
        ("_mm2", "mm2"),
        ("_mm", "mm"),
        ("_N", "N"),
    ):
        if value.endswith(suffix):
            return f"{_title(value[: -len(suffix)])} / {unit}"
    return _title(value)


def _safe_id(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in value).strip("-")
    return safe or "chart"


def _status_class(status: str) -> str:
    text = status.casefold()
    if "fail" in text:
        return "fail"
    if "warn" in text or "review" in text:
        return "warn"
    return "pass"


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
