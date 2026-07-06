from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from archives.core.layouts import MTDAAlignedLayout
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from operations.core.evidence_contract import operation_evidence_contract_records
from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contracts
from ui.method_run_wizard.view_models.gate_summary import (
    acceptance_gate_view_model,
    readiness_gate_view_model,
    validation_gate_view_model,
)
from ui.method_run_wizard.view_models.output_review import output_review_view_model


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def stage26_mtda(stage26_canonical_mtda: Path) -> Path:
    return stage26_canonical_mtda


def test_operation_evidence_contracts_exist_for_key_operations() -> None:
    contracts = operation_evidence_contract_records()
    expected = {
        "resolve_experiment_boundaries",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
        "bending_diagnostic",
    }
    assert expected <= set(contracts)
    for operation_type in expected:
        contract = contracts[operation_type]
        assert contract["operation_type"] == operation_type
        assert contract["evidence_role"]
        assert contract["default_audit_block"]
        assert contract["default_audit_view"]
        assert contract["default_workbench_view"]
        assert "input_schema" in contract
        assert "output_schema" in contract
        assert contract["evidence_artifacts_required"]


def test_procedure_and_audit_block_indexes_are_written_to_mtda(stage26_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        audit = json.loads(archive.read(f"{MTDAAlignedLayout.reports_prefix}audit_report.json"))
        surface = json.loads(archive.read(MTDAAlignedLayout.surface_manifest))
        checksums = json.loads(archive.read(MTDAAlignedLayout.checksums))
        provenance = json.loads(archive.read(MTDAAlignedLayout.provenance))

    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.json" in names
    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.json" in checksums["files"]
    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.json" in surface["key_json_artifacts"]
    assert not any(name.startswith(("audit/", "workbench/")) for name in names)
    procedure = audit["procedure_evidence"]
    audit_blocks = audit["audit_blocks"]
    assert procedure["artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#procedure_evidence"
    assert audit_blocks["artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks"
    assert audit_blocks["index_artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks"
    method_run_outputs = next(event for event in provenance["events"] if event["event"] == "method_run_completed")["outputs"]
    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.html" in method_run_outputs
    assert procedure["run_count"] == 7
    assert procedure["operation_count"] > 0
    assert audit_blocks["summary"]["bending_separate"] is True


def test_audit_block_grouping_includes_expected_operations(stage26_mtda: Path) -> None:
    trace = _json_member(stage26_mtda, MTDAAlignedLayout.method_outputs)["operation_trace"]
    operations = [row for row in trace["operations"] if row.get("run_id") == "run_001"]
    stress_types = {
        row["operation_type"]
        for row in operations
        if row.get("default_audit_block") == "run_stress_strain_reduction"
    }
    bending_types = {
        row["operation_type"]
        for row in operations
        if row.get("default_audit_block") == "run_bending_evidence"
    }

    assert {
        "resolve_experiment_boundaries",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
    } <= stress_types
    assert "bending_diagnostic" not in stress_types
    assert bending_types == {"bending_diagnostic"}


def test_audit_report_renders_runwise_and_aggregate_packets(stage26_mtda: Path) -> None:
    html = _text_member(stage26_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.html")
    audit = _json_member(stage26_mtda, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")

    assert audit["procedure_evidence"]["artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#procedure_evidence"
    assert audit["audit_blocks"]["artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks"
    assert audit["audit_blocks"]["index_artifact"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks"
    for phrase in (
        "Audit Overview",
        "Run-wise Evidence Packets",
        "Run-wise evidence packet",
        "Stress-strain reduction evidence",
        "Bending evidence",
        "Aggregate Evidence Packet",
        "Dataset / cohort population",
        "Aggregate curve-family evidence",
        "Curve-shape outlier diagnostics",
        "Decision Register",
    ):
        assert phrase in html
    assert audit["audit_blocks"]["summary"]["stress_strain_grouping"].startswith("boundary")
    assert audit["audit_blocks"]["summary"]["bending_separate"] is True


def test_test_report_remains_formal_result_surface(stage26_mtda: Path) -> None:
    html = _text_member(stage26_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.html")
    report = _json_member(stage26_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")

    assert "ISO 14126 Test Report" in html
    assert report["summary"]["selection_set"] == "final_report_runs"
    assert "Per-run audit packets" not in html
    assert "procedure_evidence_index" not in html
    assert "Run-wise evidence packet" not in html


def test_workbench_operation_trace_still_links_operation_debug(stage26_mtda: Path) -> None:
    trace = _json_member(stage26_mtda, MTDAAlignedLayout.method_outputs)["operation_trace"]

    operation_types = {row["operation_type"] for row in trace["operations"]}
    assert "resolve_experiment_boundaries" in operation_types
    assert "bending_diagnostic" in operation_types
    assert any(row["view_type"] == "experiment_boundary_resolution" for row in trace["operations"])
    assert trace["experiment_boundaries"]


def test_wizard_page_models_expose_action_contracts() -> None:
    contracts = wizard_page_action_contracts()
    expected_pages = {
        "package",
        "method",
        "mapping",
        "readiness",
        "report_metadata",
        "execution",
        "validation",
        "acceptance",
        "output",
    }
    assert expected_pages <= set(contracts)
    for page_id in expected_pages:
        contract = contracts[page_id]
        assert contract["purpose"]
        assert contract["operator_decision"]
        assert contract["allowed_actions"]
        assert contract["primary_evidence"]
        assert contract["downstream_consequence"]

    readiness = readiness_gate_view_model({"status": "READY", "requirements": []})
    validation = validation_gate_view_model({"summary": {"status": "pass"}, "checks": []})
    acceptance = acceptance_gate_view_model({"summary": {}, "flags": []})
    output = output_review_view_model({"archive_members": [MTDAAlignedLayout.surface_manifest], "surface_manifest": {}})
    assert readiness["page_action_contract"]["page_id"] == "readiness"
    assert validation["page_action_contract"]["page_id"] == "validation"
    assert acceptance["page_action_contract"]["page_id"] == "acceptance"
    assert output["page_action_contract"]["page_id"] == "output"
    assert output["wizard_action_surface"]["surface_role"] == "action_decision_repair"


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
