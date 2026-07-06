from __future__ import annotations

import json
import hashlib
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from acceptance.human_decision import decisions_from_payload
from acceptance.selection_editor import SelectionEditor
from archives.core.layouts import MTDAAlignedLayout, detect_mtdp_layout, report_member
from archives.core.json_io import json_text
from archives.mtda import MTDAWriter
from archives.mtdp import MTDPPackageReader
from audit.method_development_report_builder import MethodDevelopmentReportBuilder
from audit.operation_trace import build_operation_trace
from compatibility import CompatibilityStatus, SchemaMethodCompatibilityChecker
from mapping import MappingCandidateDiscovery, build_mapping_resolution_report, normalize_mapping_profile
from methods.core.method_executor import MethodExecutor
from methods.core.method_package import MethodPackage
from readiness import MethodReadinessError, ReadinessChecker
from readiness.readiness_report import ReadinessReport


_ALIGNED_TEST_REPORT_HTML = report_member("test_report.html")
_ALIGNED_TEST_REPORT_JSON = report_member("test_report.json")
_ALIGNED_AUDIT_REPORT_HTML = report_member("audit_report.html")
_LEGACY_TEST_REPORT_JSON = "report/test_report.json"
_LEGACY_VALIDATION_JSON = "software/validation.json"


@dataclass(frozen=True, slots=True)
class MethodRunRequest:
    input_package_path: Path
    method_path: Path
    mapping_path: Path
    output_path: Path
    overwrite: bool = False
    generate_workbench: bool = False
    human_decisions: tuple[dict[str, Any], ...] = ()
    report_overrides: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class PackageLoadResult:
    path: Path
    run_count: int
    schema_id: str | None
    sample_type: str | None
    schema_version: str | None = None
    manifest_id: str | None = None
    group_count: int = 0
    source_file_count: int = 0
    normalized_file_count: int = 0
    raw_file_count: int = 0
    included_count: int = 0
    excluded_count: int = 0
    channel_roles: tuple[str, ...] = ()
    available_channels: tuple[str, ...] = ()
    metadata_coverage: tuple[dict[str, Any], ...] = ()
    runs: tuple[dict[str, Any], ...] = ()
    source_identity_warnings: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    sample_preview: tuple[str, ...] = ()
    checksum_status: str = ""
    checksum_sha256: str = ""
    provenance_status: str = ""
    report_completion: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MethodLoadResult:
    path: Path
    method_id: str
    method_name: str
    version: str
    has_method_inputs: bool
    status: str | None = None
    analysis_type: str | None = None
    standard_reference: str | None = None
    expected_outputs: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()
    recipe_steps: tuple[str, ...] = ()
    phases: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MappingLoadResult:
    path: Path
    mapping_id: str | None
    method_id: str | None
    mapped_fields: tuple[dict[str, Any], ...] = ()
    status: str = "complete"
    summary: dict[str, Any] = field(default_factory=dict)
    compatibility_report: dict[str, Any] = field(default_factory=dict)
    candidate_report: dict[str, Any] = field(default_factory=dict)
    resolution_report: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MethodRunServiceResult:
    status: str
    readiness_status: str
    output_path: Path | None
    audit_report_path: str | None = None
    workbench_path: Path | None = None
    validation_summary: dict[str, Any] = field(default_factory=dict)
    acceptance_summary: dict[str, Any] = field(default_factory=dict)
    acceptance_report: dict[str, Any] = field(default_factory=dict)
    readiness_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    archive_members: tuple[str, ...] = ()
    report_summary: dict[str, Any] = field(default_factory=dict)
    report_artifacts: tuple[str, ...] = ()


