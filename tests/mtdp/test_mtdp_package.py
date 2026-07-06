from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

from mtdp_enrichment.index import FolderIndex
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageReader, MTDPPackageWriter, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"
HIGH_PRECISION_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "datasets"
    / "Compression"
    / "CAG-CF-Modied-ULV20-E6.csv"
)


def test_registry_loads_yaml_schemas_and_keeps_versions_selectable():
    registry = SchemaRegistry()

    latest = registry.get("mechanical.compression")

    assert latest.schema_version == "0.3.0"
    assert latest.status == "active"
    assert registry.get("mechanical.compression", "0.2.0").status == "deprecated"
    assert registry.get("mechanical.compression", "0.1.0").status == "deprecated"
    assert registry.effective_status(registry.get("mechanical.compression", "0.2.0")) == "deprecated"
    assert [schema.schema_id for schema in registry.selectable()] == [
        "mechanical.compression",
        "mechanical.flexural",
        "mechanical.generic_stress_strain",
        "mechanical.tensile",
    ]
    assert [schema.schema_version for schema in registry.versions_for("mechanical.compression")] == [
        "0.3.0",
        "0.2.0",
        "0.1.0",
    ]
    assert registry.get("mechanical.compression", "0.1.0").run_fields


def test_registry_effectively_deprecates_stale_active_versions():
    registry = SchemaRegistry()
    latest = registry.get("mechanical.compression", "0.3.0")
    stale_active = replace(registry.get("mechanical.compression", "0.2.0"), status="active")
    synthetic = SchemaRegistry([latest, stale_active])

    assert synthetic.latest("mechanical.compression").schema_version == "0.3.0"
    assert synthetic.effective_status(stale_active) == "deprecated"
    assert [schema.schema_version for schema in synthetic.selectable()] == ["0.3.0"]


def test_writer_creates_valid_multirun_dataset_package(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output_path = tmp_path / "untreated_compression.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [
            RunInput(
                "run_001",
                parsed,
                {
                    "operator": "G. Damilano",
                    "instrument_model": "Instron 5969",
                    "load_cell": EnrichedFieldValue("50", "kN"),
                    "test_speed": EnrichedFieldValue("1.0", "mm/min"),
                    "test_date": "2026-05-06",
                },
            ),
            RunInput("run_002", parsed, {"operator": "G. Damilano"}),
        ],
        schema,
        output_path,
        {"sample_type": "untreated", "material_label": "CAG-CF-ER"},
        grouping_confirmation={"group_name": "untreated", "run_count": 2, "manual_corrections": 1},
    )

    assert validation.ok
    assert MTDPPackageValidator().validate(output_path).ok

    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert names == {
            "dataset/normalized/run_001_normalized.csv",
            "dataset/normalized/run_002_normalized.csv",
            "dataset/raw/run_001_raw.csv",
            "dataset/raw/run_002_raw.csv",
            "metadata/checksums.json",
            "metadata/dataset.json",
            "metadata/manifest.json",
            "metadata/provenance.json",
            "metadata/schema.json",
        }

        manifest = json.loads(archive.read("metadata/manifest.json"))
        assert manifest == {
            "package_format": "mtdp",
            "format_version": "0.2.0",
            "schema_id": "mechanical.compression",
            "schema_version": "0.3.0",
        }

        schema_json = json.loads(archive.read("metadata/schema.json"))
        assert schema_json["schema_version"] == "0.3.0"
        assert "run_fields" in schema_json
        assert "dataset_fields" in schema_json
        assert "fields" not in schema_json

        dataset = json.loads(archive.read("metadata/dataset.json"))
        assert dataset == {
            "material_label": "CAG-CF-ER",
            "run_order": ["run_001", "run_002"],
            "sample_type": "untreated",
            "sample_type_key": "untreated",
        }

        normalized_csv = archive.read("dataset/normalized/run_001_normalized.csv").decode("utf-8")
        rows = list(csv.reader(io.StringIO(normalized_csv)))
        blank_index = rows.index([])
        tokens = {row[0]: row[1:] for row in rows[:blank_index]}
        assert tokens["Width"] == ["9.8", "mm"]
        assert tokens["Thickness"] == ["2.3", "mm"]
        assert tokens["Failure mode"] == ["Valid"]
        assert "Operator" not in tokens
        assert "Load cell" not in tokens
        assert rows[blank_index + 1] == ["Load", "Extension", "Front Strain", "Rear Strain", "Time"]
        assert rows[blank_index + 2] == ["(N)", "(mm)", "(mm/mm)", "(mm/mm)", "(s)"]
        assert rows[blank_index + 4][0] == "100"

        provenance = json.loads(archive.read("metadata/provenance.json"))
        assert "dataset_events" in provenance
        assert any(event["event"] == "grouping_confirmed" for event in provenance["dataset_events"])
        run_001 = provenance["runs"]["run_001"]
        assert run_001["original_filename"] == "Specimen_RawData_1.csv"
        assert run_001["raw_package_path"] == "dataset/raw/run_001_raw.csv"
        assert run_001["normalized_package_path"] == "dataset/normalized/run_001_normalized.csv"
        assert run_001["acquisition_context"]["operator"] == "G. Damilano"
        assert run_001["acquisition_context"]["instrument_model"] == "Instron 5969"
        assert run_001["acquisition_context"]["load_cell"] == {"value": 50.0, "unit": "kN"}
        assert any(
            event["event"] == "unit_normalized"
            and event["field"] == "Load"
            and event["from_unit"] == "kN"
            and event["to_unit"] == "N"
            and event["factor"] == 1000
            for event in run_001["processing_events"]
        )

        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert checksums["algorithm"] == "sha256"
        assert checksums["checksum_member"] == "metadata/checksums.json"
        assert "metadata/dataset.json" in checksums["files"]
        assert "dataset/normalized/run_002_normalized.csv" in checksums["files"]


