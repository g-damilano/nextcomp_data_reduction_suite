from __future__ import annotations

from statistics import median
from typing import Any

from diagnostics.curves.models import (
    CURVE_SHAPE_NORMAL,
    CURVE_SHAPE_NOT_ASSESSED,
    CURVE_SHAPE_OUTLIER,
    INSUFFICIENT_COHORT_SIZE,
    CurveThresholdPolicy,
)


DIXON_R10_QCRIT_95 = {
    3: 0.970,
    4: 0.829,
    5: 0.710,
    6: 0.625,
    7: 0.568,
}


DIXON_R11_QCRIT_95 = {
    8: 0.615,
    9: 0.570,
    10: 0.534,
}


MAD_SCALE_FACTOR = 0.6745
MAD_COMPANION_METHOD = "robust_mad_masking_screen"
MAD_COMPANION_MIN_N = 5


def classify_distances(
    score_rows: list[dict[str, Any]],
    policy: CurveThresholdPolicy,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluable = [
        row for row in score_rows
        if row.get("evaluable") and row.get("distance_rms") is not None
    ]
    n = len(evaluable)
    if n < 3:
        for row in evaluable:
            row.update(
                {
                    "threshold_method": policy.insufficient_method,
                    "diagnostic_classification": INSUFFICIENT_COHORT_SIZE,
                    "is_curve_shape_outlier": False,
                    "Qcrit_note": "At least 3 evaluable curves are required.",
                    "threshold_observation_unit": "run_level_distance_rms",
                    "pooled_raw_curve_points": False,
                    "statistical_decision_role": "not_assessed",
                    "automatic_exclusion": False,
                }
            )
        return score_rows, {
            "threshold_method": policy.insufficient_method,
            "effective_sample_size": n,
            "reason": "insufficient evaluable cohort size",
            **_statistical_process_context(policy, branch="insufficient_cohort_size"),
        }
    if n <= 10:
        return _classify_dixon(score_rows, evaluable, policy)
    return _classify_robust_mad(score_rows, evaluable, policy)


def _classify_dixon(
    score_rows: list[dict[str, Any]],
    evaluable: list[dict[str, Any]],
    policy: CurveThresholdPolicy,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ranked = sorted(evaluable, key=lambda row: float(row["distance_rms"]))
    n = len(ranked)
    components = _dixon_high_outlier_components(ranked)
    qexp = components["Qexp"]
    qcrit = components["Qcrit_95"]
    candidate_run = str(ranked[-1].get("run_id") or "")
    edge_case = str(components.get("threshold_edge_case") or "")
    outlier = not edge_case and qexp > qcrit
    dixon_decision = "not_assessed_zero_denominator" if edge_case else "outlier" if outlier else "no_outlier"
    companion = _mad_upper_tail_screen(evaluable, policy)
    companion_rows = companion["rows"] if isinstance(companion.get("rows"), dict) else {}
    companion_run_ids = [str(run_id) for run_id in companion.get("flagged_run_ids", [])]
    companion_flag_count = len(companion_run_ids) if not edge_case else 0
    masking_risk = bool(companion_flag_count >= 2 and not outlier and not edge_case)
    note = (
        "Dixon r10 high-end statistic on the pre-specified upper tail of distance_rms; denominator is highest minus lowest score. "
        "The comparison uses conservative Rorabacher 95% critical values."
        if components["dixon_variant"] == "r10"
        else "Dixon r11 high-end statistic on the pre-specified upper tail of distance_rms; denominator is highest minus second-lowest score. "
        "The comparison uses conservative Rorabacher 95% critical values."
    )
    if components["tie_count"]:
        note += " Tied distance scores are present; Dixon tables assume continuous observations, so interpret as approximate screening evidence."
    if edge_case:
        note = "Dixon Q was not assessed because the denominator is zero; tied/discretized distance scores violate the continuous-score assumption."
    elif companion_flag_count:
        note += (
            f" A companion upper-tail MAD screen flagged {companion_flag_count} high-distance run(s); "
            "this is masking-risk review evidence and is not sequential Dixon retesting."
        )
    for row in score_rows:
        if not row.get("evaluable"):
            continue
        is_candidate = str(row.get("run_id") or "") == candidate_run
        run_id = str(row.get("run_id") or "")
        companion_row = companion_rows.get(run_id, {})
        companion_flag = bool(run_id in companion_run_ids and not edge_case)
        final_outlier = bool((outlier and is_candidate) or companion_flag)
        decision_sources = []
        if outlier and is_candidate:
            decision_sources.append("dixon")
        if companion_flag:
            decision_sources.append("mad_companion")
        row.update(
            {
                "threshold_method": policy.small_sample_method,
                "secondary_threshold_method": MAD_COMPANION_METHOD,
                "secondary_threshold_available": bool(companion.get("available")),
                "Qexp": qexp if is_candidate and not edge_case else "",
                "Qcrit_95": qcrit,
                "Qcrit_note": note,
                "dixon_variant": components["dixon_variant"],
                "dixon_gap": components["dixon_gap"] if is_candidate else "",
                "dixon_denominator": components["dixon_denominator"] if is_candidate else "",
                "dixon_denominator_low_run_id": components["dixon_denominator_low_run_id"],
                "dixon_denominator_low_score": components["dixon_denominator_low_score"],
                "threshold_observation_unit": "run_level_distance_rms",
                "pooled_raw_curve_points": False,
                "statistical_decision_role": "formal_single_outlier_test_with_robust_masking_screen",
                "outlier_test_tail": "upper_tail_only",
                "critical_value_basis": "conservative_rorabacher_95_percent",
                "outlier_test_scope": "single_most_distant_run",
                "sequential_retesting_supported": False,
                "dixon_decision": dixon_decision,
                "masking_companion_flag": companion_flag,
                "masking_companion_flag_count": companion_flag_count,
                "masking_risk": bool(companion_flag and masking_risk),
                "threshold_decision_sources": ";".join(decision_sources),
                "robust_z": companion_row.get("robust_z", ""),
                "z_mad": companion_row.get("z_mad", ""),
                "mad_upper_z": companion_row.get("mad_upper_z", ""),
                "z_mad_upper": companion_row.get("z_mad_upper", ""),
                "threshold_value": companion.get("threshold_value", policy.robust_z_threshold),
                "robust_center": companion.get("robust_center", ""),
                "robust_mad": companion.get("robust_mad", ""),
                "robust_scaled_mad": companion.get("robust_scaled_mad", ""),
                "threshold_edge_case": edge_case,
                "automatic_exclusion": False,
                "requires_physical_review": final_outlier,
                "diagnostic_classification": (
                    CURVE_SHAPE_NOT_ASSESSED
                    if edge_case
                    else CURVE_SHAPE_OUTLIER
                    if final_outlier
                    else CURVE_SHAPE_NORMAL
                ),
                "is_curve_shape_outlier": final_outlier,
            }
        )
    return score_rows, {
        "threshold_method": policy.small_sample_method,
        "secondary_threshold_method": MAD_COMPANION_METHOD,
        "secondary_threshold_available": bool(companion.get("available")),
        "effective_sample_size": n,
        "Qexp": qexp,
        "Qcrit_95": qcrit,
        "candidate_run_id": candidate_run,
        "dixon_decision": dixon_decision,
        "decision": (
            "not_assessed_zero_denominator"
            if edge_case
            else "outlier"
            if outlier or companion_flag_count
            else "no_outlier"
        ),
        "Qcrit_note": note,
        "requires_physical_review": bool(outlier or companion_flag_count),
        "masking_companion_flag_count": companion_flag_count,
        "masking_companion_run_ids": companion_run_ids if not edge_case else [],
        "masking_risk": masking_risk,
        "masking_risk_note": (
            "Multiple high-distance runs were flagged by the robust companion screen while Dixon did not reject the top run; "
            "paired extremes can shrink the Dixon numerator and mask each other."
            if masking_risk
            else ""
        ),
        "companion_screening_rule": "modified_z = 0.6745 * (distance_rms - median) / MAD; flag max(0, modified_z) > threshold",
        "robust_z_threshold": companion.get("robust_z_threshold", policy.robust_z_threshold),
        "max_mad_upper_z": companion.get("max_mad_upper_z", ""),
        "robust_center": companion.get("robust_center", ""),
        "robust_mad": companion.get("robust_mad", ""),
        "robust_scaled_mad": companion.get("robust_scaled_mad", ""),
        "threshold_value": companion.get("threshold_value", policy.robust_z_threshold),
        "companion_screen_reason": companion.get("reason", ""),
        **_statistical_process_context(policy, branch=policy.small_sample_method),
        "outlier_test_tail": "upper_tail_only",
        "critical_value_basis": "conservative_rorabacher_95_percent",
        "outlier_test_scope": "single_most_distant_run",
        "sequential_retesting_supported": False,
        "continuous_scores_no_ties": components["tie_count"] == 0,
        "tie_count": components["tie_count"],
        "threshold_edge_case": edge_case,
        **components,
    }


def _dixon_high_outlier_components(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(ranked)
    highest = float(ranked[-1]["distance_rms"])
    second_highest = float(ranked[-2]["distance_rms"])
    denominator_low_index = 0 if n <= 7 else 1
    denominator_low = float(ranked[denominator_low_index]["distance_rms"])
    variant = "r10" if n <= 7 else "r11"
    qcrit_table = DIXON_R10_QCRIT_95 if variant == "r10" else DIXON_R11_QCRIT_95
    denominator = highest - denominator_low
    gap = highest - second_highest
    qexp = gap / denominator if denominator > 0 else 0.0
    values = [float(row["distance_rms"]) for row in ranked]
    tie_count = len(values) - len(set(values))
    return {
        "dixon_variant": variant,
        "dixon_gap": gap,
        "dixon_denominator": denominator,
        "dixon_denominator_low_run_id": str(ranked[denominator_low_index].get("run_id") or ""),
        "dixon_denominator_low_score": denominator_low,
        "Qexp": qexp,
        "Qcrit_95": qcrit_table.get(n, 0.0),
        "tie_count": tie_count,
        "threshold_edge_case": "zero_dixon_denominator" if denominator <= 0 else "",
    }


def _mad_upper_tail_screen(evaluable: list[dict[str, Any]], policy: CurveThresholdPolicy) -> dict[str, Any]:
    n = len(evaluable)
    threshold = policy.robust_z_threshold
    distances = [float(row["distance_rms"]) for row in evaluable]
    center = float(median(distances)) if distances else ""
    base: dict[str, Any] = {
        "method": MAD_COMPANION_METHOD,
        "available": False,
        "effective_sample_size": n,
        "robust_z_threshold": threshold,
        "threshold_value": threshold,
        "robust_center": center,
        "robust_mad": "",
        "robust_scaled_mad": "",
        "max_mad_upper_z": "",
        "flagged_run_ids": [],
        "rows": {},
        "reason": "",
    }
    if n < MAD_COMPANION_MIN_N:
        base["reason"] = (
            f"Companion MAD masking screen not assessed because n<{MAD_COMPANION_MIN_N}; "
            "small MAD screens are unstable at this cohort size."
        )
        return base
    mad = float(median([abs(value - float(center)) for value in distances]))
    base["robust_mad"] = mad
    if mad <= 0:
        base["reason"] = (
            "Companion MAD masking screen not assessed because MAD=0; distance scores are tied or too discretized."
        )
        return base
    scaled_mad = mad / MAD_SCALE_FACTOR
    rows: dict[str, dict[str, Any]] = {}
    flagged_run_ids: list[str] = []
    max_score = 0.0
    for row in evaluable:
        run_id = str(row.get("run_id") or "")
        robust_z = MAD_SCALE_FACTOR * (float(row["distance_rms"]) - float(center)) / mad
        mad_upper_z = max(0.0, robust_z)
        max_score = max(max_score, mad_upper_z)
        flag = mad_upper_z > threshold
        if flag:
            flagged_run_ids.append(run_id)
        rows[run_id] = {
            "robust_z": robust_z,
            "z_mad": robust_z,
            "mad_upper_z": mad_upper_z,
            "z_mad_upper": mad_upper_z,
            "masking_companion_flag": flag,
        }
    flagged_run_ids = sorted(
        flagged_run_ids,
        key=lambda run_id: rows.get(run_id, {}).get("mad_upper_z", 0.0),
        reverse=True,
    )
    base.update(
        {
            "available": True,
            "robust_scaled_mad": scaled_mad,
            "max_mad_upper_z": max_score,
            "flagged_run_ids": flagged_run_ids,
            "rows": rows,
            "reason": "Companion upper-tail MAD screen used only to surface multiple-candidate masking risk.",
        }
    )
    return base


def _classify_robust_mad(
    score_rows: list[dict[str, Any]],
    evaluable: list[dict[str, Any]],
    policy: CurveThresholdPolicy,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    distances = [float(row["distance_rms"]) for row in evaluable]
    center = float(median(distances))
    mad = float(median([abs(value - center) for value in distances]))
    threshold = policy.robust_z_threshold
    if mad <= 0:
        note = (
            "Modified MAD z-score is undefined because MAD=0; distance scores are tied or too discretized. "
            "Use IQR/Qn/Sn screening or inspect aligned residuals instead of forcing a z-score."
        )
        for row in score_rows:
            if not row.get("evaluable") or row.get("distance_rms") is None:
                continue
            row.update(
                {
                    "threshold_method": policy.large_sample_method,
                    "robust_z": "",
                    "z_mad": "",
                    "mad_upper_z": "",
                    "z_mad_upper": "",
                    "threshold_value": threshold,
                    "robust_center": center,
                    "robust_mad": mad,
                    "robust_scaled_mad": "",
                    "Qcrit_note": note,
                    "threshold_observation_unit": "run_level_distance_rms",
                    "pooled_raw_curve_points": False,
                    "statistical_decision_role": "robust_screening_undefined",
                    "threshold_edge_case": "mad_zero",
                    "automatic_exclusion": False,
                    "requires_physical_review": False,
                    "diagnostic_classification": CURVE_SHAPE_NOT_ASSESSED,
                    "is_curve_shape_outlier": False,
                }
            )
        return score_rows, {
            "threshold_method": policy.large_sample_method,
            "effective_sample_size": len(evaluable),
            "robust_z_threshold": threshold,
            "max_robust_z": "",
            "max_mad_upper_z": "",
            "robust_center": center,
            "robust_mad": mad,
            "robust_scaled_mad": "",
            "threshold_value": threshold,
            "decision": "not_assessed_mad_zero",
            "reason": note,
            "threshold_edge_case": "mad_zero",
            "recommended_alternative": "IQR, Qn/Sn, Hampel/local residual screening, or functional review",
            **_statistical_process_context(policy, branch=policy.large_sample_method),
        }
    scale = mad
    scaled_mad = scale / MAD_SCALE_FACTOR
    max_score = 0.0
    for row in score_rows:
        if not row.get("evaluable") or row.get("distance_rms") is None:
            continue
        robust_z = MAD_SCALE_FACTOR * (float(row["distance_rms"]) - center) / scale
        mad_upper_z = max(0.0, robust_z)
        max_score = max(max_score, mad_upper_z)
        row.update(
            {
                "threshold_method": policy.large_sample_method,
                "robust_z": robust_z,
                "z_mad": robust_z,
                "mad_upper_z": mad_upper_z,
                "z_mad_upper": mad_upper_z,
                "threshold_value": threshold,
                "robust_center": center,
                "robust_mad": mad,
                "robust_scaled_mad": scaled_mad,
                "Qcrit_note": "Upper-tail modified MAD z-score screening on one distance_rms score per run; flagged runs require physical review before exclusion.",
                "threshold_observation_unit": "run_level_distance_rms",
                "pooled_raw_curve_points": False,
                "statistical_decision_role": "robust_screening",
                "outlier_test_tail": "upper_tail_only",
                "threshold_edge_case": "",
                "automatic_exclusion": False,
                "requires_physical_review": mad_upper_z > threshold,
                "diagnostic_classification": CURVE_SHAPE_OUTLIER if mad_upper_z > threshold else CURVE_SHAPE_NORMAL,
                "is_curve_shape_outlier": mad_upper_z > threshold,
            }
        )
    return score_rows, {
        "threshold_method": policy.large_sample_method,
        "effective_sample_size": len(evaluable),
        "robust_z_threshold": threshold,
        "max_robust_z": max_score,
        "max_mad_upper_z": max_score,
        "robust_center": center,
        "robust_mad": mad,
        "robust_scaled_mad": scaled_mad,
        "threshold_value": threshold,
        "decision": "outlier" if max_score > threshold else "no_outlier",
        "requires_physical_review": max_score > threshold,
        **_statistical_process_context(policy, branch=policy.large_sample_method),
        "outlier_test_tail": "upper_tail_only",
        "screening_rule": "modified_z = 0.6745 * (distance_rms - median) / MAD; flag max(0, modified_z) > threshold",
        "mad_zero_policy": "not_assessed_when_mad_zero",
    }


def _statistical_process_context(policy: CurveThresholdPolicy, *, branch: str) -> dict[str, Any]:
    return {
        "statistical_process": "curve_shape_outlier_screening",
        "threshold_branch": branch,
        "observation_unit": "one distance_rms feature per evaluable run",
        "pooled_raw_curve_points": False,
        "curve_preprocessing_required": "aligned curves on a common experiment-progress grid before residual distances are scored",
        "alpha": round(1.0 - policy.confidence, 6),
        "confidence": policy.confidence,
        "automatic_exclusion": False,
        "post_test_action": "statistical flags require operator/metrology review before removing any run",
        "single_vs_multiple_outliers": "Dixon branch tests only the single most distant run; no sequential Dixon retesting is performed",
        "mad_role": "robust screening rule, not a formal deletion test",
    }
