from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from archives.mtdp.models import MTDPPackageInput, MTDPRun, RunChannel, RunToken
from methods.core.method_package import MethodPackage
from readiness.readiness_models import (
    MethodInputsDeclaration,
    MethodInputRequirement,
    ReadinessStatus,
    ResolvedInput,
)
from readiness.readiness_report import ReadinessReport


class MethodReadinessError(RuntimeError):
    def __init__(self, report: ReadinessReport) -> None:
        self.report = report
        super().__init__(f"Method package is not ready: {report.status.value}")


class ReadinessChecker:
    """Check concrete MTDP package readiness for a selected method and mapping."""

    def check(
        self,
        *,
        source: MTDPPackageInput,
        method_package: MethodPackage,
        mapping: Mapping[str, Any] | None,
    ) -> ReadinessReport:
        mapping_payload = mapping if isinstance(mapping, Mapping) else {}
        declaration = MethodInputsDeclaration.from_payload(method_package.method_inputs)
        if not declaration.requirements:
            return ReadinessReport.empty(
                method_id=method_package.method_id,
                schema_id=_schema_id(source),
                mapping_id=_mapping_id(mapping_payload),
            )
        records: list[ResolvedInput] = []
        warnings: list[str] = []
        for requirement in declaration.requirements:
            if not _requirement_applies(requirement, mapping_payload):
                continue
            records.extend(_evaluate_requirement(requirement, source, mapping_payload))
        status = _status(records)
        if status == ReadinessStatus.READY_WITH_WARNINGS:
            warnings.append("Report-completeness or analysis-warning inputs are missing.")
        return ReadinessReport(
            status=status,
            method_id=method_package.method_id,
            schema_id=_schema_id(source),
            mapping_id=_mapping_id(mapping_payload),
            requirements=tuple(records),
            warnings=tuple(warnings),
        )


def _evaluate_requirement(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    mapping: Mapping[str, Any],
) -> list[ResolvedInput]:
    source_kind, mapped_source = _resolve_mapping(requirement, mapping, source)
    if not mapped_source:
        records: list[ResolvedInput] = []
        for run in _runs_for_scope(source, requirement):
            records.append(
                _record(
                    requirement,
                    run_id=run.run_id if run is not None else None,
                    mapped_source=None,
                    source_kind=source_kind,
                    status="mapping_missing",
                    value_state="mapping_missing",
                    message=f"Mapping does not define source role '{requirement.source_role}'.",
                )
            )
        return records
    if requirement.scope == "per_dataset":
        return [_evaluate_dataset_requirement(requirement, source, mapped_source, source_kind)]
    if requirement.scope == "per_package":
        return [_evaluate_package_requirement(requirement, source, mapped_source, source_kind)]
    return [
        _evaluate_run_requirement(requirement, run, mapped_source, source_kind)
        for run in source.runs
    ]


def _evaluate_run_requirement(
    requirement: MethodInputRequirement,
    run: MTDPRun,
    mapped_source: str,
    source_kind: str,
) -> ResolvedInput:
    if source_kind == "channel":
        channel = run.channel(mapped_source)
        if channel is None:
            return _record(
                requirement,
                run_id=run.run_id,
                mapped_source=mapped_source,
                source_kind=source_kind,
                status="missing",
                value_state="missing",
                message=f"Run {run.run_id} does not contain channel '{mapped_source}'.",
            )
        return _channel_record(requirement, run.run_id, mapped_source, channel)
    token = run.token(mapped_source)
    if token is None:
        return _record(
            requirement,
            run_id=run.run_id,
            mapped_source=mapped_source,
            source_kind=source_kind,
            status="missing",
            value_state="missing",
            message=f"Run {run.run_id} does not contain token '{mapped_source}'.",
        )
    return _token_record(requirement, run.run_id, mapped_source, token)


def _evaluate_dataset_requirement(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    mapped_source: str,
    source_kind: str,
) -> ResolvedInput:
    value, actual_source = _dataset_value_for_requirement(source, requirement, mapped_source)
    if _is_empty(value):
        return _record(
            requirement,
            run_id=None,
            mapped_source=mapped_source,
            source_kind=source_kind,
            status="missing",
            value_state="missing",
            message=f"Dataset value '{mapped_source}' is missing.",
        )
    return _record(
        requirement,
        run_id=None,
        mapped_source=actual_source,
        source_kind=source_kind,
        status="pass",
        value_state="present",
        message=f"Dataset value '{actual_source}' found.",
        value_preview=value,
    )


