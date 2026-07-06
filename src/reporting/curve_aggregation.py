from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Any


ANALYSIS_PROGRESS_CONTRACT = {
    "x_field": "analysis_progress",
    "x_coordinate_kind": "analysis_window_progress",
    "x_label": "Normalised strain",
    "x_unit": "fraction",
    "x_display_unit": "percent",
    "x_display_scale": 100.0,
    "x_aliases": ["x_normalized", "experiment_progress"],
    "source_artifact": "report/aligned_curves.csv",
    "transform_stage": "boundary_aligned_resampling",
}

FAILURE_STRAIN_NORMALIZED_CONTRACT = {
    "x_field": "x_normalized",
    "x_coordinate_kind": "failure_strain_normalized",
    "x_label": "Failure-strain normalised coordinate",
    "x_unit": "fraction",
    "x_display_unit": "percent",
    "x_display_scale": 100.0,
    "x_aliases": [],
    "source_artifact": "report/aligned_curves.csv",
    "transform_stage": "failure_strain_normalized_resampling",
}


def build_aligned_curves(
    curve_family: list[dict[str, Any]],
    specimen_results: list[dict[str, Any]],
    *,
    selection_run_ids: set[str] | None = None,
    selection_set: str = "auto_recommended_runs",
    x_grid_points: int = 500,
    x_axis: str = "mean_strain",
    y_axis: str = "stress_MPa",
    alignment_policy: str = "normalize_by_failure_strain",
    alignment: dict[str, Any] | None = None,
    boundary_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    grouped = _group_curve_rows(curve_family, selection_run_ids)
    alignment = alignment if isinstance(alignment, dict) else {}
    alignment_domain = str(alignment.get("domain") or "").strip()
    if alignment_domain == "experiment_progress":
        return _build_boundary_aligned_curves(
            grouped=grouped,
            boundary_records=boundary_records or [],
            selection_set=selection_set,
            y_axis=y_axis,
            alignment_policy=alignment_policy or "experiment_progress",
            alignment=alignment,
        )
    failure_by_run = {
        str(row.get("run_id")): _positive_float(row.get("compressive_failure_strain"))
        for row in specimen_results
    }
    run_series: dict[str, list[tuple[float, float]]] = {}
    for run_id, rows in grouped.items():
        failure_strain = failure_by_run.get(run_id) or _max_positive(rows, x_axis)
        if not failure_strain:
            continue
        points: list[tuple[float, float]] = []
        for row in rows:
            x_value = _as_float(row.get(x_axis))
            y_value = _as_float(row.get(y_axis))
            if x_value is None or y_value is None:
                continue
            normalized_x = x_value / failure_strain if alignment_policy == "normalize_by_failure_strain" else x_value
            if math.isfinite(normalized_x) and math.isfinite(y_value):
                points.append((normalized_x, y_value))
        points.sort(key=lambda item: item[0])
        run_series[run_id] = _dedupe_x(points)

    if not run_series:
        return []

    grid_count = max(2, int(x_grid_points))
    grid = [index / (grid_count - 1) for index in range(grid_count)]
    rows: list[dict[str, Any]] = []
    for index, x_value in enumerate(grid):
        per_run: dict[str, float] = {}
        values: list[float] = []
        for run_id, points in run_series.items():
            y_value = _interp(points, x_value)
            if y_value is None:
                continue
            per_run[f"{run_id}_{y_axis}"] = y_value
            values.append(y_value)
        if values:
            value_mean = mean(values)
            value_std = stdev(values) if len(values) > 1 else 0.0
            row: dict[str, Any] = {
                "selection_set": selection_set,
                "alignment_policy": alignment_policy,
                **_row_coordinate_contract(FAILURE_STRAIN_NORMALIZED_CONTRACT),
                "x_axis": x_axis,
                "y_axis": y_axis,
                "grid_index": index,
                "x_normalized": x_value,
                "n": len(values),
                "mean": value_mean,
                "std": value_std,
                "std_err": value_std / math.sqrt(len(values)) if values else 0.0,
                "min": min(values),
                "max": max(values),
            }
            row.update(per_run)
            rows.append(row)
    return rows


def build_characteristic_points(
    specimen_results: list[dict[str, Any]],
    aggregate_statistics: list[dict[str, Any]],
    *,
    selection_run_ids: set[str] | None = None,
    selection_set: str = "auto_recommended_runs",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in specimen_results:
        run_id = str(result.get("run_id"))
        if selection_run_ids is not None and run_id not in selection_run_ids:
            continue
        rows.append(
            {
                "selection_set": selection_set,
                "scope": "run",
                "run_id": run_id,
                "point_id": "compressive_failure",
                "x_field": "compressive_failure_strain",
                "x_value": result.get("compressive_failure_strain"),
                "x_unit": "strain",
                "y_field": "compressive_strength_MPa",
                "y_value": result.get("compressive_strength_MPa"),
                "y_unit": "MPa",
            }
        )
    stats_by_metric = {str(row.get("metric")): row for row in aggregate_statistics}
    if "compressive_failure_strain" in stats_by_metric and "compressive_strength_MPa" in stats_by_metric:
        rows.append(
            {
                "selection_set": selection_set,
                "scope": "aggregate",
                "run_id": "",
                "point_id": "mean_compressive_failure",
                "x_field": "compressive_failure_strain",
                "x_value": stats_by_metric["compressive_failure_strain"].get("mean"),
                "x_unit": "strain",
                "y_field": "compressive_strength_MPa",
                "y_value": stats_by_metric["compressive_strength_MPa"].get("mean"),
                "y_unit": "MPa",
            }
        )
    return rows


def build_feature_lines(
    aggregate_statistics: list[dict[str, Any]],
    *,
    selection_set: str = "auto_recommended_runs",
) -> list[dict[str, Any]]:
    stats_by_metric = {str(row.get("metric")): row for row in aggregate_statistics}
    rows: list[dict[str, Any]] = []
    for metric, axis, label in (
        ("compressive_strength_MPa", "y", "mean_compressive_strength"),
        ("compressive_failure_strain", "x", "mean_failure_strain"),
        ("compressive_modulus_MPa", "slope", "mean_compressive_modulus"),
    ):
        stat = stats_by_metric.get(metric)
        if not stat:
            continue
        rows.append(
            {
                "selection_set": selection_set,
                "line_id": label,
                "axis": axis,
                "metric": metric,
                "value": stat.get("mean"),
                "unit": stat.get("unit"),
                "n": stat.get("n"),
            }
        )
    return rows


def _group_curve_rows(
    curve_family: list[dict[str, Any]],
    selection_run_ids: set[str] | None,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in curve_family:
        run_id = str(row.get("run_id"))
        if selection_run_ids is not None and run_id not in selection_run_ids:
            continue
        grouped.setdefault(run_id, []).append(row)
    return grouped


def _build_boundary_aligned_curves(
    *,
    grouped: dict[str, list[dict[str, Any]]],
    boundary_records: list[dict[str, Any]],
    selection_set: str,
    y_axis: str,
    alignment_policy: str,
    alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    boundaries = {str(record.get("run_id")): record for record in boundary_records if isinstance(record, dict)}
    grid_count = max(2, int(alignment.get("resample_points") or alignment.get("x_common_points") or 500))
    include_endpoint = _truthy(alignment.get("include_endpoint", True))
    grid_denominator = grid_count - 1
    grid = [index / grid_denominator for index in range(grid_count)]
    run_series: dict[str, list[tuple[float, float]]] = {}
    boundary_meta: dict[str, dict[str, Any]] = {}
    for run_id, rows in grouped.items():
        boundary = boundaries.get(run_id) or _boundary_from_rows(rows)
        start_index, end_index = _boundary_indices(boundary, rows)
        if start_index is None or end_index is None or end_index <= start_index:
            continue
        points: list[tuple[float, float]] = []
        for row in rows:
            y_value = _as_float(row.get(y_axis))
            if y_value is None:
                continue
            progress = _boundary_progress(row, start_index=start_index, end_index=end_index)
            if progress is None:
                progress = _as_float(row.get("experiment_progress"))
            if progress is None:
                continue
            if progress < 0 or progress > 1:
                continue
            if not include_endpoint and progress >= 1:
                continue
            if math.isfinite(progress) and math.isfinite(y_value):
                points.append((progress, y_value))
        points.sort(key=lambda item: item[0])
        deduped = _dedupe_x(points)
        if len(deduped) < 2:
            continue
        run_series[run_id] = deduped
        boundary_meta[run_id] = {
            "boundary_start_index": start_index,
            "boundary_end_index": end_index,
            "boundary_start_policy": boundary.get("start_policy") if isinstance(boundary, dict) else "",
            "boundary_end_policy": boundary.get("end_policy") if isinstance(boundary, dict) else "",
        }
    if not run_series:
        return []
    rows: list[dict[str, Any]] = []
    for index, progress in enumerate(grid):
        per_run: dict[str, float] = {}
        values: list[float] = []
        starts: list[int] = []
        ends: list[int] = []
        start_policies: set[str] = set()
        end_policies: set[str] = set()
        for run_id, points in run_series.items():
            y_value = _interp(points, progress)
            if y_value is None:
                continue
            per_run[f"{run_id}_{y_axis}"] = y_value
            values.append(y_value)
            meta = boundary_meta.get(run_id, {})
            if meta.get("boundary_start_index") is not None:
                starts.append(int(meta["boundary_start_index"]))
            if meta.get("boundary_end_index") is not None:
                ends.append(int(meta["boundary_end_index"]))
            if meta.get("boundary_start_policy"):
                start_policies.add(str(meta["boundary_start_policy"]))
            if meta.get("boundary_end_policy"):
                end_policies.add(str(meta["boundary_end_policy"]))
        if values:
            value_mean = mean(values)
            value_std = stdev(values) if len(values) > 1 else 0.0
            row: dict[str, Any] = {
                "selection_set": selection_set,
                "alignment_policy": alignment_policy,
                "alignment_domain": "experiment_progress",
                "source_boundaries": alignment.get("source_boundaries") or "method_resolve.experiment_boundaries",
                **_row_coordinate_contract(ANALYSIS_PROGRESS_CONTRACT),
                "x_axis": "experiment_progress",
                "y_axis": y_axis,
                "grid_index": index,
                "x_normalized": progress,
                "experiment_progress": progress,
                "analysis_progress": progress,
                "analysis_progress_percent": progress * 100.0,
                "boundary_start_index": min(starts) if starts else "",
                "boundary_end_index": max(ends) if ends else "",
                "boundary_start_policy": ",".join(sorted(start_policies)),
                "boundary_end_policy": ",".join(sorted(end_policies)),
                "n": len(values),
                "mean": value_mean,
                "std": value_std,
                "std_err": value_std / math.sqrt(len(values)) if values else 0.0,
                "min": min(values),
                "max": max(values),
            }
            row.update(per_run)
            rows.append(row)
    return rows


def _row_coordinate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "x_field": contract["x_field"],
        "x_coordinate_kind": contract["x_coordinate_kind"],
        "x_label": contract["x_label"],
        "x_unit": contract["x_unit"],
        "x_display_unit": contract["x_display_unit"],
        "x_display_scale": contract["x_display_scale"],
        "x_aliases": ",".join(contract.get("x_aliases", [])),
        "source_artifact": contract["source_artifact"],
        "transform_stage": contract["transform_stage"],
    }


def coordinate_contract_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = next((row for row in rows if isinstance(row, dict)), {})
    if first.get("x_coordinate_kind") == ANALYSIS_PROGRESS_CONTRACT["x_coordinate_kind"]:
        return dict(ANALYSIS_PROGRESS_CONTRACT)
    if first.get("alignment_domain") == "experiment_progress":
        return dict(ANALYSIS_PROGRESS_CONTRACT)
    return dict(FAILURE_STRAIN_NORMALIZED_CONTRACT)


def _boundary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("boundary_start_index") not in (None, "") and row.get("boundary_end_index") not in (None, ""):
            return {
                "start_index": row.get("boundary_start_index"),
                "end_index": row.get("boundary_end_index"),
                "start_policy": row.get("boundary_start_policy"),
                "end_policy": row.get("boundary_end_policy"),
            }
    return {}


def _boundary_indices(boundary: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
    start = _as_int(interval.get("start_index", boundary.get("start_index")))
    end = _as_int(interval.get("end_index", boundary.get("end_index")))
    if start is not None and end is not None:
        return start, end
    indices = [_as_int(row.get("point_index")) for row in rows]
    indices = [index for index in indices if index is not None]
    if not indices:
        return None, None
    return min(indices), max(indices)


def _boundary_progress(row: dict[str, Any], *, start_index: int, end_index: int) -> float | None:
    raw_index = _as_float(row.get("point_index"))
    if raw_index is None or end_index <= start_index:
        return None
    return (raw_index - start_index) / (end_index - start_index)


def _max_positive(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_positive_float(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _positive_float(value: Any) -> float | None:
    numeric = _as_float(value)
    if numeric is None or numeric <= 0:
        return None
    return numeric


def _as_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _as_int(value: Any) -> int | None:
    try:
        return None if value in (None, "") else int(float(value))
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _dedupe_x(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique: list[tuple[float, float]] = []
    for x_value, y_value in points:
        if unique and abs(unique[-1][0] - x_value) <= 1e-15:
            unique[-1] = (x_value, y_value)
        else:
            unique.append((x_value, y_value))
    return unique


def _interp(points: list[tuple[float, float]], x_value: float) -> float | None:
    if not points:
        return None
    if x_value < points[0][0]:
        return points[0][1] if x_value >= 0 else None
    if x_value > points[-1][0]:
        return None
    if x_value == points[0][0]:
        return points[0][1]
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if x_value <= x1:
            if abs(x1 - x0) <= 1e-15:
                return y1
            fraction = (x_value - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return points[-1][1]
