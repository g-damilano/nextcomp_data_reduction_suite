from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from validation.reference_values import ReferenceValueSet


@dataclass(frozen=True, slots=True)
class ValidationResult:
    check_id: str
    run_id: str
    field: str
    point_index: int | None
    computed_value: float | None
    reference_value: float | None
    unit: str | None
    difference_abs: float | None
    difference_rel: float | None
    tolerance_abs: float | None
    tolerance_rel: float | None
    status: str
    severity: str
    message: str
    recipe_step_id: str | None = None
    operation_id: str | None = None
    reference_source: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "run_id": self.run_id,
            "recipe_step_id": self.recipe_step_id,
            "operation_id": self.operation_id,
            "field": self.field,
            "point_index": self.point_index,
            "computed_value": self.computed_value,
            "reference_value": self.reference_value,
            "unit": self.unit,
            "difference_abs": self.difference_abs,
            "difference_rel": self.difference_rel,
            "tolerance_abs": self.tolerance_abs,
            "tolerance_rel": self.tolerance_rel,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "reference_source": self.reference_source,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    method_id: str
    source_mtdp: str
    mapping_profile: str | None
    reference_values: ReferenceValueSet
    checks: tuple[ValidationResult, ...]

    @property
    def summary(self) -> dict[str, Any]:
        counts = {
            "total_checks": len(self.checks),
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "missing_reference": 0,
            "not_applicable": 0,
        }
        for check in self.checks:
            if check.status == "pass":
                counts["passed"] += 1
            elif check.status == "warn":
                counts["warnings"] += 1
            elif check.status == "fail":
                counts["failed"] += 1
            elif check.status == "missing_reference":
                counts["missing_reference"] += 1
            elif check.status == "not_applicable":
                counts["not_applicable"] += 1
        counts["status"] = "fail" if counts["failed"] else "warn" if counts["warnings"] else "pass"
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.validation_report.v0_1",
            "method_id": self.method_id,
            "source_mtdp": self.source_mtdp,
            "mapping_profile": self.mapping_profile,
            "reference_sources": _reference_sources(self.reference_values),
            "summary": self.summary,
            "checks": [check.to_dict() for check in self.checks],
        }

    def summary_rows(self) -> list[dict[str, Any]]:
        row = {
            "method_id": self.method_id,
            "source_mtdp": self.source_mtdp,
            "mapping_profile": self.mapping_profile,
            "reference_sources": "; ".join(_reference_sources(self.reference_values)),
        }
        row.update(self.summary)
        return [row]

    def deviation_rows(self) -> list[dict[str, Any]]:
        return [
            check.to_dict()
            for check in self.checks
            if check.status != "pass" or (check.difference_abs not in (None, 0))
        ]

    def reference_rows(self) -> list[dict[str, Any]]:
        return self.reference_values.to_rows()


def _reference_sources(reference_values: ReferenceValueSet) -> list[str]:
    sources = {str(value.source) for value in reference_values.values if value.source}
    if reference_values.source_path is not None:
        sources.add(str(reference_values.source_path))
    return sorted(sources)
