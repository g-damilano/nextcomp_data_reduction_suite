from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from archives.core.layouts import MTDAAlignedLayout, aggregate_member, metadata_member, report_member
from ui.method_run_wizard.view_models.action_contracts import (
    wizard_action_surface_manifest,
    wizard_page_action_contract,
)


_ALIGNED_TEST_REPORT_HTML = report_member("test_report.html")
_ALIGNED_AUDIT_REPORT_HTML = report_member("audit_report.html")
_ALIGNED_REPORT_COMPLETION_TABLE = aggregate_member("report_completion_table.csv")
_ALIGNED_SURFACE_MANIFEST = MTDAAlignedLayout.surface_manifest


def output_review_view_model(result: Mapping[str, Any] | None) -> dict[str, Any]:
    result = result or {}
    members = [str(member) for member in result.get("archive_members", [])]
    member_set = set(members)
    surface_manifest = result.get("surface_manifest") if isinstance(result.get("surface_manifest"), Mapping) else {}
    surfaces = surface_manifest.get("surfaces", {}) if isinstance(surface_manifest.get("surfaces"), Mapping) else {}
    agreement = surface_manifest.get("cross_surface_agreement", {}) if isinstance(surface_manifest.get("cross_surface_agreement"), Mapping) else {}
    key_csvs = [
        member for member in members
        if member
        in {
            "dataset/01_normalized/normalization_registry.csv",
            aggregate_member("results_table.csv"),
            aggregate_member("statistics.csv"),
            aggregate_member("characteristic_points.csv"),
            aggregate_member("stress_strain_aligned.csv"),
            aggregate_member("run_decision_registry.csv"),
            aggregate_member("bending_summary_table.csv"),
            aggregate_member("missing_metadata_table.csv"),
            _ALIGNED_REPORT_COMPLETION_TABLE,
            aggregate_member("dataset_plot_manifest.csv"),
            report_member("audit_report.csv"),
            "report/report_values_used.csv",
            "report/missing_report_fields.csv",
            "report/report_completeness_summary.csv",
            "report/individual_results.csv",
            "report/aggregate_statistics.csv",
            "report/characteristic_points.csv",
            "report/feature_lines.csv",
            "report/aligned_curves.csv",
            "readiness/readiness_summary.csv",
            "readiness/resolved_inputs.csv",
            "readiness/missing_inputs.csv",
            "validation/validation_summary.csv",
            "validation/deviations.csv",
            "acceptance/acceptance_summary.csv",
            "acceptance/run_flags.csv",
            "acceptance/selection_membership.csv",
            "acceptance/selection_membership_final.csv",
            "acceptance/discharged_runs.csv",
            "acceptance/final_report_runs.csv",
            "acceptance/curve_family/curve_family_scores.csv",
            "acceptance/curve_family/curve_family_flags.csv",
            "method_outputs/dataset_summary_by_selection.csv",
        }
    ]
    key_artifacts = [
        member for member in members
        if member
        in {
            MTDAAlignedLayout.manifest,
            MTDAAlignedLayout.schema,
            MTDAAlignedLayout.dataset,
            MTDAAlignedLayout.provenance,
            MTDAAlignedLayout.checksums,
            _ALIGNED_SURFACE_MANIFEST,
            MTDAAlignedLayout.validation,
            MTDAAlignedLayout.readiness,
            MTDAAlignedLayout.method_outputs,
            metadata_member("finalization/archive_state.json"),
            metadata_member("finalization/amendment_ledger.json"),
            metadata_member("finalization/recompute_manifest.json"),
            metadata_member("finalization/finalization_report.json"),
            aggregate_member("dataset_plot.plot_package.json"),
            aggregate_member("dataset_plot.template.json"),
            report_member("test_report.json"),
            report_member("audit_report.json"),
            "manifest.json",
            "provenance.json",
            "checksums.json",
            "readiness/readiness_report.json",
            "validation/validation_report.json",
            "acceptance/acceptance_report.json",
            "acceptance/discharge_report.json",
            "acceptance/selection_sets_final.json",
            "acceptance/override_ledger.json",
            "report/report_completion_status.json",
            "report/report_field_catalog_resolved.json",
            "report/report_field_overrides.json",
            "report/report_override_ledger.json",
            "report/report_document.json",
            "report/report_quality_gate.json",
            "audit/audit_report.json",
            "workbench/operation_trace.json",
            "surface_manifest.json",
            "finalization/archive_state.json",
            "finalization/amendment_ledger.json",
            "finalization/recompute_manifest.json",
            "finalization/finalization_report.json",
        }
    ]
    test_report_member = _first_member(
        member_set,
        _ALIGNED_TEST_REPORT_HTML,
        "report/test_report.html",
        "report/iso14126_report.html",
    )
    audit_report_member = _first_member(
        member_set,
        _ALIGNED_AUDIT_REPORT_HTML,
        "audit/audit_report.html",
        "interactive_report/index.html",
    )
    workbench_member = _first_member(member_set, "workbench/index.html")
    report_completion_member = _first_member(
        member_set,
        _ALIGNED_REPORT_COMPLETION_TABLE,
        "report/report_field_catalog_resolved.json",
    )
    surface_manifest_member = _first_member(member_set, _ALIGNED_SURFACE_MANIFEST, "surface_manifest.json")
    report_completion_status = (
        result.get("report_completion_status", "")
        or (result.get("report_summary", {}) or {}).get("report_completion_status", "")
        or agreement.get("report_completion_status", "")
    )
    report_quality_gate_status = agreement.get("report_quality_gate_status", "")
    test_report_rc_status = agreement.get("test_report_rc_status", "")
    audit_report_rc_status = agreement.get("audit_report_rc_status", "")
    missing_report_field_count = (
        (result.get("report_summary", {}) or {}).get("missing_report_field_count", "")
        or agreement.get("missing_report_field_count", "")
        or _sum_missing(agreement)
    )
    required_missing_count = agreement.get("required_missing_count", "")
    recommended_missing_count = agreement.get("recommended_missing_count", "")
    final_selection_source = agreement.get("final_selection_source") or result.get("final_selection_source", "")
    finalization_status = result.get("finalization_status", "") or agreement.get("finalization_status", "")
    finalization_amendment_count = result.get("finalization_amendment_count", "") or agreement.get("finalization_amendment_count", "")
    reviewer_note_count = result.get("reviewer_note_count", "") or agreement.get("reviewer_note_count", "")
    report_override_count = (
        result.get("report_override_count", "")
        or (result.get("report_summary", {}) or {}).get("override_count", "")
        or agreement.get("report_override_count", "")
    )
    last_export_status = result.get("last_export_status", "")
    last_export_path = result.get("last_export_path", "")
    last_export_profile = result.get("last_export_profile", "")
    production_export_surface = _surface_status(surfaces, "production_export", bool(last_export_path))
    next_action = _next_action(
        report_completion_status=report_completion_status,
        required_missing_count=required_missing_count,
        recommended_missing_count=recommended_missing_count,
        finalization_status=finalization_status,
        last_export_path=last_export_path,
    )
    return {
        "schema_name": "output_review_view_model",
        "version": "0.1.0",
        "page_action_contract": wizard_page_action_contract("output"),
        "wizard_action_surface": wizard_action_surface_manifest(),
        "output_path": str(result.get("output_path") or result.get("mtda_path") or ""),
        "lanes": [
            _lane("test_report", "Test Report", "Formal method results and report-ready tables.", test_report_member in members),
            _lane("audit_report", "Audit Report", "Process-verification evidence for method execution and gates.", audit_report_member in members),
            _lane("workbench", "Method Development Workbench", "Deep operation-wise inspection for debugging.", bool(result.get("workbench_path")) or bool(workbench_member)),
            _lane("artifact_browser", "MTDA artifacts", "Archive outputs, manifest, provenance, checksums, and CSV evidence.", bool(members)),
            _lane(
                "report_completion",
                "Report completion",
                "Review missing report-only fields and recorded override provenance.",
                bool(report_completion_member),
            ),
            _lane(
                "finalization",
                "MTDA finalization",
                "Apply safe report-only or selection-only amendments without rerunning calculations.",
                bool(result.get("output_path") or result.get("mtda_path")),
            ),
            _lane(
                "production_export",
                "Production export",
                "Create shareable HTML, CSV, and Vega evidence bundles from the MTDA.",
                bool(last_export_path) or bool(result.get("output_path") or result.get("mtda_path")),
            ),
        ],
        "archive_member_count": len(members),
        "report_members": [
            member for member in members if member.startswith((MTDAAlignedLayout.reports_prefix, "report/"))
        ],
        "key_csvs": key_csvs,
        "key_artifacts": key_artifacts,
        "surface_members": {
            "test_report": test_report_member if test_report_member in members else "",
            "audit_report": audit_report_member if audit_report_member in members else "",
            "method_development_workbench": workbench_member,
        },
        "surface_manifest_available": bool(surface_manifest),
        "surface_statuses": {
            "test_report": _surface_status(surfaces, "test_report", test_report_member in members),
            "audit_report": _surface_status(surfaces, "audit_report", audit_report_member in members),
            "method_development_workbench": _surface_status(surfaces, "method_development_workbench", bool(workbench_member)),
            "production_export": production_export_surface,
        },
        "selection_summary": {
            "selection_set": agreement.get("final_selection_set") or result.get("final_selection_set", ""),
            "selection_source": final_selection_source,
            "selection_source_label": _selection_source_label(final_selection_source),
            "selected_run_count": agreement.get("selected_run_count", ""),
            "final_report_run_ids": agreement.get("final_report_run_ids", []),
            "discharged_run_count": agreement.get("discharged_run_count", ""),
            "human_override_count": agreement.get("human_override_count", result.get("human_override_count", "")),
            "definitions": _selection_definitions(),
        },
        "missing_field_summary": {
            "report_completion_status": report_completion_status,
            "report_completion_status_label": _human_status(report_completion_status),
            "missing_report_field_count": missing_report_field_count,
            "required_missing_count": required_missing_count,
            "recommended_missing_count": recommended_missing_count,
            "required_missing_label": _missing_count_label(required_missing_count, "required"),
            "recommended_missing_label": _missing_count_label(recommended_missing_count, "recommended"),
            "report_quality_gate_status": report_quality_gate_status,
            "report_quality_gate_status_label": _human_status(report_quality_gate_status),
            "test_report_rc_status": test_report_rc_status,
            "test_report_rc_status_label": _human_status(test_report_rc_status),
            "audit_report_rc_status": audit_report_rc_status,
            "audit_report_rc_status_label": _human_status(audit_report_rc_status),
            "action_hint": _completion_hint(required_missing_count, recommended_missing_count),
        },
        "export_summary": {
            "last_export_status": last_export_status,
            "last_export_status_label": _export_status_label(last_export_status, last_export_path),
            "last_export_path": last_export_path,
            "last_export_path_display": _display_path(last_export_path),
            "last_export_profile": last_export_profile,
            "last_export_profile_label": _export_profile_label(last_export_profile),
            "surface_status": production_export_surface.get("status", ""),
            "surface_status_label": production_export_surface.get("status_label", ""),
            "next_action": _export_next_action(last_export_path),
            "warnings": result.get("export_warnings", []),
        },
        "archive_state_summary": {
            "archive_state": _archive_state(finalization_status),
            "archive_state_label": _archive_state_label(finalization_status),
            "amendment_count": finalization_amendment_count,
            "reviewer_note_count": reviewer_note_count,
            "report_override_count": report_override_count,
            "export_ready": _is_export_ready(report_completion_status, finalization_status),
            "export_ready_label": _export_ready_label(report_completion_status, finalization_status),
            "next_recommended_action": next_action,
        },
        "status_summary": {
            "report_completion_status": report_completion_status,
            "report_completion_status_label": _human_status(report_completion_status),
            "test_report_rc_status": test_report_rc_status,
            "test_report_rc_status_label": _human_status(test_report_rc_status),
            "audit_report_rc_status": audit_report_rc_status,
            "audit_report_rc_status_label": _human_status(audit_report_rc_status),
            "report_quality_gate_status": report_quality_gate_status,
            "report_quality_gate_status_label": _human_status(report_quality_gate_status),
            "validation_status": result.get("validation_status", "") or agreement.get("validation_status", ""),
            "final_selection_source": final_selection_source,
            "final_selection_source_label": _selection_source_label(final_selection_source),
            "warning_count": result.get("warning_count", "") or agreement.get("warning_count", ""),
            "human_override_count": result.get("human_override_count", "") or agreement.get("human_override_count", ""),
            "missing_report_field_count": missing_report_field_count,
            "report_override_count": report_override_count,
            "finalization_status": finalization_status,
            "finalization_status_label": _archive_state_label(finalization_status),
            "finalization_amendment_count": finalization_amendment_count,
            "reviewer_note_count": reviewer_note_count,
            "last_export_status": last_export_status,
            "last_export_status_label": _export_status_label(last_export_status, last_export_path),
            "last_export_path": last_export_path,
            "next_recommended_action": next_action,
        },
        "actions": [
            {"action_id": "open_output_folder", "label": "Open output folder", "enabled": bool(result.get("output_path") or result.get("mtda_path"))},
            {"action_id": "open_test_report", "label": "Open Test Report", "enabled": test_report_member in members},
            {"action_id": "open_iso_report", "label": "Open ISO report", "enabled": test_report_member in members},
            {"action_id": "open_audit_report", "label": "Open Audit Report", "enabled": audit_report_member in members},
            {"action_id": "open_workbench", "label": "Open Method Development Workbench", "enabled": bool(result.get("workbench_path")) or bool(workbench_member)},
            {
                "action_id": "edit_report_completion",
                "label": "Review missing report fields",
                "enabled": bool(report_completion_member),
                "reason": _completion_hint(required_missing_count, recommended_missing_count),
            },
            {
                "action_id": "regenerate_report_only",
                "label": "Regenerate report only",
                "enabled": False,
                "reason": "Use MTDA finalization for safe post-run report-only amendments.",
            },
            {
                "action_id": "finalize_mtda",
                "label": "Record amendment / finalize MTDA",
                "enabled": bool(result.get("output_path") or result.get("mtda_path")),
                "reason": "Safe MTDA finalization supports report-only overrides and human selection decisions without rerunning method calculations.",
            },
            {
                "action_id": "export_production_bundle",
                "label": "Export production bundle",
                "enabled": bool(result.get("output_path") or result.get("mtda_path")),
            },
            {
                "action_id": "open_export_folder",
                "label": "Open export folder",
                "enabled": bool(result.get("last_export_path")),
            },
            {
                "action_id": "open_surface_manifest",
                "label": "Open surface manifest",
                "enabled": bool(surface_manifest) or bool(surface_manifest_member),
            },
        ],
    }


