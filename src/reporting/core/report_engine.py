from __future__ import annotations

from typing import Any

from archives.core.csv_io import write_dict_rows
from archives.core.json_io import json_bytes
from acceptance.selection_editor import FINAL_SELECTION_ID
from methods.core.method_result import MethodRunResult
from reporting.aggregate_statistics import build_aggregate_statistics
from reporting.core.block_registry import BlockRegistry
from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.renderer_registry import RendererRegistry
from reporting.core.report_context import ReportContext
from reporting.core.report_document import ReportDocument, ReportSectionDocument
from reporting.curve_aggregation import (
    build_aligned_curves,
    build_characteristic_points,
    build_feature_lines,
    coordinate_contract_from_rows,
)
from reporting.completion import ReportCompletionChecker
from reporting.report_models import ReportArtifactBundle
from reporting.report_recipe_loader import load_report_recipe
from reporting.run_labels import run_display_label


class GenericReportEngine:
    """Recipe-driven report generator shared by method packages."""

    def __init__(
        self,
        *,
        blocks: BlockRegistry | None = None,
        providers: DataProviderRegistry | None = None,
        renderers: RendererRegistry | None = None,
    ) -> None:
        self.blocks = blocks or BlockRegistry()
        self.providers = providers or DataProviderRegistry()
        self.renderers = renderers or RendererRegistry()

    def build(self, result: MethodRunResult) -> ReportArtifactBundle:
        recipe = _report_recipe(result)
        if not recipe:
            return ReportArtifactBundle(files={})
        recipe = _normalize_recipe(recipe)
        context = _build_context(result, recipe)
        document = self._document(context)
        document_payload = document.to_dict()
        payload = _report_payload(context, document_payload)
        html = self.renderers.get("html").render(document)
        files = _artifact_files(payload, html, document_payload, recipe, context)
        return ReportArtifactBundle(
            files=files,
            summary=payload["summary"],
            individual_results=list(context.table("individual_results")),
            aggregate_statistics=list(context.table("aggregate_statistics")),
            characteristic_points=list(context.table("characteristic_points")),
            feature_lines=list(context.table("feature_lines")),
            aligned_curves=list(context.table("aligned_curves")),
            missing_report_fields=list(context.table("missing_report_fields")),
        )

    def _document(self, context: ReportContext) -> ReportDocument:
        sections: list[ReportSectionDocument] = []
        for section in context.recipe.get("sections", []) or []:
            if not isinstance(section, dict):
                continue
            blocks = [
                self.blocks.resolve(block, context, self.providers)
                for block in section.get("blocks", []) or []
                if isinstance(block, dict)
            ]
            sections.append(
                ReportSectionDocument(
                    id=str(section.get("id") or ""),
                    title=str(section.get("title") or section.get("id") or ""),
                    blocks=blocks,
                )
            )
        completion_status = context.table("report_completion_status")
        iso_checks = context.table("iso14126_resolve_checks")
        return ReportDocument(
            report_id=str(context.recipe.get("recipe_id") or "method_report"),
            title=str(context.recipe.get("title") or context.result.method_package.name),
            metadata={
                "method_id": context.result.method_package.method_id,
                "method_version": context.result.method_package.version,
                "method_name": context.result.method_package.name,
                "standard_reference": context.result.method_package.manifest.get("standard_reference", "ISO 14126"),
                "selection_set": context.selection_set,
                "selection_source": context.selection_source,
                "selected_run_count": len(context.selection_run_ids),
                "missing_report_field_count": len(context.table("missing_report_fields")),
                "report_completion_status": completion_status.get("status"),
                "required_missing_count": completion_status.get("required_missing_count", 0),
                "recommended_missing_count": completion_status.get("recommended_missing_count", 0),
                "standard_required_missing_count": _iso_standard_required_missing_count(iso_checks),
                "standard_deviation_count": _iso_standard_deviation_count(iso_checks),
                "method_boundary_note": _iso_method_boundary_note(iso_checks),
                "report_quality_gate_status": _quality_status_from_completion(str(completion_status.get("status") or "")),
                "section_statuses": context.table("report_sections"),
            },
            sections=sections,
        )


def _report_recipe(result: MethodRunResult) -> dict[str, Any]:
    recipe = getattr(result.method_package, "report_recipe", {})
    if isinstance(recipe, dict) and recipe:
        return recipe
    path = result.method_package.root / "report_recipe.yaml"
    return load_report_recipe(path)


def _is_iso14126_result(result: MethodRunResult) -> bool:
    method_id = str(getattr(result.method_package, "method_id", "") or "").casefold()
    standard = str(getattr(result.method_package, "manifest", {}).get("standard_reference", "") or "").casefold()
    return "iso14126" in method_id or "14126" in standard


def _iso14126_resolve_checks(
    *,
    result: MethodRunResult,
    missing_report_fields: list[dict[str, Any]],
    report_values_used: list[dict[str, Any]],
    selection_run_ids: set[str],
) -> list[dict[str, Any]]:
    if not _is_iso14126_result(result):
        return []
    from methods.iso14126.report_compliance import build_iso14126_resolve_checks

    return build_iso14126_resolve_checks(
        result=result,
        missing_report_fields=missing_report_fields,
        report_values_used=report_values_used,
        selection_run_ids=selection_run_ids,
    )


def _iso_standard_required_missing_count(checks: list[dict[str, Any]]) -> int:
    if not checks:
        return 0
    from methods.iso14126.report_compliance import standard_required_missing_count

    return standard_required_missing_count(checks)


def _iso_standard_deviation_count(checks: list[dict[str, Any]]) -> int:
    if not checks:
        return 0
    from methods.iso14126.report_compliance import standard_deviation_count

    return standard_deviation_count(checks)


def _iso_method_boundary_note(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return ""
    from methods.iso14126.report_compliance import method_boundary_note

    return method_boundary_note(checks)


def _normalize_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    """Accept Stage 10 section-level recipes while preferring block recipes."""

    sections = recipe.get("sections") or recipe.get("report_sections") or []
    if not isinstance(sections, list):
        return dict(recipe)
    normalized = dict(recipe)
    normalized_sections: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("blocks"), list):
            normalized_sections.append(section)
            continue
        block: dict[str, Any]
        if section.get("table"):
            block = {
                "id": f"{section.get('id', 'section')}_table",
                "type": "table",
                "provider": str(section.get("table")),
            }
        else:
            fields = [
                {"label": str(field), "key": str(field)}
                for field in section.get("fields", []) or []
            ]
            block = {
                "id": f"{section.get('id', 'section')}_fields",
                "type": "field_table",
                "provider": "report_values",
                "fields": fields,
            }
        new_section = dict(section)
        new_section.pop("fields", None)
        new_section.pop("table", None)
        new_section["blocks"] = [block]
        normalized_sections.append(new_section)
    normalized["sections"] = normalized_sections
    return normalized


