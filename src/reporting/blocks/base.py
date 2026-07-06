from __future__ import annotations

from typing import Any

from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.report_context import ReportContext
from reporting.core.report_document import ReportBlockDocument


class ReportBlock:
    block_type = "base"

    def resolve(
        self,
        block: dict[str, Any],
        context: ReportContext,
        providers: DataProviderRegistry,
    ) -> ReportBlockDocument:
        provider_id = str(block.get("provider") or "")
        data = providers.provide(provider_id, context, block) if provider_id else {}
        data = self.transform(data, block, context)
        return ReportBlockDocument(
            id=str(block.get("id") or self.block_type),
            type=str(block.get("type") or self.block_type),
            title=str(block.get("title") or block.get("id") or self.block_type),
            provider=provider_id,
            data=data,
            config={key: value for key, value in block.items() if key not in {"id", "type", "title", "provider"}},
        )

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> Any:
        return data
