from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acceptance.human_decision import HumanAcceptanceDecision


FINAL_SELECTION_ID = "final_report_runs"


@dataclass(frozen=True, slots=True)
class FinalSelectionResult:
    human_decisions: dict[str, Any]
    human_decision_rows: list[dict[str, Any]]
    override_ledger: dict[str, Any]
    override_ledger_rows: list[dict[str, Any]]
    selection_sets_final: dict[str, Any]
    selection_membership_final: list[dict[str, Any]]
    final_report_runs: list[dict[str, Any]]
    final_run_ids: tuple[str, ...]
    selection_source: str


class SelectionEditor:
    """Combines machine acceptance with auditable human decisions."""

    def apply(
        self,
        *,
        specimen_results: list[dict[str, Any]],
        acceptance_report: dict[str, Any],
        machine_selection_sets: dict[str, Any],
        machine_selection_membership: list[dict[str, Any]],
        decisions: tuple[HumanAcceptanceDecision, ...] = (),
    ) -> FinalSelectionResult:
        run_ids = [str(row.get("run_id")) for row in specimen_results if row.get("run_id")]
        machine_states = {
            run_id: str(state)
            for run_id, state in (acceptance_report.get("run_states", {}) if isinstance(acceptance_report, dict) else {}).items()
        }
        default_selection = _default_selection_id(acceptance_report, machine_selection_sets)
        machine_selected = _selected_run_ids(machine_selection_sets, machine_selection_membership, default_selection, run_ids)
        if not machine_selected:
            fallback_selection = _first_nonempty_selection(
                machine_selection_sets,
                machine_selection_membership,
                run_ids,
                ("user_valid_runs", "all_runs"),
            )
            if fallback_selection:
                machine_selected = _selected_run_ids(
                    machine_selection_sets,
                    machine_selection_membership,
                    fallback_selection,
                    run_ids,
                )
        final_selected = set(machine_selected)
        final_statuses = {
            run_id: ("included" if run_id in final_selected else "excluded")
            for run_id in run_ids
        }
        previous_statuses = dict(final_statuses)
        decisions_by_run: dict[str, HumanAcceptanceDecision] = {}
        ledger_rows: list[dict[str, Any]] = []
        for decision in decisions:
            if decision.run_id not in run_ids:
                continue
            if decision.decision_type == "clear_override":
                decisions_by_run.pop(decision.run_id, None)
                new_status = "included" if decision.run_id in machine_selected else "excluded"
                if decision.run_id in machine_selected:
                    final_selected.add(decision.run_id)
                else:
                    final_selected.discard(decision.run_id)
            else:
                decisions_by_run[decision.run_id] = decision
                if decision.decision_type in {"keep", "restore", "confirm"}:
                    final_selected.add(decision.run_id)
                    new_status = "included"
                elif decision.decision_type == "remove":
                    final_selected.discard(decision.run_id)
                    new_status = "excluded"
                else:
                    new_status = previous_statuses.get(decision.run_id, "")
            row = {
                "decision_id": decision.decision_id,
                "run_id": decision.run_id,
                "original_machine_status": machine_states.get(decision.run_id, ""),
                "previous_final_status": previous_statuses.get(decision.run_id, ""),
                "new_final_status": new_status,
                "decision_type": decision.decision_type,
                "reason": decision.reason,
                "reviewer": decision.reviewer,
                "timestamp": decision.timestamp,
                "source_surface": decision.source_surface,
                "ui_context": decision.ui_context,
            }
            ledger_rows.append(row)
            previous_statuses[decision.run_id] = new_status
            final_statuses[decision.run_id] = new_status
        final_run_ids = tuple(run_id for run_id in run_ids if run_id in final_selected)
        selection_source = "human_final" if decisions else "machine_default_confirmed"
        selection_sets_final = _final_selection_sets(
            machine_selection_sets=machine_selection_sets,
            run_ids=run_ids,
            final_run_ids=final_run_ids,
            default_selection=FINAL_SELECTION_ID,
            selection_source=selection_source,
        )
        membership = _final_membership_rows(
            run_ids=run_ids,
            final_run_ids=set(final_run_ids),
            machine_selected=machine_selected,
            machine_states=machine_states,
            decisions_by_run=decisions_by_run,
        )
        final_rows = _final_report_run_rows(
            specimen_results=specimen_results,
            final_run_ids=set(final_run_ids),
            machine_selected=machine_selected,
            machine_states=machine_states,
            decisions_by_run=decisions_by_run,
        )
        decision_rows = [decision.to_dict() for decision in decisions]
        return FinalSelectionResult(
            human_decisions={
                "schema_id": "method.human_acceptance_decisions.v0_1",
                "selection_source": selection_source,
                "decisions": decision_rows,
            },
            human_decision_rows=decision_rows,
            override_ledger={
                "schema_id": "method.acceptance_override_ledger.v0_1",
                "selection_source": selection_source,
                "records": ledger_rows,
            },
            override_ledger_rows=ledger_rows,
            selection_sets_final=selection_sets_final,
            selection_membership_final=membership,
            final_report_runs=final_rows,
            final_run_ids=final_run_ids,
            selection_source=selection_source,
        )


