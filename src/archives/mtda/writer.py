from __future__ import annotations

import html
import json
import os
import re
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from archives.core.base_archive import ZipArchiveWriter
from archives.core.checksums import build_checksums, sha256_file
from archives.core.csv_io import write_dict_rows
from archives.core.json_io import json_bytes
from archives.core.layouts import MTDAAlignedLayout
from archives.core.manifest import build_mtda_manifest, utc_now_iso
from archives.mtda.models import MTDAWriteResult
from archives.mtda.plot_views import AGGREGATE_VIEW_FIELDS, RUN_VIEW_FIELDS, TRANSFORM_VERSIONS
from archives.mtda.surface_manifest import build_surface_manifest
from audit.audit_report_builder import AuditReportBuilder
from audit.audit_block_builder import build_audit_block_index_from_blocks, build_audit_blocks
from audit.method_development_report_builder import MethodDevelopmentReportBuilder
from audit.operation_trace import build_operation_trace
from audit.procedure_evidence_index import build_procedure_evidence_index
from compatibility import SchemaMethodCompatibilityChecker
from compatibility.compatibility_report import compatibility_artifacts
from html_renderer.adapters import (
    compact_plot_wrapper_context,
    dataset_plot_studio_context,
    plot_wrapper_context,
    report_shell_context,
    simple_report_context,
)
from html_renderer.mtda_page_spec import MtdaHandoffRenderRequest, render_mtda_handoff_from_spec
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_compact_plot_wrapper,
    render_dataset_plot_studio,
    render_plot_wrapper,
    render_report_shell,
    render_simple_report,
)
from mapping import MappingCandidateDiscovery, build_mapping_resolution_report, normalize_mapping_profile
from methods.core.method_result import MethodRunResult
from plotting.evidence_adapters import bending_evidence_request, stress_strain_reduction_request
from plotting.recipes.loader import load_recipe_catalog
from plotting.registry import plot_registry
from reporting.report_builder import ReportBuilder as MethodReportBuilder


_COMPACT_PLOT_PROJECTION_BY_TYPE = {
    "run_stress_strain_reduction_evidence": "mtda_run_compact_stress_strain_evidence",
    "dataset_aggregate_stress_strain": "mtda_dataset_aggregate_compact_package",
}


class MTDAWriter:
    def __init__(
        self,
        archive_writer: ZipArchiveWriter | None = None,
        report_builder: AuditReportBuilder | None = None,
        method_report_builder: MethodReportBuilder | None = None,
        plot_data_materialization: str | None = None,
    ) -> None:
        self.archive_writer = archive_writer or ZipArchiveWriter()
        self.report_builder = report_builder or AuditReportBuilder()
        self.method_report_builder = method_report_builder or MethodReportBuilder()
        resolved_materialization = plot_data_materialization or os.environ.get("MTDA_PLOT_DATA_MATERIALIZATION", "none")
        if resolved_materialization not in {"none", "compatibility", "full"}:
            raise ValueError("plot_data_materialization must be one of: none, compatibility, full")
        self.plot_data_materialization = resolved_materialization

    def write(self, result: MethodRunResult, output_path: str | Path) -> MTDAWriteResult:
        output = Path(output_path)
        files: dict[str, bytes] = {}
        source_reference = _source_reference(result)
        method_report = self.method_report_builder.build(result)
        procedure_evidence_index = build_procedure_evidence_index(result)
        audit_blocks = build_audit_blocks(result, procedure_evidence_index)
        audit_block_index = build_audit_block_index_from_blocks(audit_blocks)
        audit_payload = self.report_builder.build_payload(
            result,
            procedure_evidence_index=procedure_evidence_index,
            audit_block_index=audit_block_index,
            audit_blocks=audit_blocks,
        )
        audit_html = self.report_builder.build(
            result,
            procedure_evidence_index=procedure_evidence_index,
            audit_block_index=audit_block_index,
            audit_blocks=audit_blocks,
        )
        workbench_trace = build_operation_trace(result)
        workbench_html = MethodDevelopmentReportBuilder().build(workbench_trace, api_enabled=False)
        compatibility_report = SchemaMethodCompatibilityChecker().check(source=result.source, method_package=result.method_package)
        candidate_report = MappingCandidateDiscovery().discover(source=result.source, method_package=result.method_package)
        resolution_report = build_mapping_resolution_report(mapping=result.mapping, candidate_report=candidate_report)
        files["manifest.json"] = json_bytes(
            build_mtda_manifest(
                method_id=result.method_package.method_id,
                method_version=result.method_package.version,
                source_package_name=result.source.path.name,
                artifact_surfaces=_aligned_artifact_surfaces(),
            )
        )
        files["source_reference.json"] = json_bytes(source_reference)
        files["mapping_profile.json"] = json_bytes(result.mapping)
        files.update(compatibility_artifacts(compatibility_report))
        files["mapping/mapping_profile_used.json"] = json_bytes(normalize_mapping_profile(result.mapping))
        files["mapping/mapping_candidate_report.json"] = json_bytes(candidate_report)
        files["mapping/mapping_resolution_report.json"] = json_bytes(resolution_report)
        files["readiness/readiness_report.json"] = json_bytes(result.readiness_report)
        files["readiness/readiness_summary.csv"] = write_dict_rows(result.readiness_summary).encode("utf-8")
        files["readiness/resolved_inputs.csv"] = write_dict_rows(result.resolved_inputs).encode("utf-8")
        files["readiness/missing_inputs.csv"] = write_dict_rows(result.missing_inputs).encode("utf-8")
        files["method_outputs/specimen_results.csv"] = write_dict_rows(result.specimen_results).encode("utf-8")
        files["method_outputs/dataset_summary.csv"] = write_dict_rows(result.dataset_summary).encode("utf-8")
        files["method_outputs/dataset_summary_by_selection.csv"] = write_dict_rows(result.dataset_summary_by_selection).encode("utf-8")
        files["method_outputs/curves/stress_strain_family.csv"] = write_dict_rows(result.curve_family).encode("utf-8")
        files["method_outputs/curves/stress_strain_family_bounded.csv"] = write_dict_rows(result.bounded_curve_family or result.curve_family).encode("utf-8")
        files["method_outputs/curves/stress_strain_family_full.csv"] = write_dict_rows(result.full_curve_family or []).encode("utf-8")
        files["method_outputs/boundaries.csv"] = write_dict_rows(_boundary_summary_rows(result)).encode("utf-8")
        files["validation/validation_report.json"] = json_bytes(result.validation_report)
        files["validation/validation_summary.csv"] = write_dict_rows(result.validation_summary).encode("utf-8")
        files["validation/reference_values_used.csv"] = write_dict_rows(result.reference_values_used).encode("utf-8")
        files["validation/deviations.csv"] = write_dict_rows(result.validation_deviations).encode("utf-8")
        files["acceptance/acceptance_report.json"] = json_bytes(result.acceptance_report)
        files["acceptance/acceptance_summary.csv"] = write_dict_rows(result.acceptance_summary).encode("utf-8")
        files["acceptance/run_flags.csv"] = write_dict_rows(result.run_flags).encode("utf-8")
        files["acceptance/selection_sets.json"] = json_bytes(result.selection_sets)
        files["acceptance/selection_membership.csv"] = write_dict_rows(result.selection_membership).encode("utf-8")
        files["acceptance/discharged_runs.csv"] = write_dict_rows(result.discharged_runs).encode("utf-8")
        files["acceptance/discharge_report.json"] = json_bytes(result.discharge_report)
        files["acceptance/curve_family/curve_family_report.json"] = json_bytes(result.curve_family_assessment or _empty_curve_family_report())
        files["acceptance/curve_family/curve_family_scores.csv"] = write_dict_rows(result.curve_family_scores or []).encode("utf-8")
        files["acceptance/curve_family/curve_family_flags.csv"] = write_dict_rows(result.curve_family_flags or []).encode("utf-8")
        files["acceptance/curve_family/reference_curves.csv"] = write_dict_rows(result.curve_family_reference_rows or []).encode("utf-8")
        files["acceptance/curve_family/aligned_curve_family.csv"] = write_dict_rows(result.curve_family_aligned_rows or []).encode("utf-8")
        files["acceptance/curve_family/residuals_long.csv"] = write_dict_rows(result.curve_family_residual_rows or []).encode("utf-8")
        files["acceptance/curve_family/policy_resolved.json"] = json_bytes(result.curve_family_policy_resolved or _empty_curve_family_policy())
        files["acceptance/curve_family/curve_diagnostic_report.json"] = json_bytes(result.curve_shape_diagnostic_report or _empty_curve_diagnostic_report())
        files["acceptance/curve_family/curve_diagnostic_scores.csv"] = write_dict_rows(result.curve_shape_diagnostic_scores or []).encode("utf-8")
        files["acceptance/curve_family/curve_diagnostic_reference_curve.csv"] = write_dict_rows(result.curve_shape_diagnostic_reference_rows or []).encode("utf-8")
        files["acceptance/curve_family/curve_diagnostic_residuals.csv"] = write_dict_rows(result.curve_shape_diagnostic_residual_rows or []).encode("utf-8")
        files["acceptance/curve_family/curve_diagnostic_policy.json"] = json_bytes(result.curve_shape_diagnostic_policy_resolved or _empty_curve_diagnostic_policy())
        files["acceptance/curve_family/curve_diagnostic_flags.csv"] = write_dict_rows(result.curve_shape_diagnostic_flags or []).encode("utf-8")
        files["acceptance/human_decisions.json"] = json_bytes(result.human_decisions or _empty_human_decisions())
        files["acceptance/human_decisions.csv"] = write_dict_rows(result.human_decision_rows or []).encode("utf-8")
        files["acceptance/override_ledger.json"] = json_bytes(result.override_ledger or _empty_override_ledger())
        files["acceptance/selection_sets_final.json"] = json_bytes(result.selection_sets_final or _empty_final_selection_sets(result))
        files["acceptance/selection_membership_final.csv"] = write_dict_rows(result.selection_membership_final or []).encode("utf-8")
        files["acceptance/final_report_runs.csv"] = write_dict_rows(result.final_report_runs or []).encode("utf-8")
        files.update(method_report.files)
        files.update(_per_run_curve_files(result))
        files["audit/evidence.json"] = json_bytes(result.evidence)
        files["audit/procedure_evidence_index.json"] = json_bytes(procedure_evidence_index)
        files["audit/audit_blocks.json"] = json_bytes(audit_blocks)
        files["audit/audit_block_index.json"] = json_bytes(audit_block_index)
        files["audit/boundary_resolution.json"] = json_bytes(_boundary_resolution_payload(result))
        files["audit/boundary_events.csv"] = write_dict_rows(result.boundary_events or []).encode("utf-8")
        files["audit/operation_log.json"] = json_bytes(result.operation_log)
        files["audit/resolve_summary.json"] = json_bytes(result.resolve_summary)
        files["audit/reduce_summary.json"] = json_bytes(result.reduce_summary)
        files["audit/warnings.json"] = json_bytes(result.warnings)
        files["audit/inspections.json"] = json_bytes(result.inspections)
        files["audit/audit_report.html"] = audit_html.encode("utf-8")
        files["audit/audit_report.json"] = json_bytes(audit_payload)
        files["workbench/operation_trace.json"] = json_bytes(workbench_trace)
        files["workbench/index.html"] = workbench_html.encode("utf-8")
        files["interactive_report/index.html"] = audit_html.encode("utf-8")
        files["provenance.json"] = json_bytes(_provenance(result, source_reference, sorted(method_report.files), compatibility_report, candidate_report, resolution_report))
        files.update(_method_package_files(result))
        files = _aligned_mtda_files(
            result=result,
            legacy_files=files,
            source_reference=source_reference,
            workbench_trace=workbench_trace,
            compatibility_report=compatibility_report,
            candidate_report=candidate_report,
            resolution_report=resolution_report,
            plot_data_materialization=self.plot_data_materialization,
        )
        files[MTDAAlignedLayout.checksums] = json_bytes(
            build_checksums(files, checksum_member=MTDAAlignedLayout.checksums)
        )

        self.archive_writer.write(output, files)
        return MTDAWriteResult(path=output, members=tuple(sorted(files)))


def _aligned_mtda_files(
    *,
    result: MethodRunResult,
    legacy_files: dict[str, bytes],
    source_reference: dict[str, object],
    workbench_trace: dict[str, Any],
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
    plot_data_materialization: str = "none",
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    files.update(_aligned_input_copy_files(result))
    files.update(_aligned_processed_run_files(result))
    files.update(_aligned_aggregate_files(result, legacy_files))
    files.update(_aligned_plot_files(result, legacy_files, plot_data_materialization=plot_data_materialization))
    files.update(_aligned_report_files(result, legacy_files))
    files.update(
        _aligned_metadata_files(
            result=result,
            source_reference=source_reference,
            compatibility_report=compatibility_report,
            candidate_report=candidate_report,
            resolution_report=resolution_report,
        )
    )
    files.update(
        _aligned_software_metadata_files(
            result=result,
            legacy_files=legacy_files,
            workbench_trace=workbench_trace,
            compatibility_report=compatibility_report,
        )
    )
    files.update(_aligned_design_handoff_overlay(result, files))
    files[MTDAAlignedLayout.surface_manifest] = json_bytes(build_surface_manifest(files))
    return files


def _aligned_input_copy_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        f"{MTDAAlignedLayout.normalized_prefix}normalization_registry.csv": write_dict_rows(
            _normalization_registry_rows(result)
        ).encode("utf-8"),
    }
    for display_index, run in enumerate(result.source.runs, start=1):
        run_label = _run_label(run.run_id, display_index)
        raw_bytes = _source_archive_member(result.source.path, run.raw_package_path)
        files[f"{MTDAAlignedLayout.raw_prefix}{run_label}_raw.csv"] = (
            raw_bytes if raw_bytes is not None else _source_run_channels_csv(run).encode("utf-8")
        )
        normalized_bytes = _source_archive_member(result.source.path, run.normalized_package_path)
        files[f"{MTDAAlignedLayout.normalized_prefix}{run_label}_normalized.csv"] = (
            normalized_bytes if normalized_bytes is not None else _source_run_channels_csv(run).encode("utf-8")
        )
    return files


def _aligned_processed_run_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    bounded = _group_curve_rows(result.bounded_curve_family or result.curve_family)
    full = _group_curve_rows(result.full_curve_family or result.curve_family)
    bending = _group_curve_rows(_bending_trace_rows(result))
    run_ids = _ordered_run_ids(result)
    for display_index, run_id in enumerate(run_ids, start=1):
        run_label = _run_label(run_id, display_index)
        full_rows = full.get(run_id) or bounded.get(run_id) or []
        bounded_rows = bounded.get(run_id) or []
        files[f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv"] = write_dict_rows(full_rows).encode("utf-8")
        files[f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv"] = write_dict_rows(
            bounded_rows
        ).encode("utf-8")
        files[f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv"] = write_dict_rows(bending.get(run_id) or []).encode(
            "utf-8"
        )
    return files


def _aligned_aggregate_files(result: MethodRunResult, legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    report_completion = _csv_or_rows(legacy_files, "report/report_completeness_summary.csv", result.missing_inputs)
    return {
        f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv": write_dict_rows(result.specimen_results).encode("utf-8"),
        f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv": _legacy_or_rows(
            legacy_files,
            "report/aggregate_statistics.csv",
            result.dataset_summary_by_selection or result.dataset_summary,
        ),
        f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv": _legacy_or_rows(
            legacy_files,
            "report/aligned_curves.csv",
            result.curve_shape_diagnostic_residual_rows or result.curve_family_aligned_rows or [],
        ),
        f"{MTDAAlignedLayout.aggregate_prefix}characteristic_points.csv": _legacy_or_rows(
            legacy_files,
            "report/characteristic_points.csv",
            [],
        ),
        f"{MTDAAlignedLayout.aggregate_prefix}run_decision_registry.csv": write_dict_rows(_run_decision_rows(result)).encode("utf-8"),
        f"{MTDAAlignedLayout.aggregate_prefix}bending_summary_table.csv": write_dict_rows(_bending_summary_rows(result)).encode("utf-8"),
        f"{MTDAAlignedLayout.aggregate_prefix}missing_metadata_table.csv": _legacy_or_rows(
            legacy_files,
            "report/missing_report_fields.csv",
            result.missing_inputs,
        ),
        f"{MTDAAlignedLayout.aggregate_prefix}report_completion_table.csv": write_dict_rows(report_completion).encode("utf-8"),
    }


def _aligned_plot_files(
    result: MethodRunResult,
    legacy_files: dict[str, bytes],
    *,
    plot_data_materialization: str = "none",
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    dataset_spec = _dataset_plot_spec(result)
    dataset_title = f"Dataset report · {result.source.path.stem} · aggregate of {len(result.specimen_results)} runs"
    dataset_plot = _compact_plot_package_files(
        plot_id="dataset_plot",
        plot_type="dataset_aggregate_stress_strain",
        title=dataset_title,
        spec=dataset_spec,
        html_member=f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
        source_refs=[
            f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
            f"{MTDAAlignedLayout.aggregate_prefix}bending_summary_table.csv",
        ],
        plot_data_views=_dataset_plot_data_views(result),
        plot_data_materialization=plot_data_materialization,
        supplemental_datasets=[
            {
                "dataset_id": "stress_aggregate",
                "role": "stress_aggregate",
                "rows": _stress_aggregate_rows(result),
            },
            {
                "dataset_id": "bending_summary",
                "role": "bending_summary",
                "rows": _bending_summary_rows(result),
            },
            {
                "dataset_id": "fmax_distribution",
                "role": "fmax_distribution",
                "rows": _fmax_distribution_rows(result),
            }
        ],
    )
    files.update(dataset_plot)
    files[f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html"] = _dataset_plot_studio_html(
        title=dataset_title,
        package_path="dataset_plot.plot_package.json",
        home_path="../../index.html",
    ).encode("utf-8")
    files[f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot_manifest.csv"] = write_dict_rows(
        [
            {
                "plot_id": "dataset_plot",
                "plot_role": "dataset aggregate stress-strain view",
                "source_data_path": f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
                "plot_package": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.plot_package.json",
                "plot_template": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.template.json",
                "full_spec_export": "dataset_plot.full_vegalite_spec_with_data.vl.json",
                "settings_export": "dataset_plot.settings_only.plot_profile.json",
                "data_export": "dataset_plot.{dataset_id}.data_only.csv",
                "compact_package_export": "dataset_plot.full_plot_package_with_data.json",
                "plot_html": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
                "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,title,export",
            }
        ]
    ).encode("utf-8")

    bounded = _group_curve_rows(result.bounded_curve_family or result.curve_family)
    full = _group_curve_rows(result.full_curve_family or result.curve_family)
    specimen_by_run = {str(row.get("run_id") or ""): row for row in result.specimen_results}
    for display_index, run_id in enumerate(_ordered_run_ids(result), start=1):
        run_label = _run_label(run_id, display_index)
        spec = _run_stress_evidence_plot_spec(
            run_id,
            full.get(run_id) or bounded.get(run_id) or [],
            bounded.get(run_id) or [],
            specimen_by_run.get(run_id, {}),
        )
        files.update(
            _compact_plot_package_files(
                plot_id=f"{run_label}_plot",
                plot_type="run_stress_strain_reduction_evidence",
                title=f"{run_label} stress-strain evidence plot",
                spec=spec,
                html_member=f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.html",
                source_refs=[
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv",
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv",
                    f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv",
                ],
                plot_data_views=_run_plot_data_views(run_label),
                plot_data_materialization=plot_data_materialization,
            )
        )
        files[f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.html"] = _plot_wrapper_html(
            title=f"{run_label} stress-strain evidence plot",
            package_path=f"{run_label}_plot.plot_package.json",
            home_path="../../index.html",
        ).encode("utf-8")
        files[f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot_manifest.csv"] = write_dict_rows(
            [
                {
                    "plot_id": f"{run_label}_plot",
                    "plot_role": "run stress-strain reduction evidence",
                    "source_data_path": f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv",
                    "experiment_bound_source": f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv",
                    "bending_source": f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv",
                    "plot_package": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.plot_package.json",
                    "plot_template": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.template.json",
                    "full_spec_export": f"{run_label}_plot.full_vegalite_spec_with_data.vl.json",
                    "settings_export": f"{run_label}_plot.settings_only.plot_profile.json",
                    "data_export": f"{run_label}_plot.{{dataset_id}}.data_only.csv",
                    "compact_package_export": f"{run_label}_plot.full_plot_package_with_data.json",
                    "plot_html": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.html",
                    "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,bending_display,characteristic_point_labels,title,export",
                }
            ]
        ).encode("utf-8")
    return files


def _aligned_design_handoff_overlay(result: MethodRunResult, files: dict[str, bytes]) -> dict[str, bytes]:
    """Overlay the high-fidelity MTDA handoff shell while keeping aligned members canonical."""
    if not _handoff_overlay_available():
        required = ", ".join(str(_handoff_path(name)) for name in ("support.js", "MTDA Archive.dc.html", "MTDA Dataset.dc.html"))
        raise FileNotFoundError(
            "MTDA archive browser handoff assets are required for index.html generation: "
            f"{required}"
        )
    archive_data = _handoff_archive_data(result, files)
    metadata = _handoff_metadata(result, files, archive_data)
    archive_index = _handoff_archive_index(files)
    overlay = {
        f"{MTDAAlignedLayout.metadata_root}ui/support.js": _handoff_path("support.js").read_bytes(),
        MTDAAlignedLayout.index: _handoff_html(
            "MTDA Archive.dc.html",
            page="archive",
            globals={
                "MTDA_DATA": archive_data,
                "MTDA_METADATA": metadata,
                "MTDA_INDEX": archive_index,
                "MTDA_PAGE_SPEC": _handoff_page_spec("archive"),
            },
        ).encode("utf-8"),
        f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html": _handoff_html(
            "MTDA Dataset.dc.html",
            page="dataset",
            globals={
                "MTDA_DATA": archive_data,
                "MTDA_BENDING_DIST": _handoff_bending_dist(result),
                "MTDA_PAGE_SPEC": _handoff_page_spec("dataset"),
            },
        ).encode("utf-8"),
    }
    for index, run_id in enumerate(_ordered_run_ids(result), start=1):
        run_label = _run_label(run_id, index)
        overlay[f"{MTDAAlignedLayout.processed_prefix}{run_label}_browser.html"] = _handoff_html(
            "MTDA Archive.dc.html",
            page="run",
            globals={
                "MTDA_DATA": archive_data,
                "MTDA_METADATA": metadata,
                "MTDA_INDEX": archive_index,
                "MTDA_PAGE_SPEC": _handoff_page_spec("run", run_label=run_label),
                "MTDA_INITIAL_STATE": {"page": "run", "runId": run_label},
            },
        ).encode("utf-8")
    return overlay


def _handoff_html(filename: str, *, page: str, globals: dict[str, Any]) -> str:
    source = _handoff_path(filename).read_text(encoding="utf-8")
    support_path = "metadata/ui/support.js" if page == "archive" else "../../metadata/ui/support.js"
    dataset_name = str(((globals.get("MTDA_DATA") or {}).get("meta") or {}).get("datasetName") or "MTDA")
    page_spec = globals.get("MTDA_PAGE_SPEC")
    if not isinstance(page_spec, dict):
        raise ValueError("MTDA handoff rendering requires an MTDA_PAGE_SPEC global")
    return render_mtda_handoff_from_spec(
        MtdaHandoffRenderRequest(
            source_html=source,
            support_path=support_path,
            globals=globals,
            page_spec=page_spec,
            dataset_name=dataset_name,
            raw_root=MTDAAlignedLayout.raw_prefix.rstrip("/"),
            normalized_root=MTDAAlignedLayout.normalized_prefix.rstrip("/"),
            processed_root=MTDAAlignedLayout.processed_prefix.rstrip("/"),
            aggregate_root=MTDAAlignedLayout.aggregate_prefix.rstrip("/"),
            reports_root=MTDAAlignedLayout.reports_prefix.rstrip("/"),
        )
    )


def _handoff_page_spec(page: str, *, run_label: str = "") -> dict[str, Any]:
    if page == "archive":
        return {
            "kind": "mtda.archive.index",
            "layout": "handoff.archive",
            "route": "index.html",
            "panels": [
                {"type": "archive_header", "source": "MTDA_DATA.meta"},
                {"type": "file_catalogue", "source": "MTDA_INDEX"},
                {
                    "type": "report_links",
                    "testReportHref": "dataset/04_reports/test_report_shell.html",
                    "auditReportHref": "dataset/04_reports/audit_report_shell.html",
                },
                {"type": "dataset_plate", "href": "dataset/03_aggregate/dataset_plot.html"},
                {"type": "run_runtime", "runDataPrefix": "dataset/02_processed/"},
                {"type": "run_plate_grid", "hrefPattern": "dataset/02_processed/{run_id}_browser.html"},
            ],
        }
    if page == "dataset":
        return {
            "kind": "mtda.dataset.plot_studio",
            "layout": "handoff.plot_studio",
            "route": "dataset/03_aggregate/dataset_plot.html",
            "panels": [
                {"type": "dataset_titles"},
                {"type": "dataset_navigation", "archiveHref": "../../index.html"},
                {"type": "dataset_data_links", "localFiles": ["stress_strain_aligned.csv", "characteristic_points.csv", "statistics.csv"]},
                {"type": "plot_canvas", "source": "MTDA_DATA.alignedSeries"},
                {"type": "plot_inspector", "tabs": ["style", "layers", "data_spec"]},
                {"type": "export_menu", "outputs": ["style_profile", "csv", "svg", "png", "vega_lite", "plot_package"]},
            ],
        }
    if page == "run":
        return {
            "kind": "mtda.run.browser",
            "layout": "handoff.run_studio",
            "route": f"dataset/02_processed/{run_label}_browser.html",
            "initialState": {"page": "run", "runId": run_label},
            "panels": [
                {"type": "file_catalogue", "source": "MTDA_INDEX"},
                {
                    "type": "report_links",
                    "testReportHref": "../04_reports/test_report_shell.html",
                    "auditReportHref": "../04_reports/audit_report_shell.html",
                },
                {"type": "dataset_plate", "href": "../03_aggregate/dataset_plot.html"},
                {"type": "run_runtime", "runDataPrefix": ""},
                {"type": "run_plate_grid", "hrefPattern": "{run_id}_browser.html"},
                {"type": "run_navigation", "archiveHref": "../../index.html"},
                {"type": "run_topbar", "source": f"MTDA_DATA.runs[{run_label}]"},
                {"type": "run_plot_canvas", "source": f"MTDA_DATA.runCurves.{run_label}"},
                {"type": "plot_inspector", "tabs": ["style", "layers", "data_spec"]},
                {"type": "run_data_modal", "sources": ["stress_strain", "experiment_bound", "bending"], "localCsvHrefs": True},
            ],
        }
    raise ValueError(f"Unsupported MTDA handoff page kind: {page}")


def _handoff_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "design_handoff_dataset_plot_studio" / filename


def _handoff_overlay_available() -> bool:
    return all(
        _handoff_path(filename).is_file()
        for filename in ("support.js", "MTDA Archive.dc.html", "MTDA Dataset.dc.html")
    )


def _handoff_archive_data(result: MethodRunResult, files: dict[str, bytes]) -> dict[str, Any]:
    run_ids = _ordered_run_ids(result)
    runs = _handoff_runs(result)
    first_label = _run_label(run_ids[0], 1) if run_ids else "run_001"
    first_run = runs[0] if runs else {"boundaryEnd": 0}
    boundary_end = int(_number(first_run.get("boundaryEnd"), 0) or 0)
    run_curves = {
        str(run.get("id")): {
            "boundaryEnd": int(_number(run.get("boundaryEnd"), 0) or 0),
            "curve": _handoff_run_curve(files, str(run.get("id")), int(_number(run.get("boundaryEnd"), 0) or 0)),
        }
        for run in runs
        if run.get("id")
    }
    return {
        "meta": {
            "datasetName": result.source.dataset.get("dataset_id") or result.source.path.stem,
            "sourcePackage": result.source.path.name,
            "createdAt": utc_now_iso(),
            "methodId": result.method_package.method_id,
            "methodVersion": result.method_package.version,
            "formatVersion": "0.2.0",
            "layout": MTDAAlignedLayout.name,
            "checksumAlgorithm": "sha256",
            "checksumFileCount": len(files),
        },
        "stats": _handoff_stats(result),
        "runs": runs,
        "alignedSeries": _handoff_aligned_series(result, files),
        "run001": {
            "boundaryEnd": boundary_end,
            "curve": _handoff_run_curve(files, first_label, boundary_end),
        },
        "runCurves": run_curves,
        "completion": _handoff_completion_rows(result),
        "missingMeta": _handoff_missing_meta(result),
        "validation": {
            "checks": result.validation_summary or [],
            "schemaStatus": result.validation_report.get("status") if isinstance(result.validation_report, dict) else "",
            "schemaSummary": result.validation_report.get("summary") if isinstance(result.validation_report, dict) else {},
        },
    }


def _handoff_runs(result: MethodRunResult) -> list[dict[str, Any]]:
    specimen_by_run = {str(row.get("run_id") or ""): row for row in result.specimen_results}
    final_by_run = {str(row.get("run_id") or ""): row for row in result.final_report_runs or []}
    flags_by_run: dict[str, list[dict[str, Any]]] = {}
    for flag in result.run_flags or []:
        run_id = str(flag.get("run_id") or "")
        if run_id:
            flags_by_run.setdefault(run_id, []).append(flag)
    rows: list[dict[str, Any]] = []
    for index, run_id in enumerate(_ordered_run_ids(result), start=1):
        specimen = specimen_by_run.get(run_id, {})
        label = _run_label(run_id, index)
        width = _number(specimen.get("width_mm") or specimen.get("width"), 0)
        thickness = _number(specimen.get("thickness_mm") or specimen.get("thickness"), 0)
        area = _number(specimen.get("area_mm2") or specimen.get("section_area_mm2") or specimen.get("area"), 0)
        if not area and width and thickness:
            area = width * thickness
        final = final_by_run.get(run_id, {})
        final_recorded = bool(final)
        final_included = _truthy(final.get("final_included", final.get("included", True))) if final_recorded else None
        validity_source = "final_report_runs" if final_recorded else "specimen_results"
        validity_raw = specimen.get("validity") or specimen.get("status") or ""
        validity_display = "Accepted" if final_included is True else "Rejected" if final_included is False else _validity_label(validity_raw)
        rows.append(
            {
                "id": label,
                "specimen": specimen.get("specimen") or specimen.get("specimen_id") or run_id,
                "width": width,
                "thickness": thickness,
                "area": area,
                "maxLoad": _number(specimen.get("max_load_N") or specimen.get("maximum_load_N"), None),
                "strength": _number(specimen.get("compressive_strength_MPa") or specimen.get("max_stress_MPa"), None),
                "failStrain": _number(specimen.get("compressive_failure_strain") or specimen.get("failure_strain"), None),
                "modulus": _number(specimen.get("compressive_modulus_MPa") or specimen.get("modulus_MPa"), None),
                "bendPattern": specimen.get("bending_pattern") or "PASS",
                "bendConfidence": specimen.get("bending_pattern_confidence") or "",
                "bendReason": specimen.get("bending_pattern_reason") or "",
                "bendMax": _number(specimen.get("max_bending_percent") or specimen.get("bending_max_percent"), 0),
                "bendMean": _number(specimen.get("bending_mean_percent"), 0),
                "bendP95": _number(specimen.get("bending_p95_percent") or specimen.get("p95_bending_percent"), 0),
                "bendP99": _number(specimen.get("bending_p99_percent") or specimen.get("p99_bending_percent"), 0),
                "bendMedian": _number(specimen.get("median_bending_percent") or specimen.get("bending_median_percent"), 0),
                "bendThreshold": _number(specimen.get("bending_threshold_percent"), 10),
                "bendPtsAbove": int(_number(specimen.get("bending_points_above_threshold"), 0) or 0),
                "bendFracAbove": _number(specimen.get("bending_fraction_above_threshold"), 0),
                "boundaryStart": int(_number(specimen.get("boundary_start_index"), 0) or 0),
                "boundaryEnd": int(_number(specimen.get("boundary_end_index"), 0) or 0),
                "startPolicy": specimen.get("boundary_start_policy") or specimen.get("start_policy") or "",
                "endPolicy": specimen.get("boundary_end_policy") or specimen.get("end_policy") or "",
                "boundaryConfidence": specimen.get("boundary_confidence") or "",
                "boundaryReason": specimen.get("boundary_reason") or "",
                "validity": validity_display,
                "validityRaw": validity_raw,
                "finalIncluded": final_included,
                "validitySource": validity_source,
                "machineIncluded": final.get("machine_included", ""),
                "machineState": final.get("machine_state", ""),
                "humanDecision": final.get("human_decision", ""),
                "validityReason": final.get("human_decision_reason") or final.get("override_reason") or final.get("machine_state") or "",
                "warningsCount": len(flags_by_run.get(run_id, [])),
                "flags": flags_by_run.get(run_id, []),
            }
        )
    return rows


