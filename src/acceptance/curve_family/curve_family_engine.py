from __future__ import annotations

from typing import Any

from acceptance.curve_family.alignment import align_curve_family
from acceptance.curve_family.classifier import classify_curve
from acceptance.curve_family.distance_metrics import distance_metrics, residual_rows
from acceptance.curve_family.influence_metrics import leave_one_out_mean_shift
from acceptance.curve_family.models import (
    ACCEPT,
    PROPOSE_REMOVE,
    REVIEW,
    CurveFamilyAssessment,
    CurveFamilyScore,
)
from acceptance.curve_family.reference_curve import pointwise_median_reference
from acceptance.curve_family.shape_metrics import shape_metrics


class CurveFamilyEngine:
    """Dataset-level curve-family assessment built from reduced curve outputs."""

    def evaluate(
        self,
        *,
        recipe_payload: dict[str, Any] | None,
        curve_family_rows: list[dict[str, Any]],
        selection_run_ids_by_context: dict[str, set[str]] | None = None,
    ) -> CurveFamilyAssessment:
        recipe = _curve_family_recipe(recipe_payload)
        families = recipe.get("curve_families") if isinstance(recipe.get("curve_families"), list) else []
        if not families:
            return CurveFamilyAssessment.empty()
        selection_run_ids_by_context = selection_run_ids_by_context or {}
        scores: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        reference_rows: list[dict[str, Any]] = []
        aligned_rows: list[dict[str, Any]] = []
        residuals: list[dict[str, Any]] = []
        family_reports: list[dict[str, Any]] = []
        warnings: list[str] = []
        for family in families:
            if not isinstance(family, dict):
                continue
            family_result = self._evaluate_family(
                family=family,
                curve_family_rows=curve_family_rows,
                selection_run_ids_by_context=selection_run_ids_by_context,
            )
            scores.extend(family_result["scores"])
            flags.extend(family_result["flags"])
            reference_rows.extend(family_result["reference_rows"])
            aligned_rows.extend(family_result["aligned_rows"])
            residuals.extend(family_result["residual_rows"])
            family_reports.append(family_result["report"])
            warnings.extend(family_result["warnings"])
        summary = _summary(scores)
        report = {
            "schema_id": "method.curve_family_report.v0_1",
            "recipe_id": recipe.get("id") or recipe.get("recipe_id"),
            "applies_to": recipe.get("applies_to"),
            "summary": summary,
            "curve_families": family_reports,
            "warnings": warnings,
            "acceptance_flag_ids": [str(flag.get("flag_id")) for flag in flags],
        }
        return CurveFamilyAssessment(
            report=report,
            scores=scores,
            flags=flags,
            reference_rows=reference_rows,
            aligned_rows=aligned_rows,
            residual_rows=residuals,
            policy_resolved={
                "schema_id": "method.curve_family_policy_resolved.v0_1",
                "recipe_id": recipe.get("id") or recipe.get("recipe_id"),
                "curve_families": families,
            },
        )

    def _evaluate_family(
        self,
        *,
        family: dict[str, Any],
        curve_family_rows: list[dict[str, Any]],
        selection_run_ids_by_context: dict[str, set[str]],
    ) -> dict[str, Any]:
        family_id = str(family.get("id") or "curve_family")
        selection_context = str(family.get("selection_context") or "user_valid_runs")
        selected_run_ids = selection_run_ids_by_context.get(selection_context)
        alignment = family.get("alignment") if isinstance(family.get("alignment"), dict) else {}
        mode = str(alignment.get("mode") or "normalized_progress")
        x_common_points = int(alignment.get("x_common_points") or family.get("x_common_points") or 250)
        x_field = str(family.get("x") or "mean_strain")
        y_field = str(family.get("y") or "stress_MPa")
        aligned, warnings = align_curve_family(
            curve_family_rows,
            curve_family_id=family_id,
            run_ids=selected_run_ids,
            x_field=x_field,
            y_field=y_field,
            mode=mode,
            x_common_points=x_common_points,
        )
        reference = pointwise_median_reference(aligned, curve_family_id=family_id)
        if reference is None:
            warnings.append(f"{family_id}: no reference curve could be constructed.")
            return _empty_family_result(family_id, selection_context, mode, warnings)
        influence = leave_one_out_mean_shift(aligned)
        scores: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        residual_output: list[dict[str, Any]] = []
        for curve in aligned:
            metrics = {}
            metrics.update(distance_metrics(curve.y_aligned, reference.y_reference))
            metrics.update(shape_metrics(curve.y_aligned, reference.y_reference))
            metrics["leave_one_out_mean_shift"] = influence.get(curve.run_id)
            classification, reason = classify_curve(metrics, family.get("classification") if isinstance(family.get("classification"), dict) else {})
            score = CurveFamilyScore(
                selection_context=selection_context,
                curve_family_id=family_id,
                run_id=curve.run_id,
                alignment_mode=curve.alignment_mode,
                reference_id=reference.reference_id,
                classification=classification,
                primary_reason=reason,
                **metrics,
            ).to_dict()
            scores.append(score)
            if classification != ACCEPT:
                flags.append(_flag_row(score))
            for index, residual in enumerate(residual_rows(curve.y_aligned, reference.y_reference)):
                residual_output.append(
                    {
                        "curve_family_id": family_id,
                        "run_id": curve.run_id,
                        "x_common": curve.x_common[index],
                        **residual,
                    }
                )
        return {
            "scores": scores,
            "flags": flags,
            "reference_rows": _reference_rows(reference),
            "aligned_rows": _aligned_rows(aligned),
            "residual_rows": residual_output,
            "warnings": warnings,
            "report": {
                "curve_family_id": family_id,
                "selection_context": selection_context,
                "alignment_mode": mode,
                "reference_id": reference.reference_id,
                "reference_type": reference.reference_type,
                "assessed_runs": len(aligned),
                "classifications": _summary(scores),
                "worst_ranked_runs": sorted(
                    scores,
                    key=lambda row: _sort_metric(row.get("normalized_rmse")),
                    reverse=True,
                )[:5],
                "warnings": warnings,
            },
        }


