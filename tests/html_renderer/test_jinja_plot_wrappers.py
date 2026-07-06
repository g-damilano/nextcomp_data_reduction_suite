from __future__ import annotations

import json
from pathlib import Path

import pytest
from markupsafe import Markup

from archives.core.checksums import build_checksums
from archives.mtda.writer import (
    _compact_plot_package_files,
    _compact_plot_wrapper_html,
    _dataset_plot_studio_html,
    _legacy_compact_plot_wrapper_html,
    _legacy_dataset_plot_studio_html,
    _legacy_plot_wrapper_html,
    _plot_wrapper_html,
)
from html_renderer.context_models import CompactPlotWrapperContext, DatasetPlotStudioContext, PlotWrapperContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "html_renderer" / "templates"


def test_plot_wrapper_shells_are_byte_equivalent_to_legacy_renderers() -> None:
    spec = _inline_spec()

    assert _plot_wrapper_html(
        title="Dataset plot & review",
        spec_path="dataset_plot.vl.json",
        spec=spec,
        home_path="../../index.html",
    ) == _legacy_plot_wrapper_html(
        title="Dataset plot & review",
        spec_path="dataset_plot.vl.json",
        spec=spec,
        home_path="../../index.html",
    )
    assert _compact_plot_wrapper_html(
        title="run_001 stress-strain evidence plot",
        package_path="run_001_plot.plot_package.json",
        home_path="../../index.html",
    ) == _legacy_compact_plot_wrapper_html(
        title="run_001 stress-strain evidence plot",
        package_path="run_001_plot.plot_package.json",
        home_path="../../index.html",
    )
    assert _dataset_plot_studio_html(
        title="Dataset plot - aggregate of 2 runs",
        package_path="dataset_plot.plot_package.json",
        home_path="../../index.html",
    ) == _legacy_dataset_plot_studio_html(
        title="Dataset plot - aggregate of 2 runs",
        package_path="dataset_plot.plot_package.json",
        home_path="../../index.html",
    )


def test_plot_wrapper_shells_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _inline_spec()
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")

    assert _plot_wrapper_html(title="Plot", spec_path="plot.vl.json", spec=spec) == _legacy_plot_wrapper_html(
        title="Plot",
        spec_path="plot.vl.json",
        spec=spec,
    )
    assert _compact_plot_wrapper_html(title="Plot", package_path="plot.plot_package.json") == _legacy_compact_plot_wrapper_html(
        title="Plot",
        package_path="plot.plot_package.json",
    )
    assert _dataset_plot_studio_html(title="Plot", package_path="dataset_plot.plot_package.json") == _legacy_dataset_plot_studio_html(
        title="Plot",
        package_path="dataset_plot.plot_package.json",
    )


def test_plot_wrapper_recipe_projection_mappings_are_explicit() -> None:
    expectations = {
        RecipeResultKind.MTDA_PLOT_WRAPPER: (
            "PlotWrapperContext",
            "pages/plots/plot_wrapper.html.j2",
        ),
        RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER: (
            "CompactPlotWrapperContext",
            "pages/plots/compact_plot_wrapper.html.j2",
        ),
        RecipeResultKind.MTDA_DATASET_PLOT_STUDIO: (
            "DatasetPlotStudioContext",
            "pages/plots/dataset_plot_studio.html.j2",
        ),
    }

    for kind, (context_model, template_name) in expectations.items():
        projection = projection_for(kind)
        assert projection.context_model == context_model
        assert projection.template_name == template_name
        assert projection.projection_planes == (ProjectionPlane.MTDA_BUNDLE_VIEWER,)
        assert (TEMPLATES_DIR / template_name).is_file()


