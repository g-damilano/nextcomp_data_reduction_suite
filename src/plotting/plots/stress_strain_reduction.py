from __future__ import annotations

from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.plots.common import (
    as_float,
    average_curve_encoding,
    curve_encoding,
    gauge_trace_encoding,
    nested,
    point_encoding,
    row_at_index,
)
from plotting.vega_lite import finalise_spec, unavailable_result


START_MARKER_LABEL = "start marker"
END_MARKER_LABEL = "end marker"
MAX_FAILURE_MARKER_LABEL = "max point / failure strain"
END_MAX_FAILURE_MARKER_LABEL = "end marker (max point / failure strain)"


def build_stress_strain_reduction(request: PlotRequest) -> PlotResult:
    rows = [
        row
        for row in request.data_payload.get("bounded_rows", [])
        if isinstance(row, dict)
    ]
    post_peak_rows = [
        row
        for row in request.data_payload.get("post_peak_rows", [])
        if isinstance(row, dict)
    ]
    if not rows:
        return unavailable_result(request, "Plot unavailable: missing bounded stress-strain curve evidence.")

    block = request.data_payload.get("block") if isinstance(request.data_payload.get("block"), dict) else {}
    bounded_values = _curve_values(rows, "average strain curve")
    if not bounded_values:
        return unavailable_result(request, "Plot unavailable: bounded curve rows contain no strain/stress values.")

    gauge_trace_values = _front_rear_trace_values(rows)
    strain_envelope_values = _strain_envelope_values(rows)
    markers = _stress_markers(block, rows)
    post_peak_values = _curve_values(post_peak_rows, "post-peak audit trace") if post_peak_rows else []
    chord = _chord_line_values(block)

    layers = []
    semantic_layers = ["bounded_analysis_curve", "average_strain_curve"]
    if post_peak_values:
        semantic_layers.append("post_peak_audit_trace")
        layers.append(
            {
                "name": "post-peak audit trace",
                "data": {"values": post_peak_values},
                "mark": {
                    "type": "line",
                    "clip": True,
                    "color": "#8fb3d1",
                    "strokeWidth": 0.85,
                    "opacity": 0.22,
                },
                "encoding": curve_encoding(preserve_point_order=True),
            }
        )
    if strain_envelope_values:
        semantic_layers.append("strain_agreement_envelope")
        layers.append(
            {
                "name": "front rear strain agreement envelope",
                "data": {"values": strain_envelope_values},
                "mark": {"type": "area", "clip": True, "color": "#78aeda", "opacity": 0.16},
                "encoding": {
                    "x": {"field": "strain_min", "type": "quantitative", "title": "Strain / %"},
                    "x2": {"field": "strain_max"},
                    "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
                    "tooltip": [
                        {"field": "series", "type": "nominal", "title": "Evidence"},
                        {"field": "strain_min", "type": "quantitative", "title": "Lower gauge strain / %", "format": ".4f"},
                        {"field": "strain_max", "type": "quantitative", "title": "Upper gauge strain / %", "format": ".4f"},
                        {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
                        {"field": "point_index", "type": "quantitative", "title": "Point index"},
                    ],
                },
            }
        )
    if gauge_trace_values:
        semantic_layers.extend(["front_strain_trace", "rear_strain_trace"])
        layers.append(
            {
                "name": "front rear strain traces",
                "data": {"values": gauge_trace_values},
                "mark": {"type": "line", "clip": True, "strokeWidth": 1.1, "opacity": 0.5},
                "encoding": gauge_trace_encoding(),
            }
        )
    layers.append(
        {
            "name": "bounded curve",
            "data": {"values": bounded_values},
            "mark": {"type": "line", "clip": True, "strokeWidth": 2.4},
            "encoding": average_curve_encoding(),
        }
    )
    layers.extend(
        [
            {
                "name": "chord line",
                "data": {"values": chord},
                "mark": {"type": "line", "strokeWidth": 2, "strokeDash": [6, 4], "color": "#207245"},
                "encoding": curve_encoding(),
            },
            {
                "name": "chord points",
                "data": {"values": [row for row in chord if row.get("stress") is not None]},
                "mark": {"type": "point", "filled": True, "size": 70, "color": "#207245"},
                "encoding": point_encoding("label"),
            },
            {
                "name": "analysis markers",
                "data": {"values": markers},
                "mark": {"type": "point", "filled": True, "size": 82, "color": "#c45f20"},
                "encoding": {
                    **point_encoding("marker"),
                    "shape": {"field": "marker", "type": "nominal", "title": "Analysis markers"},
                },
            },
        ]
    )
    if chord:
        semantic_layers.extend(["modulus_chord_start", "modulus_chord_end", "modulus_chord_line"])
    if markers:
        semantic_layers.extend(["experiment_start_marker", "experiment_end_marker", "max_or_failure_marker"])
    _apply_bounded_axis_domains(layers, [*bounded_values, *markers, *chord])

    spec = {
        "description": "run_stress_strain_reduction: front strain, rear strain, average strain bounded curve, faint post-peak audit trace, strain agreement envelope, analysis markers, chord points, chord line",
        "height": 300,
        "layer": layers,
        "usermeta": {
            "semantic_layers": semantic_layers,
            "plotting_module": "plotting",
            "depiction_policy": {
                "semantic_boundary": "depiction_only",
                "bounded_rows_authority": "request.data_payload.bounded_rows",
                "line_order": "point_index",
                "plot_side_reselection": False,
            },
        },
    }
    return finalise_spec(spec, request, _contracts())


def _apply_bounded_axis_domains(
    layers: list[dict[str, Any]],
    bounded_values: list[dict[str, Any]],
    *,
    x_focus_values: list[dict[str, Any]] | None = None,
) -> None:
    x_source = x_focus_values if x_focus_values else bounded_values
    x_domain = _padded_domain([as_float(row.get("strain")) for row in x_source])
    y_domain = _padded_domain([as_float(row.get("stress")) for row in bounded_values])
    for layer in layers:
        encoding = layer.get("encoding") if isinstance(layer, dict) else None
        if not isinstance(encoding, dict):
            continue
        x = encoding.get("x")
        if isinstance(x, dict) and x.get("field") in {"strain", "gauge_strain", "strain_min"}:
            x["scale"] = {"domain": x_domain, "nice": False}
        y = encoding.get("y")
        if isinstance(y, dict) and y.get("field") == "stress":
            y["scale"] = {"domain": y_domain, "nice": False}


def _padded_domain(values: list[float | None]) -> list[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return [0.0, 1.0]
    lower = min(clean)
    upper = max(clean)
    span = upper - lower
    pad = span * 0.03 if span > 0 else max(abs(upper) * 0.03, 1.0)
    if lower >= 0:
        lower = max(0.0, lower - pad)
    else:
        lower -= pad
    upper += pad
    return [lower, upper]


def _contracts() -> list[PlotLayerContract]:
    return [
        PlotLayerContract("bounded_analysis_curve", "bounded reduced stress-strain curve", required=True),
        PlotLayerContract("front_strain_trace", "front gauge strain trace", required=False),
        PlotLayerContract("rear_strain_trace", "rear gauge strain trace", required=False),
        PlotLayerContract("strain_agreement_envelope", "front/rear strain agreement envelope", required=False),
        PlotLayerContract("post_peak_audit_trace", "faint post-peak stress-strain audit continuation", required=False),
        PlotLayerContract("average_strain_curve", "average strain reduction curve", required=True),
        PlotLayerContract("experiment_start_marker", "resolved experiment start marker", required=False),
        PlotLayerContract("experiment_end_marker", "resolved experiment end marker", required=False),
        PlotLayerContract("max_or_failure_marker", "maximum stress / failure strain marker", required=False),
        PlotLayerContract("modulus_chord_start", "modulus chord start anchor", required=False),
        PlotLayerContract("modulus_chord_end", "modulus chord end anchor", required=False),
        PlotLayerContract("modulus_chord_line", "modulus chord line", required=False),
    ]


def _curve_values(rows: list[dict[str, Any]], series: str) -> list[dict[str, Any]]:
    values = []
    for row in rows:
        strain = _first_numeric(row, "mean_strain", "strain_mm_per_mm")
        stress = as_float(row.get("stress_MPa"))
        if strain is None or stress is None:
            continue
        values.append(
            {
                "strain": strain * 100.0,
                "stress": stress,
                "point_index": as_float(row.get("point_index")),
                "series": series,
            }
        )
    return values


def _front_rear_trace_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for row in rows:
        stress = as_float(row.get("stress_MPa"))
        front = _first_numeric(row, "front_strain_abs", "front_strain")
        rear = _first_numeric(row, "rear_strain_abs", "rear_strain")
        point_index = as_float(row.get("point_index"))
        if stress is None:
            continue
        for series, strain in (("front strain", front), ("rear strain", rear)):
            if strain is None:
                continue
            values.append(
                {
                    "gauge_strain": strain * 100.0,
                    "stress": stress,
                    "point_index": point_index,
                    "series": series,
                }
            )
    return values


def _strain_envelope_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for row in rows:
        stress = as_float(row.get("stress_MPa"))
        front = _first_numeric(row, "front_strain_abs", "front_strain")
        rear = _first_numeric(row, "rear_strain_abs", "rear_strain")
        if stress is None or front is None or rear is None:
            continue
        values.append(
            {
                "strain_min": min(front, rear) * 100.0,
                "strain_max": max(front, rear) * 100.0,
                "stress": stress,
                "point_index": as_float(row.get("point_index")),
                "series": "front/rear strain agreement envelope",
            }
        )
    return values


def _stress_markers(block: dict[str, Any], bounded_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers = block.get("markers") if isinstance(block.get("markers"), dict) else {}
    start_index = as_float(nested(markers, "experiment_start", "index"))
    end_index = as_float(nested(markers, "experiment_end", "index"))
    max_index = as_float(nested(markers, "max_load_strength", "index"))
    start = row_at_index(bounded_rows, start_index) or bounded_rows[0]
    end = row_at_index(bounded_rows, end_index) or bounded_rows[-1]
    max_row = row_at_index(bounded_rows, max_index) or end
    out = []
    marker_specs: list[tuple[str, dict[str, Any], float | None]] = [
        (START_MARKER_LABEL, start, start_index),
    ]
    if _same_index(end_index, max_index):
        marker_specs.append((END_MAX_FAILURE_MARKER_LABEL, max_row or end, max_index if max_index is not None else end_index))
    else:
        marker_specs.extend(
            [
                (END_MARKER_LABEL, end, end_index),
                (MAX_FAILURE_MARKER_LABEL, max_row, max_index),
            ]
        )
    for label, row, marker_index in marker_specs:
        strain = _first_numeric(row, "mean_strain", "strain_mm_per_mm")
        stress = as_float(row.get("stress_MPa"))
        if stress is None:
            stress = as_float(nested(markers, "max_load_strength", "stress_MPa"))
        if strain is None or stress is None:
            continue
        out.append(
            {
                "marker": label,
                "strain": strain * 100.0,
                "stress": stress,
                "point_index": marker_index if marker_index is not None else as_float(row.get("point_index")),
            }
        )
    return out


def _same_index(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and abs(left - right) <= 1e-9


def _first_numeric(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def _chord_line_values(block: dict[str, Any]) -> list[dict[str, Any]]:
    line = nested(block, "markers", "chord_line") or {}
    points = [
        ("chord start 0.0005", as_float(line.get("x_start")), as_float(line.get("y_start"))),
        ("chord end 0.0025", as_float(line.get("x_end")), as_float(line.get("y_end"))),
    ]
    return [
        {"label": label, "strain": x * 100.0, "stress": y, "series": "chord line"}
        for label, x, y in points
        if x is not None and y is not None
    ]
