from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from operations.curve.boundary_resolution import (
    _max_abs_point_in_interval,
    _peak_decline_non_recovery_resolution,
    _resolve_start_boundary,
    _slope_break_pre_negative_resolution,
)
from operations.curve.gate_experiment_signal import build_experiment_signal_gate
from operations.core.operation_context import OperationContext, OperationRun
from operations.core.operation_registry import default_operation_registry


BASE_CONFIG = {
    "slope_domain": "strain",
    "min_load_fraction_of_max": 0.1,
    "min_relative_load_drop": 0.005,
    "min_negative_domain_step": 0.00001,
    "prebreak_lookback_points": 8,
    "use_prebreak_curvature": True,
}


def test_boundary_detects_load_drop_when_strain_reverses_at_the_same_time() -> None:
    resolution = _slope_break_pre_negative_resolution(
        load=[0.0, 20.0, 40.0, 80.0, 100.0, 94.0, 93.0],
        strain=[0.0, 0.1, 0.2, 0.3, 0.4, 0.39, 0.38],
        config=BASE_CONFIG,
    )

    assert resolution.end_index == 4
    assert resolution.first_negative_slope is not None
    assert resolution.first_negative_slope["negative_slope_trigger"] == "load_drop"
    assert resolution.first_negative_slope["segment_start_index"] == 4
    assert resolution.first_negative_slope["segment_end_index"] == 5


