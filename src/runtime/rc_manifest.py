from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.resources import ResourceResolver, default_resolver


def build_rc_release_manifest(
    *,
    resolver: ResourceResolver | None = None,
    smoke_test_status: str = "not_run",
    known_residuals: list[str] | None = None,
    git_state_note: str | None = None,
) -> dict[str, Any]:
    resolver = resolver or default_resolver()
    registry = _load_yaml(resolver.method_registry_path())
    methods = registry.get("methods", []) if isinstance(registry, dict) else []
    return {
        "schema_id": "compression_module.rc_release_manifest.v0_1",
        "app": {
            "name": _project_name(resolver.source_root),
            "version": _project_version(resolver.source_root),
        },
        "build": {
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "mode": "frozen" if resolver.frozen else "source",
            "git": git_state_note or _git_state_note(resolver.source_root),
        },
        "resources": resolver.inventory(),
        "supported_method_packages": [
            {
                "method_id": str(item.get("method_id", "")),
                "label": str(item.get("label", "")),
                "version": str(item.get("version", "")),
                "status": str(item.get("status", "")),
                "analysis_type": str(item.get("analysis_type", "")),
                "method_path": str(item.get("method_path", "")),
                "default_mapping_path": str(item.get("default_mapping_path", "")),
            }
            for item in methods
            if isinstance(item, dict)
        ],
        "smoke_test_status": smoke_test_status,
        "known_residuals": known_residuals
        or [
            "PDF/DOCX export deferred",
            "PNG/SVG static plot export deferred",
            "Second-method proof deferred",
            "Fuzzy mapping authoring deferred",
            "Schema-extension editor deferred",
        ],
    }


def write_rc_release_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _project_name(root: Path) -> str:
    project = _project_table(root)
    return str(project.get("name", "compression-module"))


def _project_version(root: Path) -> str:
    project = _project_table(root)
    return str(project.get("version", "0.0.0"))


def _project_table(root: Path) -> dict[str, Any]:
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    return project if isinstance(project, dict) else {}


def _git_state_note(root: Path) -> dict[str, str]:
    return {
        "commit": _git(root, "rev-parse", "--short", "HEAD"),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "working_tree": "dirty" if _git(root, "status", "--porcelain") else "clean",
    }


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    return result.stdout.strip()
