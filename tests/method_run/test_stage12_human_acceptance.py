from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.human_decision import HumanAcceptanceDecision
from acceptance.selection_editor import FINAL_SELECTION_ID, SelectionEditor
from archives.mtda import MTDAWriter
from archives.mtdp import MTDPPackageReader
from methods.core.method_executor import MethodExecutor
from methods.core.method_package import MethodPackage
from methods.core.method_run_service import MethodRunRequest, MethodRunService, load_mapping
from reporting.report_builder import ReportBuilder
from ui.method_run_wizard.view_models.gate_summary import acceptance_gate_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_mtda_contains_final_selection_artifacts(tmp_path: Path) -> None:
    result = _canonical_result()
    output = tmp_path / "stage12.mtda"

    written = MTDAWriter().write(result, output)

    required = {
        "acceptance/human_decisions.json",
        "acceptance/human_decisions.csv",
        "acceptance/override_ledger.json",
        "acceptance/selection_sets_final.json",
        "acceptance/selection_membership_final.csv",
        "acceptance/final_report_runs.csv",
    }
    assert required <= set(written.members)
    with zipfile.ZipFile(output) as archive:
        assert required <= set(json.loads(archive.read("checksums.json"))["files"])
        final_sets = json.loads(archive.read("acceptance/selection_sets_final.json"))
        final_runs = _csv_member(archive, "acceptance/final_report_runs.csv")

    assert final_sets["default_selection_set"] == FINAL_SELECTION_ID
    assert final_sets["machine_default_selection_set"] == "auto_recommended_runs"
    assert final_runs


def test_report_aggregation_uses_human_final_selection_when_overrides_exist() -> None:
    result = _canonical_result()
    included = [row["run_id"] for row in result.final_report_runs or [] if row["final_included"]]
    run_to_remove = included[0]
    decisions = (
        HumanAcceptanceDecision(
            run_id=run_to_remove,
            decision_type="remove",
            reason="Operator removed from final report selection",
            reviewer="qa",
            source_surface="test",
        ),
    )
    final = SelectionEditor().apply(
        specimen_results=result.specimen_results,
        acceptance_report=result.acceptance_report,
        machine_selection_sets=result.selection_sets,
        machine_selection_membership=result.selection_membership,
        decisions=decisions,
    )
    result = replace(
        result,
        human_decisions=final.human_decisions,
        human_decision_rows=final.human_decision_rows,
        override_ledger=final.override_ledger,
        override_ledger_rows=final.override_ledger_rows,
        selection_sets_final=final.selection_sets_final,
        selection_membership_final=final.selection_membership_final,
        final_report_runs=final.final_report_runs,
    )

    report = ReportBuilder().build(result)
    payload = json.loads(report.files["report/iso14126_report.json"])

    assert payload["selection_set"] == FINAL_SELECTION_ID
    assert payload["selection_source"] == "human_final"
    assert payload["summary"]["selected_run_count"] == len(included) - 1
    assert {row["selection_set"] for row in report.aggregate_statistics} == {FINAL_SELECTION_ID}
    assert run_to_remove not in payload["aggregate_plot_spec"]["selected_run_ids"]


def test_wizard_acceptance_model_exposes_human_decision_surface() -> None:
    result = _canonical_result()

    model = acceptance_gate_view_model(
        result.acceptance_report,
        final_selection_sets=result.selection_sets_final,
        final_membership=result.selection_membership_final,
        final_report_runs=result.final_report_runs,
        human_decisions=result.human_decisions,
        override_ledger=result.override_ledger,
    )

    assert model["final_selection"]["selection_set"] == FINAL_SELECTION_ID
    assert model["run_rows"]
    assert model["override_controls"]["available_decisions"] == [
        "keep",
        "remove",
        "restore",
        "confirm",
        "clear_override",
    ]
    assert {"keep", "remove", "restore"} == set(model["override_controls"]["reason_required_for"])


def test_method_run_service_writes_human_override_report_selection(tmp_path: Path) -> None:
    output = tmp_path / "stage12_service_override.mtda"
    service = MethodRunService()
    request = MethodRunRequest(
        input_package_path=INPUT,
        method_path=METHOD,
        mapping_path=MAPPING,
        output_path=output,
        human_decisions=(
            {
                "run_id": "run_001",
                "decision_type": "remove",
                "reason": "Operator removed from reported aggregate",
                "reviewer": "qa",
                "source_surface": "test",
            },
        ),
    )

    result = service.run(request)

    assert result.status == "completed"
    with zipfile.ZipFile(output) as archive:
        report = json.loads(archive.read("report/iso14126_report.json"))
        final_runs = _csv_member(archive, "acceptance/final_report_runs.csv")

    run_001 = next(row for row in final_runs if row["run_id"] == "run_001")
    assert report["selection_set"] == FINAL_SELECTION_ID
    assert report["selection_source"] == "human_final"
    assert run_001["final_included"] == "False"
    assert run_001["human_decision"] == "remove"


def _canonical_result() -> Any:
    source = MTDPPackageReader().read(INPUT)
    method = MethodPackage.load(METHOD)
    mapping = load_mapping(MAPPING)
    return MethodExecutor().execute(source, method, mapping)


def _csv_member(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))
