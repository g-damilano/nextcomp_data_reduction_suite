from __future__ import annotations


FIELD_LABELS: dict[str, str] = {
    "stress_MPa": "Stress / MPa",
    "stress": "Stress / MPa",
    "load_N": "Load / N",
    "bending_percent": "Bending / %",
    "mean_strain": "Mean compressive strain / %",
    "strain": "Strain / %",
    "strain_percent": "Strain / %",
    "gauge_strain": "Strain / %",
    "x": "Normalised strain / %",
    "distance_rms": "Curve difference score (distance_rms)",
    "distance_rank": "Distance rank",
    "standardized_residual": "Standardized residual z(x)",
    "diagnostic_classification": "Curve-shape classification",
    "threshold_method": "Threshold method",
    "Qexp": "Observed Dixon Q (Qexp)",
    "Qcrit_95": "Critical Q at 95% (Qcrit_95)",
    "robust_z": "Signed MAD z-score (z_mad)",
    "z_mad": "Signed MAD z-score (z_mad)",
    "mad_upper_z": "Upper-tail MAD score",
    "z_mad_upper": "Upper-tail MAD score",
    "threshold_value": "Upper-tail MAD cutoff (z_crit)",
}


def display_label(field: str, overrides: dict[str, str] | None = None) -> str:
    if overrides and field in overrides:
        return overrides[field]
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    return field.replace("_", " ").title()


def is_raw_internal_label(label: str) -> bool:
    text = str(label or "")
    return "_" in text and text not in FIELD_LABELS.values() and not text.startswith("Q")
