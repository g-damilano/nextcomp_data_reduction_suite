from __future__ import annotations

import csv
import io
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
def stage14_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage14_curve_family") / "CAG-CF-Modied-ULV20.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
        )
    )
    assert result.status == "completed"
    return output


def test_iso14126_mtda_contains_curve_family_artifacts(stage14_mtda: Path) -> None:
    with zipfile.ZipFile(stage14_mtda) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}

    assert {
        "method_package/curve_family_acceptance_recipe.yaml",
        "acceptance/curve_family/curve_family_report.json",
        "acceptance/curve_family/curve_family_scores.csv",
        "acceptance/curve_family/curve_family_flags.csv",
        "acceptance/curve_family/reference_curves.csv",
        "acceptance/curve_family/aligned_curve_family.csv",
        "acceptance/curve_family/residuals_long.csv",
        "acceptance/curve_family/policy_resolved.json",
    } <= names


def test_curve_family_outputs_are_integrated_into_surfaces(stage14_mtda: Path) -> None:
    report = _json_member(stage14_mtda, "acceptance/curve_family/curve_family_report.json")
    scores = _csv_member(stage14_mtda, "acceptance/curve_family/curve_family_scores.csv")
    acceptance = _json_member(stage14_mtda, "acceptance/acceptance_report.json")
    audit = _json_member(stage14_mtda, "audit/audit_report.json")
    workbench = _json_member(stage14_mtda, "workbench/operation_trace.json")
    html = _text_member(stage14_mtda, "workbench/index.html")

    assert report["schema_id"] == "method.curve_family_report.v0_1"
    assert report["summary"]["assessed_runs"] == len(scores)
    assert scores
    assert {"normalized_rmse", "curve_correlation", "leave_one_out_mean_shift", "classification"} <= set(scores[0])
    assert acceptance["curve_family_assessment"]["summary"]["assessed_runs"] == len(scores)
    assert audit["curve_family_assessment"]["score_count"] == len(scores)
    assert workbench["curve_family_scores"]
    assert "Curve-Family Assessment" in html
    assert "curveFamilyChart" in html


def test_human_override_can_supersede_curve_family_recommendation(stage14_mtda: Path) -> None:
    acceptance = _json_member(stage14_mtda, "acceptance/acceptance_report.json")
    flags = [flag for flag in acceptance["flags"] if flag["source"] == "curve_family_assessment"]
    assert all(flag["severity"] == "review" for flag in flags)


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
