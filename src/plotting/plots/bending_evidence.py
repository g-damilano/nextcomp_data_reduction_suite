from __future__ import annotations

from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.plots.common import as_float, bending_pattern_palette, downsample_rows, nested
from plotting.vega_lite import finalise_spec, unavailable_result


def build_bending_evidence(request: PlotRequest) -> PlotResult:
    source_rows = [
        row
        for row in request.data_payload.get("bounded_rows", [])
        if isinstance(row, dict)
    ]
    bending_rows = _bending_rows(source_rows)
    if not bending_rows:
        return unavailable_result(request, "Plot unavailable: missing front/rear strain and load evidence.")

    block = request.data_payload.get("block") if isinstance(request.data_payload.get("block"), dict) else {}
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    classification_color = _classification_color(str(summary.get("classification") or ""))
    threshold = as_float(summary.get("threshold_percent") or nested(block, "markers", "threshold_line", "bending_percent")) or 10.0
    window = nested(block, "markers", "assessment_window_10_90_fmax", "load_window_N") or []
    lower = as_float(window[0]) if isinstance(window, list) and len(window) > 0 else as_float(nested(block, "markers", "assessment_window_10_90_fmax", "lower_load_N"))
    upper = as_float(window[1]) if isinstance(window, list) and len(window) > 1 else as_float(nested(block, "markers", "assessment_window_10_90_fmax", "upper_load_N"))
    assessed_rows = _rows_in_window(bending_rows, lower, upper)
    max_y = max([row["bending_percent"] for row in bending_rows if row.get("bending_percent") is not None] + [threshold])
    exceedances = [row for row in assessed_rows if as_float(row.get("bending_percent")) is not None and float(row["bending_percent"]) > threshold]
    segments = _segment_values(block, max_y=max_y, lower=lower, upper=upper)
    boundary_values = _assessment_boundary_values(lower=lower, upper=upper, max_y=max_y)
    threshold_labels = _threshold_label_values(bending_rows, threshold=threshold)
    load_scale = _load_scale(bending_rows)

    semantic_layers = ["bending_percent_series", "context_bending_series", "threshold_line", "threshold_annotation", "assessment_window_10_90_fmax", "classification_marker"]
    if boundary_values:
        semantic_layers.extend(["assessment_window_10_percent_boundary", "assessment_window_90_percent_boundary"])
    if exceedances:
        semantic_layers.append("exceedance_points")
    if segments:
        semantic_layers.append("exceedance_segments")

    spec = {
        "description": "run_bending_evidence: threshold line, 10-90% window, exceedance segments, classification",
        "height": 280,
        "usermeta": {
            "classification": summary.get("classification", ""),
            "semantic_layers": semantic_layers,
            "plotting_module": "plotting",
        },
        "layer": [
            {
                "name": "10-90% window",
                "data": {"values": [{"x1": lower, "x2": upper, "y1": 0.0, "y2": max_y * 1.08}] if lower is not None and upper is not None else []},
                "mark": {"type": "rect", "color": "#7d8794", "opacity": 0.12},
                "encoding": {
                    "x": {"field": "x1", "type": "quantitative", "title": "Load / N", "scale": load_scale},
                    "x2": {"field": "x2"},
                    "y": {"field": "y1", "type": "quantitative", "title": "Bending / %"},
                    "y2": {"field": "y2"},
                },
            },
            {
                "name": "10% and 90% Fmax boundary lines",
                "data": {"values": boundary_values},
                "mark": {"type": "rule", "strokeDash": [5, 4], "strokeWidth": 1.3, "color": "#6d7784"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "title": "Load / N", "scale": load_scale},
                    "tooltip": [
                        {"field": "label", "type": "nominal", "title": "Assessment boundary"},
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                    ],
                },
            },
            {
                "name": "10% and 90% Fmax boundary annotations",
                "data": {"values": boundary_values},
                "mark": {"type": "text", "align": "center", "baseline": "bottom", "dy": -4, "fontSize": 11, "color": "#4d5966"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "scale": load_scale},
                    "y": {"field": "label_y", "type": "quantitative"},
                    "text": {"field": "label"},
                    "tooltip": [
                        {"field": "label", "type": "nominal", "title": "Assessment boundary"},
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                    ],
                },
            },
            {
                "name": "exceedance segments",
                "data": {"values": segments},
                "mark": {"type": "rect", "color": "#f7dfdd", "opacity": 0.36},
                "encoding": {
                    "x": {"field": "start_load_N", "type": "quantitative", "scale": load_scale},
                    "x2": {"field": "end_load_N"},
                    "y": {"field": "y1", "type": "quantitative"},
                    "y2": {"field": "y2"},
                    "tooltip": [{"field": "segment_classification", "type": "nominal", "title": "Segment"}],
                },
            },
            {
                "name": "bending percent series outside assessment window",
                "data": {"values": downsample_rows(bending_rows, 700)},
                "mark": {"type": "line", "clip": True, "strokeWidth": 1.5, "opacity": 0.26, "color": classification_color},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "title": "Load / N", "scale": load_scale},
                    "y": {"field": "bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "tooltip": [
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                    ],
                },
            },
            {
                "name": "bending percent series",
                "data": {"values": downsample_rows(assessed_rows, 700)},
                "mark": {"type": "line", "clip": True, "strokeWidth": 2.2, "color": classification_color},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "title": "Load / N", "scale": load_scale},
                    "y": {"field": "bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "tooltip": [
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                    ],
                },
            },
            {
                "name": "exceedance points",
                "data": {"values": exceedances},
                "mark": {"type": "point", "filled": True, "size": 42, "color": "#d9786d"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "scale": load_scale},
                    "y": {"field": "bending_percent", "type": "quantitative"},
                    "tooltip": [
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                    ],
                },
            },
            {
                "name": "threshold line",
                "data": {"values": [{"threshold": threshold}]},
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#d9786d"},
                "encoding": {
                    "y": {"field": "threshold", "type": "quantitative", "title": "Bending / %"},
                    "tooltip": [{"field": "threshold", "type": "quantitative", "title": "Threshold / %"}],
                },
            },
            {
                "name": "threshold annotation",
                "data": {"values": threshold_labels},
                "mark": {"type": "text", "align": "right", "baseline": "bottom", "dx": 0, "dy": -4, "fontSize": 11, "fontWeight": "bold", "color": "#b85f56"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "scale": load_scale},
                    "y": {"field": "threshold", "type": "quantitative"},
                    "text": {"field": "label"},
                    "tooltip": [{"field": "label", "type": "nominal", "title": "Threshold"}],
                },
            },
        ],
    }
    return finalise_spec(spec, request, _contracts())


