from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from mtdp_enrichment.enrichment_import import MappingRule, SidecarYamlImporter
from mtdp_enrichment.enrichment_import.mapping_profile import profile_for_mapping
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_odd_yaml_requires_mapping_and_profile_applies_to_same_signature(tmp_path: Path):
    first = _legacy_yaml_pair(tmp_path, "first", width=9.8, thickness=2.3)
    second = _legacy_yaml_pair(tmp_path, "second", width=9.7, thickness=2.2)
    parser = ParserAdapter()
    schema = SchemaRegistry().get("mechanical.compression")
    parsed_first = parser.parse(first)
    importer = SidecarYamlImporter()

    initial = importer.import_for_run(first, parsed_first, schema)
    assert initial.requires_mapping
    assert initial.document is not None

    profile = profile_for_mapping(
        profile_id="legacy_compression_yaml_v1",
        schema=schema,
        payload=initial.document.raw_payload,
        mappings=(
            MappingRule("dimension_a", "map", "width", "dimension_a", "mm"),
            MappingRule("dimension_b", "map", "thickness", "dimension_b", "mm"),
            MappingRule("LC", "map", "load_cell", "LC", "kN"),
            MappingRule("tester", "map", "operator", "tester"),
            MappingRule("legacy_note", "ignore"),
        ),
    )
    profile_path = profile.save(tmp_path / ".mtdp_mapping_profiles" / "legacy_compression_yaml_v1.yaml")
    importer.load_mapping_profiles(profile_path.parent)

    mapped_first = importer.import_for_run(first, parsed_first, schema)
    mapped_second = importer.import_for_run(second, parser.parse(second), schema)

    assert not mapped_first.requires_mapping
    assert mapped_first.mapping_profile_id == "legacy_compression_yaml_v1"
    assert mapped_first.mapping_profile_path == profile_path
    assert mapped_first.imported_fields["width"].value == 9.8
    assert mapped_first.imported_fields["load_cell"].value == "50"
    assert mapped_second.mapping_profile_id == "legacy_compression_yaml_v1"
    assert mapped_second.imported_fields["thickness"].value == 2.2


def test_mapping_profile_is_preserved_in_package_and_validated(tmp_path: Path):
    source = _legacy_yaml_pair(tmp_path, "packaged", width=9.8, thickness=2.3)
    parser = ParserAdapter()
    parsed = parser.parse(source)
    schema = SchemaRegistry().get("mechanical.compression")
    initial = SidecarYamlImporter().import_for_run(source, parsed, schema)
    assert initial.document is not None
    profile = profile_for_mapping(
        profile_id="legacy_compression_yaml_v1",
        schema=schema,
        payload=initial.document.raw_payload,
        mappings=(
            MappingRule("dimension_a", "map", "width", "dimension_a", "mm"),
            MappingRule("dimension_b", "map", "thickness", "dimension_b", "mm"),
            MappingRule("LC", "map", "load_cell", "LC", "kN"),
            MappingRule("tester", "map", "operator", "tester"),
            MappingRule("legacy_note", "ignore"),
        ),
    )
    profile_path = profile.save(tmp_path / ".mtdp_mapping_profiles" / "legacy_compression_yaml_v1.yaml")
    importer = SidecarYamlImporter([type(profile).load(profile_path)])
    result = importer.import_for_run(source, parsed, schema)
    output_path = tmp_path / "mapped.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [
            RunInput(
                "run_001",
                parsed,
                {
                    field_id: EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
                    for field_id, candidate in result.imported_fields.items()
                },
                supplemental_yaml=result.source_path,
                import_conflicts=result.conflicts,
                unknown_supplemental_keys=result.unknown_keys,
                supplemental_import_mode="mapping_profile",
                mapping_profile_id=result.mapping_profile_id,
                mapping_profile_path=result.mapping_profile_path,
            )
        ],
        schema,
        output_path,
        {"sample_type": "mapped"},
    )

    assert validation.ok
    assert MTDPPackageValidator().validate(output_path).ok
    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "supplemental/run_001.yaml" in names
        assert "supplemental/mapping_profiles/legacy_compression_yaml_v1.yaml" in names
        provenance = json.loads(archive.read("metadata/provenance.json"))
        run = provenance["runs"]["run_001"]
        assert run["supplemental_inputs"][0]["import_mode"] == "mapping_profile"
        assert run["supplemental_inputs"][0]["mapping_profile_id"] == "legacy_compression_yaml_v1"
        assert any(
            event["event"] == "yaml_mapping_profile_applied"
            for event in provenance["dataset_events"]
        )
        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert "supplemental/mapping_profiles/legacy_compression_yaml_v1.yaml" in checksums["files"]


def _legacy_yaml_pair(tmp_path: Path, stem: str, *, width: float, thickness: float) -> Path:
    source = tmp_path / f"{stem}.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yaml").write_text(
        f"""
dimension_a: {width}
dimension_b: {thickness}
LC: 50kN
tester: GD
legacy_note: old workflow
""".strip(),
        encoding="utf-8",
    )
    return source
