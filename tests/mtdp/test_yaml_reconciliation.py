from __future__ import annotations

import shutil
from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter, build_document
from mtdp_enrichment.enrichment_import.value_normalizers import extract_unit_from_key, parse_date_candidate
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_date_reconciliation_parses_uk_dates_to_iso():
    assert parse_date_candidate("2014-07-16").iso_value == "2014-07-16"
    assert parse_date_candidate("16/07/2014").iso_value == "2014-07-16"
    assert parse_date_candidate("16-07-2014").iso_value == "2014-07-16"
    ambiguous = parse_date_candidate("07/06/2014")
    assert ambiguous.iso_value == "2014-06-07"
    assert ambiguous.requires_confirmation
    assert parse_date_candidate("not a date").iso_value is None


def test_unit_reconciliation_infers_units_from_key_suffixes():
    assert extract_unit_from_key("specimen.width_mm") == ("specimen.width", "mm", "unit_inferred_from_key")
    assert extract_unit_from_key("test_setup.load_cell_kN") == (
        "test_setup.load_cell",
        "kN",
        "unit_inferred_from_key",
    )
    assert extract_unit_from_key("test_setup.test_speed_mm_min") == (
        "test_setup.test_speed",
        "mm/min",
        "unit_inferred_from_key",
    )


def test_legacy_yaml_values_are_reconciled_to_clear_canonical_fields(tmp_path: Path):
    source = tmp_path / "legacy.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yaml").write_text(
        """
sample_id: CAG-CF-Modied-ULV20-E1
user: David Anthony
date: "16/07/2014"
location: DFF lab, Mechanical Engineering, Imperial College London
specimen:
  length_mm: 20
  width_mm: 9.91
  thickness_mm: 2.23
test_setup:
  machine: Instron 5969
  load_cell_kN: 50
  test_speed_mm_min: 2
valid: 1
""".strip(),
        encoding="utf-8",
    )
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")

    result = SidecarYamlImporter().import_for_run(source, parsed, schema)

    assert not result.requires_mapping
    assert result.imported_fields["test_date"].value == "2014-07-16"
    assert result.imported_fields["width"].value == 9.91
    assert result.imported_fields["width"].unit == "mm"
    assert result.imported_fields["thickness"].unit == "mm"
    assert result.imported_fields["load_cell"].unit == "kN"
    assert result.imported_fields["test_speed"].unit == "mm/min"
    assert result.imported_fields["validity"].value == "accepted"
    assert result.imported_fields["instrument_model"].value == "Instron 5969"
    assert result.imported_fields["instrument_location"].value.startswith("DFF lab")
    assert result.imported_fields["operator"].value == "David Anthony"


def test_reconciliation_dialog_shows_all_rows_and_live_preview(monkeypatch):
    import pytest

    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from mtdp_enrichment.ui.yaml_reconciliation_dialog import YamlReconciliationDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    document = build_document(
        Path("legacy.yaml"),
        {
            "date": "16/07/2014",
            "valid": 1,
            "location": "DFF lab",
            "test_setup": {"machine": "Instron 5969", "load_cell_kN": 50},
            "specimen": {"width_mm": 9.91},
        },
    )
    schema = SchemaRegistry().get("mechanical.compression")

    dialog = YamlReconciliationDialog(document, schema)
    dialog.recompute_preview()

    assert dialog.table.rowCount() == len(document.key_paths)
    preview_fields = {
        dialog.preview_table.item(row, 2).text()
        for row in range(dialog.preview_table.rowCount())
    }
    assert {"test_date", "validity", "instrument_location", "instrument_model", "load_cell", "width"}.issubset(
        preview_fields
    )
    preview_values = [dialog.preview_table.item(row, 3).text() for row in range(dialog.preview_table.rowCount())]
    assert "2014-07-16" in preview_values
    assert "accepted" in preview_values
    dialog.close()
    app.quit()
