from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.blocks.vega_plot import VegaPlotBlock
from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.report_context import ReportContext


def test_failure_analysis_bending_distribution_vega_spec_has_threshold_band_and_summary_interval() -> None:
    source = {
        "spec_id": "failure_analysis_bending_distribution",
        "threshold_percent": 10.0,
        "assessed_domain": "10-90 % Fmax",
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
                "point_count": 4,
                "bending_pattern": "PASS",
            }
        ],
        "points": [
            {
                "run_id": "run_001",
                "run_label": "#1",
                "specimen_name": "S1",
                "bending_percent": value,
                "median_bending_percent": 5.0,
                "p95_bending_percent": 8.0,
                "max_bending_percent": 9.0,
                "fraction_above_threshold": 0.0,
                "points_above_threshold": 0,
                "assessed_point_count": 4,
                "jitter": index * 0.01,
            }
            for index, value in enumerate([4.0, 5.0, 6.0, 9.0])
        ],
    }
    context = ReportContext(
        result=SimpleNamespace(),
        recipe={},
        selection_set="final_report_runs",
        selection_run_ids={"run_001"},
        curve_policy={},
        tables={"failure_analysis_bending_distribution": source},
    )

    block = VegaPlotBlock().resolve(
        {
            "id": "bending_distribution_plot",
            "type": "vega_plot",
            "provider": "failure_analysis_bending_distribution",
            "spec": "failure_analysis_bending_distribution",
        },
        context,
        DataProviderRegistry(),
    )
    spec = block.data["vega_lite_spec"]

    assert block.data["spec_id"] == "failure_analysis_bending_distribution"
    assert spec["datasets"]["threshold"] == [{"threshold_percent": 10.0}]
    assert spec["datasets"]["criterion_band"][0]["threshold_percent"] == 10.0
    mark_types = [layer["mark"]["type"] for layer in spec["layer"]]
    assert mark_types == ["rect", "rule", "rule", "bar", "tick"]
    assert spec["layer"][3]["encoding"]["y"]["field"] == "q1_bending_percent"
    assert spec["layer"][3]["encoding"]["y2"]["field"] == "q3_bending_percent"
    assert not any(layer["mark"]["type"] == "point" for layer in spec["layer"])
    assert "legend" not in spec.get("config", {})
    assert "color" not in spec["layer"][2]["encoding"]
    body_color = spec["layer"][3]["encoding"]["color"]
    assert body_color["field"] == "bending_pattern_group"
    assert body_color["title"] == "Bending pattern"
    assert body_color["scale"]["domain"] == ["PASS", "WARN", "FAIL"]
    assert body_color["scale"]["range"] == ["#74b88b", "#e6b45a", "#d9786d"]
    tooltip_fields = {
        item["field"]
        for layer in spec["layer"][1:]
        for item in layer["encoding"]["tooltip"]
    }
    assert "bending_classification_label" not in tooltip_fields
    assert {"fraction_above_threshold", "points_above_threshold", "assessed_point_count"} <= tooltip_fields
