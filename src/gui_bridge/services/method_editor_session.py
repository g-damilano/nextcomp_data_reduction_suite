from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from gui_bridge.services.method_editor_export import MethodEditorExportError, MethodEditorExportService
from methods.core.method_package import MethodPackage
from ui.method_run_wizard.method_registry import MethodRegistry, MethodRegistryEntry


class MethodEditorSessionError(Exception):
    def __init__(
        self,
        error_type: str,
        message: str,
        *,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable
        self.details = details or {}


class MethodEditorSessionService:
    """Backend-owned Method Editor bridge service.

    This service intentionally works on generated drafts. Canonical method
    packages remain read-only golden-standard inputs for the GUI transition.
    """

    def __init__(
        self,
        *,
        registry_path: str | Path | None = None,
        generated_root: str | Path | None = None,
    ) -> None:
        self.registry_path = Path(registry_path) if registry_path is not None else None
        self.generated_root = Path(generated_root) if generated_root is not None else Path("src/methods/generated")
        self._export_service = MethodEditorExportService(self.generated_root)

    def list_methods(self) -> dict[str, Any]:
        registry = self._load_registry()
        registry_payload = self._read_registry_payload(registry.path)
        raw_methods = registry_payload.get("methods", [])
        if not isinstance(raw_methods, list):
            raw_methods = []
        methods = [
            self._registry_entry_summary(entry, raw=_find_registry_payload(raw_methods, entry.method_id))
            for entry in registry.active_entries()
        ]
        return {
            "methods": methods,
            "method_count": len(methods),
            "registry_path": str(registry.path),
        }

    def load_method(self, method_id: str) -> dict[str, Any]:
        entry, package = self._load_base_method(method_id)
        registry = self._load_registry()
        registry_payload = self._read_registry_payload(registry.path)
        raw_methods = registry_payload.get("methods", [])
        raw = _find_registry_payload(raw_methods, entry.method_id) if isinstance(raw_methods, list) and entry else None
        return {
            "method": self._method_summary(
                package,
                entry=entry,
                canonical=not self._is_generated_registry_entry(entry, raw=raw),
            ),
            "recipe_files": [str(path) for path in package.recipe_files()],
            "recipe_file_count": len(package.recipe_files()),
        }

    def create_draft(
        self,
        method_id: str,
        *,
        draft_label: str | None = None,
    ) -> dict[str, Any]:
        entry, package = self._load_base_method(method_id)
        draft_id = f"draft_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        draft_root = self._draft_root(package.method_id, draft_id)
        draft_root.mkdir(parents=True, exist_ok=False)

        copied_files: list[dict[str, str]] = []
        for source in package.recipe_files():
            target = draft_root / source.name
            shutil.copy2(source, target)
            copied_files.append({"source": str(source), "target": str(target), "kind": "recipe"})

        editor_root = draft_root / "method_editor"
        editor_root.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        edit_record = {
            "schema": "method-editor-draft/v1",
            "draft_id": draft_id,
            "draft_label": draft_label or f"{package.name} draft",
            "base_method_id": package.method_id,
            "base_method_version": package.version,
            "base_method_path": str(package.root),
            "draft_path": str(draft_root),
            "created_at": created_at,
            "canonical_mutation_allowed": False,
            "copied_files": copied_files,
            "pending_edits": [],
            "applied_edits": [],
            "validation_summary": {
                "status": "valid",
                "loadable": True,
                "checked_at": created_at,
                "warnings": [],
            },
        }
        edit_record_path = editor_root / "edit_record.json"
        edit_record_path.write_text(json.dumps(edit_record, indent=2) + "\n", encoding="utf-8")
        edit_summary_path = self._write_edit_summary(draft_root, edit_record)

        loaded_draft = MethodPackage.load(draft_root)
        return {
            "draft": {
                "draft_id": draft_id,
                "draft_label": edit_record["draft_label"],
                "base_method_id": package.method_id,
                "base_method_version": package.version,
                "base_method_path": str(package.root),
                "draft_path": str(draft_root),
                "edit_record_path": str(edit_record_path),
                "edit_summary_path": str(edit_summary_path),
                "copied_files": copied_files,
                "copied_file_count": len(copied_files),
                "loadable": True,
                "method": self._method_summary(loaded_draft, entry=entry, canonical=False),
            }
        }

    def update_draft(
        self,
        *,
        draft_id: str | None = None,
        draft_path: str | Path | None = None,
        patch: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        draft_root = self._find_draft_root(draft_id=draft_id, draft_path=draft_path)
        if not isinstance(patch, dict) or not patch:
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.updateDraft requires a non-empty payload.patch object.",
                details={"patch_type": type(patch).__name__},
            )

        edit_record = self._read_edit_record(draft_root)
        group = str(
            patch.get("parameter_group")
            or patch.get("parameterGroup")
            or patch.get("controlled_group")
            or patch.get("controlledGroup")
            or patch.get("group")
            or ""
        ).strip()
        values = patch.get("values")
        if values is None:
            values = {
                key: value
                for key, value in patch.items()
                if key
                not in {
                    "parameter_group",
                    "parameterGroup",
                    "controlled_group",
                    "controlledGroup",
                    "group",
                    "reason",
                }
            }
        if not isinstance(values, dict):
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.updateDraft requires patch.values to be an object.",
                details={"values_type": type(values).__name__},
            )

        if group != "modulus_chord_strain_window":
            raise MethodEditorSessionError(
                "Unsupported",
                "Unsupported Method Editor draft patch group.",
                details={
                    "group": group,
                    "supported_groups": ["modulus_chord_strain_window"],
                },
            )

        edit = self._apply_modulus_chord_patch(
            draft_root,
            values,
            reason=reason or str(patch.get("reason") or ""),
        )
        applied_edits = edit_record.setdefault("applied_edits", [])
        if not isinstance(applied_edits, list):
            edit_record["applied_edits"] = applied_edits = []
        applied_edits.append(edit)
        edit_record["pending_edits"] = []
        edit_record["updated_at"] = edit["applied_at"]

        validation = self._validate_draft_root(draft_root)
        edit_record["validation_summary"] = validation
        self._write_edit_record(draft_root, edit_record)
        summary_path = self._write_edit_summary(draft_root, edit_record)

        package = MethodPackage.load(draft_root)
        return {
            "draft": self._draft_summary(draft_root, package, edit_record),
            "edit": edit,
            "validation": validation,
            "edit_record_path": str(draft_root / "method_editor" / "edit_record.json"),
            "edit_summary_path": str(summary_path),
        }

    def validate_draft(
        self,
        *,
        draft_id: str | None = None,
        draft_path: str | Path | None = None,
    ) -> dict[str, Any]:
        draft_root = self._find_draft_root(draft_id=draft_id, draft_path=draft_path)
        edit_record = self._read_edit_record(draft_root)
        validation = self._validate_draft_root(draft_root)
        edit_record["validation_summary"] = validation
        edit_record["last_validated_at"] = validation["checked_at"]
        self._write_edit_record(draft_root, edit_record)
        summary_path = self._write_edit_summary(draft_root, edit_record)
        package = MethodPackage.load(draft_root)
        return {
            "draft": self._draft_summary(draft_root, package, edit_record),
            "validation": validation,
            "edit_record_path": str(draft_root / "method_editor" / "edit_record.json"),
            "edit_summary_path": str(summary_path),
        }

    def generate_version(
        self,
        *,
        draft_id: str | None = None,
        draft_path: str | Path | None = None,
        target_version: str | None = None,
    ) -> dict[str, Any]:
        target_version = _normal_version(target_version)
        draft_root = self._find_draft_root(draft_id=draft_id, draft_path=draft_path)
        draft_record = self._read_edit_record(draft_root)
        if draft_record.get("schema") != "method-editor-draft/v1":
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor generated versions must be created from a draft edit record.",
                details={"draft_path": str(draft_root), "schema": draft_record.get("schema")},
            )

        draft_validation = self._validate_draft_root(draft_root)
        draft_package = MethodPackage.load(draft_root)
        base_method_id = str(draft_record.get("base_method_id") or draft_package.method_id)
        base_method_version = str(draft_record.get("base_method_version") or draft_package.version)
        generated_method_id = _generated_method_id(base_method_id, target_version)
        target_root = self._versioned_method_root(base_method_id, target_version)
        if target_root.exists():
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method version already exists.",
                details={
                    "target_version": target_version,
                    "generated_method_id": generated_method_id,
                    "method_path": str(target_root),
                },
            )

        generated_label = _display_method_name(draft_package.name, target_version)
        copied_files: list[dict[str, str]] = []
        generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        target_root.mkdir(parents=True, exist_ok=False)
        try:
            for source in draft_package.recipe_files():
                target = target_root / source.name
                shutil.copy2(source, target)
                copied_files.append({"source": str(source), "target": str(target), "kind": "recipe"})
            self._rewrite_generated_method_identity(
                target_root,
                method_id=generated_method_id,
                version=target_version,
                method_name=generated_label,
                base_method_id=base_method_id,
            )
            generated_package = MethodPackage.load(target_root)
            self._validate_loaded_package(generated_package)
            generated_validation = {
                "status": "valid",
                "loadable": True,
                "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "method_id": generated_package.method_id,
                "version": generated_package.version,
                "source_draft_validation": draft_validation,
                "warnings": [],
            }
            generated_record = {
                "schema": "method-editor-generated/v1",
                "generated_method_id": generated_package.method_id,
                "generated_method_name": generated_package.name,
                "generated_version": generated_package.version,
                "generated_method_path": str(target_root),
                "generated_at": generated_at,
                "source_draft_id": str(draft_record.get("draft_id") or draft_root.name),
                "source_draft_path": str(draft_root),
                "base_method_id": base_method_id,
                "base_method_version": base_method_version,
                "base_method_path": str(draft_record.get("base_method_path") or ""),
                "canonical_mutation_allowed": False,
                "copied_files": copied_files,
                "applied_edits": list(draft_record.get("applied_edits") or []),
                "validation_summary": generated_validation,
                "draft_edit_record": draft_record,
            }
            edit_root = target_root / "method_editor"
            edit_root.mkdir(parents=True, exist_ok=True)
            edit_record_path = self._write_edit_record(target_root, generated_record)
            edit_summary_path = self._write_edit_summary(target_root, generated_record)
        except Exception:
            if target_root.exists():
                shutil.rmtree(target_root)
            raise

        return {
            "generated_method": self._generated_method_summary(
                target_root,
                generated_package,
                generated_record,
            ),
            "validation": generated_validation,
            "edit_record_path": str(edit_record_path),
            "edit_summary_path": str(edit_summary_path),
        }

    def register_generated_method(self, method_path: str | Path) -> dict[str, Any]:
        method_root = Path(str(method_path or "")).resolve()
        if not str(method_path or "").strip():
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.registerGeneratedMethod requires payload.method_path.",
            )
        self._assert_generated_method_root(method_root)
        edit_record = self._read_edit_record(method_root)
        if edit_record.get("schema") != "method-editor-generated/v1":
            raise MethodEditorSessionError(
                "ValidationError",
                "Only Method Editor generated method packages can be registered.",
                details={"method_path": str(method_root), "schema": edit_record.get("schema")},
            )

        try:
            package = MethodPackage.load(method_root)
            self._validate_loaded_package(package)
        except MethodEditorSessionError:
            raise
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method package does not load and cannot be registered.",
                details={"method_path": str(method_root), "exception": exc.__class__.__name__},
            ) from exc

        registry = self._load_registry()
        registry_payload = self._read_registry_payload(registry.path)
        methods = registry_payload.setdefault("methods", [])
        if not isinstance(methods, list):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method registry must contain a methods list.",
                details={"registry_path": str(registry.path)},
            )

        try:
            existing_entry = registry.by_id(package.method_id)
        except KeyError:
            existing_entry = None
        if existing_entry is not None:
            if existing_entry.method_path.resolve() == method_root:
                return {
                    "registered": False,
                    "already_registered": True,
                    "registry_path": str(registry.path),
                    "registry_entry": existing_entry.to_dict(),
                }
            raise MethodEditorSessionError(
                "ValidationError",
                "A different method registry entry already uses this generated method id.",
                details={
                    "method_id": package.method_id,
                    "existing_method_path": str(existing_entry.method_path),
                    "method_path": str(method_root),
                },
            )

        base_method_id = str(edit_record.get("base_method_id") or "")
        base_raw_entry = _find_registry_payload(methods, base_method_id)
        base_entry: MethodRegistryEntry | None = None
        try:
            base_entry = registry.by_id(base_method_id)
        except KeyError:
            base_entry = None
        default_mapping_path = None
        if isinstance(base_raw_entry, dict):
            default_mapping_path = base_raw_entry.get("default_mapping_path")
        if not default_mapping_path and base_entry is not None and base_entry.default_mapping_path is not None:
            default_mapping_path = str(base_entry.default_mapping_path)

        registry_entry: dict[str, Any] = {
            "method_id": package.method_id,
            "label": _display_method_name(package.name, package.version),
            "version": package.version,
            "status": "active",
            "analysis_type": str(package.manifest.get("analysis_type") or (base_entry.analysis_type if base_entry else "")),
            "method_path": self._registry_path_value(method_root),
            "source": "method_editor_generated",
            "base_method_id": base_method_id,
            "generated_at": str(edit_record.get("generated_at") or ""),
        }
        if default_mapping_path:
            registry_entry["default_mapping_path"] = default_mapping_path
        methods.append(registry_entry)
        registry.path.write_text(yaml.safe_dump(registry_payload, sort_keys=False), encoding="utf-8")

        reloaded = MethodRegistry.load(registry.path)
        added_entry = reloaded.by_id(package.method_id)
        return {
            "registered": True,
            "already_registered": False,
            "registry_path": str(registry.path),
            "registry_entry": self._registry_entry_summary(added_entry, raw=registry_entry),
            "method_count": len(reloaded.entries),
        }

    def export_method_package(
        self,
        method_path: str | Path,
        *,
        output_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        method_root = Path(str(method_path or "")).resolve()
        if not str(method_path or "").strip():
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.exportMethodPackage requires payload.method_path.",
            )
        self._assert_generated_method_root(method_root)
        edit_record = self._read_edit_record(method_root)
        if edit_record.get("schema") != "method-editor-generated/v1":
            raise MethodEditorSessionError(
                "ValidationError",
                "Only Method Editor generated method packages can be exported.",
                details={"method_path": str(method_root), "schema": edit_record.get("schema")},
            )
        try:
            package = MethodPackage.load(method_root)
            self._validate_loaded_package(package)
        except MethodEditorSessionError:
            raise
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method package does not load and cannot be exported.",
                details={"method_path": str(method_root), "exception": exc.__class__.__name__},
            ) from exc

        try:
            export = self._export_service.export_generated_method(
                method_root,
                package,
                output_path=output_path,
                overwrite=overwrite,
            )
        except MethodEditorExportError as exc:
            raise MethodEditorSessionError(
                exc.error_type,
                str(exc),
                details=exc.details,
            ) from exc
        except Exception as exc:
            raise MethodEditorSessionError(
                "InternalError",
                "Method Editor generated package export failed.",
                details={"method_path": str(method_root), "exception": exc.__class__.__name__},
            ) from exc
        summary = self._generated_method_summary(method_root, package, edit_record)
        return {
            "export": export,
            "generated_method": summary,
        }

    def import_method_package(
        self,
        source_path: str | Path,
        *,
        register: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        source = Path(str(source_path or "")).resolve()
        if not str(source_path or "").strip():
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.openMethodPackage requires payload.path.",
            )
        if not source.exists():
            raise MethodEditorSessionError(
                "NotFound",
                "Method Editor package source was not found.",
                details={"source_path": str(source)},
            )

        imported_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with tempfile.TemporaryDirectory(prefix="method_editor_import_") as temp_dir:
            package_source = self._resolve_import_package_root(source, Path(temp_dir))
            edit_record = self._read_edit_record(package_source)
            if edit_record.get("schema") != "method-editor-generated/v1":
                raise MethodEditorSessionError(
                    "ValidationError",
                    "Only Method Editor generated method packages can be opened.",
                    details={"source_path": str(source), "schema": edit_record.get("schema")},
                )
            try:
                package = MethodPackage.load(package_source)
                self._validate_loaded_package(package)
            except MethodEditorSessionError:
                raise
            except Exception as exc:
                raise MethodEditorSessionError(
                    "ValidationError",
                    "Method Editor package does not load and cannot be opened.",
                    details={"source_path": str(source), "exception": exc.__class__.__name__},
                ) from exc

            recorded_id = str(edit_record.get("generated_method_id") or "")
            if recorded_id and recorded_id != package.method_id:
                raise MethodEditorSessionError(
                    "ValidationError",
                    "Method Editor package id does not match its edit record.",
                    details={
                        "source_path": str(source),
                        "method_id": package.method_id,
                        "edit_record_method_id": recorded_id,
                    },
                )
            base_method_id = str(
                edit_record.get("base_method_id")
                or package.manifest.get("generated_from_method_id")
                or ""
            ).strip()
            if not base_method_id:
                raise MethodEditorSessionError(
                    "ValidationError",
                    "Method Editor package edit record is missing base_method_id.",
                    details={"source_path": str(source)},
                )
            target_root = self._versioned_method_root(base_method_id, package.version)
            same_location = package_source.resolve() == target_root.resolve()
            if target_root.exists() and not same_location:
                if not overwrite:
                    raise MethodEditorSessionError(
                        "ValidationError",
                        "A generated method package with this base method and version already exists.",
                        details={
                            "source_path": str(source),
                            "method_id": package.method_id,
                            "version": package.version,
                            "method_path": str(target_root),
                        },
                    )
                shutil.rmtree(target_root)

            if not same_location:
                target_root.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    package_source,
                    target_root,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )

            target_record = self._read_edit_record(target_root)
            target_record["generated_method_path"] = str(target_root)
            target_record["imported_at"] = imported_at
            target_record["import_source_path"] = str(source)
            target_record["canonical_mutation_allowed"] = False
            self._write_edit_record(target_root, target_record)
            self._write_edit_summary(target_root, target_record)

        imported_package = MethodPackage.load(target_root)
        self._validate_loaded_package(imported_package)
        summary = self._generated_method_summary(target_root, imported_package, self._read_edit_record(target_root))
        registry: dict[str, Any] | None = None
        if register:
            registry = self.register_generated_method(target_root)
        return {
            "import": {
                "imported": not same_location,
                "source_path": str(source),
                "method_path": str(target_root),
                "registered": bool(registry and (registry.get("registered") or registry.get("already_registered"))),
                "imported_at": imported_at,
            },
            "generated_method": summary,
            "registry": registry,
        }

    def delete_generated_method(
        self,
        *,
        method_id: str | None = None,
        method_path: str | Path | None = None,
    ) -> dict[str, Any]:
        method_root = self._find_generated_method_root(method_id=method_id, method_path=method_path)
        edit_record = self._read_edit_record(method_root)
        if edit_record.get("schema") != "method-editor-generated/v1":
            raise MethodEditorSessionError(
                "ValidationError",
                "Only Method Editor generated method packages can be deleted.",
                details={"method_path": str(method_root), "schema": edit_record.get("schema")},
            )
        generated_id = str(edit_record.get("generated_method_id") or method_id or method_root.name)
        generated_version = str(edit_record.get("generated_version") or "")
        deleted_file_count = sum(1 for path in method_root.rglob("*") if path.is_file())
        registry = self._remove_generated_registry_entries(method_root, generated_id)
        shutil.rmtree(method_root)
        return {
            "deleted": True,
            "method_id": generated_id,
            "version": generated_version,
            "method_path": str(method_root),
            "deleted_file_count": deleted_file_count,
            "registry": registry,
        }

    def rename_generated_method(
        self,
        *,
        method_id: str | None = None,
        method_path: str | Path | None = None,
        label: str = "",
    ) -> dict[str, Any]:
        method_root = self._find_generated_method_root(method_id=method_id, method_path=method_path)
        edit_record = self._read_edit_record(method_root)
        if edit_record.get("schema") != "method-editor-generated/v1":
            raise MethodEditorSessionError(
                "ValidationError",
                "Only Method Editor generated method packages can be renamed.",
                details={"method_path": str(method_root), "schema": edit_record.get("schema")},
            )
        clean_label = str(label or "").strip()
        if not clean_label:
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor.renameMethod requires a non-empty label.",
            )

        generated_id = str(edit_record.get("generated_method_id") or method_id or method_root.name)
        registry = self._load_registry()
        registry_payload = self._read_registry_payload(registry.path)
        methods = registry_payload.get("methods")
        if not isinstance(methods, list):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method registry must contain a methods list.",
                details={"registry_path": str(registry.path)},
            )

        renamed_payload: dict[str, Any] | None = None
        generated_root = self.generated_root.resolve()
        for item in methods:
            if not isinstance(item, dict):
                continue
            item_path = _registry_payload_method_path(item, registry.path.parent)
            same_id = str(item.get("method_id") or "") == generated_id
            same_path = item_path is not None and item_path.resolve() == method_root.resolve()
            generated_source = str(item.get("source") or "") == "method_editor_generated"
            generated_location = False
            if item_path is not None:
                try:
                    generated_location = item_path.resolve().is_relative_to(generated_root)
                except Exception:
                    generated_location = False
            if (same_id or same_path) and (generated_source or generated_location):
                item["label"] = clean_label
                renamed_payload = item
                break

        if renamed_payload is None:
            raise MethodEditorSessionError(
                "NotFound",
                "Generated Method Editor method was not found in the registry.",
                details={"method_id": generated_id, "method_path": str(method_root)},
            )

        registry.path.write_text(yaml.safe_dump(registry_payload, sort_keys=False), encoding="utf-8")
        reloaded = MethodRegistry.load(registry.path)
        entry = reloaded.by_id(str(renamed_payload.get("method_id") or generated_id))
        package = MethodPackage.load(method_root)
        summary = self._generated_method_summary(method_root, package, edit_record)
        summary["label"] = clean_label
        summary["method_name"] = clean_label
        return {
            "renamed": True,
            "method_id": entry.method_id,
            "label": clean_label,
            "method": summary,
            "registry_entry": self._registry_entry_summary(entry, raw=renamed_payload),
            "registry_path": str(registry.path),
        }

    def _resolve_import_package_root(self, source: Path, temp_root: Path) -> Path:
        if source.is_file() and source.suffix.lower() == ".zip":
            return self._extract_import_zip(source, temp_root)
        if source.is_file():
            return self._find_import_package_root(source.parent)
        return self._find_import_package_root(source)

    def _extract_import_zip(self, source: Path, temp_root: Path) -> Path:
        try:
            with zipfile.ZipFile(source) as archive:
                for member in archive.infolist():
                    member_name = member.filename.replace("\\", "/")
                    member_parts = Path(member_name).parts
                    if (
                        not member_name
                        or member_name.startswith("/")
                        or (member_parts and ":" in member_parts[0])
                        or ".." in member_parts
                    ):
                        raise MethodEditorSessionError(
                            "ValidationError",
                            "Method Editor package archive contains an unsafe path.",
                            details={"source_path": str(source), "member": member.filename},
                        )
                    target = (temp_root / member_name).resolve()
                    if not target.is_relative_to(temp_root.resolve()):
                        raise MethodEditorSessionError(
                            "ValidationError",
                            "Method Editor package archive escapes the import directory.",
                            details={"source_path": str(source), "member": member.filename},
                        )
                archive.extractall(temp_root)
        except MethodEditorSessionError:
            raise
        except zipfile.BadZipFile as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor package archive is not a readable zip file.",
                details={"source_path": str(source)},
            ) from exc
        return self._find_import_package_root(temp_root)

    def _find_import_package_root(self, root: Path) -> Path:
        if (root / "method_manifest.yaml").is_file():
            return root.resolve()
        candidates = sorted(path.parent.resolve() for path in root.rglob("method_manifest.yaml"))
        if not candidates:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor package source does not contain method_manifest.yaml.",
                details={"source_path": str(root)},
            )
        unique_candidates = []
        for candidate in candidates:
            if candidate not in unique_candidates:
                unique_candidates.append(candidate)
        if len(unique_candidates) != 1:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor package source contains multiple method packages.",
                details={"source_path": str(root), "matches": [str(path) for path in unique_candidates]},
            )
        return unique_candidates[0]

    def _load_registry(self) -> MethodRegistry:
        try:
            return MethodRegistry.load(self.registry_path)
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Unable to load the method registry.",
                details={"registry_path": str(self.registry_path or "")},
            ) from exc

    def _load_base_method(self, method_id: str) -> tuple[MethodRegistryEntry | None, MethodPackage]:
        method_ref = str(method_id or "").strip()
        if not method_ref:
            raise MethodEditorSessionError(
                "ValidationError",
                "methodEditor command requires payload.method_id.",
            )

        registry = self._load_registry()
        entry: MethodRegistryEntry | None = None
        method_root: Path | None = None
        try:
            entry = registry.by_id(method_ref)
            method_root = entry.method_path
        except KeyError:
            method_root = None

        if method_root is None:
            raise MethodEditorSessionError(
                "ValidationError",
                f"Unknown method for Method Editor: {method_ref}.",
                details={
                    "method_id": method_ref,
                    "eligible_method_ids": [item.method_id for item in registry.active_entries()],
                },
            )

        try:
            package = MethodPackage.load(method_root)
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Unable to load the selected method package.",
                details={"method_id": method_ref, "method_path": str(method_root)},
            ) from exc
        return entry, package

    def _draft_root(self, method_id: str, draft_id: str) -> Path:
        safe_method_id = _safe_segment(method_id)
        return (self.generated_root / safe_method_id / "drafts" / draft_id).resolve()

    def _versioned_method_root(self, method_id: str, target_version: str) -> Path:
        safe_method_id = _safe_segment(method_id)
        return (self.generated_root / safe_method_id / _version_segment(target_version)).resolve()

    def _find_draft_root(
        self,
        *,
        draft_id: str | None = None,
        draft_path: str | Path | None = None,
    ) -> Path:
        generated_root = self.generated_root.resolve()
        if draft_path:
            candidate = Path(draft_path).resolve()
            self._assert_generated_draft_root(candidate, generated_root=generated_root)
            return candidate

        draft_ref = str(draft_id or "").strip()
        if not draft_ref:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor draft commands require payload.draft_id or payload.draft_path.",
            )
        if any(sep in draft_ref for sep in ("/", "\\", "*", "?", "[", "]")) or draft_ref in {".", ".."}:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor draft id must be a draft identifier, not a path.",
                details={"draft_id": draft_ref},
            )
        matches = sorted(generated_root.glob(f"*/drafts/{draft_ref}")) if generated_root.exists() else []
        if not matches:
            raise MethodEditorSessionError(
                "NotFound",
                "Generated Method Editor draft was not found.",
                details={"draft_id": draft_ref, "generated_root": str(generated_root)},
            )
        if len(matches) > 1:
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated Method Editor draft id is ambiguous.",
                details={"draft_id": draft_ref, "matches": [str(path) for path in matches]},
            )
        candidate = matches[0].resolve()
        self._assert_generated_draft_root(candidate, generated_root=generated_root)
        return candidate

    def _find_generated_method_root(
        self,
        *,
        method_id: str | None = None,
        method_path: str | Path | None = None,
    ) -> Path:
        if method_path:
            candidate = Path(method_path).resolve()
            self._assert_generated_method_root(candidate)
            return candidate

        method_ref = str(method_id or "").strip()
        if not method_ref:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor generated method commands require payload.method_id or payload.method_path.",
            )
        try:
            entry = self._load_registry().by_id(method_ref)
        except KeyError as exc:
            raise MethodEditorSessionError(
                "NotFound",
                "Generated Method Editor method was not found in the registry.",
                details={"method_id": method_ref},
            ) from exc
        candidate = entry.method_path.resolve()
        self._assert_generated_method_root(candidate)
        return candidate

    def _assert_generated_draft_root(self, draft_root: Path, *, generated_root: Path) -> None:
        if not draft_root.is_dir() or not draft_root.is_relative_to(generated_root):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor draft path must be a generated draft directory.",
                details={"draft_path": str(draft_root), "generated_root": str(generated_root)},
            )
        if not (draft_root / "method_editor" / "edit_record.json").is_file():
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor draft is missing its edit record.",
                details={"draft_path": str(draft_root)},
            )

    def _assert_generated_method_root(self, method_root: Path) -> None:
        generated_root = self.generated_root.resolve()
        if not method_root.is_dir() or not method_root.is_relative_to(generated_root):
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method path must be inside the Method Editor generated root.",
                details={"method_path": str(method_root), "generated_root": str(generated_root)},
            )
        if "drafts" in method_root.relative_to(generated_root).parts:
            raise MethodEditorSessionError(
                "ValidationError",
                "Draft directories must be published with methodEditor.generateVersion before registration.",
                details={"method_path": str(method_root)},
            )
        if not (method_root / "method_editor" / "edit_record.json").is_file():
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method package is missing its edit record.",
                details={"method_path": str(method_root)},
            )

    def _read_edit_record(self, draft_root: Path) -> dict[str, Any]:
        record_path = draft_root / "method_editor" / "edit_record.json"
        try:
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Unable to read Method Editor edit record.",
                details={"edit_record_path": str(record_path)},
            ) from exc
        if not isinstance(payload, dict):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor edit record must be a JSON object.",
                details={"edit_record_path": str(record_path)},
            )
        if payload.get("canonical_mutation_allowed") is not False:
            raise MethodEditorSessionError(
                "ValidationError",
                "Method Editor package is not marked as canonical-safe.",
                details={"edit_record_path": str(record_path)},
            )
        return payload

    def _write_edit_record(self, draft_root: Path, edit_record: dict[str, Any]) -> Path:
        record_path = draft_root / "method_editor" / "edit_record.json"
        record_path.write_text(json.dumps(edit_record, indent=2) + "\n", encoding="utf-8")
        return record_path

    def _apply_modulus_chord_patch(
        self,
        draft_root: Path,
        values: dict[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        reduce_path = draft_root / "reduce_recipe.yaml"
        reduce_recipe = _load_yaml_for_edit(reduce_path)
        steps = reduce_recipe.get("reduce")
        if not isinstance(steps, list):
            raise MethodEditorSessionError(
                "ValidationError",
                "Draft reduce recipe does not contain a reduce step list.",
                details={"path": str(reduce_path)},
            )
        chord_step = next(
            (
                step
                for step in steps
                if isinstance(step, dict)
                and (step.get("id") == "reduce.chord_modulus" or step.get("op") == "chord_slope")
            ),
            None,
        )
        if not isinstance(chord_step, dict):
            raise MethodEditorSessionError(
                "ValidationError",
                "Draft reduce recipe does not contain the controlled chord modulus step.",
                details={"path": str(reduce_path)},
            )

        old_start = _finite_float(chord_step.get("x1"), field="current x1")
        old_end = _finite_float(chord_step.get("x2"), field="current x2")
        start = _finite_float(_first_present(values, "start_strain", "startStrain", "x1", default=old_start), field="start_strain")
        end = _finite_float(_first_present(values, "end_strain", "endStrain", "x2", default=old_end), field="end_strain")
        self._validate_chord_window(start, end)

        chord_step["x1"] = start
        chord_step["x2"] = end
        reduce_path.write_text(yaml.safe_dump(reduce_recipe, sort_keys=False), encoding="utf-8")

        applied_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "edit_id": f"edit_{uuid.uuid4().hex[:12]}",
            "applied_at": applied_at,
            "controlled_group": "modulus_chord_strain_window",
            "recipe_file": "reduce_recipe.yaml",
            "step_id": str(chord_step.get("id") or "reduce.chord_modulus"),
            "fields": {
                "x1": {"old": old_start, "new": start},
                "x2": {"old": old_end, "new": end},
            },
            "reason": reason,
            "safety": {
                "canonical_mutation_allowed": False,
                "path_scope": "generated_draft_only",
            },
        }

    def _validate_chord_window(self, start: float, end: float) -> None:
        if start < 0:
            raise MethodEditorSessionError(
                "ValidationError",
                "Modulus chord start strain must be non-negative.",
                details={"start_strain": start},
            )
        if not start < end:
            raise MethodEditorSessionError(
                "ValidationError",
                "Modulus chord start strain must be less than end strain.",
                details={"start_strain": start, "end_strain": end},
            )
        if end > 0.05:
            raise MethodEditorSessionError(
                "ValidationError",
                "Modulus chord end strain is outside the controlled editor range.",
                details={"start_strain": start, "end_strain": end, "max_end_strain": 0.05},
            )

    def _validate_draft_root(self, draft_root: Path) -> dict[str, Any]:
        checked_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        try:
            package = MethodPackage.load(draft_root)
            self._validate_loaded_package(package)
        except MethodEditorSessionError:
            raise
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated Method Editor draft does not load as a method package.",
                details={"draft_path": str(draft_root), "exception": exc.__class__.__name__},
            ) from exc
        return {
            "status": "valid",
            "loadable": True,
            "checked_at": checked_at,
            "method_id": package.method_id,
            "version": package.version,
            "warnings": [],
        }

    def _validate_loaded_package(self, package: MethodPackage) -> None:
        steps = package.reduce_recipe.get("reduce")
        if not isinstance(steps, list):
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method reduce recipe is missing reduce steps.",
                details={"draft_path": str(package.root)},
            )
        chord_step = next(
            (
                step
                for step in steps
                if isinstance(step, dict)
                and (step.get("id") == "reduce.chord_modulus" or step.get("op") == "chord_slope")
            ),
            None,
        )
        if not isinstance(chord_step, dict):
            raise MethodEditorSessionError(
                "ValidationError",
                "Generated method is missing the controlled chord modulus step.",
                details={"draft_path": str(package.root)},
            )
        start = _finite_float(chord_step.get("x1"), field="reduce.chord_modulus.x1")
        end = _finite_float(chord_step.get("x2"), field="reduce.chord_modulus.x2")
        self._validate_chord_window(start, end)

    def _rewrite_generated_method_identity(
        self,
        method_root: Path,
        *,
        method_id: str,
        version: str,
        method_name: str,
        base_method_id: str,
    ) -> None:
        for recipe_path in sorted(method_root.glob("*.yaml")):
            payload = _load_yaml_for_edit(recipe_path)
            changed = False
            if "method_id" in payload:
                payload["method_id"] = method_id
                changed = True
            if "version" in payload:
                payload["version"] = version
                changed = True
            if recipe_path.name == "method_manifest.yaml":
                payload["method_id"] = method_id
                payload["method_name"] = method_name
                payload["version"] = version
                payload["generated_from_method_id"] = base_method_id
                payload["generated_by"] = "method_editor"
                changed = True
            if changed:
                recipe_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _draft_summary(
        self,
        draft_root: Path,
        package: MethodPackage,
        edit_record: dict[str, Any],
    ) -> dict[str, Any]:
        applied_edits = edit_record.get("applied_edits")
        validation = edit_record.get("validation_summary")
        return {
            "draft_id": str(edit_record.get("draft_id") or draft_root.name),
            "draft_label": str(edit_record.get("draft_label") or package.name),
            "base_method_id": str(edit_record.get("base_method_id") or ""),
            "base_method_version": str(edit_record.get("base_method_version") or ""),
            "base_method_path": str(edit_record.get("base_method_path") or ""),
            "draft_path": str(draft_root),
            "edit_record_path": str(draft_root / "method_editor" / "edit_record.json"),
            "edit_summary_path": str(draft_root / "method_editor" / "edit_summary.md"),
            "edit_count": len(applied_edits) if isinstance(applied_edits, list) else 0,
            "loadable": bool(isinstance(validation, dict) and validation.get("loadable")),
            "validation": validation if isinstance(validation, dict) else None,
            "method": self._method_summary(package, entry=None, canonical=False),
        }

    def _generated_method_summary(
        self,
        method_root: Path,
        package: MethodPackage,
        edit_record: dict[str, Any],
    ) -> dict[str, Any]:
        applied_edits = edit_record.get("applied_edits")
        validation = edit_record.get("validation_summary")
        display_name = _display_method_name(package.name, package.version)
        return {
            "method_id": package.method_id,
            "method_name": display_name,
            "label": display_name,
            "version": package.version,
            "method_path": str(method_root),
            "source_draft_id": str(edit_record.get("source_draft_id") or ""),
            "source_draft_path": str(edit_record.get("source_draft_path") or ""),
            "base_method_id": str(edit_record.get("base_method_id") or ""),
            "base_method_version": str(edit_record.get("base_method_version") or ""),
            "edit_count": len(applied_edits) if isinstance(applied_edits, list) else 0,
            "loadable": bool(isinstance(validation, dict) and validation.get("loadable")),
            "validation": validation if isinstance(validation, dict) else None,
            "edit_record_path": str(method_root / "method_editor" / "edit_record.json"),
            "edit_summary_path": str(method_root / "method_editor" / "edit_summary.md"),
            "method": self._method_summary(package, entry=None, canonical=False),
        }

    def _write_edit_summary(self, draft_root: Path, edit_record: dict[str, Any]) -> Path:
        summary_path = draft_root / "method_editor" / "edit_summary.md"
        edits = edit_record.get("applied_edits")
        validation = edit_record.get("validation_summary")
        schema = str(edit_record.get("schema") or "")
        is_generated = schema == "method-editor-generated/v1"
        package_label = "Generated method" if is_generated else "Draft"
        package_id = edit_record.get("generated_method_id") if is_generated else edit_record.get("draft_id")
        timestamp = edit_record.get("generated_at") if is_generated else edit_record.get("created_at")
        lines = [
            "# Method Editor Generated Method" if is_generated else "# Method Editor Draft",
            "",
            f"- {package_label} ID: {package_id or draft_root.name}",
            f"- Base method: {edit_record.get('base_method_id', '')}",
            f"- Base version: {edit_record.get('base_method_version', '')}",
            f"- Created at: {timestamp or ''}",
            "- Canonical mutation allowed: false",
            "",
            "## Validation",
            "",
            f"- Status: {(validation or {}).get('status', 'not_checked') if isinstance(validation, dict) else 'not_checked'}",
            f"- Checked at: {(validation or {}).get('checked_at', '') if isinstance(validation, dict) else ''}",
            "",
            "## Applied Edits",
            "",
        ]
        if isinstance(edits, list) and edits:
            for edit in edits:
                fields = edit.get("fields") if isinstance(edit, dict) else {}
                lines.extend(
                    [
                        f"- {edit.get('applied_at', '')} `{edit.get('controlled_group', '')}`",
                        f"  - Recipe file: `{edit.get('recipe_file', '')}`",
                        f"  - Step: `{edit.get('step_id', '')}`",
                    ]
                )
                if isinstance(fields, dict):
                    for field_name, field_change in fields.items():
                        if isinstance(field_change, dict):
                            lines.append(
                                f"  - {field_name}: {field_change.get('old')} -> {field_change.get('new')}"
                            )
        else:
            lines.append("- No edits applied.")
        lines.append("")
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        return summary_path

    def _read_registry_payload(self, registry_path: Path) -> dict[str, Any]:
        try:
            payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise MethodEditorSessionError(
                "ValidationError",
                "Unable to read the method registry for generated method registration.",
                details={"registry_path": str(registry_path)},
            ) from exc
        if not isinstance(payload, dict):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method registry YAML must contain a mapping.",
                details={"registry_path": str(registry_path)},
            )
        return payload

    def _remove_generated_registry_entries(self, method_root: Path, method_id: str) -> dict[str, Any]:
        registry = self._load_registry()
        registry_payload = self._read_registry_payload(registry.path)
        methods = registry_payload.get("methods", [])
        if not isinstance(methods, list):
            raise MethodEditorSessionError(
                "ValidationError",
                "Method registry must contain a methods list.",
                details={"registry_path": str(registry.path)},
            )

        kept: list[Any] = []
        removed: list[dict[str, Any]] = []
        for item in methods:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            item_path = _registry_payload_method_path(item, registry.path.parent)
            same_id = str(item.get("method_id") or "") == method_id
            same_path = item_path is not None and item_path.resolve() == method_root.resolve()
            generated_source = str(item.get("source") or "") == "method_editor_generated"
            if (same_id or same_path) and (generated_source or same_path):
                removed.append(item)
            else:
                kept.append(item)

        if removed:
            registry_payload["methods"] = kept
            registry.path.write_text(yaml.safe_dump(registry_payload, sort_keys=False), encoding="utf-8")
        return {
            "deregistered": bool(removed),
            "removed_entry_count": len(removed),
            "registry_path": str(registry.path),
        }

    def _registry_path_value(self, path: Path) -> str:
        repo_root = _find_repo_root(path)
        if repo_root is not None:
            try:
                return path.resolve().relative_to(repo_root).as_posix()
            except ValueError:
                pass
        return str(path.resolve())

    def _registry_entry_summary(self, entry: MethodRegistryEntry, *, raw: dict[str, Any] | None = None) -> dict[str, Any]:
        generated = self._is_generated_registry_entry(entry, raw=raw)
        payload = entry.to_dict()
        payload["canonical"] = not generated
        payload["generated"] = generated
        payload["editable"] = generated
        payload["deletable"] = generated
        if generated:
            payload["label"] = _display_method_name(str(payload.get("label") or ""), str(payload.get("version") or ""))
        if raw:
            payload["source"] = str(raw.get("source") or ("method_editor_generated" if generated else "registry"))
            for key in ("base_method_id", "generated_at"):
                if key in raw:
                    payload[key] = raw[key]
        elif generated:
            payload["source"] = "method_editor_generated"
        else:
            payload["source"] = "registry"
        return payload

    def _is_generated_registry_entry(
        self,
        entry: MethodRegistryEntry | None,
        *,
        raw: dict[str, Any] | None = None,
    ) -> bool:
        if raw and str(raw.get("source") or "") == "method_editor_generated":
            return True
        if entry is None:
            return False
        try:
            return entry.method_path.resolve().is_relative_to(self.generated_root.resolve())
        except Exception:
            return False

    def _method_summary(
        self,
        package: MethodPackage,
        *,
        entry: MethodRegistryEntry | None,
        canonical: bool,
    ) -> dict[str, Any]:
        manifest = package.manifest
        display_name = _display_method_name(package.name, package.version) if not canonical else package.name
        return {
            "method_id": package.method_id,
            "method_name": display_name,
            "label": display_name,
            "version": package.version,
            "standard_reference": manifest.get("standard_reference") or manifest.get("standard") or "",
            "method_path": str(package.root),
            "canonical": canonical,
            "manifest": manifest,
            "registry_entry": entry.to_dict() if entry is not None else None,
            "recipe_files": [str(path) for path in package.recipe_files()],
            "recipe_file_count": len(package.recipe_files()),
        }


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._-") or "method"


