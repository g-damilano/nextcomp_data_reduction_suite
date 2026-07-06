from __future__ import annotations

import json
import os
from typing import Any

from markupsafe import Markup

from html_renderer.context_models import ExportVegaHtmlContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_export_vega_html


def aggregate_stress_strain_spec(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = []
    replicate_values = []
    for row in rows:
        try:
            x_raw = row.get("analysis_progress", row.get("experiment_progress", row.get("x_normalized", 0.0)))
            x_value = float(x_raw) * 100.0
            mean = float(row.get("mean", 0.0))
            std = float(row.get("std", 0.0))
            min_value = float(row.get("min", mean))
            max_value = float(row.get("max", mean))
            n = int(float(row.get("n", 0)))
        except (TypeError, ValueError):
            continue
        values.append(
            {
                "analysis_progress_percent": x_value,
                "mean": mean,
                "std_low": mean - std,
                "std_high": mean + std,
                "min": min_value,
                "max": max_value,
                "n": n,
            }
        )
        for key, value in row.items():
            if key.endswith("_stress_MPa") and key != "stress_MPa":
                try:
                    replicate_values.append(
                        {
                            "analysis_progress_percent": x_value,
                            "stress_MPa": float(value),
                            "run_id": key.removesuffix("_stress_MPa"),
                        }
                    )
                except (TypeError, ValueError):
                    continue
    marker_values = _failure_markers(values)
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Stress-strain aggregation",
        "description": "Production export evidence for individual replicates, aggregate mean, range envelope, mean +/- 1 sigma band, observation count, and characteristic failure marker.",
        "datasets": {
            "aggregate": values,
            "replicates": replicate_values,
            "markers": marker_values,
        },
        "hconcat": [
            {
                "title": "Individual replicates",
                "width": 420,
                "height": 320,
                "data": {"name": "replicates"},
                "mark": {"type": "line", "opacity": 0.24, "strokeWidth": 1.4, "color": "#78aeda"},
                "encoding": {**_xy_encoding("stress_MPa"), "detail": {"field": "run_id"}},
            },
            {
                "title": "Mean curve with variability",
                "width": 460,
                "height": 320,
                "layer": [
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "area", "opacity": 0.16, "color": "#6baed6"},
                        "encoding": {**_xy_encoding("min"), "y2": {"field": "max"}},
                    },
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "area", "opacity": 0.28, "color": "#3182bd"},
                        "encoding": {**_xy_encoding("std_low"), "y2": {"field": "std_high"}},
                    },
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "line", "strokeWidth": 3, "color": "#08519c"},
                        "encoding": {
                            **_xy_encoding("mean"),
                            "tooltip": [
                                {"field": "analysis_progress_percent", "type": "quantitative", "title": "Normalised strain / %"},
                                {"field": "mean", "type": "quantitative", "title": "Mean stress / MPa"},
                                {"field": "n", "type": "quantitative", "title": "Observations"},
                            ],
                        },
                    },
                    {
                        "data": {"name": "markers"},
                        "mark": {"type": "point", "filled": True, "size": 110, "color": "#d95f5f"},
                        "encoding": {
                            **_xy_encoding("stress_MPa"),
                            "tooltip": [
                                {"field": "label", "type": "nominal", "title": "Marker"},
                                {"field": "stress_MPa", "type": "quantitative", "title": "Stress / MPa"},
                            ],
                        },
                    },
                    {
                        "data": {"name": "markers"},
                        "mark": {"type": "text", "dy": -12, "fontSize": 11, "color": "#9b2f2f"},
                        "encoding": {
                            "x": {"field": "analysis_progress_percent", "type": "quantitative"},
                            "y": {"field": "stress_MPa", "type": "quantitative"},
                            "text": {"field": "label"},
                        },
                    },
                ],
            },
        ],
        "resolve": {"scale": {"y": "shared"}},
        "config": {
            "axis": {"labelFontSize": 11, "titleFontSize": 12},
            "title": {"fontSize": 15},
            "view": {"stroke": "#d7dde5"},
        },
    }


def vega_html(spec: dict[str, Any], *, title: str) -> bytes:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_vega_html(spec, title=title)
    return render_export_vega_html(_export_vega_html_context(spec, title=title)).encode("utf-8")


def _legacy_vega_html(spec: dict[str, Any], *, title: str) -> bytes:
    payload = json.dumps(spec, indent=2, sort_keys=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    .vg-tooltip {{ max-width: 340px !important; white-space: normal !important; overflow-wrap: anywhere !important; pointer-events: none !important; }}
    .vg-tooltip table {{ width: auto !important; table-layout: auto !important; border-collapse: collapse !important; font-size: 12px !important; background: #fff !important; }}
    .vg-tooltip th, .vg-tooltip td {{ padding: 2px 6px !important; border: 0 !important; white-space: nowrap !important; overflow-wrap: normal !important; }}
  </style>
</head>
<body>
  <main style="max-width: 1120px; margin: 28px auto; font-family: Arial, sans-serif; color: #17202a;">
  <h1>{_escape(title)}</h1>
  <p style="color:#5b6876;">Standalone operator evidence figure exported from the MTDA. The figure preserves individual replicate curves, the aggregate mean, range envelope, mean +/- 1 sigma band, and observation counts for the selected report set. Individual replicates are intentionally subdued so the aggregate evidence remains readable.</p>
  <div id="aggregate-stress-strain"></div>
  </main>
  <script>
    const spec = {payload};
    vegaEmbed('#aggregate-stress-strain', spec, {{actions: true}});
  </script>
</body>
</html>
"""
    return html.encode("utf-8")


def _export_vega_html_context(spec: dict[str, Any], *, title: str) -> ExportVegaHtmlContext:
    payload = json.dumps(spec, indent=2, sort_keys=True)
    return ExportVegaHtmlContext(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_VEGA_HTML,
        title_html=Markup(_escape(title)),
        spec_json=Markup(payload),
    )


def _xy_encoding(y_field: str) -> dict[str, Any]:
    return {
        "x": {"field": "analysis_progress_percent", "type": "quantitative", "title": "Normalised strain / %"},
        "y": {"field": y_field, "type": "quantitative", "title": "Stress / MPa"},
    }


def _failure_markers(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not values:
        return []
    last = values[-1]
    return [
        {
            "analysis_progress_percent": last.get("analysis_progress_percent", 100.0),
            "stress_MPa": last.get("mean", 0.0),
            "label": "mean failure",
        }
    ]


def _escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
