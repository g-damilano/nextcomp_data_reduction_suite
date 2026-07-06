from __future__ import annotations

from typing import Any

from acceptance.curve_family.models import ACCEPT, PROPOSE_REMOVE, REVIEW


def classify_curve(score: dict[str, Any], policy: dict[str, Any] | None = None) -> tuple[str, str]:
    policy = policy or {}
    review_policy = policy.get("review_if") if isinstance(policy.get("review_if"), dict) else {}
    remove_policy = policy.get("propose_remove_if") if isinstance(policy.get("propose_remove_if"), dict) else {}
    review_reasons = _matched_conditions(score, review_policy)
    remove_reasons = _matched_conditions(score, remove_policy)
    multi_metric = _as_int(remove_policy.get("multi_metric_review_count_gte"))
    if multi_metric is not None and len(review_reasons) >= multi_metric:
        remove_reasons.append(f"{len(review_reasons)} review metrics met or exceeded policy threshold")
    if remove_reasons:
        return PROPOSE_REMOVE, "; ".join(remove_reasons)
    if review_reasons:
        return REVIEW, "; ".join(review_reasons)
    return ACCEPT, "Curve is within configured family policy."


def _matched_conditions(score: dict[str, Any], conditions: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key, threshold in conditions.items():
        key_text = str(key)
        if key_text.endswith("_gt"):
            metric = key_text[:-3]
            value = _as_float(score.get(metric))
            limit = _as_float(threshold)
            if value is not None and limit is not None and value > limit:
                reasons.append(f"{metric} {value:.6g} > {limit:.6g}")
        elif key_text.endswith("_lt"):
            metric = key_text[:-3]
            value = _as_float(score.get(metric))
            limit = _as_float(threshold)
            if value is not None and limit is not None and value < limit:
                reasons.append(f"{metric} {value:.6g} < {limit:.6g}")
    return reasons


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return None if value in (None, "") else int(value)
    except (TypeError, ValueError):
        return None