def _default_selection_id(acceptance_report: dict[str, Any], machine_selection_sets: dict[str, Any]) -> str:
    return str(
        acceptance_report.get("default_selection_set")
        or machine_selection_sets.get("default_selection_set")
        or "auto_recommended_runs"
    )


def _selected_run_ids(
    selection_sets: dict[str, Any],
    membership_rows: list[dict[str, Any]],
    selection_id: str,
    fallback_run_ids: list[str],
) -> set[str]:
    selected = {
        str(row.get("run_id"))
        for row in membership_rows
        if str(row.get("selection_set")) == selection_id and _truthy(row.get("included"))
    }
    if selected:
        return selected
    for selection in selection_sets.get("selection_sets", []) if isinstance(selection_sets, dict) else []:
        if isinstance(selection, dict) and selection.get("selection_id") == selection_id:
            return {str(run_id) for run_id in selection.get("run_ids", [])}
    return set(fallback_run_ids)


def _first_nonempty_selection(
    selection_sets: dict[str, Any],
    membership_rows: list[dict[str, Any]],
    fallback_run_ids: list[str],
    candidates: tuple[str, ...],
) -> str:
    for candidate in candidates:
        if _selected_run_ids(selection_sets, membership_rows, candidate, []) or (
            candidate == "all_runs" and fallback_run_ids
        ):
            return candidate
    return ""


def _final_selection_sets(
    *,
    machine_selection_sets: dict[str, Any],
    run_ids: list[str],
    final_run_ids: tuple[str, ...],
    default_selection: str,
    selection_source: str,
) -> dict[str, Any]:
    machine_sets = [
        dict(selection, source="machine")
        for selection in machine_selection_sets.get("selection_sets", [])
        if isinstance(selection, dict)
    ]
    final_set = {
        "selection_id": FINAL_SELECTION_ID,
        "label": "Final Report Runs",
        "description": "Human-confirmed selected run set used for report aggregation.",
        "run_ids": list(final_run_ids),
        "excluded_run_ids": [run_id for run_id in run_ids if run_id not in set(final_run_ids)],
        "policy_id": "machine_selection_plus_human_overrides",
        "created_by": "selection_editor",
        "source": selection_source,
    }
    return {
        "schema_id": "method.selection_sets_final.v0_1",
        "default_selection_set": default_selection,
        "machine_default_selection_set": machine_selection_sets.get("default_selection_set"),
        "selection_source": selection_source,
        "selection_sets": [*machine_sets, final_set],
    }


def _final_membership_rows(
    *,
    run_ids: list[str],
    final_run_ids: set[str],
    machine_selected: set[str],
    machine_states: dict[str, str],
    decisions_by_run: dict[str, HumanAcceptanceDecision],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id in run_ids:
        decision = decisions_by_run.get(run_id)
        rows.append(
            {
                "run_id": run_id,
                "selection_set": FINAL_SELECTION_ID,
                "machine_included": run_id in machine_selected,
                "included": run_id in final_run_ids,
                "machine_state": machine_states.get(run_id, ""),
                "human_decision": decision.decision_type if decision else "",
                "human_decision_type": decision.decision_type if decision else "",
                "reason": decision.reason if decision else "",
                "human_decision_reason": decision.reason if decision else "",
                "selection_source": "human_override" if decision else "machine_default",
            }
        )
    return rows


def _final_report_run_rows(
    *,
    specimen_results: list[dict[str, Any]],
    final_run_ids: set[str],
    machine_selected: set[str],
    machine_states: dict[str, str],
    decisions_by_run: dict[str, HumanAcceptanceDecision],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for specimen in specimen_results:
        run_id = str(specimen.get("run_id") or "")
        decision = decisions_by_run.get(run_id)
        rows.append(
            {
                "run_id": run_id,
                "specimen_name": specimen.get("specimen_name", ""),
                "machine_state": machine_states.get(run_id, ""),
                "machine_included": run_id in machine_selected,
                "human_decision": decision.decision_type if decision else "",
                "human_decision_type": decision.decision_type if decision else "",
                "override_reason": decision.reason if decision else "",
                "human_decision_reason": decision.reason if decision else "",
                "final_included": run_id in final_run_ids,
                "included": run_id in final_run_ids,
                "final_selection_set": FINAL_SELECTION_ID,
            }
        )
    return rows


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