def _evaluate_package_requirement(
    requirement: MethodInputRequirement,
    source: MTDPPackageInput,
    mapped_source: str,
    source_kind: str,
) -> ResolvedInput:
    value = source.manifest.get(mapped_source) or source.schema.get(mapped_source)
    if _is_empty(value):
        return _record(
            requirement,
            run_id=None,
            mapped_source=mapped_source,
            source_kind=source_kind,
            status="missing",
            value_state="missing",
            message=f"Package value '{mapped_source}' is missing.",
        )
    return _record(
        requirement,
        run_id=None,
        mapped_source=mapped_source,
        source_kind=source_kind,
        status="pass",
        value_state="present",
        message=f"Package value '{mapped_source}' found.",
        value_preview=value,
    )


def _channel_record(
    requirement: MethodInputRequirement,
    run_id: str,
    mapped_source: str,
    channel: RunChannel,
) -> ResolvedInput:
    present_values = [value for value in channel.values if value is not None]
    if not present_values:
        return _record(
            requirement,
            run_id=run_id,
            mapped_source=mapped_source,
            source_kind="channel",
            status="empty",
            value_state="empty",
            unit=channel.unit,
            message=f"Channel '{mapped_source}' contains no numeric values.",
        )
    status = "pass"
    message = f"Channel '{mapped_source}' found."
    if requirement.expected_unit and channel.unit and not _units_compatible(requirement.expected_unit, channel.unit):
        status = "unit_warning" if requirement.severity != "execution_critical" else "pass"
        message = f"Channel '{mapped_source}' unit is '{channel.unit}', expected '{requirement.expected_unit}'."
    return _record(
        requirement,
        run_id=run_id,
        mapped_source=mapped_source,
        source_kind="channel",
        status=status,
        value_state="present",
        unit=channel.unit,
        message=message,
        value_preview={"point_count": channel.point_count, "first_present": present_values[0]},
    )


def _token_record(
    requirement: MethodInputRequirement,
    run_id: str,
    mapped_source: str,
    token: RunToken,
) -> ResolvedInput:
    if _is_empty(token.value):
        return _record(
            requirement,
            run_id=run_id,
            mapped_source=mapped_source,
            source_kind="field",
            status="empty",
            value_state="empty",
            unit=token.unit,
            message=f"Token '{mapped_source}' is empty.",
        )
    status = "pass"
    message = f"Token '{mapped_source}' found."
    if requirement.expected_unit and token.unit and not _units_compatible(requirement.expected_unit, token.unit):
        status = "unit_warning" if requirement.severity != "execution_critical" else "pass"
        message = f"Token '{mapped_source}' unit is '{token.unit}', expected '{requirement.expected_unit}'."
    return _record(
        requirement,
        run_id=run_id,
        mapped_source=mapped_source,
        source_kind="field",
        status=status,
        value_state="present",
        unit=token.unit,
        message=message,
        value_preview=token.value,
    )


def _record(
    requirement: MethodInputRequirement,
    *,
    run_id: str | None,
    mapped_source: str | None,
    source_kind: str | None,
    status: str,
    value_state: str,
    message: str,
    unit: str | None = None,
    value_preview: Any = None,
) -> ResolvedInput:
    return ResolvedInput(
        requirement_id=requirement.requirement_id,
        method_field=requirement.method_field,
        source_role=requirement.source_role,
        severity=requirement.severity,
        scope=requirement.scope,
        run_id=run_id,
        mapped_source=mapped_source,
        status=status,
        value_state=value_state,
        unit=unit,
        expected_unit=requirement.expected_unit,
        message=message,
        required_for=requirement.required_for,
        value_preview=value_preview,
        source_kind=source_kind,
    )


