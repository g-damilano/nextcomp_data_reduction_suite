from __future__ import annotations

import math
from statistics import mean
from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.plots.common import as_float, analysis_progress_percent, curve_shape_color_scale, score_tooltip_fields, stddev
from plotting.vega_lite import finalise_spec, unavailable_result


ANALYSIS_WINDOW_AXIS = "Normalised strain / %"


def build_aggregate_curve_family(request: PlotRequest) -> PlotResult:
    aligned_rows = [
        row
        for row in request.data_payload.get("aligned_rows", [])
        if isinstance(row, dict)
    ]
    fallback_curves = [
        row
        for row in request.data_payload.get("fallback_curves", [])
        if isinstance(row, dict)
    ]
    reference_rows = [
        row
        for row in request.data_payload.get("reference_rows", [])
        if isinstance(row, dict)
    ]
    diagnostic_scores = [
        row
        for row in request.data_payload.get("diagnostic_scores", [])
        if isinstance(row, dict)
    ]
    highlight_run_id = str(request.data_payload.get("highlight_run_id") or "").strip()
    plot_data_freshness = request.data_payload.get("plot_data_freshness")
    plot_data_freshness = dict(plot_data_freshness) if isinstance(plot_data_freshness, dict) else {}
    if not aligned_rows and not fallback_curves:
        return unavailable_result(request, "Plot unavailable: missing aligned or bounded curve-family evidence.")

    curves, stats = _aggregate_curve_values(aligned_rows, fallback_curves, diagnostic_scores)
    if not curves:
        return unavailable_result(request, "Plot unavailable: curve-family rows contain no plottable stress values.")

    reference = [
        {
            "x": _analysis_window_x_value(row),
            "stress": as_float(row.get("y_reference")),
            "series": "mean or median curve",
            "std_lower": as_float(row.get("y_lower")),
            "std_upper": as_float(row.get("y_upper")),
            "n": row.get("support_n", ""),
        }
        for row in reference_rows
        if as_float(row.get("y_reference")) is not None and _analysis_window_x_value(row) is not None
    ]
    band = [
        {
            "x": row["x"],
            "std_lower": row.get("std_lower", row.get("stress")),
            "std_upper": row.get("std_upper", row.get("stress")),
            "n": row.get("n", ""),
        }
        for row in reference
    ] or stats
    threshold_method = _threshold_method(diagnostic_scores)
    mad_available = threshold_method == "robust_mad_zscore" and any(_mad_upper_score(row) is not None for row in curves)
    rank_available = threshold_method == "dixon_high_outlier_q_test" and any(
        as_float(row.get("distance_rank_number")) is not None for row in curves
    )
    classification_values = _present_classifications(curves)
    color_encoding = _curve_color_encoding(
        curves,
        rank_available=rank_available,
        mad_available=mad_available,
        classification_values=classification_values,
    )
    stress_scale = _stress_scale(curves, reference or stats, band)
    highlight_values = _focused_run_values(curves, highlight_run_id)
    endpoint_labels = _endpoint_labels(curves)
    semantic_layers = ["all_evaluable_curves"]
    if reference or stats:
        semantic_layers.append("reference_curve")
    if band:
        semantic_layers.append("variability_band")
    if mad_available:
        semantic_layers.append("mad_zscore_coloring")
    if rank_available:
        semantic_layers.append("dixon_rank_coloring")
    if endpoint_labels:
        semantic_layers.append("run_endpoint_labels")
    if highlight_values:
        semantic_layers.append("focused_run_curve")
    if any(str(row.get("diagnostic_classification") or "") == "CURVE_SHAPE_OUTLIER" for row in curves):
        semantic_layers.append("outlier_candidate_curves")
    if any(str(row.get("diagnostic_classification") or "").startswith("INSUFFICIENT") for row in diagnostic_scores):
        semantic_layers.append("insufficient_data_summary")

    layers: list[dict[str, Any]] = []
    if band:
        layers.append(
            {
                "name": "cohort variability band",
                "data": {"values": band},
                "mark": {"type": "area", "opacity": 0.12, "color": "#8fb9d6"},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS},
                    "y": {"field": "std_lower", "type": "quantitative", "title": "Stress / MPa", "scale": stress_scale},
                    "y2": {"field": "std_upper"},
                    "tooltip": [{"field": "n", "type": "quantitative", "title": "Observation count"}],
                },
            }
        )
    curve_encoding = _aggregate_curve_encoding(
        detail=True,
        color_encoding=color_encoding,
        stress_scale=stress_scale,
        threshold_method=threshold_method,
    )
    if mad_available:
        curve_layer_name = "all evaluable curves by upper-tail MAD score"
    elif rank_available:
        curve_layer_name = "all evaluable curves by Dixon rank"
    else:
        curve_layer_name = "all evaluable curves"
    curve_layer: dict[str, Any] = {
        "name": curve_layer_name,
        "data": {"values": curves},
        "mark": {"type": "line", "strokeWidth": 1.35, "opacity": 0.62},
        "encoding": curve_encoding,
    }
    if not color_encoding:
        curve_layer["mark"]["color"] = "#78aeda"
    layers.append(curve_layer)
    if highlight_values:
        layers.append(
            {
                "name": "focused run curve",
                "data": {"values": highlight_values},
                "mark": {"type": "line", "strokeWidth": 4.0, "opacity": 1.0, "color": "#c83f49"},
                "encoding": _aggregate_curve_encoding(
                    detail=True,
                    stress_scale=stress_scale,
                    threshold_method=threshold_method,
                ),
            }
        )
    layers.append(
        {
            "name": "mean or median curve",
            "data": {"values": reference or stats},
            "mark": {"type": "line", "strokeWidth": 3, "color": "#142f43", "strokeDash": [5, 3]},
            "encoding": {
                "x": {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS},
                "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "scale": stress_scale},
                "tooltip": [
                    {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS, "format": ".2f"},
                    {"field": "stress", "type": "quantitative", "title": "Reference stress / MPa", "format": ".2f"},
                ],
            },
        }
    )
    if endpoint_labels:
        layers.append(
            {
                "name": "run endpoint labels",
                "data": {"values": endpoint_labels},
                "mark": {"type": "text", "align": "right", "baseline": "middle", "dx": -4, "fontSize": 10, "color": "#253746"},
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS},
                    "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "scale": stress_scale},
                    "text": {"field": "run_label"},
                    "tooltip": _endpoint_tooltip(mad_available=mad_available),
                },
            }
        )

    spec = {
        "description": "aggregate_curve_family: all evaluable curves, cohort reference curve, variability band, and curve-shape diagnostic rank/state context",
        "height": 320,
        "usermeta": {
            "semantic_layers": semantic_layers,
            "plotting_module": "plotting",
            "plot_data_freshness": plot_data_freshness
            or _default_plot_data_freshness(aligned_rows, fallback_curves, curves),
            "focused_run_id": highlight_run_id,
            "caption": _aggregate_caption(
                curves,
                classification_values=classification_values,
                rank_available=rank_available,
                mad_available=mad_available,
                endpoint_labels=endpoint_labels,
            ),
        },
        "layer": layers,
    }
    return finalise_spec(spec, request, _contracts())


