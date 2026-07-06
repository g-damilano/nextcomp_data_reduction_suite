from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.iso14126.report_compliance import build_iso14126_resolve_checks
from reporting.core.report_engine import _missing_report_fields_with_iso_run_gaps  # noqa: PLC2701


def test_accepted_final_runs_without_structured_failure_mode_are_incomplete() -> None:
    result = _result(
        [
            {"run_id": "run_001", "failure_mode": "Valid", "primary_failure_mode": "", "failure_location": ""},
            {"run_id": "run_002", "failure_mode": "", "primary_failure_mode": "", "failure_location": ""},
        ]
    )

    missing = _missing_report_fields_with_iso_run_gaps(result, [], {"run_001"})

    assert {row["field"] for row in missing} == {"primary_failure_mode", "failure_location"}
    assert next(row for row in missing if row["field"] == "primary_failure_mode")["affected_run_ids"] == ["run_001"]
    assert next(row for row in missing if row["field"] == "failure_location")["affected_run_ids"] == ["run_001"]


def test_excluded_runs_do_not_block_failure_mode_completion_policy() -> None:
    result = _result(
        [
            {
                "run_id": "run_001",
                "primary_failure_mode": "splitting",
                "failure_location": "within_gauge_length",
            },
            {"run_id": "run_002", "primary_failure_mode": "", "failure_location": ""},
        ]
    )

    missing = _missing_report_fields_with_iso_run_gaps(result, [], {"run_001"})
    checks = build_iso14126_resolve_checks(
        result=result,
        missing_report_fields=missing,
        report_values_used=[],
        selection_run_ids={"run_001"},
    )

    assert missing == []
    assert all(
        not str(check["requirement_id"]).startswith("iso14126.clause_9_9_failure_mode:run_002")
        for check in checks
    )


def test_legacy_failure_mode_maps_when_it_is_clean_iso_vocabulary() -> None:
    result = _result(
        [
            {"run_id": "run_001", "failure_mode": "through-thickness shear", "failure_location": "within_gauge_length"},
        ]
    )

    missing = _missing_report_fields_with_iso_run_gaps(result, [], {"run_001"})
    checks = build_iso14126_resolve_checks(
        result=result,
        missing_report_fields=missing,
        report_values_used=[],
        selection_run_ids={"run_001"},
    )

    assert missing == []
    failure_check = next(check for check in checks if str(check["requirement_id"]).startswith("iso14126.clause_9_9_failure_mode:"))
    assert failure_check["resolved_value"] == "through-thickness shear"
    assert failure_check["status"] == "pass"


def _result(specimen_results: list[dict[str, object]]) -> SimpleNamespace:
    return SimpleNamespace(
        method_package=SimpleNamespace(method_id="iso14126", manifest={"standard_reference": "ISO 14126"}),
        specimen_results=specimen_results,
        acceptance_report={"run_states": {str(row["run_id"]): "accepted" for row in specimen_results}},
        bounded_curve_family=[],
        curve_family=[],
        validation_deviations=[],
        experiment_boundaries=[],
    )
