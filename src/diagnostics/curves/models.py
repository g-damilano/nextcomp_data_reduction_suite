from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CURVE_SHAPE_NORMAL = "CURVE_SHAPE_NORMAL"
CURVE_SHAPE_OUTLIER = "CURVE_SHAPE_OUTLIER"
INSUFFICIENT_CURVE_DATA = "INSUFFICIENT_CURVE_DATA"
INSUFFICIENT_COHORT_SIZE = "INSUFFICIENT_COHORT_SIZE"
CURVE_SHAPE_NOT_ASSESSED = "CURVE_SHAPE_NOT_ASSESSED"


@dataclass(frozen=True, slots=True)
class CurveSeries:
    run_id: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CurveCohortPolicy:
    group_by: tuple[str, ...] = ()
    default_grouping: str = "whole_comparable_dataset"
    minimum_evaluable_curves: int = 3


@dataclass(frozen=True, slots=True)
class CurveAlignmentPolicy:
    domain: str = "resolved_experiment_interval"
    resample_points: int = 250
    interpolation_mode: str = "linear"


@dataclass(frozen=True, slots=True)
class CurveReferencePolicy:
    curve: str = "mean"
    variability: str = "std"


@dataclass(frozen=True, slots=True)
class CurveThresholdPolicy:
    small_sample_method: str = "dixon_high_outlier_q_test"
    large_sample_method: str = "robust_mad_zscore"
    insufficient_method: str = "insufficient_cohort_size"
    robust_z_threshold: float = 3.5
    confidence: float = 0.95


@dataclass(frozen=True, slots=True)
class CurveDistanceResult:
    run_id: str
    cohort_id: str
    cohort_label: str
    evaluable: bool
    distance_rms: float | None
    distance_rank: int | None
    distance_note: str
    effective_sample_size: int
    metrics: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CurveThresholdResult:
    threshold_method: str
    Qexp: float | None = None
    Qcrit_95: float | None = None
    Qcrit_note: str = ""
    robust_z_threshold: float | None = None
    threshold_value: float | None = None
    decision_note: str = ""


@dataclass(frozen=True, slots=True)
class CurveDiagnosticArtifactSet:
    report: dict[str, Any]
    scores: tuple[dict[str, Any], ...]
    reference_rows: tuple[dict[str, Any], ...]
    residual_rows: tuple[dict[str, Any], ...]
    policy: dict[str, Any]
    flags: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class CurveDiagnosticResult:
    report: dict[str, Any]
    scores: tuple[dict[str, Any], ...]
    reference_rows: tuple[dict[str, Any], ...]
    residual_rows: tuple[dict[str, Any], ...]
    policy_resolved: dict[str, Any]
    flags: tuple[dict[str, Any], ...]

    def artifacts(self) -> CurveDiagnosticArtifactSet:
        return CurveDiagnosticArtifactSet(
            report=self.report,
            scores=self.scores,
            reference_rows=self.reference_rows,
            residual_rows=self.residual_rows,
            policy=self.policy_resolved,
            flags=self.flags,
        )

