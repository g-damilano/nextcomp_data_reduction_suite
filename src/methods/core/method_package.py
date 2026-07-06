from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from methods.core.recipe_loader import load_yaml


@dataclass(frozen=True, slots=True)
class MethodPackage:
    root: Path
    manifest: dict[str, Any]
    resolve_recipe: dict[str, Any]
    reduce_recipe: dict[str, Any]
    audit_recipe: dict[str, Any]
    validation_recipe: dict[str, Any]
    acceptance_recipe: dict[str, Any]
    method_inputs: dict[str, Any]
    report_recipe: dict[str, Any]
    curve_aggregation_policy: dict[str, Any]
    curve_family_acceptance_recipe: dict[str, Any]

    @classmethod
    def load(cls, root: str | Path) -> "MethodPackage":
        path = Path(root)
        return cls(
            root=path,
            manifest=load_yaml(path / "method_manifest.yaml"),
            resolve_recipe=load_yaml(path / "resolve_recipe.yaml"),
            reduce_recipe=load_yaml(path / "reduce_recipe.yaml"),
            audit_recipe=load_yaml(path / "audit_recipe.yaml"),
            validation_recipe=load_yaml(path / "validation_recipe.yaml") if (path / "validation_recipe.yaml").exists() else {},
            acceptance_recipe=load_yaml(path / "acceptance_recipe.yaml") if (path / "acceptance_recipe.yaml").exists() else {},
            method_inputs=load_yaml(path / "method_inputs.yaml") if (path / "method_inputs.yaml").exists() else {},
            report_recipe=load_yaml(path / "report_recipe.yaml") if (path / "report_recipe.yaml").exists() else {},
            curve_aggregation_policy=load_yaml(path / "curve_aggregation_policy.yaml") if (path / "curve_aggregation_policy.yaml").exists() else {},
            curve_family_acceptance_recipe=load_yaml(path / "curve_family_acceptance_recipe.yaml") if (path / "curve_family_acceptance_recipe.yaml").exists() else {},
        )

    @property
    def method_id(self) -> str:
        return str(self.manifest.get("method_id", self.root.name))

    @property
    def version(self) -> str:
        return str(self.manifest.get("version", "0.0.0"))

    @property
    def name(self) -> str:
        return str(self.manifest.get("method_name", self.method_id))

    def recipe_files(self) -> list[Path]:
        names = [
            "method_manifest.yaml",
            "resolve_recipe.yaml",
            "reduce_recipe.yaml",
            "audit_recipe.yaml",
            "validation_recipe.yaml",
            "acceptance_recipe.yaml",
            "method_inputs.yaml",
            "bending_assessment_policy.yaml",
            "report_recipe.yaml",
            "curve_aggregation_policy.yaml",
            "curve_family_acceptance_recipe.yaml",
            "export_recipe.yaml",
            "plot_style_recipe.yaml",
        ]
        return [self.root / name for name in names if (self.root / name).exists()]
