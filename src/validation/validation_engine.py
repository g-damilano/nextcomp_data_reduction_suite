from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from archives.mtdp.models import MTDPPackageInput
from methods.core.method_package import MethodPackage
from validation.reference_values import ReferenceValue, ReferenceValueSet
from validation.tolerance_policy import TolerancePolicy
from validation.validation_check import ValidationCheck
from validation.validation_report import ValidationReport, ValidationResult


class MethodValidationEngine:
    """Reference-value validator for method-run outputs."""

    def validate(
        self,
        *,
        source: MTDPPackageInput,
        method_package: MethodPackage,
        mapping: dict[str, Any],
        specimen_results: list[dict[str, Any]],
        curve_family: list[dict[str, Any]],
        operation_log: list[dict[str, Any]],
    ) -> ValidationReport:
        recipe = _validation_recipe(method_package)
        reference_values = _load_reference_values(recipe, mapping, method_package, source)
        checks = _checks_by_reference_field(recipe)
        specimen_by_run = {str(row.get("run_id")): row for row in specimen_results}
        curves_by_run = _group_curves_by_run(curve_family)
        results: list[ValidationResult] = []
        for reference in reference_values.values:
            check = checks.get(reference.field)
            if check is None:
                results.append(_not_applicable(method_package, reference, "No validation recipe check is declared for this reference field."))
                continue
            computed_value = _computed_value(check, reference, specimen_by_run, curves_by_run)
            tolerance_abs = reference.tolerance_abs if reference.tolerance_abs is not None else check.tolerance_abs
            tolerance_rel = reference.tolerance_rel if reference.tolerance_rel is not None else check.tolerance_rel
            policy = TolerancePolicy(tolerance_abs=tolerance_abs, tolerance_rel=tolerance_rel, severity=check.severity)
            status, difference_abs, difference_rel = policy.evaluate(computed_value, reference.reference_value)
            operation = _find_operation(operation_log, reference.run_id, check)
            message = _message(status, check, computed_value, reference.reference_value)
            results.append(
                ValidationResult(
                    check_id=_check_id(reference),
                    run_id=reference.run_id,
                    field=reference.field,
                    point_index=reference.point_index,
                    computed_value=computed_value,
                    reference_value=reference.reference_value,
                    unit=check.unit or reference.unit,
                    difference_abs=difference_abs,
                    difference_rel=difference_rel,
                    tolerance_abs=tolerance_abs,
                    tolerance_rel=tolerance_rel,
                    status=status,
                    severity=check.severity,
                    message=message,
                    recipe_step_id=check.recipe_step_id or _operation_value(operation, "recipe_step_id"),
                    operation_id=_operation_value(operation, "operation_id"),
                    reference_source=reference.source,
                    note=reference.note or check.description,
                )
            )
        return ValidationReport(
            method_id=method_package.method_id,
            source_mtdp=str(source.path),
            mapping_profile=str(mapping.get("mapping_id")) if mapping.get("mapping_id") else None,
            reference_values=reference_values,
            checks=tuple(results),
        )


def _validation_recipe(method_package: MethodPackage) -> dict[str, Any]:
    recipe = method_package.validation_recipe.get("validation") if hasattr(method_package, "validation_recipe") else None
    return recipe if isinstance(recipe, dict) else {}


def _checks_by_reference_field(recipe: Mapping[str, Any]) -> dict[str, ValidationCheck]:
    payload = recipe.get("checks", ())
    if not isinstance(payload, list):
        return {}
    checks = [ValidationCheck.from_recipe(item) for item in payload if isinstance(item, dict)]
    return {check.reference_field: check for check in checks if check.reference_field}


def _load_reference_values(
    recipe: Mapping[str, Any],
    mapping: Mapping[str, Any],
    method_package: MethodPackage,
    source: MTDPPackageInput,
) -> ReferenceValueSet:
    path_text = _reference_path_text(recipe, mapping)
    if not path_text:
        return ReferenceValueSet.empty()
    path = _resolve_reference_path(path_text, method_package, source)
    if path is None:
        return ReferenceValueSet.empty()
    return ReferenceValueSet.from_csv(path)


def _reference_path_text(recipe: Mapping[str, Any], mapping: Mapping[str, Any]) -> str | None:
    validation_mapping = mapping.get("validation")
    if isinstance(validation_mapping, Mapping):
        path = validation_mapping.get("reference_values_path")
        if path:
            return str(path)
    reference_config = recipe.get("reference_values")
    if isinstance(reference_config, Mapping) and reference_config.get("path"):
        return str(reference_config.get("path"))
    return None


def _resolve_reference_path(path_text: str, method_package: MethodPackage, source: MTDPPackageInput) -> Path | None:
    candidate = Path(path_text)
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.extend(
            [
                method_package.root / candidate,
                source.path.parent / candidate,
                Path.cwd() / candidate,
            ]
        )
    for path in candidates:
        if path.exists():
            return path
    return None


def _group_curves_by_run(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("run_id")), []).append(row)
    return grouped


def _computed_value(
    check: ValidationCheck,
    reference: ReferenceValue,
    specimen_by_run: Mapping[str, Mapping[str, Any]],
    curves_by_run: Mapping[str, list[Mapping[str, Any]]],
) -> float | None:
    if check.source == "specimen_results":
        row = specimen_by_run.get(reference.run_id)
        value = row.get(check.computed_field) if row else None
    elif check.source == "curve_family":
        rows = curves_by_run.get(reference.run_id, [])
        if reference.point_index is None or reference.point_index >= len(rows):
            value = None
        else:
            value = rows[reference.point_index].get(check.computed_field)
    else:
        value = None
    numeric = _as_float(value)
    return None if numeric is None else numeric * check.computed_scale


def _find_operation(
    operation_log: list[dict[str, Any]],
    run_id: str,
    check: ValidationCheck,
) -> dict[str, Any] | None:
    for record in reversed(operation_log):
        if record.get("run_id") != run_id:
            continue
        if check.recipe_step_id and record.get("recipe_step_id") == check.recipe_step_id:
            return record
        outputs = record.get("outputs")
        if isinstance(outputs, Mapping) and check.computed_field in outputs:
            return record
    return None


def _not_applicable(method_package: MethodPackage, reference: ReferenceValue, message: str) -> ValidationResult:
    return ValidationResult(
        check_id=_check_id(reference),
        run_id=reference.run_id,
        field=reference.field,
        point_index=reference.point_index,
        computed_value=None,
        reference_value=reference.reference_value,
        unit=reference.unit,
        difference_abs=None,
        difference_rel=None,
        tolerance_abs=reference.tolerance_abs,
        tolerance_rel=reference.tolerance_rel,
        status="not_applicable",
        severity="warn",
        message=message,
        reference_source=reference.source,
        note=f"Method {method_package.method_id}",
    )


def _message(status: str, check: ValidationCheck, computed: float | None, reference: float | None) -> str:
    if computed is None:
        return f"Computed value for {check.computed_field} is missing."
    if status == "pass":
        return "Computed value is within tolerance."
    return f"Computed value {computed} differs from reference {reference}."


def _check_id(reference: ReferenceValue) -> str:
    suffix = "" if reference.point_index is None else f":{reference.point_index}"
    return f"{reference.run_id}:{reference.field}{suffix}"


def _operation_value(operation: Mapping[str, Any] | None, key: str) -> str | None:
    if not operation:
        return None
    value = operation.get(key)
    return str(value) if value else None


def _as_float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
