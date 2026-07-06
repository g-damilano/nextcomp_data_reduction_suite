from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportFieldOverride:
    field_key: str
    value: Any
    reason: str
    reviewer: str = ""
    timestamp: str = ""
    source_surface: str = "method_run"
    section: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ReportFieldOverride":
        field_key = str(payload.get("field_key") or payload.get("field") or "").strip()
        if not field_key:
            raise ValueError("Report override requires field_key.")
        if payload.get("value") in (None, ""):
            raise ValueError(f"Report override for '{field_key}' requires a value.")
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise ValueError(f"Report override for '{field_key}' requires a reason.")
        return cls(
            field_key=field_key,
            value=payload.get("value"),
            reason=reason,
            reviewer=str(payload.get("reviewer") or ""),
            timestamp=str(payload.get("timestamp") or _now()),
            source_surface=str(payload.get("source_surface") or "method_run"),
            section=str(payload.get("section") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_key": self.field_key,
            "value": self.value,
            "reason": self.reason,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "source_surface": self.source_surface,
            "section": self.section,
        }


def normalize_report_overrides(payloads: Any) -> tuple[ReportFieldOverride, ...]:
    if payloads in (None, ""):
        return ()
    if isinstance(payloads, dict):
        payloads = payloads.get("overrides", [])
    overrides = []
    for payload in payloads or []:
        if isinstance(payload, ReportFieldOverride):
            overrides.append(payload)
        elif isinstance(payload, dict):
            overrides.append(ReportFieldOverride.from_payload(payload))
    return tuple(overrides)


def build_override_ledger(overrides: tuple[ReportFieldOverride, ...]) -> dict[str, Any]:
    return {
        "schema_id": "report.override_ledger.v0_1",
        "records": [
            {
                "field_key": override.field_key,
                "new_value": override.value,
                "decision_type": "set_report_value",
                "reason": override.reason,
                "reviewer": override.reviewer,
                "timestamp": override.timestamp,
                "source_surface": override.source_surface,
                "section": override.section,
            }
            for override in overrides
        ],
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
