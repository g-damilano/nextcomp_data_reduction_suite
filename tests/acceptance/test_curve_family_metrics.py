from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.curve_family.distance_metrics import distance_metrics
from acceptance.curve_family.influence_metrics import leave_one_out_mean_shift
from acceptance.curve_family.models import AlignedCurve
from acceptance.curve_family.shape_metrics import shape_metrics


def test_distance_and_shape_metrics_identify_deviation() -> None:
    reference = (0.0, 1.0, 2.0, 3.0, 4.0)
    coherent = (0.0, 1.02, 2.01, 2.99, 4.0)
    magnitude_outlier = (0.0, 2.0, 4.0, 6.0, 8.0)
    shape_outlier = (0.0, 3.0, 1.0, 4.0, 2.0)

    coherent_distance = distance_metrics(coherent, reference)
    outlier_distance = distance_metrics(magnitude_outlier, reference)
    shape = shape_metrics(shape_outlier, reference)

    assert coherent_distance["normalized_rmse"] is not None
    assert outlier_distance["normalized_rmse"] is not None
    assert coherent_distance["normalized_rmse"] < 0.01
    assert outlier_distance["normalized_rmse"] > 0.5
    assert shape["curve_correlation"] is not None
    assert shape["curve_correlation"] < 0.6


def test_leave_one_out_mean_shift_is_largest_for_high_influence_curve() -> None:
    curves = [
        AlignedCurve("family", "run_a", (0.0, 0.5, 1.0), (0.0, 1.0, 2.0), "normalized_progress"),
        AlignedCurve("family", "run_b", (0.0, 0.5, 1.0), (0.0, 1.1, 2.1), "normalized_progress"),
        AlignedCurve("family", "run_c", (0.0, 0.5, 1.0), (0.0, 8.0, 16.0), "normalized_progress"),
    ]

    shifts = leave_one_out_mean_shift(curves)

    assert shifts["run_c"] is not None
    assert shifts["run_c"] > shifts["run_a"]
    assert shifts["run_c"] > shifts["run_b"]
