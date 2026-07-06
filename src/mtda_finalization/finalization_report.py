from __future__ import annotations

from typing import Any


def build_finalization_report(
    *,
    archive_state: dict[str, Any],
    amendment_record: dict[str, Any],
    recompute_manifest: dict[str, Any],
    report_completion_status: dict[str, Any],
    final_selection_source: str,
) -> dict[str, Any]:
    return {
        "schema_id": "mtda.finalization_report.v0_1",
        "status": "finalized",
        "archive_state": archive_state,
        "amendment": amendment_record,
        "recompute_manifest": recompute_manifest,
        "report_completion_status": report_completion_status,
        "final_selection_source": final_selection_source,
        "mtdp_mutated": False,
    }
