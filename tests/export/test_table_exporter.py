from __future__ import annotations

import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.artifact_collector import MTDAArtifactCollector
from export.table_exporter import TableExporter


def test_table_exporter_collects_key_csv_tables(tmp_path: Path) -> None:
    archive_path = tmp_path / "input.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("dataset/03_aggregate/run_decision_registry.csv", "run_id,included\nrun_001,True\n")
        archive.writestr("dataset/03_aggregate/statistics.csv", "metric,n\nstrength,1\n")
        archive.writestr("unrelated/table.csv", "x\n1\n")

    files = TableExporter().export(MTDAArtifactCollector(archive_path), profile="minimal")

    assert files["tables/final_report_runs.csv"].startswith(b"run_id")
    assert files["tables/aggregate_statistics.csv"].startswith(b"metric")
    assert "tables/table.csv" not in files