def _normal_version(value: str | None) -> str:
    version = str(value or "").strip()
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise MethodEditorSessionError(
            "ValidationError",
            "methodEditor.generateVersion requires target_version as major.minor.patch.",
            details={"target_version": value},
        )
    return version


def _version_segment(version: str) -> str:
    return f"v{_normal_version(version).replace('.', '_')}"


def _display_method_name(name: str, version: str | None = None) -> str:
    label = str(name or "").strip()
    raw_version = str(version or "").strip().lstrip("vV")
    if raw_version:
        label = re.sub(
            rf"\s*\(generated\s+v?{re.escape(raw_version)}\)\s*$",
            "",
            label,
            flags=re.IGNORECASE,
        )
    label = re.sub(r"\s*\(generated\s+v?[0-9]+(?:\.[0-9]+){2}\)\s*$", "", label, flags=re.IGNORECASE)
    return label.strip() or str(name or "").strip() or "Generated method"


def _generated_method_id(base_method_id: str, version: str) -> str:
    return _safe_segment(f"{base_method_id}_{_version_segment(version)}")


def _find_registry_payload(methods: list[Any], method_id: str) -> dict[str, Any] | None:
    for item in methods:
        if isinstance(item, dict) and str(item.get("method_id") or "") == method_id:
            return item
    return None


