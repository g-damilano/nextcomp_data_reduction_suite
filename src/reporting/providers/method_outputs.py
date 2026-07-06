from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class IndividualResultsProvider(ReportDataProvider):
    provider_id = "individual_results"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list(context.table("individual_results"))
