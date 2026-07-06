from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from methods.core.method_package import MethodPackage


class MethodEditorExportError(Exception):
    def __init__(
        self,
        error_type: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


@dataclass(slots=True)
class MethodEditorExportService:
    """Writes generated Method Editor packages as external method files."""

    generated_root: Path

    def export_generated_method(
        self,
        method_root: Path,
        package: MethodPackage,
        *,
        output_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        exported_at = datetime.now(UTC)
        export_slug = (
            f"{_safe_segment(package.method_id)}_"
            f"{_safe_segment(package.version)}_"
            f"{exported_at.strftime('%Y%m%d_%H%M%S')}"
        )
        target = self._target_path(output_path, default_name=export_slug)
        if target.resolve().is_relative_to(method_root.resolve()):
            raise MethodEditorExportError(
                "ValidationError",
                "Method Editor export target cannot be inside the generated method package.",
                details={"method_path": str(method_root), "export_path": str(target)},
            )
        if target.exists():
            if not overwrite:
                raise MethodEditorExportError(
                    "ValidationError",
                    "Method Editor export target already exists.",
                    details={"export_path": str(target)},
                )
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)

        files = list(_package_files(method_root))
        if target.suffix.lower() == ".zip":
            file_count, byte_count = self._write_zip(method_root, target, package, files)
            export_kind = "zip"
        else:
            file_count, byte_count = self._write_directory(method_root, target, files)
            export_kind = "directory"

        return {
            "method_id": package.method_id,
            "version": package.version,
            "method_path": str(method_root),
            "export_path": str(target),
            "export_kind": export_kind,
            "export_name": target.name,
            "archive_name": target.name if export_kind == "zip" else "",
            "file_count": file_count,
            "byte_count": byte_count,
            "files": [path.relative_to(method_root).as_posix() for path in files],
            "exported_at": exported_at.isoformat().replace("+00:00", "Z"),
        }

    def _target_path(self, output_path: str | Path | None, *, default_name: str) -> Path:
        output_ref = str(output_path or "").strip()
        if not output_ref:
            return (self.generated_root / "exports" / default_name).resolve()
        target = Path(output_ref).resolve()
        if target.exists() and target.is_dir():
            return target / default_name
        return target

    def _write_directory(
        self,
        method_root: Path,
        target: Path,
        files: list[Path],
    ) -> tuple[int, int]:
        total_bytes = 0
        for source in files:
            relative = source.relative_to(method_root)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            total_bytes += destination.stat().st_size
        return len(files), total_bytes

    def _write_zip(
        self,
        method_root: Path,
        target: Path,
        package: MethodPackage,
        files: list[Path],
    ) -> tuple[int, int]:
        archive_root = _safe_segment(package.method_id)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in files:
                relative = source.relative_to(method_root).as_posix()
                archive.write(source, f"{archive_root}/{relative}")
        return len(files), target.stat().st_size


def _package_files(method_root: Path) -> list[Path]:
    return sorted(
        path
        for path in method_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(method_root).parts
    )


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._-") or "method"