def _lane(lane_id: str, title: str, role: str, available: bool) -> dict[str, Any]:
    status = "available" if available else "not_generated"
    return {
        "lane_id": lane_id,
        "title": title,
        "role": role,
        "available": available,
        "status": status,
        "status_label": _human_status(status),
        "next_action": "" if available else "Generate this artifact before review.",
    }


def _surface_status(surfaces: Mapping[str, Any], surface_id: str, fallback_available: bool) -> dict[str, Any]:
    payload = surfaces.get(surface_id)
    if isinstance(payload, Mapping):
        status = str(payload.get("status") or ("available" if fallback_available else "not_generated"))
        return {
            "status": status,
            "status_label": str(payload.get("status_label") or _human_status(status)),
            "role": str(payload.get("role") or ""),
            "label": str(payload.get("label") or surface_id),
            "html_member": str(payload.get("html_member") or ""),
            "json_member": str(payload.get("json_member") or ""),
            "rc_status": str(payload.get("rc_status") or ""),
        }
    status = "available" if fallback_available else "not_generated"
    return {
        "status": status,
        "status_label": _human_status(status),
        "role": "",
        "label": surface_id,
        "html_member": "",
        "json_member": "",
        "rc_status": "",
    }


def _first_member(members: set[str], *candidates: str) -> str:
    return next((member for member in candidates if member in members), "")


