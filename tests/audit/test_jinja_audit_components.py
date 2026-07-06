from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audit.audit_report_builder import (
    _acceptance_summary,
    _bending_pattern_heading,
    _chart_hint,
    _chord_endpoint_note,
    _legacy_acceptance_summary,
    _legacy_bending_pattern_heading,
    _legacy_chart_hint,
    _legacy_chord_endpoint_note,
    _legacy_grouped_sections_intro,
    _legacy_inspection_log_appendix_purpose,
    _legacy_operation_log_appendix_purpose,
    _legacy_process_section_evidence_purpose,
    _legacy_readiness_summary,
    _legacy_render_component,
    _legacy_technical_appendix_purpose,
    _legacy_unsupported_component_note,
    _legacy_validation_summary,
    _grouped_sections_intro,
    _inspection_log_appendix_purpose,
    _operation_log_appendix_purpose,
    _process_section_evidence_purpose,
    _readiness_summary,
    _render_component,
    _technical_appendix_purpose,
    _unsupported_component_note,
    _validation_summary,
)
from html_renderer.context_models import (
    AuditAcceptanceSummaryContext,
    AuditChartComponentContext,
    AuditComponentContext,
    AuditComponentMicrocopyContext,
    AuditInspectionLogComponentContext,
    AuditOperationLogComponentContext,
    AuditReadinessSummaryContext,
    AuditValidationSummaryContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_audit_acceptance_summary,
    render_audit_chart_component,
    render_audit_component,
    render_audit_component_microcopy,
    render_audit_inspection_log_component,
    render_audit_operation_log_component,
    render_audit_readiness_summary,
    render_audit_validation_summary,
)


