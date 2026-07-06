from __future__ import annotations

import argparse
import hashlib
import copy
import csv
import json
import math
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_DATA_ROOT = ROOT / "datasets"
DEFAULT_METHOD_PATH = ROOT / "src" / "methods" / "iso14126"
DEFAULT_DATABASE_ROOT = ROOT / "artifacts" / "boundary_curve_database"
DEFAULT_LABEL_PATH = DEFAULT_DATABASE_ROOT / "labels.json"
DEFAULT_PATTERN = "**/*_stress_strain.csv"


@dataclass(frozen=True, slots=True)
class CurveRecord:
    curve_id: str
    run_id: str
    source_path: Path
    point_index: list[int]
    strain: list[float | None]
    stress: list[float | None]
    load: list[float | None]
    time: list[float | None]
    row_count: int

    @property
    def point_count(self) -> int:
        return len(self.point_index)

    def value_at(self, index: int, values: list[float | None]) -> float | None:
        try:
            position = self.point_index.index(index)
        except ValueError:
            return None
        if position < 0 or position >= len(values):
            return None
        return values[position]


@dataclass(frozen=True, slots=True)
class StoredCurveFile:
    original_path: Path
    stored_path: Path
    sha256: str
    size_bytes: int
    package_member: str | None = None


@dataclass(frozen=True, slots=True)
class AlgorithmResult:
    gate_record: dict[str, Any]
    boundary_record: dict[str, Any]
    gate_warnings: tuple[str, ...]
    boundary_warnings: tuple[str, ...]

    @property
    def gate_start_index(self) -> int | None:
        return _as_int((self.gate_record.get("coherent_window") or {}).get("start_index"))

    @property
    def gate_end_index(self) -> int | None:
        return _as_int((self.gate_record.get("coherent_window") or {}).get("end_index"))

    @property
    def boundary_start_index(self) -> int | None:
        return _as_int(self.boundary_record.get("start_index"))

    @property
    def boundary_end_index(self) -> int | None:
        return _as_int(self.boundary_record.get("end_index"))


def discover_curves(
    data_root: Path,
    *,
    pattern: str = DEFAULT_PATTERN,
    limit: int | None = None,
    accept_any_csv: bool = False,
) -> list[CurveRecord]:
    records: list[CurveRecord] = []
    for path in sorted(data_root.glob(pattern)):
        if not path.is_file():
            continue
        if accept_any_csv:
            if not _is_csv_curve_candidate(path):
                continue
        elif not _is_stress_strain_candidate(path):
            continue
        records.extend(load_curve_records(path, catalogue_root=data_root))
        if limit is not None and len(records) >= limit:
            return records[:limit]
    return records


def discover_catalogue_curves(database_root: Path, *, limit: int | None = None) -> list[CurveRecord]:
    return discover_curves(_database_raw_dir(database_root), pattern="**/*.csv", limit=limit, accept_any_csv=True)


def discover_labeller_curves(
    *,
    data_root: Path,
    database_root: Path,
    pattern: str = DEFAULT_PATTERN,
    include_data_root: bool = True,
) -> list[CurveRecord]:
    curves: list[CurveRecord] = []
    if include_data_root:
        curves.extend(discover_curves(data_root, pattern=pattern))
    curves.extend(discover_catalogue_curves(database_root))
    return _dedupe_curves(curves)


def import_curve_files(paths: list[Path], *, database_root: Path) -> list[CurveRecord]:
    imported_curves: list[CurveRecord] = []
    manifest = load_database_manifest(database_root)
    raw_dir = _database_raw_dir(database_root)
    raw_dir.mkdir(parents=True, exist_ok=True)
    for source_path in paths:
        for stored in copy_curve_source_to_database(source_path, database_root=database_root):
            curves = load_curve_records(stored.stored_path, catalogue_root=raw_dir)
            imported_curves.extend(curves)
            record = {
                "stored_path": _portable_path(stored.stored_path),
                "original_path": str(stored.original_path),
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "curve_ids": [curve.curve_id for curve in curves],
                "run_ids": [curve.run_id for curve in curves],
                "imported_at": _now_iso(),
            }
            if stored.package_member:
                record["package_member"] = stored.package_member
            _upsert_manifest_record(manifest, record)
    write_database_manifest(database_root, manifest)
    return imported_curves


def copy_curve_source_to_database(source_path: Path, *, database_root: Path) -> list[StoredCurveFile]:
    source = Path(source_path).resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    if _is_package_candidate(source):
        return extract_package_curves_to_database(source, database_root=database_root)
    return [copy_curve_to_database(source, database_root=database_root)]


def copy_curve_to_database(source_path: Path, *, database_root: Path) -> StoredCurveFile:
    source = Path(source_path).resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    digest = _file_sha256(source)
    raw_dir = _database_raw_dir(database_root)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{_safe_filename(source.stem)}__{digest[:12]}{source.suffix.lower() or '.csv'}"
    destination = raw_dir / stored_name
    if not destination.exists():
        shutil.copy2(source, destination)
    return StoredCurveFile(
        original_path=source,
        stored_path=destination,
        sha256=digest,
        size_bytes=source.stat().st_size,
    )


def extract_package_curves_to_database(package_path: Path, *, database_root: Path) -> list[StoredCurveFile]:
    package = Path(package_path).resolve()
    if not zipfile.is_zipfile(package):
        raise ValueError(f"Package is not a readable zip archive: {package}")
    digest = _file_sha256(package)
    raw_dir = _database_raw_dir(database_root)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stored: list[StoredCurveFile] = []
    with zipfile.ZipFile(package) as archive:
        members = _package_curve_members(archive)
        for member in members:
            if not _is_package_curve_member(member):
                continue
            data = archive.read(member)
            if not data.strip():
                continue
            stored_name = (
                f"{_safe_filename(Path(member).stem)}__{_safe_filename(package.stem)}__"
                f"{digest[:12]}.csv"
            )
            destination = raw_dir / stored_name
            if not destination.exists():
                destination.write_bytes(data)
            stored.append(
                StoredCurveFile(
                    original_path=package,
                    stored_path=destination,
                    sha256=hashlib.sha256(data).hexdigest(),
                    size_bytes=len(data),
                    package_member=member,
                )
            )
    if not stored:
        raise ValueError(f"No stress-strain curve CSV files found in package: {package}")
    return stored