def _build_context(result: MethodRunResult, recipe: dict[str, Any]) -> ReportContext:
    selection_set = _default_selection_set(result, recipe)
    selection_source = _selection_source(result, selection_set)
    selection_run_ids = _selection_run_ids(result, selection_set)
    individual_results = _individual_results(result, selection_set, selection_run_ids)
    aggregate_statistics = build_aggregate_statistics(
        result.specimen_results,
        selection_run_ids=selection_run_ids,
        selection_set=selection_set,
    )
    curve_policy = _curve_policy(result, recipe)
    aligned_curves = build_aligned_curves(
        result.curve_family,
        result.specimen_results,
        selection_run_ids=selection_run_ids,
        selection_set=selection_set,
        x_grid_points=_curve_grid_points(curve_policy),
        x_axis=str(curve_policy.get("x_axis") or "mean_strain"),
        y_axis=str(curve_policy.get("y_axis") or "stress_MPa"),
        alignment_policy=str(curve_policy.get("alignment_policy") or "normalize_by_failure_strain"),
        alignment=curve_policy.get("alignment") if isinstance(curve_policy.get("alignment"), dict) else None,
        boundary_records=result.experiment_boundaries or [],
    )
    characteristic_points = build_characteristic_points(
        result.specimen_results,
        aggregate_statistics,
        selection_run_ids=selection_run_ids,
        selection_set=selection_set,
    )
    feature_lines = build_feature_lines(aggregate_statistics, selection_set=selection_set)
    completion = ReportCompletionChecker().check(
        result=result,
        recipe=recipe,
        selection_set=selection_set,
        selection_source=selection_source,
        overrides=getattr(result, "report_overrides", ()),
    )
    report_values_used = completion.values_used
    missing_report_fields = _missing_report_fields_with_iso_run_gaps(
        result,
        completion.missing_fields,
        selection_run_ids,
        report_values_used,
    )
    report_completion_status = (
        _report_completion_status(missing_report_fields)
        if len(missing_report_fields) != len(completion.missing_fields)
        else completion.completion_status
    )
    values_by_key = _values_by_key(report_values_used, result.specimen_results)
    values_by_key = _values_with_iso_analysis_remarks(values_by_key, result)
    values_by_key = _values_with_controlled_choice_display(values_by_key, result)
    report_sections = _report_sections(recipe, missing_report_fields)
    report_completeness_summary = _report_completeness_summary(report_sections)
    failure_analysis_run_evidence = _failure_analysis_run_rows(result, selection_set, selection_run_ids)
    failure_analysis = _failure_analysis_rows(result, selection_set, selection_run_ids, failure_analysis_run_evidence)
    failure_analysis_observations = _failure_analysis_observation_rows(failure_analysis_run_evidence)
    failure_analysis_invalid_specimens = _failure_analysis_invalid_specimen_rows(failure_analysis_run_evidence)
    failure_analysis_bending_distribution = _failure_analysis_bending_distribution(result, failure_analysis_run_evidence)
    iso14126_resolve_checks = _iso14126_resolve_checks(
        result=result,
        missing_report_fields=missing_report_fields,
        report_values_used=report_values_used,
        selection_run_ids=selection_run_ids,
    )
    deviations_from_standard = _deviations_from_standard_rows(result, missing_report_fields, iso14126_resolve_checks)
    aggregate_curve_summary = _aggregate_curve_summary(aligned_curves, curve_policy, selection_set)
    aggregate_plot_spec = _aggregate_plot_spec(
        aligned_curves=aligned_curves,
        characteristic_points=characteristic_points,
        curve_policy=curve_policy,
        selection_set=selection_set,
        selected_run_ids=selection_run_ids,
    )
    artifacts = _artifact_paths()
    return ReportContext(
        result=result,
        recipe=recipe,
        selection_set=selection_set,
        selection_source=selection_source,
        selection_run_ids=selection_run_ids,
        curve_policy=curve_policy,
        values_by_key=values_by_key,
        tables={
            "report_values_used": report_values_used,
            "missing_report_fields": missing_report_fields,
            "report_field_catalog_resolved": completion.field_catalog,
            "report_completion_status": report_completion_status,
            "report_field_overrides": [override.to_dict() for override in completion.overrides],
            "report_override_ledger": completion.override_ledger or {"schema_id": "report.override_ledger.v0_1", "records": []},
            "report_sections": report_sections,
            "report_completeness_summary": report_completeness_summary,
            "individual_results": individual_results,
            "aggregate_statistics": aggregate_statistics,
            "characteristic_points": characteristic_points,
            "feature_lines": feature_lines,
            "aligned_curves": aligned_curves,
            "failure_analysis": failure_analysis,
            "failure_analysis_run_evidence": failure_analysis_run_evidence,
            "failure_analysis_observations": failure_analysis_observations,
            "failure_analysis_invalid_specimens": failure_analysis_invalid_specimens,
            "failure_analysis_bending_distribution": failure_analysis_bending_distribution,
            "bending_distribution_summary": failure_analysis_bending_distribution.get("summary", []),
            "iso14126_resolve_checks": iso14126_resolve_checks,
            "deviations_from_standard": deviations_from_standard,
            "aggregate_curve_summary": aggregate_curve_summary,
            "aggregate_plot_spec": aggregate_plot_spec,
            "artifacts": artifacts,
        },
    )


def _curve_policy(result: MethodRunResult, recipe: dict[str, Any]) -> dict[str, Any]:
    policy = recipe.get("curve_aggregation")
    if isinstance(policy, dict):
        return policy
    method_policy = getattr(result.method_package, "curve_aggregation_policy", {})
    if isinstance(method_policy, dict) and method_policy:
        if isinstance(method_policy.get("curve_aggregation"), dict):
            return method_policy["curve_aggregation"]
        return method_policy
    return {
        "selection_set": "selected",
        "x_axis": "mean_strain",
        "y_axis": "stress_MPa",
        "alignment_policy": "normalize_by_failure_strain",
        "x_grid_points": 500,
    }


def _curve_grid_points(curve_policy: dict[str, Any]) -> int:
    alignment = curve_policy.get("alignment") if isinstance(curve_policy.get("alignment"), dict) else {}
    return int(alignment.get("resample_points") or curve_policy.get("x_grid_points") or 500)


def _default_selection_set(result: MethodRunResult, recipe: dict[str, Any]) -> str:
    if _has_final_selection(result):
        return FINAL_SELECTION_ID
    recipe_selection = recipe.get("selection_set") if isinstance(recipe, dict) else None
    if recipe_selection and recipe_selection != "selected":
        return str(recipe_selection)
    if recipe_selection == "selected":
        return _first_nonempty_selection(result, ("auto_recommended_runs", "user_valid_runs", "all_runs"))
    default = result.acceptance_report.get("default_selection_set")
    if default:
        return str(default)
    if isinstance(result.selection_sets, dict) and result.selection_sets.get("default_selection_set"):
        return str(result.selection_sets.get("default_selection_set"))
    return "auto_recommended_runs"


def _selection_source(result: MethodRunResult, selection_set: str) -> str:
    if selection_set == FINAL_SELECTION_ID:
        final_payload = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
        source = final_payload.get("selection_source")
        if source:
            return str(source)
        decisions = result.human_decisions if isinstance(result.human_decisions, dict) else {}
        return "human_final" if decisions.get("decisions") else "machine_default_confirmed"
    return "machine_acceptance"


def _first_nonempty_selection(result: MethodRunResult, candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if _selection_run_ids(result, candidate):
            return candidate
    return candidates[-1]


def _selection_run_ids(result: MethodRunResult, selection_set: str) -> set[str]:
    if selection_set == FINAL_SELECTION_ID:
        selected = {
            str(row.get("run_id"))
            for row in (result.selection_membership_final or [])
            if str(row.get("selection_set")) == FINAL_SELECTION_ID and _truthy(row.get("included"))
        }
        if selected:
            return selected
        final_rows = result.final_report_runs or []
        selected = {
            str(row.get("run_id"))
            for row in final_rows
            if row.get("run_id") and _truthy(row.get("included", True))
        }
        if selected:
            return selected
        payload = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
        for selection in payload.get("selection_sets", []) or []:
            if isinstance(selection, dict) and selection.get("selection_id") == FINAL_SELECTION_ID:
                return {str(run_id) for run_id in selection.get("run_ids", [])}
    selected = {
        str(row.get("run_id"))
        for row in result.selection_membership
        if str(row.get("selection_set")) == selection_set and _truthy(row.get("included"))
    }
    if selected:
        return selected
    payload = result.selection_sets.get("selection_sets", []) if isinstance(result.selection_sets, dict) else []
    for selection in payload:
        if isinstance(selection, dict) and selection.get("selection_id") == selection_set:
            return {str(run_id) for run_id in selection.get("run_ids", [])}
    return {str(row.get("run_id")) for row in result.specimen_results if row.get("run_id")}


def _individual_results(
    result: MethodRunResult,
    selection_set: str,
    selection_run_ids: set[str],
) -> list[dict[str, Any]]:
    states = result.acceptance_report.get("run_states", {})
    final_by_run = _final_rows_by_run(result)
    rows: list[dict[str, Any]] = []
    for row in result.specimen_results:
        run_id = str(row.get("run_id"))
        output = dict(row)
        output["selection_set"] = selection_set
        output["included_in_selection"] = run_id in selection_run_ids
        output["acceptance_state"] = states.get(run_id, "")
        final_row = final_by_run.get(run_id, {})
        output["machine_acceptance_state"] = final_row.get("machine_state", states.get(run_id, ""))
        output["human_decision_type"] = final_row.get("human_decision_type", "")
        output["human_decision_reason"] = final_row.get("human_decision_reason", "")
        output["final_included"] = final_row.get("included", run_id in selection_run_ids)
        if "compressive_failure_strain" in output:
            try:
                output["failure_strain_percent"] = float(output["compressive_failure_strain"]) * 100.0
            except (TypeError, ValueError):
                output["failure_strain_percent"] = ""
        rows.append(output)
    return rows


def _report_values_and_missing(
    result: MethodRunResult,
    recipe: dict[str, Any],
    selection_set: str,
    selection_source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    values: list[dict[str, Any]] = [
        _value_row("method_id", result.method_package.method_id, "method_manifest", "execution_critical"),
        _value_row("method_version", result.method_package.version, "method_manifest", "execution_critical"),
        _value_row("method_name", result.method_package.name, "method_manifest", "execution_critical"),
        _value_row("source_package", str(result.source.path), "source_reference", "execution_critical"),
        _value_row("selection_set", selection_set, "acceptance", "execution_critical"),
        _value_row("selection_source", selection_source, "acceptance", "execution_critical"),
        _value_row("run_count", len(result.specimen_results), "method_outputs", "execution_critical"),
        _value_row("selected_run_count", len(_selection_run_ids(result, selection_set)), "acceptance", "execution_critical"),
    ]
    manifest = result.method_package.manifest
    standard = manifest.get("standard_reference") or "ISO 14126"
    values.append(_value_row("standard_reference", standard, "method_manifest", "report_completeness"))
    values = _merge_value_rows(values, _source_metadata_value_rows(result))
    expected = _expected_report_fields(recipe)
    available = {str(row["field"]) for row in values}
    for row in values:
        available.update(str(alias) for alias in row.get("aliases", []) or [])
    available.update(_specimen_available_fields(result.specimen_results))
    missing: list[dict[str, Any]] = []
    for section_id, section_title, field, requirement_level in expected:
        if field in available:
            continue
        missing.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "field": field,
                "severity": "required" if requirement_level == "required" else "report_completeness",
                "requirement_level": requirement_level,
                "message": f"Report field '{field}' was not found in method outputs or package metadata.",
            }
        )
    return values, missing


