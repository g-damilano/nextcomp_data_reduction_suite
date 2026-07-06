from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import yaml

from mtdp_enrichment.enrichment_import.canonical_yaml import (
    extract_value_and_unit,
    flatten_key_paths,
    structure_signature,
)
from mtdp_enrichment.enrichment_import.models import ImportedFieldCandidate, SupplementalYamlDocument
from mtdp_enrichment.enrichment_import.value_normalizers import transform_value_for_field

if TYPE_CHECKING:
    from mtdp_enrichment.package.schema import MTDPSchema


@dataclass(frozen=True, slots=True)
class MappingRule:
    source_key: str
    action: str = "map"
    target_field_id: str | None = None
    value_path: str | None = None
    unit: str | None = None
    date_format: str | None = None
    value_transform: str | None = None
    status: str | None = None
    user_corrected: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MappingRule":
        return cls(
            source_key=str(payload.get("source_key", payload.get("value_path", ""))),
            action=str(payload.get("action", "map")),
            target_field_id=None if payload.get("target_field_id") in (None, "") else str(payload.get("target_field_id")),
            value_path=None if payload.get("value_path") in (None, "") else str(payload.get("value_path")),
            unit=None if payload.get("unit") in (None, "") else str(payload.get("unit")),
            date_format=None if payload.get("date_format") in (None, "") else str(payload.get("date_format")),
            value_transform=None if payload.get("value_transform") in (None, "") else str(payload.get("value_transform")),
            status=None if payload.get("status") in (None, "") else str(payload.get("status")),
            user_corrected=bool(payload.get("user_corrected", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"source_key": self.source_key, "action": self.action}
        if self.target_field_id:
            data["target_field_id"] = self.target_field_id
        if self.value_path:
            data["value_path"] = self.value_path
        if self.unit:
            data["unit"] = self.unit
        if self.date_format:
            data["date_format"] = self.date_format
        if self.value_transform:
            data["value_transform"] = self.value_transform
        if self.status:
            data["status"] = self.status
        if self.user_corrected:
            data["user_corrected"] = self.user_corrected
        return data


@dataclass(frozen=True, slots=True)
class YamlMappingProfile:
    mapping_profile_id: str
    target_schema_id: str
    target_schema_version: str
    structure_signature: str
    mappings: tuple[MappingRule, ...]
    mapping_profile_version: str = "0.1.0"
    description: str = ""
    source_file_glob: str = "*.yaml"
    source_path: Path | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, source_path: Path | None = None) -> "YamlMappingProfile":
        source = payload.get("source", {}) if isinstance(payload.get("source"), dict) else {}
        return cls(
            mapping_profile_id=str(payload["mapping_profile_id"]),
            target_schema_id=str(payload["target_schema_id"]),
            target_schema_version=str(payload["target_schema_version"]),
            structure_signature=str(source.get("structure_signature", payload.get("structure_signature", ""))),
            mappings=tuple(MappingRule.from_dict(item) for item in payload.get("mappings", ()) or ()),
            mapping_profile_version=str(payload.get("mapping_profile_version", "0.1.0")),
            description=str(source.get("description", "")),
            source_file_glob=str((source.get("applies_to", {}) or {}).get("file_glob", "*.yaml"))
            if isinstance(source.get("applies_to", {}), dict)
            else "*.yaml",
            source_path=source_path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "YamlMappingProfile":
        profile_path = Path(path)
        payload = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Mapping profile {profile_path} must contain a mapping.")
        return cls.from_dict(payload, source_path=profile_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_profile_version": self.mapping_profile_version,
            "mapping_profile_id": self.mapping_profile_id,
            "target_schema_id": self.target_schema_id,
            "target_schema_version": self.target_schema_version,
            "source": {
                "description": self.description,
                "structure_signature": self.structure_signature,
                "applies_to": {"file_glob": self.source_file_glob},
            },
            "mappings": [rule.to_dict() for rule in self.mappings],
        }

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False)

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_yaml(), encoding="utf-8")
        return target

    def applies_to(self, schema: MTDPSchema, document: SupplementalYamlDocument) -> bool:
        return (
            self.target_schema_id == schema.schema_id
            and self.target_schema_version == schema.schema_version
            and self.structure_signature == document.structure_signature
        )

    def apply(
        self,
        document: SupplementalYamlDocument,
        schema: MTDPSchema,
    ) -> tuple[dict[str, ImportedFieldCandidate], tuple[str, ...], tuple[str, ...]]:
        imported: dict[str, ImportedFieldCandidate] = {}
        ignored: list[str] = []
        warnings: list[str] = []
        for rule in self.mappings:
            if rule.action == "ignore":
                ignored.append(rule.source_key)
                continue
            if rule.action != "map" or not rule.target_field_id:
                continue
            field = schema.field_by_id(rule.target_field_id)
            if field is None:
                warnings.append(f"Mapping target field does not exist: {rule.target_field_id}.")
                continue
            source_key = rule.value_path or rule.source_key
            raw_value = get_dotted_value(document.raw_payload, source_key)
            value, unit = extract_value_and_unit(raw_value)
            unit = rule.unit or unit
            value = normalize_compact_value(value, unit)
            transformed = transform_value_for_field(
                source_key=rule.source_key,
                raw_value=value,
                raw_unit=unit,
                field=field,
                selected_unit=unit,
                date_format=rule.date_format,
                value_transform=rule.value_transform,
            )
            if transformed is not None:
                value = transformed.canonical_value
                unit = transformed.canonical_unit
            imported[field.field_id] = ImportedFieldCandidate(
                field_id=field.field_id,
                value=value,
                unit=unit,
                source_path=document.source_path,
                source_key=rule.source_key,
                source_format="mapped_supplemental_yaml",
            )
        return imported, tuple(sorted(set(ignored))), tuple(warnings)


def profile_id_from_signature(prefix: str, signature: str) -> str:
    digest = signature.split(":", 1)[-1][:12]
    text = re.sub(r"[^a-z0-9_]+", "_", prefix.casefold()).strip("_") or "yaml_mapping"
    return f"{text}_{digest}"


def profile_for_mapping(
    *,
    profile_id: str,
    schema: MTDPSchema,
    payload: Mapping[str, Any],
    mappings: tuple[MappingRule, ...],
    description: str = "User-defined supplemental YAML mapping",
) -> YamlMappingProfile:
    signature = structure_signature(flatten_key_paths(payload))
    return YamlMappingProfile(
        mapping_profile_id=profile_id,
        target_schema_id=schema.schema_id,
        target_schema_version=schema.schema_version,
        structure_signature=signature,
        mappings=mappings,
        description=description,
    )


def load_profiles(directory: str | Path) -> tuple[YamlMappingProfile, ...]:
    root = Path(directory)
    if not root.exists():
        return ()
    profiles: list[YamlMappingProfile] = []
    for path in sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")):
        try:
            profiles.append(YamlMappingProfile.load(path))
        except (OSError, ValueError, yaml.YAMLError):
            continue
    return tuple(profiles)


def get_dotted_value(payload: Mapping[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, Mapping) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def normalize_compact_value(value: Any, unit: str | None) -> Any:
    if unit is None or not isinstance(value, str):
        return value
    pattern = rf"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*{re.escape(unit)}\s*$"
    match = re.match(pattern, value, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return value
