from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from mtdp_enrichment.package import MTDPMigrator, MTDPPackageWriter, RunInput
from mtdp_enrichment.package.migrator import MigrationRegistry
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_migration_registry_loads_real_compression_plan():
    plan = MigrationRegistry().plan("mechanical.compression", "0.1.0", "0.2.0")

    assert plan is not None
    assert plan.status == "ambiguous_migration"
    assert {operation.operation_type for operation in plan.operations} >= {"map_enum_value", "require_user_value"}


def test_ambiguous_migration_requires_review_until_user_value_provided(tmp_path: Path):
    source = _legacy_package(tmp_path)
    target_schema = SchemaRegistry().get("mechanical.compression", "0.2.0")
    migrator = MTDPMigrator()

    result = migrator.migrate_package(source, tmp_path / "migrated.mtdp", target_schema)

    assert result.status == "ambiguous_migration"
    assert result.review_state is not None
    assert not result.rewritten


def test_user_resolved_migration_rewrites_schema_and_records_provenance(tmp_path: Path):
    source = _legacy_package(tmp_path)
    target = tmp_path / "migrated.mtdp"
    target_schema = SchemaRegistry().get("mechanical.compression", "0.2.0")
    result = MTDPMigrator().migrate_package(source, target, target_schema, user_values={"sample_type": "legacy"})

    assert result.status == "user_resolved_migration"
    assert result.rewritten
    assert MTDPPackageValidator().validate(target).ok
    with zipfile.ZipFile(target) as archive:
        manifest = json.loads(archive.read("metadata/manifest.json"))
        assert manifest["schema_version"] == "0.2.0"
        rows = list(csv.reader(io.StringIO(archive.read("dataset/normalized/run_001_normalized.csv").decode("utf-8"))))
        assert ["Validity", "accepted"] in [row[:2] for row in rows if row]
        provenance = json.loads(archive.read("metadata/provenance.json"))
        event = provenance["migration_events"][0]
        assert event["event"] == "schema_migrated"
        assert event["details"]["status"] == "user_resolved_migration"
        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert "metadata/schema.json" in checksums["files"]


def _legacy_package(tmp_path: Path) -> Path:
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression", "0.1.0")
    output = tmp_path / "legacy.mtdp"
    assert MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed, {"failure_mode": "Valid"})],
        schema,
        output,
        {},
    ).ok
    return output
