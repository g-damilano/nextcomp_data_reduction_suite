from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ResourceResolver:
    """Resolve repository resources in source and PyInstaller/frozen mode."""

    source_root: Path
    runtime_root: Path
    frozen: bool = False
    external_root: Path | None = None

    @classmethod
    def discover(cls) -> "ResourceResolver":
        frozen = bool(getattr(sys, "frozen", False))
        runtime_root = Path(getattr(sys, "_MEIPASS", Path.cwd())).resolve() if frozen else _discover_source_root()
        external_root = _user_editable_resource_root() if frozen else None
        source_root = _discover_source_root()
        resolver = cls(source_root=source_root, runtime_root=runtime_root, frozen=frozen, external_root=external_root)
        resolver.materialize_external_resources()
        return resolver

    def materialize_external_resources(self, *, strict: bool = False) -> tuple[Path, ...]:
        if not self.frozen or self.external_root is None:
            return ()
        materialized: list[Path] = []
        for relative, suffixes in _EDITABLE_RESOURCE_TREES:
            source = self.runtime_root / relative
            target = self.external_root / relative
            if not source.exists():
                continue
            try:
                if _copy_missing_tree(source, target, suffixes=suffixes):
                    materialized.append(target)
            except OSError:
                if strict:
                    raise
        return tuple(materialized)

    def resource_path(self, *parts: str | Path, required: bool = True) -> Path:
        relative = Path(*[str(part) for part in parts])
        for root in self._candidate_roots():
            candidate = root / relative
            if candidate.exists():
                return candidate
        candidate = self.runtime_root / relative
        if required:
            raise FileNotFoundError(f"Runtime resource not found: {relative}")
        return candidate

    def method_registry_path(self) -> Path:
        return self.resource_path("config", "method_registry.yaml")

    def method_packages_root(self) -> Path:
        return self.resource_path("src", "methods")

    def method_package_path(self, relative_or_absolute: str | Path) -> Path:
        raw = Path(relative_or_absolute)
        if raw.is_absolute():
            return raw
        return self.resource_path(raw)

    def mappings_root(self) -> Path:
        return self.resource_path("mappings")

    def mapping_profile_path(self, relative_or_absolute: str | Path) -> Path:
        raw = Path(relative_or_absolute)
        if raw.is_absolute():
            return raw
        return self.resource_path(raw)

    def schema_library_root(self) -> Path:
        candidates = (
            (("mtdp_enrichment", "schema_library"), ("src", "mtdp_enrichment", "schema_library"))
            if self.frozen
            else (("src", "mtdp_enrichment", "schema_library"), ("mtdp_enrichment", "schema_library"))
        )
        for parts in candidates:
            path = self.resource_path(*parts, required=False)
            if path.exists():
                return path
        raise FileNotFoundError("MTDP schema library resource not found")

    def package_asset_root(self) -> Path:
        candidates = (
            (("mtdp_enrichment", "assets"), ("src", "mtdp_enrichment", "assets"))
            if self.frozen
            else (("src", "mtdp_enrichment", "assets"), ("mtdp_enrichment", "assets"))
        )
        for parts in candidates:
            path = self.resource_path(*parts, required=False)
            if path.exists():
                return path
        raise FileNotFoundError("MTDP asset resource not found")

    def asset_path(self, *parts: str | Path, required: bool = False) -> Path | None:
        try:
            return self.package_asset_root().joinpath(*[str(part) for part in parts])
        except FileNotFoundError:
            if required:
                raise
            return None

    def inventory(self) -> dict[str, object]:
        registry = self.method_registry_path()
        method_files = _relative_files(self.method_packages_root(), suffixes={".yaml", ".yml", ".json"})
        mapping_files = _relative_files(self.mappings_root(), suffixes={".json", ".yaml", ".yml"})
        schema_files = _relative_files(self.schema_library_root(), suffixes={".yaml", ".yml", ".json"})
        return {
            "schema_id": "runtime.resource_inventory.v0_1",
            "mode": "frozen" if self.frozen else "source",
            "source_root": str(self.source_root),
            "runtime_root": str(self.runtime_root),
            "method_registry": str(registry),
            "method_packages": method_files,
            "mapping_profiles": mapping_files,
            "schema_files": schema_files,
        }

    def _candidate_roots(self) -> Iterable[Path]:
        if self.external_root is not None:
            yield self.external_root
        yield self.runtime_root
        if self.source_root != self.runtime_root:
            yield self.source_root


_DEFAULT_RESOLVER: ResourceResolver | None = None


def default_resolver() -> ResourceResolver:
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        _DEFAULT_RESOLVER = ResourceResolver.discover()
    return _DEFAULT_RESOLVER


def _discover_source_root() -> Path:
    start = Path(__file__).resolve()
    for parent in [start.parent, *start.parents]:
        if (parent / "config" / "method_registry.yaml").exists() and (parent / "src").exists():
            return parent
    return Path.cwd().resolve()


def _user_editable_resource_root() -> Path:
    override = os.environ.get(_RESOURCE_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base).expanduser().resolve() / _APP_VENDOR / _APP_NAME
        return Path.home() / "AppData" / "Roaming" / _APP_VENDOR / _APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _APP_VENDOR / _APP_NAME

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser().resolve() / _APP_VENDOR / _APP_NAME
    return Path.home() / ".config" / _APP_VENDOR / _APP_NAME


def _relative_files(root: Path, *, suffixes: set[str]) -> list[str]:
    if not root.exists():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in suffixes
    ]


_EDITABLE_RESOURCE_TREES: tuple[tuple[Path, set[str]], ...] = (
    (Path("config"), {".yaml", ".yml", ".json"}),
    (Path("mappings"), {".json", ".yaml", ".yml"}),
    (Path("src", "methods"), {".yaml", ".yml", ".json"}),
    (Path("mtdp_enrichment", "schema_library"), {".yaml", ".yml", ".json"}),
    (Path("mtdp_enrichment", "assets"), {".ico", ".png", ".jpg", ".jpeg", ".svg"}),
)

_APP_VENDOR = "NextCOMP"
_APP_NAME = "mtdp_enrichment"
_RESOURCE_ROOT_ENV = "MTDP_ENRICHMENT_RESOURCE_ROOT"


def _copy_missing_tree(source: Path, target: Path, *, suffixes: set[str]) -> bool:
    copied = False
    if source.is_file():
        if source.suffix.lower() not in suffixes or target.exists():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True

    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        destination = target / path.relative_to(source)
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied = True
    return copied
