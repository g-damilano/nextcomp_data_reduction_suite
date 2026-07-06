from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from archives.mtda.writer import _aligned_report_shell_html, _legacy_aligned_report_shell_html


REMOVED_DATASET_PAGE_LINK = '<a href="../03_aggregate/' + "dataset_" + 'report.html">Dataset report</a>'


def test_aligned_report_shell_frames_clean_report_with_archive_banner() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
        )
    )

    shell = _aligned_report_shell_html(result, report_kind="test_report", report_href="test_report.html")

    assert 'data-mtda-report-shell="test_report"' in shell
    assert 'src="test_report.html"' in shell
    assert '<a href="../../index.html">&larr; Archive</a>' in shell
    assert REMOVED_DATASET_PAGE_LINK not in shell
    assert '<a href="audit_report_shell.html">Audit report</a>' in shell
    assert "CAG-CF-Modied-ULV20" in shell
    assert "@media print" in shell
    assert ".mtda-report-shell-banner{display:none!important}" in shell


def test_audit_report_shell_links_back_to_test_shell() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={},
            path=Path("sample.mtdp"),
        )
    )

    shell = _aligned_report_shell_html(result, report_kind="audit_report", report_href="audit_report.html")

    assert 'data-mtda-report-shell="audit_report"' in shell
    assert 'src="audit_report.html"' in shell
    assert '<a href="test_report_shell.html">Test report</a>' in shell


def test_jinja_report_shell_matches_legacy_renderer_bytes() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
        )
    )

    assert _aligned_report_shell_html(
        result,
        report_kind="test_report",
        report_href="test_report.html",
    ) == _legacy_aligned_report_shell_html(
        result,
        report_kind="test_report",
        report_href="test_report.html",
    )
