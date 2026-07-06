from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout


TEST_HTML = f"{MTDAAlignedLayout.reports_prefix}test_report.html"
TEST_JSON = f"{MTDAAlignedLayout.reports_prefix}test_report.json"
METHOD_OUTPUTS = MTDAAlignedLayout.method_outputs


def test_test_report_remains_formal_result_oriented(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, TEST_HTML)
    report = _json_member(stage26_canonical_mtda, TEST_JSON)

    assert "ISO 14126 Test Report" in html
    assert report["summary"]["selection_set"] == "final_report_runs"
    assert "Run-wise audit packets" not in html
    assert "Stress-strain reduction evidence" not in html
    assert "audit/procedure_evidence_index.json" not in html
    assert "audit/audit_blocks.json" not in html


def test_workbench_remains_operation_level_debug_surface(stage26_canonical_mtda: Path) -> None:
    trace = _json_member(stage26_canonical_mtda, METHOD_OUTPUTS)["operation_trace"]
    operations = trace["operations"]

    assert operations
    boundary = next(row for row in operations if row["operation_type"] == "resolve_experiment_boundaries")
    assert boundary["workbench_view"] == "boundary_resolution_view"
    assert boundary["view_type"] in {"experiment_boundary_resolution", "boundary_markers_overlay", "boundary_resolution_view"}
    assert trace["experiment_boundaries"]


def test_surface_manifest_declares_role_split(stage26_canonical_mtda: Path) -> None:
    manifest = _json_member(stage26_canonical_mtda, MTDAAlignedLayout.surface_manifest)
    roles = manifest["operator_handoff"]["surface_roles"]

    assert roles["test_report"] == "Final formal report."
    assert roles["audit_report"] == "Scientific audit evidence."
    assert roles["metadata"] == "Machine reproducibility and integrity trace."
    assert roles["processed_data"] == "Run-level summaries, CSVs, and plots."
    assert manifest["surfaces"]["audit_report"]["json_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.json"
    assert manifest["surfaces"]["audit_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
