from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportArtifactBundle:
    """Archive-ready report artifacts plus the rows used to build them."""

    files: dict[str, bytes]
    summary: dict[str, Any] = field(default_factory=dict)
    individual_results: list[dict[str, Any]] = field(default_factory=list)
    aggregate_statistics: list[dict[str, Any]] = field(default_factory=list)
    characteristic_points: list[dict[str, Any]] = field(default_factory=list)
    feature_lines: list[dict[str, Any]] = field(default_factory=list)
    aligned_curves: list[dict[str, Any]] = field(default_factory=list)
    missing_report_fields: list[dict[str, Any]] = field(default_factory=list)

