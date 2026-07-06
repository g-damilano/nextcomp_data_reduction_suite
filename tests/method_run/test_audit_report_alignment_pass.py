from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout


AUDIT_HTML = f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
AUDIT_JSON = f"{MTDAAlignedLayout.reports_prefix}audit_report.json"
TEST_HTML = f"{MTDAAlignedLayout.reports_prefix}test_report.html"
METHOD_OUTPUTS = MTDAAlignedLayout.method_outputs


def test_audit_report_alignment_structure_is_human_evidence_first(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    positions = [
        html.index('id="audit_overview"'),
        html.index('id="evidence_navigation_run_index"'),
        html.index('id="run_wise_evidence_packets"'),
        html.index('id="aggregate_evidence_packet"'),
        html.index('id="decision_register"'),
    ]
    assert positions == sorted(positions)
    assert "Formal result values are in" in html
    assert "test_report.html" in html
    assert "Artifact Links" not in html
    assert "This report first presents evidence" not in html
    assert "Evidence first, decisions after evidence" not in html


def test_audit_report_embeds_visual_first_run_and_aggregate_evidence(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    assert 'data-audit-plot="run_stress_strain_reduction"' in html
    assert 'data-audit-plot="run_bending_evidence"' in html
    assert 'data-audit-plot="aggregate_curve_family"' in html
    for phrase in (
        "bounded curve",
        "front strain",
        "rear strain",
        "average strain",
        "strain agreement envelope",
        "start marker",
        "end marker",
        "max point",
        "chord points",
        "chord line",
            "threshold line",
            "10-90% window",
            "exceedance segments",
            "classification",
            "all evaluable curves",
            "variability band",
            "curve-shape diagnostic",
        ):
        assert phrase in html


def test_audit_report_plots_are_clipped_to_resolved_experiment_boundaries(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    specs = _embedded_vega_specs(html)

    stress_specs = {
        spec_id: spec
        for spec_id, spec in specs.items()
        if spec_id.endswith("_stress_strain_reduction_plot")
    }
    assert stress_specs
    assert "full curve context" not in html
    assert "optional shaded excluded post-end region" not in html

    for spec in stress_specs.values():
        assert spec["usermeta"]["plotting_module"] == "plotting"
        assert "bounded_analysis_curve" in spec["usermeta"]["semantic_layers"]
        layers = spec["layer"]
        layer_names = {layer.get("name") for layer in layers}
        assert "bounded curve" in layer_names
        assert "front rear strain traces" in layer_names
        assert "front rear strain agreement envelope" in layer_names
        assert "post-peak audit trace" not in layer_names
        assert "marker labels" not in layer_names
        assert "full curve context" not in layer_names
        assert "optional shaded excluded post-end region" not in layer_names
        assert spec["usermeta"]["depiction_policy"]["semantic_boundary"] == "depiction_only"
        assert spec["usermeta"]["depiction_policy"]["plot_side_reselection"] is False
        serialized = json.dumps(spec)
        assert "Strain traces" in serialized
        assert "Analysis markers" in serialized
        assert "Faint post-peak audit trace shown from Fmax to 10% of Fmax." not in serialized
        assert "Gauge trace, Marker" not in serialized

        bounded = next(layer for layer in layers if layer.get("name") == "bounded curve")
        bounded_values = bounded["data"]["values"]
        assert bounded_values
        lower = min(row["strain"] for row in bounded_values)
        upper = max(row["strain"] for row in bounded_values)

        for layer in layers:
            layer_values = (layer.get("data") or {}).get("values") if isinstance(layer, dict) else None
            for value in layer_values or []:
                if not isinstance(value, dict):
                    continue
                if "strain" in value:
                    assert lower - 1e-9 <= value["strain"] <= upper + 1e-9
                assert "x1" not in value
                assert "x2" not in value

        assert bounded["encoding"]["order"] == {"field": "point_index", "type": "quantitative"}
        assert bounded["encoding"]["x"]["scale"]["domain"][1] >= upper

        gauge_traces = next(layer for layer in layers if layer.get("name") == "front rear strain traces")
        gauge_values = gauge_traces["data"]["values"]
        assert gauge_values
        assert {row["series"] for row in gauge_values} == {"front strain", "rear strain"}
        bounded_indexes = {row["point_index"] for row in bounded_values}
        assert {row["point_index"] for row in gauge_values}.issubset(bounded_indexes)

        envelope = next(layer for layer in layers if layer.get("name") == "front rear strain agreement envelope")
        envelope_values = envelope["data"]["values"]
        assert envelope_values
        assert all(row["strain_min"] <= row["strain_max"] for row in envelope_values)
        assert {row["point_index"] for row in envelope_values}.issubset(bounded_indexes)

    aggregate = specs["aggregate_curve_family_plot"]
    assert aggregate["usermeta"]["plotting_module"] == "plotting"
    assert "all_evaluable_curves" in aggregate["usermeta"]["semantic_layers"]
    aggregate_values = [
        value
        for value in _spec_data_values(aggregate)
        if "x" in value
    ]
    assert aggregate_values
    assert all(0.0 <= value["x"] <= 100.0 for value in aggregate_values)
    freshness = aggregate["usermeta"]["plot_data_freshness"]
    assert freshness["status"] == "current"
    assert freshness["alignment_domain"] == "experiment_progress"
    assert freshness["source_boundaries"] == "method_resolve.experiment_boundaries"
    assert freshness["bounded_replicates"] is True
    assert freshness["boundary_aligned_aggregation"] is True
    assert freshness["endpoint_by_run"]
    assert not freshness["reasons"]

    bending_specs = {
        spec_id: spec
        for spec_id, spec in specs.items()
        if spec_id.endswith("_bending_evidence_plot")
    }
    assert bending_specs
    for spec in bending_specs.values():
        assert spec["usermeta"]["plotting_module"] == "plotting"
        assert "bending_percent_series" in spec["usermeta"]["semantic_layers"]
        serialized = json.dumps(spec)
        assert '"datum": 0' not in serialized
        window = next(layer for layer in spec["layer"] if layer.get("name") == "10-90% window")
        segments = next(layer for layer in spec["layer"] if layer.get("name") == "exceedance segments")
        assert window["encoding"]["y"]["field"] == "y1"
        assert all("y1" in row for row in window["data"]["values"])
        assert segments["encoding"]["y"]["field"] == "y1"
        assert all("y1" in row for row in segments["data"]["values"])

    stress_section_start = html.index('data-block-type="run_stress_strain_reduction"')
    stress_block_start = html.rfind("<div", 0, stress_section_start)
    stress_section_end = html.index('data-block-type="run_bending_evidence"', stress_section_start)
    stress_section = html[stress_block_start:stress_section_end]
    assert 'class="audit-block run_stress_strain_reduction visual-first"' in stress_section
    assert '<button type="button" class="note-marker" aria-label="Show method note" aria-expanded="false">i</button>' not in stress_section
    assert "Faint post-peak audit trace shown from Fmax to 10% of Fmax." not in stress_section


def test_audit_report_style_tracks_test_report_plain_report_surface(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    assert 'class="report-state-card audit-overview-card"' in html
    assert ".page { max-width: 1320px; margin: 0 auto; padding: 28px; }" in html
    assert ".link-bar" not in html
    assert 'window.vegaEmbed("#" + id, spec, {actions: false, renderer: "svg"})' in html
    assert "renderVisibleAuditPlots" in html
    assert 'class="report-tracker"' in html
    assert ".layout { display: grid; grid-template-columns: 310px minmax(0, 1fr);" in html
    assert 'details.addEventListener("toggle"' not in html
    assert "<details" not in html
    assert "flow-card" not in html
    assert "process-flow" not in html
    assert "metric-card" not in html
    assert "metric-grid" not in html
    assert "summary-card" not in html
    assert "summary-panel" in html
    assert "header { background:" not in html
    assert "Interactive stress-strain evidence:" not in html


def test_audit_tracker_nests_runs_under_run_wise_section(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    tracker = re.search(r'<nav aria-label="Audit report locations" class="report-tracker">(.*?)</nav>', html, re.S)
    assert tracker is not None
    tracker_html = tracker.group(1)

    runwise_pos = tracker_html.index("Run-wise Evidence Packets")
    sublist_pos = tracker_html.index('class="report-tracker-sublist"')
    aggregate_pos = tracker_html.index("Aggregate Evidence Packet")

    assert runwise_pos < sublist_pos < aggregate_pos
    assert '<div class="report-tracker-sublist"><a href="#packet-run_001">' in tracker_html
    assert '<em class="status-badge">run</em>' not in tracker_html
    assert ">run_001<" not in tracker_html
    assert ">#1<" in tracker_html
    assert "EVIDENCE_RECORDED" not in html


def test_audit_report_removes_software_process_details_from_default_surface(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    before_decisions = html[: html.index('id="decision_register"')]

    assert "<h4>Summary</h4>" not in html
    assert "Underlying operation records" not in html
    assert "Technical trace" not in html
    assert "Process evidence detail" not in html
    assert "Compact evidence" not in html
    assert "Bending conclusion" not in html
    assert "Numerical evidence" not in html
    assert 'data-block-type="run_selection_consequence"' not in html
    assert "Machine Recommendation" not in html
    assert "Machine Reason" not in html
    assert "Machine Consequence" not in html
    assert "Human Decision" not in before_decisions
    assert "Human Consequence" not in html
    assert "Warning and failure checks" not in html
    assert "Report inclusion evidence" not in html
    assert "<details" not in html


def test_audit_report_tables_use_dimension_unit_headers(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    for header in (
        "Width / mm",
        "Thickness / mm",
        "Area / mm2",
        "Fmax / N",
        "Strength / MPa",
        "Modulus / MPa",
        "Stress at 0.0005 / MPa",
        "Stress at 0.0025 / MPa",
        "Threshold / %",
        "Max bending / %",
        "Above-threshold extent",
    ):
        assert header in html
    for raw_header in (
        "<th>Width</th>",
        "<th>Thickness</th>",
        "<th>Fmax</th>",
        "<th>Strength</th>",
        "<th>Modulus</th>",
        "<th>Threshold</th>",
    ):
        assert raw_header not in html


def test_run_evidence_summaries_are_user_readable(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    assert "Specimen name" in html
    assert "Data validity" in html
    assert "Experimental failure" in html
    assert ">Yes<" in html
    assert "Operator failure metadata records a failure flag" in html
    assert "Failure observation metadata is 0" not in html
    assert "Run is marked invalid by user/operator failure-mode metadata" not in html
    assert "Bending result" in html
    assert "Above-threshold extent" in html
    assert "Curve-shape result" in html
    assert "Difference score (distance_rms)" in html
    assert "Observed Dixon Q (Qexp)" in html
    assert "Curve-shape method" in html
    assert "Curve-shape results" in html
    assert "Cohort ID" in html
    assert "Comparable curves assessed (n)" in html
    assert "Audit interpretation" not in html
    assert "Evaluable curve" not in html


def test_audit_run_packets_surface_failure_observation_evidence(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    audit = _json_member(stage26_canonical_mtda, AUDIT_JSON)

    assert "Failure observation evidence" in html
    assert "Failure mode" in html
    assert "Failure location" in html
    assert "<th scope=\"row\">Failure mode</th><td>not recorded</td>" in html
    assert "<th scope=\"row\">Failure location</th><td>not recorded</td>" in html
    assert "Invalid specimen reason" in html
    assert "operator marked invalid; bending non-compliance" in html
    assert "points &gt; 10 %" in html
    assert audit["audit_blocks"]["summary"]["run_packet_count"] == 7


def test_bending_blocks_are_visible_plain_articles(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    pass_match = re.search(
        r'<div class="[^"]*run_bending_evidence[^"]*" id="run_001:run_bending_evidence"[^>]*>',
        html,
    )
    problem_match = re.search(
        r'<div class="[^"]*run_bending_evidence[^"]*" id="run_002:run_bending_evidence"[^>]*>',
        html,
    )
    assert pass_match is not None
    assert problem_match is not None
    assert html.count('data-block-type="run_bending_evidence"') == 7
    assert "<th scope=\"row\">Bending result</th><td>Pass</td>" in html
    assert "Sustained bending above limit" in html
    assert "Bending evidence" in html


def test_audit_blocks_are_traceable_to_workbench_and_operation_records(stage26_canonical_mtda: Path) -> None:
    method_outputs = _json_member(stage26_canonical_mtda, METHOD_OUTPUTS)
    operations = method_outputs["operation_trace"]["operations"]
    audit_operations = [row for row in operations if row.get("default_audit_block")]

    assert audit_operations
    for operation in audit_operations:
        evidence_refs = operation.get("evidence_refs") or {}
        assert evidence_refs.get("operation_record")
        assert evidence_refs.get("workbench_record")


def test_audit_report_does_not_duplicate_test_report_or_workbench_roles(stage26_canonical_mtda: Path) -> None:
    audit_html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    test_html = _text_member(stage26_canonical_mtda, TEST_HTML)

    assert "Test Report" in audit_html
    assert "Artifact Links" not in audit_html
    assert "Property value checks" not in audit_html
    assert "Scalar evidence" not in audit_html
    assert "statistical_screening" not in audit_html
    assert "Run-wise evidence packet" not in test_html
    assert "procedure_evidence_index" not in test_html
    assert "operation log" not in test_html.casefold()


def test_audit_report_omits_scalar_aggregate_statistics_block(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)
    audit = _json_member(stage26_canonical_mtda, AUDIT_JSON)

    assert audit["audit_blocks"]["aggregate_packet"]["block_count"] == 4
    assert 'id="aggregate:aggregate_statistics"' not in html
    assert "Scalar/statistical evidence" not in html
    assert "Formal aggregate statistics" not in html
    assert "bending max percent" not in html


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def _embedded_vega_specs(html_text: str) -> dict[str, Any]:
    match = re.search(r"const specs = (\{.*?\});\s+const renderedSpecs", html_text, re.S)
    assert match is not None
    return json.loads(match.group(1))


def _spec_data_values(spec: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for layer in spec.get("layer", []):
        data = layer.get("data") if isinstance(layer, dict) else None
        layer_values = data.get("values") if isinstance(data, dict) else None
        if isinstance(layer_values, list):
            values.extend(row for row in layer_values if isinstance(row, dict))
    return values
