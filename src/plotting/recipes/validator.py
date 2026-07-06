from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REQUIRED_RECIPE_FIELDS = (
    "projection_id",
    "golden_id",
    "version",
    "plot_type",
    "production_state",
    "surface_profiles",
    "data_contract",
    "transform_ids",
    "semantic_contract",
    "quality_contract",
    "staleness_contract",
    "artifact_contract",
    "migration_metadata",
)

VALID_PRODUCTION_STATES = {
    "production",
    "support",
    "diagnostic",
    "legacy",
    "stale",
    "unknown",
    "quarantined",
    "removal_candidate",
}


class RecipeValidationError(ValueError):
    """Raised when a projection recipe does not satisfy the local contract."""


def validate_recipe(recipe: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_RECIPE_FIELDS:
        if field not in recipe:
            errors.append(f"missing required field: {field}")

    projection_id = recipe.get("projection_id")
    if not isinstance(projection_id, str) or not projection_id.strip():
        errors.append("projection_id must be a non-empty string")

    golden_id = recipe.get("golden_id")
    if not isinstance(golden_id, str) or not golden_id.strip():
        errors.append("golden_id must be a non-empty string")

    version = recipe.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("version must be a non-empty string")

    plot_type = recipe.get("plot_type")
    if not isinstance(plot_type, str) or not plot_type.strip():
        errors.append("plot_type must be a non-empty string")

    production_state = recipe.get("production_state")
    if production_state not in VALID_PRODUCTION_STATES:
        errors.append(
            "production_state must be one of: "
            + ", ".join(sorted(VALID_PRODUCTION_STATES))
        )

    _expect_list(recipe, "surface_profiles", errors)
    _expect_list(recipe, "transform_ids", errors)
    for object_field in (
        "data_contract",
        "semantic_contract",
        "quality_contract",
        "staleness_contract",
        "artifact_contract",
        "migration_metadata",
    ):
        _expect_mapping(recipe, object_field, errors)

    semantic_contract = recipe.get("semantic_contract")
    if isinstance(semantic_contract, Mapping):
        layers = semantic_contract.get("layers")
        if not isinstance(layers, list) or not layers:
            errors.append("semantic_contract.layers must be a non-empty list")
        elif any(not isinstance(layer, Mapping) or not layer.get("layer_id") for layer in layers):
            errors.append("semantic_contract.layers entries must declare layer_id")

    data_contract = recipe.get("data_contract")
    if isinstance(data_contract, Mapping):
        if not data_contract.get("source_tables"):
            errors.append("data_contract.source_tables must be declared")

    return errors


def require_valid_recipe(recipe: Mapping[str, Any]) -> None:
    errors = validate_recipe(recipe)
    if errors:
        projection_id = recipe.get("projection_id", "<unknown>")
        raise RecipeValidationError(f"Invalid projection recipe {projection_id}: " + "; ".join(errors))


def _expect_list(recipe: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if field in recipe and not isinstance(recipe.get(field), list):
        errors.append(f"{field} must be a list")


def _expect_mapping(recipe: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if field in recipe and not isinstance(recipe.get(field), Mapping):
        errors.append(f"{field} must be an object")
