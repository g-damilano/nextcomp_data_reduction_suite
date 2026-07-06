from __future__ import annotations

import math
from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.plots.common import as_float
from plotting.vega_lite import finalise_spec, unavailable_result


def build_curve_shape_distance_ranking(request: PlotRequest) -> PlotResult:
    source_values = [
        row
        for row in request.data_payload.get("scores", [])
        if isinstance(row, dict) and as_float(row.get("distance_rms")) is not None
    ]
    if not source_values:
        return unavailable_result(request, "Plot unavailable: missing curve diagnostic scores.")
    threshold_method = _threshold_method(source_values)
    mad_branch = threshold_method == "robust_mad_zscore" and any(_mad_upper_score(row) is not None for row in source_values)
    companion_branch = (
        threshold_method == "dixon_high_outlier_q_test"
        and any(str(row.get("secondary_threshold_method") or "") == "robust_mad_masking_screen" for row in source_values)
    )
    values = _ranked_values(source_values, threshold_method=threshold_method)

    q_geometry = []
    dixon_rows = [
        row
        for row in values
        if threshold_method == "dixon_high_outlier_q_test"
        and str(row.get("threshold_method") or "") == "dixon_high_outlier_q_test"
    ]
    if dixon_rows:
        q_geometry = _dixon_geometry(dixon_rows)

    semantic_layers = ["mad_upper_tail_score_by_run" if mad_branch else "distance_rms_by_run"]
    if q_geometry:
        semantic_layers.append("dixon_q_test_against_critical_threshold")
        semantic_layers.append("dixon_gap_denominator_geometry")
    if mad_branch:
        semantic_layers.append("mad_upper_tail_threshold")
    if companion_branch:
        semantic_layers.append("mad_masking_companion_screen")
    if any(str(row.get("diagnostic_classification") or "") == "CURVE_SHAPE_OUTLIER" for row in values):
        semantic_layers.append("outlier_candidate_marker")
    if any(str(row.get("diagnostic_classification") or "").startswith("INSUFFICIENT") for row in values):
        semantic_layers.append("insufficient_data_marker")
    semantic_layers.append("threshold_method_annotation")

    run_order = [str(row.get("run_label") or "") for row in values if row.get("run_label")]
    x_encoding = _x_encoding(run_order, mad_branch=mad_branch)
    y_encoding = _y_encoding(values, mad_branch=mad_branch)
    bar_name = "Upper-tail MAD score by run" if mad_branch else "distance_rms by run"
    layers: list[dict[str, Any]] = [
        {
            "name": bar_name,
            "data": {"values": values},
            "mark": {"type": "bar"},
            "encoding": {
                "x": x_encoding,
                "y": y_encoding,
                "color": _bar_color(mad_branch=mad_branch),
                "tooltip": _bar_tooltip(mad_branch=mad_branch, companion_branch=companion_branch),
            },
        }
    ]
    if q_geometry:
        layers.extend(_dixon_geometry_layers(q_geometry, x_encoding, y_encoding))
    if mad_branch:
        layers.extend(_mad_threshold_layers(values, y_encoding))

    spec = {
        "description": _description(mad_branch=mad_branch),
        "height": 330,
        "usermeta": {
            "semantic_layers": semantic_layers,
            "plotting_module": "plotting",
            "caption": _caption(
                q_geometry,
                mad_branch=mad_branch,
                companion_branch=companion_branch,
                mad_threshold=_first_float(values, "threshold_value"),
            ),
        },
        "layer": layers,
    }
    return finalise_spec(spec, request, _contracts())


def _contracts() -> list[PlotLayerContract]:
    return [
        PlotLayerContract("distance_rms_by_run", "distance ranking marks", required=False),
        PlotLayerContract("mad_upper_tail_score_by_run", "upper-tail MAD score ranking marks", required=False),
        PlotLayerContract("mad_upper_tail_threshold", "upper-tail MAD cutoff reference", required=False),
        PlotLayerContract("mad_masking_companion_screen", "small-cohort MAD masking companion evidence", required=False),
        PlotLayerContract("dixon_q_test_against_critical_threshold", "Dixon Q threshold comparison", required=False),
        PlotLayerContract("dixon_gap_denominator_geometry", "Dixon gap and denominator geometry", required=False),
        PlotLayerContract("outlier_candidate_marker", "outlier candidate marker", required=False),
        PlotLayerContract("insufficient_data_marker", "insufficient data marker", required=False),
        PlotLayerContract("threshold_method_annotation", "threshold method annotation", required=False),
    ]


