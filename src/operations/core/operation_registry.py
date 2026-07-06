from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from dataclasses import replace

from operations.core.operation import Operation
from operations.core.operation_context import OperationContext
from operations.core.operation_contract_registry import get_evidence_contract
from operations.core.operation_result import OperationResult


class OperationRegistry:
    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}

    def register(self, operation: Operation) -> None:
        self._operations[operation.operation_id] = operation

    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        operation_id = str(step.get("op", "")).strip()
        if not operation_id:
            raise ValueError("Recipe step is missing an op value.")
        operation = self._operations.get(operation_id)
        if operation is None:
            raise KeyError(f"Unknown operation: {operation_id}")
        results = operation.run(context, step)
        step_id = str(step.get("id") or operation_id).strip()
        step_label = str(step.get("label") or step.get("title") or step_id).strip()
        audit_view = step.get("audit_view")
        patched: list[OperationResult] = []
        for result in results:
            operation_type = result.operation_type or result.operation_id
            contract = get_evidence_contract(operation_type)
            evidence_annotation = step.get("evidence") if isinstance(step.get("evidence"), Mapping) else {}
            report_annotation = step.get("report") if isinstance(step.get("report"), Mapping) else {}
            surface_policy = step.get("surface_policy") if isinstance(step.get("surface_policy"), Mapping) else {}
            annotated_roles = report_annotation.get("roles") if isinstance(report_annotation, Mapping) else None
            report_roles = tuple(str(role) for role in annotated_roles) if isinstance(annotated_roles, list) else contract.report_roles
            default_audit_view = str(
                evidence_annotation.get("audit_view")
                or evidence_annotation.get("default_audit_view")
                or audit_view
                or contract.default_audit_view
                or ""
            )
            workbench_view = str(
                evidence_annotation.get("workbench_view")
                or contract.workbench_view
                or ""
            )
            evidence_refs = _evidence_refs_from_annotation(evidence_annotation, contract.required_evidence_refs)
            patched.append(
                replace(
                    result,
                    procedure_step_id=step_id,
                    recipe_step_id=step_id,
                    recipe_step_label=step_label,
                    evidence_contract_id=contract.contract_id,
                    evidence_role=str(evidence_annotation.get("evidence_role") or contract.evidence_role),
                    default_audit_block=str(evidence_annotation.get("default_audit_block") or contract.default_audit_block or ""),
                    default_audit_view=default_audit_view,
                    workbench_view=workbench_view,
                    report_roles=report_roles,
                    evidence_refs=evidence_refs,
                    surface_policy_snapshot=dict(surface_policy),
                    audit_view_hint=default_audit_view if default_audit_view and not result.audit_view_hint else result.audit_view_hint,
                )
            )
        return patched


def default_operation_registry() -> OperationRegistry:
    from operations.curve.boundary_resolution import ResolveExperimentBoundariesOperation
    from operations.curve.chord_slope import ChordSlopeOperation
    from operations.curve.derive_series import (
        DeriveAreaOperation,
        DeriveSeriesByScalarOperation,
        DeriveSeriesMeanOperation,
        MapChannelOperation,
        MapScalarOperation,
    )
    from operations.curve.gate_experiment_signal import GateExperimentSignalOperation
    from operations.curve.max_point import AcceptedPeakPointOperation, MaxPointOperation
    from operations.curve.orient_strain_channels import OrientStrainChannelsOperation
    from operations.curve.value_at import ValueAtIndexOperation
    from operations.diagnostics.bending import BendingDiagnosticOperation

    registry = OperationRegistry()
    for operation in (
        MapChannelOperation(),
        MapScalarOperation(),
        DeriveAreaOperation(),
        OrientStrainChannelsOperation(),
        DeriveSeriesMeanOperation(),
        GateExperimentSignalOperation(),
        ResolveExperimentBoundariesOperation(),
        DeriveSeriesByScalarOperation(),
        MaxPointOperation(),
        AcceptedPeakPointOperation(),
        ValueAtIndexOperation(),
        ChordSlopeOperation(),
        BendingDiagnosticOperation(),
    ):
        registry.register(operation)
    return registry


def _evidence_refs_from_annotation(
    evidence_annotation: Mapping[str, Any],
    contract_refs: tuple[str, ...],
) -> dict[str, Any]:
    refs = {f"contract_ref_{index + 1}": ref for index, ref in enumerate(contract_refs)}
    required = evidence_annotation.get("required_artifacts") if isinstance(evidence_annotation, Mapping) else None
    if isinstance(required, list):
        for item in required:
            key = str(item).strip()
            if key:
                refs[key] = key
    return refs
