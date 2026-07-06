from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WizardPageActionContract:
    page_id: str
    purpose: str
    operator_decision: str
    editable_items: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    primary_evidence: tuple[str, ...]
    blocking_states: tuple[str, ...]
    downstream_consequence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "purpose": self.purpose,
            "operator_decision": self.operator_decision,
            "editable_items": list(self.editable_items),
            "allowed_actions": list(self.allowed_actions),
            "primary_evidence": list(self.primary_evidence),
            "blocking_states": list(self.blocking_states),
            "downstream_consequence": self.downstream_consequence,
        }


def wizard_page_action_contract(page_id: str) -> dict[str, Any]:
    key = _ALIASES.get(page_id, page_id)
    return _action_contract_record(_CONTRACTS.get(key, _fallback_contract(key)))


def wizard_page_action_contracts() -> dict[str, dict[str, Any]]:
    return {
        page_id: _action_contract_record(contract)
        for page_id, contract in _CONTRACTS.items()
    }


def wizard_action_surface_manifest() -> dict[str, Any]:
    return {
        "schema_id": "wizard.action_surface_contracts.v0_1",
        "surface_role": "action_decision_repair",
        "pages": wizard_page_action_contracts(),
    }


def _fallback_contract(page_id: str) -> WizardPageActionContract:
    return WizardPageActionContract(
        page_id=page_id,
        purpose="Expose the page's operator action contract.",
        operator_decision="Review available evidence and decide the next safe action.",
        editable_items=(),
        allowed_actions=("review_evidence",),
        primary_evidence=(),
        blocking_states=(),
        downstream_consequence="No downstream consequence is declared for this page.",
    )


def _action_contract_record(contract: WizardPageActionContract) -> dict[str, Any]:
    return contract.to_dict()


_ALIASES = {
    "select_package": "package",
    "select_method": "method",
    "report_authoring": "report_metadata",
    "report_completion": "report_metadata",
    "final_selection": "acceptance",
    "output_finalization": "output",
}


