from __future__ import annotations

import csv
import hashlib
import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


@pytest.fixture(scope="module")
def mtda_archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    before = _sha256(INPUT)
    output = tmp_path_factory.mktemp("dataset_summary_by_selection") / "CAG-CF-Modied-ULV20.mtda"
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


def test_dataset_summary_rows_are_selection_aware(mtda_archive: Path) -> None:
    rows = _csv_member(mtda_archive, "method_outputs/dataset_summary_by_selection.csv")
    assert rows
    assert all(row["selection_set"] for row in rows)
    assert {"all_runs", "user_valid_runs", "auto_recommended_runs", "review_required_runs", "excluded_runs"} <= {
        row["selection_set"] for row in rows
    }
    assert _row(rows, "all_runs", "run_count")["value"] == "7"
    assert _row(rows, "user_valid_runs", "run_count")["value"] == "6"
    assert _row(rows, "excluded_runs", "run_count")["value"] == "1"


def test_selection_membership_drives_summary_members(mtda_archive: Path) -> None:
    specimen_rows = {row["run_id"]: row for row in _csv_member(mtda_archive, "method_outputs/specimen_results.csv")}
    membership = _csv_member(mtda_archive, "acceptance/selection_membership.csv")
    summary = _csv_member(mtda_archive, "method_outputs/dataset_summary_by_selection.csv")

    excluded_members = _included_run_ids(membership, "excluded_runs")
    assert excluded_members == ["run_002"]
    excluded_strength = _row(summary, "excluded_runs", "compressive_strength_MPa")
    assert float(excluded_strength["value"]) == pytest.approx(float(specimen_rows["run_002"]["compressive_strength_MPa"]))

    user_valid_members = _included_run_ids(membership, "user_valid_runs")
    expected = _mean(float(specimen_rows[run_id]["compressive_strength_MPa"]) for run_id in user_valid_members)
    user_valid_strength = _row(summary, "user_valid_runs", "compressive_strength_MPa")
    assert int(user_valid_strength["n"]) == len(user_valid_members)
    assert float(user_valid_strength["value"]) == pytest.approx(expected)

    auto_members = _included_run_ids(membership, "auto_recommended_runs")
    auto_strength = _row(summary, "auto_recommended_runs", "compressive_strength_MPa")
    assert int(auto_strength["n"]) == len(auto_members)
    if auto_members:
        expected_auto = _mean(float(specimen_rows[run_id]["compressive_strength_MPa"]) for run_id in auto_members)
        assert float(auto_strength["value"]) == pytest.approx(expected_auto)
    else:
        assert auto_strength["value"] == ""


def test_original_dataset_summary_identifies_all_runs(mtda_archive: Path) -> None:
    rows = _csv_member(mtda_archive, "method_outputs/dataset_summary.csv")
    assert rows
    assert {row["selection_set"] for row in rows} == {"all_runs"}


def _csv_member(path: Path, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _row(rows: list[dict[str, str]], selection_set: str, metric: str) -> dict[str, str]:
    return next(row for row in rows if row["selection_set"] == selection_set and row["metric"] == metric)


def _included_run_ids(membership: list[dict[str, str]], selection_set: str) -> list[str]:
    return [
        row["run_id"]
        for row in membership
        if row["selection_set"] == selection_set and row["included"] in {"True", "true", "1"}
    ]


def _mean(values: object) -> float:
    sequence = list(values)
    return sum(sequence) / len(sequence)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
