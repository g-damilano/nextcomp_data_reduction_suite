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
    _audit_decision_register_context,
    _audit_grouped_sections_context,
    _audit_process_overview_context,
    _audit_process_sections_context,
    _audit_process_summary_sentence_context,
    _audit_tracker,
    _decision_register_section,
    _grouped_audit_sections,
    _legacy_audit_tracker,
    _legacy_decision_register_section,
    _legacy_grouped_audit_sections,
    _legacy_process_sections,
    _legacy_process_overview,
    _legacy_summary_sentence,
    _process_sections,
    _process_overview,
    _summary_sentence,
)
from html_renderer.context_models import (
    AuditBlockCardContext,
    AuditDecisionRegisterContext,
    AuditGroupedSectionsContext,
    AuditProcessOverviewContext,
    AuditProcessSectionContext,
    AuditProcessSectionsContext,
    AuditProcessSummarySentenceContext,
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
    AuditTrackerContext,
    AuditTrackerLinkContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import (
    render_audit_decision_register,
    render_audit_grouped_sections,
    render_audit_process_overview,
    render_audit_process_sections,
    render_audit_process_summary_sentence,
    render_audit_tracker,
)


def test_audit_tracker_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_blocks = {
        "run_packets": [
            {"run_id": "run_001"},
            {"run_id": "run_002"},
        ]
    }

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _audit_tracker(audit_blocks)

    assert html == _legacy_audit_tracker(audit_blocks)
    assert '<nav aria-label="Audit report locations" class="report-tracker">' in html
    assert '<em class="status-badge status-pass">2</em>' in html
    assert 'href="#packet-run_001"' in html


def test_audit_process_overview_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _audit_payload()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _process_overview(payload)
    context = _audit_process_overview_context(payload)

    assert html == _legacy_process_overview(payload)
    assert context.lede_html == Markup('<p class="report-state-note">Grouped human audit evidence and traceability.</p>')
    assert str(context.overview_html).startswith("<p>ISO 14126 analysis evidence")
    assert 'id="audit_overview" class="report-state-card audit-overview-card"' in html
    assert '<table class="compact report-state-table">' in html
    assert '<a href="../report/test_report.html">Test Report</a>' in html


def test_audit_process_sections_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _audit_payload()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _process_sections(payload)
    context = _audit_process_sections_context(payload)

    assert html == _legacy_process_sections(payload)
    assert context.sections[0].evidence_detail_html == Markup(
        '<details class="audit-details"><summary>Source MTDP evidence detail</summary><div>'
        f"{context.sections[0].evidence_purpose_html}{context.sections[0].table_html}"
        "</div></details>"
    )
    assert 'id="audit_rc_source_mtdp"' in html
    assert '<summary>Source MTDP evidence detail</summary>' in html
    assert '<strong>Audit evidence.</strong>' in html


def test_audit_process_summary_sentences_jinja_match_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [
        ("source_mtdp", {"path": "example.mtdp"}),
        ("readiness", {"status": "READY_WITH_WARNINGS"}),
        (
            "experiment_boundary_resolution",
            {
                "status": "resolved",
                "policy": {"start_policy": "first_load", "end_policy": "failure"},
                "bounded_reduction": True,
                "boundary_aligned_aggregation": False,
                "endpoints": [{"run_id": "run_001", "start_index": 2, "end_index": 10}],
            },
        ),
        ("validation", {"status": "pass", "summary": {"passed": 3, "warnings": 1, "failed": 0}}),
        (
            "acceptance_final_selection",
            {
                "final_selection_set": "final_report_runs",
                "selection_source": "human_final",
                "discharged_run_count": 2,
            },
        ),
        ("warnings_residuals", {"count": 4}),
        ("linked_artifacts", {"test_report": "report/test_report.html"}),
        ("anything_else", object()),
    ]

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    for section_id, data in cases:
        context = _audit_process_summary_sentence_context(section_id, data)
        assert str(context.sentence_html) == _legacy_summary_sentence(section_id, data)
        assert _summary_sentence(section_id, data) == _legacy_summary_sentence(section_id, data)


def test_audit_decision_register_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _decision_result()
    payload = _audit_payload()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _decision_register_section(result, payload)
    context = _audit_decision_register_context(result, payload)

    assert html == _legacy_decision_register_section(result, payload)
    assert context.section_heading_html == Markup("<h2>Decision Register</h2>")
    assert context.human_overrides_heading_html == Markup("<h3>Human overrides</h3>")
    assert context.amendments_heading_html == Markup("<h3>Finalization / report-only amendments</h3>")
    assert 'id="decision_register"' in html
    assert '<h3>Human overrides</h3>' in html
    assert '<h3>Finalization / report-only amendments</h3>' in html


def test_grouped_audit_sections_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    block_index = _block_index()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    html = _grouped_audit_sections(block_index)
    context = _audit_grouped_sections_context(block_index)

    assert html == _legacy_grouped_audit_sections(block_index)
    assert context is not None
    assert context.overview_heading_html == Markup("<h2>Audit overview</h2>")
    assert context.run_packets_heading_html == Markup("<h2>Per-run audit packets</h2>")
    assert context.aggregate_heading_html == Markup("<h2>Aggregate audit packet</h2>")
    assert context.run_packets[0].packet_heading_html == Markup(
        '<h3><span class="packet-label">Run-wise audit packet</span><br>run_001</h3>'
    )
    assert str(context.run_packets[0].blocks[0].card_html).startswith(
        '<details class="audit-details" id="run_identity" open>'
    )
    assert 'id="procedure_derived_audit_blocks"' in html
    assert 'id="run_identity"' in html
    assert '<h4>Validation checks</h4>' in html
    assert '<h4>MTDA artifacts</h4>' in html
    assert '<span class="packet-label">Run-wise audit packet</span><br>run_001' in html


def test_audit_report_section_renderers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _audit_payload()
    audit_blocks = {"run_packets": [{"run_id": "run_001"}]}
    block_index = _block_index()
    result = _decision_result()

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _audit_tracker(audit_blocks) == _legacy_audit_tracker(audit_blocks)
    assert _process_overview(payload) == _legacy_process_overview(payload)
    assert _process_sections(payload) == _legacy_process_sections(payload)
    assert _decision_register_section(result, payload) == _legacy_decision_register_section(result, payload)
    assert _grouped_audit_sections(block_index) == _legacy_grouped_audit_sections(block_index)


def test_audit_report_section_recipe_projections_are_explicit() -> None:
    tracker_projection = projection_for(RecipeResultKind.AUDIT_TRACKER)
    overview_projection = projection_for(RecipeResultKind.AUDIT_PROCESS_OVERVIEW)
    process_summary_projection = projection_for(RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE)
    process_sections_projection = projection_for(RecipeResultKind.AUDIT_PROCESS_SECTIONS)
    decision_projection = projection_for(RecipeResultKind.AUDIT_DECISION_REGISTER)
    grouped_projection = projection_for(RecipeResultKind.AUDIT_GROUPED_SECTIONS)

    assert tracker_projection.context_model == "AuditTrackerContext"
    assert tracker_projection.template_name == "components/trackers/audit_report_tracker.html.j2"
    assert tracker_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert overview_projection.context_model == "AuditProcessOverviewContext"
    assert process_summary_projection.context_model == "AuditProcessSummarySentenceContext"
    assert process_summary_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert process_sections_projection.context_model == "AuditProcessSectionsContext"
    assert process_sections_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert decision_projection.context_model == "AuditDecisionRegisterContext"
    assert decision_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert grouped_projection.context_model == "AuditGroupedSectionsContext"

    tracker_html = render_audit_tracker(
        AuditTrackerContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            links=(
                AuditTrackerLinkContext(
                    number_html=Markup("1"),
                    label_html=Markup("Evidence Navigation"),
                    anchor_html=Markup("evidence_navigation_run_index"),
                    pill_html=Markup(""),
                ),
            ),
        )
    )
    overview_html = render_audit_process_overview(
        AuditProcessOverviewContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_OVERVIEW,
            lede_html=Markup('<p class="report-state-note">Grouped human audit evidence and traceability.</p>'),
            overview_html=Markup(
                '<p>ISO 14126 analysis evidence. Formal result values are in the '
                '<a href="../report/test_report.html">Test Report</a>.</p>'
            ),
            table=_table_context(),
        )
    )
    process_sections_html = render_audit_process_sections(
        AuditProcessSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_SECTIONS,
            sections=(
                AuditProcessSectionContext(
                    section_id_html=Markup("source"),
                    title_html=Markup("Source"),
                    summary_html=Markup("<p>Summary</p>"),
                    evidence_purpose_html=Markup("<p>Purpose</p>"),
                    table_html=Markup("<table></table>"),
                    evidence_detail_html=Markup(
                        '<details class="audit-details"><summary>Source evidence detail</summary>'
                        "<div><p>Purpose</p><table></table></div></details>"
                    ),
                ),
            ),
        )
    )
    process_summary_html = render_audit_process_summary_sentence(
        _summary_sentence_context(
            "readiness",
            status_html=Markup("Ready"),
            sentence_html=Markup(
                "<p>Readiness status: <strong>Ready</strong>. Report-only warnings remain non-blocking; "
                "execution-critical blockers would stop before resolve.</p>"
            ),
        )
    )
    decision_html = render_audit_decision_register(
        AuditDecisionRegisterContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_DECISION_REGISTER,
            section_heading_html=Markup("<h2>Decision Register</h2>"),
            disposition_summary_heading_html=Markup("<h3>Final report run set summary</h3>"),
            disposition_summary_table_html=Markup("<table></table>"),
            disposition_heading_html=Markup("<h3>Run disposition register</h3>"),
            disposition_table_html=Markup("<table></table>"),
            has_human_overrides=False,
            human_overrides_heading_html=Markup("<h3>Human overrides</h3>"),
            human_overrides_table_html=Markup(""),
            has_amendments=False,
            amendments_heading_html=Markup("<h3>Finalization / report-only amendments</h3>"),
            amendments_table_html=Markup(""),
        )
    )
    grouped_html = render_audit_grouped_sections(
        AuditGroupedSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_GROUPED_SECTIONS,
            overview_heading_html=Markup("<h2>Audit overview</h2>"),
            intro_html=Markup("<p>Intro</p>"),
            overview=AuditBlockCardContext(
                block_id_html=Markup("overview"),
                title_html=Markup("Overview"),
                status_html=Markup("recorded"),
                purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
                fragments=(),
                card_html=Markup(
                    '<details class="audit-details" id="overview" open><summary>Overview '
                    '<span class="muted">recorded</span></summary>'
                    '<div><p class="audit-purpose">Purpose</p></div></details>'
                ),
            ),
            run_packets_heading_html=Markup("<h2>Per-run audit packets</h2>"),
            run_packets=(),
            aggregate_heading_html=Markup("<h2>Aggregate audit packet</h2>"),
            aggregate_blocks=(),
        )
    )

    assert 'href="#evidence_navigation_run_index"' in tracker_html
    assert '<table class="compact report-state-table">' in overview_html
    assert "Readiness status" in process_summary_html
    assert 'id="audit_rc_source"' in process_sections_html
    assert 'id="decision_register"' in decision_html
    assert 'id="procedure_derived_audit_blocks"' in grouped_html


