from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class ReadinessSummaryProvider(ReportDataProvider):
    provider_id = "readiness_summary"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list(context.result.readiness_summary)
