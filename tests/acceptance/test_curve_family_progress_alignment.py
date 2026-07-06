from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.curve_family.alignment import align_curve_family


def test_experiment_progress_alignment_uses_recorded_progress_not_row_order() -> None:
    aligned, warnings = align_curve_family(
        [
            {"run_id": "run_001", "point_index": 0, "experiment_progress": 0.0, "stress_MPa": 0.0},
            {"run_id": "run_001", "point_index": 1, "experiment_progress": 0.9, "stress_MPa": 90.0},
            {"run_id": "run_001", "point_index": 2, "experiment_progress": 1.0, "stress_MPa": 100.0},
        ],
        curve_family_id="stress_strain_family",
        run_ids={"run_001"},
        x_field="experiment_progress",
        y_field="stress_MPa",
        mode="experiment_progress",
        x_common_points=3,
    )

    assert not warnings
    assert len(aligned) == 1
    assert aligned[0].x_common == (0.0, 0.5, 1.0)
    assert aligned[0].y_aligned[1] == 50.0
