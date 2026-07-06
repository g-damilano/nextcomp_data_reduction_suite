from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.human_decision import HumanAcceptanceDecision
from acceptance.selection_editor import FINAL_SELECTION_ID, SelectionEditor


def test_override_reason_required_for_manual_inclusion_changes() -> None:
    with pytest.raises(ValueError, match="Reason is required"):
        HumanAcceptanceDecision(run_id="run_001", decision_type="remove")

    decision = HumanAcceptanceDecision(run_id="run_001", decision_type="confirm")

    assert decision.reason == ""
    assert decision.decision_type == "confirm"


def test_selection_editor_preserves_machine_sets_and_recomputes_final_selection() -> None:
    specimen_results = [
        {"run_id": "run_001", "specimen_name": "E1"},
        {"run_id": "run_002", "specimen_name": "E2"},
        {"run_id": "run_003", "specimen_name": "E3"},
    ]
    machine_selection_sets = {
        "schema_id": "method.selection_sets.v0_1",
        "default_selection_set": "auto_recommended_runs",
        "selection_sets": [
            {"selection_id": "all_runs", "run_ids": ["run_001", "run_002", "run_003"]},
            {"selection_id": "auto_recommended_runs", "run_ids": ["run_001", "run_002"]},
            {"selection_id": "excluded_runs", "run_ids": ["run_003"]},
        ],
    }
    machine_membership = [
        {"selection_set": "auto_recommended_runs", "run_id": "run_001", "included": True},
        {"selection_set": "auto_recommended_runs", "run_id": "run_002", "included": True},
        {"selection_set": "auto_recommended_runs", "run_id": "run_003", "included": False},
    ]
    acceptance_report = {
        "default_selection_set": "auto_recommended_runs",
        "run_states": {
            "run_001": "accepted",
            "run_002": "accepted",
            "run_003": "excluded",
        },
    }
    decisions = (
        HumanAcceptanceDecision(run_id="run_002", decision_type="remove", reason="Edge delamination"),
        HumanAcceptanceDecision(run_id="run_003", decision_type="restore", reason="Operator confirmed valid failure"),
    )

    final = SelectionEditor().apply(
        specimen_results=specimen_results,
        acceptance_report=acceptance_report,
        machine_selection_sets=machine_selection_sets,
        machine_selection_membership=machine_membership,
        decisions=decisions,
    )

    machine_by_id = {row["selection_id"]: row for row in final.selection_sets_final["selection_sets"] if row.get("source") == "machine"}
    final_by_run = {row["run_id"]: row for row in final.final_report_runs}

    assert machine_by_id["auto_recommended_runs"]["run_ids"] == ["run_001", "run_002"]
    assert final.selection_sets_final["default_selection_set"] == FINAL_SELECTION_ID
    assert final.selection_sets_final["selection_source"] == "human_final"
    assert final.final_run_ids == ("run_001", "run_003")
    assert final_by_run["run_002"]["final_included"] is False
    assert final_by_run["run_002"]["human_decision"] == "remove"
    assert final_by_run["run_003"]["final_included"] is True
    assert len(final.override_ledger["records"]) == 2