def _curve_family_recipe(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("curve_family_acceptance"), dict):
        return dict(payload["curve_family_acceptance"])
    return dict(payload)


def _flag_row(score: dict[str, Any]) -> dict[str, Any]:
    classification = str(score.get("classification"))
    proposed = classification == PROPOSE_REMOVE
    flag_type = "curve_family_propose_remove" if proposed else "curve_family_review"
    metric, value = _primary_metric(score)
    return {
        "run_id": score.get("run_id"),
        "flag_id": f"{flag_type}:{score.get('curve_family_id')}:{score.get('run_id')}",
        "flag_type": flag_type,
        "severity": "review",
        "classification": classification,
        "reason": score.get("primary_reason"),
        "metric": metric,
        "value": value,
        "threshold": "",
        "selection_context": score.get("selection_context"),
        "curve_family_id": score.get("curve_family_id"),
    }


def _primary_metric(score: dict[str, Any]) -> tuple[str, Any]:
    for key in ("normalized_rmse", "derivative_rmse", "leave_one_out_mean_shift", "curve_correlation"):
        value = score.get(key)
        if value not in (None, ""):
            return key, value
    return "", ""


def _reference_rows(reference: Any) -> list[dict[str, Any]]:
    return [
        {
            "curve_family_id": reference.curve_family_id,
            "reference_id": reference.reference_id,
            "x_common": reference.x_common[index],
            "y_reference": y_value,
            "reference_type": reference.reference_type,
            "n_observations": reference.n_observations[index],
        }
        for index, y_value in enumerate(reference.y_reference)
    ]


def _aligned_rows(aligned: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for curve in aligned:
        for index, y_value in enumerate(curve.y_aligned):
            rows.append(
                {
                    "curve_family_id": curve.curve_family_id,
                    "run_id": curve.run_id,
                    "x_common": curve.x_common[index],
                    "y_aligned": y_value,
                    "alignment_mode": curve.alignment_mode,
                    "included_in_reference": curve.included_in_reference,
                }
            )
    return rows


def _summary(scores: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "curve_family_count": len({str(score.get("curve_family_id")) for score in scores}) if scores else 0,
        "assessed_runs": len(scores),
        "accepted": sum(1 for score in scores if score.get("classification") == ACCEPT),
        "review": sum(1 for score in scores if score.get("classification") == REVIEW),
        "propose_remove": sum(1 for score in scores if score.get("classification") == PROPOSE_REMOVE),
    }


def _empty_family_result(
    family_id: str,
    selection_context: str,
    mode: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "scores": [],
        "flags": [],
        "reference_rows": [],
        "aligned_rows": [],
        "residual_rows": [],
        "warnings": warnings,
        "report": {
            "curve_family_id": family_id,
            "selection_context": selection_context,
            "alignment_mode": mode,
            "assessed_runs": 0,
            "classifications": _summary([]),
            "warnings": warnings,
        },
    }


def _sort_metric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
