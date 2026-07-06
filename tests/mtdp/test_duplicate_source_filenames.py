from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from mtdp_enrichment.grouping import GroupingInput, SampleTypeGrouper, build_source_identities
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services.group_exporter import GroupExporter
from mtdp_enrichment.services.group_state import GroupState, RunState


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_repeated_anonymous_basenames_get_disambiguated_source_identities(tmp_path: Path) -> None:
    paths = _duplicate_fixture_tree(tmp_path)

    identities = build_source_identities(paths)

    assert set(identities) == {path.resolve() for path in paths}
    assert {identity.source_display_name for identity in identities.values()} == {
        "A/Specimen_RawData1.csv",
        "B/Specimen_RawData1.csv",
        "C/Specimen_RawData1.csv",
    }
    assert {identity.source_basename for identity in identities.values()} == {"Specimen_RawData1.csv"}
    assert {identity.parent_folder_name for identity in identities.values()} == {"A", "B", "C"}


def test_grouping_prefers_parent_folder_for_repeated_anonymous_filenames(tmp_path: Path) -> None:
    paths = _duplicate_fixture_tree(tmp_path)
    schema = _schema_with_grouping(
        {
            "enabled": True,
            "source_priority": ["filename_pattern", "folder_name"],
            "canonicalization": {
                "casefold": True,
                "replace_separators_with_space": True,
                "collapse_whitespace": True,
            },
        }
    )

    proposal = SampleTypeGrouper().propose(_inputs(paths), schema)

    assert len(proposal.bundles) == 3
    assert {bundle.display_name for bundle in proposal.bundles} == {"A", "B", "C"}
    assert [assignment.reason for bundle in proposal.bundles for assignment in bundle.assignments] == [
        "parent folder name",
        "parent folder name",
        "parent folder name",
    ]
    assert {assignment.source_path for bundle in proposal.bundles for assignment in bundle.assignments} == set(paths)


def test_bundle_tree_labels_repeated_basenames_with_context(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.bundle_builder import BundleBuilder
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    paths = _duplicate_fixture_tree(tmp_path)
    schema = _schema_with_grouping({"enabled": True, "source_priority": ["filename_pattern", "folder_name"]})
    inputs = _inputs(paths)
    proposal = SampleTypeGrouper().propose(inputs, schema)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    builder = BundleBuilder()
    builder.load_proposal(proposal, inputs)

    labels: list[str] = []
    tooltips: list[str] = []
    for index in range(builder.tree.topLevelItemCount()):
        parent = builder.tree.topLevelItem(index)
        for child_index in range(parent.childCount()):
            child = parent.child(child_index)
            labels.append(child.text(0))
            tooltips.append(child.toolTip(0))

    assert any("A/Specimen_RawData1.csv" in label for label in labels)
    assert any("B/Specimen_RawData1.csv" in label for label in labels)
    assert any("C/Specimen_RawData1.csv" in label for label in labels)
    assert all(str(tmp_path) in tooltip for tooltip in tooltips)

    builder.close()
    app.quit()


def test_group_export_keeps_repeated_basenames_as_distinct_runs(tmp_path: Path) -> None:
    paths = _duplicate_fixture_tree(tmp_path)
    parser = ParserAdapter()
    schema = SchemaRegistry().get("mechanical.compression")
    group = GroupState(
        group_key="duplicate_filenames",
        display_name="Duplicate Filenames",
        schema=schema,
        dataset_enrichment={"sample_type": EnrichedFieldValue("duplicate filenames")},
        runs=[
            RunState(f"run_{index:03d}", path, parser.parse(path))
            for index, path in enumerate(paths, start=1)
        ],
    )
    output = tmp_path / "duplicate_filenames.mtdp"

    validation = GroupExporter().export_group(group, output)

    assert validation.ok
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {"dataset/raw/run_001_raw.csv", "dataset/raw/run_002_raw.csv", "dataset/raw/run_003_raw.csv"} <= names
        assert {
            "dataset/normalized/run_001_normalized.csv",
            "dataset/normalized/run_002_normalized.csv",
            "dataset/normalized/run_003_normalized.csv",
        } <= names
        provenance = json.loads(archive.read("metadata/provenance.json"))

    relative_paths = {
        provenance["runs"][run_id]["source_relative_path"]
        for run_id in ("run_001", "run_002", "run_003")
    }
    assert relative_paths == {
        "A/Specimen_RawData1.csv",
        "B/Specimen_RawData1.csv",
        "C/Specimen_RawData1.csv",
    }
    assert {provenance["runs"][run_id]["original_filename"] for run_id in ("run_001", "run_002", "run_003")} == {
        "Specimen_RawData1.csv"
    }


def _duplicate_fixture_tree(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for folder_name in ("A", "B", "C"):
        folder = tmp_path / folder_name
        folder.mkdir()
        path = folder / "Specimen_RawData1.csv"
        shutil.copyfile(FIXTURE, path)
        paths.append(path)
    return paths


def _inputs(paths: list[Path]) -> list[GroupingInput]:
    parser = ParserAdapter()
    registry = SchemaRegistry()
    return [
        GroupingInput(path, parser.parse(path), registry.infer(parser.parse(path), path))
        for path in paths
    ]


def _schema_with_grouping(grouping: dict[str, object]) -> MTDPSchema:
    payload = SchemaRegistry().get("mechanical.compression").to_dict()
    payload["dataset_grouping"] = grouping
    return MTDPSchema.from_dict(payload)
