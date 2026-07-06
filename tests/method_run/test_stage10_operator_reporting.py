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

from methods.core.method_run_service import MethodRunRequest, MethodRunService
from ui.method_run_wizard.view_models.gate_summary import (
    acceptance_gate_view_model,
    readiness_gate_view_model,
    validation_gate_view_model,
)
from ui.method_run_wizard.view_models.mapping_preview import mapping_preview_view_model
from ui.method_run_wizard.view_models.method_preview import method_preview_view_model
from ui.method_run_wizard.view_models.output_review import output_review_view_model
from ui.method_run_wizard.view_models.package_preview import package_preview_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def service() -> MethodRunService:
    return MethodRunService()


@pytest.fixture(scope="module")
def stage10_mtda(service: MethodRunService, tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage10_method_run") / "stage10.mtda"
    result = service.run(
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


def test_package_method_and_mapping_preview_view_models(service: MethodRunService) -> None:
    package = package_preview_view_model(service.load_package(INPUT))
    method = method_preview_view_model(service.load_method(METHOD))
    mapping = mapping_preview_view_model(service.load_mapping(MAPPING, METHOD))

    assert package["schema_name"] == "package_preview_view_model"
    assert package["schema_id"] == "mechanical.compression"
    assert package["schema_version"] == "0.2.0"
    assert package["run_count"] == 7
    assert package["source_file_count"] == 7
    assert {"Load", "Front Strain", "Rear Strain"} <= set(package["available_channels"])
    assert package["runs"][0]["run_id"] == "run_001"

    assert method["schema_name"] == "method_preview_view_model"
    assert method["method_id"] == "iso14126_2023"
    assert method["analysis_type"] == "mechanical.compression"
    assert {"resolve", "reduce", "validation", "acceptance", "report"} <= set(method["method_phases"])
    assert "channel.load_N" in method["required_inputs"]
    assert "specimen_properties.compressive_strength_MPa" in method["expected_outputs"]

    assert mapping["schema_name"] == "mapping_preview_view_model"
    assert mapping["status"] == "warnings"
    assert mapping["summary"]["execution_critical_mapped"] == mapping["summary"]["execution_critical_total"]
    assert any(row["method_field"] == "channel.front_strain" and row["status"] == "pass" for row in mapping["rows"])
    assert any(row["severity"] == "report_completeness" and row["status"] == "warn" for row in mapping["rows"])


def test_gate_view_models_are_summary_first(stage10_mtda: Path) -> None:
    readiness = readiness_gate_view_model(_json_member(stage10_mtda, "readiness/readiness_report.json"))
    validation = validation_gate_view_model(_json_member(stage10_mtda, "validation/validation_report.json"))
    acceptance = acceptance_gate_view_model(_json_member(stage10_mtda, "acceptance/acceptance_report.json"))

    assert readiness["gate_id"] == "readiness"
    assert readiness["next_enabled"] is True
    assert readiness["status"] == "ready_with_warnings"
    assert readiness["groups"][0]["group_id"] == "execution_critical"

    assert validation["gate_id"] == "validation"
    assert validation["next_enabled"] is True
    assert [card["label"] for card in validation["summary_cards"]] == ["Status", "Passed", "Warned", "Failed"]
    assert validation["groups"][0]["group_id"] == "failed_checks"

    assert acceptance["gate_id"] == "acceptance"
    assert acceptance["next_enabled"] is True
    assert any(card["label"] == "Default Selection" for card in acceptance["summary_cards"])
    assert {"excluded_flags", "review_flags", "selection_sets", "bending_pattern_flags"} <= {
        group["group_id"] for group in acceptance["groups"]
    }


def test_stage10_report_sections_and_aggregate_plot_spec(stage10_mtda: Path) -> None:
    with zipfile.ZipFile(stage10_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {
            "report/report_sections.json",
            "report/report_completeness_summary.csv",
            "report/failure_analysis.csv",
            "report/failure_observations.csv",
            "report/invalid_specimen_summary.csv",
            "report/bending_distribution_summary.csv",
            "report/deviations_from_standard.csv",
            "report/aggregate_curve_summary.csv",
            "report/aggregate_plot_spec.json",
            "report/vega_specs/failure_analysis_bending_distribution.json",
        } <= names

    report = _json_member(stage10_mtda, "report/iso14126_report.json")
    sections = _json_member(stage10_mtda, "report/report_sections.json")
    completeness = _csv_member(stage10_mtda, "report/report_completeness_summary.csv")
    curve_summary = _csv_member(stage10_mtda, "report/aggregate_curve_summary.csv")
    plot_spec = _json_member(stage10_mtda, "report/aggregate_plot_spec.json")

    assert len(sections) == 12
    assert [section["title"] for section in sections] == [
        "Test Identification",
        "Material Identification",
        "Specimen Preparation",
        "Loading Fixture",
        "Specimen Geometry",
        "Test Conditions",
        "Measurement Method",
        "Individual Test Results",
        "Aggregated Results",
        "Failure Analysis",
        "Deviations from Standard",
        "Remarks",
    ]
    assert report["report_sections"] == sections
    assert completeness[0]["section_id"] == "test_identification"
    assert curve_summary[0]["selection_set"] == "final_report_runs"
    assert curve_summary[0]["supports_range_band"] == "True"
    assert curve_summary[0]["supports_std_band"] == "True"

    assert plot_spec["schema_id"] == "method.aggregate_plot_spec.v0_1"
    assert plot_spec["selection_set"] == "final_report_runs"
    assert plot_spec["data_sources"]["aligned_curves"] == "report/aligned_curves.csv"
    assert plot_spec["layers"]["individual_replicates"]["enabled"] is True
    assert plot_spec["layers"]["range_band"]["max_field"] == "max"
    assert plot_spec["layers"]["std_band"]["upper_expression"] == "mean + std"
    assert plot_spec["layers"]["observation_count"]["field"] == "n"


def test_output_review_view_model_exposes_operator_lanes(stage10_mtda: Path) -> None:
    with zipfile.ZipFile(stage10_mtda) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    model = output_review_view_model(
        {
            "output_path": str(stage10_mtda),
            "archive_members": members,
            "workbench_path": str(stage10_mtda.with_suffix("")) + "_workbench",
        }
    )

    lanes = {lane["lane_id"]: lane for lane in model["lanes"]}
    assert {"test_report", "audit_report", "workbench", "artifact_browser"}.issubset(lanes)
    assert {"report_completion", "finalization", "production_export"}.issubset(lanes)
    assert lanes["test_report"]["status"] == "available"
    assert lanes["audit_report"]["role"].startswith("Process-verification evidence")
    assert lanes["workbench"]["available"] is True
    assert lanes["artifact_browser"]["available"] is True
    assert lanes["report_completion"]["available"] is True
    assert lanes["finalization"]["available"] is True
    assert "shareable" in lanes["production_export"]["role"].lower()
    assert "report/aggregate_plot_spec.json" in model["report_members"]


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))
