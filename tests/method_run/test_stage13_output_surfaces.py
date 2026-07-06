from __future__ import annotations

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


@pytest.fixture(scope="module")
def stage13_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage13_surfaces") / "CAG-CF-Modied-ULV20.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
        )
    )
    assert result.status == "completed"
    return output


def test_mtda_contains_separate_test_audit_and_workbench_surfaces(stage13_mtda: Path) -> None:
    with zipfile.ZipFile(stage13_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}

    assert {
        MTDAAlignedLayout.index,
        f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        f"{MTDAAlignedLayout.reports_prefix}test_report.json",
        f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
        f"{MTDAAlignedLayout.reports_prefix}audit_report.json",
        MTDAAlignedLayout.method_outputs,
        MTDAAlignedLayout.surface_manifest,
    } <= names
    assert {name.split("/", 1)[0] for name in names} <= {"index.html", "dataset", "metadata"}
    assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
    method_outputs = _json_member(stage13_mtda, MTDAAlignedLayout.method_outputs)
    assert "operation_trace" in method_outputs


def test_manifest_records_artifact_surfaces(stage13_mtda: Path) -> None:
    manifest = _json_member(stage13_mtda, MTDAAlignedLayout.manifest)

    assert manifest["layout_version"] == MTDAAlignedLayout.name
    assert manifest["artifact_surfaces"]["home"] == MTDAAlignedLayout.index
    assert manifest["artifact_surfaces"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
    assert manifest["artifact_surfaces"]["audit_report"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
    assert manifest["artifact_surfaces"]["test_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert manifest["artifact_surfaces"]["audit_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
    assert manifest["artifact_surfaces"]["surface_manifest"] == MTDAAlignedLayout.surface_manifest
    assert manifest["artifact_surfaces"]["method_outputs"] == MTDAAlignedLayout.method_outputs


def test_test_report_is_generic_report_and_renders_vega(stage13_mtda: Path) -> None:
    report = _json_member(stage13_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    html = _text_member(stage13_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")
    completion = report["report_completion_status"]

    assert report["surface"] == "test_report"
    assert report["report_recipe_id"] == "iso14126_report_v0_2"
    assert report["report_completion_status"]["status"] in {"COMPLETE", "COMPLETE_WITH_WARNINGS", "INCOMPLETE"}
    assert completion["schema_id"] == "report.completion_status.v0_1"
    assert "data-vega-block" in html
    assert "vegaEmbed" in html
    assert "Stress-strain aggregate" in html


def test_audit_report_is_operator_analysis_evidence_surface(stage13_mtda: Path) -> None:
    audit = _json_member(stage13_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    html = _text_member(stage13_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.html")

    assert audit["surface"] == "audit_report"
    assert {"source_mtdp", "method_package", "mapping_profile", "readiness", "validation", "acceptance", "human_overrides"} <= set(audit)
    assert audit["artifact_links"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert REMOVED_DATASET_KEY not in audit["artifact_links"]
    assert audit["artifact_links"]["dataset_plot"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
    assert audit["artifact_links"]["surface_manifest"] == MTDAAlignedLayout.surface_manifest
    assert "Audit Overview" in html
    assert "Process Verification Overview" not in html
    assert "Artifact Links" not in html
    assert "Formal result values are in" in html
    assert "test_report.html" in html


def test_output_review_model_exposes_three_surfaces_and_statuses(stage13_mtda: Path) -> None:
    with zipfile.ZipFile(stage13_mtda) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    surface = _json_member(stage13_mtda, MTDAAlignedLayout.surface_manifest)
    model = output_review_view_model(
        {
            "output_path": str(stage13_mtda),
            "archive_members": members,
            "surface_manifest": surface,
            "report_completion_status": "COMPLETE_WITH_WARNINGS",
            "validation_status": "pass",
            "final_selection_source": "machine_default_confirmed",
            "warning_count": 0,
            "human_override_count": 0,
            "report_override_count": 2,
        }
    )
    lanes = {lane["lane_id"]: lane for lane in model["lanes"]}
    actions = {action["action_id"]: action for action in model["actions"]}

    assert lanes["test_report"]["available"] is True
    assert lanes["audit_report"]["available"] is True
    assert lanes["workbench"]["available"] is False
    assert model["surface_members"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert model["surface_members"]["audit_report"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
    assert model["surface_members"]["method_development_workbench"] == ""
    assert actions["open_test_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_workbench"]["enabled"] is False
    assert actions["edit_report_completion"]["enabled"] is True
    assert actions["regenerate_report_only"]["enabled"] is False
    assert model["status_summary"]["report_completion_status"] == "COMPLETE_WITH_WARNINGS"
    assert model["status_summary"]["report_override_count"] == 2


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
