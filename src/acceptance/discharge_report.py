from __future__ import annotations

from acceptance.acceptance_flag import AcceptanceFlag, strongest_flag


def build_discharge_report(
    *,
    method_id: str,
    default_selection_set: str,
    run_states: dict[str, str],
    flags_by_run: dict[str, list[AcceptanceFlag]],
    default_run_ids: set[str],
    specimen_by_run: dict[str, dict[str, object]],
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for run_id, state in run_states.items():
        if run_id in default_run_ids:
            continue
        flags = flags_by_run.get(run_id, [])
        primary = strongest_flag(flags)
        operation_refs = sorted({item for flag in flags for item in flag.operation_ids})
        validation_refs = sorted({item for flag in flags for item in flag.validation_check_ids})
        inspection_refs = sorted({item for flag in flags for item in flag.inspection_ids})
        records.append(
            {
                "run_id": run_id,
                "specimen_name": specimen_by_run.get(run_id, {}).get("specimen_name"),
                "state": state,
                "included_in_default": False,
                "primary_reason": primary.message if primary else "Not included in default selection set.",
                "flags": [flag.to_dict() for flag in flags],
                "operation_refs": operation_refs,
                "validation_refs": validation_refs,
                "inspection_refs": inspection_refs,
                "human_decision": None,
                "human_decision_reason": None,
                "human_decision_timestamp": None,
                "human_decision_author": None,
            }
        )
    return {
        "schema_id": "method.discharge_report.v0_1",
        "method_id": method_id,
        "default_selection_set": default_selection_set,
        "records": records,
    }
