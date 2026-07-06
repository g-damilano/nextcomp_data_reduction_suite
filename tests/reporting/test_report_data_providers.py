from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.report_context import ReportContext


def test_provider_registry_returns_report_values_and_tables() -> None:
    context = ReportContext(
        result=None,  # type: ignore[arg-type]
        recipe={},
        selection_set="selected",
        selection_run_ids=set(),
        curve_policy={},
        values_by_key={"standard_reference": "ISO 14126"},
        tables={
            "missing_report_fields": [{"field": "operator"}],
            "aggregate_statistics": [{"metric": "compressive_strength_MPa", "mean": 240.0}],
        },
    )
    providers = DataProviderRegistry()

    assert "report_values" in providers.provider_ids()
    assert "aggregate_statistics" in providers.provider_ids()
    assert providers.provide("report_values", context)["standard_reference"] == "ISO 14126"
    assert providers.provide("missing_report_fields", context)[0]["field"] == "operator"
    assert providers.provide("aggregate_statistics", context)[0]["mean"] == 240.0
