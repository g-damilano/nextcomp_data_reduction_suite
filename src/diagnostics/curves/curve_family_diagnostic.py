from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from diagnostics.curves.alignment import align_curves
from diagnostics.curves.artifacts import ARTIFACT_PATHS, artifact_manifest
from diagnostics.curves.cohorting import group_curves
from diagnostics.curves.distance_metrics import (
    max_abs_residual,
    normalized_mae,
    normalized_rmse,
    rms,
    standardized_residuals,
)
from diagnostics.curves.models import (
    CURVE_SHAPE_NOT_ASSESSED,
    CURVE_SHAPE_OUTLIER,
    INSUFFICIENT_CURVE_DATA,
    CurveAlignmentPolicy,
    CurveCohortPolicy,
    CurveDiagnosticResult,
    CurveReferencePolicy,
    CurveSeries,
    CurveThresholdPolicy,
)
from diagnostics.curves.reference_curve import reference_curve
from diagnostics.curves.thresholding import classify_distances


class CurveFamilyDiagnostic:
    """Generic curve-shape diagnostic for comparable reduced curve families."""

    def evaluate(
        self,
        *,
        curve_rows: list[dict[str, Any]],
        specimen_results: list[dict[str, Any]] | None = None,
        policy_payload: Mapping[str, Any] | None = None,
    ) -> CurveDiagnosticResult:
        policy_payload = policy_payload or {}
        curve_source = _curve_source(policy_payload)
        cohort_policy = _cohort_policy(policy_payload)
        alignment_policy = _alignment_policy(policy_payload)
        reference_policy = _reference_policy(policy_payload)
        threshold_policy = _threshold_policy(policy_payload)
        specimen_by_run = {
            str(row.get("run_id")): row
            for row in specimen_results or []
            if isinstance(row, dict) and row.get("run_id")
        }
        curves = _series_from_rows(curve_rows, curve_source, specimen_by_run)
        cohorts = group_curves(curves, cohort_policy)
        scores: list[dict[str, Any]] = []
        reference_rows: list[dict[str, Any]] = []
        residual_rows: list[dict[str, Any]] = []
        cohort_reports: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        for cohort in cohorts.values():
            cohort_id = str(cohort["cohort_id"])
            cohort_label = str(cohort["cohort_label"])
            cohort_curves = [curve for curve in cohort["curves"] if isinstance(curve, CurveSeries)]
            for curve in cohort_curves:
                curve.metadata["cohort_id"] = cohort_id
            evaluable_curves = [curve for curve in cohort_curves if len(curve.x) >= 2 and len(curve.y) >= 2]
            insufficient_curves = [curve for curve in cohort_curves if curve not in evaluable_curves]
            x_grid, aligned, aligned_rows = align_curves(evaluable_curves, alignment_policy)
            reference, variability = reference_curve(aligned, reference_policy)
            for row in aligned_rows:
                row["cohort_id"] = cohort_id
            for index, (x_value, ref_value) in enumerate(zip(x_grid, reference, strict=False)):
                reference_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "cohort_label": cohort_label,
                        "x_common": x_value,
                        "y_reference": ref_value,
                        "y_variability": variability[index] if index < len(variability) else None,
                        "y_lower": ref_value - variability[index] if index < len(variability) else None,
                        "y_upper": ref_value + variability[index] if index < len(variability) else None,
                        "support_n": len(aligned),
                        "reference_curve": reference_policy.curve,
                        "variability": reference_policy.variability,
                    }
                )
            cohort_scores: list[dict[str, Any]] = []
            for curve in evaluable_curves:
                values = aligned.get(curve.run_id)
                if not values or not reference:
                    continue
                residuals = standardized_residuals(values, reference, variability)
                distance = rms(residuals)
                metrics = {
                    "normalized_rmse": normalized_rmse(values, reference),
                    "normalized_mae": normalized_mae(values, reference),
                    "max_abs_residual": max_abs_residual(residuals),
                }
                cohort_scores.append(
                    {
                        "run_id": curve.run_id,
                        "specimen": curve.metadata.get("specimen_name", ""),
                        "sample_id": curve.metadata.get("sample_id", ""),
                        "cohort_id": cohort_id,
                        "cohort_label": cohort_label,
                        "evaluable": True,
                        "distance_rms": distance,
                        "distance_note": "RMS standardized residual distance.",
                        "effective_sample_size": len(evaluable_curves),
                        "diagnostic_classification": CURVE_SHAPE_NOT_ASSESSED,
                        **metrics,
                    }
                )
                for x_value, observed, ref_value, scale, z_value in zip(x_grid, values, reference, variability, residuals, strict=False):
                    residual_rows.append(
                        {
                            "run_id": curve.run_id,
                            "cohort_id": cohort_id,
                            "x_common": x_value,
                            "y_observed": observed,
                            "y_reference": ref_value,
                            "y_variability": scale,
                            "standardized_residual": z_value,
                            "diagnostic_classification": CURVE_SHAPE_NOT_ASSESSED,
                        }
                    )
            ranked = sorted(
                [row for row in cohort_scores if row.get("distance_rms") is not None],
                key=lambda row: float(row["distance_rms"]),
                reverse=True,
            )
            for index, row in enumerate(ranked, start=1):
                row["distance_rank"] = index
            cohort_scores, threshold_summary = classify_distances(cohort_scores, threshold_policy)
            for curve in insufficient_curves:
                cohort_scores.append(
                    {
                        "run_id": curve.run_id,
                        "specimen": curve.metadata.get("specimen_name", ""),
                        "sample_id": curve.metadata.get("sample_id", ""),
                        "cohort_id": cohort_id,
                        "cohort_label": cohort_label,
                        "evaluable": False,
                        "distance_rms": None,
                        "distance_rank": None,
                        "distance_note": "Insufficient curve data for alignment.",
                        "threshold_method": "not_assessed",
                        "diagnostic_classification": INSUFFICIENT_CURVE_DATA,
                        "is_curve_shape_outlier": False,
                        "effective_sample_size": len(evaluable_curves),
                    }
                )
            scores.extend(cohort_scores)
            cohort_reports.append(
                {
                    "cohort_id": cohort_id,
                    "cohort_label": cohort_label,
                    "cohort_definition": _cohort_definition(cohort_policy, cohort["cohort_key"]),
                    "total_runs": len(cohort_curves),
                    "evaluable_curves": len(evaluable_curves),
                    "insufficient_curve_data": len(insufficient_curves),
                    "not_assessed": sum(1 for row in cohort_scores if row.get("diagnostic_classification") == CURVE_SHAPE_NOT_ASSESSED),
                    "threshold_branch_used": threshold_summary.get("threshold_method"),
                    "threshold_branch_reason": _threshold_reason(threshold_summary),
                    "threshold_summary": threshold_summary,
                }
            )
            if len(evaluable_curves) < cohort_policy.minimum_evaluable_curves:
                warnings.append(
                    {
                        "cohort_id": cohort_id,
                        "warning": "insufficient_evaluable_curves",
                        "minimum_evaluable_curves": cohort_policy.minimum_evaluable_curves,
                        "evaluable_curves": len(evaluable_curves),
                    }
                )
        flags = tuple(_flags_from_scores(scores))
        report = {
            "schema_id": "diagnostics.curve_family_diagnostic_report.v0_1",
            "operation_type": "curve_family_diagnostic",
            "summary": {
                "cohort_count": len(cohort_reports),
                "total_runs": len(curves),
                "evaluable_runs": sum(1 for row in scores if row.get("evaluable")),
                "curve_shape_outliers": sum(1 for row in scores if row.get("diagnostic_classification") == CURVE_SHAPE_OUTLIER),
                "insufficient_curve_data": sum(1 for row in scores if row.get("diagnostic_classification") == INSUFFICIENT_CURVE_DATA),
                "insufficient_cohort_size": sum(1 for row in scores if row.get("diagnostic_classification") == "INSUFFICIENT_COHORT_SIZE"),
                "threshold_methods": sorted({str(row.get("threshold_method") or "") for row in scores if row.get("threshold_method")}),
            },
            "preprocessing": _preprocessing_report(curves, curve_source),
            "method_explanation": (
                "Each reduced stress-strain curve is compared against the cohort reference curve. "
                "The score is the RMS of local standardized residuals: z(x) = "
                "[stress_run(x) - cohort_mean(x)] / cohort_std(x); "
                "distance_rms = sqrt(mean(z(x)^2)). Statistical thresholding is applied to this one run-level "
                "feature per specimen/run, not to pooled raw curve points."
            ),
            "threshold_policy_statement": (
                "If 3 <= n <= 10, use the Dixon high-outlier Q-test: r10 for n=3..7 and r11 for n=8..10. "
                "Dixon is used only for the single most distant curve and is not applied sequentially. "
                "A one-sided MAD companion screen is also reported for small cohorts when defined, to surface "
                "multiple high-distance candidates that can mask the Dixon numerator. "
                "If n > 10, use the upper-tail modified MAD score as robust screening; if MAD=0, mark the "
                "statistic undefined instead of forcing a z-score. If n < 3, mark insufficient cohort size. "
                "Any statistical flag requires operator/metrology review before exclusion."
            ),
            "cohorts": cohort_reports,
            "artifact_manifest": artifact_manifest(),
            "warnings": warnings,
        }
        return CurveDiagnosticResult(
            report=report,
            scores=tuple(scores),
            reference_rows=tuple(reference_rows),
            residual_rows=tuple(residual_rows),
            policy_resolved=_policy_resolved(curve_source, cohort_policy, alignment_policy, reference_policy, threshold_policy),
            flags=flags,
        )


