from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


DEFAULT_BENDING_ASSESSMENT_POLICY: dict[str, Any] = {
    "threshold_percent": 10.0,
    "segment_detection": {
        "allow_gap_points": 0,
        "classify_single_point_as_spike": True,
    },
    "classification": {
        "pass_with_spikes": {
            "max_longest_segment_points": 2,
            "max_total_exceedance_fraction": 0.02,
        },
        "warn_transient": {
            "max_longest_segment_fraction": 0.05,
            "max_total_exceedance_fraction": 0.10,
        },
        "fail_sustained": {
            "longest_segment_fraction_above": 0.05,
            "total_exceedance_fraction_above": 0.10,
        },
    },
}


def assess_bending_pattern(
    *,
    bending_series: list[float | None],
    load_series: list[float | None],
    window_indices: Iterable[int],
    policy: Mapping[str, Any] | None = None,
    threshold_percent: float | None = None,
) -> dict[str, Any]:
    resolved_policy = _merge_policy(policy)
    threshold = float(threshold_percent if threshold_percent is not None else resolved_policy["threshold_percent"])
    indices = list(window_indices)
    values_by_index = {
        index: bending_series[index]
        for index in indices
        if 0 <= index < len(bending_series) and bending_series[index] is not None
    }
    values = [float(value) for value in values_by_index.values()]
    exceedance_indices = [index for index, value in values_by_index.items() if float(value) > threshold]
    segments = _segments(
        exceedance_indices,
        bending_series=bending_series,
        load_series=load_series,
        total_points=len(values),
        policy=resolved_policy,
    )
    longest = max(segments, key=lambda segment: int(segment["point_count"]), default=None)
    pointwise = {
        "threshold_percent": threshold,
        "max_bending_percent": max(values) if values else None,
        "mean_bending_percent": sum(values) / len(values) if values else None,
        "median_bending_percent": _percentile(values, 50),
        "p95_bending_percent": _percentile(values, 95),
        "p99_bending_percent": _percentile(values, 99),
        "points_above_threshold": len(exceedance_indices),
        "total_points": len(values),
        "fraction_above_threshold": len(exceedance_indices) / len(values) if values else 0.0,
    }
    pattern = _classify(pointwise, longest, resolved_policy)
    return {
        "pointwise": pointwise,
        "segments": segments,
        "longest_segment": longest,
        "pattern": pattern,
    }


