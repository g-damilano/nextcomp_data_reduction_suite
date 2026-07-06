from __future__ import annotations

from typing import Any


def stress_strain_family_spec(
    curve_rows: list[dict[str, Any]],
    *,
    x_field: str = "strain_mm_per_mm",
    y_field: str = "stress_MPa",
    group_field: str = "run_id",
) -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 360,
        "params": [_run_selector_param(group_field)],
        "data": {"values": curve_rows},
        "mark": {"type": "line", "clip": True},
        "encoding": {
            "x": {"field": x_field, "type": "quantitative", "title": "Mean strain"},
            "y": {"field": y_field, "type": "quantitative", "title": "Stress / MPa"},
            "color": {"field": group_field, "type": "nominal", "title": "Run"},
            "opacity": _run_selector_opacity(),
            "tooltip": [
                {"field": group_field, "type": "nominal", "title": "Run"},
                {"field": x_field, "type": "quantitative", "title": "Mean strain", "format": ".5f"},
                {"field": y_field, "type": "quantitative", "title": "Stress / MPa", "format": ".3f"},
                {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
            ],
        },
        "config": _plot_config(),
    }


def modulus_window_spec(curve_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 280,
        "layer": [
            {
                "data": {"values": curve_rows},
                "mark": {"type": "line", "clip": True},
                "encoding": {
                    "x": {"field": "strain_mm_per_mm", "type": "quantitative", "title": "Mean strain"},
                    "y": {"field": "stress_MPa", "type": "quantitative", "title": "Stress / MPa"},
                    "color": {"field": "run_id", "type": "nominal"},
                },
            },
            {
                "data": {"values": [{"x": 0.0005}, {"x": 0.0025}]},
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#a64222"},
                "encoding": {"x": {"field": "x", "type": "quantitative"}},
            },
        ],
    }


def bending_spec(curve_rows: list[dict[str, Any]], *, threshold_percent: float = 10.0) -> dict[str, Any]:
    rows = []
    for row in curve_rows:
        front = row.get("front_strain_abs") or row.get("front_strain")
        rear = row.get("rear_strain_abs") or row.get("rear_strain")
        if front in (None, "") or rear in (None, ""):
            continue
        front = abs(float(front))
        rear = abs(float(rear))
        denominator = abs(front + rear)
        if denominator == 0:
            continue
        rows.append(
            {
                "run_id": row.get("run_id"),
                "load_N": row.get("load_N"),
                "bending_percent": abs(front - rear) / denominator * 100.0,
                "exceeds_threshold": abs(front - rear) / denominator * 100.0 > threshold_percent,
            }
        )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 280,
        "params": [_run_selector_param("run_id")],
        "layer": [
            {
                "data": {"values": rows},
                "mark": {"type": "line", "clip": True},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative", "title": "Load / N"},
                    "y": {"field": "bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "color": {"field": "run_id", "type": "nominal"},
                    "opacity": _run_selector_opacity(selected=0.9, muted=0.12),
                    "tooltip": [
                        {"field": "run_id", "type": "nominal", "title": "Run"},
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                    ],
                },
            },
            {
                "data": {"values": [row for row in rows if row["exceeds_threshold"]]},
                "mark": {"type": "point", "filled": True, "size": 32, "color": "#d9786d"},
                "encoding": {
                    "x": {"field": "load_N", "type": "quantitative"},
                    "y": {"field": "bending_percent", "type": "quantitative"},
                    "opacity": _run_selector_opacity(selected=0.9, muted=0.12),
                    "tooltip": [
                        {"field": "run_id", "type": "nominal", "title": "Run"},
                        {"field": "load_N", "type": "quantitative", "title": "Load / N", "format": ".1f"},
                        {"field": "bending_percent", "type": "quantitative", "title": "Bending / %", "format": ".2f"},
                        {"field": "exceeds_threshold", "type": "nominal", "title": "Above threshold"},
                    ],
                },
            },
            {
                "data": {"values": [{"threshold": threshold_percent}]},
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#d9786d"},
                "encoding": {"y": {"field": "threshold", "type": "quantitative"}},
            },
        ],
        "config": _plot_config(),
    }


def _run_selector_param(field: str) -> dict[str, Any]:
    return {
        "name": "run_selector",
        "select": {"type": "point", "fields": [field]},
        "bind": "legend",
    }


def _run_selector_opacity(*, selected: float = 0.85, muted: float = 0.08) -> dict[str, Any]:
    return {"condition": {"param": "run_selector", "value": selected}, "value": muted}


def _plot_config() -> dict[str, Any]:
    return {
        "axis": {"labelFontSize": 11, "titleFontSize": 12},
        "legend": {"labelLimit": 160, "titleFontSize": 12, "labelFontSize": 11},
        "view": {"stroke": "#d7dde5"},
    }
