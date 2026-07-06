from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mtdp_enrichment.package import MTDPPackageValidator, MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.supplemental import SupplementalFile


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_general_supplemental_files_are_packaged_checksummed_and_recorded(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    dataset_note = tmp_path / "operator_notes.txt"
    run_note = tmp_path / "manual_measurement.txt"
    dataset_note.write_text("Dataset note", encoding="utf-8")
    run_note.write_text("Run note", encoding="utf-8")

    output = tmp_path / "supplemental.mtdp"
    validation = MTDPPackageWriter().create_dataset_package(
        [
            RunInput(
                "run_001",
                parsed,
                supplemental_files=(
                    SupplementalFile(run_note, scope="run", role="run_evidence", run_id="run_001"),
                ),
            )
        ],
        schema,
        output,
        {"sample_type": "supplemental"},
        supplemental_files=(SupplementalFile(dataset_note, scope="dataset", role="documents"),),
    )

    assert validation.ok
    assert MTDPPackageValidator().validate(output).ok
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        dataset_member = "supplemental/documents/operator_notes.txt"
        run_member = "supplemental/runs/run_001/manual_measurement.txt"
        assert dataset_member in names
        assert run_member in names
        provenance = json.loads(archive.read("metadata/provenance.json"))
        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert provenance["supplemental_files"][0]["package_path"] == dataset_member
        assert provenance["runs"]["run_001"]["supplemental_inputs"][0]["package_path"] == run_member
        assert dataset_member in checksums["files"]
        assert run_member in checksums["files"]
