from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.supplemental import SupplementalFile


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_package_emits_taxonomy_events_for_units_and_supplemental_files(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    note = tmp_path / "operator_notes.txt"
    note.write_text("checked", encoding="utf-8")
    output = tmp_path / "events.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [
            RunInput(
                "run_001",
                parsed,
                {"width": EnrichedFieldValue(1.0, "cm", "user")},
            )
        ],
        schema,
        output,
        {"sample_type": "events"},
        supplemental_files=[SupplementalFile(note, scope="dataset", role="documents")],
    )

    assert validation.ok
    assert MTDPPackageValidator().validate(output).ok
    with zipfile.ZipFile(output) as archive:
        provenance = json.loads(archive.read("metadata/provenance.json"))
        dataset_events = provenance["dataset_events"]
        run_events = provenance["runs"]["run_001"]["processing_events"]
        assert any(event["event"] == "supplemental_file_added" for event in dataset_events)
        assert any(event["event"] == "unit_normalized" for event in run_events)
        for event in [*dataset_events, *run_events]:
            assert event["event"]
            assert event.get("timestamp") or event.get("parser")
