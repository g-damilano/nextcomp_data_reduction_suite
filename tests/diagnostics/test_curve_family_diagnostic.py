from __future__ import annotations

import pytest

from diagnostics.curves import CurveFamilyDiagnostic
from diagnostics.curves.models import CurveThresholdPolicy
from diagnostics.curves.thresholding import classify_distances


def _curve_rows(run_id: str, scale: float = 1.0, *, group: str = "A", points: int = 60) -> list[dict[str, object]]:
    rows = []
    for index in range(points):
        x = index / (points - 1)
        base = 10.0 + 180.0 * x
        shape = base * scale
        if scale > 1.5 and x > 0.55:
            shape += 150.0 * (x - 0.55)
        rows.append(
            {
                "run_id": run_id,
                "experiment_progress": x,
                "stress_MPa": shape,
                "group": group,
            }
        )
    return rows


def test_synthetic_curve_shape_outlier_is_detected_with_dixon_branch() -> None:
    rows = []
    specimens = []
    for index in range(6):
        run_id = f"run_{index + 1:03d}"
        scale = 1.0 if index < 5 else 1.85
        rows.extend(_curve_rows(run_id, scale=scale))
        specimens.append({"run_id": run_id, "specimen_name": f"specimen-{index + 1}"})

    result = CurveFamilyDiagnostic().evaluate(curve_rows=rows, specimen_results=specimens)
    scores = {row["run_id"]: row for row in result.scores}

    assert result.report["summary"]["threshold_methods"] == ["dixon_high_outlier_q_test"]
    assert scores["run_006"]["diagnostic_classification"] == "CURVE_SHAPE_OUTLIER"
    assert scores["run_006"]["Qexp"] != ""
    assert scores["run_006"]["Qcrit_95"] != ""


@pytest.mark.parametrize(
    ("n", "variant", "denominator_low_index", "qcrit"),
    [
        (3, "r10", 0, 0.970),
        (4, "r10", 0, 0.829),
        (5, "r10", 0, 0.710),
        (6, "r10", 0, 0.625),
        (7, "r10", 0, 0.568),
        (8, "r11", 1, 0.615),
        (9, "r11", 1, 0.570),
        (10, "r11", 1, 0.534),
    ],
)
def test_dixon_high_outlier_uses_order_statistic_definition_for_supported_small_cohorts(
    n: int,
    variant: str,
    denominator_low_index: int,
    qcrit: float,
) -> None:
    distances = [float(index) for index in range(n - 1)] + [200.0]
    rows = [_score_row(f"run_{index + 1:03d}", value) for index, value in enumerate(distances)]

    classified, summary = classify_distances(rows, CurveThresholdPolicy())
    candidate = next(row for row in classified if row["run_id"] == f"run_{n:03d}")

    expected_gap = distances[-1] - distances[-2]
    expected_denominator = distances[-1] - distances[denominator_low_index]
    assert summary["dixon_variant"] == variant
    assert summary["dixon_gap"] == pytest.approx(expected_gap)
    assert summary["dixon_denominator"] == pytest.approx(expected_denominator)
    assert summary["Qexp"] == pytest.approx(expected_gap / expected_denominator)
    assert summary["Qcrit_95"] == pytest.approx(qcrit)
    assert summary["dixon_denominator_low_run_id"] == f"run_{denominator_low_index + 1:03d}"
    assert summary["observation_unit"] == "one distance_rms feature per evaluable run"
    assert summary["pooled_raw_curve_points"] is False
    assert summary["sequential_retesting_supported"] is False
    assert summary["critical_value_basis"] == "conservative_rorabacher_95_percent"
    assert candidate["Qexp"] == pytest.approx(expected_gap / expected_denominator)
    assert candidate["automatic_exclusion"] is False
    assert candidate["outlier_test_scope"] == "single_most_distant_run"
    assert candidate["critical_value_basis"] == "conservative_rorabacher_95_percent"
    assert candidate["is_curve_shape_outlier"] is True


def test_dixon_zero_denominator_is_not_forced_into_outlier_decision() -> None:
    rows = [_score_row(f"run_{index + 1:03d}", 1.0) for index in range(5)]

    classified, summary = classify_distances(rows, CurveThresholdPolicy())

    assert summary["decision"] == "not_assessed_zero_denominator"
    assert summary["threshold_edge_case"] == "zero_dixon_denominator"
    assert summary["tie_count"] == 4
    assert all(row["diagnostic_classification"] == "CURVE_SHAPE_NOT_ASSESSED" for row in classified)
    assert all(row["is_curve_shape_outlier"] is False for row in classified)


