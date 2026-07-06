from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "docs" / "development_control"


def test_stage_ledger_records_stage10_and_stage10_5() -> None:
    ledger = yaml.safe_load((CONTROL / "STAGE_LEDGER.yaml").read_text(encoding="utf-8"))
    stages = {stage["id"]: stage for stage in ledger["stages"]}

    assert ledger["stage_ledger_schema"] == "development.stage_ledger.v0_1"
    assert stages["stage_10_operator_reporting_maturation"]["status"] == "implemented_architecturally_partial"
    assert stages["stage_10_5_generic_reporting_engine"]["status"] == "verified"
    assert "src/reporting/core/" in stages["stage_10_5_generic_reporting_engine"]["evidence"]["code_paths"]


def test_development_control_records_exist() -> None:
    required = [
        "BACKLOG.md",
        "STAGE_LEDGER.yaml",
        "OPEN_RISKS.md",
        "COMPLETION_CRITERIA.md",
        "stage_records/STAGE_10_OPERATOR_REPORTING_MATURATION.md",
        "stage_records/STAGE_10_5_GENERIC_REPORTING_ENGINE.md",
    ]

    for relative in required:
        assert (CONTROL / relative).exists(), relative