def test_gate_experiment_signal_leaves_clean_signal_unbounded() -> None:
    load = [0.0, 10.0, 30.0, 28.0, 29.0, 27.0]
    strain = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

    gate = build_experiment_signal_gate(run_id="clean", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == len(load) - 1
    assert gate["excluded_regions"] == []
    assert gate["confidence"] == "high"


def test_gate_experiment_signal_keeps_leading_toe_and_settling_points() -> None:
    load = [0.0, 0.2, 0.1, 5.0, 20.0, 60.0, 100.0, 92.0, 84.0]
    strain = [0.0, 0.01, 0.015, 0.03, 0.08, 0.16, 0.25, 0.32, 0.39]

    gate = build_experiment_signal_gate(run_id="toe-settling", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == len(load) - 1
    assert gate["excluded_regions"] == []
    assert "diagnostic_loading_onset_not_used_for_truncation" not in _gate_classifications(gate)


def test_gate_experiment_signal_keeps_legitimate_post_peak_recovery_available() -> None:
    load = [0.0, 20.0, 50.0, 100.0, 92.0, 88.0, 94.0, 98.0, 90.0, 80.0]
    strain = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    gate = build_experiment_signal_gate(run_id="post-peak-recovery", load=load, strain=strain)

    assert gate["status"] == "ok"
    assert gate["confidence"] == "high"
    assert gate["coherent_window"]["end_index"] == len(load) - 1
    assert gate["excluded_regions"] == []


def test_gate_experiment_signal_excludes_embedded_malformed_tail() -> None:
    load = [
        0.0,
        4000.0,
        9000.0,
        11923.5,
        11300.0,
        12097.5,
        11662.0,
        12743.5,
        10491.0,
        15489.0,
        4575.0,
        "#VALUE!",
        "#VALUE!",
        39318.5,
        39318.5,
        39318.5,
    ]
    strain = [
        0.0,
        0.4,
        1.0,
        1.363351479,
        1.365,
        1.368730038,
        1.357927723,
        1.387984372,
        1.328413451,
        1.463962154,
        0.9387617766,
        None,
        None,
        2.0,
        2.01,
        2.02,
    ]

    gate = build_experiment_signal_gate(run_id="malformed", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == 4
    classifications = {region["classification"] for region in gate["excluded_regions"]}
    assert "post_experiment_invalid_tail" in classifications
    assert "domain_reset_or_reversal" in classifications
    assert "non_numeric_cluster" in classifications
    assert "implausible_tail_jump" in classifications
    assert "artificial_plateau_or_saturation" in classifications


def test_borderline_low_load_high_domain_discontinuity_reviews_without_truncation() -> None:
    load = [0.0, 20.0, 50.0, 100.0, 95.0, 90.0, 15.0, 14.0]
    strain = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 2.4, 2.5]

    gate = build_experiment_signal_gate(run_id="borderline-domain-tail", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == len(load) - 1
    assert gate["excluded_regions"] == []
    assert gate["status"] == "review"
    assert gate["confidence"] == "low"
    classifications = _gate_classifications(gate)
    assert "borderline_low_load_high_domain_discontinuity" in classifications
    assert "low_load_high_domain_tail" not in classifications


def test_preload_scale_low_load_high_domain_discontinuity_reports_with_audit_without_truncation() -> None:
    load = [0.0, 1.0, 2.0, 0.2, 0.1, 0.1, 0.1, 50.0, 100.0, 92.0, 80.0]
    strain = [0.0, 0.1, 0.2, 0.3, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1]

    gate = build_experiment_signal_gate(run_id="run_002-preload-scale", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == len(load) - 1
    assert gate["excluded_regions"] == []
    assert gate["status"] == "ok"
    assert gate["confidence"] == "medium"
    assert gate["report_routing"]["state"] == "reportable_with_audit"
    assert gate["report_routing"]["severity"] == "info"
    diagnostic = next(
        item
        for item in gate["diagnostics"]
        if item["classification"] == "preload_scale_low_load_high_domain_discontinuity"
    )
    assert diagnostic["reference_peak_load"] == 2.0
    assert diagnostic["full_run_peak_load"] == 100.0
    assert diagnostic["reference_peak_scale_floor_pass"] is False


def _gate_classifications(gate: dict[str, object]) -> set[str]:
    values = set(gate.get("classifications", []))
    for region in gate.get("excluded_regions", []):
        if isinstance(region, dict):
            values.add(str(region.get("classification")))
    for diagnostic in gate.get("diagnostics", []):
        if isinstance(diagnostic, dict):
            values.add(str(diagnostic.get("classification")))
    return values


def test_low_load_high_domain_tail_is_excluded_without_start_truncation() -> None:
    load = [0.0, 20.0, 50.0, 100.0, 95.0, 90.0, 5.0, 4.0, 4.5, 4.2]
    strain = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 2.4, 2.5, 2.6, 2.7]

    gate = build_experiment_signal_gate(run_id="low-domain-tail", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == 5
    assert gate["status"] == "ok"
    assert gate["confidence"] == "medium"
    classifications = _gate_classifications(gate)
    assert "low_load_high_domain_tail" in classifications
    assert "diagnostic_loading_onset_not_used_for_truncation" in classifications
    assert gate["coherent_window"]["start_index"] != gate["diagnostic_markers"]["loading_onset"]["index"]


def test_false_clean_pass_blocked_for_low_load_high_domain_tail_variants() -> None:
    variants = [
        (
            [0.0, 25.0, 55.0, 90.0, 88.0, 82.0, 6.0, 5.0, 5.2, 5.1],
            [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 1.70, 1.80, 1.90, 2.00],
        ),
        (
            [0.0, 15.0, 40.0, 76.0, 75.0, 71.0, 9.0, 8.0, 8.1, 8.2],
            [0.0, 0.08, 0.16, 0.24, 0.32, 0.40, 2.20, 2.24, 2.28, 2.32],
        ),
        (
            [0.0, 30.0, 80.0, 120.0, 118.0, 111.0, 12.0, 10.0, 10.4, 10.2],
            [0.0, 0.12, 0.24, 0.36, 0.48, 0.60, 4.00, 4.10, 4.20, 4.30],
        ),
        (
            [0.0, 10.0, 35.0, 70.0, 69.0, 66.0, 3.0, 2.8, 2.7, 2.9],
            [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 1.80, 1.90, 2.00, 2.10],
        ),
    ]

    for index, (load, strain) in enumerate(variants):
        gate = build_experiment_signal_gate(run_id=f"tail-variant-{index}", load=load, strain=strain)

        assert gate["coherent_window"]["start_index"] == 0
        assert gate["coherent_window"]["end_index"] < len(load) - 1
        assert not (gate["confidence"] == "high" and gate["excluded_regions"] == [] and gate["diagnostics"] == [])
        classifications = _gate_classifications(gate)
        assert "low_load_high_domain_tail" in classifications
        assert "false_clean_pass_prevented" in classifications


def test_multi_fragment_signal_fails_with_disconnected_high_load_fragment() -> None:
    load = [
        0.0,
        30.0,
        70.0,
        100.0,
        96.0,
        93.0,
        5.0,
        4.0,
        4.5,
        4.2,
        72.0,
        78.0,
        77.0,
        75.0,
        73.0,
    ]
    strain = [
        0.0,
        0.1,
        0.2,
        0.3,
        1.3,
        1.4,
        3.0,
        3.1,
        3.2,
        3.3,
        4.0,
        4.1,
        4.2,
        4.3,
        4.4,
    ]

    gate = build_experiment_signal_gate(run_id="multi-fragment", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == 5
    assert gate["status"] == "fail"
    assert gate["confidence"] == "low"
    classifications = _gate_classifications(gate)
    assert "high_load_domain_reset_before_tail" in classifications
    assert "low_load_high_domain_tail" in classifications
    assert "disconnected_high_load_fragment" in classifications


def test_late_restart_spike_reviews_without_start_truncation() -> None:
    load = [0.0, 20.0, 40.0, 60.0, 80.0, 75.0, 50.0, 45.0, 105.0, 110.0, 104.0, 5.0, 4.5, 4.2]
    strain = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.5, 1.6, 1.7, 3.5, 3.6, 3.7]

    gate = build_experiment_signal_gate(run_id="late-restart", load=load, strain=strain)

    assert gate["coherent_window"]["start_index"] == 0
    assert gate["coherent_window"]["end_index"] == 10
    assert gate["status"] == "review"
    assert gate["confidence"] == "low"
    classifications = _gate_classifications(gate)
    assert "low_load_high_domain_tail" in classifications
    assert "late_restart_spike_before_peak" in classifications


def test_boundary_outputs_respect_low_load_high_domain_gate_window() -> None:
    registry = default_operation_registry()
    run = OperationRun(
        source_run=object(),
        series={
            "load_N": [0.0, 20.0, 50.0, 100.0, 95.0, 90.0, 5.0, 4.0, 4.5, 150.0],
            "mean_strain": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 2.4, 2.5, 2.6, 2.7],
            "time_s": list(range(10)),
        },
    )
    context = OperationContext(source=None, mapping={}, runs={"run_001": run}, inspector=None, phase="resolve")

    gate_results = registry.run(
        context,
        {
            "id": "resolve.gate_experiment_signal",
            "op": "gate_experiment_signal",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain"},
            "output": "experiment_signal_gate",
        },
    )
    boundary_results = registry.run(
        context,
        {
            "id": "resolve.experiment_boundaries",
            "op": "resolve_experiment_boundaries",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain", "gate": "experiment_signal_gate"},
            "parameters": {"start_policy": "first_point", "end_policy": "peak_decline_non_recovery", "sustained_decline": {"min_points": 3}},
            "output": "experiment_boundaries",
        },
    )

    gate = gate_results[0].outputs["experiment_signal_gate"]
    boundary = boundary_results[0].outputs["experiment_boundaries"]
    gate_end = gate["coherent_window"]["end_index"]
    assert "low_load_high_domain_tail" in _gate_classifications(gate)
    assert boundary["end_index"] <= gate_end
    assert boundary["accepted_failure_peak_index"] <= gate_end
    assert boundary["max_within_interval_index"] <= gate_end
    assert boundary["reported_strength_index"] <= gate_end


def test_peak_decline_fallback_is_constrained_to_gate_window() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 20.0, 30.0, 31.0, 100.0],
        start_index=0,
        sustained_config={"min_points": 3},
        gate_end_index=4,
    )

    assert resolution.end_index == 4
    assert resolution.accepted_failure_peak_index == 4
    assert "inside the experiment signal gate" in resolution.reason


def test_first_point_start_policy_moves_to_preload_reset_boundary_only_for_clear_reset() -> None:
    reset_load = (
        [24.0] * 30
        + [15.0, 2.0, -5.0, -5.0, -6.0, -12.0, -25.0, -50.0, -90.0, -140.0, -210.0, -300.0]
        + [-400.0 - index * 100.0 for index in range(90)]
    )
    reset_resolution = _resolve_start_boundary(
        load=reset_load,
        time=list(range(len(reset_load))),
        strain=[0.0] * len(reset_load),
        start_policy="first_point",
        config={},
        fallback_config={},
    )
    rising_resolution = _resolve_start_boundary(
        load=[20.0, 21.0, 25.0, 31.0, 39.0, 51.0, 70.0],
        time=list(range(7)),
        strain=[0.0] * 7,
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert reset_resolution.start_index == 29
    assert "preload point before a reset" in reset_resolution.reason
    assert rising_resolution.start_index == 0


def test_first_point_start_policy_promotes_zero_reset_to_stable_low_load_seating_shelf() -> None:
    load = (
        [1.0] * 24
        + [0.0, 0.0, 0.0, 0.0]
        + [-1.0] * 14
        + [-4.0, -8.0, -12.0, -18.0, -35.0, -70.0, -120.0]
        + [-180.0 - index * 50.0 for index in range(90)]
    )

    resolution = _resolve_start_boundary(
        load=load,
        time=list(range(len(load))),
        strain=[0.0] * len(load),
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert resolution.start_index is not None
    assert resolution.start_index > 23
    assert load[resolution.start_index] == -1.0
    assert "low-load seating shelf" in resolution.reason


def test_first_point_start_policy_keeps_nonzero_preload_reset_start() -> None:
    load = (
        [18.0] * 24
        + [12.0, 2.0, -5.0, -12.0, -20.0, -45.0, -90.0]
        + [-150.0 - index * 40.0 for index in range(80)]
    )

    resolution = _resolve_start_boundary(
        load=load,
        time=list(range(len(load))),
        strain=[0.0] * len(load),
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert resolution.start_index == 23
    assert "preload point before a reset" in resolution.reason


def test_first_point_start_policy_moves_before_low_stiffness_to_material_branch_transition() -> None:
    load: list[float] = []
    strain: list[float] = []
    load_value = 0.0
    strain_value = 0.0
    for _ in range(35):
        load_value += 0.5
        strain_value += 5e-6
        load.append(load_value)
        strain.append(strain_value)
    for _ in range(120):
        load_value += 25.0
        strain_value += 20e-6
        load.append(load_value)
        strain.append(strain_value)

    resolution = _resolve_start_boundary(
        load=load,
        time=list(range(len(load))),
        strain=strain,
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert resolution.start_index is not None
    assert 0 < resolution.start_index < 35
    assert "low-stiffness toe" in resolution.reason


def test_first_point_start_policy_keeps_clean_material_branch_at_raw_start() -> None:
    load = [index * 25.0 for index in range(120)]
    strain = [index * 20e-6 for index in range(120)]

    resolution = _resolve_start_boundary(
        load=load,
        time=list(range(len(load))),
        strain=strain,
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert resolution.start_index == 0
    assert resolution.reason == "first recorded point selected as analysis start."


def test_first_point_start_policy_moves_after_initial_strain_relaxation() -> None:
    load = [
        16.0,
        17.0,
        23.0,
        26.0,
        28.0,
        30.0,
        32.0,
        33.0,
        35.0,
        37.0,
        40.0,
        42.0,
        43.0,
        46.0,
        49.0,
        52.0,
        54.0,
        58.0,
        64.0,
        70.0,
        78.0,
        89.0,
        99.0,
        110.0,
        122.0,
        135.0,
        148.0,
        160.0,
        172.0,
        184.0,
        196.0,
        208.0,
    ]
    strain = [
        13.6e-6,
        13.8e-6,
        11.7e-6,
        10.6e-6,
        11.2e-6,
        9.6e-6,
        9.7e-6,
        9.1e-6,
        8.0e-6,
        7.7e-6,
        8.0e-6,
        7.7e-6,
        7.6e-6,
        6.9e-6,
        6.1e-6,
        6.2e-6,
        6.6e-6,
        6.9e-6,
        6.6e-6,
        7.3e-6,
        7.0e-6,
        7.3e-6,
        9.0e-6,
        11.5e-6,
        15.2e-6,
        20.5e-6,
        25.8e-6,
        31.0e-6,
        36.0e-6,
        41.0e-6,
        46.0e-6,
        51.0e-6,
    ]

    resolution = _resolve_start_boundary(
        load=load,
        time=list(range(len(load))),
        strain=strain,
        start_policy="first_point",
        config={},
        fallback_config={},
    )

    assert resolution.start_index == 15
    assert "strain-relaxation minimum" in resolution.reason


def test_peak_decline_separates_failure_peak_from_gate_post_peak_transition() -> None:
    gate_record = {
        "diagnostics": [
            {
                "classification": "load_bearing_restart_after_jagged_region",
                "accepted_failure_peak_index": 3,
                "post_peak_transition": {
                    "schema_id": "method.post_peak_transition.v0_1",
                    "peak_index": 3,
                    "peak_load": 100.0,
                    "end_index": 5,
                    "noise_floor_load": 3.0,
                },
            }
        ]
    }
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 30.0, 80.0, 100.0, 99.0, 98.0, 80.0, 60.0],
        start_index=0,
        sustained_config={"min_points": 3},
        gate_end_index=5,
        gate_record=gate_record,
    )

    assert resolution.end_index == 5
    assert resolution.accepted_failure_peak_index == 3
    assert resolution.reported_strength_index == 3
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate["post_peak_transition"]["analysis_end_index"] == 5


def test_boundary_surfaces_stale_preload_scale_gate_window_for_review() -> None:
    registry = default_operation_registry()
    run = OperationRun(
        source_run=object(),
        series={
            "load_N": [0.0, 1.0, 2.0, 0.2, 0.1, 0.1, 0.1, 50.0, 100.0, 92.0, 80.0],
            "mean_strain": [0.0, 0.1, 0.2, 0.3, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1],
            "time_s": list(range(11)),
        },
    )
    run.scalars["experiment_signal_gate"] = {
        "status": "ok",
        "confidence": "medium",
        "coherent_window": {"start_index": 0, "end_index": 2, "point_count": 3},
        "classifications": ["coherent_experiment_signal", "low_load_high_domain_tail"],
        "report_routing": {"state": "reportable_with_audit", "severity": "info"},
    }
    context = OperationContext(source=None, mapping={}, runs={"run_002": run}, inspector=None, phase="resolve")

    result = registry.run(
        context,
        {
            "id": "resolve.experiment_boundaries",
            "op": "resolve_experiment_boundaries",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain", "gate": "experiment_signal_gate"},
            "parameters": {
                "start_policy": "first_point",
                "end_policy": "peak_decline_non_recovery",
                "sustained_decline": {"min_points": 3, "min_gate_peak_fraction_of_full_run_max": 0.10},
            },
            "output": "experiment_boundaries",
        },
    )[0]

    boundary = result.outputs["experiment_boundaries"]
    scale = boundary["signal_window_load_scale"]
    assert result.status == "warning"
    assert scale["routing_severity"] == "review"
    assert scale["gate_window_peak_load"] == 2.0
    assert scale["raw_full_run_peak_load"] == 100.0
    assert scale["gate_to_full_run_peak_fraction"] == 0.02


def test_gate_operation_is_registered() -> None:
    registry = default_operation_registry()
    assert "gate_experiment_signal" in registry._operations


def test_registered_gate_matches_base_blunt_tail_window() -> None:
    registry = default_operation_registry()
    run = OperationRun(
        source_run=object(),
        series={
            "load_N": [0.0, 4000.0, 9000.0, 11923.5, 11300.0, 12097.5, 11662.0, 39318.5],
            "mean_strain": [0.0, 0.4, 1.0, 1.363351479, 1.365, 1.368730038, 1.357927723, 2.0],
            "time_s": list(range(8)),
        },
    )
    context = OperationContext(source=None, mapping={}, runs={"run_001": run}, inspector=None, phase="resolve")

    result = registry.run(
        context,
        {
            "id": "resolve.gate_experiment_signal",
            "op": "gate_experiment_signal",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain"},
            "output": "experiment_signal_gate",
        },
    )[0]

    gate = result.outputs["experiment_signal_gate"]
    assert gate["coherent_window"]["end_index"] == 4
    assert any(region["start_index"] <= 5 for region in gate["excluded_regions"])


def test_recipe_like_gate_feeds_boundary_resolution_and_preserves_evidence() -> None:
    registry = default_operation_registry()
    run = OperationRun(
        source_run=object(),
        series={
            "load_N": [0.0, 4000.0, 9000.0, 11923.5, 11300.0, 12097.5, 11662.0, 39318.5],
            "mean_strain": [0.0, 0.4, 1.0, 1.363351479, 1.365, 1.368730038, 1.357927723, 2.0],
            "time_s": list(range(8)),
        },
    )
    context = OperationContext(source=None, mapping={}, runs={"run_001": run}, inspector=None, phase="resolve")

    gate_results = registry.run(
        context,
        {
            "id": "resolve.gate_experiment_signal",
            "op": "gate_experiment_signal",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain"},
            "output": "experiment_signal_gate",
        },
    )
    boundary_results = registry.run(
        context,
        {
            "id": "resolve.experiment_boundaries",
            "op": "resolve_experiment_boundaries",
            "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain", "gate": "experiment_signal_gate"},
            "parameters": {"start_policy": "first_point", "end_policy": "peak_decline_non_recovery", "sustained_decline": {"min_points": 3}},
            "output": "experiment_boundaries",
        },
    )

    gate = gate_results[0].outputs["experiment_signal_gate"]
    boundary = boundary_results[0].outputs["experiment_boundaries"]
    assert gate["coherent_window"]["end_index"] == 4
    assert boundary["end_index"] == 3
    assert boundary["experiment_signal_gate"]["coherent_window"]["end_index"] == 4
    assert boundary_results[0].evidence["experiment_signal_gate"]["excluded_regions"]


def test_boundary_detects_meaningful_strain_reversal_without_load_drop() -> None:
    resolution = _slope_break_pre_negative_resolution(
        load=[0.0, 20.0, 40.0, 40.0, 39.9],
        strain=[0.0, 0.1, 0.2, 0.18, 0.17],
        config=BASE_CONFIG,
    )

    assert resolution.end_index == 2
    assert resolution.first_negative_slope is not None
    assert resolution.first_negative_slope["negative_slope_trigger"] == "domain_reversal"
    assert resolution.first_negative_slope["segment_start_index"] == 2


def test_boundary_ignores_tiny_strain_jitter_below_reversal_tolerance() -> None:
    resolution = _slope_break_pre_negative_resolution(
        load=[0.0, 20.0, 40.0, 60.0, 80.0],
        strain=[0.0, 0.1, 0.2, 0.199999, 0.3],
        config=BASE_CONFIG,
    )

    assert resolution.end_index == 4
    assert resolution.first_negative_slope is None


def test_boundary_detects_strain_collapse_before_late_spurious_load_peak() -> None:
    resolution = _slope_break_pre_negative_resolution(
        load=[0.0, 100.0, 200.0, 300.0, 5000.0],
        strain=[0.0, 0.0002, 0.0005, 0.00001, 0.00001],
        config=BASE_CONFIG
        | {
            "detect_strain_collapse": True,
            "min_strain_before_collapse": 0.0002,
            "min_relative_strain_collapse": 0.25,
        },
    )

    assert resolution.end_index == 2
    assert resolution.first_negative_slope is not None
    assert resolution.first_negative_slope["negative_slope_trigger"] == "strain_collapse"
    assert resolution.first_negative_slope["segment_start_index"] == 2


def test_bounded_max_load_selector_uses_last_equal_plateau_point() -> None:
    assert _max_abs_point_in_interval(
        [0.0, 100.0, 3000.0, 3000.0, 3000.0, 4000.0],
        start_index=0,
        end_index=4,
        include_endpoint=True,
    ) == (4, 3000.0)


def test_boundary_can_use_sustained_post_peak_decline_as_endpoint() -> None:
    resolution = _slope_break_pre_negative_resolution(
        load=[0.0, 20.0, 40.0, 100.0, 99.7, 99.4, 99.3],
        strain=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        config=BASE_CONFIG,
        sustained_config={
            "enabled": True,
            "min_points": 2,
            "min_relative_drop": 0.005,
            "use_as": "endpoint",
        },
    )

    assert resolution.end_index == 3
    assert resolution.first_negative_slope is None
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["event_index"] == 5


def test_peak_decline_accepts_plus_minus_peak() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 30.0, 20.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 2
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["candidate_pattern"] == "+ -"


def test_peak_decline_accepts_plus_zero_minus_plateau_right_edge() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 30.0, 30.0, 30.0, 20.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 4
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["candidate_pattern"] == "+ 0 -"


def test_peak_decline_rejects_plus_minus_plus_recovery() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 30.0, 20.0, 35.0, 50.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 5
    assert resolution.sustained_decline is None
    assert "fallback" in resolution.warnings[0]


def test_peak_decline_rejects_plus_zero_plus_nonterminal_plateau() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 30.0, 30.0, 35.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 4
    assert resolution.sustained_decline is None
    assert "fallback" in resolution.warnings[0]


def test_peak_decline_rejects_high_spike_when_load_recovers() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 20.0, 100.0, 91.0, 121.0, 151.0, 181.0, 170.0, 158.0, 146.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 6
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["selection"] == "peak_decline_non_recovery"


def test_peak_decline_selects_peak_before_non_recovering_decline() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 30.0, 70.0, 68.0, 64.0, 60.0, 59.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 3


def test_peak_decline_selects_lower_true_break_after_higher_recovered_spike() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 50.0, 120.0, 40.0, 60.0, 80.0, 100.0, 118.0, 109.0, 101.0, 94.0],
        strain=[0.0, 1.0, 2.0, 2.1, 2.4, 2.7, 3.0, 3.3, 4.3, 5.3, 6.3],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 7


def test_peak_decline_rejects_high_plus_minus_plus_and_selects_lower_terminal_peak() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 20.0, 30.0, 40.0, 20.0, 30.0, 38.0, 30.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 7
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["peak_index"] == 7


def test_peak_decline_ignores_strain_instability_while_load_rises() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 20.0, 40.0, 60.0, 82.0, 104.0, 103.0, 101.0, 99.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 5
    assert resolution.first_negative_slope is None
    assert resolution.prebreak_curvature is None


def test_peak_decline_selects_plateau_exit_into_decline() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 20.0, 50.0, 80.0, 80.0, 80.0, 74.0, 68.0, 62.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 5


def test_peak_decline_cuts_off_sustained_post_peak_plateau() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 60.0, 120.0, 118.0, 117.5, 117.0, 116.5, 116.0, 115.5],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 2
    assert resolution.sustained_decline is not None


def test_peak_decline_accepts_peak_when_later_rising_block_is_not_comparable_recovery() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[
            0.0,
            80.0,
            160.0,
            240.0,
            300.0,
            320.0,
            322.0,
            323.0,
            323.2,
            323.4,
            323.6,
            323.8,
            323.9,
            207.0,
            104.0,
            20.0,
            10.0,
            11.0,
            12.0,
            13.0,
            14.0,
            13.0,
            12.0,
            11.0,
        ],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 12
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["peak_index"] == 12


def test_peak_decline_accepts_peak_before_negative_strain_plateau() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[
            236.790,
            238.094,
            238.860,
            239.920,
            240.784,
            241.818,
            242.865,
            243.362,
            244.774,
            238.785,
            232.841,
            226.920,
            228.219,
            229.192,
            230.428,
            231.680,
            232.353,
            234.021,
            225.392,
            217.732,
            208.297,
        ],
        strain=[
            0.494454,
            0.497914,
            0.500427,
            0.503388,
            1.362233,
            0.518718,
            0.512794,
            0.514831,
            0.519019,
            0.646509,
            1.482733,
            2.394192,
            2.293081,
            2.295892,
            2.297466,
            2.296216,
            2.292905,
            2.293802,
            2.177812,
            2.088292,
            2.068476,
        ],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 8
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["peak_index"] == 8


def test_peak_decline_selects_terminal_peak_after_recovered_branch() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 80.0, 160.0, 300.0, 30.0, 115.0, 200.0, 285.0, 270.0, 250.0, 230.0],
        strain=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 7
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["peak_index"] == 7


