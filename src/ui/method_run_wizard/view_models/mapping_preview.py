from __future__ import annotations

from typing import Any

from methods.core.method_run_service import MappingLoadResult
from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contract


def mapping_preview_view_model(result: MappingLoadResult) -> dict[str, Any]:
    rows = [_operator_row(row) for row in result.mapped_fields]
    candidate_rows = _candidate_rows(result.candidate_report)
    resolution_rows = _resolution_rows(result.resolution_report)
    summary = dict(result.summary)
    compatibility_summary = _nested_dict(result.compatibility_report, "summary")
    missing_rows = [row for row in rows if row.get("status") in {"fail", "missing"}]
    attention_rows = [
        row
        for row in rows
        if row.get("status") in {"fail", "missing", "warn", "warning", "ambiguous"}
    ]
    blocking_rows = [
        row
        for row in rows
        if row.get("severity") == "execution_critical"
        and row.get("status") in {"fail", "missing", "ambiguous"}
    ]
    return {
        "schema_name": "mapping_preview_view_model",
        "version": "0.1.0",
        "page_action_contract": wizard_page_action_contract("mapping"),
        "mapping_path": str(result.path),
        "mapping_id": result.mapping_id or "",
        "method_id": result.method_id or "",
        "status": result.status,
        "summary": summary,
        "compatibility_status": _nested(result.compatibility_report, "summary", "status"),
        "compatibility_summary": compatibility_summary,
        "candidate_summary": _nested_dict(result.candidate_report, "summary"),
        "resolution_summary": _nested_dict(result.resolution_report, "summary"),
        "why_required": (
            "Mapping tells the method which MTDP tokens and channels satisfy each declared method input. "
            "Readiness can only decide if this concrete package is runnable after these bindings are resolved."
        ),
        "rows": rows,
        "missing_rows": missing_rows,
        "attention_rows": attention_rows,
        "blocking_rows": blocking_rows,
        "mapped_rows": [row for row in rows if row.get("status") == "pass"],
        "candidate_rows": candidate_rows,
        "disambiguation_rows": resolution_rows,
        "ambiguous_rows": [row for row in resolution_rows if row.get("status") == "ambiguous"],
        "action_guidance": _action_guidance(rows, summary, compatibility_summary),
    }


def _operator_row(row: dict[str, Any]) -> dict[str, Any]:
    required_for = row.get("required_for", [])
    if isinstance(required_for, list):
        required_for_text = ", ".join(str(item) for item in required_for)
    else:
        required_for_text = str(required_for or "")
    severity = str(row.get("severity") or "")
    raw_status = str(row.get("status") or "")
    mapped_source = row.get("mapped_source", "")
    source_kind = str(row.get("source_kind") or "")
    source_location = _source_location(source_kind, str(mapped_source or ""))
    return {
        "method_field": row.get("method_field", ""),
        "description": row.get("description") or row.get("requirement_id") or row.get("method_field", ""),
        "required_for": required_for_text,
        "required_or_recommended": "required" if severity == "execution_critical" else "recommended",
        "severity": severity,
        "scope": row.get("scope", ""),
        "mapped_source": mapped_source,
        "source": mapped_source,
        "source_kind": source_kind,
        "source_location": source_location,
        "source_path": source_location,
        "source_role": row.get("source_role", ""),
        "unit": row.get("expected_unit") or row.get("source_unit") or "",
        "expected_unit": row.get("expected_unit", ""),
        "source_unit": row.get("source_unit", ""),
        "coverage": row.get("coverage", ""),
        "example_value": row.get("example_value", ""),
        "candidate_count": row.get("candidate_count", ""),
        "confidence": row.get("confidence", ""),
        "resolution_status": row.get("resolution_status", ""),
        "status": raw_status,
        "operator_status": _operator_status(raw_status),
    }


def _candidate_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for requirement in report.get("requirements", []) if isinstance(report, dict) else []:
        if not isinstance(requirement, dict):
            continue
        method_field = requirement.get("method_field", "")
        source_role = requirement.get("source_role", "")
        severity = requirement.get("severity", "")
        for candidate in requirement.get("candidates", []) or []:
            if not isinstance(candidate, dict):
                continue
            rows.append(
                {
                    "method_field": method_field,
                    "source_role": source_role,
                    "severity": severity,
                    "source_name": candidate.get("source_name", ""),
                    "candidate_source": candidate.get("source_path") or candidate.get("field_key") or "",
                    "source_kind": candidate.get("source_kind", ""),
                    "scope": candidate.get("scope", ""),
                    "confidence": candidate.get("confidence", ""),
                    "coverage": candidate.get("coverage", ""),
                    "example_value": candidate.get("example_value", ""),
                    "reason": candidate.get("reason", ""),
                    "status": requirement.get("status", ""),
                }
            )
    return rows


def _resolution_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "method_field": row.get("method_field", ""),
            "source_role": row.get("source_role", ""),
            "severity": row.get("severity", ""),
            "mapped_source": row.get("mapped_source", ""),
            "candidate_count": row.get("candidate_count", ""),
            "confidence": row.get("confidence", ""),
            "status": row.get("status", ""),
            "message": row.get("message", ""),
        }
        for row in report.get("resolutions", []) if isinstance(row, dict)
    ] if isinstance(report, dict) else []


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current if current is not None else ""