def load_database_manifest(database_root: Path) -> dict[str, Any]:
    path = _database_manifest_path(database_root)
    if not path.exists():
        return {"schema_id": "dev.boundary_curve_database.v0_1", "files": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Database manifest is not a JSON object: {path}")
    payload.setdefault("schema_id", "dev.boundary_curve_database.v0_1")
    payload.setdefault("files", [])
    if not isinstance(payload["files"], list):
        raise ValueError(f"Database manifest files member is not a list: {path}")
    return payload


def write_database_manifest(database_root: Path, manifest: dict[str, Any]) -> None:
    path = _database_manifest_path(database_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = _now_iso()
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_curve_records(path: Path, *, catalogue_root: Path | None = None) -> list[CurveRecord]:
    rows = _read_csv_rows(path)
    if not rows:
        return []
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        scope = str(row.get("curve_scope") or "").strip().lower()
        if scope and scope not in {"full", "raw"}:
            continue
        run_id = str(row.get("run_id") or _run_id_from_path(path)).strip() or _run_id_from_path(path)
        groups.setdefault(run_id, []).append(row)
    records: list[CurveRecord] = []
    for run_id, run_rows in sorted(groups.items()):
        if not run_rows:
            continue
        header = run_rows[0]
        index_col = _first_present(header, ("point_index", "index", "Index", "Scan #", "scan"))
        strain_col = _first_present(header, ("mean_strain", "strain_mm_per_mm", "strain", "Strain"))
        front_strain_col = _first_present(header, ("front_strain", "front_strain_raw", "Front strain"))
        rear_strain_col = _first_present(header, ("rear_strain", "rear_strain_raw", "Rear strain"))
        gauge_cols = _gauge_strain_columns(header)
        front_strain_col = front_strain_col or (gauge_cols[0] if gauge_cols else None)
        rear_strain_col = rear_strain_col or (gauge_cols[1] if len(gauge_cols) > 1 else None)
        stress_col = _first_present(header, ("stress_MPa", "stress", "Stress")) or _first_column_containing(header, ("stress",))
        load_col = _first_present(header, ("load_N", "load_N_raw", "Force", "force_N", "load")) or _first_column_containing(header, ("load", "force"))
        time_col = _first_present(header, ("time_s", "Time", "time")) or _first_column_containing(header, ("time",))

        point_index: list[int] = []
        strain: list[float | None] = []
        stress: list[float | None] = []
        load: list[float | None] = []
        time: list[float | None] = []
        for row in run_rows:
            parsed_index = _as_int(row.get(index_col)) if index_col else None
            load_value = _load_from_row(row, load_col=load_col)
            strain_value = _strain_from_row(row, strain_col=strain_col, front_col=front_strain_col, rear_col=rear_strain_col)
            stress_value = _as_float(row.get(stress_col)) if stress_col else None
            time_value = _as_float(row.get(time_col)) if time_col else None
            if load_value is None and strain_value is None and stress_value is None and time_value is None:
                continue
            fallback_index = len(point_index)
            point_index.append(parsed_index if parsed_index is not None else fallback_index)
            strain.append(strain_value)
            stress.append(stress_value)
            load.append(load_value)
            time.append(time_value if time_value is not None else float(fallback_index))

        if not any(value is not None for value in load):
            load = list(stress)
        if not any(value is not None for value in stress):
            stress = list(load)
        if not any(value is not None for value in strain):
            strain = [float(index) for index in point_index]
        if not any(value is not None for value in time):
            time = [float(index) for index in point_index]

        records.append(
            CurveRecord(
                curve_id=_curve_id(path, run_id, catalogue_root=catalogue_root),
                run_id=run_id,
                source_path=path,
                point_index=point_index,
                strain=strain,
                stress=stress,
                load=load,
                time=time,
                row_count=len(run_rows),
            )
        )
    return records


def evaluate_curve(
    curve: CurveRecord,
    *,
    method_path: Path | None = DEFAULT_METHOD_PATH,
    gate_step: dict[str, Any] | None = None,
    boundary_step: dict[str, Any] | None = None,
) -> AlgorithmResult:
    from operations.core.operation_context import OperationContext, OperationRun
    from operations.core.operation_registry import default_operation_registry

    if gate_step is None or boundary_step is None:
        recipe_gate, recipe_boundary = load_recipe_steps(method_path or DEFAULT_METHOD_PATH)
        gate_step = gate_step or recipe_gate
        boundary_step = boundary_step or recipe_boundary

    run = OperationRun(
        source_run={"path": str(curve.source_path), "curve_id": curve.curve_id},
        series={
            "load_N": list(curve.load),
            "mean_strain": list(curve.strain),
            "stress_MPa": list(curve.stress),
            "time_s": list(curve.time),
            "point_index": [float(index) for index in curve.point_index],
        },
        units={
            "load_N": "N",
            "mean_strain": "mm/mm",
            "stress_MPa": "MPa",
            "time_s": "s",
            "point_index": "index",
        },
    )
    context = OperationContext(
        source=None,
        mapping={},
        runs={curve.run_id: run},
        inspector=None,
        phase="resolve",
    )
    registry = default_operation_registry()
    gate_results = registry.run(context, copy.deepcopy(gate_step))
    boundary_results = registry.run(context, copy.deepcopy(boundary_step))

    gate_output = str(gate_step.get("output") or "experiment_signal_gate")
    boundary_output = str(boundary_step.get("output") or "experiment_boundaries")
    gate_record = gate_results[0].outputs.get(gate_output, {}) if gate_results else {}
    boundary_record = boundary_results[0].outputs.get(boundary_output, {}) if boundary_results else {}
    return AlgorithmResult(
        gate_record=gate_record if isinstance(gate_record, dict) else {},
        boundary_record=boundary_record if isinstance(boundary_record, dict) else {},
        gate_warnings=tuple(gate_results[0].warnings) if gate_results else (),
        boundary_warnings=tuple(boundary_results[0].warnings) if boundary_results else (),
    )


def load_recipe_steps(method_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if method_path is None:
        return default_gate_step(), default_boundary_step()
    recipe_path = Path(method_path) / "resolve_recipe.yaml"
    if not recipe_path.exists():
        return default_gate_step(), default_boundary_step()
    try:
        import yaml

        payload = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    except Exception:
        return default_gate_step(), default_boundary_step()
    steps = payload.get("resolve") if isinstance(payload, dict) else None
    if not isinstance(steps, list):
        return default_gate_step(), default_boundary_step()
    gate = _find_step(steps, "gate_experiment_signal") or default_gate_step()
    boundary = _find_step(steps, "resolve_experiment_boundaries") or default_boundary_step()
    return copy.deepcopy(gate), copy.deepcopy(boundary)


def default_gate_step() -> dict[str, Any]:
    return {
        "id": "resolve.gate_experiment_signal",
        "op": "gate_experiment_signal",
        "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain"},
        "output": "experiment_signal_gate",
    }


def default_boundary_step() -> dict[str, Any]:
    return {
        "id": "resolve.experiment_boundaries",
        "op": "resolve_experiment_boundaries",
        "inputs": {"load": "load_N", "time": "time_s", "strain": "mean_strain", "gate": "experiment_signal_gate"},
        "parameters": {
            "start_policy": "first_point",
            "end_policy": "peak_decline_non_recovery",
            "include_endpoint": True,
            "slope_break": {
                "slope_domain": "strain",
                "derivative_step_points": 1,
                "min_load_fraction_of_max": 0.1,
                "min_relative_load_drop": 0.005,
                "min_negative_domain_step": 0.00001,
                "detect_strain_collapse": True,
                "min_strain_before_collapse": 0.0002,
                "min_relative_strain_collapse": 0.25,
                "prebreak_lookback_points": 8,
                "use_prebreak_curvature": True,
            },
            "sustained_decline": {
                "enabled": True,
                "min_points": 3,
                "use_as": "endpoint",
                "min_drop_fraction_of_peak": 0.005,
                "recovery_level_fraction_of_peak": 0.9,
                "low_state_level_fraction_of_peak": 0.99,
                "low_state_window_points": 3,
                "low_state_min_fraction": 0.5,
                "min_low_state_points": 1,
                "local_recovery_window_multiplier": 2.0,
                "min_recovery_window_points": 5,
                "trough_to_recovery_window_points": 6,
                "recovery_amplitude_decisive_fraction_of_peak": 0.95,
                "recovery_slope_fraction": 0.75,
                "later_higher_relative_tolerance": 0.0001,
                "later_higher_absolute_tolerance": 0.0,
                "min_gate_peak_fraction_of_full_run_max": 0.10,
                "significant_recovery_requires_higher_or_slope": True,
                "sign_state_audit_policy": "diagnostic_veto_recovery",
            },
        },
        "output": "experiment_boundaries",
    }


def build_label_record(
    curve: CurveRecord,
    *,
    start_index: int | None,
    end_index: int | None,
    notes: str = "",
    algorithm: AlgorithmResult | None = None,
) -> dict[str, Any]:
    return {
        "label_id": curve.curve_id,
        "curve_id": curve.curve_id,
        "run_id": curve.run_id,
        "source_path": _portable_path(curve.source_path),
        "point_count": curve.point_count,
        "label_start_index": start_index,
        "label_end_index": end_index,
        "human_label": {
            "schema_id": "dev.human_boundary_label.v0_1",
            "start_index": start_index,
            "end_index": end_index,
            "notes": notes,
        },
        "label_start_strain": curve.value_at(start_index, curve.strain) if start_index is not None else None,
        "label_start_stress_MPa": curve.value_at(start_index, curve.stress) if start_index is not None else None,
        "label_start_load_N": curve.value_at(start_index, curve.load) if start_index is not None else None,
        "label_end_strain": curve.value_at(end_index, curve.strain) if end_index is not None else None,
        "label_end_stress_MPa": curve.value_at(end_index, curve.stress) if end_index is not None else None,
        "label_end_load_N": curve.value_at(end_index, curve.load) if end_index is not None else None,
        "notes": notes,
        "algorithm_snapshot": algorithm_snapshot(algorithm) if algorithm else {},
        "updated_at": _now_iso(),
    }


def algorithm_snapshot(algorithm: AlgorithmResult | None) -> dict[str, Any]:
    if algorithm is None:
        return {}
    routing = algorithm.gate_record.get("report_routing")
    if not isinstance(routing, dict):
        routing = {}
    return {
        "gate_start_index": algorithm.gate_start_index,
        "gate_end_index": algorithm.gate_end_index,
        "gate_status": algorithm.gate_record.get("status"),
        "gate_confidence": algorithm.gate_record.get("confidence"),
        "gate_report_routing_state": routing.get("state"),
        "gate_report_routing_severity": routing.get("severity"),
        "gate_classifications": algorithm.gate_record.get("classifications", []),
        "gate_warning_count": len(algorithm.gate_warnings),
        "boundary_start_index": algorithm.boundary_start_index,
        "boundary_end_index": algorithm.boundary_end_index,
        "boundary_confidence": algorithm.boundary_record.get("confidence"),
        "boundary_reason": algorithm.boundary_record.get("reason"),
        "boundary_warning_count": len(algorithm.boundary_warnings),
        "accepted_failure_peak_index": algorithm.boundary_record.get("accepted_failure_peak_index"),
        "reported_strength_index": algorithm.boundary_record.get("reported_strength_index"),
    }


def load_label_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_id": "dev.boundary_label_catalog.v0_1", "labels": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Label catalog is not a JSON object: {path}")
    payload.setdefault("schema_id", "dev.boundary_label_catalog.v0_1")
    payload.setdefault("labels", [])
    if not isinstance(payload["labels"], list):
        raise ValueError(f"Label catalog labels member is not a list: {path}")
    return payload


def write_label_catalog(path: Path, catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    catalog["updated_at"] = _now_iso()
    path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_label(catalog: dict[str, Any], label: dict[str, Any]) -> None:
    labels = catalog.setdefault("labels", [])
    if not isinstance(labels, list):
        raise ValueError("Label catalog labels member is not a list.")
    key = str(label.get("curve_id") or label.get("label_id"))
    for index, existing in enumerate(labels):
        if str(existing.get("curve_id") or existing.get("label_id")) == key:
            labels[index] = label
            return
    labels.append(label)


def labels_by_curve_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    labels = catalog.get("labels")
    if not isinstance(labels, list):
        return {}
    return {
        str(label.get("curve_id") or label.get("label_id")): label
        for label in labels
        if isinstance(label, dict) and (label.get("curve_id") or label.get("label_id"))
    }


def assess_labels(
    label_path: Path,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    method_path: Path | None = DEFAULT_METHOD_PATH,
    output_json: Path | None = None,
    output_csv: Path | None = None,
    start_tolerance: int = 2,
    end_tolerance: int = 3,
    gate_tolerance: int = 3,
    gate_step: dict[str, Any] | None = None,
    boundary_step: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = load_label_catalog(label_path)
    labels = [label for label in catalog.get("labels", []) if isinstance(label, dict)]
    results: list[dict[str, Any]] = []
    for label in labels:
        curve = _curve_from_label(label, data_root=data_root, label_path=label_path)
        if curve is None:
            results.append(_missing_curve_result(label))
            continue
        algorithm = evaluate_curve(
            curve,
            method_path=method_path,
            gate_step=gate_step,
            boundary_step=boundary_step,
        )
        results.append(
            _assessment_row(
                label=label,
                curve=curve,
                algorithm=algorithm,
                start_tolerance=start_tolerance,
                end_tolerance=end_tolerance,
                gate_tolerance=gate_tolerance,
            )
        )

    summary = _assessment_summary(results)
    report = {
        "schema_id": "dev.boundary_label_assessment.v0_1",
        "label_catalog": str(label_path),
        "generated_at": _now_iso(),
        "tolerances": {
            "boundary_start_index": start_tolerance,
            "boundary_end_index": end_tolerance,
            "gate_start_index": gate_tolerance,
            "gate_end_index": gate_tolerance,
        },
        "summary": summary,
        "results": results,
    }
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if output_csv:
        _write_assessment_csv(output_csv, results)
    return report


def launch_label_gui(
    *,
    data_root: Path,
    database_root: Path,
    pattern: str,
    label_path: Path,
    method_path: Path,
    initial_curve_id: str | None = None,
    include_data_root: bool = True,
) -> int:
    try:
        from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
        from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
        from PyQt6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QSplitter,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        try:
            from PySide6.QtCore import QPointF, QRectF, Qt, Signal as pyqtSignal
            from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
            from PySide6.QtWidgets import (
                QApplication,
                QCheckBox,
                QComboBox,
                QFileDialog,
                QGridLayout,
                QHBoxLayout,
                QLabel,
                QListWidget,
                QListWidgetItem,
                QMainWindow,
                QMessageBox,
                QPushButton,
                QSpinBox,
                QSplitter,
                QTextEdit,
                QVBoxLayout,
                QWidget,
            )
        except ImportError:
            print(f"PyQt6 or PySide6 is required for label mode: {exc}", file=sys.stderr)
            return 2

    curves = discover_labeller_curves(
        data_root=data_root,
        database_root=database_root,
        pattern=pattern,
        include_data_root=include_data_root,
    )

    class CurveCanvas(QWidget):
        pointPicked = pyqtSignal(int)

        def __init__(self, title: str) -> None:
            super().__init__()
            self.setMinimumSize(300, 260)
            self.title = title
            self.x_label = ""
            self.y_label = ""
            self.x_values: list[float | None] = []
            self.y_values: list[float | None] = []
            self.point_indices: list[int] = []
            self.markers: list[dict[str, Any]] = []
            self.spans: list[dict[str, Any]] = []

        def set_plot(
            self,
            *,
            title: str,
            x_label: str,
            y_label: str,
            x_values: list[float | None],
            y_values: list[float | None],
            point_indices: list[int],
            markers: list[dict[str, Any]] | None = None,
            spans: list[dict[str, Any]] | None = None,
        ) -> None:
            self.title = title
            self.x_label = x_label
            self.y_label = y_label
            self.x_values = x_values
            self.y_values = y_values
            self.point_indices = point_indices
            self.markers = markers or []
            self.spans = spans or []
            self.update()

        def paintEvent(self, event: Any) -> None:  # noqa: N802
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QColor("#ffffff"))
            rect = self._plot_rect()
            painter.setPen(QPen(QColor("#0f172a"), 1))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(QRectF(12, 8, self.width() - 24, 20), Qt.AlignmentFlag.AlignLeft, self.title)
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QPen(QColor("#475569"), 1))
            painter.drawText(QRectF(rect.left(), self.height() - 28, rect.width(), 18), Qt.AlignmentFlag.AlignCenter, self.x_label)
            painter.save()
            painter.translate(14, rect.center().y())
            painter.rotate(-90)
            painter.drawText(QRectF(-rect.height() / 2, -8, rect.height(), 16), Qt.AlignmentFlag.AlignCenter, self.y_label)
            painter.restore()

            bounds = self._bounds()
            if bounds is None:
                painter.setPen(QPen(QColor("#64748b"), 1))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No numeric data")
                return
            x_min, x_max, y_min, y_max = bounds

            painter.setPen(QPen(QColor("#cbd5e1"), 1))
            painter.drawRect(rect)
            for fraction in (0.25, 0.5, 0.75):
                x = rect.left() + rect.width() * fraction
                y = rect.top() + rect.height() * fraction
                painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
                painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

            for span in self.spans:
                start = _as_int(span.get("start_index"))
                end = _as_int(span.get("end_index"))
                if start is None or end is None:
                    continue
                start_x = self._x_for_index(start)
                end_x = self._x_for_index(end)
                if start_x is None or end_x is None:
                    continue
                left = self._screen_x(start_x, x_min, x_max, rect)
                right = self._screen_x(end_x, x_min, x_max, rect)
                color = QColor(str(span.get("color") or "#dcfce7"))
                color.setAlpha(int(span.get("alpha") or 70))
                painter.fillRect(QRectF(min(left, right), rect.top(), abs(right - left), rect.height()), color)

            path = QPainterPath()
            has_active_segment = False
            step = max(1, len(self.x_values) // 1600)
            for x_value, y_value in zip(self.x_values[::step], self.y_values[::step]):
                if not _finite(x_value) or not _finite(y_value):
                    has_active_segment = False
                    continue
                point = QPointF(
                    self._screen_x(float(x_value), x_min, x_max, rect),
                    self._screen_y(float(y_value), y_min, y_max, rect),
                )
                if not has_active_segment:
                    path.moveTo(point)
                    has_active_segment = True
                else:
                    path.lineTo(point)
            painter.setPen(QPen(QColor("#334155"), 1.35))
            painter.drawPath(path)

            for marker in self.markers:
                index = _as_int(marker.get("index"))
                if index is None:
                    continue
                x_value = self._x_for_index(index)
                y_value = self._y_for_index(index)
                if not _finite(x_value):
                    continue
                color = QColor(str(marker.get("color") or "#2563eb"))
                pen = QPen(color, 1.5)
                if marker.get("dash"):
                    pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                screen_x = self._screen_x(float(x_value), x_min, x_max, rect)
                painter.drawLine(QPointF(screen_x, rect.top()), QPointF(screen_x, rect.bottom()))
                if _finite(y_value):
                    screen_y = self._screen_y(float(y_value), y_min, y_max, rect)
                    painter.setBrush(color)
                    painter.drawEllipse(QPointF(screen_x, screen_y), 4.0, 4.0)
                painter.setPen(QPen(color, 1))
                painter.drawText(
                    QRectF(screen_x + 4, rect.top() + 4, 120, 16),
                    Qt.AlignmentFlag.AlignLeft,
                    str(marker.get("label") or index),
                )

            painter.setPen(QPen(QColor("#64748b"), 1))
            painter.drawText(QRectF(rect.left(), rect.bottom() + 2, 90, 16), Qt.AlignmentFlag.AlignLeft, _fmt_axis(x_min))
            painter.drawText(QRectF(rect.right() - 90, rect.bottom() + 2, 90, 16), Qt.AlignmentFlag.AlignRight, _fmt_axis(x_max))
            painter.drawText(QRectF(rect.left() - 52, rect.top() - 8, 48, 16), Qt.AlignmentFlag.AlignRight, _fmt_axis(y_max))
            painter.drawText(QRectF(rect.left() - 52, rect.bottom() - 8, 48, 16), Qt.AlignmentFlag.AlignRight, _fmt_axis(y_min))

        def mousePressEvent(self, event: Any) -> None:  # noqa: N802
            rect = self._plot_rect()
            if not rect.contains(event.position()):
                return
            index = self._nearest_index(event.position())
            if index is not None:
                self.pointPicked.emit(index)

        def _plot_rect(self) -> QRectF:
            return QRectF(58, 36, max(40, self.width() - 78), max(40, self.height() - 76))

        def _bounds(self) -> tuple[float, float, float, float] | None:
            xs = [float(value) for value in self.x_values if _finite(value)]
            ys = [float(value) for value in self.y_values if _finite(value)]
            if not xs or not ys:
                return None
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            if math.isclose(x_min, x_max):
                x_min -= 1.0
                x_max += 1.0
            if math.isclose(y_min, y_max):
                y_min -= 1.0
                y_max += 1.0
            y_pad = (y_max - y_min) * 0.06
            x_pad = (x_max - x_min) * 0.02
            return x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad

        def _nearest_index(self, point: QPointF) -> int | None:
            bounds = self._bounds()
            if bounds is None:
                return None
            rect = self._plot_rect()
            x_min, x_max, y_min, y_max = bounds
            best_index: int | None = None
            best_distance: float | None = None
            for index, x_value, y_value in zip(self.point_indices, self.x_values, self.y_values):
                if not _finite(x_value) or not _finite(y_value):
                    continue
                dx = (self._screen_x(float(x_value), x_min, x_max, rect) - point.x()) / max(rect.width(), 1.0)
                dy = (self._screen_y(float(y_value), y_min, y_max, rect) - point.y()) / max(rect.height(), 1.0)
                distance = dx * dx + dy * dy
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_index = index
            return best_index

        def _x_for_index(self, index: int) -> float | None:
            return _value_for_index(self.point_indices, self.x_values, index)

        def _y_for_index(self, index: int) -> float | None:
            return _value_for_index(self.point_indices, self.y_values, index)

        @staticmethod
        def _screen_x(value: float, x_min: float, x_max: float, rect: QRectF) -> float:
            return rect.left() + ((value - x_min) / (x_max - x_min)) * rect.width()

        @staticmethod
        def _screen_y(value: float, y_min: float, y_max: float, rect: QRectF) -> float:
            return rect.bottom() - ((value - y_min) / (y_max - y_min)) * rect.height()

    class BoundaryLabelWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Boundary labeller")
            self.resize(1420, 820)
            self.all_curves = curves
            self.curves: list[CurveRecord] = []
            self.catalog = load_label_catalog(label_path)
            self.labels = labels_by_curve_id(self.catalog)
            self.algorithms: dict[str, AlgorithmResult] = {}
            self.current_curve: CurveRecord | None = None

            self.list_widget = QListWidget()
            self.unlabelled_only = QCheckBox("Unlabelled only")
            self.unlabelled_only.setChecked(True)
            self.unlabelled_only.stateChanged.connect(lambda: self._populate_catalogue())
            self.raw_canvas = CurveCanvas("Raw stress-strain curve")
            self.gate_canvas = CurveCanvas("gate_experiment_signal")
            self.boundary_canvas = CurveCanvas("boundary_resolution")
            for canvas in (self.raw_canvas, self.gate_canvas, self.boundary_canvas):
                canvas.pointPicked.connect(self._point_picked)

            self.pick_mode = QComboBox()
            self.pick_mode.addItems(["start", "end"])
            self.start_spin = QSpinBox()
            self.end_spin = QSpinBox()
            for spin in (self.start_spin, self.end_spin):
                spin.setMinimum(-1)
                spin.setSpecialValueText("unset")
                spin.valueChanged.connect(self._refresh_plots)
            self.notes = QTextEdit()
            self.notes.setPlaceholderText("Notes for this curve")
            self.notes.setMaximumHeight(74)
            self.status = QLabel("")
            self.status.setWordWrap(True)

            load_button = QPushButton("Load curve")
            load_button.clicked.connect(self._load_curves)
            save_button = QPushButton("Save label")
            save_button.clicked.connect(self._save_label)
            assess_button = QPushButton("Run assessment")
            assess_button.clicked.connect(self._run_assessment)
            next_button = QPushButton("Next unlabeled")
            next_button.clicked.connect(self._next_unlabeled)
            clear_button = QPushButton("Clear")
            clear_button.clicked.connect(self._clear_current)

            control_layout = QGridLayout()
            control_layout.addWidget(QLabel("Pick"), 0, 0)
            control_layout.addWidget(self.pick_mode, 0, 1)
            control_layout.addWidget(QLabel("Start index"), 0, 2)
            control_layout.addWidget(self.start_spin, 0, 3)
            control_layout.addWidget(QLabel("End index"), 0, 4)
            control_layout.addWidget(self.end_spin, 0, 5)
            control_layout.addWidget(self.unlabelled_only, 0, 6)
            control_layout.addWidget(load_button, 0, 7)
            control_layout.addWidget(save_button, 0, 8)
            control_layout.addWidget(assess_button, 0, 9)
            control_layout.addWidget(next_button, 0, 10)
            control_layout.addWidget(clear_button, 0, 11)
            control_layout.addWidget(QLabel("Notes"), 1, 0)
            control_layout.addWidget(self.notes, 1, 1, 1, 11)
            control_layout.addWidget(self.status, 2, 0, 1, 12)

            plot_layout = QHBoxLayout()
            plot_layout.addWidget(self.raw_canvas, 1)
            plot_layout.addWidget(self.gate_canvas, 1)
            plot_layout.addWidget(self.boundary_canvas, 1)

            right = QWidget()
            right_layout = QVBoxLayout(right)
            right_layout.addLayout(control_layout)
            right_layout.addLayout(plot_layout, 1)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(self.list_widget)
            splitter.addWidget(right)
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)
            self.setCentralWidget(splitter)

            self.list_widget.currentRowChanged.connect(self._select_curve)
            self._populate_catalogue(select_curve_id=initial_curve_id)

        def _populate_catalogue(self, select_curve_id: str | None = None) -> None:
            current_id = select_curve_id or (self.current_curve.curve_id if self.current_curve else None)
            self.curves = [
                curve
                for curve in self.all_curves
                if not self.unlabelled_only.isChecked() or not _has_label(self.labels.get(curve.curve_id))
            ]
            self.list_widget.clear()
            for curve in self.curves:
                label = self.labels.get(curve.curve_id)
                prefix = "[labelled]" if _has_label(label) else "[open]"
                item = QListWidgetItem(f"{prefix} {curve.run_id}  {Path(curve.source_path).name}")
                item.setData(Qt.ItemDataRole.UserRole, curve.curve_id)
                self.list_widget.addItem(item)
            if not self.curves:
                self.current_curve = None
                self.status.setText("No curves in the current view. Use Load curve or disable Unlabelled only.")
                return
            row = 0
            if current_id:
                for index, curve in enumerate(self.curves):
                    if curve.curve_id == current_id:
                        row = index
                        break
            self.list_widget.setCurrentRow(row)

        def _select_curve(self, row: int) -> None:
            if row < 0 or row >= len(self.curves):
                return
            self.current_curve = self.curves[row]
            self._ensure_algorithm(self.current_curve)
            self.start_spin.blockSignals(True)
            self.end_spin.blockSignals(True)
            self.start_spin.setMaximum(max(-1, self.current_curve.point_count - 1))
            self.end_spin.setMaximum(max(-1, self.current_curve.point_count - 1))
            label = self.labels.get(self.current_curve.curve_id, {})
            label_start = _as_int(label.get("label_start_index")) if label else None
            label_end = _as_int(label.get("label_end_index")) if label else None
            self.start_spin.setValue(label_start if label_start is not None else -1)
            self.end_spin.setValue(label_end if label_end is not None else -1)
            self.notes.setPlainText(str(label.get("notes") or ""))
            self.start_spin.blockSignals(False)
            self.end_spin.blockSignals(False)
            self._refresh_plots()

        def _ensure_algorithm(self, curve: CurveRecord) -> AlgorithmResult:
            cached = self.algorithms.get(curve.curve_id)
            if cached is not None:
                return cached
            self.status.setText(f"Running gate and boundary logic for {curve.run_id}...")
            QApplication.processEvents()
            algorithm = evaluate_curve(curve, method_path=method_path)
            self.algorithms[curve.curve_id] = algorithm
            return algorithm

        def _point_picked(self, point_index: int) -> None:
            if self.pick_mode.currentText() == "start":
                self.start_spin.setValue(point_index)
                self.pick_mode.setCurrentText("end")
            else:
                self.end_spin.setValue(point_index)
            self._refresh_plots()

        def _refresh_plots(self) -> None:
            curve = self.current_curve
            if curve is None:
                return
            algorithm = self._ensure_algorithm(curve)
            start_index = _spin_value(self.start_spin)
            end_index = _spin_value(self.end_spin)
            strain_percent = _percent_series(curve.strain)
            raw_markers = _label_markers(start_index, end_index)
            boundary_markers = raw_markers + _algorithm_boundary_markers(algorithm)
            gate_markers = raw_markers + _algorithm_gate_markers(algorithm)
            self.raw_canvas.set_plot(
                title="Raw stress-strain curve",
                x_label="mean strain (%)",
                y_label="stress (MPa)",
                x_values=strain_percent,
                y_values=curve.stress,
                point_indices=curve.point_index,
                markers=raw_markers,
            )
            self.gate_canvas.set_plot(
                title="gate_experiment_signal",
                x_label="point index",
                y_label="load (N)",
                x_values=[float(index) for index in curve.point_index],
                y_values=curve.load,
                point_indices=curve.point_index,
                markers=gate_markers,
                spans=_gate_spans(algorithm),
            )
            self.boundary_canvas.set_plot(
                title="boundary_resolution",
                x_label="mean strain (%)",
                y_label="stress (MPa)",
                x_values=strain_percent,
                y_values=curve.stress,
                point_indices=curve.point_index,
                markers=boundary_markers,
            )
            snapshot = algorithm_snapshot(algorithm)
            self.status.setText(
                f"{curve.curve_id} | gate {snapshot.get('gate_start_index')}:{snapshot.get('gate_end_index')} "
                f"{snapshot.get('gate_status')}/{snapshot.get('gate_confidence')} | "
                f"boundary {snapshot.get('boundary_start_index')}:{snapshot.get('boundary_end_index')} "
                f"{snapshot.get('boundary_confidence')} | labels {start_index}:{end_index}"
            )

        def _save_label(self) -> None:
            curve = self.current_curve
            if curve is None:
                return
            algorithm = self._ensure_algorithm(curve)
            label = build_label_record(
                curve,
                start_index=_spin_value(self.start_spin),
                end_index=_spin_value(self.end_spin),
                notes=self.notes.toPlainText().strip(),
                algorithm=algorithm,
            )
            upsert_label(self.catalog, label)
            write_label_catalog(label_path, self.catalog)
            self.labels = labels_by_curve_id(self.catalog)
            self._populate_catalogue(select_curve_id=curve.curve_id)
            self._restore_current(curve.curve_id)
            self.status.setText(f"Saved label for {curve.run_id} to {label_path}")

        def _run_assessment(self) -> None:
            self._save_label()
            output_json = label_path.with_name(label_path.stem + "_assessment.json")
            output_csv = label_path.with_name(label_path.stem + "_assessment.csv")
            report = assess_labels(
                label_path,
                data_root=_database_raw_dir(database_root),
                method_path=method_path,
                output_json=output_json,
                output_csv=output_csv,
            )
            summary = report["summary"]
            QMessageBox.information(
                self,
                "Assessment complete",
                f"Assessed {summary['assessed_count']} labelled curve(s).\n"
                f"Passed: {summary['pass_count']}  Failed: {summary['fail_count']}\n"
                f"Wrote:\n{output_json}\n{output_csv}",
            )

        def _load_curves(self) -> None:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Load curves or packages into catalogue",
                str(data_root),
                "Curve sources (*.csv *.mtdp *.mtda *.zip);;Curve CSV files (*.csv);;MTDP/MTDA packages (*.mtdp *.mtda *.zip);;All files (*.*)",
            )
            if not paths:
                return
            try:
                imported = import_curve_files([Path(path) for path in paths], database_root=database_root)
            except Exception as exc:
                QMessageBox.critical(self, "Load failed", str(exc))
                return
            self.all_curves = discover_labeller_curves(
                data_root=data_root,
                database_root=database_root,
                pattern=pattern,
                include_data_root=include_data_root,
            )
            self.algorithms.clear()
            first_curve_id = imported[0].curve_id if imported else None
            self.unlabelled_only.setChecked(True)
            self._populate_catalogue(select_curve_id=first_curve_id)
            self.status.setText(f"Loaded {len(paths)} file(s) into {_database_raw_dir(database_root)}")

        def _next_unlabeled(self) -> None:
            current = self.list_widget.currentRow()
            count = len(self.curves)
            if count == 0:
                return
            for offset in range(1, count + 1):
                row = (current + offset) % count
                if not _has_label(self.labels.get(self.curves[row].curve_id)):
                    self.list_widget.setCurrentRow(row)
                    return

        def _clear_current(self) -> None:
            self.start_spin.setValue(-1)
            self.end_spin.setValue(-1)
            self.notes.clear()
            self._refresh_plots()

        def _restore_current(self, curve_id: str) -> None:
            for row, curve in enumerate(self.curves):
                if curve.curve_id == curve_id:
                    self.list_widget.setCurrentRow(row)
                    break

    app = QApplication.instance() or QApplication(sys.argv)
    window = BoundaryLabelWindow()
    window.show()
    return int(app.exec())


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return launch_label_gui(
            data_root=DEFAULT_DATA_ROOT,
            database_root=DEFAULT_DATABASE_ROOT,
            pattern=DEFAULT_PATTERN,
            label_path=DEFAULT_LABEL_PATH,
            method_path=DEFAULT_METHOD_PATH,
        )

    parser = argparse.ArgumentParser(description="Development utility for labelling and assessing experiment boundaries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    catalogue = subparsers.add_parser("catalogue", help="Print discovered curve records.")
    catalogue.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    catalogue.add_argument("--database-root", type=Path, default=DEFAULT_DATABASE_ROOT)
    catalogue.add_argument("--pattern", default=DEFAULT_PATTERN)
    catalogue.add_argument("--limit", type=int)
    catalogue.add_argument("--catalogue-only", action="store_true", help="Show only copied raw files in the local catalogue.")

    load = subparsers.add_parser("load", help="Copy curve files into the local raw-curve catalogue.")
    load.add_argument("paths", type=Path, nargs="+")
    load.add_argument("--database-root", type=Path, default=DEFAULT_DATABASE_ROOT)

    label = subparsers.add_parser("label", help="Launch the visual curve labeller.")
    label.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    label.add_argument("--database-root", type=Path, default=DEFAULT_DATABASE_ROOT)
    label.add_argument("--pattern", default=DEFAULT_PATTERN)
    label.add_argument("--labels", type=Path, default=DEFAULT_LABEL_PATH)
    label.add_argument("--method", type=Path, default=DEFAULT_METHOD_PATH)
    label.add_argument("--curve-id")
    label.add_argument("--catalogue-only", action="store_true", help="Label only copied files in the local catalogue.")

    assess = subparsers.add_parser("assess", help="Assess current gate/boundary logic against saved labels.")
    assess.add_argument("--data-root", type=Path, default=_database_raw_dir(DEFAULT_DATABASE_ROOT))
    assess.add_argument("--labels", type=Path, default=DEFAULT_LABEL_PATH)
    assess.add_argument("--method", type=Path, default=DEFAULT_METHOD_PATH)
    assess.add_argument("--output-json", type=Path)
    assess.add_argument("--output-csv", type=Path)
    assess.add_argument("--start-tolerance", type=int, default=2)
    assess.add_argument("--end-tolerance", type=int, default=3)
    assess.add_argument("--gate-tolerance", type=int, default=3)
    assess.add_argument("--fail-on-mismatch", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "catalogue":
        if args.catalogue_only:
            curves = discover_catalogue_curves(args.database_root, limit=args.limit)
        else:
            curves = discover_labeller_curves(data_root=args.data_root, database_root=args.database_root, pattern=args.pattern)
            if args.limit is not None:
                curves = curves[: args.limit]
        for curve in curves:
            print(f"{curve.curve_id}\t{curve.run_id}\t{curve.point_count}\t{curve.source_path}")
        print(f"Discovered {len(curves)} curve(s).")
        return 0
    if args.command == "load":
        imported = import_curve_files(args.paths, database_root=args.database_root)
        print(f"Loaded {len(args.paths)} file(s) into {_database_raw_dir(args.database_root)}.")
        print(f"Imported curve records: {len(imported)}")
        for curve in imported:
            print(f"{curve.curve_id}\t{curve.run_id}\t{curve.point_count}\t{curve.source_path}")
        return 0
    if args.command == "label":
        return launch_label_gui(
            data_root=args.data_root,
            database_root=args.database_root,
            pattern=args.pattern,
            label_path=args.labels,
            method_path=args.method,
            initial_curve_id=args.curve_id,
            include_data_root=not args.catalogue_only,
        )
    if args.command == "assess":
        output_json = args.output_json or args.labels.with_name(args.labels.stem + "_assessment.json")
        output_csv = args.output_csv or args.labels.with_name(args.labels.stem + "_assessment.csv")
        report = assess_labels(
            args.labels,
            data_root=args.data_root,
            method_path=args.method,
            output_json=output_json,
            output_csv=output_csv,
            start_tolerance=args.start_tolerance,
            end_tolerance=args.end_tolerance,
            gate_tolerance=args.gate_tolerance,
        )
        summary = report["summary"]
        print(
            "Assessment: "
            f"{summary['pass_count']} passed, {summary['fail_count']} failed, "
            f"{summary['missing_count']} missing, {summary['assessed_count']} assessed."
        )
        print(f"JSON: {output_json}")
        print(f"CSV: {output_csv}")
        if args.fail_on_mismatch and summary["fail_count"]:
            return 1
        return 0
    return 1


def _assessment_row(
    *,
    label: dict[str, Any],
    curve: CurveRecord,
    algorithm: AlgorithmResult,
    start_tolerance: int,
    end_tolerance: int,
    gate_tolerance: int,
) -> dict[str, Any]:
    label_start = _as_int(label.get("label_start_index"))
    label_end = _as_int(label.get("label_end_index"))
    boundary_start_index = _label_coordinate_index(curve, algorithm.boundary_start_index, label_start)
    boundary_end_index = _label_coordinate_index(curve, algorithm.boundary_end_index, label_end)
    gate_start_index = _label_coordinate_index(curve, algorithm.gate_start_index, label_start)
    gate_end_index = _label_coordinate_index(curve, algorithm.gate_end_index, label_end)
    boundary_start_delta = _delta(boundary_start_index, label_start)
    boundary_end_delta = _delta(boundary_end_index, label_end)
    gate_start_delta = _delta(gate_start_index, label_start)
    gate_end_delta = _delta(gate_end_index, label_end)
    boundary_start_pass = _within_tolerance(boundary_start_delta, start_tolerance)
    boundary_end_pass = _within_tolerance(boundary_end_delta, end_tolerance)
    gate_start_pass = _within_tolerance(gate_start_delta, gate_tolerance) or _gate_starts_before_label(
        gate_record=algorithm.gate_record,
        gate_start_index=gate_start_index,
        label_start=label_start,
    )
    gate_end_pass = _within_tolerance(gate_end_delta, gate_tolerance) or _gate_contains_label(
        curve=curve,
        gate_record=algorithm.gate_record,
        gate_start_index=gate_start_index,
        gate_end_index=gate_end_index,
        label_start=label_start,
        label_end=label_end,
    )
    boundary_pass = boundary_start_pass and boundary_end_pass
    gate_pass = gate_start_pass and gate_end_pass
    review_flags = _review_flags(
        label_start=label_start,
        label_end=label_end,
        gate_start_delta=gate_start_delta,
        gate_end_delta=gate_end_delta,
        boundary_start_delta=boundary_start_delta,
        boundary_end_delta=boundary_end_delta,
        gate_start_pass=gate_start_pass,
        gate_end_pass=gate_end_pass,
        boundary_start_pass=boundary_start_pass,
        boundary_end_pass=boundary_end_pass,
        gate_status=algorithm.gate_record.get("status"),
        boundary_confidence=algorithm.boundary_record.get("confidence"),
    )
    failure_category, failure_detail = _failure_classification(
        gate_start_pass=gate_start_pass,
        gate_end_pass=gate_end_pass,
        boundary_start_pass=boundary_start_pass,
        boundary_end_pass=boundary_end_pass,
        gate_status=algorithm.gate_record.get("status"),
        boundary_confidence=algorithm.boundary_record.get("confidence"),
        review_flags=review_flags,
    )
    label_start_context = _label_start_context(curve, label_start)
    overall_status = "pass" if gate_pass and boundary_pass else "fail"
    diagnostic_columns = _assessment_diagnostic_columns(
        label_start=label_start,
        label_end=label_end,
        gate_start_index=gate_start_index,
        gate_end_index=gate_end_index,
        boundary_start_index=boundary_start_index,
        boundary_end_index=boundary_end_index,
        gate_status=algorithm.gate_record.get("status"),
        gate_confidence=algorithm.gate_record.get("confidence"),
        boundary_confidence=algorithm.boundary_record.get("confidence"),
        boundary_reason=algorithm.boundary_record.get("reason"),
    )
    justification_category, justification_detail = _failure_justification(
        overall_status=overall_status,
        failure_category=failure_category,
        boundary_start_pass=boundary_start_pass,
        boundary_end_pass=boundary_end_pass,
        gate_start_pass=gate_start_pass,
        gate_end_pass=gate_end_pass,
        gate_status=algorithm.gate_record.get("status"),
        gate_classifications=algorithm.gate_record.get("classifications", []),
        boundary_confidence=algorithm.boundary_record.get("confidence"),
        boundary_start_delta=boundary_start_delta,
        boundary_end_delta=boundary_end_delta,
        gate_start_delta=gate_start_delta,
        gate_end_delta=gate_end_delta,
        label_start_context=label_start_context["category"],
        start_tolerance=start_tolerance,
        end_tolerance=end_tolerance,
    )
    justified_failure = overall_status == "fail" and justification_category not in {"none", "unjustified"}
    return {
        "curve_id": curve.curve_id,
        "run_id": curve.run_id,
        "source_path": _portable_path(curve.source_path),
        "point_count": curve.point_count,
        "label_start_index": label_start,
        "label_end_index": label_end,
        "gate_start_index": gate_start_index,
        "gate_end_index": gate_end_index,
        "boundary_start_index": boundary_start_index,
        "boundary_end_index": boundary_end_index,
        "gate_start_delta": gate_start_delta,
        "gate_end_delta": gate_end_delta,
        "boundary_start_delta": boundary_start_delta,
        "boundary_end_delta": boundary_end_delta,
        "gate_start_pass": gate_start_pass,
        "gate_end_pass": gate_end_pass,
        "boundary_start_pass": boundary_start_pass,
        "boundary_end_pass": boundary_end_pass,
        "gate_pass": gate_pass,
        "boundary_pass": boundary_pass,
        "overall_status": overall_status,
        "outlier_flag": bool(review_flags),
        "review_flags": ";".join(review_flags),
        "failure_category": failure_category,
        "failure_detail": failure_detail,
        "justified_failure": justified_failure,
        "justification_category": justification_category,
        "justification_detail": justification_detail,
        "diagnostic_columns": diagnostic_columns,
        "diagnostic_columns_json": json.dumps(diagnostic_columns, sort_keys=True, separators=(",", ":")),
        "label_start_context": label_start_context["category"],
        "label_start_context_detail": label_start_context["detail"],
        "gate_status": algorithm.gate_record.get("status"),
        "gate_confidence": algorithm.gate_record.get("confidence"),
        "gate_classifications": ";".join(str(item) for item in algorithm.gate_record.get("classifications", []) or []),
        "boundary_confidence": algorithm.boundary_record.get("confidence"),
        "boundary_reason": algorithm.boundary_record.get("reason"),
        "notes": label.get("notes") or "",
    }


def _assessment_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    assessed = [row for row in results if row.get("overall_status") in {"pass", "fail"}]
    passed = [row for row in assessed if row.get("overall_status") == "pass"]
    failed = [row for row in assessed if row.get("overall_status") == "fail"]
    outliers = [row for row in assessed if row.get("outlier_flag")]
    missing = [row for row in results if row.get("overall_status") == "missing_curve"]
    justified = [row for row in failed if row.get("justified_failure")]
    unjustified = [row for row in failed if not row.get("justified_failure")]
    failure_categories: dict[str, int] = {}
    justification_categories: dict[str, int] = {}
    for row in failed:
        category = str(row.get("failure_category") or "uncategorized")
        failure_categories[category] = failure_categories.get(category, 0) + 1
        justification = str(row.get("justification_category") or "unjustified")
        justification_categories[justification] = justification_categories.get(justification, 0) + 1
    return {
        "label_count": len(results),
        "assessed_count": len(assessed),
        "pass_count": len(passed),
        "fail_count": len(failed),
        "justified_fail_count": len(justified),
        "unjustified_fail_count": len(unjustified),
        "outlier_count": len(outliers),
        "missing_count": len(missing),
        "failure_categories": failure_categories,
        "justification_categories": justification_categories,
    }


def _review_flags(
    *,
    label_start: int | None,
    label_end: int | None,
    gate_start_delta: int | None,
    gate_end_delta: int | None,
    boundary_start_delta: int | None,
    boundary_end_delta: int | None,
    gate_start_pass: bool,
    gate_end_pass: bool,
    boundary_start_pass: bool,
    boundary_end_pass: bool,
    gate_status: Any,
    boundary_confidence: Any,
) -> list[str]:
    flags: list[str] = []
    if label_start is None:
        flags.append("missing_human_start_label")
    if label_end is None:
        flags.append("missing_human_end_label")
    if not gate_start_pass:
        flags.append(f"gate_start_delta={gate_start_delta}")
    if not gate_end_pass:
        flags.append(f"gate_end_delta={gate_end_delta}")
    if not boundary_start_pass:
        flags.append(f"boundary_start_delta={boundary_start_delta}")
    if not boundary_end_pass:
        flags.append(f"boundary_end_delta={boundary_end_delta}")
    if str(gate_status or "").lower() in {"review", "fail", "warning"}:
        flags.append(f"gate_status={gate_status}")
    if str(boundary_confidence or "").lower() == "low":
        flags.append("boundary_confidence=low")
    return flags


def _assessment_diagnostic_columns(
    *,
    label_start: int | None,
    label_end: int | None,
    gate_start_index: int | None,
    gate_end_index: int | None,
    boundary_start_index: int | None,
    boundary_end_index: int | None,
    gate_status: Any,
    gate_confidence: Any,
    boundary_confidence: Any,
    boundary_reason: Any,
) -> dict[str, dict[str, Any]]:
    return {
        "raw_curve_human_label": {
            "start_index": label_start,
            "end_index": label_end,
        },
        "gate_experiment_signal": {
            "start_index": gate_start_index,
            "end_index": gate_end_index,
            "status": gate_status,
            "confidence": gate_confidence,
        },
        "boundary_resolution": {
            "start_index": boundary_start_index,
            "end_index": boundary_end_index,
            "confidence": boundary_confidence,
            "reason": boundary_reason,
        },
    }


def _failure_classification(
    *,
    gate_start_pass: bool,
    gate_end_pass: bool,
    boundary_start_pass: bool,
    boundary_end_pass: bool,
    gate_status: Any,
    boundary_confidence: Any,
    review_flags: list[str],
) -> tuple[str, str]:
    if boundary_start_pass and boundary_end_pass and gate_start_pass and gate_end_pass:
        if str(gate_status or "").lower() in {"review", "fail", "warning"}:
            return "gate_routing", ";".join(review_flags)
        if str(boundary_confidence or "").lower() == "low":
            return "boundary_confidence_only", ";".join(review_flags)
        return "none", ""
    if not boundary_start_pass or not gate_start_pass:
        return "start_onset_delta", ";".join(review_flags)
    if not boundary_end_pass:
        return "boundary_endpoint_delta", ";".join(review_flags)
    if not gate_end_pass:
        return "gate_window_delta", ";".join(review_flags)
    return "uncategorized", ";".join(review_flags)


def _failure_justification(
    *,
    overall_status: str,
    failure_category: str,
    boundary_start_pass: bool,
    boundary_end_pass: bool,
    gate_start_pass: bool,
    gate_end_pass: bool,
    gate_status: Any,
    gate_classifications: Any,
    boundary_confidence: Any,
    boundary_start_delta: int | None,
    boundary_end_delta: int | None,
    gate_start_delta: int | None,
    gate_end_delta: int | None,
    label_start_context: str,
    start_tolerance: int,
    end_tolerance: int,
) -> tuple[str, str]:
    if overall_status != "fail":
        return "none", ""

    classifications = _classification_set(gate_classifications)
    hard_tail_classes = {
        "artificial_plateau_or_saturation",
        "disconnected_high_load_fragment",
        "domain_reset_or_reversal",
        "isolated_terminal_jump",
        "non_numeric_tail_cluster",
        "post_experiment_invalid_tail",
    }
    if boundary_start_pass and boundary_end_pass and str(gate_status or "").lower() == "fail":
        hard_evidence = sorted(classifications & hard_tail_classes)
        if hard_evidence:
            detail = (
                "boundary window is label-aligned, but the gate still fails on hard invalid-tail "
                f"evidence: {','.join(hard_evidence)}"
            )
            return "hard_invalid_tail_gate", detail

    if failure_category == "start_onset_delta" and boundary_end_pass and gate_start_pass and gate_end_pass:
        if (
            boundary_start_delta is not None
            and abs(int(boundary_start_delta)) == int(start_tolerance) + 1
            and label_start_context == "preload_to_load_rise"
            and str(gate_status or "").lower() == "ok"
        ):
            detail = (
                "boundary start is one sample beyond strict tolerance during a clean preload-to-load "
                f"rise; delta={boundary_start_delta}, tolerance={start_tolerance}"
            )
            return "borderline_start_sampling_tolerance", detail
        if label_start_context == "ongoing_settling_or_reset":
            detail = (
                "human label lies inside an ongoing multi-step settling/reset transition; this is "
                "kept as a strict outlier rather than driving a bespoke onset rule"
            )
            return "low_priority_multistep_settling_outlier", detail

    detail = (
        f"failure_category={failure_category};boundary_start_delta={boundary_start_delta};"
        f"boundary_end_delta={boundary_end_delta};gate_start_delta={gate_start_delta};"
        f"gate_end_delta={gate_end_delta};gate_status={gate_status};"
        f"boundary_confidence={boundary_confidence};label_start_context={label_start_context};"
        f"end_tolerance={end_tolerance}"
    )
    return "unjustified", detail


def _classification_set(classifications: Any) -> set[str]:
    if classifications is None:
        return set()
    if isinstance(classifications, str):
        raw_items = classifications.replace(",", ";").split(";")
    elif isinstance(classifications, (list, tuple, set)):
        raw_items = [str(item) for item in classifications]
    else:
        raw_items = [str(classifications)]
    return {item.strip() for item in raw_items if item and item.strip()}


def _label_start_context(curve: CurveRecord, label_start: int | None) -> dict[str, str]:
    position = _label_position(curve, label_start)
    if position is None:
        return {"category": "missing_label_start", "detail": ""}
    if position <= 2:
        return {"category": "raw_or_near_raw_start", "detail": f"position={position}"}
    load = [value for value in curve.load]
    strain = [value for value in curve.strain]
    point_count = max(1, curve.point_count)
    window = max(4, min(16, int(point_count ** 0.5)))
    prefix = _numeric_slice(load, max(0, position - window), position)
    future = _numeric_slice(load, position, min(point_count, position + window))
    strain_prefix = _numeric_slice(strain, max(0, position - window), position)
    strain_future = _numeric_slice(strain, position, min(point_count, position + window))
    if len(prefix) < 3 or len(future) < 3:
        return {"category": "insufficient_local_start_context", "detail": f"position={position};window={window}"}
    prefix_range = max(prefix) - min(prefix)
    future_range = max(future) - min(future)
    prefix_steps = [abs(prefix[index] - prefix[index - 1]) for index in range(1, len(prefix))]
    prefix_noise = _median_positive(prefix_steps)
    local_floor = max(prefix_noise, prefix_range / max(1, len(prefix) - 1), 1e-12)
    future_net = future[-1] - future[0]
    future_min_drop = future[0] - min(future)
    future_max_rise = max(future) - future[0]
    strain_future_net = strain_future[-1] - strain_future[0] if len(strain_future) >= 2 else 0.0
    strain_prefix_range = max(strain_prefix) - min(strain_prefix) if strain_prefix else 0.0
    change_floor = local_floor * (len(future) ** 0.5)
    stable_prefix = prefix_range <= change_floor
    if stable_prefix and future_min_drop > change_floor and future_max_rise <= future_min_drop:
        category = "preload_plateau_before_reset"
    elif stable_prefix and abs(future_net) <= change_floor and strain_future_net > strain_prefix_range:
        category = "preload_plateau_with_strain_drift"
    elif stable_prefix and future_max_rise > change_floor and future_net > 0.0:
        category = "preload_to_load_rise"
    elif stable_prefix and future_min_drop > change_floor:
        category = "settling_reset_after_prefix"
    elif not stable_prefix and future_net > change_floor:
        category = "ongoing_load_rise"
    elif not stable_prefix and future_net < -change_floor:
        category = "ongoing_settling_or_reset"
    else:
        category = "mixed_prefix_transition"
    detail = (
        f"position={position};point_index={curve.point_index[position]};window={window};"
        f"prefix_range={prefix_range:.6g};future_range={future_range:.6g};"
        f"future_net={future_net:.6g};future_min_drop={future_min_drop:.6g};"
        f"future_max_rise={future_max_rise:.6g};local_floor={local_floor:.6g};"
        f"strain_future_net={strain_future_net:.6g}"
    )
    return {"category": category, "detail": detail}


def _label_position(curve: CurveRecord, label_index: int | None) -> int | None:
    if label_index is None:
        return None
    try:
        return curve.point_index.index(int(label_index))
    except ValueError:
        detected = int(label_index)
        return detected if 0 <= detected < curve.point_count else None


def _numeric_slice(values: list[float | None], start: int, end: int) -> list[float]:
    return [float(value) for value in values[start:end] if value is not None and math.isfinite(float(value))]


def _median_positive(values: list[float]) -> float:
    positive = sorted(value for value in values if value > 0.0 and math.isfinite(float(value)))
    if not positive:
        return 0.0
    middle = len(positive) // 2
    if len(positive) % 2:
        return float(positive[middle])
    return (float(positive[middle - 1]) + float(positive[middle])) / 2.0


def _gate_contains_label(
    *,
    curve: CurveRecord,
    gate_record: dict[str, Any],
    gate_start_index: int | None,
    gate_end_index: int | None,
    label_start: int | None,
    label_end: int | None,
) -> bool:
    if None in (gate_start_index, gate_end_index, label_start, label_end):
        return False
    if str(gate_record.get("status") or "") != "ok":
        return False
    if str(gate_record.get("confidence") or "") not in {"high", "medium"}:
        return False
    for region in gate_record.get("excluded_regions") or []:
        if not isinstance(region, dict):
            continue
        start = _as_int(region.get("start_index"))
        end = _as_int(region.get("end_index"))
        if start is None:
            continue
        end = start if end is None else end
        start = _label_coordinate_index(curve, start, label_end)
        end = _label_coordinate_index(curve, end, label_end)
        if start is None or end is None:
            continue
        if start <= int(label_end) and end >= int(label_start):
            return False
    return int(gate_start_index) <= int(label_start) and int(gate_end_index) >= int(label_end)


def _gate_starts_before_label(
    *,
    gate_record: dict[str, Any],
    gate_start_index: int | None,
    label_start: int | None,
) -> bool:
    if gate_start_index is None or label_start is None:
        return False
    if str(gate_record.get("status") or "") != "ok":
        return False
    if str(gate_record.get("confidence") or "") not in {"high", "medium"}:
        return False
    return int(gate_start_index) <= int(label_start)


def _label_coordinate_index(curve: CurveRecord, detected_position: int | None, label_index: int | None) -> int | None:
    if detected_position is None:
        return None
    detected = int(detected_position)
    if label_index is None or detected < 0 or detected >= len(curve.point_index):
        return detected
    mapped = int(curve.point_index[detected])
    raw_delta = abs(detected - int(label_index))
    mapped_delta = abs(mapped - int(label_index))
    return mapped if mapped_delta < raw_delta else detected


def _write_assessment_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "overall_status",
        "curve_id",
        "run_id",
        "label_start_index",
        "label_end_index",
        "gate_start_index",
        "gate_end_index",
        "boundary_start_index",
        "boundary_end_index",
        "gate_start_delta",
        "gate_end_delta",
        "boundary_start_delta",
        "boundary_end_delta",
        "gate_pass",
        "boundary_pass",
        "outlier_flag",
        "review_flags",
        "failure_category",
        "failure_detail",
        "justified_failure",
        "justification_category",
        "justification_detail",
        "diagnostic_columns_json",
        "label_start_context",
        "label_start_context_detail",
        "gate_status",
        "gate_confidence",
        "boundary_confidence",
        "source_path",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _curve_from_label(label: dict[str, Any], *, data_root: Path, label_path: Path) -> CurveRecord | None:
    source = str(label.get("source_path") or "").strip()
    run_id = str(label.get("run_id") or "").strip()
    candidates: list[Path] = []
    if source:
        source_path = Path(source)
        if source_path.is_absolute():
            candidates.append(source_path)
        else:
            candidates.extend([ROOT / source_path, data_root / source_path, label_path.parent / source_path])
    curve_id = str(label.get("curve_id") or label.get("label_id") or "")
    if curve_id and "::" in curve_id:
        relative, _, curve_run = curve_id.partition("::")
        run_id = run_id or curve_run
        candidates.extend([data_root / relative, ROOT / relative])
    for candidate in candidates:
        if not candidate.exists():
            continue
        for curve in load_curve_records(candidate, catalogue_root=data_root):
            if not run_id or curve.run_id == run_id:
                return curve
    return None


def _missing_curve_result(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "curve_id": label.get("curve_id") or label.get("label_id"),
        "run_id": label.get("run_id"),
        "source_path": label.get("source_path"),
        "overall_status": "missing_curve",
    }


def _label_markers(start_index: int | None, end_index: int | None) -> list[dict[str, Any]]:
    return [
        {"index": start_index, "label": "label start", "color": "#15803d"} if start_index is not None else {},
        {"index": end_index, "label": "label end", "color": "#b45309"} if end_index is not None else {},
    ]


def _algorithm_gate_markers(algorithm: AlgorithmResult) -> list[dict[str, Any]]:
    return [
        {"index": algorithm.gate_start_index, "label": "gate start", "color": "#0f766e", "dash": True},
        {"index": algorithm.gate_end_index, "label": "gate end", "color": "#0f766e", "dash": True},
    ]


def _algorithm_boundary_markers(algorithm: AlgorithmResult) -> list[dict[str, Any]]:
    return [
        {"index": algorithm.boundary_start_index, "label": "boundary start", "color": "#2563eb", "dash": True},
        {"index": algorithm.boundary_end_index, "label": "boundary end", "color": "#7c3aed", "dash": True},
    ]


def _gate_spans(algorithm: AlgorithmResult) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    window = algorithm.gate_record.get("coherent_window")
    if isinstance(window, dict):
        spans.append(
            {
                "start_index": window.get("start_index"),
                "end_index": window.get("end_index"),
                "color": "#bbf7d0",
                "alpha": 85,
            }
        )
    regions = algorithm.gate_record.get("excluded_regions")
    if isinstance(regions, list):
        for region in regions:
            if not isinstance(region, dict):
                continue
            spans.append(
                {
                    "start_index": region.get("start_index"),
                    "end_index": region.get("end_index"),
                    "color": "#fecaca",
                    "alpha": 90,
                }
            )
    return spans


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        lines = handle.readlines()
    header_index = _csv_header_index(lines)
    if header_index > 0:
        lines = lines[header_index:]
    sample = "".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(lines, dialect=dialect)
    return [dict(row) for row in reader if not _is_units_row(row)]


def _csv_header_index(lines: list[str]) -> int:
    index = _find_csv_header_index(lines)
    return index if index is not None else 0


def _find_csv_header_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[:80]):
        for row in _csv_rows_from_line(line):
            if _header_fields_look_like_curve(row):
                return index
    return None


def _header_fields_look_like_curve(fields: list[str]) -> bool:
    lowered = [field.strip().lower() for field in fields]
    has_load = any("load" in field or "force" in field for field in lowered)
    has_time_or_index = any("time" in field or "scan" in field or "index" in field for field in lowered)
    has_strain = any("strain" in field or "gage" in field or "gauge" in field for field in lowered)
    has_stress = any("stress" in field for field in lowered)
    return has_load and has_time_or_index and (has_strain or has_stress)


def _is_units_row(row: dict[str, str]) -> bool:
    values = [str(value or "").strip().lower() for value in row.values()]
    if not values:
        return False
    unit_markers = {"s", "sec", "n", "kn", "mpa", "mm/mm", "microstrain", "usn", "mm"}
    non_empty = [value.strip("()[] ") for value in values if value]
    return bool(non_empty) and all(value in unit_markers for value in non_empty)


def _database_raw_dir(database_root: Path) -> Path:
    return Path(database_root) / "raw"


def _database_manifest_path(database_root: Path) -> Path:
    return Path(database_root) / "manifest.json"


def _upsert_manifest_record(manifest: dict[str, Any], record: dict[str, Any]) -> None:
    files = manifest.setdefault("files", [])
    if not isinstance(files, list):
        raise ValueError("Database manifest files member is not a list.")
    stored_path = str(record.get("stored_path") or "")
    for index, existing in enumerate(files):
        if isinstance(existing, dict) and str(existing.get("stored_path") or "") == stored_path:
            previous_imported_at = existing.get("imported_at")
            merged = dict(existing)
            merged.update(record)
            if previous_imported_at:
                merged["first_imported_at"] = existing.get("first_imported_at") or previous_imported_at
            files[index] = merged
            return
    files.append(record)


def _dedupe_curves(curves: list[CurveRecord]) -> list[CurveRecord]:
    seen: set[str] = set()
    deduped: list[CurveRecord] = []
    for curve in curves:
        if curve.curve_id in seen:
            continue
        seen.add(curve.curve_id)
        deduped.append(curve)
    return deduped


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_")
    return safe or "curve"


def _is_stress_strain_candidate(path: Path) -> bool:
    name = path.name.lower()
    if "experiment_bound" in name:
        return False
    return "stress_strain" in name and name.endswith(".csv")


def _is_csv_curve_candidate(path: Path) -> bool:
    name = path.name.lower()
    if "experiment_bound" in name:
        return False
    return name.endswith(".csv")


def _is_package_candidate(path: Path) -> bool:
    return path.suffix.lower() in {".mtdp", ".mtda", ".zip"}


def _is_package_curve_member(member: str) -> bool:
    name = member.replace("\\", "/").lower()
    if not name.endswith(".csv"):
        return False
    if name.endswith("/"):
        return False
    if "experiment_bound" in name:
        return False
    if name.startswith("normalized/") and Path(name).name.endswith(".csv"):
        return True
    if name.startswith("raw/") and Path(name).name.endswith(".csv"):
        return True
    if name.startswith("dataset/normalized/") and Path(name).name.endswith(".csv"):
        return True
    if name.startswith("dataset/raw/") and Path(name).name.endswith(".csv"):
        return True
    if "stress_strain" not in Path(name).name:
        return False
    if name.startswith("dataset/03_processed/"):
        return True
    if name.startswith("method_outputs/curves/") and ("_full" in name or name.endswith("_stress_strain.csv")):
        return True
    return False


def _package_curve_members(archive: zipfile.ZipFile) -> list[str]:
    candidates: list[str] = []
    for member in sorted(archive.namelist()):
        if not _is_package_curve_member(member):
            continue
        try:
            data = archive.read(member)
        except KeyError:
            continue
        if not _csv_bytes_look_like_curve(data):
            continue
        candidates.append(member)
    if not candidates:
        return []
    by_run: dict[str, str] = {}
    for member in candidates:
        key = _normalise_run_stem(Path(member).stem).lower()
        current = by_run.get(key)
        if current is None or _package_member_priority(member) < _package_member_priority(current):
            by_run[key] = member
    return sorted(by_run.values())


def _package_member_priority(member: str) -> int:
    name = member.replace("\\", "/").lower()
    if name.startswith("dataset/03_processed/"):
        return 0
    if name.startswith("method_outputs/curves/"):
        return 1
    if name.startswith("normalized/"):
        return 2
    if name.startswith("raw/"):
        return 3
    if name.startswith("dataset/normalized/"):
        return 2
    if name.startswith("dataset/raw/"):
        return 3
    return 9


def _csv_bytes_look_like_curve(data: bytes) -> bool:
    try:
        text = data[:8192].decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data[:8192].decode("latin-1", errors="replace")
    return _find_csv_header_index(text.splitlines(True)) is not None


def _csv_rows_from_line(line: str) -> list[list[str]]:
    try:
        return list(csv.reader([line]))
    except csv.Error:
        return []


def _find_step(steps: list[Any], operation_id: str) -> dict[str, Any] | None:
    for step in steps:
        if isinstance(step, dict) and step.get("op") == operation_id:
            return step
    return None


def _first_present(row: dict[str, str], names: tuple[str, ...]) -> str | None:
    lower = {key.lower(): key for key in row}
    for name in names:
        if name in row:
            return name
        match = lower.get(name.lower())
        if match:
            return match
    return None


def _first_column_containing(row: dict[str, str], tokens: tuple[str, ...]) -> str | None:
    for key in row:
        lowered = key.lower()
        if any(token.lower() in lowered for token in tokens):
            return key
    return None


def _gauge_strain_columns(row: dict[str, str]) -> list[str]:
    columns: list[str] = []
    for key in row:
        lowered = key.lower()
        if "strain" not in lowered and "gage" not in lowered and "gauge" not in lowered:
            continue
        if "load" in lowered or "stress" in lowered:
            continue
        columns.append(key)
    return columns


def _load_from_row(row: dict[str, str], *, load_col: str | None) -> float | None:
    value = _as_float(row.get(load_col)) if load_col else None
    if value is None:
        return None
    if load_col and "kn" in load_col.lower():
        return value * 1000.0
    return value


def _strain_from_row(row: dict[str, str], *, strain_col: str | None, front_col: str | None, rear_col: str | None) -> float | None:
    strain_value = _as_float(row.get(strain_col)) if strain_col else None
    if strain_value is not None:
        return strain_value
    front = _as_float(row.get(front_col)) if front_col else None
    rear = _as_float(row.get(rear_col)) if rear_col else None
    values = [abs(value) for value in (front, rear) if value is not None]
    if not values:
        return None
    mean_value = sum(values) / len(values)
    if mean_value > 0.1:
        return mean_value * 1e-6
    return mean_value


def _run_id_from_path(path: Path) -> str:
    stem = path.stem
    normalised_stem = _normalise_run_stem(stem)
    if normalised_stem != stem:
        return normalised_stem
    for part in stem.split("__"):
        if part.lower().startswith("run_"):
            return _normalise_run_stem(part)
    return stem


def _normalise_run_stem(stem: str) -> str:
    value = stem
    for suffix in ("_stress_strain", "_raw", "_normalized"):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _curve_id(path: Path, run_id: str, *, catalogue_root: Path | None = None) -> str:
    base = catalogue_root or ROOT
    try:
        relative = path.resolve().relative_to(base.resolve())
    except ValueError:
        try:
            relative = path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            relative = path.resolve()
    return f"{relative.as_posix()}::{run_id}"


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _percent_series(values: list[float | None]) -> list[float | None]:
    return [value * 100.0 if value is not None else None for value in values]


def _value_for_index(point_indices: list[int], values: list[float | None], index: int) -> float | None:
    try:
        position = point_indices.index(index)
    except ValueError:
        return None
    if position < 0 or position >= len(values):
        return None
    return values[position]


def _spin_value(spin: Any) -> int | None:
    value = int(spin.value())
    return value if value >= 0 else None


def _has_label(label: dict[str, Any] | None) -> bool:
    if not isinstance(label, dict):
        return False
    return _as_int(label.get("label_start_index")) is not None and _as_int(label.get("label_end_index")) is not None


def _delta(detected: int | None, label: int | None) -> int | None:
    if detected is None or label is None:
        return None
    return int(detected) - int(label)


def _within_tolerance(delta: int | None, tolerance: int) -> bool:
    return delta is not None and abs(delta) <= tolerance


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "#value!"}:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _fmt_axis(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1000 or (magnitude > 0 and magnitude < 0.01):
        return f"{value:.2e}"
    return f"{value:.3g}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
