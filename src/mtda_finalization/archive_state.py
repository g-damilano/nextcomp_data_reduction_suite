from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout, metadata_member
from archives.core.checksums import sha256_file


@dataclass(frozen=True, slots=True)
class MTDAArchiveState:
    path: Path
    member_count: int
    manifest: dict[str, Any]
    has_finalization_namespace: bool
    checksum: str

    @classmethod
    def load(cls, path: str | Path) -> "MTDAArchiveState":
        archive_path = Path(path)
        with zipfile.ZipFile(archive_path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            manifest = _json_member(
                archive,
                MTDAAlignedLayout.manifest if MTDAAlignedLayout.manifest in names else "manifest.json",
            )
        return cls(
            path=archive_path,
            member_count=len(names),
            manifest=manifest,
            has_finalization_namespace=any(
                name.startswith("finalization/") or name.startswith(metadata_member("finalization/"))
                for name in names
            ),
            checksum=sha256_file(archive_path),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "mtda.archive_state.v0_1",
            "path": str(self.path),
            "member_count": self.member_count,
            "method_id": self.manifest.get("method_id", ""),
            "method_version": self.manifest.get("method_version", ""),
            "source_package": self.manifest.get("source_package", ""),
            "has_finalization_namespace": self.has_finalization_namespace,
            "checksum_sha256": self.checksum,
        }


def _json_member(archive: zipfile.ZipFile, member: str) -> dict[str, Any]:
    try:
        payload = json.loads(archive.read(member))
    except (KeyError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