def test_audit_report_section_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditTrackerContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            links=(),
        )

    with pytest.raises(ValueError, match="audit_process_overview"):
        AuditProcessOverviewContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            lede_html=Markup('<p class="report-state-note">Grouped human audit evidence and traceability.</p>'),
            overview_html=Markup("<p>Overview.</p>"),
            table=_table_context(),
        )

    with pytest.raises(ValueError, match="lede_html must be an HTML-safe Markup fragment"):
        AuditProcessOverviewContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_OVERVIEW,
            lede_html="<p>Grouped human audit evidence and traceability.</p>",
            overview_html=Markup("<p>Overview.</p>"),
            table=_table_context(),
        )

    with pytest.raises(ValueError, match="overview_html must be an HTML-safe Markup fragment"):
        AuditProcessOverviewContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_OVERVIEW,
            lede_html=Markup('<p class="report-state-note">Grouped human audit evidence and traceability.</p>'),
            overview_html="<p>Overview.</p>",
            table=_table_context(),
        )

    with pytest.raises(ValueError, match="audit_process_sections"):
        AuditProcessSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            sections=(),
        )

    with pytest.raises(ValueError, match="audit_process_summary_sentence"):
        AuditProcessSummarySentenceContext(
            **{
                **_summary_sentence_context_kwargs("readiness"),
                "recipe_result_kind": RecipeResultKind.AUDIT_TRACKER,
            }
        )

    with pytest.raises(ValueError, match="known audit process summary variant"):
        _summary_sentence_context("surprising")

    with pytest.raises(ValueError, match="status_html must be an HTML-safe Markup fragment"):
        AuditProcessSummarySentenceContext(
            **{
                **_summary_sentence_context_kwargs("readiness"),
                "status_html": "Ready",
            }
        )

    with pytest.raises(ValueError, match="sentence_html must be an HTML-safe Markup fragment"):
        AuditProcessSummarySentenceContext(
            **{
                **_summary_sentence_context_kwargs("readiness"),
                "sentence_html": "<p>Ready</p>",
            }
        )

    with pytest.raises(ValueError, match="audit_decision_register"):
        AuditDecisionRegisterContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_TRACKER,
            section_heading_html=Markup(""),
            disposition_summary_heading_html=Markup(""),
            disposition_summary_table_html=Markup(""),
            disposition_heading_html=Markup(""),
            disposition_table_html=Markup(""),
            has_human_overrides=False,
            human_overrides_heading_html=Markup(""),
            human_overrides_table_html=Markup(""),
            has_amendments=False,
            amendments_heading_html=Markup(""),
            amendments_table_html=Markup(""),
        )

    with pytest.raises(ValueError, match="section_heading_html must be an HTML-safe Markup fragment"):
        AuditDecisionRegisterContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_DECISION_REGISTER,
            section_heading_html="<h2>Decision Register</h2>",
            disposition_summary_heading_html=Markup(""),
            disposition_summary_table_html=Markup(""),
            disposition_heading_html=Markup(""),
            disposition_table_html=Markup(""),
            has_human_overrides=False,
            human_overrides_heading_html=Markup(""),
            human_overrides_table_html=Markup(""),
            has_amendments=False,
            amendments_heading_html=Markup(""),
            amendments_table_html=Markup(""),
        )

    with pytest.raises(ValueError, match="sections must contain"):
        AuditProcessSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_PROCESS_SECTIONS,
            sections=(object(),),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="evidence_purpose_html must be an HTML-safe Markup fragment"):
        AuditProcessSectionContext(
            section_id_html=Markup("source"),
            title_html=Markup("Source"),
            summary_html=Markup("<p>Summary</p>"),
            evidence_purpose_html="<p>Purpose</p>",
            table_html=Markup("<table></table>"),
            evidence_detail_html=Markup(
                '<details class="audit-details"><summary>Source evidence detail</summary>'
                "<div><p>Purpose</p><table></table></div></details>"
            ),
        )

    with pytest.raises(ValueError, match="evidence_detail_html must be an HTML-safe Markup fragment"):
        AuditProcessSectionContext(
            section_id_html=Markup("source"),
            title_html=Markup("Source"),
            summary_html=Markup("<p>Summary</p>"),
            evidence_purpose_html=Markup("<p>Purpose</p>"),
            table_html=Markup("<table></table>"),
            evidence_detail_html=(
                '<details class="audit-details"><summary>Source evidence detail</summary>'
                "<div><p>Purpose</p><table></table></div></details>"
            ),
        )

    with pytest.raises(ValueError, match="intro_html must be an HTML-safe Markup fragment"):
        AuditGroupedSectionsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_GROUPED_SECTIONS,
            overview_heading_html=Markup(""),
            intro_html="<p>Intro</p>",
            overview=None,
            run_packets_heading_html=Markup(""),
            run_packets=(),
            aggregate_heading_html=Markup(""),
            aggregate_blocks=(),
        )

    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        AuditBlockCardContext(
            block_id_html=Markup("overview"),
            title_html="Overview",
            status_html=Markup("recorded"),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
            fragments=(),
            card_html=Markup(""),
        )

    with pytest.raises(ValueError, match="fragments must be an HTML-safe Markup fragment"):
        AuditBlockCardContext(
            block_id_html=Markup("overview"),
            title_html=Markup("Overview"),
            status_html=Markup("recorded"),
            purpose_html=Markup('<p class="audit-purpose">Purpose</p>'),
            fragments=("<p></p>",),
            card_html=Markup(""),
        )