def _nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    value = _nested(payload, *keys)
    return dict(value) if isinstance(value, dict) else {}


def _source_location(source_kind: str, mapped_source: str) -> str:
    if not mapped_source:
        return ""
    kind = source_kind or "field"
    return f"{kind}:{mapped_source}"


def _operator_status(status: str) -> str:
    return {
        "pass": "found",
        "warn": "warning",
        "fail": "missing",
        "missing": "unmapped",
        "ambiguous": "warning",
    }.get(status, status or "unmapped")


def _action_guidance(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    compatibility_summary: dict[str, Any],
) -> dict[str, Any]:
    critical_total = int(summary.get("execution_critical_total") or 0)
    critical_mapped = int(summary.get("execution_critical_mapped") or 0)
    critical_ambiguous = int(summary.get("execution_critical_ambiguous") or 0)
    if not critical_ambiguous:
        critical_ambiguous = sum(
            1
            for row in rows
            if row.get("severity") == "execution_critical"
            and row.get("status") == "ambiguous"
        )
    report_total = int(summary.get("report_fields_total") or 0)
    report_mapped = int(summary.get("report_fields_mapped") or 0)
    critical_missing = max(0, critical_total - critical_mapped)
    report_missing = max(0, report_total - report_mapped)
    compatibility_status = str(compatibility_summary.get("status") or "").upper()
    compatibility_blocks = bool(compatibility_summary.get("blocks_mapping")) or "INCOMPATIBLE" in compatibility_status
    blocking_fields = [
        str(row.get("method_field") or "")
        for row in rows
        if row.get("severity") == "execution_critical"
        and row.get("status") in {"fail", "missing", "ambiguous"}
    ]
    report_warning_fields = [
        str(row.get("method_field") or "")
        for row in rows
        if row.get("severity") != "execution_critical"
        and row.get("status") in {"fail", "missing", "warn", "warning", "ambiguous"}
    ]

    if compatibility_blocks:
        return {
            "severity": "block",
            "can_confirm": False,
            "headline": "This mapping is not compatible with the selected method/package.",
            "safe_next_step": "choose a compatible mapping profile or method/package pair",
            "primary_actions": [
                "Use Browse to choose a mapping profile made for this method and package schema.",
                "Review candidate evidence to see which required method inputs have no usable source.",
            ],
            "red_light_help": "A red mapping state means readiness should not run yet; change the profile or selected inputs first.",
            "blocking_fields": blocking_fields,
            "warning_fields": report_warning_fields,
            "confirm_tooltip": "Mapping cannot be confirmed while compatibility blocks the selected method/package.",
        }
    if critical_missing or blocking_fields:
        fields = ", ".join(blocking_fields[:4]) or "execution-critical inputs"
        return {
            "severity": "block",
            "can_confirm": False,
            "headline": f"Missing execution-critical mapping: {fields}.",
            "safe_next_step": "map the missing critical inputs, then reload or choose the corrected profile",
            "primary_actions": [
                "Open candidate evidence and identify a source field or channel for each missing method input.",
                "Edit or choose the mapping profile, then reload this page and confirm again.",
            ],
            "red_light_help": "Red rows are run blockers. Fix those before readiness; report-only warnings can wait.",
            "blocking_fields": blocking_fields,
            "warning_fields": report_warning_fields,
            "confirm_tooltip": "Confirm is disabled until all execution-critical inputs are mapped.",
        }
    if critical_ambiguous:
        return {
            "severity": "block",
            "can_confirm": False,
            "headline": "Ambiguous execution-critical mappings need operator resolution before readiness.",
            "safe_next_step": "review candidate evidence and choose the intended source for each ambiguous input",
            "primary_actions": [
                "Expand candidate/disambiguation evidence.",
                "Resolve ambiguous source choices in the mapping profile, then reload this page.",
            ],
            "red_light_help": "Ambiguity is treated like a red light because the method could read the wrong channel.",
            "blocking_fields": blocking_fields,
            "warning_fields": report_warning_fields,
            "confirm_tooltip": "Confirm is disabled until ambiguous mappings are resolved.",
        }
    if report_missing or report_warning_fields or "WARNING" in compatibility_status:
        return {
            "severity": "warn",
            "can_confirm": True,
            "headline": "Execution-critical mapping is usable; report fields still need attention.",
            "safe_next_step": "continue to readiness, or complete report metadata first if the final report needs it",
            "primary_actions": [
                "Use report warnings to decide whether operator/report metadata should be added before finalization.",
                "If a red critical row appears later, map that method input before readiness.",
            ],
            "red_light_help": "Green means the method can find required inputs. Yellow report fields affect report completeness, not calculation safety.",
            "blocking_fields": [],
            "warning_fields": report_warning_fields,
            "confirm_tooltip": "Execution-critical inputs are mapped. Report-completeness warnings can be handled later.",
        }
    return {
        "severity": "pass",
        "can_confirm": True,
        "headline": "Mapping is ready for readiness.",
        "safe_next_step": "confirm mapping and continue to readiness",
        "primary_actions": [
            "Continue to readiness.",
            "If a future mapping shows red rows, fix missing critical inputs before running.",
        ],
        "red_light_help": "Red rows mean a method input is missing or ambiguous; choose a profile or source binding before readiness.",
        "blocking_fields": [],
        "warning_fields": [],
        "confirm_tooltip": "Confirm this mapping and continue to readiness.",
    }
