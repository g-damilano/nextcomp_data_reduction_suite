from __future__ import annotations

import math
from statistics import mean
from typing import Any

from plotting.layout import downsample


def as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def nested(payload: Any, *keys: str) -> Any:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def x_common_percent(row: dict[str, Any]) -> float | None:
    value = as_float(row.get("x_common"))
    if value is None:
        return None
    return value * 100.0 if value <= 1.5 else value


def analysis_progress_percent(row: dict[str, Any]) -> float | None:
    for key in ("analysis_progress_percent", "analysis_window_progress_percent"):
        value = as_float(row.get(key))
        if value is not None:
            return value
    for key in ("analysis_progress", "experiment_progress", "x_common", "x_normalized"):
        value = as_float(row.get(key))
        if value is not None:
            return value * 100.0 if value <= 1.5 else value
    return None


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def curve_shape_color_scale() -> dict[str, Any]:
    return {
        "domain": [
            "CURVE_SHAPE_NORMAL",
            "CURVE_SHAPE_OUTLIER",
            "INSUFFICIENT_CURVE_DATA",
            "INSUFFICIENT_COHORT_SIZE",
            "CURVE_SHAPE_NOT_ASSESSED",
        ],
        "range": ["#78aeda", "#c83f49", "#8a6500", "#9a7fd1", "#7d8794"],
    }


def bending_pattern_palette() -> dict[str, str]:
    return {
        "PASS": "#74b88b",
        "PASS_WITH_SPIKES": "#74b88b",
        "WARN": "#e6b45a",
        "WARN_TRANSIENT_BENDING": "#e6b45a",
        "FAIL": "#d9786d",
        "FAIL_SUSTAINED_BENDING": "#d9786d",
    }


def bending_pattern_color_scale() -> dict[str, Any]:
    palette = bending_pattern_palette()
    return {
        "domain": ["PASS", "PASS_WITH_SPIKES", "WARN", "WARN_TRANSIENT_BENDING", "FAIL", "FAIL_SUSTAINED_BENDING"],
        "range": [
            palette["PASS"],
            palette["PASS_WITH_SPIKES"],
            palette["WARN"],
            palette["WARN_TRANSIENT_BENDING"],
            palette["FAIL"],
            palette["FAIL_SUSTAINED_BENDING"],
        ],
    }


def score_tooltip_fields(scores: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    for row in scores:
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id:
            return {
                "specimen": row.get("specimen", ""),
                "distance_rms": row.get("distance_rms", ""),
                "distance_rank": row.get("distance_rank", ""),
                "Qexp": row.get("Qexp", ""),
                "Qcrit_95": row.get("Qcrit_95", ""),
                "robust_z": row.get("robust_z", row.get("z_mad", "")),
                "z_mad": row.get("z_mad", row.get("robust_z", "")),
                "mad_upper_z": row.get("mad_upper_z", row.get("z_mad_upper", "")),
                "z_mad_upper": row.get("z_mad_upper", row.get("mad_upper_z", "")),
                "threshold_value": row.get("threshold_value", ""),
                "threshold_method": row.get("threshold_method", ""),
                "diagnostic_classification": row.get("diagnostic_classification", ""),
            }
    return {}


def strain_percent_bounds(values: list[dict[str, Any]]) -> tuple[float, float] | None:
    strains = [as_float(row.get("strain")) for row in values]
    strains = [strain for strain in strains if strain is not None]
    if not strains:
        return None
    return min(strains), max(strains)


def clip_strain_values(
    values: list[dict[str, Any]],
    bounds: tuple[float, float] | None,
) -> list[dict[str, Any]]:
    if bounds is None:
        return values
    lower, upper = bounds
    clipped = []
    for row in values:
        strain = as_float(row.get("strain"))
        if strain is None or lower - 1e-9 <= strain <= upper + 1e-9:
            clipped.append(row)
    return clipped


def row_at_index(rows: list[dict[str, Any]], point_index: float | None) -> dict[str, Any] | None:
    if point_index is None:
        return None
    for row in rows:
        value = as_float(row.get("point_index"))
        if value is not None and abs(value - point_index) < 0.5:
            return row
    return None


def point_encoding(label_field: str) -> dict[str, Any]:
    return {
        "x": {"field": "strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "tooltip": [
            {"field": label_field, "type": "nominal", "title": "Marker"},
            {"field": "strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
        ],
    }


def curve_encoding(*, preserve_point_order: bool = False) -> dict[str, Any]:
    encoding = {
        "x": {"field": "strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "tooltip": [
            {"field": "series", "type": "nominal", "title": "Evidence"},
            {"field": "strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "point_index", "type": "quantitative", "title": "Point index"},
        ],
    }
    if preserve_point_order:
        encoding["order"] = {"field": "point_index", "type": "quantitative"}
    return encoding


def strain_trace_color_encoding() -> dict[str, Any]:
    return {
        "field": "series",
        "type": "nominal",
        "title": "Strain traces",
        "scale": {
            "domain": ["average strain curve", "front strain", "rear strain"],
            "range": ["#1f78b4", "#8aa8c4", "#b1bfd0"],
        },
    }


def average_curve_encoding() -> dict[str, Any]:
    encoding = curve_encoding(preserve_point_order=True)
    encoding["color"] = strain_trace_color_encoding()
    return encoding


def gauge_trace_encoding() -> dict[str, Any]:
    return {
        "x": {"field": "gauge_strain", "type": "quantitative", "title": "Strain / %"},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa"},
        "order": {"field": "point_index", "type": "quantitative"},
        "color": strain_trace_color_encoding(),
        "tooltip": [
            {"field": "series", "type": "nominal", "title": "Evidence"},
            {"field": "gauge_strain", "type": "quantitative", "title": "Strain / %", "format": ".4f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "point_index", "type": "quantitative", "title": "Point index"},
        ],
    }


def downsample_rows(rows: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    return downsample(rows, max_rows)
