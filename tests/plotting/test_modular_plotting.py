from __future__ import annotations

from typing import Any

from plotting.evidence_adapters import (
    aggregate_curve_family_request,
    bending_evidence_request,
    curve_shape_distance_ranking_request,
    curve_shape_residuals_request,
    stress_strain_reduction_request,
)
from plotting.models import PlotRequest
from plotting.registry import plot_registry


def test_registry_has_current_plot_types_and_controlled_unknown_failure() -> None:
    assert {
        "stress_strain_reduction",
        "bending_evidence",
        "aggregate_curve_family",
        "curve_shape_distance_ranking",
        "curve_shape_residuals",
        "curve_shape_diagnostics",
        "generic_xy_overlay",
    }.issubset(set(plot_registry.plot_types()))

    result = plot_registry.build(PlotRequest(plot_type="not_registered", plot_id="missing"))
    assert result.status == "failed"
    assert "not registered" in result.fallback_message


def test_stress_strain_reduction_spec_has_semantic_layers_and_fallback() -> None:
    request = stress_strain_reduction_request(
        plot_id="run_001_stress",
        run_id="run_001",
        bounded_rows=_stress_rows(),
        block=_stress_block(),
    )
    result = plot_registry.build(request)

    assert result.status == "rendered"
    spec = result.spec or {}
    assert spec["$schema"].endswith("vega-lite/v5.json")
    layer_names = {layer["name"] for layer in spec["layer"]}
    assert "bounded curve" in layer_names
    assert "front rear strain traces" in layer_names
    assert "front rear strain agreement envelope" in layer_names
    assert "chord line" in layer_names
    assert "chord points" in layer_names
    assert "analysis markers" in layer_names
    semantic_layers = set(spec["usermeta"]["semantic_layers"])
    assert "bounded_analysis_curve" in semantic_layers
    assert "experiment_start_marker" in semantic_layers
    assert "experiment_end_marker" in semantic_layers
    assert "modulus_chord_line" in semantic_layers
    bounded_layer = next(layer for layer in spec["layer"] if layer["name"] == "bounded curve")
    marker_layer = next(layer for layer in spec["layer"] if layer["name"] == "analysis markers")
    marker_names = {row["marker"] for row in marker_layer["data"]["values"]}
    assert marker_names == {"start marker", "end marker (max point / failure strain)"}
    assert bounded_layer["encoding"]["order"] == {"field": "point_index", "type": "quantitative"}
    assert spec["usermeta"]["depiction_policy"]["semantic_boundary"] == "depiction_only"
    assert spec["usermeta"]["depiction_policy"]["plot_side_reselection"] is False
    assert "marginalia" not in spec["usermeta"]

    untrimmed_result = plot_registry.build(
        stress_strain_reduction_request(
            plot_id="run_001_untrimmed_stress",
            run_id="run_001",
            bounded_rows=_stress_raw_rows(),
            block=_stress_block(),
        )
    )
    untrimmed_spec = untrimmed_result.spec or {}
    untrimmed_bounded = next(layer for layer in untrimmed_spec["layer"] if layer["name"] == "bounded curve")
    untrimmed_values = untrimmed_bounded["data"]["values"]
    assert max(row["point_index"] for row in untrimmed_values) == 12.0
    assert "post-peak audit trace" not in {layer["name"] for layer in untrimmed_spec["layer"]}

    strain_excursion_rows = [
        {
            "run_id": "run_001",
            "point_index": 0,
            "mean_strain": 0.0,
            "front_strain_abs": 0.0,
            "rear_strain_abs": 0.0,
            "stress_MPa": 0.0,
            "load_N": 0.0,
        },
        {
            "run_id": "run_001",
            "point_index": 1,
            "mean_strain": 0.0005,
            "front_strain_abs": 0.0005,
            "rear_strain_abs": 0.0005,
            "stress_MPa": 25.0,
            "load_N": 200.0,
        },
        {
            "run_id": "run_001",
            "point_index": 2,
            "mean_strain": 0.02,
            "front_strain_abs": 0.039,
            "rear_strain_abs": 0.001,
            "stress_MPa": 75.0,
            "load_N": 600.0,
        },
        {
            "run_id": "run_001",
            "point_index": 3,
            "mean_strain": 0.0015,
            "front_strain_abs": 0.0014,
            "rear_strain_abs": 0.0016,
            "stress_MPa": 100.0,
            "load_N": 800.0,
        },
    ]
    excursion_result = plot_registry.build(
        stress_strain_reduction_request(
            plot_id="run_001_strain_excursion",
            run_id="run_001",
            bounded_rows=strain_excursion_rows,
            block={
                "markers": {
                    "experiment_start": {"index": 0},
                    "experiment_end": {"index": 3},
                    "max_load_strength": {"index": 3, "stress_MPa": 100.0},
                    "chord_line": {"x_start": 0.0005, "y_start": 25.0, "x_end": 0.0015, "y_end": 100.0},
                }
            },
        )
    )
    excursion_spec = excursion_result.spec or {}
    excursion_bounded = next(layer for layer in excursion_spec["layer"] if layer["name"] == "bounded curve")
    excursion_values = excursion_bounded["data"]["values"]
    assert max(row["strain"] for row in excursion_values) == 2.0
    assert excursion_bounded["encoding"]["x"]["scale"]["domain"][1] > 2.0

    marker_peak_rows = [
        {
            "run_id": "run_001",
            "point_index": index,
            "mean_strain": index * 0.0001,
            "front_strain_abs": index * 0.00009,
            "rear_strain_abs": index * 0.00011,
            "stress_MPa": 200.0 if index == 2 else 25.0,
            "load_N": 1600.0 if index == 2 else 200.0,
        }
        for index in range(700)
    ]
    marker_peak_result = plot_registry.build(
        stress_strain_reduction_request(
            plot_id="run_001_marker_peak",
            run_id="run_001",
            bounded_rows=marker_peak_rows,
            block={
                "markers": {
                    "experiment_start": {"index": 0},
                    "experiment_end": {"index": 699},
                    "max_load_strength": {"index": 2},
                }
            },
        )
    )
    marker_peak_spec = marker_peak_result.spec or {}
    marker_peak_layer = next(layer for layer in marker_peak_spec["layer"] if layer["name"] == "bounded curve")
    marker_peak_y_domain = marker_peak_layer["encoding"]["y"]["scale"]["domain"]
    assert marker_peak_y_domain[1] >= 200.0

    assert result.quality_report is not None
    assert result.quality_report.axis_labels_present is True
    assert result.quality_report.tooltip_present is True

    missing = plot_registry.build(
        stress_strain_reduction_request(plot_id="missing", run_id="run_001", bounded_rows=[], block={})
    )
    assert missing.status == "unavailable"
    assert "Plot unavailable" in missing.fallback_message


