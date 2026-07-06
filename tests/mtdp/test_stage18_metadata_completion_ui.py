from __future__ import annotations

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.ui.metadata_section_panel import metadata_section_panel_model


def test_metadata_panel_completion_summary_and_missing_filters() -> None:
    schema = SchemaRegistry().get("mechanical.compression")

    model = metadata_section_panel_model(
        schema,
        scope="dataset",
        values={
            "sample_type": EnrichedFieldValue("SS85_100_60"),
            "loading_method": EnrichedFieldValue("method_1_shear_loading"),
        },
    )

    summary = model.completion_summary
    assert summary["field_count"] > 0
    assert summary["present_count"] == 2
    assert summary["required_missing_count"] > 0
    assert summary["status"] == "INCOMPLETE"
    assert all(row.report_importance == "required" for row in model.missing_fields("required"))
    assert any(row.report_importance == "recommended" for row in model.missing_fields("recommended"))


def test_metadata_section_badges_identify_complete_and_warning_sections() -> None:
    schema = SchemaRegistry().get("mechanical.compression")
    model = metadata_section_panel_model(
        schema,
        scope="dataset",
        values={
            "sample_type": EnrichedFieldValue("SS85_100_60"),
            "treatment": EnrichedFieldValue("aged"),
            "material_label": EnrichedFieldValue("CAG-CF-ER"),
        },
    )

    overview = next(section for section in model.sections if section.id == "overview")
    material = next(section for section in model.sections if section.id == "material_identification")

    assert overview.status == "complete"
    assert overview.completion_badge == "Complete"
    assert material.status == "recommended_missing"
    assert "recommended missing" in material.completion_badge
