from __future__ import annotations

from pathlib import Path

import pytest

from html_renderer.recipe_projection import RECIPE_PROJECTIONS, RecipeResultKind, projection_for


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "html_renderer" / "templates"


def test_all_registered_template_paths_exist() -> None:
    missing = [
        projection.template_name
        for projection in RECIPE_PROJECTIONS.values()
        if not (TEMPLATES_DIR / projection.template_name).is_file()
    ]

    assert missing == []


def test_active_recipe_projections_do_not_use_partials_paths() -> None:
    stale = [
        projection.template_name
        for projection in RECIPE_PROJECTIONS.values()
        if projection.template_name.startswith("partials/")
    ]

    assert stale == []


def test_formal_and_audit_reports_share_specialisable_page_layout() -> None:
    formal_projection = projection_for(RecipeResultKind.FORMAL_METHOD_REPORT)
    audit_projection = projection_for(RecipeResultKind.AUDIT_EVIDENCE_REPORT)

    assert formal_projection.template_name == "layouts/report_page.html.j2"
    assert audit_projection.template_name == "layouts/report_page.html.j2"


def test_optional_table_producers_share_table_component() -> None:
    optional_table_kinds = (
        RecipeResultKind.FORMAL_REPORT_EVIDENCE_TABLE,
        RecipeResultKind.FORMAL_REPORT_TABLE_SECTION,
        RecipeResultKind.FORMAL_REPORT_MISSING_DATA,
        RecipeResultKind.FORMAL_REPORT_DATA_USE_DEVIATIONS,
        RecipeResultKind.AUDIT_TABLE,
        RecipeResultKind.AUDIT_BLOCK_TABLE,
    )

    assert {
        projection_for(result_kind).template_name for result_kind in optional_table_kinds
    } == {"components/tables/optional_report_table.html.j2"}


def test_titled_fragments_and_panels_share_specialisable_components() -> None:
    panel_kinds = (
        RecipeResultKind.AUDIT_BLOCK_SUMMARY_PANEL,
        RecipeResultKind.AUDIT_BLOCK_ANALYSIS_COMPARISON,
    )

    assert projection_for(RecipeResultKind.AUDIT_BLOCK_TITLED_FRAGMENT).template_name == (
        "components/typography/heading_fragment.html.j2"
    )
    assert {projection_for(result_kind).template_name for result_kind in panel_kinds} == {
        "components/panels/titled_panel.html.j2"
    }


def test_raw_evidence_note_producers_share_note_component() -> None:
    note_kinds = (
        RecipeResultKind.REPORT_RAW_EVIDENCE_NOTE,
        RecipeResultKind.FORMAL_REPORT_RAW_EVIDENCE_NOTE,
        RecipeResultKind.AUDIT_RAW_EVIDENCE_NOTE,
    )

    assert {projection_for(result_kind).template_name for result_kind in note_kinds} == {
        "components/notes/raw_evidence_note.html.j2"
    }


def test_report_body_fragment_is_compatibility_adapter_not_registered_template() -> None:
    with pytest.raises(ValueError, match="No HTML projection registered"):
        projection_for(RecipeResultKind.REPORT_BODY_FRAGMENT)
