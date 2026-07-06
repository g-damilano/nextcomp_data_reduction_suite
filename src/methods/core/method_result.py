from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from archives.mtdp.models import MTDPPackageInput
from methods.core.method_package import MethodPackage


@dataclass(frozen=True, slots=True)
class MethodRunResult:
    source: MTDPPackageInput
    method_package: MethodPackage
    mapping: dict[str, Any]
    readiness_report: dict[str, Any]
    readiness_summary: list[dict[str, Any]]
    resolved_inputs: list[dict[str, Any]]
    missing_inputs: list[dict[str, Any]]
    specimen_results: list[dict[str, Any]]
    dataset_summary: list[dict[str, Any]]
    dataset_summary_by_selection: list[dict[str, Any]]
    curve_family: list[dict[str, Any]]
    operation_log: list[dict[str, Any]]
    evidence: dict[str, Any]
    inspections: list[dict[str, Any]]
    resolve_summary: dict[str, Any]
    reduce_summary: dict[str, Any]
    warnings: list[dict[str, Any]]
    validation_report: dict[str, Any]
    validation_summary: list[dict[str, Any]]
    validation_deviations: list[dict[str, Any]]
    reference_values_used: list[dict[str, Any]]
    acceptance_report: dict[str, Any]
    acceptance_summary: list[dict[str, Any]]
    run_flags: list[dict[str, Any]]
    selection_sets: dict[str, Any]
    selection_membership: list[dict[str, Any]]
    discharged_runs: list[dict[str, Any]]
    discharge_report: dict[str, Any]
    curve_family_assessment: dict[str, Any] | None = None
    curve_family_scores: list[dict[str, Any]] | None = None
    curve_family_flags: list[dict[str, Any]] | None = None
    curve_family_reference_rows: list[dict[str, Any]] | None = None
    curve_family_aligned_rows: list[dict[str, Any]] | None = None
    curve_family_residual_rows: list[dict[str, Any]] | None = None
    curve_family_policy_resolved: dict[str, Any] | None = None
    curve_shape_diagnostic_report: dict[str, Any] | None = None
    curve_shape_diagnostic_scores: list[dict[str, Any]] | None = None
    curve_shape_diagnostic_reference_rows: list[dict[str, Any]] | None = None
    curve_shape_diagnostic_residual_rows: list[dict[str, Any]] | None = None
    curve_shape_diagnostic_policy_resolved: dict[str, Any] | None = None
    curve_shape_diagnostic_flags: list[dict[str, Any]] | None = None
    experiment_boundaries: list[dict[str, Any]] | None = None
    boundary_events: list[dict[str, Any]] | None = None
    bounded_curve_family: list[dict[str, Any]] | None = None
    full_curve_family: list[dict[str, Any]] | None = None
    human_decisions: dict[str, Any] | None = None
    human_decision_rows: list[dict[str, Any]] | None = None
    override_ledger: dict[str, Any] | None = None
    override_ledger_rows: list[dict[str, Any]] | None = None
    selection_sets_final: dict[str, Any] | None = None
    selection_membership_final: list[dict[str, Any]] | None = None
    final_report_runs: list[dict[str, Any]] | None = None
    report_overrides: tuple[dict[str, Any], ...] = ()