def _segments(
    exceedance_indices: list[int],
    *,
    bending_series: list[float | None],
    load_series: list[float | None],
    total_points: int,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not exceedance_indices:
        return []
    allow_gap = int((policy.get("segment_detection") or {}).get("allow_gap_points", 0))
    grouped: list[list[int]] = []
    current: list[int] = []
    previous: int | None = None
    for index in sorted(exceedance_indices):
        if previous is None or index <= previous + allow_gap + 1:
            current.append(index)
        else:
            grouped.append(current)
            current = [index]
        previous = index
    if current:
        grouped.append(current)

    segments: list[dict[str, Any]] = []
    for number, indices in enumerate(grouped, start=1):
        values = [float(bending_series[index]) for index in indices if bending_series[index] is not None]
        start = indices[0]
        end = indices[-1]
        point_count = len(indices)
        segment_fraction = point_count / total_points if total_points else 0.0
        segments.append(
            {
                "segment_id": f"seg_{number:03d}",
                "start_index": start,
                "end_index": end,
                "start_load_N": _series_value(load_series, start),
                "end_load_N": _series_value(load_series, end),
                "point_count": point_count,
                "fraction_of_window": segment_fraction,
                "max_bending_percent": max(values) if values else None,
                "mean_bending_percent": sum(values) / len(values) if values else None,
                "segment_classification": _segment_classification(point_count, segment_fraction, policy),
            }
        )
    return segments


def _segment_classification(point_count: int, segment_fraction: float, policy: Mapping[str, Any]) -> str:
    pass_with_spikes = (policy.get("classification") or {}).get("pass_with_spikes") or {}
    warn_transient = (policy.get("classification") or {}).get("warn_transient") or {}
    max_spike_points = int(pass_with_spikes.get("max_longest_segment_points", 2))
    max_transient_fraction = float(warn_transient.get("max_longest_segment_fraction", 0.05))
    if point_count <= 1:
        return "isolated_spike"
    if point_count <= max_spike_points:
        return "isolated_spike"
    if segment_fraction <= max_transient_fraction:
        return "transient_cluster"
    return "sustained_region"


def _classify(
    pointwise: Mapping[str, Any],
    longest_segment: Mapping[str, Any] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    total_points = int(pointwise.get("total_points") or 0)
    points_above = int(pointwise.get("points_above_threshold") or 0)
    if points_above == 0:
        return {
            "classification": "PASS",
            "confidence": "high" if total_points else "low",
            "reason": "No bending values exceed the configured threshold in the assessment window.",
        }

    classification = policy.get("classification") or {}
    pass_with_spikes = classification.get("pass_with_spikes") or {}
    warn_transient = classification.get("warn_transient") or {}
    fail_sustained = classification.get("fail_sustained") or {}
    longest_points = int((longest_segment or {}).get("point_count") or 0)
    longest_fraction = float((longest_segment or {}).get("fraction_of_window") or 0.0)
    total_fraction = float(pointwise.get("fraction_above_threshold") or 0.0)

    if (
        longest_points <= int(pass_with_spikes.get("max_longest_segment_points", 2))
        and total_fraction <= float(pass_with_spikes.get("max_total_exceedance_fraction", 0.02))
    ):
        return {
            "classification": "PASS_WITH_SPIKES",
            "confidence": "high",
            "reason": "Only isolated bending-threshold exceedance spikes were detected.",
        }

    if (
        longest_fraction <= float(warn_transient.get("max_longest_segment_fraction", 0.05))
        and total_fraction <= float(warn_transient.get("max_total_exceedance_fraction", 0.10))
    ):
        return {
            "classification": "WARN_TRANSIENT_BENDING",
            "confidence": "medium",
            "reason": "Bending exceedance is clustered but not sustained across the load window.",
        }

    if (
        longest_fraction > float(fail_sustained.get("longest_segment_fraction_above", 0.05))
        or total_fraction > float(fail_sustained.get("total_exceedance_fraction_above", 0.10))
    ):
        return {
            "classification": "FAIL_SUSTAINED_BENDING",
            "confidence": "high",
            "reason": "Bending threshold exceedance persists over a sustained portion of the load window.",
        }

    return {
        "classification": "WARN_TRANSIENT_BENDING",
        "confidence": "low",
        "reason": "Bending exceedance pattern is above threshold but close to configured classification boundaries.",
    }


def _merge_policy(policy: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = {
        "threshold_percent": DEFAULT_BENDING_ASSESSMENT_POLICY["threshold_percent"],
        "segment_detection": dict(DEFAULT_BENDING_ASSESSMENT_POLICY["segment_detection"]),
        "classification": {
            key: dict(value)
            for key, value in DEFAULT_BENDING_ASSESSMENT_POLICY["classification"].items()
        },
    }
    if not isinstance(policy, Mapping):
        return merged
    if policy.get("threshold_percent") is not None:
        merged["threshold_percent"] = float(policy["threshold_percent"])
    for section in ("segment_detection",):
        if isinstance(policy.get(section), Mapping):
            merged[section].update(policy[section])
    if isinstance(policy.get("classification"), Mapping):
        for key, value in policy["classification"].items():
            if isinstance(value, Mapping):
                merged["classification"].setdefault(str(key), {}).update(value)
    return merged


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _series_value(series: list[float | None], index: int) -> float | None:
    return series[index] if 0 <= index < len(series) else None
