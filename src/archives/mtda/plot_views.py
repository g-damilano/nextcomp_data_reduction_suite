from __future__ import annotations

import csv
import io
from collections.abc import Callable, Mapping
from typing import Any


TRANSFORM_VERSIONS: dict[str, str] = {
    "run.front_rear_strain_envelope.v1": "1.0.0",
    "run.front_rear_strain_traces.v1": "1.0.0",
    "run.bounded_average_curve.v1": "1.0.0",
    "run.empty_chord_line.v1": "1.0.0",
    "run.empty_chord_points.v1": "1.0.0",
    "run.analysis_markers.v1": "1.0.0",
    "aggregate.all_runs_resampled_curve_family.v1": "1.0.0",
    "aggregate.stress_band_from_run_grid.v1": "1.0.0",
    "aggregate.bending_summary_passthrough.v1": "1.0.0",
    "aggregate.fmax_distribution.v1": "1.0.0",
}


RUN_VIEW_FIELDS: dict[str, list[str]] = {
    "run.front_rear_strain_envelope.v1": ["strain_min", "strain_max", "stress", "point_index", "series"],
    "run.front_rear_strain_traces.v1": ["gauge_strain", "stress", "point_index", "series"],
    "run.bounded_average_curve.v1": ["strain", "stress", "point_index", "series"],
    "run.empty_chord_line.v1": [],
    "run.empty_chord_points.v1": [],
    "run.analysis_markers.v1": ["marker", "strain", "stress", "point_index"],
}


AGGREGATE_VIEW_FIELDS: dict[str, list[str]] = {
    "aggregate.all_runs_resampled_curve_family.v1": [
        "run_id",
        "cohort_id",
        "x_common",
        "y_observed",
        "y_reference",
        "y_variability",
        "standardized_residual",
        "diagnostic_classification",
    ],
    "aggregate.stress_band_from_run_grid.v1": [
        "x_common",
        "mean_stress_MPa",
        "min_stress_MPa",
        "max_stress_MPa",
        "std_stress_MPa",
        "lo_stress_MPa",
        "hi_stress_MPa",
        "run_count",
    ],
    "aggregate.bending_summary_passthrough.v1": [
        "run_id",
        "min_bending_percent",
        "q1_bending_percent",
        "median_bending_percent",
        "q3_bending_percent",
        "max_bending_percent",
        "bending_max_percent",
        "bending_mean_percent",
        "bending_median_percent",
        "bending_p95_percent",
        "bending_p99_percent",
        "bending_threshold_percent",
        "bending_points_above_threshold",
        "bending_fraction_above_threshold",
        "bending_pattern",
        "bending_pattern_confidence",
        "bending_pattern_reason",
    ],
    "aggregate.fmax_distribution.v1": [
        "x_position",
        "label",
        "min_strength_MPa",
        "q1_strength_MPa",
        "median_strength_MPa",
        "q3_strength_MPa",
        "max_strength_MPa",
        "mean_strength_MPa",
        "std_strength_MPa",
        "run_count",
    ],
}