def test_dixon_branch_surfaces_paired_high_distance_masking_with_mad_companion() -> None:
    distances = [
        ("run_007", 0.4200),
        ("run_002", 0.4541),
        ("run_006", 0.4900),
        ("run_005", 0.5000),
        ("run_003", 0.5184),
        ("run_001", 0.5945),
        ("run_008", 0.6100),
        ("run_010", 0.7800),
        ("run_009", 1.6320),
        ("run_004", 1.9690),
    ]
    rows = [_score_row(run_id, distance) for run_id, distance in distances]

    classified, summary = classify_distances(rows, CurveThresholdPolicy())
    by_run = {row["run_id"]: row for row in classified}

    assert summary["dixon_decision"] == "no_outlier"
    assert summary["Qexp"] == pytest.approx(0.337 / 1.5149)
    assert summary["Qexp"] < summary["Qcrit_95"]
    assert summary["secondary_threshold_method"] == "robust_mad_masking_screen"
    assert summary["masking_companion_flag_count"] == 2
    assert summary["masking_companion_run_ids"] == ["run_004", "run_009"]
    assert summary["masking_risk"] is True
    assert summary["automatic_exclusion"] is False
    assert by_run["run_004"]["diagnostic_classification"] == "CURVE_SHAPE_OUTLIER"
    assert by_run["run_009"]["diagnostic_classification"] == "CURVE_SHAPE_OUTLIER"
    assert by_run["run_004"]["threshold_decision_sources"] == "mad_companion"
    assert by_run["run_009"]["threshold_decision_sources"] == "mad_companion"
    assert by_run["run_004"]["masking_risk"] is True
    assert by_run["run_009"]["masking_risk"] is True
    assert by_run["run_010"]["diagnostic_classification"] == "CURVE_SHAPE_NORMAL"
    assert by_run["run_004"]["mad_upper_z"] > 3.5
    assert by_run["run_009"]["mad_upper_z"] > 3.5
    assert all(row["automatic_exclusion"] is False for row in classified)


def test_synthetic_normal_cohort_has_no_false_outlier() -> None:
    rows = []
    for index in range(5):
        rows.extend(_curve_rows(f"run_{index + 1:03d}", scale=1.0 + index * 0.002))

    result = CurveFamilyDiagnostic().evaluate(curve_rows=rows)

    assert all(row["diagnostic_classification"] == "CURVE_SHAPE_NORMAL" for row in result.scores)


def test_insufficient_curve_data_is_surfaced_explicitly() -> None:
    rows = _curve_rows("run_001") + [{"run_id": "run_002", "experiment_progress": 0.0, "stress_MPa": 1.0}]

    result = CurveFamilyDiagnostic().evaluate(curve_rows=rows)
    scores = {row["run_id"]: row for row in result.scores}

    assert scores["run_002"]["diagnostic_classification"] == "INSUFFICIENT_CURVE_DATA"
    assert result.flags


def test_robust_mad_branch_is_used_for_larger_cohorts() -> None:
    rows = []
    for index in range(12):
        rows.extend(_curve_rows(f"run_{index + 1:03d}", scale=1.0 + index * 0.001))

    result = CurveFamilyDiagnostic().evaluate(curve_rows=rows)

    assert {row["threshold_method"] for row in result.scores} == {"robust_mad_zscore"}
    assert all("robust_z" in row for row in result.scores)
    assert all("z_mad" in row for row in result.scores)
    assert all("mad_upper_z" in row for row in result.scores)
    assert all(row["mad_upper_z"] >= 0 for row in result.scores)
    assert all(row["threshold_value"] == 3.5 for row in result.scores)
    assert all("robust_scaled_mad" in row for row in result.scores)
    assert all(row["statistical_decision_role"] == "robust_screening" for row in result.scores)
    assert all(row["automatic_exclusion"] is False for row in result.scores)
    assert result.report["cohorts"][0]["threshold_summary"]["robust_scaled_mad"] > 0
    assert result.report["cohorts"][0]["threshold_summary"]["mad_role"] == "robust screening rule, not a formal deletion test"


def test_robust_mad_zero_is_reported_as_undefined_screening() -> None:
    rows = [_score_row(f"run_{index + 1:03d}", 1.0) for index in range(11)]

    classified, summary = classify_distances(rows, CurveThresholdPolicy())

    assert summary["decision"] == "not_assessed_mad_zero"
    assert summary["threshold_edge_case"] == "mad_zero"
    assert summary["recommended_alternative"]
    assert all(row["diagnostic_classification"] == "CURVE_SHAPE_NOT_ASSESSED" for row in classified)
    assert all(row["robust_z"] == "" for row in classified)


