from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.layouts import MTDAAlignedLayout
from methods.core.method_run_service import MethodRunRequest, MethodRunService


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


@pytest.fixture(scope="module")
def service_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage16_method_service") / "service.mtda"
    before = _sha256(INPUT)
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    assert result.readiness_status == "READY_WITH_WARNINGS"
    assert _sha256(INPUT) == before
    return output


@pytest.fixture(scope="module")
def cli_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage16_method_cli") / "cli.mtda"
    before = _sha256(INPUT)
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--input",
            str(INPUT),
            "--method",
            str(METHOD),
            "--mapping",
            str(MAPPING),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Readiness: READY_WITH_WARNINGS" in completed.stdout
    assert "Wrote" in completed.stdout
    assert _sha256(INPUT) == before
    return output


def test_canonical_method_run_success_and_mtda_integrity(service_mtda: Path) -> None:
    with zipfile.ZipFile(service_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        manifest = json.loads(archive.read(MTDAAlignedLayout.manifest))
        provenance = json.loads(archive.read(MTDAAlignedLayout.provenance))
        readiness = json.loads(archive.read(MTDAAlignedLayout.readiness))["readiness_report"]
        validation = json.loads(archive.read(MTDAAlignedLayout.validation))["validation_report"]
        method_outputs = json.loads(archive.read(MTDAAlignedLayout.method_outputs))
        checksums = json.loads(archive.read(MTDAAlignedLayout.checksums))

    assert manifest["package_format"] == "mtda"
    assert manifest["layout_version"] == MTDAAlignedLayout.name
    assert manifest["method_id"] == "iso14126_2023"
    assert manifest["artifact_surfaces"]["test_report"] == f"{MTDAAlignedLayout.reports_prefix}test_report_shell.html"
    assert manifest["artifact_surfaces"]["audit_report"] == f"{MTDAAlignedLayout.reports_prefix}audit_report_shell.html"
    assert manifest["artifact_surfaces"]["test_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}test_report.html"
    assert manifest["artifact_surfaces"]["audit_report_raw"] == f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
    assert manifest["artifact_surfaces"]["method_outputs"] == MTDAAlignedLayout.method_outputs
    assert provenance["source_mtdp"]["checksum"] == _sha256(INPUT)
    assert readiness["status"] == "READY_WITH_WARNINGS"
    assert readiness["blocks_execution"] is False
    assert validation["summary"]["status"] == "pass"
    assert method_outputs["acceptance_report"]["summary"]["total_runs"] == 7
    assert {
        MTDAAlignedLayout.index,
        MTDAAlignedLayout.manifest,
        MTDAAlignedLayout.provenance,
        MTDAAlignedLayout.readiness,
        MTDAAlignedLayout.validation,
        MTDAAlignedLayout.method_outputs,
        f"{MTDAAlignedLayout.aggregate_prefix}results_table.csv",
        f"{MTDAAlignedLayout.reports_prefix}test_report.html",
        f"{MTDAAlignedLayout.reports_prefix}audit_report.html",
    } <= names
    assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
    assert set(checksums["files"]) == names - {MTDAAlignedLayout.checksums}
    assert _checksums_match_archive(service_mtda, checksums)


def test_missing_required_value_blocks_execution_before_resolve(tmp_path: Path) -> None:
    broken_package = _package_with_blank_width(tmp_path)
    output = tmp_path / "blank_width.mtda"

    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=broken_package,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
        )
    )

    assert result.status == "not_ready"
    assert result.readiness_status == "NOT_READY"
    assert result.output_path is None
    assert not output.exists()
    assert any("iso14126.geometry.width" in error for error in result.errors)


def test_mapping_failure_is_caught_before_resolve(tmp_path: Path) -> None:
    bad_mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    bad_mapping["channels"].pop("load")
    mapping_path = tmp_path / "missing_load_mapping.json"
    mapping_path.write_text(json.dumps(bad_mapping), encoding="utf-8")
    output = tmp_path / "missing_load.mtda"

    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=mapping_path,
            output_path=output,
            overwrite=True,
        )
    )

    assert result.status == "not_ready"
    assert result.readiness_status == "MAPPING_REQUIRED"
    assert result.output_path is None
    assert not output.exists()
    assert any("iso14126.channel.load" in error for error in result.errors)


def test_readiness_warnings_allow_execution_and_are_archived(service_mtda: Path) -> None:
    readiness_bundle = _json_member(service_mtda, MTDAAlignedLayout.readiness)
    readiness = readiness_bundle["readiness_report"]
    missing_rows = readiness_bundle["missing_inputs"]
    summary_rows = readiness_bundle["readiness_summary"]

    assert readiness["status"] == "READY_WITH_WARNINGS"
    assert readiness["blocks_execution"] is False
    assert missing_rows
    assert all(row["severity"] != "execution_critical" for row in missing_rows)
    assert summary_rows[0]["status"] == "READY_WITH_WARNINGS"


def test_method_run_service_and_cli_use_same_backend_contract(service_mtda: Path, cli_mtda: Path) -> None:
    service_outputs = _json_member(service_mtda, MTDAAlignedLayout.method_outputs)
    cli_outputs = _json_member(cli_mtda, MTDAAlignedLayout.method_outputs)
    service_specimens = service_outputs["specimen_results"]
    cli_specimens = cli_outputs["specimen_results"]
    service_validation = _json_member(service_mtda, MTDAAlignedLayout.validation)["validation_report"]
    cli_validation = _json_member(cli_mtda, MTDAAlignedLayout.validation)["validation_report"]
    service_selection = service_outputs["selection_sets"]
    cli_selection = cli_outputs["selection_sets"]
    service_report = _json_member(service_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")
    cli_report = _json_member(cli_mtda, f"{MTDAAlignedLayout.reports_prefix}test_report.json")

    assert [row["run_id"] for row in service_specimens] == [row["run_id"] for row in cli_specimens]
    assert _metric_by_run(service_specimens, "compressive_strength_MPa") == pytest.approx(
        _metric_by_run(cli_specimens, "compressive_strength_MPa")
    )
    assert service_validation["summary"] == cli_validation["summary"]
    assert service_selection["default_selection_set"] == cli_selection["default_selection_set"]
    assert service_report["selection_set"] == cli_report["selection_set"] == "final_report_runs"
    assert service_report["selection_source"] == cli_report["selection_source"]
    assert service_report["summary"]["selected_run_count"] == cli_report["summary"]["selected_run_count"]


def _package_with_blank_width(tmp_path: Path) -> Path:
    output = tmp_path / "blank_width.mtdp"
    shutil.copyfile(INPUT, output)
    temp = tmp_path / "rewrite"
    temp.mkdir()
    rewritten = tmp_path / "blank_width_rewritten.mtdp"
    with zipfile.ZipFile(output) as source, zipfile.ZipFile(rewritten, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            data = source.read(name)
            if name == "normalized/run_001.csv":
                text = data.decode("utf-8").replace("Width,9.91,mm", "Width,,mm", 1)
                data = text.encode("utf-8")
            target.writestr(name, data)
    return rewritten


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _checksums_match_archive(path: Path, checksums: dict[str, Any]) -> bool:
    with zipfile.ZipFile(path) as archive:
        for member, expected in checksums["files"].items():
            if member == "checksums.json":
                continue
            actual = hashlib.sha256(archive.read(member)).hexdigest()
            if actual != expected:
                return False
    return True


def _metric_by_run(rows: list[dict[str, str]], metric: str) -> dict[str, float]:
    return {row["run_id"]: float(row[metric]) for row in rows}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
