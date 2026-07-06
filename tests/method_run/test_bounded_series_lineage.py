from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_executor import _build_curve_family, _build_specimen_results
from operations.core.operation_context import OperationRun


def test_bounded_curve_family_does_not_fall_back_to_full_series_after_boundary() -> None:
    run = OperationRun(
        source_run=None,
        series={
            "mean_strain": [float(index) for index in range(30)],
            "mean_strain_bounded": [0.001, 0.002, 0.003],
            "load_N": [1000.0 + index for index in range(30)],
            "load_N_bounded": [10.0, 20.0, 30.0],
            "load_N_raw": [-(1000.0 + index) for index in range(30)],
            "load_N_raw_bounded": [-10.0, -20.0, -30.0],
            "stress_MPa": [5.0, 15.0, 25.0],
            "stress_MPa_full": [50.0 + index for index in range(30)],
            "extension_mm": [900.0 + index for index in range(30)],
            "point_index_bounded": [10, 11, 12],
        },
        metadata={
            "experiment_boundaries": {
                "analysis_interval": {"start_index": 10, "end_index": 12, "include_endpoint": True},
                "start_policy": "first_point",
                "end_policy": "slope_break_pre_negative",
            }
        },
    )
    context = SimpleNamespace(runs={"run_001": run})

    rows = _build_curve_family(context, bounded=True)

    assert [row["point_index"] for row in rows] == [10, 11, 12]
    assert [row["mean_strain"] for row in rows] == [0.001, 0.002, 0.003]
    assert [row["load_N"] for row in rows] == [10.0, 20.0, 30.0]
    assert [row["load_N_raw"] for row in rows] == [-10.0, -20.0, -30.0]
    assert [row["stress_MPa"] for row in rows] == [5.0, 15.0, 25.0]
    assert [row["extension_mm"] for row in rows] == [None, None, None]
    assert all(row["curve_scope"] == "bounded" for row in rows)
    assert all(0.0 <= row["experiment_progress"] <= 1.0 for row in rows)


def test_specimen_results_expose_raw_point_indices_for_bounded_max_markers() -> None:
    run = OperationRun(
        source_run=None,
        scalars={
            "max_load_index": 2,
            "max_load_N": 30.0,
            "max_stress_index": 1,
            "compressive_strength_MPa": 15.0,
        },
        series={"point_index_bounded": [10, 11, 12]},
        metadata={
            "experiment_boundaries": {
                "analysis_interval": {"start_index": 10, "end_index": 12, "include_endpoint": True},
                "start_policy": "first_point",
                "end_policy": "slope_break_pre_negative",
            }
        },
    )
    context = SimpleNamespace(runs={"run_001": run}, warnings=[])

    specimen = _build_specimen_results(context)[0]

    assert specimen["max_load_index"] == 2
    assert specimen["max_load_point_index"] == 12
    assert specimen["max_stress_index"] == 1
    assert specimen["max_stress_point_index"] == 11
