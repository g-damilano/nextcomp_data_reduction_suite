from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markupsafe import Markup

from acceptance.human_decision import decisions_from_payload
from acceptance.selection_editor import SelectionEditor
from archives.core.checksums import build_checksums
from archives.core.csv_io import write_dict_rows
from archives.core.json_io import json_bytes
from archives.core.layouts import MTDAAlignedLayout, aggregate_member, metadata_member, report_member
from archives.mtda.surface_manifest import build_surface_manifest
from audit.method_development_report_builder import MethodDevelopmentReportBuilder
from html_renderer.context_models import MtdaFinalizationSectionContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_mtda_finalization_section
from mtda_finalization.amendment_ledger import build_amendment_record, ledger_with_record
from mtda_finalization.amendment_policy import AmendmentPolicy
from mtda_finalization.amendment_request import AmendmentRequest
from mtda_finalization.archive_state import MTDAArchiveState
from mtda_finalization.finalization_report import build_finalization_report
from mtda_finalization.mtda_rewriter import read_archive_files, write_archive_files
from mtda_finalization.recompute_planner import plan_recompute
from reporting.aggregate_statistics import build_aggregate_statistics
from reporting.completion.report_completion_status import report_completion_status
from reporting.completion.report_override import build_override_ledger, normalize_report_overrides
from reporting.core.report_document import ReportBlockDocument, ReportDocument, ReportSectionDocument
from reporting.curve_aggregation import build_aligned_curves, build_characteristic_points, build_feature_lines
from reporting.quality_gate import build_report_quality_gate
from reporting.renderers.html_renderer import HtmlRenderer


@dataclass(frozen=True, slots=True)
class FinalizationResult:
    status: str
    input_path: Path
    output_path: Path | None
    amendment_classes: tuple[str, ...]
    artifacts_updated: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    new_run_required: bool = False


@dataclass(frozen=True, slots=True)
class _MTDAMembers:
    aligned: bool
    manifest: str
    provenance: str
    checksums: str
    surface_manifest: str
    validation: str
    method_outputs: str
    test_report_json: str
    test_report_html: str
    iso_report_json: str
    iso_report_html: str
    audit_report_json: str
    audit_report_html: str
    interactive_audit_html: str
    report_values_csv: str
    missing_fields_csv: str
    completion_status_json: str
    field_overrides_json: str
    override_ledger_json: str
    report_document_json: str
    completion_table_csv: str
    final_report_runs_csv: str
    aggregate_statistics_csv: str
    aligned_curves_csv: str
    characteristic_points_csv: str
    feature_lines_csv: str
    individual_results_csv: str
    specimen_results_csv: str
    curve_family_csv: str
    boundary_resolution_json: str
    acceptance_report_json: str
    selection_sets_json: str
    selection_membership_csv: str
    human_decisions_json: str
    human_decisions_csv: str
    acceptance_override_ledger_json: str
    selection_sets_final_json: str
    selection_membership_final_csv: str
    workbench_trace_json: str
    workbench_html: str
    finalization_state_json: str
    finalization_ledger_json: str
    finalization_ledger_csv: str
    recompute_manifest_json: str
    finalization_report_json: str


class MTDAFinalizationService:
    def __init__(self, policy: AmendmentPolicy | None = None) -> None:
        self.policy = policy or AmendmentPolicy()

    def load_state(self, path: str | Path) -> MTDAArchiveState:
        return MTDAArchiveState.load(path)

    def finalize(
        self,
        *,
        input_path: str | Path,
        request: AmendmentRequest,
        output_path: str | Path | None = None,
        in_place: bool = False,
    ) -> FinalizationResult:
        source = Path(input_path)
        decision = self.policy.classify(request)
        if not decision.accepted:
            return FinalizationResult(
                status="rejected_new_run_required",
                input_path=source,
                output_path=None,
                amendment_classes=decision.amendment_classes,
                errors=tuple(decision.rejected_reasons),
                new_run_required=decision.new_run_required,
            )
        target = Path(output_path) if output_path else source if in_place else source.with_name(f"{source.stem}_finalized{source.suffix}")
        files = read_archive_files(source)
        members = _member_layout(files)
        before_state = MTDAArchiveState.load(source)
        recompute_manifest = plan_recompute(decision, aligned=members.aligned)
        updated: set[str] = set()

        if request.report_overrides:
            updated.update(_apply_report_overrides(files, request.report_overrides, members))
        if request.human_decisions:
            updated.update(_apply_human_decisions(files, request.human_decisions, members))

        updated.update(_update_audit(files, request, members))
        updated.update(_append_finalization(files, before_state, request, recompute_manifest, members))
        updated.update(_update_workbench(files, members))
        updated.update(_update_manifest(files, request, members))
        updated.update(_append_provenance(files, request, recompute_manifest, members))
        updated.update(_update_report_quality_gate(files, members))
        files[members.surface_manifest] = json_bytes(build_surface_manifest(files))
        updated.add(members.surface_manifest)
        files[members.checksums] = json_bytes(build_checksums(files, checksum_member=members.checksums))
        updated.add(members.checksums)

        write_archive_files(target, files)
        return FinalizationResult(
            status="finalized",
            input_path=source,
            output_path=target,
            amendment_classes=decision.amendment_classes,
            artifacts_updated=tuple(sorted(updated)),
            errors=(),
            new_run_required=False,
        )


