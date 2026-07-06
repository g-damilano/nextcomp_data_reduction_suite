from __future__ import annotations

import shutil
from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.grouping import GroupingInput, SampleTypeGrouper
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_same_stem_yaml_imports_aliases_and_prefers_yaml_value(tmp_path: Path):
    source = tmp_path / "run.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yaml").write_text(
        """
specimen_width:
  value: 9.75
  unit: mm
operator: G. Damilano
legacy_note: keep outside schema
""".strip(),
        encoding="utf-8",
    )
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")

    result = SidecarYamlImporter().import_for_run(source, parsed, schema)

    assert result.source_path == source.with_suffix(".yaml")
    assert result.imported_fields["width"].value == 9.75
    assert result.imported_fields["width"].unit == "mm"
    assert result.imported_fields["operator"].value == "G. Damilano"
    assert not result.conflicts
    assert result.unknown_keys == ("legacy_note",)


def test_same_stem_yml_is_detected_and_unitless_metrology_needs_confirmation(tmp_path: Path):
    source = tmp_path / "run.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yml").write_text("width: 9.75\n", encoding="utf-8")
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")

    result = SidecarYamlImporter().import_for_run(source, parsed, schema)

    assert result.source_path == source.with_suffix(".yml")
    assert result.imported_fields["width"].value == 9.75
    assert len(result.conflicts) == 1
    assert result.conflicts[0].field_id == "width"
    assert "without a unit" in result.conflicts[0].message


def test_sidecar_sample_type_can_drive_grouping(tmp_path: Path):
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yaml").write_text("sample_type: Untreated\n", encoding="utf-8")
    parser = ParserAdapter()
    parsed = parser.parse(source)
    registry = SchemaRegistry()
    schema = registry.get("mechanical.compression")
    supplemental = SidecarYamlImporter().import_for_run(source, parsed, schema)

    proposal = SampleTypeGrouper().propose(
        [GroupingInput(source, parsed, registry.infer(parsed, source), supplemental)],
        schema,
    )

    assert proposal.bundles[0].display_name == "Untreated"
    assert proposal.bundles[0].assignments[0].reason == "supplemental YAML field"
