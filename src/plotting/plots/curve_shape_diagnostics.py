from __future__ import annotations

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.vega_lite import finalise_spec, unavailable_result


def build_curve_shape_diagnostics(request: PlotRequest) -> PlotResult:
    scores = [
        row
        for row in request.data_payload.get("scores", [])
        if isinstance(row, dict)
    ]
    if not scores:
        return unavailable_result(request, "Plot unavailable: missing curve diagnostic scores.")
    values = [
        {
            "classification": str(row.get("diagnostic_classification") or "CURVE_SHAPE_NOT_ASSESSED"),
            "count": 1,
        }
        for row in scores
    ]
    spec = {
        "description": "curve_shape_diagnostics: compact count by diagnostic classification.",
        "height": 220,
        "usermeta": {"semantic_layers": ["diagnostic_classification_summary"], "plotting_module": "plotting"},
        "mark": {"type": "bar"},
        "data": {"values": values},
        "encoding": {
            "x": {"field": "classification", "type": "nominal", "title": "Curve-shape classification"},
            "y": {"aggregate": "count", "field": "count", "type": "quantitative", "title": "Run count"},
            "tooltip": [
                {"field": "classification", "type": "nominal", "title": "Classification"},
                {"aggregate": "count", "field": "count", "type": "quantitative", "title": "Run count"},
            ],
        },
    }
    return finalise_spec(spec, request, [PlotLayerContract("diagnostic_classification_summary", "classification summary")])
