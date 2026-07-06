from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportFieldCatalogEntry:
    field_key: str
    label: str
    section_id: str
    section_title: str
    report_importance: str = "recommended"
    report_role: str = ""
    source: str = "recipe"
    required: bool = False
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "field_key": self.field_key,
            "label": self.label,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "report_importance": self.report_importance,
            "report_role": self.report_role,
            "source": self.source,
            "required": self.required,
        }
        if self.default not in (None, ""):
            data["default"] = self.default
        return data


def build_report_field_catalog(recipe: dict[str, Any], source_schema: dict[str, Any] | None = None) -> list[ReportFieldCatalogEntry]:
    schema_roles = _schema_roles(source_schema or {})
    entries: list[ReportFieldCatalogEntry] = []
    seen: set[str] = set()
    for section in _sections(recipe):
        section_id = str(section.get("id") or "")
        section_title = str(section.get("title") or section_id)
        for block in section.get("blocks", []) or []:
            if not isinstance(block, dict) or block.get("type") != "field_table":
                continue
            for field in block.get("fields", []) or []:
                entry = _entry_from_recipe_field(field, section_id, section_title, schema_roles)
                if entry and entry.field_key not in seen:
                    entries.append(entry)
                    seen.add(entry.field_key)
    return entries


def _sections(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    sections = recipe.get("sections") or recipe.get("report_sections") or []
    return [section for section in sections if isinstance(section, dict)]


def _entry_from_recipe_field(
    field: Any,
    section_id: str,
    section_title: str,
    schema_roles: dict[str, dict[str, Any]],
) -> ReportFieldCatalogEntry | None:
    if isinstance(field, str):
        key = field
        label = field
        payload: dict[str, Any] = {}
    elif isinstance(field, dict) and field.get("key"):
        key = str(field["key"])
        label = str(field.get("label") or key)
        payload = field
    else:
        return None
    schema = schema_roles.get(key, {})
    importance = _importance(payload, schema)
    return ReportFieldCatalogEntry(
        field_key=key,
        label=label,
        section_id=section_id,
        section_title=section_title,
        report_importance=importance,
        report_role=str(schema.get("report_role") or key),
        source="recipe+schema" if schema else "recipe",
        required=importance == "required",
        default=payload.get("default", schema.get("default")),
    )


def _schema_roles(source_schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    roles: dict[str, dict[str, Any]] = {}
    fields = list(source_schema.get("dataset_fields", []) or []) + list(source_schema.get("run_fields", []) or [])
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_id = str(field.get("field_id") or field.get("key") or "").strip()
        report_role = str(field.get("report_role") or "").strip()
        for key in (field_id, report_role):
            if key:
                roles.setdefault(key, field)
    return roles


def _importance(payload: dict[str, Any], schema: dict[str, Any]) -> str:
    explicit = str(payload.get("report_importance") or payload.get("requirement_level") or "").casefold()
    if explicit in {"required", "recommended", "optional", "none"}:
        return explicit
    severity = str(payload.get("severity") or "").casefold()
    if severity in {"required", "execution_critical", "critical"}:
        return "required"
    if payload.get("required") is True:
        return "required"
    required_for = payload.get("required_for")
    if isinstance(required_for, list) and any(str(item).casefold() in {"formal_report", "test_report"} for item in required_for):
        return "required"
    schema_importance = str(schema.get("report_importance") or "").casefold()
    if schema_importance in {"required", "recommended", "optional", "none"}:
        return schema_importance
    return "recommended"
