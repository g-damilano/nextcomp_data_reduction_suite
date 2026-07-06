from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


PlotSurface = Literal["audit_report", "test_report", "workbench", "export", "wizard"]
PlotStatus = Literal["rendered", "unavailable", "degraded", "failed"]


@dataclass(frozen=True, slots=True)
class PlotLayerContract:
    layer_id: str
    semantic_role: str
    required: bool = True
    visible_by_default: bool = True
    tooltip_fields: tuple[str, ...] = ()
    encoding_policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "semantic_role": self.semantic_role,
            "required": self.required,
            "visible_by_default": self.visible_by_default,
            "tooltip_fields": list(self.tooltip_fields),
            "encoding_policy": dict(self.encoding_policy),
        }


@dataclass(frozen=True, slots=True)
class PlotQualityReport:
    has_data: bool
    has_required_layers: bool
    axis_labels_present: bool
    units_present: bool
    tooltip_present: bool
    legend_state: str
    clipping_state: str
    annotation_conflicts: list[str] = field(default_factory=list)
    visible_label_suppression: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_data": self.has_data,
            "has_required_layers": self.has_required_layers,
            "axis_labels_present": self.axis_labels_present,
            "units_present": self.units_present,
            "tooltip_present": self.tooltip_present,
            "legend_state": self.legend_state,
            "clipping_state": self.clipping_state,
            "annotation_conflicts": list(self.annotation_conflicts),
            "visible_label_suppression": list(self.visible_label_suppression),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class PlotTheme:
    theme_id: str = "compression_default"
    font: str = "Arial"
    default_width: str | int = "container"
    default_height: int = 300
    axis_label_conventions: dict[str, str] = field(default_factory=dict)
    opacity_conventions: dict[str, float] = field(default_factory=dict)
    status_colors: dict[str, str] = field(default_factory=dict)
    tooltip_conventions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "font": self.font,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "axis_label_conventions": dict(self.axis_label_conventions),
            "opacity_conventions": dict(self.opacity_conventions),
            "status_colors": dict(self.status_colors),
            "tooltip_conventions": dict(self.tooltip_conventions),
        }


@dataclass(frozen=True, slots=True)
class PlotCustomizationProfile:
    theme_id: str = "compression_default"
    width: str | int | None = None
    height: int | None = None
    optional_layers: dict[str, bool] = field(default_factory=dict)
    axis_unit_display: str = "with_units"
    legend_placement: str = "right"
    tooltip_verbosity: str = "standard"
    export_format_preferences: tuple[str, ...] = ("html", "json")
    label_density_policy: str = "suppress_dense_labels"

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "width": self.width,
            "height": self.height,
            "optional_layers": dict(self.optional_layers),
            "axis_unit_display": self.axis_unit_display,
            "legend_placement": self.legend_placement,
            "tooltip_verbosity": self.tooltip_verbosity,
            "export_format_preferences": list(self.export_format_preferences),
            "label_density_policy": self.label_density_policy,
        }


@dataclass(frozen=True, slots=True)
class PlotRequest:
    plot_type: str
    plot_id: str
    title: str = ""
    subtitle: str = ""
    data_payload: dict[str, Any] = field(default_factory=dict)
    evidence_refs: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    theme_id: str = "compression_default"
    layout_policy: dict[str, Any] = field(default_factory=dict)
    quality_policy: dict[str, Any] = field(default_factory=dict)
    interaction_policy: dict[str, Any] = field(default_factory=dict)
    surface_context: PlotSurface = "audit_report"
    method_context: dict[str, Any] | None = None
    operation_context: dict[str, Any] | None = None
    customization: PlotCustomizationProfile | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plot_type": self.plot_type,
            "plot_id": self.plot_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "data_payload": self.data_payload,
            "evidence_refs": dict(self.evidence_refs),
            "units": dict(self.units),
            "theme_id": self.theme_id,
            "layout_policy": dict(self.layout_policy),
            "quality_policy": dict(self.quality_policy),
            "interaction_policy": dict(self.interaction_policy),
            "surface_context": self.surface_context,
            "method_context": self.method_context,
            "operation_context": self.operation_context,
            "customization": self.customization.to_dict() if self.customization else None,
        }


@dataclass(frozen=True, slots=True)
class PlotResult:
    plot_id: str
    plot_type: str
    status: PlotStatus
    spec: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    quality_report: PlotQualityReport | None = None
    evidence_refs: dict[str, str] = field(default_factory=dict)
    data_refs: dict[str, str] = field(default_factory=dict)
    artifact_refs: dict[str, str] = field(default_factory=dict)
    fallback_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plot_id": self.plot_id,
            "plot_type": self.plot_type,
            "status": self.status,
            "spec": self.spec,
            "warnings": list(self.warnings),
            "quality_report": self.quality_report.to_dict() if self.quality_report else None,
            "evidence_refs": dict(self.evidence_refs),
            "data_refs": dict(self.data_refs),
            "artifact_refs": dict(self.artifact_refs),
            "fallback_message": self.fallback_message,
        }