def _sum_missing(agreement: Mapping[str, Any]) -> object:
    required = agreement.get("required_missing_count", "")
    recommended = agreement.get("recommended_missing_count", "")
    try:
        return int(required) + int(recommended)
    except (TypeError, ValueError):
        return ""


def _human_status(value: object) -> str:
    code = str(value or "").strip()
    labels = {
        "": "",
        "available": "Available",
        "missing": "Missing",
        "not_generated": "Not generated",
        "COMPLETE": "Complete",
        "COMPLETE_WITH_WARNINGS": "Complete with warnings",
        "INCOMPLETE": "Incomplete",
        "RC_READY": "RC ready",
        "RC_WITH_WARNINGS": "RC ready with warnings",
        "RC_BLOCKED": "RC blocked",
        "pass": "Pass",
        "warn": "Warning",
        "fail": "Fail",
        "not_finalized": "Draft, not finalized",
        "finalized": "Finalized",
        "amended": "Amended",
        "external_or_not_recorded": "Not exported from this MTDA yet",
        "not_run": "Not exported yet",
        "exported": "Exported",
    }
    return labels.get(code, code.replace("_", " ").strip().capitalize())


def _selection_source_label(value: object) -> str:
    code = str(value or "").strip()
    labels = {
        "machine_default_confirmed": "Machine-selected report runs",
        "machine_acceptance": "Machine-selected report runs",
        "machine_default": "Machine-selected report runs",
        "human_final": "Human-confirmed final report runs",
        "human_override": "Human override",
    }
    return labels.get(code, _human_status(code))


