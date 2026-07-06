from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    reference_field: str
    computed_field: str
    source: str
    unit: str | None = None
    computed_scale: float = 1.0
    tolerance_abs: float | None = None
    tolerance_rel: float | None = None
    severity: str = "fail"
    recipe_step_id: str | None = None
    description: str | None = None

    @classmethod
    def from_recipe(cls, payload: dict[str, Any]) -> "ValidationCheck":
        reference_field = str(payload.get("reference_field") or payload.get("field") or "").strip()
        computed_field = str(payload.get("computed_field") or reference_field).strip()
        return cls(
            reference_field=reference_field,
            computed_field=computed_field,
            source=str(payload.get("source") or "specimen_results").strip(),
            unit=_optional_text(payload.get("unit")),
            computed_scale=float(payload.get("computed_scale", 1.0)),
            tolerance_abs=_optional_float(payload.get("tolerance_abs")),
            tolerance_rel=_optional_float(payload.get("tolerance_rel")),
            severity=str(payload.get("severity") or "fail").strip(),
            recipe_step_id=_optional_text(payload.get("recipe_step_id")),
            description=_optional_text(payload.get("description")),
        )


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
