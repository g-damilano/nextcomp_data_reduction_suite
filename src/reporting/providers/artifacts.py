from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class ArtifactsProvider(ReportDataProvider):
    provider_id = "artifacts"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[str]:
        return list(context.table("artifacts"))