def _resolve_mapping(
    requirement: MethodInputRequirement,
    mapping: Mapping[str, Any],
    source: MTDPPackageInput | None = None,
) -> tuple[str, str | None]:
    if _role_section(requirement, "channel"):
        return "channel", _mapping_lookup(mapping, "channels", requirement.source_role)
    if _role_section(requirement, "field"):
        mapped = _mapping_lookup(mapping, "fields", requirement.source_role)
        if requirement.scope in {"per_dataset", "per_package"}:
            return "dataset", mapped or _dataset_key(requirement, source)
        return "field", mapped
    channel = _mapping_lookup(mapping, "channels", requirement.source_role)
    if channel:
        return "channel", channel
    field = _mapping_lookup(mapping, "fields", requirement.source_role)
    if field:
        return "field", field
    if requirement.scope in {"per_dataset", "per_package"}:
        return "dataset", _mapping_lookup(mapping, "fields", requirement.source_role) or _dataset_key(requirement, source)
    return "field", None


def _role_section(requirement: MethodInputRequirement, section: str) -> bool:
    if section == "channel":
        return requirement.method_field.startswith("channel.")
    return requirement.method_field.startswith(("specimen.", "report."))


def _mapping_lookup(mapping: Mapping[str, Any], section: str, key: str) -> str | None:
    payload = mapping.get(section, {})
    if not isinstance(payload, Mapping):
        return None
    value = payload.get(key)
    if isinstance(value, Mapping):
        if str(value.get("status") or "").casefold() in {"ambiguous", "unresolved"}:
            return None
        value = value.get("source") or value.get("field") or value.get("name") or value.get("token") or value.get("channel")
    text = str(value or "").strip()
    return text or None


def _dataset_key(requirement: MethodInputRequirement, source: MTDPPackageInput | None = None) -> str:
    field = _schema_dataset_field_for_requirement(source, requirement)
    if field is not None:
        storage = field.get("storage") if isinstance(field.get("storage"), Mapping) else {}
        path = storage.get("path") if isinstance(storage, Mapping) else None
        return str(path or field.get("field_id") or requirement.source_role)
    return requirement.source_role


def _dataset_value_for_requirement(
    source: MTDPPackageInput,
    requirement: MethodInputRequirement,
    mapped_source: str,
) -> tuple[Any, str]:
    candidates = _dataset_value_candidates(source, requirement, mapped_source)
    for candidate in candidates:
        value = _dataset_value(source.dataset, candidate)
        if not _is_empty(value):
            return value, candidate
    return None, mapped_source


def _dataset_value_candidates(
    source: MTDPPackageInput,
    requirement: MethodInputRequirement,
    mapped_source: str,
) -> tuple[str, ...]:
    candidates: list[str] = []
    for item in (mapped_source, requirement.source_role, requirement.method_field):
        _append_unique(candidates, item)
    for field in _schema_dataset_fields(source):
        if not _field_matches_requirement(field, requirement):
            continue
        storage = field.get("storage") if isinstance(field.get("storage"), Mapping) else {}
        if isinstance(storage, Mapping):
            _append_unique(candidates, storage.get("path"))
        _append_unique(candidates, field.get("field_id"))
        _append_unique(candidates, field.get("role"))
        _append_unique(candidates, field.get("report_role"))
        _append_unique(candidates, field.get("method_role"))
        for alias in field.get("import_aliases", ()) or ():
            if isinstance(alias, Mapping):
                _append_unique(candidates, alias.get("alias"))
            else:
                _append_unique(candidates, alias)
    return tuple(candidates)


def _dataset_value(dataset: Mapping[str, Any], mapped_source: str) -> Any:
    if mapped_source in dataset:
        return dataset.get(mapped_source)
    cursor: Any = dataset
    for part in [item for item in mapped_source.split(".") if item]:
        if not isinstance(cursor, Mapping):
            return None
        cursor = cursor.get(part)
    if isinstance(cursor, Mapping) and "value" in cursor:
        return cursor.get("value")
    return cursor


def _schema_dataset_field_for_requirement(
    source: MTDPPackageInput | None,
    requirement: MethodInputRequirement,
) -> Mapping[str, Any] | None:
    for field in _schema_dataset_fields(source):
        if _field_matches_requirement(field, requirement):
            return field
    return None


def _schema_dataset_fields(source: MTDPPackageInput | None) -> tuple[Mapping[str, Any], ...]:
    if source is None or not isinstance(source.schema, Mapping):
        return ()
    fields = source.schema.get("dataset_fields", ()) or ()
    return tuple(field for field in fields if isinstance(field, Mapping))


