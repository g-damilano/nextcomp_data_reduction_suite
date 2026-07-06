from __future__ import annotations

import inspect
import json
import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout
from archives.mtda import writer as mtda_writer
from archives.mtda.surface_manifest import build_surface_manifest


LEGACY_SURFACE_PATH_FRAGMENTS = (
    '"report/',
    '"audit/',
    '"software/',
    '"interactive_report/',
    '"workbench/',
    '"dataset/05_plots/',
    '"dataset/04_aggregate/',
    '"dataset/03_processed/',
    '"surface_manifest.json"',
)


def test_aligned_surface_manifest_quarantines_legacy_surface_paths(stage26_canonical_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        files = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/") and name != MTDAAlignedLayout.surface_manifest
        }

    rebuilt = build_surface_manifest(files)
    serialized = json.dumps(rebuilt, sort_keys=True)

    assert rebuilt["schema_id"] == "mtda.surface_manifest.v0_3"
    assert rebuilt["layout_version"] == MTDAAlignedLayout.name
    assert rebuilt["operator_handoff"]["open_test_report_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
    assert rebuilt["operator_handoff"]["open_audit_report_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
    assert rebuilt["surfaces"]["test_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert rebuilt["surfaces"]["audit_report"]["raw_html_member"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"

    for fragment in LEGACY_SURFACE_PATH_FRAGMENTS:
        assert fragment not in serialized


def test_aligned_surface_manifest_dispatch_wins_over_legacy_compatibility_members(stage26_canonical_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        files = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/") and name != MTDAAlignedLayout.surface_manifest
        }

    files.update(
        {
            "report/test_report.html": b"<html>legacy report</html>",
            "audit/audit_report.html": b"<html>legacy audit</html>",
            "software/manifest.json": b'{"layout":"mtda.recommended.v1"}',
            "software/surface_manifest.json": b'{"schema_id":"mtda.surface_manifest.v0_2"}',
            "surface_manifest.json": b'{"schema_id":"mtda.surface_manifest.v0_1"}',
            "workbench/index.html": b"<html>legacy workbench</html>",
        }
    )

    rebuilt = build_surface_manifest(files)
    serialized = json.dumps(rebuilt, sort_keys=True)

    assert rebuilt["schema_id"] == "mtda.surface_manifest.v0_3"
    assert rebuilt["layout_version"] == MTDAAlignedLayout.name
    assert "mtda.surface_manifest.v0_1" not in serialized
    assert "mtda.surface_manifest.v0_2" not in serialized
    for fragment in LEGACY_SURFACE_PATH_FRAGMENTS:
        assert fragment not in serialized


def test_current_mtda_writer_uses_aligned_rewrite_not_recommended_compatibility_branch() -> None:
    writer_source = inspect.getsource(mtda_writer.MTDAWriter.write)

    assert "_aligned_mtda_files(" in writer_source
    assert "_recommended_mtda_files(" not in writer_source
