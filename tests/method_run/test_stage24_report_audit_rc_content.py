from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.layouts import MTDAAlignedLayout
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from ui.method_run_wizard.view_models.output_review import output_review_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
REMOVED_DATASET_KEY = "dataset_" + "report"

EXPECTED_SECTIONS = [
    "test_identification",
    "material_identification",
    "specimen_preparation",
    "loading_fixture",
    "specimen_geometry",
    "test_conditions",
    "measurement_method",
    "individual_test_results",
    "aggregated_results",
    "failure_analysis",
    "deviations_from_standard",
    "remarks",
]


@pytest.fixture(scope="module")
def stage24_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage24_report_rc") / "CAG-CF-Modied-ULV20.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output


def test_test_report_has_rc_sections_statuses_and_missing_field_groups(stage24_mtda: Path) -> None:
    report = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    sections = report["report_sections"]
    completion = report["report_completion_status"]
    document = report["report_document"]
    html = _text_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")

    assert [section["section_id"] for section in sections] == EXPECTED_SECTIONS
    assert all(section["status"] in {"complete", "complete_with_warnings", "incomplete", "not_applicable"} for section in sections)
    assert all("missing_fields_by_importance" in section for section in sections)
    assert any(section["status"] == "complete_with_warnings" for section in sections)
    assert report["report_sections"] == sections
    assert report["summary"]["selection_set"] == "final_report_runs"
    assert report["summary"]["selection_source"] == "machine_default_confirmed"
    assert completion["status"] == "INCOMPLETE"
    assert "Report Completion Summary" in html
    assert 'class="report-state-card"' in html
    assert 'class="report-tracker"' in html
    assert 'id="section-test_identification"' in html
    assert 'class="report-section report-section--empty"' in html
    assert 'Failure Analysis</span><em class="pill warn">2 missing</em>' in html
    assert 'Deviations from Standard</span><em class="pill warn">Review</em>' in html
    assert "11.1 Missing data" in html
    assert "11.2 Data deviations / standard-facing deviations" in html
    assert "No report-ready values were supplied for this section." in html
    assert 'id="section-failure_analysis"' in html
    assert "required_missing_count" in html
    assert "recommended_missing_count" in html
    assert "No required report fields are missing" not in html
    assert "2 required fields missing" in html
    assert "Recommended field missing." not in html
    assert "Add if available, or finalize with warning." not in html
    assert "Report field 'loading_method' was not found" not in html
    assert "ISO 14126 Clause 9.5" in html
    assert "CAG-CF-ER-Comp-E5" in html
    assert "CAG-CF-Modied-ULV20-E5" in html
    specimen_block = next(
        block
        for section in document["sections"]
        if section["id"] == "specimen_geometry"
        for block in section["blocks"]
        if block["id"] == "specimen_geometry_table"
    )
    geometry_by_run = {row["run_id"]: row for row in specimen_block["data"]}
    assert geometry_by_run["run_005"]["specimen_name"] == "CAG-CF-ER-Comp-E5"
    assert geometry_by_run["run_005"]["sample_id"] == "CAG-CF-Modied-ULV20-E5"


