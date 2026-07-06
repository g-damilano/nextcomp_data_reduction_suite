from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class _TableProvider(ReportDataProvider):
    table_name = ""

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> Any:
        return context.table(self.table_name)


class ReportSectionsProvider(_TableProvider):
    provider_id = "report_sections"
    table_name = "report_sections"


class ReportCompletenessProvider(_TableProvider):
    provider_id = "report_completeness_summary"
    table_name = "report_completeness_summary"


class FailureAnalysisProvider(_TableProvider):
    provider_id = "failure_analysis"
    table_name = "failure_analysis"


class FailureAnalysisObservationsProvider(_TableProvider):
    provider_id = "failure_analysis_observations"
    table_name = "failure_analysis_observations"


class FailureAnalysisInvalidSpecimensProvider(_TableProvider):
    provider_id = "failure_analysis_invalid_specimens"
    table_name = "failure_analysis_invalid_specimens"


class FailureAnalysisBendingDistributionProvider(_TableProvider):
    provider_id = "failure_analysis_bending_distribution"
    table_name = "failure_analysis_bending_distribution"


class DeviationsFromStandardProvider(_TableProvider):
    provider_id = "deviations_from_standard"
    table_name = "deviations_from_standard"
