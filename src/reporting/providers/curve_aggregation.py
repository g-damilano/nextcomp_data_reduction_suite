from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class _TableProvider(ReportDataProvider):
    table_name = ""

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> Any:
        return context.table(self.table_name)


class AggregateStatisticsProvider(_TableProvider):
    provider_id = "aggregate_statistics"
    table_name = "aggregate_statistics"


class CharacteristicPointsProvider(_TableProvider):
    provider_id = "characteristic_points"
    table_name = "characteristic_points"


class FeatureLinesProvider(_TableProvider):
    provider_id = "feature_lines"
    table_name = "feature_lines"


class AlignedCurvesProvider(_TableProvider):
    provider_id = "aligned_curves"
    table_name = "aligned_curves"


class AggregateCurveSummaryProvider(_TableProvider):
    provider_id = "aggregate_curve_summary"
    table_name = "aggregate_curve_summary"


class AggregatePlotSpecProvider(_TableProvider):
    provider_id = "aggregate_plot_spec"
    table_name = "aggregate_plot_spec"
