from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping


_TRANSITION_CHECKSUM_MEMBERS = {
    "checksums.json",
    "software/checksums.json",
    "metadata/checksums.json",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_checksums(files: Mapping[str, bytes], *, checksum_member: str = "checksums.json") -> dict[str, object]:
    excluded = {*_TRANSITION_CHECKSUM_MEMBERS, checksum_member}
    return {
        "schema_id": "archive.checksums",
        "schema_version": "0.1.0",
        "algorithm": "sha256",
        "checksum_member": checksum_member,
        "files": {
            path: sha256_bytes(content)
            for path, content in sorted(files.items())
            if path not in excluded
        },
    }
