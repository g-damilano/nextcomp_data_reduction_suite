from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.curve_family.alignment import align_curve_family
from acceptance.curve_family.reference_curve import pointwise_median_reference


def test_normalized_progress_alignment_and_median_reference() -> None:
    rows = _curve_rows({"run_a": 1.0, "run_b": 1.1, "run_c": 0.9})
    aligned, warnings = align_curve_family(
        rows,
        curve_family_id="stress_strain_family",
        run_ids={"run_a", "run_b", "run_c"},
        x_field="mean_strain",
        y_field="stress_MPa",
        mode="normalized_progress",
        x_common_points=5,
    )
    reference = pointwise_median_reference(aligned, curve_family_id="stress_strain_family")

    assert not warnings
    assert len(aligned) == 3
    assert aligned[0].x_common == (0.0, 0.25, 0.5, 0.75, 1.0)
    assert reference is not None
    assert reference.reference_type == "pointwise_median"
    assert reference.n_observations == (3, 3, 3, 3, 3)
    assert reference.y_reference[-1] == 4.0


def _curve_rows(scales: dict[str, float]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for run_id, scale in scales.items():
        for index in range(5):
            x_value = index / 4.0
            rows.append(
                {
                    "run_id": run_id,
                    "point_index": index,
                    "mean_strain": x_value,
                    "stress_MPa": scale * (x_value * 4.0),
                }
            )
    return rows
