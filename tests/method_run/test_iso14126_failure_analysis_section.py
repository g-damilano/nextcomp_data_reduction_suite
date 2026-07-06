from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_run_service import MethodRunRequest, MethodRunService


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def iso14126_failure_analysis_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("iso14126_failure_analysis") / "report.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            generate_workbench=False,
        )
    )
    assert result.status == "completed"
    return output


def test_iso14126_test_report_inserts_failure_analysis_before_deviations(iso14126_failure_analysis_mtda: Path) -> None:
    report = _json_member(iso14126_failure_analysis_mtda, "dataset/04_reports/test_report.json")
    document = report["report_document"]
    html = _text_member(iso14126_failure_analysis_mtda, "dataset/04_reports/test_report.html")

    assert [section["section_id"] for section in report["report_sections"]][8:12] == [
        "aggregated_results",
        "failure_analysis",
        "deviations_from_standard",
        "remarks",
    ]
    assert html.find("9. Aggregated Results") < html.find("10. Failure Analysis")
    assert html.find("10. Failure Analysis") < html.find("11. Deviations from Standard")
    assert html.find("11. Deviations from Standard") < html.find("12. Remarks")
    assert "<b>10</b><span>Failure Analysis</span>" in html
    assert report["failure_analysis"]
    assert {row["Field"] for row in report["failure_analysis"]} == {
        "Failure Observation Completeness",
        "Invalid Specimens",
        "Bending Compliance",
        "Notes",
    }
    assert all("Basis" not in row for row in report["failure_analysis"])
    failure_summary = "\n".join(str(row.get("Value", "")) for row in report["failure_analysis"])
    assert "operator validity/failure observation" not in failure_summary
    assert "Automatic note" not in failure_summary
    assert "Final report runs" not in failure_summary
    assert "Accepted" not in failure_summary
    assert "Failure mode recorded for 0 of 3 reported specimens; failure location recorded for 0 of 3." in failure_summary
    assert report["failure_analysis_observations"]
    assert [row["Run #"] for row in report["failure_analysis_observations"]] == ["#1", "#3", "#7"]
    assert all(row["Failure mode"] == "not recorded" for row in report["failure_analysis_observations"])
    assert all(row["Failure location"] == "not recorded" for row in report["failure_analysis_observations"])
    invalid_rows = report["failure_analysis_invalid_specimens"]
    assert [row["Run #"] for row in invalid_rows] == ["#2", "#4", "#5", "#6"]
    section = next(item for item in document["sections"] if item["id"] == "failure_analysis")
    assert [block["id"] for block in section["blocks"]] == [
        "failure_analysis_summary",
        "failure_observation_table",
        "bending_distribution_plot",
        "invalid_specimen_summary",
    ]
    assert html.find("Failure Analysis Summary") < html.find("Specimen Failure Observations")
    assert html.find("Specimen Failure Observations") < html.find("Bending distribution over assessed domain")
    assert "Accepted Specimen Failure" not in html


def test_iso14126_failure_analysis_bending_plot_artifact_is_present(iso14126_failure_analysis_mtda: Path) -> None:
    report = _json_member(iso14126_failure_analysis_mtda, "dataset/04_reports/test_report.json")
    spec = _vega_spec(report["report_document"], "failure_analysis_bending_distribution")
    summary = report["failure_analysis_bending_distribution"]["summary"]
    observations = report["failure_analysis_observations"]

    assert report["failure_analysis_bending_distribution"]["assessed_domain"] == "10-90 % Fmax"
    assert report["failure_analysis_bending_distribution"]["threshold_percent"] == 10.0
    assert report["failure_analysis_bending_distribution"]["points"]
    assert spec["datasets"]["threshold"] == [{"threshold_percent": 10.0}]
    assert spec["datasets"]["criterion_band"][0]["threshold_percent"] == 10.0
    mark_types = [layer["mark"]["type"] for layer in spec["layer"]]
    assert mark_types == ["rect", "rule", "rule", "bar", "tick"]
    assert spec["layer"][3]["encoding"]["y"]["field"] == "q1_bending_percent"
    assert spec["layer"][3]["encoding"]["y2"]["field"] == "q3_bending_percent"
    assert not any(layer["mark"]["type"] == "point" for layer in spec["layer"])
    assert "legend" not in spec.get("config", {})
    assert "Classification" not in json.dumps(spec)
    assert "bending_classification" not in json.dumps(report["failure_analysis_bending_distribution"])
    assert report["failure_analysis_bending_distribution"]["assessed_domain"] == "10-90 % Fmax"
    assert "assessed_point_count" in summary[0]
    assert observations[0]["Failure mode"] == "not recorded"
    assert observations[0]["Failure location"] == "not recorded"


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    import csv
    import io

    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _vega_spec(document: dict[str, Any], spec_id: str) -> dict[str, Any]:
    for section in document.get("sections", []):
        for block in section.get("blocks", []):
            data = block.get("data") if isinstance(block.get("data"), dict) else {}
            if data.get("spec_id") == spec_id:
                spec = data.get("vega_lite_spec")
                return spec if isinstance(spec, dict) else {}
    raise AssertionError(f"Vega spec not found: {spec_id}")
