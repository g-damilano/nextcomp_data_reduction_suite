from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contract


RUN_ENABLED = {"READY", "READY_WITH_WARNINGS"}


def readiness_gate_view_model(report: Mapping[str, Any] | None) -> dict[str, Any]:
    report = report or {}
    status = str(report.get("status") or "not_checked")
    requirements = report.get("requirements") if isinstance(report.get("requirements"), list) else []
    critical = [row for row in requirements if isinstance(row, dict) and row.get("severity") == "execution_critical"]
    report_warnings = [
        row for row in requirements
        if isinstance(row, dict) and row.get("severity") != "execution_critical" and row.get("status") != "pass"
    ]
    per_run_warnings = [
        row for row in requirements
        if isinstance(row, dict) and row.get("scope") == "per_run" and row.get("status") != "pass"
    ]
    critical_fail = [row for row in critical if row.get("status") != "pass"]
    return {
        "schema_name": "wizard_gate_view_model",
        "version": "0.1.0",
        "gate_id": "readiness",
        "page_action_contract": wizard_page_action_contract("readiness"),
        "status": _gate_status(status),
        "summary_cards": [
            _card("Status", status, "pass" if status == "READY" else "warn" if status == "READY_WITH_WARNINGS" else "fail"),
            _card("Execution Critical", f"{len(critical) - len(critical_fail)}/{len(critical)}", "pass" if not critical_fail else "fail"),
            _card("Report Warnings", str(len(report_warnings)), "pass" if not report_warnings else "warn"),
        ],
        "primary_messages": list(report.get("warnings", [])) if isinstance(report.get("warnings"), list) else [],
        "groups": [
            {"group_id": "execution_critical", "label": "Execution-critical inputs", "status": "pass" if not critical_fail else "fail", "rows": critical},
            {"group_id": "report_completeness", "label": "Report-completeness warnings", "status": "pass" if not report_warnings else "warn", "rows": report_warnings},
            {"group_id": "per_run_warnings", "label": "Per-run warnings", "status": "pass" if not per_run_warnings else "warn", "rows": per_run_warnings},
        ],
        "raw_artifact_refs": ["readiness/readiness_report.json", "readiness/missing_inputs.csv"],
        "workbench_links": [],
        "next_enabled": status in RUN_ENABLED,
        "recommended_action": "Continue to execution." if status in RUN_ENABLED else "Resolve missing execution-critical inputs before running.",
    }


def validation_gate_view_model(report: Mapping[str, Any] | None) -> dict[str, Any]:
    report = report or {}
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    failed = [row for row in checks if isinstance(row, dict) and row.get("status") == "fail"]
    warned = [row for row in checks if isinstance(row, dict) and row.get("status") == "warn"]
    by_run = _group_rows(checks, "run_id")
    by_check_type = _group_rows(checks, "field")
    status = str(summary.get("status") or ("fail" if failed else "pass" if checks else "not_checked"))
    return {
        "schema_name": "wizard_gate_view_model",
        "version": "0.1.0",
        "gate_id": "validation",
        "page_action_contract": wizard_page_action_contract("validation"),
        "status": "fail" if failed else "warn" if warned else status,
        "summary_cards": [
            _card("Status", status, "pass" if not failed else "fail"),
            _card("Passed", str(summary.get("passed", 0)), "pass"),
            _card("Warned", str(summary.get("warned", 0)), "warn" if warned else "pass"),
            _card("Failed", str(summary.get("failed", 0)), "fail" if failed else "pass"),
        ],
        "primary_messages": [str(row.get("message")) for row in failed[:5] if isinstance(row, dict)],
        "groups": [
            {"group_id": "failed_checks", "label": "Failed checks", "status": "fail" if failed else "pass", "rows": failed},
            {"group_id": "warned_checks", "label": "Warned checks", "status": "warn" if warned else "pass", "rows": warned},
            {"group_id": "checks_by_run", "label": "Checks by run", "status": "neutral", "rows": by_run},
            {"group_id": "checks_by_type", "label": "Checks by type", "status": "neutral", "rows": by_check_type},
        ],
        "raw_artifact_refs": ["validation/validation_report.json", "validation/deviations.csv"],
        "workbench_links": _operation_links(checks),
        "next_enabled": not failed,
        "recommended_action": "Review failed validation checks before accepting outputs." if failed else "Continue to acceptance review.",
    }