def _ranked_values(values: list[dict[str, Any]], *, threshold_method: str = "") -> list[dict[str, Any]]:
    mad_branch = threshold_method == "robust_mad_zscore"

    def sort_key(row: dict[str, Any]) -> tuple[float, float]:
        if mad_branch:
            z_mad = _mad_upper_score(row)
            distance = as_float(row.get("distance_rms")) or 0.0
            return (-(z_mad if z_mad is not None else -math.inf), -distance)
        rank = as_float(row.get("distance_rank"))
        distance = as_float(row.get("distance_rms")) or 0.0
        return (rank if rank is not None else math.inf, -distance)

    ranked = []
    for index, row in enumerate(sorted(values, key=sort_key), start=1):
        copied = dict(row)
        rank = as_float(copied.get("distance_rank"))
        copied["rank_order"] = rank if rank is not None else index
        copied["run_label"] = _run_label(str(copied.get("run_id") or ""))
        signed_z = _mad_score(copied)
        upper_z = _mad_upper_score(copied)
        if signed_z is not None:
            copied["z_mad"] = signed_z
            copied["robust_z"] = signed_z
        if upper_z is not None:
            copied["mad_upper_z"] = upper_z
            copied["z_mad_upper"] = upper_z
        copied["is_outlier_for_display"] = _truthy(copied.get("is_curve_shape_outlier")) or str(
            copied.get("diagnostic_classification") or ""
        ) == "CURVE_SHAPE_OUTLIER"
        return_rank = int(rank) if rank is not None and abs(rank - int(rank)) < 1e-9 else rank
        copied["distance_rank"] = return_rank if return_rank is not None else copied.get("distance_rank")
        ranked.append(copied)
    return ranked


def _dixon_geometry(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: as_float(row.get("rank_order")) or math.inf)
    if len(ordered) < 2:
        return []
    rank_1 = ordered[0]
    rank_2 = ordered[1]
    d1 = as_float(rank_1.get("distance_rms"))
    d2 = as_float(rank_2.get("distance_rms"))
    fallback_low = ordered[-1]
    denominator_low_run = str(rank_1.get("dixon_denominator_low_run_id") or "")
    denominator_low_row = _row_for_run_id(ordered, denominator_low_run) or fallback_low
    denominator_low_score = as_float(rank_1.get("dixon_denominator_low_score"))
    if denominator_low_score is None:
        denominator_low_score = as_float(denominator_low_row.get("distance_rms"))
    qexp = as_float(rank_1.get("Qexp"))
    qcrit = as_float(rank_1.get("Qcrit_95")) or _first_float(rows, "Qcrit_95")
    if d1 is None or d2 is None or denominator_low_score is None or qexp is None or qcrit is None:
        return []
    gap = as_float(rank_1.get("dixon_gap"))
    gap = d1 - d2 if gap is None else gap
    denominator = as_float(rank_1.get("dixon_denominator"))
    denominator = d1 - denominator_low_score if denominator is None else denominator
    if denominator <= 0:
        return []
    variant = str(rank_1.get("dixon_variant") or "r10")
    decision = "CURVE_SHAPE_OUTLIER" if qexp > qcrit else "CURVE_SHAPE_NORMAL"
    decision_label = "outlier candidate" if qexp > qcrit else "not an outlier"
    comparator = ">" if qexp > qcrit else "<="
    denominator_label = "range" if variant == "r10" else f"{variant} denominator"
    return [
        {
            "rank1_run": rank_1.get("run_label"),
            "rank2_run": rank_2.get("run_label"),
            "denominator_low_run": denominator_low_row.get("run_label"),
            "rank1_score": d1,
            "rank2_score": d2,
            "denominator_low_score": denominator_low_score,
            "gap": gap,
            "denominator": denominator,
            "gap_mid": d2 + gap / 2.0,
            "denominator_mid": denominator_low_score + denominator / 2.0,
            "gap_label": f"gap = {_format_number(gap)}",
            "denominator_label": f"{denominator_label} = {_format_number(denominator)}",
            "q_label": (
                f"Qexp ({variant}) = gap/denominator = {_format_number(gap)} / {_format_number(denominator)} = {_format_number(qexp)}\n"
                f"Qcrit 95% = {_format_number(qcrit)}; {_format_number(qexp)} {comparator} {_format_number(qcrit)} -> {decision_label}"
            ),
            "Qexp": qexp,
            "Qcrit_95": qcrit,
            "dixon_variant": variant,
            "decision": decision,
            "decision_label": decision_label,
        }
    ]


