from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_mtda_manifest(
    *,
    method_id: str,
    method_version: str,
    source_package_name: str,
    artifact_surfaces: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "package_format": "mtda",
        "format_version": "0.1.0",
        "method_id": method_id,
        "method_version": method_version,
        "source_package": source_package_name,
        "created_at": utc_now_iso(),
        "artifact_surfaces": artifact_surfaces or {},
    }
