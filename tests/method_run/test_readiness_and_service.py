from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.mtdp import MTDPPackageReader
from methods.core.method_executor import MethodExecutor
from methods.core.method_package import MethodPackage
from methods.core.method_run_service import MethodRunRequest, MethodRunService, load_mapping
from readiness import MethodReadinessError, ReadinessChecker


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def source() -> Any:
    return MTDPPackageReader().read(INPUT)


@pytest.fixture(scope="module")
def method() -> MethodPackage:
    return MethodPackage.load(METHOD)


@pytest.fixture(scope="module")
def mapping() -> dict[str, Any]:
    return load_mapping(MAPPING)


def test_iso14126_method_inputs_load(method: MethodPackage) -> None:
    requirements = method.method_inputs["requirements"]
    assert method.method_inputs["method_id"] == "iso14126_2023"
    assert {item["requirement_id"] for item in requirements} >= {
        "iso14126.geometry.width",
        "iso14126.geometry.thickness",
        "iso14126.channel.load",
        "iso14126.channel.front_strain",
        "iso14126.channel.rear_strain",
    }


def test_canonical_package_is_ready_with_report_warnings(
    source: Any,
    method: MethodPackage,
    mapping: dict[str, Any],
) -> None:
    report = ReadinessChecker().check(source=source, method_package=method, mapping=mapping)
    missing = report.missing_rows()
    assert report.status.value == "READY_WITH_WARNINGS"
    assert report.blocks_execution is False
    assert report.summary["execution_critical_passed"] == report.summary["execution_critical_total"]
    assert missing
    assert all(row["severity"] != "execution_critical" for row in missing)


def test_missing_execution_critical_mapping_returns_mapping_required(
    source: Any,
    method: MethodPackage,
    mapping: dict[str, Any],
) -> None:
    bad_mapping = json.loads(json.dumps(mapping))
    bad_mapping["channels"].pop("load")

    report = ReadinessChecker().check(source=source, method_package=method, mapping=bad_mapping)

    assert report.status.value == "MAPPING_REQUIRED"
    assert report.blocks_execution is True
    assert any(
        row["requirement_id"] == "iso14126.channel.load" and row["status"] == "mapping_missing"
        for row in report.missing_rows()
    )


def test_missing_execution_critical_value_returns_not_ready(
    source: Any,
    method: MethodPackage,
    mapping: dict[str, Any],
) -> None:
    bad_source = _source_with_empty_channel(source, run_id="run_006", channel_name="Load")

    report = ReadinessChecker().check(source=bad_source, method_package=method, mapping=mapping)

    assert report.status.value == "NOT_READY"
    assert report.blocks_execution is True
    assert any(
        row["run_id"] == "run_006" and row["requirement_id"] == "iso14126.channel.load" and row["status"] == "empty"
        for row in report.missing_rows()
    )


def test_not_ready_prevents_method_resolve(
    source: Any,
    method: MethodPackage,
    mapping: dict[str, Any],
) -> None:
    bad_source = _source_with_empty_channel(source, run_id="run_006", channel_name="Load")

    with pytest.raises(MethodReadinessError) as excinfo:
        MethodExecutor().execute(bad_source, method, mapping)

    assert excinfo.value.report.status.value == "NOT_READY"


def test_ready_with_warnings_allows_execution(
    source: Any,
    method: MethodPackage,
    mapping: dict[str, Any],
) -> None:
    result = MethodExecutor().execute(source, method, mapping)

    assert result.readiness_report["status"] == "READY_WITH_WARNINGS"
    assert result.readiness_report["blocks_execution"] is False
    assert result.operation_log
    assert result.validation_report["summary"]["status"] == "pass"


def test_method_run_service_runs_canonical_flow_and_writes_readiness_artifacts(tmp_path: Path) -> None:
    before = _sha256(INPUT)
    output = tmp_path / "service_run.mtda"
    progress_events: list[dict[str, Any]] = []
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            generate_workbench=True,
        ),
        progress_callback=progress_events.append,
    )

    assert result.status == "completed"
    assert result.readiness_status == "READY_WITH_WARNINGS"
    assert result.output_path == output
    assert result.workbench_path is not None
    assert (result.workbench_path / "index.html").exists()
    assert result.acceptance_report["summary"]["total_runs"] >= 1
    assert isinstance(result.acceptance_report["flags"], list)
    assert _sha256(INPUT) == before

    with zipfile.ZipFile(output) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {
            "readiness/readiness_report.json",
            "readiness/readiness_summary.csv",
            "readiness/resolved_inputs.csv",
            "readiness/missing_inputs.csv",
        } <= names
        audit_html = archive.read("interactive_report/index.html").decode("utf-8")
        assert "Audit Overview" in audit_html
        assert "Package Readiness" not in audit_html
        readiness = json.loads(archive.read("readiness/readiness_report.json"))
        summary_rows = list(csv.DictReader(io.StringIO(archive.read("readiness/readiness_summary.csv").decode("utf-8"))))
    assert readiness["status"] == "READY_WITH_WARNINGS"
    assert summary_rows[0]["status"] == "READY_WITH_WARNINGS"
    phases = [event["phase"] for event in progress_events]
    for phase in (
        "load_input_package",
        "load_method_package",
        "load_mapping",
        "readiness_check",
        "method_resolve",
        "method_reduce",
        "validation",
        "acceptance",
        "write_mtda",
        "build_audit_report",
        "build_workbench_optional",
        "complete",
    ):
        assert phase in phases
    assert any(event.get("runs") for event in progress_events)


def test_method_run_service_blocks_missing_mapping_before_output(tmp_path: Path) -> None:
    bad_mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    bad_mapping["channels"].pop("load")
    mapping_path = tmp_path / "missing_load_mapping.json"
    mapping_path.write_text(json.dumps(bad_mapping), encoding="utf-8")
    output = tmp_path / "blocked.mtda"

    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=mapping_path,
            output_path=output,
        )
    )

    assert result.status == "not_ready"
    assert result.readiness_status == "MAPPING_REQUIRED"
    assert result.output_path is None
    assert not output.exists()
    assert any("iso14126.channel.load" in error for error in result.errors)


def _source_with_empty_channel(source: Any, *, run_id: str, channel_name: str) -> Any:
    runs = []
    for run in source.runs:
        if run.run_id != run_id:
            runs.append(run)
            continue
        channel = run.channel(channel_name)
        assert channel is not None
        bad_channel = replace(channel, values=tuple(None for _ in channel.values))
        channels = dict(run.channels)
        channels[channel.name] = bad_channel
        runs.append(replace(run, channels=channels))
    return replace(source, runs=tuple(runs))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
