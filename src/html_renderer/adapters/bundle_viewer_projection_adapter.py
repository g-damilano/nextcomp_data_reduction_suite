from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from markupsafe import Markup

from html_renderer.context_models import (
    CompactPlotWrapperContext,
    DatasetPlotStudioContext,
    NavigationLinkContext,
    PlotWrapperContext,
    ReportShellContext,
    SimpleReportContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind


REPORT_SHELL_SPECS: dict[str, dict[str, str]] = {
    "test_report": {
        "title": "Test report",
        "right": "formal record",
        "peer_href": "audit_report_shell.html",
        "peer_label": "Audit report",
    },
    "audit_report": {
        "title": "Audit report",
        "right": "",
        "peer_href": "test_report_shell.html",
        "peer_label": "Test report",
    },
}


def report_shell_context(result: Any, *, report_kind: str, report_href: str) -> ReportShellContext:
    source = getattr(result, "source", None)
    dataset = getattr(source, "dataset", {}) if source is not None else {}
    source_path = getattr(source, "path", Path("dataset")) if source is not None else Path("dataset")
    dataset_name = str(dataset.get("dataset_id") or Path(source_path).stem)
    spec = REPORT_SHELL_SPECS.get(report_kind, REPORT_SHELL_SPECS["test_report"])
    return ReportShellContext(
        projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
        recipe_result_kind=RecipeResultKind.REPORT_SHELL,
        report_kind=report_kind,
        report_href=report_href,
        page_title=f'{spec["title"]} - {dataset_name}',
        report_title=spec["title"],
        dataset_name=dataset_name,
        right_label=spec["right"],
        archive_href="../../index.html",
        navigation_links=(
            NavigationLinkContext(href=spec["peer_href"], label=spec["peer_label"]),
        ),
    )


def plot_wrapper_context(
    *,
    title: str,
    spec_path: str,
    spec_json: str,
    home_path: str,
) -> PlotWrapperContext:
    return PlotWrapperContext(
        projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
        recipe_result_kind=RecipeResultKind.MTDA_PLOT_WRAPPER,
        title_html=Markup(html.escape(title)),
        spec_path_html=Markup(html.escape(spec_path)),
        spec_json=Markup(spec_json),
        home_path_html=Markup(html.escape(home_path)),
    )


def compact_plot_wrapper_context(
    *,
    title: str,
    package_path: str,
    home_path: str,
) -> CompactPlotWrapperContext:
    return CompactPlotWrapperContext(
        projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
        recipe_result_kind=RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER,
        title_html=Markup(html.escape(title)),
        package_path_html=Markup(html.escape(package_path)),
        home_path_html=Markup(html.escape(home_path)),
    )


def dataset_plot_studio_context(
    *,
    title: str,
    package_path: str,
    home_path: str,
) -> DatasetPlotStudioContext:
    return DatasetPlotStudioContext(
        projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
        recipe_result_kind=RecipeResultKind.MTDA_DATASET_PLOT_STUDIO,
        title_html=Markup(html.escape(title)),
        title_json=Markup(json.dumps(title)),
        package_json=Markup(json.dumps(package_path)),
        home_path_html=Markup(html.escape(home_path)),
    )


def simple_report_context(
    *,
    projection_plane: ProjectionPlane,
    recipe_result_kind: RecipeResultKind,
    page_title: str,
    nav_html: str,
    heading: str,
    body_html: str,
    table_body_html: str | None = None,
) -> SimpleReportContext:
    return SimpleReportContext(
        projection_plane=projection_plane,
        recipe_result_kind=recipe_result_kind,
        page_title=page_title,
        nav_html=Markup(nav_html),
        heading=heading,
        body_html=Markup(body_html),
        table_body_html=Markup(table_body_html) if table_body_html is not None else None,
    )
