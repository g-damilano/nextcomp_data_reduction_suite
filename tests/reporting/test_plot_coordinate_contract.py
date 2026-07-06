from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.core.report_engine import _aggregate_plot_spec
from reporting.curve_aggregation import build_aligned_curves


def test_boundary_aligned_curves_expose_analysis_progress_contract() -> None:
    rows = build_aligned_curves(
        _curve_rows(),
        specimen_results=[],
        selection_run_ids={"run_001", "run_002"},
        selection_set="final_report_runs",
        y_axis="stress_MPa",
        alignment_policy="experiment_progress",
        alignment={"domain": "experiment_progress", "resample_points": 3},
        boundary_records=[
            {"run_id": "run_001", "analysis_interval": {"start_index": 10, "end_index": 20}},
            {"run_id": "run_002", "analysis_interval": {"start_index": 30, "end_index": 40}},
        ],
    )

    assert [row["analysis_progress"] for row in rows] == [0.0, 0.5, 1.0]
    assert [row["analysis_progress_percent"] for row in rows] == [0.0, 50.0, 100.0]
    assert {row["x_coordinate_kind"] for row in rows} == {"analysis_window_progress"}
    assert {row["x_field"] for row in rows} == {"analysis_progress"}
    assert {row["x_label"] for row in rows} == {"Normalised strain"}
    assert {row["x_unit"] for row in rows} == {"fraction"}
    assert {row["x_display_unit"] for row in rows} == {"percent"}
    assert {row["x_display_scale"] for row in rows} == {100.0}
    assert {row["transform_stage"] for row in rows} == {"boundary_aligned_resampling"}
    assert "x_normalized" in rows[0]["x_aliases"]
    assert rows[1]["x_normalized"] == rows[1]["analysis_progress"]


def test_boundary_aligned_curves_prefer_resolved_indices_over_stale_progress() -> None:
    rows = build_aligned_curves(
        [
            {"run_id": "run_001", "point_index": 10, "experiment_progress": 0.4, "stress_MPa": 10.0},
            {"run_id": "run_001", "point_index": 15, "experiment_progress": 0.7, "stress_MPa": 30.0},
            {"run_id": "run_001", "point_index": 20, "experiment_progress": 0.9, "stress_MPa": 50.0},
        ],
        specimen_results=[],
        selection_run_ids={"run_001"},
        selection_set="final_report_runs",
        y_axis="stress_MPa",
        alignment_policy="experiment_progress",
        alignment={"domain": "experiment_progress", "resample_points": 3},
        boundary_records=[
            {"run_id": "run_001", "analysis_interval": {"start_index": 10, "end_index": 20}},
        ],
    )

    assert [row["analysis_progress"] for row in rows] == [0.0, 0.5, 1.0]
    assert [row["run_001_stress_MPa"] for row in rows] == [10.0, 30.0, 50.0]


def test_aggregate_plot_spec_uses_coordinate_contract_normalised_strain_label() -> None:
    aligned_curves = [
        {
            "x_field": "analysis_progress",
            "x_coordinate_kind": "analysis_window_progress",
            "x_label": "Normalised strain",
            "x_unit": "fraction",
            "x_display_unit": "percent",
            "x_display_scale": 100.0,
            "x_aliases": "x_normalized,experiment_progress",
            "source_artifact": "report/aligned_curves.csv",
            "transform_stage": "boundary_aligned_resampling",
            "alignment_domain": "experiment_progress",
            "source_boundaries": "method_resolve.experiment_boundaries",
            "analysis_progress": 0.0,
            "analysis_progress_percent": 0.0,
            "x_normalized": 0.0,
            "experiment_progress": 0.0,
            "mean": 10.0,
            "std": 0.0,
            "min": 10.0,
            "max": 10.0,
            "n": 1,
            "run_001_stress_MPa": 10.0,
        }
    ]

    spec = _aggregate_plot_spec(
        aligned_curves=aligned_curves,
        characteristic_points=[],
        curve_policy={
            "alignment_policy": "experiment_progress",
            "alignment": {"domain": "experiment_progress"},
            "y_axis": "stress_MPa",
        },
        selection_set="final_report_runs",
        selected_run_ids={"run_001"},
    )

    x_axis = spec["axes"]["x"]
    assert x_axis["field"] == "analysis_progress"
    assert x_axis["coordinate_kind"] == "analysis_window_progress"
    assert x_axis["label"] == "Normalised strain"
    assert x_axis["unit"] == "fraction"
    assert x_axis["display_unit"] == "percent"
    assert x_axis["display_scale"] == 100.0
    assert x_axis["compatibility_aliases"] == ["x_normalized", "experiment_progress"]
    assert spec["x_coordinate_contract"]["x_field"] == "analysis_progress"
    assert spec["x_coordinate_contract"]["x_coordinate_kind"] == "analysis_window_progress"
    assert spec["x_coordinate_contract"]["x_label"] == "Normalised strain"


def _curve_rows() -> list[dict[str, float | str]]:
    return [
        {"run_id": "run_001", "point_index": 10, "stress_MPa": 10.0},
        {"run_id": "run_001", "point_index": 15, "stress_MPa": 30.0},
        {"run_id": "run_001", "point_index": 20, "stress_MPa": 50.0},
        {"run_id": "run_002", "point_index": 30, "stress_MPa": 20.0},
        {"run_id": "run_002", "point_index": 35, "stress_MPa": 40.0},
        {"run_id": "run_002", "point_index": 40, "stress_MPa": 60.0},
    ]