def _dixon_geometry_layers(
    geometry: list[dict[str, Any]],
    x_encoding: dict[str, Any],
    y_encoding: dict[str, Any],
) -> list[dict[str, Any]]:
    bracket_color = "#7a5a00"
    range_color = "#4b5b6a"
    return [
        {
            "name": "Dixon gap vertical bracket",
            "data": {"values": geometry},
            "mark": {"type": "rule", "strokeWidth": 2, "color": bracket_color, "xOffset": 14},
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "rank2_run"),
                "y": _aux_y_encoding(y_encoding, "rank2_score"),
                "y2": {"field": "rank1_score"},
                "tooltip": _dixon_tooltip(),
            },
        },
        {
            "name": "Dixon gap bracket ticks",
            "data": {"values": _gap_tick_rows(geometry)},
            "mark": {"type": "rule", "strokeWidth": 2, "color": bracket_color},
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "x_start"),
                "x2": {"field": "x_end"},
                "y": _aux_y_encoding(y_encoding, "score"),
                "tooltip": [{"field": "label", "type": "nominal", "title": "Dixon geometry"}],
            },
        },
        {
            "name": "Dixon denominator vertical bracket",
            "data": {"values": geometry},
            "mark": {"type": "rule", "strokeWidth": 2, "color": range_color, "xOffset": 14},
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "denominator_low_run"),
                "y": _aux_y_encoding(y_encoding, "denominator_low_score"),
                "y2": {"field": "rank1_score"},
                "tooltip": _dixon_tooltip(),
            },
        },
        {
            "name": "Dixon denominator bracket ticks",
            "data": {"values": _range_tick_rows(geometry)},
            "mark": {"type": "rule", "strokeWidth": 2, "color": range_color},
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "x_start"),
                "x2": {"field": "x_end"},
                "y": _aux_y_encoding(y_encoding, "score"),
                "tooltip": [{"field": "label", "type": "nominal", "title": "Dixon geometry"}],
            },
        },
        {
            "name": "Dixon bracket labels",
            "data": {"values": _bracket_label_rows(geometry)},
            "mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 18, "fontSize": 11, "fontWeight": "bold"},
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "x_label"),
                "y": _aux_y_encoding(y_encoding, "score"),
                "text": {"field": "label"},
                "color": {"field": "color", "type": "nominal", "scale": None, "legend": None},
            },
        },
        {
            "name": "Dixon Q decision annotation",
            "data": {"values": geometry},
            "mark": {
                "type": "text",
                "align": "right",
                "baseline": "top",
                "dx": -4,
                "dy": 8,
                "fontSize": 11,
                "fontWeight": "bold",
                "lineBreak": "\n",
                "lineHeight": 13,
                "color": "#253746",
            },
            "encoding": {
                "x": _aux_x_encoding(x_encoding, "denominator_low_run"),
                "y": _aux_y_encoding(y_encoding, "rank1_score"),
                "text": {"field": "q_label"},
                "tooltip": _dixon_tooltip(),
            },
        },
    ]


