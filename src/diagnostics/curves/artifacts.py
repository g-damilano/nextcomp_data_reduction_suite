from __future__ import annotations

from typing import Any


ARTIFACT_PATHS = {
    "report": "acceptance/curve_family/curve_diagnostic_report.json",
    "scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
    "reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
    "residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
    "policy": "acceptance/curve_family/curve_diagnostic_policy.json",
    "flags": "acceptance/curve_family/curve_diagnostic_flags.csv",
}


def artifact_manifest() -> dict[str, Any]:
    return {
        "schema_id": "diagnostics.curve_family_diagnostic_artifacts.v0_1",
        "operation_type": "curve_family_diagnostic",
        "artifacts": dict(ARTIFACT_PATHS),
    }