def _table_context() -> AuditTableContext:
    return AuditTableContext(
        table_class="compact report-state-table",
        headers=(
            AuditTableCellContext(html=Markup("Area")),
            AuditTableCellContext(html=Markup("State")),
            AuditTableCellContext(html=Markup("Evidence")),
        ),
        rows=(
            AuditTableRowContext(
                cells=(
                    AuditTableCellContext(html=Markup("Source")),
                    AuditTableCellContext(html=Markup("Recorded")),
                    AuditTableCellContext(html=Markup("Archive")),
                )
            ),
        ),
    )


def _summary_sentence_context(sentence_kind: str, **overrides: Markup) -> AuditProcessSummarySentenceContext:
    return AuditProcessSummarySentenceContext(**_summary_sentence_context_kwargs(sentence_kind, **overrides))


def _summary_sentence_context_kwargs(sentence_kind: str, **overrides: Markup) -> dict[str, object]:
    values = {
        "projection_plane": ProjectionPlane.AUDIT,
        "recipe_result_kind": RecipeResultKind.AUDIT_PROCESS_SUMMARY_SENTENCE,
        "sentence_kind": sentence_kind,
        "status_html": Markup(""),
        "start_policy_html": Markup(""),
        "end_policy_html": Markup(""),
        "bounded_reduction_html": Markup(""),
        "boundary_aligned_aggregation_html": Markup(""),
        "endpoints_table_html": Markup(""),
        "passed_html": Markup(""),
        "warnings_html": Markup(""),
        "failed_html": Markup(""),
        "final_selection_set_html": Markup(""),
        "selection_source_html": Markup(""),
        "discharged_run_count_html": Markup(""),
        "warning_count_html": Markup(""),
        "sentence_html": Markup("<p>Summary</p>"),
    }
    values.update(overrides)
    return values


