from __future__ import annotations

from typing import Any

from plotting.models import PlotRequest, PlotResult
from plotting.plots.common import bending_pattern_color_scale
from plotting.quality import evaluate_spec


FORMAL_AGGREGATE_PLOT_TYPE = "aggregate_stress_strain_mean_variability"
FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE = "failure_analysis_bending_distribution"


def build_aggregate_stress_strain_mean_variability(request: PlotRequest) -> PlotResult:
    payload = request.data_payload
    spec = aggregate_stress_strain_vega_lite(
        source_spec=_dict_payload(payload.get("source_spec")),
        aligned_curves=payload.get("aligned_curves"),
        replicate_curves=payload.get("replicate_curves"),
        selected_run_ids=_string_set(payload.get("selected_run_ids")),
        endpoint_strains=_float_mapping(payload.get("endpoint_strains")),
        boundary_records=payload.get("boundary_records"),
        replicate_source=str(payload.get("replicate_source") or "none"),
        source_warnings=_string_list(payload.get("source_warnings")),
    )
    quality = evaluate_spec(spec, request, [])
    return PlotResult(
        plot_id=request.plot_id,
        plot_type="aggregate_curve_family",
        status="rendered",
        spec=spec,
        quality_report=quality,
    )


def build_failure_analysis_bending_distribution(request: PlotRequest) -> PlotResult:
    source_spec = _dict_payload(request.data_payload.get("source_spec"))
    spec = failure_analysis_bending_distribution_vega_lite(source_spec)
    status = "unavailable" if source_spec.get("unavailable_message") else "rendered"
    quality = evaluate_spec(spec, request, [])
    return PlotResult(
        plot_id=request.plot_id,
        plot_type=FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
        status=status,
        spec=spec,
        quality_report=quality,
    )