def test_test_report_evidence_blocks_embed_aggregate_vega(stage24_mtda: Path) -> None:
    report = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    html = _text_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")
    vega = report["aggregate_plot_spec"]
    document = report["report_document"]
    aligned = _csv_member(stage24_mtda, f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv")

    assert aligned
    assert vega["schema_id"] == "method.aggregate_plot_spec.v0_1"
    assert vega["selection_set"] == "final_report_runs"
    assert "data-vega-block" in html
    assert "vegaEmbed" in html
    assert "Stress-strain aggregate" in html
    assert "Plot data current" not in html
    assert "Plot data needs review" not in html
    assert "plot-freshness" not in html
    assert "bounded_curve_family" in html
    assert ".layout { display: grid; grid-template-columns: 310px minmax(0, 1fr);" in html
    assert "@media (min-width: 921px) and (max-width: 1960px)" not in html
    assert "Aggregate evidence shows individual replicate curves" not in html
    assert "Individual replicate curves remain visually subdued" not in html
    assert "Normalised strain / %" in html
    assert "Actual strain / %" in html
    assert "Stress / MPa" in html
    assert "Normalised strain (%)" not in html
    assert "Stress (MPa)" not in html
    assert "Stress-strain aggregation" not in html
    assert "run_selector" not in html
    assert ".vg-tooltip table" in html
    assert ".plot { border: 1px solid var(--line); border-radius: 10px; padding: 12px; margin-top: 14px; background: #fcfdff; max-width: 100%; overflow: hidden; }" in html
    assert ".vega-chart { min-height: 330px; width: 100%; max-width: 100%; overflow: hidden; }" in html
    assert 'renderer: "svg"' in html
    assert "bounds.width > 10 && bounds.height > 10" in html
    assert "Characteristic points" not in html
    assert "Feature lines" not in html
    assert "Mean compressive strength line" not in html
    assert "Mean failure-strain line" not in html
    assert "Mean compressive modulus slope" not in html
    assert "Mean Compressive Failure" not in html
    assert "Feature lines are plot-construction evidence" not in html
    assert "Raw feature-line evidence" not in html
    assert "Characteristic points are the run-level and aggregate anchors" not in html
    assert "Raw characteristic-point evidence" not in html

    plot_block = next(
        block
        for section in document["sections"]
        for block in section["blocks"]
        if block["id"] == "aggregate_stress_strain_plot"
    )
    plot_spec = plot_block["data"]["vega_lite_spec"]
    freshness = plot_block["data"]["plot_data_freshness"]
    replicate_values = plot_spec["datasets"]["replicates"]
    aggregate_values = plot_spec["datasets"]["aggregate"]
    assert freshness["replicate_source"] == "bounded_curve_family"
    assert freshness["boundary_aligned_replicates"] is True
    assert freshness["boundary_aligned_aggregation"] is True
    assert "peak_decline_non_recovery" in freshness["policy_signatures"][0]
    assert freshness["status"] == "stale"
    assert freshness["filtered_replicate_row_count"] == 0
    assert "autosize" not in plot_spec
    assert plot_spec["hconcat"][0]["width"] == 330
    assert plot_spec["hconcat"][1]["width"] == 360
    assert plot_spec["hconcat"][0]["height"] == 270
    assert plot_spec["hconcat"][1]["height"] == 270
    assert plot_spec["hconcat"][0]["encoding"]["x"]["title"] == "Actual strain / %"
    assert plot_spec["hconcat"][1]["layer"][2]["encoding"]["x"]["title"] == "Normalised strain / %"
    assert max(row["actual_strain_percent"] for row in replicate_values) < 0.6
    assert all(0.0 <= row["experiment_progress"] <= 1.0 for row in replicate_values)
    assert all("strain_percent" not in row for row in aggregate_values)
    assert max(row["analysis_progress_percent"] for row in aggregate_values) == pytest.approx(100.0)


def test_iso14126_resolve_to_report_alignment_is_factual(stage24_mtda: Path) -> None:
    report = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    html = _text_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")
    checks_payload = report["iso14126_resolve_checks"]
    checks = checks_payload["records"] if isinstance(checks_payload, dict) else checks_payload
    individual_rows = report["individual_results"]

    required_keys = {
        "requirement_id",
        "standard_basis",
        "source",
        "resolved_value",
        "status",
        "consequence",
        "aggregate_eligible",
        "report_target",
    }
    assert checks
    assert all(required_keys <= set(record) for record in checks)
    requirement_ids = {record["requirement_id"].split(":", 1)[0] for record in checks}
    assert {
        "iso14126.clause_9_3_back_to_back_strain",
        "iso14126.clause_9_4_mounting_prestrain_face_difference",
        "iso14126.clause_9_5_speed_of_testing",
        "iso14126.clause_9_6_load_strain_recorded",
        "iso14126.clause_9_7_fmax",
        "iso14126.clause_9_8_validity",
        "iso14126.clause_9_9_failure_mode",
        "iso14126.clause_7_1_minimum_specimen_count",
        "iso14126.clause_7_2_discard_replacement",
        "iso14126.annex_a_fixture_alignment",
    } <= requirement_ids

    assert any(record["standard_basis"] == "ISO 14126 Clause 7.1" and record["consequence"] == "standard_non_compliant" for record in checks)
    assert any(record["standard_basis"] == "ISO 14126 Clause 9.5" and record["status"] == "missing" for record in checks)
    assert any(record["standard_basis"] == "ISO 14126 Clause 9.9 / Clause 12(l)" and record["status"] == "missing" for record in checks)
    assert report["summary"]["standard_required_missing_count"] >= 1
    assert "Section 11.2" in html
    assert "Required report content complete." not in html
    assert "2 required fields missing" in html
    assert "ISO 14126 Clause 7.1" in html
    assert "ISO 14126 Clause 9.9 / Clause 12(l)" not in html
    assert "Analysis interval policy</td><td>Internal reduction/audit policy" not in html
    assert "Analysis interval: reported calculations use the resolved test interval" in html
    assert "Max load" in html
    assert "Failure mode" in html
    assert "Run #" in html
    assert ">run 001<" not in html
    assert ">run_001<" not in html
    assert ">#1<" in html
    assert "Related report surfaces" not in html
    assert "Workbench Evidence" not in html
    assert "missing</td><td>accepted" in html
    assert "Modulus</span> / <span class=\"unit-label\">MPa" in html
    assert "Modulus</span> / <span class=\"unit-label\">GPa" not in html
    assert all(row.get("max_load_N") not in (None, "") for row in individual_rows)


def test_audit_report_has_operator_facing_analysis_sections(stage24_mtda: Path) -> None:
    audit = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    html = _text_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.html")

    expected_payload_keys = {
        "source_mtdp",
        "method_package",
        "schema_method_compatibility",
        "mapping_profile",
        "readiness",
        "validation",
        "acceptance",
        "human_overrides",
        "mtda_finalization",
        "warnings",
        "artifact_links",
    }
    assert expected_payload_keys <= set(audit)
    assert audit["artifact_links"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert REMOVED_DATASET_KEY not in audit["artifact_links"]
    assert audit["artifact_links"]["dataset_plot"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
    assert audit["artifact_links"]["surface_manifest"] == MTDAAlignedLayout.surface_manifest
    for phrase in (
        "Audit Overview",
        "Evidence Navigation / Run Evidence Index",
        "Run-wise Evidence Packets",
        "Aggregate Evidence Packet",
        "Decision Register",
        "Source data",
        "Method",
        "Experiment boundary resolution",
        "Validation",
        "Curve-shape diagnostics",
    ):
        assert phrase in html
    assert "Artifact Links" not in html
    assert "Technical trace" not in html
    assert "CAG-CF-Modied-ULV20.mtdp" in html
    assert "flow-card--warn" not in html
    assert "flow-card--ok" not in html
    assert "process-flow" not in html
    assert 'class="report-state-card audit-overview-card"' in html
    assert ".vg-tooltip table" in html
    assert "Click run names in the legend" not in html
    assert "run_selector" not in html


def test_surface_manifest_records_aligned_report_audit_status(stage24_mtda: Path) -> None:
    validation = _json_member(stage24_mtda, MTDAAlignedLayout.validation)
    surface = _json_member(stage24_mtda, MTDAAlignedLayout.surface_manifest)

    assert "report_quality_gate" not in validation
    assert surface["layout_version"] == MTDAAlignedLayout.name
    assert surface["surfaces"]["test_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
    assert surface["surfaces"]["test_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert surface["surfaces"]["audit_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
    assert surface["surfaces"]["audit_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
    assert surface["surfaces"]["test_report"]["report_completion_status"] == "INCOMPLETE"
    expected_validation_status = (
        validation.get("validation_report", {}).get("status")
        or (validation.get("validation_summary") or [{}])[0].get("status")
    )
    assert surface["surfaces"]["audit_report"]["validation_status"] == expected_validation_status
    assert MTDAAlignedLayout.validation in surface["key_json_artifacts"]


def test_final_report_runs_agree_across_report_audit_surface_and_quality_gate(stage24_mtda: Path) -> None:
    method_outputs = _json_member(stage24_mtda, MTDAAlignedLayout.method_outputs)
    final_rows = method_outputs["final_report_runs"]
    report = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    audit = _json_member(stage24_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    surface = _json_member(stage24_mtda, MTDAAlignedLayout.surface_manifest)
    selected_ids = [row["run_id"] for row in final_rows if _truthy(row.get("included", True))]

    assert report["selection_set"] == "final_report_runs"
    assert report["summary"]["selected_run_count"] == len(selected_ids)
    assert audit["acceptance"]["final_selection_set"] == "final_report_runs"
    assert surface["cross_surface_agreement"]["final_report_run_ids"] == selected_ids
    assert surface["cross_surface_agreement"]["selected_run_count"] == len(selected_ids)


def test_wizard_output_model_exposes_report_audit_rc_statuses(stage24_mtda: Path) -> None:
    surface = _json_member(stage24_mtda, MTDAAlignedLayout.surface_manifest)
    with zipfile.ZipFile(stage24_mtda) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    model = output_review_view_model(
        {
            "output_path": str(stage24_mtda),
            "archive_members": members,
            "surface_manifest": surface,
        }
    )
    actions = {action["action_id"]: action for action in model["actions"]}

    assert model["missing_field_summary"]["test_report_rc_status"] == ""
    assert model["missing_field_summary"]["audit_report_rc_status"] == ""
    assert model["missing_field_summary"]["report_quality_gate_status"] == ""
    assert model["status_summary"]["test_report_rc_status"] == ""
    assert model["status_summary"]["audit_report_rc_status"] == ""
    assert model["selection_summary"]["selected_run_count"] == len(surface["cross_surface_agreement"]["final_report_run_ids"])
    assert actions["open_test_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_workbench"]["enabled"] is False
    assert actions["open_surface_manifest"]["enabled"] is True


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