def _contracts() -> list[PlotLayerContract]:
    return [
        PlotLayerContract("all_evaluable_curves", "all evaluable curves", required=True),
        PlotLayerContract("reference_curve", "cohort reference curve", required=False),
        PlotLayerContract("variability_band", "cohort variability band", required=False),
        PlotLayerContract("mad_zscore_coloring", "upper-tail MAD score color encoding", required=False),
        PlotLayerContract("dixon_rank_coloring", "Dixon rank color encoding", required=False),
        PlotLayerContract("run_endpoint_labels", "run endpoint labels", required=False),
        PlotLayerContract("focused_run_curve", "recoloured curve under acceptance review", required=False),
        PlotLayerContract("outlier_candidate_curves", "curve-shape outlier candidates", required=False),
        PlotLayerContract("insufficient_data_summary", "insufficient data summary", required=False),
    ]


def _aggregate_curve_values(
    aligned_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]],
    diagnostic_scores: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    classification_by_run = {
        str(row.get("run_id") or ""): str(row.get("diagnostic_classification") or "CURVE_SHAPE_NOT_ASSESSED")
        for row in diagnostic_scores
        if isinstance(row, dict)
    }
    curves = []
    grouped: dict[float, list[float]] = {}
    if aligned_rows:
        for row in aligned_rows:
            run_id = str(row.get("run_id") or "")
            stress = as_float(row.get("y_observed", row.get("y_aligned")))
            x_value = _analysis_window_x_value(row)
            if stress is None or x_value is None or x_value < -1e-9 or x_value > 100.0 + 1e-9:
                continue
            score_fields = score_tooltip_fields(diagnostic_scores, run_id)
            distance_rank = as_float(score_fields.get("distance_rank"))
            curves.append(
                {
                    "x": x_value,
                    "stress": stress,
                    "run_id": run_id,
                    "run_label": _run_label(run_id),
                    "distance_rank_number": distance_rank,
                    "diagnostic_classification": classification_by_run.get(run_id, "CURVE_SHAPE_NOT_ASSESSED"),
                    **score_fields,
                }
            )
            grouped.setdefault(round(float(x_value), 8), []).append(stress)
    else:
        for row in fallback_curves:
            run_id = str(row.get("run_id") or "")
            stress = as_float(row.get("stress_MPa"))
            x_value = _fallback_x_value(row)
            if x_value is None or stress is None:
                continue
            score_fields = score_tooltip_fields(diagnostic_scores, run_id)
            distance_rank = as_float(score_fields.get("distance_rank"))
            curves.append(
                {
                    "x": x_value,
                    "stress": stress,
                    "run_id": run_id,
                    "run_label": _run_label(run_id),
                    "distance_rank_number": distance_rank,
                    "diagnostic_classification": classification_by_run.get(run_id, "CURVE_SHAPE_NOT_ASSESSED"),
                    **score_fields,
                }
            )
            grouped.setdefault(round(float(x_value), 8), []).append(stress)
    stats = []
    for x_value, stresses in sorted(grouped.items()):
        avg = mean(stresses)
        sd = stddev(stresses)
        stats.append(
            {
                "x": x_value,
                "stress": avg,
                "std_lower": avg - sd,
                "std_upper": avg + sd,
                "n": len(stresses),
            }
        )
    return curves, stats


def _focused_run_values(curves: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    if not run_id:
        return []
    return [dict(row) for row in curves if str(row.get("run_id") or "") == run_id]


def _fallback_x_value(row: dict[str, Any]) -> float | None:
    boundary_progress = _boundary_progress_percent(row)
    if boundary_progress is not None:
        return boundary_progress
    progress = _first_float(row, "analysis_progress", "experiment_progress", "x_common", "x_normalized")
    if progress is not None:
        x_value = progress * 100.0 if progress <= 1.5 else progress
        if -1e-9 <= x_value <= 100.0 + 1e-9:
            return max(0.0, min(100.0, x_value))
        return None
    point_index = as_float(row.get("point_index"))
    start_index = as_float(row.get("boundary_start_index"))
    end_index = as_float(row.get("boundary_end_index"))
    if point_index is not None and start_index is not None and end_index not in (None, start_index):
        x_value = (point_index - start_index) / (end_index - start_index) * 100.0
        if -1e-9 <= x_value <= 100.0 + 1e-9:
            return max(0.0, min(100.0, x_value))
        return None
    return None


def _analysis_window_x_value(row: dict[str, Any]) -> float | None:
    boundary_progress = _boundary_progress_percent(row)
    if boundary_progress is not None:
        return boundary_progress
    return analysis_progress_percent(row)


def _boundary_progress_percent(row: dict[str, Any]) -> float | None:
    point_index = as_float(row.get("point_index"))
    start_index = as_float(row.get("boundary_start_index"))
    end_index = as_float(row.get("boundary_end_index"))
    if point_index is None or start_index is None or end_index in (None, start_index):
        return None
    x_value = (point_index - start_index) / (end_index - start_index) * 100.0
    if -1e-9 <= x_value <= 100.0 + 1e-9:
        return max(0.0, min(100.0, x_value))
    return None


def _first_float(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def _default_plot_data_freshness(
    aligned_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]],
    curves: list[dict[str, Any]],
) -> dict[str, Any]:
    source = "aligned_rows" if aligned_rows else "bounded_curve_family" if fallback_curves else "none"
    x_values = [as_float(row.get("x")) for row in curves]
    leaks = [value for value in x_values if value is not None and (value < -1e-9 or value > 100.0 + 1e-9)]
    return {
        "schema_id": "report.plot_data_freshness.v0_1",
        "status": "stale" if leaks else "current",
        "replicate_source": source,
        "bounded_replicates": source == "bounded_curve_family"
        or any(row.get("curve_scope") in {"bounded", "boundary_aligned"} for row in aligned_rows),
        "boundary_aligned_replicates": bool(aligned_rows),
        "boundary_aligned_aggregation": bool(aligned_rows),
        "alignment_domain": "experiment_progress",
        "source_boundaries": "method_resolve.experiment_boundaries",
        "reasons": ["Aggregate curve-family plot contains x values outside the resolved analysis window."] if leaks else [],
    }