_CONTRACTS: dict[str, WizardPageActionContract] = {
    "package": WizardPageActionContract(
        page_id="package",
        purpose="Choose and verify the MTDP package before any method work begins.",
        operator_decision="Use this source package, or return to package selection.",
        editable_items=("selected_package_path",),
        allowed_actions=("browse_package", "reload_package", "confirm_package", "open_source_folder"),
        primary_evidence=("manifest.json", "source_reference.json", "package_preview_view_model"),
        blocking_states=("missing_package", "unreadable_package", "schema_not_supported"),
        downstream_consequence="Confirmed package identity defines the run set, source checksums, and available channels for mapping and readiness.",
    ),
    "method": WizardPageActionContract(
        page_id="method",
        purpose="Choose the method package and inspect declared method inputs, recipes, and surfaces.",
        operator_decision="Use this method package for the selected source package.",
        editable_items=("selected_method_path",),
        allowed_actions=("browse_method", "reload_method", "confirm_method", "open_method_folder"),
        primary_evidence=("method_manifest.yaml", "method_inputs.yaml", "resolve_recipe.yaml", "reduce_recipe.yaml"),
        blocking_states=("missing_method", "method_manifest_invalid", "method_source_incompatible"),
        downstream_consequence="Confirmed method controls required inputs, operations, report recipes, validation, and acceptance policy.",
    ),
    "mapping": WizardPageActionContract(
        page_id="mapping",
        purpose="Resolve concrete package channels and tokens against method inputs.",
        operator_decision="Accept this mapping profile, repair it, or choose another profile.",
        editable_items=("mapping_profile_path", "source_bindings"),
        allowed_actions=("browse_mapping", "reload_mapping", "review_candidates", "confirm_mapping"),
        primary_evidence=("mapping/mapping_profile_used.json", "mapping/mapping_candidate_report.json", "mapping/mapping_resolution_report.json"),
        blocking_states=("execution_critical_missing", "ambiguous_binding", "schema_method_incompatible"),
        downstream_consequence="Confirmed bindings determine what resolve/reduce operations read; red mapping rows block readiness.",
    ),
    "readiness": WizardPageActionContract(
        page_id="readiness",
        purpose="Decide whether the method can run with the selected package/method/mapping.",
        operator_decision="Continue to execution or repair missing execution-critical inputs.",
        editable_items=(),
        allowed_actions=("run_readiness", "open_mapping_repair", "continue_to_execution"),
        primary_evidence=("readiness/readiness_report.json", "readiness/missing_inputs.csv", "readiness/resolved_inputs.csv"),
        blocking_states=("NOT_READY", "MAPPING_REQUIRED", "SCHEMA_EXTENSION_REQUIRED"),
        downstream_consequence="A ready state allows method execution; readiness warnings remain visible downstream as report or audit evidence.",
    ),
    "report_metadata": WizardPageActionContract(
        page_id="report_metadata",
        purpose="Complete report-only metadata without mutating the MTDP.",
        operator_decision="Supply report-only values, mark missing values acceptable, or continue with warnings.",
        editable_items=("report_only_field_values", "override_reasons", "reviewer"),
        allowed_actions=("filter_missing_fields", "record_report_override", "clear_report_override", "continue_with_warnings"),
        primary_evidence=("report/report_field_catalog_resolved.json", "report/missing_report_fields.csv", "report/report_values_used.csv"),
        blocking_states=("required_report_field_missing", "override_reason_missing"),
        downstream_consequence="Report-only amendments affect Test Report completeness and provenance, not method calculations.",
    ),
    "execution": WizardPageActionContract(
        page_id="execution",
        purpose="Run the method pipeline and monitor completion or repairable failures.",
        operator_decision="Start execution, wait, cancel, or inspect a failed run state.",
        editable_items=("output_path",),
        allowed_actions=("start_method_run", "cancel_run", "open_run_log", "retry_after_repair"),
        primary_evidence=("audit/operation_log.json", "workbench/operation_trace.json", "audit/warnings.json"),
        blocking_states=("readiness_not_ready", "run_failed", "output_unwritable"),
        downstream_consequence="Successful execution creates MTDA evidence used by validation, acceptance, reports, and finalization.",
    ),
    "validation": WizardPageActionContract(
        page_id="validation",
        purpose="Review validation checks and decide whether failures block acceptance.",
        operator_decision="Continue with passing/warning validation or repair/re-run after failures.",
        editable_items=(),
        allowed_actions=("open_validation_evidence", "open_workbench_for_check", "continue_to_acceptance", "return_to_mapping_or_method"),
        primary_evidence=("validation/validation_report.json", "validation/deviations.csv", "workbench/operation_trace.json"),
        blocking_states=("failed_validation_check",),
        downstream_consequence="Validation outcomes feed audit traceability and acceptance review, without changing method outputs.",
    ),
    "acceptance": WizardPageActionContract(
        page_id="acceptance",
        purpose="Confirm final run inclusion, discharge excluded runs, and record human selection decisions.",
        operator_decision="Accept machine selection, keep/remove/restore runs, or defer final selection.",
        editable_items=("run_selection_decisions", "decision_reasons", "reviewer"),
        allowed_actions=("confirm_machine_selection", "keep_run", "remove_run", "restore_run", "clear_override", "open_discharge_report"),
        primary_evidence=("acceptance/acceptance_report.json", "acceptance/run_flags.csv", "acceptance/final_report_runs.csv", "acceptance/discharge_report.json"),
        blocking_states=("selection_reason_missing", "review_required_unresolved"),
        downstream_consequence="Final report selection controls aggregate statistics and the formal Test Report run set.",
    ),
    "output": WizardPageActionContract(
        page_id="output",
        purpose="Review generated surfaces, finalize the MTDA, and choose handoff actions.",
        operator_decision="Finalize, amend report-only evidence, export, or open the appropriate surface.",
        editable_items=("finalization_note", "report_only_amendments", "export_profile"),
        allowed_actions=("open_test_report", "open_audit_report", "open_workbench", "finalize_mtda", "export_production_bundle"),
        primary_evidence=("surface_manifest.json", "provenance.json", "checksums.json", "report/report_quality_gate.json"),
        blocking_states=("required_report_field_missing", "archive_not_written", "checksum_missing"),
        downstream_consequence="Output actions affect archive handoff state and distribution artifacts, not the completed method calculations.",
    ),
}