def _selection_definitions() -> list[dict[str, str]]:
    return [
        {"term": "Selected runs", "definition": "Runs currently included by the machine acceptance policy."},
        {"term": "Excluded runs", "definition": "Runs kept in the archive but excluded from the default report set."},
        {"term": "Review-required runs", "definition": "Runs that need operator review before final reporting."},
        {"term": "Discharged runs", "definition": "Runs not used for report aggregation, with reasons preserved."},
        {"term": "Final report runs", "definition": "Runs used for the Test Report and aggregate statistics after any human decisions."},
    ]


def _missing_count_label(value: object, kind: str) -> str:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return ""
    if count == 0:
        return f"No {kind} report fields missing"
    return f"{count} {kind} report field{'s' if count != 1 else ''} missing"


def _completion_hint(required_missing: object, recommended_missing: object) -> str:
    required = _to_int(required_missing)
    recommended = _to_int(recommended_missing)
    if required > 0:
        return "Review missing required fields, then record report-only overrides or mark them not applicable before final issue."
    if recommended > 0:
        return "Recommended fields are missing. Add report-only overrides when the information is available, or finalize with warnings."
    return "No report fields need action before finalization."


def _archive_state(status: object) -> str:
    code = str(status or "").strip()
    if code in {"finalized", "amended"}:
        return code
    return "draft"


