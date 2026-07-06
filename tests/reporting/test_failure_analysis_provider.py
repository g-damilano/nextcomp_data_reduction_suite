from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.core.report_context import ReportContext
from reporting.core.report_engine import (  # noqa: PLC2701 - focused regression coverage for report derivation.
    _failure_analysis_observation_rows,
    _failure_analysis_invalid_specimen_rows,
    _failure_analysis_rows,
    _failure_analysis_run_rows,
)
from reporting.providers.reporting_tables import FailureAnalysisObservationsProvider, FailureAnalysisProvider


def test_failure_analysis_provider_returns_iso_summary_rows() -> None:
    result = SimpleNamespace(
        specimen_results=[
            {
                "run_id": "run_001",
                "specimen_name": "S1",
                "primary_failure_mode": "in_plane_shear",
                "failure_location": "within_gauge_length",
                "bending_pattern": "PASS",
                "bending_threshold_percent": 10,
                "bending_point_count": 42,
                "validity": "accepted",
            },
            {
                "run_id": "run_002",
                "specimen_name": "S2",
                "primary_failure_mode": "delamination",
                "failure_location": "grip_end_block",
                "bending_pattern": "FAIL_SUSTAINED_BENDING",
                "bending_threshold_percent": 10,
                "bending_points_above_threshold": 12,
                "bending_fraction_above_threshold": 0.4,
                "bending_point_count": 42,
                "invalid_specimen_reason": "bending_non_compliance",
                "failure_analysis_notes": "visible instability near fixture",
                "validity": "rejected",
            },
        ],
        acceptance_report={"run_states": {"run_001": "accepted", "run_002": "excluded"}, "flags": []},
        curve_family_scores=[],
        run_flags=[],
        final_report_runs=[
            {"run_id": "run_001", "included": True},
            {"run_id": "run_002", "included": False, "human_decision_reason": "bending evidence"},
        ],
    )
    run_rows = _failure_analysis_run_rows(result, "final_report_runs", {"run_001"})
    summary_rows = _failure_analysis_rows(result, "final_report_runs", {"run_001"}, run_rows)
    observation_rows = _failure_analysis_observation_rows(run_rows)
    invalid_rows = _failure_analysis_invalid_specimen_rows(run_rows)
    context = ReportContext(
        result=result,
        recipe={},
        selection_set="final_report_runs",
        selection_run_ids={"run_001"},
        curve_policy={},
        tables={"failure_analysis": summary_rows, "failure_analysis_observations": observation_rows},
    )

    provided = FailureAnalysisProvider().provide(context)
    observations = FailureAnalysisObservationsProvider().provide(context)

    assert [row["Field"] for row in provided] == [
        "Failure Observation Completeness",
        "Invalid Specimens",
        "Bending Compliance",
        "Notes",
    ]
    assert provided[0]["Value"] == (
        "Failure mode recorded for 1 of 1 reported specimen; failure location recorded for 1 of 1."
    )
    assert "Accepted" not in "\n".join(row["Field"] for row in provided)
    assert all("Basis" not in row for row in provided)
    assert provided[1]["Value"] == "#2 excluded/reviewed; see invalid specimen summary."
    assert "Criterion: 10 % over 10-90 % Fmax." in provided[2]["Value"]
    assert "#2" not in provided[2]["Value"]
    assert "Excluded/reviewed for bending" not in provided[2]["Value"]
    assert "sustained bending failure" not in provided[2]["Value"]
    assert observations == [
        {
            "Run #": "#1",
            "Specimen": "S1",
            "Failure mode": "in-plane shear",
            "Failure location": "within gauge length",
            "Notes": "",
        }
    ]
    assert invalid_rows[0]["Run #"] == "#2"
    assert "bending non-compliance" in invalid_rows[0]["Reason"]
    assert "operator marked invalid" in invalid_rows[0]["Reason"]
    assert "Bending classification" not in invalid_rows[0]
    assert "Bending evidence" in invalid_rows[0]
    assert "operator validity/failure observation" not in provided[1]["Value"]
