from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportBlockDocument:
    id: str
    type: str
    title: str
    provider: str
    data: Any
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "provider": self.provider,
            "data": self.data,
            "config": self.config,
        }


@dataclass(frozen=True, slots=True)
class ReportSectionDocument:
    id: str
    title: str
    blocks: list[ReportBlockDocument]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True, slots=True)
class ReportDocument:
    report_id: str
    title: str
    metadata: dict[str, Any]
    sections: list[ReportSectionDocument]
    schema_id: str = "report.document.v0_1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "report_id": self.report_id,
            "title": self.title,
            "metadata": self.metadata,
            "sections": [section.to_dict() for section in self.sections],
        }
