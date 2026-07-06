from __future__ import annotations

import sys
import pytest
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from operations.core.operation_context import OperationCancelled, OperationContext, OperationRun
from operations.curve.derive_series import (
    DeriveSeriesByScalarOperation,
    DeriveSeriesMeanOperation,
    MapChannelOperation,
)
from operations.curve.max_point import AcceptedPeakPointOperation, MaxPointOperation


def test_map_channel_absolute_transform_preserves_signed_raw_series() -> None:
    channel = SimpleNamespace(values=[-3.0, 0.0, 2.5, None, "Overflow"], unit="N", point_count=5)
    source_run = _source_run({"Load": channel})
    run = OperationRun(source_run=source_run)
    context = _context(run)

    result = MapChannelOperation().run(
        context,
        {
            "from_mapping": "load",
            "output": "load_N",
            "transform": "absolute",
            "raw_output": "load_N_raw",
        },
    )[0]

    assert run.series["load_N_raw"] == [-3.0, 0.0, 2.5, None, "Overflow"]
    assert run.series["load_N"] == [3.0, 0.0, 2.5, None, None]
    assert run.units["load_N_raw"] == "N"
    assert run.units["load_N"] == "N"
    assert result.outputs["load_N"]["point_count"] == 5
    assert result.outputs["load_N_raw"]["point_count"] == 5
    assert result.parameters == {"required": True, "transform": "absolute", "raw_output": "load_N_raw"}
    assert "load_N = abs(channel:Load)" in result.evidence["formula"]
    assert result.warnings == ("Absolute channel transform skipped 1 non-numeric value(s). Examples: index 4: 'Overflow'.",)


def test_absolute_load_mapping_feeds_positive_strength_selection() -> None:
    channel = SimpleNamespace(values=[-10.0, -30.0, -20.0], unit="N", point_count=3)
    source_run = _source_run({"Load": channel})
    run = OperationRun(source_run=source_run, scalars={"area_mm2": 10.0}, units={"area_mm2": "mm^2"})
    context = _context(run)

    MapChannelOperation().run(
        context,
        {
            "from_mapping": "load",
            "output": "load_N",
            "transform": "absolute",
            "raw_output": "load_N_raw",
        },
    )
    DeriveSeriesByScalarOperation().run(
        context,
        {"numerator": "load_N", "denominator": "area_mm2", "output": "stress_MPa", "unit": "MPa"},
    )
    MaxPointOperation().run(
        context,
        {"y": "stress_MPa", "output_value": "compressive_strength_MPa", "output_index": "max_stress_index"},
    )

    assert run.series["load_N_raw"] == [-10.0, -30.0, -20.0]
    assert run.series["load_N"] == [10.0, 30.0, 20.0]
    assert run.series["stress_MPa"] == [1.0, 3.0, 2.0]
    assert run.scalars["compressive_strength_MPa"] == 3.0
    assert run.scalars["max_stress_index"] == 1


def test_max_point_operation_uses_last_equal_plateau_point() -> None:
    run = OperationRun(
        source_run=_source_run({}),
        series={"stress_MPa": [100.0, 150.0, 150.0, 150.0]},
        units={"stress_MPa": "MPa"},
    )
    context = _context(run)

    MaxPointOperation().run(
        context,
        {"y": "stress_MPa", "output_value": "compressive_strength_MPa", "output_index": "max_stress_index"},
    )

    assert run.scalars["compressive_strength_MPa"] == 150.0
    assert run.scalars["max_stress_index"] == 3


def test_accepted_peak_point_operation_uses_resolved_endpoint_anchor() -> None:
    run = OperationRun(
        source_run=_source_run({}),
        series={
            "stress_MPa": [100.0, 250.0, 180.0, 220.0],
            "point_index_bounded": [10, 11, 12, 13],
        },
        scalars={"accepted_failure_peak_index": 13},
        units={"stress_MPa": "MPa", "point_index_bounded": "index"},
    )
    context = _context(run)

    AcceptedPeakPointOperation().run(
        context,
        {
            "y": "stress_MPa",
            "output_value": "compressive_strength_MPa",
            "output_index": "max_stress_index",
        },
    )

    assert run.scalars["compressive_strength_MPa"] == 220.0
    assert run.scalars["max_stress_index"] == 3


def test_derive_series_mean_operation_checks_for_cancellation_inside_long_loop() -> None:
    run = OperationRun(
        source_run=_source_run({}),
        series={"front_strain": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "rear_strain": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]},
        units={"front_strain": "mm/mm", "rear_strain": "mm/mm"},
    )
    calls: dict[str, int] = {"count": 0}

    def _cancel_requested() -> bool:
        calls["count"] += 1
        return calls["count"] >= 5

    context = _context(run, cancel_requested=_cancel_requested)

    with pytest.raises(OperationCancelled):
        DeriveSeriesMeanOperation().run(
            context,
            {
                "inputs": ["front_strain", "rear_strain"],
                "output": "mean_strain",
                "parameters": {"mode": "arithmetic_mean"},
            },
        )

    assert "mean_strain" not in run.series


def _context(
    run: OperationRun,
    *,
    cancel_requested: Callable[[], bool] | None = None,
) -> OperationContext:
    return OperationContext(
        source=None,
        mapping={"channels": {"load": "Load"}},
        runs={"run_001": run},
        inspector=None,
        phase="method_resolve",
        cancel_requested=cancel_requested,
    )


def _source_run(channels: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        normalized_package_path="raw/run_001.csv",
        channel=lambda name: channels.get(name),
    )
