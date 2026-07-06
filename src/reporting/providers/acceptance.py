from __future__ import annotations

from typing import Any

from reporting.core.report_context import ReportContext
from reporting.providers.base import ReportDataProvider


class AcceptanceSummaryProvider(ReportDataProvider):
    provider_id = "acceptance_summary"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> dict[str, Any]:
        summary = dict(context.result.acceptance_report.get("summary", {}))
        summary["final_selection_set"] = context.selection_set
        summary["selection_source"] = context.selection_source
        summary["final_selected_runs"] = len(context.selection_run_ids)
        decisions = context.result.human_decisions if isinstance(context.result.human_decisions, dict) else {}
        rows = decisions.get("decisions", [])
        summary["human_decision_count"] = len(rows) if isinstance(rows, list) else 0
        curve_family = context.result.curve_family_assessment if isinstance(context.result.curve_family_assessment, dict) else {}
        curve_summary = curve_family.get("summary") if isinstance(curve_family.get("summary"), dict) else {}
        summary["curve_family_assessed_runs"] = curve_summary.get("assessed_runs", 0)
        summary["curve_family_review"] = curve_summary.get("review", 0)
        summary["curve_family_propose_remove"] = curve_summary.get("propose_remove", 0)
        return summary


class DischargeSummaryProvider(ReportDataProvider):
    provider_id = "discharge_summary"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list(context.result.discharged_runs)


class CurveFamilySummaryProvider(ReportDataProvider):
    provider_id = "curve_family_summary"

    def provide(self, context: ReportContext, block: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        report = context.result.curve_family_assessment if isinstance(context.result.curve_family_assessment, dict) else {}
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        if not summary:
            return []
        return [{"metric": key, "value": value} for key, value in summary.items()]
