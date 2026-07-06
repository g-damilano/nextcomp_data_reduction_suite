from __future__ import annotations

from typing import Any

from reporting.blocks.base import ReportBlock
from reporting.core.report_context import ReportContext


class TableBlock(ReportBlock):
    block_type = "table"

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> list[dict[str, Any]]:
        rows = list(data) if isinstance(data, list) else []
        columns = block.get("columns")
        if not isinstance(columns, list) or not columns:
            return rows
        selected = [str(column) for column in columns]
        return [{column: row.get(column, "") for column in selected} for row in rows if isinstance(row, dict)]