def test_cohort_grouping_can_be_configured_by_metadata_field() -> None:
    rows = []
    specimens = []
    for index in range(3):
        run_id = f"a_{index}"
        rows.extend(_curve_rows(run_id, group="A"))
        specimens.append({"run_id": run_id, "batch": "A"})
    for index in range(3):
        run_id = f"b_{index}"
        rows.extend(_curve_rows(run_id, scale=1.2, group="B"))
        specimens.append({"run_id": run_id, "batch": "B"})

    result = CurveFamilyDiagnostic().evaluate(
        curve_rows=rows,
        specimen_results=specimens,
        policy_payload={"cohort_policy": {"group_by": ["batch"]}},
    )

    cohort_ids = {row["cohort_id"] for row in result.scores}
    assert cohort_ids == {"batch=A", "batch=B"}


def test_no_gauge_grouping_happens_unless_configured() -> None:
    rows = []
    specimens = []
    for index, gauge in enumerate([50, 50, 75, 75]):
        run_id = f"run_{index}"
        rows.extend(_curve_rows(run_id))
        specimens.append({"run_id": run_id, "gauge_length_mm": gauge})

    default_result = CurveFamilyDiagnostic().evaluate(curve_rows=rows, specimen_results=specimens)
    grouped_result = CurveFamilyDiagnostic().evaluate(
        curve_rows=rows,
        specimen_results=specimens,
        policy_payload={"cohort_policy": {"group_by": ["gauge_length_mm"]}},
    )

    assert {row["cohort_id"] for row in default_result.scores} == {"whole_comparable_dataset"}
    assert {row["cohort_id"] for row in grouped_result.scores} == {"gauge_length_mm=50", "gauge_length_mm=75"}


def test_diagnostic_can_run_with_generic_x_y_series() -> None:
    rows = []
    for index in range(4):
        for point in range(20):
            rows.append(
                {
                    "run_id": f"run_{index}",
                    "time": point * 0.1,
                    "load": 5 + point * (1 + index * 0.001),
                }
            )

    result = CurveFamilyDiagnostic().evaluate(
        curve_rows=rows,
        policy_payload={"curve_source": {"x": "time", "y": "load"}},
    )

    assert len(result.scores) == 4
    assert all(row["evaluable"] for row in result.scores)


def test_default_curve_shape_diagnostic_preserves_resolved_experiment_start() -> None:
    rows = []
    for run_index in range(3):
        for point in range(25):
            x_value = point / 24
            rows.append(
                {
                    "run_id": f"run_{run_index + 1:03d}",
                    "experiment_progress": x_value,
                    "load_N": point * 10.0,
                    "stress_MPa": x_value * 100.0 * (1.0 + run_index * 0.01),
                }
            )

    result = CurveFamilyDiagnostic().evaluate(curve_rows=rows)

    assert result.policy_resolved["preprocessing"]["start_policy"] == "none"
    assert result.report["preprocessing"]["scope"] == "resolved_experiment_interval"
    assert result.report["preprocessing"]["runs_with_excluded_leading_points"] == 0
    assert result.reference_rows[0]["x_common"] == pytest.approx(0.0)
    assert result.reference_rows[0]["y_reference"] == pytest.approx(0.0)
    first_residual_by_run = {}
    for row in result.residual_rows:
        first_residual_by_run.setdefault(row["run_id"], row)
    assert first_residual_by_run
    assert all(row["x_common"] == pytest.approx(0.0) for row in first_residual_by_run.values())
    assert all(row["y_observed"] == pytest.approx(0.0) for row in first_residual_by_run.values())


def test_curve_shape_preprocessing_trims_leading_low_load_noise_only_inside_diagnostic() -> None:
    rows = []
    for run_index in range(3):
        for point in range(25):
            rows.append(
                {
                    "run_id": f"run_{run_index + 1:03d}",
                    "experiment_progress": point / 24,
                    "load_N": 0.0 if point < 5 else float(point),
                    "stress_MPa": 1000.0 if point < 5 else 10.0 + point,
                }
            )

    result = CurveFamilyDiagnostic().evaluate(
        curve_rows=rows,
        policy_payload={
            "curve_source": {"x": "experiment_progress", "y": "stress_MPa", "load": "load_N"},
            "preprocessing": {
                "start_policy": "load_fraction_of_max",
                "min_load_fraction_of_max": 0.05,
                "scope": "curve_shape_diagnostic_only",
            },
        },
    )

    assert rows[0]["stress_MPa"] == 1000.0
    assert result.policy_resolved["preprocessing"]["start_policy"] == "load_fraction_of_max"
    assert result.report["preprocessing"]["scope"] == "curve_shape_diagnostic_only"
    assert result.report["preprocessing"]["runs_with_excluded_leading_points"] == 3
    assert result.report["preprocessing"]["total_excluded_leading_points"] == 15
    assert result.reference_rows[0]["y_reference"] == pytest.approx(15.0)


def _score_row(run_id: str, distance: float) -> dict[str, object]:
    return {
        "run_id": run_id,
        "evaluable": True,
        "distance_rms": distance,
    }
