from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contract


REPORT_AUTHORING_FILTERS = ("all", "missing", "required", "recommended", "overridden")


def report_authoring_view_model(
    *,
    catalog: Iterable[Mapping[str, Any]] = (),
    values_used: Iterable[Mapping[str, Any]] = (),
    missing_fields: Iterable[Mapping[str, Any]] = (),
    overrides: Iterable[Mapping[str, Any]] | Mapping[str, Any] = (),
) -> dict[str, Any]:
    """Build a plain-data model for report-only field authoring.

    The model deliberately consumes already-resolved report completion artifacts
    instead of repeating value resolution in the UI.
    """

    value_by_key = {_row_key(row): dict(row) for row in values_used if _row_key(row)}
    missing_by_key = {_row_key(row): dict(row) for row in missing_fields if _row_key(row)}
    override_rows = _override_rows(overrides)
    override_by_key = {_row_key(row): dict(row) for row in override_rows if _row_key(row)}

    fields: list[dict[str, Any]] = []
    section_order: list[str] = []
    section_titles: dict[str, str] = {}
    for entry in catalog:
        field_key = str(entry.get("field_key") or entry.get("field") or "").strip()
        if not field_key:
            continue
        value_row = value_by_key.get(field_key, {})
        missing_row = missing_by_key.get(field_key, {})
        override_row = override_by_key.get(field_key, {})
        section_id = str(
            entry.get("section_id")
            or value_row.get("section")
            or missing_row.get("section_id")
            or override_row.get("section")
            or "unsectioned"
        )
        section_title = str(
            entry.get("section_title")
            or missing_row.get("section_title")
            or section_id.replace("_", " ").title()
        )
        if section_id not in section_order:
            section_order.append(section_id)
            section_titles[section_id] = section_title
        current_value = value_row.get("value", "")
        report_importance = str(
            entry.get("report_importance")
            or missing_row.get("report_importance")
            or missing_row.get("requirement_level")
            or ""
        )
        overridden = bool(override_row)
        missing = bool(missing_row) and not overridden
        status = "overridden" if overridden else "missing" if missing else "present" if current_value not in (None, "") else "missing"
        missing_reason = _missing_reason(missing_row)
        fields.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "label": str(entry.get("label") or field_key),
                "field_key": field_key,
                "report_role": str(entry.get("report_role") or field_key),
                "report_importance": report_importance or "recommended",
                "required": bool(entry.get("required")) or report_importance == "required",
                "current_value": current_value,
                "source_type": "report_override" if overridden else value_row.get("source_type") or value_row.get("source") or ("missing" if missing else ""),
                "source_type_label": _source_type_label("report_override" if overridden else value_row.get("source_type") or value_row.get("source") or ("missing" if missing else "")),
                "source_path": f"report_overrides.{field_key}" if overridden else value_row.get("source_path", ""),
                "status": status,
                "status_label": _status_label(status),
                "report_importance_label": _importance_label(report_importance or "recommended"),
                "missing_reason": missing_reason,
                "guidance": _guidance(report_importance or "recommended", missing_reason),
                "override_value": override_row.get("value", ""),
                "override_reason": override_row.get("reason", ""),
                "override_reviewer": override_row.get("reviewer", ""),
                "overridden": overridden,
                "editable": _is_report_only(entry, value_row, missing_row),
            }
        )

    sections = []
    for section_id in section_order:
        section_fields = [field for field in fields if field["section_id"] == section_id]
        sections.append(
            {
                "section_id": section_id,
                "title": section_titles.get(section_id, section_id),
                "field_count": len(section_fields),
                "missing_count": sum(1 for field in section_fields if field["status"] == "missing"),
                "required_missing_count": sum(
                    1
                    for field in section_fields
                    if field["status"] == "missing" and field["report_importance"] == "required"
                ),
                "recommended_missing_count": sum(
                    1
                    for field in section_fields
                    if field["status"] == "missing" and field["report_importance"] == "recommended"
                ),
                "overridden_count": sum(1 for field in section_fields if field["overridden"]),
                "fields": section_fields,
            }
        )

    return {
        "schema_name": "report_authoring_view_model",
        "version": "0.1.0",
        "page_action_contract": wizard_page_action_contract("report_metadata"),
        "sections": sections,
        "fields": fields,
        "summary": {
            "field_count": len(fields),
            "missing_count": sum(1 for field in fields if field["status"] == "missing"),
            "required_missing_count": sum(
                1 for field in fields if field["status"] == "missing" and field["report_importance"] == "required"
            ),
            "recommended_missing_count": sum(
                1 for field in fields if field["status"] == "missing" and field["report_importance"] == "recommended"
            ),
            "override_count": sum(1 for field in fields if field["overridden"]),
            "section_count": len(sections),
        },
        "filters": [
            {
                "filter_id": filter_id,
                "label": filter_id.replace("_", " ").title(),
                "count": len(filter_report_authoring_fields(fields, filter_id)),
            }
            for filter_id in REPORT_AUTHORING_FILTERS
        ],
    }