def _member_layout(files: dict[str, bytes]) -> _MTDAMembers:
    if MTDAAlignedLayout.manifest in files:
        finalization = "finalization/"
        return _MTDAMembers(
            aligned=True,
            manifest=MTDAAlignedLayout.manifest,
            provenance=MTDAAlignedLayout.provenance,
            checksums=MTDAAlignedLayout.checksums,
            surface_manifest=MTDAAlignedLayout.surface_manifest,
            validation=MTDAAlignedLayout.validation,
            method_outputs=MTDAAlignedLayout.method_outputs,
            test_report_json=report_member("test_report.json"),
            test_report_html=report_member("test_report.html"),
            iso_report_json="",
            iso_report_html="",
            audit_report_json=report_member("audit_report.json"),
            audit_report_html=report_member("audit_report.html"),
            interactive_audit_html="",
            report_values_csv="",
            missing_fields_csv=aggregate_member("missing_metadata_table.csv"),
            completion_status_json="",
            field_overrides_json="",
            override_ledger_json="",
            report_document_json="",
            completion_table_csv=aggregate_member("report_completion_table.csv"),
            final_report_runs_csv=aggregate_member("run_decision_registry.csv"),
            aggregate_statistics_csv=aggregate_member("statistics.csv"),
            aligned_curves_csv=aggregate_member("stress_strain_aligned.csv"),
            characteristic_points_csv=aggregate_member("characteristic_points.csv"),
            feature_lines_csv=aggregate_member("feature_lines.csv"),
            individual_results_csv=aggregate_member("results_table.csv"),
            specimen_results_csv="",
            curve_family_csv="",
            boundary_resolution_json="",
            acceptance_report_json="",
            selection_sets_json="",
            selection_membership_csv="",
            human_decisions_json="",
            human_decisions_csv="",
            acceptance_override_ledger_json="",
            selection_sets_final_json="",
            selection_membership_final_csv="",
            workbench_trace_json="",
            workbench_html="",
            finalization_state_json=metadata_member(finalization + "archive_state.json"),
            finalization_ledger_json=metadata_member(finalization + "amendment_ledger.json"),
            finalization_ledger_csv=metadata_member(finalization + "amendment_ledger.csv"),
            recompute_manifest_json=metadata_member(finalization + "recompute_manifest.json"),
            finalization_report_json=metadata_member(finalization + "finalization_report.json"),
        )
    return _MTDAMembers(
        aligned=False,
        manifest="manifest.json",
        provenance="provenance.json",
        checksums="checksums.json",
        surface_manifest="surface_manifest.json",
        validation="validation/validation_report.json",
        method_outputs="",
        test_report_json="report/test_report.json",
        test_report_html="report/test_report.html",
        iso_report_json="report/iso14126_report.json",
        iso_report_html="report/iso14126_report.html",
        audit_report_json="audit/audit_report.json",
        audit_report_html="audit/audit_report.html",
        interactive_audit_html="interactive_report/index.html",
        report_values_csv="report/report_values_used.csv",
        missing_fields_csv="report/missing_report_fields.csv",
        completion_status_json="report/report_completion_status.json",
        field_overrides_json="report/report_field_overrides.json",
        override_ledger_json="report/report_override_ledger.json",
        report_document_json="report/report_document.json",
        completion_table_csv="report/report_completeness_summary.csv",
        final_report_runs_csv="acceptance/final_report_runs.csv",
        aggregate_statistics_csv="report/aggregate_statistics.csv",
        aligned_curves_csv="report/aligned_curves.csv",
        characteristic_points_csv="report/characteristic_points.csv",
        feature_lines_csv="report/feature_lines.csv",
        individual_results_csv="report/individual_results.csv",
        specimen_results_csv="method_outputs/specimen_results.csv",
        curve_family_csv="method_outputs/curves/stress_strain_family.csv",
        boundary_resolution_json="audit/boundary_resolution.json",
        acceptance_report_json="acceptance/acceptance_report.json",
        selection_sets_json="acceptance/selection_sets.json",
        selection_membership_csv="acceptance/selection_membership.csv",
        human_decisions_json="acceptance/human_decisions.json",
        human_decisions_csv="acceptance/human_decisions.csv",
        acceptance_override_ledger_json="acceptance/override_ledger.json",
        selection_sets_final_json="acceptance/selection_sets_final.json",
        selection_membership_final_csv="acceptance/selection_membership_final.csv",
        workbench_trace_json="workbench/operation_trace.json",
        workbench_html="workbench/index.html",
        finalization_state_json="finalization/archive_state.json",
        finalization_ledger_json="finalization/amendment_ledger.json",
        finalization_ledger_csv="finalization/amendment_ledger.csv",
        recompute_manifest_json="finalization/recompute_manifest.json",
        finalization_report_json="finalization/finalization_report.json",
    )


