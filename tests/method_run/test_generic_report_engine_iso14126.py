from __future__ import annotations

import inspect
import json
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import reporting.report_builder as report_builder_module
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from reporting.core.report_engine import GenericReportEngine
from reporting.iso14126_report_builder import ISO14126ReportBuilder
from reporting.report_builder import ReportBuilder


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def generic_engine_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("generic_report_engine") / "generic.mtda"
    result = MethodRunService().run(MethodRunRequest(INPUT, METHOD, MAPPING, output))
    assert result.status == "completed"
    return output


def test_report_builder_uses_generic_engine_without_iso_branch() -> None:
    source = inspect.getsource(report_builder_module.ReportBuilder)

    assert isinstance(ReportBuilder().engine, GenericReportEngine)
    assert "ISO14126ReportBuilder" not in source
    assert "iso14126" not in source.casefold()


def test_legacy_iso_builder_is_thin_delegator() -> None:
    builder = ISO14126ReportBuilder()

    assert isinstance(builder.engine, GenericReportEngine)


def test_generic_engine_preserves_iso14126_report_contract(generic_engine_mtda: Path) -> None:
    with zipfile.ZipFile(generic_engine_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {
            "dataset/04_reports/test_report.html",
            "dataset/04_reports/test_report_shell.html",
            "dataset/04_reports/test_report.json",
            "dataset/04_reports/test_report.pdf",
            "dataset/04_reports/audit_report.html",
            "dataset/04_reports/audit_report_shell.html",
            "dataset/04_reports/audit_report.json",
            "dataset/04_reports/audit_report.csv",
            "metadata/manifest.json",
            "metadata/surface_manifest.json",
        } <= names
        report = json.loads(archive.read("dataset/04_reports/test_report.json"))
        document = report["report_document"]
        vega = report["aggregate_plot_spec"]

    assert report["schema_id"] == "method.iso14126_report.v0_1"
    assert report["report_recipe_id"] == "iso14126_report_v0_2"
    assert len(report["report_sections"]) == 12
    assert document["schema_id"] == "report.document.v0_1"
    assert len(document["sections"]) == 12
    assert any(
        block["type"] == "vega_plot"
        for section in document["sections"]
        for block in section["blocks"]
    )
    assert vega["schema_id"] == "method.aggregate_plot_spec.v0_1"
    assert vega["layers"]["mean_curve"]["enabled"] is True
