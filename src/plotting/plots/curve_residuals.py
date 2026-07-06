from __future__ import annotations

from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.plots.common import as_float, curve_shape_color_scale, downsample_rows, x_common_percent
from plotting.vega_lite import finalise_spec, unavailable_result


def build_curve_shape_residuals(request: PlotRequest) -> PlotResult:
    residuals = [
        row
        for row in request.data_payload.get("residuals", [])
        if isinstance(row, dict)
    ]
    if not residuals:
        return unavailable_result(request, "Plot unavailable: missing curve diagnostic residuals.")
    scores = [
        row
        for row in request.data_payload.get("scores", [])
        if isinstance(row, dict)
    ]
    classification_by_run = {
        str(row.get("run_id") or ""): str(row.get("diagnostic_classification") or "")
        for row in scores
    }
    values = []
    for row in downsample_rows(residuals, 1600):
        x_value = x_common_percent(row)
        z_value = as_float(row.get("standardized_residual"))
        run_id = str(row.get("run_id") or "")
        if x_value is None or z_value is None or not run_id:
            continue
        values.append(
            {
                "run_id": run_id,
                "x": x_value,
                "standardized_residual": z_value,
                "diagnostic_classification": classification_by_run.get(run_id, row.get("diagnostic_classification", "")),
            }
        )
    if not values:
        return unavailable_result(request, "Plot unavailable: residual rows contain no standardized residual values.")

    semantic_layers = ["residual_curves", "zero_line"]
    if any(str(row.get("diagnostic_classification") or "") == "CURVE_SHAPE_OUTLIER" for row in values):
        semantic_layers.append("highlighted_outlier_residuals")

    spec = {
        "description": "Curve residual detail: standardized residual z(x) by run.",
        "height": 260,
        "usermeta": {"semantic_layers": semantic_layers, "plotting_module": "plotting"},
        "layer": [
            {
                "name": "zero line",
                "data": {"values": [{"zero": 0}]},
                "mark": {"type": "rule", "color": "#7d8794", "strokeDash": [4, 4]},
                "encoding": {"y": {"field": "zero", "type": "quantitative", "title": "Standardized residual z(x)"}},
            },
            {
                "name": "residual curves",
                "data": {"values": values},
                "mark": {"type": "line", "strokeWidth": 1.2, "opacity": 0.45},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": "Normalised strain / %"},
                    "y": {"field": "standardized_residual", "type": "quantitative", "title": "Standardized residual z(x)"},
                    "detail": {"field": "run_id"},
                    "color": {
                        "field": "diagnostic_classification",
                        "type": "nominal",
                        "title": "Curve-shape classification",
                        "scale": curve_shape_color_scale(),
                    },
                    "tooltip": [
                        {"field": "run_id", "type": "nominal", "title": "Run"},
                        {"field": "x", "type": "quantitative", "title": "Normalised strain / %", "format": ".2f"},
                        {"field": "standardized_residual", "type": "quantitative", "title": "z(x)", "format": ".3f"},
                        {"field": "diagnostic_classification", "type": "nominal", "title": "Classification"},
                    ],
                },
            },
        ],
    }
    return finalise_spec(spec, request, _contracts())


def _contracts() -> list[PlotLayerContract]:
    return [
        PlotLayerContract("residual_curves", "standardized residual curves", required=True),
        PlotLayerContract("zero_line", "zero residual guide", required=True),
        PlotLayerContract("highlighted_outlier_residuals", "outlier residual highlighting", required=False),
        PlotLayerContract("threshold_guide_bands", "residual threshold guide bands", required=False),
    ]
