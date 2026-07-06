from __future__ import annotations

from typing import Any

from archives.mtdp.models import MTDPPackageInput
from compatibility.compatibility_models import (
    CompatibilityReport,
    CompatibilityRequirement,
    CompatibilityStatus,
)
from methods.core.method_package import MethodPackage
from readiness.readiness_models import MethodInputsDeclaration, MethodInputRequirement


class SchemaMethodCompatibilityChecker:
    """Check whether an MTDP schema can theoretically support a method."""

    def check(self, *, source: MTDPPackageInput, method_package: MethodPackage) -> CompatibilityReport:
        declaration = MethodInputsDeclaration.from_payload(method_package.method_inputs)
        requirements = tuple(
            _requirement_support(requirement, source.schema)
            for requirement in declaration.requirements
        )
        status = _status(requirements)
        return CompatibilityReport(
            status=status,
            method_id=method_package.method_id,
            schema_id=str(source.manifest.get("schema_id") or source.schema.get("schema_id") or ""),
            schema_version=str(source.manifest.get("schema_version") or source.schema.get("version") or ""),
            requirements=requirements,
        )


def _requirement_support(requirement: MethodInputRequirement, schema: dict[str, Any]) -> CompatibilityRequirement:
    evidence: list[str] = []
    support_kind = ""
    if requirement.method_field.startswith("channel."):
        supported, support_kind, evidence = _channel_support(requirement, schema)
    else:
        supported, support_kind, evidence = _field_support(requirement, schema)
    message = (
        f"Schema can support source role '{requirement.source_role}' via {support_kind}."
        if supported
        else f"Schema does not declare support for source role '{requirement.source_role}'."
    )
    return CompatibilityRequirement(
        requirement_id=requirement.requirement_id,
        method_field=requirement.method_field,
        source_role=requirement.source_role,
        severity=requirement.severity,
        scope=requirement.scope,
        compatible=supported,
        support_kind=support_kind if supported else "missing",
        evidence=tuple(evidence),
        message=message,
    )


def _channel_support(requirement: MethodInputRequirement, schema: dict[str, Any]) -> tuple[bool, str, list[str]]:
    columns = ((schema.get("data_table") or {}).get("columns") or [])
    role = requirement.source_role.casefold()
    for column in columns:
        if not isinstance(column, dict):
            continue
        family = str(column.get("family") or "").casefold()
        label = str(column.get("label") or "").casefold()
        if role == family or role in label or family in role:
            return True, "data_table.column_family", [f"data_table.columns.{family}"]
        if "strain" in role and family == "strain":
            return True, "data_table.repeatable_strain_family", ["data_table.columns.strain"]
    return False, "", []


def _field_support(requirement: MethodInputRequirement, schema: dict[str, Any]) -> tuple[bool, str, list[str]]:
    fields = list(schema.get("dataset_fields", []) or []) + list(schema.get("run_fields", []) or [])
    role = requirement.source_role.casefold()
    for field in fields:
        if not isinstance(field, dict):
            continue
        keys = {
            str(field.get("field_id") or "").casefold(),
            str(field.get("key") or "").casefold(),
            str(field.get("role") or "").casefold(),
            str(field.get("report_role") or "").casefold(),
            str(field.get("suggestion_key") or "").casefold(),
        }
        keys.update(str(alias).casefold() for alias in field.get("import_aliases", []) or [])
        if role in keys:
            field_id = str(field.get("field_id") or field.get("key") or requirement.source_role)
            return True, "schema_field", [field_id]
    if requirement.scope == "per_dataset" and any(
        isinstance(field, dict) and str(field.get("report_role") or "").casefold() == role
        for field in schema.get("dataset_fields", []) or []
    ):
        return True, "dataset_field_role", [requirement.source_role]
    return False, "", []


def _status(requirements: tuple[CompatibilityRequirement, ...]) -> CompatibilityStatus:
    critical_unsupported = [
        row for row in requirements
        if row.severity == "execution_critical" and not row.compatible
    ]
    if critical_unsupported:
        return CompatibilityStatus.SCHEMA_EXTENSION_REQUIRED
    if any(not row.compatible for row in requirements):
        return CompatibilityStatus.COMPATIBLE_WITH_WARNINGS
    return CompatibilityStatus.COMPATIBLE
