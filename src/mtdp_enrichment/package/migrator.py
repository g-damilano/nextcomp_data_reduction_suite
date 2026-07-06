from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from archives.core.layouts import MTDPAlignedLayout, MTDPLayout, MTDPLegacyLayout, detect_mtdp_layout
from mtdp_enrichment.package.checksums import build_checksums
from mtdp_enrichment.package.manifest import build_manifest
from mtdp_enrichment.package.provenance_taxonomy import SCHEMA_MIGRATED, build_event
from mtdp_enrichment.package.schema import MTDPSchema


MIGRATION_STATUSES = {
    "clean_migration",
    "automatic_migration",
    "user_resolved_migration",
    "ambiguous_migration",
    "partial_migration",
    "blocked_migration",
    "legacy_schema_read_only",
}


@dataclass(frozen=True, slots=True)
class MigrationOperation:
    operation_type: str
    source_field: str | None = None
    target_field: str | None = None
    source_token: str | None = None
    target_token: str | None = None
    value_map: dict[str, Any] = field(default_factory=dict)
    default: Any = None
    storage: str = "token_preamble"
    requires_user: bool = False
    note: str = ""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MigrationOperation":
        return cls(
            operation_type=str(payload.get("operation", payload.get("operation_type", ""))),
            source_field=_optional_text(payload.get("source_field")),
            target_field=_optional_text(payload.get("target_field")),
            source_token=_optional_text(payload.get("source_token")),
            target_token=_optional_text(payload.get("target_token")),
            value_map={str(key): value for key, value in dict(payload.get("value_map", {}) or {}).items()},
            default=payload.get("default"),
            storage=str(payload.get("storage", "token_preamble")),
            requires_user=bool(payload.get("requires_user", False)),
            note=str(payload.get("note", "")),
        )


@dataclass(frozen=True, slots=True)
class MigrationIssue:
    code: str
    message: str
    operation: MigrationOperation | None = None
    field_id: str | None = None


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    schema_id: str
    from_schema_version: str
    to_schema_version: str
    operations: tuple[MigrationOperation, ...]
    issues: tuple[MigrationIssue, ...] = ()

    @property
    def status(self) -> str:
        if any(issue.code == "blocked" for issue in self.issues):
            return "blocked_migration"
        if any(operation.requires_user or operation.operation_type == "require_user_value" for operation in self.operations):
            return "ambiguous_migration"
        return "automatic_migration"

    @property
    def automatic_operations(self) -> tuple[MigrationOperation, ...]:
        return tuple(
            operation
            for operation in self.operations
            if not operation.requires_user and operation.operation_type != "require_user_value"
        )

    @property
    def review_operations(self) -> tuple[MigrationOperation, ...]:
        return tuple(
            operation
            for operation in self.operations
            if operation.requires_user or operation.operation_type == "require_user_value"
        )


@dataclass(frozen=True, slots=True)
class MigrationReviewState:
    plan: MigrationPlan
    unresolved_operations: tuple[MigrationOperation, ...]
    user_values: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        required = {operation.target_field or operation.source_field for operation in self.unresolved_operations}
        return all(field_id in self.user_values for field_id in required if field_id)


@dataclass(frozen=True, slots=True)
class MigrationResult:
    status: str
    message: str
    rewritten: bool = False
    plan: MigrationPlan | None = None
    review_state: MigrationReviewState | None = None


class MigrationRegistry:
    def __init__(self, migration_dirs: Sequence[str | Path] | None = None) -> None:
        if migration_dirs is None:
            migration_dirs = [Path(__file__).resolve().parents[1] / "schema_library"]
        self._plans: dict[tuple[str, str, str], MigrationPlan] = {}
        for directory in migration_dirs:
            self.load_directory(directory)

    def load_directory(self, directory: str | Path) -> None:
        root = Path(directory)
        if not root.exists():
            return
        for path in sorted(root.rglob("migrations/*.yaml")) + sorted(root.rglob("migrations/*.yml")):
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(payload, dict):
                continue
            schema_id = str(payload.get("schema_id") or _schema_id_from_path(path))
            from_version = str(payload.get("from_schema_version", ""))
            to_version = str(payload.get("to_schema_version", ""))
            operations = tuple(MigrationOperation.from_dict(item) for item in payload.get("operations", ()) or ())
            issues = tuple(
                MigrationIssue(str(item.get("code", "issue")), str(item.get("message", "")))
                for item in payload.get("issues", ()) or ()
                if isinstance(item, dict)
            )
            if schema_id and from_version and to_version:
                self._plans[(schema_id, from_version, to_version)] = MigrationPlan(
                    schema_id=schema_id,
                    from_schema_version=from_version,
                    to_schema_version=to_version,
                    operations=operations,
                    issues=issues,
                )

    def plan(self, schema_id: str, from_version: str, to_version: str) -> MigrationPlan | None:
        return self._plans.get((schema_id, from_version, to_version))


