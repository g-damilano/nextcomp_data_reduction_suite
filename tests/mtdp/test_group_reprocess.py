from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from mtdp_enrichment.package import MTDPPackageUpdater, MTDPPackageWriter, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services import GroupExporter, GroupLoader, GroupReprocessor, ValidationService


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_package_updater_inspects_valid_package_for_reprocess(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output = tmp_path / "group.mtdp"
    assert MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output,
        {"sample_type": "reprocess"},
    ).ok

    package, validation = MTDPPackageUpdater().inspect_for_update(output)

    assert validation.ok
    assert package.dataset["sample_type"] == "reprocess"


def test_reprocessed_package_records_removed_run_and_regenerates_checksums(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    original = tmp_path / "original_group.mtdp"
    revised = tmp_path / "original_group_revised.mtdp"
    writer = MTDPPackageWriter()
    assert writer.create_dataset_package(
        [RunInput("run_001", parsed), RunInput("run_002", parsed)],
        schema,
        original,
        {"sample_type": "reprocess"},
    ).ok

    package, validation = MTDPPackageUpdater().inspect_for_update(original)
    assert validation.ok
    assert package.dataset["run_order"] == ["run_001", "run_002"]

    assert writer.create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        revised,
        {"sample_type": "reprocess"},
        grouping_confirmation={
            "group_name": "reprocess",
            "run_count": 1,
            "manual_corrections": 1,
            "removed_runs": [{"run_id": "run_002", "original_filename": FIXTURE.name}],
        },
    ).ok
    assert MTDPPackageValidator().validate(revised).ok

    with zipfile.ZipFile(revised) as archive:
        names = set(archive.namelist())
        assert "dataset/raw/run_002_raw.csv" not in names
        assert "dataset/normalized/run_002_normalized.csv" not in names
        provenance = json.loads(archive.read("metadata/provenance.json"))
        assert any(event["event"] == "run_removed" for event in provenance["dataset_events"])
        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert "dataset/raw/run_001_raw.csv" in checksums["files"]
        assert "dataset/normalized/run_001_normalized.csv" in checksums["files"]


def test_group_services_open_modify_validate_and_export_without_qt(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    original = tmp_path / "service_group.mtdp"
    revised = tmp_path / "service_group_revised.mtdp"
    assert MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed), RunInput("run_002", parsed)],
        schema,
        original,
        {"sample_type": "service"},
    ).ok

    group = GroupLoader().load_package(original)
    removed = GroupReprocessor().remove_run(group, "run_002")
    validation = ValidationService().validate_group(group)
    export_result = GroupExporter().export_group(group, revised)

    assert removed.run_id == "run_002"
    assert validation.ok
    assert export_result.ok
    with zipfile.ZipFile(revised) as archive:
        dataset = json.loads(archive.read("metadata/dataset.json"))
        provenance = json.loads(archive.read("metadata/provenance.json"))
        assert dataset["run_order"] == ["run_001"]
        assert any(event["event"] == "run_removed" for event in provenance["dataset_events"])


def test_main_window_loads_existing_group_package(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output = tmp_path / "group.mtdp"
    assert MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output,
        {"sample_type": "loaded"},
    ).ok

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    window.load_existing_package(output)

    assert window.current_package_path == output
    assert len(window.bundle_builder.bundles) == 1
    assert window.bundle_builder.bundles[0].display_name == "loaded"
    assert len(window.bundle_builder.bundles[0].runs) == 1
    assert window._output_path_for_bundle(window.bundle_builder.bundles[0]).name == "group_revised.mtdp"

    window.close()
    app.quit()
