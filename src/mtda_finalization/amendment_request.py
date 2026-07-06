from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AmendmentRequest:
    report_overrides: tuple[dict[str, Any], ...] = ()
    human_decisions: tuple[dict[str, Any], ...] = ()
    reviewer: str = ""
    reason: str = ""
    reviewer_notes: tuple[str, ...] = ()
    method_package_changes: dict[str, Any] = field(default_factory=dict)
    mapping_profile_changes: dict[str, Any] = field(default_factory=dict)
    input_mtdp_changes: dict[str, Any] = field(default_factory=dict)
    calculation_input_changes: dict[str, Any] = field(default_factory=dict)
    operation_policy_changes: dict[str, Any] = field(default_factory=dict)
    validation_reference_changes: dict[str, Any] = field(default_factory=dict)
    source_surface: str = "mtda_finalization"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AmendmentRequest":
        return cls(
            report_overrides=tuple(_as_rows(payload.get("report_overrides"))),
            human_decisions=tuple(_as_rows(payload.get("human_decisions"))),
            reviewer=str(payload.get("reviewer") or ""),
            reason=str(payload.get("reason") or ""),
            reviewer_notes=tuple(str(item) for item in payload.get("reviewer_notes", []) or []),
            method_package_changes=dict(payload.get("method_package_changes") or {}),
            mapping_profile_changes=dict(payload.get("mapping_profile_changes") or {}),
            input_mtdp_changes=dict(payload.get("input_mtdp_changes") or {}),
            calculation_input_changes=dict(payload.get("calculation_input_changes") or {}),
            operation_policy_changes=dict(payload.get("operation_policy_changes") or {}),
            validation_reference_changes=dict(payload.get("validation_reference_changes") or {}),
            source_surface=str(payload.get("source_surface") or "mtda_finalization"),
        )

    def amendment_classes(self) -> tuple[str, ...]:
        classes: list[str] = []
        if self.report_overrides:
            classes.append("report_only")
        if self.human_decisions:
            classes.append("selection_only")
        if self.reviewer_notes or self.reviewer or self.reason:
            classes.append("finalization_note")
        return tuple(classes)

    def disallowed_changes(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "method_package_changes": self.method_package_changes,
                "mapping_profile_changes": self.mapping_profile_changes,
                "input_mtdp_changes": self.input_mtdp_changes,
                "calculation_input_changes": self.calculation_input_changes,
                "operation_policy_changes": self.operation_policy_changes,
                "validation_reference_changes": self.validation_reference_changes,
            }.items()
            if value
        }


def _as_rows(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, dict):
        if isinstance(value.get("overrides"), list):
            value = value["overrides"]
        elif isinstance(value.get("decisions"), list):
            value = value["decisions"]
        else:
            value = [value]
    if not isinstance(value, list):
        raise ValueError("Amendment payload must be an object or list of objects.")
    return [dict(item) for item in value if isinstance(item, dict)]
