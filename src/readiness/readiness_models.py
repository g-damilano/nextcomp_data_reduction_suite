from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ReadinessStatus(StrEnum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    NOT_READY = "NOT_READY"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    SCHEMA_EXTENSION_REQUIRED = "SCHEMA_EXTENSION_REQUIRED"


@dataclass(frozen=True, slots=True)
class MethodInputRequirement:
    requirement_id: str
    method_field: str
    source_role: str
    severity: str
    scope: str
    required_for: tuple[str, ...] = ()
    empty_policy: str = "fail"
    expected_unit: str | None = None
    required_when: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MethodInputRequirement":
        required_for = payload.get("required_for", ())
        return cls(
            requirement_id=str(payload.get("requirement_id") or ""),
            method_field=str(payload.get("method_field") or ""),
            source_role=str(payload.get("source_role") or ""),
            severity=str(payload.get("severity") or "execution_critical"),
            scope=str(payload.get("scope") or "per_run"),
            required_for=tuple(str(item) for item in required_for) if isinstance(required_for, list) else (),
            empty_policy=str(payload.get("empty_policy") or "fail"),
            expected_unit=_optional_text(payload.get("expected_unit")),
            required_when=_optional_text(payload.get("required_when")),
        )


@dataclass(frozen=True, slots=True)
class ResolvedInput:
    requirement_id: str
    method_field: str
    source_role: str
    severity: str
    scope: str
    run_id: str | None
    mapped_source: str | None
    status: str
    value_state: str
    unit: str | None = None
    message: str = ""
    required_for: tuple[str, ...] = ()
    expected_unit: str | None = None
    value_preview: Any = None
    source_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "method_field": self.method_field,
            "source_role": self.source_role,
            "severity": self.severity,
            "scope": self.scope,
            "run_id": self.run_id,
            "mapped_source": self.mapped_source,
            "status": self.status,
            "value_state": self.value_state,
            "unit": self.unit,
            "expected_unit": self.expected_unit,
            "message": self.message,
            "required_for": list(self.required_for),
            "value_preview": self.value_preview,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True, slots=True)
class MethodInputsDeclaration:
    method_id: str
    version: str
    purpose: str
    requirements: tuple[MethodInputRequirement, ...] = field(default_factory=tuple)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MethodInputsDeclaration":
        requirements = payload.get("requirements", ())
        return cls(
            method_id=str(payload.get("method_id") or ""),
            version=str(payload.get("version") or ""),
            purpose=str(payload.get("purpose") or ""),
            requirements=tuple(
                MethodInputRequirement.from_payload(item)
                for item in requirements
                if isinstance(item, dict)
            )
            if isinstance(requirements, list)
            else (),
        )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
