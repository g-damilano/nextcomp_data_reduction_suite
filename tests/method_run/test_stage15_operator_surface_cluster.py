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
def stage15_mtda(service: MethodRunService, tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage15_operator_surface") / "operator_surface.mtda"
    result = service.run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output


def test_package_preview_contains_operator_identity_summary(service: MethodRunService) -> None:
    model = package_preview_view_model(service.load_package(INPUT))

    assert model["package_path"].endswith(".mtdp")
    assert model["schema_id"] == "mechanical.compression"
    assert model["schema_version"] == "0.2.0"
    assert model["run_count"] == 7
    assert model["source_file_count"] == 7
    assert model["normalized_file_count"] == 7
    assert model["raw_file_count"] == 7
    assert model["source_identity_summary"]["status"] == "ok"
    assert model["validity_summary"]["valid"] == 7
    assert model["failure_mode_summary"]["0"] == 1
    assert model["provenance"]["status"] == "present"
    assert model["provenance"]["checksum_status"] == "present"
    assert len(model["provenance"]["sha256"]) == 64
    assert model["source_files"][0]["normalized_package_path"].startswith("normalized/")
    assert model["source_files"][0]["raw_package_path"].startswith("raw/")


def test_method_preview_exposes_process_and_surfaces(service: MethodRunService) -> None:
    model = method_preview_view_model(service.load_method(METHOD))

    assert model["method_id"] == "iso14126_2023"
    assert model["supported_analysis_types"] == ["mechanical.compression"]
    assert {"resolve", "reduce", "validation", "acceptance", "report"} <= set(model["method_phases"])
    assert "channel.load_N" in model["required_inputs"]
    surfaces = {row["surface"]: row["member"] for row in model["surface_outputs"]}
    assert surfaces["test_report"] == "dataset/04_reports/test_report.html"
    assert surfaces["audit_report"] == "dataset/04_reports/audit_report.html"
    assert surfaces["method_development_workbench"] == "metadata/software/method_outputs.json#operation_trace"
    assert any("report-ready evidence" in item for item in model["process_summary"])


def test_mapping_preview_is_readable_without_opening_json(service: MethodRunService) -> None:
    model = mapping_preview_view_model(service.load_mapping(MAPPING, METHOD, INPUT))
    rows = {row["method_field"]: row for row in model["rows"]}

    assert model["status"] == "warnings"
    assert "Mapping tells the method" in model["why_required"]
    assert rows["specimen.width_mm"]["operator_status"] == "found"
    assert rows["specimen.width_mm"]["source_location"] == "field:Width"
    assert rows["specimen.width_mm"]["example_value"] == "9.91"
    assert rows["channel.load_N"]["coverage"] == "7/7 runs"
    assert rows["channel.front_strain"]["unit"] == "mm/mm"
    assert any(row["operator_status"] == "warning" for row in model["rows"])


def test_readiness_validation_and_acceptance_pages_are_gate_summaries(stage15_mtda: Path) -> None:
    readiness_bundle = _json_member(stage15_mtda, MTDAAlignedLayout.readiness)
    validation_bundle = _json_member(stage15_mtda, MTDAAlignedLayout.validation)
    method_outputs = _json_member(stage15_mtda, MTDAAlignedLayout.method_outputs)
    report = _json_member(stage15_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    readiness = readiness_gate_view_model(readiness_bundle["readiness_report"])
    validation = validation_gate_view_model(validation_bundle["validation_report"])
    acceptance = acceptance_gate_view_model(
        method_outputs["acceptance_report"],
        final_selection_sets={
            "default_selection_set": "final_report_runs",
            "selection_source": report["selection_source"],
        },
        final_membership=method_outputs["selection_membership"],
        final_report_runs=method_outputs["final_report_runs"],
        human_decisions={"decisions": []},
        override_ledger={"records": []},
    )

    assert readiness["status"] == "ready_with_warnings"
    assert readiness["next_enabled"] is True
    assert {"execution_critical", "report_completeness", "per_run_warnings"} <= {
        group["group_id"] for group in readiness["groups"]
    }
    assert validation["next_enabled"] is True
    assert {"failed_checks", "warned_checks", "checks_by_run", "checks_by_type"} <= {
        group["group_id"] for group in validation["groups"]
    }
    assert acceptance["next_enabled"] is True
    assert {"final_selection_membership", "human_decisions", "curve_family_assessment"} <= {
        group["group_id"] for group in acceptance["groups"]
    }
    assert any(card["label"] == "Final Report Runs" for card in acceptance["summary_cards"])


def test_output_page_is_handoff_dashboard_and_surfaces_agree(stage15_mtda: Path) -> None:
    members = _members(stage15_mtda)
    method_outputs = _json_member(stage15_mtda, MTDAAlignedLayout.method_outputs)
    surface = _json_member(stage15_mtda, MTDAAlignedLayout.surface_manifest)
    report = _json_member(stage15_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    audit = _json_member(stage15_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    output_model = output_review_view_model(
        {
            "output_path": str(stage15_mtda),
            "archive_members": members,
            "surface_manifest": surface,
            "final_selection_source": report["selection_source"],
            "validation_status": _json_member(stage15_mtda, MTDAAlignedLayout.validation)["validation_report"]["summary"]["status"],
            "human_override_count": 0,
        }
    )

    assert output_model["surface_members"] == {
        "test_report": f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        "audit_report": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
        "method_development_workbench": "",
    }
    assert f"{MTDAAlignedLayout.aggregate_prefix}run_decision_registry.csv" in output_model["key_csvs"]
    assert MTDAAlignedLayout.validation in output_model["key_artifacts"]
    assert MTDAAlignedLayout.method_outputs in output_model["key_artifacts"]
    actions = {action["action_id"]: action for action in output_model["actions"]}
    assert actions["open_test_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_workbench"]["enabled"] is False

    final_run_ids = {row["run_id"] for row in method_outputs["final_report_runs"] if _truthy(row.get("final_included"))}
    assert report["selection_set"] == "final_report_runs"
    assert report["selection_source"] == "machine_default_confirmed"
    assert set(report["aggregate_plot_spec"]["selected_run_ids"]) == final_run_ids
    assert audit["acceptance"]["selection_source"] == report["selection_source"]
    assert f"{MTDAAlignedLayout.reports_prefix}test_report.html" in members
    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.html" in members
    assert MTDAAlignedLayout.method_outputs in members
    assert not any(member.startswith(("acceptance/", "report/", "audit/", "workbench/")) for member in members)


def test_worker_boundary_remains_plain_data_and_non_widget() -> None:
    worker_source = (SRC / "ui" / "method_run_wizard" / "worker.py").read_text(encoding="utf-8")
    adapter_source = (SRC / "ui" / "method_run_wizard" / "service_adapter.py").read_text(encoding="utf-8")

    assert "QtWidgets" not in worker_source
    assert "QTextDocument" not in worker_source
    assert "QPlainTextEdit" not in worker_source
    assert "progress = QtCore.pyqtSignal(dict)" in worker_source
    assert "completed = QtCore.pyqtSignal(dict)" in worker_source
    assert "failed = QtCore.pyqtSignal(dict)" in worker_source
    assert "def request_to_payload" in adapter_source
    assert "def run_payload" in adapter_source


def _members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return [name for name in archive.namelist() if not name.endswith("/")]


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
