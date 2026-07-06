from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.curve_family.classifier import classify_curve
from acceptance.curve_family.models import ACCEPT, PROPOSE_REMOVE, REVIEW


def test_classifier_accepts_review_and_proposes_remove() -> None:
    policy = {
        "review_if": {"normalized_rmse_gt": 0.15, "leave_one_out_mean_shift_gt": 0.2},
        "propose_remove_if": {"normalized_rmse_gt": 0.45, "curve_correlation_lt": 0.8, "multi_metric_review_count_gte": 2},
    }

    assert classify_curve({"normalized_rmse": 0.02, "curve_correlation": 0.99}, policy)[0] == ACCEPT
    review, review_reason = classify_curve({"normalized_rmse": 0.2, "curve_correlation": 0.98}, policy)
    remove, remove_reason = classify_curve({"normalized_rmse": 0.5, "curve_correlation": 0.7}, policy)

    assert review == REVIEW
    assert "normalized_rmse" in review_reason
    assert remove == PROPOSE_REMOVE
    assert "curve_correlation" in remove_reason or "normalized_rmse" in remove_reason
