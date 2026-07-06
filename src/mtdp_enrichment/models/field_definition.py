from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALIAS_CONFIDENCE: dict[str, float] = {
    "canonical_path": 1.00,
    "field_id": 0.95,
    "local_path": 0.90,
    "source_specific": 0.85,
    "legacy_key": 0.75,
    "unit_encoded_key": 0.70,
    "weak_key": 0.55,
    "deprecated": 0.40,
}

ALIAS_GROUP_TO_KIND: dict[str, str] = {
    "canonical_paths": "canonical_path",
    "canonical_path": "canonical_path",
    "local_paths": "local_path",
    "local_path": "local_path",
    "field_ids": "field_id",
    "field_id": "field_id",
    "source_specific": "source_specific",
    "source_specific_keys": "source_specific",
    "legacy_keys": "legacy_key",
    "legacy_key": "legacy_key",
    "weak_keys": "weak_key",
    "weak_key": "weak_key",
    "unit_encoded_keys": "unit_encoded_key",
    "unit_encoded_key": "unit_encoded_key",
    "deprecated": "deprecated",
    "deprecated_keys": "deprecated",
}


@dataclass(frozen=True, slots=True)
class AliasEntry:
    alias: str
    kind: str = "legacy_key"
    confidence: float = 0.75
    source: str | None = None
    deprecated: bool = False

    @classmethod
    def from_value(cls, value: Any, *, kind: str) -> "AliasEntry":
        if isinstance(value, dict):
            alias = str(value.get("alias", "")).strip()
            entry_kind = str(value.get("kind", kind)).strip() or kind
            confidence = value.get("confidence")
            deprecated = bool(value.get("deprecated", entry_kind == "deprecated"))
            source = value.get("source")
        else:
            alias = str(value).strip()
            entry_kind = kind
            confidence = None
            deprecated = entry_kind == "deprecated"
            source = None
        entry_kind = ALIAS_GROUP_TO_KIND.get(entry_kind, entry_kind)
        return cls(
            alias=alias,
            kind=entry_kind,
            confidence=float(confidence) if confidence is not None else ALIAS_CONFIDENCE.get(entry_kind, 0.75),
            source=None if source in (None, "") else str(source),
            deprecated=deprecated,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "alias": self.alias,
            "kind": self.kind,
            "confidence": self.confidence,
        }
        if self.source:
            data["source"] = self.source
        if self.deprecated:
            data["deprecated"] = True
        return data


