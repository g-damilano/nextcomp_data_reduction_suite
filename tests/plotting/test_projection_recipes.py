from __future__ import annotations

from plotting.recipes.loader import load_recipe_catalog
from plotting.recipes.validator import validate_recipe


EXPECTED_PRODUCTION_RECIPES = {
    "stress_strain_reduction",
    "bending_evidence",
    "aggregate_curve_family",
    "curve_shape_distance_ranking",
    "curve_shape_residuals",
    "aggregate_stress_strain_mean_variability",
    "failure_analysis_bending_distribution",
    "audit_stress_strain_family",
    "audit_modulus_window",
    "audit_bending_trace",
    "mtda_run_compact_stress_strain_evidence",
    "mtda_dataset_aggregate_compact_package",
}


def test_projection_recipe_catalog_loads_expected_production_recipes() -> None:
    catalog = load_recipe_catalog()

    assert EXPECTED_PRODUCTION_RECIPES <= set(catalog)
    assert all(recipe["production_state"] == "production" for recipe in catalog.values())


def test_projection_recipes_satisfy_minimal_contract() -> None:
    catalog = load_recipe_catalog()

    for projection_id, recipe in catalog.items():
        assert validate_recipe(recipe) == [], projection_id
        assert recipe["projection_id"] == projection_id
        assert str(recipe["golden_id"]).startswith("golden_")
        assert recipe["semantic_contract"]["layers"]
        assert recipe["artifact_contract"]["primary_artifacts"]
