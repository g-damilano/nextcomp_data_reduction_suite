from __future__ import annotations

import csv
import hashlib
import io
import json
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

from methods.core.method_package import MethodPackage


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


@pytest.fixture(scope="module")
def mtda_archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    before = _sha256(INPUT)
    output = tmp_path_factory.mktemp("acceptance_selection") / "CAG-CF-Modied-ULV20.mtda"
    subprocess.run(
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
    assert _sha256(INPUT) == before
    return output


def test_acceptance_recipe_loads() -> None:
    package = MethodPackage.load(METHOD)
    acceptance = package.acceptance_recipe["acceptance"]
    assert acceptance["recipe_id"] == "iso14126_acceptance_v0_1"
    assert acceptance["default_selection_set"] == "auto_recommended_runs"
    assert {rule["id"] for rule in acceptance["flags"]} >= {
        "user_validity_invalid",
        "bending_exceeds_review_threshold",
        "validation_failed",
    }


def test_acceptance_artifacts_and_checksums_exist(mtda_archive: Path) -> None:
    required = {
        "acceptance/acceptance_report.json",
        "acceptance/acceptance_summary.csv",
        "acceptance/run_flags.csv",
        "acceptance/selection_sets.json",
        "acceptance/selection_membership.csv",
        "acceptance/discharged_runs.csv",
        "acceptance/discharge_report.json",
        "acceptance/human_decisions.json",
        "acceptance/human_decisions.csv",
        "acceptance/override_ledger.json",
        "acceptance/selection_sets_final.json",
        "acceptance/selection_membership_final.csv",
        "acceptance/final_report_runs.csv",
        "method_outputs/dataset_summary_by_selection.csv",
        "method_package/acceptance_recipe.yaml",
    }
    with zipfile.ZipFile(mtda_archive) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert required <= names
        checksums = json.loads(archive.read("checksums.json"))
    assert required <= set(checksums["files"])


def test_acceptance_engine_emits_structured_flags(mtda_archive: Path) -> None:
    report = _json_member(mtda_archive, "acceptance/acceptance_report.json")
    flags = report["flags"]
    assert report["schema_id"] == "method.acceptance_report.v0_1"
    assert report["default_selection_set"] == "auto_recommended_runs"
    assert flags

    required = {
        "flag_id",
        "run_id",
        "source",
        "severity",
        "category",
        "message",
        "evidence_refs",
        "operation_ids",
        "validation_check_ids",
        "inspection_ids",
        "selection_effect",
    }
    assert all(required <= set(flag) for flag in flags)
    assert not any(flag["category"] == "statistical_screening" for flag in flags)
    run_002_user_flag = next(flag for flag in flags if flag["flag_id"] == "user_validity_invalid:run_002")
    assert run_002_user_flag["severity"] == "exclude"
    assert run_002_user_flag["category"] == "user_validity"
    assert run_002_user_flag["operation_ids"]
    assert report["run_states"]["run_002"] == "excluded"


def test_selection_sets_are_generated(mtda_archive: Path) -> None:
    selection_sets = _json_member(mtda_archive, "acceptance/selection_sets.json")
    assert selection_sets["schema_id"] == "method.selection_sets.v0_1"
    assert selection_sets["default_selection_set"] == "auto_recommended_runs"
    by_id = {item["selection_id"]: item for item in selection_sets["selection_sets"]}
    assert {
        "all_runs",
        "user_valid_runs",
        "auto_recommended_runs",
        "review_required_runs",
        "excluded_runs",
        "human_curated_runs",
    } <= set(by_id)
    assert len(by_id["all_runs"]["run_ids"]) == 7
    assert "run_002" not in by_id["user_valid_runs"]["run_ids"]
    assert by_id["excluded_runs"]["run_ids"] == ["run_002"]
    assert by_id["human_curated_runs"]["run_ids"] == []


def test_final_selection_artifacts_preserve_machine_acceptance(mtda_archive: Path) -> None:
    machine_sets = _json_member(mtda_archive, "acceptance/selection_sets.json")
    final_sets = _json_member(mtda_archive, "acceptance/selection_sets_final.json")
    final_membership = _csv_member(mtda_archive, "acceptance/selection_membership_final.csv")
    final_runs = _csv_member(mtda_archive, "acceptance/final_report_runs.csv")
    human_decisions = _json_member(mtda_archive, "acceptance/human_decisions.json")

    machine_by_id = {item["selection_id"]: item for item in machine_sets["selection_sets"]}
    final_machine_by_id = {
        item["selection_id"]: item
        for item in final_sets["selection_sets"]
        if item.get("source") == "machine"
    }

    assert final_sets["default_selection_set"] == "final_report_runs"
    assert final_sets["machine_default_selection_set"] == "auto_recommended_runs"
    assert final_sets["selection_source"] == "machine_default_confirmed"
    assert final_machine_by_id["auto_recommended_runs"]["run_ids"] == machine_by_id["auto_recommended_runs"]["run_ids"]
    assert len(final_membership) == 7
    assert len(final_runs) == 7
    assert human_decisions["decisions"] == []


def test_excluded_runs_remain_in_outputs(mtda_archive: Path) -> None:
    specimen_rows = _csv_member(mtda_archive, "method_outputs/specimen_results.csv")
    curve_rows = _csv_member(mtda_archive, "method_outputs/curves/stress_strain_family.csv")
    assert "run_002" in {row["run_id"] for row in specimen_rows}
    assert "run_002" in {row["run_id"] for row in curve_rows}
    assert next(row for row in specimen_rows if row["run_id"] == "run_002")["validity"] == "accepted"


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _json_member(path: Path, member: str) -> Any:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
