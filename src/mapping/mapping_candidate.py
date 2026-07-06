from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MappingCandidate:
    requirement_id: str
    method_field: str
    source_role: str
    severity: str
    scope: str
    source_kind: str
    source_name: str
    source_path: str
    confidence: float
    status: str
    unit: str = ""
    expected_unit: str = ""
    coverage: str = ""
    example_value: Any = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "method_field": self.method_field,
            "source_role": self.source_role,
            "severity": self.severity,
            "scope": self.scope,
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "source_path": self.source_path,
            "confidence": self.confidence,
            "status": self.status,
            "unit": self.unit,
            "expected_unit": self.expected_unit,
            "coverage": self.coverage,
            "example_value": self.example_value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class MappingCandidateSet:
    requirement_id: str
    method_field: str
    source_role: str
    severity: str
    scope: str
    candidates: tuple[MappingCandidate, ...]

    @property
    def status(self) -> str:
        if not self.candidates:
            return "missing"
        best = self.candidates[0].confidence
        tied = [item for item in self.candidates if abs(item.confidence - best) < 0.001]
        if len(tied) > 1 and best < 0.96:
            return "ambiguous"
        return "resolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "method_field": self.method_field,
            "source_role": self.source_role,
            "severity": self.severity,
            "scope": self.scope,
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }
