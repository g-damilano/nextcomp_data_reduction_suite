from __future__ import annotations

from reporting.core.report_document import ReportDocument


class JsonRenderer:
    renderer_id = "json"

    def render(self, document: ReportDocument) -> dict[str, object]:
        return document.to_dict()
