from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OperationResult:
    operation_id: str
    phase: str
    run_id: str | None
    operation_type: str | None = None
    recipe_step_id: str | None = None
    recipe_step_label: str | None = None
    status: str = "pass"
    inputs: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    units: dict[str, str | None] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    inspection_refs: tuple[str, ...] = ()
    audit_view_hint: str | None = None
    warnings: tuple[str, ...] = ()
    procedure_step_id: str | None = None
    evidence_contract_id: str | None = None
    evidence_role: str | None = None
    default_audit_block: str | None = None
    default_audit_view: str | None = None
    workbench_view: str | None = None
    report_roles: tuple[str, ...] = ()
    evidence_refs: dict[str, Any] = field(default_factory=dict)
    surface_policy_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_record(self, sequence: int) -> dict[str, Any]:
        operation_type = self.operation_type or self.operation_id
        status = _normalize_status(self.status, self.warnings)
        stable_run = self.run_id or "dataset"
        operation_record_ref = f"audit/operation_log.json#/sequence/{sequence}"
        evidence_refs = _default_evidence_refs(
            run_id=self.run_id,
            sequence=sequence,
            default_audit_block=self.default_audit_block,
        )
        evidence_refs.update(self.evidence_refs)
        evidence_refs.setdefault("operation_record", operation_record_ref)
        return {
            "operation_id": f"{sequence:04d}_{self.phase}_{stable_run}_{operation_type}",
            "procedure_step_id": self.procedure_step_id or self.recipe_step_id,
            "recipe_step_id": self.recipe_step_id,
            "recipe_step_label": self.recipe_step_label,
            "operation_type": operation_type,
            "evidence_contract_id": self.evidence_contract_id,
            "evidence_role": self.evidence_role,
            "default_audit_block": self.default_audit_block,
            "default_audit_view": self.default_audit_view,
            "workbench_view": self.workbench_view,
            "report_roles": list(self.report_roles),
            "evidence_refs": evidence_refs,
            "surface_policy_snapshot": self.surface_policy_snapshot,
            "sequence": sequence,
            "phase": self.phase,
            "operation": operation_type,
            "run_id": self.run_id,
            "status": status,
            "inputs": self.inputs,
            "parameters": self.parameters,
            "outputs": self.outputs,
            "units": self.units,
            "evidence": self.evidence,
            "inspection_refs": list(self.inspection_refs),
            "audit_view_hint": self.audit_view_hint,
            "warnings": list(self.warnings),
        }


def _normalize_status(status: str, warnings: tuple[str, ...]) -> str:
    if status == "ok":
        status = "pass"
    elif status == "warning":
        status = "pass_with_warning"
    elif status == "error":
        status = "failed"
    if warnings and status == "pass":
        return "pass_with_warning"
    return status


def _default_evidence_refs(
    *,
    run_id: str | None,
    sequence: int,
    default_audit_block: str | None,
) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "workbench_record": f"workbench/operation_trace.json#/operations/{sequence}",
    }
    if run_id:
        safe_run = "".join(char if char.isalnum() or char in "-_" else "_" for char in run_id).strip("_") or run_id
        bounded_curve = f"method_outputs/curves/{safe_run}_stress_strain_bounded.csv"
        full_curve = f"method_outputs/curves/{safe_run}_stress_strain_full.csv"
        refs.update(
            {
                "input_curve": bounded_curve,
                "bounded_stress_strain_curve": bounded_curve,
                "full_stress_strain_curve": full_curve,
                "run_curve": f"method_outputs/curves/{safe_run}_stress_strain.csv",
            }
        )
        if default_audit_block:
            refs["audit_block"] = f"audit/audit_blocks.json#/runs/{run_id}/blocks/{default_audit_block}"
    return refs