def report_authoring_view_model_from_report_payload(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    return report_authoring_view_model(
        catalog=report_payload.get("report_field_catalog_resolved", []) or [],
        values_used=report_payload.get("report_values_used", []) or [],
        missing_fields=report_payload.get("missing_report_fields", []) or [],
        overrides=report_payload.get("report_field_overrides", []) or [],
    )


def filter_report_authoring_fields(fields_or_model: Any, filter_id: str) -> list[dict[str, Any]]:
    fields = fields_or_model.get("fields", []) if isinstance(fields_or_model, Mapping) else fields_or_model
    rows = [dict(row) for row in fields or [] if isinstance(row, Mapping)]
    if filter_id == "missing":
        return [row for row in rows if row.get("status") == "missing"]
    if filter_id == "required":
        return [row for row in rows if row.get("report_importance") == "required" or row.get("required") is True]
    if filter_id == "recommended":
        return [row for row in rows if row.get("report_importance") == "recommended"]
    if filter_id == "overridden":
        return [row for row in rows if row.get("overridden") is True or row.get("status") == "overridden"]
    return rows


def build_report_override_payload(
    *,
    field_key: str,
    value: Any,
    reason: str,
    reviewer: str = "",
    section: str = "",
    source_surface: str = "method_run_wizard.report_authoring",
) -> dict[str, Any]:
    field_key = str(field_key).strip()
    reason = str(reason).strip()
    if not field_key:
        raise ValueError("Report override requires field_key.")
    if value in (None, ""):
        raise ValueError(f"Report override for '{field_key}' requires a value.")
    if not reason:
        raise ValueError(f"Report override for '{field_key}' requires a reason.")
    return {
        "field_key": field_key,
        "value": value,
        "reason": reason,
        "reviewer": reviewer,
        "section": section,
        "source_surface": source_surface,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _override_rows(overrides: Iterable[Mapping[str, Any]] | Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if isinstance(overrides, Mapping):
        payload = overrides.get("overrides")
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, Mapping)]
        records = overrides.get("records")
        if isinstance(records, list):
            return [row for row in records if isinstance(row, Mapping)]
        return [overrides]
    return [row for row in overrides or [] if isinstance(row, Mapping)]


def _row_key(row: Mapping[str, Any]) -> str:
    return str(row.get("field_key") or row.get("field") or "").strip()


def _is_report_only(
    entry: Mapping[str, Any],
    value_row: Mapping[str, Any],
    missing_row: Mapping[str, Any],
) -> bool:
    importance = str(entry.get("report_importance") or missing_row.get("report_importance") or "").casefold()
    source_type = str(value_row.get("source_type") or value_row.get("source") or "").casefold()
    if source_type == "mtda_method_output":
        return False
    return importance in {"required", "recommended", "optional", ""}


def _importance_label(value: str) -> str:
    labels = {
        "required": "Required for complete report",
        "recommended": "Recommended report field",
        "optional": "Optional report field",
        "none": "Not used for report completion",
        "": "Recommended report field",
    }
    return labels.get(str(value).casefold(), str(value).replace("_", " ").title())


def _status_label(value: str) -> str:
    labels = {
        "missing": "Missing",
        "present": "Present",
        "overridden": "Report override recorded",
    }
    return labels.get(str(value).casefold(), str(value).replace("_", " ").title())


def _source_type_label(value: object) -> str:
    labels = {
        "missing": "Not recorded in source package",
        "report_override": "Report-only amendment",
        "source_mtdp_dataset": "Source package dataset metadata",
        "source_mtdp_run": "Source package run metadata",
        "mtda_method_output": "Computed method output",
    }
    text = str(value or "").strip()
    return labels.get(text, text.replace("_", " ").title())


def _missing_reason(row: Mapping[str, Any]) -> str:
    if not row:
        return ""
    return "Not recorded in source package."


def _guidance(importance: str, missing_reason: str) -> str:
    if str(importance).casefold() == "required":
        return "Resolve this before final issue."
    if missing_reason:
        return "Add a value or status. Unresolved recommended fields finalize with warnings."
    return "Review this field only if the formal report needs more detail."
