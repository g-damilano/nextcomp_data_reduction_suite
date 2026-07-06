from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acceptance.acceptance_flag import AcceptanceFlag, strongest_flag
from acceptance.selection_set import SelectionSet


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    method_id: str
    recipe_id: str
    default_selection_set: str
    run_states: dict[str, str]
    flags: tuple[AcceptanceFlag, ...]
    selection_sets: tuple[SelectionSet, ...]
    selection_membership: tuple[dict[str, Any], ...]
    discharge_report: dict[str, Any]
    dataset_summary_by_selection: tuple[dict[str, Any], ...]
    curve_family_assessment: dict[str, Any]
    curve_family_scores: tuple[dict[str, Any], ...]
    curve_family_flags: tuple[dict[str, Any], ...]
    curve_family_reference_rows: tuple[dict[str, Any], ...]
    curve_family_aligned_rows: tuple[dict[str, Any], ...]
    curve_family_residual_rows: tuple[dict[str, Any], ...]
    curve_family_policy_resolved: dict[str, Any]
    curve_shape_diagnostic_report: dict[str, Any]
    curve_shape_diagnostic_scores: tuple[dict[str, Any], ...]
    curve_shape_diagnostic_reference_rows: tuple[dict[str, Any], ...]
    curve_shape_diagnostic_residual_rows: tuple[dict[str, Any], ...]
    curve_shape_diagnostic_policy_resolved: dict[str, Any]
    curve_shape_diagnostic_flags: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.acceptance_report.v0_1",
            "method_id": self.method_id,
            "recipe_id": self.recipe_id,
            "default_selection_set": self.default_selection_set,
            "summary": self.summary,
            "run_states": self.run_states,
            "flags": [flag.to_dict() for flag in self.flags],
            "selection_sets": self.selection_sets_payload(),
            "discharge_report": self.discharge_report,
            "curve_family_assessment": self.curve_family_assessment,
            "curve_shape_diagnostic": self.curve_shape_diagnostic_report,
        }

    @property
    def summary(self) -> dict[str, Any]:
        counts = {
            "total_runs": len(self.run_states),
            "accepted": 0,
            "accepted_with_warning": 0,
            "review_required": 0,
            "excluded": 0,
            "total_flags": len(self.flags),
        }
        for state in self.run_states.values():
            if state in counts:
                counts[state] += 1
        counts["default_selection_set"] = self.default_selection_set
        counts["default_selected_runs"] = len(_selection_run_ids(self.selection_sets, self.default_selection_set))
        curve_summary = self.curve_family_assessment.get("summary", {}) if isinstance(self.curve_family_assessment, dict) else {}
        if isinstance(curve_summary, dict):
            counts["curve_family_assessed_runs"] = curve_summary.get("assessed_runs", 0)
            counts["curve_family_review"] = curve_summary.get("review", 0)
            counts["curve_family_propose_remove"] = curve_summary.get("propose_remove", 0)
        diagnostic_summary = (
            self.curve_shape_diagnostic_report.get("summary", {})
            if isinstance(self.curve_shape_diagnostic_report, dict)
            else {}
        )
        if isinstance(diagnostic_summary, dict):
            counts["curve_shape_evaluable_runs"] = diagnostic_summary.get("evaluable_runs", 0)
            counts["curve_shape_outliers"] = diagnostic_summary.get("curve_shape_outliers", 0)
            counts["curve_shape_insufficient_data"] = diagnostic_summary.get("insufficient_curve_data", 0)
        return counts

    def summary_rows(self) -> list[dict[str, Any]]:
        row = {
            "method_id": self.method_id,
            "recipe_id": self.recipe_id,
        }
        row.update(self.summary)
        return [row]

    def run_flag_rows(self) -> list[dict[str, Any]]:
        return [flag.to_dict() for flag in self.flags]

    def selection_sets_payload(self) -> dict[str, Any]:
        return {
            "schema_id": "method.selection_sets.v0_1",
            "default_selection_set": self.default_selection_set,
            "selection_sets": [selection.to_dict() for selection in self.selection_sets],
        }

    def selection_membership_rows(self) -> list[dict[str, Any]]:
        return list(self.selection_membership)

    def discharged_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self.discharge_report.get("records", []):
            if not isinstance(record, dict):
                continue
            flags = record.get("flags", [])
            flag_ids = [str(flag.get("flag_id")) for flag in flags if isinstance(flag, dict)]
            rows.append(
                {
                    "run_id": record.get("run_id"),
                    "specimen_name": record.get("specimen_name"),
                    "state": record.get("state"),
                    "included_in_default": record.get("included_in_default"),
                    "primary_reason": record.get("primary_reason"),
                    "flags": "; ".join(flag_ids),
                    "operation_refs": "; ".join(record.get("operation_refs", [])),
                    "validation_refs": "; ".join(record.get("validation_refs", [])),
                    "inspection_refs": "; ".join(record.get("inspection_refs", [])),
                }
            )
        return rows


def membership_rows(
    *,
    run_ids: list[str],
    run_states: dict[str, str],
    flags_by_run: dict[str, list[AcceptanceFlag]],
    selection_sets: list[SelectionSet],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selection in selection_sets:
        selected = set(selection.run_ids)
        for run_id in run_ids:
            primary = strongest_flag(flags_by_run.get(run_id, []))
            rows.append(
                {
                    "run_id": run_id,
                    "selection_set": selection.selection_id,
                    "included": run_id in selected,
                    "state": run_states.get(run_id),
                    "primary_reason": primary.message if primary else "",
                    "flags": "; ".join(flag.flag_id for flag in flags_by_run.get(run_id, [])),
                }
            )
    return rows


def _selection_run_ids(selection_sets: tuple[SelectionSet, ...], selection_id: str) -> tuple[str, ...]:
    for selection in selection_sets:
        if selection.selection_id == selection_id:
            return selection.run_ids
    return ()
