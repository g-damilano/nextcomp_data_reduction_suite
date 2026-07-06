from __future__ import annotations

from typing import Any

from reporting.blocks.base import ReportBlock
from reporting.core.report_context import ReportContext


class SummaryCardsBlock(ReportBlock):
    block_type = "summary_cards"

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            return [{"label": key, "value": value} for key, value in data.items()]
        if isinstance(data, list):
            return data
        return []
