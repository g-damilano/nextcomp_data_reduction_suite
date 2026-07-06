from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.mtdp import MTDPPackageReader as MethodMTDPReader
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from mtdp_enrichment.grouping import GroupingInput, SampleTypeGrouper, build_source_identities
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services.group_exporter import GroupExporter
from mtdp_enrichment.services.group_state import GroupState, RunState
from ui.method_run_wizard.view_models.package_preview import package_preview_view_model


FIXTURE = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture()
def duplicate_package(tmp_path: Path) -> Path:
    paths = _duplicate_fixture_tree(tmp_path)
    parser = ParserAdapter()
    schema = SchemaRegistry().get("mechanical.compression")
    group = GroupState(
        group_key="stage16_duplicate_sources",
        display_name="Stage 16 Duplicate Sources",
        schema=schema,
        dataset_enrichment={"sample_type": EnrichedFieldValue("stage16 duplicate sources")},
        runs=[
            RunState(f"run_{index:03d}", path, parser.parse(path))
            for index, path in enumerate(paths, start=1)
        ],
    )
    output = tmp_path / "stage16_duplicate_sources.mtdp"
    validation = GroupExporter().export_group(group, output)
    assert validation.ok
    return output


def test_repeated_anonymous_filenames_have_distinct_source_identities(tmp_path: Path) -> None:
    paths = _duplicate_fixture_tree(tmp_path)
    identities = build_source_identities(paths)
    inputs = _grouping_inputs(paths)
    proposal = SampleTypeGrouper().propose(inputs, SchemaRegistry().get("mechanical.compression"))

    assert set(identities) == {path.resolve() for path in paths}
    assert {identity.source_display_name for identity in identities.values()} == {
        "A/Specimen_RawData1.csv",
        "B/Specimen_RawData1.csv",
        "C/Specimen_RawData1.csv",
    }
    assert len({assignment.source_path for bundle in proposal.bundles for assignment in bundle.assignments}) == 3


def test_mtdp_export_reload_preserves_source_identity_and_schema(duplicate_package: Path) -> None:
    source = MethodMTDPReader().read(duplicate_package)
    with zipfile.ZipFile(duplicate_package) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        manifest = json.loads(archive.read("metadata/manifest.json"))
        schema = json.loads(archive.read("metadata/schema.json"))
        dataset = json.loads(archive.read("metadata/dataset.json"))
        provenance = json.loads(archive.read("metadata/provenance.json"))
        checksums = json.loads(archive.read("metadata/checksums.json"))

    assert manifest["schema_id"] == "mechanical.compression"
    assert manifest["schema_version"] == "0.3.0"
    assert schema["schema_id"] == "mechanical.compression"
    assert schema["schema_version"] == "0.3.0"
    assert dataset["sample_type"] == "stage16 duplicate sources"
    assert dataset["run_order"] == ["run_001", "run_002", "run_003"]
    assert {"dataset/raw/run_001_raw.csv", "dataset/raw/run_002_raw.csv", "dataset/raw/run_003_raw.csv"} <= names
    assert {
        "dataset/normalized/run_001_normalized.csv",
        "dataset/normalized/run_002_normalized.csv",
        "dataset/normalized/run_003_normalized.csv",
    } <= names
    assert _checksums_match_archive(duplicate_package, checksums)

    assert source.run_ids == ("run_001", "run_002", "run_003")
    for run_id, folder in zip(source.run_ids, ("A", "B", "C")):
        run = next(item for item in source.runs if item.run_id == run_id)
        record = provenance["runs"][run_id]
        assert run.original_filename == "Specimen_RawData1.csv"
        assert run.raw_package_path == f"dataset/raw/{run_id}_raw.csv"
        assert run.normalized_package_path == f"dataset/normalized/{run_id}_normalized.csv"
        assert record["source_relative_path"] == f"{folder}/Specimen_RawData1.csv"
        assert record["source_display_name"] == f"{folder}/Specimen_RawData1.csv"
        assert record["parent_folder_name"] == folder
        assert record["source_basename"] == "Specimen_RawData1.csv"


def test_package_preview_is_consistent_with_archive_contents(duplicate_package: Path) -> None:
    with zipfile.ZipFile(duplicate_package) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        provenance = json.loads(archive.read("metadata/provenance.json"))
    model = package_preview_view_model(MethodRunService().load_package(duplicate_package))

    assert model["schema_id"] == "mechanical.compression"
    assert model["schema_version"] == "0.3.0"
    assert model["run_count"] == 3
    assert model["source_file_count"] == len(provenance["runs"])
    assert model["normalized_file_count"] == len([name for name in names if name.startswith("dataset/normalized/")])
    assert model["raw_file_count"] == len([name for name in names if name.startswith("dataset/raw/")])
    assert model["source_identity_summary"]["repeated_basenames"] == ["Specimen_RawData1.csv"]
    assert model["source_identity_summary"]["status"] == "warning"
    assert {row["source_relative_path"] for row in model["source_files"]} == {
        "A/Specimen_RawData1.csv",
        "B/Specimen_RawData1.csv",
        "C/Specimen_RawData1.csv",
    }
    assert model["provenance"]["status"] == "present"
    assert model["provenance"]["checksum_status"] == "present"


def test_duplicate_filename_mtdp_to_mtda_handoff_preserves_source_reference(duplicate_package: Path, tmp_path: Path) -> None:
    source_hash_before = _sha256(duplicate_package)
    output = tmp_path / "stage16_duplicate_sources.mtda"

    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=duplicate_package,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
        )
    )

    assert result.status == "completed"
    assert _sha256(duplicate_package) == source_hash_before
    with zipfile.ZipFile(output) as archive:
        mtda_provenance = json.loads(archive.read("software/provenance.json"))
        source_reference = mtda_provenance["source_reference"]
        specimen_rows = list(
            csv.DictReader(io.StringIO(archive.read("dataset/04_aggregate/results_table.csv").decode("utf-8")))
        )
        checksums = json.loads(archive.read("software/checksums.json"))
    assert source_reference["source_package"]["checksum"] == source_hash_before
    assert mtda_provenance["source_reference"]["source_package"]["checksum"] == source_hash_before
    assert [row["run_id"] for row in specimen_rows] == ["run_001", "run_002", "run_003"]
    assert _checksums_match_archive(output, checksums)


def _duplicate_fixture_tree(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for folder_name in ("A", "B", "C"):
        folder = tmp_path / folder_name
        folder.mkdir()
        path = folder / "Specimen_RawData1.csv"
        shutil.copyfile(FIXTURE, path)
        paths.append(path)
    return paths


def _grouping_inputs(paths: list[Path]) -> list[GroupingInput]:
    parser = ParserAdapter()
    registry = SchemaRegistry()
    return [
        GroupingInput(path, parser.parse(path), registry.infer(parser.parse(path), path))
        for path in paths
    ]


def _checksums_match_archive(path: Path, checksums: dict[str, Any]) -> bool:
    with zipfile.ZipFile(path) as archive:
        checksum_member = str(checksums.get("checksum_member") or "checksums.json")
        for member, expected in checksums["files"].items():
            if member == checksum_member:
                continue
            actual = hashlib.sha256(archive.read(member)).hexdigest()
            if actual != expected:
                return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