def _apply_report_overrides(files: dict[str, bytes], payloads: tuple[dict[str, Any], ...], members: _MTDAMembers) -> set[str]:
    updated: set[str] = set()
    overrides = normalize_report_overrides(list(payloads))
    values = _report_values_used(files, members)
    missing = _missing_report_fields(files, members)
    values_by_key = {str(row.get("field_key") or row.get("field")): row for row in values}
    missing_by_key = {str(row.get("field_key") or row.get("field")): row for row in missing}
    for override in overrides:
        existing = values_by_key.get(override.field_key, {})
        missing_row = missing_by_key.get(override.field_key, {})
        row = {
            **missing_row,
            **existing,
            "field": existing.get("field") or missing_row.get("field") or override.field_key,
            "field_key": override.field_key,
            "value": override.value,
            "status": "present",
            "source": "report_override",
            "source_type": "report_override",
            "source_path": f"report_overrides.{override.field_key}",
            "report_importance": existing.get("report_importance") or missing_row.get("report_importance", ""),
            "section": override.section or existing.get("section") or missing_row.get("section_id", ""),
        }
        values_by_key[override.field_key] = row
        missing_by_key.pop(override.field_key, None)
    values_rows = list(values_by_key.values())
    missing_rows = list(missing_by_key.values())
    completion = _finalized_report_completion_status(missing_rows)
    override_rows = [override.to_dict() for override in overrides]
    override_payload = {
        "schema_id": "report.field_overrides.v0_1",
        "overrides": override_rows,
    }
    ledger = build_override_ledger(overrides)
    if members.aligned:
        existing_report = _json_member(files, members.test_report_json)
        files[members.missing_fields_csv] = write_dict_rows(missing_rows).encode("utf-8")
        files[members.completion_table_csv] = write_dict_rows(
            _updated_completion_rows(_csv_member(files, members.completion_table_csv), existing_report, missing_rows)
        ).encode("utf-8")
        _update_test_report_json(
            files,
            members,
            report_values_used=values_rows,
            missing_report_fields=missing_rows,
            report_completion_status=completion,
            report_field_overrides=override_rows,
            report_override_ledger=ledger,
        )
        _inject_html_notice(files, members.test_report_html, "Report Finalization", _report_override_notice(overrides, completion))
        updated.update(
            {
                members.missing_fields_csv,
                members.completion_table_csv,
                members.test_report_json,
                members.test_report_html,
            }
        )
    else:
        files[members.report_values_csv] = write_dict_rows(values_rows).encode("utf-8")
        files[members.missing_fields_csv] = write_dict_rows(missing_rows).encode("utf-8")
        files[members.completion_status_json] = json_bytes(completion)
        files[members.field_overrides_json] = json_bytes(override_payload)
        files[members.override_ledger_json] = json_bytes(ledger)
        _update_test_report_json(
            files,
            members,
            report_values_used=values_rows,
            missing_report_fields=missing_rows,
            report_completion_status=completion,
            report_field_overrides=override_payload,
            report_override_ledger=ledger,
        )
        _update_report_document_and_html(files, members, values_rows=values_rows, missing_rows=missing_rows, completion=completion)
        _inject_html_notice(files, members.test_report_html, "Report Finalization", _report_override_notice(overrides, completion))
        updated.update(
            {
                members.report_values_csv,
                members.missing_fields_csv,
                members.completion_status_json,
                members.field_overrides_json,
                members.override_ledger_json,
                members.report_document_json,
                members.test_report_json,
                members.test_report_html,
            }
        )
    if members.iso_report_html and members.iso_report_html in files:
        _inject_html_notice(files, members.iso_report_html, "Report Finalization", _report_override_notice(overrides, completion))
        updated.add(members.iso_report_html)
    if members.iso_report_json and members.iso_report_json in files:
        _update_json_member(files, members.iso_report_json, {"report_completion_status": completion, "report_values_used": values_rows, "missing_report_fields": missing_rows})
        updated.add(members.iso_report_json)
    return updated


