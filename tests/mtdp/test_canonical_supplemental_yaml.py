from __future__ import annotations

import shutil
from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_canonical_yaml_imports_dataset_run_acquisition_and_images(tmp_path: Path):
    source = tmp_path / "sample_001.csv"
    shutil.copyfile(FIXTURE, source)
    image = tmp_path / "sample_001_front.jpg"
    image.write_bytes(b"image evidence")
    source.with_suffix(".yaml").write_text(
        """
mtdp_supplemental_version: 0.1.0
scope: run
schema_hint:
  schema_id: mechanical.compression
  schema_version: 0.2.0
dataset:
  sample_type: CAG-CF-Modied-ULV20
  treatment: modified
  material_label: CAG-CF
run:
  specimen_name: CAG-CF-Modied-ULV20-E1
  metrology:
    width:
      value: 9.8
      unit: mm
      method: caliper
    thickness:
      value: 2.3
      unit: mm
  acquisition:
    operator: G. Damilano
    instrument: Instron 5969
    load_cell:
      value: 50
      unit: kN
    test_speed:
      value: 1.0
      unit: mm/min
    test_date: 2026-05-06
  review:
    validity: accepted
images:
  - path: sample_001_front.jpg
    view: front
    role: audit_evidence
    used_for_metrology: false
""".strip(),
        encoding="utf-8",
    )
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")

    result = SidecarYamlImporter().import_for_run(source, parsed, schema)

    assert result.document is not None
    assert result.document.is_canonical
    assert result.document.version == "0.1.0"
    assert not result.requires_mapping
    assert result.imported_fields["sample_type"].value == "CAG-CF-Modied-ULV20"
    assert result.imported_fields["width"].value == 9.8
    assert result.imported_fields["width"].unit == "mm"
    assert result.imported_fields["instrument_model"].value == "Instron 5969"
    assert str(result.imported_fields["test_date"].value) == "2026-05-06"
    assert result.image_references[0].path == image
    assert result.image_references[0].view == "front"


def test_package_without_supplemental_still_valid(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    output_path = tmp_path / "plain.mtdp"

    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed, images=(RunImageEvidence(tmp_path / "missing.jpg", "front"),))],
        schema,
        output_path,
        {"sample_type": "plain"},
    )

    assert not validation.ok

    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output_path,
        {"sample_type": "plain"},
    )
    assert validation.ok
