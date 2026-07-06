from __future__ import annotations

import hashlib
from typing import Mapping

_CHECKSUM_MEMBERS = {
    "checksums.json",
    "metadata/checksums.json",
    "software/checksums.json",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_checksums(files: Mapping[str, bytes], *, checksum_member: str = "checksums.json") -> dict[str, object]:
    return {
        "schema_id": "nextcomp.archive.checksums",
        "schema_version": "0.2.0",
        "algorithm": "sha256",
        "checksum_member": checksum_member,
        "files": {
            path: sha256_bytes(content)
            for path, content in sorted(files.items())
            if path not in _CHECKSUM_MEMBERS and path != checksum_member
        },
    }
