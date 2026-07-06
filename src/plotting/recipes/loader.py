from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from plotting.recipes.validator import require_valid_recipe


def catalog_dir() -> Path:
    return Path(__file__).resolve().parent / "catalog"


def load_recipe(path: str | Path) -> dict[str, Any]:
    recipe_path = Path(path)
    loaded = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Projection recipe is not a mapping: {recipe_path}")
    require_valid_recipe(loaded)
    return loaded


def load_recipe_catalog(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    root = Path(path) if path is not None else catalog_dir()
    catalog: dict[str, dict[str, Any]] = {}
    for recipe_path in sorted(root.glob("*.yaml")):
        recipe = load_recipe(recipe_path)
        projection_id = str(recipe["projection_id"])
        if projection_id in catalog:
            raise ValueError(f"Duplicate projection recipe id: {projection_id}")
        catalog[projection_id] = recipe
    return catalog
