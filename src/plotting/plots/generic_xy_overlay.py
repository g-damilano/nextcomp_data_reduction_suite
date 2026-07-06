from __future__ import annotations

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.vega_lite import finalise_spec, unavailable_result


def build_generic_xy_overlay(request: PlotRequest) -> PlotResult:
    rows = [
        row
        for row in request.data_payload.get("rows", [])
        if isinstance(row, dict)
    ]
    if not rows:
        return unavailable_result(request, "Plot unavailable: missing x/y overlay data.")
    x_field = str(request.data_payload.get("x_field") or "x")
    y_field = str(request.data_payload.get("y_field") or "y")
    series_field = str(request.data_payload.get("series_field") or "series")
    x_title = str(request.data_payload.get("x_title") or x_field.replace("_", " ").title())
    y_title = str(request.data_payload.get("y_title") or y_field.replace("_", " ").title())
    spec = {
        "description": "generic_xy_overlay: reusable x/y line overlay.",
        "height": 280,
        "usermeta": {"semantic_layers": ["generic_xy_series"], "plotting_module": "plotting"},
        "data": {"values": rows},
        "mark": {"type": "line", "clip": True},
        "encoding": {
            "x": {"field": x_field, "type": "quantitative", "title": x_title},
            "y": {"field": y_field, "type": "quantitative", "title": y_title},
            "color": {"field": series_field, "type": "nominal", "title": "Series"},
            "tooltip": [
                {"field": series_field, "type": "nominal", "title": "Series"},
                {"field": x_field, "type": "quantitative", "title": x_title},
                {"field": y_field, "type": "quantitative", "title": y_title},
            ],
        },
    }
    return finalise_spec(spec, request, [PlotLayerContract("generic_xy_series", "generic x/y overlay")])