def test_bending_evidence_spec_has_threshold_window_and_segments() -> None:
    result = plot_registry.build(
        bending_evidence_request(
            plot_id="run_001_bending",
            run_id="run_001",
            bounded_rows=_stress_rows(),
            block=_bending_block(),
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    layer_names = {layer["name"] for layer in spec["layer"]}
    assert "bending percent series" in layer_names
    assert "bending percent series outside assessment window" in layer_names
    assert "threshold line" in layer_names
    assert "threshold annotation" in layer_names
    assert "10-90% window" in layer_names
    assert "10% and 90% Fmax boundary lines" in layer_names
    assert "10% and 90% Fmax boundary annotations" in layer_names
    assert "exceedance points" in layer_names
    assert "exceedance segments" in layer_names
    semantic_layers = set(spec["usermeta"]["semantic_layers"])
    assert "bending_percent_series" in semantic_layers
    assert "context_bending_series" in semantic_layers
    assert "threshold_line" in semantic_layers
    assert "threshold_annotation" in semantic_layers
    assert "assessment_window_10_90_fmax" in semantic_layers
    assert "assessment_window_10_percent_boundary" in semantic_layers
    assert "assessment_window_90_percent_boundary" in semantic_layers
    boundary_layer = next(layer for layer in spec["layer"] if layer["name"] == "10% and 90% Fmax boundary lines")
    assert {row["label"] for row in boundary_layer["data"]["values"]} == {"10% Fmax", "90% Fmax"}
    assessed_layer = next(layer for layer in spec["layer"] if layer["name"] == "bending percent series")
    assert all(200 <= row["load_N"] <= 600 for row in assessed_layer["data"]["values"])
    assert assessed_layer["mark"]["color"] == "#d9786d"
    context_layer = next(layer for layer in spec["layer"] if layer["name"] == "bending percent series outside assessment window")
    assert context_layer["mark"]["opacity"] < assessed_layer["mark"].get("opacity", 1)
    point_layer = next(layer for layer in spec["layer"] if layer["name"] == "exceedance points")
    assert point_layer["mark"]["color"] == "#d9786d"
    assert all(200 <= row["load_N"] <= 600 for row in point_layer["data"]["values"])
    segment_layer = next(layer for layer in spec["layer"] if layer["name"] == "exceedance segments")
    assert all(200 <= row["start_load_N"] <= row["end_load_N"] <= 600 for row in segment_layer["data"]["values"])
    annotation_layer = next(layer for layer in spec["layer"] if layer["name"] == "threshold annotation")
    assert annotation_layer["data"]["values"][0]["label"] == "5% threshold"
    assert annotation_layer["data"]["values"][0]["load_N"] == 700
    assert annotation_layer["mark"]["align"] == "right"
    assert annotation_layer["encoding"]["x"]["scale"] == {"domain": [0.0, 700.0], "nice": False}


def test_aggregate_curve_family_spec_surfaces_reference_band_and_outlier_state() -> None:
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_plot",
            aligned_rows=_aligned_rows(),
            reference_rows=_reference_rows(),
            diagnostic_scores=_scores(),
            plot_data_freshness={
                "schema_id": "report.plot_data_freshness.v0_1",
                "status": "current",
                "replicate_source": "curve_shape_diagnostic_residual_rows",
                "alignment_domain": "experiment_progress",
                "source_boundaries": "method_resolve.experiment_boundaries",
            },
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    layer_names = {layer["name"] for layer in spec["layer"]}
    assert "cohort variability band" in layer_names
    assert "all evaluable curves by Dixon rank" in layer_names
    assert "mean or median curve" in layer_names
    semantic_layers = set(spec["usermeta"]["semantic_layers"])
    assert "all_evaluable_curves" in semantic_layers
    assert "reference_curve" in semantic_layers
    assert "variability_band" in semantic_layers
    assert "dixon_rank_coloring" in semantic_layers
    assert "outlier_candidate_curves" in semantic_layers
    assert spec["usermeta"]["plot_data_freshness"]["status"] == "current"
    assert spec["usermeta"]["plot_data_freshness"]["replicate_source"] == "curve_shape_diagnostic_residual_rows"
    assert "The x-axis is strain normalised to each run's resolved experimental window." in spec["usermeta"]["caption"]
    curve_layer = next(layer for layer in spec["layer"] if layer["name"] == "all evaluable curves by Dixon rank")
    assert curve_layer["encoding"]["x"]["title"] == "Normalised strain / %"


def test_aggregate_curve_family_fallback_uses_experiment_progress_window() -> None:
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_plot",
            aligned_rows=[],
            reference_rows=[],
            fallback_curves=[
                {
                    "run_id": "run_001",
                    "point_index": 10,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 0.2,
                    "mean_strain": 0.10,
                    "stress_MPa": 0.0,
                },
                {
                    "run_id": "run_001",
                    "point_index": 15,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 0.7,
                    "mean_strain": 0.20,
                    "stress_MPa": 50.0,
                },
                {
                    "run_id": "run_001",
                    "point_index": 20,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 0.9,
                    "mean_strain": 0.30,
                    "stress_MPa": 100.0,
                },
                {
                    "run_id": "run_001",
                    "point_index": 22,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 1.2,
                    "mean_strain": 0.40,
                    "stress_MPa": 120.0,
                },
            ],
            diagnostic_scores=_scores(),
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    curve_layer = next(layer for layer in spec["layer"] if layer["name"] == "all evaluable curves by Dixon rank")
    x_values = [row["x"] for row in curve_layer["data"]["values"]]
    assert x_values == [0.0, 50.0, 100.0]
    assert max(x_values) == 100.0
    assert spec["usermeta"]["plot_data_freshness"]["replicate_source"] == "bounded_curve_family"


def test_aggregate_curve_family_aligned_rows_prefer_boundary_progress() -> None:
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_plot",
            aligned_rows=[
                {
                    "run_id": "run_001",
                    "point_index": 10,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 0.3,
                    "y_observed": 0.0,
                },
                {
                    "run_id": "run_001",
                    "point_index": 20,
                    "boundary_start_index": 10,
                    "boundary_end_index": 20,
                    "experiment_progress": 0.8,
                    "y_observed": 100.0,
                },
            ],
            reference_rows=[],
            diagnostic_scores=_scores(),
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    curve_layer = next(layer for layer in spec["layer"] if layer["name"] == "all evaluable curves by Dixon rank")
    assert [row["x"] for row in curve_layer["data"]["values"]] == [0.0, 100.0]


def test_aggregate_curve_family_reference_rows_prefer_canonical_analysis_progress() -> None:
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_plot",
            aligned_rows=[
                {"run_id": "run_001", "analysis_progress_percent": 0.0, "x_common": 0.2, "y_observed": 0.0},
                {"run_id": "run_001", "analysis_progress_percent": 100.0, "x_common": 0.8, "y_observed": 100.0},
            ],
            reference_rows=[
                {"analysis_progress_percent": 0.0, "x_common": 0.2, "y_reference": 0.0, "y_lower": 0.0, "y_upper": 0.0},
                {
                    "analysis_progress_percent": 100.0,
                    "x_common": 0.8,
                    "y_reference": 100.0,
                    "y_lower": 90.0,
                    "y_upper": 110.0,
                },
            ],
            diagnostic_scores=_scores(),
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    curve_layer = next(layer for layer in spec["layer"] if layer["name"] == "all evaluable curves by Dixon rank")
    reference_layer = next(layer for layer in spec["layer"] if layer["name"] == "mean or median curve")
    band_layer = next(layer for layer in spec["layer"] if layer["name"] == "cohort variability band")
    assert [row["x"] for row in curve_layer["data"]["values"]] == [0.0, 100.0]
    assert [row["x"] for row in reference_layer["data"]["values"]] == [0.0, 100.0]
    assert [row["x"] for row in band_layer["data"]["values"]] == [0.0, 100.0]


def test_aggregate_curve_family_missing_progress_does_not_fallback_to_actual_strain() -> None:
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_plot",
            aligned_rows=[],
            reference_rows=[],
            fallback_curves=[
                {
                    "run_id": "run_001",
                    "point_index": 10,
                    "mean_strain": 0.10,
                    "stress_MPa": 50.0,
                }
            ],
            diagnostic_scores=_scores(),
        )
    )

    assert result.status == "unavailable"
    assert "no plottable stress values" in result.fallback_message


def test_curve_shape_distance_and_residual_specs_keep_threshold_methods_distinct() -> None:
    dixon = plot_registry.build(curve_shape_distance_ranking_request(plot_id="distance_dixon", scores=_scores()))
    assert dixon.status == "rendered"
    assert "dixon_high_outlier_q_test" in str(dixon.spec)
    assert "robust_mad_zscore" not in str(dixon.spec)
    assert "threshold_method_annotation" in dixon.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "dixon_q_test_against_critical_threshold" in dixon.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "dixon_gap_denominator_geometry" in dixon.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "vconcat" not in dixon.spec
    assert "Dixon gap vertical bracket" in str(dixon.spec)
    assert "Dixon Q decision annotation" in str(dixon.spec)

    mad_scores = [
        {
            **row,
            "threshold_method": "robust_mad_zscore",
            "Qexp": "",
            "Qcrit_95": "",
            "robust_z": 1.8 - index * 0.4,
            "z_mad": 1.8 - index * 0.4,
            "mad_upper_z": max(0.0, 1.8 - index * 0.4),
            "threshold_value": 3.5,
        }
        for index, row in enumerate(_scores())
    ]
    mad = plot_registry.build(curve_shape_distance_ranking_request(plot_id="distance_mad", scores=mad_scores))
    assert mad.status == "rendered"
    assert "robust_mad_zscore" in str(mad.spec)
    assert "mad_upper_tail_score_by_run" in mad.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "mad_upper_tail_threshold" in mad.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "Upper-tail MAD cutoff" in str(mad.spec)
    assert "below-median signed z_mad values are displayed as zero" in mad.spec["usermeta"]["caption"]  # type: ignore[index]
    assert "No Dixon Q threshold panel" not in str(mad.spec)

    residual = plot_registry.build(
        curve_shape_residuals_request(
            plot_id="residuals",
            residuals=[
                {"run_id": "run_001", "x_common": 0.0, "standardized_residual": 0.0},
                {"run_id": "run_001", "x_common": 0.5, "standardized_residual": 1.2},
            ],
            scores=_scores(),
        )
    )
    assert residual.status == "rendered"
    assert "residual_curves" in residual.spec["usermeta"]["semantic_layers"]  # type: ignore[index]
    assert "zero_line" in residual.spec["usermeta"]["semantic_layers"]  # type: ignore[index]


def test_aggregate_curve_family_mad_branch_uses_mad_labels() -> None:
    mad_scores = [
        {
            **row,
            "threshold_method": "robust_mad_zscore",
            "Qexp": "",
            "Qcrit_95": "",
            "robust_z": 1.8 - index * 0.4,
            "z_mad": 1.8 - index * 0.4,
            "mad_upper_z": max(0.0, 1.8 - index * 0.4),
            "threshold_value": 3.5,
        }
        for index, row in enumerate(_scores())
    ]
    result = plot_registry.build(
        aggregate_curve_family_request(
            plot_id="aggregate_curve_family_mad_plot",
            aligned_rows=_aligned_rows(),
            reference_rows=_reference_rows(),
            diagnostic_scores=mad_scores,
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    layer_names = {layer["name"] for layer in spec["layer"]}
    assert "all evaluable curves by upper-tail MAD score" in layer_names
    semantic_layers = set(spec["usermeta"]["semantic_layers"])
    assert "mad_zscore_coloring" in semantic_layers
    assert "dixon_rank_coloring" not in semantic_layers
    assert "Upper-tail MAD score" in str(spec)
    assert "Dixon rank (1 = most distant)" not in str(spec)


def test_curve_shape_distance_plot_sorts_by_rank_and_uses_prose_decision() -> None:
    result = plot_registry.build(
        curve_shape_distance_ranking_request(
            plot_id="distance_dixon_ranked",
            scores=[
                {
                    "run_id": "run_001",
                    "specimen": "Specimen 1",
                    "distance_rms": 0.46,
                    "distance_rank": 6,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_002",
                    "specimen": "Specimen 2",
                    "distance_rms": 1.07,
                    "distance_rank": 3,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_003",
                    "specimen": "Specimen 3",
                    "distance_rms": 0.28,
                    "distance_rank": 7,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_004",
                    "specimen": "Specimen 4",
                    "distance_rms": 0.68,
                    "distance_rank": 4,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_005",
                    "specimen": "Specimen 5",
                    "distance_rms": 0.53,
                    "distance_rank": 5,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_006",
                    "specimen": "Specimen 6",
                    "distance_rms": 1.31,
                    "distance_rank": 2,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
                {
                    "run_id": "run_007",
                    "specimen": "Specimen 7",
                    "distance_rms": 1.447,
                    "distance_rank": 1,
                    "Qexp": 0.117,
                    "Qcrit_95": 0.568,
                    "threshold_method": "dixon_high_outlier_q_test",
                    "diagnostic_classification": "CURVE_SHAPE_NORMAL",
                },
            ],
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    expected_order = ["#7", "#6", "#2", "#4", "#5", "#1", "#3"]
    bar_layer = next(layer for layer in spec["layer"] if layer["name"] == "distance_rms by run")
    assert [row["run_label"] for row in bar_layer["data"]["values"]] == expected_order
    assert bar_layer["encoding"]["x"]["scale"]["domain"] == expected_order
    assert bar_layer["encoding"]["x"]["axis"]["labelAngle"] == -35
    assert bar_layer["encoding"]["x"]["title"] == "Run (sorted by curve difference rank)"
    assert bar_layer["encoding"]["y"]["title"] == "Curve difference score"
    assert bar_layer["encoding"]["y"]["scale"] == {"domain": [0, 1.5], "nice": False}
    for layer_name in (
        "Dixon gap vertical bracket",
        "Dixon gap bracket ticks",
        "Dixon denominator vertical bracket",
        "Dixon denominator bracket ticks",
        "Dixon bracket labels",
        "Dixon Q decision annotation",
    ):
        layer = next(item for item in spec["layer"] if item["name"] == layer_name)
        assert "axis" not in layer["encoding"]["x"]
        assert "title" not in layer["encoding"]["x"]
        assert "axis" not in layer["encoding"]["y"]
        assert "title" not in layer["encoding"]["y"]
    decision_layer = next(layer for layer in spec["layer"] if layer["name"] == "Dixon Q decision annotation")
    decision_text = decision_layer["data"]["values"][0]["q_label"]
    assert "not an outlier" in decision_text
    assert "CURVE_SHAPE_NORMAL" not in decision_text
    assert decision_layer["mark"]["lineBreak"] == "\n"


def test_curve_shape_distance_plot_uses_reported_dixon_denominator() -> None:
    scores = [
        ("run_004", 1.9690, 1),
        ("run_009", 1.6320, 2),
        ("run_010", 0.7800, 3),
        ("run_008", 0.6100, 4),
        ("run_001", 0.5945, 5),
        ("run_003", 0.5184, 6),
        ("run_005", 0.5000, 7),
        ("run_006", 0.4900, 8),
        ("run_002", 0.4541, 9),
        ("run_007", 0.4200, 10),
    ]
    rows = []
    for run_id, distance, rank in scores:
        row = {
            "run_id": run_id,
            "distance_rms": distance,
            "distance_rank": rank,
            "Qcrit_95": 0.534,
            "threshold_method": "dixon_high_outlier_q_test",
            "diagnostic_classification": "CURVE_SHAPE_NORMAL",
            "dixon_variant": "r11",
            "dixon_denominator_low_run_id": "run_002",
            "dixon_denominator_low_score": 0.4541,
        }
        if rank == 1:
            row.update({"Qexp": 0.22245, "dixon_gap": 0.3370, "dixon_denominator": 1.5149})
        rows.append(row)

    result = plot_registry.build(
        curve_shape_distance_ranking_request(
            plot_id="distance_dixon_r11",
            scores=rows,
        )
    )

    assert result.status == "rendered"
    spec = result.spec or {}
    decision_layer = next(layer for layer in spec["layer"] if layer["name"] == "Dixon Q decision annotation")
    geometry = decision_layer["data"]["values"][0]
    assert geometry["denominator"] == 1.5149
    assert geometry["denominator_low_run"] == "#2"
    assert "Qexp (r11) = gap/denominator" in geometry["q_label"]
    bracket_labels = next(layer for layer in spec["layer"] if layer["name"] == "Dixon bracket labels")
    assert any("r11 denominator = 1.51" == row["label"] for row in bracket_labels["data"]["values"])


def test_curve_shape_distance_plot_surfaces_dixon_companion_screen() -> None:
    rows = []
    for run_id, distance, rank, companion_flag in [
        ("run_004", 1.9690, 1, True),
        ("run_009", 1.6320, 2, True),
        ("run_010", 0.7800, 3, False),
        ("run_008", 0.6100, 4, False),
        ("run_001", 0.5945, 5, False),
        ("run_003", 0.5184, 6, False),
        ("run_005", 0.5000, 7, False),
        ("run_006", 0.4900, 8, False),
        ("run_002", 0.4541, 9, False),
        ("run_007", 0.4200, 10, False),
    ]:
        row = {
            "run_id": run_id,
            "distance_rms": distance,
            "distance_rank": rank,
            "Qcrit_95": 0.534,
            "threshold_method": "dixon_high_outlier_q_test",
            "secondary_threshold_method": "robust_mad_masking_screen",
            "diagnostic_classification": "CURVE_SHAPE_OUTLIER" if companion_flag else "CURVE_SHAPE_NORMAL",
            "masking_companion_flag": companion_flag,
            "mad_upper_z": 8.0 if companion_flag else 0.0,
            "dixon_variant": "r11",
            "dixon_decision": "no_outlier",
            "dixon_denominator_low_run_id": "run_002",
            "dixon_denominator_low_score": 0.4541,
        }
        if rank == 1:
            row.update({"Qexp": 0.22245, "dixon_gap": 0.3370, "dixon_denominator": 1.5149})
        rows.append(row)

    result = plot_registry.build(curve_shape_distance_ranking_request(plot_id="distance_dixon_companion", scores=rows))

    assert result.status == "rendered"
    spec = result.spec or {}
    assert "mad_masking_companion_screen" in spec["usermeta"]["semantic_layers"]
    assert "Companion MAD score" in str(spec)
    assert "Red bars can therefore represent either the formal Dixon candidate or a companion MAD masking review flag" in spec["usermeta"]["caption"]


def test_quality_policy_flags_missing_data_and_avoids_raw_visible_titles() -> None:
    result = plot_registry.build(
        PlotRequest(
            plot_type="generic_xy_overlay",
            plot_id="generic",
            data_payload={
                "rows": [{"x": 0, "y": 1, "series": "a"}],
                "x_title": "Strain / %",
                "y_title": "Stress / MPa",
            },
        )
    )
    assert result.status == "rendered"
    assert result.quality_report is not None
    assert result.quality_report.warnings == []

    missing = plot_registry.build(
        PlotRequest(plot_type="generic_xy_overlay", plot_id="generic_missing", data_payload={"rows": []})
    )
    assert missing.status == "unavailable"
    assert missing.quality_report is not None
    assert missing.quality_report.has_data is False


def _stress_rows() -> list[dict[str, Any]]:
    return [
        {
            "run_id": "run_001",
            "point_index": index,
            "mean_strain": index * 0.0005,
            "front_strain_abs": index * 0.00045,
            "rear_strain_abs": index * 0.00055,
            "stress_MPa": index * 12.5,
            "load_N": index * 100.0,
        }
        for index in range(1, 8)
    ]


def _stress_raw_rows() -> list[dict[str, Any]]:
    rows = _stress_rows()
    rows.extend(
        {
            "run_id": "run_001",
            "point_index": index,
            "mean_strain": index * 0.0005,
            "front_strain_abs": index * 0.00045,
            "rear_strain_abs": index * 0.00055,
            "stress_MPa": stress,
            "load_N": stress * 8.0,
        }
        for index, stress in ((8, 70.0), (9, 45.0), (10, 20.0), (11, 8.0), (12, 4.0))
    )
    return rows


def _stress_block() -> dict[str, Any]:
    return {
        "markers": {
            "experiment_start": {"index": 1},
            "experiment_end": {"index": 7},
            "max_load_strength": {"index": 7, "stress_MPa": 87.5},
            "chord_line": {"x_start": 0.0005, "y_start": 12.5, "x_end": 0.0025, "y_end": 62.5},
        },
        "evidence_refs": {"bounded_curve": "method_outputs/curves/run_001.csv"},
    }


def _bending_block() -> dict[str, Any]:
    return {
        "summary": {"classification": "FAIL_SUSTAINED_BENDING", "threshold_percent": 5},
        "markers": {
            "threshold_line": {"bending_percent": 5},
            "assessment_window_10_90_fmax": {"load_window_N": [200, 600]},
            "exceedance_segments": [
                {
                    "start_load_N": 500,
                    "end_load_N": 700,
                    "segment_classification": "sustained_region",
                }
            ],
        },
    }


def _aligned_rows() -> list[dict[str, Any]]:
    return [
        {"run_id": "run_001", "x_common": 0.0, "y_observed": 0.0},
        {"run_id": "run_001", "x_common": 0.5, "y_observed": 100.0},
        {"run_id": "run_002", "x_common": 0.0, "y_observed": 0.0},
        {"run_id": "run_002", "x_common": 0.5, "y_observed": 160.0},
    ]


def _reference_rows() -> list[dict[str, Any]]:
    return [
        {"x_common": 0.0, "y_reference": 0.0, "y_lower": 0.0, "y_upper": 0.0, "support_n": 2},
        {"x_common": 0.5, "y_reference": 130.0, "y_lower": 100.0, "y_upper": 160.0, "support_n": 2},
    ]


def _scores() -> list[dict[str, Any]]:
    return [
        {
            "run_id": "run_002",
            "specimen": "Specimen 2",
            "distance_rms": 1.3,
            "distance_rank": 1,
            "Qexp": 0.7,
            "Qcrit_95": 0.568,
            "threshold_method": "dixon_high_outlier_q_test",
            "diagnostic_classification": "CURVE_SHAPE_OUTLIER",
        },
        {
            "run_id": "run_001",
            "specimen": "Specimen 1",
            "distance_rms": 0.2,
            "distance_rank": 2,
            "Qexp": "",
            "Qcrit_95": 0.568,
            "threshold_method": "dixon_high_outlier_q_test",
            "diagnostic_classification": "CURVE_SHAPE_NORMAL",
        },
    ]
