from __future__ import annotations

from audit.audit_block_renderers import _analysis_window_rows


def test_analysis_window_rows_canonicalise_boundary_coordinate_aliases() -> None:
    rows = _analysis_window_rows(
        [
            {
                "run_id": "run_001",
                "point_index": 10,
                "boundary_start_index": 10,
                "boundary_end_index": 20,
                "x_common": 0.35,
                "experiment_progress": 0.35,
                "y_observed": 0.0,
            },
            {
                "run_id": "run_001",
                "point_index": 20,
                "boundary_start_index": 10,
                "boundary_end_index": 20,
                "x_common": 0.85,
                "experiment_progress": 0.85,
                "y_observed": 100.0,
            },
        ]
    )

    assert [row["analysis_progress_percent"] for row in rows] == [0.0, 100.0]
    assert [row["analysis_progress"] for row in rows] == [0.0, 1.0]
    assert [row["experiment_progress"] for row in rows] == [0.0, 1.0]
    assert [row["x_common"] for row in rows] == [0.0, 1.0]
    assert {row["curve_scope"] for row in rows} == {"boundary_aligned"}

