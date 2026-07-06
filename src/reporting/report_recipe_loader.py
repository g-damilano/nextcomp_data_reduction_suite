from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_report_recipe(path: str | Path) -> dict[str, Any]:
    recipe_path = Path(path)
    if not recipe_path.exists():
        return {}
    payload = yaml.safe_load(recipe_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Report recipe must contain an object: {recipe_path}")
    return payload

