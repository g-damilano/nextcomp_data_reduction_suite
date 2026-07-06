from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_amendment_record(
    *,
    amendment_id: str,
    classes: tuple[str, ...],
    reviewer: str,
    reason: str,
    source_surface: str,
    affected_artifacts: list[str],
) -> dict[str, Any]:
    return {
        "amendment_id": amendment_id,
        "timestamp": utc_now(),
        "amendment_classes": list(classes),
        "reviewer": reviewer,
        "reason": reason,
        "source_surface": source_surface,
        "affected_artifacts": affected_artifacts,
    }


def ledger_with_record(existing: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    records = existing.get("records", []) if isinstance(existing, dict) else []
    records = list(records) if isinstance(records, list) else []
    records.append(record)
    return {
        "schema_id": "mtda.amendment_ledger.v0_1",
        "records": records,
    }
