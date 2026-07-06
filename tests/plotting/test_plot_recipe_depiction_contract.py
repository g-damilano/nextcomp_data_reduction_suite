from __future__ import annotations

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_iso14126_plot_recipe_declares_depiction_only_data_contract() -> None:
    recipe_path = ROOT / "src" / "methods" / "iso14126" / "plot_style_recipe.yaml"
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))

    contract = recipe["data_contract"]
    stress_contract = contract["allowed_data_products"]["stress_strain_reduction"]

    assert contract["agency"] == "depiction_only"
    assert stress_contract["order_by"] == "point_index"
    assert stress_contract["required"] == ["bounded_stress_strain_curve"]
    assert {
        "boundary_reselection",
        "max_point_recalculation",
        "failure_marker_recalculation",
        "post_peak_derivation_from_raw_rows",
        "downsampling",
        "smoothing",
        "interpolation",
    } <= set(stress_contract["forbidden_transforms"])