def _apply_human_decisions(files: dict[str, bytes], payloads: tuple[dict[str, Any], ...], members: _MTDAMembers) -> set[str]:
    updated: set[str] = set()
    method_outputs = _method_outputs(files, members)
    specimen_results = _method_output_rows(files, members, "specimen_results", members.specimen_results_csv)
    acceptance_report = _method_output_object(files, members, "acceptance_report", members.acceptance_report_json)
    selection_sets = _method_output_object(files, members, "selection_sets", members.selection_sets_json)
    selection_membership = _method_output_rows(files, members, "selection_membership", members.selection_membership_csv)
    final = SelectionEditor().apply(
        specimen_results=specimen_results,
        acceptance_report=acceptance_report,
        machine_selection_sets=selection_sets,
        machine_selection_membership=selection_membership,
        decisions=decisions_from_payload(list(payloads)),
    )
    final_run_ids = set(final.final_run_ids)
    curve_family = _method_output_rows(files, members, "curve_family", members.curve_family_csv)
    report_payload = _json_member(files, members.test_report_json)
    curve_policy = report_payload.get("alignment_policy") if isinstance(report_payload.get("alignment_policy"), dict) else {}
    alignment = curve_policy.get("alignment") if isinstance(curve_policy.get("alignment"), dict) else {}
    boundary_payload = _method_output_value(files, members, "experiment_boundaries", members.boundary_resolution_json)
    boundary_records = (
        boundary_payload
        if isinstance(boundary_payload, list)
        else boundary_payload.get("records", []) if isinstance(boundary_payload.get("records"), list) else []
    )
    aggregate = build_aggregate_statistics(specimen_results, selection_run_ids=final_run_ids, selection_set="final_report_runs")
    aligned = build_aligned_curves(
        curve_family,
        specimen_results,
        selection_run_ids=final_run_ids,
        selection_set="final_report_runs",
        alignment_policy=str(curve_policy.get("alignment_policy") or "experiment_progress"),
        alignment=alignment if isinstance(alignment, dict) else None,
        boundary_records=boundary_records,
    )
    characteristic = build_characteristic_points(specimen_results, aggregate, selection_run_ids=final_run_ids, selection_set="final_report_runs")
    feature = build_feature_lines(aggregate, selection_set="final_report_runs")
    individual = _individual_results_with_final_selection(_csv_member(files, members.individual_results_csv), final_run_ids)
    if not individual:
        individual = _individual_results_with_final_selection(specimen_results, final_run_ids)
    if members.aligned:
        method_outputs.update(
            {
                "human_decisions": final.human_decisions,
                "human_decision_rows": final.human_decision_rows,
                "override_ledger": final.override_ledger,
                "override_ledger_rows": final.override_ledger_rows,
                "selection_sets_final": final.selection_sets_final,
                "selection_membership_final": final.selection_membership_final,
                "final_report_runs": final.final_report_runs,
            }
        )
        files[members.method_outputs] = json_bytes(method_outputs)
        files[members.final_report_runs_csv] = write_dict_rows(_run_decision_rows(final.final_report_runs, files, members)).encode("utf-8")
    else:
        files[members.human_decisions_json] = json_bytes(final.human_decisions)
        files[members.human_decisions_csv] = write_dict_rows(final.human_decision_rows).encode("utf-8")
        files[members.acceptance_override_ledger_json] = json_bytes(final.override_ledger)
        files[members.selection_sets_final_json] = json_bytes(final.selection_sets_final)
        files[members.selection_membership_final_csv] = write_dict_rows(final.selection_membership_final).encode("utf-8")
        files[members.final_report_runs_csv] = write_dict_rows(final.final_report_runs).encode("utf-8")
    files[members.aggregate_statistics_csv] = write_dict_rows(aggregate).encode("utf-8")
    files[members.aligned_curves_csv] = write_dict_rows(aligned).encode("utf-8")
    files[members.characteristic_points_csv] = write_dict_rows(characteristic).encode("utf-8")
    files[members.feature_lines_csv] = write_dict_rows(feature).encode("utf-8")
    files[members.individual_results_csv] = write_dict_rows(individual).encode("utf-8")
    _update_test_report_json(
        files,
        members,
        selection_set="final_report_runs",
        selection_source=final.selection_source,
        aggregate_statistics=aggregate,
        aligned_curves=aligned,
        aligned_curves_preview=aligned[:10],
        characteristic_points=characteristic,
        feature_lines=feature,
        individual_results=individual,
        summary={**_json_member(files, members.test_report_json).get("summary", {}), "selected_run_count": len(final_run_ids)},
    )
    _inject_html_notice(files, members.test_report_html, "Selection Finalization", f"Final report runs: {len(final_run_ids)}; selection source: {final.selection_source}.")
    updated.update(
        {
            members.final_report_runs_csv,
            members.aggregate_statistics_csv,
            members.aligned_curves_csv,
            members.characteristic_points_csv,
            members.feature_lines_csv,
            members.individual_results_csv,
            members.test_report_json,
            members.test_report_html,
        }
    )
    if members.aligned:
        updated.add(members.method_outputs)
    else:
        updated.update(
            {
                members.human_decisions_json,
                members.human_decisions_csv,
                members.acceptance_override_ledger_json,
                members.selection_sets_final_json,
                members.selection_membership_final_csv,
            }
    )
    return updated


def _method_outputs(files: dict[str, bytes], members: _MTDAMembers) -> dict[str, Any]:
    if not members.aligned:
        return {}
    payload = _json_member(files, members.method_outputs)
    return payload if isinstance(payload, dict) else {}


def _method_output_value(files: dict[str, bytes], members: _MTDAMembers, key: str, fallback_member: str = "") -> Any:
    if members.aligned:
        return _method_outputs(files, members).get(key)
    if fallback_member.endswith(".json"):
        return _json_member(files, fallback_member)
    if fallback_member.endswith(".csv"):
        return _csv_member(files, fallback_member)
    return None


def _method_output_object(files: dict[str, bytes], members: _MTDAMembers, key: str, fallback_member: str = "") -> dict[str, Any]:
    value = _method_output_value(files, members, key, fallback_member)
    return value if isinstance(value, dict) else {}


def _method_output_rows(files: dict[str, bytes], members: _MTDAMembers, key: str, fallback_member: str = "") -> list[dict[str, Any]]:
    value = _method_output_value(files, members, key, fallback_member)
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _report_values_used(files: dict[str, bytes], members: _MTDAMembers) -> list[dict[str, Any]]:
    report = _json_member(files, members.test_report_json)
    values = report.get("report_values_used")
    if isinstance(values, list):
        return [row for row in values if isinstance(row, dict)]
    return _csv_member(files, members.report_values_csv)


def _missing_report_fields(files: dict[str, bytes], members: _MTDAMembers) -> list[dict[str, Any]]:
    report = _json_member(files, members.test_report_json)
    missing = report.get("missing_report_fields")
    if isinstance(missing, list):
        return [row for row in missing if isinstance(row, dict)]
    return _csv_member(files, members.missing_fields_csv)


def _report_completion(files: dict[str, bytes], members: _MTDAMembers) -> dict[str, Any]:
    report = _json_member(files, members.test_report_json)
    completion = report.get("report_completion_status")
    if isinstance(completion, dict):
        return completion
    return _json_member(files, members.completion_status_json)


