from __future__ import annotations

from typing import Any

from archives.mtdp.models import MTDPPackageInput, MTDPRun, RunToken
from mapping.mapping_candidate import MappingCandidate, MappingCandidateSet
from methods.core.method_package import MethodPackage
from mtdp_enrichment.units import default_unit_normaliser
from readiness.readiness_models import MethodInputRequirement, MethodInputsDeclaration


class MappingCandidateDiscovery:
    """Generate package-backed mapping candidates for declared method inputs."""

    def discover(self, *, source: MTDPPackageInput, method_package: MethodPackage) -> dict[str, Any]:
        declaration = MethodInputsDeclaration.from_payload(method_package.method_inputs)
        sets = tuple(
            _candidate_set(requirement, source)
            for requirement in declaration.requirements
        )
        return {
            "schema_id": "method.mapping_candidate_report.v0_1",
            "method_id": method_package.method_id,
            "source_schema_id": source.manifest.get("schema_id") or source.schema.get("schema_id"),
            "summary": {
                "requirement_total": len(sets),
                "resolved_total": sum(1 for item in sets if item.status == "resolved"),
                "ambiguous_total": sum(1 for item in sets if item.status == "ambiguous"),
                "missing_total": sum(1 for item in sets if item.status == "missing"),
            },
            "requirements": [item.to_dict() for item in sets],
        }


def _candidate_set(requirement: MethodInputRequirement, source: MTDPPackageInput) -> MappingCandidateSet:
    if requirement.method_field.startswith("channel."):
        candidates = _channel_candidates(requirement, source)
    else:
        candidates = _field_candidates(requirement, source)
    candidates = tuple(sorted(candidates, key=lambda item: item.confidence, reverse=True))
    return MappingCandidateSet(
        requirement_id=requirement.requirement_id,
        method_field=requirement.method_field,
        source_role=requirement.source_role,
        severity=requirement.severity,
        scope=requirement.scope,
        candidates=candidates,
    )


def _channel_candidates(requirement: MethodInputRequirement, source: MTDPPackageInput) -> list[MappingCandidate]:
    rows: list[MappingCandidate] = []
    first_run = source.runs[0] if source.runs else None
    if first_run is None:
        return rows
    role = requirement.source_role
    for name, channel in first_run.channels.items():
        confidence, reason = _name_confidence(role, name, channel=True)
        if confidence <= 0:
            continue
        rows.append(_channel_candidate(requirement, source, first_run, name, confidence, reason))
    rows.extend(_fallback_channel_candidates(requirement, source, first_run, existing={row.source_name for row in rows}))
    return rows


def _fallback_channel_candidates(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    first_run: MTDPRun,
    *,
    existing: set[str],
) -> list[MappingCandidate]:
    role = requirement.source_role
    compatible = [
        name
        for name, channel in first_run.channels.items()
        if name not in existing and _channel_is_compatible_with_role(role, requirement.expected_unit, name, channel)
    ]
    rows: list[MappingCandidate] = []
    for ordinal, name in enumerate(compatible):
        confidence, reason = _fallback_channel_confidence(role, name, ordinal)
        if confidence <= 0:
            continue
        rows.append(_channel_candidate(requirement, source, first_run, name, confidence, reason))
    return rows


def _channel_candidate(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    first_run: MTDPRun,
    name: str,
    confidence: float,
    reason: str,
) -> MappingCandidate:
    channel = first_run.channels[name]
    return MappingCandidate(
        requirement_id=requirement.requirement_id,
        method_field=requirement.method_field,
        source_role=requirement.source_role,
        severity=requirement.severity,
        scope=requirement.scope,
        source_kind="channel",
        source_name=name,
        source_path=f"channels.{name}",
        confidence=confidence,
        status="candidate",
        unit=channel.unit or "",
        expected_unit=requirement.expected_unit or "",
        coverage=_channel_coverage(source, name),
        example_value=_first_channel_value(first_run, name),
        reason=reason,
    )


def _field_candidates(requirement: MethodInputRequirement, source: MTDPPackageInput) -> list[MappingCandidate]:
    rows: list[MappingCandidate] = []
    role = requirement.source_role
    rows.extend(_run_token_candidates(requirement, source, role))
    existing = {(row.source_kind, row.source_name) for row in rows}
    rows.extend(_dataset_schema_candidates(requirement, source, role, existing=existing))
    return rows


