from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.acceptance import AcceptanceSummaryProvider, CurveFamilySummaryProvider, DischargeSummaryProvider
from reporting.providers.artifacts import ArtifactsProvider
from reporting.providers.curve_aggregation import (
    AggregateCurveSummaryProvider,
    AggregatePlotSpecProvider,
    AggregateStatisticsProvider,
    AlignedCurvesProvider,
    CharacteristicPointsProvider,
    FeatureLinesProvider,
)
from reporting.providers.method_metadata import MethodMetadataProvider
from reporting.providers.method_outputs import IndividualResultsProvider
from reporting.providers.readiness import ReadinessSummaryProvider
from reporting.providers.report_values import MissingReportFieldsProvider, ReportValuesProvider
from reporting.providers.reporting_tables import (
    DeviationsFromStandardProvider,
    FailureAnalysisBendingDistributionProvider,
    FailureAnalysisInvalidSpecimensProvider,
    FailureAnalysisObservationsProvider,
    FailureAnalysisProvider,
    ReportCompletenessProvider,
    ReportSectionsProvider,
)
from reporting.providers.validation import ValidationSummaryProvider


class DataProviderRegistry:
    """Registry of reusable report data providers."""

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}
        for provider in (
            MethodMetadataProvider(),
            ReportValuesProvider(),
            MissingReportFieldsProvider(),
            ReportSectionsProvider(),
            ReportCompletenessProvider(),
            ReadinessSummaryProvider(),
            ValidationSummaryProvider(),
            AcceptanceSummaryProvider(),
            DischargeSummaryProvider(),
            CurveFamilySummaryProvider(),
            IndividualResultsProvider(),
            AggregateStatisticsProvider(),
            CharacteristicPointsProvider(),
            FeatureLinesProvider(),
            AlignedCurvesProvider(),
            FailureAnalysisProvider(),
            FailureAnalysisObservationsProvider(),
            FailureAnalysisInvalidSpecimensProvider(),
            FailureAnalysisBendingDistributionProvider(),
            DeviationsFromStandardProvider(),
            AggregateCurveSummaryProvider(),
            AggregatePlotSpecProvider(),
            ArtifactsProvider(),
        ):
            self.register(provider.provider_id, provider)

    def register(self, provider_id: str, provider: Any) -> None:
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> Any:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown report data provider: {provider_id}") from exc

    def provide(self, provider_id: str, context: ReportContext, block: dict[str, Any] | None = None) -> Any:
        return self.get(provider_id).provide(context, block)

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
