from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from html_renderer.adapters import report_shell_context
from html_renderer.context_models import NavigationLinkContext, ReportShellContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_report_shell


REMOVED_DATASET_PAGE_LINK = '<a href="../03_aggregate/' + "dataset_" + 'report.html">Dataset report</a>'


def test_report_shell_context_declares_recipe_kind_and_projection_plane() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
        )
    )

    context = report_shell_context(result, report_kind="test_report", report_href="test_report.html")

    assert context.projection_plane is ProjectionPlane.MTDA_BUNDLE_VIEWER
    assert context.recipe_result_kind is RecipeResultKind.REPORT_SHELL
    assert projection_for(context.recipe_result_kind).template_name == "pages/report_shell.html.j2"
    assert [link.label for link in context.navigation_links] == ["Audit report"]


def test_report_shell_template_preserves_current_runtime_wiring() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
        )
    )

    html = render_report_shell(
        report_shell_context(result, report_kind="test_report", report_href="test_report.html")
    )

    assert html.startswith("<!doctype html>\n<html")
    assert '<main class="mtda-report-shell" data-mtda-report-shell="test_report">' in html
    assert '<iframe class="mtda-report-frame" src="test_report.html" title="Test report"></iframe>' in html
    assert '<a href="../../index.html">&larr; Archive</a>' in html
    assert REMOVED_DATASET_PAGE_LINK not in html
    assert '<a href="audit_report_shell.html">Audit report</a>' in html
    assert "@media print" in html
    assert ".mtda-report-shell-banner{display:none!important}" in html


def test_report_shell_template_matches_raw_golden_html_for_first_slice() -> None:
    result = SimpleNamespace(
        source=SimpleNamespace(
            dataset={"dataset_id": "CAG-CF-Modied-ULV20"},
            path=Path("CAG-CF-Modied-ULV20.mtdp"),
        )
    )

    html = render_report_shell(
        report_shell_context(result, report_kind="test_report", report_href="test_report.html")
    )

    assert html == """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test report - CAG-CF-Modied-ULV20</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#fff;color:#1d2a36;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.mtda-report-shell{height:100%;display:grid;grid-template-rows:auto minmax(0,1fr)}
.mtda-report-shell-banner{box-sizing:border-box;min-height:44px;padding:9px 20px;display:flex;align-items:center;justify-content:space-between;gap:18px;background:#fff;border-bottom:1px solid #d8e1ea}
.mtda-report-shell-banner a{color:#126292;text-decoration:none;font-weight:700}
.mtda-report-shell-banner a:hover{text-decoration:underline}
.mtda-report-shell-left{display:flex;align-items:center;gap:13px;min-width:0}
.mtda-report-shell-divider{width:1px;height:26px;background:#d8e1ea;display:inline-block;flex:0 0 auto}
.mtda-report-shell-title{font-size:14px;font-weight:750;white-space:nowrap}
.mtda-report-shell-subtitle{font-size:13px;color:#748394;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mtda-report-shell-right{display:flex;align-items:center;gap:16px;font-size:12px;color:#748394;white-space:nowrap}
.mtda-report-shell-links{display:flex;align-items:center;gap:10px}
.mtda-report-shell-links a{font-size:12px;font-weight:650;color:#185f8f}
.mtda-report-frame{display:block;width:100%;height:100%;border:0;background:#fff}
@media(max-width:820px){
  .mtda-report-shell-banner{align-items:flex-start;flex-direction:column;padding:10px 14px}
  .mtda-report-shell-right{align-items:flex-start;flex-direction:column;gap:8px}
}
@media print{
  html,body{height:auto;overflow:visible}
  .mtda-report-shell{display:block;height:auto}
  .mtda-report-shell-banner{display:none!important}
  .mtda-report-frame{height:100vh}
}
</style>
</head>
<body>
<main class="mtda-report-shell" data-mtda-report-shell="test_report">
<header class="mtda-report-shell-banner">
<div class="mtda-report-shell-left">
<a href="../../index.html">&larr; Archive</a>
<span class="mtda-report-shell-divider" aria-hidden="true"></span>
<span class="mtda-report-shell-title">Test report</span>
<span class="mtda-report-shell-subtitle">&middot; CAG-CF-Modied-ULV20</span>
</div>
<div class="mtda-report-shell-right">
<span>formal record</span>
<nav class="mtda-report-shell-links" aria-label="Report navigation">
<a href="audit_report_shell.html">Audit report</a>
</nav>
</div>
</header>
<iframe class="mtda-report-frame" src="test_report.html" title="Test report"></iframe>
</main>
</body>
</html>"""


def test_report_shell_context_rejects_wrong_projection_plane() -> None:
    with pytest.raises(ValueError, match="MTDA bundle viewer"):
        ReportShellContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.REPORT_SHELL,
            report_kind="test_report",
            report_href="test_report.html",
            page_title="Test report - dataset",
            report_title="Test report",
            dataset_name="dataset",
            right_label="formal record",
            archive_href="../../index.html",
            navigation_links=(NavigationLinkContext(href="../../index.html", label="Archive"),),
        )


def test_report_shell_context_rejects_missing_required_value() -> None:
    with pytest.raises(ValueError, match="report_href"):
        ReportShellContext(
            projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
            recipe_result_kind=RecipeResultKind.REPORT_SHELL,
            report_kind="test_report",
            report_href="",
            page_title="Test report - dataset",
            report_title="Test report",
            dataset_name="dataset",
            right_label="formal record",
            archive_href="../../index.html",
            navigation_links=(NavigationLinkContext(href="../../index.html", label="Archive"),),
        )
