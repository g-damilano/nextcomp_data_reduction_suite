from __future__ import annotations


FIELD_UNITS: dict[str, str] = {
    "stress": "MPa",
    "stress_MPa": "MPa",
    "load_N": "N",
    "bending_percent": "%",
    "strain": "%",
    "strain_percent": "%",
    "gauge_strain": "%",
    "x": "%",
    "standardized_residual": "",
    "distance_rms": "",
}


def unit_for(field: str, overrides: dict[str, str] | None = None) -> str:
    if overrides and field in overrides:
        return overrides[field]
    return FIELD_UNITS.get(field, "")


def with_unit(label: str, unit: str) -> str:
    if not unit or f"/ {unit}" in label or label.endswith(f" {unit}") or unit in label:
        return label
    return f"{label} / {unit}"
