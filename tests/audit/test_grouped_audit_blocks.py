from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout


def test_grouped_audit_blocks_are_written_to_mtda(stage26_canonical_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        names = set(archive.namelist())
        blocks = _audit_blocks(archive)

    audit_report_member = f"{MTDAAlignedLayout.reports_prefix}audit_report.json"
    assert audit_report_member in names
    assert not any(name.startswith("audit/") for name in names)
    assert blocks["artifact"] == f"{audit_report_member}#audit_blocks"
    assert blocks["index_artifact"] == f"{audit_report_member}#audit_blocks"
    assert len(blocks["run_packets"]) == 7
    assert blocks["aggregate_packet"]["block_count"] == 4
    assert blocks["summary"]["aggregate_block_count"] == 4
    assert blocks["summary"]["bending_separate"] is True
    assert blocks["summary"]["stress_strain_grouping"].startswith("boundary")


def test_run_stress_strain_reduction_groups_calculation_evidence(stage26_canonical_mtda: Path) -> None:
    operations = _run_operations(stage26_canonical_mtda, "run_006")
    stress_ops = [row for row in operations if row.get("default_audit_block") == "run_stress_strain_reduction"]
    stress_types = {row["operation_type"] for row in stress_ops}

    assert {
        "resolve_experiment_boundaries",
        "construct_mean_series",
        "derive_stress",
        "max_point",
        "value_at_max",
        "chord_slope",
    } <= stress_types
    boundary = next(row for row in stress_ops if row["operation_type"] == "resolve_experiment_boundaries")
    assert boundary["evidence_refs"]["contract_ref_1"] == "audit/boundary_resolution.json"
    assert boundary["evidence_refs"]["operation_record"].startswith("audit/operation_log.json#")
    max_point = next(row for row in stress_ops if row["operation_type"] == "max_point" and "max_load_N" in row["outputs"])
    strength = next(row for row in stress_ops if row["operation_type"] == "max_point" and "compressive_strength_MPa" in row["outputs"])
    failure = next(row for row in stress_ops if row["operation_type"] == "value_at_max")
    modulus = next(row for row in stress_ops if row["operation_type"] == "chord_slope")
    assert max_point["outputs"]["max_load_N"]
    assert strength["outputs"]["compressive_strength_MPa"]
    assert failure["outputs"]["compressive_failure_strain"]
    assert modulus["outputs"]["compressive_modulus_MPa"]


def test_bending_evidence_is_a_separate_audit_block(stage26_canonical_mtda: Path) -> None:
    operations = _run_operations(stage26_canonical_mtda, "run_006")
    stress_ops = {
        row["operation_type"]
        for row in operations
        if row.get("default_audit_block") == "run_stress_strain_reduction"
    }
    bending_rows = [
        row
        for row in operations
        if row.get("default_audit_block") == "run_bending_evidence"
    ]
    bending_ops = {row["operation_type"] for row in bending_rows}
    assert "bending_diagnostic" not in stress_ops
    assert "bending_diagnostic" in bending_ops
    bending = bending_rows[0]
    assert "threshold_line" in bending["evidence_refs"]
    assert "assessment_window_10_90_fmax" in bending["evidence_refs"]
    assert "exceedance_segments" in bending["evidence_refs"]
    diagnostic = bending["outputs"]["bending_diagnostic"]
    assert diagnostic["pattern"]
    assert "threshold_percent" in diagnostic
    assert "points_above_threshold" in diagnostic
    assert "fraction_above_threshold" in diagnostic
    assert diagnostic["longest_segment"]["point_count"]
    assert "max_bending_percent" in diagnostic


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _audit_blocks(archive: zipfile.ZipFile) -> dict[str, Any]:
    audit = json.loads(archive.read(f"{MTDAAlignedLayout.reports_prefix}audit_report.json"))
    return audit["audit_blocks"]


def _run_operations(path: Path, run_id: str) -> list[dict[str, Any]]:
    method_outputs = _json_member(path, MTDAAlignedLayout.method_outputs)
    operations = method_outputs["operation_trace"]["operations"]
    return [row for row in operations if row.get("run_id") == run_id]