def resolve_plot_data_view(view: Mapping[str, Any], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    transform_id = str(view.get("transform_id") or "")
    source_members = [str(member) for member in view.get("source_members") or []]
    transform = _TRANSFORMS.get(transform_id)
    if transform is None:
        raise ValueError(f"Unsupported plot data view transform: {transform_id}")
    return transform(source_members, member_rows)


def parse_csv_rows(content: bytes | str | None) -> list[dict[str, Any]]:
    if content in (None, b"", ""):
        return []
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def run_front_rear_strain_envelope(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        stress = _num(row.get("stress_MPa"))
        front = _first_num(row, "front_strain_abs", "front_strain")
        rear = _first_num(row, "rear_strain_abs", "rear_strain")
        if stress is None or front is None or rear is None:
            continue
        out.append(
            {
                "strain_min": min(front, rear) * 100.0,
                "strain_max": max(front, rear) * 100.0,
                "stress": stress,
                "point_index": _num(row.get("point_index")),
                "series": "front/rear strain agreement envelope",
            }
        )
    return out


def run_front_rear_strain_traces(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        stress = _num(row.get("stress_MPa"))
        front = _first_num(row, "front_strain_abs", "front_strain")
        rear = _first_num(row, "rear_strain_abs", "rear_strain")
        point_index = _num(row.get("point_index"))
        if stress is None:
            continue
        for series, strain in (("front strain", front), ("rear strain", rear)):
            if strain is not None:
                out.append({"gauge_strain": strain * 100.0, "stress": stress, "point_index": point_index, "series": series})
    return out


def run_bounded_average_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        strain = _first_num(row, "mean_strain", "strain_mm_per_mm")
        stress = _num(row.get("stress_MPa"))
        if strain is None or stress is None:
            continue
        out.append(
            {
                "strain": strain * 100.0,
                "stress": stress,
                "point_index": _num(row.get("point_index")),
                "series": "average strain curve",
            }
        )
    return out


def run_analysis_markers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    for marker, row in (
        ("start marker", rows[0]),
        ("end marker (max point / failure strain)", rows[-1]),
    ):
        strain = _first_num(row, "mean_strain", "strain_mm_per_mm")
        stress = _num(row.get("stress_MPa"))
        if strain is None or stress is None:
            continue
        out.append(
            {
                "marker": marker,
                "strain": strain * 100.0,
                "stress": stress,
                "point_index": _num(row.get("point_index")),
            }
        )
    return out


def aggregate_all_runs_resampled_curve_family(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    grid = _run_grid(source_members, member_rows)
    grouped: dict[float, list[float]] = {}
    for rows in grid.values():
        for row in rows:
            grouped.setdefault(float(row["x_common"]), []).append(float(row["y_observed"]))
    stats = {x_value: _mean_std(values) for x_value, values in grouped.items()}
    out: list[dict[str, Any]] = []
    for member in source_members:
        for row in grid.get(member, []):
            x_value = float(row["x_common"])
            mean_value, std_value = stats[x_value]
            observed = float(row["y_observed"])
            out.append(
                {
                    "run_id": row["run_id"],
                    "cohort_id": "whole_comparable_dataset",
                    "x_common": x_value,
                    "y_observed": observed,
                    "y_reference": mean_value,
                    "y_variability": std_value,
                    "standardized_residual": (observed - mean_value) / std_value if std_value else 0.0,
                    "diagnostic_classification": "CURVE_SHAPE_NOT_ASSESSED",
                }
            )
    return out


def aggregate_stress_band_from_run_grid(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    family = aggregate_all_runs_resampled_curve_family(source_members, member_rows)
    grouped: dict[float, list[float]] = {}
    for row in family:
        x_value = _num(row.get("x_common"))
        observed = _num(row.get("y_observed"))
        if x_value is None or observed is None or abs(x_value) <= 1e-15:
            continue
        grouped.setdefault(x_value, []).append(observed)
    out: list[dict[str, Any]] = []
    for x_value in sorted(grouped):
        values = grouped[x_value]
        mean_value, std_value = _mean_std(values)
        out.append(
            {
                "x_common": x_value,
                "mean_stress_MPa": mean_value,
                "min_stress_MPa": min(values),
                "max_stress_MPa": max(values),
                "std_stress_MPa": std_value,
                "lo_stress_MPa": mean_value - std_value,
                "hi_stress_MPa": mean_value + std_value,
                "run_count": len(values),
            }
        )
    return out


def aggregate_bending_summary_passthrough(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [dict(row) for member in source_members for row in member_rows.get(member, [])]


def aggregate_fmax_distribution(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    strengths = [
        value
        for member in source_members
        for row in member_rows.get(member, [])
        for value in [_first_num(row, "compressive_strength_MPa", "max_stress_MPa")]
        if value is not None
    ]
    if not strengths:
        return []
    ordered = sorted(strengths)
    mean_value, std_value = _mean_std(ordered)
    return [
        {
            "x_position": 100,
            "label": "Fmax",
            "min_strength_MPa": ordered[0],
            "q1_strength_MPa": _percentile(ordered, 25),
            "median_strength_MPa": _percentile(ordered, 50),
            "q3_strength_MPa": _percentile(ordered, 75),
            "max_strength_MPa": ordered[-1],
            "mean_strength_MPa": mean_value,
            "std_strength_MPa": std_value,
            "run_count": len(ordered),
        }
    ]


def _single_source(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return member_rows.get(source_members[0], []) if source_members else []


def _run_grid(source_members: list[str], member_rows: Mapping[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    grid = [index / 249.0 for index in range(250)]
    out: dict[str, list[dict[str, Any]]] = {}
    for member in source_members:
        rows = member_rows.get(member, [])
        run_id = _run_id_from_member(member, rows)
        points = _progress_points(rows)
        out[member] = [
            {
                "run_id": run_id,
                "x_common": x_value,
                "y_observed": _interpolate(points, x_value),
            }
            for x_value in grid
            if points
        ]
    return out


def _progress_points(rows: list[dict[str, Any]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    fallback_count = max(len(rows) - 1, 1)
    for index, row in enumerate(rows):
        y_value = _num(row.get("stress_MPa"))
        if y_value is None:
            continue
        x_value = _first_num(row, "experiment_progress", "analysis_progress", "x_common", "x_normalized")
        if x_value is None:
            x_value = index / fallback_count
        x_value = x_value / 100.0 if x_value > 1.5 else x_value
        points.append((max(0.0, min(1.0, x_value)), y_value))
    return sorted(points, key=lambda item: item[0])


def _interpolate(points: list[tuple[float, float]], target: float) -> float:
    if not points:
        return 0.0
    if target <= points[0][0]:
        return points[0][1]
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if target <= x1:
            if abs(x1 - x0) <= 1e-15:
                return y1
            fraction = (target - x0) / (x1 - x0)
            return y0 + (y1 - y0) * fraction
    return points[-1][1]


def _run_id_from_member(member: str, rows: list[dict[str, Any]]) -> str:
    for row in rows:
        run_id = str(row.get("run_id") or "").strip()
        if run_id:
            return run_id
    filename = member.rsplit("/", 1)[-1]
    if filename.startswith("run_"):
        return "_".join(filename.split("_")[:2])
    return filename.removesuffix(".csv")


def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_num(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _num(row.get(key))
        if value is not None:
            return value
    return None


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean_value = sum(values) / len(values)
    if len(values) == 1:
        return mean_value, 0.0
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return mean_value, variance**0.5


def _percentile(ordered: list[float], percentile: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


_TRANSFORMS: dict[str, Callable[[list[str], Mapping[str, list[dict[str, Any]]]], list[dict[str, Any]]]] = {
    "run.front_rear_strain_envelope.v1": lambda source, rows: run_front_rear_strain_envelope(_single_source(source, rows)),
    "run.front_rear_strain_traces.v1": lambda source, rows: run_front_rear_strain_traces(_single_source(source, rows)),
    "run.bounded_average_curve.v1": lambda source, rows: run_bounded_average_curve(_single_source(source, rows)),
    "run.empty_chord_line.v1": lambda source, rows: [],
    "run.empty_chord_points.v1": lambda source, rows: [],
    "run.analysis_markers.v1": lambda source, rows: run_analysis_markers(_single_source(source, rows)),
    "aggregate.all_runs_resampled_curve_family.v1": aggregate_all_runs_resampled_curve_family,
    "aggregate.stress_band_from_run_grid.v1": aggregate_stress_band_from_run_grid,
    "aggregate.bending_summary_passthrough.v1": aggregate_bending_summary_passthrough,
    "aggregate.fmax_distribution.v1": aggregate_fmax_distribution,
}