def _report_field_overrides(files: dict[str, bytes], members: _MTDAMembers) -> Any:
    report = _json_member(files, members.test_report_json)
    overrides = report.get("report_field_overrides")
    if isinstance(overrides, (dict, list)):
        return overrides
    return _json_member(files, members.field_overrides_json)


def _report_override_ledger(files: dict[str, bytes], members: _MTDAMembers) -> dict[str, Any]:
    report = _json_member(files, members.test_report_json)
    ledger = report.get("report_override_ledger")
    if isinstance(ledger, dict):
        return ledger
    return _json_member(files, members.override_ledger_json)


def _human_decisions(files: dict[str, bytes], members: _MTDAMembers) -> dict[str, Any]:
    if members.aligned:
        payload = _method_outputs(files, members).get("human_decisions")
        return payload if isinstance(payload, dict) else {"schema_id": "method.human_acceptance_decisions.v0_1", "decisions": []}
    return _json_member(files, members.human_decisions_json)


def _final_selection_sets(files: dict[str, bytes], members: _MTDAMembers) -> dict[str, Any]:
    if members.aligned:
        payload = _method_outputs(files, members).get("selection_sets_final")
        if isinstance(payload, dict):
            return payload
        decision_rows = _csv_member(files, members.final_report_runs_csv)
        selected = [str(row.get("run_id") or "") for row in decision_rows if _truthy(row.get("included", row.get("final_included", True)))]
        return {
            "schema_id": "method.selection_sets_final.v0_1",
            "default_selection_set": "final_report_runs",
            "selection_source": "machine_default_confirmed",
            "selection_sets": [{"selection_id": "final_report_runs", "run_ids": selected}],
        }
    return _json_member(files, members.selection_sets_final_json)