def _classification_color(classification: str) -> str:
    palette = bending_pattern_palette()
    value = classification.strip().upper()
    if value in palette:
        return palette[value]
    if value.startswith("FAIL"):
        return palette["FAIL"]
    if value.startswith("WARN"):
        return palette["WARN"]
    return palette["PASS"]


def _contracts() -> list[PlotLayerContract]:
    return [
        PlotLayerContract("bending_percent_series", "bending percent series", required=True),
        PlotLayerContract("context_bending_series", "bending percent context outside assessment window", required=False),
        PlotLayerContract("threshold_line", "bending threshold line", required=True),
        PlotLayerContract("threshold_annotation", "bending threshold annotation", required=False),
        PlotLayerContract("assessment_window_10_90_fmax", "10-90% Fmax assessment window", required=False),
        PlotLayerContract("assessment_window_10_percent_boundary", "10% Fmax assessment boundary", required=False),
        PlotLayerContract("assessment_window_90_percent_boundary", "90% Fmax assessment boundary", required=False),
        PlotLayerContract("exceedance_points", "above-threshold points", required=False),
        PlotLayerContract("exceedance_segments", "above-threshold sustained/transient segments", required=False),
        PlotLayerContract("classification_marker", "classification context", required=False),
    ]


def _bending_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        front = as_float(row.get("front_strain_abs") or row.get("front_strain"))
        rear = as_float(row.get("rear_strain_abs") or row.get("rear_strain"))
        load = as_float(row.get("load_N"))
        if front is None or rear is None or load is None:
            continue
        denominator = abs(front + rear)
        if denominator == 0:
            continue
        out.append(
            {
                "point_index": as_float(row.get("point_index")),
                "load_N": abs(load),
                "bending_percent": abs(front - rear) / denominator * 100.0,
            }
        )
    return out


def _assessment_boundary_values(*, lower: float | None, upper: float | None, max_y: float) -> list[dict[str, Any]]:
    values = []
    if lower is not None:
        values.append({"load_N": lower, "label": "10% Fmax", "label_y": max_y * 1.08})
    if upper is not None:
        values.append({"load_N": upper, "label": "90% Fmax", "label_y": max_y * 1.08})
    return values


def _rows_in_window(rows: list[dict[str, Any]], lower: float | None, upper: float | None) -> list[dict[str, Any]]:
    if lower is None or upper is None:
        return list(rows)
    lo, hi = sorted((lower, upper))
    return [
        row
        for row in rows
        if (load := as_float(row.get("load_N"))) is not None and lo <= load <= hi
    ]


def _threshold_label_values(rows: list[dict[str, Any]], *, threshold: float) -> list[dict[str, Any]]:
    loads = [as_float(row.get("load_N")) for row in rows]
    loads = [load for load in loads if load is not None]
    if not loads:
        return []
    return [{"load_N": max(loads), "threshold": threshold, "label": f"{threshold:g}% threshold"}]


def _load_scale(rows: list[dict[str, Any]]) -> dict[str, Any]:
    loads = [as_float(row.get("load_N")) for row in rows]
    loads = [load for load in loads if load is not None]
    if not loads:
        return {}
    lower = min(0.0, min(loads))
    upper = max(loads)
    if upper <= lower:
        upper = lower + 1.0
    return {"domain": [lower, upper], "nice": False}


def _segment_values(block: dict[str, Any], *, max_y: float, lower: float | None = None, upper: float | None = None) -> list[dict[str, Any]]:
    segments = nested(block, "markers", "exceedance_segments")
    if not isinstance(segments, list):
        return []
    rows = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = as_float(segment.get("start_load_N"))
        end = as_float(segment.get("end_load_N"))
        if start is None or end is None:
            continue
        start, end = sorted((start, end))
        if lower is not None and upper is not None:
            lo, hi = sorted((lower, upper))
            start = max(start, lo)
            end = min(end, hi)
            if start > end:
                continue
        rows.append(
            {
                "start_load_N": start,
                "end_load_N": end,
                "y1": 0.0,
                "y2": max_y * 1.08,
                "segment_classification": segment.get("segment_classification", ""),
            }
        )
    return rows
