from __future__ import annotations

from typing import Any


def report_completion_status(missing_fields: list[dict[str, Any]]) -> dict[str, Any]:
    required_missing = [
        row for row in missing_fields
        if str(row.get("report_importance") or row.get("requirement_level") or row.get("severity")).casefold()
        in {"required", "execution_critical", "critical"}
    ]
    if required_missing:
        status = "INCOMPLETE"
    elif missing_fields:
        status = "COMPLETE_WITH_WARNINGS"
    else:
        status = "COMPLETE"
    return {
        "schema_id": "report.completion_status.v0_1",
        "status": status,
        "required_missing_count": len(required_missing),
        "recommended_missing_count": max(0, len(missing_fields) - len(required_missing)),
        "missing_field_count": len(missing_fields),
        "required_missing_fields": [str(row.get("field") or row.get("field_key")) for row in required_missing],
        "recommended_missing_fields": [
            str(row.get("field") or row.get("field_key"))
            for row in missing_fields
            if row not in required_missing
        ],
    }
