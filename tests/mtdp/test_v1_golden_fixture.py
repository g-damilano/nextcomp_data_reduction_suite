from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageValidator, MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services import GroupExporter, GroupLoader, GroupReprocessor, SupplementalService, ValidationService


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "mtdp" / "golden_compression_group"
SOURCE_ROOT = FIXTURE_ROOT / "source"
EXPECTED_ROOT = FIXTURE_ROOT / "expected"


def test_v1_golden_package_fixture_is_valid_and_matches_contract():
    package_path = EXPECTED_ROOT / "golden_compression_group.mtdp"
    expected = json.loads((EXPECTED_ROOT / "expected_structure.json").read_text(encoding="utf-8"))

    validation = MTDPPackageValidator().validate(package_path)

    assert validation.ok
    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        dataset = json.loads(archive.read("dataset.json"))
        provenance = json.loads(archive.read("provenance.json"))
        checksums = json.loads(archive.read("checksums.json"))

    assert manifest == expected["manifest"]
    for key, value in expected["dataset"].items():
        assert dataset[key] == value
    assert set(expected["required_members"]).issubset(names)
    checksum_expected = set(expected["required_members"]) - {"checksums.json"}
    assert checksum_expected.issubset(checksums["files"])
    events = _event_names(provenance)
    for event_name in expected["expected_events"]:
        assert event_name in events


def test_v1_golden_lifecycle_create_open_reprocess_reexport(tmp_path: Path):
    schema = SchemaRegistry().get("mechanical.compression")
    created = tmp_path / "created_from_golden_sources.mtdp"
    revised = tmp_path / "created_from_golden_sources_revised.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        _run_inputs(["golden_run_001.csv", "golden_run_002.csv"], schema),
        schema,
        created,
        _dataset_fields(["golden_run_001.csv", "golden_run_002.csv"], schema),
        grouping_confirmation={"group_name": "Golden untreated compression", "run_count": 2, "manual_corrections": 0},
    )
    assert validation.ok
    assert MTDPPackageValidator().validate(created).ok

    group = GroupLoader().load_package(created)
    GroupReprocessor().remove_run(group, "run_002")
    GroupReprocessor().add_raw_file(group, SOURCE_ROOT / "golden_run_003_missed.csv")
    SupplementalService().add_dataset_file(group, SOURCE_ROOT / "operator_notes.txt", role="documents")

    group_validation = ValidationService().validate_group(group)
    export_validation = GroupExporter().export_group(group, revised)

    assert group_validation.ok
    assert export_validation.ok
    assert MTDPPackageValidator().validate(revised).ok
    with zipfile.ZipFile(revised) as archive:
        names = set(archive.namelist())
        dataset = json.loads(archive.read("metadata/dataset.json"))
        provenance = json.loads(archive.read("metadata/provenance.json"))
        checksums = json.loads(archive.read("metadata/checksums.json"))

    assert dataset["run_order"] == ["run_001", "run_002"]
    assert "dataset/raw/run_001_raw.csv" in names
    assert "dataset/raw/run_002_raw.csv" in names
    assert "dataset/normalized/run_002_normalized.csv" in names
    assert any(name.startswith("supplemental/documents/operator_notes") for name in names)
    assert set(names - {"metadata/checksums.json"}).issubset(checksums["files"])
    events = _event_names(provenance)
    assert "run_removed" in events
    assert "supplemental_file_added" in events
    assert "yaml_sidecar_imported" in events


def _run_inputs(source_names: list[str], schema) -> list[RunInput]:
    parser = ParserAdapter()
    importer = SidecarYamlImporter()
    runs: list[RunInput] = []
    dataset_ids = {field.field_id for field in schema.dataset_fields}
    for index, source_name in enumerate(source_names, start=1):
        source_path = SOURCE_ROOT / source_name
        parsed = parser.parse(source_path)
        imported = importer.import_for_run(source_path, parsed, schema)
        enrichment = {
            field_id: EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
            for field_id, candidate in imported.imported_fields.items()
            if field_id not in dataset_ids
        }
        images = (RunImageEvidence(SOURCE_ROOT / "run_001_front.jpg", "front"),) if index == 1 else ()
        runs.append(
            RunInput(
                f"run_{index:03d}",
                parsed,
                enrichment,
                supplemental_yaml=imported.source_path,
                import_conflicts=imported.conflicts,
                unknown_supplemental_keys=imported.unknown_keys,
                supplemental_import_mode="canonical",
                images=images,
            )
        )
    return runs


def _dataset_fields(source_names: list[str], schema) -> dict[str, EnrichedFieldValue]:
    parser = ParserAdapter()
    importer = SidecarYamlImporter()
    dataset_ids = {field.field_id for field in schema.dataset_fields}
    values: dict[str, EnrichedFieldValue] = {}
    for source_name in source_names:
        source_path = SOURCE_ROOT / source_name
        imported = importer.import_for_run(source_path, parser.parse(source_path), schema)
        for field_id, candidate in imported.imported_fields.items():
            if field_id in dataset_ids:
                values[field_id] = EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
    return values


def _event_names(provenance: dict[str, object]) -> set[str]:
    names: set[str] = set()
    for event in provenance.get("dataset_events", ()) or ():
        if isinstance(event, dict):
            names.add(str(event.get("event")))
    for event in provenance.get("migration_events", ()) or ():
        if isinstance(event, dict):
            names.add(str(event.get("event")))
    runs = provenance.get("runs", {})
    if isinstance(runs, dict):
        for run_payload in runs.values():
            if not isinstance(run_payload, dict):
                continue
            for event in run_payload.get("processing_events", ()) or ():
                if isinstance(event, dict):
                    names.add(str(event.get("event")))
    return names