def aggregate_stress_strain_vega_lite(
    *,
    source_spec: dict[str, Any],
    aligned_curves: Any,
    replicate_curves: Any = None,
    selected_run_ids: set[str] | None = None,
    endpoint_strains: dict[str, float] | None = None,
    boundary_records: Any = None,
    replicate_source: str = "none",
    source_warnings: list[str] | None = None,
) -> dict[str, Any]:
    values = []
    replicate_values = []
    boundary_by_run = _boundary_by_run(boundary_records)
    filtered_replicate_rows = 0
    effective_replicate_source = replicate_source
    selected_runs = sorted(str(run_id) for run_id in (selected_run_ids or set()) if str(run_id))
    if not selected_runs:
        selected_runs = sorted(boundary_by_run)
    if isinstance(aligned_curves, list):
        for row in aligned_curves:
            if not isinstance(row, dict):
                continue
            mean = _as_float(row.get("mean"))
            std = _as_float(row.get("std")) or 0.0
            progress = _as_float(row.get("analysis_progress"))
            if progress is None:
                progress = _as_float(row.get("experiment_progress"))
            if progress is None:
                progress = _as_float(row.get("x_normalized"))
            if progress is None:
                continue
            x_value = progress * 100.0
            values.append(
                {
                    "analysis_progress_percent": x_value,
                    "analysis_progress": progress,
                    "min": _as_float(row.get("min")),
                    "max": _as_float(row.get("max")),
                    "mean": mean,
                    "std_lower": mean - std if mean is not None else None,
                    "std_upper": mean + std if mean is not None else None,
                    "n": _as_float(row.get("n")),
                }
            )
    if not replicate_values and isinstance(replicate_curves, list):
        for row in replicate_curves:
            if not isinstance(row, dict):
                continue
            run_id = str(row.get("run_id") or "")
            if selected_run_ids is not None and run_id not in selected_run_ids:
                continue
            if not _within_boundary(row):
                continue
            strain = _as_float(row.get("mean_strain"))
            stress = _as_float(row.get("stress_MPa"))
            if strain is None or stress is None:
                continue
            point_index = _as_float(row.get("point_index"))
            boundary = boundary_by_run.get(run_id, {})
            boundary_start = _first_present_float(_boundary_index(boundary, "start_index"), row.get("boundary_start_index"))
            boundary_end = _first_present_float(_boundary_index(boundary, "end_index"), row.get("boundary_end_index"))
            replicate_values.append(
                {
                    "actual_strain_percent": strain * 100.0,
                    "stress_MPa": stress,
                    "run_id": run_id,
                    "point_index": point_index,
                    "curve_scope": row.get("curve_scope"),
                    "experiment_progress": _as_float(row.get("experiment_progress")),
                    "boundary_start_index": boundary_start,
                    "boundary_end_index": boundary_end,
                }
            )
            effective_replicate_source = "bounded_curve_family"
    markers = _marker_values(source_spec)
    x_title = _x_axis_title(source_spec)
    freshness = _plot_data_freshness(
        aligned_curves=aligned_curves,
        aggregate_values=values,
        replicate_values=replicate_values,
        selected_run_ids=selected_run_ids,
        boundary_by_run=boundary_by_run,
        replicate_source=effective_replicate_source,
        filtered_replicate_rows=filtered_replicate_rows,
        source_warnings=source_warnings or [],
    )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Operator evidence view for individual replicates, aggregate mean, range, standard deviation, observations, and characteristic markers.",
        "usermeta": {"plot_data_freshness": freshness},
        "datasets": {
            "aggregate": values,
            "replicates": replicate_values,
            "markers": markers,
        },
        "hconcat": [
            {
                "title": "Individual replicates",
                "width": 330,
                "height": 270,
                "data": {"name": "replicates"},
                "mark": {"type": "line", "opacity": 0.24, "strokeWidth": 1.5, "color": "#78aeda"},
                "encoding": {
                    **_xy_encoding(y_field="stress_MPa", x_title="Actual strain / %", x_field="actual_strain_percent"),
                    "detail": {"field": "run_id"},
                },
            },
            {
                "title": "Mean curve with variability",
                "width": 360,
                "height": 270,
                "layer": [
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "area", "opacity": 0.16, "color": "#7bb7df"},
                        "encoding": {
                            **_xy_encoding(y_field="min", x_title=x_title),
                            "y2": {"field": "max"},
                        },
                    },
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "area", "opacity": 0.28, "color": "#2a7fb8"},
                        "encoding": {
                            **_xy_encoding(y_field="std_lower", x_title=x_title),
                            "y2": {"field": "std_upper"},
                        },
                    },
                    {
                        "data": {"name": "aggregate"},
                        "mark": {"type": "line", "strokeWidth": 3, "color": "#1f78b4"},
                        "encoding": {
                            **_xy_encoding(y_field="mean", x_title=x_title),
                            "tooltip": [
                                {"field": "analysis_progress_percent", "type": "quantitative", "title": x_title},
                                {"field": "mean", "type": "quantitative", "title": "Mean stress / MPa"},
                                {"field": "n", "type": "quantitative", "title": "Observations"},
                            ],
                        },
                    },
                    {
                        "data": {"name": "markers"},
                        "mark": {"type": "point", "filled": True, "size": 90, "color": "#d95f5f"},
                        "encoding": {
                            **_xy_encoding(y_field="stress_MPa", x_title=x_title),
                            "tooltip": [
                                {"field": "label", "type": "nominal", "title": "Marker"},
                                {"field": "run_id", "type": "nominal", "title": "Run"},
                                {"field": "stress_MPa", "type": "quantitative", "title": "Stress / MPa"},
                            ],
                        },
                    },
                    {
                        "data": {"name": "markers"},
                        "mark": {"type": "text", "dy": -10, "fontSize": 11, "color": "#9b2f2f"},
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
            "view": {"stroke": "#d7dde5"},
            "axis": {"labelFontSize": 11, "titleFontSize": 12},
            "title": {"fontSize": 15},
        },
    }