def _updated_completion_rows(
    existing_rows: list[dict[str, Any]],
    report: dict[str, Any],
    missing_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    missing_by_section: dict[str, list[dict[str, Any]]] = {}
    for row in missing_rows:
        section_id = str(row.get("section_id") or row.get("section") or "unsectioned")
        missing_by_section.setdefault(section_id, []).append(row)

    field_counts = {
        str(row.get("section_id") or "unsectioned"): 0
        for row in existing_rows
    }
    for entry in report.get("report_field_catalog_resolved", []) if isinstance(report.get("report_field_catalog_resolved"), list) else []:
        if isinstance(entry, dict):
            field_counts[str(entry.get("section_id") or "unsectioned")] = field_counts.get(str(entry.get("section_id") or "unsectioned"), 0) + 1

    rows = existing_rows or [
        {"section_id": section_id, "title": section_id.replace("_", " ").title(), "field_count": field_counts.get(section_id, 0)}
        for section_id in sorted({*field_counts, *missing_by_section})
    ]
    updated: list[dict[str, Any]] = []
    for row in rows:
        section_id = str(row.get("section_id") or "unsectioned")
        missing = missing_by_section.get(section_id, [])
        required = [
            item
            for item in missing
            if str(item.get("report_importance") or item.get("requirement_level") or item.get("severity")).casefold()
            in {"required", "execution_critical", "critical"}
        ]
        recommended = [item for item in missing if item not in required]
        status = "incomplete" if required else "complete_with_warnings" if recommended else "complete"
        updated.append(
            {
                **row,
                "field_count": row.get("field_count") or field_counts.get(section_id, 0),
                "missing_field_count": len(missing),
                "missing_required_count": len(required),
                "missing_recommended_count": len(recommended),
                "missing_optional_count": 0,
                "status": status,
            }
        )
    return updated


def _run_decision_rows(final_report_runs: list[dict[str, Any]], files: dict[str, bytes], members: _MTDAMembers) -> list[dict[str, Any]]:
    existing_by_run = {str(row.get("run_id") or ""): row for row in _csv_member(files, members.final_report_runs_csv)}
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(final_report_runs, start=1):
        run_id = str(row.get("run_id") or "")
        existing = existing_by_run.get(run_id, {})
        included = row.get("included", row.get("final_included", ""))
        rows.append(
            {
                **existing,
                **row,
                "run_id": run_id,
                "run_label": existing.get("run_label") or f"run_{index:03d}",
                "included": included,
                "final_included": row.get("final_included", included),
                "selection_set": row.get("selection_set") or row.get("final_selection_set") or "final_report_runs",
                "selection_source": row.get("selection_source") or ("human_final" if row.get("human_decision") else existing.get("selection_source", "")),
                "decision": row.get("decision") or row.get("human_decision", ""),
                "reason": row.get("reason") or row.get("human_decision_reason") or row.get("override_reason", ""),
            }
        )
    return rows


def _finalized_report_completion_status(missing_rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_rows: list[dict[str, Any]] = []
    for row in missing_rows:
        if _is_standard_required_gap(row):
            status_rows.append(dict(row))
        else:
            status_rows.append({**row, "report_importance": "recommended", "requirement_level": "recommended", "severity": "recommended"})
    return report_completion_status(status_rows)


def _is_standard_required_gap(row: dict[str, Any]) -> bool:
    if str(row.get("report_importance") or row.get("requirement_level") or row.get("severity")).casefold() not in {
        "required",
        "execution_critical",
        "critical",
    }:
        return False
    if str(row.get("requirement_id") or "").startswith("iso14126.clause_9_9_failure_mode:"):
        return True
    field = str(row.get("field") or row.get("field_key") or "").strip()
    section = str(row.get("section_id") or row.get("section") or "").strip()
    return section == "failure_analysis" and field in {"primary_failure_mode", "failure_location"}


def _update_audit(files: dict[str, bytes], request: AmendmentRequest, members: _MTDAMembers) -> set[str]:
    updated: set[str] = set()
    audit = _json_member(files, members.audit_report_json)
    if audit:
        completion = _report_completion(files, members)
        final_sets = _final_selection_sets(files, members)
        human = _human_decisions(files, members)
        overrides = _report_field_overrides(files, members)
        override_count = (
            len(overrides.get("overrides", []))
            if isinstance(overrides, dict) and isinstance(overrides.get("overrides"), list)
            else len(overrides)
            if isinstance(overrides, list)
            else 0
        )
        audit.setdefault("report_completion", {}).update(
            {
                "status": completion.get("status", ""),
                "missing_field_count": completion.get("missing_field_count", 0),
                "override_count": override_count,
                "mtdp_mutated": False,
            }
        )
        audit.setdefault("acceptance", {}).update(
            {
                "final_selection_set": final_sets.get("default_selection_set", ""),
                "selection_source": final_sets.get("selection_source", audit.get("acceptance", {}).get("selection_source", "")),
            }
        )
        audit["human_overrides"] = {
            "decision_count": len(human.get("decisions", [])) if isinstance(human.get("decisions"), list) else 0,
            "decisions": human.get("decisions", []),
        }
        audit["mtda_finalization"] = {
            "status": "finalized",
            "reviewer": request.reviewer,
            "reason": request.reason,
            "mtdp_mutated": False,
        }
        files[members.audit_report_json] = json_bytes(audit)
        updated.add(members.audit_report_json)
    notice = f"Finalized by {request.reviewer or 'operator'}; reason: {request.reason or 'not specified'}. MTDP mutated: false."
    for member in (members.audit_report_html, members.interactive_audit_html):
        if member in files:
            _update_audit_finalization_copy(files, member, notice)
            _inject_html_notice(files, member, "MTDA Finalization", notice, projection_plane=ProjectionPlane.AUDIT)
            updated.add(member)
    return updated


def _update_workbench(files: dict[str, bytes], members: _MTDAMembers) -> set[str]:
    if members.aligned:
        method_outputs = _method_outputs(files, members)
        trace = method_outputs.get("operation_trace") if isinstance(method_outputs.get("operation_trace"), dict) else {}
        if not trace:
            return set()
        trace["report_completion"] = _report_completion(files, members)
        trace["report_values_used"] = _report_values_used(files, members)
        trace["missing_report_fields"] = _missing_report_fields(files, members)
        trace["report_overrides"] = _report_field_overrides(files, members)
        trace["report_override_ledger"] = _report_override_ledger(files, members)
        trace["finalization"] = {
            "archive_state": _json_member(files, members.finalization_state_json),
            "amendment_ledger": _json_member(files, members.finalization_ledger_json),
            "finalization_report": _json_member(files, members.finalization_report_json),
        }
        method_outputs["operation_trace"] = trace
        files[members.method_outputs] = json_bytes(method_outputs)
        return {members.method_outputs}

    trace = _json_member(files, members.workbench_trace_json)
    if not trace:
        return set()
    trace["report_completion"] = _report_completion(files, members)
    trace["report_values_used"] = _report_values_used(files, members)
    trace["missing_report_fields"] = _missing_report_fields(files, members)
    trace["report_overrides"] = _report_field_overrides(files, members)
    trace["report_override_ledger"] = _report_override_ledger(files, members)
    trace["finalization"] = {
        "archive_state": _json_member(files, members.finalization_state_json),
        "amendment_ledger": _json_member(files, members.finalization_ledger_json),
        "finalization_report": _json_member(files, members.finalization_report_json),
    }
    files[members.workbench_trace_json] = json_bytes(trace)
    files[members.workbench_html] = MethodDevelopmentReportBuilder().build(trace).encode("utf-8")
    return {members.workbench_trace_json, members.workbench_html}


def _append_finalization(
    files: dict[str, bytes],
    state: MTDAArchiveState,
    request: AmendmentRequest,
    recompute_manifest: dict[str, Any],
    members: _MTDAMembers,
) -> set[str]:
    existing_ledger = _json_member(files, members.finalization_ledger_json)
    amendment_id = f"amendment_{len(existing_ledger.get('records', []) if isinstance(existing_ledger.get('records'), list) else []) + 1:03d}"
    record = build_amendment_record(
        amendment_id=amendment_id,
        classes=tuple(recompute_manifest.get("amendment_classes", [])),
        reviewer=request.reviewer,
        reason=request.reason,
        source_surface=request.source_surface,
        affected_artifacts=list(recompute_manifest.get("regenerated_artifacts", [])),
    )
    ledger = ledger_with_record(existing_ledger, record)
    completion = _report_completion(files, members)
    final_sets = _final_selection_sets(files, members)
    state_payload = {
        **state.to_dict(),
        "archive_state": "finalized",
        "finalized_by": request.reviewer,
        "finalization_reason": request.reason,
        "mtdp_mutated": False,
    }
    report = build_finalization_report(
        archive_state=state_payload,
        amendment_record=record,
        recompute_manifest=recompute_manifest,
        report_completion_status=completion,
        final_selection_source=str(final_sets.get("selection_source") or ""),
    )
    files[members.finalization_state_json] = json_bytes(state_payload)
    files[members.finalization_ledger_json] = json_bytes(ledger)
    files[members.finalization_ledger_csv] = write_dict_rows(ledger.get("records", [])).encode("utf-8")
    files[members.recompute_manifest_json] = json_bytes(recompute_manifest)
    files[members.finalization_report_json] = json_bytes(report)
    return {
        members.finalization_state_json,
        members.finalization_ledger_json,
        members.finalization_ledger_csv,
        members.recompute_manifest_json,
        members.finalization_report_json,
    }


def _update_manifest(files: dict[str, bytes], request: AmendmentRequest, members: _MTDAMembers) -> set[str]:
    manifest = _json_member(files, members.manifest)
    manifest["finalization"] = {
        "status": "finalized",
        "reviewer": request.reviewer,
        "reason": request.reason,
        "mtdp_mutated": False,
    }
    files[members.manifest] = json_bytes(manifest)
    return {members.manifest}


def _append_provenance(files: dict[str, bytes], request: AmendmentRequest, recompute_manifest: dict[str, Any], members: _MTDAMembers) -> set[str]:
    provenance = _json_member(files, members.provenance)
    events = provenance.get("events", []) if isinstance(provenance.get("events"), list) else []
    events.append(
        {
            "event": "mtda_amendments_applied",
            "reviewer": request.reviewer,
            "reason": request.reason,
            "amendment_classes": recompute_manifest.get("amendment_classes", []),
            "regenerated_artifacts": recompute_manifest.get("regenerated_artifacts", []),
            "mtdp_mutated": False,
        }
    )
    events.append(
        {
            "event": "mtda_finalized",
            "reviewer": request.reviewer,
            "reason": request.reason,
            "artifact": members.finalization_report_json,
            "mtdp_mutated": False,
        }
    )
    provenance["events"] = events
    files[members.provenance] = json_bytes(provenance)
    return {members.provenance}


def _update_report_quality_gate(files: dict[str, bytes], members: _MTDAMembers) -> set[str]:
    quality_gate = build_report_quality_gate(files)
    if members.aligned:
        validation = _json_member(files, members.validation)
        validation["report_quality_gate"] = quality_gate
        files[members.validation] = json_bytes(validation)
        return {members.validation}
    member = "report/report_quality_gate.json"
    files[member] = json_bytes(quality_gate)
    return {member}


def _update_test_report_json(files: dict[str, bytes], members: _MTDAMembers, **updates: Any) -> None:
    report = _json_member(files, members.test_report_json)
    for key, value in updates.items():
        report[key] = value
    files[members.test_report_json] = json_bytes(report)


def _update_report_document_and_html(
    files: dict[str, bytes],
    members: _MTDAMembers,
    *,
    values_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    completion: dict[str, Any],
) -> None:
    document = _json_member(files, members.report_document_json)
    if not document:
        return
    values_by_key = {str(row.get("field_key") or row.get("field") or ""): row for row in values_rows}
    missing_by_key = {str(row.get("field_key") or row.get("field") or ""): row for row in missing_rows}
    metadata = dict(document.get("metadata", {}) if isinstance(document.get("metadata"), dict) else {})
    metadata.update(
        {
            "missing_report_field_count": completion.get("missing_field_count", 0),
            "recommended_missing_count": completion.get("recommended_missing_count", 0),
            "required_missing_count": completion.get("required_missing_count", 0),
            "report_completion_status": completion.get("status", metadata.get("report_completion_status", "")),
        }
    )
    metadata["section_statuses"] = _updated_section_statuses(metadata.get("section_statuses", []), missing_rows)
    sections = []
    for section in document.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        blocks = []
        for block in section.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            data = block.get("data")
            if isinstance(data, list):
                data = [_updated_report_row(row, values_by_key, missing_by_key) if isinstance(row, dict) else row for row in data]
            blocks.append({**block, "data": data})
        sections.append({**section, "blocks": blocks})
    document = {**document, "metadata": metadata, "sections": sections}
    files[members.report_document_json] = json_bytes(document)
    files[members.test_report_html] = HtmlRenderer().render(_report_document_from_payload(document)).encode("utf-8")


def _updated_report_row(
    row: dict[str, Any],
    values_by_key: dict[str, dict[str, Any]],
    missing_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    key = str(row.get("field_key") or row.get("field") or row.get("key") or "")
    if key in values_by_key:
        value = values_by_key[key]
        return {
            **row,
            "value": value.get("value", row.get("value", "")),
            "status": value.get("status", "present"),
            "source_type": value.get("source_type", value.get("source", row.get("source_type", ""))),
            "source_path": value.get("source_path", row.get("source_path", "")),
        }
    if key in missing_by_key:
        return {**row, "value": "", "status": "missing"}
    return row


def _updated_section_statuses(statuses: Any, missing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_by_section: dict[str, list[dict[str, Any]]] = {}
    for row in missing_rows:
        section = str(row.get("section_id") or row.get("section") or "")
        missing_by_section.setdefault(section, []).append(row)
    updated: list[dict[str, Any]] = []
    for status in statuses or []:
        if not isinstance(status, dict):
            continue
        section_id = str(status.get("section_id") or "")
        rows = missing_by_section.get(section_id, [])
        required = [row for row in rows if str(row.get("report_importance") or row.get("requirement_level") or "") == "required"]
        recommended = [row for row in rows if str(row.get("report_importance") or row.get("requirement_level") or "") == "recommended"]
        state = "complete"
        if required:
            state = "incomplete"
        elif recommended:
            state = "complete_with_warnings"
        updated.append(
            {
                **status,
                "status": state,
                "missing_field_count": len(rows),
                "missing_required_count": len(required),
                "missing_recommended_count": len(recommended),
                "missing_fields": [str(row.get("field_key") or row.get("field") or "") for row in rows],
                "missing_fields_by_importance": {
                    "required": [str(row.get("field_key") or row.get("field") or "") for row in required],
                    "recommended": [str(row.get("field_key") or row.get("field") or "") for row in recommended],
                    "optional": [],
                    "none": [],
                },
            }
        )
    return updated


def _report_document_from_payload(payload: dict[str, Any]) -> ReportDocument:
    return ReportDocument(
        report_id=str(payload.get("report_id") or "test_report"),
        title=str(payload.get("title") or "Test Report"),
        metadata=dict(payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}),
        sections=[
            ReportSectionDocument(
                id=str(section.get("id") or ""),
                title=str(section.get("title") or ""),
                blocks=[
                    ReportBlockDocument(
                        id=str(block.get("id") or ""),
                        type=str(block.get("type") or ""),
                        title=str(block.get("title") or ""),
                        provider=str(block.get("provider") or ""),
                        data=block.get("data"),
                        config=dict(block.get("config", {}) if isinstance(block.get("config"), dict) else {}),
                    )
                    for block in section.get("blocks", []) or []
                    if isinstance(block, dict)
                ],
            )
            for section in payload.get("sections", []) or []
            if isinstance(section, dict)
        ],
        schema_id=str(payload.get("schema_id") or "report.document.v0_1"),
    )


def _update_json_member(files: dict[str, bytes], member: str, updates: dict[str, Any]) -> None:
    payload = _json_member(files, member)
    payload.update(updates)
    files[member] = json_bytes(payload)


def _inject_html_notice(
    files: dict[str, bytes],
    member: str,
    title: str,
    body: str,
    *,
    projection_plane: ProjectionPlane = ProjectionPlane.TEST,
) -> None:
    if member not in files:
        return
    text = files[member].decode("utf-8", errors="replace")
    section = _mtda_finalization_section(title, body, projection_plane=projection_plane)
    if "</main>" in text:
        text = text.replace("</main>", section + "</main>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", section + "</body>", 1)
    else:
        text += section
    files[member] = text.encode("utf-8")


def _mtda_finalization_section(
    title: str,
    body: str,
    *,
    projection_plane: ProjectionPlane = ProjectionPlane.TEST,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_mtda_finalization_section(title, body)
    return render_mtda_finalization_section(
        _mtda_finalization_section_context(title, body, projection_plane=projection_plane)
    )


def _legacy_mtda_finalization_section(title: str, body: str) -> str:
    return f"<section class=\"mtda-finalization\"><h2>{_escape(title)}</h2><p>{_escape(body)}</p></section>"


def _mtda_finalization_section_context(
    title: str,
    body: str,
    *,
    projection_plane: ProjectionPlane = ProjectionPlane.TEST,
) -> MtdaFinalizationSectionContext:
    return MtdaFinalizationSectionContext(
        projection_plane=projection_plane,
        recipe_result_kind=RecipeResultKind.MTDA_FINALIZATION_SECTION,
        title_html=Markup(_escape(title)),
        body_html=Markup(_escape(body)),
    )


def _update_audit_finalization_copy(files: dict[str, bytes], member: str, notice: str) -> None:
    text = files[member].decode("utf-8", errors="replace")
    replacements = {
        "Not finalized": "Finalized",
        "No post-run MTDA finalization amendments are recorded for this archive.": notice,
    }
    for old, new in replacements.items():
        text = text.replace(old, _escape(new) if old.startswith("No post-run") else new)
    files[member] = text.encode("utf-8")


def _report_override_notice(overrides: tuple[Any, ...], completion: dict[str, Any]) -> str:
    fields = ", ".join(
        f"{_display_field_key(override.field_key)}: {override.value}"
        for override in overrides
    )
    status = _display_status(completion.get("status", ""))
    return f"Applied report-only amendments for {fields}. Report completion: {status}."


def _display_field_key(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().title() or "Report field"


def _display_status(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().title() or "Not recorded"


def _individual_results_with_final_selection(rows: list[dict[str, Any]], final_run_ids: set[str]) -> list[dict[str, Any]]:
    updated = []
    for row in rows:
        run_id = str(row.get("run_id") or "")
        updated.append({**row, "included_in_selection": run_id in final_run_ids, "selection_set": "final_report_runs"})
    return updated


def _json_member(files: dict[str, bytes], member: str) -> dict[str, Any]:
    if not member:
        return {}
    try:
        payload = json.loads(files.get(member, b"{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _csv_member(files: dict[str, bytes], member: str) -> list[dict[str, Any]]:
    if not member:
        return []
    content = files.get(member)
    if not content:
        return []
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
