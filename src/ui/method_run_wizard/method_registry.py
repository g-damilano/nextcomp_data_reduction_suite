from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from runtime.resources import default_resolver

DEFAULT_REGISTRY_PATH = default_resolver().method_registry_path()


@dataclass(frozen=True, slots=True)
class MethodRegistryEntry:
    method_id: str
    label: str
    version: str
    status: str
    analysis_type: str
    method_path: Path
    default_mapping_path: Path | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, base_path: Path) -> "MethodRegistryEntry":
        method_path = _resolve_repo_path(payload.get("method_path"), base_path)
        default_mapping = payload.get("default_mapping_path")
        return cls(
            method_id=str(payload.get("method_id", method_path.name)),
            label=str(payload.get("label", payload.get("method_id", method_path.name))),
            version=str(payload.get("version", "")),
            status=str(payload.get("status", "active")),
            analysis_type=str(payload.get("analysis_type", "")),
            method_path=method_path,
            default_mapping_path=_resolve_repo_path(default_mapping, base_path) if default_mapping else None,
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "method_id": self.method_id,
            "label": self.label,
            "version": self.version,
            "status": self.status,
            "analysis_type": self.analysis_type,
            "method_path": str(self.method_path),
            "default_mapping_path": str(self.default_mapping_path) if self.default_mapping_path else None,
        }


class MethodRegistry:
    def __init__(self, entries: list[MethodRegistryEntry], *, path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self.entries = entries
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "MethodRegistry":
        registry_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        methods = payload.get("methods", [])
        if not isinstance(methods, list):
            raise ValueError(f"Method registry must contain a methods list: {registry_path}")
        entries = [
            MethodRegistryEntry.from_dict(item, base_path=registry_path.parent)
            for item in methods
            if isinstance(item, dict)
        ]
        return cls(entries, path=registry_path)

    def active_entries(self) -> list[MethodRegistryEntry]:
        return [entry for entry in self.entries if entry.status.casefold() == "active"]

    def by_id(self, method_id: str) -> MethodRegistryEntry:
        for entry in self.entries:
            if entry.method_id == method_id:
                return entry
        raise KeyError(method_id)

    def defaults_for_analysis_type(self, analysis_type: str | None) -> list[MethodRegistryEntry]:
        if not analysis_type:
            return self.active_entries()
        return [
            entry
            for entry in self.active_entries()
            if entry.analysis_type == analysis_type
        ] or self.active_entries()


def _resolve_repo_path(raw: object, base_path: Path) -> Path:
    path = Path(str(raw or ""))
    if path.is_absolute():
        return path
    candidate = default_resolver().resource_path(path, required=False)
    if candidate.exists():
        return candidate
    return (base_path / path).resolve()