def test_non_plot_audit_components_jinja_match_legacy_renderer_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _result()
    components = [
        {"type": "table", "title": "Specimens", "source": "specimen_results.csv"},
        {"type": "summary_table", "title": "Dataset summary", "source": "dataset_summary.csv"},
        {"type": "specimen_results_table", "title": "Specimen results"},
        {"type": "dataset_summary", "title": "Dataset Summary"},
        {"type": "readiness_summary", "title": "Readiness"},
        {"type": "validation_summary", "title": "Validation"},
        {"type": "validation_deviations", "title": "Deviations"},
        {"type": "acceptance_summary", "title": "Acceptance"},
        {"type": "selection_set_table", "title": "Selection"},
        {"type": "discharge_report", "title": "Discharged Runs"},
        {"type": "operation_log", "title": "Operation Log"},
        {"type": "inspection_log", "title": "Inspection Log"},
        {"type": "not_supported", "title": "Unknown"},
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    for component in components:
        jinja_specs: dict[str, dict[str, object]] = {}
        legacy_specs: dict[str, dict[str, object]] = {}

        html = _render_component(result, component, [], jinja_specs)
        legacy_html = _legacy_render_component(result, component, [], legacy_specs)

        assert html == legacy_html
        assert jinja_specs == legacy_specs == {}


def test_audit_plot_wrapper_components_jinja_match_legacy_html_and_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _result()
    curve_rows = _curve_rows()
    components = [
        {"type": "curve_family_plot", "id": "stress_family", "title": "Stress Family"},
        {"type": "operation_overlay", "id": "chord_window", "operation_type": "chord_slope", "title": "Chord Window"},
        {
            "type": "operation_overlay",
            "id": "bending_diagnostic",
            "operation_type": "bending_diagnostic",
            "title": "Bending Diagnostic",
        },
        {"type": "operation_overlay", "operation_type": "unknown_op", "title": "Operation Overlay"},
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    for component in components:
        jinja_specs: dict[str, dict[str, object]] = {}
        legacy_specs: dict[str, dict[str, object]] = {}

        html = _render_component(result, component, curve_rows, jinja_specs)
        legacy_html = _legacy_render_component(result, component, curve_rows, legacy_specs)

        assert html == legacy_html
        assert jinja_specs == legacy_specs
        if component.get("operation_type") != "unknown_op":
            assert jinja_specs
            assert '<div id="' in html
            assert 'class="chart"' in html


def test_audit_summary_helpers_jinja_match_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _result()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _validation_summary(result) == _legacy_validation_summary(result)
    assert _readiness_summary(result) == _legacy_readiness_summary(result)
    assert _acceptance_summary(result) == _legacy_acceptance_summary(result)

    no_checks = _result()
    no_checks.validation_report = {"summary": {}, "checks": []}

    assert _validation_summary(no_checks) == _legacy_validation_summary(no_checks)
    assert _validation_summary(no_checks) == "<p>No reference validation checks were executed.</p>"


def test_audit_component_microcopy_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    assert _chart_hint() == _legacy_chart_hint()
    assert _chord_endpoint_note() == _legacy_chord_endpoint_note()
    assert _bending_pattern_heading() == _legacy_bending_pattern_heading()
    assert _operation_log_appendix_purpose() == _legacy_operation_log_appendix_purpose()
    assert _inspection_log_appendix_purpose() == _legacy_inspection_log_appendix_purpose()
    assert _process_section_evidence_purpose() == _legacy_process_section_evidence_purpose()
    assert _technical_appendix_purpose() == _legacy_technical_appendix_purpose()
    assert _grouped_sections_intro() == _legacy_grouped_sections_intro()
    assert _unsupported_component_note("weird <component>") == _legacy_unsupported_component_note("weird <component>")


def test_audit_component_renderers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _result()
    component = {"type": "operation_log", "title": "Operation Log"}

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _render_component(result, component, [], {}) == _legacy_render_component(result, component, [], {})
    assert _validation_summary(result) == _legacy_validation_summary(result)
    assert _readiness_summary(result) == _legacy_readiness_summary(result)
    assert _acceptance_summary(result) == _legacy_acceptance_summary(result)
    assert _chart_hint() == _legacy_chart_hint()
    assert _chord_endpoint_note() == _legacy_chord_endpoint_note()
    assert _bending_pattern_heading() == _legacy_bending_pattern_heading()
    assert _operation_log_appendix_purpose() == _legacy_operation_log_appendix_purpose()
    assert _inspection_log_appendix_purpose() == _legacy_inspection_log_appendix_purpose()
    assert _process_section_evidence_purpose() == _legacy_process_section_evidence_purpose()
    assert _technical_appendix_purpose() == _legacy_technical_appendix_purpose()
    assert _grouped_sections_intro() == _legacy_grouped_sections_intro()
    assert _unsupported_component_note("weird") == _legacy_unsupported_component_note("weird")


def test_audit_component_recipe_projections_are_explicit() -> None:
    component_projection = projection_for(RecipeResultKind.AUDIT_COMPONENT)
    microcopy_projection = projection_for(RecipeResultKind.AUDIT_COMPONENT_MICROCOPY)
    validation_projection = projection_for(RecipeResultKind.AUDIT_VALIDATION_SUMMARY)
    readiness_projection = projection_for(RecipeResultKind.AUDIT_READINESS_SUMMARY)
    acceptance_projection = projection_for(RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY)
    operation_projection = projection_for(RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT)
    inspection_projection = projection_for(RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT)
    chart_projection = projection_for(RecipeResultKind.AUDIT_CHART_COMPONENT)

    assert component_projection.context_model == "AuditComponentContext"
    assert component_projection.template_name == "components/typography/heading_fragment.html.j2"
    assert component_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert microcopy_projection.context_model == "AuditComponentMicrocopyContext"
    assert microcopy_projection.template_name == "components/typography/audit_microcopy.html.j2"
    assert microcopy_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert validation_projection.context_model == "AuditValidationSummaryContext"
    assert readiness_projection.template_name == "sections/audit/readiness_summary.html.j2"
    assert acceptance_projection.context_model == "AuditAcceptanceSummaryContext"
    assert operation_projection.context_model == "AuditOperationLogComponentContext"
    assert operation_projection.template_name == "sections/audit/log_component.html.j2"
    assert inspection_projection.context_model == "AuditInspectionLogComponentContext"
    assert inspection_projection.template_name == "sections/audit/log_component.html.j2"
    assert chart_projection.context_model == "AuditChartComponentContext"
    assert chart_projection.template_name == "components/plots/audit_chart_component.html.j2"

    component_html = render_audit_component(
        AuditComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT,
            title_html=Markup("Title"),
            body_html=Markup("<p>Body</p>"),
        )
    )
    microcopy_html = render_audit_component_microcopy(
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            microcopy_kind="unsupported_component_note",
            component_type_html=Markup("unknown"),
            body_html=Markup("<p>Unsupported audit component: unknown</p>"),
        )
    )
    validation_html = render_audit_validation_summary(
        AuditValidationSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
            summary_html=Markup("<p>No reference validation checks were executed.</p>"),
            has_checks=False,
            status_html=Markup("UNKNOWN"),
            status_class="status-unknown",
            checks_html=Markup("0"),
            passed_html=Markup("0"),
            warnings_html=Markup("0"),
            failed_html=Markup("0"),
            deviations_table_html=Markup("<p>No rows.</p>"),
        )
    )
    readiness_html = render_audit_readiness_summary(
        AuditReadinessSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_READINESS_SUMMARY,
            summary_html=Markup(
                '<p>Readiness status: <span class="status-pass">READY</span>. '
                "Execution-critical passed: 2 / 2; missing inputs: 0; blocks execution: False.</p>"
            ),
            status_html=Markup("READY"),
            status_class="status-pass",
            execution_critical_passed_html=Markup("2"),
            execution_critical_total_html=Markup("2"),
            missing_total_html=Markup("0"),
            blocks_execution_html=Markup("False"),
            readiness_table_html=Markup("<p>No rows.</p>"),
            missing_inputs_heading_html=Markup("<h4>Missing or Warning Inputs</h4>"),
            missing_inputs_table_html=Markup("<p>No rows.</p>"),
        )
    )
    acceptance_html = render_audit_acceptance_summary(
        AuditAcceptanceSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY,
            summary_html=Markup(
                "<p>Default selection set: <code>machine</code>. Runs: 2; accepted: 1; warnings: 1; "
                "review: 0; excluded: 0; flags: 0.</p>"
                "<p>Final report selection: <code>operator</code>; selection source: <code>manual</code>; "
                "final included runs: 2; human decisions recorded: 1.</p>"
                "<p>Deep inspection entry point: <code>tools/run_method_development.py</code>.</p>"
            ),
            default_selection_html=Markup("machine"),
            total_runs_html=Markup("2"),
            accepted_html=Markup("1"),
            accepted_with_warning_html=Markup("1"),
            review_required_html=Markup("0"),
            excluded_html=Markup("0"),
            total_flags_html=Markup("0"),
            final_selection_html=Markup("operator"),
            selection_source_html=Markup("manual"),
            final_included_html=Markup("2"),
            human_decisions_html=Markup("1"),
            acceptance_table_html=Markup("<p>No rows.</p>"),
            curve_summary_heading_html=Markup("<h4>Curve-Family Assessment</h4>"),
            curve_summary_table_html=Markup("<p>No rows.</p>"),
            curve_scores_table_html=Markup("<p>No rows.</p>"),
            final_runs_heading_html=Markup("<h4>Final Report Runs</h4>"),
            final_runs_table_html=Markup("<p>No rows.</p>"),
            override_ledger_heading_html=Markup("<h4>Human Override Ledger</h4>"),
            override_ledger_table_html=Markup("<p>No rows.</p>"),
        )
    )
    operation_html = render_audit_operation_log_component(
        AuditOperationLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT,
            title_html=Markup("Operations"),
            purpose_html=Markup(_operation_log_appendix_purpose()),
            summary_table_html=Markup("<p>summary</p>"),
            preview_table_html=Markup("<p>preview</p>"),
            raw_evidence_note_html=Markup("<p>raw</p>"),
        )
    )
    inspection_html = render_audit_inspection_log_component(
        AuditInspectionLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT,
            title_html=Markup("Inspections"),
            purpose_html=Markup(_inspection_log_appendix_purpose()),
            summary_table_html=Markup("<p>summary</p>"),
            preview_table_html=Markup("<p>preview</p>"),
            raw_evidence_note_html=Markup("<p>raw</p>"),
        )
    )
    chart_html = render_audit_chart_component(
        AuditChartComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_CHART_COMPONENT,
            title_html=Markup("Chart"),
            chart_id_html=Markup("chart-id"),
            chart_hint_html=Markup("<p>hint</p>"),
            after_chart_html=Markup("<p>after</p>"),
        )
    )

    assert component_html == "<h3>Title</h3><p>Body</p>"
    assert microcopy_html == "<p>Unsupported audit component: unknown</p>"
    assert validation_html == "<p>No reference validation checks were executed.</p>"
    assert "Missing or Warning Inputs" in readiness_html
    assert "Curve-Family Assessment" in acceptance_html
    assert "Operation-level replay belongs in the Workbench" in operation_html
    assert "Full inspection records remain in the MTDA and Workbench" in inspection_html
    assert chart_html == '<h3>Chart</h3><p>hint</p><div id="chart-id" class="chart"></div><p>after</p>'