def _audit_payload() -> dict[str, object]:
    return {
        "source_mtdp": {"path": "example.mtdp", "run_count": 2},
        "method_package": {"standard_reference": "ISO 14126", "name": "Compression"},
        "experiment_boundary_resolution": {"status": "resolved", "summary": "2 runs resolved."},
        "validation": {"status": "pass", "deviation_count": 0},
        "curve_shape_diagnostic": {"score_count": 2},
        "report_completion": {"status": "complete", "missing_field_count": 0, "override_count": 0},
        "warnings": {"count": 0},
    }


def _decision_result() -> SimpleNamespace:
    return SimpleNamespace(
        specimen_results=[
            {"run_id": "run_001", "specimen_name": "S-1"},
            {"run_id": "run_002", "specimen_name": "S-2"},
        ],
        final_report_runs=[
            {"run_id": "run_001", "specimen_name": "S-1", "final_included": True},
            {
                "run_id": "run_002",
                "specimen_name": "S-2",
                "final_included": False,
                "human_decision": "exclude",
                "human_decision_reason": "operator review",
            },
        ],
        discharged_runs=[
            {"run_id": "run_002", "state": "excluded", "primary_reason": "curve family outlier"},
        ],
        run_flags=[
            {
                "run_id": "run_002",
                "category": "curve_shape",
                "flag_id": "curve_shape_review",
                "message": "Curve-shape review required.",
            }
        ],
        human_decision_rows=[
            {"run_id": "run_002", "decision": "exclude", "reason": "operator review"},
        ],
        override_ledger_rows=[
            {"field": "operator", "decision": "recorded"},
        ],
        report_overrides=[],
    )


