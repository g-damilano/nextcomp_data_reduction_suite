from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPSchema


FIELD_MARKER_LEGEND = "* Required    ** Recommended    Blank = optional"


@dataclass(frozen=True, slots=True)
class MetadataFieldRow:
    field_id: str
    label: str
    type: str
    required: bool
    report_importance: str
    report_role: str
    method_role: str
    unit: str
    description: str
    marker: str
    display_label: str
    status: str
    value_preview: str = ""


@dataclass(frozen=True, slots=True)
class MetadataSectionView:
    id: str
    label: str
    scope: str
    ui_group: str
    report_section: str
    fields: tuple[MetadataFieldRow, ...]
    required_missing_count: int = 0
    recommended_missing_count: int = 0
    optional_missing_count: int = 0
    present_count: int = 0

    @property
    def summary(self) -> str:
        return (
            f"{self.present_count}/{len(self.fields)} present, "
            f"{self.required_missing_count} required missing, "
            f"{self.recommended_missing_count} recommended missing"
        )

    @property
    def completion_badge(self) -> str:
        if self.required_missing_count:
            return f"{self.required_missing_count} required missing"
        if self.recommended_missing_count:
            return f"{self.recommended_missing_count} recommended missing"
        return "Complete"

    @property
    def status(self) -> str:
        if self.required_missing_count:
            return "required_missing"
        if self.recommended_missing_count:
            return "recommended_missing"
        return "complete"


@dataclass(frozen=True, slots=True)
class MetadataSectionPanelModel:
    scope: str
    sections: tuple[MetadataSectionView, ...] = field(default_factory=tuple)
    legend: str = FIELD_MARKER_LEGEND

    @property
    def required_missing_count(self) -> int:
        return sum(section.required_missing_count for section in self.sections)

    @property
    def recommended_missing_count(self) -> int:
        return sum(section.recommended_missing_count for section in self.sections)

    @property
    def optional_missing_count(self) -> int:
        return sum(section.optional_missing_count for section in self.sections)

    @property
    def present_count(self) -> int:
        return sum(section.present_count for section in self.sections)

    @property
    def field_count(self) -> int:
        return sum(len(section.fields) for section in self.sections)

    @property
    def completion_summary(self) -> dict[str, int | str]:
        if self.required_missing_count:
            status = "INCOMPLETE"
        elif self.recommended_missing_count:
            status = "COMPLETE_WITH_WARNINGS"
        else:
            status = "COMPLETE"
        return {
            "status": status,
            "field_count": self.field_count,
            "present_count": self.present_count,
            "required_missing_count": self.required_missing_count,
            "recommended_missing_count": self.recommended_missing_count,
            "optional_missing_count": self.optional_missing_count,
        }

    def missing_fields(self, importance: str | None = None) -> tuple[MetadataFieldRow, ...]:
        rows = [
            row
            for section in self.sections
            for row in section.fields
            if row.status in {"required_missing", "recommended_missing", "optional_missing"}
        ]
        if importance:
            rows = [row for row in rows if row.report_importance == importance]
        return tuple(rows)


def metadata_section_panel_model(
    schema: MTDPSchema,
    *,
    scope: str,
    values: Mapping[str, EnrichedFieldValue | Any] | None = None,
) -> MetadataSectionPanelModel:
    values = values or {}
    sections: list[MetadataSectionView] = []
    for section in schema.metadata_sections_for_scope(scope):
        rows: list[MetadataFieldRow] = []
        for field in section.fields:
            value = values.get(field.field_id)
            preview = _preview_value(value)
            importance = field.report_importance or ("required" if field.required else "optional")
            status = _field_status(field.required, importance, preview)
            rows.append(
                MetadataFieldRow(
                    field_id=field.field_id,
                    label=field.label,
                    type=field.type,
                    required=field.required,
                    report_importance=importance,
                    report_role=field.report_role or "",
                    method_role=field.method_role or "",
                    unit=field.standard_unit or "",
                    description=field.description or "",
                    marker=importance_marker(field),
                    display_label=_display_label(field),
                    status=status,
                    value_preview=preview,
                )
            )
        sections.append(
            MetadataSectionView(
                id=section.id,
                label=section.label,
                scope=section.scope,
                ui_group=section.ui_group,
                report_section=section.report_section or "",
                fields=tuple(rows),
                required_missing_count=sum(1 for row in rows if row.status == "required_missing"),
                recommended_missing_count=sum(1 for row in rows if row.status == "recommended_missing"),
                optional_missing_count=sum(1 for row in rows if row.status == "optional_missing"),
                present_count=sum(1 for row in rows if row.status == "present"),
            )
        )
    return MetadataSectionPanelModel(scope=scope, sections=tuple(sections))


def importance_marker(field: Any) -> str:
    if bool(getattr(field, "required", False)) or is_required_importance(getattr(field, "report_importance", "")):
        return "*"
    if is_recommended_importance(getattr(field, "report_importance", "")):
        return "**"
    return ""


def _display_label(field: Any) -> str:
    marker = importance_marker(field)
    return f"{field.label} {marker}" if marker else str(field.label)


def _preview_value(value: EnrichedFieldValue | Any) -> str:
    if isinstance(value, EnrichedFieldValue):
        value = value.value
    if value in (None, ""):
        return ""
    if isinstance(value, dict) and "value" in value:
        value = value.get("value")
    return str(value)


def _field_status(required: bool, importance: str, preview: str) -> str:
    if preview:
        return "present"
    if required or is_required_importance(importance):
        return "required_missing"
    if is_recommended_importance(importance):
        return "recommended_missing"
    return "optional_missing"


def is_required_importance(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    return text == "required" or text.startswith("required_")


def is_recommended_importance(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    return text == "recommended" or text.startswith("recommended_")
