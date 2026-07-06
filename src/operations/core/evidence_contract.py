from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


EvidenceRole = Literal[
    "primary_audit_block",
    "supporting_evidence",
    "hidden_by_default",
    "workbench_only",
    "test_report_value",
]


@dataclass(frozen=True, slots=True)
class OperationIOContract:
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    schema_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": list(self.required),
            "optional": list(self.optional),
            "schema_ref": self.schema_ref,
        }


@dataclass(frozen=True, slots=True)
class EvidenceContract:
    operation_type: str
    evidence_role: EvidenceRole
    default_audit_block: str | None
    default_audit_view: str | None
    workbench_view: str | None
    required_evidence_refs: tuple[str, ...] = ()
    default_narrative: str = ""
    report_roles: tuple[str, ...] = ()
    input_schema: OperationIOContract = field(default_factory=OperationIOContract)
    output_schema: OperationIOContract = field(default_factory=OperationIOContract)
    version: str = "0.1.0"

    @property
    def contract_id(self) -> str:
        return f"operation_evidence:{self.operation_type}:v{self.version}"

    def to_dict(self) -> dict[str, Any]:
        # Keep legacy aliases alongside the directive fields until older callers
        # have migrated to the operation-owned contract vocabulary.
        report_role = self.report_roles[0] if self.report_roles else ""
        return {
            "contract_id": self.contract_id,
            "operation_type": self.operation_type,
            "version": self.version,
            "input_schema": self.input_schema.to_dict(),
            "output_schema": self.output_schema.to_dict(),
            "evidence_role": self.evidence_role,
            "default_audit_block": self.default_audit_block,
            "default_audit_fragment": self.default_audit_view,
            "default_audit_view": self.default_audit_view,
            "workbench_view": self.workbench_view,
            "default_workbench_view": self.workbench_view,
            "required_evidence_refs": list(self.required_evidence_refs),
            "evidence_artifacts_required": [
                {"member": ref, "role": ref.replace("/", "_").replace(".", "_"), "required": True}
                for ref in self.required_evidence_refs
            ],
            "default_narrative": self.default_narrative,
            "report_roles": list(self.report_roles),
            "report_role": report_role,
        }


# Backwards-compatible name used by the first Stage 26 pass.
OperationEvidenceContract = EvidenceContract


@dataclass(frozen=True, slots=True)
class EvidenceArtifactRequirement:
    member: str
    role: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"member": self.member, "role": self.role, "required": self.required}


def get_operation_evidence_contract(operation_type: str) -> EvidenceContract:
    from operations.core.operation_contract_registry import get_evidence_contract

    return get_evidence_contract(operation_type)


def operation_evidence_contracts() -> dict[str, EvidenceContract]:
    from operations.core.operation_contract_registry import registered_evidence_contracts

    return registered_evidence_contracts()


def operation_evidence_contract_records() -> dict[str, dict[str, Any]]:
    from operations.core.operation_contract_registry import evidence_contract_records

    return evidence_contract_records()