def _distance_scale(values: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [as_float(row.get("distance_rms")) for row in values]
    scores = [score for score in scores if score is not None]
    if not scores:
        return {}
    upper = max(scores)
    if upper <= 0:
        return {"domain": [0, 1], "nice": False}
    step = 0.5 if upper <= 2 else 1.0
    ceiling = math.ceil(upper / step) * step
    if ceiling <= upper:
        ceiling += step
    return {"domain": [0, ceiling], "nice": False}


def _x_encoding(run_order: list[str], *, mad_branch: bool = False) -> dict[str, Any]:
    return {
        "field": "run_label",
        "type": "nominal",
        "scale": {"domain": run_order},
        "title": "Run (sorted by upper-tail MAD score)" if mad_branch else "Run (sorted by curve difference rank)",
        "axis": {"labelAngle": -35, "labelOverlap": False, "labelLimit": 80},
    }


def _y_encoding(values: list[dict[str, Any]], *, mad_branch: bool = False) -> dict[str, Any]:
    if mad_branch:
        return {
            "field": "mad_upper_z",
            "type": "quantitative",
            "title": "Upper-tail MAD score",
            "scale": _mad_scale(values),
        }
    return {
        "field": "distance_rms",
        "type": "quantitative",
        "title": "Curve difference score",
        "scale": _distance_scale(values),
    }


def _aux_x_encoding(base: dict[str, Any], field: str) -> dict[str, Any]:
    return {
        "field": field,
        "type": base.get("type", "nominal"),
        "scale": dict(base.get("scale") or {}),
    }


def _aux_y_encoding(base: dict[str, Any], field: str) -> dict[str, Any]:
    return {
        "field": field,
        "type": base.get("type", "quantitative"),
        "scale": dict(base.get("scale") or {}),
    }


def _bar_color(*, mad_branch: bool = False) -> dict[str, Any]:
    if mad_branch:
        return {
            "field": "mad_upper_z",
            "type": "quantitative",
            "title": "Upper-tail MAD score",
            "scale": {"range": ["#d7e8f6", "#1f5d8f"]},
            "legend": {"format": ".2f"},
        }
    return {
        "condition": {
            "test": "datum.is_outlier_for_display === true",
            "value": "#c83f49",
        },
        "value": "#6ea6d3",
    }


def _bar_tooltip(*, mad_branch: bool = False, companion_branch: bool = False) -> list[dict[str, str]]:
    common = [
        {"field": "run_label", "type": "nominal", "title": "Run"},
        {"field": "specimen", "type": "nominal", "title": "Specimen"},
        {"field": "distance_rms", "type": "quantitative", "title": "Curve difference score", "format": ".4f"},
        {"field": "distance_rank", "type": "nominal", "title": "Distance rank"},
    ]
    if mad_branch:
        common.extend(
            [
                {"field": "mad_upper_z", "type": "quantitative", "title": "Upper-tail MAD score", "format": ".3f"},
                {"field": "z_mad", "type": "quantitative", "title": "Signed MAD z-score (z_mad)", "format": ".3f"},
                {"field": "threshold_value", "type": "quantitative", "title": "Upper-tail MAD cutoff (z_crit)", "format": ".3f"},
            ]
        )
    elif companion_branch:
        common.extend(
            [
                {"field": "mad_upper_z", "type": "quantitative", "title": "Companion MAD score", "format": ".3f"},
                {"field": "masking_companion_flag", "type": "nominal", "title": "Companion MAD flag"},
                {"field": "dixon_decision", "type": "nominal", "title": "Dixon decision"},
            ]
        )
    common.append({"field": "diagnostic_classification", "type": "nominal", "title": "Classification"})
    return common


def _mad_threshold_layers(values: list[dict[str, Any]], y_encoding: dict[str, Any]) -> list[dict[str, Any]]:
    threshold = _first_float(values, "threshold_value")
    if threshold is None:
        return []
    row = {"z_crit": threshold, "label": f"upper-tail MAD cutoff = {_format_number(threshold)}"}
    return [
        {
            "name": "Upper-tail MAD cutoff",
            "data": {"values": [row]},
            "mark": {"type": "rule", "strokeWidth": 2, "strokeDash": [6, 4], "color": "#c83f49"},
            "encoding": {
                "y": _aux_y_encoding(y_encoding, "z_crit"),
                "tooltip": [{"field": "label", "type": "nominal", "title": "Threshold"}],
            },
        }
    ]


def _caption(
    geometry: list[dict[str, Any]],
    *,
    mad_branch: bool = False,
    companion_branch: bool = False,
    mad_threshold: float | None = None,
) -> str:
    if mad_branch:
        threshold_text = f" Dashed rule marks the upper cutoff z_crit = {_format_number(mad_threshold)}." if mad_threshold is not None else ""
        return (
            "Bars show the upper-tail robust MAD score per run, sorted from most shape-extreme to least. "
            "Because distance_rms is a non-negative difference score, only unusually high distances are outlier evidence; "
            "below-median signed z_mad values are displayed as zero outlier evidence."
            f"{threshold_text}"
        )
    if geometry:
        companion_text = (
            " Red bars can therefore represent either the formal Dixon candidate or a companion MAD masking review flag."
            if companion_branch
            else ""
        )
        return (
            "Bars show curve difference score per run, sorted by distance rank. "
            "Brackets show the Dixon gap between rank 1 and rank 2 and the denominator used to compute Qexp."
            f"{companion_text}"
        )
    return "Curve difference score per run, sorted by distance rank."


def _description(*, mad_branch: bool = False) -> str:
    if mad_branch:
        return "curve-shape distance ranking plot: upper-tail robust MAD score ranking with cutoff reference for large cohorts"
    return "curve-shape distance ranking plot: distance_rms ranking with Dixon gap/denominator geometry when Dixon Q-test applies"


def _gap_tick_rows(geometry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in geometry:
        rows.extend(
            [
                {
                    "x_start": row.get("rank1_run"),
                    "x_end": row.get("rank2_run"),
                    "score": row.get("rank1_score"),
                    "label": row.get("gap_label"),
                },
                {
                    "x_start": row.get("rank1_run"),
                    "x_end": row.get("rank2_run"),
                    "score": row.get("rank2_score"),
                    "label": row.get("gap_label"),
                },
            ]
        )
    return rows


def _range_tick_rows(geometry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in geometry:
        rows.extend(
            [
                {
                    "x_start": row.get("rank1_run"),
                    "x_end": row.get("denominator_low_run"),
                    "score": row.get("rank1_score"),
                    "label": row.get("denominator_label"),
                },
                {
                    "x_start": row.get("rank1_run"),
                    "x_end": row.get("denominator_low_run"),
                    "score": row.get("denominator_low_score"),
                    "label": row.get("denominator_label"),
                },
            ]
        )
    return rows


def _bracket_label_rows(geometry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in geometry:
        rows.extend(
            [
                {
                    "x_label": row.get("rank2_run"),
                    "score": row.get("gap_mid"),
                    "label": row.get("gap_label"),
                    "color": "#7a5a00",
                },
                {
                    "x_label": row.get("denominator_low_run"),
                    "score": row.get("denominator_mid"),
                    "label": row.get("denominator_label"),
                    "color": "#4b5b6a",
                },
            ]
        )
    return rows


def _dixon_tooltip() -> list[dict[str, str]]:
    return [
        {"field": "gap", "type": "quantitative", "title": "Gap", "format": ".3f"},
        {"field": "denominator", "type": "quantitative", "title": "Denominator", "format": ".3f"},
        {"field": "Qexp", "type": "quantitative", "title": "Qexp", "format": ".3f"},
        {"field": "Qcrit_95", "type": "quantitative", "title": "Qcrit 95%", "format": ".3f"},
        {"field": "dixon_variant", "type": "nominal", "title": "Dixon variant"},
        {"field": "decision", "type": "nominal", "title": "Decision"},
    ]


def _first_float(rows: list[dict[str, Any]], key: str) -> float | None:
    for row in rows:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def _row_for_run_id(rows: list[dict[str, Any]], run_id: str) -> dict[str, Any] | None:
    if not run_id:
        return None
    for row in rows:
        if str(row.get("run_id") or "") == run_id:
            return row
    return None


def _threshold_method(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        method = str(row.get("threshold_method") or "").strip()
        if method and method != "not_assessed":
            return method
    return ""


def _mad_score(row: dict[str, Any]) -> float | None:
    value = as_float(row.get("robust_z"))
    return value if value is not None else as_float(row.get("z_mad"))


def _mad_upper_score(row: dict[str, Any]) -> float | None:
    value = as_float(row.get("mad_upper_z"))
    if value is None:
        value = as_float(row.get("z_mad_upper"))
    if value is not None:
        return max(0.0, value)
    signed = _mad_score(row)
    return max(0.0, signed) if signed is not None else None


def _mad_scale(values: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [_mad_upper_score(row) for row in values]
    scores = [score for score in scores if score is not None]
    threshold = _first_float(values, "threshold_value")
    upper = max(scores + ([threshold] if threshold is not None else []) or [1.0])
    if upper <= 0:
        return {"domain": [0, 1], "nice": False}
    step = 0.5 if upper <= 4 else 1.0
    ceiling = math.ceil(upper / step) * step
    if ceiling <= upper:
        ceiling += step
    return {"domain": [0, ceiling], "nice": False}


def _format_number(value: float) -> str:
    return f"{value:.3g}"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _run_label(run_id: str) -> str:
    text = str(run_id or "")
    if text.startswith("run_"):
        suffix = text[4:]
        if suffix.isdigit():
            return f"#{int(suffix)}"
    return text