def _block_index() -> dict[str, object]:
    return {
        "audit_overview": {
            "block_id": "overview",
            "title": "Audit overview",
            "purpose": "Shows grouping.",
            "status": "recorded",
            "artifact_refs": ["reports/audit_report.json"],
        },
        "run_packets": [
            {
                "run_id": "run_001",
                "blocks": [
                    {
                        "block_id": "run_identity",
                        "title": "Identity",
                        "purpose": "Run identity evidence.",
                        "status": "recorded",
                        "operations": [{"sequence": 1, "operation_type": "map_metadata"}],
                        "validation_checks": [{"check_id": "geometry", "status": "pass"}],
                    },
                    {
                        "block_id": "run_selection",
                        "title": "Selection",
                        "purpose": "Selection evidence.",
                        "status": "recorded",
                        "selection": {"run_id": "run_001", "included": True},
                        "flags": [{"flag": "none"}],
                    },
                ],
            }
        ],
        "aggregate_packet": {
            "blocks": [
                {
                    "block_id": "aggregate",
                    "title": "Aggregate",
                    "purpose": "Aggregate evidence.",
                    "status": "recorded",
                    "scope": "aggregate",
                    "selected_run_ids": ["run_001"],
                    "artifact_refs": ["reports/audit_report.json"],
                }
            ]
        },
    }
