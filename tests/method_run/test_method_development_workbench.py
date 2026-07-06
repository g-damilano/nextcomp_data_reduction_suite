from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_development.py"


def test_method_development_workbench_generates_operation_trace(tmp_path: Path) -> None:
    output = tmp_path / "dev_trace"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--input",
            str(INPUT),
            "--method",
            str(METHOD),
            "--mapping",
            str(MAPPING),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Wrote development workbench" in completed.stdout
    assert (output / "index.html").exists()
    assert (output / "operation_trace.json").exists()
    assert (output / "trace_manifest.json").exists()
    assert (output / "snapshots" / "curve_rows_by_run.json").exists()

    trace = json.loads((output / "operation_trace.json").read_text(encoding="utf-8"))
    assert trace["trace_format"] == "method_development_trace"
    assert trace["method"]["method_id"] == "iso14126_2023"
    assert len(trace["runs"]) == 7
    assert len(trace["operations"]) >= 7 * 10
    assert trace["readiness"]["status"] == "READY_WITH_WARNINGS"
    assert trace["readiness"]["blocks_execution"] is False
    assert trace["readiness_summary"][0]["execution_critical_passed"] == trace["readiness_summary"][0]["execution_critical_total"]
    assert trace["resolved_inputs"]
    assert trace["missing_inputs"]
    assert trace["validation"]["summary"]["status"] == "pass"
    assert trace["validation_summary"][0]["total_checks"] == 12
    assert trace["validation_deviations"]
    assert trace["acceptance"]["default_selection_set"] == "auto_recommended_runs"
    assert trace["acceptance_summary"][0]["total_runs"] == 7
    assert trace["run_flags"]
    assert trace["selection_sets"]["schema_id"] == "method.selection_sets.v0_1"
    assert trace["selection_membership"]
    assert trace["discharged_runs"]
    assert next(run for run in trace["runs"] if run["run_id"] == "run_006")["validation_status"] == "pass"
    run_002 = next(run for run in trace["runs"] if run["run_id"] == "run_002")
    assert run_002["acceptance_state"] == "excluded"
    assert run_002["acceptance_flags"] >= 1
    assert run_002["included_in_default"] is False

    first = trace["operations"][0]
    assert first["recipe_step_id"].startswith("resolve.")
    assert first["implementation_path"].startswith("src/operations/")
    assert first["view_type"]

    operation_types = {record["operation_type"] for record in trace["operations"]}
    assert {
        "map_channel",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
        "bending_diagnostic",
    } <= operation_types
    assert "orient_strain_channels" not in operation_types

    mean_strain = next(
        record
        for record in trace["operations"]
        if record["run_id"] == "run_006" and record["recipe_step_id"] == "resolve.derive_mean_strain"
    )
    assert mean_strain["view_type"] == "mean_absolute_strain_construction"
    assert mean_strain["parameters"]["mode"] == "mean_absolute"
    assert mean_strain["evidence"]["formula"] == "mean_strain = mean(abs(front_strain_raw), abs(rear_strain_raw))"
    assert mean_strain["validation_status"] == "pass"
    assert any(check["field"] == "mean_strain_microstrain" for check in mean_strain["validation_checks"])

    chord = next(record for record in trace["operations"] if record["operation_type"] == "chord_slope")
    assert chord["parameters"]["x1"] == 0.0005
    assert chord["parameters"]["x2"] == 0.0025
    assert chord["inspection_refs"]

    bending = next(record for record in trace["operations"] if record["operation_type"] == "bending_diagnostic")
    assert bending["parameters"]["window_percent_of_max_load"] == [10.0, 90.0]
    assert bending["inspection_refs"]
    assert bending["view_type"] == "bending_pattern_assessment"
    assert bending["outputs"]["bending_diagnostic"]["pattern"]["classification"]
    assert "segments" in bending["outputs"]["bending_diagnostic"]

    html = (output / "index.html").read_text(encoding="utf-8")
    assert "Method Development Workbench" in html
    assert "<h1>Method Development Workbench</h1>" not in html
    assert "Operation-wise trace and visual audit" not in html
    assert 'id=\"runSelect\"' in html
    assert "runOptionLabel" in html
    assert 'id=\"timelinePanel\"' in html
    assert 'id=\"toggleTimeline\"' in html
    assert 'id=\"detailsPanel\"' in html
    assert 'id=\"toggleDetails\"' in html
    assert "function statusDotClass" in html
    assert 'data-tab=\"data\">Data</div>' in html
    assert 'data-tab=\"data\">Data table</div>' not in html
    assert "Cumulative operation data" in html
    assert "Newly introduced columns" in html
    assert "function cumulativeColumns" in html
    assert "Stepwise plot sequence" in html
    assert "Operation Guide" in html
    assert "Available operations from this method trace" in html
    assert "Before operation" in html
    assert "After operation" in html
    assert "front_strain_abs" in html
    assert "mean_absolute_strain_construction" in html
    assert "Readiness" in html
    assert "readinessPanel" in html
    assert "Pre-run Package Readiness" in html
    assert "Validation" in html
    assert "validationPanel" in html
    assert "Jump to first failed/warned validation" in html
    assert "Acceptance" in html
    assert "acceptancePanel" in html
    assert "Dataset Acceptance" in html
    assert "Selection set filter" in html
    assert "Bending Pattern" in html
    assert "exceeds_threshold" in html
    assert "Recipe editor" in html
    assert "Run edited recipes" in html
    assert "Open operation implementation" in html
    assert "Load / N" in html
    assert "Load (N)" not in html
