from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.image_gateway import ImageEvidenceImporter
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_image_importer_accepts_schema_formats_and_rejects_unknown(tmp_path: Path):
    schema = SchemaRegistry().get("mechanical.compression")
    importer = ImageEvidenceImporter()
    front = tmp_path / "run_front.jpg"
    front.write_bytes(b"jpeg evidence")
    bmp = tmp_path / "run_front.bmp"
    bmp.write_bytes(b"bmp evidence")

    evidence, validation = importer.make_evidence(front, schema)
    rejected, rejected_validation = importer.make_evidence(bmp, schema)

    assert validation.ok
    assert evidence is not None
    assert evidence.view == "front"
    assert rejected is None
    assert not rejected_validation.ok


def test_package_copies_sidecar_and_images_with_provenance_and_checksums(tmp_path: Path):
    source = tmp_path / "Specimen_RawData_1.csv"
    shutil.copyfile(FIXTURE, source)
    sidecar = source.with_suffix(".yaml")
    sidecar.write_text(
        """
width:
  value: 9.75
  unit: mm
operator: G. Damilano
""".strip(),
        encoding="utf-8",
    )
    image = tmp_path / "Specimen_RawData_1_front.jpg"
    image.write_bytes(b"jpeg evidence")
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")
    supplemental = SidecarYamlImporter().import_for_run(source, parsed, schema)
    evidence, image_validation = ImageEvidenceImporter().make_evidence(image, schema)
    assert image_validation.ok
    assert evidence is not None

    output_path = tmp_path / "evidence.mtdp"
    validation = MTDPPackageWriter().create_dataset_package(
        [
            RunInput(
                "run_001",
                parsed,
                {
                    field_id: EnrichedFieldValue(candidate.value, candidate.unit, "sidecar_yaml")
                    for field_id, candidate in supplemental.imported_fields.items()
                },
                supplemental_yaml=supplemental.source_path,
                images=(evidence,),
                import_conflicts=supplemental.conflicts,
                unknown_supplemental_keys=supplemental.unknown_keys,
            )
        ],
        schema,
        output_path,
        {"sample_type": "evidence"},
    )

    assert validation.ok
    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "supplemental/run_001.yaml" in names
        assert "images/run_001_front.jpg" in names
        provenance = json.loads(archive.read("metadata/provenance.json"))
        run = provenance["runs"]["run_001"]
        assert run["supplemental_inputs"][0]["package_path"] == "supplemental/run_001.yaml"
        assert run["image_evidence"][0]["package_path"] == "images/run_001_front.jpg"
        checksums = json.loads(archive.read("metadata/checksums.json"))
        assert "supplemental/run_001.yaml" in checksums["files"]
        assert "images/run_001_front.jpg" in checksums["files"]


def test_validator_rejects_missing_image_referenced_by_provenance(tmp_path: Path):
    source = tmp_path / "Specimen_RawData_1.csv"
    shutil.copyfile(FIXTURE, source)
    image = tmp_path / "Specimen_RawData_1_front.jpg"
    image.write_bytes(b"jpeg evidence")
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")
    evidence, image_validation = ImageEvidenceImporter().make_evidence(image, schema)
    assert image_validation.ok
    assert evidence is not None
    valid_path = tmp_path / "valid.mtdp"
    broken_path = tmp_path / "broken.mtdp"
    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed, images=(evidence,))],
        schema,
        valid_path,
        {"sample_type": "broken image"},
    )
    assert validation.ok

    with zipfile.ZipFile(valid_path) as source_zip, zipfile.ZipFile(broken_path, "w") as target:
        for name in source_zip.namelist():
            if name == "images/run_001_front.jpg":
                continue
            target.writestr(name, source_zip.read(name))

    broken = MTDPPackageValidator().validate(broken_path)
    assert not broken.ok
    assert any(issue.code == "missing_image" for issue in broken.errors)