def test_writer_preserves_normalized_channel_precision(tmp_path: Path):
    parsed = ParserAdapter().parse(HIGH_PRECISION_FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output_path = tmp_path / "high_precision.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output_path,
        {"sample_type": "high precision"},
    )

    assert validation.ok
    normalized_csv = MTDPPackageReader().read_member(
        output_path,
        "dataset/normalized/run_001_normalized.csv",
    ).decode("utf-8")
    rows = list(csv.reader(io.StringIO(normalized_csv)))
    blank_index = rows.index([])
    assert rows[blank_index + 1] == ["Load", "Extension", "Front Strain", "Rear Strain", "Time"]
    row_29 = rows[blank_index + 3 + 29]
    assert row_29[0] == "19.92"
    assert row_29[2] == "-0.00010858492"
    assert row_29[3] == "0.00011622511"


def test_single_run_wrapper_still_creates_dataset_package(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output_path = tmp_path / "single_run.mtdp"

    validation = MTDPPackageWriter().create_package(
        parsed,
        schema,
        output_path,
        {"width": EnrichedFieldValue("1", "cm")},
    )

    assert validation.ok
    normalized_csv = MTDPPackageReader().read_member(
        output_path,
        "dataset/normalized/run_001_normalized.csv",
    ).decode("utf-8")
    rows = list(csv.reader(io.StringIO(normalized_csv)))
    tokens = {row[0]: row[1:] for row in rows[: rows.index([])]}
    assert tokens["Width"] == ["10", "mm"]
    dataset = json.loads(MTDPPackageReader().read_member(output_path, "metadata/dataset.json"))
    assert dataset["run_order"] == ["run_001"]


def test_folder_index_scans_multirun_packages(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output_path = tmp_path / "indexed.mtdp"
    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed), RunInput("run_002", parsed)],
        schema,
        output_path,
        {"sample_type": "indexed"},
    )
    assert validation.ok

    index = FolderIndex(tmp_path)
    index.open()
    packages = index.packages()
    assert packages[0]["path"] == "indexed.mtdp"
    assert packages[0]["status"] == "valid"
    assert packages[0]["run_count"] == 2
    assert packages[0]["sample_type"] == "indexed"
    assert packages[0]["sample_type_key"] == "indexed"
    assert packages[0]["schema_status"] == "active"
    assert index.path.name == ".mtdp_index.sqlite"


def test_validator_rejects_missing_raw_normalized_counterpart(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    valid_path = tmp_path / "valid.mtdp"
    broken_path = tmp_path / "broken.mtdp"
    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        valid_path,
        {"sample_type": "broken"},
    )
    assert validation.ok

    with zipfile.ZipFile(valid_path) as source, zipfile.ZipFile(broken_path, "w") as target:
        for name in source.namelist():
            if name == "dataset/raw/run_001_raw.csv":
                continue
            target.writestr(name, source.read(name))

    broken = MTDPPackageValidator().validate(broken_path)
    assert not broken.ok
    assert any(issue.code == "missing_raw_counterpart" for issue in broken.errors)
