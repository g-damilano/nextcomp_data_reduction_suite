from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acceptance.acceptance_engine import AcceptanceEngine


def test_acceptance_engine_integrates_curve_family_review_flags() -> None:
    specimen_results = [{"run_id": run_id, "compressive_strength_MPa": 100.0} for run_id in ("run_a", "run_b", "run_c", "run_outlier")]
    curve_rows = _curve_rows({"run_a": 1.0, "run_b": 1.02, "run_c": 0.98, "run_outlier": 2.0})
    report = AcceptanceEngine().evaluate(
        method_id="demo",
        recipe_payload={
            "acceptance": {
                "recipe_id": "demo_acceptance",
                "default_selection_set": "auto_recommended_runs",
                "selection_sets": [
                    {"id": "all_runs", "include": "all"},
                    {"id": "user_valid_runs", "include": "all"},
                    {"id": "auto_recommended_runs", "include_if_max_severity_below": "review"},
                ],
            }
        },
        specimen_results=specimen_results,
        curve_family=curve_rows,
        operation_log=[],
        inspections=[],
        validation_report={"checks": []},
        dataset={},
        curve_family_recipe_payload={
            "curve_family_acceptance": {
                "id": "demo_curve_family",
                "curve_families": [
                    {
                        "id": "stress_strain_family",
                        "x": "mean_strain",
                        "y": "stress_MPa",
                        "selection_context": "user_valid_runs",
                        "alignment": {"mode": "normalized_progress", "x_common_points": 20},
                        "classification": {
                            "review_if": {"normalized_rmse_gt": 0.1},
                            "propose_remove_if": {"normalized_rmse_gt": 0.4},
                        },
                    }
                ],
            }
        },
    )

    payload = report.to_dict()
    curve_flags = [flag for flag in payload["flags"] if flag["source"] == "curve_family_assessment"]

    assert curve_flags
    assert payload["curve_family_assessment"]["summary"]["assessed_runs"] == 4
    assert payload["run_states"]["run_outlier"] == "review_required"
    assert "run_outlier" not in _selection(payload, "auto_recommended_runs")
    assert "run_outlier" in _selection(payload, "user_valid_runs")


def test_acceptance_curve_shape_diagnostic_uses_resolved_boundary_from_zero_by_default() -> None:
    specimen_results = [{"run_id": run_id, "compressive_strength_MPa": 100.0} for run_id in ("run_a", "run_b", "run_c")]
    curve_rows: list[dict[str, float | int | str]] = []
    for run_index, run_id in enumerate(("run_a", "run_b", "run_c")):
        for index in range(12):
            progress = index / 11.0
            curve_rows.append(
                {
                    "run_id": run_id,
                    "point_index": index,
                    "experiment_progress": progress,
                    "load_N": index * 10.0,
                    "stress_MPa": progress * 100.0 * (1.0 + run_index * 0.01),
                }
            )

    report = AcceptanceEngine().evaluate(
        method_id="demo",
        recipe_payload={
            "acceptance": {
                "recipe_id": "demo_acceptance",
                "default_selection_set": "all_runs",
                "selection_sets": [{"id": "all_runs", "include": "all"}],
            }
        },
        specimen_results=specimen_results,
        curve_family=curve_rows,
        operation_log=[],
        inspections=[],
        validation_report={"checks": []},
        dataset={},
    )

    assert report.curve_shape_diagnostic_policy_resolved["preprocessing"]["start_policy"] == "none"
    assert report.curve_shape_diagnostic_report["preprocessing"]["scope"] == "resolved_experiment_interval"
    assert report.curve_shape_diagnostic_reference_rows[0]["x_common"] == 0.0
    assert report.curve_shape_diagnostic_reference_rows[0]["y_reference"] == 0.0
    first_residual_by_run = {}
    for row in report.curve_shape_diagnostic_residual_rows:
        first_residual_by_run.setdefault(row["run_id"], row)
    assert set(first_residual_by_run) == {"run_a", "run_b", "run_c"}
    assert all(row["x_common"] == 0.0 for row in first_residual_by_run.values())
    assert all(row["y_observed"] == 0.0 for row in first_residual_by_run.values())


def test_iso_acceptance_recipe_routes_signal_window_review_out_of_default() -> None:
    recipe = yaml.safe_load((ROOT / "src" / "methods" / "iso14126" / "acceptance_recipe.yaml").read_text(encoding="utf-8"))
    specimen_results = [
        {
            "run_id": "run_ok",
            "compressive_strength_MPa": 100.0,
            "experiment_signal_gate_report_routing_severity": "none",
            "signal_window_load_scale_routing_severity": "none",
        },
        {
            "run_id": "run_review",
            "compressive_strength_MPa": 101.0,
            "experiment_signal_gate_report_routing_severity": "review",
            "signal_window_load_scale_routing_severity": "none",
        },
        {
            "run_id": "run_scale_review",
            "compressive_strength_MPa": 102.0,
            "experiment_signal_gate_report_routing_severity": "info",
            "signal_window_load_scale_routing_severity": "review",
        },
    ]

    report = AcceptanceEngine().evaluate(
        method_id="iso14126_2023",
        recipe_payload=recipe,
        specimen_results=specimen_results,
        curve_family=_curve_rows({"run_ok": 1.0, "run_review": 1.01, "run_scale_review": 0.99}),
        operation_log=[
            {
                "run_id": "run_review",
                "recipe_step_id": "resolve.gate_experiment_signal",
                "operation_id": "gate_experiment_signal",
                "outputs": {"experiment_signal_gate": {}},
            },
            {
                "run_id": "run_scale_review",
                "recipe_step_id": "resolve.experiment_boundaries",
                "operation_id": "resolve_experiment_boundaries",
                "outputs": {"experiment_boundaries": {}},
            },
        ],
        inspections=[],
        validation_report={"checks": []},
        dataset={},
    )

    payload = report.to_dict()
    rule_ids = {flag["rule_id"] for flag in payload["flags"]}

    assert "signal_window_requires_review" in rule_ids
    assert "signal_window_load_scale_review" in rule_ids
    assert payload["run_states"]["run_review"] == "review_required"
    assert payload["run_states"]["run_scale_review"] == "review_required"
    assert "run_review" not in _selection(payload, "auto_recommended_runs")
    assert "run_scale_review" not in _selection(payload, "auto_recommended_runs")
    assert {"run_review", "run_scale_review"} <= _selection(payload, "review_required_runs")
    assert "run_ok" in _selection(payload, "auto_recommended_runs")


def _curve_rows(scales: dict[str, float]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for run_id, scale in scales.items():
        for index in range(12):
            x_value = index / 11.0
            rows.append(
                {
                    "run_id": run_id,
                    "point_index": index,
                    "mean_strain": x_value,
                    "stress_MPa": scale * x_value,
                }
            )
    return rows


def _selection(payload: dict[str, object], selection_id: str) -> set[str]:
    sets = payload["selection_sets"]["selection_sets"]  # type: ignore[index]
    return {
        str(run_id)
        for row in sets
        if isinstance(row, dict) and row.get("selection_id") == selection_id
        for run_id in row.get("run_ids", [])
    }
