from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExperimentBoundaryPoint:
    index: int | None
    policy: str
    confidence: str
    reason: str
    domain: str | None = None
    domain_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "policy": self.policy,
            "confidence": self.confidence,
            "reason": self.reason,
            "domain": self.domain,
            "domain_value": self.domain_value,
        }


@dataclass(frozen=True, slots=True)
class ExperimentBoundaryEvent:
    event_id: str
    index: int | None
    value: float | None = None
    unit: str | None = None
    domain: str | None = None
    domain_value: float | None = None
    diagnostic_only: bool = False
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "index": self.index,
            "value": self.value,
            "unit": self.unit,
            "domain": self.domain,
            "domain_value": self.domain_value,
            "diagnostic_only": self.diagnostic_only,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ExperimentBoundaryRecord:
    run_id: str
    start_index: int | None
    end_index: int | None
    include_endpoint: bool
    start_policy: str
    end_policy: str
    confidence: str
    reason: str
    domain: str | None = None
    domain_value: float | None = None
    events: tuple[ExperimentBoundaryEvent, ...] = ()
    warnings: tuple[str, ...] = ()
    source_series_refs: dict[str, Any] = field(default_factory=dict)
    start: ExperimentBoundaryPoint | None = None
    end: ExperimentBoundaryPoint | None = None

    def to_dict(self) -> dict[str, Any]:
        start = self.start or ExperimentBoundaryPoint(
            index=self.start_index,
            policy=self.start_policy,
            confidence=self.confidence,
            reason="Analysis start resolved from start policy.",
            domain=self.domain,
            domain_value=None,
        )
        end = self.end or ExperimentBoundaryPoint(
            index=self.end_index,
            policy=self.end_policy,
            confidence=self.confidence,
            reason=self.reason,
            domain=self.domain,
            domain_value=self.domain_value,
        )
        return {
            "run_id": self.run_id,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "include_endpoint": self.include_endpoint,
            "start_policy": self.start_policy,
            "end_policy": self.end_policy,
            "confidence": self.confidence,
            "reason": self.reason,
            "domain": self.domain,
            "domain_value": self.domain_value,
            "start": start.to_dict(),
            "end": end.to_dict(),
            "analysis_interval": {
                "start_index": self.start_index,
                "end_index": self.end_index,
                "include_endpoint": self.include_endpoint,
            },
            "events": [event.to_dict() for event in self.events],
            "warnings": list(self.warnings),
            "source_series_refs": dict(self.source_series_refs),
        }
