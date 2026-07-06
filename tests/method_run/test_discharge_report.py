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
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


@pytest.fixture(scope="module")
def mtda_archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    before = _sha256(INPUT)
    output = tmp_path_factory.mktemp("discharge_report") / "CAG-CF-Modied-ULV20.mtda"
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


def test_discharge_report_contains_review_and_excluded_records(mtda_archive: Path) -> None:
    report = _json_member(mtda_archive, "acceptance/discharge_report.json")
    assert report["schema_id"] == "method.discharge_report.v0_1"
    assert report["default_selection_set"] == "auto_recommended_runs"
    records = report["records"]
    assert records
    by_run = {record["run_id"]: record for record in records}
    assert "run_002" in by_run
    assert by_run["run_002"]["state"] == "excluded"
    assert by_run["run_002"]["included_in_default"] is False
    assert by_run["run_002"]["primary_reason"]
    assert any(flag["severity"] == "exclude" for flag in by_run["run_002"]["flags"])
    assert by_run["run_002"]["operation_refs"]

    review_records = [record for record in records if record["state"] == "review_required"]
    assert review_records
    assert all(record["included_in_default"] is False for record in review_records)


def test_discharged_runs_csv_mirrors_report(mtda_archive: Path) -> None:
    rows = _csv_member(mtda_archive, "acceptance/discharged_runs.csv")
    assert rows
    run_002 = next(row for row in rows if row["run_id"] == "run_002")
    assert run_002["state"] == "excluded"
    assert run_002["included_in_default"] == "False"
    assert "user_validity_invalid:run_002" in run_002["flags"]


def test_audit_report_includes_acceptance_and_discharge_views(mtda_archive: Path) -> None:
    with zipfile.ZipFile(mtda_archive) as archive:
        html = archive.read("interactive_report/index.html").decode("utf-8")
        validation_report = json.loads(archive.read("validation/validation_report.json"))
    assert validation_report["summary"]["status"] == "pass"
    assert validation_report["summary"]["total_checks"] == 12
    assert "Decision Register" in html
    assert "Run disposition register" in html
    assert "Final report run set summary" in html
    assert "Discharge / review / exclusion decisions" not in html
    assert "Downstream Effect" not in html
    assert "Human Override State" not in html
    assert "Reviewer action / override" not in html
    assert "Manual accept/exclude decision required" not in html
    assert "#packet-run_001" in html
    assert "#packet-run 001" not in html
    assert "Run-wise Evidence Packets" in html
    assert "tools/run_method_development.py" not in html


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
