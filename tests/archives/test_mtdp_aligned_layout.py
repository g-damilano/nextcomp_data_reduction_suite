from __future__ import annotations

import zipfile
from pathlib import Path

from archives.core.json_io import json_bytes
from archives.mtdp.reader import MTDPPackageReader


ROOT = Path(__file__).resolve().parents[2]
LEGACY_FIXTURE = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"


def test_legacy_mtdp_fixture_remains_readable() -> None:
    package = MTDPPackageReader().read(LEGACY_FIXTURE)

    assert package.path == LEGACY_FIXTURE
    assert package.manifest
    assert package.schema
    assert package.dataset
    assert package.provenance
    assert package.runs
    assert package.runs[0].normalized_package_path.startswith("normalized/")
    assert package.runs[0].raw_package_path is None or package.runs[0].raw_package_path.startswith("raw/")


def test_aligned_mtdp_synthetic_archive_is_readable(tmp_path: Path) -> None:
    package_path = tmp_path / "aligned.mtdp"
    normalized = "\n".join(
        [
            "Width,10,mm",
            "Failure mode,Valid",
            "",
            "Load,Extension",
            "(N),(mm)",
            "1,0.1",
            "2,0.2",
            "",
        ]
    )
    files = {
        "metadata/manifest.json": json_bytes(
            {
                "package_format": "mtdp",
                "format_version": "0.3.0",
                "schema_id": "mechanical.compression",
                "schema_version": "0.3.0",
            }
        ),
        "metadata/schema.json": json_bytes({"schema_id": "mechanical.compression", "schema_version": "0.3.0"}),
        "metadata/dataset.json": json_bytes({"sample_type": "synthetic", "run_order": ["run_001"]}),
        "metadata/provenance.json": json_bytes(
            {
                "runs": {
                    "run_001": {
                        "original_filename": "run_001.csv",
                        "raw_package_path": "dataset/raw/run_001_raw.csv",
                        "normalized_package_path": "dataset/normalized/run_001_normalized.csv",
                    }
                }
            }
        ),
        "metadata/checksums.json": json_bytes({"algorithm": "sha256", "files": {}}),
        "dataset/raw/run_001_raw.csv": b"raw",
        "dataset/normalized/run_001_normalized.csv": normalized.encode("utf-8"),
    }
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, content in sorted(files.items()):
            archive.writestr(member, content)

    package = MTDPPackageReader().read(package_path)

    assert package.manifest["package_format"] == "mtdp"
    assert package.dataset["run_order"] == ["run_001"]
    assert package.checksums["algorithm"] == "sha256"
    assert package.run_ids == ("run_001",)
    run = package.runs[0]
    assert run.raw_package_path == "dataset/raw/run_001_raw.csv"
    assert run.normalized_package_path == "dataset/normalized/run_001_normalized.csv"
    assert run.original_filename == "run_001.csv"
    assert run.token("Width").value == "10"
    assert run.token("Width").unit == "mm"
    assert run.channel("Load").unit == "N"
    assert run.channel("Load").values == (1.0, 2.0)
