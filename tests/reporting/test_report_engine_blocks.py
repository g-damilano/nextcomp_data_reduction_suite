from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.core.block_registry import BlockRegistry
from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.report_context import ReportContext
from plotting.models import PlotRequest
from plotting.plots.formal_report import (
    FORMAL_AGGREGATE_PLOT_TYPE,
    FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
    aggregate_stress_strain_vega_lite,
    failure_analysis_bending_distribution_vega_lite,
)
from plotting.registry import plot_registry


def test_formal_report_plot_types_are_registered_and_preserve_legacy_specs() -> None:
    assert FORMAL_AGGREGATE_PLOT_TYPE in plot_registry.plot_types()
    assert FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE in plot_registry.plot_types()

    source_spec = {"schema_id": "method.aggregate_plot_spec.v0_1"}
    aligned_curves = [
        {
            "analysis_progress": 0.0,
            "mean": 10.0,
            "std": 0.0,
            "min": 10.0,
            "max": 10.0,
            "n": 1,
        }
    ]
    aggregate_request = PlotRequest(
        plot_type=FORMAL_AGGREGATE_PLOT_TYPE,
        plot_id="aggregate_stress_strain_mean_variability",
        data_payload={
            "source_spec": source_spec,
            "aligned_curves": aligned_curves,
            "replicate_curves": [],
            "selected_run_ids": ["run_001"],
            "endpoint_strains": {},
            "boundary_records": [],
            "replicate_source": "none",
            "source_warnings": [],
        },
        surface_context="test_report",
    )
    aggregate_result = plot_registry.build(aggregate_request)
    assert aggregate_result.spec == aggregate_stress_strain_vega_lite(
        source_spec=source_spec,
        aligned_curves=aligned_curves,
        replicate_curves=[],
        selected_run_ids={"run_001"},
        endpoint_strains={},
        boundary_records=[],
        replicate_source="none",
        source_warnings=[],
    )
    assert aggregate_result.plot_type == "aggregate_curve_family"

    bending_source = _bending_distribution_source()
    bending_request = PlotRequest(
        plot_type=FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
        plot_id=FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE,
        data_payload={"source_spec": bending_source},
        surface_context="test_report",
    )
    bending_result = plot_registry.build(bending_request)
    assert bending_result.spec == failure_analysis_bending_distribution_vega_lite(bending_source)
    assert bending_result.plot_type == FORMAL_BENDING_DISTRIBUTION_PLOT_TYPE


def test_block_registry_resolves_field_table_and_vega_plot() -> None:
    context = ReportContext(
        result=None,  # type: ignore[arg-type]
        recipe={},
        selection_set="selected",
        selection_run_ids={"run_001"},
        curve_policy={},
        values_by_key={"operator": "Ada"},
        tables={"aggregate_plot_spec": {"schema_id": "method.aggregate_plot_spec.v0_1"}},
    )
    blocks = BlockRegistry()
    providers = DataProviderRegistry()

    field_block = blocks.resolve(
        {
            "id": "operator_fields",
            "type": "field_table",
            "provider": "report_values",
            "fields": [{"label": "Operator", "key": "operator"}],
        },
        context,
        providers,
    )
    plot_block = blocks.resolve(
        {
            "id": "aggregate_plot",
            "type": "vega_plot",
            "provider": "aligned_curves",
            "spec": "aggregate_stress_strain_mean_variability",
        },
        context,
        providers,
    )

    assert "field_table" in blocks.block_types()
    assert "vega_plot" in blocks.block_types()
    assert field_block.data == [{"label": "Operator", "key": "operator", "value": "Ada", "status": "present"}]
    assert plot_block.data["schema_id"] == "report.vega_plot_block.v0_1"
    assert plot_block.data["source_spec"]["schema_id"] == "method.aggregate_plot_spec.v0_1"
    assert plot_block.data["vega_lite_spec"]["$schema"] == "https://vega.github.io/schema/vega-lite/v5.json"
    assert plot_block.data["plot_result"]["plot_type"] == "aggregate_curve_family"
    assert plot_block.data["plot_result"]["quality_report"]["tooltip_present"] is True


