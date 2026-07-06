from __future__ import annotations

from archives.core.checksums import build_checksums


def test_build_checksums_excludes_explicit_metadata_checksum_member() -> None:
    files = {
        "dataset/raw/run_001.csv": b"raw",
        "metadata/manifest.json": b"{}",
        "metadata/checksums.json": b"stale",
        "checksums.json": b"legacy",
        "software/checksums.json": b"recommended",
    }

    checksums = build_checksums(files, checksum_member="metadata/checksums.json")

    assert checksums["algorithm"] == "sha256"
    assert checksums["checksum_member"] == "metadata/checksums.json"
    assert set(checksums["files"]) == {"dataset/raw/run_001.csv", "metadata/manifest.json"}


def test_build_checksums_keeps_legacy_default_exclusions() -> None:
    files = {
        "manifest.json": b"{}",
        "checksums.json": b"stale",
        "software/checksums.json": b"recommended",
        "metadata/checksums.json": b"aligned",
    }

    checksums = build_checksums(files)

    assert checksums["checksum_member"] == "checksums.json"
    assert set(checksums["files"]) == {"manifest.json"}