def test_peak_decline_accepts_highest_terminal_peak_before_short_wobble() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 20.0, 31.0, 30.0, 30.5, 29.0, 28.0, 27.0],
        strain=[0.0, 1.0, 2.0, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 3
    assert resolution.sustained_decline is not None
    assert resolution.sustained_decline["peak_index"] == 3


def test_peak_decline_rejects_candidate_when_later_load_exceeds_it() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 25.0, 50.0, 100.0, 94.0, 90.0, 86.0, 91.0, 104.0, 112.0],
        strain=[0.0, 1.0, 2.0, 3.0, 3.2, 3.4, 3.6, 4.4, 5.4, 6.4],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 9
    assert resolution.sustained_decline is None
    assert "fallback" in resolution.warnings[0]


def test_peak_decline_promotes_coherent_gate_endpoint_when_later_fmax_exists() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 40.0, 80.0, 120.0, 112.0, 100.0, 96.0, 90.0, 88.0, 86.0, 92.0, 104.0, 124.0, 136.0],
        strain=[0.0, 0.1, 0.2, 0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.40, 0.46, 0.54, 0.62],
        start_index=0,
        sustained_config={"min_points": 3},
        gate_end_index=13,
        gate_record={
            "status": "ok",
            "confidence": "high",
            "coherent_window": {
                "start_index": 0,
                "end_index": 13,
                "classification": "coherent_experiment_signal",
            },
            "excluded_regions": [],
        },
    )

    assert resolution.end_index == 13
    selected = resolution.selected_candidate or {}
    assert selected["candidate_peak_index"] == 13
    assert selected["endpoint_promotion"]["reason"].startswith("High-confidence coherent gate")


