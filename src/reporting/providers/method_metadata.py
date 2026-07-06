from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class MethodMetadataProvider(ReportDataProvider):
    provider_id = "method_metadata"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> dict[str, Any]:
        result = context.result
        return {
            "method_id": result.method_package.method_id,
            "method_version": result.method_package.version,
            "method_name": result.method_package.name,
            "standard_reference": result.method_package.manifest.get("standard_reference", "ISO 14126"),
            "source_package": str(result.source.path),
            "selection_set": context.selection_set,
        }