@dataclass(frozen=True, slots=True)
class StorageMapping:
    location: str
    token: str | None = None
    path: str | None = None
    file: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StorageMapping":
        return cls(
            location=str(payload.get("location", "token_preamble")),
            token=payload.get("token"),
            path=payload.get("path"),
            file=payload.get("file"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"location": self.location}
        if self.token is not None:
            data["token"] = self.token
        if self.path is not None:
            data["path"] = self.path
        if self.file is not None:
            data["file"] = self.file
        return data


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    field_id: str
    label: str
    role: str
    required: bool
    type: str
    ui_group: str
    storage: StorageMapping
    accepted_units: tuple[str, ...] = ()
    standard_unit: str | None = None
    allowed_values: tuple[str, ...] = ()
    display_labels: dict[str, str] = field(default_factory=dict)
    iso_compliant_values: tuple[str, ...] = ()
    deviation_values: tuple[str, ...] = ()
    visible_when: dict[str, Any] = field(default_factory=dict)
    required_when: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    default: Any = None
    suggestion_key: str | None = None
    import_aliases: tuple[str, ...] = ()
    import_alias_entries: tuple[AliasEntry, ...] = ()
    value_map: dict[str, Any] = field(default_factory=dict)
    date_formats: dict[str, Any] = field(default_factory=dict)
    unit_dimension: str | None = None
    report_role: str | None = None
    report_importance: str | None = None
    method_role: str | None = None
    description: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FieldDefinition":
        field_id = str(payload.get("field_id") or payload.get("key") or "").strip()
        label = str(payload.get("label") or field_id)
        report_role = payload.get("report_role")
        method_role = payload.get("method_role")
        unit = payload.get("unit")
        standard_unit = payload.get("standard_unit", unit)
        accepted_units = tuple(payload.get("accepted_units", ()) or ())
        if unit and not accepted_units:
            accepted_units = (str(unit),)
        alias_entries = _parse_import_alias_entries(
            payload.get("import_aliases", ()) or (),
            field_id=field_id,
            label=label,
        )
        return cls(
            field_id=field_id,
            label=label,
            role=str(payload.get("role") or method_role or report_role or "metadata"),
            required=bool(payload.get("required", False)),
            type=str(payload.get("type", "string")),
            ui_group=str(payload.get("ui_group", "General")),
            storage=StorageMapping.from_dict(payload.get("storage", {})),
            accepted_units=accepted_units,
            standard_unit=standard_unit,
            allowed_values=tuple(payload.get("allowed_values", payload.get("choices", ())) or ()),
            display_labels={str(key): str(value) for key, value in dict(payload.get("display_labels", {}) or {}).items()},
            iso_compliant_values=tuple(payload.get("iso_compliant_values", ()) or ()),
            deviation_values=tuple(payload.get("deviation_values", ()) or ()),
            visible_when=dict(payload.get("visible_when", {}) or {}),
            required_when=dict(payload.get("required_when", {}) or {}),
            validation=dict(payload.get("validation", {}) or {}),
            default=payload.get("default"),
            suggestion_key=payload.get("suggestion_key"),
            import_aliases=tuple(entry.alias for entry in alias_entries),
            import_alias_entries=alias_entries,
            value_map={str(key): value for key, value in dict(payload.get("value_map", {}) or {}).items()},
            date_formats=dict(payload.get("date_formats", {}) or {}),
            unit_dimension=payload.get("unit_dimension"),
            report_role=None if report_role in (None, "") else str(report_role),
            report_importance=None if payload.get("report_importance") in (None, "") else str(payload.get("report_importance")),
            method_role=None if method_role in (None, "") else str(method_role),
            description=None if payload.get("description") in (None, "") else str(payload.get("description")),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "field_id": self.field_id,
            "label": self.label,
            "role": self.role,
            "required": self.required,
            "type": self.type,
            "ui_group": self.ui_group,
            "storage": self.storage.to_dict(),
        }
        if self.accepted_units:
            data["accepted_units"] = list(self.accepted_units)
        if self.standard_unit:
            data["standard_unit"] = self.standard_unit
        if self.allowed_values:
            data["allowed_values"] = list(self.allowed_values)
        if self.display_labels:
            data["display_labels"] = dict(self.display_labels)
        if self.iso_compliant_values:
            data["iso_compliant_values"] = list(self.iso_compliant_values)
        if self.deviation_values:
            data["deviation_values"] = list(self.deviation_values)
        if self.visible_when:
            data["visible_when"] = dict(self.visible_when)
        if self.required_when:
            data["required_when"] = dict(self.required_when)
        if self.validation:
            data["validation"] = dict(self.validation)
        if self.default is not None:
            data["default"] = self.default
        if self.suggestion_key:
            data["suggestion_key"] = self.suggestion_key
        if self.import_aliases:
            if _has_structured_aliases(self.import_alias_entries):
                grouped: dict[str, list[str | dict[str, Any]]] = {}
                for entry in self.import_alias_entries:
                    group = _alias_group_name(entry.kind)
                    if entry.confidence != ALIAS_CONFIDENCE.get(entry.kind, entry.confidence) or entry.source or entry.deprecated:
                        grouped.setdefault(group, []).append(entry.to_dict())
                    else:
                        grouped.setdefault(group, []).append(entry.alias)
                data["import_aliases"] = grouped
            else:
                data["import_aliases"] = list(self.import_aliases)
        if self.value_map:
            data["value_map"] = dict(self.value_map)
        if self.date_formats:
            data["date_formats"] = dict(self.date_formats)
        if self.unit_dimension:
            data["unit_dimension"] = self.unit_dimension
        if self.report_role:
            data["report_role"] = self.report_role
        if self.report_importance:
            data["report_importance"] = self.report_importance
        if self.method_role:
            data["method_role"] = self.method_role
        if self.description:
            data["description"] = self.description
        return data


@dataclass(frozen=True, slots=True)
class EnrichedFieldValue:
    value: Any
    unit: str | None = None
    source: str = "user"


def _parse_import_alias_entries(payload: Any, *, field_id: str, label: str) -> tuple[AliasEntry, ...]:
    entries: list[AliasEntry] = []
    if isinstance(payload, dict):
        for group, values in payload.items():
            kind = ALIAS_GROUP_TO_KIND.get(str(group), str(group))
            if isinstance(values, (str, bytes)):
                values = [values]
            for value in values or ():
                entry = AliasEntry.from_value(value, kind=kind)
                if entry.alias:
                    entries.append(entry)
    else:
        for value in payload or ():
            alias = str(value).strip()
            if not alias:
                continue
            entries.append(AliasEntry.from_value(alias, kind=_infer_flat_alias_kind(alias, field_id, label)))
    return _dedupe_alias_entries(entries)


def _infer_flat_alias_kind(alias: str, field_id: str, label: str) -> str:
    normalized = alias.strip().casefold()
    if normalized == field_id.casefold():
        return "field_id"
    if alias.startswith(("run.", "dataset.")):
        return "canonical_path"
    if "." in alias:
        if alias.split(".", 1)[0] in {"test_setup", "specimen"}:
            return "source_specific"
        return "local_path"
    if normalized == label.strip().casefold():
        return "legacy_key"
    if normalized in {"instrument", "machine", "location", "valid"}:
        return "weak_key"
    return "legacy_key"


def _dedupe_alias_entries(entries: list[AliasEntry]) -> tuple[AliasEntry, ...]:
    by_alias: dict[str, AliasEntry] = {}
    for entry in entries:
        key = entry.alias.strip().casefold()
        previous = by_alias.get(key)
        if previous is None or entry.confidence > previous.confidence:
            by_alias[key] = entry
    return tuple(by_alias.values())


def _has_structured_aliases(entries: tuple[AliasEntry, ...]) -> bool:
    return any(entry.kind not in {"legacy_key", "field_id", "canonical_path", "local_path", "source_specific"} for entry in entries)


def _alias_group_name(kind: str) -> str:
    for group, candidate in ALIAS_GROUP_TO_KIND.items():
        if candidate == kind and group.endswith("s"):
            return group
    return f"{kind}s"