def _handoff_stats(result: MethodRunResult) -> dict[str, Any]:
    return {
        "max_load_N": _stat_block(result.specimen_results, "max_load_N", "N"),
        "compressive_strength_MPa": _stat_block(result.specimen_results, "compressive_strength_MPa", "MPa"),
        "compressive_failure_strain": _stat_block(result.specimen_results, "compressive_failure_strain", "strain"),
    }


def _stat_block(rows: list[dict[str, Any]], key: str, unit: str) -> dict[str, Any]:
    values = [value for row in rows for value in [_float_or_none(row.get(key))] if value is not None]
    if not values:
        return {"unit": unit, "n": 0}
    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0
    std_value = variance**0.5
    std_error = std_value / (len(values) ** 0.5)
    return {
        "unit": unit,
        "n": len(values),
        "mean": mean_value,
        "std": std_value,
        "stdErr": std_error,
        "ci95Low": mean_value - 1.96 * std_error,
        "ci95High": mean_value + 1.96 * std_error,
        "min": min(values),
        "max": max(values),
    }


def _handoff_aligned_series(result: MethodRunResult, files: dict[str, bytes]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, run_id in enumerate(_ordered_run_ids(result), start=1):
        label = _run_label(run_id, index)
        for row in _csv_rows(files.get(f"{MTDAAlignedLayout.processed_prefix}{label}_stress_strain.csv")):
            x_value = _row_number(row, ("analysis_window_progress_percent", "experiment_progress", "x_common", "strain_percent"))
            if x_value is None:
                strain = _row_number(row, ("mean_strain", "strain_mm_per_mm", "strain"))
                x_value = strain * 100 if strain is not None else None
            y_value = _row_number(row, ("stress_MPa", "stress_mpa", "y_observed", "stress"))
            if x_value is not None and y_value is not None:
                rows.append({"run": label, "x": x_value, "y": y_value})
    if rows:
        return rows
    for row in _csv_rows(files.get(f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv")):
        run = str(row.get("run") or row.get("run_id") or "")
        x_value = _row_number(row, ("x", "x_common", "analysis_window_progress_percent"))
        y_value = _row_number(row, ("y", "stress_MPa", "y_observed", "mean_stress_MPa"))
        if run and x_value is not None and y_value is not None:
            rows.append({"run": run, "x": x_value, "y": y_value})
    return rows


def _handoff_run_curve(files: dict[str, bytes], run_label: str, boundary_end: int) -> list[dict[str, Any]]:
    stress_rows = _csv_rows(files.get(f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv"))
    bending_rows = _csv_rows(files.get(f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv"))
    bend_by_index = {
        int(_number(row.get("point_index") or row.get("i"), index) or index): _row_number(row, ("bending_percent", "bend", "bending"))
        for index, row in enumerate(bending_rows)
    }
    curve: list[dict[str, Any]] = []
    for index, row in enumerate(stress_rows):
        point_index = int(_number(row.get("point_index") or row.get("i"), index) or index)
        strain = _row_number(row, ("mean_strain", "strain_mm_per_mm", "strain")) or 0
        curve.append(
            {
                "i": point_index,
                "strain": strain,
                "f": _row_number(row, ("front_strain", "front", "f")) or strain,
                "r": _row_number(row, ("rear_strain", "rear", "r")) or strain,
                "stress": _row_number(row, ("stress_MPa", "stress_mpa", "stress")) or 0,
                "load": _row_number(row, ("load_N", "load", "force_N")) or 0,
                "bend": bend_by_index.get(point_index) or 0,
                "inBound": point_index <= boundary_end if boundary_end else bool(row.get("experiment_progress") not in ("", None)),
            }
        )
    return curve


def _handoff_bending_dist(result: MethodRunResult) -> dict[str, Any]:
    dist: dict[str, Any] = {}
    for index, row in enumerate(_bending_summary_rows(result), start=1):
        run_id = str(row.get("run_id") or "")
        label = _run_label(run_id, index)
        dist[label] = {
            "min": _number(row.get("min_bending_percent"), 0),
            "q1": _number(row.get("q1_bending_percent"), 0),
            "median": _number(row.get("median_bending_percent") or row.get("bending_median_percent"), 0),
            "q3": _number(row.get("q3_bending_percent"), 0),
            "max": _number(row.get("max_bending_percent") or row.get("bending_max_percent"), 0),
            "p95": _number(row.get("bending_p95_percent"), 0),
            "p99": _number(row.get("bending_p99_percent"), 0),
        }
    return dist


def _handoff_metadata(result: MethodRunResult, files: dict[str, bytes], archive_data: dict[str, Any]) -> dict[str, Any]:
    source_schema = result.source.schema if isinstance(result.source.schema, dict) else {}
    missing = _handoff_missing_meta(result)
    missing_groups: dict[str, list[dict[str, Any]]] = {}
    for row in missing:
        missing_groups.setdefault(str(row.get("section") or "Metadata"), []).append(row)
    return {
        "package": archive_data["meta"],
        "completion": {
            "overall": "RC_WITH_WARNINGS" if missing else "RC_READY",
            "reportStatus": "INCOMPLETE" if missing else "COMPLETE",
            "readiness": _analysis_status(result),
            "validationStatus": result.validation_report.get("status") if isinstance(result.validation_report, dict) else "",
            "sections": _handoff_completion_rows(result),
        },
        "missingGroups": [
            {"id": _safe_plot_id(section).casefold(), "title": section, "fields": rows}
            for section, rows in missing_groups.items()
        ],
        "gate": {"checks": result.validation_summary or [], "schemaId": "report.rc_quality_gate.v0_2", "layout": MTDAAlignedLayout.name},
        "schema": {
            "status": result.validation_report.get("status") if isinstance(result.validation_report, dict) else "",
            "sourceSchema": source_schema.get("schema_id") or "",
            "sourceSchemaVersion": source_schema.get("schema_version") or "",
            "summary": result.validation_report.get("summary") if isinstance(result.validation_report, dict) else {},
        },
        "integrity": {"algorithm": "sha256", "fileCount": len(files), "checksumMember": MTDAAlignedLayout.checksums},
        "archive": {
            "schemaId": source_schema.get("schema_id") or "",
            "schemaVersion": source_schema.get("schema_version") or "",
            "checksumMember": MTDAAlignedLayout.checksums,
            "totals": {"files": len(files), "checksummed": len(files)},
        },
    }


def _handoff_archive_index(files: dict[str, bytes]) -> dict[str, Any]:
    stage_members: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "dataset/00_source",
            (
                MTDAAlignedLayout.manifest,
                MTDAAlignedLayout.schema,
                MTDAAlignedLayout.dataset,
                MTDAAlignedLayout.provenance,
                MTDAAlignedLayout.checksums,
            ),
        ),
        (MTDAAlignedLayout.raw_prefix.rstrip("/"), (MTDAAlignedLayout.raw_prefix,)),
        (MTDAAlignedLayout.normalized_prefix.rstrip("/"), (MTDAAlignedLayout.normalized_prefix,)),
        (MTDAAlignedLayout.processed_prefix.rstrip("/"), (MTDAAlignedLayout.processed_prefix,)),
        (MTDAAlignedLayout.aggregate_prefix.rstrip("/"), (MTDAAlignedLayout.aggregate_prefix,)),
    )
    sections: list[dict[str, Any]] = []
    for stage, prefixes_or_members in stage_members:
        stage_files = []
        members: set[str] = set()
        for prefix_or_member in prefixes_or_members:
            if prefix_or_member.endswith("/"):
                members.update(name for name in files if name.startswith(prefix_or_member))
            elif prefix_or_member in files:
                members.add(prefix_or_member)
        for member in sorted(members):
            suffix = PurePosixPath(member).suffix.lower().lstrip(".")
            stage_files.append(
                {
                    "name": PurePosixPath(member).name,
                    "path": member,
                    "href": member,
                    "kind": suffix,
                    "bytes": len(files[member]),
                }
            )
        sections.append({"id": stage, "files": stage_files})
    return {"sections": sections, "totals": {"files": len(files), "bytes": sum(len(value) for value in files.values())}}


def _handoff_completion_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.missing_inputs or []:
        title = str(row.get("section") or row.get("group") or "Metadata")
        entry = grouped.setdefault(
            title,
            {"id": _safe_plot_id(title).casefold(), "title": title, "fieldCount": 0, "missing": 0, "reqMissing": 0, "recMissing": 0, "optMissing": 0, "status": "complete"},
        )
        entry["fieldCount"] += 1
        entry["missing"] += 1
        level = str(row.get("level") or row.get("severity") or "").casefold()
        if level == "required":
            entry["reqMissing"] += 1
        elif level == "optional":
            entry["optMissing"] += 1
        else:
            entry["recMissing"] += 1
        entry["status"] = "incomplete" if entry["reqMissing"] else "complete_with_warnings"
    return list(grouped.values())


def _handoff_missing_meta(result: MethodRunResult) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for row in result.missing_inputs or []:
        missing.append(
            {
                "section": row.get("section") or row.get("group") or "Metadata",
                "label": row.get("label") or row.get("field") or row.get("key") or "Missing field",
                "key": row.get("key") or row.get("field") or "",
                "level": row.get("level") or row.get("severity") or "recommended",
                "severity": row.get("severity") or "report_completeness",
                "status": "missing",
                "message": row.get("message") or "",
                "affected": row.get("affected"),
            }
        )
    return missing


def _csv_rows(payload: bytes | None) -> list[dict[str, str]]:
    if not payload:
        return []
    import csv
    import io

    return list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))


def _row_number(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _float_or_none(row.get(key))
        if value is not None:
            return value
    return None


def _number(value: Any, default: float | None) -> float | None:
    number = _float_or_none(value)
    return default if number is None else number


def _aligned_report_files(result: MethodRunResult, legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    report_payload = _rewrite_aligned_paths(_json_from_bytes(legacy_files.get("report/test_report.json")) or {})
    report_payload = report_payload if isinstance(report_payload, dict) else {}
    report_payload["artifacts"] = [
        f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        f"{MTDAAlignedLayout.reports_prefix}test_report.pdf",
        f"{MTDAAlignedLayout.reports_prefix}test_report.json",
    ]
    report_html = legacy_files.get("report/test_report.html")
    report_html_text = (
        report_html.decode("utf-8", errors="replace") if report_html else _aligned_test_report_html(result, report_payload)
    )
    files[f"{MTDAAlignedLayout.reports_prefix}test_report.html"] = _rewrite_aligned_text_paths(report_html_text).encode("utf-8")
    files[f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"] = _aligned_report_shell_html(
        result,
        report_kind="test_report",
        report_href="test_report.html",
    ).encode("utf-8")
    files[f"{MTDAAlignedLayout.reports_prefix}test_report.json"] = json_bytes(report_payload)
    files[f"{MTDAAlignedLayout.reports_prefix}test_report.pdf"] = _report_pdf_bytes(report_payload)

    audit_payload = _rewrite_aligned_paths(_json_from_bytes(legacy_files.get("audit/audit_report.json")) or {})
    audit_payload = audit_payload if isinstance(audit_payload, dict) else {}
    links = audit_payload.get("artifact_links") if isinstance(audit_payload.get("artifact_links"), dict) else {}
    links.pop("method_development_workbench", None)
    links.update(
        {
            "test_report": f"{MTDAAlignedLayout.reports_prefix}test_report.html",
            "dataset_plot": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
            "audit_report": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
            "surface_manifest": MTDAAlignedLayout.surface_manifest,
        }
    )
    audit_payload["artifact_links"] = links
    audit_html = legacy_files.get("audit/audit_report.html")
    audit_html_text = audit_html.decode("utf-8", errors="replace") if audit_html else _aligned_audit_report_html(result, audit_payload)
    files[f"{MTDAAlignedLayout.reports_prefix}audit_report.html"] = _rewrite_aligned_text_paths(audit_html_text).encode("utf-8")
    files[f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"] = _aligned_report_shell_html(
        result,
        report_kind="audit_report",
        report_href="audit_report.html",
    ).encode("utf-8")
    files[f"{MTDAAlignedLayout.reports_prefix}audit_report.json"] = json_bytes(audit_payload)
    files[f"{MTDAAlignedLayout.reports_prefix}audit_report.csv"] = write_dict_rows(_audit_rows(result)).encode("utf-8")
    return files


def _aligned_report_shell_html(result: MethodRunResult, *, report_kind: str, report_href: str) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_aligned_report_shell_html(result, report_kind=report_kind, report_href=report_href)
    context = report_shell_context(result, report_kind=report_kind, report_href=report_href)
    return render_report_shell(context)


def _legacy_aligned_report_shell_html(result: MethodRunResult, *, report_kind: str, report_href: str) -> str:
    dataset_name = str(result.source.dataset.get("dataset_id") or result.source.path.stem)
    specs: dict[str, dict[str, str]] = {
        "test_report": {
            "title": "Test report",
            "right": "formal record",
            "peer_href": "audit_report_shell.html",
            "peer_label": "Audit report",
        },
        "audit_report": {
            "title": "Audit report",
            "right": "",
            "peer_href": "test_report_shell.html",
            "peer_label": "Test report",
        },
    }
    spec = specs.get(report_kind, specs["test_report"])
    title = f'{spec["title"]} - {dataset_name}'
    right_label_html = f'<span>{html.escape(spec["right"])}</span>\n' if spec["right"] else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
html,body{{margin:0;height:100%;overflow:hidden;background:#fff;color:#1d2a36;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.mtda-report-shell{{height:100%;display:grid;grid-template-rows:auto minmax(0,1fr)}}
.mtda-report-shell-banner{{box-sizing:border-box;min-height:44px;padding:9px 20px;display:flex;align-items:center;justify-content:space-between;gap:18px;background:#fff;border-bottom:1px solid #d8e1ea}}
.mtda-report-shell-banner a{{color:#126292;text-decoration:none;font-weight:700}}
.mtda-report-shell-banner a:hover{{text-decoration:underline}}
.mtda-report-shell-left{{display:flex;align-items:center;gap:13px;min-width:0}}
.mtda-report-shell-divider{{width:1px;height:26px;background:#d8e1ea;display:inline-block;flex:0 0 auto}}
.mtda-report-shell-title{{font-size:14px;font-weight:750;white-space:nowrap}}
.mtda-report-shell-subtitle{{font-size:13px;color:#748394;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mtda-report-shell-right{{display:flex;align-items:center;gap:16px;font-size:12px;color:#748394;white-space:nowrap}}
.mtda-report-shell-links{{display:flex;align-items:center;gap:10px}}
.mtda-report-shell-links a{{font-size:12px;font-weight:650;color:#185f8f}}
.mtda-report-frame{{display:block;width:100%;height:100%;border:0;background:#fff}}
@media(max-width:820px){{
  .mtda-report-shell-banner{{align-items:flex-start;flex-direction:column;padding:10px 14px}}
  .mtda-report-shell-right{{align-items:flex-start;flex-direction:column;gap:8px}}
}}
@media print{{
  html,body{{height:auto;overflow:visible}}
  .mtda-report-shell{{display:block;height:auto}}
  .mtda-report-shell-banner{{display:none!important}}
  .mtda-report-frame{{height:100vh}}
}}
</style>
</head>
<body>
<main class="mtda-report-shell" data-mtda-report-shell="{html.escape(report_kind)}">
<header class="mtda-report-shell-banner">
<div class="mtda-report-shell-left">
<a href="../../index.html">&larr; Archive</a>
<span class="mtda-report-shell-divider" aria-hidden="true"></span>
<span class="mtda-report-shell-title">{html.escape(spec["title"])}</span>
<span class="mtda-report-shell-subtitle">&middot; {html.escape(dataset_name)}</span>
</div>
<div class="mtda-report-shell-right">
{right_label_html}<nav class="mtda-report-shell-links" aria-label="Report navigation">
<a href="{html.escape(spec["peer_href"])}">{html.escape(spec["peer_label"])}</a>
</nav>
</div>
</header>
<iframe class="mtda-report-frame" src="{html.escape(report_href)}" title="{html.escape(spec["title"])}"></iframe>
</main>
</body>
</html>"""


def _aligned_metadata_files(
    *,
    result: MethodRunResult,
    source_reference: dict[str, object],
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> dict[str, bytes]:
    return {
        MTDAAlignedLayout.manifest: json_bytes(_aligned_manifest(result, source_reference)),
        MTDAAlignedLayout.schema: json_bytes(_aligned_schema(result)),
        MTDAAlignedLayout.dataset: json_bytes(_aligned_dataset(result)),
        MTDAAlignedLayout.provenance: json_bytes(
            _aligned_provenance(
                result=result,
                source_reference=source_reference,
                compatibility_report=compatibility_report,
                candidate_report=candidate_report,
                resolution_report=resolution_report,
            )
        ),
    }


def _aligned_software_metadata_files(
    *,
    result: MethodRunResult,
    legacy_files: dict[str, bytes],
    workbench_trace: dict[str, Any],
    compatibility_report: object,
) -> dict[str, bytes]:
    return {
        MTDAAlignedLayout.validation: json_bytes(
            {
                "schema_id": "mtda.validation_bundle",
                "schema_version": "0.1.0",
                "layout_version": MTDAAlignedLayout.name,
                "validation_report": result.validation_report,
                "validation_summary": result.validation_summary,
                "validation_deviations": result.validation_deviations,
                "reference_values_used": result.reference_values_used,
                "schema_method_compatibility": getattr(compatibility_report, "to_dict", lambda: {})(),
            }
        ),
        MTDAAlignedLayout.readiness: json_bytes(
            {
                "schema_id": "mtda.readiness_bundle",
                "schema_version": "0.1.0",
                "layout_version": MTDAAlignedLayout.name,
                "readiness_report": result.readiness_report,
                "readiness_summary": result.readiness_summary,
                "resolved_inputs": result.resolved_inputs,
                "missing_inputs": result.missing_inputs,
            }
        ),
        MTDAAlignedLayout.method_outputs: json_bytes(
            {
                "schema_id": "mtda.method_outputs_bundle",
                "schema_version": "0.1.0",
                "layout_version": MTDAAlignedLayout.name,
                **_method_outputs_payload(result, legacy_files, workbench_trace),
            }
        ),
    }


def _aligned_manifest(result: MethodRunResult, source_reference: dict[str, object]) -> dict[str, object]:
    source_package = source_reference.get("source_package") if isinstance(source_reference.get("source_package"), dict) else {}
    manifest = build_mtda_manifest(
        method_id=result.method_package.method_id,
        method_version=result.method_package.version,
        source_package_name=result.source.path.name,
        artifact_surfaces=_aligned_artifact_surfaces(),
    )
    manifest.update(
        {
            "format_version": "0.2.0",
            "layout_version": MTDAAlignedLayout.name,
            "package_id": f"{result.source.path.stem}-{result.method_package.method_id}",
            "method": {
                "method_id": result.method_package.method_id,
                "method_version": result.method_package.version,
                "standard_reference": result.method_package.manifest.get("standard_reference", ""),
            },
            "source_package": {
                "package_format": source_package.get("package_format") or result.source.manifest.get("package_format", ""),
                "package_id": result.source.manifest.get("package_id") or result.source.manifest.get("manifest_id") or "",
                "source_path": str(result.source.path),
                "source_name": result.source.path.name,
                "source_checksum_sha256": source_package.get("checksum", ""),
                "schema_id": result.source.manifest.get("schema_id") or result.source.schema.get("schema_id") or "",
                "schema_version": result.source.manifest.get("schema_version") or result.source.schema.get("schema_version") or "",
            },
            "dataset_ref": _aligned_dataset_ref(result),
            "entrypoint": MTDAAlignedLayout.index,
        }
    )
    return manifest


def _aligned_schema(result: MethodRunResult) -> dict[str, object]:
    return {
        "schema_id": "mtda.archive_schema",
        "schema_version": "0.1.0",
        "layout_version": MTDAAlignedLayout.name,
        "source_schema": result.source.schema,
        "archive_contract": {
            "required_root_members": [MTDAAlignedLayout.index, MTDAAlignedLayout.dataset_root, MTDAAlignedLayout.metadata_root],
            "required_dataset_stages": [
                MTDAAlignedLayout.raw_prefix,
                MTDAAlignedLayout.normalized_prefix,
                MTDAAlignedLayout.processed_prefix,
                MTDAAlignedLayout.aggregate_prefix,
                MTDAAlignedLayout.reports_prefix,
            ],
            "required_metadata_members": [
                MTDAAlignedLayout.manifest,
                MTDAAlignedLayout.schema,
                MTDAAlignedLayout.dataset,
                MTDAAlignedLayout.provenance,
                MTDAAlignedLayout.surface_manifest,
                MTDAAlignedLayout.validation,
                MTDAAlignedLayout.readiness,
                MTDAAlignedLayout.method_outputs,
                MTDAAlignedLayout.checksums,
            ],
            "deferred_batches": {
                "method_run_export_consumers": "RJ-20260611-F6A9D0",
            },
        },
    }


def _aligned_dataset(result: MethodRunResult) -> dict[str, object]:
    return {
        "schema_id": "mtda.dataset",
        "schema_version": "0.1.0",
        "layout_version": MTDAAlignedLayout.name,
        "dataset_id": result.source.dataset.get("dataset_id") or result.source.path.stem,
        "source_dataset_id": result.source.dataset.get("dataset_id") or "",
        "sample_type": result.source.dataset.get("sample_type", ""),
        "source_package_name": result.source.path.name,
        "run_order": _ordered_run_ids(result),
        "analysis_state": {
            "status": _analysis_status(result),
            "method_id": result.method_package.method_id,
            "method_version": result.method_package.version,
        },
        "run_counts": _aligned_dataset_ref(result),
    }


def _aligned_provenance(
    *,
    result: MethodRunResult,
    source_reference: dict[str, object],
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_id": "mtda.provenance",
        "schema_version": "0.1.0",
        "layout_version": MTDAAlignedLayout.name,
        "created_at": utc_now_iso(),
        "source_mtdp": source_reference.get("source_package", {}),
        "runs": _aligned_run_provenance_rows(result),
        "mapping": {
            "profile": normalize_mapping_profile(result.mapping),
            "candidate_report": candidate_report,
            "resolution_report": resolution_report,
        },
        "human_decisions": result.human_decisions or _empty_human_decisions(),
        "override_ledger": result.override_ledger or _empty_override_ledger(),
        "compatibility": getattr(compatibility_report, "to_dict", lambda: {})(),
        "events": _aligned_provenance_events(
            result,
            compatibility_report=compatibility_report,
            candidate_report=candidate_report,
            resolution_report=resolution_report,
        ),
    }


def _aligned_artifact_surfaces() -> dict[str, str]:
    return {
        "home": MTDAAlignedLayout.index,
        "dataset_plot": f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
        "test_report": f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html",
        "audit_report": f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html",
        "test_report_raw": f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        "audit_report_raw": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
        "surface_manifest": MTDAAlignedLayout.surface_manifest,
        "validation": MTDAAlignedLayout.validation,
        "readiness": MTDAAlignedLayout.readiness,
        "method_outputs": MTDAAlignedLayout.method_outputs,
    }


def _aligned_dataset_ref(result: MethodRunResult) -> dict[str, int]:
    final_rows = result.final_report_runs or []
    included = sum(1 for row in final_rows if _truthy(row.get("included", row.get("final_included", True))))
    review = sum(1 for row in result.run_flags if str(row.get("decision") or row.get("flag") or "").casefold() == "review")
    total = len(_ordered_run_ids(result))
    if not final_rows:
        included = len(result.specimen_results) or total
    return {
        "run_count": total,
        "included_run_count": included,
        "excluded_run_count": max(total - included, 0),
        "review_run_count": review,
    }


def _aligned_run_provenance_rows(result: MethodRunResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for display_index, run in enumerate(result.source.runs, start=1):
        run_label = _run_label(run.run_id, display_index)
        rows.append(
            {
                "run_id": run.run_id,
                "run_label": run_label,
                "original_filename": run.original_filename or "",
                "raw_package_path": run.raw_package_path or "",
                "normalized_package_path": run.normalized_package_path,
                "raw_archive_member": f"{MTDAAlignedLayout.raw_prefix}{run_label}_raw.csv",
                "normalized_archive_member": f"{MTDAAlignedLayout.normalized_prefix}{run_label}_normalized.csv",
                "processed_members": {
                    "browser_html": f"{MTDAAlignedLayout.processed_prefix}{run_label}_browser.html",
                    "stress_strain_csv": f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain.csv",
                    "stress_strain_experiment_bound_csv": f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv",
                    "bending_csv": f"{MTDAAlignedLayout.processed_prefix}{run_label}_bending.csv",
                    "plot_package": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.plot_package.json",
                    "plot_template": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.template.json",
                    "plot_html": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot.html",
                    "plot_manifest": f"{MTDAAlignedLayout.processed_prefix}{run_label}_plot_manifest.csv",
                },
            }
        )
    return rows


def _aligned_provenance_events(
    result: MethodRunResult,
    *,
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> list[dict[str, Any]]:
    compatibility_status = getattr(getattr(compatibility_report, "status", None), "value", "")
    candidate_summary = candidate_report.get("summary", {}) if isinstance(candidate_report, dict) else {}
    resolution_summary = resolution_report.get("summary", {}) if isinstance(resolution_report, dict) else {}
    events = [
        {
            "event": "schema_method_compatibility_checked",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "status": compatibility_status,
            "artifact": f"{MTDAAlignedLayout.validation}#schema_method_compatibility",
        },
        {
            "event": "mapping_candidates_generated",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "candidate_summary": candidate_summary,
            "artifact": f"{MTDAAlignedLayout.provenance}#mapping.candidate_report",
        },
        {
            "event": "mapping_profile_confirmed",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "mapping_id": result.mapping.get("mapping_id"),
            "resolution_summary": resolution_summary,
            "artifact": f"{MTDAAlignedLayout.provenance}#mapping.profile",
        },
        {
            "event": "readiness_checked_with_mapping",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "mapping_id": result.mapping.get("mapping_id"),
            "readiness_status": result.readiness_report.get("status"),
            "artifact": f"{MTDAAlignedLayout.readiness}#readiness_report",
        },
        {
            "event": "method_run_completed",
            "timestamp": utc_now_iso(),
            "software": "compression_module_method_run_layer",
            "software_version": "0.1.0",
            "method_id": result.method_package.method_id,
            "method_version": result.method_package.version,
            "inputs": [str(result.source.path)],
            "outputs": [
                MTDAAlignedLayout.index,
                f"{MTDAAlignedLayout.aggregate_prefix}dataset_plot.html",
                f"{MTDAAlignedLayout.reports_prefix}test_report.html",
                f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
                MTDAAlignedLayout.manifest,
                MTDAAlignedLayout.schema,
                MTDAAlignedLayout.dataset,
                MTDAAlignedLayout.provenance,
                MTDAAlignedLayout.surface_manifest,
                MTDAAlignedLayout.validation,
                MTDAAlignedLayout.readiness,
                MTDAAlignedLayout.method_outputs,
                MTDAAlignedLayout.checksums,
            ],
        },
    ]
    if result.report_overrides:
        events.append(
            {
                "event": "report_overrides_applied",
                "timestamp": utc_now_iso(),
                "software": "compression_module_method_run_layer",
                "method_id": result.method_package.method_id,
                "field_count": len(result.report_overrides),
                "source_type": "report_override",
                "mtdp_mutated": False,
                "artifacts": [
                    f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_field_overrides",
                    f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_override_ledger",
                    f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_values_used",
                ],
            }
        )
    return events


def _analysis_status(result: MethodRunResult) -> str:
    validation_status = str(result.validation_report.get("status") or result.validation_report.get("overall_status") or "").casefold()
    if "fail" in validation_status or "error" in validation_status:
        return "incomplete"
    if result.warnings or "warn" in validation_status:
        return "completed_with_warnings"
    return "completed"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "included"}


def _validity_label(value: Any) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized in {"", "accepted", "valid", "true", "1", "yes", "y", "included"}:
        return "Accepted"
    if normalized in {"rejected", "invalid", "false", "0", "no", "n", "excluded"}:
        return "Rejected"
    return str(value).strip() or "Accepted"


def _recommended_mtda_files(
    *,
    result: MethodRunResult,
    legacy_files: dict[str, bytes],
    source_reference: dict[str, object],
    workbench_trace: dict[str, Any],
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    report_files = _filtered_report_files(legacy_files)
    files.update(report_files)
    files.update(_source_dataset_files(result))
    files.update(_processed_run_files(result))
    files.update(_aggregate_dataset_files(result, legacy_files))
    files.update(_plot_bundle_files(result, legacy_files))
    files.update(_audit_files(result, legacy_files))
    files["README.md"] = _readme_text().encode("utf-8")
    files.update(
        _software_files(
            result=result,
            legacy_files=legacy_files,
            recommended_files=files,
            source_reference=source_reference,
            workbench_trace=workbench_trace,
            compatibility_report=compatibility_report,
            candidate_report=candidate_report,
            resolution_report=resolution_report,
        )
    )
    return files


def _filtered_report_files(legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path, content in legacy_files.items():
        if not path.startswith("report/"):
            continue
        if Path(path).name.startswith("iso14126_report."):
            continue
        if path == "report/test_report.json":
            payload = _json_from_bytes(content) or {}
            payload["artifacts"] = ["report/test_report.html", "report/test_report.pdf", "report/test_report.json"]
            files[path] = json_bytes(_rewrite_recommended_paths(payload))
            files["report/test_report.pdf"] = _report_pdf_bytes(payload)
        elif path == "report/test_report.html":
            files[path] = content
    return files


def _source_dataset_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        "dataset/00_source/source_mtdp_manifest.json": json_bytes(result.source.manifest),
        "dataset/00_source/source_dataset.json": json_bytes(result.source.dataset),
        "dataset/00_source/source_file_index.csv": write_dict_rows(_source_file_index_rows(result)).encode("utf-8"),
        "dataset/02_normalized/normalization_registry.csv": write_dict_rows(_normalization_registry_rows(result)).encode("utf-8"),
    }
    for display_index, run in enumerate(result.source.runs, start=1):
        run_label = _run_label(run.run_id, display_index)
        raw_bytes = _source_archive_member(result.source.path, run.raw_package_path)
        files[f"dataset/01_raw/{run_label}_raw.csv"] = raw_bytes if raw_bytes is not None else _source_run_channels_csv(run).encode("utf-8")
        normalized_bytes = _source_archive_member(result.source.path, run.normalized_package_path)
        files[f"dataset/02_normalized/{run_label}_normalized.csv"] = (
            normalized_bytes if normalized_bytes is not None else _source_run_channels_csv(run).encode("utf-8")
        )
    return files


def _report_pdf_bytes(payload: dict[str, Any]) -> bytes:
    return _simple_pdf(_report_pdf_lines(payload))


def _report_pdf_lines(payload: dict[str, Any]) -> list[str]:
    document = payload.get("report_document") if isinstance(payload.get("report_document"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    completion = payload.get("report_completion_status") if isinstance(payload.get("report_completion_status"), dict) else {}
    lines = [
        str(document.get("title") or "Test report"),
        f"Method: {payload.get('method_id', '')} {payload.get('method_version', '')}".strip(),
        f"Standard: {payload.get('standard_reference', '')}".strip(),
        f"Source package: {payload.get('source_package', '')}".strip(),
        f"Report completion: {completion.get('status', '')}".strip(),
        "",
        "Summary",
    ]
    for key, value in summary.items():
        lines.append(f"{key}: {_pdf_value(value)}")
    aggregate = payload.get("aggregate_statistics")
    if isinstance(aggregate, list) and aggregate:
        lines.extend(["", "Aggregate statistics"])
        for row in aggregate[:12]:
            if isinstance(row, dict):
                lines.append(", ".join(f"{key}={_pdf_value(value)}" for key, value in row.items() if value not in (None, ""))[:110])
    individual = payload.get("individual_results")
    if isinstance(individual, list) and individual:
        lines.extend(["", "Individual results"])
        for row in individual[:24]:
            if not isinstance(row, dict):
                continue
            selected = {
                key: row.get(key)
                for key in ("run_id", "specimen_id", "compressive_strength_MPa", "compressive_modulus_MPa", "compressive_failure_strain", "validity")
                if row.get(key) not in (None, "")
            }
            lines.append(", ".join(f"{key}={_pdf_value(value)}" for key, value in selected.items())[:110])
    missing = payload.get("missing_report_fields")
    if isinstance(missing, list) and missing:
        lines.extend(["", "Missing report fields"])
        for row in missing[:32]:
            if isinstance(row, dict):
                field = row.get("field") or row.get("field_id") or row.get("name") or row
                severity = row.get("severity", "")
                lines.append(f"{field} {severity}".strip()[:110])
            else:
                lines.append(str(row)[:110])
    return [line for line in lines if line is not None]


def _pdf_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _simple_pdf(lines: list[str]) -> bytes:
    page_line_count = 48
    pages = [lines[index : index + page_line_count] for index in range(0, max(len(lines), 1), page_line_count)] or [[]]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_refs: list[str] = []
    for page_index, page_lines in enumerate(pages):
        content_id = 4 + page_index * 2
        page_id = content_id + 1
        content = _pdf_content_stream(page_lines)
        objects.append(b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_refs.append(f"{page_id} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>".encode("ascii")
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for obj_id, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{obj_id} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return pdf


def _pdf_content_stream(lines: list[str]) -> bytes:
    content = ["BT", "/F1 10 Tf", "13 TL", "72 740 Td"]
    for line in lines:
        content.append(f"({_pdf_escape(line)}) Tj")
        content.append("T*")
    content.append("ET")
    return "\n".join(content).encode("latin-1", errors="replace")


def _pdf_escape(value: str) -> str:
    ascii_text = str(value).encode("latin-1", errors="replace").decode("latin-1")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _processed_run_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    bounded = _group_curve_rows(result.bounded_curve_family or result.curve_family)
    full = _group_curve_rows(result.full_curve_family or result.curve_family)
    bending = _group_curve_rows(_bending_trace_rows(result))
    run_ids = _ordered_run_ids(result)
    for display_index, run_id in enumerate(run_ids, start=1):
        run_label = _run_label(run_id, display_index)
        full_rows = full.get(run_id) or bounded.get(run_id) or []
        bounded_rows = bounded.get(run_id) or []
        files[f"dataset/03_processed/{run_label}_stress_strain.csv"] = write_dict_rows(full_rows).encode("utf-8")
        files[f"dataset/03_processed/{run_label}_stress_strain_experiment_bound.csv"] = write_dict_rows(bounded_rows).encode("utf-8")
        files[f"dataset/03_processed/{run_label}_bending.csv"] = write_dict_rows(bending.get(run_id) or []).encode("utf-8")
    return files


def _aggregate_dataset_files(result: MethodRunResult, legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    report_completion = _csv_or_rows(legacy_files, "report/report_completeness_summary.csv", result.missing_inputs)
    files = {
        "dataset/04_aggregate/results_table.csv": write_dict_rows(result.specimen_results).encode("utf-8"),
        "dataset/04_aggregate/statistics.csv": _legacy_or_rows(legacy_files, "report/aggregate_statistics.csv", result.dataset_summary_by_selection or result.dataset_summary),
        "dataset/04_aggregate/stress_strain_aligned.csv": _legacy_or_rows(
            legacy_files,
            "report/aligned_curves.csv",
            result.curve_shape_diagnostic_residual_rows or result.curve_family_aligned_rows or [],
        ),
        "dataset/04_aggregate/characteristic_points.csv": _legacy_or_rows(legacy_files, "report/characteristic_points.csv", []),
        "dataset/04_aggregate/run_decision_registry.csv": write_dict_rows(_run_decision_rows(result)).encode("utf-8"),
        "dataset/04_aggregate/bending_summary_table.csv": write_dict_rows(_bending_summary_rows(result)).encode("utf-8"),
        "dataset/04_aggregate/missing_metadata_table.csv": _legacy_or_rows(legacy_files, "report/missing_report_fields.csv", result.missing_inputs),
        "dataset/04_aggregate/report_completion_table.csv": write_dict_rows(report_completion).encode("utf-8"),
    }
    return files


def _plot_bundle_files(result: MethodRunResult, legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    dataset_spec = _json_from_bytes(legacy_files.get("report/vega_specs/aggregate_stress_strain_mean_variability.json")) or _dataset_plot_spec(result)
    files["dataset/05_plots/dataset_plot/dataset_plot.vl.json"] = json_bytes(dataset_spec)
    files["dataset/05_plots/dataset_plot/dataset_plot.html"] = _plot_wrapper_html(
        title="Dataset plot",
        spec_path="dataset_plot.vl.json",
        spec=dataset_spec,
    ).encode("utf-8")
    files["dataset/05_plots/dataset_plot/dataset_plot_manifest.csv"] = write_dict_rows(
        [
            {
                "source_data_path": "dataset/04_aggregate/stress_strain_aligned.csv",
                "plot_spec": "dataset/05_plots/dataset_plot/dataset_plot.vl.json",
                "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,title,export",
            }
        ]
    ).encode("utf-8")
    bounded = _group_curve_rows(result.bounded_curve_family or result.curve_family)
    full = _group_curve_rows(result.full_curve_family or result.curve_family)
    for display_index, run_id in enumerate(_ordered_run_ids(result), start=1):
        run_label = _run_label(run_id, display_index)
        bounded_rows = bounded.get(run_id) or []
        full_rows = full.get(run_id) or []
        specimen = next((row for row in result.specimen_results if str(row.get("run_id") or "") == run_id), {})
        spec = _run_stress_evidence_plot_spec(run_id, full_rows, bounded_rows, specimen)
        debug_spec = _run_debug_plot_spec(run_id, full_rows, bounded_rows)
        bending_spec = _run_bending_plot_spec(result, run_id, bounded_rows)
        base = f"dataset/05_plots/{run_label}_plot"
        files[f"{base}/{run_label}_plot.vl.json"] = json_bytes(spec)
        files[f"{base}/{run_label}_plot.html"] = _plot_wrapper_html(
            title=f"{run_label} stress-strain evidence plot",
            spec_path=f"{run_label}_plot.vl.json",
            spec=spec,
        ).encode("utf-8")
        files[f"{base}/{run_label}_debug_plot.vl.json"] = json_bytes(debug_spec)
        files[f"{base}/{run_label}_debug_plot.html"] = _plot_wrapper_html(
            title=f"{run_label} stress-strain debug plot",
            spec_path=f"{run_label}_debug_plot.vl.json",
            spec=debug_spec,
        ).encode("utf-8")
        files[f"{base}/{run_label}_bending_plot.vl.json"] = json_bytes(bending_spec)
        files[f"{base}/{run_label}_bending_plot.html"] = _plot_wrapper_html(
            title=f"{run_label} bending plot",
            spec_path=f"{run_label}_bending_plot.vl.json",
            spec=bending_spec,
        ).encode("utf-8")
        files[f"{base}/{run_label}_plot_manifest.csv"] = write_dict_rows(
            [
                {
                    "source_data_path": f"dataset/03_processed/{run_label}_stress_strain.csv",
                    "experiment_bound_source": f"dataset/03_processed/{run_label}_stress_strain_experiment_bound.csv",
                    "bending_source": f"dataset/03_processed/{run_label}_bending.csv",
                    "plot_spec": f"{base}/{run_label}_plot.vl.json",
                    "plot_role": "audit-style stress-strain reduction evidence",
                    "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,bending_display,characteristic_point_labels,title,export",
                },
                {
                    "source_data_path": f"dataset/03_processed/{run_label}_stress_strain.csv",
                    "experiment_bound_source": f"dataset/03_processed/{run_label}_stress_strain_experiment_bound.csv",
                    "bending_source": f"dataset/03_processed/{run_label}_bending.csv",
                    "plot_spec": f"{base}/{run_label}_debug_plot.vl.json",
                    "plot_role": "debug full-vs-experiment-bound stress-strain plot",
                    "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,bending_display,characteristic_point_labels,title,export",
                },
                {
                    "source_data_path": f"dataset/03_processed/{run_label}_stress_strain_experiment_bound.csv",
                    "bending_source": f"dataset/03_processed/{run_label}_bending.csv",
                    "plot_spec": f"{base}/{run_label}_bending_plot.vl.json",
                    "plot_role": "bending evidence plot",
                    "controls": "visibility,axis_range,axis_labels,line_width,opacity,point_size,title,export",
                },
            ]
        ).encode("utf-8")
    return files


def _audit_files(result: MethodRunResult, legacy_files: dict[str, bytes]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    if "audit/audit_report.html" in legacy_files:
        files["audit/audit_report.html"] = _rewrite_recommended_text_paths(
            legacy_files["audit/audit_report.html"].decode("utf-8", errors="replace")
        ).encode("utf-8")
    if "audit/audit_report.json" in legacy_files:
        payload = _json_from_bytes(legacy_files["audit/audit_report.json"]) or {}
        files["audit/audit_report.json"] = json_bytes(_sanitize_audit_payload(payload))
    files["audit/audit_report.csv"] = write_dict_rows(_audit_rows(result)).encode("utf-8")
    return files


def _software_files(
    *,
    result: MethodRunResult,
    legacy_files: dict[str, bytes],
    recommended_files: dict[str, bytes],
    source_reference: dict[str, object],
    workbench_trace: dict[str, Any],
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> dict[str, bytes]:
    report_quality_gate = _recommended_report_quality_gate(recommended_files)
    manifest = build_mtda_manifest(
        method_id=result.method_package.method_id,
        method_version=result.method_package.version,
        source_package_name=result.source.path.name,
        artifact_surfaces=_aligned_artifact_surfaces(),
    )
    manifest["layout"] = "mtda.recommended.v1"
    provenance = _provenance(
        result,
        source_reference,
        report_outputs=["report/test_report.html", "report/test_report.json"],
        compatibility_report=compatibility_report,
        candidate_report=candidate_report,
        resolution_report=resolution_report,
    )
    provenance["events"] = _recommended_provenance_events(
        result,
        compatibility_report=compatibility_report,
        candidate_report=candidate_report,
        resolution_report=resolution_report,
    )
    provenance["mapping"] = {
        "profile": _json_from_bytes(legacy_files.get("mapping/mapping_profile_used.json")) or normalize_mapping_profile(result.mapping),
        "candidate_report": candidate_report,
        "resolution_report": resolution_report,
    }
    provenance["recommended_layout"] = {
        "root_entrypoint": "index.html",
        "human_surfaces": [
            "report/test_report.html",
            "dataset/05_plots/dataset_plot/dataset_plot.html",
            "audit/audit_report.html",
        ],
        "software_namespace": "software/",
        "internal_checksum_member": "software/checksums.json",
    }
    return {
        "software/manifest.json": json_bytes(manifest),
        "software/provenance.json": json_bytes(provenance),
        "software/validation.json": json_bytes(
            {
                "schema_id": "mtda.validation_bundle.v0_1",
                "validation_report": result.validation_report,
                "validation_summary": result.validation_summary,
                "validation_deviations": result.validation_deviations,
                "reference_values_used": result.reference_values_used,
                "schema_method_compatibility": getattr(compatibility_report, "to_dict", lambda: {})(),
                "report_quality_gate": report_quality_gate,
            }
        ),
        "software/readiness.json": json_bytes(
            {
                "schema_id": "mtda.readiness_bundle.v0_1",
                "readiness_report": result.readiness_report,
                "readiness_summary": result.readiness_summary,
                "resolved_inputs": result.resolved_inputs,
                "missing_inputs": result.missing_inputs,
            }
        ),
        "software/method_outputs.json": json_bytes(_rewrite_recommended_paths(_method_outputs_payload(result, legacy_files, workbench_trace))),
    }


def _source_reference(result: MethodRunResult) -> dict[str, object]:
    return {
        "source_package": {
            "path": str(result.source.path),
            "package_format": result.source.manifest.get("package_format"),
            "format_version": result.source.manifest.get("format_version"),
            "checksum_algorithm": "sha256",
            "checksum": sha256_file(result.source.path),
            "schema_id": result.source.manifest.get("schema_id"),
            "schema_version": result.source.manifest.get("schema_version"),
            "run_count": len(result.source.runs),
        }
    }


def _ordered_run_ids(result: MethodRunResult) -> list[str]:
    run_ids = [str(run.run_id) for run in result.source.runs]
    seen = set(run_ids)
    for row in result.specimen_results:
        run_id = str(row.get("run_id") or "")
        if run_id and run_id not in seen:
            run_ids.append(run_id)
            seen.add(run_id)
    return run_ids


def _run_label(run_id: str, display_index: int | None = None) -> str:
    text = str(run_id or "").strip()
    if text.startswith("run_"):
        suffix = text.removeprefix("run_")
        if suffix.isdigit():
            return f"run_{int(suffix):03d}"
    if display_index is not None:
        return f"run_{display_index:03d}"
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in text).strip("_")
    return safe or "run"


def _source_file_index_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, run in enumerate(result.source.runs, start=1):
        rows.append(
            {
                "run_id": run.run_id,
                "run_label": _run_label(run.run_id, index),
                "original_filename": run.original_filename or "",
                "raw_package_path": run.raw_package_path or "",
                "normalized_package_path": run.normalized_package_path,
                "channel_count": len(run.channels),
                "token_count": len(run.tokens),
            }
        )
    return rows


def _normalization_registry_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    channels = result.mapping.get("channels", {}) if isinstance(result.mapping.get("channels"), dict) else {}
    for method_channel, source_channel in sorted(channels.items()):
        rows.append(
            {
                "mapping_id": result.mapping.get("mapping_id", ""),
                "method_channel": method_channel,
                "source_channel": source_channel,
                "normalization_role": "channel_mapping",
                "unit_conversion": "",
                "notes": "Resolved mapping used for method execution.",
            }
        )
    for row in result.resolved_inputs:
        rows.append(
            {
                "mapping_id": result.mapping.get("mapping_id", ""),
                "method_channel": row.get("input_id") or row.get("field") or "",
                "source_channel": row.get("source") or row.get("source_field") or "",
                "normalization_role": "resolved_input",
                "unit_conversion": row.get("unit") or "",
                "notes": row.get("status") or "",
            }
        )
    return rows


def _source_archive_member(path: Path, member: str | None) -> bytes | None:
    if not member:
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.read(member)
    except (FileNotFoundError, KeyError, zipfile.BadZipFile):
        return None


def _source_run_channels_csv(run: Any) -> str:
    channels = list(getattr(run, "channels", {}).values())
    max_len = max((len(channel.values) for channel in channels), default=0)
    rows: list[dict[str, Any]] = []
    for index in range(max_len):
        row: dict[str, Any] = {"point_index": index}
        for channel in channels:
            row[channel.name] = channel.values[index] if index < len(channel.values) else ""
        rows.append(row)
    return write_dict_rows(rows)


def _legacy_or_rows(legacy_files: dict[str, bytes], path: str, rows: list[dict[str, Any]]) -> bytes:
    return legacy_files.get(path) or write_dict_rows(rows).encode("utf-8")


def _csv_or_rows(legacy_files: dict[str, bytes], path: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = legacy_files.get(path)
    if not payload:
        return rows
    import csv
    import io

    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


def _json_from_bytes(content: bytes | None) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _bending_trace_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in result.bounded_curve_family or result.curve_family:
        if not isinstance(row, dict):
            continue
        bending_keys = [key for key in row if "bend" in key.casefold()]
        bending_percent = _bending_percent_from_curve_row(row)
        keep = {
            "run_id": row.get("run_id"),
            "point_index": row.get("point_index"),
            "experiment_progress": row.get("experiment_progress"),
            "stress_MPa": row.get("stress_MPa"),
            "load_N": row.get("load_N"),
        }
        if bending_percent is not None:
            keep["bending_percent"] = bending_percent
        for key in bending_keys:
            keep[key] = row.get(key)
        rows.append(keep)
    return rows


def _bending_percent_from_curve_row(row: dict[str, Any]) -> float | None:
    explicit = _float_or_none(row.get("bending_percent"))
    if explicit is not None:
        return explicit
    front = _first_float(row, ("front_strain_abs", "front_strain_oriented", "front_strain", "front_strain_raw", "front"))
    rear = _first_float(row, ("rear_strain_abs", "rear_strain_oriented", "rear_strain", "rear_strain_raw", "rear"))
    if front is None or rear is None:
        return None
    denominator = abs(front + rear)
    if denominator == 0:
        return None
    return abs(front - rear) / denominator * 100.0


def _first_float(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _float_or_none(row.get(key))
        if value is not None:
            return value
    return None


def _ordered_five_number_values(
    minimum: Any,
    q1: Any,
    median: Any,
    q3: Any,
    maximum: Any,
) -> tuple[Any, Any, Any, Any, Any]:
    values = [_float_or_none(value) for value in (minimum, q1, median, q3, maximum)]
    if any(value is None for value in values):
        return minimum, q1, median, q3, maximum
    ordered = sorted(value for value in values if value is not None)
    return ordered[0], ordered[1], ordered[2], ordered[3], ordered[4]


def _run_decision_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    final_by_run = {str(row.get("run_id") or ""): row for row in result.final_report_runs or []}
    flags_by_run: dict[str, list[str]] = {}
    for flag in result.run_flags or []:
        run_id = str(flag.get("run_id") or "")
        if run_id:
            flags_by_run.setdefault(run_id, []).append(str(flag.get("flag") or flag.get("reason") or flag))
    for index, run_id in enumerate(_ordered_run_ids(result), start=1):
        final = final_by_run.get(run_id, {})
        rows.append(
            {
                "run_id": run_id,
                "run_label": _run_label(run_id, index),
                "included": final.get("included", final.get("final_included", "")),
                "selection_set": final.get("selection_set", "final_report_runs"),
                "selection_source": final.get("selection_source", ""),
                "decision": final.get("decision", ""),
                "reason": final.get("reason", ""),
                "flags": "; ".join(flags_by_run.get(run_id, [])),
            }
        )
    return rows


def _bending_summary_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    fields = (
        "run_id",
        "min_bending_percent",
        "q1_bending_percent",
        "median_bending_percent",
        "q3_bending_percent",
        "max_bending_percent",
        "bending_max_percent",
        "bending_mean_percent",
        "bending_median_percent",
        "bending_p95_percent",
        "bending_p99_percent",
        "bending_threshold_percent",
        "bending_points_above_threshold",
        "bending_fraction_above_threshold",
        "bending_pattern",
        "bending_pattern_confidence",
        "bending_pattern_reason",
    )
    rows: list[dict[str, Any]] = []
    for row in result.specimen_results:
        next_row = {field: row.get(field, "") for field in fields}
        maximum = row.get("max_bending_percent") or row.get("bending_max_percent") or ""
        median = row.get("median_bending_percent") or row.get("bending_median_percent") or ""
        p95 = row.get("p95_bending_percent") or row.get("bending_p95_percent") or maximum
        mean = row.get("bending_mean_percent") or median
        minimum, q1, median, q3, maximum = _ordered_five_number_values(
            row.get("min_bending_percent") or 0,
            row.get("q1_bending_percent") or mean or median,
            median,
            row.get("q3_bending_percent") or p95 or maximum,
            maximum,
        )
        next_row["max_bending_percent"] = maximum
        next_row["median_bending_percent"] = median
        next_row["q1_bending_percent"] = q1
        next_row["q3_bending_percent"] = q3
        next_row["min_bending_percent"] = minimum
        next_row["bending_max_percent"] = row.get("bending_max_percent") or maximum
        next_row["bending_median_percent"] = row.get("bending_median_percent") or median
        rows.append(next_row)
    return rows


def _stress_aggregate_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows = result.curve_shape_diagnostic_residual_rows or result.curve_family_aligned_rows or []
    grouped: dict[float, list[float]] = {}
    for row in rows:
        x_value = _float_or_none(row.get("x_common") or row.get("analysis_window_progress_percent"))
        y_value = _float_or_none(row.get("y_observed") or row.get("stress_MPa"))
        if x_value is None or y_value is None:
            continue
        grouped.setdefault(x_value, []).append(y_value)
    aggregate_rows: list[dict[str, Any]] = []
    for x_value in sorted(grouped):
        values = grouped[x_value]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0
        std_value = variance**0.5
        aggregate_rows.append(
            {
                "x_common": x_value,
                "mean_stress_MPa": mean_value,
                "min_stress_MPa": min(values),
                "max_stress_MPa": max(values),
                "std_stress_MPa": std_value,
                "lo_stress_MPa": mean_value - std_value,
                "hi_stress_MPa": mean_value + std_value,
                "run_count": len(values),
            }
        )
    return aggregate_rows


def _fmax_distribution_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    strengths = [
        value
        for row in result.specimen_results
        for value in [_float_or_none(row.get("compressive_strength_MPa") or row.get("max_stress_MPa"))]
        if value is not None
    ]
    if not strengths:
        return []
    ordered = sorted(strengths)
    mean_value = sum(ordered) / len(ordered)
    variance = sum((value - mean_value) ** 2 for value in ordered) / (len(ordered) - 1) if len(ordered) > 1 else 0.0
    return [
        {
            "x_position": 100,
            "label": "Fmax",
            "min_strength_MPa": ordered[0],
            "q1_strength_MPa": _interpolated_percentile(ordered, 25),
            "median_strength_MPa": _interpolated_percentile(ordered, 50),
            "q3_strength_MPa": _interpolated_percentile(ordered, 75),
            "max_strength_MPa": ordered[-1],
            "mean_strength_MPa": mean_value,
            "std_strength_MPa": variance**0.5,
            "run_count": len(ordered),
        }
    ]


def _interpolated_percentile(ordered: list[float], percentile: float) -> float:
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _audit_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.boundary_events or []:
        rows.append({"audit_type": "boundary_event", **event})
    for warning in result.warnings or []:
        rows.append({"audit_type": "warning", **warning})
    if not rows:
        rows.append({"audit_type": "status", "status": "no audit events recorded"})
    return rows


def _sanitize_audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = _rewrite_recommended_paths(payload)
    if not isinstance(sanitized, dict):
        return {}
    links = sanitized.get("artifact_links") if isinstance(sanitized.get("artifact_links"), dict) else {}
    links.pop("method_development_workbench", None)
    links["test_report"] = "report/test_report.html"
    links["dataset_plot"] = "dataset/05_plots/dataset_plot/dataset_plot.html"
    links["audit_report"] = "audit/audit_report.html"
    links["surface_manifest"] = "software/surface_manifest.json"
    sanitized["artifact_links"] = links
    return sanitized


def _recommended_report_quality_gate(files: dict[str, bytes]) -> dict[str, Any]:
    names = {*files, "archive_index.csv", "software/checksums.json", "software/surface_manifest.json"}
    report = _json_from_bytes(files.get("report/test_report.json")) or {}
    audit = _json_from_bytes(files.get("audit/audit_report.json")) or {}
    completion = report.get("report_completion_status") if isinstance(report.get("report_completion_status"), dict) else {}
    checks = [
        _recommended_member_check(
            "human_surfaces",
            names,
            [
                "index.html",
                "report/test_report.html",
                "report/test_report.pdf",
                "report/test_report.json",
                "dataset/05_plots/dataset_plot/dataset_plot.html",
                "audit/audit_report.html",
                "audit/audit_report.json",
            ],
        ),
        _recommended_member_check(
            "canonical_dataset_tables",
            names,
            [
                "dataset/04_aggregate/results_table.csv",
                "dataset/04_aggregate/statistics.csv",
                "dataset/04_aggregate/stress_strain_aligned.csv",
                "dataset/04_aggregate/characteristic_points.csv",
                "dataset/04_aggregate/run_decision_registry.csv",
                "dataset/04_aggregate/bending_summary_table.csv",
                "dataset/04_aggregate/missing_metadata_table.csv",
                "dataset/04_aggregate/report_completion_table.csv",
            ],
        ),
        _recommended_member_check(
            "source_lineage",
            names,
            [
                "dataset/00_source/source_mtdp_manifest.json",
                "dataset/00_source/source_dataset.json",
                "dataset/00_source/source_file_index.csv",
                "dataset/02_normalized/normalization_registry.csv",
            ],
        ),
        _recommended_report_completion_check(completion),
        _recommended_audit_links_check(audit),
    ]
    failures = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]
    return {
        "schema_id": "report.rc_quality_gate.v0_2",
        "layout": "mtda.recommended.v1",
        "overall_status": "RC_BLOCKED" if failures else "RC_WITH_WARNINGS" if warnings else "RC_READY",
        "surfaces": {
            "test_report": {
                "rc_status": "RC_BLOCKED"
                if any(check["surface"] == "test_report" and check["status"] == "fail" for check in checks)
                else "RC_WITH_WARNINGS"
                if any(check["surface"] == "test_report" and check["status"] == "warn" for check in checks)
                else "RC_READY",
                "failed_checks": [check["check_id"] for check in checks if check["surface"] == "test_report" and check["status"] == "fail"],
                "warning_checks": [check["check_id"] for check in checks if check["surface"] == "test_report" and check["status"] == "warn"],
            },
            "audit_report": {
                "rc_status": "RC_BLOCKED"
                if any(check["surface"] == "audit_report" and check["status"] == "fail" for check in checks)
                else "RC_READY",
                "failed_checks": [check["check_id"] for check in checks if check["surface"] == "audit_report" and check["status"] == "fail"],
                "warning_checks": [check["check_id"] for check in checks if check["surface"] == "audit_report" and check["status"] == "warn"],
            },
        },
        "cross_surface_agreement": {
            "source_package": report.get("source_package") or _nested(audit, "source_mtdp", "path") or "",
            "method_id": report.get("method_id") or _nested(audit, "method_package", "method_id") or "",
            "mapping_id": report.get("mapping_id") or _nested(audit, "mapping_profile", "mapping_id") or "",
            "readiness_status": _nested(audit, "readiness", "status") or "",
            "validation_status": _nested(audit, "validation", "status") or "",
            "report_completion_status": completion.get("status") or "",
        },
        "checks": checks,
    }


def _recommended_member_check(check_id: str, names: set[str], required: list[str]) -> dict[str, Any]:
    missing = [member for member in required if member not in names]
    return {
        "check_id": check_id,
        "surface": "shared",
        "status": "fail" if missing else "pass",
        "severity": "error" if missing else "info",
        "message": "Required recommended-layout members are present." if not missing else "Recommended-layout members are missing.",
        "evidence": {"required": required, "missing": missing},
    }


def _recommended_report_completion_check(completion: dict[str, Any]) -> dict[str, Any]:
    status = str(completion.get("status") or "")
    failed = not status
    warning = status in {"INCOMPLETE", "COMPLETE_WITH_WARNINGS"}
    return {
        "check_id": "test_report_completion_status",
        "surface": "test_report",
        "status": "fail" if failed else "warn" if warning else "pass",
        "severity": "error" if failed else "warning" if warning else "info",
        "message": f"Report completion status is {status or 'missing'}.",
        "evidence": completion,
    }


def _recommended_audit_links_check(audit: dict[str, Any]) -> dict[str, Any]:
    links = audit.get("artifact_links") if isinstance(audit.get("artifact_links"), dict) else {}
    expected = {
        "test_report": "report/test_report.html",
        "dataset_plot": "dataset/05_plots/dataset_plot/dataset_plot.html",
        "audit_report": "audit/audit_report.html",
        "surface_manifest": "software/surface_manifest.json",
    }
    mismatches = [key for key, value in expected.items() if links.get(key) != value]
    return {
        "check_id": "audit_report_recommended_links",
        "surface": "audit_report",
        "status": "fail" if mismatches else "pass",
        "severity": "error" if mismatches else "info",
        "message": "Audit report links point to recommended MTDA surfaces." if not mismatches else "Audit report links need recommended-layout updates.",
        "evidence": {"expected": expected, "mismatches": mismatches},
    }


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _recommended_provenance_events(
    result: MethodRunResult,
    *,
    compatibility_report: object,
    candidate_report: dict[str, object],
    resolution_report: dict[str, object],
) -> list[dict[str, Any]]:
    compatibility_status = getattr(getattr(compatibility_report, "status", None), "value", "")
    candidate_summary = candidate_report.get("summary", {}) if isinstance(candidate_report, dict) else {}
    resolution_summary = resolution_report.get("summary", {}) if isinstance(resolution_report, dict) else {}
    outputs = [
        "index.html",
        "archive_index.csv",
        "README.md",
        "report/test_report.html",
        "report/test_report.pdf",
        "report/test_report.json",
        "dataset/00_source/source_mtdp_manifest.json",
        "dataset/00_source/source_dataset.json",
        "dataset/00_source/source_file_index.csv",
        "dataset/02_normalized/normalization_registry.csv",
        "dataset/05_plots/dataset_plot/dataset_plot.html",
        "dataset/04_aggregate/results_table.csv",
        "dataset/04_aggregate/statistics.csv",
        "dataset/04_aggregate/stress_strain_aligned.csv",
        "dataset/04_aggregate/characteristic_points.csv",
        "dataset/04_aggregate/run_decision_registry.csv",
        "dataset/04_aggregate/bending_summary_table.csv",
        "dataset/04_aggregate/missing_metadata_table.csv",
        "dataset/04_aggregate/report_completion_table.csv",
        "audit/audit_report.html",
        "audit/audit_report.csv",
        "audit/audit_report.json",
        "software/manifest.json",
        "software/provenance.json",
        "software/validation.json",
        "software/readiness.json",
        "software/method_outputs.json",
        "software/surface_manifest.json",
        "software/checksums.json",
    ]
    return [
        {
            "event": "schema_method_compatibility_checked",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "status": compatibility_status,
            "artifact": "software/validation.json#schema_method_compatibility",
        },
        {
            "event": "mapping_candidates_generated",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "candidate_summary": candidate_summary,
            "artifact": "software/provenance.json#mapping.candidate_report",
        },
        {
            "event": "mapping_profile_confirmed",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "mapping_id": result.mapping.get("mapping_id"),
            "resolution_summary": resolution_summary,
            "artifact": "software/provenance.json#mapping.profile",
        },
        {
            "event": "readiness_checked_with_mapping",
            "timestamp": utc_now_iso(),
            "method_id": result.method_package.method_id,
            "mapping_id": result.mapping.get("mapping_id"),
            "readiness_status": result.readiness_report.get("status"),
            "artifact": "software/readiness.json#readiness_report",
        },
        {
            "event": "method_run_completed",
            "timestamp": utc_now_iso(),
            "software": "compression_module_method_run_layer",
            "software_version": "0.1.0",
            "method_id": result.method_package.method_id,
            "method_version": result.method_package.version,
            "inputs": [str(result.source.path)],
            "outputs": outputs,
        },
    ]


def _rewrite_recommended_paths(value: Any) -> Any:
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, item in value.items():
            if "workbench" in str(key).casefold():
                continue
            rewritten[key] = _rewrite_recommended_paths(item)
        return rewritten
    if isinstance(value, list):
        return [_rewrite_recommended_paths(item) for item in value]
    if isinstance(value, str):
        return _rewrite_recommended_text_paths(value)
    return value


def _rewrite_recommended_text_paths(text: str) -> str:
    replacements = {
        "interactive_report/index.html": "audit/audit_report.html",
        "compatibility/schema_method_compatibility_report.json": "software/validation.json#schema_method_compatibility",
        "compatibility/schema_method_compatibility_summary.csv": "software/validation.json#schema_method_compatibility",
        "mapping/mapping_profile_used.json": "software/provenance.json#mapping.profile",
        "mapping/mapping_candidate_report.json": "software/provenance.json#mapping.candidate_report",
        "mapping/mapping_resolution_report.json": "software/provenance.json#mapping.resolution_report",
        "readiness/readiness_report.json": "software/readiness.json#readiness_report",
        "readiness/readiness_summary.csv": "software/readiness.json#readiness_summary",
        "readiness/resolved_inputs.csv": "software/readiness.json#resolved_inputs",
        "readiness/missing_inputs.csv": "software/readiness.json#missing_inputs",
        "validation/validation_report.json": "software/validation.json#validation_report",
        "validation/validation_summary.csv": "software/validation.json#validation_summary",
        "validation/reference_values_used.csv": "software/validation.json#reference_values_used",
        "validation/deviations.csv": "software/validation.json#validation_deviations",
        "method_outputs/specimen_results.csv": "dataset/04_aggregate/results_table.csv",
        "method_outputs/dataset_summary.csv": "dataset/04_aggregate/statistics.csv",
        "method_outputs/dataset_summary_by_selection.csv": "dataset/04_aggregate/statistics.csv",
        "method_outputs/boundaries.csv": "software/method_outputs.json#experiment_boundaries",
        "method_outputs/curves/stress_strain_family.csv": "dataset/04_aggregate/stress_strain_aligned.csv",
        "method_outputs/curves/stress_strain_family_bounded.csv": "dataset/04_aggregate/stress_strain_aligned.csv",
        "method_outputs/curves/stress_strain_family_full.csv": "software/method_outputs.json#curve_family_full",
        "method_outputs/curves/{run_id}_stress_strain_full.csv": "dataset/03_processed/{run_id}_stress_strain.csv",
        "method_outputs/curves/{run_id}_stress_strain_bounded.csv": "dataset/03_processed/{run_id}_stress_strain_experiment_bound.csv",
        "method_outputs/curves/{run_id}_stress_strain.csv": "dataset/03_processed/{run_id}_stress_strain_experiment_bound.csv",
        "audit/operation_log.json": "software/method_outputs.json#operation_trace",
        "audit/procedure_evidence_index.json": "audit/audit_report.json#procedure_evidence",
        "audit/audit_blocks.json": "audit/audit_report.json#audit_blocks",
        "audit/audit_block_index.json": "audit/audit_report.json#audit_blocks",
        "audit/boundary_resolution.json": "audit/audit_report.json#experiment_boundary_resolution",
        "audit/boundary_events.csv": "audit/audit_report.csv",
        "workbench/operation_trace.json": "software/method_outputs.json#operation_trace",
        "workbench/index.html": "software/method_outputs.json",
    }
    rewritten = text
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain_full\.csv",
        r"dataset/03_processed/\1_stress_strain.csv",
        rewritten,
    )
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain_bounded\.csv",
        r"dataset/03_processed/\1_stress_strain_experiment_bound.csv",
        rewritten,
    )
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain\.csv",
        r"dataset/03_processed/\1_stress_strain_experiment_bound.csv",
        rewritten,
    )
    for old, new in replacements.items():
        rewritten = rewritten.replace(old, new)
    return re.sub(r"(?<!software/)surface_manifest\.json", "software/surface_manifest.json", rewritten)


def _rewrite_aligned_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _rewrite_aligned_paths(item) for key, item in value.items() if "workbench" not in str(key).casefold()}
    if isinstance(value, list):
        return [_rewrite_aligned_paths(item) for item in value]
    if isinstance(value, str):
        return _rewrite_aligned_text_paths(value)
    return value


def _rewrite_aligned_text_paths(text: str) -> str:
    rewritten = text
    replacements = {
        "../report/test_report.html": "test_report.html",
        "../report/test_report.json": "test_report.json",
        "../report/test_report.pdf": "test_report.pdf",
        "../audit/audit_report.html": "audit_report.html",
        "../audit/audit_report.json": "audit_report.json",
        "../audit/audit_report.csv": "audit_report.csv",
        "report/test_report.html": f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        "report/test_report.json": f"{MTDAAlignedLayout.reports_prefix}test_report.json",
        "report/test_report.pdf": f"{MTDAAlignedLayout.reports_prefix}test_report.pdf",
        "report/report_completion_status.json": f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_completion_status",
        "report/report_field_catalog_resolved.json": f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_field_catalog_resolved",
        "report/report_values_used.csv": f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_values_used",
        "report/report_override_ledger.json": f"{MTDAAlignedLayout.reports_prefix}test_report.json#report_override_ledger",
        "report/aggregate_statistics.csv": f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv",
        "report/aligned_curves.csv": f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
        "report/characteristic_points.csv": f"{MTDAAlignedLayout.aggregate_prefix}characteristic_points.csv",
        "report/missing_report_fields.csv": f"{MTDAAlignedLayout.aggregate_prefix}missing_metadata_table.csv",
        "report/report_completeness_summary.csv": f"{MTDAAlignedLayout.aggregate_prefix}report_completion_table.csv",
        "audit/audit_report.html": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
        "audit/audit_report.json": f"{MTDAAlignedLayout.reports_prefix}audit_report.json",
        "audit/audit_report.csv": f"{MTDAAlignedLayout.reports_prefix}audit_report.csv",
        "audit/procedure_evidence_index.json": f"{MTDAAlignedLayout.reports_prefix}audit_report.json#procedure_evidence",
        "audit/audit_blocks.json": f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks",
        "audit/audit_block_index.json": f"{MTDAAlignedLayout.reports_prefix}audit_report.json#audit_blocks",
        "audit/boundary_resolution.json": f"{MTDAAlignedLayout.reports_prefix}audit_report.json#experiment_boundary_resolution",
        "audit/boundary_events.csv": f"{MTDAAlignedLayout.reports_prefix}audit_report.csv",
        "interactive_report/index.html": f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
        "readiness/readiness_report.json": f"{MTDAAlignedLayout.readiness}#readiness_report",
        "readiness/readiness_summary.csv": f"{MTDAAlignedLayout.readiness}#readiness_summary",
        "readiness/resolved_inputs.csv": f"{MTDAAlignedLayout.readiness}#resolved_inputs",
        "readiness/missing_inputs.csv": f"{MTDAAlignedLayout.readiness}#missing_inputs",
        "validation/validation_report.json": f"{MTDAAlignedLayout.validation}#validation_report",
        "validation/validation_summary.csv": f"{MTDAAlignedLayout.validation}#validation_summary",
        "validation/reference_values_used.csv": f"{MTDAAlignedLayout.validation}#reference_values_used",
        "validation/deviations.csv": f"{MTDAAlignedLayout.validation}#validation_deviations",
        "acceptance/acceptance_report.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report",
        "acceptance/acceptance_summary.csv": f"{MTDAAlignedLayout.method_outputs}#acceptance_summary",
        "acceptance/run_flags.csv": f"{MTDAAlignedLayout.method_outputs}#run_flags",
        "acceptance/selection_sets.json": f"{MTDAAlignedLayout.method_outputs}#selection_sets",
        "acceptance/selection_membership.csv": f"{MTDAAlignedLayout.method_outputs}#selection_membership",
        "acceptance/discharged_runs.csv": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/discharge_report",
        "acceptance/discharge_report.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/discharge_report",
        "acceptance/selection_sets_final.json": f"{MTDAAlignedLayout.method_outputs}#selection_sets",
        "acceptance/selection_membership_final.csv": f"{MTDAAlignedLayout.method_outputs}#selection_membership",
        "acceptance/final_report_runs.csv": f"{MTDAAlignedLayout.method_outputs}#final_report_runs",
        "acceptance/human_decisions.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report",
        "acceptance/override_ledger.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report",
        "acceptance/curve_family/curve_family_report.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/curve_family_assessment",
        "acceptance/curve_family/curve_family_scores.csv": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/curve_family_assessment",
        "acceptance/curve_family/curve_family_flags.csv": f"{MTDAAlignedLayout.method_outputs}#run_flags",
        "acceptance/curve_family/reference_curves.csv": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/curve_family_assessment",
        "acceptance/curve_family/aligned_curve_family.csv": f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
        "acceptance/curve_family/residuals_long.csv": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/curve_family_assessment",
        "acceptance/curve_family/policy_resolved.json": f"{MTDAAlignedLayout.method_outputs}#acceptance_report/curve_family_assessment",
        "acceptance/curve_family/curve_diagnostic_report.json": f"{MTDAAlignedLayout.method_outputs}#curve_shape_diagnostic_report",
        "acceptance/curve_family/curve_diagnostic_scores.csv": f"{MTDAAlignedLayout.method_outputs}#curve_shape_diagnostic_scores",
        "acceptance/curve_family/curve_diagnostic_reference_curve.csv": f"{MTDAAlignedLayout.method_outputs}#curve_shape_diagnostic_report/artifact_manifest",
        "acceptance/curve_family/curve_diagnostic_residuals.csv": f"{MTDAAlignedLayout.method_outputs}#curve_shape_diagnostic_report/artifact_manifest",
        "acceptance/curve_family/curve_diagnostic_policy.json": f"{MTDAAlignedLayout.method_outputs}#curve_shape_diagnostic_report/artifact_manifest",
        "acceptance/curve_family/curve_diagnostic_flags.csv": f"{MTDAAlignedLayout.method_outputs}#run_flags",
        "method_outputs/specimen_results.csv": f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv",
        "method_outputs/dataset_summary.csv": f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv",
        "method_outputs/dataset_summary_by_selection.csv": f"{MTDAAlignedLayout.aggregate_prefix}statistics.csv",
        "method_outputs/boundaries.csv": f"{MTDAAlignedLayout.method_outputs}#experiment_boundaries",
        "method_outputs/curves/stress_strain_family.csv": f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
        "method_outputs/curves/stress_strain_family_bounded.csv": f"{MTDAAlignedLayout.aggregate_prefix}stress_strain_aligned.csv",
        "method_outputs/curves/stress_strain_family_full.csv": f"{MTDAAlignedLayout.method_outputs}#curve_family_full",
        "dataset/04_aggregate/": MTDAAlignedLayout.aggregate_prefix,
        "dataset/03_processed/": MTDAAlignedLayout.processed_prefix,
        "dataset/02_normalized/": MTDAAlignedLayout.normalized_prefix,
        "dataset/01_raw/": MTDAAlignedLayout.raw_prefix,
    }
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain_full\.csv",
        lambda match: f"{MTDAAlignedLayout.processed_prefix}{match.group(1)}_stress_strain.csv",
        rewritten,
    )
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain_bounded\.csv",
        lambda match: f"{MTDAAlignedLayout.processed_prefix}{match.group(1)}_stress_strain_experiment_bound.csv",
        rewritten,
    )
    rewritten = re.sub(
        r"method_outputs/curves/([A-Za-z0-9_-]+)_stress_strain\.csv",
        lambda match: f"{MTDAAlignedLayout.processed_prefix}{match.group(1)}_stress_strain_experiment_bound.csv",
        rewritten,
    )
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(old, new)
    rewritten = re.sub(r"(?<!metadata/)software/manifest\.json", MTDAAlignedLayout.manifest, rewritten)
    rewritten = re.sub(r"(?<!metadata/)software/provenance\.json", MTDAAlignedLayout.provenance, rewritten)
    rewritten = re.sub(r"(?<!metadata/)software/validation\.json", MTDAAlignedLayout.validation, rewritten)
    rewritten = re.sub(r"(?<!metadata/)software/readiness\.json", MTDAAlignedLayout.readiness, rewritten)
    rewritten = re.sub(r"(?<!metadata/)software/method_outputs\.json", MTDAAlignedLayout.method_outputs, rewritten)
    rewritten = re.sub(r"(?<!metadata/)software/checksums\.json", MTDAAlignedLayout.checksums, rewritten)
    return re.sub(r"(?<!metadata/)surface_manifest\.json", MTDAAlignedLayout.surface_manifest, rewritten)


def _method_outputs_payload(result: MethodRunResult, legacy_files: dict[str, bytes], workbench_trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": "mtda.method_outputs_bundle.v0_1",
        "specimen_results": result.specimen_results,
        "dataset_summary": result.dataset_summary,
        "dataset_summary_by_selection": result.dataset_summary_by_selection,
        "curve_family": result.curve_family,
        "bounded_curve_family": result.bounded_curve_family or result.curve_family,
        "curve_family_full": result.full_curve_family or [],
        "experiment_boundaries": result.experiment_boundaries or [],
        "boundary_events": result.boundary_events or [],
        "acceptance_report": result.acceptance_report,
        "acceptance_summary": result.acceptance_summary,
        "run_flags": result.run_flags,
        "selection_sets": result.selection_sets,
        "selection_membership": result.selection_membership,
        "final_report_runs": result.final_report_runs or [],
        "curve_shape_diagnostic_report": result.curve_shape_diagnostic_report or {},
        "curve_shape_diagnostic_scores": result.curve_shape_diagnostic_scores or [],
        "operation_trace": workbench_trace,
        "legacy_member_count": len(legacy_files),
    }


def _compact_plot_package_files(
    *,
    plot_id: str,
    plot_type: str,
    title: str,
    spec: dict[str, Any],
    html_member: str,
    source_refs: list[str],
    supplemental_datasets: list[dict[str, Any]] | None = None,
    plot_data_views: list[dict[str, Any]] | None = None,
    plot_data_materialization: str = "none",
) -> dict[str, bytes]:
    base = PurePosixPath(html_member).parent
    template_member = str(base / f"{plot_id}.template.json")
    package_member = str(base / f"{plot_id}.plot_package.json")
    data_prefix = str(base / f"{plot_id}_data")
    template, datasets, data_files, embedded_rows = _extract_compact_plot_datasets(spec, data_prefix=data_prefix)
    views_by_dataset = {str(view.get("dataset_id")): view for view in plot_data_views or []}
    for supplemental in supplemental_datasets or []:
        rows = _rows_from_values(supplemental.get("rows") or [])
        dataset_id = _safe_plot_id(str(supplemental.get("dataset_id") or f"dataset_{len(datasets) + 1:03d}"))
        existing_ids = {str(dataset.get("dataset_id")) for dataset in datasets}
        if dataset_id in existing_ids:
            dataset_id = f"{dataset_id}_{len(datasets) + 1:03d}"
        member = f"{data_prefix}/{dataset_id}.csv"
        data_files[member] = write_dict_rows(rows).encode("utf-8")
        embedded_rows[dataset_id] = rows
        datasets.append(
            {
                "dataset_id": dataset_id,
                "format": "csv",
                "path": _relative_member_path(data_prefix.rsplit("/", 1)[0], member),
                "member": member,
                "fields": _field_order(rows),
                "row_count": len(rows),
                "role": str(supplemental.get("role") or dataset_id),
            }
        )
    if plot_data_materialization == "none":
        data_files = {}
        embedded_rows = {}
    projection_metadata = _compact_projection_metadata(plot_type)
    package = {
        "package_type": "compact-vegalite-workbench",
        "schema_version": "0.1",
        "plot_id": plot_id,
        "plot_type": plot_type,
        **projection_metadata,
        "title": title,
        "data_mode": "archive_view" if plot_data_materialization == "none" else "external_csv",
        "view_data_mode": "runtime_resolved" if plot_data_materialization == "none" else "embedded_rows_preferred",
        "template": template,
        "embedded_datasets": [
            {
                **dataset,
                "rows": embedded_rows.get(str(dataset.get("dataset_id")), []),
            }
            for dataset in datasets
        ] if plot_data_materialization != "none" else [],
        "template_member": template_member,
        "template_path": f"{plot_id}.template.json",
        "html_member": html_member,
        "datasets": [_dataset_with_view(dataset, views_by_dataset) for dataset in datasets],
        "data_refs": [_dataset_with_view(dataset, views_by_dataset) for dataset in datasets],
        "plot_data_views": [_plot_data_view_payload(view) for view in (plot_data_views or [])],
        "plot_data_materialization": plot_data_materialization,
        "semantic_layers": _compact_semantic_layers(template),
        "source_refs": list(source_refs),
        "state_model": {
            "originalPackage": "immutable compact package loaded from archive members",
            "workingPackage": "browser working copy for edits and exports",
            "currentSpec": "hydrated Vega-Lite render/export spec built in memory",
        },
        "exports": {
            "settings_only": f"{plot_id}.settings_only.plot_profile.json",
            "data_only": f"{plot_id}.{{dataset_id}}.data_only.csv",
            "plot_image": [f"{plot_id}.svg", f"{plot_id}.png"],
            "plot_spec_hydrated_data": f"{plot_id}.full_vegalite_spec_with_data.vl.json",
            "compact_plot_package_data": f"{plot_id}.full_plot_package_with_data.json",
        },
    }
    return {
        template_member: json_bytes(template),
        package_member: json_bytes(package),
        **data_files,
    }


@lru_cache(maxsize=1)
def _projection_recipe_catalog() -> dict[str, dict[str, Any]]:
    return load_recipe_catalog()


def _compact_projection_metadata(plot_type: str) -> dict[str, Any]:
    projection_id = _COMPACT_PLOT_PROJECTION_BY_TYPE.get(plot_type)
    if not projection_id:
        return {}
    recipe = _projection_recipe_catalog()[projection_id]
    recipe_version = str(recipe.get("version") or "")
    recipe_schema_version = str(recipe.get("schema_version") or "")
    golden_id = str(recipe.get("golden_id") or "")
    production_state = str(recipe.get("production_state") or "")
    return {
        "projection_id": projection_id,
        "recipe_version": recipe_version,
        "recipe_schema_version": recipe_schema_version,
        "golden_id": golden_id,
        "production_state": production_state,
        "projection_recipe": {
            "projection_id": projection_id,
            "plot_type": str(recipe.get("plot_type") or plot_type),
            "version": recipe_version,
            "schema_version": recipe_schema_version,
            "golden_id": golden_id,
            "production_state": production_state,
            "catalog_path": f"src/plotting/recipes/catalog/{projection_id}.yaml",
        },
        "projection_contracts": {
            "data_contract": recipe.get("data_contract") or {},
            "semantic_contract": recipe.get("semantic_contract") or {},
            "quality_contract": recipe.get("quality_contract") or {},
            "staleness_contract": recipe.get("staleness_contract") or {},
            "artifact_contract": recipe.get("artifact_contract") or {},
            "transform_ids": list(recipe.get("transform_ids") or []),
        },
    }


def _dataset_with_view(dataset: dict[str, Any], views_by_dataset: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dataset_id = str(dataset.get("dataset_id") or "")
    view = views_by_dataset.get(dataset_id)
    if not view:
        return dict(dataset)
    next_dataset = dict(dataset)
    next_dataset["view_ref"] = dataset_id
    next_dataset["source_members"] = list(view.get("source_members") or [])
    next_dataset["transform_id"] = str(view.get("transform_id") or "")
    return next_dataset


def _plot_data_view_payload(view: dict[str, Any]) -> dict[str, Any]:
    transform_id = str(view.get("transform_id") or "")
    transform_version = TRANSFORM_VERSIONS.get(transform_id, "1.0.0")
    return {
        **view,
        "data_view_schema_version": "mtda.plot_data_view.v0_1",
        "data_view_version": transform_version,
        "transform_version": transform_version,
        "implementation": "mtda.runtime.plot_views",
        "source_checksum_policy": "must_match_archive_checksum",
        "source_checksum_member": MTDAAlignedLayout.checksums,
    }


def _run_plot_data_views(run_label: str) -> list[dict[str, Any]]:
    source = f"{MTDAAlignedLayout.processed_prefix}{run_label}_stress_strain_experiment_bound.csv"
    specs = [
        ("dataset_001", "front rear strain agreement envelope", "run.front_rear_strain_envelope.v1"),
        ("dataset_002", "front rear strain traces", "run.front_rear_strain_traces.v1"),
        ("dataset_003", "bounded average strain curve", "run.bounded_average_curve.v1"),
        ("dataset_004", "empty chord line", "run.empty_chord_line.v1"),
        ("dataset_005", "empty chord points", "run.empty_chord_points.v1"),
        ("dataset_006", "analysis markers", "run.analysis_markers.v1"),
    ]
    return [
        {
            "dataset_id": dataset_id,
            "role": role,
            "source_members": [source],
            "transform_id": transform_id,
            "fields": RUN_VIEW_FIELDS[transform_id],
        }
        for dataset_id, role, transform_id in specs
    ]


def _dataset_plot_data_views(result: MethodRunResult) -> list[dict[str, Any]]:
    run_sources = [
        f"{MTDAAlignedLayout.processed_prefix}{_run_label(run_id, index)}_stress_strain_experiment_bound.csv"
        for index, run_id in enumerate(_ordered_run_ids(result), start=1)
    ]
    bending_source = f"{MTDAAlignedLayout.aggregate_prefix}bending_summary_table.csv"
    results_source = f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv"
    specs = [
        (
            "dataset_001",
            "all runs resampled curve family",
            run_sources,
            "aggregate.all_runs_resampled_curve_family.v1",
            250 * len(run_sources),
        ),
        (
            "stress_aggregate",
            "stress aggregate band",
            run_sources,
            "aggregate.stress_band_from_run_grid.v1",
            249 if run_sources else 0,
        ),
        (
            "bending_summary",
            "bending summary",
            [bending_source],
            "aggregate.bending_summary_passthrough.v1",
            len(_bending_summary_rows(result)),
        ),
        (
            "fmax_distribution",
            "Fmax distribution",
            [results_source],
            "aggregate.fmax_distribution.v1",
            1 if result.specimen_results else 0,
        ),
    ]
    return [
        {
            "dataset_id": dataset_id,
            "role": role,
            "source_members": source_members,
            "transform_id": transform_id,
            "fields": AGGREGATE_VIEW_FIELDS[transform_id],
            "expected_row_count": expected_rows,
        }
        for dataset_id, role, source_members, transform_id, expected_rows in specs
    ]


def _extract_compact_plot_datasets(
    spec: dict[str, Any],
    *,
    data_prefix: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, bytes], dict[str, list[dict[str, Any]]]]:
    datasets: list[dict[str, Any]] = []
    files: dict[str, bytes] = {}
    embedded_rows: dict[str, list[dict[str, Any]]] = {}

    def visit(value: Any, role_hint: str = "plot_data") -> Any:
        if isinstance(value, dict):
            data = value.get("data")
            if isinstance(data, dict) and isinstance(data.get("values"), list):
                dataset_id = f"dataset_{len(datasets) + 1:03d}"
                rows = _rows_from_values(data.get("values") or [])
                fields = _field_order(rows)
                member = f"{data_prefix}/{dataset_id}.csv"
                files[member] = write_dict_rows(rows).encode("utf-8")
                embedded_rows[dataset_id] = rows
                datasets.append(
                    {
                        "dataset_id": dataset_id,
                        "format": "csv",
                        "path": _relative_member_path(data_prefix.rsplit("/", 1)[0], member),
                        "member": member,
                        "fields": fields,
                        "row_count": len(rows),
                        "role": str(value.get("name") or data.get("name") or role_hint),
                    }
                )
                rewritten = {key: visit(item, key) for key, item in value.items() if key != "data"}
                rewritten["data"] = {"__compact_dataset_ref__": dataset_id}
                return rewritten
            return {key: visit(item, key) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item, role_hint) for item in value]
        return value

    template = visit(spec)
    return template if isinstance(template, dict) else {}, datasets, files, embedded_rows


def _rows_from_values(values: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value in values:
        rows.append(dict(value) if isinstance(value, dict) else {"value": value})
    return rows


def _field_order(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(str(key))
    return fields


def _compact_semantic_layers(template: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    usermeta = template.get("usermeta") if isinstance(template.get("usermeta"), dict) else {}
    semantic_ids = usermeta.get("semantic_layers") if isinstance(usermeta.get("semantic_layers"), list) else []
    for layer_id in semantic_ids:
        layers.append({"layer_id": str(layer_id), "semantic_role": str(layer_id).replace("_", " ")})
    for index, layer in enumerate(template.get("layer") if isinstance(template.get("layer"), list) else []):
        if isinstance(layer, dict):
            name = str(layer.get("name") or f"layer_{index + 1}")
            if not any(item["layer_id"] == name for item in layers):
                layers.append({"layer_id": name, "semantic_role": name.replace("_", " ")})
    return layers


def _relative_member_path(from_member: str, to_member: str) -> str:
    from_parts = PurePosixPath(from_member).parts
    to_parts = PurePosixPath(to_member).parts
    common = 0
    for left, right in zip(from_parts, to_parts):
        if left != right:
            break
        common += 1
    return "/".join([".."] * (len(from_parts) - common) + list(to_parts[common:])) or PurePosixPath(to_member).name


def _dataset_plot_spec(result: MethodRunResult) -> dict[str, Any]:
    values = result.curve_shape_diagnostic_residual_rows or result.curve_family_aligned_rows or []
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Dataset stress-strain aggregate plot.",
        "data": {"values": values[:5000]},
        "mark": {"type": "line"},
        "encoding": {
            "x": {"field": "x_common", "type": "quantitative", "title": "Aligned strain / progress"},
            "y": {"field": "y_observed", "type": "quantitative", "title": "Stress / MPa"},
            "color": {"field": "run_id", "type": "nominal"},
        },
    }


def _run_stress_evidence_plot_spec(
    run_id: str,
    full_rows: list[dict[str, Any]],
    bounded_rows: list[dict[str, Any]],
    specimen: dict[str, Any],
) -> dict[str, Any]:
    plot_result = plot_registry.build(
        stress_strain_reduction_request(
            plot_id=f"{_safe_plot_id(run_id)}_stress_strain_evidence_plot",
            run_id=run_id,
            bounded_rows=bounded_rows,
            block=_stress_evidence_plot_block(run_id, specimen),
            surface_context="export",
        )
    )
    if plot_result.spec:
        return plot_result.spec
    return _unavailable_plot_spec(plot_result.fallback_message or "Stress-strain evidence plot unavailable for this run.")


def _stress_evidence_plot_block(
    run_id: str,
    specimen: dict[str, Any],
) -> dict[str, Any]:
    start_index = _float_or_none(specimen.get("boundary_start_index"))
    end_index = _float_or_none(specimen.get("boundary_end_index"))
    max_index = _float_or_none(specimen.get("max_load_point_index") or specimen.get("max_load_index") or end_index)
    strength = _float_or_none(specimen.get("compressive_strength_MPa"))
    markers: dict[str, Any] = {
        "experiment_start": {"index": start_index},
        "experiment_end": {"index": end_index},
        "max_load_strength": {"index": max_index, "stress_MPa": strength},
    }
    chord = _stress_chord_line(specimen)
    if chord:
        markers["chord_line"] = chord
    return {
        "run_id": run_id,
        "markers": markers,
        "summary": {
            "boundary_end_policy": specimen.get("boundary_end_policy") or "",
            "boundary_reason": specimen.get("boundary_reason") or "",
        },
    }


def _stress_chord_line(specimen: dict[str, Any]) -> dict[str, float] | None:
    x_start = 0.0005
    x_end = 0.0025
    y_start = _float_or_none(
        specimen.get("chord_stress_at_0_0005_MPa")
        or specimen.get("stress_at_0_0005")
        or specimen.get("stress_at_0.0005")
    )
    y_end = _float_or_none(
        specimen.get("chord_stress_at_0_0025_MPa")
        or specimen.get("stress_at_0_0025")
        or specimen.get("stress_at_0.0025")
    )
    if y_start is None or y_end is None:
        return None
    return {"x_start": x_start, "y_start": y_start, "x_end": x_end, "y_end": y_end}


def _run_debug_plot_spec(run_id: str, full_rows: list[dict[str, Any]], bounded_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def values_for(scope: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for row in rows[:3000]:
            values.append(
                {
                    "scope": scope,
                    "strain": row.get("mean_strain", row.get("strain_mm_per_mm")),
                    "stress": row.get("stress_MPa"),
                    "point_index": row.get("point_index"),
                    "run_id": run_id,
                }
            )
        return values

    x_encoding = {"field": "strain", "type": "quantitative", "title": "Strain / mm/mm"}
    y_encoding = {"field": "stress", "type": "quantitative", "title": "Stress / MPa"}
    tooltip = [
        {"field": "scope", "type": "nominal"},
        {"field": "point_index", "type": "quantitative"},
        {"field": "strain", "type": "quantitative"},
        {"field": "stress", "type": "quantitative"},
    ]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": f"Run stress-strain summary plot for {run_id}.",
        "layer": [
            {
                "name": "experiment-bound stress-strain curve",
                "data": {"values": values_for("experiment-bound", bounded_rows)},
                "mark": {"type": "line", "strokeWidth": 2.4, "opacity": 0.95, "color": "#1f78b4", "clip": True},
                "encoding": {"x": dict(x_encoding), "y": dict(y_encoding), "tooltip": tooltip},
            },
            {
                "name": "full stress-strain curve",
                "data": {"values": values_for("full", full_rows)},
                "mark": {"type": "line", "strokeWidth": 1.2, "opacity": 0.35, "color": "#94b9d7", "clip": True},
                "encoding": {"x": dict(x_encoding), "y": dict(y_encoding), "tooltip": tooltip},
            },
        ],
    }


def _run_bending_plot_spec(result: MethodRunResult, run_id: str, bounded_rows: list[dict[str, Any]]) -> dict[str, Any]:
    plot_result = plot_registry.build(
        bending_evidence_request(
            plot_id=f"{_safe_plot_id(run_id)}_bending_plot",
            run_id=run_id,
            bounded_rows=bounded_rows,
            block=_bending_plot_block(result, run_id),
            surface_context="export",
        )
    )
    if plot_result.spec:
        return plot_result.spec
    return _unavailable_plot_spec(plot_result.fallback_message or "Bending plot unavailable for this run.")


def _bending_plot_block(result: MethodRunResult, run_id: str) -> dict[str, Any]:
    diagnostic = _nested(result.reduce_summary or {}, "runs", run_id, "diagnostics", "bending_diagnostic")
    diagnostic = diagnostic if isinstance(diagnostic, dict) else {}
    pattern = diagnostic.get("pattern") if isinstance(diagnostic.get("pattern"), dict) else {}
    window = diagnostic.get("window") if isinstance(diagnostic.get("window"), dict) else {}
    threshold = _float_or_none(diagnostic.get("threshold_percent"))
    lower = _float_or_none(window.get("lower_load_N"))
    upper = _float_or_none(window.get("upper_load_N"))
    markers: dict[str, Any] = {}
    if threshold is not None:
        markers["threshold_line"] = {"bending_percent": threshold}
    if lower is not None or upper is not None:
        markers["assessment_window_10_90_fmax"] = {
            "lower_load_N": lower,
            "upper_load_N": upper,
            "load_window_N": [lower, upper],
        }
    segments = diagnostic.get("segments")
    if isinstance(segments, list):
        markers["exceedance_segments"] = segments
    return {
        "run_id": run_id,
        "summary": {
            "threshold_percent": threshold,
            "classification": diagnostic.get("pattern_classification")
            or diagnostic.get("classification")
            or pattern.get("classification")
            or "",
        },
        "markers": markers,
    }


def _unavailable_plot_spec(message: str) -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": message,
        "width": "container",
        "height": 220,
        "data": {"values": [{"message": message}]},
        "mark": {"type": "text", "fontSize": 14, "color": "#5f5f5f"},
        "encoding": {"text": {"field": "message", "type": "nominal"}},
    }


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_plot_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "run"


def _plot_wrapper_html(
    *,
    title: str,
    spec_path: str = "",
    spec: dict[str, Any] | None = None,
    package_path: str = "",
    home_path: str = "../../../index.html",
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_plot_wrapper_html(
            title=title,
            spec_path=spec_path,
            spec=spec,
            package_path=package_path,
            home_path=home_path,
        )
    if package_path:
        return _compact_plot_wrapper_html(title=title, package_path=package_path, home_path=home_path)
    spec_json = json.dumps(spec or {}, ensure_ascii=False)
    return render_plot_wrapper(
        plot_wrapper_context(
            title=title,
            spec_path=spec_path,
            spec_json=spec_json,
            home_path=home_path,
        )
    )


def _legacy_plot_wrapper_html(
    *,
    title: str,
    spec_path: str = "",
    spec: dict[str, Any] | None = None,
    package_path: str = "",
    home_path: str = "../../../index.html",
) -> str:
    if package_path:
        return _legacy_compact_plot_wrapper_html(title=title, package_path=package_path, home_path=home_path)
    spec = spec or {}
    spec_json = json.dumps(spec, ensure_ascii=False)
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>__TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<style>
:root{color-scheme:light;--line:#d7dde5;--ink:#17202a;--muted:#5b6470;--panel:#f8fafc;--blue:#0b5cad}
*{box-sizing:border-box}body{font-family:Arial,sans-serif;margin:0;color:var(--ink);line-height:1.35;background:white}
a{color:var(--blue)}main{padding:24px;max-width:1440px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
h1{font-size:28px;margin:18px 0 8px}.hint{color:var(--muted);margin:0 0 16px}
.workspace{display:grid;grid-template-columns:minmax(260px,320px) minmax(560px,1fr);gap:18px;align-items:start}
.plot-controls{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:14px;position:sticky;top:16px}
.control-group{border:0;border-top:1px solid var(--line);margin:12px 0 0;padding:12px 0 0}.control-group:first-child{border-top:0;margin-top:0;padding-top:0}
legend{font-weight:700;padding:0 6px 0 0}.field{display:grid;grid-template-columns:92px minmax(0,1fr);gap:8px;align-items:center;margin:8px 0}
.field label,.check label{font-size:13px;color:#26313d}.field input,.field select{width:100%;min-width:0;border:1px solid #c9d2dd;border-radius:6px;padding:6px;background:white}
.split{display:grid;grid-template-columns:1fr 1fr;gap:8px}.check{display:flex;gap:8px;align-items:center;margin:7px 0}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
button{border:1px solid #b9c6d3;background:white;border-radius:6px;padding:7px 10px;cursor:pointer}button.primary{background:#0b5cad;color:white;border-color:#0b5cad}
.chart-shell{min-width:0;border:1px solid var(--line);border-radius:8px;padding:16px;background:white}.chart{width:100%;min-height:520px}
.status{font-size:12px;color:var(--muted);margin-top:8px}.vega-actions{font-size:12px}
@media (max-width:900px){main{padding:14px}.workspace{grid-template-columns:1fr}.plot-controls{position:static}.chart-shell{padding:10px}.chart{min-height:380px}}
</style></head>
<body><main>
<div class="topbar"><p><a href="__HOME_PATH__">Back to home</a></p><p class="hint"><a href="__SPEC_PATH__">Canonical Vega-Lite JSON</a></p></div>
<h1 id="pageTitle">__TITLE__</h1>
<div class="workspace">
<aside class="plot-controls" id="controls">
<fieldset class="control-group"><legend>View</legend><div id="layerControls"></div></fieldset>
<fieldset class="control-group"><legend>Axis range</legend>
<div class="split"><div class="field"><label for="xMin">x min</label><input id="xMin" inputmode="decimal"></div><div class="field"><label for="xMax">x max</label><input id="xMax" inputmode="decimal"></div></div>
<div class="split"><div class="field"><label for="yMin">y min</label><input id="yMin" inputmode="decimal"></div><div class="field"><label for="yMax">y max</label><input id="yMax" inputmode="decimal"></div></div>
</fieldset>
<fieldset class="control-group"><legend>Axis labels</legend>
<div class="field"><label for="xLabel">x label</label><input id="xLabel"></div>
<div class="field"><label for="yLabel">y label</label><input id="yLabel"></div>
</fieldset>
<fieldset class="control-group"><legend>Style</legend>
<div class="field"><label for="lineWidth">line</label><input id="lineWidth" type="range" min="0.25" max="3" step="0.25" value="1"></div>
<div class="field"><label for="opacity">opacity</label><input id="opacity" type="range" min="0.05" max="1" step="0.05" value="1"></div>
<div class="field"><label for="pointSize">point</label><input id="pointSize" type="range" min="0.5" max="3" step="0.25" value="1"></div>
</fieldset>
<fieldset class="control-group"><legend>Bending</legend>
<div class="field"><label for="bendingMode">display</label><select id="bendingMode"><option value="overlay">overlay</option><option value="secondary">secondary axis</option><option value="normalized">normalized</option><option value="hidden">hidden</option></select></div>
</fieldset>
<fieldset class="control-group"><legend>Labels</legend>
<div class="field"><label for="pointLabels">points</label><select id="pointLabels"><option value="show">show labels</option><option value="hide">hide labels</option></select></div>
<div class="field"><label for="plotTitle">title</label><input id="plotTitle"></div>
</fieldset>
<div class="buttons"><button class="primary" id="applyControls">Apply</button><button id="resetControls">Reset</button><button id="downloadSvg">SVG</button><button id="downloadPng">PNG</button><button id="downloadSpec">Spec</button></div>
<div class="status" id="plotStatus"></div>
</aside>
<section class="chart-shell"><div id="plot" class="chart"></div></section>
</div>
</main>
<script>
const spec = __SPEC_JSON__;
const baseSpec = clone(spec);
let rendered = null;
let currentSpec = null;
const state = {visibleLayers:{}};
const controls = {
  xMin: document.getElementById("xMin"), xMax: document.getElementById("xMax"),
  yMin: document.getElementById("yMin"), yMax: document.getElementById("yMax"),
  xLabel: document.getElementById("xLabel"), yLabel: document.getElementById("yLabel"),
  lineWidth: document.getElementById("lineWidth"), opacity: document.getElementById("opacity"),
  pointSize: document.getElementById("pointSize"), bendingMode: document.getElementById("bendingMode"),
  pointLabels: document.getElementById("pointLabels"), plotTitle: document.getElementById("plotTitle")
};
function clone(value){return JSON.parse(JSON.stringify(value));}
function layerList(source){return Array.isArray(source.layer) ? source.layer : [source];}
function layerName(layer,index){return layer.name || layer.usermeta?.layer_id || `layer ${index+1}`;}
function markObject(mark){return typeof mark === "string" ? {type:mark} : {...(mark || {type:"line"})};}
function markType(layer){return markObject(layer.mark).type || "line";}
function isBendingLayer(layer){return /bending|threshold|fmax|exceedance/i.test(layerName(layer,0)) || JSON.stringify(layer.encoding || {}).includes("bending_percent");}
function isTextLayer(layer){return markType(layer) === "text";}
function initControls(){
  controls.plotTitle.value = baseSpec.title?.text || baseSpec.title || document.getElementById("pageTitle").textContent;
  const firstEncoding = firstXYEncoding(baseSpec);
  controls.xLabel.value = firstEncoding?.x?.title || "";
  controls.yLabel.value = firstEncoding?.y?.title || "";
  const container = document.getElementById("layerControls");
  container.innerHTML = "";
  layerList(baseSpec).forEach((layer,index) => {
    const id = `layer_${index}`;
    const name = layerName(layer,index);
    state.visibleLayers[name] = true;
    const row = document.createElement("div");
    row.className = "check";
    row.innerHTML = `<input type="checkbox" id="${id}" checked><label for="${id}">${escapeHtml(name)}</label>`;
    row.querySelector("input").addEventListener("change", event => {state.visibleLayers[name] = event.target.checked; render();});
    container.appendChild(row);
  });
}
function firstXYEncoding(source){
  if (source.encoding?.x || source.encoding?.y) return source.encoding;
  for (const layer of layerList(source)) if (layer.encoding?.x || layer.encoding?.y) return layer.encoding;
  return {};
}
function renderSpec(){
  const next = clone(baseSpec);
  const title = controls.plotTitle.value.trim();
  if (title) next.title = title;
  next.width = "container";
  next.height = Number(next.height || 420);
  next.autosize = {type:"fit-x", contains:"padding"};
  if (Array.isArray(next.layer)) next.layer = next.layer.filter(layer => layerVisible(layer));
  applyRecursive(next, layer => {
    if (!layer.encoding) return;
    applyAxis(layer.encoding.x, controls.xLabel.value, controls.xMin.value, controls.xMax.value);
    applyAxis(layer.encoding.y, controls.yLabel.value, controls.yMin.value, controls.yMax.value);
    if (controls.bendingMode.value === "secondary" && isBendingLayer(layer) && layer.encoding.y) {
      layer.encoding.y.axis = {...(layer.encoding.y.axis || {}), orient:"right"};
    }
    if (controls.bendingMode.value === "normalized" && isBendingLayer(layer) && layer.encoding.y?.field === "bending_percent") {
      normalizeBendingLayer(layer);
      layer.encoding.y = {...layer.encoding.y, field:"bending_normalized", title:"Normalized bending"};
    }
  });
  applyStyle(next);
  return next;
}
function layerVisible(layer){
  const name = layerName(layer,0);
  if (state.visibleLayers[name] === false) return false;
  if (controls.bendingMode.value === "hidden" && isBendingLayer(layer)) return false;
  if (controls.pointLabels.value === "hide" && isTextLayer(layer)) return false;
  return true;
}
function applyAxis(axis, title, minValue, maxValue){
  if (!axis) return;
  if (title) axis.title = title;
  const min = parseNumber(minValue), max = parseNumber(maxValue);
  if (min !== null && max !== null) {
    axis.scale = {...(axis.scale || {})};
    axis.scale.domain = [min, max];
  }
}
function applyStyle(source){
  const lineScale = Number(controls.lineWidth.value || 1);
  const opacityScale = Number(controls.opacity.value || 1);
  const pointScale = Number(controls.pointSize.value || 1);
  applyRecursive(source, layer => {
    const mark = markObject(layer.mark);
    if (["line","rule","area","trail"].includes(mark.type)) mark.strokeWidth = baseNumber(mark.strokeWidth, 2) * lineScale;
    if (["point","circle","square"].includes(mark.type)) sizePoint(mark, baseNumber(mark.size, 42) * pointScale);
    if (mark.type !== "rect" && mark.type !== "text") mark.opacity = Math.max(0.01, Math.min(1, baseNumber(mark.opacity, 1) * opacityScale));
    layer.mark = mark;
  });
}
function sizePoint(mark, pointSize){mark.size = pointSize; mark.filled = mark.filled ?? true;}
function baseNumber(value, fallback){const number = Number(value); return Number.isFinite(number) ? number : fallback;}
function normalizeBendingLayer(layer){
  const values = layer.data?.values;
  if (!Array.isArray(values)) return;
  const maxValue = values.reduce((max,row) => Math.max(max, Math.abs(Number(row.bending_percent || 0))), 0) || 1;
  values.forEach(row => { row.bending_normalized = Number(row.bending_percent || 0) / maxValue; });
}
function applyRecursive(node, fn){
  if (!node || typeof node !== "object") return;
  if (node.mark || node.encoding) fn(node);
  for (const key of ["layer","hconcat","vconcat","concat"]) if (Array.isArray(node[key])) node[key].forEach(item => applyRecursive(item, fn));
}
async function render(){
  currentSpec = renderSpec();
  document.getElementById("pageTitle").textContent = controls.plotTitle.value || "__TITLE__";
  document.getElementById("plotStatus").textContent = "";
  try {
    rendered = await window.vegaEmbed("#plot", currentSpec, {actions:true, renderer:"canvas"});
  } catch (error) {
    document.getElementById("plotStatus").textContent = `Plot render failed: ${error.message || error}`;
  }
}
function reset(){
  Object.values(document.querySelectorAll("#layerControls input[type=checkbox]")).forEach(input => {input.checked = true;});
  Object.keys(state.visibleLayers).forEach(key => state.visibleLayers[key] = true);
  ["xMin","xMax","yMin","yMax"].forEach(key => controls[key].value = "");
  controls.lineWidth.value = 1; controls.opacity.value = 1; controls.pointSize.value = 1;
  controls.bendingMode.value = "overlay"; controls.pointLabels.value = "show";
  initControls(); render();
}
function parseNumber(value){if (value === "") return null; const number = Number(value); return Number.isFinite(number) ? number : null;}
function escapeHtml(value){
  return String(value).replace(/[&<>"']/g, char => {
    if (char === "&") return "&amp;";
    if (char === "<") return "&lt;";
    if (char === ">") return "&gt;";
    if (char === '"') return "&quot;";
    return "&#39;";
  });
}
function downloadBlob(name, type, content){const blob = new Blob([content], {type}); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url);}
document.getElementById("applyControls").addEventListener("click", render);
document.getElementById("resetControls").addEventListener("click", reset);
["xMin","xMax","yMin","yMax","xLabel","yLabel","lineWidth","opacity","pointSize","bendingMode","pointLabels","plotTitle"].forEach(key => controls[key].addEventListener("change", render));
document.getElementById("downloadSpec").addEventListener("click", () => downloadBlob("__SPEC_PATH__", "application/json", JSON.stringify(currentSpec || renderSpec(), null, 2)));
document.getElementById("downloadSvg").addEventListener("click", async () => {if (rendered) downloadBlob("__TITLE__.svg", "image/svg+xml", await rendered.view.toSVG());});
document.getElementById("downloadPng").addEventListener("click", async () => {if (!rendered) return; const canvas = await rendered.view.toCanvas(); canvas.toBlob(blob => {if (blob) downloadBlob("__TITLE__.png", "image/png", blob);});});
initControls();
render();
</script>
</body></html>"""
    return (
        template
        .replace("__TITLE__", html.escape(title))
        .replace("__HOME_PATH__", html.escape(home_path))
        .replace("__SPEC_PATH__", html.escape(spec_path))
        .replace("__SPEC_JSON__", spec_json)
    )


def _dataset_plot_studio_html(*, title: str, package_path: str, home_path: str = "../../index.html") -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_dataset_plot_studio_html(title=title, package_path=package_path, home_path=home_path)
    return render_dataset_plot_studio(
        dataset_plot_studio_context(
            title=title,
            package_path=package_path,
            home_path=home_path,
        )
    )


def _legacy_dataset_plot_studio_html(*, title: str, package_path: str, home_path: str = "../../index.html") -> str:
    title_json = json.dumps(title)
    package_json = json.dumps(package_path)
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>__TITLE_HTML__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<style>
:root{{--bg:#ffffff;--surface:#fff;--panel:#f8fafc;--line:#dfe5ec;--line-strong:#c5cfd9;--ink:#1c2530;--muted:#6b7785;--soft-muted:#9aa5b1;--primary:#185f8f;--primary-soft:#eef4f9;--pass:#70b58a;--warn:#e7b45b;--fail:#dd7f72;--fail-line:#c84f45;--shadow:0 8px 28px rgba(23,32,42,.16)}}
*{{box-sizing:border-box}}html,body{{height:100%}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,"Segoe UI","Helvetica Neue",Helvetica,Arial,sans-serif;line-height:1.45}}a{{color:var(--primary);text-decoration:none}}button,input,select,textarea{{font:inherit}}button{{border:1px solid var(--line-strong);background:#fff;border-radius:6px;min-height:28px;padding:5px 10px;font-size:12.5px;cursor:pointer;color:#344251}}button.primary{{background:var(--primary);border-color:var(--primary);color:#fff;font-weight:700}}button.danger{{border-color:#d6b0b0;color:#9d2222}}button[aria-pressed="true"],.segment button.active{{background:var(--primary);border-color:var(--primary);color:#fff}}
.plot-studio{{display:flex;flex-direction:column;height:100vh;min-height:720px;overflow:hidden;background:#fff}}.topbar{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:9px 18px;background:#fff;border-bottom:1px solid var(--line);flex-shrink:0}}.brand-link{{border:0;background:transparent;color:var(--primary);font-weight:650;font-size:13px;padding:4px 6px;min-height:0}}.brand-link:hover{{background:var(--primary-soft)}}.title-block{{display:flex;align-items:center;gap:12px;min-width:0;flex:1;border-left:1px solid var(--line);padding-left:14px}}.title-block h1{{font-size:13.5px;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:700}}.title-block p{{margin:0;color:#b3bcc6;font-size:12px;white-space:nowrap}}.top-actions{{display:flex;gap:7px;align-items:center;position:relative;flex-shrink:0}}.export-menu{{display:none;position:absolute;right:0;top:calc(100% + 6px);width:312px;background:#fff;border:1px solid #c9d2dd;border-radius:10px;box-shadow:var(--shadow);padding:8px;z-index:40}}.export-menu.open{{display:block}}.export-row{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;border:0;background:transparent;width:100%;text-align:left;padding:9px 10px;border-radius:7px;min-height:0;font-size:13px}}.export-row:hover{{background:#f2f6fa}}.export-row .pill{{order:2}}.pill{{display:inline-flex;justify-content:center;border:1px solid var(--line);border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600;color:var(--muted)}}.pill.style{{background:#fff8e6;border-color:#d9bd7c;color:#73520a}}.pill.data{{background:#f2fbef;border-color:#b8d7a8;color:#2f6424}}.pill.full{{background:#eef6ff;border-color:#a6bed7;color:var(--primary)}}
.workspace{{flex:1;display:grid;grid-template-columns:minmax(0,1fr) 380px;min-height:0}}.canvas{{position:relative;min-width:0;background:#fff;padding:0;display:block}}.figure-strip{{position:absolute;top:10px;left:18px;z-index:5;display:flex;align-items:center;gap:6px}}.tabs{{display:flex;gap:6px}}.tabs button{{border-radius:999px;padding:5px 12px;font-size:12px;min-height:28px;border-color:#c5cfd9}}.tabs button.active{{background:var(--primary);border-color:var(--primary);color:#fff;font-weight:700}}.canvas-tools{{display:flex;gap:8px}}.chart-card{{position:absolute;inset:46px 14px 36px 14px;background:#fff;border:0;border-radius:0;min-height:0;padding:0;box-shadow:none}}#plot{{width:100%;height:100%;min-height:0}}.chart-overlay{{position:absolute;right:16px;top:12px;display:flex;gap:6px;z-index:6}}.chart-overlay button{{background:rgba(255,255,255,.92);font-size:12px;padding:4px 10px;min-height:26px}}.hint{{color:var(--soft-muted);font-size:11.5px}}.footer-strip{{position:absolute;left:18px;right:18px;bottom:10px;display:flex;gap:14px;align-items:center;font-size:11.5px;color:var(--soft-muted);padding:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.inspector{{position:relative;display:flex;flex-direction:column;background:#f8fafc;border-left:1px solid var(--line);min-width:0;min-height:0}}.segment{{display:flex;gap:4px;padding:10px 12px 8px;border-bottom:0;flex-shrink:0}}.segment button{{min-width:0;flex:1;border-color:transparent;background:transparent;font-size:12px;font-weight:650;color:#5b6470}}.segment button.active{{background:#fff;border-color:#c9d2dd;color:#17202a;box-shadow:0 1px 2px rgba(23,32,42,.05)}}.inspector-body{{overflow:auto;padding:4px 14px 18px;flex:1;min-height:0}}.panel{{display:none}}.panel.active{{display:block}}.card{{background:#fff;border:1px solid #e4e8ed;border-radius:8px;padding:11px;margin-bottom:14px}}.card h2{{font-size:11.5px;margin:0 0 10px;font-weight:700;color:#3a4654}}#panel-style .card h2::after{{content:"▾";float:right;color:#9aa5b1}}#panel-style .card:not(:first-child){{padding:0;overflow:hidden}}#panel-style .card:not(:first-child)>h2{{margin:0;padding:9px 11px;cursor:pointer}}#panel-style .card:not(:first-child)>h2::after{{content:"▸"}}#panel-style .card:not(:first-child)>:not(h2){{display:none}}.field{{display:grid;grid-template-columns:78px minmax(0,1fr);gap:7px 8px;align-items:center;margin:7px 0}}.field label,.check label{{font-size:12.5px;color:#344256}}.field input,.field select{{width:100%;border:1px solid #c9d2dd;border-radius:6px;padding:5px 7px;background:#fff;min-width:0}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.buttons{{display:flex;gap:6px;margin-bottom:10px}}.buttons button{{flex:1;padding:5px 0;font-size:12px}}#layerControls{{display:flex;flex-direction:column;gap:10px}}.layer-card{{border:1px solid #dbe2ea;border-radius:8px;background:#fff;padding:10px 12px}}.layer-head{{display:flex;align-items:center;gap:8px;cursor:pointer}}.layer-head input[type=checkbox]{{flex-shrink:0;cursor:pointer}}.layer-label{{flex:1;min-width:0;border:1px solid transparent;border-radius:6px;padding:3px 6px;font-size:13px;font-weight:650;background:transparent;color:#1c2530;cursor:text}}.layer-label:hover{{border-color:#c9d2dd;background:#fff}}.layer-label:focus{{outline:none;border-color:#185f8f;background:#fff}}.role-pill{{flex-shrink:0;font-size:10px;color:#9aa5b1;border:1px solid #e0e6ec;border-radius:999px;padding:1px 7px}}.layer-chev{{flex-shrink:0;width:22px;height:22px;display:grid;place-items:center;color:#6b7785;font-size:12px}}.layer-src{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:#9aa5b1;margin:6px 0 0 26px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.layer-grid{{display:grid;grid-template-columns:64px minmax(0,1fr);gap:6px 8px;align-items:center;font-size:12px;margin-top:8px;color:#5b6470}}.layer-grid input,.layer-grid select{{border:1px solid #c9d2dd;border-radius:6px;padding:4px 7px;min-width:0;background:#fff}}.layer-grid input[type=color]{{height:28px;width:100%;padding:2px}}.layer-footnote{{font-size:11.5px;color:#8a95a1}}.saved-looks{{border-top:1px solid var(--line);padding:10px 12px;background:#eaf2f8;flex-shrink:0}}.saved-row{{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:6px}}.saved-row input{{min-width:0;border:1px solid #c9d2dd;border-radius:6px;padding:6px}}.status{{font-size:12px;color:var(--muted);margin-top:8px}}.status.error{{color:#a6332a}}.status.success{{color:#2f7650}}
#panel-layers .card{{background:transparent;border:0;border-radius:0;padding:0;margin:0}}#panel-layers .card>h2{{display:none}}#layerControls .layer-src{{display:none}}
.modal-backdrop{{display:none;position:fixed;left:0;right:380px;top:49px;bottom:0;background:rgba(248,250,252,.98);z-index:30;padding:0;border-right:1px solid var(--line)}}.modal-backdrop.open{{display:block}}.modal{{width:100%;height:100%;max-height:none;background:rgba(248,250,252,.98);border-radius:0;box-shadow:none;display:flex;flex-direction:column}}.modal header{{padding:10px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px;flex-wrap:wrap}}.modal footer{{display:none}}.modal .sheet-title{{font-size:13.5px;font-weight:750;white-space:nowrap}}.modal .sheet-spacer{{flex:1}}.modal .sheet-pager{{display:flex;align-items:center;gap:6px;font-size:12px;color:#5b6470}}.modal .sheet-pager button{{padding:3px 9px;min-height:26px}}.modal .sheet-dataset{{display:flex;align-items:center;gap:7px;margin:0}}.modal .sheet-dataset label{{font-size:12.5px;color:#344256}}.modal .sheet-dataset select{{border:1px solid #c9d2dd;border-radius:6px;padding:4px 8px;font-size:12.5px;background:#fff}}.modal .sheet-hint{{padding:4px 18px 6px;font-size:11.5px;color:#6b7785}}.modal-body{{flex:1;padding:0 18px 16px;overflow:auto;min-height:0}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:6px;max-height:none;height:100%;background:#fff}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid var(--line);padding:5px 6px;vertical-align:top}}th{{background:#eef3f7;position:sticky;top:0}}td input{{width:100px;border:1px solid transparent;border-radius:4px;background:#fffdf3;padding:2px 5px;font:inherit;font-family:ui-monospace,Menlo,Consolas,monospace}}td[contenteditable]{{background:#fffdf3}}textarea{{width:100%;height:100%;min-height:0;border:1px solid #c9d2dd;border-radius:8px;padding:10px;font-family:Consolas,monospace;font-size:11.5px;line-height:1.4;resize:none;background:#fff;color:#2a3744}}
@media(max-width:980px){{.plot-studio{{height:auto;min-height:100vh}}.workspace{{grid-template-columns:1fr}}.inspector{{border-left:0;border-top:1px solid var(--line)}}.topbar{{grid-template-columns:1fr}}.top-actions{{justify-content:flex-start}}.modal-backdrop{{right:0;top:0;bottom:0}}}}
</style></head>
<body><main class="plot-studio" data-studio="mtda-dataset-aggregate">
<header class="topbar"><button id="archiveButton" class="brand-link">&larr; Archive</button><div class="title-block"><h1 id="studioTitle">__TITLE_HTML__</h1><p>selection set final_report_runs</p></div><div class="top-actions"><button id="resetView">Reset view</button><button id="resetPage" class="danger">Reset page</button><button id="exportButton" class="primary">Export</button><div id="exportMenu" class="export-menu" aria-label="Export menu"><button class="export-row" data-export="profile"><span class="pill style">Style</span><span>Style profile</span></button><button class="export-row" id="importProfile"><span class="pill style">Style</span><span>Import style profile</span></button><button class="export-row" data-export="csv"><span class="pill data">Data</span><span>Dataset CSV</span></button><button class="export-row" id="downloadSvg"><span class="pill full">Figure</span><span>Figure SVG</span></button><button class="export-row" id="downloadPng"><span class="pill full">Figure</span><span>Figure PNG (2x)</span></button><button class="export-row" id="downloadSpecExport"><span class="pill full">Spec</span><span>Vega-Lite spec</span></button><button class="export-row" id="downloadPackage"><span class="pill full">Package</span><span>Compact plot package</span></button></div></div></header>
<section class="workspace"><section class="canvas"><div class="figure-strip"><div class="tabs" role="tablist"><button id="tabStress" class="active" data-figure="stress">Stress-strain</button><button id="tabBending" data-figure="bending">Bending candle</button></div></div><div class="chart-overlay"><button id="alignOrigin">&#8974; Align to origin</button><button id="resetZoom">&#10530; Reset zoom</button></div><section class="chart-card"><div id="plot"></div></section><div class="footer-strip"><span>Generated view &mdash; not the data of record</span><a href="stress_strain_aligned.csv">stress_strain_aligned.csv</a><a href="characteristic_points.csv">characteristic_points.csv</a><a href="statistics.csv">statistics.csv</a><span id="packageSummary"></span></div></section>
<aside class="inspector"><nav class="segment"><button class="active" data-panel="style">Style</button><button data-panel="layers">Layers</button><button data-panel="data">Data &amp; spec</button></nav><div class="inspector-body"><section id="panel-style" class="panel active"><div class="card"><h2>Titles &amp; labels</h2><div class="field"><label for="titleInput">Title</label><input id="titleInput"></div><div class="field"><label for="xLabelInput">X label</label><input id="xLabelInput"></div><div class="field"><label for="yLabelInput">Y label</label><input id="yLabelInput"></div></div><div class="card"><h2>Axis &amp; range</h2><div class="split"><div class="field"><label for="xMin">X min</label><input id="xMin"></div><div class="field"><label for="xMax">X max</label><input id="xMax"></div></div><div class="split"><div class="field"><label for="yMin">Y min</label><input id="yMin"></div><div class="field"><label for="yMax">Y max</label><input id="yMax"></div></div></div><div class="card"><h2>Type / sizes in pt</h2><div class="field"><label for="masterScale">Master scale</label><input id="masterScale" type="range" min="0.65" max="1.6" step="0.05" value="1"></div><div class="field"><label for="opacityScale">Opacity</label><input id="opacityScale" type="range" min="0.15" max="1" step="0.05" value="1"></div></div><div class="card"><h2>Axes, ticks &amp; grid</h2><label class="check"><input id="gridToggle" type="checkbox" checked> Show grid</label></div><div class="card"><h2>Legend</h2><label class="check"><input id="legendToggle" type="checkbox" checked> Show legend</label></div></section><section id="panel-layers" class="panel"><div class="card"><h2>Figure layers</h2><div class="buttons"><button id="showAllLayers">Show all</button><button id="hideContextLayers">Hide context</button></div><div id="layerControls"></div></div></section><section id="panel-data" class="panel"><div class="card"><h2>Main results</h2><p class="status" id="dataSummary">Loading archive-backed package...</p></div><div class="card"><h2>Data block</h2><button id="openDataSheet2">Open data table</button></div><div class="card"><h2>Spec block</h2><button id="openSpecSheet2">Open spec editor</button><button id="downloadSpecJson">Download spec JSON</button><p class="status">Working edits regenerate the browser view only.</p></div></section></div><footer class="saved-looks"><div class="saved-row"><input id="lookName" placeholder="Name this look..."><button id="saveLook">Save</button><button id="importLook">Import file...</button></div><p class="status" id="lookStatus">Saved looks use localStorage key mtda_plot_style_presets.</p></footer></aside></section></main>
<div id="dataModal" class="modal-backdrop"><section class="modal"><header><div class="sheet-title">Data <span class="pill data">data only</span></div><div class="sheet-dataset"><label for="datasetSelect">Dataset</label><select id="datasetSelect"></select></div><div class="sheet-pager"><button id="prevDataPage">&larr;</button><span id="pagerLabel">1-100</span><button id="nextDataPage">&rarr;</button></div><span class="sheet-spacer"></span><button id="resetData" class="danger">Reset data</button><button id="downloadData">Download CSV</button><button data-close="dataModal">Close &#10005;</button></header><div id="dataHint" class="sheet-hint"></div><div class="modal-body"><div class="table-wrap"><table id="dataTable"></table></div></div><footer></footer></section></div>
<div id="specModal" class="modal-backdrop"><section class="modal"><header><div class="sheet-title">Vega-Lite spec <span class="pill full">plot spec + hydrated data</span></div><span class="sheet-spacer"></span><button id="formatSpec">Format</button><button id="validateSpec">Validate</button><button id="copySpec">Copy</button><button id="applySpec" class="primary">Apply spec</button><button id="regenerateSpec">Regenerate</button><button data-close="specModal">Close &#10005;</button></header><div id="specStatus" class="sheet-hint">Generated from the current controls. Edit freely, then Apply.</div><div class="modal-body"><textarea id="specEditor"></textarea></div><footer></footer></section></div>
<script>
const packagePath = __PACKAGE_JSON__;
const defaultTitle = __TITLE_JSON__;
const storeKey = "mtda_plot_style_presets";
let plotPackage = null, templateSpec = null, datasets = {{}}, rendered = null, customSpec = null, activeFigure = "stress";
const state = {{title:defaultTitle,xLabel:"",yLabel:"",xMin:"",xMax:"",yMin:"",yMax:"",scale:1,opacity:1,grid:true,legend:true,visibleLayers:{{}},dataPage:0}};
const $ = id => document.getElementById(id);
function clone(v){{return JSON.parse(JSON.stringify(v));}}
async function text(path){{const r=await fetch(path); if(!r.ok) throw new Error(`${{path}}: ${{r.status}}`); return await r.text();}}
async function json(path){{return JSON.parse(await text(path));}}
function csvRows(raw){{const lines=raw.trim().split(/\\r?\\n/); if(!lines.length) return []; const h=splitCsv(lines.shift()); return lines.filter(Boolean).map(line=>{{const cells=splitCsv(line); const row={{}}; h.forEach((key,i)=>row[key]=coerce(cells[i] ?? "")); return row;}});}}
function splitCsv(line){{const out=[];let cur="",q=false;for(let i=0;i<line.length;i++){{const c=line[i];if(c==='"'&&line[i+1]==='"'){{cur+='"';i++;}}else if(c==='"')q=!q;else if(c===','&&!q){{out.push(cur);cur="";}}else cur+=c;}}out.push(cur);return out;}}
function coerce(v){{const n=Number(v);return v!==""&&Number.isFinite(n)?n:v;}}
async function boot(){{try{{plotPackage=await json(packagePath); templateSpec=plotPackage.template||await json(plotPackage.template_path||plotPackage.template_member); if(Array.isArray(plotPackage.embedded_datasets)&&plotPackage.embedded_datasets.length){{for(const d of plotPackage.embedded_datasets) datasets[d.dataset_id]={{meta:d,rows:clone(d.rows||[])}};}}else{{for(const d of plotPackage.datasets||[]) datasets[d.dataset_id]={{meta:d,rows:csvRows(await text(d.path))}};}} normalizeWorkingViewData(); initState(); renderLayerControls(); renderDatasetSelect(); render();}}catch(err){{$("dataSummary").textContent=`Load failed: ${{err.message||err}}`; $("dataSummary").className="status error";}}}}
function normalizeWorkingViewData(){{for(const dataset of Object.values(datasets)){{const rows=dataset.rows||[]; if(!rows.length) continue; const hasX=rows.some(row=>Number.isFinite(Number(row.x_common))); if(!hasX) continue; const maxX=Math.max(...rows.map(row=>Number(row.x_common)).filter(Number.isFinite)); if(maxX>0&&maxX<=1.5){{rows.forEach(row=>{{const value=Number(row.x_common); if(Number.isFinite(value)) row.x_common=value*100;}}); dataset.meta={{...dataset.meta,view_normalization:"x_common_fraction_to_percent"}};}}}}}}
function initState(){{const enc=firstEncoding(templateSpec); state.title=defaultStressTitle(); state.xLabel=enc.x?.title||"Strain / %"; state.yLabel=enc.y?.title||"Stress / MPa"; $("titleInput").value=state.title; $("xLabelInput").value=state.xLabel; $("yLabelInput").value=state.yLabel; $("packageSummary").textContent=`${{plotPackage.datasets?.length||0}} datasets from ${{packagePath}}`; $("dataSummary").textContent=`${{Object.values(datasets).reduce((a,d)=>a+d.rows.length,0)}} rows loaded from archive data members.`;}}
function datasetName(){{const match=String(defaultTitle||"").match(/Dataset report\\s*·\\s*(.*?)\\s*·\\s*aggregate/i); return match&&match[1]?match[1]:"dataset";}}
function defaultStressTitle(){{return `${{datasetName()}} — aggregate compressive stress-strain`;}}
function firstEncoding(spec){{let found={{}}; walk(spec,l=>{{if(!found.x&&!found.y&&(l.encoding?.x||l.encoding?.y)) found=l.encoding;}}); return found;}}
function hydrate(node){{if(Array.isArray(node)) return node.map(hydrate); if(node&&typeof node==="object"){{if(node.__compact_dataset_ref__) return {{values:clone(datasets[node.__compact_dataset_ref__]?.rows||[])}}; const out={{}}; Object.entries(node).forEach(([k,v])=>out[k]=hydrate(v)); return out;}} return node;}}
function buildSpec(){{if(customSpec) return clone(customSpec); let spec=hydrate(templateSpec); spec.width="container"; spec.height=500; spec.autosize={{type:"fit-x",contains:"padding"}}; spec.background="#ffffff"; spec.title={{text:state.title,fontSize:15,anchor:"start"}}; spec.config={{...(spec.config||{{}}),axis:{{grid:state.grid,labelFontSize:11,titleFontSize:12}},legend:{{disable:!state.legend}},view:{{stroke:"#d7e0ea"}}}}; if(activeFigure!=="bending") spec=addStressAggregateLayers(spec); if(activeFigure!=="bending") spec=addFmaxLayers(spec); if(activeFigure!=="bending") spec=applyStressDomains(spec); walk(spec,layer=>styleLayer(layer)); if(Array.isArray(spec.layer)) spec.layer=spec.layer.filter(layer=>layerAllowed(layer)); if(activeFigure==="bending") spec = buildBendingSpec(spec); return spec;}}
function applyStressDomains(spec){{const rows=stressAggregateRows(); if(!Array.isArray(spec.layer)||!rows.length) return spec; const fmax=fmaxRows()[0]; let ymax=0; rows.forEach(row=>{{["max_stress_MPa","hi_stress_MPa","mean_stress_MPa"].forEach(key=>{{const value=Number(row[key]); if(Number.isFinite(value)&&value>ymax) ymax=value;}});}}); if(fmax&&Number.isFinite(Number(fmax.max_strength_MPa))) ymax=Math.max(ymax,Number(fmax.max_strength_MPa)); const xMax=fmax?103:100; const yMax=ymax>0?Number((ymax*1.04).toFixed(1)):undefined; const first=spec.layer.find(layer=>layer.encoding&&layer.encoding.x&&layer.encoding.y); if(first){{first.encoding.x={{...(first.encoding.x||{{}}),title:state.xLabel,scale:{{nice:false,domain:[0,xMax]}}}}; first.encoding.y={{...(first.encoding.y||{{}}),title:state.yLabel,scale:{{nice:false,domain:[0,yMax]}}}};}} return spec;}}
function ensureLayeredSpec(spec){{const next=clone(spec); if(!Array.isArray(next.layer)){{const base={{data:next.data,mark:next.mark,encoding:next.encoding,name:next.name||"stress_strain_curves"}}; delete next.data; delete next.mark; delete next.encoding; delete next.name; next.layer=[base];}} return next;}}
function addStressAggregateLayers(spec){{const rows=stressAggregateRows(); if(!rows.length) return spec; const next=ensureLayeredSpec(spec); const data={{values:rows}}; next.layer=[{{name:"min_max_band",data,mark:{{type:"area",color:"#9fbad2",opacity:.18}},encoding:{{x:{{field:"x_common",type:"quantitative",title:state.xLabel}},y:{{field:"min_stress_MPa",type:"quantitative",title:state.yLabel}},y2:{{field:"max_stress_MPa"}},tooltip:stressAggregateTooltip()}}}},{{name:"std_band",data,mark:{{type:"area",color:"#5d8eb5",opacity:.22}},encoding:{{x:{{field:"x_common",type:"quantitative",title:state.xLabel}},y:{{field:"lo_stress_MPa",type:"quantitative",title:state.yLabel}},y2:{{field:"hi_stress_MPa"}},tooltip:stressAggregateTooltip()}}}},{{name:"mean_curve",data,mark:{{type:"line",color:"#185f8f",strokeWidth:2.4}},encoding:{{x:{{field:"x_common",type:"quantitative",title:state.xLabel}},y:{{field:"mean_stress_MPa",type:"quantitative",title:state.yLabel}},tooltip:stressAggregateTooltip()}}}},...next.layer]; return next;}}
function stressAggregateRows(){{const dataset=Object.values(datasets).find(d=>d.meta?.role==="stress_aggregate"||d.meta?.dataset_id==="stress_aggregate"); return dataset?(dataset.rows||[]).filter(row=>Number.isFinite(Number(row.mean_stress_MPa))):[];}}
function stressAggregateTooltip(){{return [{{field:"x_common",type:"quantitative",title:"Aligned strain / progress",format:".2f"}},{{field:"mean_stress_MPa",type:"quantitative",title:"Mean stress / MPa",format:".2f"}},{{field:"std_stress_MPa",type:"quantitative",title:"Std / MPa",format:".2f"}},{{field:"min_stress_MPa",type:"quantitative",title:"Min stress / MPa",format:".2f"}},{{field:"max_stress_MPa",type:"quantitative",title:"Max stress / MPa",format:".2f"}},{{field:"run_count",type:"quantitative",title:"Runs"}}];}}
function addFmaxLayers(spec){{const rows=fmaxRows(); if(!rows.length) return spec; const next=clone(spec); if(!Array.isArray(next.layer)){{const base={{data:next.data,mark:next.mark,encoding:next.encoding,name:next.name||"stress_strain_curves"}}; delete next.data; delete next.mark; delete next.encoding; delete next.name; next.layer=[base];}} const data={{values:rows}}; next.layer.push({{name:"fmax_wick",data,mark:{{type:"rule",color:"#7a2020",strokeWidth:1.5}},encoding:{{x:{{field:"x_position",type:"quantitative",title:state.xLabel}},y:{{field:"min_strength_MPa",type:"quantitative",title:state.yLabel}},y2:{{field:"max_strength_MPa"}},tooltip:fmaxTooltip()}}}},{{name:"fmax_box",data,mark:{{type:"bar",size:22,color:"#b3392f",opacity:.9,stroke:"#ffffff",strokeWidth:.75,cornerRadius:1}},encoding:{{x:{{field:"x_position",type:"quantitative"}},y:{{field:"q1_strength_MPa",type:"quantitative"}},y2:{{field:"q3_strength_MPa"}},tooltip:fmaxTooltip()}}}},{{name:"fmax_median",data,mark:{{type:"tick",color:"#3a0d0d",thickness:3,size:80}},encoding:{{x:{{field:"x_position",type:"quantitative"}},y:{{field:"median_strength_MPa",type:"quantitative"}},tooltip:fmaxTooltip()}}}},{{name:"fmax_label",data,mark:{{type:"text",align:"left",dx:10,dy:-8,fontWeight:"bold",color:"#7a2020"}},encoding:{{x:{{field:"x_position",type:"quantitative"}},y:{{field:"max_strength_MPa",type:"quantitative"}},text:{{field:"label"}}}}}}); return next;}}
function fmaxRows(){{const dataset=Object.values(datasets).find(d=>d.meta?.role==="fmax_distribution"||d.meta?.dataset_id==="fmax_distribution"); return dataset?(dataset.rows||[]).filter(row=>Number.isFinite(Number(row.max_strength_MPa))):[];}}
function fmaxTooltip(){{return [{{field:"label",type:"nominal",title:"Marker"}},{{field:"run_count",type:"quantitative",title:"Runs"}},{{field:"min_strength_MPa",type:"quantitative",title:"Min strength / MPa",format:".2f"}},{{field:"q1_strength_MPa",type:"quantitative",title:"Q1 strength / MPa",format:".2f"}},{{field:"median_strength_MPa",type:"quantitative",title:"Median strength / MPa",format:".2f"}},{{field:"q3_strength_MPa",type:"quantitative",title:"Q3 strength / MPa",format:".2f"}},{{field:"max_strength_MPa",type:"quantitative",title:"Max strength / MPa",format:".2f"}}];}}
function buildBendingSpec(spec){{const rows = bendingRows(); if(rows.length) return {{width:"container",height:500,background:"#ffffff",title:{{text:state.title.replace(/stress-strain/i,"bending"),fontSize:15,anchor:"start"}},data:{{values:rows}},layer:[{{mark:{{type:"rule",color:"#82909f",strokeWidth:1.4}},encoding:{{x:{{field:"run",type:"ordinal",sort:null,title:"Run",axis:{{labelAngle:-35}}}},y:{{field:"min_bending_percent",type:"quantitative",title:"Bending / %"}},y2:{{field:"max_bending_percent"}},tooltip:bendingTooltip()}}}},{{mark:{{type:"bar",size:28}},encoding:{{x:{{field:"run",type:"ordinal",sort:null,title:"Run",axis:{{labelAngle:-35}}}},y:{{field:"q1_bending_percent",type:"quantitative",title:"Bending / %"}},y2:{{field:"q3_bending_percent"}},color:{{field:"pattern",type:"nominal",title:"Bending pattern",scale:{{domain:["PASS","WARN","FAIL"],range:["#70b58a","#e7b45b","#dd7f72"]}}}},tooltip:bendingTooltip()}}}},{{mark:{{type:"tick",color:"#344256",thickness:3,size:34}},encoding:{{x:{{field:"run",type:"ordinal",sort:null}},y:{{field:"median_bending_percent",type:"quantitative"}},tooltip:bendingTooltip()}}}},{{mark:{{type:"rule",strokeDash:[6,5],color:"#c84f45",strokeWidth:1.5}},encoding:{{y:{{field:"threshold_percent",type:"quantitative",title:"Bending / %"}}}}}}],config:{{axis:{{grid:state.grid}},legend:{{disable:!state.legend}},view:{{stroke:"#d7e0ea"}}}}}}; const fallback=clone(spec); fallback.title={{text:"Bending candle",subtitle:"No bending-summary dataset found in this package yet.",anchor:"start"}}; return fallback;}}
function bendingTooltip(){{return [{{field:"run",type:"nominal",title:"Run"}},{{field:"pattern",type:"nominal",title:"Pattern"}},{{field:"max_bending_percent",type:"quantitative",title:"Max bending / %",format:".2f"}},{{field:"median_bending_percent",type:"quantitative",title:"Median bending / %",format:".2f"}},{{field:"threshold_percent",type:"quantitative",title:"Threshold / %",format:".2f"}}];}}
function bendingRows(){{const dataset=Object.values(datasets).find(d=>d.meta?.role==="bending_summary"||d.meta?.dataset_id==="bending_summary"); const rows=dataset?dataset.rows:[]; return rows.map((r,i)=>{{const max=numberField(r,"max_bending_percent","bending_max_percent","bending_p95_percent"); const median=numberField(r,"median_bending_percent","bending_median_percent","bending_mean_percent"); const threshold=numberField(r,"bending_threshold_percent")||10; return {{run:r.run_id||r.run||`run_${{i+1}}`,min_bending_percent:numberField(r,"min_bending_percent")||0,q1_bending_percent:numberField(r,"q1_bending_percent","bending_mean_percent","bending_median_percent")||median,q3_bending_percent:numberField(r,"q3_bending_percent","bending_p95_percent","bending_max_percent")||max,median_bending_percent:median,max_bending_percent:max,threshold_percent:threshold,pattern:bendingPatternGroup(r.bending_pattern,max,threshold)}};}}).filter(r=>Number.isFinite(r.max_bending_percent));}}
function numberField(row,...keys){{for(const key of keys){{const value=Number(row[key]); if(Number.isFinite(value)) return value;}} return null;}}
function bendingPatternGroup(pattern,maxValue,threshold){{const text=String(pattern||"").toUpperCase(); if(text.includes("FAIL")||maxValue>threshold) return "FAIL"; if(text.includes("WARN")) return "WARN"; return "PASS";}}
function layerName(layer,i){{return layer.name||layer.usermeta?.layer_id||`layer_${{i+1}}`;}}
function layerAllowed(layer){{const name=layerName(layer,0); return state.visibleLayers[name]!==false;}}
function styleLayer(layer){{if(!layer.encoding) return; if(layer.encoding.x) applyAxis(layer.encoding.x,state.xLabel,state.xMin,state.xMax); if(layer.encoding.y) applyAxis(layer.encoding.y,state.yLabel,state.yMin,state.yMax); if(layer.mark){{const mark=typeof layer.mark==="string"?{{type:layer.mark}}:{{...layer.mark}}; if(["line","area","rule","trail"].includes(mark.type)) mark.strokeWidth=(Number(mark.strokeWidth)||2)*state.scale; if(mark.type==="point") mark.size=(Number(mark.size)||42)*state.scale; if(mark.type!=="text") mark.opacity=Math.max(.05,Math.min(1,(Number(mark.opacity)||1)*state.opacity)); layer.mark=mark;}}}}
function optionalNumber(value){{if(value===null||value===undefined||String(value).trim()==="") return null; const number=Number(value); return Number.isFinite(number)?number:null;}}
function applyAxis(axis,title,min,max){{axis.title=title||axis.title; const lo=optionalNumber(min),hi=optionalNumber(max); if(lo!==null&&hi!==null) axis.scale={{...(axis.scale||{{}}),domain:[lo,hi]}};}}
function walk(node,fn){{if(!node||typeof node!=="object")return; if(node.mark||node.encoding)fn(node); ["layer","hconcat","vconcat","concat"].forEach(k=>Array.isArray(node[k])&&node[k].forEach(x=>walk(x,fn)));}}
async function render(){{const spec=buildSpec(); $("specEditor").value=JSON.stringify(spec,null,2); rendered=await vegaEmbed("#plot",spec,{{actions:false,renderer:"canvas"}});}}
function renderLayerControls(){{const box=$("layerControls"); box.innerHTML=""; semanticLayerControls().forEach((item,index)=>{{if(state.visibleLayers[item.key]===undefined) state.visibleLayers[item.key]=item.visible!==false; const card=document.createElement("div"); card.className="layer-card"; card.innerHTML=`<div class="layer-head"><input type="checkbox" ${{state.visibleLayers[item.key]!==false?"checked":""}}><input class="layer-label" value="${{escapeHtml(item.label)}}" title="Rename — this name shows in the legend / annotation"><span class="role-pill">${{escapeHtml(item.role)}}</span><span class="layer-chev">▸</span></div><div class="layer-src">${{escapeHtml(item.src)}}</div>`; const checkbox=card.querySelector('input[type="checkbox"]'); const labelInput=card.querySelector('.layer-label'); checkbox.onchange=e=>{{state.visibleLayers[item.key]=e.target.checked;render();}}; labelInput.onchange=e=>{{item.label=e.target.value;}}; card.dataset.layerKey=item.key; card.dataset.layerIndex=String(index); box.appendChild(card);}});}}
function semanticLayerControls(){{if(activeFigure==="bending") return [{{key:"bending_box",label:"Inter-quartile (q1–q3)",role:"box",src:"bending in-window dist · q1–q3",color:"#7d8794"}},{{key:"bending_wick",label:"Range (min→max)",role:"wick",src:"bending in-window dist · min → max",color:"#9aa5b1"}},{{key:"bending_median",label:"Median bending",role:"tick",src:"bending in-window dist · median",color:"#17202a"}},{{key:"bending_threshold",label:"Threshold 10%",role:"rule",src:"method · bending threshold",color:"#9d2222"}}]; return [{{key:"min_max_band",label:"Min–max range",role:"band",src:"stress_strain_aligned.csv · min / max",color:"#d2e2ef"}},{{key:"std_band",label:"±1σ band",role:"band",src:"stress_strain_aligned.csv · mean ± std",color:"#9cbfdc"}},{{key:"stress_strain_curves",label:"Individual replicates",role:"multiline",src:"stress_strain_aligned.csv · per run",color:"#8a9eb2"}},{{key:"mean_curve",label:"Mean curve",role:"line",src:"stress_strain_aligned.csv · mean",color:"#1f4e79"}},{{key:"fmax_wick",label:"Fmax min–max",role:"wick",src:"σmax per run · min → max",color:"#7a2020"}},{{key:"fmax_box",label:"Fmax q1–q3",role:"box",src:"σmax per run · q1–q3",color:"#b3392f"}},{{key:"fmax_median",label:"Fmax median",role:"tick",src:"σmax per run · median",color:"#3a0d0d"}},{{key:"fmax_label",label:"Run σmax points",role:"markers",src:"characteristic_points.csv · σmax per run",color:"#9d2222",visible:false}}];}}
function renderDatasetSelect(){{const sel=$("datasetSelect"); sel.innerHTML=""; Object.values(datasets).forEach(d=>{{const o=document.createElement("option"); o.value=d.meta.dataset_id; o.textContent=`${{d.meta.dataset_id}} - ${{d.meta.role||"dataset"}}`; sel.appendChild(o);}}); const preferred=Object.values(datasets).find(d=>d.meta?.role==="stress_aggregate"||d.meta?.dataset_id==="stress_aggregate")||Object.values(datasets)[0]; if(preferred) sel.value=preferred.meta.dataset_id; renderDataTable();}}
function renderDataTable(){{const d=datasets[$("datasetSelect").value]||Object.values(datasets)[0]; const table=$("dataTable"); if(!d){{table.innerHTML="";return;}} const fields=displayFields(d); const per=100; const total=d.rows.length; const maxPage=Math.max(0,Math.ceil(total/per)-1); state.dataPage=Math.max(0,Math.min(state.dataPage,maxPage)); const start=state.dataPage*per; const pageRows=d.rows.slice(start,start+per); $("pagerLabel").textContent=total?`${{start+1}}-${{Math.min(total,start+per)}} of ${{total}}`:"0 rows"; $("dataHint").textContent=`${{displayDatasetName(d)}} · editable working copy, data of record remains in archive CSV members`; table.innerHTML=`<thead><tr>${{fields.map(f=>`<th>${{escapeHtml(f.label)}}</th>`).join("")}}</tr></thead><tbody>${{pageRows.map((r,offset)=>`<tr>${{fields.map(f=>dataCell(r,f,start+offset)).join("")}}</tr>`).join("")}}</tbody>`;}}
function displayDatasetName(dataset){{if(dataset.meta?.role==="stress_aggregate"||dataset.meta?.dataset_id==="stress_aggregate") return `aligned mean & variability (${{dataset.rows.length}} grid points)`; return `${{dataset.meta.dataset_id}} · ${{dataset.meta.role||"dataset"}}`;}}
function displayFields(dataset){{if(dataset.meta?.role==="stress_aggregate"||dataset.meta?.dataset_id==="stress_aggregate") return [{{key:"x_common",label:"norm. strain %",editable:false}},{{key:"mean_stress_MPa",label:"mean MPa ✎",editable:true}},{{key:"std_stress_MPa",label:"σ MPa ✎",editable:true}},{{key:"min_stress_MPa",label:"min MPa ✎",editable:true}},{{key:"max_stress_MPa",label:"max MPa ✎",editable:true}},{{key:"run_count",label:"n",editable:false}}]; const fields=dataset.meta.fields?.length?dataset.meta.fields:Object.keys(dataset.rows[0]||{{}}); return fields.map(key=>({{key,label:key,editable:Number.isFinite(Number(dataset.rows.find(row=>row[key]!==undefined)?.[key]))}}));}}
function dataCell(row,field,index){{const value=row[field.key]??""; const text=formatCellValue(value); const numeric=value!==""&&Number.isFinite(Number(value)); if(field.editable&&numeric) return `<td><input data-row="${{index}}" data-field="${{escapeHtml(field.key)}}" value="${{escapeHtml(text)}}"></td>`; return `<td data-row="${{index}}" data-field="${{escapeHtml(field.key)}}">${{escapeHtml(text)}}</td>`;}}
function formatCellValue(value){{const number=Number(value); if(value!==""&&Number.isFinite(number)) return String(Number(number.toFixed(3))); return value;}}
function exportCsv(){{const d=datasets[$("datasetSelect").value]||Object.values(datasets)[0]; if(!d)return; const fields=d.meta.fields?.length?d.meta.fields:Object.keys(d.rows[0]||{{}}); const body=[fields.join(","),...d.rows.map(r=>fields.map(f=>csvCell(r[f])).join(","))].join("\\n"); download(`${{plotPackage.plot_id}}.${{d.meta.dataset_id}}.data_only.csv`,"text/csv",body);}}
function csvCell(v){{const s=String(v??""); return /[",\\n]/.test(s)?`"${{s.replace(/"/g,'""')}}"`:s;}}
function download(name,type,content){{const blob=new Blob([content],{{type}}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}}
function escapeHtml(v){{return String(v).replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));}}
["titleInput","xLabelInput","yLabelInput","xMin","xMax","yMin","yMax","masterScale","opacityScale","gridToggle","legendToggle"].forEach(id=>$(id).addEventListener("change",()=>{{state.title=$("titleInput").value;state.xLabel=$("xLabelInput").value;state.yLabel=$("yLabelInput").value;state.xMin=$("xMin").value;state.xMax=$("xMax").value;state.yMin=$("yMin").value;state.yMax=$("yMax").value;state.scale=Number($("masterScale").value);state.opacity=Number($("opacityScale").value);state.grid=$("gridToggle").checked;state.legend=$("legendToggle").checked;render();}}));
document.querySelectorAll(".segment button").forEach(b=>b.onclick=()=>{{document.querySelectorAll(".segment button").forEach(x=>x.classList.remove("active"));document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active"));b.classList.add("active");$(`panel-${{b.dataset.panel}}`).classList.add("active");}});
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{{document.querySelectorAll(".tabs button").forEach(x=>x.classList.remove("active"));b.classList.add("active");activeFigure=b.dataset.figure;renderLayerControls();render();}});
$("archiveButton").onclick=()=>{{location.href="__HOME_HTML__";}}; $("exportButton").onclick=()=>$("exportMenu").classList.toggle("open"); $("resetView").onclick=render; $("resetZoom").onclick=render; $("alignOrigin").onclick=()=>{{$("xMin").value="0";$("yMin").value="0";$("xMin").dispatchEvent(new Event("change"));}}; $("resetPage").onclick=()=>location.reload();
["openDataSheet","openDataSheet2"].forEach(id=>{{const el=$(id); if(el) el.onclick=()=>$("dataModal").classList.add("open");}}); ["openSpecSheet","openSpecSheet2"].forEach(id=>{{const el=$(id); if(el) el.onclick=()=>$("specModal").classList.add("open");}}); document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$(`${{b.dataset.close}}`).classList.remove("open"));
$("datasetSelect").onchange=()=>{{state.dataPage=0;renderDataTable();}}; $("prevDataPage").onclick=()=>{{state.dataPage=Math.max(0,state.dataPage-1);renderDataTable();}}; $("nextDataPage").onclick=()=>{{state.dataPage+=1;renderDataTable();}}; $("resetData").onclick=renderDataTable; $("downloadData").onclick=exportCsv; document.querySelector('[data-export="csv"]').onclick=exportCsv; $("downloadSpecExport").onclick=()=>download(`${{plotPackage.plot_id}}.full_vegalite_spec_with_data.vl.json`,"application/json",JSON.stringify(buildSpec(),null,2)); $("downloadSpecJson").onclick=$("downloadSpecExport").onclick; $("downloadPackage").onclick=()=>download(`${{plotPackage.plot_id}}.full_plot_package_with_data.json`,"application/json",JSON.stringify(plotPackage,null,2));
$("showAllLayers").onclick=()=>{{Object.keys(state.visibleLayers).forEach(key=>state.visibleLayers[key]=true); document.querySelectorAll("#layerControls input[type=checkbox]").forEach(input=>input.checked=true); render();}}; $("hideContextLayers").onclick=()=>{{Array.from(document.querySelectorAll("#layerControls input[type=checkbox]")).forEach((input,index)=>{{if(index>1){{input.checked=false;}}}}); Object.keys(state.visibleLayers).forEach((key,index)=>state.visibleLayers[key]=index<=1); render();}};
$("downloadSvg").onclick=async()=>{{if(rendered)download(`${{plotPackage.plot_id}}.svg`,"image/svg+xml",await rendered.view.toSVG());}}; $("downloadPng").onclick=async()=>{{if(!rendered)return;const canvas=await rendered.view.toCanvas(2);canvas.toBlob(b=>{{if(b)download(`${{plotPackage.plot_id}}.png`,"image/png",b);}});}};
$("formatSpec").onclick=()=>{{$("specEditor").value=JSON.stringify(JSON.parse($("specEditor").value),null,2);}}; $("validateSpec").onclick=()=>{{try{{JSON.parse($("specEditor").value);$("specStatus").textContent="Spec JSON is valid."; $("specStatus").className="status success";}}catch(e){{$("specStatus").textContent=e.message; $("specStatus").className="status error";}}}}; $("copySpec").onclick=()=>navigator.clipboard?.writeText($("specEditor").value); $("applySpec").onclick=()=>{{customSpec=JSON.parse($("specEditor").value);render();}}; $("regenerateSpec").onclick=()=>{{customSpec=null;render();}};
$("saveLook").onclick=()=>{{const name=$("lookName").value.trim()||"Plot look"; const looks=JSON.parse(localStorage.getItem(storeKey)||"[]"); looks.push({{name,state:clone(state)}}); localStorage.setItem(storeKey,JSON.stringify(looks)); $("lookStatus").textContent=`Saved ${{name}}.`;}}; $("importLook").onclick=()=>{{$("lookStatus").textContent="Import file support is pending in this active convergence pass.";}}
boot();
</script></body></html>"""
    return (
        template.replace("__TITLE_HTML__", html.escape(title))
        .replace("__HOME_HTML__", html.escape(home_path))
        .replace("__PACKAGE_JSON__", package_json)
        .replace("__TITLE_JSON__", title_json)
        .replace("{{", "{")
        .replace("}}", "}")
    )


def _compact_plot_wrapper_html(*, title: str, package_path: str, home_path: str = "../../../index.html") -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_compact_plot_wrapper_html(title=title, package_path=package_path, home_path=home_path)
    return render_compact_plot_wrapper(
        compact_plot_wrapper_context(
            title=title,
            package_path=package_path,
            home_path=home_path,
        )
    )


def _legacy_compact_plot_wrapper_html(*, title: str, package_path: str, home_path: str = "../../../index.html") -> str:
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<style>
:root{color-scheme:light;--bg:#f4f6f8;--surface:#fff;--panel:#f8fafc;--line:#d7dde5;--ink:#17202a;--muted:#5b6470;--blue:#0b5cad;--green:#146c43;--amber:#8a5a00;--bad:#b42318}
*{box-sizing:border-box}
body{font-family:Arial,sans-serif;margin:0;color:var(--ink);line-height:1.35;background:var(--bg)}
a{color:var(--blue)}main{padding:18px;max-width:1680px;margin:0 auto}
h1{font-size:24px;margin:6px 0 4px;line-height:1.2;letter-spacing:0}.subtle,.status{color:var(--muted)}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:end;margin-bottom:12px}
.crumbs{font-size:13px;margin:0 0 4px}.summary-strip{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.mode-chip,.export-kind{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--line);border-radius:999px;background:var(--surface);font-size:11px;font-weight:700;line-height:1;padding:5px 8px;text-transform:lowercase}
.mode-chip.data,.export-kind.data{border-color:#97c5a9;color:var(--green);background:#f1faf4}.mode-chip.settings,.export-kind.settings{border-color:#c7b995;color:var(--amber);background:#fff9e8}.mode-chip.full,.export-kind.full{border-color:#a6bed7;color:var(--blue);background:#eef6ff}
.top-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}.workspace{display:grid;grid-template-columns:minmax(320px,390px) minmax(0,1fr);gap:16px;align-items:start}
.plot-controls{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:12px;position:sticky;top:12px;box-shadow:0 1px 2px rgba(23,32,42,.04)}
.tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin:0 0 12px}.tabs button{padding:8px 6px}.tabs button[aria-selected="true"]{background:#e9f1fb;border-color:#7ca8d3;color:#083f78;font-weight:700}
.panel{display:none}.panel.active{display:block}.control-group{border:0;border-top:1px solid var(--line);margin:12px 0 0;padding:12px 0 0}.control-group:first-child{border-top:0;margin-top:0;padding-top:0}
legend{font-weight:700;padding:0 6px 0 0}.field{display:grid;grid-template-columns:96px minmax(0,1fr);gap:8px;align-items:center;margin:8px 0}
.field label,.check label{font-size:13px;color:#26313d}.field input,.field select,.file-input{width:100%;min-width:0;border:1px solid #c9d2dd;border-radius:6px;padding:7px;background:white}.file-input{display:block;border-style:dashed}
.split{display:grid;grid-template-columns:1fr 1fr;gap:8px}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
button{font:inherit;border:1px solid #b9c6d3;background:white;border-radius:6px;padding:7px 10px;cursor:pointer;min-height:34px}button.primary{background:var(--blue);color:white;border-color:var(--blue)}button.danger{border-color:#d0a3a3;color:var(--bad)}button:disabled{opacity:.55;cursor:not-allowed}
.chart-shell{min-width:0;border:1px solid var(--line);border-radius:8px;background:var(--surface);overflow:hidden}.chart-toolbar{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding:10px 12px;background:#fbfcfd}.chart{width:100%;min-height:560px;padding:14px}
.status{margin:10px 0 0;font-size:13px}.status.error{color:var(--bad)}.status.success{color:var(--green)}.status.warn{color:var(--amber)}
.layer-card{border:1px solid var(--line);border-radius:8px;background:#fff;margin:8px 0;padding:10px}.layer-head{display:flex;gap:8px;align-items:flex-start;justify-content:space-between}.layer-title{font-weight:700;overflow-wrap:anywhere}.layer-meta{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.layer-note{font-size:12px;color:var(--muted);margin-top:7px}.layer-actions{white-space:nowrap}
.table-tools{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px;background:white;max-height:560px;margin-top:10px}.data-table{width:100%;border-collapse:collapse;font-size:12px;table-layout:auto}.data-table th,.data-table td{border:1px solid var(--line);padding:5px 6px;vertical-align:top}.data-table th{position:sticky;top:0;background:#eef2f6;z-index:1}.data-table td[contenteditable]{background:#fffdf5;min-width:76px;outline:none}.data-table td.invalid{outline:2px solid var(--bad);background:#fff0f0}
textarea{width:100%;min-height:260px;font-family:Consolas,monospace;font-size:12px;border:1px solid #c9d2dd;border-radius:6px;padding:8px;resize:vertical}.export-grid{display:grid;grid-template-columns:1fr;gap:10px}.export-card{border:1px solid var(--line);border-radius:8px;background:white;padding:10px}.export-card h3{font-size:15px;margin:8px 0 4px}.export-card p{margin:0;color:var(--muted);font-size:12px}.code-name{font-family:Consolas,monospace;font-size:11px;overflow-wrap:anywhere}
@media (max-width:1020px){main{padding:12px}.topbar{grid-template-columns:1fr}.top-actions{justify-content:flex-start}.workspace{grid-template-columns:1fr}.plot-controls{position:static}.chart{min-height:420px}.tabs{grid-template-columns:repeat(3,1fr)}}
@media (max-width:560px){.split,.table-tools{grid-template-columns:1fr}.field{grid-template-columns:1fr}.tabs{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body><main class="mtda-workbench-v14 refined">
<header class="topbar">
<div>
<p class="crumbs"><a href="__HOME_PATH__">Back to home</a> / <a href="__PACKAGE_PATH__">Compact plot package</a></p>
<h1 id="pageTitle">__TITLE__</h1>
<div class="summary-strip">
<span class="mode-chip data">external CSV data</span><span class="mode-chip settings">settings-only profiles</span><span class="mode-chip full">hydrated exports on demand</span>
<span class="subtle" id="packageSummary">Loading package...</span>
</div>
</div>
<div class="top-actions"><button type="button" id="resetPage" class="danger">Reset page</button><button type="button" id="downloadSpecQuick">JSON</button><button type="button" id="downloadSvgQuick">SVG</button></div>
</header>
<div class="workspace">
<aside class="plot-controls" id="controls">
<div class="tabs" role="tablist">
<button type="button" data-tab="plot" aria-selected="true">Plot</button><button type="button" data-tab="layers">Layers</button><button type="button" data-tab="data">Data</button><button type="button" data-tab="spec">Spec</button><button type="button" data-tab="export">Export</button>
</div>
<section class="panel active" id="tab-plot">
<fieldset class="control-group"><legend>Axis range</legend>
<div class="split"><div class="field"><label for="xMin">x min</label><input id="xMin" inputmode="decimal"></div><div class="field"><label for="xMax">x max</label><input id="xMax" inputmode="decimal"></div></div>
<div class="split"><div class="field"><label for="yMin">y min</label><input id="yMin" inputmode="decimal"></div><div class="field"><label for="yMax">y max</label><input id="yMax" inputmode="decimal"></div></div>
</fieldset>
<fieldset class="control-group"><legend>Axis labels</legend><div class="field"><label for="xLabel">x label</label><input id="xLabel"></div><div class="field"><label for="yLabel">y label</label><input id="yLabel"></div></fieldset>
<fieldset class="control-group"><legend>Canvas</legend>
<div class="split"><div class="field"><label for="styleWidth">width</label><input id="styleWidth" type="number" min="120" step="10" placeholder="fit"></div><div class="field"><label for="styleHeight">height</label><input id="styleHeight" type="number" min="120" step="10" placeholder="auto"></div></div>
<div class="field"><label for="fontFamily">font</label><select id="fontFamily"><option value="">Default</option><option value="Arial">Arial</option><option value="Calibri">Calibri</option><option value="Segoe UI">Segoe UI</option><option value="Times New Roman">Times New Roman</option></select></div>
</fieldset>
<fieldset class="control-group"><legend>Marks</legend>
<div class="field"><label for="lineWidth">line</label><input id="lineWidth" type="range" min="0.25" max="3" step="0.25" value="1"></div>
<div class="field"><label for="pointSize">points</label><input id="pointSize" type="range" min="0.5" max="4" step="0.25" value="1"></div>
<div class="field"><label for="opacity">opacity</label><input id="opacity" type="range" min="0.05" max="1" step="0.05" value="1"></div>
<div class="field"><label for="plotTitle">title</label><input id="plotTitle"></div>
</fieldset>
<div class="buttons"><button type="button" class="primary" id="applyControls">Apply</button><button type="button" id="resetControls">Reset controls</button></div>
</section>
<section class="panel" id="tab-layers"><fieldset class="control-group"><legend>Semantic layers</legend><p class="status" id="layerStatus"></p><div id="layerControls"></div></fieldset></section>
<section class="panel" id="tab-data"><fieldset class="control-group"><legend>Data <span class="export-kind data">data only</span></legend><div class="field"><label for="datasetSelect">dataset</label><select id="datasetSelect"></select></div><div class="table-tools"><input id="dataFilter" placeholder="filter rows"><div class="buttons"><button type="button" id="resetDataset">Reset dataset</button><button type="button" id="resetAllData">Reset all</button><button type="button" id="downloadDataset">CSV</button></div></div><p class="status" id="dataStatus"></p><p class="subtle" id="datasetSummary"></p><div id="dataTable"></div></fieldset></section>
<section class="panel" id="tab-spec"><fieldset class="control-group"><legend>Spec <span class="export-kind full">plot spec + hydrated data</span></legend><p class="subtle">Generated render/export JSON with hydrated data arrays. Not a settings-only profile.</p><textarea id="specEditor" spellcheck="false"></textarea><div class="buttons"><button type="button" id="formatSpec">Format</button><button type="button" id="validateSpec">Validate</button><button type="button" id="applySpec">Apply JSON</button><button type="button" id="resetSpec">Reset generated</button><button type="button" id="downloadSpec">Full JSON</button></div><p class="status" id="specStatus"></p></fieldset></section>
<section class="panel" id="tab-export"><fieldset class="control-group"><legend>Export</legend>
<div class="export-grid">
<div class="export-card"><span class="export-kind settings">settings only</span><h3>Plot style profile</h3><p>Reusable view, design and layer settings. No plot rows.</p><p class="code-name">*.settings_only.plot_profile.json</p><div class="buttons"><button type="button" id="downloadProfile">Download profile</button><label class="file-input">Import profile <input id="importProfile" type="file" accept=".json,application/json"></label></div></div>
<div class="export-card"><span class="export-kind data">data only</span><h3>Selected dataset CSV</h3><p>Current working rows for the selected dataset.</p><p class="code-name">*.{dataset_id}.data_only.csv</p><div class="buttons"><button type="button" id="downloadDatasetExport">Download CSV</button></div></div>
<div class="export-card"><span class="export-kind full">plot image</span><h3>Rendered figure</h3><p>Current visible plot as static output.</p><p class="code-name">*.svg / *.png</p><div class="buttons"><button type="button" id="downloadSvg">SVG</button><button type="button" id="downloadPng">PNG</button></div></div>
<div class="export-card"><span class="export-kind full">plot spec + hydrated data</span><h3>Vega-Lite JSON</h3><p>Current render/export spec with hydrated data arrays.</p><p class="code-name">*.full_vegalite_spec_with_data.vl.json</p><div class="buttons"><button type="button" id="downloadSpecExport">Download JSON</button></div></div>
<div class="export-card"><span class="export-kind full">compact plot package + data</span><h3>Compact package</h3><p>Current working package plus editable data rows.</p><p class="code-name">*.full_plot_package_with_data.json</p><div class="buttons"><button type="button" id="downloadPackage">Download package</button></div></div>
</div>
</fieldset></section>
<div class="status" id="plotStatus"></div>
</aside>
<section class="chart-shell"><div class="chart-toolbar"><span id="activeSummary" class="subtle">Preparing plot...</span><div class="buttons"><button type="button" id="toggleAllLayers">Toggle layers</button><button type="button" id="refreshPlot">Refresh</button></div></div><div id="plot" class="chart"></div></section>
</div>
</main>
<script>
const packagePath = "__PACKAGE_PATH__";
let originalPackage = null;
let workingPackage = null;
let templateSpec = null;
let originalDatasets = {};
let workingDatasets = {};
let currentSpec = null;
let rendered = null;
let editTimer = null;
const state = {visibleLayers:{}, layerOrder:[]};
const controls = {
  xMin: byId("xMin"), xMax: byId("xMax"), yMin: byId("yMin"), yMax: byId("yMax"),
  xLabel: byId("xLabel"), yLabel: byId("yLabel"), lineWidth: byId("lineWidth"),
  opacity: byId("opacity"), pointSize: byId("pointSize"), styleWidth: byId("styleWidth"),
  styleHeight: byId("styleHeight"), fontFamily: byId("fontFamily"),
  plotTitle: byId("plotTitle"), datasetSelect: byId("datasetSelect"), dataFilter: byId("dataFilter")
};
function byId(id){return document.getElementById(id);}
function clone(value){return JSON.parse(JSON.stringify(value));}
function setStatus(text, level){const node=byId("plotStatus"); node.textContent=text || ""; node.className=`status ${level || ""}`.trim();}
function setNodeStatus(id,text,level){const node=byId(id); node.textContent=text || ""; node.className=`status ${level || ""}`.trim();}
async function loadJson(path){const response = await fetch(path); if(!response.ok) throw new Error(`${path}: ${response.status}`); return response.json();}
async function loadText(path){const response = await fetch(path); if(!response.ok) throw new Error(`${path}: ${response.status}`); return response.text();}
class ArchiveTableStore {
  constructor(baseUrl=".", checksumIndex=null){this.baseUrl=baseUrl; this.cache=new Map(); this.checksumIndex=checksumIndex;}
  async csv(member){if(this.cache.has(member)) return this.cache.get(member); const rows=parseCsv(await loadText(this.resolveMemberUrl(member))); this.cache.set(member, rows); return rows;}
  resolveMemberUrl(member){return member.startsWith("../") || member.startsWith("./") ? member : relativeFromPackage(member);}
}
function relativeFromPackage(member){
  const baseMember=(originalPackage && originalPackage.html_member) ? originalPackage.html_member : packagePath;
  const base=baseMember.split("/").slice(0,-1);
  const target=member.split("/");
  let common=0;
  while(common<base.length && common<target.length && base[common]===target[common]) common++;
  return [...Array(base.length-common).fill(".."), ...target.slice(common)].join("/") || target[target.length-1];
}
async function loadPackageDatasets(pkg){
  const loaded = {};
  if(Array.isArray(pkg.embedded_datasets) && pkg.embedded_datasets.length){
    for(const dataset of pkg.embedded_datasets) loaded[dataset.dataset_id]=clone(dataset.rows || []);
    return loaded;
  }
  const views = new Map((pkg.plot_data_views || []).map(view => [view.dataset_id, view]));
  const store = new ArchiveTableStore(".");
  for (const dataset of pkg.datasets || []) {
    const view = views.get(dataset.dataset_id) || (dataset.view_ref ? views.get(dataset.view_ref) : null);
    if(view) loaded[dataset.dataset_id] = await resolvePlotDataView(view, store);
    else if(dataset.path) loaded[dataset.dataset_id] = parseCsv(await loadText(dataset.path));
    else loaded[dataset.dataset_id] = [];
  }
  return loaded;
}
async function resolvePlotDataView(view, store){
  const memberRows = {};
  for(const member of view.source_members || []) memberRows[member] = await store.csv(member);
  const id = view.transform_id;
  if(id === "run.front_rear_strain_envelope.v1") return runEnvelope(firstSourceRows(view, memberRows));
  if(id === "run.front_rear_strain_traces.v1") return runTraces(firstSourceRows(view, memberRows));
  if(id === "run.bounded_average_curve.v1") return runAverage(firstSourceRows(view, memberRows));
  if(id === "run.empty_chord_line.v1" || id === "run.empty_chord_points.v1") return [];
  if(id === "run.analysis_markers.v1") return runMarkers(firstSourceRows(view, memberRows));
  if(id === "aggregate.all_runs_resampled_curve_family.v1") return aggregateCurveFamily(view.source_members || [], memberRows);
  if(id === "aggregate.stress_band_from_run_grid.v1") return aggregateStressBand(view.source_members || [], memberRows);
  if(id === "aggregate.bending_summary_passthrough.v1") return (view.source_members || []).flatMap(member => clone(memberRows[member] || []));
  if(id === "aggregate.fmax_distribution.v1") return aggregateFmax(view.source_members || [], memberRows);
  throw new Error(`Unsupported plot data view transform: ${id}`);
}
function firstSourceRows(view, memberRows){const member=(view.source_members || [])[0]; return memberRows[member] || [];}
function n(value){if(value === null || value === undefined || value === "") return null; const out=Number(value); return Number.isFinite(out) ? out : null;}
function firstNum(row, keys){for(const key of keys){const value=n(row[key]); if(value !== null) return value;} return null;}
function runEnvelope(rows){return rows.map(row => {const stress=n(row.stress_MPa), front=firstNum(row,["front_strain_abs","front_strain"]), rear=firstNum(row,["rear_strain_abs","rear_strain"]); if(stress===null||front===null||rear===null) return null; return {strain_min:Math.min(front,rear)*100,strain_max:Math.max(front,rear)*100,stress,point_index:n(row.point_index),series:"front/rear strain agreement envelope"};}).filter(Boolean);}
function runTraces(rows){const out=[]; for(const row of rows){const stress=n(row.stress_MPa), front=firstNum(row,["front_strain_abs","front_strain"]), rear=firstNum(row,["rear_strain_abs","rear_strain"]), point_index=n(row.point_index); if(stress===null) continue; if(front!==null) out.push({gauge_strain:front*100,stress,point_index,series:"front strain"}); if(rear!==null) out.push({gauge_strain:rear*100,stress,point_index,series:"rear strain"});} return out;}
function runAverage(rows){return rows.map(row => {const strain=firstNum(row,["mean_strain","strain_mm_per_mm"]), stress=n(row.stress_MPa); if(strain===null||stress===null) return null; return {strain:strain*100,stress,point_index:n(row.point_index),series:"average strain curve"};}).filter(Boolean);}
function runMarkers(rows){if(!rows.length) return []; return [["start marker",rows[0]],["end marker (max point / failure strain)",rows[rows.length-1]]].map(([marker,row]) => {const strain=firstNum(row,["mean_strain","strain_mm_per_mm"]), stress=n(row.stress_MPa); if(strain===null||stress===null) return null; return {marker,strain:strain*100,stress,point_index:n(row.point_index)};}).filter(Boolean);}
function progressPoints(rows){const last=Math.max(rows.length-1,1); return rows.map((row,index) => {const stress=n(row.stress_MPa); if(stress===null) return null; let x=firstNum(row,["experiment_progress","analysis_progress","x_common","x_normalized"]); if(x===null) x=index/last; if(x>1.5) x=x/100; return [Math.max(0,Math.min(1,x)), stress];}).filter(Boolean).sort((a,b)=>a[0]-b[0]);}
function interp(points,target){if(!points.length) return 0; if(target<=points[0][0]) return points[0][1]; for(let i=1;i<points.length;i++){const [x0,y0]=points[i-1], [x1,y1]=points[i]; if(target<=x1){if(Math.abs(x1-x0)<=1e-15) return y1; return y0+(y1-y0)*((target-x0)/(x1-x0));}} return points[points.length-1][1];}
function runIdFromMember(member, rows){for(const row of rows){if(row.run_id) return String(row.run_id);} const file=member.split("/").pop() || ""; return file.startsWith("run_") ? file.split("_").slice(0,2).join("_") : file.replace(/\\.csv$/,"");}
function meanStd(values){const mean=values.reduce((a,b)=>a+b,0)/Math.max(values.length,1); if(values.length<=1) return [mean,0]; const variance=values.reduce((sum,value)=>sum+(value-mean)*(value-mean),0)/(values.length-1); return [mean,Math.sqrt(variance)];}
function aggregateCurveFamily(sourceMembers, memberRows){const grid=Array.from({length:250},(_,i)=>i/249); const byRun=[]; const grouped=new Map(); for(const member of sourceMembers){const rows=memberRows[member] || []; const run_id=runIdFromMember(member, rows); const points=progressPoints(rows); const runRows=grid.map(x_common => ({run_id,x_common,y_observed:interp(points,x_common)})); byRun.push(runRows); for(const row of runRows){const key=String(row.x_common); if(!grouped.has(key)) grouped.set(key,[]); grouped.get(key).push(row.y_observed);}} const stats=new Map([...grouped.entries()].map(([key,values]) => [key,meanStd(values)])); const out=[]; for(const runRows of byRun){for(const row of runRows){const [mean,std]=stats.get(String(row.x_common)); out.push({run_id:row.run_id,cohort_id:"whole_comparable_dataset",x_common:row.x_common,y_observed:row.y_observed,y_reference:mean,y_variability:std,standardized_residual:std ? (row.y_observed-mean)/std : 0,diagnostic_classification:"CURVE_SHAPE_NOT_ASSESSED"});}} return out;}
function aggregateStressBand(sourceMembers, memberRows){const family=aggregateCurveFamily(sourceMembers, memberRows); const grouped=new Map(); for(const row of family){if(Math.abs(row.x_common)<=1e-15) continue; const key=String(row.x_common); if(!grouped.has(key)) grouped.set(key,[]); grouped.get(key).push(row.y_observed);} return [...grouped.entries()].sort((a,b)=>Number(a[0])-Number(b[0])).map(([key,values]) => {const [mean,std]=meanStd(values); return {x_common:Number(key),mean_stress_MPa:mean,min_stress_MPa:Math.min(...values),max_stress_MPa:Math.max(...values),std_stress_MPa:std,lo_stress_MPa:mean-std,hi_stress_MPa:mean+std,run_count:values.length};});}
function percentile(ordered,p){if(ordered.length===1) return ordered[0]; const pos=(ordered.length-1)*p/100; const lo=Math.floor(pos), hi=Math.min(lo+1,ordered.length-1), f=pos-lo; return ordered[lo]+(ordered[hi]-ordered[lo])*f;}
function aggregateFmax(sourceMembers, memberRows){const strengths=sourceMembers.flatMap(member => (memberRows[member] || []).map(row => firstNum(row,["compressive_strength_MPa","max_stress_MPa"])).filter(value => value !== null)).sort((a,b)=>a-b); if(!strengths.length) return []; const [mean,std]=meanStd(strengths); return [{x_position:100,label:"Fmax",min_strength_MPa:strengths[0],q1_strength_MPa:percentile(strengths,25),median_strength_MPa:percentile(strengths,50),q3_strength_MPa:percentile(strengths,75),max_strength_MPa:strengths[strengths.length-1],mean_strength_MPa:mean,std_strength_MPa:std,run_count:strengths.length}];}
async function bootstrap(){
  try {
    originalPackage = await loadJson(packagePath);
    templateSpec = await loadJson(originalPackage.template_path);
    originalDatasets = await loadPackageDatasets(originalPackage);
    workingPackage = clone(originalPackage);
    workingDatasets = clone(originalDatasets);
    initControls();
    renderDataTable();
    updatePackageSummary();
    await render();
  } catch (error) {
    setStatus(`Could not load compact package data. Open this MTDA through a local/static viewer if file loading is blocked. ${error.message || error}`, "error");
    byId("activeSummary").textContent = "Package load failed.";
  }
}
function parseCsv(text){
  const rows = text.trim() ? text.trim().split(/\\r?\\n/) : [];
  if (!rows.length) return [];
  const headers = splitCsv(rows[0]);
  return rows.slice(1).map(line => Object.fromEntries(splitCsv(line).map((value,index) => [headers[index] || `field_${index+1}`, coerce(value)])));
}
function splitCsv(line){const values=[]; let value="", quoted=false; for(let i=0;i<line.length;i++){const char=line[i]; if(char === '"' && line[i+1] === '"'){value += '"'; i++;} else if(char === '"'){quoted=!quoted;} else if(char === "," && !quoted){values.push(value); value="";} else value += char;} values.push(value); return values;}
function csvEscape(value){const text = String(value ?? ""); return /[",\\n\\r]/.test(text) ? `"${text.replace(/"/g,'""')}"` : text;}
function coerce(value){const text = String(value ?? ""); if(text.trim() === "") return ""; const number = Number(text); return Number.isFinite(number) ? number : text;}
function datasetCsv(datasetId){const rows = workingDatasets[datasetId] || []; const fields = (workingPackage.datasets || []).find(item => item.dataset_id === datasetId)?.fields || Object.keys(rows[0] || {}); return [fields.join(","), ...rows.map(row => fields.map(field => csvEscape(row[field])).join(","))].join("\\n");}
function hydrate(node){if(Array.isArray(node)) return node.map(hydrate); if(!node || typeof node !== "object") return node; if(node.__compact_dataset_ref__) return {values: clone(workingDatasets[node.__compact_dataset_ref__] || [])}; const next={}; for(const [key,value] of Object.entries(node)) next[key]=hydrate(value); return next;}
function layerList(source){return Array.isArray(source.layer) ? source.layer : [source];}
function layerName(layer,index){return layer.name || layer.usermeta?.layer_id || `layer ${index+1}`;}
function layerMark(layer){const mark=markObject(layer.mark); return mark.type || "layer";}
function layerDatasetRef(layer){return layer.data?.__compact_dataset_ref__ || "";}
function datasetMeta(datasetId){return (workingPackage.datasets || []).find(item => item.dataset_id === datasetId) || {};}
function initControls(){
  state.visibleLayers = {};
  state.layerOrder = [];
  controls.plotTitle.value = originalPackage.title || byId("pageTitle").textContent;
  const firstEncoding = firstXYEncoding(templateSpec);
  controls.xLabel.value = firstEncoding?.x?.title || "";
  controls.yLabel.value = firstEncoding?.y?.title || "";
  controls.xMin.value = ""; controls.xMax.value = ""; controls.yMin.value = ""; controls.yMax.value = "";
  controls.lineWidth.value = 1; controls.opacity.value = 1; controls.pointSize.value = 1;
  controls.styleWidth.value = ""; controls.styleHeight.value = ""; controls.fontFamily.value = "";
  renderLayerControls();
  controls.datasetSelect.innerHTML = "";
  for (const dataset of workingPackage.datasets || []) {
    const option = document.createElement("option"); option.value = dataset.dataset_id; option.textContent = `${dataset.dataset_id} - ${dataset.role || "plot data"} (${dataset.row_count ?? (workingDatasets[dataset.dataset_id] || []).length} rows)`;
    controls.datasetSelect.appendChild(option);
  }
  updateLayerStatus();
}
function renderLayerControls(){
  const target = byId("layerControls");
  target.innerHTML = "";
  layerList(templateSpec).forEach((layer,index) => {
    const id = `layer_${index}`; const name = layerName(layer,index); const datasetId = layerDatasetRef(layer);
    state.visibleLayers[name] = true; state.layerOrder.push(name);
    const meta = datasetMeta(datasetId);
    const card = document.createElement("div"); card.className = "layer-card";
    card.innerHTML = `<div class="layer-head"><div><div class="layer-title">${escapeHtml(name)}</div><div class="layer-meta"><span class="mode-chip full">${escapeHtml(layerMark(layer))}</span>${datasetId ? `<span class="mode-chip data">${escapeHtml(datasetId)}</span>` : ""}${meta.role ? `<span class="mode-chip settings">${escapeHtml(meta.role)}</span>` : ""}</div><div class="layer-note">${escapeHtml(layer.encoding?.x?.field || "")}${layer.encoding?.y?.field ? " / " + escapeHtml(layer.encoding.y.field) : ""}</div></div><div class="layer-actions"><input type="checkbox" id="${id}" checked aria-label="Show ${escapeHtml(name)}"></div></div>`;
    card.querySelector("input").addEventListener("change", event => {state.visibleLayers[name] = event.target.checked; updateLayerStatus(); render();});
    target.appendChild(card);
  });
}
function firstXYEncoding(source){if(source.encoding?.x || source.encoding?.y) return source.encoding; for(const layer of layerList(source)) if(layer.encoding?.x || layer.encoding?.y) return layer.encoding; return {};}
function renderSpec(){
  const next = hydrate(clone(templateSpec));
  const title = controls.plotTitle.value.trim(); if(title) next.title = title;
  const width = parseNumber(controls.styleWidth.value), height = parseNumber(controls.styleHeight.value);
  next.width = width || "container"; if(height) next.height = height;
  next.autosize = {type:"fit-x", contains:"padding"};
  if(controls.fontFamily.value){next.config = {...(next.config || {}), font: controls.fontFamily.value, axis:{...(next.config?.axis || {}), labelFont:controls.fontFamily.value, titleFont:controls.fontFamily.value}, legend:{...(next.config?.legend || {}), labelFont:controls.fontFamily.value, titleFont:controls.fontFamily.value}, title:{...(next.config?.title || {}), font:controls.fontFamily.value}};}
  if(Array.isArray(next.layer)) next.layer = next.layer.filter((layer,index) => state.visibleLayers[layerName(layer,index)] !== false);
  applyRecursive(next, layer => { if(!layer.encoding) return; applyAxis(layer.encoding.x, controls.xLabel.value, controls.xMin.value, controls.xMax.value); applyAxis(layer.encoding.y, controls.yLabel.value, controls.yMin.value, controls.yMax.value); });
  applyStyle(next); return next;
}
function applyAxis(axis,title,minValue,maxValue){if(!axis) return; if(title) axis.title = title; const min=parseNumber(minValue), max=parseNumber(maxValue); if(min !== null && max !== null){axis.scale={...(axis.scale || {}), domain:[min,max]};}}
function applyStyle(source){const lineScale=Number(controls.lineWidth.value || 1); const opacityScale=Number(controls.opacity.value || 1); const pointScale=Number(controls.pointSize.value || 1); applyRecursive(source, layer => {const mark=markObject(layer.mark); if(["line","rule","area","trail"].includes(mark.type)) mark.strokeWidth=baseNumber(mark.strokeWidth,2)*lineScale; if(["point","circle","square"].includes(mark.type)){mark.size=baseNumber(mark.size,42)*pointScale; mark.filled = mark.filled ?? true;} if(mark.type !== "rect" && mark.type !== "text") mark.opacity=Math.max(0.01,Math.min(1,baseNumber(mark.opacity,1)*opacityScale)); layer.mark=mark;});}
function applyRecursive(node,fn){if(!node || typeof node !== "object") return; if(node.mark || node.encoding) fn(node); for(const key of ["layer","hconcat","vconcat","concat"]) if(Array.isArray(node[key])) node[key].forEach(item => applyRecursive(item, fn));}
function markObject(mark){return typeof mark === "string" ? {type:mark} : {...(mark || {type:"line"})};}
function baseNumber(value,fallback){const number=Number(value); return Number.isFinite(number) ? number : fallback;}
function parseNumber(value){if(value === "") return null; const number=Number(value); return Number.isFinite(number) ? number : null;}
function queueRender(){clearTimeout(editTimer); editTimer=setTimeout(render,180);}
async function render(){currentSpec = renderSpec(); byId("specEditor").value = JSON.stringify(currentSpec, null, 2); byId("pageTitle").textContent = controls.plotTitle.value || "__TITLE__"; try{rendered = await window.vegaEmbed("#plot", currentSpec, {actions:true, renderer:"canvas"}); setStatus("", "success"); updateActiveSummary();}catch(error){setStatus(`Plot render failed: ${error.message || error}`, "error");}}
function renderDataTable(){
  const datasetId = controls.datasetSelect.value; const rows = workingDatasets[datasetId] || []; const meta = (workingPackage.datasets || []).find(item => item.dataset_id === datasetId) || {}; const fields = meta.fields || Object.keys(rows[0] || {});
  const filter = controls.dataFilter.value.trim().toLowerCase();
  const indexedRows = rows.map((row,index) => ({row,index})).filter(item => !filter || fields.some(field => String(item.row[field] ?? "").toLowerCase().includes(filter)));
  const shown = indexedRows.slice(0,100);
  byId("datasetSummary").textContent = `${rows.length} rows / ${fields.length} fields / ${meta.path || meta.member || datasetId}${filter ? ` / ${indexedRows.length} matching` : ""}`;
  byId("dataTable").innerHTML = `<div class="table-wrap"><table class="data-table"><thead><tr>${fields.map(field => `<th title="${escapeHtml(field)}">${escapeHtml(field)}</th>`).join("")}</tr></thead><tbody>${shown.map(item => `<tr>${fields.map(field => `<td contenteditable data-row="${item.index}" data-field="${escapeHtml(field)}">${escapeHtml(item.row[field] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  byId("dataTable").querySelectorAll("td[contenteditable]").forEach(cell => cell.addEventListener("input", () => updateCell(cell)));
  setNodeStatus("dataStatus", shown.length < indexedRows.length ? `Showing ${shown.length} of ${indexedRows.length} matching rows.` : "", "warn");
}
function updateCell(cell){const datasetId=controls.datasetSelect.value; const row=Number(cell.dataset.row); const field=cell.dataset.field; const value=cell.textContent || ""; const original=originalDatasets[datasetId]?.[row]?.[field]; const invalid=value.includes("\\t") || value.includes("\\n") || (typeof original === "number" && value.trim() !== "" && !Number.isFinite(Number(value))); cell.classList.toggle("invalid", invalid); if(invalid){setNodeStatus("dataStatus", "Invalid cell value. Fix highlighted cells before export/render.", "error"); return;} workingDatasets[datasetId][row][field]=coerce(value); updatePackageSummary(); queueRender();}
function settingsProfile(){return {profile_type:"vega-workbench-plot-profile", schema_version:"0.3", source_plot_id:workingPackage.plot_id, viewControls:{title:controls.plotTitle.value,xLabel:controls.xLabel.value,yLabel:controls.yLabel.value,xMin:controls.xMin.value,xMax:controls.xMax.value,yMin:controls.yMin.value,yMax:controls.yMax.value,width:controls.styleWidth.value,height:controls.styleHeight.value,fontFamily:controls.fontFamily.value}, styleSettings:{lineWidth:controls.lineWidth.value,pointSize:controls.pointSize.value,opacity:controls.opacity.value}, hiddenLayers:Object.entries(state.visibleLayers).filter(([,visible]) => !visible).map(([layer]) => layer)};}
function packageWithData(){const payload=clone(workingPackage); payload.data_mode="embedded_rows"; payload.datasets=(payload.datasets || []).map(dataset => ({...dataset, rows:clone(workingDatasets[dataset.dataset_id] || [])})); return payload;}
function resetAll(){workingPackage=clone(originalPackage); workingDatasets=clone(originalDatasets); initControls(); renderDataTable(); updatePackageSummary(); render();}
function resetDataset(){const id=controls.datasetSelect.value; workingDatasets[id]=clone(originalDatasets[id] || []); renderDataTable(); updatePackageSummary(); render();}
function resetControls(){const datasets=clone(workingDatasets); initControls(); workingDatasets=datasets; renderDataTable(); render();}
function downloadBlob(name,type,content){const blob=new Blob([content],{type}); const url=URL.createObjectURL(blob); const link=document.createElement("a"); link.href=url; link.download=name; link.click(); URL.revokeObjectURL(url);}
function escapeHtml(value){return String(value).replace(/[&<>"']/g, char => char === "&" ? "&amp;" : char === "<" ? "&lt;" : char === ">" ? "&gt;" : char === '"' ? "&quot;" : "&#39;");}
function updatePackageSummary(){const datasetCount=(workingPackage?.datasets || []).length; const rows=Object.values(workingDatasets).reduce((sum,dataset) => sum + (dataset || []).length, 0); byId("packageSummary").textContent = `${datasetCount} datasets / ${rows} rows / MTDA package mode`; updateActiveSummary();}
function updateLayerStatus(){const active=Object.values(state.visibleLayers).filter(Boolean).length; const total=state.layerOrder.length; setNodeStatus("layerStatus", `${active} of ${total} layers visible.`, active ? "success" : "warn"); updateActiveSummary();}
function updateActiveSummary(){if(!workingPackage) return; const visible=Object.values(state.visibleLayers).filter(Boolean).length; const total=state.layerOrder.length; const datasetId=controls.datasetSelect.value || (workingPackage.datasets || [])[0]?.dataset_id || ""; const rows=(workingDatasets[datasetId] || []).length; byId("activeSummary").textContent = `${visible}/${total || 0} layers visible / ${datasetId || "no dataset"} / ${rows} rows`;}
function selectedDatasetDownload(){downloadBlob(`${workingPackage.plot_id}.${controls.datasetSelect.value}.data_only.csv`, "text/csv", datasetCsv(controls.datasetSelect.value));}
function specDownload(){downloadBlob(`${workingPackage.plot_id}.full_vegalite_spec_with_data.vl.json`, "application/json", JSON.stringify(currentSpec || renderSpec(), null, 2));}
function profileDownload(){downloadBlob(`${workingPackage.plot_id}.settings_only.plot_profile.json`, "application/json", JSON.stringify(settingsProfile(), null, 2));}
function applyProfile(profile){if(!profile || typeof profile !== "object") throw new Error("Profile must be a JSON object."); const view=profile.viewControls || {}; const style=profile.styleSettings || {}; controls.plotTitle.value=view.title ?? controls.plotTitle.value; controls.xLabel.value=view.xLabel ?? controls.xLabel.value; controls.yLabel.value=view.yLabel ?? controls.yLabel.value; controls.xMin.value=view.xMin ?? controls.xMin.value; controls.xMax.value=view.xMax ?? controls.xMax.value; controls.yMin.value=view.yMin ?? controls.yMin.value; controls.yMax.value=view.yMax ?? controls.yMax.value; controls.styleWidth.value=view.width ?? controls.styleWidth.value; controls.styleHeight.value=view.height ?? controls.styleHeight.value; controls.fontFamily.value=view.fontFamily ?? controls.fontFamily.value; controls.lineWidth.value=style.lineWidth ?? controls.lineWidth.value; controls.pointSize.value=style.pointSize ?? controls.pointSize.value; controls.opacity.value=style.opacity ?? controls.opacity.value; const hidden=new Set(profile.hiddenLayers || []); for(const layer of state.layerOrder) state.visibleLayers[layer]=!hidden.has(layer); byId("layerControls").querySelectorAll("input[type=checkbox]").forEach(input => {const name=state.layerOrder[Number(input.id.replace("layer_",""))]; input.checked=state.visibleLayers[name] !== false;}); updateLayerStatus(); render();}
document.querySelectorAll(".tabs button").forEach(button => button.addEventListener("click", () => {document.querySelectorAll(".tabs button").forEach(item => item.setAttribute("aria-selected","false")); document.querySelectorAll(".panel").forEach(item => item.classList.remove("active")); button.setAttribute("aria-selected","true"); byId(`tab-${button.dataset.tab}`).classList.add("active");}));
["xMin","xMax","yMin","yMax","xLabel","yLabel","lineWidth","pointSize","opacity","plotTitle","styleWidth","styleHeight","fontFamily"].forEach(key => controls[key].addEventListener("change", render));
byId("applyControls").addEventListener("click", render);
byId("resetControls").addEventListener("click", resetControls);
byId("resetPage").addEventListener("click", resetAll);
byId("refreshPlot").addEventListener("click", render);
byId("toggleAllLayers").addEventListener("click", () => {const anyVisible=Object.values(state.visibleLayers).some(Boolean); state.layerOrder.forEach(layer => state.visibleLayers[layer]=!anyVisible); byId("layerControls").querySelectorAll("input[type=checkbox]").forEach(input => input.checked=!anyVisible); updateLayerStatus(); render();});
byId("datasetSelect").addEventListener("change", () => {renderDataTable(); updateActiveSummary();});
byId("dataFilter").addEventListener("input", renderDataTable);
byId("resetDataset").addEventListener("click", resetDataset);
byId("resetAllData").addEventListener("click", resetAll);
byId("downloadDataset").addEventListener("click", selectedDatasetDownload);
byId("downloadDatasetExport").addEventListener("click", selectedDatasetDownload);
byId("downloadProfile").addEventListener("click", profileDownload);
byId("downloadSpec").addEventListener("click", specDownload);
byId("downloadSpecExport").addEventListener("click", specDownload);
byId("downloadSpecQuick").addEventListener("click", specDownload);
byId("downloadPackage").addEventListener("click", () => downloadBlob(`${workingPackage.plot_id}.full_plot_package_with_data.json`, "application/json", JSON.stringify(packageWithData(), null, 2)));
byId("formatSpec").addEventListener("click", () => {try{byId("specEditor").value = JSON.stringify(JSON.parse(byId("specEditor").value), null, 2); setNodeStatus("specStatus", "Spec formatted.", "success");}catch(error){setNodeStatus("specStatus", `Spec JSON is invalid: ${error.message || error}`, "error");}});
byId("validateSpec").addEventListener("click", () => {try{JSON.parse(byId("specEditor").value); setNodeStatus("specStatus", "Spec JSON is valid.", "success");}catch(error){setNodeStatus("specStatus", `Spec JSON is invalid: ${error.message || error}`, "error");}});
byId("applySpec").addEventListener("click", async () => {try{currentSpec=JSON.parse(byId("specEditor").value); rendered = await window.vegaEmbed("#plot", currentSpec, {actions:true, renderer:"canvas"}); setNodeStatus("specStatus", "Spec applied to view.", "success"); setStatus("");}catch(error){setNodeStatus("specStatus", `Spec apply failed: ${error.message || error}`, "error");}});
byId("resetSpec").addEventListener("click", render);
byId("importProfile").addEventListener("change", async event => {const file=event.target.files?.[0]; if(!file) return; try{applyProfile(JSON.parse(await file.text())); setStatus("Profile imported.", "success");}catch(error){setStatus(`Profile import failed: ${error.message || error}`, "error");} finally {event.target.value="";}});
byId("downloadSvg").addEventListener("click", async () => {if(rendered) downloadBlob(`${workingPackage.plot_id}.svg`, "image/svg+xml", await rendered.view.toSVG());});
byId("downloadSvgQuick").addEventListener("click", async () => {if(rendered) downloadBlob(`${workingPackage.plot_id}.svg`, "image/svg+xml", await rendered.view.toSVG());});
byId("downloadPng").addEventListener("click", async () => {if(!rendered) return; const canvas=await rendered.view.toCanvas(); canvas.toBlob(blob => {if(blob) downloadBlob(`${workingPackage.plot_id}.png`, "image/png", blob);});});
bootstrap();
</script>
</body></html>"""
    return (
        template
        .replace("__TITLE__", html.escape(title))
        .replace("__HOME_PATH__", html.escape(home_path))
        .replace("__PACKAGE_PATH__", html.escape(package_path))
    )


def _aligned_test_report_html(result: MethodRunResult, payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_aligned_test_report_html(result, payload)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>" for key, value in summary.items()
    )
    context = simple_report_context(
        projection_plane=ProjectionPlane.TEST,
        recipe_result_kind=RecipeResultKind.TEST_REPORT,
        page_title="Formal report",
        nav_html='<a href="../../index.html">Back to home</a> · <a href="audit_report.html">Audit report</a>',
        heading="Formal report",
        body_html=f"<p>{html.escape(result.method_package.method_id)} {html.escape(result.method_package.version)}</p>",
        table_body_html=rows,
    )
    return render_simple_report(context)


def _legacy_aligned_test_report_html(result: MethodRunResult, payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>" for key, value in summary.items()
    )
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Formal report</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;line-height:1.45}}table{{border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:6px 9px}}</style></head>
<body><p><a href=\"../../index.html\">Back to home</a> · <a href=\"audit_report.html\">Audit report</a></p>
<h1>Formal report</h1>
<p>{html.escape(result.method_package.method_id)} {html.escape(result.method_package.version)}</p>
<table><tbody>{rows}</tbody></table>
</body></html>"""


def _aligned_audit_report_html(result: MethodRunResult, payload: dict[str, Any]) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_aligned_audit_report_html(result, payload)
    status = html.escape(str(_nested(payload, "readiness", "status") or _nested(payload, "validation", "status") or ""))
    context = simple_report_context(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_REPORT,
        page_title="Audit report",
        nav_html='<a href="../../index.html">Back to home</a> · <a href="test_report.html">Formal report</a>',
        heading="Audit report",
        body_html=f"<p>ISO 14126 analysis evidence for {html.escape(result.source.path.name)}.</p>\n<p>Status: {status}</p>",
    )
    return render_simple_report(context)


def _legacy_aligned_audit_report_html(result: MethodRunResult, payload: dict[str, Any]) -> str:
    status = html.escape(str(_nested(payload, "readiness", "status") or _nested(payload, "validation", "status") or ""))
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Audit report</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;line-height:1.45}}</style></head>
<body><p><a href=\"../../index.html\">Back to home</a> · <a href=\"test_report.html\">Formal report</a></p>
<h1>Audit report</h1>
<p>ISO 14126 analysis evidence for {html.escape(result.source.path.name)}.</p>
<p>Status: {status}</p>
</body></html>"""


def _readme_text() -> str:
    return """# MTDA analysed dataset archive

Open `index.html` after extracting the archive for normal human use.

Canonical machine-readable data are stored under `dataset/` as CSV/JSON.
Formal report outputs are under `report/`.
Scientist-facing audit outputs are under `audit/`.
Software/debug/reproducibility metadata are under `software/`.

Internal archive validation uses `software/checksums.json`; no external sidecar checksum is required.
"""


def _archive_index_rows(files: dict[str, bytes]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted({*files, "archive_index.csv", "software/checksums.json"}):
        rows.append(
            {
                "path": path,
                "level": path.split("/", 1)[0] if "/" in path else "root",
                "role": _archive_role(path),
                "content": _archive_content(path),
                "source_of_truth": _archive_source_of_truth(path),
                "human_use": "yes" if path.endswith(".html") or path in {"README.md", "archive_index.csv"} else "",
                "machine_use": "yes" if path.endswith((".csv", ".json")) else "",
                "generated_from": "method run result",
                "notes": "",
            }
        )
    return rows


def _archive_role(path: str) -> str:
    if path == "index.html":
        return "main local website entry point"
    if path.startswith("report/"):
        return "formal report"
    if path.startswith("dataset/00_source/"):
        return "source lineage"
    if path.startswith("dataset/01_raw/"):
        return "raw input"
    if path.startswith("dataset/02_normalized/"):
        return "normalized input"
    if path.startswith("dataset/03_processed/"):
        return "run-level processed data/view"
    if path.startswith("dataset/04_aggregate/"):
        return "dataset-level aggregate data/view"
    if path.startswith("dataset/05_plots/"):
        return "plot definition/view"
    if path.startswith("audit/"):
        return "scientist-facing audit"
    if path.startswith("software/"):
        return "software reproducibility metadata"
    return "archive metadata"


def _archive_content(path: str) -> str:
    suffix = Path(path).suffix.casefold()
    return {
        ".html": "human static HTML view",
        ".csv": "canonical tabular data",
        ".json": "structured machine-readable data",
        ".md": "plain text explanation",
    }.get(suffix, "archive member")


def _archive_source_of_truth(path: str) -> str:
    if path.endswith(".html"):
        return "no"
    if path.startswith("dataset/") and path.endswith(".csv"):
        return "yes"
    if path in {"report/test_report.json", "audit/audit_report.json", "software/manifest.json", "software/provenance.json", "software/checksums.json"}:
        return "yes"
    return ""


def _method_package_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in result.method_package.recipe_files():
        files[f"method_package/{path.name}"] = path.read_bytes()
    return files


def _provenance(
    result: MethodRunResult,
    source_reference: dict[str, object],
    report_outputs: list[str] | None = None,
    compatibility_report: object | None = None,
    candidate_report: dict[str, object] | None = None,
    resolution_report: dict[str, object] | None = None,
) -> dict[str, object]:
    compatibility_status = getattr(getattr(compatibility_report, "status", None), "value", "")
    candidate_summary = (candidate_report or {}).get("summary", {}) if isinstance(candidate_report, dict) else {}
    resolution_summary = (resolution_report or {}).get("summary", {}) if isinstance(resolution_report, dict) else {}
    return {
        "events": [
            {
                "event": "schema_method_compatibility_checked",
                "timestamp": utc_now_iso(),
                "method_id": result.method_package.method_id,
                "status": compatibility_status,
                "artifact": "compatibility/schema_method_compatibility_report.json",
            },
            {
                "event": "mapping_candidates_generated",
                "timestamp": utc_now_iso(),
                "method_id": result.method_package.method_id,
                "candidate_summary": candidate_summary,
                "artifact": "mapping/mapping_candidate_report.json",
            },
            {
                "event": "mapping_profile_confirmed",
                "timestamp": utc_now_iso(),
                "method_id": result.method_package.method_id,
                "mapping_id": result.mapping.get("mapping_id"),
                "resolution_summary": resolution_summary,
                "artifact": "mapping/mapping_profile_used.json",
            },
            {
                "event": "mapping_profile_saved",
                "timestamp": utc_now_iso(),
                "method_id": result.method_package.method_id,
                "mapping_id": result.mapping.get("mapping_id"),
                "artifact": "mapping/mapping_profile_used.json",
            },
            {
                "event": "readiness_checked_with_mapping",
                "timestamp": utc_now_iso(),
                "method_id": result.method_package.method_id,
                "mapping_id": result.mapping.get("mapping_id"),
                "readiness_status": result.readiness_report.get("status"),
                "artifact": "readiness/readiness_report.json",
            },
            {
                "event": "method_run_completed",
                "timestamp": utc_now_iso(),
                "software": "compression_module_method_run_layer",
                "software_version": "0.1.0",
                "method_id": result.method_package.method_id,
                "method_version": result.method_package.version,
                "inputs": [str(result.source.path)],
                "outputs": [
                    "compatibility/schema_method_compatibility_report.json",
                    "compatibility/schema_method_compatibility_summary.csv",
                    "mapping/mapping_profile_used.json",
                    "mapping/mapping_candidate_report.json",
                    "mapping/mapping_resolution_report.json",
                    "method_outputs/specimen_results.csv",
                    "readiness/readiness_report.json",
                    "readiness/readiness_summary.csv",
                    "readiness/resolved_inputs.csv",
                    "readiness/missing_inputs.csv",
                    "method_outputs/dataset_summary.csv",
                    "method_outputs/dataset_summary_by_selection.csv",
                    "method_outputs/curves/stress_strain_family.csv",
                    "method_outputs/curves/stress_strain_family_bounded.csv",
                    "method_outputs/curves/stress_strain_family_full.csv",
                    "method_outputs/boundaries.csv",
                    "validation/validation_report.json",
                    "validation/validation_summary.csv",
                    "validation/reference_values_used.csv",
                    "validation/deviations.csv",
                    "acceptance/acceptance_report.json",
                    "acceptance/acceptance_summary.csv",
                    "acceptance/run_flags.csv",
                    "acceptance/selection_sets.json",
                    "acceptance/selection_membership.csv",
                    "acceptance/discharged_runs.csv",
                    "acceptance/discharge_report.json",
                    "acceptance/curve_family/curve_family_report.json",
                    "acceptance/curve_family/curve_family_scores.csv",
                    "acceptance/curve_family/curve_family_flags.csv",
                    "acceptance/curve_family/reference_curves.csv",
                    "acceptance/curve_family/aligned_curve_family.csv",
                    "acceptance/curve_family/residuals_long.csv",
                    "acceptance/curve_family/policy_resolved.json",
                    "acceptance/curve_family/curve_diagnostic_report.json",
                    "acceptance/curve_family/curve_diagnostic_scores.csv",
                    "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
                    "acceptance/curve_family/curve_diagnostic_residuals.csv",
                    "acceptance/curve_family/curve_diagnostic_policy.json",
                    "acceptance/curve_family/curve_diagnostic_flags.csv",
                    "acceptance/human_decisions.json",
                    "acceptance/human_decisions.csv",
                    "acceptance/override_ledger.json",
                    "acceptance/selection_sets_final.json",
                    "acceptance/selection_membership_final.csv",
                    "acceptance/final_report_runs.csv",
                    *(report_outputs or []),
                    "audit/evidence.json",
                    "audit/procedure_evidence_index.json",
                    "audit/audit_blocks.json",
                    "audit/audit_block_index.json",
                    "audit/boundary_resolution.json",
                    "audit/boundary_events.csv",
                    "audit/inspections.json",
                    "audit/audit_report.html",
                    "audit/audit_report.json",
                    "workbench/index.html",
                    "workbench/operation_trace.json",
                    "interactive_report/index.html",
                    "report/report_quality_gate.json",
                    "surface_manifest.json",
                ],
            }
        ]
        + (
            [
                {
                    "event": "report_overrides_applied",
                    "timestamp": utc_now_iso(),
                    "software": "compression_module_method_run_layer",
                    "method_id": result.method_package.method_id,
                    "field_count": len(result.report_overrides),
                    "source_type": "report_override",
                    "mtdp_mutated": False,
                    "artifacts": [
                        "report/report_field_overrides.json",
                        "report/report_override_ledger.json",
                        "report/report_values_used.csv",
                    ],
                }
            ]
            if result.report_overrides
            else []
        ),
        "boundary_resolution": {
            "enabled": bool(result.experiment_boundaries),
            "method_stage": "method_resolve",
            "start_policy": _first_boundary_value(result, "start_policy"),
            "end_policy": _first_boundary_value(result, "end_policy"),
            "bounded_reduction": bool(result.experiment_boundaries),
            "bounded_aggregation": _aggregation_is_boundary_aligned(result),
        },
        "source_reference": source_reference,
        "mapping_id": result.mapping.get("mapping_id"),
    }


def _per_run_curve_files(result: MethodRunResult) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    bounded_grouped = _group_curve_rows(result.bounded_curve_family or result.curve_family)
    full_grouped = _group_curve_rows(result.full_curve_family or [])
    for run_id, rows in bounded_grouped.items():
        safe_run = "".join(char if char.isalnum() or char in "-_" else "_" for char in run_id).strip("_")
        files[f"method_outputs/curves/{safe_run}_stress_strain.csv"] = write_dict_rows(rows).encode("utf-8")
        files[f"method_outputs/curves/{safe_run}_stress_strain_bounded.csv"] = write_dict_rows(rows).encode("utf-8")
        if run_id in full_grouped:
            files[f"method_outputs/curves/{safe_run}_stress_strain_full.csv"] = write_dict_rows(full_grouped[run_id]).encode("utf-8")
    return files


def _group_curve_rows(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        run_id = str(row.get("run_id"))
        grouped.setdefault(run_id, []).append(row)
    return grouped


def _boundary_resolution_payload(result: MethodRunResult) -> dict[str, object]:
    boundaries = result.experiment_boundaries or []
    return {
        "schema_id": "method.experiment_boundary_resolution.v0_1",
        "method_id": result.method_package.method_id,
        "record_count": len(boundaries),
        "bounded_reduction": bool(boundaries),
        "boundary_aligned_aggregation": _aggregation_is_boundary_aligned(result),
        "records": boundaries,
        "events": result.boundary_events or [],
        "warnings": [
            {"run_id": record.get("run_id"), "warnings": record.get("warnings", [])}
            for record in boundaries
            if isinstance(record, dict) and record.get("warnings")
        ],
    }


def _boundary_summary_rows(result: MethodRunResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    specimen_by_run = {str(row.get("run_id")): row for row in result.specimen_results}
    for record in result.experiment_boundaries or []:
        if not isinstance(record, dict):
            continue
        run_id = str(record.get("run_id") or "")
        specimen = specimen_by_run.get(run_id, {})
        interval = record.get("analysis_interval") if isinstance(record.get("analysis_interval"), dict) else {}
        policy = record.get("resolution_policy") if isinstance(record.get("resolution_policy"), dict) else {}
        start_policy = policy.get("start") if isinstance(policy.get("start"), dict) else {}
        slope_break = policy.get("slope_break") if isinstance(policy.get("slope_break"), dict) else {}
        rows.append(
            {
                "run_id": run_id,
                "start_index": interval.get("start_index", record.get("start_index")),
                "end_index": interval.get("end_index", record.get("end_index")),
                "include_endpoint": interval.get("include_endpoint", record.get("include_endpoint")),
                "accepted_failure_peak_index": record.get("accepted_failure_peak_index"),
                "max_within_interval_index": record.get("max_within_interval_index"),
                "reported_strength_index": record.get("reported_strength_index"),
                "start_policy": record.get("start_policy"),
                "start_min_load_fraction_of_max": start_policy.get("min_load_fraction_of_max"),
                "end_policy": record.get("end_policy"),
                "slope_domain": slope_break.get("slope_domain"),
                "policy_signature": policy.get("signature"),
                "confidence": record.get("confidence"),
                "reason": record.get("reason"),
                "domain": record.get("domain"),
                "domain_value": record.get("domain_value"),
                "max_load_N": specimen.get("max_load_N"),
                "max_load_index": specimen.get("max_load_index"),
                "warnings": "; ".join(str(warning) for warning in record.get("warnings", []) or []),
            }
        )
    return rows


def _first_boundary_value(result: MethodRunResult, key: str) -> object:
    for record in result.experiment_boundaries or []:
        if isinstance(record, dict) and record.get(key) not in (None, ""):
            return record.get(key)
    return ""


def _aggregation_is_boundary_aligned(result: MethodRunResult) -> bool:
    policy = result.method_package.curve_aggregation_policy
    if isinstance(policy, dict):
        curve_policy = policy.get("curve_aggregation") if isinstance(policy.get("curve_aggregation"), dict) else policy
        alignment = curve_policy.get("alignment") if isinstance(curve_policy, dict) else {}
        if isinstance(alignment, dict) and alignment.get("domain") == "experiment_progress":
            return True
    return any(
        isinstance(row, dict) and row.get("alignment_domain") == "experiment_progress"
        for row in result.curve_family_aligned_rows or []
    )


def _empty_human_decisions() -> dict[str, object]:
    return {
        "schema_id": "method.human_acceptance_decisions.v0_1",
        "selection_source": "machine_default_confirmed",
        "decisions": [],
    }


def _empty_override_ledger() -> dict[str, object]:
    return {
        "schema_id": "method.acceptance_override_ledger.v0_1",
        "selection_source": "machine_default_confirmed",
        "records": [],
    }


def _empty_curve_family_report() -> dict[str, object]:
    return {
        "schema_id": "method.curve_family_report.v0_1",
        "summary": {
            "curve_family_count": 0,
            "assessed_runs": 0,
            "accepted": 0,
            "review": 0,
            "propose_remove": 0,
        },
        "curve_families": [],
        "warnings": [],
        "acceptance_flag_ids": [],
    }


def _empty_curve_family_policy() -> dict[str, object]:
    return {
        "schema_id": "method.curve_family_policy_resolved.v0_1",
        "curve_families": [],
    }


def _empty_curve_diagnostic_report() -> dict[str, object]:
    return {
        "schema_id": "diagnostics.curve_family_diagnostic_report.v0_1",
        "operation_type": "curve_family_diagnostic",
        "summary": {
            "cohort_count": 0,
            "total_runs": 0,
            "evaluable_runs": 0,
            "curve_shape_outliers": 0,
            "insufficient_curve_data": 0,
        },
        "cohorts": [],
        "warnings": [{"warning": "curve-shape diagnostic evidence unavailable"}],
    }


def _empty_curve_diagnostic_policy() -> dict[str, object]:
    return {
        "schema_id": "diagnostics.curve_family_diagnostic_policy.v0_1",
        "operation_type": "curve_family_diagnostic",
        "artifact_paths": {
            "report": "acceptance/curve_family/curve_diagnostic_report.json",
            "scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
            "reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
            "residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
            "policy": "acceptance/curve_family/curve_diagnostic_policy.json",
            "flags": "acceptance/curve_family/curve_diagnostic_flags.csv",
        },
    }


def _empty_final_selection_sets(result: MethodRunResult) -> dict[str, object]:
    return {
        "schema_id": "method.selection_sets_final.v0_1",
        "default_selection_set": "final_report_runs",
        "machine_default_selection_set": result.selection_sets.get("default_selection_set") if isinstance(result.selection_sets, dict) else None,
        "selection_source": "machine_default_confirmed",
        "selection_sets": [],
    }