def test_aggregate_plot_uses_normalised_strain_for_aggregate_and_actual_strain_for_replicates() -> None:
    result = SimpleNamespace(
        experiment_boundaries=[
            {
                "run_id": "run_001",
                "analysis_interval": {"start_index": 10, "end_index": 20},
                "resolution_policy": {
                    "end_policy": "slope_break_pre_negative",
                    "slope_break": {"slope_domain": "strain"},
                    "signature": "first_point->slope_break_pre_negative:domain=strain",
                },
            }
        ],
        bounded_curve_family=[
            {
                "run_id": "run_001",
                "point_index": 10,
                "experiment_progress": 0.25,
                "boundary_start_index": 10,
                "boundary_end_index": 20,
                "mean_strain": 0.001,
                "stress_MPa": 10.0,
            },
            {
                "run_id": "run_001",
                "point_index": 15,
                "experiment_progress": 0.75,
                "boundary_start_index": 10,
                "boundary_end_index": 20,
                "mean_strain": 0.006,
                "stress_MPa": 55.0,
            },
            {
                "run_id": "run_001",
                "point_index": 20,
                "experiment_progress": 1.2,
                "boundary_start_index": 10,
                "boundary_end_index": 20,
                "mean_strain": 0.01,
                "stress_MPa": 100.0,
            },
        ],
        specimen_results=[
            {
                "run_id": "run_001",
                "compressive_failure_strain": 0.2,
                "compressive_strength_MPa": 100.0,
            }
        ],
    )
    context = ReportContext(
        result=result,  # type: ignore[arg-type]
        recipe={},
        selection_set="selected",
        selection_run_ids={"run_001"},
        curve_policy={},
        values_by_key={},
        tables={
            "aggregate_plot_spec": {"schema_id": "method.aggregate_plot_spec.v0_1"},
            "aligned_curves": [
                {
                    "alignment_domain": "experiment_progress",
                    "source_boundaries": "method_resolve.experiment_boundaries",
                    "experiment_progress": 0.0,
                    "x_normalized": 0.0,
                    "run_001_stress_MPa": 10.0,
                    "mean": 10.0,
                    "std": 0.0,
                    "min": 10.0,
                    "max": 10.0,
                    "n": 1,
                },
                {
                    "alignment_domain": "experiment_progress",
                    "source_boundaries": "method_resolve.experiment_boundaries",
                    "experiment_progress": 0.5,
                    "x_normalized": 0.5,
                    "run_001_stress_MPa": 55.0,
                    "mean": 55.0,
                    "std": 0.0,
                    "min": 55.0,
                    "max": 55.0,
                    "n": 1,
                },
                {
                    "alignment_domain": "experiment_progress",
                    "source_boundaries": "method_resolve.experiment_boundaries",
                    "experiment_progress": 1.0,
                    "x_normalized": 1.0,
                    "run_001_stress_MPa": 100.0,
                    "mean": 100.0,
                    "std": 0.0,
                    "min": 100.0,
                    "max": 100.0,
                    "n": 1,
                },
            ],
        },
    )

    block = BlockRegistry().resolve(
        {
            "id": "aggregate_plot",
            "type": "vega_plot",
            "provider": "aligned_curves",
            "spec": "aggregate_stress_strain_mean_variability",
        },
        context,
        DataProviderRegistry(),
    )

    spec = block.data["vega_lite_spec"]
    aggregate_values = spec["datasets"]["aggregate"]
    replicate_values = spec["datasets"]["replicates"]
    assert [round(row["analysis_progress_percent"], 6) for row in aggregate_values] == [0.0, 50.0, 100.0]
    assert all("strain_percent" not in row for row in aggregate_values)
    assert [round(row["actual_strain_percent"], 6) for row in replicate_values] == [0.1, 0.6, 1.0]
    assert max(row["actual_strain_percent"] for row in replicate_values) != 20.0
    assert spec["hconcat"][0]["encoding"]["x"]["title"] == "Actual strain / %"
    assert spec["hconcat"][1]["layer"][2]["encoding"]["x"]["title"] == "Normalised strain / %"
    assert spec["usermeta"]["plot_data_freshness"]["status"] == "current"
    assert spec["usermeta"]["plot_data_freshness"]["aggregate_x_field"] == "analysis_progress_percent"
    assert spec["usermeta"]["plot_data_freshness"]["replicate_x_field"] == "actual_strain_percent"
    assert spec["usermeta"]["plot_data_freshness"]["replicate_strain_source"] == "bounded_curve_family"


def test_aggregate_plot_does_not_reconstruct_replicate_strain_from_progress() -> None:
    result = SimpleNamespace(
        experiment_boundaries=[
            {
                "run_id": "run_001",
                "analysis_interval": {"start_index": 10, "end_index": 20},
                "resolution_policy": {
                    "end_policy": "slope_break_pre_negative",
                    "slope_break": {"slope_domain": "strain"},
                    "signature": "first_point->slope_break_pre_negative:domain=strain",
                },
            }
        ],
        bounded_curve_family=[],
        specimen_results=[
            {
                "run_id": "run_001",
                "compressive_failure_strain": 0.2,
                "compressive_strength_MPa": 100.0,
            }
        ],
    )
    context = ReportContext(
        result=result,  # type: ignore[arg-type]
        recipe={},
        selection_set="selected",
        selection_run_ids={"run_001"},
        curve_policy={},
        values_by_key={},
        tables={
            "aggregate_plot_spec": {"schema_id": "method.aggregate_plot_spec.v0_1"},
            "aligned_curves": [
                {
                    "alignment_domain": "experiment_progress",
                    "source_boundaries": "method_resolve.experiment_boundaries",
                    "analysis_progress": 1.0,
                    "experiment_progress": 1.0,
                    "run_001_stress_MPa": 100.0,
                    "mean": 100.0,
                    "std": 0.0,
                    "min": 100.0,
                    "max": 100.0,
                    "n": 1,
                }
            ],
        },
    )

    block = BlockRegistry().resolve(
        {
            "id": "aggregate_plot",
            "type": "vega_plot",
            "provider": "aligned_curves",
            "spec": "aggregate_stress_strain_mean_variability",
        },
        context,
        DataProviderRegistry(),
    )

    spec = block.data["vega_lite_spec"]
    assert spec["datasets"]["replicates"] == []
    freshness = spec["usermeta"]["plot_data_freshness"]
    assert freshness["status"] == "warning"
    assert any("No replicate plot rows" in reason for reason in freshness["reasons"])


def _bending_distribution_source() -> dict[str, Any]:
    return {
        "spec_id": "failure_analysis_bending_distribution",
        "threshold_percent": 10.0,
        "summary": [
            {
                "run_id": "run_001",
                "run_label": "#1",
                "specimen_name": "S1",
                "min_bending_percent": 4.0,
                "q1_bending_percent": 4.75,
                "median_bending_percent": 5.0,
                "q3_bending_percent": 6.75,
                "p95_bending_percent": 8.0,
                "max_bending_percent": 9.0,
                "fraction_above_threshold": 0.0,
                "points_above_threshold": 0,
                "assessed_point_count": 4,
                "bending_pattern": "PASS",
            }
        ],
        "points": [],
    }
