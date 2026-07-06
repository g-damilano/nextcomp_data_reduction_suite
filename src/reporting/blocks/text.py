from __future__ import annotations

from typing import Any

from reporting.blocks.base import ReportBlock
from reporting.core.report_context import ReportContext


class TextBlock(ReportBlock):
    block_type = "text"

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> str:
        key = block.get("key")
        if key and isinstance(data, dict):
            return str(data.get(str(key)) or "")
        return str(data or "")
