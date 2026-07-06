from __future__ import annotations

from typing import Any

from archives.core.layouts import MTDAAlignedLayout, report_member
from methods.core.method_run_service import MethodLoadResult
from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contract


def method_preview_view_model(result: MethodLoadResult) -> dict[str, Any]:
    phases = list(result.phases)
    recipe_steps = list(result.recipe_steps)
    return {
        "schema_name": "method_preview_view_model",
        "version": "0.1.0",
        "page_action_contract": wizard_page_action_contract("method"),
        "method_path": str(result.path),
        "method_id": result.method_id,
        "method_label": result.method_name,
        "version_label": result.version,
        "status": result.status or "",
        "standard_name": result.method_name,
        "standard_reference": result.standard_reference or "",
        "analysis_type": result.analysis_type or "",
        "supported_analysis_types": [result.analysis_type] if result.analysis_type else [],
        "required_inputs": list(result.required_inputs),
        "required_input_count": len(result.required_inputs),
        "expected_outputs": list(result.expected_outputs),
        "expected_output_count": len(result.expected_outputs),
        "declared_outputs": list(result.expected_outputs),
        "method_phases": phases,
        "process_summary": _process_summary(phases),
        "recipe_steps": recipe_steps,
        "recipe_step_count": len(recipe_steps),
        "available_recipes": _available_recipes(phases),
        "surface_outputs": [
            {"surface": "test_report", "member": report_member("test_report.html")},
            {"surface": "audit_report", "member": report_member("audit_report.html")},
            {"surface": "method_development_workbench", "member": f"{MTDAAlignedLayout.method_outputs}#operation_trace"},
            {"surface": "mtda_archive", "member": MTDAAlignedLayout.manifest},
        ],
        "limitations": list(result.limitations),
        "summary_cards": [
            {"label": "Method", "value": result.method_id},
            {"label": "Version", "value": result.version},
            {"label": "Inputs", "value": str(len(result.required_inputs))},
            {"label": "Outputs", "value": str(len(result.expected_outputs))},
        ],
    }


def _process_summary(phases: list[str]) -> list[str]:
    labels = {
        "resolve": "Resolve package channels and metadata into method inputs.",
        "reduce": "Calculate specimen-level curves, metrics, and diagnostics.",
        "validation": "Compare selected outputs with reference values.",
        "acceptance": "Apply inclusion, review, discharge, and selection policies.",
        "report": "Build report-ready evidence from the selected run set.",
    }
    return [labels.get(phase, phase.replace("_", " ").title()) for phase in phases]


def _available_recipes(phases: list[str]) -> list[str]:
    recipes = ["method_manifest", "method_inputs", "resolve_recipe", "reduce_recipe", "audit_recipe"]
    if "validation" in phases:
        recipes.append("validation_recipe")
    if "acceptance" in phases:
        recipes.append("acceptance_recipe")
    if "report" in phases:
        recipes.extend(["report_recipe", "curve_aggregation_policy"])
    return recipes
