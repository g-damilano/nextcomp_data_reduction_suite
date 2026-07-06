from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    source_path: Path
    source_relative_path: str
    source_basename: str
    parent_folder_name: str
    source_display_name: str


def build_source_identities(paths: Iterable[str | Path], *, root: str | Path | None = None) -> dict[Path, SourceIdentity]:
    normalized = [_normalize_path(path) for path in paths]
    source_root = _normalize_path(root) if root is not None else common_source_root(normalized)
    duplicate_basenames = repeated_basenames(normalized)
    identities: dict[Path, SourceIdentity] = {}
    for path in normalized:
        identities[path] = source_identity_for_path(
            path,
            root=source_root,
            repeated_basename=path.name.casefold() in duplicate_basenames,
        )
    return identities


def source_identity_for_path(
    path: str | Path,
    *,
    root: str | Path | None = None,
    repeated_basename: bool | None = None,
) -> SourceIdentity:
    source_path = _normalize_path(path)
    source_root = _normalize_path(root) if root is not None else source_path.parent
    relative_path = _relative_path(source_path, source_root)
    basename = source_path.name
    parent = source_path.parent.name
    display = relative_path if repeated_basename else basename
    return SourceIdentity(
        source_path=source_path,
        source_relative_path=relative_path,
        source_basename=basename,
        parent_folder_name=parent,
        source_display_name=display,
    )


def repeated_basenames(paths: Iterable[str | Path]) -> set[str]:
    counts = Counter(_normalize_path(path).name.casefold() for path in paths)
    return {name for name, count in counts.items() if count > 1}


def common_source_root(paths: Iterable[str | Path]) -> Path | None:
    normalized = [_normalize_path(path) for path in paths]
    if not normalized:
        return None
    parents = [path.parent for path in normalized]
    try:
        return Path(os.path.commonpath([str(parent) for parent in parents]))
    except ValueError:
        return None


def identity_rows(identities: Mapping[Path, SourceIdentity]) -> list[dict[str, str]]:
    return [
        {
            "source_path": str(identity.source_path),
            "source_relative_path": identity.source_relative_path,
            "source_basename": identity.source_basename,
            "parent_folder_name": identity.parent_folder_name,
            "source_display_name": identity.source_display_name,
        }
        for identity in identities.values()
    ]


def _normalize_path(path: str | Path | None) -> Path:
    if path is None:
        return Path()
    return Path(path).expanduser().resolve()


def _relative_path(path: Path, root: Path | None) -> str:
    if root is None or str(root) == ".":
        return path.name
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