def _archive_state_label(status: object) -> str:
    code = str(status or "").strip()
    if code == "finalized":
        return "Finalized"
    if code == "amended":
        return "Amended"
    return "Draft, not finalized"


def _is_export_ready(completion_status: object, finalization_status: object) -> bool:
    if str(completion_status or "") == "INCOMPLETE":
        return False
    return str(finalization_status or "") in {"finalized", "amended"}


def _export_ready_label(completion_status: object, finalization_status: object) -> str:
    if str(completion_status or "") == "INCOMPLETE":
        return "Not export-ready: required report fields are missing"
    if str(finalization_status or "") not in {"finalized", "amended"}:
        return "Export can run, but finalization is still recommended"
    return "Export-ready"


def _next_action(
    *,
    report_completion_status: object,
    required_missing_count: object,
    recommended_missing_count: object,
    finalization_status: object,
    last_export_path: object,
) -> str:
    if _to_int(required_missing_count) > 0 or str(report_completion_status or "") == "INCOMPLETE":
        return "Review missing required report fields and record report-only amendments."
    if _to_int(recommended_missing_count) > 0 and str(finalization_status or "") not in {"finalized", "amended"}:
        return "Decide whether to add recommended metadata, then finalize the MTDA with warnings if needed."
    if str(finalization_status or "") not in {"finalized", "amended"}:
        return "Finalize the MTDA to lock the review state before distribution."
    if not str(last_export_path or ""):
        return "Export the production bundle for handoff."
    return "Open the export folder and review the shareable bundle."


def _export_status_label(status: object, path: object) -> str:
    if str(path or ""):
        return "Exported"
    return _human_status(status or "not_run")


def _export_profile_label(profile: object) -> str:
    code = str(profile or "").strip()
    labels = {
        "minimal": "Minimal",
        "figures": "Figures",
        "full_html": "Full HTML",
    }
    return labels.get(code, _human_status(code) if code else "")


def _export_next_action(path: object) -> str:
    return "Open export folder or rerun export if the handoff needs refreshing." if str(path or "") else "Run production export when the MTDA is ready for handoff."


def _to_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _display_path(value: object, *, max_chars: int = 72) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    keep = max(12, (max_chars - 3) // 2)
    return f"{text[:keep]}...{text[-keep:]}"
