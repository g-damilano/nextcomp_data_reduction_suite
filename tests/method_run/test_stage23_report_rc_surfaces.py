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
def stage23_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage23_report_rc") / "CAG-CF-Modied-ULV20.mtda"
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


def test_surface_manifest_indexes_operator_surfaces_and_key_artifacts(stage23_mtda: Path) -> None:
    with zipfile.ZipFile(stage23_mtda) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read(MTDAAlignedLayout.surface_manifest))
        checksums = json.loads(archive.read(MTDAAlignedLayout.checksums))

    assert MTDAAlignedLayout.surface_manifest in names
    assert MTDAAlignedLayout.surface_manifest in checksums["files"]
    assert manifest["schema_id"] == "mtda.surface_manifest.v0_3"
    assert manifest["layout_version"] == MTDAAlignedLayout.name
    assert manifest["surfaces"]["test_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
    assert manifest["surfaces"]["test_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert manifest["surfaces"]["audit_report"]["html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
    assert manifest["surfaces"]["audit_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
    assert REMOVED_DATASET_KEY not in manifest["surfaces"]
    assert manifest["surfaces"]["dataset_plot"]["html_member"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
    assert f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv" in manifest["key_csv_artifacts"]
    assert MTDAAlignedLayout.checksums in manifest["key_json_artifacts"]


def test_test_report_audit_and_surface_manifest_agree_on_rc_status(stage23_mtda: Path) -> None:
    report = _json_member(stage23_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    audit = _json_member(stage23_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    surface = _json_member(stage23_mtda, MTDAAlignedLayout.surface_manifest)
    method_outputs = _json_member(stage23_mtda, MTDAAlignedLayout.method_outputs)
    agreement = surface["cross_surface_agreement"]
    final_runs = method_outputs["final_report_runs"]

    assert agreement["source_package"] == Path(report["source_package"]).name
    assert audit["source_mtdp"]["path"].endswith(agreement["source_package"])
    assert agreement["method_id"] == report["method_id"] == audit["method_package"]["method_id"]
    assert agreement["readiness_status"] == audit["readiness"]["status"]
    assert agreement["validation_status"] == audit["validation"]["status"]
    assert agreement["report_completion_status"] == report["report_completion_status"]["status"]
    assert agreement["final_report_run_ids"] == [row["run_id"] for row in final_runs if _truthy(row.get("included", True))]
    assert agreement["selected_run_count"] == report["summary"]["selected_run_count"]


def test_test_report_is_formal_result_surface_with_completion_and_vega(stage23_mtda: Path) -> None:
    html = _text_member(stage23_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")

    assert "Formal method results and report-ready evidence" in html
    assert "report_completion_status" in html
    assert "required_missing_count" in html
    assert "recommended_missing_count" in html
    assert "data-vega-block" in html
    assert "vegaEmbed" in html
    assert "Process Verification Overview" not in html


def test_audit_report_is_operator_analysis_evidence_surface(stage23_mtda: Path) -> None:
    audit = _json_member(stage23_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    html = _text_member(stage23_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.html")

    assert audit["surface"] == "audit_report"
    assert audit["purpose"].startswith("ISO 14126 analysis evidence")
    assert audit["mtda_finalization"]["status"] == "not_finalized"
    assert audit["artifact_links"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert REMOVED_DATASET_KEY not in audit["artifact_links"]
    assert audit["artifact_links"]["dataset_plot"] == f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"
    assert audit["artifact_links"]["surface_manifest"] == MTDAAlignedLayout.surface_manifest
    assert "Audit Overview" in html
    assert "MTDA Finalization" not in html
    assert "Artifact Links" not in html
    assert "Technical trace" not in html
    assert "Formal result values are in" in html
    assert "test_report.html" in html


def test_wizard_output_model_uses_surface_manifest_as_handoff_dashboard(stage23_mtda: Path) -> None:
    surface = _json_member(stage23_mtda, MTDAAlignedLayout.surface_manifest)
    with zipfile.ZipFile(stage23_mtda) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    model = output_review_view_model(
        {
            "output_path": str(stage23_mtda),
            "archive_members": members,
            "surface_manifest": surface,
            "last_export_status": "not_run",
            "last_export_profile": "full_html",
        }
    )
    actions = {action["action_id"]: action for action in model["actions"]}

    assert model["surface_manifest_available"] is True
    assert model["surface_statuses"]["test_report"]["status"] == "available"
    assert model["surface_statuses"]["audit_report"]["status"] == "available"
    assert model["surface_statuses"]["method_development_workbench"]["status"] == "not_generated"
    assert model["selection_summary"]["selected_run_count"] == surface["cross_surface_agreement"]["selected_run_count"]
    assert model["export_summary"]["last_export_profile"] == "full_html"
    assert actions["open_test_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_workbench"]["enabled"] is False
    assert actions["export_production_bundle"]["enabled"] is True


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    import csv
    import io

    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