def _threshold_method(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        value = str(row.get("threshold_method") or "").strip()
        if value and value != "not_assessed":
            return value
    return ""


def _aggregate_curve_encoding(
    *,
    detail: bool = False,
    color_encoding: dict[str, Any] | None = None,
    stress_scale: dict[str, Any] | None = None,
    threshold_method: str = "",
) -> dict[str, Any]:
    branch_tooltips: list[dict[str, Any]]
    if threshold_method == "robust_mad_zscore":
        branch_tooltips = [
            {"field": "mad_upper_z", "type": "quantitative", "title": "Upper-tail MAD score", "format": ".3f"},
            {"field": "robust_z", "type": "quantitative", "title": "Signed MAD z-score (z_mad)", "format": ".3f"},
            {"field": "threshold_value", "type": "quantitative", "title": "Upper-tail MAD cutoff (z_crit)", "format": ".3f"},
        ]
    else:
        branch_tooltips = [
            {"field": "Qexp", "type": "nominal", "title": "Observed Dixon Q (Qexp)"},
            {"field": "Qcrit_95", "type": "nominal", "title": "Critical Q at 95% (Qcrit_95)"},
        ]
    encoding: dict[str, Any] = {
        "x": {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS},
        "y": {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "scale": stress_scale or {}},
        "order": {"field": "x", "type": "quantitative"},
        "tooltip": [
            {"field": "run_label", "type": "nominal", "title": "Run"},
            {"field": "specimen", "type": "nominal", "title": "Specimen"},
            {"field": "x", "type": "quantitative", "title": ANALYSIS_WINDOW_AXIS, "format": ".2f"},
            {"field": "stress", "type": "quantitative", "title": "Stress / MPa", "format": ".2f"},
            {"field": "distance_rms", "type": "quantitative", "title": "Curve difference score (distance_rms)", "format": ".4f"},
            {"field": "distance_rank", "type": "nominal", "title": "Distance rank"},
            *branch_tooltips,
            {"field": "threshold_method", "type": "nominal", "title": "Threshold method"},
            {"field": "diagnostic_classification", "type": "nominal", "title": "Classification"},
        ],
    }
    if color_encoding:
        encoding["color"] = color_encoding
    if detail:
        encoding["detail"] = {"field": "run_id"}
    return encoding


def _curve_color_encoding(
    curves: list[dict[str, Any]],
    *,
    rank_available: bool,
    mad_available: bool,
    classification_values: list[str],
) -> dict[str, Any] | None:
    if mad_available:
        scores = [_mad_upper_score(row) for row in curves]
        score_values = [score for score in scores if score is not None]
        threshold = _first_numeric(curves, "threshold_value")
        upper = max(score_values + ([threshold] if threshold is not None else []) or [1.0])
        middle = threshold if threshold is not None and 0 < threshold < upper else upper / 2.0
        return {
            "field": "mad_upper_z",
            "type": "quantitative",
            "title": "Upper-tail MAD score",
            "scale": {
                "domain": [0, middle, upper],
                "range": ["#d7e8f6", "#1f5d8f", "#c83f49"],
            },
            "legend": {"format": ".2f"},
        }
    if rank_available:
        ranks = [as_float(row.get("distance_rank_number")) for row in curves]
        rank_values = [rank for rank in ranks if rank is not None]
        rank_max = max(rank_values) if rank_values else 1.0
        return {
            "field": "distance_rank_number",
            "type": "quantitative",
            "title": "Dixon rank (1 = most distant)",
            "scale": {"domain": [1, rank_max], "range": ["#1f5d8f", "#d7e8f6"]},
            "legend": {"format": ".0f"},
        }
    if len(classification_values) > 1:
        scale = curve_shape_color_scale()
        palette = dict(zip(scale["domain"], scale["range"], strict=False))
        return {
            "field": "diagnostic_classification",
            "type": "nominal",
            "title": "Curve-shape state",
            "scale": {
                "domain": classification_values,
                "range": [palette.get(value, "#78aeda") for value in classification_values],
            },
        }
    return None


def _first_numeric(rows: list[dict[str, Any]], key: str) -> float | None:
    for row in rows:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def _mad_upper_score(row: dict[str, Any]) -> float | None:
    value = as_float(row.get("mad_upper_z"))
    if value is None:
        value = as_float(row.get("z_mad_upper"))
    if value is not None:
        return max(0.0, value)
    signed = as_float(row.get("robust_z", row.get("z_mad")))
    return max(0.0, signed) if signed is not None else None


def _present_classifications(curves: list[dict[str, Any]]) -> list[str]:
    values = []
    for row in curves:
        value = str(row.get("diagnostic_classification") or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _endpoint_tooltip(*, mad_available: bool) -> list[dict[str, Any]]:
    tooltip: list[dict[str, Any]] = [{"field": "run_id", "type": "nominal", "title": "Run"}]
    if mad_available:
        tooltip.append({"field": "mad_upper_z", "type": "quantitative", "title": "Upper-tail MAD score", "format": ".3f"})
        tooltip.append({"field": "robust_z", "type": "quantitative", "title": "Signed MAD z-score (z_mad)", "format": ".3f"})
    else:
        tooltip.append({"field": "distance_rank", "type": "nominal", "title": "Dixon rank"})
    return tooltip


def _endpoint_labels(curves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in curves:
        run_id = str(row.get("run_id") or "")
        x_value = as_float(row.get("x"))
        stress = as_float(row.get("stress"))
        if not run_id or x_value is None or stress is None:
            continue
        existing = grouped.get(run_id)
        if existing is None or (as_float(existing.get("x")) or -math.inf) <= x_value:
            grouped[run_id] = dict(row)
    rows = list(grouped.values())
    if len(rows) <= 12:
        return rows
    important = [
        row
        for row in rows
        if as_float(row.get("distance_rank_number")) == 1
        or str(row.get("diagnostic_classification") or "") == "CURVE_SHAPE_OUTLIER"
    ]
    return important[:6]


def _stress_scale(*row_groups: list[dict[str, Any]]) -> dict[str, Any]:
    values: list[float] = []
    actual_stresses: list[float] = []
    for rows in row_groups:
        for row in rows:
            for key in ("stress", "std_lower", "std_upper"):
                value = as_float(row.get(key))
                if value is not None:
                    values.append(value)
                    if key == "stress":
                        actual_stresses.append(value)
    if not values:
        return {}
    lower = min(actual_stresses or values)
    upper = max(values)
    if lower >= 0:
        floor_value = 0.0
    else:
        floor_value = math.floor(lower / 50.0) * 50.0
    ceiling = math.ceil(upper / 50.0) * 50.0
    if ceiling <= floor_value:
        ceiling = floor_value + 50.0
    return {"domain": [floor_value, ceiling], "nice": False}


def _aggregate_caption(
    curves: list[dict[str, Any]],
    *,
    classification_values: list[str],
    rank_available: bool,
    mad_available: bool,
    endpoint_labels: list[dict[str, Any]],
) -> str:
    run_count = len({str(row.get("run_id") or "") for row in curves if row.get("run_id")})
    pieces = ["The x-axis is strain normalised to each run's resolved experimental window."]
    if len(classification_values) == 1:
        pieces.append(f"All {run_count} curves classified {_human_classification(classification_values[0])}.")
    if mad_available:
        pieces.append(
            "Curve colour encodes the upper-tail MAD score from the cohort median; only unusually high curve-difference scores are outlier evidence."
        )
    if rank_available:
        pieces.append("Curve colour encodes Dixon distance rank; rank 1 is the most distant curve.")
    if endpoint_labels and run_count <= 12:
        pieces.append("Run labels are shown at curve endpoints.")
    pieces.append("The shaded band is the stored cohort reference variability envelope; the dashed dark line is the reference curve.")
    return " ".join(pieces)


def _human_classification(value: str) -> str:
    return {
        "CURVE_SHAPE_NORMAL": "Matches cohort",
        "CURVE_SHAPE_OUTLIER": "Curve-shape outlier",
        "INSUFFICIENT_CURVE_DATA": "Insufficient curve data",
        "INSUFFICIENT_COHORT_SIZE": "Insufficient cohort size",
        "CURVE_SHAPE_NOT_ASSESSED": "Not assessed",
    }.get(value, value.replace("_", " ").title())


def _run_label(run_id: str) -> str:
    text = str(run_id or "")
    if text.startswith("run_"):
        suffix = text[4:]
        if suffix.isdigit():
            return f"#{int(suffix)}"
    return text