class MTDPMigrator:
    def __init__(self, registry: MigrationRegistry | None = None) -> None:
        self.registry = registry or MigrationRegistry()

    def migration_status(
        self,
        package_schema_id: str,
        package_schema_version: str,
        current_schema_id: str,
        current_schema_version: str,
    ) -> MigrationResult:
        if package_schema_id == current_schema_id and package_schema_version == current_schema_version:
            return MigrationResult("clean_migration", "Package schema is current.", rewritten=False)
        if package_schema_id != current_schema_id:
            return MigrationResult(
                "legacy_schema_read_only",
                "Package schema ID differs from the selected current schema.",
                rewritten=False,
            )
        plan = self.registry.plan(current_schema_id, package_schema_version, current_schema_version)
        if plan is None:
            return MigrationResult(
                "blocked_migration",
                "Schema version differs and no migration path is registered.",
                rewritten=False,
            )
        review = MigrationReviewState(plan=plan, unresolved_operations=plan.review_operations)
        return MigrationResult(plan.status, f"Migration path has {len(plan.operations)} operation(s).", False, plan, review)

    def migrate_package(
        self,
        input_path: str | Path,
        output_path: str | Path,
        target_schema: MTDPSchema,
        *,
        user_values: Mapping[str, Any] | None = None,
    ) -> MigrationResult:
        input_path = Path(input_path)
        output_path = Path(output_path)
        with zipfile.ZipFile(input_path, "r") as archive:
            files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
        layout = _detect_layout_for_files(files)
        manifest = json.loads(files[layout.manifest].decode("utf-8"))
        status = self.migration_status(
            str(manifest.get("schema_id")),
            str(manifest.get("schema_version")),
            target_schema.schema_id,
            target_schema.schema_version,
        )
        if status.plan is None:
            return status
        unresolved = [
            operation
            for operation in status.plan.review_operations
            if not user_values or (operation.target_field or operation.source_field or "") not in user_values
        ]
        if unresolved:
            review = MigrationReviewState(status.plan, tuple(unresolved), dict(user_values or {}))
            return MigrationResult(
                "ambiguous_migration",
                "Migration requires user-confirmed values before writing.",
                False,
                status.plan,
                review,
            )

        migrated = self.apply_plan_to_files(files, target_schema, status.plan, user_values=dict(user_values or {}))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(migrated.items()):
                archive.writestr(name, content)
        return MigrationResult(
            "user_resolved_migration" if status.plan.review_operations else "automatic_migration",
            "Package migrated.",
            True,
            status.plan,
            None,
        )

    def apply_plan_to_files(
        self,
        files: Mapping[str, bytes],
        target_schema: MTDPSchema,
        plan: MigrationPlan,
        *,
        user_values: Mapping[str, Any] | None = None,
    ) -> dict[str, bytes]:
        user_values = user_values or {}
        migrated = dict(files)
        layout = _detect_layout_for_files(migrated)
        for name in list(migrated):
            if name.startswith(layout.normalized_prefix) and name.endswith(".csv"):
                migrated[name] = _apply_operations_to_token_csv(migrated[name], plan.operations, user_values)
        dataset = json.loads(migrated.get(layout.dataset, b"{}").decode("utf-8"))
        for operation in plan.operations:
            if operation.storage == "dataset_json" and operation.operation_type == "map_enum_value":
                _map_dataset_enum_value(dataset, target_schema, operation)
            if operation.storage != "dataset_json" or operation.operation_type != "require_user_value":
                continue
            field_id = operation.target_field or operation.source_field
            if field_id and field_id in user_values:
                field = target_schema.field_by_id(field_id)
                path = field.storage.path if field and field.storage.path else field_id
                _set_dotted_value(dataset, path, user_values[field_id])
        run_order = dataset.get("run_order")
        if not run_order:
            dataset["run_order"] = sorted(
                layout.run_stem(name)
                for name in migrated
                if name.startswith(layout.normalized_prefix) and name.endswith(".csv")
            )
        migrated[layout.dataset] = _json_bytes(dataset)
        manifest = build_manifest(target_schema)
        migrated[layout.manifest] = _json_bytes(manifest)
        migrated[layout.schema] = _json_bytes(target_schema.to_dict())
        provenance = json.loads(migrated.get(layout.provenance, b"{}").decode("utf-8"))
        provenance.setdefault("migration_events", []).append(
            build_event(
                SCHEMA_MIGRATED,
                scope="dataset",
                details={
                    "from_schema": f"{plan.schema_id}@{plan.from_schema_version}",
                    "to_schema": f"{plan.schema_id}@{plan.to_schema_version}",
                    "status": "user_resolved_migration" if plan.review_operations else "automatic_migration",
                    "operations": [operation.operation_type for operation in plan.operations],
                    "user_resolved_fields": sorted(user_values),
                },
            )
        )
        migrated[layout.provenance] = _json_bytes(provenance)
        for checksum_member in ("checksums.json", "metadata/checksums.json", "software/checksums.json"):
            migrated.pop(checksum_member, None)
        migrated[layout.checksums] = _json_bytes(build_checksums(migrated, checksum_member=layout.checksums))
        return migrated


