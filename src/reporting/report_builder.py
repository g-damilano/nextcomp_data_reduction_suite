from __future__ import annotations

from methods.core.method_result import MethodRunResult
from reporting.core.report_engine import GenericReportEngine
from reporting.report_models import ReportArtifactBundle


class ReportBuilder:
    """Writer-facing API for recipe-driven method reports."""

    def __init__(self, engine: GenericReportEngine | None = None) -> None:
        self.engine = engine or GenericReportEngine()

    def build(self, result: MethodRunResult) -> ReportArtifactBundle:
        return self.engine.build(result)
