from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.report_recipe_loader import load_report_recipe


def test_iso14126_report_recipe_loads_block_style() -> None:
    recipe = load_report_recipe(ROOT / "src" / "methods" / "iso14126" / "report_recipe.yaml")

    assert recipe["schema_version"] == "report.recipe.v0_2"
    assert recipe["recipe_id"] == "iso14126_report_v0_2"
    assert len(recipe["sections"]) == 12
    assert all("blocks" in section for section in recipe["sections"])
    aggregate = next(section for section in recipe["sections"] if section["id"] == "aggregated_results")
    assert any(block["type"] == "vega_plot" and block["provider"] == "aligned_curves" for block in aggregate["blocks"])
