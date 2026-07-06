from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from archives.core.checksums import sha256_file


def build_export_manifest(
    *,
    source_mtda: Path,
    profile: str,
    source_reference: dict[str, Any],
    manifest: dict[str, Any],
    artifacts: list[dict[str, Any]],
    selection: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_id": "mtda.production_export_manifest.v0_1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "profile": profile,
        "source_mtda": {
            "path": str(source_mtda),
            "checksum_algorithm": "sha256",
            "checksum": sha256_file(source_mtda),
        },
        "source_mtdp": source_reference.get("source_package", {}),
        "method": {
            "method_id": manifest.get("method_id", ""),
            "method_version": manifest.get("method_version", ""),
        },
        "selection": selection,
        "artifacts": artifacts,
        "warnings": warnings,
        "deferred_formats": ["pdf", "docx"],
        "mtdp_mutated": False,
        "mtda_mutated": False,
    }
