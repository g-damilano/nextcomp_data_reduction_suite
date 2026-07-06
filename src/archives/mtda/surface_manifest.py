from __future__ import annotations

import csv
import io
import json
from typing import Any

from archives.core.layouts import MTDAAlignedLayout


def build_surface_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    """Build the operator-facing surface index from already materialized MTDA files."""

    if MTDAAlignedLayout.manifest in files:
        return _build_aligned_surface_manifest(files)

    if "software/manifest.json" in files or "index.html" in files:
        return _build_recommended_surface_manifest(files)

    names = set(files)
    report = _json_member(files, "report/test_report.json")
    audit = _json_member(files, "audit/audit_report.json")
    completion = _json_member(files, "report/report_completion_status.json")
    manifest = _json_member(files, "manifest.json")
    source = _json_member(files, "source_reference.json")
    finalization = _json_member(files, "finalization/archive_state.json")
    final_sets = _json_member(files, "acceptance/selection_sets_final.json")
    acceptance = _json_member(files, "acceptance/acceptance_report.json")
    human = _json_member(files, "acceptance/human_decisions.json")
    overrides = _json_member(files, "report/report_field_overrides.json")
    quality_gate = _json_member(files, "report/report_quality_gate.json")
    warnings = _json_any(files, "audit/warnings.json")
    final_report_runs = _csv_member(files, "acceptance/final_report_runs.csv")
    discharged_runs = _csv_member(files, "acceptance/discharged_runs.csv")

    readiness_status = str(_nested(audit, "readiness", "status") or "")
    validation_status = str(_nested(audit, "validation", "status") or "")
    finalization_status = str(finalization.get("archive_state") or _nested(manifest, "finalization", "status") or "not_finalized")
    report_completion_status = str(completion.get("status") or _nested(report, "report_completion_status", "status") or "")
    selected_run_ids = _selected_run_ids(final_report_runs)
    amendment_ledger = _json_member(files, "finalization/amendment_ledger.json")
    amendment_records = amendment_ledger.get("records", []) if isinstance(amendment_ledger.get("records"), list) else []
    reviewer_note_count = _reviewer_note_count(amendment_records)

    return {
        "schema_id": "mtda.surface_manifest.v0_1",
        "surfaces": {
            "test_report": {
                "surface_id": "test_report",
                "label": "Test Report",
                "role": "Formal method/result report.",
                "html_member": "report/test_report.html",
                "json_member": "report/test_report.json",
                "status": _availability("report/test_report.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "test_report", "rc_status") or "",
                "report_completion_status": report_completion_status,
                "required_missing_count": completion.get("required_missing_count", 0),
                "recommended_missing_count": completion.get("recommended_missing_count", 0),
                "missing_report_field_count": completion.get("missing_field_count", 0),
                "values_used_member": "report/report_values_used.csv",
                "missing_fields_member": "report/missing_report_fields.csv",
                "iso14126_resolve_checks_member": "report/iso14126_resolve_checks.json" if "report/iso14126_resolve_checks.json" in names else "",
                "aggregate_plot_member": "report/vega_specs/aggregate_stress_strain_mean_variability.json",
                "has_renderable_vega_plot": "report/vega_specs/aggregate_stress_strain_mean_variability.json" in names
                and "data-vega-block" in _text_member(files, "report/test_report.html"),
            },
            "audit_report": {
                "surface_id": "audit_report",
                "label": "Audit Report",
                "role": "Grouped ISO 14126 analysis evidence and traceability report.",
                "html_member": "audit/audit_report.html",
                "json_member": "audit/audit_report.json",
                "status": _availability("audit/audit_report.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "audit_report", "rc_status") or "",
                "readiness_status": readiness_status,
                "validation_status": validation_status,
                "acceptance_selection_source": _nested(audit, "acceptance", "selection_source") or "",
                "finalization_status": finalization_status,
                "warning_count": _warning_count(warnings),
                "procedure_evidence_index_member": "audit/procedure_evidence_index.json" if "audit/procedure_evidence_index.json" in names else "",
                "audit_blocks_member": "audit/audit_blocks.json" if "audit/audit_blocks.json" in names else "",
                "audit_block_index_member": "audit/audit_block_index.json" if "audit/audit_block_index.json" in names else "",
                "curve_diagnostic_report_member": "acceptance/curve_family/curve_diagnostic_report.json" if "acceptance/curve_family/curve_diagnostic_report.json" in names else "",
                "curve_diagnostic_scores_member": "acceptance/curve_family/curve_diagnostic_scores.csv" if "acceptance/curve_family/curve_diagnostic_scores.csv" in names else "",
            },
            "method_development_workbench": {
                "surface_id": "method_development_workbench",
                "label": "Method Development Workbench",
                "role": "Operation-level replay and debugging surface.",
                "html_member": "workbench/index.html",
                "trace_member": "workbench/operation_trace.json",
                "status": _availability("workbench/index.html", names),
            },
            "production_export": {
                "surface_id": "production_export",
                "label": "Production Export",
                "role": "External distribution bundle produced from this MTDA when exported.",
                "status": "external_or_not_recorded",
                "status_label": "Not exported from this MTDA yet",
                "operator_action": "Use the Production export action to create a shareable HTML/CSV/Vega bundle.",
                "manifest_member": "export/export_manifest.json" if "export/export_manifest.json" in names else "",
            },
        },
        "key_csv_artifacts": _present(
            names,
            [
                "acceptance/final_report_runs.csv",
                "acceptance/discharged_runs.csv",
                "acceptance/run_flags.csv",
                "validation/validation_summary.csv",
                "validation/deviations.csv",
                "readiness/readiness_summary.csv",
                "report/report_values_used.csv",
                "report/missing_report_fields.csv",
                "report/iso14126_resolve_checks.csv",
                "report/individual_results.csv",
                "report/aggregate_statistics.csv",
                "report/aligned_curves.csv",
                "method_outputs/dataset_summary_by_selection.csv",
                "method_outputs/boundaries.csv",
                "audit/boundary_events.csv",
                "acceptance/curve_family/curve_diagnostic_scores.csv",
                "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
                "acceptance/curve_family/curve_diagnostic_residuals.csv",
                "acceptance/curve_family/curve_diagnostic_flags.csv",
            ],
        ),
        "key_json_artifacts": _present(
            names,
            [
                "manifest.json",
                "source_reference.json",
                "provenance.json",
                "compatibility/schema_method_compatibility_report.json",
                "mapping/mapping_profile_used.json",
                "readiness/readiness_report.json",
                "validation/validation_report.json",
                "acceptance/acceptance_report.json",
                "acceptance/discharge_report.json",
                "acceptance/selection_sets_final.json",
                "report/report_completion_status.json",
                "report/report_quality_gate.json",
                "report/plot_data_freshness.json",
                "report/iso14126_resolve_checks.json",
                "audit/audit_report.json",
                "audit/procedure_evidence_index.json",
                "audit/audit_blocks.json",
                "audit/audit_block_index.json",
                "audit/boundary_resolution.json",
                "acceptance/curve_family/curve_diagnostic_report.json",
                "acceptance/curve_family/curve_diagnostic_policy.json",
                "workbench/operation_trace.json",
                "finalization/archive_state.json",
            ],
        )
        + ["checksums.json"],
        "cross_surface_agreement": {
            "source_package": _nested(source, "source_package", "path") or report.get("source_package") or _nested(audit, "source_mtdp", "path") or "",
            "source_schema_id": _nested(source, "source_package", "schema_id") or _nested(audit, "source_mtdp", "schema_id") or "",
            "source_schema_version": _nested(source, "source_package", "schema_version") or _nested(audit, "source_mtdp", "schema_version") or "",
            "method_id": manifest.get("method_id") or report.get("method_id") or _nested(audit, "method_package", "method_id") or "",
            "method_version": manifest.get("method_version") or report.get("method_version") or _nested(audit, "method_package", "version") or "",
            "mapping_id": report.get("mapping_id") or _nested(audit, "mapping_profile", "mapping_id") or _json_member(files, "mapping/mapping_profile_used.json").get("mapping_id") or "",
            "readiness_status": readiness_status,
            "validation_status": validation_status,
            "acceptance_default_selection_set": _nested(audit, "acceptance", "default_selection_set") or acceptance.get("default_selection_set") or "",
            "final_selection_set": final_sets.get("default_selection_set") or _nested(audit, "acceptance", "final_selection_set") or "",
            "final_selection_source": final_sets.get("selection_source") or _nested(audit, "acceptance", "selection_source") or "",
            "final_report_run_ids": selected_run_ids,
            "selected_run_count": len(selected_run_ids),
            "discharged_run_count": len(discharged_runs),
            "human_override_count": len(human.get("decisions", [])) if isinstance(human.get("decisions"), list) else 0,
            "report_override_count": len(overrides.get("overrides", [])) if isinstance(overrides.get("overrides"), list) else 0,
            "report_completion_status": report_completion_status,
            "report_completion_status_label": _human_status(report_completion_status),
            "report_quality_gate_status": quality_gate.get("overall_status", ""),
            "test_report_rc_status": _nested(quality_gate, "surfaces", "test_report", "rc_status") or "",
            "audit_report_rc_status": _nested(quality_gate, "surfaces", "audit_report", "rc_status") or "",
            "required_missing_count": completion.get("required_missing_count", 0),
            "recommended_missing_count": completion.get("recommended_missing_count", 0),
            "warning_count": _warning_count(warnings),
            "boundary_resolution_status": _nested(audit, "experiment_boundary_resolution", "status") or "",
            "bounded_reduction": _nested(audit, "experiment_boundary_resolution", "bounded_reduction") or False,
            "boundary_aligned_aggregation": _nested(audit, "experiment_boundary_resolution", "boundary_aligned_aggregation") or False,
            "finalization_status": finalization_status,
            "finalization_status_label": _human_status(finalization_status),
            "finalization_amendment_count": len(amendment_records),
            "reviewer_note_count": reviewer_note_count,
            "selection_source_label": _human_status(final_sets.get("selection_source") or _nested(audit, "acceptance", "selection_source") or ""),
        },
        "operator_handoff": {
            "open_test_report_member": "report/test_report.html",
            "open_audit_report_member": "audit/audit_report.html",
            "open_workbench_member": "workbench/index.html",
            "surface_roles": {
                "test_report": "Formal results.",
                "audit_report": "ISO analysis evidence.",
                "method_development_workbench": "Operation-level debug evidence.",
                "wizard": "Action, decision, and repair surface.",
                "mtda": "Archive backing all surfaces.",
            },
            "term_definitions": {
                "selected_runs": "Runs currently included by the machine acceptance policy.",
                "excluded_runs": "Runs kept in the archive but excluded from the default report set.",
                "review_required_runs": "Runs that need operator review before final reporting.",
                "discharged_runs": "Runs not used for report aggregation, with reasons preserved.",
                "final_report_runs": "Runs used for the Test Report and aggregate statistics after any human decisions.",
            },
            "next_action": _next_action(
                report_completion_status=report_completion_status,
                required_missing_count=completion.get("required_missing_count", 0),
                recommended_missing_count=completion.get("recommended_missing_count", 0),
                finalization_status=finalization_status,
            ),
        },
    }


def _build_aligned_surface_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    names = {
        *files,
        MTDAAlignedLayout.surface_manifest,
        MTDAAlignedLayout.checksums,
    }
    manifest = _json_member(files, MTDAAlignedLayout.manifest)
    dataset = _json_member(files, MTDAAlignedLayout.dataset)
    validation = _json_member(files, MTDAAlignedLayout.validation)
    readiness = _json_member(files, MTDAAlignedLayout.readiness)
    method_outputs = _json_member(files, MTDAAlignedLayout.method_outputs)
    report = _json_member(files, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    audit = _json_member(files, f"{MTDAAlignedLayout.reports_prefix}audit_report.json")
    dataset_plot_package = _json_member(files, f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json")
    decision_rows = _csv_member(files, f"{MTDAAlignedLayout.aggregate_prefix}run_decision_registry.csv")
    result_rows = _csv_member(files, f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv")
    run_surfaces = _aligned_run_surfaces(names, files)

    final_run_ids = [
        str(row.get("run_id") or "").strip()
        for row in decision_rows
        if str(row.get("run_id") or "").strip() and _truthy(row.get("included", True))
    ]
    if not final_run_ids:
        final_run_ids = [str(row.get("run_id") or "").strip() for row in result_rows if str(row.get("run_id") or "").strip()]

    validation_report = validation.get("validation_report") if isinstance(validation.get("validation_report"), dict) else {}
    readiness_report = readiness.get("readiness_report") if isinstance(readiness.get("readiness_report"), dict) else {}
    report_completion = report.get("report_completion_status") if isinstance(report.get("report_completion_status"), dict) else {}
    quality_gate = validation.get("report_quality_gate") if isinstance(validation.get("report_quality_gate"), dict) else {}

    return {
        "schema_id": "mtda.surface_manifest.v0_3",
        "layout_version": MTDAAlignedLayout.name,
        "surfaces": {
            "home": {
                "surface_id": "home",
                "label": "Home",
                "role": "Main aligned archive entry point.",
                "html_member": MTDAAlignedLayout.index,
                "status": _availability(MTDAAlignedLayout.index, names),
            },
            "dataset_plot": {
                "surface_id": "dataset_plot",
                "label": "Dataset Plot",
                "role": "Aggregate dataset plot studio and exploratory surface.",
                "html_member": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
                "plot_html_member": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
                "plot_package_member": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json",
                "plot_template_member": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.template.json",
                "plot_data_members": _compact_plot_data_members(names, f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot_data/"),
                "plot_data_views": _plot_data_views(dataset_plot_package),
                "projection_recipe": _plot_projection_metadata(dataset_plot_package),
                "export_semantics": _plot_export_semantics("dataset_plot"),
                "status": _availability(f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html", names),
            },
            "processed_data": {
                "surface_id": "processed_data",
                "label": "Processed Data",
                "role": "Run-level analysed data, summaries, and plot surfaces.",
                "status": "available" if run_surfaces else "missing",
                "run_count": len(run_surfaces),
            },
            "test_report": {
                "surface_id": "test_report",
                "label": "Formal Report",
                "role": "Formal method/result report.",
                "html_member": f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html",
                "raw_html_member": f"{MTDAAlignedLayout.reports_prefix}test_report.html",
                "pdf_member": f"{MTDAAlignedLayout.reports_prefix}test_report.pdf",
                "json_member": f"{MTDAAlignedLayout.reports_prefix}test_report.json",
                "status": _availability(f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "test_report", "rc_status") or "",
                "report_completion_status": report_completion.get("status", ""),
            },
            "audit_report": {
                "surface_id": "audit_report",
                "label": "Audit Report",
                "role": "Scientist-facing audit and endpoint evidence.",
                "html_member": f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html",
                "raw_html_member": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
                "json_member": f"{MTDAAlignedLayout.reports_prefix}audit_report.json",
                "csv_member": f"{MTDAAlignedLayout.reports_prefix}audit_report.csv",
                "status": _availability(f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "audit_report", "rc_status") or "",
                "readiness_status": readiness_report.get("status") or _nested(audit, "readiness", "status") or "",
                "validation_status": validation_report.get("status") or _nested(audit, "validation", "status") or "",
            },
            "metadata": {
                "surface_id": "metadata",
                "label": "Metadata",
                "role": "Archive contract, provenance, validation, readiness, and integrity metadata.",
                "manifest_member": MTDAAlignedLayout.manifest,
                "checksums_member": MTDAAlignedLayout.checksums,
                "status": _availability(MTDAAlignedLayout.manifest, names),
            },
        },
        "run_surfaces": run_surfaces,
        "key_csv_artifacts": _present(
            names,
            [
                f"{MTDAAlignedLayout.normalized_prefix}normalization_registry.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}characteristic_points.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}run_decision_registry.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}bending_summary_table.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}missing_metadata_table.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}report_completion_table.csv",
                f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot_manifest.csv",
                *_compact_plot_data_members(names, f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot_data/"),
                f"{MTDAAlignedLayout.reports_prefix}audit_report.csv",
                *[
                    member
                    for surface in run_surfaces
                    for member in [
                        *surface.get("csv_members", []),
                        *surface.get("plot_data_members", []),
                        surface.get("plot_manifest_member", ""),
                    ]
                    if member
                ],
            ],
        ),
        "key_json_artifacts": _present(
            names,
            [
                MTDAAlignedLayout.manifest,
                MTDAAlignedLayout.schema,
                MTDAAlignedLayout.dataset,
                MTDAAlignedLayout.provenance,
                MTDAAlignedLayout.surface_manifest,
                MTDAAlignedLayout.validation,
                MTDAAlignedLayout.readiness,
                MTDAAlignedLayout.method_outputs,
                MTDAAlignedLayout.checksums,
                f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json",
                f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.template.json",
                f"{MTDAAlignedLayout.reports_prefix}test_report.json",
                f"{MTDAAlignedLayout.reports_prefix}audit_report.json",
                *[surface.get("plot_package_member", "") for surface in run_surfaces if surface.get("plot_package_member")],
                *[surface.get("plot_template_member", "") for surface in run_surfaces if surface.get("plot_template_member")],
            ],
        ),
        "cross_surface_agreement": {
            "source_package": _nested(manifest, "source_package", "source_name") or manifest.get("source_package_name") or "",
            "source_schema_id": _nested(manifest, "source_package", "schema_id") or "",
            "source_schema_version": _nested(manifest, "source_package", "schema_version") or "",
            "method_id": manifest.get("method_id") or _nested(manifest, "method", "method_id") or report.get("method_id") or "",
            "method_version": manifest.get("method_version") or _nested(manifest, "method", "method_version") or report.get("method_version") or "",
            "readiness_status": readiness_report.get("status") or _nested(audit, "readiness", "status") or "",
            "validation_status": validation_report.get("status") or _nested(audit, "validation", "status") or "",
            "final_report_run_ids": final_run_ids,
            "selected_run_count": len(final_run_ids),
            "result_row_count": len(result_rows),
            "report_completion_status": report_completion.get("status", ""),
            "run_count": _nested(dataset, "run_counts", "run_count") or len(run_surfaces),
            "legacy_member_count": method_outputs.get("legacy_member_count", 0),
            "internal_checksum_member": MTDAAlignedLayout.checksums,
        },
        "operator_handoff": {
            "open_home_member": MTDAAlignedLayout.index,
            "open_dataset_plot_member": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
            "open_test_report_member": f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html",
            "open_audit_report_member": f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html",
            "open_surface_manifest_member": MTDAAlignedLayout.surface_manifest,
            "surface_roles": {
                "home": "Normal aligned archive entry point.",
                "dataset_plot": "Dataset-level plot studio and human exploration.",
                "processed_data": "Run-level summaries, CSVs, and plots.",
                "test_report": "Final formal report.",
                "audit_report": "Scientific audit evidence.",
                "metadata": "Machine reproducibility and integrity trace.",
            },
            "term_definitions": {
                "html": "Human view.",
                "csv": "Canonical tabular data.",
                "json": "Structured machine/reproducibility data.",
                "vega_spec": "Canonical editable plot definition.",
            },
            "next_action": "Extract the MTDA and open index.html for normal review.",
        },
    }


def _aligned_run_surfaces(names: set[str], files: dict[str, bytes]) -> list[dict[str, Any]]:
    run_surfaces: list[dict[str, Any]] = []
    for member in sorted(names):
        if not member.startswith(MTDAAlignedLayout.processed_prefix) or not member.endswith("_browser.html"):
            continue
        run_label = member.rsplit("/", 1)[-1].removesuffix("_browser.html")
        package_member = f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.plot_package.json"
        package = _json_member(files, package_member)
        run_surfaces.append(
            {
                "run_id": run_label,
                "run_label": run_label,
                "html_member": member,
                "browser_html_member": member,
                "plot_html_member": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.html",
                "plot_package_member": package_member,
                "plot_template_member": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.template.json",
                "plot_data_members": _compact_plot_data_members(
                    names,
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot_data/",
                ),
                "plot_data_views": _plot_data_views(package),
                "projection_recipe": _plot_projection_metadata(package),
                "plot_manifest_member": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot_manifest.csv",
                "export_semantics": _plot_export_semantics(f"{run_label}_plot"),
                "csv_members": [
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv",
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv",
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv",
                ],
                "status": _availability(member, names),
            }
        )
    return run_surfaces


def _compact_plot_data_members(names: set[str], prefix: str) -> list[str]:
    return sorted(member for member in names if member.startswith(prefix) and member.endswith(".csv"))


def _plot_data_views(package: dict[str, Any]) -> list[dict[str, Any]]:
    views = package.get("plot_data_views") if isinstance(package.get("plot_data_views"), list) else []
    surfaced_views: list[dict[str, Any]] = []
    for view in views:
        if not isinstance(view, dict):
            continue
        surfaced = {
            "dataset_id": str(view.get("dataset_id") or ""),
            "transform_id": str(view.get("transform_id") or ""),
            "source_members": [str(member) for member in view.get("source_members") or []],
            "fields": [str(field) for field in view.get("fields") or []],
            **({"expected_row_count": view.get("expected_row_count")} if view.get("expected_row_count") is not None else {}),
        }
        for key in (
            "data_view_schema_version",
            "data_view_version",
            "transform_version",
            "implementation",
            "source_checksum_policy",
            "source_checksum_member",
        ):
            if view.get(key) is not None:
                surfaced[key] = view.get(key)
        surfaced_views.append(surfaced)
    return surfaced_views


def _plot_projection_metadata(package: dict[str, Any]) -> dict[str, Any]:
    if not package:
        return {}
    recipe = package.get("projection_recipe") if isinstance(package.get("projection_recipe"), dict) else {}
    contracts = package.get("projection_contracts") if isinstance(package.get("projection_contracts"), dict) else {}
    semantic_contract = contracts.get("semantic_contract") if isinstance(contracts.get("semantic_contract"), dict) else {}
    return {
        "projection_id": str(package.get("projection_id") or recipe.get("projection_id") or ""),
        "plot_type": str(package.get("plot_type") or recipe.get("plot_type") or ""),
        "recipe_version": str(package.get("recipe_version") or recipe.get("version") or ""),
        "recipe_schema_version": str(package.get("recipe_schema_version") or recipe.get("schema_version") or ""),
        "golden_id": str(package.get("golden_id") or recipe.get("golden_id") or ""),
        "production_state": str(package.get("production_state") or recipe.get("production_state") or ""),
        "catalog_path": str(recipe.get("catalog_path") or ""),
        "semantic_contract_layer_ids": [
            str(layer.get("layer_id") or "")
            for layer in semantic_contract.get("layers") or []
            if isinstance(layer, dict) and layer.get("layer_id")
        ],
        "staleness_contract": contracts.get("staleness_contract") or {},
        "artifact_contract": contracts.get("artifact_contract") or {},
    }


def _plot_export_semantics(plot_id: str) -> dict[str, Any]:
    return {
        "settings_only": f"{plot_id}.settings_only.plot_profile.json",
        "data_only": f"{plot_id}.{{dataset_id}}.data_only.csv",
        "plot_image": [f"{plot_id}.svg", f"{plot_id}.png"],
        "plot_spec_hydrated_data": f"{plot_id}.full_vegalite_spec_with_data.vl.json",
        "compact_plot_package_data": f"{plot_id}.full_plot_package_with_data.json",
    }


def _availability(member: str, names: set[str]) -> str:
    return "available" if member in names else "missing"


def _present(names: set[str], members: list[str]) -> list[str]:
    return [member for member in members if member in names]


def _json_member(files: dict[str, bytes], member: str) -> dict[str, Any]:
    payload = _json_any(files, member)
    return payload if isinstance(payload, dict) else {}


def _json_any(files: dict[str, bytes], member: str) -> Any:
    try:
        payload = json.loads(files.get(member, b"{}"))
    except json.JSONDecodeError:
        return {}
    return payload


def _csv_member(files: dict[str, bytes], member: str) -> list[dict[str, Any]]:
    content = files.get(member)
    if not content:
        return []
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _text_member(files: dict[str, bytes], member: str) -> str:
    content = files.get(member)
    return content.decode("utf-8", errors="replace") if content else ""


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _selected_run_ids(final_report_runs: list[dict[str, Any]]) -> list[str]:
    run_ids: list[str] = []
    for row in final_report_runs:
        run_id = str(row.get("run_id") or "").strip()
        if run_id and _truthy(row.get("included", row.get("final_included", True))):
            run_ids.append(run_id)
    return run_ids


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _warning_count(warnings: Any) -> int:
    if isinstance(warnings, list):
        return len(warnings)
    if not isinstance(warnings, dict):
        return 0
    items = warnings.get("items")
    if isinstance(items, list):
        return len(items)
    count = warnings.get("count")
    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


def _build_recommended_surface_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    names = {*files, "archive_index.csv", "software/checksums.json", "software/surface_manifest.json"}
    report = _json_member(files, "report/test_report.json")
    audit = _json_member(files, "audit/audit_report.json")
    manifest = _json_member(files, "software/manifest.json")
    provenance = _json_member(files, "software/provenance.json")
    readiness = _json_member(files, "software/readiness.json")
    validation = _json_member(files, "software/validation.json")
    method_outputs = _json_member(files, "software/method_outputs.json")
    source = _json_member(files, "dataset/00_source/source_mtdp_manifest.json")
    result_rows = _csv_member(files, "dataset/04_aggregate/results_table.csv")
    decision_rows = _csv_member(files, "dataset/04_aggregate/run_decision_registry.csv")

    final_run_ids = [
        str(row.get("run_id") or "").strip()
        for row in decision_rows
        if str(row.get("run_id") or "").strip() and _truthy(row.get("included", True))
    ]
    if not final_run_ids:
        final_run_ids = [str(row.get("run_id") or "").strip() for row in result_rows if str(row.get("run_id") or "").strip()]

    validation_report = validation.get("validation_report") if isinstance(validation.get("validation_report"), dict) else {}
    readiness_report = readiness.get("readiness_report") if isinstance(readiness.get("readiness_report"), dict) else {}
    quality_gate = validation.get("report_quality_gate") if isinstance(validation.get("report_quality_gate"), dict) else {}

    return {
        "schema_id": "mtda.surface_manifest.v0_2",
        "layout": "mtda.recommended.v1",
        "surfaces": {
            "home": {
                "surface_id": "home",
                "label": "Home",
                "role": "Main local website entry point.",
                "html_member": "index.html",
                "status": _availability("index.html", names),
            },
            "test_report": {
                "surface_id": "test_report",
                "label": "Final Report",
                "role": "Final formal method/result report.",
                "html_member": "report/test_report.html",
                "pdf_member": "report/test_report.pdf",
                "json_member": "report/test_report.json",
                "status": _availability("report/test_report.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "test_report", "rc_status") or "",
            },
            "audit_report": {
                "surface_id": "audit_report",
                "label": "Audit Report",
                "role": "Scientist-facing audit and endpoint evidence.",
                "html_member": "audit/audit_report.html",
                "json_member": "audit/audit_report.json",
                "csv_member": "audit/audit_report.csv",
                "status": _availability("audit/audit_report.html", names),
                "rc_status": _nested(quality_gate, "surfaces", "audit_report", "rc_status") or "",
            },
            "software_status": {
                "surface_id": "software_status",
                "label": "Integrity / Software Status",
                "role": "Machine/debug/reproducibility trace.",
                "manifest_member": "software/manifest.json",
                "checksums_member": "software/checksums.json",
                "status": _availability("software/manifest.json", names),
            },
        },
        "run_surfaces": [],
        "key_csv_artifacts": _present(
            names,
            [
                "archive_index.csv",
                "dataset/00_source/source_file_index.csv",
                "dataset/02_normalized/normalization_registry.csv",
                "dataset/04_aggregate/results_table.csv",
                "dataset/04_aggregate/statistics.csv",
                "dataset/04_aggregate/stress_strain_aligned.csv",
                "dataset/04_aggregate/characteristic_points.csv",
                "dataset/04_aggregate/run_decision_registry.csv",
                "dataset/04_aggregate/bending_summary_table.csv",
                "dataset/04_aggregate/missing_metadata_table.csv",
                "dataset/04_aggregate/report_completion_table.csv",
                "audit/audit_report.csv",
            ],
        ),
        "key_json_artifacts": _present(
            names,
            [
                "report/test_report.json",
                "dataset/00_source/source_mtdp_manifest.json",
                "dataset/00_source/source_dataset.json",
                "audit/audit_report.json",
                "software/manifest.json",
                "software/provenance.json",
                "software/validation.json",
                "software/readiness.json",
                "software/method_outputs.json",
                "software/surface_manifest.json",
                "software/checksums.json",
            ],
        ),
        "cross_surface_agreement": {
            "source_package": _nested(provenance, "source_reference", "source_package", "path")
            or source.get("source_package_name")
            or source.get("name")
            or "",
            "source_schema_id": source.get("schema_id") or _nested(audit, "source_mtdp", "schema_id") or "",
            "source_schema_version": source.get("schema_version") or _nested(audit, "source_mtdp", "schema_version") or "",
            "method_id": manifest.get("method_id") or report.get("method_id") or _nested(audit, "method_package", "method_id") or "",
            "method_version": manifest.get("method_version") or report.get("method_version") or _nested(audit, "method_package", "version") or "",
            "readiness_status": readiness_report.get("status") or _nested(audit, "readiness", "status") or "",
            "validation_status": validation_report.get("status") or _nested(audit, "validation", "status") or "",
            "final_report_run_ids": final_run_ids,
            "selected_run_count": len(final_run_ids),
            "result_row_count": len(result_rows),
            "report_quality_gate_status": quality_gate.get("overall_status", ""),
            "boundary_resolution_status": _nested(audit, "experiment_boundary_resolution", "status") or "",
            "bounded_reduction": _nested(audit, "experiment_boundary_resolution", "bounded_reduction") or False,
            "boundary_aligned_aggregation": _nested(audit, "experiment_boundary_resolution", "boundary_aligned_aggregation") or False,
            "legacy_member_count": method_outputs.get("legacy_member_count", 0),
            "internal_checksum_member": "software/checksums.json",
        },
        "operator_handoff": {
            "open_home_member": "index.html",
            "open_test_report_member": "report/test_report.html",
            "open_audit_report_member": "audit/audit_report.html",
            "surface_roles": {
                "home": "Normal archive entry point.",
                "test_report": "Final formal report.",
                "audit_report": "Scientific audit evidence.",
                "software_status": "Machine reproducibility and integrity trace.",
            },
            "term_definitions": {
                "html": "Human view.",
                "csv": "Canonical tabular data.",
                "json": "Structured machine/reproducibility data.",
                "vega_spec": "Canonical editable plot definition.",
            },
            "next_action": "Extract the MTDA and open index.html for normal review.",
        },
    }


def _human_status(value: Any) -> str:
    code = str(value or "").strip()
    labels = {
        "COMPLETE": "Complete",
        "COMPLETE_WITH_WARNINGS": "Complete with warnings",
        "INCOMPLETE": "Incomplete",
        "RC_READY": "RC ready",
        "RC_WITH_WARNINGS": "RC ready with warnings",
        "not_finalized": "Draft, not finalized",
        "finalized": "Finalized",
        "amended": "Amended",
        "machine_default_confirmed": "Machine-selected report runs",
        "machine_acceptance": "Machine-selected report runs",
        "human_final": "Human-confirmed final report runs",
    }
    return labels.get(code, code.replace("_", " ").strip().capitalize())


def _reviewer_note_count(records: list[Any]) -> int:
    count = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        reason = str(record.get("reason") or "").strip()
        if reason:
            count += 1
    return count


def _next_action(*, report_completion_status: str, required_missing_count: Any, recommended_missing_count: Any, finalization_status: str) -> str:
    required = _int_value(required_missing_count)
    recommended = _int_value(recommended_missing_count)
    if required > 0 or report_completion_status == "INCOMPLETE":
        return "Review missing required report fields and record report-only amendments."
    if recommended > 0 and finalization_status not in {"finalized", "amended"}:
        return "Decide whether to add recommended metadata, then finalize with warnings if needed."
    if finalization_status not in {"finalized", "amended"}:
        return "Finalize the MTDA before external distribution."
    return "Export the production bundle for operator handoff."


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