def _run_token_candidates(requirement: MethodInputRequirement, source: MTDPPackageInput, role: str) -> list[MappingCandidate]:
    first_run = source.runs[0] if source.runs else None
    if first_run is None:
        return []
    rows: list[MappingCandidate] = []
    for name, token in first_run.tokens.items():
        confidence, reason = _name_confidence(role, name, channel=False)
        if confidence <= 0:
            confidence, reason = _fallback_field_confidence(requirement, token.unit, source_kind="token")
        if confidence <= 0:
            continue
        rows.append(_token_candidate(requirement, source, name, token, confidence, reason))
    return rows


def _token_candidate(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    name: str,
    token: RunToken,
    confidence: float,
    reason: str,
) -> MappingCandidate:
    return MappingCandidate(
        requirement_id=requirement.requirement_id,
        method_field=requirement.method_field,
        source_role=requirement.source_role,
        severity=requirement.severity,
        scope=requirement.scope,
        source_kind="field",
        source_name=name,
        source_path=f"tokens.{name}",
        confidence=confidence,
        status="candidate",
        unit=token.unit or "",
        expected_unit=requirement.expected_unit or "",
        coverage=_token_coverage(source, name),
        example_value=token.value,
        reason=reason,
    )


def _dataset_schema_candidates(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    role: str,
    *,
    existing: set[tuple[str, str]],
) -> list[MappingCandidate]:
    rows: list[MappingCandidate] = []
    dataset_fields = list(source.schema.get("dataset_fields", []) or [])
    run_fields = list(source.schema.get("run_fields", []) or [])
    fields = dataset_fields + run_fields
    for field in fields:
        if not isinstance(field, dict):
            continue
        field_id = str(field.get("field_id") or field.get("key") or "")
        scope = "dataset" if field in dataset_fields else "field"
        if (scope, field_id) in existing:
            continue
        names = [field_id, str(field.get("role") or ""), str(field.get("report_role") or "")]
        names.extend(str(alias) for alias in field.get("import_aliases", []) or [])
        confidence = max((_schema_field_confidence(role, value) for value in names), default=0.0)
        reason = "schema field/report role match"
        if confidence <= 0:
            confidence, reason = _fallback_field_confidence(
                requirement,
                field.get("standard_unit") or field.get("unit"),
                source_kind=scope,
            )
        if confidence <= 0:
            continue
        rows.append(
            MappingCandidate(
                requirement_id=requirement.requirement_id,
                method_field=requirement.method_field,
                source_role=role,
                severity=requirement.severity,
                scope=requirement.scope,
                source_kind=scope,
                source_name=field_id,
                source_path=_field_source_path(field),
                confidence=confidence,
                status="candidate",
                unit=str(field.get("standard_unit") or field.get("unit") or ""),
                expected_unit=requirement.expected_unit or "",
                coverage=_schema_field_coverage(source, field),
                example_value=_schema_field_example(source, field),
                reason=reason,
            )
        )
    return rows


def _name_confidence(role: str, candidate: str, *, channel: bool) -> tuple[float, str]:
    role_norm = _norm(role)
    candidate_norm = _norm(candidate)
    if role_norm == candidate_norm:
        return 1.0, "exact role/name match"
    if role_norm in candidate_norm or candidate_norm in role_norm:
        return 0.92, "name contains source role"
    if role_norm == "front_strain" and {"front", "strain"} <= set(candidate_norm.split("_")):
        return 0.95, "front strain name match"
    if role_norm == "rear_strain" and {"rear", "strain"} <= set(candidate_norm.split("_")):
        return 0.95, "rear strain name match"
    if channel and role_norm == "load" and "load" in candidate_norm:
        return 0.94, "load channel name match"
    if not channel and role_norm in {"width", "thickness", "gauge_length", "failure_mode", "validity"} and role_norm in candidate_norm:
        return 0.9, "token name match"
    return 0.0, ""


def _fallback_field_confidence(
    requirement: MethodInputRequirement,
    source_unit: str | None,
    *,
    source_kind: str,
) -> tuple[float, str]:
    if not _units_compatible(source_unit, requirement.expected_unit):
        return 0.0, ""
    label = "token" if source_kind == "token" else "schema field"
    return 0.62, f"unit-compatible {label}"