def _curve_source(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = payload.get("curve_source") if isinstance(payload.get("curve_source"), Mapping) else {}
    preprocessing = payload.get("preprocessing") if isinstance(payload.get("preprocessing"), Mapping) else {}
    return {
        "x": str(source.get("x") or "experiment_progress"),
        "y": str(source.get("y") or "stress_MPa"),
        "load": str(source.get("load") or "load_N"),
        "preprocessing": {
            "start_policy": str(preprocessing.get("start_policy") or "none"),
            "min_load_fraction_of_max": _bounded_fraction(preprocessing.get("min_load_fraction_of_max")),
            "scope": str(preprocessing.get("scope") or "resolved_experiment_interval"),
        },
    }


def _cohort_policy(payload: Mapping[str, Any]) -> CurveCohortPolicy:
    raw = payload.get("cohort_policy") if isinstance(payload.get("cohort_policy"), Mapping) else {}
    group_by = raw.get("group_by", ())
    return CurveCohortPolicy(
        group_by=tuple(str(item) for item in group_by) if isinstance(group_by, list | tuple) else (),
        default_grouping=str(raw.get("default_grouping") or "whole_comparable_dataset"),
        minimum_evaluable_curves=int(raw.get("minimum_evaluable_curves") or 3),
    )


def _alignment_policy(payload: Mapping[str, Any]) -> CurveAlignmentPolicy:
    raw = payload.get("alignment_policy") if isinstance(payload.get("alignment_policy"), Mapping) else {}
    return CurveAlignmentPolicy(
        domain=str(raw.get("domain") or "resolved_experiment_interval"),
        resample_points=int(raw.get("resample_points") or 250),
        interpolation_mode=str(raw.get("interpolation_mode") or "linear"),
    )


def _reference_policy(payload: Mapping[str, Any]) -> CurveReferencePolicy:
    raw = payload.get("reference_policy") if isinstance(payload.get("reference_policy"), Mapping) else {}
    return CurveReferencePolicy(
        curve=str(raw.get("curve") or "mean"),
        variability=str(raw.get("variability") or "std"),
    )


def _threshold_policy(payload: Mapping[str, Any]) -> CurveThresholdPolicy:
    raw = payload.get("threshold_policy") if isinstance(payload.get("threshold_policy"), Mapping) else {}
    return CurveThresholdPolicy(
        robust_z_threshold=float(raw.get("robust_z_threshold") or 3.5),
    )


def _series_from_rows(
    curve_rows: list[dict[str, Any]],
    source: Mapping[str, Any],
    specimen_by_run: Mapping[str, Mapping[str, Any]],
) -> list[CurveSeries]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in curve_rows:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        if run_id:
            grouped.setdefault(run_id, []).append(row)
    curves: list[CurveSeries] = []
    for run_id, rows in grouped.items():
        rows, preprocessing_meta = _apply_start_preprocessing(rows, source)
        x_values: list[float] = []
        y_values: list[float] = []
        for index, row in enumerate(rows):
            x_value = _as_float(row.get(source["x"]))
            if x_value is None:
                x_value = _fallback_x(row, index, len(rows))
            y_value = _as_float(row.get(source["y"]))
            if x_value is None or y_value is None:
                continue
            x_values.append(float(x_value))
            y_values.append(float(y_value))
        metadata = dict(specimen_by_run.get(run_id, {}))
        metadata.setdefault("run_id", run_id)
        metadata["curve_shape_preprocessing"] = preprocessing_meta
        curves.append(CurveSeries(run_id=run_id, x=tuple(x_values), y=tuple(y_values), metadata=metadata))
    return curves


def _apply_start_preprocessing(
    rows: list[dict[str, Any]],
    source: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    preprocessing = source.get("preprocessing")
    preprocessing = preprocessing if isinstance(preprocessing, Mapping) else {}
    policy = str(preprocessing.get("start_policy") or "none")
    if policy != "load_fraction_of_max":
        return rows, {"start_policy": policy, "excluded_leading_points": 0}
    load_key = str(source.get("load") or "load_N")
    numeric_loads = [_as_float(row.get(load_key)) for row in rows]
    finite_loads = [abs(float(value)) for value in numeric_loads if value is not None]
    if not finite_loads:
        return rows, {
            "start_policy": policy,
            "load_series": load_key,
            "excluded_leading_points": 0,
            "warning": "load series unavailable for diagnostic start preprocessing",
        }
    max_load = max(finite_loads)
    fraction = _bounded_fraction(preprocessing.get("min_load_fraction_of_max"))
    if max_load <= 0 or fraction <= 0:
        return rows, {
            "start_policy": policy,
            "load_series": load_key,
            "min_load_fraction_of_max": fraction,
            "threshold_abs_load": 0.0,
            "excluded_leading_points": 0,
        }
    threshold = max_load * fraction
    start_offset = 0
    for index, value in enumerate(numeric_loads):
        if value is not None and abs(float(value)) >= threshold:
            start_offset = index
            break
    trimmed = rows[start_offset:] if start_offset else rows
    return trimmed, {
        "start_policy": policy,
        "load_series": load_key,
        "min_load_fraction_of_max": fraction,
        "threshold_abs_load": threshold,
        "excluded_leading_points": start_offset,
        "input_point_count": len(rows),
        "output_point_count": len(trimmed),
    }


def _fallback_x(row: Mapping[str, Any], index: int, count: int) -> float | None:
    for key in ("strain_mm_per_mm", "mean_strain", "time_s", "point_index"):
        value = _as_float(row.get(key))
        if value is not None:
            return value
    if count > 1:
        return index / (count - 1)
    return None


def _flags_from_scores(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    for row in scores:
        classification = str(row.get("diagnostic_classification") or "")
        if classification == CURVE_SHAPE_OUTLIER:
            flag_type = "curve_shape_outlier_review"
            if row.get("masking_companion_flag") and str(row.get("dixon_decision") or "") == "no_outlier":
                reason = (
                    "Curve-shape diagnostic flagged this run by the robust masking companion screen; "
                    "Dixon did not reject the single top-distance candidate."
                )
            elif row.get("masking_companion_flag"):
                reason = "Curve-shape diagnostic flagged this run by the robust masking companion screen."
            else:
                reason = "Curve-shape diagnostic identified a cohort-shape outlier."
        elif classification == INSUFFICIENT_CURVE_DATA:
            flag_type = "insufficient_curve_data"
            reason = "Curve-shape diagnostic had insufficient curve data for this run."
        elif classification == "INSUFFICIENT_COHORT_SIZE":
            flag_type = "insufficient_curve_cohort_size"
            reason = "Curve-shape diagnostic cohort has insufficient evaluable curves."
        else:
            continue
        run_id = str(row.get("run_id") or "")
        flags.append(
            {
                "flag_id": f"{flag_type}:{run_id}",
                "flag_type": flag_type,
                "run_id": run_id,
                "source": "curve_family_diagnostic",
                "category": "curve_shape_diagnostic",
                "severity": "info",
                "reason": reason,
                "classification": classification,
                "cohort_id": row.get("cohort_id"),
                "value": row.get("distance_rms"),
                "threshold": row.get("Qcrit_95") or row.get("threshold_value"),
                "evidence_refs": [
                    f"{ARTIFACT_PATHS['scores']}:{run_id}",
                    f"{ARTIFACT_PATHS['residuals']}:{run_id}",
                ],
            }
        )
    return flags


def _policy_resolved(
    curve_source: Mapping[str, Any],
    cohort_policy: CurveCohortPolicy,
    alignment_policy: CurveAlignmentPolicy,
    reference_policy: CurveReferencePolicy,
    threshold_policy: CurveThresholdPolicy,
) -> dict[str, Any]:
    return {
        "schema_id": "diagnostics.curve_family_diagnostic_policy.v0_1",
        "operation_type": "curve_family_diagnostic",
        "curve_source": {
            "x": curve_source.get("x"),
            "y": curve_source.get("y"),
            "load": curve_source.get("load"),
        },
        "preprocessing": (
            dict(curve_source.get("preprocessing"))
            if isinstance(curve_source.get("preprocessing"), Mapping)
            else {"start_policy": "none"}
        ),
        "cohort_policy": {
            "group_by": list(cohort_policy.group_by),
            "default_grouping": cohort_policy.default_grouping,
            "minimum_evaluable_curves": cohort_policy.minimum_evaluable_curves,
        },
        "alignment_policy": {
            "domain": alignment_policy.domain,
            "resample_points": alignment_policy.resample_points,
            "interpolation_mode": alignment_policy.interpolation_mode,
        },
        "reference_policy": {
            "curve": reference_policy.curve,
            "variability": reference_policy.variability,
        },
        "distance_policy": {
            "primary_metric": "rms_standardized_residual",
            "supporting_metrics": [
                "normalized_rmse",
                "normalized_mae",
                "max_abs_residual",
                "derivative_rmse",
                "correlation",
            ],
        },
        "threshold_policy": {
            "if_3_to_10": threshold_policy.small_sample_method,
            "dixon_variant_by_sample_size": {
                "3_to_7": "r10 = (x_n - x_(n-1)) / (x_n - x_1)",
                "8_to_10": "r11 = (x_n - x_(n-1)) / (x_n - x_2)",
            },
            "dixon_scope": "single most distant run only; no sequential retesting for multiple outliers",
            "dixon_tail": "upper tail only because distance_rms is a non-negative difference score",
            "small_cohort_companion_screen": "upper-tail modified MAD screen on distance_rms to surface masking risk",
            "companion_screen_role": "robust labeling evidence only; not a formal Dixon retest or automatic deletion rule",
            "if_gt_10": threshold_policy.large_sample_method,
            "mad_role": "modified z-score screening on run-level distance_rms, not automatic deletion",
            "mad_zero_policy": "mark not assessed and recommend robust alternatives instead of epsilon scaling",
            "if_lt_3": threshold_policy.insufficient_method,
            "observation_unit": "one distance_rms feature per evaluable run",
            "pooled_raw_curve_points": False,
            "automatic_exclusion": False,
            "post_test_action": "physical/metrology review before excluding a run",
            "robust_z_threshold": threshold_policy.robust_z_threshold,
            "confidence": threshold_policy.confidence,
        },
        "insufficient_data_policy": {
            "classify_as": INSUFFICIENT_CURVE_DATA,
            "emit_evidence": True,
            "do_not_drop_silently": True,
        },
        "artifact_paths": dict(ARTIFACT_PATHS),
    }


def _preprocessing_report(curves: list[CurveSeries], curve_source: Mapping[str, Any]) -> dict[str, Any]:
    preprocessing = curve_source.get("preprocessing")
    preprocessing = preprocessing if isinstance(preprocessing, Mapping) else {}
    rows = [
        curve.metadata.get("curve_shape_preprocessing")
        for curve in curves
        if isinstance(curve.metadata.get("curve_shape_preprocessing"), dict)
    ]
    excluded = [
        int(row.get("excluded_leading_points") or 0)
        for row in rows
        if isinstance(row, dict)
    ]
    return {
        "scope": preprocessing.get("scope") or "curve_shape_diagnostic_only",
        "start_policy": preprocessing.get("start_policy") or "none",
        "min_load_fraction_of_max": preprocessing.get("min_load_fraction_of_max"),
        "load_series": curve_source.get("load"),
        "runs_with_excluded_leading_points": sum(1 for value in excluded if value > 0),
        "total_excluded_leading_points": sum(excluded),
    }


def _cohort_definition(policy: CurveCohortPolicy, key: Any) -> str:
    if not policy.group_by:
        return "Whole comparable dataset: same package, method, sample/material family where available, analysis interval policy, and curve domain."
    return "Grouped by " + ", ".join(policy.group_by) + f": {key}"


def _threshold_reason(summary: Mapping[str, Any]) -> str:
    method = str(summary.get("threshold_method") or "")
    n = summary.get("effective_sample_size")
    decision = str(summary.get("decision") or "")
    reason = str(summary.get("reason") or "")
    if decision.startswith("not_assessed"):
        return f"Threshold branch selected for evaluable cohort size n={n}, but no statistical decision was made: {reason or decision}."
    if method == "dixon_high_outlier_q_test":
        companion_count = int(summary.get("masking_companion_flag_count") or 0)
        companion_note = (
            f" Companion MAD screen flagged {companion_count} high-distance run(s) for masking-risk review."
            if companion_count
            else ""
        )
        return (
            f"Dixon branch used because evaluable cohort size is {n}; it tests only the single most distant run."
            f"{companion_note}"
        )
    if method == "robust_mad_zscore":
        return f"Upper-tail robust MAD screening branch used because evaluable cohort size is {n}."
    return f"Insufficient cohort-size branch used because evaluable cohort size is {n}."


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded_fraction(value: Any) -> float:
    numeric = _as_float(value)
    if numeric is None:
        return 0.0
    return max(0.0, min(1.0, numeric))
