from __future__ import annotations

from typing import Any

from reporting.blocks.base import ReportBlock
from reporting.core.report_context import ReportContext


class FieldTableBlock(ReportBlock):
    block_type = "field_table"

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> list[dict[str, Any]]:
        values = data if isinstance(data, dict) else {}
        rows: list[dict[str, Any]] = []
        for field in block.get("fields", []) or []:
            if not isinstance(field, dict):
                continue
            key = str(field.get("key") or "")
            value = values.get(key, "")
            rows.append(
                {
                    "label": field.get("label") or key,
                    "key": key,
                    "value": value,
                    "status": "missing" if value in ("", None) else "present",
                }
            )
        return rows