def test_peak_decline_falls_back_to_post_start_maximum_without_clear_non_recovery() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 10.0, 80.0, 81.0, 82.0, 83.0],
        start_index=2,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 5
    assert resolution.sustained_decline is None
    assert "fallback" in resolution.warnings[0]


def test_peak_decline_accepts_one_step_catastrophic_drop_then_drift() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 1.0, 1.1, 2.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 0
    selected = resolution.selected_candidate or {}
    assert selected["candidate_peak_index"] == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["meaningful_drop_seen"] is True
    assert diagnostic["sustained_non_recovered_state"] is True
    assert diagnostic["recovery_amplitude_seen"] is False


def test_peak_decline_accepts_staircase_decline_fragmented_by_noise() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 70.0, 71.0, 60.0, 61.0, 50.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["candidate_final_decision"] == "accepted"
    assert diagnostic["non_recovered_point_count"] >= 2


def test_peak_decline_does_not_treat_late_low_level_drift_as_recovery() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 1.0, 2.0, 3.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["recovery_amplitude_seen"] is False
    assert diagnostic["candidate_final_decision"] == "accepted"


def test_peak_decline_rejects_true_near_peak_recovery() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 60.0, 70.0, 82.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 3
    first_candidate = resolution.candidate_diagnostics[0]
    assert first_candidate["candidate_peak_index"] == 0
    assert first_candidate["candidate_final_decision"] == "rejected"
    assert first_candidate["candidate_rejection_reason"] == "local_continuous_recovery_near_candidate_peak"