def _missing_report_fields_with_iso_run_gaps(
    result: MethodRunResult,
    missing_fields: list[dict[str, Any]],
    selection_run_ids: set[str],
    report_values_used: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Add report-facing per-run ISO gaps that recipe catalog checks cannot see."""

    if not _is_iso14126_result(result):
        return missing_fields
    selected = set(selection_run_ids)
    missing_failure_runs = []
    missing_location_runs = []
    for row in result.specimen_results:
        if not isinstance(row, dict) or not row.get("run_id"):
            continue
        run_id = str(row.get("run_id") or "")
        if selected and run_id not in selected:
            continue
        if _iso_failure_mode(row) == "not recorded":
            missing_failure_runs.append(run_id)
        if _failure_location(row) == "not recorded":
            missing_location_runs.append(run_id)
    enriched = list(missing_fields)
    if missing_failure_runs and not _missing_field_recorded(missing_fields, "primary_failure_mode"):
        enriched.append(
            {
                "section_id": "failure_analysis",
                "section_title": "Failure Analysis",
                "field": "primary_failure_mode",
                "label": "Primary failure mode",
                "severity": "required",
                "requirement_level": "required",
                "report_importance": "required",
                "affected_run_ids": missing_failure_runs,
                "missing_count": len(missing_failure_runs),
                "message": "Primary failure mode is required for accepted/final-report runs.",
            }
        )
    if missing_location_runs and not _missing_field_recorded(missing_fields, "failure_location"):
        enriched.append(
            {
                "section_id": "failure_analysis",
                "section_title": "Failure Analysis",
                "field": "failure_location",
                "label": "Failure location",
                "severity": "required",
                "requirement_level": "required",
                "report_importance": "required",
                "affected_run_ids": missing_location_runs,
                "missing_count": len(missing_location_runs),
                "message": "Failure location is required for accepted/final-report runs.",
            }
        )
    if report_values_used is not None:
        enriched.extend(_missing_iso_controlled_choice_rows(result, report_values_used, enriched))
    return enriched


def _missing_field_recorded(missing_fields: list[dict[str, Any]], field_name: str) -> bool:
    return any(
        str(row.get("field") or row.get("field_key") or "") == field_name
        for row in missing_fields
    )


def _missing_iso_controlled_choice_rows(
    result: MethodRunResult,
    report_values_used: list[dict[str, Any]],
    existing_missing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    values = _values_by_key(report_values_used, result.specimen_results)
    rows: list[dict[str, Any]] = []
    for field, detail_field, label, detail_label in (
        ("loading_method", "loading_method_other", "Loading method", "Other loading method"),
        ("specimen_type", "specimen_type_other", "Specimen type", "Other specimen type"),
    ):
        if _missing_field_recorded(existing_missing, field) or _missing_field_recorded(existing_missing, detail_field):
            continue
        status = _iso_controlled_choice_status(field, values.get(field), values.get(detail_field))
        if status == "iso":
            continue
        if status == "other_with_detail":
            continue
        missing_field = detail_field if status == "other_missing_detail" else field
        missing_label = detail_label if status == "other_missing_detail" else label
        message = (
            f"{detail_label} is required when {label.lower()} is Other specified."
            if status == "other_missing_detail"
            else f"{label} must use an ISO-controlled choice or Other specified with details."
        )
        rows.append(
            {
                "section_id": "test_identification",
                "section_title": "Test Identification",
                "field": missing_field,
                "field_key": missing_field,
                "label": missing_label,
                "severity": "required",
                "requirement_level": "required",
                "report_importance": "required",
                "status": "missing",
                "source_type": "missing",
                "source_path": "",
                "message": message,
            }
        )
    return rows


def _source_metadata_value_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    source = result.source
    fields = list(source.schema.get("dataset_fields", []) or []) + list(source.schema.get("run_fields", []) or [])
    rows: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_id = str(field.get("field_id") or field.get("key") or "").strip()
        if not field_id:
            continue
        report_role = str(field.get("report_role") or "").strip()
        value, unit, source_label = _metadata_value_for_field(source, field)
        if value in (None, ""):
            continue
        row = _value_row(
            report_role or field_id,
            value,
            source_label,
            "report_completeness",
        )
        aliases = [field_id]
        if report_role and report_role != field_id:
            aliases.append(report_role)
        row["aliases"] = aliases
        row["unit"] = unit or str(field.get("standard_unit") or "")
        row["scope"] = _metadata_field_scope(field)
        row["source_field_id"] = field_id
        row["report_importance"] = field.get("report_importance") or ""
        rows.append(row)
    return rows


def _metadata_value_for_field(source: Any, field: dict[str, Any]) -> tuple[Any, str, str]:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    if location == "dataset_json":
        return (*_payload_value(_get_dotted_value(source.dataset, str(storage.get("path") or ""))), "source_mtdp_dataset")
    if location == "token_preamble":
        token = str(storage.get("token") or "")
        for run in source.runs:
            run_token = run.token(token)
            if run_token is not None and run_token.value not in (None, ""):
                return run_token.value, run_token.unit or "", "source_mtdp_run_token"
    if location == "provenance":
        path = str(storage.get("path") or "")
        for run in source.runs:
            run_path = path.format(run_id=run.run_id)
            prefix = f"runs.{run.run_id}."
            if run_path.startswith(prefix):
                run_path = run_path[len(prefix):]
            value, unit = _payload_value(_get_dotted_value(run.provenance, run_path))
            if value not in (None, ""):
                return value, unit, "source_mtdp_run_provenance"
    return None, "", "source_mtdp_metadata"


def _payload_value(value: Any) -> tuple[Any, str]:
    if isinstance(value, dict) and "value" in value:
        return value.get("value"), "" if value.get("unit") in (None, "") else str(value.get("unit"))
    return value, ""


def _get_dotted_value(payload: Any, path: str) -> Any:
    cursor = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _metadata_field_scope(field: dict[str, Any]) -> str:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    return "dataset" if location == "dataset_json" else "run"


def _merge_value_rows(existing: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing)
    existing_fields = {str(row.get("field")) for row in merged if row.get("value") not in (None, "")}
    for row in extra:
        field = str(row.get("field") or "")
        aliases = {str(alias) for alias in row.get("aliases", []) or []}
        if field in existing_fields or existing_fields & aliases:
            continue
        merged.append(row)
        existing_fields.add(field)
    return merged


def _values_by_key(report_values_used: list[dict[str, Any]], specimen_results: list[dict[str, Any]]) -> dict[str, Any]:
    values = {str(row.get("field")): row.get("value") for row in report_values_used}
    for row in report_values_used:
        for alias in row.get("aliases", []) or []:
            values.setdefault(str(alias), row.get("value"))
    values.update(_first_specimen_values(specimen_results))
    return values


def _values_with_iso_analysis_remarks(values: dict[str, Any], result: MethodRunResult) -> dict[str, Any]:
    if not _is_iso14126_result(result):
        return values
    try:
        from methods.iso14126.report_compliance import analysis_interval_remark
    except Exception:
        return values
    remark = analysis_interval_remark(getattr(result, "experiment_boundaries", []) or [])
    if not remark:
        return values
    merged = dict(values)
    existing = str(merged.get("remarks") or "").strip()
    merged["remarks"] = f"{existing}\n\n{remark}" if existing else remark
    return merged


def _values_with_controlled_choice_display(values: dict[str, Any], result: MethodRunResult) -> dict[str, Any]:
    if not _is_iso14126_result(result):
        return values
    merged = dict(values)
    for field, detail_field in (
        ("loading_method", "loading_method_other"),
        ("specimen_type", "specimen_type_other"),
    ):
        raw = merged.get(field)
        detail = merged.get(detail_field)
        status = _iso_controlled_choice_status(field, raw, detail)
        canonical = _canonical_iso_controlled_choice(field, raw)
        if status == "iso" and canonical:
            merged[field] = _ISO_CONTROLLED_CHOICE_LABELS[field][canonical]
        elif status == "other_with_detail":
            merged[field] = f"Other specified: {str(detail).strip()}"
        elif status == "other_missing_detail":
            merged[field] = "Other specified"
        elif raw not in (None, ""):
            merged[field] = ""
    return merged


_ISO_CONTROLLED_CHOICE_LABELS = {
    "loading_method": {
        "method_1_shear_loading": "Shear loading (Method 1)",
        "method_2_combined_loading": "Combined loading (Method 2)",
        "other_specified": "Other specified",
    },
    "specimen_type": {
        "type_a": "Type A",
        "type_b1": "Type B1",
        "type_b2": "Type B2",
        "other_specified": "Other specified",
    },
}

_ISO_CONTROLLED_CHOICE_SYNONYMS = {
    "loading_method": {
        "method_1_shear_loading": "method_1_shear_loading",
        "method 1": "method_1_shear_loading",
        "shear loading": "method_1_shear_loading",
        "shear loading method 1": "method_1_shear_loading",
        "shear loading (method 1)": "method_1_shear_loading",
        "method_2_combined_loading": "method_2_combined_loading",
        "method 2": "method_2_combined_loading",
        "combined loading": "method_2_combined_loading",
        "combined loading method 2": "method_2_combined_loading",
        "combined loading (method 2)": "method_2_combined_loading",
        "other_specified": "other_specified",
        "other specified": "other_specified",
    },
    "specimen_type": {
        "type_a": "type_a",
        "type a": "type_a",
        "a": "type_a",
        "type_b1": "type_b1",
        "type b1": "type_b1",
        "b1": "type_b1",
        "type_b2": "type_b2",
        "type b2": "type_b2",
        "b2": "type_b2",
        "other_specified": "other_specified",
        "other specified": "other_specified",
    },
}

_ISO_COMPLIANT_CONTROLLED_CHOICES = {
    "loading_method": {"method_1_shear_loading", "method_2_combined_loading"},
    "specimen_type": {"type_a", "type_b1", "type_b2"},
}


def _iso_controlled_choice_status(field: str, value: Any, detail: Any = None) -> str:
    canonical = _canonical_iso_controlled_choice(field, value)
    if canonical in _ISO_COMPLIANT_CONTROLLED_CHOICES.get(field, set()):
        return "iso"
    if canonical == "other_specified":
        return "other_with_detail" if str(detail or "").strip() else "other_missing_detail"
    if value in (None, ""):
        return "missing"
    return "unresolved"


def _canonical_iso_controlled_choice(field: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = " ".join(text.replace("-", " ").replace("_", " ").casefold().split())
    direct = str(value).strip()
    synonyms = _ISO_CONTROLLED_CHOICE_SYNONYMS.get(field, {})
    return synonyms.get(direct, synonyms.get(normalized, ""))


def _expected_report_fields(recipe: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    fields: list[tuple[str, str, str, str]] = []
    sections = recipe.get("sections") or recipe.get("report_sections") or []
    if not isinstance(sections, list):
        return fields
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or "")
        section_title = str(section.get("title") or section_id)
        for block in section.get("blocks", []) or []:
            if not isinstance(block, dict) or block.get("type") != "field_table":
                continue
            for field in block.get("fields", []) or []:
                if isinstance(field, dict) and field.get("key"):
                    fields.append((section_id, section_title, str(field["key"]), _field_requirement_level(field)))
                elif isinstance(field, str):
                    fields.append((section_id, section_title, field, "recommended"))
    return fields


def _field_requirement_level(field: dict[str, Any]) -> str:
    if field.get("required") is True:
        return "required"
    severity = str(field.get("severity") or field.get("requirement_level") or "").casefold()
    if severity in {"required", "execution_critical", "critical"}:
        return "required"
    required_for = field.get("required_for")
    if isinstance(required_for, list) and any(str(item).casefold() in {"formal_report", "test_report"} for item in required_for):
        return "required"
    return "recommended"


def _report_completion_status(missing_fields: list[dict[str, Any]]) -> dict[str, Any]:
    required_missing = [
        row for row in missing_fields
        if str(row.get("severity")).casefold() in {"required", "execution_critical", "critical"}
        or str(row.get("requirement_level")).casefold() == "required"
    ]
    if required_missing:
        status = "INCOMPLETE"
    elif missing_fields:
        status = "COMPLETE_WITH_WARNINGS"
    else:
        status = "COMPLETE"
    return {
        "schema_id": "report.completion_status.v0_1",
        "status": status,
        "required_missing_count": len(required_missing),
        "recommended_missing_count": max(0, len(missing_fields) - len(required_missing)),
        "missing_field_count": len(missing_fields),
        "required_missing_fields": [str(row.get("field")) for row in required_missing],
        "recommended_missing_fields": [
            str(row.get("field"))
            for row in missing_fields
            if row not in required_missing
        ],
    }


def _report_sections(recipe: dict[str, Any], missing_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_by_section: dict[str, list[dict[str, Any]]] = {}
    for field in missing_fields:
        missing_by_section.setdefault(str(field.get("section_id") or ""), []).append(field)
    rows: list[dict[str, Any]] = []
    sections = recipe.get("sections") or recipe.get("report_sections") or []
    if not isinstance(sections, list):
        return rows
    for order, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or f"section_{order}")
        field_count = 0
        blocks = section.get("blocks", []) if isinstance(section.get("blocks"), list) else []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "field_table":
                field_count += len(block.get("fields", []) or [])
        missing = missing_by_section.get(section_id, [])
        missing_by_importance = _missing_by_importance(missing)
        missing_required_count = len(missing_by_importance["required"])
        missing_recommended_count = len(missing_by_importance["recommended"])
        missing_optional_count = len(missing_by_importance["optional"])
        rows.append(
            {
                "order": order,
                "section_id": section_id,
                "title": section.get("title") or section_id,
                "source": section.get("source") or "",
                "block_count": len(blocks),
                "field_count": field_count,
                "missing_field_count": len(missing),
                "missing_required_count": missing_required_count,
                "missing_recommended_count": missing_recommended_count,
                "missing_optional_count": missing_optional_count,
                "missing_fields_by_importance": missing_by_importance,
                "status": _section_status(
                    block_count=len(blocks),
                    field_count=field_count,
                    missing_required_count=missing_required_count,
                    missing_recommended_count=missing_recommended_count,
                    missing_optional_count=missing_optional_count,
                ),
                "missing_fields": [field.get("field") for field in missing],
            }
        )
    return rows


def _missing_by_importance(missing: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped = {"required": [], "recommended": [], "optional": [], "none": []}
    for field in missing:
        importance = str(field.get("report_importance") or field.get("requirement_level") or "recommended").casefold()
        if importance not in grouped:
            importance = "recommended"
        grouped[importance].append(str(field.get("field_key") or field.get("field") or ""))
    return grouped


def _section_status(
    *,
    block_count: int,
    field_count: int,
    missing_required_count: int,
    missing_recommended_count: int,
    missing_optional_count: int,
) -> str:
    if block_count == 0:
        return "not_applicable"
    if missing_required_count:
        return "incomplete"
    if missing_recommended_count or missing_optional_count:
        return "complete_with_warnings"
    return "complete"


def _report_completeness_summary(report_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section_id": section.get("section_id"),
            "title": section.get("title"),
            "field_count": section.get("field_count"),
            "missing_field_count": section.get("missing_field_count"),
            "missing_required_count": section.get("missing_required_count"),
            "missing_recommended_count": section.get("missing_recommended_count"),
            "missing_optional_count": section.get("missing_optional_count"),
            "status": section.get("status"),
        }
        for section in report_sections
    ]


def _failure_analysis_run_rows(
    result: MethodRunResult,
    selection_set: str,
    selection_run_ids: set[str],
) -> list[dict[str, Any]]:
    states = result.acceptance_report.get("run_states", {})
    final_by_run = _final_rows_by_run(result)
    flags_by_run = _acceptance_flags_by_run(result)
    curve_family_by_run = {
        str(row.get("run_id")): row
        for row in (result.curve_family_scores or [])
        if isinstance(row, dict) and row.get("run_id")
    }
    rows: list[dict[str, Any]] = []
    for specimen in result.specimen_results:
        run_id = str(specimen.get("run_id") or "")
        curve_score = curve_family_by_run.get(run_id, {})
        rows.append(
            {
                "selection_set": selection_set,
                "run_id": run_id,
                "run_label": run_display_label(run_id),
                "specimen_name": specimen.get("specimen_name", ""),
                "included_in_selection": run_id in selection_run_ids,
                "acceptance_state": states.get(run_id, ""),
                "machine_acceptance_state": final_by_run.get(run_id, {}).get("machine_state", states.get(run_id, "")),
                "human_decision_type": final_by_run.get(run_id, {}).get("human_decision_type", ""),
                "human_decision_reason": final_by_run.get(run_id, {}).get("human_decision_reason", ""),
                "final_included": final_by_run.get(run_id, {}).get("included", run_id in selection_run_ids),
                "primary_failure_mode": specimen.get("primary_failure_mode", ""),
                "failure_mode": specimen.get("failure_mode", ""),
                "failure_mode_report_value": _iso_failure_mode(specimen),
                "failure_location": specimen.get("failure_location", ""),
                "failure_location_report_value": _failure_location(specimen),
                "failure_observed": specimen.get("failure_observed", ""),
                "invalid_specimen_reason": specimen.get("invalid_specimen_reason", ""),
                "invalid_specimen_reason_other": specimen.get("invalid_specimen_reason_other", ""),
                "failure_analysis_notes": specimen.get("failure_analysis_notes", ""),
                "visible_buckling_or_bending_observation": specimen.get("visible_buckling_or_bending_observation", ""),
                "visible_buckling_or_bending_observation_other": specimen.get("visible_buckling_or_bending_observation_other", ""),
                "visible_buckling_or_bending_observation_report_value": _enum_label_with_detail(
                    specimen.get("visible_buckling_or_bending_observation", ""),
                    specimen.get("visible_buckling_or_bending_observation_other", ""),
                ),
                "failure_image_reference": specimen.get("failure_image_reference", ""),
                "rejection_reason": specimen.get("rejection_reason", ""),
                "run_notes": specimen.get("run_notes", ""),
                "validity": specimen.get("validity", ""),
                "bending_pattern": specimen.get("bending_pattern", ""),
                "bending_pattern_confidence": specimen.get("bending_pattern_confidence", ""),
                "bending_pattern_reason": specimen.get("bending_pattern_reason", ""),
                "bending_threshold_percent": specimen.get("bending_threshold_percent", ""),
                "bending_points_above_threshold": specimen.get("bending_points_above_threshold", ""),
                "bending_fraction_above_threshold": specimen.get("bending_fraction_above_threshold", ""),
                "bending_longest_segment_points": specimen.get("bending_longest_segment_points", ""),
                "bending_mean_percent": specimen.get("bending_mean_percent", ""),
                "bending_median_percent": specimen.get("bending_median_percent", ""),
                "bending_p95_percent": specimen.get("bending_p95_percent", ""),
                "bending_max_percent": specimen.get("bending_max_percent", ""),
                "bending_point_count": specimen.get("bending_point_count", ""),
                "curve_family_classification": curve_score.get("classification", ""),
                "curve_family_reason": curve_score.get("primary_reason", ""),
                "curve_family_normalized_rmse": curve_score.get("normalized_rmse", ""),
                "requires_review": specimen.get("requires_review", ""),
                "acceptance_flags": "; ".join(flag.get("flag_id", "") for flag in flags_by_run.get(run_id, [])),
                "acceptance_flag_messages": "; ".join(flag.get("message", "") for flag in flags_by_run.get(run_id, [])),
            }
        )
    return rows


def _failure_analysis_rows(
    result: MethodRunResult,
    selection_set: str,
    selection_run_ids: set[str],
    run_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    final_rows = [row for row in run_rows if _truthy(row.get("final_included", row.get("included_in_selection")))]
    invalid_rows = _failure_analysis_invalid_specimen_rows(run_rows)
    return [
        {
            "Field": "Failure Observation Completeness",
            "Value": _failure_observation_completeness(final_rows),
        },
        {
            "Field": "Invalid Specimens",
            "Value": _invalid_specimen_overview(invalid_rows),
        },
        {
            "Field": "Bending Compliance",
            "Value": _bending_compliance_summary(run_rows, final_rows),
        },
        {
            "Field": "Notes",
            "Value": _failure_analysis_notes(run_rows, invalid_rows),
        },
    ]


def _failure_analysis_observation_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in run_rows:
        if not _truthy(row.get("final_included", row.get("included_in_selection"))):
            continue
        rows.append(
            {
                "Run #": row.get("run_label") or run_display_label(row.get("run_id", "")),
                "Specimen": row.get("specimen_name", ""),
                "Failure mode": _failure_observation_cell(row.get("failure_mode_report_value")),
                "Failure location": _failure_observation_cell(row.get("failure_location_report_value")),
                "Notes": _failure_observation_note(row),
            }
        )
    return rows


def _failure_analysis_invalid_specimen_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in run_rows:
        reasons = _invalid_specimen_reasons(row)
        if not reasons:
            continue
        rows.append(
            {
                "Run #": row.get("run_label") or run_display_label(row.get("run_id", "")),
                "Specimen": row.get("specimen_name", ""),
                "Reason": "; ".join(reasons),
                "Bending evidence": _bending_evidence_label(row),
                "Operator note": _first_present(
                    row,
                    ("failure_analysis_notes", "rejection_reason", "human_decision_reason", "run_notes"),
                ),
            }
        )
    return rows


def _invalid_specimen_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    validity = str(row.get("validity") or "").casefold()
    invalid_reason = str(row.get("invalid_specimen_reason") or "").strip()
    bending = str(row.get("bending_pattern") or "")
    state = str(row.get("acceptance_state") or "")
    final_included = _truthy(row.get("final_included", row.get("included_in_selection")))
    flag_text = " ".join(str(row.get(key) or "") for key in ("acceptance_flags", "acceptance_flag_messages")).casefold()
    location = str(row.get("failure_location") or "").casefold()
    if validity in {"invalid", "rejected", "false", "0"} or "user_validity_invalid" in flag_text:
        reasons.append("operator marked invalid")
    if invalid_reason and invalid_reason not in {"none", "not_recorded", "not recorded"}:
        reasons.append(_enum_label_with_detail(invalid_reason, row.get("invalid_specimen_reason_other")))
    if bending == "FAIL_SUSTAINED_BENDING":
        reasons.append("bending non-compliance")
    elif bending in {"PASS_WITH_SPIKES", "WARN_TRANSIENT_BENDING"}:
        reasons.append("bending review")
    if any(token in location for token in ("grip", "end_block")):
        reasons.append("grip/end block failure")
    if "tab" in location:
        reasons.append("end tab failure")
    if not final_included and not reasons:
        reasons.append(state.replace("_", " ") or "excluded from reported statistics")
    return _dedupe_text(reasons)


def _failure_analysis_bending_distribution(result: MethodRunResult, run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    point_values, exact_values_by_run = _bending_distribution_points(result, run_rows)
    summary = _bending_distribution_summary(run_rows, point_values, exact_values_by_run)
    unavailable = "" if point_values else "Bending distribution plot unavailable: pointwise bending values are not present in the report payload."
    return {
        "schema_id": "method.failure_analysis_bending_distribution.v0_1",
        "spec_id": "failure_analysis_bending_distribution",
        "plot_title": "Bending distribution over assessed domain",
        "threshold_percent": 10.0,
        "assessed_domain": "10-90 % Fmax",
        "run_count": len(summary),
        "summary": summary,
        "points": point_values,
        "unavailable_message": unavailable,
    }


def _bending_distribution_summary(
    run_rows: list[dict[str, Any]],
    point_values: list[dict[str, Any]],
    exact_values_by_run: dict[str, list[float]] | None = None,
) -> list[dict[str, Any]]:
    points_by_run: dict[str, list[float]] = {}
    for point in point_values:
        run_id = str(point.get("run_id") or "")
        value = _as_float(point.get("bending_percent"))
        if run_id and value is not None:
            points_by_run.setdefault(run_id, []).append(value)
    exact_values_by_run = exact_values_by_run or {}
    rows = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "")
        values = exact_values_by_run.get(run_id) or points_by_run.get(run_id, [])
        assessed_point_count = row.get("bending_point_count", "") or len(values)
        threshold_percent = row.get("bending_threshold_percent") or 10.0
        threshold_value = _as_float(threshold_percent) or 10.0
        computed_points_above = sum(1 for value in values if value > threshold_value)
        points_above_threshold = row.get("bending_points_above_threshold", "")
        if points_above_threshold in (None, ""):
            points_above_threshold = computed_points_above if values else ""
        fraction_above_threshold = row.get("bending_fraction_above_threshold", "")
        if fraction_above_threshold in (None, ""):
            fraction_above_threshold = (computed_points_above / len(values)) if values else ""
        rows.append(
            {
                "run_id": run_id,
                "run_label": row.get("run_label") or run_display_label(run_id),
                "specimen_name": row.get("specimen_name", ""),
                "bending_pattern": row.get("bending_pattern", ""),
                "threshold_percent": threshold_percent,
                "assessed_domain": "10-90 % Fmax",
                "point_count": assessed_point_count,
                "assessed_point_count": assessed_point_count,
                "min_bending_percent": _percentile(values, 0),
                "q1_bending_percent": _percentile(values, 25),
                "median_bending_percent": row.get("bending_median_percent") or _percentile(values, 50),
                "q3_bending_percent": _percentile(values, 75),
                "p95_bending_percent": row.get("bending_p95_percent") or _percentile(values, 95),
                "max_bending_percent": row.get("bending_max_percent") or (max(values) if values else ""),
                "fraction_above_threshold": fraction_above_threshold,
                "points_above_threshold": points_above_threshold,
            }
        )
    return rows


def _bending_distribution_points(result: MethodRunResult, run_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    curve_rows = (
        getattr(result, "bounded_curve_family", None)
        or getattr(result, "curve_family", None)
        or getattr(result, "full_curve_family", None)
        or []
    )
    if not isinstance(curve_rows, list):
        return [], {}
    meta_by_run = {str(row.get("run_id") or ""): row for row in run_rows if row.get("run_id")}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in curve_rows:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        grouped.setdefault(run_id, []).append(row)
    points: list[dict[str, Any]] = []
    exact_values_by_run: dict[str, list[float]] = {}
    for run_id, rows in sorted(grouped.items()):
        loads = [_as_float(row.get("load_N")) for row in rows]
        load_values = [abs(value) for value in loads if value is not None]
        if not load_values:
            continue
        max_load = max(load_values)
        if max_load <= 0:
            continue
        lower = max_load * 0.10
        upper = max_load * 0.90
        selected: list[dict[str, Any]] = []
        for row, load in zip(rows, loads):
            if load is None or abs(load) < lower or abs(load) > upper:
                continue
            bending = _bending_percent_from_curve_row(row)
            if bending is None:
                continue
            selected.append(
                {
                    "run_id": run_id,
                    "point_index": row.get("point_index", len(selected)),
                    "load_N": load,
                    "bending_percent": bending,
                }
            )
        if not selected:
            continue
        meta = meta_by_run.get(run_id, {})
        summary_values = [float(point["bending_percent"]) for point in selected]
        exact_values_by_run[run_id] = summary_values
        display_points = _representative_points(selected, max_points=12)
        for order, point in enumerate(display_points):
            points.append(
                {
                    **point,
                    "run_label": meta.get("run_label") or run_display_label(run_id),
                    "specimen_name": meta.get("specimen_name", ""),
                    "median_bending_percent": meta.get("bending_median_percent") or _percentile(summary_values, 50),
                    "p95_bending_percent": meta.get("bending_p95_percent") or _percentile(summary_values, 95),
                    "max_bending_percent": meta.get("bending_max_percent") or max(summary_values),
                    "fraction_above_threshold": meta.get("bending_fraction_above_threshold"),
                    "points_above_threshold": meta.get("bending_points_above_threshold"),
                    "assessed_point_count": len(selected),
                    "sample_order": order,
                    "threshold_percent": meta.get("bending_threshold_percent") or 10.0,
                    "jitter": ((order % 9) - 4) * 0.015,
                }
            )
    return points, exact_values_by_run


def _representative_points(points: list[dict[str, Any]], *, max_points: int) -> list[dict[str, Any]]:
    if len(points) <= max_points:
        return list(points)
    if max_points <= 1:
        return [points[0]]
    selected: list[dict[str, Any]] = []
    last_index = len(points) - 1
    for slot in range(max_points):
        index = round(slot * last_index / (max_points - 1))
        selected.append(points[index])
    return selected


def _bending_percent_from_curve_row(row: dict[str, Any]) -> float | None:
    front = _as_float(
        row.get("front_strain_abs")
        if row.get("front_strain_abs") not in (None, "")
        else row.get("front_strain")
        if row.get("front_strain") not in (None, "")
        else row.get("front_strain_raw")
    )
    rear = _as_float(
        row.get("rear_strain_abs")
        if row.get("rear_strain_abs") not in (None, "")
        else row.get("rear_strain")
        if row.get("rear_strain") not in (None, "")
        else row.get("rear_strain_raw")
    )
    if front is None or rear is None:
        return None
    denominator = abs(front + rear)
    if denominator == 0:
        return None
    return abs(front - rear) / denominator * 100.0


def _acceptance_flags_by_run(result: MethodRunResult) -> dict[str, list[dict[str, Any]]]:
    flags: dict[str, list[dict[str, Any]]] = {}
    payload = result.acceptance_report if isinstance(result.acceptance_report, dict) else {}
    for flag in payload.get("flags", []) or []:
        if not isinstance(flag, dict):
            continue
        run_id = str(flag.get("run_id") or "")
        if run_id:
            flags.setdefault(run_id, []).append(flag)
    for flag in result.run_flags or []:
        if not isinstance(flag, dict):
            continue
        run_id = str(flag.get("run_id") or "")
        if run_id and flag not in flags.setdefault(run_id, []):
            flags[run_id].append(flag)
    return flags


def _iso_failure_mode(row: dict[str, Any]) -> str:
    for key in ("primary_failure_mode", "failure_mode"):
        mode = _iso_failure_mode_value(row.get(key))
        if mode != "not recorded":
            return mode
    return "not recorded"


def _iso_failure_mode_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "not recorded"
    normalized = text.casefold().replace("-", "_").replace(" ", "_")
    normalized = "_".join(part for part in normalized.split("_") if part)
    mapping = {
        "in_plane_shear": "in-plane shear",
        "inplaneshear": "in-plane shear",
        "complex": "complex",
        "through_thickness_shear": "through-thickness shear",
        "throughthicknessshear": "through-thickness shear",
        "splitting": "splitting",
        "delamination": "delamination",
        "not_recorded": "not recorded",
        "unknown": "not recorded",
        "valid": "not recorded",
        "invalid": "not recorded",
        "accepted": "not recorded",
        "rejected": "not recorded",
        "0": "not recorded",
        "1": "not recorded",
    }
    return mapping.get(normalized, "not recorded")


def _failure_location(row: dict[str, Any]) -> str:
    text = str(row.get("failure_location") or "").strip()
    if not text:
        return "not recorded"
    normalized = text.casefold().replace("-", "_").replace(" ", "_")
    if normalized in {"not_recorded", "unknown", "none", "null"}:
        return "not recorded"
    return _enum_label(normalized)


def _failure_observation_completeness(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No reported specimens are available for failure observation review."
    mode_count = sum(1 for row in rows if not _is_not_recorded(row.get("failure_mode_report_value")))
    location_count = sum(1 for row in rows if not _is_not_recorded(row.get("failure_location_report_value")))
    total = len(rows)
    specimen_word = "specimen" if total == 1 else "specimens"
    return (
        f"Failure mode recorded for {mode_count} of {total} reported {specimen_word}; "
        f"failure location recorded for {location_count} of {total}."
    )


def _failure_observation_cell(value: Any) -> str:
    if _is_not_recorded(value):
        return "not recorded"
    return str(value).strip()


def _failure_observation_note(row: dict[str, Any]) -> str:
    note = _first_present(
        row,
            (
                "failure_analysis_notes",
                "visible_buckling_or_bending_observation_report_value",
                "visible_buckling_or_bending_observation",
                "run_notes",
            ),
    )
    if _is_not_recorded(note):
        return ""
    return str(note).strip()


def _is_not_recorded(value: Any) -> bool:
    text = str(value or "").strip()
    normalized = text.casefold().replace("_", " ").replace("-", " ")
    return not text or normalized in {"not recorded", "unknown", "none", "none observed", "null"}


def _invalid_specimen_overview(rows: list[dict[str, Any]]) -> str:
    labels = [str(row.get("Run #") or "").strip() for row in rows if row.get("Run #")]
    labels = _dedupe_text(labels)
    if not labels:
        return "None recorded."
    return f"{', '.join(labels)} excluded/reviewed; see invalid specimen summary."


def _invalid_specimen_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "None recorded"
    return "; ".join(
        f"{row.get('Run #')}: {row.get('Reason')}"
        for row in rows
        if row.get("Run #")
    )


def _bending_compliance_summary(all_rows: list[dict[str, Any]], final_rows: list[dict[str, Any]]) -> str:
    def count(rows: list[dict[str, Any]], *patterns: str) -> int:
        wanted = set(patterns)
        return sum(1 for row in rows if str(row.get("bending_pattern") or "") in wanted)

    total = len(all_rows)
    passing = count(all_rows, "PASS")
    exceeding = sum(1 for row in all_rows if _bending_points_above_threshold(row) > 0)
    if not exceeding:
        exceeding = count(all_rows, "PASS_WITH_SPIKES", "WARN_TRANSIENT_BENDING", "FAIL_SUSTAINED_BENDING")
    not_assessed = sum(
        1
        for row in all_rows
        if not row.get("bending_pattern")
        and row.get("bending_points_above_threshold") in (None, "")
        and row.get("bending_point_count") in (None, "")
    )
    not_assessed_text = f" {not_assessed} not assessed." if not_assessed else ""
    return (
        f"{passing}/{total} tested runs remain within the 10 % bending criterion; "
        f"{exceeding} exceed the criterion.{not_assessed_text} "
        "Criterion: 10 % over 10-90 % Fmax."
    )


def _failure_analysis_notes(run_rows: list[dict[str, Any]], invalid_rows: list[dict[str, Any]]) -> str:
    notes: list[str] = []
    for row in run_rows:
        label = str(row.get("run_label") or run_display_label(row.get("run_id", "")))
        note = _first_present(
            row,
            (
                "failure_analysis_notes",
                "visible_buckling_or_bending_observation_report_value",
                "visible_buckling_or_bending_observation",
                "rejection_reason",
                "human_decision_reason",
                "run_notes",
            ),
        )
        if note:
            notes.append(f"{label}: {note}")
    return "; ".join(_dedupe_text(notes)) if notes else "No failure-analysis notes recorded."


def _bending_evidence_label(row: dict[str, Any]) -> str:
    threshold = _as_float(row.get("bending_threshold_percent")) or 10.0
    points_above = _bending_points_above_threshold(row)
    point_count = _as_float(row.get("bending_point_count"))
    max_bending = _as_float(row.get("bending_max_percent"))
    parts: list[str] = []
    if point_count is not None:
        parts.append(f"{int(points_above)}/{int(point_count)} points > {_format_plain_number(threshold)} %")
    elif points_above > 0:
        parts.append(f"{int(points_above)} points > {_format_plain_number(threshold)} %")
    if max_bending is not None:
        parts.append(f"max {_format_plain_number(max_bending)} %")
    return "; ".join(parts)


def _bending_points_above_threshold(row: dict[str, Any]) -> float:
    points = _as_float(row.get("bending_points_above_threshold"))
    if points is not None:
        return points
    max_bending = _as_float(row.get("bending_max_percent"))
    threshold = _as_float(row.get("bending_threshold_percent")) or 10.0
    if max_bending is not None and max_bending > threshold:
        return 1.0
    return 0.0


def _format_plain_number(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _enum_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("_", " ").replace("-", " ").strip()


def _enum_label_with_detail(value: Any, detail: Any) -> str:
    label = _enum_label(value)
    detail_text = str(detail or "").strip()
    if label.casefold() in {"other", "other specified"} and detail_text:
        return f"Other: {detail_text}"
    return label


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return ""


def _dedupe_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _percentile(values: list[float], percentile: float) -> float | str:
    if not values:
        return ""
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _deviations_from_standard_rows(
    result: MethodRunResult,
    missing_report_fields: list[dict[str, Any]],
    iso14126_resolve_checks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if _is_iso14126_result(result):
        from methods.iso14126.report_compliance import deviation_rows_from_checks

        return deviation_rows_from_checks(
            iso14126_resolve_checks or [],
            missing_report_fields,
            list(result.validation_deviations),
        )

    rows: list[dict[str, Any]] = []
    for item in result.validation_deviations:
        rows.append(
            {
                "source": "validation",
                "section_id": "",
                "field": item.get("field"),
                "severity": item.get("severity"),
                "status": item.get("status"),
                "message": item.get("message") or item.get("note") or "",
                "run_id": item.get("run_id"),
            }
        )
    for field in missing_report_fields:
        rows.append(
            {
                "source": "report_completeness",
                "section_id": field.get("section_id"),
                "field": field.get("field"),
                "severity": field.get("severity"),
                "status": "warn",
                "message": field.get("message"),
                "run_id": "",
            }
        )
    return rows


def _aggregate_curve_summary(
    aligned_curves: list[dict[str, Any]],
    curve_policy: dict[str, Any],
    selection_set: str,
) -> list[dict[str, Any]]:
    if not aligned_curves:
        return []
    coordinate_contract = coordinate_contract_from_rows(aligned_curves)
    observations = [_as_int(row.get("n")) for row in aligned_curves]
    observations = [value for value in observations if value is not None]
    return [
        {
            "selection_set": selection_set,
            "alignment_policy": curve_policy.get("alignment_policy") or _nested(curve_policy, "alignment", "policy"),
            "alignment_domain": _nested(curve_policy, "alignment", "domain") or aligned_curves[0].get("alignment_domain", ""),
            "source_boundaries": _nested(curve_policy, "alignment", "source_boundaries") or aligned_curves[0].get("source_boundaries", ""),
            "boundary_aligned": (aligned_curves[0].get("alignment_domain") == "experiment_progress"),
            "x_axis": curve_policy.get("x_axis") or _nested(curve_policy, "alignment", "x_axis") or "mean_strain",
            "x_field": coordinate_contract["x_field"],
            "x_coordinate_kind": coordinate_contract["x_coordinate_kind"],
            "x_label": coordinate_contract["x_label"],
            "x_unit": coordinate_contract["x_unit"],
            "x_display_unit": coordinate_contract["x_display_unit"],
            "x_display_scale": coordinate_contract["x_display_scale"],
            "x_aliases": ",".join(coordinate_contract.get("x_aliases", [])),
            "source_artifact": coordinate_contract["source_artifact"],
            "transform_stage": coordinate_contract["transform_stage"],
            "y_axis": curve_policy.get("y_axis") or "stress_MPa",
            "grid_points": len(aligned_curves),
            "observations_min": min(observations) if observations else "",
            "observations_max": max(observations) if observations else "",
            "observations_at_start": observations[0] if observations else "",
            "observations_at_end": observations[-1] if observations else "",
            "supports_range_band": True,
            "supports_std_band": True,
            "supports_mean_curve": True,
            "supports_individual_replicates": True,
        }
    ]


def _aggregate_plot_spec(
    *,
    aligned_curves: list[dict[str, Any]],
    characteristic_points: list[dict[str, Any]],
    curve_policy: dict[str, Any],
    selection_set: str,
    selected_run_ids: set[str],
) -> dict[str, Any]:
    run_columns = sorted(
        key for key in aligned_curves[0].keys()
        if aligned_curves and key.endswith("_stress_MPa") and key not in {"stress_MPa"}
    ) if aligned_curves else []
    coordinate_contract = coordinate_contract_from_rows(aligned_curves)
    return {
        "schema_id": "method.aggregate_plot_spec.v0_1",
        "plot_title": "",
        "selection_set": selection_set,
        "selected_run_ids": sorted(selected_run_ids),
        "alignment_policy": curve_policy,
        "x_coordinate_contract": coordinate_contract,
        "data_sources": {
            "aligned_curves": "report/aligned_curves.csv",
            "characteristic_points": "report/characteristic_points.csv",
        },
        "axes": {
            "x": {
                "field": coordinate_contract["x_field"],
                "coordinate_kind": coordinate_contract["x_coordinate_kind"],
                "label": coordinate_contract["x_label"],
                "unit": coordinate_contract["x_unit"],
                "display_unit": coordinate_contract["x_display_unit"],
                "display_scale": coordinate_contract["x_display_scale"],
                "compatibility_aliases": coordinate_contract.get("x_aliases", []),
                "source_artifact": coordinate_contract["source_artifact"],
                "transform_stage": coordinate_contract["transform_stage"],
            },
            "y": {"field": "stress_MPa", "label": "Stress", "unit": "MPa"},
        },
        "layers": {
            "individual_replicates": {"enabled": True, "columns": run_columns},
            "range_band": {"enabled": True, "min_field": "min", "max_field": "max"},
            "std_band": {"enabled": True, "lower_expression": "mean - std", "upper_expression": "mean + std"},
            "mean_curve": {"enabled": True, "field": "mean"},
            "observation_count": {"enabled": True, "field": "n"},
            "characteristic_markers": {"enabled": True, "points": characteristic_points},
        },
    }


def _report_payload(context: ReportContext, document_payload: dict[str, Any]) -> dict[str, Any]:
    result = context.result
    plot_data_freshness = _plot_data_freshness_from_document(document_payload)
    summary = {
        "selection_set": context.selection_set,
        "selection_source": context.selection_source,
        "run_count": len(result.specimen_results),
        "selected_run_count": len(context.selection_run_ids),
        "aggregate_metric_count": len(context.table("aggregate_statistics")),
        "aligned_curve_points": len(context.table("aligned_curves")),
        "missing_report_field_count": len(context.table("missing_report_fields")),
        "standard_deviation_count": _iso_standard_deviation_count(context.table("iso14126_resolve_checks")),
        "standard_required_missing_count": _iso_standard_required_missing_count(context.table("iso14126_resolve_checks")),
        "report_completion_status": context.table("report_completion_status").get("status"),
        "bounded_reduction": bool(result.experiment_boundaries),
        "boundary_aligned_aggregation": any(
            isinstance(row, dict) and row.get("alignment_domain") == "experiment_progress"
            for row in context.table("aligned_curves")[:1]
        ),
        "plot_data_status": plot_data_freshness.get("status", ""),
    }
    return {
        "schema_id": "method.iso14126_report.v0_1",
        "report_id": "iso14126_report",
        "surface": "test_report",
        "method_id": result.method_package.method_id,
        "method_version": result.method_package.version,
        "method_name": result.method_package.name,
        "standard_reference": result.method_package.manifest.get("standard_reference", "ISO 14126"),
        "source_package": str(result.source.path),
        "mapping_id": result.mapping.get("mapping_id"),
        "selection_set": context.selection_set,
        "selection_source": context.selection_source,
        "summary": summary,
        "report_recipe_id": context.recipe.get("recipe_id"),
        "report_document": document_payload,
        "report_values_used": context.table("report_values_used"),
        "missing_report_fields": context.table("missing_report_fields"),
        "report_field_catalog_resolved": context.table("report_field_catalog_resolved"),
        "report_completion_status": context.table("report_completion_status"),
        "report_field_overrides": context.table("report_field_overrides"),
        "report_override_ledger": context.table("report_override_ledger"),
        "report_sections": context.table("report_sections"),
        "report_completeness_summary": context.table("report_completeness_summary"),
        "failure_analysis": context.table("failure_analysis"),
        "failure_analysis_run_evidence": context.table("failure_analysis_run_evidence"),
        "failure_analysis_observations": context.table("failure_analysis_observations"),
        "failure_analysis_invalid_specimens": context.table("failure_analysis_invalid_specimens"),
        "failure_analysis_bending_distribution": context.table("failure_analysis_bending_distribution"),
        "iso14126_resolve_checks": context.table("iso14126_resolve_checks"),
        "deviations_from_standard": context.table("deviations_from_standard"),
        "individual_results": context.table("individual_results"),
        "aggregate_statistics": context.table("aggregate_statistics"),
        "aggregate_curve_summary": context.table("aggregate_curve_summary"),
        "plot_data_freshness": plot_data_freshness,
        "aggregate_plot_spec": context.table("aggregate_plot_spec"),
        "characteristic_points": context.table("characteristic_points"),
        "feature_lines": context.table("feature_lines"),
        "aligned_curves": context.table("aligned_curves"),
        "aligned_curves_preview": context.table("aligned_curves")[:25],
        "alignment_policy": context.curve_policy,
        "artifacts": _artifact_paths(),
    }


def _artifact_files(
    payload: dict[str, Any],
    html: str,
    document_payload: dict[str, Any],
    recipe: dict[str, Any],
    context: ReportContext,
) -> dict[str, bytes]:
    report_manifest = {
        "schema_id": "report.manifest.v0_1",
        "report_id": payload["report_id"],
        "recipe_id": recipe.get("recipe_id"),
        "engine": "GenericReportEngine",
        "artifacts": _artifact_paths(),
    }
    return {
        "report/test_report.html": html.encode("utf-8"),
        "report/test_report.json": json_bytes(payload),
        "report/iso14126_report.html": html.encode("utf-8"),
        "report/iso14126_report.json": json_bytes(payload),
        "report/report_document.json": json_bytes(document_payload),
        "report/report_manifest.json": json_bytes(report_manifest),
        "report/report_recipe_resolved.json": json_bytes(recipe),
        "report/report_completion_status.json": json_bytes(context.table("report_completion_status")),
        "report/report_field_catalog_resolved.json": json_bytes(context.table("report_field_catalog_resolved")),
        "report/report_values_used.csv": write_dict_rows(context.table("report_values_used")).encode("utf-8"),
        "report/missing_report_fields.csv": write_dict_rows(context.table("missing_report_fields")).encode("utf-8"),
        "report/report_field_overrides.json": json_bytes({
            "schema_id": "report.field_overrides.v0_1",
            "overrides": context.table("report_field_overrides"),
        }),
        "report/report_override_ledger.json": json_bytes(context.table("report_override_ledger")),
        "report/report_sections.json": json_bytes(context.table("report_sections")),
        "report/report_completeness_summary.csv": write_dict_rows(context.table("report_completeness_summary")).encode("utf-8"),
        "report/individual_results.csv": write_dict_rows(context.table("individual_results")).encode("utf-8"),
        "report/aggregate_statistics.csv": write_dict_rows(context.table("aggregate_statistics")).encode("utf-8"),
        "report/characteristic_points.csv": write_dict_rows(context.table("characteristic_points")).encode("utf-8"),
        "report/feature_lines.csv": write_dict_rows(context.table("feature_lines")).encode("utf-8"),
        "report/aligned_curves.csv": write_dict_rows(context.table("aligned_curves")).encode("utf-8"),
        "report/failure_analysis.csv": write_dict_rows(context.table("failure_analysis")).encode("utf-8"),
        "report/failure_observations.csv": write_dict_rows(context.table("failure_analysis_observations")).encode("utf-8"),
        "report/invalid_specimen_summary.csv": write_dict_rows(context.table("failure_analysis_invalid_specimens")).encode("utf-8"),
        "report/bending_distribution_summary.csv": write_dict_rows(context.table("bending_distribution_summary")).encode("utf-8"),
        "report/iso14126_resolve_checks.csv": write_dict_rows(context.table("iso14126_resolve_checks")).encode("utf-8"),
        "report/iso14126_resolve_checks.json": json_bytes({
            "schema_id": "method.iso14126_resolve_checks.v0_1",
            "records": context.table("iso14126_resolve_checks"),
        }),
        "report/deviations_from_standard.csv": write_dict_rows(context.table("deviations_from_standard")).encode("utf-8"),
        "report/aggregate_curve_summary.csv": write_dict_rows(context.table("aggregate_curve_summary")).encode("utf-8"),
        "report/plot_data_freshness.json": json_bytes(payload.get("plot_data_freshness", {})),
        "report/aggregate_plot_spec.json": json_bytes(context.table("aggregate_plot_spec")),
        "report/vega_specs/aggregate_stress_strain_mean_variability.json": json_bytes(context.table("aggregate_plot_spec")),
        "report/vega_specs/failure_analysis_bending_distribution.json": json_bytes(
            _vega_lite_spec_from_document(document_payload, "failure_analysis_bending_distribution")
            or context.table("failure_analysis_bending_distribution")
        ),
    }


def _artifact_paths() -> list[str]:
    return [
        "report/test_report.html",
        "report/test_report.json",
        "report/iso14126_report.html",
        "report/iso14126_report.json",
        "report/report_document.json",
        "report/report_manifest.json",
        "report/report_recipe_resolved.json",
        "report/report_completion_status.json",
        "report/report_quality_gate.json",
        "report/report_field_catalog_resolved.json",
        "report/report_values_used.csv",
        "report/missing_report_fields.csv",
        "report/report_field_overrides.json",
        "report/report_override_ledger.json",
        "report/report_sections.json",
        "report/report_completeness_summary.csv",
        "report/individual_results.csv",
        "report/aggregate_statistics.csv",
        "report/characteristic_points.csv",
        "report/feature_lines.csv",
        "report/aligned_curves.csv",
        "report/failure_analysis.csv",
        "report/failure_observations.csv",
        "report/invalid_specimen_summary.csv",
        "report/bending_distribution_summary.csv",
        "report/iso14126_resolve_checks.csv",
        "report/iso14126_resolve_checks.json",
        "report/deviations_from_standard.csv",
        "report/aggregate_curve_summary.csv",
        "report/plot_data_freshness.json",
        "report/aggregate_plot_spec.json",
        "report/vega_specs/aggregate_stress_strain_mean_variability.json",
        "report/vega_specs/failure_analysis_bending_distribution.json",
    ]


def _plot_data_freshness_from_document(document_payload: dict[str, Any]) -> dict[str, Any]:
    sections = document_payload.get("sections") if isinstance(document_payload.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        blocks = section.get("blocks") if isinstance(section.get("blocks"), list) else []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            data = block.get("data") if isinstance(block.get("data"), dict) else {}
            freshness = data.get("plot_data_freshness") if isinstance(data.get("plot_data_freshness"), dict) else {}
            if freshness:
                return dict(freshness)
    return {"schema_id": "report.plot_data_freshness.v0_1", "status": "unavailable", "reasons": ["No plot-data freshness block was generated."]}


def _vega_lite_spec_from_document(document_payload: dict[str, Any], spec_id: str) -> dict[str, Any]:
    sections = document_payload.get("sections") if isinstance(document_payload.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        blocks = section.get("blocks") if isinstance(section.get("blocks"), list) else []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            data = block.get("data") if isinstance(block.get("data"), dict) else {}
            if data.get("spec_id") == spec_id and isinstance(data.get("vega_lite_spec"), dict):
                return data["vega_lite_spec"]
    return {}


def _quality_status_from_completion(status: str) -> str:
    if status == "COMPLETE":
        return "RC_READY"
    if status == "COMPLETE_WITH_WARNINGS":
        return "RC_WITH_WARNINGS"
    if status:
        return "RC_BLOCKED"
    return "UNKNOWN"


def _first_specimen_values(specimen_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not specimen_results:
        return {}
    return dict(specimen_results[0])


def _specimen_available_fields(specimen_results: list[dict[str, Any]]) -> set[str]:
    available: set[str] = set()
    for row in specimen_results:
        available.update(str(key) for key in row)
    return available


def _value_row(field: str, value: Any, source: str, category: str) -> dict[str, Any]:
    return {
        "field": field,
        "value": value,
        "unit": "",
        "source": source,
        "category": category,
    }


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _has_human_overrides(result: MethodRunResult) -> bool:
    decisions = result.human_decisions if isinstance(result.human_decisions, dict) else {}
    rows = decisions.get("decisions", [])
    return isinstance(rows, list) and any(
        isinstance(row, dict) and str(row.get("decision_type")) != "confirm"
        for row in rows
    )


def _has_final_selection(result: MethodRunResult) -> bool:
    if result.final_report_runs:
        return True
    if result.selection_membership_final:
        return True
    payload = result.selection_sets_final if isinstance(result.selection_sets_final, dict) else {}
    return any(
        isinstance(selection, dict) and selection.get("selection_id") == FINAL_SELECTION_ID
        for selection in payload.get("selection_sets", []) or []
    )


def _final_rows_by_run(result: MethodRunResult) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("run_id")): row
        for row in (result.final_report_runs or [])
        if isinstance(row, dict) and row.get("run_id")
    }
