from __future__ import annotations

from typing import Any

from methods.core.method_result import MethodRunResult
from reporting.completion.report_field_catalog import ReportFieldCatalogEntry
from reporting.completion.report_override import ReportFieldOverride


class ReportValueResolver:
    """Resolve report values with explicit source precedence and provenance."""

    def resolve(
        self,
        *,
        result: MethodRunResult,
        catalog: list[ReportFieldCatalogEntry],
        selection_set: str,
        selection_source: str,
        overrides: tuple[ReportFieldOverride, ...] = (),
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        base_rows = _base_rows(result, selection_set, selection_source)
        override_rows = _override_rows(overrides, catalog)
        metadata_rows = _source_metadata_value_rows(result)
        method_rows = _method_output_rows(result, catalog)
        default_rows = _default_rows(catalog)
        values = _merge_by_precedence([override_rows, metadata_rows, base_rows, method_rows, default_rows])
        missing = _missing_rows(catalog, values)
        return values, missing


def _base_rows(result: MethodRunResult, selection_set: str, selection_source: str) -> list[dict[str, Any]]:
    standard = result.method_package.manifest.get("standard_reference") or "ISO 14126"
    return [
        _value_row("method_id", result.method_package.method_id, "method_manifest", "method_package.method_id"),
        _value_row("method_version", result.method_package.version, "method_manifest", "method_package.version"),
        _value_row("method_name", result.method_package.name, "method_manifest", "method_package.name"),
        _value_row("source_package", str(result.source.path), "source_reference", "source_reference.source_package.path"),
        _value_row("selection_set", selection_set, "acceptance", "acceptance.selection_set"),
        _value_row("selection_source", selection_source, "acceptance", "acceptance.selection_source"),
        _value_row("run_count", len(result.specimen_results), "method_outputs", "method_outputs.specimen_results"),
        _value_row("selected_run_count", len(_selection_run_ids(result, selection_set)), "acceptance", "acceptance.selection_membership"),
        _value_row("standard_reference", standard, "method_manifest", "method_package.manifest.standard_reference"),
    ]


def _override_rows(overrides: tuple[ReportFieldOverride, ...], catalog: list[ReportFieldCatalogEntry]) -> list[dict[str, Any]]:
    by_key = {entry.field_key: entry for entry in catalog}
    rows: list[dict[str, Any]] = []
    for override in overrides:
        entry = by_key.get(override.field_key)
        rows.append(
            _value_row(
                override.field_key,
                override.value,
                "report_override",
                f"report_overrides.{override.field_key}",
                section=override.section or (entry.section_id if entry else ""),
                report_importance=entry.report_importance if entry else "",
                status="present_override",
                provenance={
                    "reason": override.reason,
                    "reviewer": override.reviewer,
                    "timestamp": override.timestamp,
                    "source_surface": override.source_surface,
                },
            )
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
        value, unit, source_type, source_path = _metadata_value_for_field(source, field)
        if value in (None, ""):
            continue
        aliases = [field_id]
        if report_role and report_role != field_id:
            aliases.append(report_role)
        rows.append(
            _value_row(
                report_role or field_id,
                value,
                source_type,
                source_path,
                unit=unit or str(field.get("standard_unit") or ""),
                aliases=aliases,
                scope=_metadata_field_scope(field),
                source_field_id=field_id,
                report_importance=str(field.get("report_importance") or ""),
                section=_section_for_schema_field(source.schema, field_id),
            )
        )
    return rows


def _metadata_value_for_field(source: Any, field: dict[str, Any]) -> tuple[Any, str, str, str]:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    if location == "dataset_json":
        path = str(storage.get("path") or "")
        value, unit = _payload_value(_get_dotted_value(source.dataset, path))
        return value, unit, "source_mtdp_dataset", f"dataset.{path}"
    if location == "token_preamble":
        token = str(storage.get("token") or "")
        for run in source.runs:
            run_token = run.token(token)
            if run_token is not None and run_token.value not in (None, ""):
                return run_token.value, run_token.unit or "", "source_mtdp_run_token", f"runs.{run.run_id}.tokens.{token}"
    if location == "provenance":
        path = str(storage.get("path") or "")
        for run in source.runs:
            run_path = path.format(run_id=run.run_id)
            prefix = f"runs.{run.run_id}."
            local_path = run_path[len(prefix):] if run_path.startswith(prefix) else run_path
            value, unit = _payload_value(_get_dotted_value(run.provenance, local_path))
            if value not in (None, ""):
                return value, unit, "source_mtdp_run_provenance", f"runs.{run.run_id}.{local_path}"
    return None, "", "source_mtdp_metadata", ""


def _method_output_rows(result: MethodRunResult, catalog: list[ReportFieldCatalogEntry]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_specimen = dict(result.specimen_results[0]) if result.specimen_results else {}
    dataset_summary = dict(result.dataset_summary[0]) if result.dataset_summary else {}
    for entry in catalog:
        if entry.field_key in first_specimen and first_specimen[entry.field_key] not in (None, ""):
            rows.append(
                _value_row(
                    entry.field_key,
                    first_specimen[entry.field_key],
                    "mtda_method_output",
                    f"method_outputs.specimen_results[0].{entry.field_key}",
                    section=entry.section_id,
                    report_importance=entry.report_importance,
                )
            )
        elif entry.field_key in dataset_summary and dataset_summary[entry.field_key] not in (None, ""):
            rows.append(
                _value_row(
                    entry.field_key,
                    dataset_summary[entry.field_key],
                    "mtda_method_output",
                    f"method_outputs.dataset_summary[0].{entry.field_key}",
                    section=entry.section_id,
                    report_importance=entry.report_importance,
                )
            )
    return rows


def _default_rows(catalog: list[ReportFieldCatalogEntry]) -> list[dict[str, Any]]:
    return [
        _value_row(
            entry.field_key,
            entry.default,
            "method_report_default",
            f"report_recipe.defaults.{entry.field_key}",
            section=entry.section_id,
            report_importance=entry.report_importance,
        )
        for entry in catalog
        if entry.default not in (None, "")
    ]


def _merge_by_precedence(row_groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in row_groups:
        for row in group:
            field = str(row.get("field") or "")
            aliases = {str(alias) for alias in row.get("aliases", []) or []}
            if field in seen or seen & aliases:
                continue
            rows.append(row)
            seen.add(field)
            seen.update(aliases)
    return rows


def _missing_rows(catalog: list[ReportFieldCatalogEntry], values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = {str(row.get("field")) for row in values if row.get("value") not in (None, "")}
    for row in values:
        available.update(str(alias) for alias in row.get("aliases", []) or [])
    missing: list[dict[str, Any]] = []
    for entry in catalog:
        if entry.field_key in available:
            continue
        missing.append(
            {
                "section_id": entry.section_id,
                "section_title": entry.section_title,
                "field": entry.field_key,
                "field_key": entry.field_key,
                "label": entry.label,
                "severity": "required" if entry.report_importance == "required" else "report_completeness",
                "requirement_level": entry.report_importance,
                "report_importance": entry.report_importance,
                "status": "missing",
                "source_type": "missing",
                "source_path": "",
                "message": f"Report field '{entry.field_key}' was not found in overrides, package metadata, method outputs, or defaults.",
            }
        )
    return missing


def _value_row(
    field: str,
    value: Any,
    source_type: str,
    source_path: str,
    *,
    unit: str = "",
    aliases: list[str] | None = None,
    scope: str = "",
    source_field_id: str = "",
    report_importance: str = "",
    section: str = "",
    status: str = "present",
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "field": field,
        "field_key": field,
        "value": value,
        "unit": unit,
        "status": status,
        "source": source_type,
        "source_type": source_type,
        "source_path": source_path,
        "category": "report_completeness",
        "report_importance": report_importance,
        "section": section,
    }
    if aliases:
        row["aliases"] = aliases
    if scope:
        row["scope"] = scope
    if source_field_id:
        row["source_field_id"] = source_field_id
    if provenance:
        row.update(provenance)
    return row


def _selection_run_ids(result: MethodRunResult, selection_set: str) -> set[str]:
    if selection_set == "final_report_runs":
        selected = {
            str(row.get("run_id"))
            for row in (result.selection_membership_final or [])
            if str(row.get("selection_set")) == "final_report_runs"
            and str(row.get("included")).casefold() in {"1", "true", "yes"}
        }
        if selected:
            return selected
        selected = {
            str(row.get("run_id"))
            for row in (result.final_report_runs or [])
            if row.get("run_id") and str(row.get("included", True)).casefold() in {"1", "true", "yes"}
        }
        if selected:
            return selected
    selected = {
        str(row.get("run_id"))
        for row in result.selection_membership
        if str(row.get("selection_set")) == selection_set and str(row.get("included")).casefold() in {"1", "true", "yes"}
    }
    return selected or {str(row.get("run_id")) for row in result.specimen_results if row.get("run_id")}


def _section_for_schema_field(source_schema: dict[str, Any], field_id: str) -> str:
    for section in source_schema.get("metadata_sections", []) or []:
        if not isinstance(section, dict):
            continue
        for field_ref in section.get("fields", []) or []:
            ref = field_ref.get("field_ref") if isinstance(field_ref, dict) else field_ref
            if str(ref) == field_id:
                return str(section.get("id") or "")
    return ""


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
    return "dataset" if str(storage.get("location") or "") == "dataset_json" else "run"
