from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext


class ReportDataProvider:
    """Base provider for resolved report data."""

    provider_id = "base"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError
