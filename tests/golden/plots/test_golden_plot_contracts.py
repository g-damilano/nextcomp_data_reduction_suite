from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from archives.mtda.writer import _compact_plot_package_files
from audit.vega_specs import bending_spec, modulus_window_spec, stress_strain_family_spec
from plotting.evidence_adapters import (
    aggregate_curve_family_request,
    bending_evidence_request,
    curve_shape_distance_ranking_request,
    curve_shape_residuals_request,
    stress_strain_reduction_request,
)
from plotting.plots.formal_report import (
    aggregate_stress_strain_vega_lite,
    failure_analysis_bending_distribution_vega_lite,
)
from plotting.registry import plot_registry


GOLDEN = Path(__file__).with_name("golden_plot_contracts.json")


def test_current_production_plot_contracts_match_golden_baseline() -> None:
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))

    assert _current_contracts() == expected


def _current_contracts() -> dict[str, Any]:
    built_specs = {
        "golden_stress_strain_reduction": plot_registry.build(
            stress_strain_reduction_request(
                plot_id="stress",
                run_id="run_001",
                bounded_rows=_stress_rows(),
                block=_stress_block(),
            )
        ).spec,
        "golden_bending_evidence": plot_registry.build(
            bending_evidence_request(
                plot_id="bend",
                run_id="run_001",
                bounded_rows=_stress_rows(),
                block=_bending_block(),
            )
        ).spec,
        "golden_aggregate_curve_family": plot_registry.build(
            aggregate_curve_family_request(
                plot_id="agg",
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
        ).spec,
        "golden_curve_shape_distance_ranking": plot_registry.build(
            curve_shape_distance_ranking_request(plot_id="dist", scores=_scores())
        ).spec,
        "golden_curve_shape_residuals": plot_registry.build(
            curve_shape_residuals_request(
                plot_id="resid",
                residuals=_residuals(),
                scores=_scores(),
            )
        ).spec,
    }
    contracts = {
        golden_id: _spec_contract(spec or {})
        for golden_id, spec in built_specs.items()
    }
    contracts["golden_aggregate_stress_strain_mean_variability"] = _spec_contract(
        aggregate_stress_strain_vega_lite(
            source_spec={},
            aligned_curves=[
                {"analysis_progress": 0.0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 2},
                {"analysis_progress": 1.0, "mean": 120.0, "std": 10.0, "min": 100.0, "max": 140.0, "n": 2},
            ],
            replicate_curves=_stress_rows(),
            selected_run_ids={"run_001"},
            boundary_records=[],
            replicate_source="bounded_curve_family",
        )
    )
    contracts["golden_failure_analysis_bending_distribution"] = _spec_contract(
        failure_analysis_bending_distribution_vega_lite(
            {
                "threshold_percent": 10.0,
                "summary": [
                    {
                        "run_label": "run_001",
                        "specimen_name": "Specimen 1",
                        "min_bending_percent": 1.0,
                        "q1_bending_percent": 2.0,
                        "median_bending_percent": 3.0,
                        "q3_bending_percent": 4.0,
                        "p95_bending_percent": 5.0,
                        "max_bending_percent": 6.0,
                        "fraction_above_threshold": 0.0,
                        "points_above_threshold": 0,
                        "assessed_point_count": 10,
                        "bending_pattern": "PASS",
                    }
                ],
            }
        )
    )
    audit_rows = [
        {
            **row,
            "strain_mm_per_mm": row["mean_strain"],
        }
        for row in _stress_rows()
    ]
    contracts["golden_audit_stress_strain_family"] = _spec_contract(
        stress_strain_family_spec(audit_rows)
    )
    contracts["golden_audit_modulus_window"] = _spec_contract(
        modulus_window_spec(audit_rows)
    )
    contracts["golden_audit_bending_trace"] = _spec_contract(
        bending_spec(audit_rows, threshold_percent=5.0)
    )

    run_package = _compact_plot_package_files(
        plot_id="run_001_plot",
        plot_type="run_stress_strain_reduction_evidence",
        title="run_001 stress-strain evidence plot",
        spec=built_specs["golden_stress_strain_reduction"] or {},
        html_member="processed/runs/run_001_plot.html",
        source_refs=["processed/runs/run_001_stress_strain.csv"],
        plot_data_views=[
            {
                "dataset_id": "dataset_003",
                "role": "bounded average strain curve",
                "source_members": ["processed/runs/run_001_stress_strain_experiment_bound.csv"],
                "transform_id": "run.bounded_average_curve.v1",
                "fields": ["strain", "stress", "point_index", "series"],
            }
        ],
        plot_data_materialization="none",
    )
    contracts["golden_mtda_run_compact_stress_strain_evidence"] = _package_contract(
        run_package,
        "processed/runs/run_001_plot.plot_package.json",
    )

    aggregate_spec = aggregate_stress_strain_vega_lite(
        source_spec={},
        aligned_curves=[{"analysis_progress": 0.0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 2}],
        replicate_curves=[],
        selected_run_ids=set(),
        boundary_records=[],
        replicate_source="none",
    )
    dataset_package = _compact_plot_package_files(
        plot_id="dataset_plot",
        plot_type="dataset_aggregate_stress_strain",
        title="Dataset report",
        spec=aggregate_spec,
        html_member="aggregate/dataset_plot.html",
        source_refs=["aggregate/stress_strain_aligned.csv"],
        plot_data_views=[
            {
                "dataset_id": "dataset_001",
                "role": "all runs resampled curve family",
                "source_members": ["processed/runs/run_001_stress_strain_experiment_bound.csv"],
                "transform_id": "aggregate.all_runs_resampled_curve_family.v1",
                "fields": ["run_id", "x_common", "y_observed"],
            }
        ],
        plot_data_materialization="none",
    )
    contracts["golden_mtda_dataset_aggregate_compact_package"] = _package_contract(
        dataset_package,
        "aggregate/dataset_plot.plot_package.json",
    )
    return dict(sorted(contracts.items()))


def _spec_contract(spec: dict[str, Any]) -> dict[str, Any]:
    mark_types: list[str] = []
    layer_names: list[str] = []
    x_titles: list[str] = []
    y_titles: list[str] = []
    tooltip_fields: list[str] = []
    legend_titles: list[str] = []
    scale_channels: list[dict[str, Any]] = []

    for node in _walk(spec):
        mark = node.get("mark")
        if isinstance(mark, dict):
            mark_types.append(str(mark.get("type")))
        elif isinstance(mark, str):
            mark_types.append(mark)
        if node.get("name"):
            layer_names.append(str(node["name"]))
        encoding = node.get("encoding")
        if not isinstance(encoding, dict):
            continue
        for channel_name, titles in (("x", x_titles), ("y", y_titles)):
            channel = encoding.get(channel_name)
            if not isinstance(channel, dict):
                continue
            if channel.get("title"):
                titles.append(str(channel["title"]))
            if "scale" in channel:
                scale_channels.append(
                    {
                        "channel": channel_name,
                        "field": channel.get("field"),
                        "scale": channel.get("scale"),
                    }
                )
        color = encoding.get("color")
        if isinstance(color, dict) and color.get("title"):
            legend_titles.append(str(color["title"]))
        tooltip = encoding.get("tooltip")
        if isinstance(tooltip, list):
            tooltip_fields.extend(
                str(item["field"])
                for item in tooltip
                if isinstance(item, dict) and item.get("field")
            )

    usermeta = spec.get("usermeta") if isinstance(spec.get("usermeta"), dict) else {}
    freshness = usermeta.get("plot_data_freshness")
    return {
        "axis_titles": {"x": _unique(x_titles), "y": _unique(y_titles)},
        "freshness_status": freshness.get("status") if isinstance(freshness, dict) else None,
        "layer_names": _unique(layer_names),
        "layout_keys": [key for key in ("layer", "hconcat", "vconcat", "facet", "mark") if key in spec],
        "legend_titles": _unique(legend_titles),
        "mark_types": _unique(mark_types),
        "scale_channels": _unique(scale_channels),
        "schema": spec.get("$schema"),
        "semantic_layers": list(usermeta.get("semantic_layers") or []),
        "tooltip_fields": _unique(tooltip_fields),
    }


def _package_contract(files: dict[str, bytes], member: str) -> dict[str, Any]:
    package = json.loads(files[member].decode("utf-8"))
    projection_contracts = package.get("projection_contracts") if isinstance(package.get("projection_contracts"), dict) else {}
    semantic_contract = (
        projection_contracts.get("semantic_contract") if isinstance(projection_contracts.get("semantic_contract"), dict) else {}
    )
    staleness_contract = (
        projection_contracts.get("staleness_contract") if isinstance(projection_contracts.get("staleness_contract"), dict) else {}
    )
    return {
        "data_mode": package.get("data_mode"),
        "dataset_roles": [dataset.get("role") for dataset in package.get("datasets") or []],
        "export_keys": sorted((package.get("exports") or {}).keys()),
        "golden_id": package.get("golden_id"),
        "html_member": package.get("html_member"),
        "package_type": package.get("package_type"),
        "plot_data_view_schema_versions": _unique(
            [view.get("data_view_schema_version") for view in package.get("plot_data_views") or []]
        ),
        "plot_data_view_transform_ids": [
            view.get("transform_id") for view in package.get("plot_data_views") or []
        ],
        "plot_data_view_versions": [view.get("data_view_version") for view in package.get("plot_data_views") or []],
        "plot_id": package.get("plot_id"),
        "plot_type": package.get("plot_type"),
        "production_state": package.get("production_state"),
        "projection_contract_keys": sorted(projection_contracts.keys()),
        "projection_id": package.get("projection_id"),
        "projection_semantic_layer_ids": [
            layer.get("layer_id")
            for layer in semantic_contract.get("layers") or []
            if isinstance(layer, dict)
        ],
        "recipe_schema_version": package.get("recipe_schema_version"),
        "recipe_version": package.get("recipe_version"),
        "schema_version": package.get("schema_version"),
        "semantic_layer_ids": [layer.get("layer_id") for layer in package.get("semantic_layers") or []],
        "state_model_keys": sorted((package.get("state_model") or {}).keys()),
        "staleness_contract_keys": sorted(staleness_contract.keys()),
        "template_path": package.get("template_path"),
        "view_data_mode": package.get("view_data_mode"),
    }


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _unique(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


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


def _stress_block() -> dict[str, Any]:
    return {
        "markers": {
            "experiment_start": {"index": 1},
            "experiment_end": {"index": 7},
            "max_load_strength": {"index": 7, "stress_MPa": 87.5},
            "chord_line": {"x_start": 0.0005, "y_start": 12.5, "x_end": 0.0025, "y_end": 62.5},
        }
    }


def _bending_block() -> dict[str, Any]:
    return {
        "summary": {"classification": "FAIL_SUSTAINED_BENDING", "threshold_percent": 5},
        "markers": {
            "threshold_line": {"bending_percent": 5},
            "assessment_window_10_90_fmax": {"load_window_N": [200, 600]},
            "exceedance_segments": [
                {"start_load_N": 500, "end_load_N": 700, "segment_classification": "sustained_region"}
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


def _residuals() -> list[dict[str, Any]]:
    return [
        {"run_id": "run_001", "x_common": 0.0, "standardized_residual": 0.0},
        {"run_id": "run_001", "x_common": 0.5, "standardized_residual": 1.2},
    ]
