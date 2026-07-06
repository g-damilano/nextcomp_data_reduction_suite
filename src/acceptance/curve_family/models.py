from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ACCEPT = "CURVE_FAMILY_ACCEPT"
REVIEW = "CURVE_FAMILY_REVIEW"
PROPOSE_REMOVE = "CURVE_FAMILY_PROPOSE_REMOVE"


@dataclass(frozen=True, slots=True)
class AlignedCurve:
    curve_family_id: str
    run_id: str
    x_common: tuple[float, ...]
    y_aligned: tuple[float | None, ...]
    alignment_mode: str
    included_in_reference: bool = True


@dataclass(frozen=True, slots=True)
class ReferenceCurve:
    curve_family_id: str
    reference_id: str
    x_common: tuple[float, ...]
    y_reference: tuple[float | None, ...]
    reference_type: str
    n_observations: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CurveFamilyScore:
    selection_context: str
    curve_family_id: str
    run_id: str
    alignment_mode: str
    reference_id: str
    normalized_rmse: float | None
    normalized_mae: float | None
    integrated_absolute_residual: float | None
    max_absolute_residual: float | None
    derivative_rmse: float | None
    curve_correlation: float | None
    leave_one_out_mean_shift: float | None
    classification: str
    primary_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_context": self.selection_context,
            "curve_family_id": self.curve_family_id,
            "run_id": self.run_id,
            "alignment_mode": self.alignment_mode,
            "reference_id": self.reference_id,
            "normalized_rmse": self.normalized_rmse,
            "normalized_mae": self.normalized_mae,
            "integrated_absolute_residual": self.integrated_absolute_residual,
            "max_absolute_residual": self.max_absolute_residual,
            "derivative_rmse": self.derivative_rmse,
            "curve_correlation": self.curve_correlation,
            "leave_one_out_mean_shift": self.leave_one_out_mean_shift,
            "classification": self.classification,
            "primary_reason": self.primary_reason,
        }


@dataclass(frozen=True, slots=True)
class CurveFamilyAssessment:
    report: dict[str, Any]
    scores: list[dict[str, Any]]
    flags: list[dict[str, Any]]
    reference_rows: list[dict[str, Any]]
    aligned_rows: list[dict[str, Any]]
    residual_rows: list[dict[str, Any]]
    policy_resolved: dict[str, Any]

    @classmethod
    def empty(cls, *, reason: str = "No curve-family acceptance recipe was configured.") -> "CurveFamilyAssessment":
        report = {
            "schema_id": "method.curve_family_report.v0_1",
            "summary": {
                "curve_family_count": 0,
                "assessed_runs": 0,
                "accepted": 0,
                "review": 0,
                "propose_remove": 0,
            },
            "curve_families": [],
            "warnings": [reason],
            "acceptance_flag_ids": [],
        }
        return cls(
            report=report,
            scores=[],
            flags=[],
            reference_rows=[],
            aligned_rows=[],
            residual_rows=[],
            policy_resolved={"schema_id": "method.curve_family_policy_resolved.v0_1", "curve_families": []},
        )