class MethodRunService:
    """Backend facade for CLI and future Method Run Wizard."""

    def __init__(
        self,
        *,
        package_reader: MTDPPackageReader | None = None,
        executor: MethodExecutor | None = None,
        writer: MTDAWriter | None = None,
        readiness_checker: ReadinessChecker | None = None,
    ) -> None:
        self.package_reader = package_reader or MTDPPackageReader()
        self.executor = executor or MethodExecutor()
        self.writer = writer or MTDAWriter()
        self.readiness_checker = readiness_checker or ReadinessChecker()

    def load_package(self, path: str | Path) -> PackageLoadResult:
        source = self.package_reader.read(path)
        repeated = _repeated_basenames(source.runs)
        channel_roles = tuple(_channel_roles(source))
        warnings = tuple(f"Repeated basename detected: {name}" for name in sorted(repeated))
        archive_summary = _package_archive_summary(source.path)
        return PackageLoadResult(
            path=source.path,
            run_count=len(source.runs),
            schema_id=str(source.manifest.get("schema_id") or source.schema.get("schema_id") or ""),
            schema_version=str(source.manifest.get("schema_version") or source.schema.get("version") or ""),
            manifest_id=str(source.manifest.get("package_id") or source.manifest.get("manifest_id") or ""),
            sample_type=str(source.dataset.get("sample_type") or ""),
            group_count=_group_count(source.dataset),
            source_file_count=len(source.runs),
            normalized_file_count=archive_summary["normalized_file_count"],
            raw_file_count=archive_summary["raw_file_count"],
            included_count=len(source.runs),
            excluded_count=0,
            channel_roles=channel_roles,
            available_channels=channel_roles,
            metadata_coverage=tuple(_metadata_coverage(source)),
            runs=tuple(_run_preview_rows(source)),
            source_identity_warnings=warnings,
            warnings=warnings,
            sample_preview=tuple(
                f"{run.run_id}: {run.original_filename or run.normalized_package_path}"
                for run in source.runs[:5]
            ),
            checksum_status=archive_summary["checksum_status"],
            checksum_sha256=archive_summary["checksum_sha256"],
            provenance_status=archive_summary["provenance_status"],
            report_completion=_package_report_completion(source),
        )

    def load_method(self, path: str | Path) -> MethodLoadResult:
        method = MethodPackage.load(path)
        return MethodLoadResult(
            path=method.root,
            method_id=method.method_id,
            method_name=method.name,
            version=method.version,
            has_method_inputs=bool(method.method_inputs),
            status=str(method.manifest.get("status") or "active"),
            analysis_type=str(method.manifest.get("analysis_type") or ""),
            standard_reference=str(method.manifest.get("standard_reference") or "ISO 14126"),
            expected_outputs=tuple(_expected_outputs(method.manifest)),
            required_inputs=tuple(_required_inputs(method.method_inputs)),
            recipe_steps=tuple(_recipe_step_ids(method)),
            phases=tuple(_method_phases(method)),
            limitations=tuple(str(item) for item in method.manifest.get("limitations", []) if item) if isinstance(method.manifest.get("limitations"), list) else (),
        )

    def load_mapping(
        self,
        path: str | Path,
        method_path: str | Path | None = None,
        package_path: str | Path | None = None,
    ) -> MappingLoadResult:
        mapping = load_mapping(path)
        method_inputs = MethodPackage.load(method_path).method_inputs if method_path else {}
        source = self.package_reader.read(package_path) if package_path else None
        method = MethodPackage.load(method_path) if method_path else None
        candidate_report = (
            MappingCandidateDiscovery().discover(source=source, method_package=method)
            if source is not None and method is not None
            else {}
        )
        compatibility_report = (
            SchemaMethodCompatibilityChecker().check(source=source, method_package=method).to_dict()
            if source is not None and method is not None
            else {}
        )
        resolution_report = build_mapping_resolution_report(mapping=mapping, candidate_report=candidate_report) if candidate_report else {}
        rows = _mapping_rows(mapping, method_inputs, source=source, resolution_report=resolution_report)
        return MappingLoadResult(
            path=Path(path),
            mapping_id=str(mapping.get("mapping_id")) if mapping.get("mapping_id") else None,
            method_id=str(mapping.get("method_id")) if mapping.get("method_id") else None,
            mapped_fields=tuple(rows),
            status=_mapping_status(rows),
            summary=_mapping_summary(rows),
            compatibility_report=compatibility_report,
            candidate_report=candidate_report,
            resolution_report=resolution_report,
        )

    def check_readiness(self, request: MethodRunRequest) -> ReadinessReport:
        source = self.package_reader.read(request.input_package_path)
        method = MethodPackage.load(request.method_path)
        mapping = load_mapping(request.mapping_path)
        return self.readiness_checker.check(source=source, method_package=method, mapping=mapping)

    def run(
        self,
        request: MethodRunRequest,
        *,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> MethodRunServiceResult:
        output_path = Path(request.output_path)
        if output_path.exists() and not request.overwrite:
            return MethodRunServiceResult(
                status="error",
                readiness_status="UNKNOWN",
                output_path=None,
                errors=[f"Output already exists: {output_path}"],
            )
        _service_progress(progress_callback, phase="load_input_package", message="Loading MTDP package")
        source = self.package_reader.read(request.input_package_path)
        _service_progress(
            progress_callback,
            phase="load_input_package",
            message=f"Loaded MTDP package with {len(source.runs)} run{'s' if len(source.runs) != 1 else ''}",
            source=source,
            status="queued",
            note="waiting for method inputs",
        )
        _service_progress(progress_callback, phase="load_method_package", message="Loading method package", source=source)
        method = MethodPackage.load(request.method_path)
        _service_progress(progress_callback, phase="load_mapping", message="Loading mapping profile", source=source)
        mapping = load_mapping(request.mapping_path)
        _service_progress(
            progress_callback,
            phase="readiness_check",
            message="Checking method/package compatibility",
            source=source,
        )
        compatibility = SchemaMethodCompatibilityChecker().check(source=source, method_package=method)
        if compatibility.status == CompatibilityStatus.SCHEMA_EXTENSION_REQUIRED:
            return MethodRunServiceResult(
                status="not_ready",
                readiness_status="SCHEMA_EXTENSION_REQUIRED",
                output_path=None,
                errors=[
                    f"Schema-method compatibility failed: {row.source_role}"
                    for row in compatibility.requirements
                    if row.severity == "execution_critical" and not row.compatible
                ],
            )
        _service_progress(progress_callback, phase="readiness_check", message="Checking package readiness", source=source)
        readiness = self.readiness_checker.check(source=source, method_package=method, mapping=mapping)
        if readiness.blocks_execution:
            return MethodRunServiceResult(
                status="not_ready",
                readiness_status=readiness.status.value,
                output_path=None,
                readiness_summary=readiness.summary,
                warnings=list(readiness.warnings),
                errors=_readiness_errors(readiness),
            )
        try:
            result = self.executor.execute(
                source,
                method,
                mapping,
                progress_callback=progress_callback,
                cancel_requested=cancel_requested,
            )
        except MethodReadinessError as exc:
            return MethodRunServiceResult(
                status="not_ready",
                readiness_status=exc.report.status.value,
                output_path=None,
                readiness_summary=exc.report.summary,
                warnings=list(exc.report.warnings),
                errors=_readiness_errors(exc.report),
            )
        if request.human_decisions:
            _service_progress(
                progress_callback,
                phase="acceptance",
                message="Applying operator acceptance decisions",
                source=source,
                status="running",
                note="applying review overrides",
            )
            final_selection = SelectionEditor().apply(
                specimen_results=result.specimen_results,
                acceptance_report=result.acceptance_report,
                machine_selection_sets=result.selection_sets,
                machine_selection_membership=result.selection_membership,
                decisions=decisions_from_payload(list(request.human_decisions)),
            )
            result = replace(
                result,
                human_decisions=final_selection.human_decisions,
                human_decision_rows=final_selection.human_decision_rows,
                override_ledger=final_selection.override_ledger,
                override_ledger_rows=final_selection.override_ledger_rows,
                selection_sets_final=final_selection.selection_sets_final,
                selection_membership_final=final_selection.selection_membership_final,
                final_report_runs=final_selection.final_report_runs,
            )
        if request.report_overrides:
            result = replace(result, report_overrides=tuple(request.report_overrides))
        _service_progress(
            progress_callback,
            phase="write_mtda",
            message="Writing MTDA archive",
            source=source,
            status="running",
            note="writing output artifacts",
        )
        written = self.writer.write(result, output_path)
        _service_progress(
            progress_callback,
            phase="build_audit_report",
            message="Building audit report",
            source=source,
            status="running",
            note="assembling report surfaces",
        )
        workbench_path = _write_workbench(result, output_path) if request.generate_workbench else None
        if request.generate_workbench:
            _service_progress(
                progress_callback,
                phase="build_workbench_optional",
                message="Building Method Development Workbench",
                source=source,
                status="running",
                note="creating development workbench",
            )
        report_artifacts = tuple(
            member for member in written.members if member.startswith(MTDAAlignedLayout.reports_prefix)
        )
        report_completion_status = _report_completion_status_from_archive(written.path)
        _service_progress(
            progress_callback,
            phase="complete",
            message="Method run complete",
            source=source,
            status="done",
            note="output ready",
        )
        return MethodRunServiceResult(
            status="completed",
            readiness_status=str(result.readiness_report.get("status", readiness.status.value)),
            output_path=written.path,
            audit_report_path=_ALIGNED_AUDIT_REPORT_HTML,
            workbench_path=workbench_path,
            validation_summary=dict(result.validation_report.get("summary", {})),
            acceptance_summary=dict(result.acceptance_report.get("summary", {})),
            acceptance_report=dict(result.acceptance_report),
            readiness_summary=dict(result.readiness_report.get("summary", {})),
            warnings=[str(warning.get("message")) for warning in result.warnings],
            archive_members=written.members,
            report_summary={
                "report_artifact_count": len(report_artifacts),
                "test_report_html": _ALIGNED_TEST_REPORT_HTML in report_artifacts,
                "test_report_json": _ALIGNED_TEST_REPORT_JSON in report_artifacts,
                "audit_report_html": _ALIGNED_AUDIT_REPORT_HTML in report_artifacts,
                "iso_report_html": report_member("iso14126_report.html") in report_artifacts,
                "iso_report_json": report_member("iso14126_report.json") in report_artifacts,
                "report_completion_status": report_completion_status.get("status", ""),
                "missing_report_field_count": report_completion_status.get("missing_field_count", 0),
                "required_missing_count": report_completion_status.get("required_missing_count", 0),
                "recommended_missing_count": report_completion_status.get("recommended_missing_count", 0),
                "override_count": len(request.report_overrides),
            },
            report_artifacts=report_artifacts,
        )


def load_mapping(path: str | Path) -> dict[str, Any]:
    mapping_path = Path(path)
    text = mapping_path.read_text(encoding="utf-8")
    if mapping_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Mapping file must contain an object: {mapping_path}")
    return normalize_mapping_profile(payload)


def _service_progress(
    callback: Callable[[dict[str, Any]], None] | None,
    *,
    phase: str,
    message: str,
    source: Any | None = None,
    status: str = "running",
    note: str = "",
) -> None:
    if callback is None:
        return
    payload: dict[str, Any] = {
        "phase": phase,
        "message": message,
        "status": status,
    }
    runs = getattr(source, "runs", ()) if source is not None else ()
    if runs:
        payload["runs"] = {run.run_id: status for run in runs}
        payload["notes"] = {run.run_id: note or message for run in runs}
    callback(payload)


def _report_completion_status_from_archive(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for member in (_ALIGNED_TEST_REPORT_JSON, _LEGACY_TEST_REPORT_JSON):
                if member in names:
                    report = json.loads(archive.read(member))
                    completion = report.get("report_completion_status") if isinstance(report, dict) else None
                    if isinstance(completion, dict):
                        return completion
            for member in (MTDAAlignedLayout.validation, _LEGACY_VALIDATION_JSON):
                if member in names:
                    validation = json.loads(archive.read(member))
                    quality_gate = validation.get("report_quality_gate") if isinstance(validation, dict) else None
                    completion = quality_gate.get("report_completion_status") if isinstance(quality_gate, dict) else None
                    if isinstance(completion, dict):
                        return completion
    except (KeyError, OSError, zipfile.BadZipFile, json.JSONDecodeError):
        return {}
    return {}


def _group_count(dataset: dict[str, Any]) -> int:
    groups = dataset.get("groups")
    if isinstance(groups, list):
        return len(groups)
    return 1 if dataset.get("sample_type") else 0


def _channel_roles(source: Any) -> list[str]:
    roles: list[str] = []
    for run in source.runs[:1]:
        roles.extend(str(name) for name in run.channels)
    return sorted(roles)


def _metadata_coverage(source: Any) -> list[dict[str, Any]]:
    fields: list[str] = []
    for run in source.runs:
        for name in run.tokens:
            if name not in fields:
                fields.append(name)
    rows: list[dict[str, Any]] = []
    total = len(source.runs)
    for field in sorted(fields):
        present = sum(1 for run in source.runs if run.token(field) is not None)
        ratio = present / total if total else 0
        rows.append(
            {
                "field": field,
                "present": present,
                "total": total,
                "status": "pass" if ratio >= 1 else "warn" if present else "fail",
            }
        )
    return rows


def _package_report_completion(source: Any) -> dict[str, Any]:
    fields = [
        field for field in list(source.schema.get("dataset_fields", []) or []) + list(source.schema.get("run_fields", []) or [])
        if isinstance(field, dict) and field.get("report_role") and str(field.get("report_importance") or "") in {"required", "recommended"}
    ]
    required_missing = 0
    recommended_missing = 0
    present = 0
    missing_rows: list[dict[str, Any]] = []
    for field in fields:
        value = _source_value_for_schema_field(source, field)
        if value not in (None, ""):
            present += 1
            continue
        row = {
            "field_id": field.get("field_id"),
            "report_role": field.get("report_role"),
            "report_importance": field.get("report_importance"),
            "label": field.get("label") or field.get("field_id"),
        }
        missing_rows.append(row)
        if field.get("report_importance") == "required":
            required_missing += 1
        else:
            recommended_missing += 1
    status = "INCOMPLETE" if required_missing else "COMPLETE_WITH_WARNINGS" if recommended_missing else "COMPLETE"
    return {
        "status": status,
        "field_count": len(fields),
        "present_count": present,
        "required_missing_count": required_missing,
        "recommended_missing_count": recommended_missing,
        "missing_fields": missing_rows,
    }


def _source_value_for_schema_field(source: Any, field: dict[str, Any]) -> Any:
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    location = str(storage.get("location") or "")
    if location == "dataset_json":
        return _dotted_value(source.dataset, str(storage.get("path") or ""))
    if location == "token_preamble":
        token = str(storage.get("token") or "")
        for run in source.runs:
            run_token = run.token(token)
            if run_token is not None and run_token.value not in (None, ""):
                return run_token.value
    if location == "provenance":
        path = str(storage.get("path") or "")
        for run in source.runs:
            local_path = path.format(run_id=run.run_id)
            prefix = f"runs.{run.run_id}."
            if local_path.startswith(prefix):
                local_path = local_path[len(prefix):]
            value = _dotted_value(run.provenance, local_path)
            if isinstance(value, dict) and "value" in value:
                value = value.get("value")
            if value not in (None, ""):
                return value
    return None


def _dotted_value(payload: Any, path: str) -> Any:
    cursor = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    if isinstance(cursor, dict) and "value" in cursor:
        return cursor.get("value")
    return cursor


def _run_preview_rows(source: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in source.runs:
        provenance = run.provenance if isinstance(run.provenance, dict) else {}
        source_path = (
            provenance.get("source_display_name")
            or provenance.get("source_relative_path")
            or run.original_filename
            or run.raw_package_path
            or run.normalized_package_path
        )
        source_relative_path = (
            provenance.get("source_relative_path")
            or run.original_filename
            or run.raw_package_path
            or run.normalized_package_path
        )
        validity = run.token("Validity")
        failure_mode = run.token("Failure mode") or run.token("Failure Mode")
        rows.append(
            {
                "run_id": run.run_id,
                "display_name": f"{run.run_id} {source_path}",
                "source_relative_path": source_relative_path,
                "original_filename": provenance.get("original_filename") or run.original_filename or "",
                "raw_package_path": run.raw_package_path or "",
                "normalized_package_path": run.normalized_package_path or "",
                "validity_flag": validity.value if validity else "",
                "failure_mode": failure_mode.value if failure_mode else "",
                "channels_present": sorted(run.channels),
            }
        )
    return rows


def _repeated_basenames(runs: Any) -> set[str]:
    counts: dict[str, int] = {}
    for run in runs:
        name = Path(str(run.original_filename or run.raw_package_path or run.normalized_package_path)).name
        counts[name] = counts.get(name, 0) + 1
    return {name for name, count in counts.items() if count > 1}


def _package_archive_summary(path: Path) -> dict[str, Any]:
    summary = {
        "normalized_file_count": 0,
        "raw_file_count": 0,
        "checksum_status": "unavailable",
        "checksum_sha256": "",
        "provenance_status": "unavailable",
    }
    try:
        with zipfile.ZipFile(path) as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
    except (OSError, zipfile.BadZipFile):
        return summary
    try:
        layout = detect_mtdp_layout(names)
    except ValueError:
        layout = None
    if layout is not None:
        summary["normalized_file_count"] = sum(1 for name in names if name.startswith(layout.normalized_prefix))
        summary["raw_file_count"] = sum(1 for name in names if name.startswith(layout.raw_prefix))
        summary["checksum_status"] = "present" if layout.checksums in names else "missing"
        summary["provenance_status"] = "present" if layout.provenance in names else "missing"
    else:
        summary["normalized_file_count"] = sum(1 for name in names if name.startswith("normalized/"))
        summary["raw_file_count"] = sum(1 for name in names if name.startswith("raw/"))
        summary["checksum_status"] = "present" if "checksums.json" in names else "missing"
        summary["provenance_status"] = "present" if "provenance.json" in names else "missing"
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        summary["checksum_sha256"] = digest.hexdigest()
    except OSError:
        summary["checksum_sha256"] = ""
    return summary


def _expected_outputs(manifest: dict[str, Any]) -> list[str]:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        return []
    rows: list[str] = []
    for category, values in outputs.items():
        if isinstance(values, list):
            rows.extend(f"{category}.{value}" for value in values)
    return rows


def _required_inputs(method_inputs: dict[str, Any]) -> list[str]:
    requirements = method_inputs.get("inputs") or method_inputs.get("requirements") or []
    if not isinstance(requirements, list):
        return []
    rows: list[str] = []
    for item in requirements:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("category") or item.get("severity") or "")
        if severity in {"execution_critical", "critical"}:
            rows.append(str(item.get("method_field") or item.get("field") or item.get("requirement_id") or item.get("id") or item.get("name")))
    return [row for row in rows if row]


def _recipe_step_ids(method: MethodPackage) -> list[str]:
    steps: list[str] = []
    for recipe in (method.resolve_recipe, method.reduce_recipe):
        for step in recipe.get("steps", []) if isinstance(recipe, dict) else []:
            if isinstance(step, dict) and step.get("id"):
                steps.append(str(step["id"]))
    return steps


def _method_phases(method: MethodPackage) -> list[str]:
    phases = ["resolve", "reduce"]
    if method.validation_recipe:
        phases.append("validation")
    if method.acceptance_recipe:
        phases.append("acceptance")
    if method.report_recipe:
        phases.append("report")
    return phases


def _mapping_rows(
    mapping: dict[str, Any],
    method_inputs: dict[str, Any] | None = None,
    *,
    source: Any | None = None,
    resolution_report: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    requirements = method_inputs.get("requirements", []) if isinstance(method_inputs, dict) else []
    resolution_by_role = {
        str(row.get("source_role")): row
        for row in (resolution_report or {}).get("resolutions", [])
        if isinstance(row, dict)
    }
    if isinstance(requirements, list) and requirements:
        rows = []
        for item in requirements:
            if not isinstance(item, dict):
                continue
            if not _mapping_requirement_applies(item, mapping):
                continue
            source_role = str(item.get("source_role") or "")
            mapped_source, source_kind = _mapped_source_for_role(mapping, source_role)
            resolution = resolution_by_role.get(source_role, {})
            resolution_status = str(resolution.get("status") or "")
            availability = _availability_for_mapped_source(source, source_kind, mapped_source, requirement=item)
            status = _mapped_row_status(item, mapped_source, resolution_status, availability)
            rows.append(
                {
                    "requirement_id": item.get("requirement_id", ""),
                    "method_field": item.get("method_field") or item.get("requirement_id"),
                    "description": item.get("description") or item.get("purpose") or item.get("requirement_id", ""),
                    "required_for": item.get("required_for", []),
                    "severity": item.get("severity", ""),
                    "scope": item.get("scope", ""),
                    "mapped_source": mapped_source,
                    "source_kind": source_kind,
                    "source_role": source_role,
                    "expected_unit": item.get("expected_unit", ""),
                    "source_unit": availability["source_unit"],
                    "coverage": availability["coverage"] if mapped_source else "not mapped",
                    "example_value": availability["example_value"],
                    "candidate_count": resolution.get("candidate_count", ""),
                    "confidence": resolution.get("confidence", ""),
                    "resolution_status": resolution_status,
                    "status": status,
                }
            )
        return rows
    rows: list[dict[str, Any]] = []
    for section_name in ("tokens", "channels", "fields"):
        section = mapping.get(section_name)
        if not isinstance(section, dict):
            continue
        for method_field, mapped in section.items():
            if isinstance(mapped, dict):
                mapped_name = mapped.get("source") or mapped.get("field") or mapped.get("name") or mapped.get("token") or mapped.get("channel")
                unit = mapped.get("unit") or mapped.get("target_unit") or mapped.get("source_unit")
                source_kind = mapped.get("source_kind") or section_name.rstrip("s")
                source_role = mapped.get("role") or mapped.get("source_role") or ""
            else:
                mapped_name = mapped
                unit = ""
                source_kind = section_name.rstrip("s")
                source_role = ""
            availability = _availability_for_mapped_source(source, source_kind, str(mapped_name or ""))
            rows.append(
                {
                    "method_field": method_field,
                    "description": str(method_field),
                    "mapped_source": mapped_name,
                    "source_kind": source_kind,
                    "source_role": source_role,
                    "expected_unit": unit,
                    "source_unit": availability["source_unit"] if mapped_name else "",
                    "coverage": availability["coverage"] if mapped_name else "not mapped",
                    "example_value": availability["example_value"] if mapped_name else "",
                    "status": "pass" if mapped_name else "fail",
                }
            )
    return rows


def _mapped_source_for_role(mapping: dict[str, Any], source_role: str) -> tuple[str, str]:
    for source_kind in ("channels", "fields", "tokens"):
        section = mapping.get(source_kind)
        if isinstance(section, dict) and source_role in section:
            value = section[source_role]
            if isinstance(value, dict):
                if str(value.get("status") or "").casefold() in {"ambiguous", "unresolved"}:
                    return "", source_kind.rstrip("s")
                value = value.get("source") or value.get("field") or value.get("name") or value.get("token") or value.get("channel")
            return str(value), source_kind.rstrip("s")
    return "", "missing"


def _mapping_requirement_applies(requirement: Mapping[str, Any], mapping: Mapping[str, Any]) -> bool:
    condition = str(requirement.get("required_when") or "").strip()
    if not condition:
        return True
    left, operator, right = condition.partition("==")
    if not operator:
        return False
    key = left.strip()
    actual = _mapping_config_value(mapping, key)
    if actual in (None, "") and key == "strain_source":
        actual = _mapping_strain_source(mapping)
    return str(actual or "").strip() == right.strip()


def _mapping_config_value(mapping: Mapping[str, Any], dotted_key: str) -> Any:
    current: Any = mapping
    for part in dotted_key.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
        else:
            return None
    return current


def _mapping_strain_source(mapping: Mapping[str, Any]) -> str | None:
    payload = dict(mapping)
    front, _ = _mapped_source_for_role(payload, "front_strain")
    rear, _ = _mapped_source_for_role(payload, "rear_strain")
    if front and rear:
        return "direct_strain_channels"
    extension, _ = _mapped_source_for_role(payload, "extension")
    if extension:
        return "extension_derived"
    return None


def _availability_for_mapped_source(
    source: Any | None,
    source_kind: str,
    mapped_source: str,
    *,
    requirement: dict[str, Any] | None = None,
) -> dict[str, str]:
    if source is None or not mapped_source:
        return {"coverage": "mapping declared", "example_value": "", "source_unit": ""}
    if requirement and str(requirement.get("scope") or "") in {"per_dataset", "per_package"}:
        return _availability_for_dataset_source(source, requirement, mapped_source)
    present = 0
    total = len(source.runs)
    example = ""
    unit = ""
    kind = source_kind.casefold()
    for run in source.runs:
        value: Any | None = None
        value_unit = ""
        if kind in {"channel", "channels"}:
            channel = run.channel(mapped_source)
            if channel is not None:
                present += 1
                value_unit = channel.unit or ""
                value = next((item for item in channel.values if item is not None), None)
        elif kind in {"field", "fields", "token", "tokens"}:
            token = run.token(mapped_source)
            if token is not None:
                present += 1
                value_unit = token.unit or ""
                value = token.value
        if example == "" and value not in (None, ""):
            example = str(value)
        if not unit and value_unit:
            unit = value_unit
    status = f"{present}/{total} runs" if total else "0/0 runs"
    return {"coverage": status, "example_value": example, "source_unit": unit}


def _mapped_row_status(
    requirement: dict[str, Any],
    mapped_source: str,
    resolution_status: str,
    availability: dict[str, str],
) -> str:
    severity = str(requirement.get("severity") or "")
    if resolution_status == "ambiguous":
        return "ambiguous" if severity == "execution_critical" else "warn"
    if not mapped_source:
        return "fail" if severity == "execution_critical" else "warn"
    if not _availability_has_value(availability):
        return "fail" if severity == "execution_critical" else "warn"
    return "pass"


def _availability_has_value(availability: dict[str, str]) -> bool:
    coverage = str(availability.get("coverage") or "")
    head = coverage.split("/", 1)[0].strip()
    try:
        return int(head) > 0
    except ValueError:
        return bool(coverage == "mapping declared")


def _availability_for_dataset_source(
    source: Any,
    requirement: dict[str, Any],
    mapped_source: str,
) -> dict[str, str]:
    dataset = getattr(source, "dataset", {}) or {}
    for candidate in _dataset_value_candidates(source, requirement, mapped_source):
        value = _dataset_value(dataset, candidate)
        if value not in (None, ""):
            return {
                "coverage": "1/1 dataset",
                "example_value": _preview_value(value),
                "source_unit": "",
            }
    return {"coverage": "0/1 dataset", "example_value": "", "source_unit": ""}


def _dataset_value_candidates(source: Any, requirement: dict[str, Any], mapped_source: str) -> tuple[str, ...]:
    candidates: list[str] = []
    for item in (mapped_source, requirement.get("source_role"), requirement.get("method_field")):
        _append_unique(candidates, item)
    for field in _schema_dataset_fields(source):
        if not _schema_field_matches_requirement(field, requirement):
            continue
        storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
        if isinstance(storage, dict):
            _append_unique(candidates, storage.get("path"))
        for key in ("field_id", "role", "report_role", "method_role", "suggestion_key", "label"):
            _append_unique(candidates, field.get(key))
        for alias in field.get("import_aliases", ()) or ():
            _append_unique(candidates, alias.get("alias") if isinstance(alias, dict) else alias)
    return tuple(candidates)


def _schema_dataset_fields(source: Any) -> tuple[dict[str, Any], ...]:
    schema = getattr(source, "schema", {}) or {}
    fields = schema.get("dataset_fields", ()) if isinstance(schema, dict) else ()
    return tuple(field for field in fields if isinstance(field, dict))


def _schema_field_matches_requirement(field: dict[str, Any], requirement: dict[str, Any]) -> bool:
    targets = {
        _normalise_key(requirement.get("source_role")),
        _normalise_key(requirement.get("method_field")),
        _normalise_key(str(requirement.get("method_field") or "").rsplit(".", 1)[-1]),
        _normalise_key(str(requirement.get("requirement_id") or "").rsplit(".", 1)[-1]),
    }
    values: list[Any] = [field.get(key) for key in ("field_id", "role", "report_role", "method_role", "suggestion_key", "label")]
    storage = field.get("storage") if isinstance(field.get("storage"), dict) else {}
    if isinstance(storage, dict):
        values.extend([storage.get("path"), str(storage.get("path") or "").rsplit(".", 1)[-1]])
    for alias in field.get("import_aliases", ()) or ():
        values.append(alias.get("alias") if isinstance(alias, dict) else alias)
    normalized = {_normalise_key(value) for value in values if value not in (None, "")}
    if targets & normalized:
        return True
    if "testing_speed" in targets and "speed_of_testing" in normalized:
        return True
    if "conditioning" in targets and any(value.startswith("conditioning_") for value in normalized):
        return True
    return False


def _dataset_value(dataset: Any, mapped_source: str) -> Any:
    if not isinstance(dataset, dict):
        return None
    if mapped_source in dataset:
        value = dataset.get(mapped_source)
        return value.get("value") if isinstance(value, dict) and "value" in value else value
    cursor: Any = dataset
    for part in [item for item in str(mapped_source or "").split(".") if item]:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    if isinstance(cursor, dict) and "value" in cursor:
        return cursor.get("value")
    return cursor


def _preview_value(value: Any) -> str:
    if isinstance(value, dict) and "value" in value:
        value = value.get("value")
    return str(value)


def _append_unique(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _normalise_key(value: Any) -> str:
    text = str(value or "").casefold()
    parts: list[str] = []
    previous_was_sep = False
    for char in text:
        if char.isalnum():
            parts.append(char)
            previous_was_sep = False
        elif not previous_was_sep:
            parts.append("_")
            previous_was_sep = True
    return "".join(parts).strip("_")


def _mapping_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    critical = [row for row in rows if row.get("severity") == "execution_critical"]
    report = [row for row in rows if row.get("severity") == "report_completeness"]
    critical_pass = sum(1 for row in critical if row.get("status") == "pass")
    report_pass = sum(1 for row in report if row.get("status") == "pass")
    critical_ambiguous = sum(1 for row in critical if row.get("status") == "ambiguous")
    report_ambiguous = sum(1 for row in report if row.get("status") == "ambiguous")
    return {
        "execution_critical_mapped": critical_pass,
        "execution_critical_total": len(critical),
        "execution_critical_missing": max(0, len(critical) - critical_pass - critical_ambiguous),
        "execution_critical_ambiguous": critical_ambiguous,
        "report_fields_mapped": report_pass,
        "report_fields_total": len(report),
        "report_fields_missing": max(0, len(report) - report_pass - report_ambiguous),
        "report_ambiguous": report_ambiguous,
        "ambiguous": sum(1 for row in rows if row.get("status") == "ambiguous"),
    }


def _mapping_status(rows: list[dict[str, Any]]) -> str:
    if any(row.get("status") == "ambiguous" and row.get("severity") == "execution_critical" for row in rows):
        return "ambiguous"
    if any(row.get("status") == "fail" and row.get("severity") == "execution_critical" for row in rows):
        return "incomplete"
    if any(row.get("status") in {"fail", "warn"} for row in rows):
        return "warnings"
    return "complete"


def _readiness_errors(report: ReadinessReport) -> list[str]:
    rows = report.missing_rows()
    critical = [row for row in rows if row.get("severity") == "execution_critical"]
    selected = critical or rows
    return [
        f"{row.get('requirement_id')}: {row.get('message')}"
        for row in selected[:12]
    ]


def _write_workbench(result: Any, output_path: Path) -> Path:
    directory = output_path.with_suffix("")
    workbench = directory.parent / f"{directory.name}_workbench"
    workbench.mkdir(parents=True, exist_ok=True)
    trace = build_operation_trace(result)
    (workbench / "operation_trace.json").write_text(json_text(trace), encoding="utf-8")
    (workbench / "index.html").write_text(
        MethodDevelopmentReportBuilder().build(trace, api_enabled=False),
        encoding="utf-8",
    )
    return workbench
