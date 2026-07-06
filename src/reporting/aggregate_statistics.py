from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Any


SCALAR_METRICS: dict[str, str] = {
    "max_load_N": "N",
    "compressive_strength_MPa": "MPa",
    "compressive_modulus_MPa": "MPa",
    "compressive_failure_strain": "strain",
    "max_bending_percent": "%",
    "mean_bending_percent": "%",
    "p95_bending_percent": "%",
    "p99_bending_percent": "%",
}


def build_aggregate_statistics(
    specimen_results: list[dict[str, Any]],
    *,
    selection_run_ids: set[str] | None = None,
    selection_set: str = "auto_recommended_runs",
) -> list[dict[str, Any]]:
    rows = [
        row for row in specimen_results
        if selection_run_ids is None or str(row.get("run_id")) in selection_run_ids
    ]
    statistics_rows: list[dict[str, Any]] = []
    for metric, unit in SCALAR_METRICS.items():
        values = [_as_float(row.get(metric)) for row in rows]
        values = [value for value in values if value is not None and math.isfinite(value)]
        if not values:
            continue
        value_mean = mean(values)
        value_std = stdev(values) if len(values) > 1 else 0.0
        std_err = value_std / math.sqrt(len(values)) if values else 0.0
        ci_delta = _student_t_975(len(values) - 1) * std_err if len(values) > 1 else 0.0
        statistics_rows.append(
            {
                "selection_set": selection_set,
                "metric": metric,
                "unit": unit,
                "n": len(values),
                "mean": value_mean,
                "std": value_std,
                "std_err": std_err,
                "ci95_low": value_mean - ci_delta,
                "ci95_high": value_mean + ci_delta,
                "min": min(values),
                "max": max(values),
            }
        )
    return statistics_rows


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _student_t_975(df: int) -> float:
    """Two-sided 95% Student-t critical value for common report sample sizes."""

    if df <= 0:
        return 0.0
    table = {
        1: 12.7062047364,
        2: 4.3026527297,
        3: 3.1824463053,
        4: 2.7764451052,
        5: 2.5705818366,
        6: 2.4469118511,
        7: 2.3646242510,
        8: 2.3060041350,
        9: 2.2621571628,
        10: 2.2281388519,
        11: 2.2009851601,
        12: 2.17881283,
        13: 2.1603686565,
        14: 2.1447866879,
        15: 2.1314495456,
        16: 2.1199052992,
        17: 2.1098155778,
        18: 2.1009220402,
        19: 2.0930240544,
        20: 2.0859634473,
        21: 2.0796138447,
        22: 2.0738730679,
        23: 2.0686576104,
        24: 2.0638985616,
        25: 2.0595385528,
        26: 2.0555294386,
        27: 2.0518305165,
        28: 2.0484071418,
        29: 2.0452296421,
        30: 2.0422724563,
    }
    if df in table:
        return table[df]
    if df <= 40:
        return 2.0210753903
    if df <= 60:
        return 2.0002978211
    if df <= 120:
        return 1.9799304051
    return 1.9599639845
