from __future__ import annotations

from typing import Any

from plotting.models import PlotRequest, PlotResult
from plotting.plots.formal_report import (
    FORMAL_AGGREGATE_PLOT_TYPE,
    FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
    aggregate_stress_strain_vega_lite as _aggregate_stress_strain_vega_lite,
    build_aggregate_stress_strain_mean_variability,
    build_failure_analysis_bending_distribution,
    failure_analysis_bending_distribution_vega_lite as _failure_analysis_bending_distribution_vega_lite,
)
from reporting.blocks.base import ReportBlock
from reporting.core.report_context import ReportContext


class VegaPlotBlock(ReportBlock):
    block_type = "vega_plot"

    def transform(self, data: Any, block: dict[str, Any], context: ReportContext) -> dict[str, Any]:
        spec_id = str(block.get("spec") or "aggregate_stress_strain_mean_variability")
        if spec_id == "aggregate_stress_strain_mean_variability":
            spec = context.table("aggregate_plot_spec")
            source_spec = spec if isinstance(spec, dict) else {}
            result = context.result
            replicate_curves = []
            replicate_source = "boundary_aligned_curves"
            source_warnings: list[str] = []
            endpoint_strains = {}
            boundary_records = []
            if result is not None:
                boundary_records = getattr(result, "experiment_boundaries", None) or []
                bounded_curves = getattr(result, "bounded_curve_family", None)
                replicate_curves = bounded_curves or []
                if not boundary_records:
                    replicate_curves = bounded_curves or getattr(result, "curve_family", [])
                    replicate_source = "bounded_curve_family" if bounded_curves else "curve_family"
                endpoint_strains = _endpoint_strains(getattr(result, "specimen_results", []))
            plot_request = PlotRequest(
                plot_type=FORMAL_AGGREGATE_PLOT_TYPE,
                plot_id=spec_id,
                title="Aggregate stress-strain mean and variability",
                data_payload={
                    "source_spec": source_spec,
                    "aligned_curves": context.table("aligned_curves"),
                    "replicate_curves": replicate_curves,
                    "selected_run_ids": sorted(context.selection_run_ids),
                    "endpoint_strains": endpoint_strains,
                    "boundary_records": boundary_records,
                    "replicate_source": replicate_source,
                    "source_warnings": source_warnings,
                },
                surface_context="test_report",
            )
            plot_result = _build_registered_formal_plot(plot_request)
            vega_lite_spec = plot_result.spec or {}
            freshness = _freshness_from_spec(vega_lite_spec)
            return {
                "schema_id": "report.vega_plot_block.v0_1",
                "spec_id": spec_id,
                "source_spec": source_spec,
                "plot_data_freshness": freshness,
                "vega_lite_spec": vega_lite_spec,
                "plot_result": plot_result.to_dict(),
            }
        if spec_id == "failure_analysis_bending_distribution":
            source_spec = context.table("failure_analysis_bending_distribution")
            source_spec = source_spec if isinstance(source_spec, dict) else {}
            status = "unavailable" if source_spec.get("unavailable_message") else "current"
            plot_request = PlotRequest(
                plot_type=FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
                plot_id=spec_id,
                title="Bending distribution over assessed domain",
                data_payload={"source_spec": source_spec},
                surface_context="test_report",
            )
            plot_result = _build_registered_formal_plot(plot_request)
            vega_lite_spec = plot_result.spec or {}
            return {
                "schema_id": "report.vega_plot_block.v0_1",
                "spec_id": spec_id,
                "source_spec": source_spec,
                "plot_data_freshness": {
                    "schema_id": "report.plot_data_freshness.v0_1",
                    "status": status,
                    "reasons": [source_spec.get("unavailable_message")] if source_spec.get("unavailable_message") else [],
                },
                "vega_lite_spec": vega_lite_spec,
                "plot_result": plot_result.to_dict(),
                "unavailable_message": source_spec.get("unavailable_message", ""),
            }
        return {"spec_id": spec_id, "data": data}


def _build_registered_formal_plot(request: PlotRequest) -> PlotResult:
    from plotting.registry import plot_registry

    return plot_registry.build(request)


def _freshness_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    usermeta = spec.get("usermeta") if isinstance(spec.get("usermeta"), dict) else {}
    freshness = usermeta.get("plot_data_freshness") if isinstance(usermeta.get("plot_data_freshness"), dict) else {}
    return dict(freshness)


def _endpoint_strains(specimen_results: Any) -> dict[str, float]:
    endpoints: dict[str, float] = {}
    if not isinstance(specimen_results, list):
        return endpoints
    for row in specimen_results:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        endpoint = _as_float(row.get("compressive_failure_strain"))
        if run_id and endpoint is not None and endpoint > 0:
            endpoints[run_id] = endpoint
    return endpoints


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
