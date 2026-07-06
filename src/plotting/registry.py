from __future__ import annotations

from collections.abc import Callable

from plotting.models import PlotRequest, PlotResult
from plotting.vega_lite import failed_result

PlotBuilder = Callable[[PlotRequest], PlotResult]


class PlotRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, PlotBuilder] = {}

    def register(self, plot_type: str, builder: PlotBuilder) -> None:
        self._builders[plot_type] = builder

    def build(self, request: PlotRequest) -> PlotResult:
        builder = self._builders.get(request.plot_type)
        if builder is None:
            return failed_result(request, f"Plot type '{request.plot_type}' is not registered.")
        try:
            return builder(request)
        except Exception as exc:  # pragma: no cover - defensive envelope for report generation
            return failed_result(request, f"Plot '{request.plot_id}' failed: {exc}")

    def plot_types(self) -> list[str]:
        return sorted(self._builders)


def create_default_registry() -> PlotRegistry:
    from plotting.plots.aggregate_curve_family import build_aggregate_curve_family
    from plotting.plots.bending_evidence import build_bending_evidence
    from plotting.plots.curve_residuals import build_curve_shape_residuals
    from plotting.plots.curve_shape_diagnostics import build_curve_shape_diagnostics
    from plotting.plots.distance_ranking import build_curve_shape_distance_ranking
    from plotting.plots.generic_xy_overlay import build_generic_xy_overlay
    from plotting.plots.stress_strain_reduction import build_stress_strain_reduction
    from plotting.plots.formal_report import (
        FORMAL_AGGREGATE_PLOT_TYPE,
        FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
        build_aggregate_stress_strain_mean_variability,
        build_failure_analysis_bending_distribution,
    )

    registry = PlotRegistry()
    registry.register("stress_strain_reduction", build_stress_strain_reduction)
    registry.register("bending_evidence", build_bending_evidence)
    registry.register("aggregate_curve_family", build_aggregate_curve_family)
    registry.register("curve_shape_distance_ranking", build_curve_shape_distance_ranking)
    registry.register("curve_shape_residuals", build_curve_shape_residuals)
    registry.register("curve_shape_diagnostics", build_curve_shape_diagnostics)
    registry.register("generic_xy_overlay", build_generic_xy_overlay)
    registry.register(FORMAL_AGGREGATE_PLOT_TYPE, build_aggregate_stress_strain_mean_variability)
    registry.register(FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE, build_failure_analysis_bending_distribution)
    return registry


plot_registry = create_default_registry()
