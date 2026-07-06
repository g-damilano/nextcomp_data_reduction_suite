from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True, slots=True)
class MappingProfile:
    mapping_id: str
    method_id: str
    channels: dict[str, Any]
    fields: dict[str, Any]
    validation: dict[str, Any]
    version: str = "0.2"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MappingProfile":
        return cls(
            mapping_id=str(payload.get("mapping_id") or "mapping_profile"),
            method_id=str(payload.get("method_id") or ""),
            channels=dict(payload.get("channels") or {}),
            fields=dict(payload.get("fields") or {}),
            validation=dict(payload.get("validation") or {}),
            version=str(payload.get("version") or payload.get("schema_version") or "0.2"),
        )

    @classmethod
    def load(cls, path: str | Path) -> "MappingProfile":
        text = Path(path).read_text(encoding="utf-8")
        payload = yaml.safe_load(text) if Path(path).suffix.lower() in {".yaml", ".yml"} else json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError(f"Mapping profile must contain an object: {path}")
        return cls.from_payload(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.mapping_profile.v0_2",
            "version": self.version,
            "mapping_id": self.mapping_id,
            "method_id": self.method_id,
            "channels": self.channels,
            "fields": self.fields,
            "validation": self.validation,
        }


def normalize_mapping_profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    profile = MappingProfile.from_payload(payload)
    data = profile.to_dict()
    # Preserve legacy top-level keys that downstream code may still read.
    for key, value in payload.items():
        data.setdefault(str(key), value)
    return data
