from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
import yaml

from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.schemas.linter import lint_schema
from mtdp_enrichment.ui.metadata_section_panel import (
    FIELD_MARKER_LEGEND,
    importance_marker,
    metadata_section_panel_model,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "src" / "mtdp_enrichment" / "schema_library" / "mechanical" / "compression" / "0.2.0.yaml"
FIXTURE = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"


def test_metadata_sections_are_view_refs_not_duplicate_field_definitions() -> None:
    raw = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    canonical_ids = {field["field_id"] for field in raw["dataset_fields"] + raw["run_fields"]}

    for section in raw["metadata_sections"]:
        assert section["fields"], section["id"]
        for field in section["fields"]:
            assert set(field) == {"field_ref"}
            assert field["field_ref"] in canonical_ids

    legacy_groups = {"Dataset", "Run analysis inputs", "Run acquisition provenance", "Review / validity", "Run Notes"}
    assert not legacy_groups & set(raw["ui"]["groups"])


def test_schema_resolves_refs_without_duplicate_visible_fields() -> None:
    schema = SchemaRegistry().get("mechanical.compression")
    all_fields = schema.dataset_fields + schema.run_fields

    field_ids = [field.field_id for field in all_fields]
    assert len(field_ids) == len(set(field_ids))

    dataset_visible = [
        row.field_id
        for section in metadata_section_panel_model(schema, scope="dataset").sections
        for row in section.fields
    ]
    run_visible = [
        row.field_id
        for section in metadata_section_panel_model(schema, scope="run").sections
        for row in section.fields
    ]
    assert len(dataset_visible) == len(set(dataset_visible))
    assert len(run_visible) == len(set(run_visible))
    assert schema.field_by_id("sample_type").report_role == "sample_type"
    assert schema.field_by_id("operator").report_role == "operator"
    lint = lint_schema(schema)
    assert lint.ok
    assert not [
        warning
        for warning in lint.warnings
        if warning.code.startswith("metadata_section_")
    ]


def test_required_recommended_markers_and_legend_are_compact() -> None:
    schema = SchemaRegistry().get("mechanical.compression")
    model = metadata_section_panel_model(schema, scope="dataset")
    rows = {
        row.field_id: row
        for section in model.sections
        for row in section.fields
    }

    assert model.legend == FIELD_MARKER_LEGEND
    assert rows["sample_type"].marker == "*"
    assert rows["sample_type"].display_label == "Sample type *"
    assert rows["treatment"].marker == "**"
    assert rows["treatment"].display_label == "Treatment **"
    assert rows["manufacturer_code"].marker == ""
    assert importance_marker(schema.field_by_id("width")) == "*"


def test_schema_form_uses_marker_labels_and_bottom_legend(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from mtdp_enrichment.ui.schema_form import SchemaForm

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    schema = SchemaRegistry().get("mechanical.compression")
    form = SchemaForm()
    form.build(schema, scope="dataset")

    legend = form.findChild(QtWidgets.QLabel, "metadata_marker_legend")
    assert legend is not None
    assert legend.text() == FIELD_MARKER_LEGEND
    assert form._field_label(schema.field_by_id("sample_type")) == "Sample type *"
    assert form._field_label(schema.field_by_id("treatment")) == "Treatment **"
    assert form._field_label(schema.field_by_id("manufacturer_code")) == "Manufacturer code"

    form.close()
    app.quit()


def test_embedded_mtdp_schema_keeps_metadata_sections_as_refs(tmp_path: Path) -> None:
    parser = ParserAdapter()
    parsed = parser.parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output = tmp_path / "stage17_5_metadata_refs.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output,
        {
            "sample_type": "stage17_5",
            "loading_method": "method_1_shear_loading",
            "specimen_type": "type_a",
            "strain_measurement_method": "dual strain gauges",
        },
    )

    assert validation.ok, validation.messages()
    with zipfile.ZipFile(output) as archive:
        embedded_schema = json.loads(archive.read("metadata/schema.json"))

    for section in embedded_schema["metadata_sections"]:
        for field in section["fields"]:
            assert set(field) == {"field_ref"}
