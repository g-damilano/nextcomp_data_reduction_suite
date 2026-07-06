from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from operations.diagnostics.bending_pattern import assess_bending_pattern


def test_bending_pattern_passes_without_exceedance() -> None:
    result = _assess([5.0] * 100)

    assert result["pattern"]["classification"] == "PASS"
    assert result["pointwise"]["points_above_threshold"] == 0
    assert result["segments"] == []


def test_bending_pattern_treats_single_point_as_spike() -> None:
    values = [5.0] * 100
    values[20] = 12.0

    result = _assess(values)

    assert result["pattern"]["classification"] == "PASS_WITH_SPIKES"
    assert result["pointwise"]["points_above_threshold"] == 1
    assert result["longest_segment"]["segment_classification"] == "isolated_spike"


def test_bending_pattern_treats_two_isolated_points_as_spikes() -> None:
    values = [5.0] * 100
    values[20] = 12.0
    values[70] = 14.0

    result = _assess(values)

    assert result["pattern"]["classification"] == "PASS_WITH_SPIKES"
    assert len(result["segments"]) == 2
    assert {segment["segment_classification"] for segment in result["segments"]} == {"isolated_spike"}


def test_bending_pattern_warns_for_short_transient_cluster() -> None:
    values = [5.0] * 100
    for index in range(40, 44):
        values[index] = 13.0

    result = _assess(values)

    assert result["pattern"]["classification"] == "WARN_TRANSIENT_BENDING"
    assert result["longest_segment"]["point_count"] == 4
    assert result["longest_segment"]["segment_classification"] == "transient_cluster"


def test_bending_pattern_fails_for_sustained_segment() -> None:
    values = [5.0] * 100
    for index in range(40, 48):
        values[index] = 15.0

    result = _assess(values)

    assert result["pattern"]["classification"] == "FAIL_SUSTAINED_BENDING"
    assert result["longest_segment"]["point_count"] == 8
    assert result["longest_segment"]["segment_classification"] == "sustained_region"


def _assess(values: list[float]):
    return assess_bending_pattern(
        bending_series=values,
        load_series=[float(index) for index in range(len(values))],
        window_indices=range(len(values)),
        threshold_percent=10.0,
    )