def failure_analysis_bending_distribution_vega_lite(source_spec: dict[str, Any]) -> dict[str, Any]:
    points = source_spec.get("points") if isinstance(source_spec.get("points"), list) else []
    summary = source_spec.get("summary") if isinstance(source_spec.get("summary"), list) else []
    summary = [_with_bending_pattern_group(row) for row in summary if isinstance(row, dict)]
    threshold = _as_float(source_spec.get("threshold_percent")) or 10.0
    if not summary:
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": source_spec.get(
                "unavailable_message",
                "Bending distribution plot unavailable: pointwise bending values are not present in the report payload.",
            ),
            "data": {
                "values": [
                    {
                        "message": source_spec.get(
                            "unavailable_message",
                            "Bending distribution plot unavailable: pointwise bending values are not present in the report payload.",
                        )
                    }
                ]
            },
            "mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 10},
            "encoding": {"text": {"field": "message"}},
        }
    run_count = len(summary)
    width = max(420, min(900, run_count * 34))
    ceiling = _bending_plot_ceiling(summary, threshold)
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Bending percentage distribution summary by run over the 10-90 % Fmax assessment window.",
        "width": width,
        "height": 260,
        "datasets": {
            "bending_points": points,
            "bending_summary": summary,
            "threshold": [{"threshold_percent": threshold}],
            "criterion_band": [{"threshold_percent": threshold, "ceiling_percent": ceiling}],
        },
        "layer": [
            {
                "data": {"name": "criterion_band"},
                "mark": {"type": "rect", "color": "#f7dfdd", "opacity": 0.36},
                "encoding": {
                    "x": {"value": 0},
                    "x2": {"value": width},
                    "y": {"field": "threshold_percent", "type": "quantitative", "title": "Bending / %"},
                    "y2": {"field": "ceiling_percent"},
                },
            },
            {
                "data": {"name": "threshold"},
                "mark": {"type": "rule", "strokeDash": [6, 4], "strokeWidth": 2, "color": "#d9786d"},
                "encoding": {
                    "y": {"field": "threshold_percent", "type": "quantitative"},
                    "tooltip": [
                        {
                            "field": "threshold_percent",
                            "type": "quantitative",
                            "title": "Bending threshold / %",
                        }
                    ],
                },
            },
            {
                "data": {"name": "bending_summary"},
                "mark": {"type": "rule", "strokeWidth": 1.25, "opacity": 0.75, "color": "#5b6775"},
                "encoding": {
                    "x": _bending_x_encoding(summary),
                    "y": {"field": "min_bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "y2": {"field": "max_bending_percent"},
                    "tooltip": _bending_summary_tooltip(),
                },
            },
            {
                "data": {"name": "bending_summary"},
                "mark": {"type": "bar", "size": 18, "opacity": 0.72},
                "encoding": {
                    "x": _bending_x_encoding(summary),
                    "y": {"field": "q1_bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "y2": {"field": "q3_bending_percent"},
                    "color": {
                        "field": "bending_pattern_group",
                        "type": "nominal",
                        "title": "Bending pattern",
                        "scale": {
                            "domain": ["PASS", "WARN", "FAIL"],
                            "range": [
                                bending_pattern_color_scale()["range"][0],
                                bending_pattern_color_scale()["range"][2],
                                bending_pattern_color_scale()["range"][4],
                            ],
                        },
                    },
                    "tooltip": _bending_summary_tooltip(),
                },
            },
            {
                "data": {"name": "bending_summary"},
                "mark": {"type": "tick", "thickness": 2, "size": 22, "color": "#1f2933"},
                "encoding": {
                    "x": _bending_x_encoding(summary),
                    "y": {"field": "median_bending_percent", "type": "quantitative", "title": "Bending / %"},
                    "tooltip": _bending_summary_tooltip(),
                },
            },
        ],
        "config": {
            "view": {"stroke": "#d7dde5"},
            "axis": {"labelFontSize": 10, "titleFontSize": 12, "labelOverlap": "greedy"},
        },
    }


def _dict_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_set(value: Any) -> set[str]:
    if isinstance(value, set):
        return {str(item) for item in value if str(item)}
    if isinstance(value, (list, tuple)):
        return {str(item) for item in value if str(item)}
    return set()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _float_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    mapped: dict[str, float] = {}
    for key, item in value.items():
        number = _as_float(item)
        if number is not None:
            mapped[str(key)] = number
    return mapped


def _bending_x_encoding(summary: list[Any]) -> dict[str, Any]:
    return {
        "field": "run_label",
        "type": "nominal",
        "title": "Run",
        "sort": _run_sort(summary),
        "axis": {
            "labelAngle": -45,
            "labelOverlap": "greedy",
        },
    }


def _with_bending_pattern_group(row: dict[str, Any]) -> dict[str, Any]:
    next_row = dict(row)
    next_row["bending_pattern_group"] = _bending_pattern_group(row.get("bending_pattern"))
    return next_row


def _bending_pattern_group(pattern: Any) -> str:
    value = str(pattern or "").upper()
    if value.startswith("FAIL"):
        return "FAIL"
    if value.startswith("WARN"):
        return "WARN"
    if value == "PASS_WITH_SPIKES":
        return "PASS"
    return "PASS"


def _bending_plot_ceiling(summary: list[Any], threshold: float) -> float:
    values = [threshold]
    for row in summary:
        if isinstance(row, dict):
            for key in ("max_bending_percent", "p95_bending_percent", "q3_bending_percent"):
                value = _as_float(row.get(key))
                if value is not None:
                    values.append(value)
    maximum = max(values)
    return max(12.0, maximum * 1.08)


def _bending_summary_tooltip() -> list[dict[str, Any]]:
    return [
        {"field": "run_label", "type": "nominal", "title": "Run"},
        {"field": "specimen_name", "type": "nominal", "title": "Specimen"},
        {"field": "min_bending_percent", "type": "quantitative", "title": "Min bending / %"},
        {"field": "q1_bending_percent", "type": "quantitative", "title": "Q1 bending / %"},
        {"field": "median_bending_percent", "type": "quantitative", "title": "Median bending / %"},
        {"field": "q3_bending_percent", "type": "quantitative", "title": "Q3 bending / %"},
        {"field": "p95_bending_percent", "type": "quantitative", "title": "p95 bending / %"},
        {"field": "max_bending_percent", "type": "quantitative", "title": "Max bending / %"},
        {"field": "fraction_above_threshold", "type": "quantitative", "title": "Fraction above threshold"},
        {"field": "points_above_threshold", "type": "quantitative", "title": "Points above threshold"},
        {"field": "assessed_point_count", "type": "quantitative", "title": "Assessed point count"},
    ]


def _run_sort(points: list[Any]) -> list[str]:
    labels = []
    for point in points:
        if isinstance(point, dict):
            label = str(point.get("run_label") or "")
            if label and label not in labels:
                labels.append(label)
    return labels


def _xy_encoding(
    *,
    y_field: str,
    x_title: str = "Normalised strain / %",
    x_field: str = "analysis_progress_percent",
) -> dict[str, Any]:
    return _xy_encoding_from_label(y_field=y_field, x_title=x_title, x_field=x_field)


def _xy_encoding_from_label(*, y_field: str, x_title: str, x_field: str) -> dict[str, Any]:
    return {
        "x": {
            "field": x_field,
            "type": "quantitative",
            "title": x_title,
        },
        "y": {
            "field": y_field,
            "type": "quantitative",
            "title": "Stress / MPa",
        },
    }


def _x_axis_title(source_spec: dict[str, Any]) -> str:
    axes = source_spec.get("axes") if isinstance(source_spec.get("axes"), dict) else {}
    x_axis = axes.get("x") if isinstance(axes.get("x"), dict) else {}
    label = str(x_axis.get("label") or "").strip()
    if label:
        if "%" in label:
            return label
        return f"{label} / %"
    return "Normalised strain / %"


def _plot_data_freshness(
    *,
    aligned_curves: Any,
    aggregate_values: list[dict[str, Any]],
    replicate_values: list[dict[str, Any]],
    selected_run_ids: set[str] | None,
    boundary_by_run: dict[str, dict[str, Any]],
    replicate_source: str,
    filtered_replicate_rows: int,
    source_warnings: list[str],
) -> dict[str, Any]:
    reasons = list(source_warnings)
    stale = False
    warning = False
    selected = set(selected_run_ids or [])
    selected_with_boundaries = selected & set(boundary_by_run)
    if selected_with_boundaries and replicate_source != "boundary_aligned_curves":
        if replicate_source != "bounded_curve_family":
            stale = True
            reasons.append("Replicate plot source is not a plot-ready bounded curve table for a boundary-resolved method run.")
    if selected_with_boundaries:
        stale_policy_runs = sorted(
            run_id
            for run_id in selected_with_boundaries
            if _boundary_policy_signature(boundary_by_run[run_id]).get("slope_domain") != "strain"
            or _boundary_policy_signature(boundary_by_run[run_id]).get("end_policy") != "slope_break_pre_negative"
        )
        if stale_policy_runs:
            stale = True
            reasons.append(
                "Boundary policy metadata is stale for "
                + ", ".join(stale_policy_runs)
                + "; rerun method resolution so the plot uses slope_break_pre_negative on strain."
            )
    if isinstance(aligned_curves, list) and aligned_curves:
        first = next((row for row in aligned_curves if isinstance(row, dict)), {})
        if first.get("alignment_domain") != "experiment_progress":
            stale = True
            reasons.append("Aggregate curve rows are not aligned on resolved experiment_progress.")
        if first.get("source_boundaries") != "method_resolve.experiment_boundaries":
            stale = True
            reasons.append("Aggregate curve rows do not cite method_resolve.experiment_boundaries as their boundary source.")
    elif selected_with_boundaries:
        stale = True
        reasons.append("Aggregate curve rows are missing for the boundary-resolved report plot.")

    leaks = []
    for row in replicate_values:
        run_id = str(row.get("run_id") or "")
        point_index = _as_float(row.get("point_index"))
        end_index = _as_float(row.get("boundary_end_index"))
        progress = _as_float(row.get("experiment_progress"))
        start_index = _as_float(row.get("boundary_start_index"))
        has_point_boundary = point_index is not None and start_index is not None and end_index is not None
        if point_index is not None and end_index is not None and point_index > end_index:
            leaks.append(run_id)
        if not has_point_boundary and progress is not None and progress > 1:
            leaks.append(run_id)
    if leaks:
        stale = True
        reasons.append("Replicate plot contains points beyond the resolved experiment boundary for " + ", ".join(sorted(set(leaks))) + ".")
    if filtered_replicate_rows:
        warning = True
        reasons.append(
            f"{filtered_replicate_rows} bounded replicate point(s) were hidden by the endpoint-strain guard; review boundary resolution if this persists."
        )
    missing_runs = sorted(
        run_id
        for run_id in selected_with_boundaries
        if not any(str(row.get("run_id") or "") == run_id for row in replicate_values)
    )
    if missing_runs:
        warning = True
        reasons.append("No replicate plot rows were available for boundary-resolved run(s): " + ", ".join(missing_runs) + ".")
    if selected_with_boundaries and not aggregate_values:
        stale = True
        reasons.append("Aggregate plot dataset is empty for a boundary-resolved report.")

    status = "stale" if stale else "warning" if warning else "current"
    policy_signatures = sorted(
        {
            str(_boundary_policy_signature(boundary).get("signature") or "")
            for boundary in boundary_by_run.values()
            if _boundary_policy_signature(boundary).get("signature")
        }
    )
    endpoint_by_run = {
        run_id: _boundary_index(boundary, "end_index")
        for run_id, boundary in sorted(boundary_by_run.items())
        if not selected or run_id in selected
    }
    return {
        "schema_id": "report.plot_data_freshness.v0_1",
        "status": status,
        "replicate_source": replicate_source,
        "aggregate_x_field": "analysis_progress_percent",
        "aggregate_x_coordinate_kind": "analysis_window_progress",
        "replicate_x_field": "actual_strain_percent",
        "replicate_x_coordinate_kind": "actual_strain",
        "replicate_strain_source": "bounded_curve_family",
        "bounded_replicates": replicate_source in {"boundary_aligned_curves", "bounded_curve_family"},
        "boundary_aligned_replicates": replicate_source in {"boundary_aligned_curves", "bounded_curve_family"},
        "boundary_aligned_aggregation": bool(
            isinstance(aligned_curves, list)
            and aligned_curves
            and isinstance(aligned_curves[0], dict)
            and aligned_curves[0].get("alignment_domain") == "experiment_progress"
        ),
        "selected_run_count": len(selected),
        "boundary_resolved_run_count": len(selected_with_boundaries),
        "aggregate_row_count": len(aggregate_values),
        "replicate_row_count": len(replicate_values),
        "filtered_replicate_row_count": filtered_replicate_rows,
        "endpoint_by_run": endpoint_by_run,
        "policy_signatures": policy_signatures,
        "reasons": reasons,
    }


def _boundary_by_run(boundary_records: Any) -> dict[str, dict[str, Any]]:
    records = boundary_records if isinstance(boundary_records, list) else []
    return {
        str(record.get("run_id")): record
        for record in records
        if isinstance(record, dict) and record.get("run_id")
    }


def _boundary_index(boundary: dict[str, Any], key: str) -> float | None:
    interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
    return _as_float(interval.get(key, boundary.get(key)))


def _boundary_policy_signature(boundary: dict[str, Any]) -> dict[str, Any]:
    policy = boundary.get("resolution_policy") if isinstance(boundary.get("resolution_policy"), dict) else {}
    slope = policy.get("slope_break") if isinstance(policy.get("slope_break"), dict) else {}
    return {
        "end_policy": policy.get("end_policy") or boundary.get("end_policy"),
        "slope_domain": slope.get("slope_domain"),
        "signature": policy.get("signature"),
    }


def _marker_values(source_spec: dict[str, Any]) -> list[dict[str, Any]]:
    points = source_spec.get("layers", {}).get("characteristic_markers", {}).get("points", [])
    if not isinstance(points, list):
        return []
    aggregate_points = [point for point in points if isinstance(point, dict) and point.get("scope") == "aggregate"]
    source_points = aggregate_points or [point for point in points if isinstance(point, dict)][:1]
    marker_rows: list[dict[str, Any]] = []
    for point in source_points:
        stress = _as_float(point.get("y_value"))
        if stress is None:
            continue
        marker_rows.append(
            {
                "analysis_progress_percent": 100.0,
                "stress_MPa": stress,
                "run_id": str(point.get("run_id") or "aggregate"),
                "label": "mean failure" if point.get("scope") == "aggregate" else "failure",
            }
        )
    return marker_rows


def _within_boundary(row: dict[str, Any]) -> bool:
    point_index = _as_float(row.get("point_index"))
    end_index = _as_float(row.get("boundary_end_index"))
    start_index = _as_float(row.get("boundary_start_index"))
    has_point_boundary = point_index is not None and start_index is not None and end_index is not None
    if point_index is not None and start_index is not None and point_index < start_index:
        return False
    if point_index is not None and end_index is not None and point_index > end_index:
        return False
    if has_point_boundary:
        return True
    progress = _as_float(row.get("experiment_progress"))
    if progress is not None and (progress < 0 or progress > 1):
        return False
    return True


def _first_present_float(*values: Any) -> float | None:
    for value in values:
        number = _as_float(value)
        if number is not None:
            return number
    return None


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