def test_plot_wrapper_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    plot_kwargs = {
        "projection_plane": ProjectionPlane.MTDA_BUNDLE_VIEWER,
        "recipe_result_kind": RecipeResultKind.MTDA_PLOT_WRAPPER,
        "title_html": Markup("Plot"),
        "spec_path_html": Markup("plot.vl.json"),
        "spec_json": Markup("{}"),
        "home_path_html": Markup("../../index.html"),
    }
    with pytest.raises(ValueError, match="mtda_bundle_viewer"):
        PlotWrapperContext(**{**plot_kwargs, "projection_plane": ProjectionPlane.TEST})
    with pytest.raises(ValueError, match="mtda_plot_wrapper"):
        PlotWrapperContext(**{**plot_kwargs, "recipe_result_kind": RecipeResultKind.MTDA_HANDOFF_PAGE})
    with pytest.raises(ValueError, match="title_html must be an HTML-safe Markup fragment"):
        PlotWrapperContext(**{**plot_kwargs, "title_html": "Plot"})

    compact_kwargs = {
        "projection_plane": ProjectionPlane.MTDA_BUNDLE_VIEWER,
        "recipe_result_kind": RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER,
        "title_html": Markup("Plot"),
        "package_path_html": Markup("plot.plot_package.json"),
        "home_path_html": Markup("../../index.html"),
    }
    with pytest.raises(ValueError, match="mtda_compact_plot_wrapper"):
        CompactPlotWrapperContext(**{**compact_kwargs, "recipe_result_kind": RecipeResultKind.MTDA_PLOT_WRAPPER})

    dataset_kwargs = {
        "projection_plane": ProjectionPlane.MTDA_BUNDLE_VIEWER,
        "recipe_result_kind": RecipeResultKind.MTDA_DATASET_PLOT_STUDIO,
        "title_html": Markup("Plot"),
        "title_json": Markup(json.dumps("Plot")),
        "package_json": Markup(json.dumps("dataset_plot.plot_package.json")),
        "home_path_html": Markup("../../index.html"),
    }
    with pytest.raises(ValueError, match="mtda_dataset_plot_studio"):
        DatasetPlotStudioContext(**{**dataset_kwargs, "recipe_result_kind": RecipeResultKind.MTDA_COMPACT_PLOT_WRAPPER})


def test_plot_wrapper_migration_preserves_runtime_payload_and_checksum_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    package_files = _compact_plot_package_files(
        plot_id="run_001_plot",
        plot_type="run_stress_strain_reduction_evidence",
        title="run_001 stress-strain evidence plot",
        spec=_inline_spec(),
        html_member="dataset/02_processed/run_001_plot.html",
        source_refs=["dataset/02_processed/run_001_stress_strain.csv"],
        plot_data_materialization="none",
    )

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_files = _plot_surface_files(package_files)
    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    legacy_files = _plot_surface_files(package_files)

    assert jinja_files == legacy_files
    assert b"const spec = " in jinja_files["dataset/05_plots/dataset_plot/dataset_plot.html"]
    assert b"const packagePath = " in jinja_files["dataset/02_processed/run_001_plot.html"]
    assert b"const packagePath = " in jinja_files["dataset/03_aggregate/dataset_plot.html"]
    assert json.loads(jinja_files["dataset/02_processed/run_001_plot.plot_package.json"]) == json.loads(
        legacy_files["dataset/02_processed/run_001_plot.plot_package.json"]
    )
    assert build_checksums(jinja_files, checksum_member="metadata/checksums.json") == build_checksums(
        legacy_files,
        checksum_member="metadata/checksums.json",
    )


def _plot_surface_files(package_files: dict[str, bytes]) -> dict[str, bytes]:
    return {
        **package_files,
        "dataset/05_plots/dataset_plot/dataset_plot.html": _plot_wrapper_html(
            title="Dataset plot",
            spec_path="dataset_plot.vl.json",
            spec=_inline_spec(),
            home_path="../../index.html",
        ).encode("utf-8"),
        "dataset/02_processed/run_001_plot.html": _plot_wrapper_html(
            title="run_001 stress-strain evidence plot",
            package_path="run_001_plot.plot_package.json",
            home_path="../../index.html",
        ).encode("utf-8"),
        "dataset/03_aggregate/dataset_plot.html": _dataset_plot_studio_html(
            title="Dataset plot - aggregate of 2 runs",
            package_path="dataset_plot.plot_package.json",
            home_path="../../index.html",
        ).encode("utf-8"),
    }


def _inline_spec() -> dict[str, object]:
    return {
        "data": {"values": [{"x": 0, "y": 0}, {"x": 1, "y": 2}]},
        "mark": "line",
        "encoding": {
            "x": {"field": "x", "type": "quantitative", "title": "x"},
            "y": {"field": "y", "type": "quantitative", "title": "y"},
        },
    }
