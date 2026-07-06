from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditViewContract:
    view_type: str
    renderer: str
    required_series: tuple[str, ...] = ()
    required_scalars: tuple[str, ...] = ()
    required_markers: tuple[str, ...] = ()
    default_caption: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_type": self.view_type,
            "renderer": self.renderer,
            "required_series": list(self.required_series),
            "required_scalars": list(self.required_scalars),
            "required_markers": list(self.required_markers),
            "default_caption": self.default_caption,
        }


AUDIT_VIEW_CONTRACTS: dict[str, AuditViewContract] = {
    "boundary_markers_overlay": AuditViewContract(
        view_type="boundary_markers_overlay",
        renderer="stress_strain_boundary_overlay",
        required_series=("load", "strain"),
        required_markers=("experiment_start", "experiment_end", "max_load"),
        default_caption="Resolved analysis interval with boundary and maximum-load markers.",
    ),
    "mean_absolute_strain_overlay": AuditViewContract(
        view_type="mean_absolute_strain_overlay",
        renderer="series_construction_overlay",
        required_series=("front_strain_abs", "rear_strain_abs", "mean_strain"),
        default_caption="Mean compressive strain constructed from opposite-face strain magnitudes.",
    ),
    "stress_curve_overlay": AuditViewContract(
        view_type="stress_curve_overlay",
        renderer="stress_strain_curve",
        required_series=("mean_strain", "stress_MPa"),
        required_scalars=("area_mm2",),
        default_caption="Stress curve derived from bounded load divided by specimen area.",
    ),
    "max_point_marker": AuditViewContract(
        view_type="max_point_marker",
        renderer="marker_overlay",
        required_series=("stress_MPa",),
        required_markers=("max_point",),
        default_caption="Maximum stress/strength marker in the bounded analysis interval.",
    ),
    "failure_strain_marker": AuditViewContract(
        view_type="failure_strain_marker",
        renderer="marker_overlay",
        required_series=("mean_strain",),
        required_markers=("failure_strain",),
        default_caption="Failure strain sampled at the maximum stress point.",
    ),
    "chord_slope_overlay": AuditViewContract(
        view_type="chord_slope_overlay",
        renderer="chord_line_overlay",
        required_series=("mean_strain", "stress_MPa"),
        required_markers=("chord_start", "chord_end"),
        default_caption="Chord modulus anchors and slope line.",
    ),
    "bending_window_threshold_overlay": AuditViewContract(
        view_type="bending_window_threshold_overlay",
        renderer="bending_threshold_overlay",
        required_series=("load", "bending_percent"),
        required_markers=("window_start", "window_end", "threshold"),
        default_caption="Bending percent evidence in the 10-90% maximum-load assessment window.",
    ),
    "bending_segments_overlay": AuditViewContract(
        view_type="bending_segments_overlay",
        renderer="bending_segments_overlay",
        required_series=("bending_percent",),
        required_markers=("exceedance_segments",),
        default_caption="Bending threshold exceedance segments.",
    ),
    "validation_summary_table": AuditViewContract(
        view_type="validation_summary_table",
        renderer="compact_table",
        default_caption="Validation summary with detailed checks behind it.",
    ),
    "selection_decision_card": AuditViewContract(
        view_type="selection_decision_card",
        renderer="decision_card",
        default_caption="Machine and human final-selection consequence.",
    ),
    "aggregate_curve_family_plot": AuditViewContract(
        view_type="aggregate_curve_family_plot",
        renderer="aggregate_curve_family_plot",
        required_series=("aligned_curves",),
        default_caption="Boundary-aligned curve-family evidence.",
    ),
    "curve_family_diagnostic_view": AuditViewContract(
        view_type="curve_family_diagnostic_view",
        renderer="curve_shape_diagnostic_packet",
        required_series=("curve_diagnostic_reference_curve", "curve_diagnostic_residuals"),
        required_scalars=("distance_rms", "distance_rank", "Qexp", "Qcrit_95"),
        default_caption="Curve-shape diagnostic distance ranking and residual trace.",
    ),
    "aggregate_statistics_table": AuditViewContract(
        view_type="aggregate_statistics_table",
        renderer="compact_table",
        default_caption="Formal aggregate statistics used by the Test Report.",
    ),
}


def get_audit_view_contract(view_type: str) -> AuditViewContract | None:
    return AUDIT_VIEW_CONTRACTS.get(view_type)


def audit_view_contract_records() -> dict[str, dict[str, Any]]:
    return {key: value.to_dict() for key, value in sorted(AUDIT_VIEW_CONTRACTS.items())}
