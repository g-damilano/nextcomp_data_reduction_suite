from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


DEFAULT_SELECTION_SETS: tuple[dict[str, Any], ...] = (
    {"id": "all_runs", "include": "all"},
    {"id": "user_valid_runs", "include_if_not_flagged_by": ["user_validity_invalid"]},
    {"id": "auto_recommended_runs", "include_if_max_severity_below": "review"},
    {"id": "review_required_runs", "include_if_max_severity_equals": "review"},
    {"id": "excluded_runs", "include_if_max_severity_equals": "exclude"},
    {"id": "human_curated_runs", "include": "none"},
)


@dataclass(frozen=True, slots=True)
class AcceptanceRecipe:
    payload: dict[str, Any]

    @classmethod
    def from_method_recipe(cls, recipe: Mapping[str, Any] | None) -> "AcceptanceRecipe":
        payload = recipe.get("acceptance") if isinstance(recipe, Mapping) else None
        return cls(payload if isinstance(payload, dict) else _default_payload())

    @property
    def recipe_id(self) -> str:
        return str(self.payload.get("recipe_id") or "acceptance_v0_1")

    @property
    def default_selection_set(self) -> str:
        return str(self.payload.get("default_selection_set") or "auto_recommended_runs")

    @property
    def flags(self) -> list[dict[str, Any]]:
        flags = self.payload.get("flags", [])
        return [flag for flag in flags if isinstance(flag, dict)] if isinstance(flags, list) else []

    @property
    def statistical_screening(self) -> dict[str, Any]:
        screening = self.payload.get("statistical_screening", {})
        return screening if isinstance(screening, dict) else {}

    @property
    def selection_sets(self) -> list[dict[str, Any]]:
        configured = self.payload.get("selection_sets", [])
        sets = [item for item in configured if isinstance(item, dict)] if isinstance(configured, list) else []
        seen = {str(item.get("id")) for item in sets}
        for item in DEFAULT_SELECTION_SETS:
            if str(item.get("id")) not in seen:
                sets.append(dict(item))
        return sets


def _default_payload() -> dict[str, Any]:
    return {
        "recipe_id": "acceptance_v0_1",
        "default_selection_set": "auto_recommended_runs",
        "flags": [],
        "selection_sets": [dict(item) for item in DEFAULT_SELECTION_SETS],
    }
