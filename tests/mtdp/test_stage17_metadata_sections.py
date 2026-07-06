from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services.group_loader import GroupLoader
from mtdp_enrichment.ui.metadata_section_panel import metadata_section_panel_model


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_compression_schema_parses_metadata_sections() -> None:
    schema = SchemaRegistry().get("mechanical.compression")

    dataset_sections = schema.metadata_sections_for_scope("dataset")
    run_sections = schema.metadata_sections_for_scope("run")

    assert {section.id for section in dataset_sections} >= {
        "test_identification",
        "material_identification",
        "measurement_method",
    }
    assert {section.id for section in run_sections} >= {
        "specimen_geometry",
        "user_validity_failure_observation",
    }
    assert schema.field_by_id("loading_method").report_role == "loading_method"
    assert schema.field_by_id("strain_measurement_method").report_importance == "required"
    assert schema.field_by_id("operator").report_role == "operator"


def test_metadata_section_view_model_tracks_report_completeness_markers() -> None:
    schema = SchemaRegistry().get("mechanical.compression")

    model = metadata_section_panel_model(
        schema,
        scope="dataset",
        values={
            "sample_type": EnrichedFieldValue("SS85_100_60"),
            "loading_method": EnrichedFieldValue("end-loaded compression"),
        },
    )
    test_identification = next(section for section in model.sections if section.id == "test_identification")
    loading_method = next(row for row in test_identification.fields if row.field_id == "loading_method")
    specimen_type = next(row for row in test_identification.fields if row.field_id == "specimen_type")

    assert loading_method.status == "present"
    assert specimen_type.status == "required_missing"
    assert model.required_missing_count > 0


def test_mtdp_stores_and_reloads_expanded_metadata(tmp_path: Path) -> None:
    parser = ParserAdapter()
    parsed = parser.parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output = tmp_path / "stage17_metadata.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed, {"run_notes": "Gauge leads checked."})],
        schema,
        output,
        {
            "sample_type": "stage17",
            "material_label": "CAG-CF-ER",
            "test_id": "T-17",
            "loading_method": "method_1_shear_loading",
            "specimen_type": "type_a",
            "strain_measurement_method": "dual strain gauges",
            "report_operator": "G. Damilano",
        },
    )

    assert validation.ok, validation.messages()
    with zipfile.ZipFile(output) as archive:
        dataset = json.loads(archive.read("metadata/dataset.json"))
        embedded_schema = json.loads(archive.read("metadata/schema.json"))
        provenance = json.loads(archive.read("metadata/provenance.json"))

    assert dataset["report"]["test_identification"]["loading_method"] == "method_1_shear_loading"
    assert dataset["report"]["measurement"]["strain_measurement_method"] == "dual strain gauges"
    assert embedded_schema["metadata_sections"]
    assert provenance["runs"]["run_001"]["report_notes"]["run_notes"] == "Gauge leads checked."

    loaded = GroupLoader(registry=SchemaRegistry(), parser=parser).load_package(output)
    assert loaded.dataset_enrichment["loading_method"].value == "method_1_shear_loading"
    assert loaded.runs[0].enrichment["run_notes"].value == "Gauge leads checked."