def acceptance_gate_view_model(
    report: Mapping[str, Any] | None,
    *,
    final_selection_sets: Mapping[str, Any] | None = None,
    final_membership: list[Mapping[str, Any]] | None = None,
    final_report_runs: list[Mapping[str, Any]] | None = None,
    human_decisions: Mapping[str, Any] | None = None,
    override_ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = report or {}
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    flags = report.get("flags") if isinstance(report.get("flags"), list) else []
    selection_sets = report.get("selection_sets")
    if isinstance(selection_sets, Mapping):
        selection_rows = selection_sets.get("selection_sets") if isinstance(selection_sets.get("selection_sets"), list) else []
    else:
        selection_rows = []
    exclude_flags = [row for row in flags if isinstance(row, dict) and row.get("severity") == "exclude"]
    review_flags = [row for row in flags if isinstance(row, dict) and row.get("severity") == "review"]
    bending_flags = [
        row for row in flags
        if isinstance(row, dict) and (
            "bending" in str(row.get("category", "")).casefold()
            or "bending" in str(row.get("flag_id", "")).casefold()
            or "bending" in str(row.get("message", "")).casefold()
        )
    ]
    curve_family_flags = [
        row for row in flags
        if isinstance(row, dict) and (
            str(row.get("source", "")).casefold() == "curve_family_assessment"
            or "curve_family" in str(row.get("category", "")).casefold()
            or "curve_family" in str(row.get("flag_id", "")).casefold()
        )
    ]
    curve_family = report.get("curve_family_assessment") if isinstance(report.get("curve_family_assessment"), Mapping) else {}
    curve_summary = curve_family.get("summary") if isinstance(curve_family, Mapping) and isinstance(curve_family.get("summary"), Mapping) else {}
    final_selection_sets = final_selection_sets or {}
    final_report_runs = final_report_runs or []
    final_membership = final_membership or []
    human_decision_rows = human_decisions.get("decisions", []) if isinstance(human_decisions, Mapping) else []
    ledger_rows = override_ledger.get("records", []) if isinstance(override_ledger, Mapping) else []
    final_included = [
        row for row in final_report_runs
        if isinstance(row, Mapping) and _truthy(row.get("final_included", row.get("included", True)))
    ]
    final_selection_id = str(final_selection_sets.get("default_selection_set") or "final_report_runs")
    selection_source = str(final_selection_sets.get("selection_source") or "machine_acceptance")
    return {
        "schema_name": "wizard_gate_view_model",
        "version": "0.1.0",
        "gate_id": "acceptance",
        "page_action_contract": wizard_page_action_contract("acceptance"),
        "status": "warn" if review_flags or exclude_flags else "pass",
        "summary_cards": [
            _card("Default Selection", str(summary.get("default_selection_set", "")), "neutral"),
            _card("Selected Runs", str(summary.get("default_selected_runs", "")), "pass"),
            _card("Final Report Runs", str(len(final_included)), "pass"),
            _card("Human Decisions", str(len(human_decision_rows)), "warn" if human_decision_rows else "pass"),
            _card("Excluded", str(summary.get("excluded", 0)), "warn" if exclude_flags else "pass"),
            _card("Review Required", str(summary.get("review_required", 0)), "warn" if review_flags else "pass"),
            _card("Curve-Family Review", str(curve_summary.get("review", 0)), "warn" if curve_family_flags else "pass"),
            _card("Curve-Family Proposed Remove", str(curve_summary.get("propose_remove", 0)), "warn" if curve_family_flags else "pass"),
        ],
        "final_selection": {
            "selection_set": final_selection_id,
            "selection_source": selection_source,
            "included_count": len(final_included),
            "human_decision_count": len(human_decision_rows),
        },
        "run_rows": [
            {
                "run_id": str(row.get("run_id") or ""),
                "machine_state": str(row.get("machine_state") or ""),
                "machine_included": _truthy(row.get("machine_included")),
                "human_decision": str(row.get("human_decision") or row.get("human_decision_type") or ""),
                "human_decision_reason": str(row.get("human_decision_reason") or row.get("override_reason") or ""),
                "final_included": _truthy(row.get("final_included", row.get("included"))),
            }
            for row in final_report_runs
            if isinstance(row, Mapping)
        ],
        "override_controls": {
            "available_decisions": ["keep", "remove", "restore", "confirm", "clear_override"],
            "reason_required_for": ["keep", "remove", "restore"],
        },
        "selection_cards": [
            _card(
                str(row.get("label") or row.get("selection_id") or "Selection"),
                f"{len(row.get('run_ids', [])) if isinstance(row.get('run_ids'), list) else 0} included",
                "neutral",
            )
            for row in selection_rows
            if isinstance(row, dict)
        ],
        "primary_messages": [str(row.get("message")) for row in (exclude_flags + review_flags)[:5] if isinstance(row, dict)],
        "groups": [
            {"group_id": "excluded_flags", "label": "Exclude flags", "status": "warn" if exclude_flags else "pass", "rows": exclude_flags},
            {"group_id": "review_flags", "label": "Review flags", "status": "warn" if review_flags else "pass", "rows": review_flags},
            {"group_id": "selection_sets", "label": "Selection sets", "status": "neutral", "rows": selection_rows},
            {"group_id": "final_selection_membership", "label": "Final report selection", "status": "neutral", "rows": list(final_membership)},
            {"group_id": "human_decisions", "label": "Human decisions", "status": "warn" if human_decision_rows else "pass", "rows": list(human_decision_rows)},
            {"group_id": "override_ledger", "label": "Override ledger", "status": "warn" if ledger_rows else "pass", "rows": list(ledger_rows)},
            {"group_id": "bending_pattern_flags", "label": "Bending-pattern classifications", "status": "warn" if bending_flags else "pass", "rows": bending_flags},
            {"group_id": "curve_family_assessment", "label": "Curve-family assessment", "status": "warn" if curve_family_flags else "pass", "rows": curve_family_flags},
        ],
        "raw_artifact_refs": [
            "acceptance/acceptance_report.json",
            "acceptance/discharge_report.json",
            "acceptance/human_decisions.json",
            "acceptance/selection_sets_final.json",
            "acceptance/final_report_runs.csv",
            "acceptance/curve_family/curve_family_report.json",
            "acceptance/curve_family/curve_family_scores.csv",
        ],
        "workbench_links": _operation_links(flags),
        "next_enabled": True,
        "recommended_action": "Confirm the selected run set and open the discharge report for excluded/review runs.",
    }


def _gate_status(status: str) -> str:
    return {
        "READY": "ready",
        "READY_WITH_WARNINGS": "ready_with_warnings",
        "NOT_READY": "fail",
        "MAPPING_REQUIRED": "fail",
        "SCHEMA_EXTENSION_REQUIRED": "fail",
    }.get(status, status.casefold())


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _card(label: str, value: str, status: str) -> dict[str, str]:
    return {"label": label, "value": value, "status": status}


def _operation_links(rows: list[Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        operation_id = row.get("operation_id")
        operation_ids = row.get("operation_ids")
        if not operation_id and isinstance(operation_ids, list) and operation_ids:
            operation_id = operation_ids[0]
        elif not operation_id and isinstance(operation_ids, str):
            operation_id = operation_ids
        if operation_id:
            links.append(
                {
                    "run_id": str(row.get("run_id") or ""),
                    "operation_id": str(operation_id),
                    "label": str(row.get("field") or row.get("flag_id") or operation_id),
                }
            )
    return links


def _group_rows(rows: list[Any], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        group_id = str(row.get(key) or "dataset")
        status = str(row.get("status") or "unknown")
        bucket = grouped.setdefault(group_id, {"pass": 0, "warn": 0, "fail": 0, "unknown": 0})
        bucket[status if status in bucket else "unknown"] += 1
    return [
        {
            key: group_id,
            "passed": counts["pass"],
            "warned": counts["warn"],
            "failed": counts["fail"],
            "unknown": counts["unknown"],
            "total": sum(counts.values()),
        }
        for group_id, counts in sorted(grouped.items())
    ]