def _channel_is_compatible_with_role(
    role: str,
    expected_unit: str | None,
    name: str,
    channel,
) -> bool:
    role_norm = _norm(role)
    unit = default_unit_normaliser.normalize_unit_text(channel.unit)
    if _units_compatible(unit, expected_unit):
        return True
    candidate_norm = _norm(name)
    if role_norm in {"front_strain", "rear_strain"}:
        return _unit_dimension(unit) == "strain" or "strain" in candidate_norm or "gage" in candidate_norm or "gauge" in candidate_norm
    if role_norm in {"load", "force"}:
        return _unit_dimension(unit) == "force"
    if role_norm in {"extension", "displacement"}:
        return _unit_dimension(unit) == "length"
    if role_norm == "time":
        return _unit_dimension(unit) == "time"
    return False


def _fallback_channel_confidence(role: str, name: str, ordinal: int) -> tuple[float, str]:
    role_norm = _norm(role)
    candidate_norm = _norm(name)
    if role_norm == "front_strain":
        if "front" in candidate_norm:
            return 0.88, "unit-compatible front strain channel"
        if ordinal == 0:
            return 0.82, "unit-compatible strain channel; first strain channel default"
        return 0.66, "unit-compatible strain channel"
    if role_norm == "rear_strain":
        if "rear" in candidate_norm:
            return 0.88, "unit-compatible rear strain channel"
        if ordinal == 1:
            return 0.82, "unit-compatible strain channel; second strain channel default"
        return 0.66, "unit-compatible strain channel"
    if role_norm in {"load", "force"}:
        return 0.78, "unit-compatible force channel"
    if role_norm in {"extension", "displacement"}:
        return 0.72, "unit-compatible length channel"
    if role_norm == "time":
        return 0.72, "unit-compatible time channel"
    return 0.0, ""


def _unit_dimension(unit: str | None) -> str | None:
    return default_unit_normaliser.dimensions.dimension_for_unit(unit)


def _units_compatible(source_unit: str | None, expected_unit: str | None) -> bool:
    unit = default_unit_normaliser.normalize_unit_text(source_unit)
    expected = default_unit_normaliser.normalize_unit_text(expected_unit)
    if not unit or not expected:
        return False
    if unit == expected:
        return True
    dimension = default_unit_normaliser.dimensions.dimension_for_unit(expected)
    return default_unit_normaliser.conversion_factor(unit, expected, dimension=dimension) is not None


def _schema_field_confidence(role: str, candidate: str) -> float:
    role_norm = _norm(role)
    candidate_norm = _norm(candidate)
    if not candidate_norm:
        return 0.0
    if role_norm == candidate_norm:
        return 0.98
    if role_norm in candidate_norm or candidate_norm in role_norm:
        return 0.86
    return 0.0


def _norm(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def _channel_coverage(source: MTDPPackageInput, name: str) -> str:
    present = sum(1 for run in source.runs if run.channel(name) is not None)
    return f"{present}/{len(source.runs)} runs"


def _token_coverage(source: MTDPPackageInput, name: str) -> str:
    present = sum(1 for run in source.runs if run.token(name) is not None)
    return f"{present}/{len(source.runs)} runs"


def _first_channel_value(run: MTDPRun, name: str) -> Any:
    channel = run.channel(name)
    if channel is None:
        return ""
    return next((value for value in channel.values if value is not None), "")


def _field_source_path(field: dict[str, Any]) -> str:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    path = str(storage.get("path") or storage.get("token") or "")
    return f"{location}:{path}" if location or path else str(field.get("field_id") or "")


def _schema_field_coverage(source: MTDPPackageInput, field: dict[str, Any]) -> str:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    if location == "dataset_json":
        return "dataset schema field"
    token = str(storage.get("token") or field.get("field_id") or "")
    if token:
        return _token_coverage(source, token)
    return "schema field"


def _schema_field_example(source: MTDPPackageInput, field: dict[str, Any]) -> Any:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    if location == "dataset_json":
        return _dotted(source.dataset, str(storage.get("path") or ""))
    token = str(storage.get("token") or "")
    if token and source.runs:
        found = source.runs[0].token(token)
        return found.value if found else ""
    return ""


def _dotted(payload: dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict):
            return ""
        cursor = cursor.get(part)
    if isinstance(cursor, dict) and "value" in cursor:
        return cursor.get("value")
    return "" if cursor is None else cursor
