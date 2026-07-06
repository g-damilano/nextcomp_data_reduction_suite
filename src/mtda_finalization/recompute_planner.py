from __future__ import annotations

from typing import Any

from archives.core.layouts import MTDAAlignedLayout, aggregate_member, metadata_member, report_member
from mtda_finalization.amendment_policy import AmendmentDecision


def plan_recompute(decision: AmendmentDecision, *, aligned: bool = False) -> dict[str, Any]:
    classes = set(decision.amendment_classes)
    if aligned:
        artifacts: list[str] = [
            metadata_member("finalization/archive_state.json"),
            metadata_member("finalization/amendment_ledger.json"),
            metadata_member("finalization/amendment_ledger.csv"),
            metadata_member("finalization/recompute_manifest.json"),
            metadata_member("finalization/finalization_report.json"),
            MTDAAlignedLayout.provenance,
            MTDAAlignedLayout.checksums,
            MTDAAlignedLayout.manifest,
            MTDAAlignedLayout.surface_manifest,
            MTDAAlignedLayout.validation,
        ]
    else:
        artifacts = [
            "finalization/archive_state.json",
            "finalization/amendment_ledger.json",
            "finalization/amendment_ledger.csv",
            "finalization/recompute_manifest.json",
            "finalization/finalization_report.json",
            "provenance.json",
            "checksums.json",
            "manifest.json",
        ]
    if "report_only" in classes:
        artifacts.extend(_report_only_artifacts(aligned))
    if "selection_only" in classes:
        artifacts.extend(_selection_artifacts(aligned))
    return {
        "schema_id": "mtda.recompute_manifest.v0_1",
        "new_run_required": decision.new_run_required,
        "amendment_classes": list(decision.amendment_classes),
        "regenerated_artifacts": sorted(set(artifacts)),
        "method_artifacts_unchanged": _unchanged_method_artifacts(aligned),
    }


def _report_only_artifacts(aligned: bool) -> list[str]:
    if aligned:
        return [
            report_member("test_report.html"),
            report_member("test_report.json"),
            report_member("audit_report.html"),
            report_member("audit_report.json"),
            aggregate_member("missing_metadata_table.csv"),
            aggregate_member("report_completion_table.csv"),
            MTDAAlignedLayout.method_outputs,
        ]
    return [
        "report/report_field_overrides.json",
        "report/report_override_ledger.json",
        "report/report_values_used.csv",
        "report/missing_report_fields.csv",
        "report/report_completion_status.json",
        "report/test_report.html",
        "report/test_report.json",
        "audit/audit_report.html",
        "audit/audit_report.json",
    ]


def _selection_artifacts(aligned: bool) -> list[str]:
    if aligned:
        return [
            MTDAAlignedLayout.method_outputs,
            aggregate_member("run_decision_registry.csv"),
            aggregate_member("statistics.csv"),
            aggregate_member("characteristic_points.csv"),
            aggregate_member("feature_lines.csv"),
            aggregate_member("stress_strain_aligned.csv"),
            aggregate_member("results_table.csv"),
            report_member("test_report.html"),
            report_member("test_report.json"),
            report_member("audit_report.html"),
            report_member("audit_report.json"),
        ]
    return [
        "acceptance/human_decisions.json",
        "acceptance/human_decisions.csv",
        "acceptance/override_ledger.json",
        "acceptance/selection_sets_final.json",
        "acceptance/selection_membership_final.csv",
        "acceptance/final_report_runs.csv",
        "report/aggregate_statistics.csv",
        "report/characteristic_points.csv",
        "report/feature_lines.csv",
        "report/aligned_curves.csv",
        "report/individual_results.csv",
        "report/test_report.html",
        "report/test_report.json",
        "audit/audit_report.html",
        "audit/audit_report.json",
    ]


def _unchanged_method_artifacts(aligned: bool) -> list[str]:
    if aligned:
        return [
            f"{MTDAAlignedLayout.method_outputs}#operation_trace",
            f"{MTDAAlignedLayout.method_outputs}#specimen_results",
            f"{MTDAAlignedLayout.method_outputs}#curve_family",
            f"{MTDAAlignedLayout.validation}#validation_report",
        ]
    return [
        "audit/operation_log.json",
        "method_outputs/specimen_results.csv",
        "method_outputs/curves/stress_strain_family.csv",
        "validation/validation_report.json",
    ]
