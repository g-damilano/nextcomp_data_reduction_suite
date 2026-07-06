from __future__ import annotations


def test_active_compression_schema_declares_unit_system_and_dimensions():
    from mtdp_enrichment.schemas import SchemaRegistry

    schema = SchemaRegistry().get("mechanical.compression")

    assert schema.unit_system == "mechanical_metric_mm_N"
    width = schema.field_by_id("width")
    load = schema.table_definition_for_family("load")
    assert width is not None and width.unit_dimension == "length"
    assert load is not None and load.unit_dimension == "force"
    assert "mechanical_metric_mm_N" in schema.unit_systems
