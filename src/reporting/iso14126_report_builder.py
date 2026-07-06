from __future__ import annotations

from methods.core.method_result import MethodRunResult
from reporting.core.report_engine import GenericReportEngine
from reporting.report_models import ReportArtifactBundle


class ISO14126ReportBuilder:
    """Compatibility wrapper for callers that still import the old ISO builder.

    Stage 10.5 moved report assembly into GenericReportEngine. This class stays
    as a thin delegator until downstream imports migrate.
    """

    def __init__(self, engine: GenericReportEngine | None = None) -> None:
        self.engine = engine or GenericReportEngine()

    def build(self, result: MethodRunResult) -> ReportArtifactBundle:
        return self.engine.build(result)
