from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDPLayout, detect_mtdp_layout
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPPackageValidator
from mtdp_enrichment.package.schema import MTDPSchema
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry

from .group_state import GroupState, RunState


@dataclass(slots=True)
class PackageWorkspace:
    package_path: Path
    root: Path
    tempdir: tempfile.TemporaryDirectory[str]


class GroupLoader:
    """Load raw folders or existing .mtdp archives into editable backend state."""

    def __init__(
        self,
        *,
        registry: SchemaRegistry | None = None,
        parser: ParserAdapter | None = None,
        validator: MTDPPackageValidator | None = None,
    ) -> None:
        self.registry = registry or SchemaRegistry()
        self.parser = parser or ParserAdapter()
        self.validator = validator or MTDPPackageValidator()
        self._workspaces: list[PackageWorkspace] = []

    def load_package(self, package_path: str | Path) -> GroupState:
        package_path = Path(package_path)
        validation = self.validator.validate(package_path)
        if not validation.ok:
            raise ValueError("; ".join(validation.messages()))
        tempdir = tempfile.TemporaryDirectory(prefix="mtdp_reprocess_")
        workspace = PackageWorkspace(package_path, Path(tempdir.name), tempdir)
        self._workspaces.append(workspace)
        with zipfile.ZipFile(package_path, "r") as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
            layout = detect_mtdp_layout(names)
            manifest = json.loads(archive.read(layout.manifest).decode("utf-8"))
            dataset = json.loads(archive.read(layout.dataset).decode("utf-8"))
            provenance = json.loads(archive.read(layout.provenance).decode("utf-8"))
            schema = self.registry.get(str(manifest["schema_id"]), str(manifest["schema_version"]))
            group = GroupState(
                group_key=str(dataset.get("sample_type_key") or str(dataset.get("sample_type") or package_path.stem).casefold()),
                display_name=str(dataset.get("sample_type") or package_path.stem),
                schema=schema,
                source_package_path=package_path,
                workspace=workspace,
            )
            group.dataset_enrichment = _dataset_enrichment_from_json(schema, dataset)
            group.runs = self._runs_from_archive(archive, names, schema, dataset, provenance, workspace.root, layout)
            return group

    def _runs_from_archive(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        schema: MTDPSchema,
        dataset: dict[str, Any],
        provenance: dict[str, Any],
        workspace: Path,
        layout: type[MTDPLayout],
    ) -> list[RunState]:
        raw_by_stem = {layout.run_stem(name): name for name in names if name.startswith(layout.raw_prefix)}
        normalized_by_stem = {
            layout.run_stem(name): name
            for name in names
            if name.startswith(layout.normalized_prefix) and name.endswith(".csv")
        }
        run_ids = [str(item) for item in dataset.get("run_order", ()) or ()] or sorted(normalized_by_stem)
        provenance_runs = provenance.get("runs", {}) if isinstance(provenance.get("runs"), dict) else {}
        runs: list[RunState] = []
        for run_id in run_ids:
            raw_member = raw_by_stem.get(run_id)
            if raw_member is None:
                continue
            raw_path = _extract_member(archive, raw_member, workspace)
            parsed = self.parser.parse(raw_path)
            run = RunState(run_id=run_id, source_path=raw_path, parsed=parsed)
            normalized_member = normalized_by_stem.get(run_id)
            if normalized_member:
                run.enrichment.update(
                    _run_enrichment_from_normalized_csv(schema, archive.read(normalized_member).decode("utf-8-sig"))
                )
            run_payload = provenance_runs.get(run_id, {})
            if isinstance(run_payload, dict):
                run.enrichment.update(_run_enrichment_from_provenance(schema, run_id, run_payload))
                sidecar = _first_package_path(run_payload.get("supplemental_inputs", ()), "sidecar_yaml")
                if sidecar and sidecar in archive.namelist():
                    run.sidecar_path = _extract_member(archive, sidecar, workspace)
                    run.sidecar_import_status = "YAML imported"
            runs.append(run)
        return runs


def _dataset_enrichment_from_json(schema: MTDPSchema, dataset: dict[str, Any]) -> dict[str, EnrichedFieldValue]:
    values: dict[str, EnrichedFieldValue] = {}
    for field in schema.dataset_fields:
        if field.storage.location != "dataset_json" or not field.storage.path:
            continue
        value = _get_dotted_value(dataset, field.storage.path)
        if value not in (None, ""):
            values[field.field_id] = _field_value(value, "package_dataset")
    return values


def _run_enrichment_from_normalized_csv(schema: MTDPSchema, text: str) -> dict[str, EnrichedFieldValue]:
    values: dict[str, EnrichedFieldValue] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row:
            break
        field = schema.field_by_token(row[0])
        if field is None or len(row) < 2:
            continue
        unit = row[2] if len(row) > 2 and row[2] else None
        values[field.field_id] = EnrichedFieldValue(row[1], unit, "package_normalized")
    return values


def _run_enrichment_from_provenance(
    schema: MTDPSchema,
    run_id: str,
    payload: dict[str, Any],
) -> dict[str, EnrichedFieldValue]:
    values: dict[str, EnrichedFieldValue] = {}
    for field in schema.run_fields:
        if field.storage.location != "provenance" or not field.storage.path:
            continue
        path = field.storage.path.format(run_id=run_id)
        prefix = f"runs.{run_id}."
        if path.startswith(prefix):
            path = path[len(prefix) :]
        value = _get_dotted_value(payload, path)
        if value not in (None, ""):
            values[field.field_id] = _field_value(value, "package_provenance")
    return values


def _extract_member(archive: zipfile.ZipFile, member: str, workspace: Path) -> Path:
    target = workspace / member
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archive.read(member))
    return target


def _get_dotted_value(payload: object, path: str) -> object:
    cursor = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _field_value(value: object, source: str) -> EnrichedFieldValue:
    if isinstance(value, dict) and "value" in value:
        return EnrichedFieldValue(value.get("value"), None if value.get("unit") in (None, "") else str(value.get("unit")), source)
    return EnrichedFieldValue(value, None, source)


def _first_package_path(records: object, record_type: str) -> str | None:
    if not isinstance(records, list):
        return None
    for record in records:
        if isinstance(record, dict) and record.get("type") == record_type and isinstance(record.get("package_path"), str):
            return str(record["package_path"])
    return None