def _detect_layout_for_files(files: Mapping[str, bytes]) -> type[MTDPLayout]:
    names = set(files)
    try:
        return detect_mtdp_layout(names)
    except ValueError:
        if any(name.startswith(MTDPAlignedLayout.normalized_prefix) for name in names) or any(
            name in {
                MTDPAlignedLayout.dataset,
                MTDPAlignedLayout.provenance,
                MTDPAlignedLayout.schema,
                MTDPAlignedLayout.checksums,
            }
            for name in names
        ):
            return MTDPAlignedLayout
        return MTDPLegacyLayout


def _apply_operations_to_token_csv(
    content: bytes,
    operations: Sequence[MigrationOperation],
    user_values: Mapping[str, Any],
) -> bytes:
    text = content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    preamble_end = next((index for index, row in enumerate(rows) if not row), len(rows))
    preamble = rows[:preamble_end]
    body = rows[preamble_end:]

    for operation in operations:
        if operation.storage != "token_preamble":
            continue
        if operation.operation_type in {"rename_token", "rename_field"}:
            _rename_token(preamble, operation.source_token, operation.target_token)
        elif operation.operation_type == "map_enum_value":
            _map_enum_token(preamble, operation)
        elif operation.operation_type == "set_default":
            token = operation.target_token or operation.target_field
            if token and not _find_row(preamble, token):
                preamble.append([token, str(operation.default)])
        elif operation.operation_type == "require_user_value":
            field_id = operation.target_field or operation.source_field
            token = operation.target_token or field_id
            if field_id and token and field_id in user_values:
                row = _find_row(preamble, token)
                if row is None:
                    preamble.append([token, str(user_values[field_id])])
                else:
                    row[:] = [token, str(user_values[field_id])]
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows([*preamble, *body])
    return output.getvalue().encode("utf-8")


def _rename_token(preamble: list[list[str]], source_token: str | None, target_token: str | None) -> None:
    if not source_token or not target_token:
        return
    row = _find_row(preamble, source_token)
    if row is not None:
        row[0] = target_token


def _map_enum_token(preamble: list[list[str]], operation: MigrationOperation) -> None:
    source_token = operation.source_token or operation.source_field
    target_token = operation.target_token or operation.target_field
    if not source_token or not target_token:
        return
    row = _find_row(preamble, source_token)
    if row is None:
        return
    source_value = row[1] if len(row) > 1 else ""
    mapped = operation.value_map.get(str(source_value), operation.value_map.get(str(source_value).casefold(), source_value))
    row[:] = [target_token, str(mapped)]


def _find_row(preamble: list[list[str]], token: str) -> list[str] | None:
    token_norm = token.strip().casefold()
    return next((row for row in preamble if row and row[0].strip().casefold() == token_norm), None)


def _set_dotted_value(payload: dict[str, Any], path: str, value: Any) -> None:
    cursor = payload
    parts = [part for part in path.split(".") if part]
    for part in parts[:-1]:
        next_value = cursor.setdefault(part, {})
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    if parts:
        cursor[parts[-1]] = value


def _get_dotted_value(payload: dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in [part for part in path.split(".") if part]:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return cursor


def _delete_dotted_value(payload: dict[str, Any], path: str) -> None:
    cursor: Any = payload
    parts = [part for part in path.split(".") if part]
    for part in parts[:-1]:
        if not isinstance(cursor, dict):
            return
        cursor = cursor.get(part)
    if isinstance(cursor, dict) and parts:
        cursor.pop(parts[-1], None)


def _map_dataset_enum_value(dataset: dict[str, Any], target_schema: MTDPSchema, operation: MigrationOperation) -> None:
    source_field = target_schema.field_by_id(operation.source_field or operation.target_field or "")
    target_field = target_schema.field_by_id(operation.target_field or operation.source_field or "")
    if source_field is None or target_field is None or not source_field.storage.path or not target_field.storage.path:
        return
    source_value = _get_dotted_value(dataset, source_field.storage.path)
    if source_value in (None, ""):
        return
    mapped = operation.value_map.get(str(source_value), operation.value_map.get(str(source_value).casefold()))
    if mapped in (None, ""):
        if source_field.storage.path == target_field.storage.path:
            _delete_dotted_value(dataset, target_field.storage.path)
        return
    _set_dotted_value(dataset, target_field.storage.path, mapped)


def _schema_id_from_path(path: Path) -> str:
    parts = path.parts
    try:
        mechanical = parts.index("mechanical")
    except ValueError:
        return ""
    return ".".join(parts[mechanical : mechanical + 2])


def _optional_text(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