def test_audit_component_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditComponentContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT,
            title_html=Markup("Title"),
            body_html=Markup("<p>Body</p>"),
        )

    with pytest.raises(ValueError, match="audit_component"):
        AuditComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TABLE,
            title_html=Markup("Title"),
            body_html=Markup("<p>Body</p>"),
        )

    with pytest.raises(ValueError, match="audit_component_microcopy"):
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT,
            microcopy_kind="chart_hint",
            component_type_html=Markup(""),
            body_html=Markup("<p>hint</p>"),
        )

    with pytest.raises(ValueError, match="known audit component microcopy variant"):
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            microcopy_kind="surprising",
            component_type_html=Markup(""),
            body_html=Markup("<p>hint</p>"),
        )

    with pytest.raises(ValueError, match="component_type_html must be an HTML-safe Markup fragment"):
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            microcopy_kind="unsupported_component_note",
            component_type_html="unknown",
            body_html=Markup("<p>Unsupported audit component: unknown</p>"),
        )

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        AuditComponentMicrocopyContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT_MICROCOPY,
            microcopy_kind="unsupported_component_note",
            component_type_html=Markup("unknown"),
            body_html="<p>Unsupported audit component: unknown</p>",
        )

    with pytest.raises(ValueError, match="body_html must be an HTML-safe Markup fragment"):
        AuditComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_COMPONENT,
            title_html=Markup("Title"),
            body_html="<p>Body</p>",
        )

    with pytest.raises(ValueError, match="has_checks must be a boolean"):
        AuditValidationSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
            summary_html=Markup("<p>Summary</p>"),
            has_checks="yes",
            status_html=Markup("PASS"),
            status_class="status-pass",
            checks_html=Markup("1"),
            passed_html=Markup("1"),
            warnings_html=Markup("0"),
            failed_html=Markup("0"),
            deviations_table_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="summary_html must be an HTML-safe Markup fragment"):
        AuditValidationSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_VALIDATION_SUMMARY,
            summary_html="<p>Summary</p>",
            has_checks=True,
            status_html=Markup("PASS"),
            status_class="status-pass",
            checks_html=Markup("1"),
            passed_html=Markup("1"),
            warnings_html=Markup("0"),
            failed_html=Markup("0"),
            deviations_table_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="missing_inputs_heading_html must be an HTML-safe Markup fragment"):
        AuditReadinessSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_READINESS_SUMMARY,
            summary_html=Markup("<p>Summary</p>"),
            status_html=Markup("READY"),
            status_class="status-pass",
            execution_critical_passed_html=Markup("2"),
            execution_critical_total_html=Markup("2"),
            missing_total_html=Markup("0"),
            blocks_execution_html=Markup("False"),
            readiness_table_html=Markup("<p>No rows.</p>"),
            missing_inputs_heading_html="<h4>Missing or Warning Inputs</h4>",
            missing_inputs_table_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="curve_summary_heading_html must be an HTML-safe Markup fragment"):
        AuditAcceptanceSummaryContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_ACCEPTANCE_SUMMARY,
            summary_html=Markup("<p>Summary</p>"),
            default_selection_html=Markup("machine"),
            total_runs_html=Markup("2"),
            accepted_html=Markup("1"),
            accepted_with_warning_html=Markup("1"),
            review_required_html=Markup("0"),
            excluded_html=Markup("0"),
            total_flags_html=Markup("0"),
            final_selection_html=Markup("operator"),
            selection_source_html=Markup("manual"),
            final_included_html=Markup("2"),
            human_decisions_html=Markup("1"),
            acceptance_table_html=Markup("<p>No rows.</p>"),
            curve_summary_heading_html="<h4>Curve-Family Assessment</h4>",
            curve_summary_table_html=Markup("<p>No rows.</p>"),
            curve_scores_table_html=Markup("<p>No rows.</p>"),
            final_runs_heading_html=Markup("<h4>Final Report Runs</h4>"),
            final_runs_table_html=Markup("<p>No rows.</p>"),
            override_ledger_heading_html=Markup("<h4>Human Override Ledger</h4>"),
            override_ledger_table_html=Markup("<p>No rows.</p>"),
        )

    with pytest.raises(ValueError, match="preview_table_html must be an HTML-safe Markup fragment"):
        AuditOperationLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_OPERATION_LOG_COMPONENT,
            title_html=Markup("Operations"),
            purpose_html=Markup("<p>purpose</p>"),
            summary_table_html=Markup("<p>summary</p>"),
            preview_table_html="<p>preview</p>",
            raw_evidence_note_html=Markup("<p>raw</p>"),
        )

    with pytest.raises(ValueError, match="purpose_html must be an HTML-safe Markup fragment"):
        AuditInspectionLogComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_INSPECTION_LOG_COMPONENT,
            title_html=Markup("Inspections"),
            purpose_html="<p>purpose</p>",
            summary_table_html=Markup("<p>summary</p>"),
            preview_table_html=Markup("<p>preview</p>"),
            raw_evidence_note_html=Markup("<p>raw</p>"),
        )

    with pytest.raises(ValueError, match="chart_id_html must be an HTML-safe Markup fragment"):
        AuditChartComponentContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_CHART_COMPONENT,
            title_html=Markup("Chart"),
            chart_id_html="chart",
            chart_hint_html=Markup(""),
            after_chart_html=Markup(""),
        )


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        specimen_results=[
            {
                "run_id": "run_001",
                "modulus_MPa": 1234,
                "strength_MPa": 86,
                "bending_threshold_percent": 10.0,
                "bending_pattern": "low",
                "bending_pattern_confidence": "high",
                "bending_points_above_threshold": 0,
                "bending_fraction_above_threshold": 0.0,
                "bending_p95_percent": 4.2,
                "bending_pattern_reason": "within threshold",
            },
            {
                "run_id": "run_002",
                "modulus_MPa": 1250,
                "strength_MPa": 88,
                "bending_pattern": "review",
                "bending_pattern_confidence": "medium",
                "bending_points_above_threshold": 2,
                "bending_fraction_above_threshold": 0.25,
                "bending_p95_percent": 12.4,
                "bending_pattern_reason": "localized excursions",
            },
        ],
        dataset_summary=[{"metric": "mean strength", "value": 87, "unit": "MPa"}],
        validation_report={
            "checks": [{"check_id": "modulus_range"}],
            "summary": {"status": "pass", "total_checks": 3, "passed": 2, "warnings": 1, "failed": 0},
        },
        validation_deviations=[{"check_id": "modulus_range", "status": "warn"}],
        readiness_report={
            "status": "READY_WITH_WARNINGS",
            "blocks_execution": False,
            "summary": {
                "execution_critical_passed": 4,
                "execution_critical_total": 4,
                "missing_total": 1,
            },
        },
        readiness_summary=[{"area": "mapping", "status": "ready"}],
        missing_inputs=[{"field": "operator", "severity": "warning"}],
        acceptance_report={
            "default_selection_set": "machine_acceptance",
            "summary": {
                "default_selection_set": "machine_acceptance",
                "total_runs": 2,
                "accepted": 1,
                "accepted_with_warning": 1,
                "review_required": 0,
                "excluded": 0,
                "total_flags": 1,
            },
        },
        acceptance_summary=[{"status": "accepted", "count": 1}, {"status": "warning", "count": 1}],
        selection_sets_final={"default_selection_set": "operator_final", "selection_source": "human_review"},
        final_report_runs=[
            {"run_id": "run_001", "final_included": True},
            {"run_id": "run_002", "final_included": True},
        ],
        human_decision_rows=[{"run_id": "run_002", "decision": "include"}],
        curve_family_assessment={"summary": {"state": "reviewed", "score_count": 2}},
        curve_family_scores=[{"run_id": "run_001", "score": 0.1}, {"run_id": "run_002", "score": 0.2}],
        override_ledger_rows=[{"run_id": "run_002", "override": "include"}],
        selection_membership_final=[{"run_id": "run_001", "final_included": True}],
        selection_membership=[{"run_id": "run_001", "included": True}],
        discharged_runs=[{"run_id": "run_003", "reason": "operator discharge"}],
        operation_log=[
            {
                "sequence": 1,
                "recipe_step_label": "Resolve inputs",
                "operation_type": "resolve_inputs",
                "phase": "setup",
                "run_id": "run_001",
                "status": "pass",
                "outputs": {"resolved_inputs": 4},
                "warnings": [],
            },
            {
                "sequence": 2,
                "operation_type": "inspect_curve",
                "phase": "inspection",
                "run_id": "run_002",
                "status": "warn",
                "inspection_refs": ["inspect-1"],
                "warnings": ["manual review"],
            },
        ],
        inspections=[
            {
                "inspection_id": "inspect-1",
                "run_id": "run_002",
                "type": "curve",
                "status": "recorded",
                "point_count": 42,
            }
        ],
    )


def _curve_rows() -> list[dict[str, object]]:
    return [
        {
            "run_id": "run_001",
            "strain_mm_per_mm": 0.001,
            "stress_MPa": 45.0,
            "load_N": 420.0,
            "front_strain_abs": 0.001,
            "rear_strain_abs": 0.0011,
        },
        {
            "run_id": "run_002",
            "strain_mm_per_mm": 0.002,
            "stress_MPa": 80.0,
            "load_N": 760.0,
            "front_strain_abs": 0.0018,
            "rear_strain_abs": 0.0024,
        },
    ]
