from __future__ import annotations


PROFILES = {"minimal", "figures", "full_html"}


def validate_profile(profile: str) -> str:
    if profile not in PROFILES:
        raise ValueError(f"Unsupported export profile '{profile}'. Expected one of: {', '.join(sorted(PROFILES))}.")
    return profile


def profile_includes_figures(profile: str) -> bool:
    return profile in {"figures", "full_html"}


def profile_includes_full_html(profile: str) -> bool:
    return profile == "full_html"


def export_warnings(profile: str) -> list[str]:
    warnings = ["PDF/DOCX export is deferred; HTML, CSV, and Vega artifacts were exported."]
    if profile == "minimal":
        warnings.append("Figure export skipped by minimal profile.")
    return warnings
