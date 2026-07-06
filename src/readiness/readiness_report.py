from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from readiness.readiness_models import ReadinessStatus, ResolvedInput


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    status: ReadinessStatus
    method_id: str
    schema_id: str | None
    mapping_id: str | None
    requirements: tuple[ResolvedInput, ...]
    warnings: tuple[str, ...] = ()

    @property
    def blocks_execution(self) -> bool:
        return self.status in {
            ReadinessStatus.NOT_READY,
            ReadinessStatus.MAPPING_REQUIRED,
            ReadinessStatus.SCHEMA_EXTENSION_REQUIRED,
        }

    @property
    def summary(self) -> dict[str, Any]:
        critical = [item for item in self.requirements if item.severity == "execution_critical"]
        warnings = [item for item in self.requirements if item.status != "pass" and item.severity != "execution_critical"]
        missing = [item for item in self.requirements if item.status != "pass"]
        mapping_missing = [item for item in self.requirements if item.status == "mapping_missing"]
        critical_missing = [item for item in critical if item.status != "pass"]
        critical_mapping_missing = [item for item in critical if item.status == "mapping_missing"]
        report_missing = [item for item in self.requirements if item.status != "pass" and item.severity != "execution_critical"]
        return {
            "execution_critical_total": len(critical),
            "execution_critical_passed": sum(1 for item in critical if item.status == "pass"),
            "execution_critical_missing": len(critical_missing),
            "execution_critical_mapping_missing": len(critical_mapping_missing),
            "report_missing_total": len(report_missing),
            "warnings_total": len(warnings) + len(self.warnings),
            "missing_total": len(missing),
            "mapping_missing_total": len(mapping_missing),
            "resolved_total": sum(1 for item in self.requirements if item.status == "pass"),
            "requirement_total": len(self.requirements),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "method.readiness_report.v0_1",
            "status": self.status.value,
            "method_id": self.method_id,
            "source_schema_id": self.schema_id,
            "mapping_id": self.mapping_id,
            "summary": self.summary,
            "requirements": [item.to_dict() for item in self.requirements],
            "blocks_execution": self.blocks_execution,
            "warnings": list(self.warnings),
        }

    def summary_rows(self) -> list[dict[str, Any]]:
        row = {
            "status": self.status.value,
            "method_id": self.method_id,
            "schema_id": self.schema_id,
            "mapping_id": self.mapping_id,
            "blocks_execution": self.blocks_execution,
        }
        row.update(self.summary)
        return [row]

    def resolved_rows(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.requirements if item.status == "pass"]

    def missing_rows(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.requirements if item.status != "pass"]

    @classmethod
    def empty(cls, *, method_id: str, schema_id: str | None = None, mapping_id: str | None = None) -> "ReadinessReport":
        return cls(
            status=ReadinessStatus.READY,
            method_id=method_id,
            schema_id=schema_id,
            mapping_id=mapping_id,
            requirements=(),
        )