def _registry_payload_method_path(item: dict[str, Any], base_path: Path) -> Path | None:
    try:
        return MethodRegistryEntry.from_dict(item, base_path=base_path).method_path
    except Exception:
        return None


def _find_repo_root(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if (candidate / "config" / "method_registry.yaml").is_file() and (candidate / "src").is_dir():
            return candidate
    return None


def _load_yaml_for_edit(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise MethodEditorSessionError(
            "ValidationError",
            "Unable to read Method Editor draft recipe YAML.",
            details={"path": str(path)},
        ) from exc
    if not isinstance(payload, dict):
        raise MethodEditorSessionError(
            "ValidationError",
            "Method Editor draft recipe YAML must contain a mapping.",
            details={"path": str(path)},
        )
    return payload


def _first_present(values: dict[str, Any], *keys: str, default: Any) -> Any:
    for key in keys:
        if key in values:
            return values[key]
    return default


def _finite_float(value: Any, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MethodEditorSessionError(
            "ValidationError",
            f"Method Editor field {field} must be numeric.",
            details={"field": field, "value": value},
        ) from exc
    if not math.isfinite(number):
        raise MethodEditorSessionError(
            "ValidationError",
            f"Method Editor field {field} must be finite.",
            details={"field": field, "value": value},
        )
    return number