def test_peak_decline_accepts_late_unrelated_recovery_like_rise() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 1.0, 1.0, 1.2, 1.1, 1.3, 1.2, 75.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["recovery_amplitude_seen"] is True
    assert diagnostic["recovery_locality_pass"] is False
    assert diagnostic["candidate_final_decision"] == "accepted"


def test_peak_decline_ignores_tiny_later_higher_noise_within_tolerance() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[80.0, 20.0, 80.001],
        start_index=0,
        sustained_config={"min_points": 1, "later_higher_relative_tolerance": 0.0001},
    )

    assert resolution.end_index == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["later_significant_higher_peak_seen"] is False
    assert diagnostic["candidate_final_decision"] == "accepted"


def test_peak_decline_surfaces_noisy_strain_domain_as_diagnostic_not_veto() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 20.0, 40.0, 80.0, 20.0, 10.0, 9.0],
        strain=[0.0, 1.0, 0.5, 0.4, 0.3, 0.2, 0.1],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 3
    diagnostic = next(row for row in resolution.candidate_diagnostics if row["candidate_peak_index"] == 3)
    assert diagnostic["candidate_final_decision"] == "accepted"
    assert diagnostic["domain_evidence_quality"] == "point_index_fallback"


def test_peak_decline_marks_isolated_spike_for_review() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[50.0, 200.0, 51.0, 52.0, 53.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    diagnostic = next(row for row in resolution.candidate_diagnostics if row["candidate_peak_index"] == 1)
    assert diagnostic["candidate_peak_robust"] is False
    assert diagnostic["candidate_final_decision"] == "review"


def test_peak_decline_selects_plateau_edge_with_candidate_diagnostics() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[0.0, 50.0, 80.0, 80.0, 70.0, 60.0],
        start_index=0,
        sustained_config={"min_points": 3},
    )

    assert resolution.end_index == 3
    diagnostic = next(row for row in resolution.candidate_diagnostics if row["candidate_peak_index"] == 3)
    assert diagnostic["candidate_pattern"] == "+ 0 -"
    assert diagnostic["candidate_final_decision"] == "accepted"


def test_peak_decline_flags_sign_reversal_after_failure_without_overriding_endpoint() -> None:
    resolution = _peak_decline_non_recovery_resolution(
        load=[-80.0, -1.0, 1.0, 79.0],
        start_index=0,
        sustained_config={"min_points": 1},
    )

    assert resolution.end_index == 0
    diagnostic = resolution.candidate_diagnostics[0]
    assert diagnostic["sign_state_diagnostic"]["sign_reversal_after_peak_seen"] is True
    assert diagnostic["candidate_final_decision"] == "accepted"