def _field_matches_requirement(field: Mapping[str, Any], requirement: MethodInputRequirement) -> bool:
    targets = {
        _normalise_key(requirement.source_role),
        _normalise_key(requirement.method_field),
        _normalise_key(requirement.method_field.rsplit(".", 1)[-1]),
        _normalise_key(requirement.requirement_id.rsplit(".", 1)[-1]),
    }
    values: list[Any] = [
        field.get("field_id"),
        field.get("role"),
        field.get("report_role"),
        field.get("method_role"),
        field.get("suggestion_key"),
        field.get("label"),
    ]
    storage = field.get("storage") if isinstance(field.get("storage"), Mapping) else {}
    if isinstance(storage, Mapping):
        values.extend([storage.get("path"), str(storage.get("path") or "").rsplit(".", 1)[-1]])
    for alias in field.get("import_aliases", ()) or ():
        values.append(alias.get("alias") if isinstance(alias, Mapping) else alias)
    normalized_values = {_normalise_key(value) for value in values if value not in (None, "")}
    if targets & normalized_values:
        return True
    if "testing_speed" in targets and "speed_of_testing" in normalized_values:
        return True
    if "conditioning" in targets and any(value.startswith("conditioning_") for value in normalized_values):
        return True
    return False


def _append_unique(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _normalise_key(value: Any) -> str:
    text = str(value or "").casefold()
    parts: list[str] = []
    previous_was_sep = False
    for char in text:
        if char.isalnum():
            parts.append(char)
            previous_was_sep = False
        elif not previous_was_sep:
            parts.append("_")
            previous_was_sep = True
    return "".join(parts).strip("_")


def _requirement_applies(requirement: MethodInputRequirement, mapping: Mapping[str, Any]) -> bool:
    if not requirement.required_when:
        return True
    left, operator, right = requirement.required_when.partition("==")
    if not operator:
        return False
    key = left.strip()
    actual = _mapping_config_value(mapping, key)
    if actual in (None, "") and key == "strain_source":
        actual = _mapping_strain_source(mapping)
    return str(actual or "").strip() == right.strip()


def _mapping_config_value(mapping: Mapping[str, Any], dotted_key: str) -> Any:
    current: Any = mapping
    for part in dotted_key.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
        else:
            return None
    return current


def _mapping_strain_source(mapping: Mapping[str, Any]) -> str | None:
    if _mapping_lookup(mapping, "channels", "front_strain") and _mapping_lookup(mapping, "channels", "rear_strain"):
        return "direct_strain_channels"
    if _mapping_lookup(mapping, "channels", "extension"):
        return "extension_derived"
    return None


def _runs_for_scope(source: MTDPPackageInput, requirement: MethodInputRequirement) -> tuple[MTDPRun | None, ...]:
    if requirement.scope == "per_run":
        return tuple(source.runs)
    return (None,)


def _status(records: list[ResolvedInput]) -> ReadinessStatus:
    if any(item.severity == "execution_critical" and item.status == "mapping_missing" for item in records):
        return ReadinessStatus.MAPPING_REQUIRED
    if any(item.severity == "execution_critical" and item.status not in {"pass", "unit_warning"} for item in records):
        return ReadinessStatus.NOT_READY
    if any(item.status != "pass" for item in records):
        return ReadinessStatus.READY_WITH_WARNINGS
    return ReadinessStatus.READY


def _schema_id(source: MTDPPackageInput) -> str | None:
    value = source.manifest.get("schema_id") or source.schema.get("schema_id")
    return str(value) if value else None


def _mapping_id(mapping: Mapping[str, Any]) -> str | None:
    value = mapping.get("mapping_id")
    return str(value) if value else None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _units_compatible(expected: str, actual: str) -> bool:
    return _normalize_unit(expected) == _normalize_unit(actual)


def _normalize_unit(unit: str) -> str:
    text = unit.strip().lower()
    return {
        "n": "n",
        "newton": "n",
        "newtons": "n",
        "mm": "mm",
        "millimeter": "mm",
        "millimetre": "mm",
        "mm/mm": "mm/mm",
        "strain": "mm/mm",
        "usn": "microstrain",
        "microstrain": "microstrain",
    }.get(text, text)
