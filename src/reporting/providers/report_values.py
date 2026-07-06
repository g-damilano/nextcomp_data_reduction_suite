from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class ReportValuesProvider(ReportDataProvider):
    provider_id = "report_values"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict(context.values_by_key)


class MissingReportFieldsProvider(ReportDataProvider):
    provider_id = "missing_report_fields"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list(context.table("missing_report_fields"))
