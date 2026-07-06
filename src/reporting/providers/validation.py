from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class ValidationSummaryProvider(ReportDataProvider):
    provider_id = "validation_summary"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict(context.result.validation_report.get("summary", {}))
