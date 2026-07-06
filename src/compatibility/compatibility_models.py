from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_WITH_WARNINGS = "COMPATIBLE_WITH_WARNINGS"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    SCHEMA_EXTENSION_REQUIRED = "SCHEMA_EXTENSION_REQUIRED"


@dataclass(frozen=True, slots=True)
class CompatibilityRequirement:
    requirement_id: str
    method_field: str
    source_role: str
    severity: str
    scope: str
    compatible: bool
    support_kind: str
    evidence: tuple[str, ...] = ()
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "method_field": self.method_field,
            "source_role": self.source_role,
            "severity": self.severity,
            "scope": self.scope,
            "compatible": self.compatible,
            "support_kind": self.support_kind,
            "evidence": list(self.evidence),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    status: CompatibilityStatus
    method_id: str
    schema_id: str
    schema_version: str
    requirements: tuple[CompatibilityRequirement, ...]

    @property
    def blocks_mapping(self) -> bool:
        return self.status == CompatibilityStatus.SCHEMA_EXTENSION_REQUIRED

    @property
    def summary(self) -> dict[str, Any]:
        critical = [row for row in self.requirements if row.severity == "execution_critical"]
        compatible = [row for row in self.requirements if row.compatible]
        unsupported = [row for row in self.requirements if not row.compatible]
        return {
            "status": self.status.value,
            "method_id": self.method_id,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "requirement_total": len(self.requirements),
            "compatible_total": len(compatible),
            "unsupported_total": len(unsupported),
            "execution_critical_total": len(critical),
            "execution_critical_supported": sum(1 for row in critical if row.compatible),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.schema_method_compatibility_report.v0_1",
            "status": self.status.value,
            "method_id": self.method_id,
            "source_schema_id": self.schema_id,
            "source_schema_version": self.schema_version,
            "summary": self.summary,
            "requirements": [row.to_dict() for row in self.requirements],
            "blocks_mapping": self.blocks_mapping,
        }

    def summary_rows(self) -> list[dict[str, Any]]:
        return [self.summary]

    def schema_extension_stub(self) -> dict[str, Any]:
        unsupported = [row.to_dict() for row in self.requirements if not row.compatible]
        return {
            "schema_id": "method.schema_extension_proposal_stub.v0_1",
            "status": "not_required" if not unsupported else "proposal_required",
            "method_id": self.method_id,
            "source_schema_id": self.schema_id,
            "unsupported_requirements": unsupported,
            "note": "This is a diagnostic stub only; Stage 20 does not implement schema-extension authoring.",
        }
