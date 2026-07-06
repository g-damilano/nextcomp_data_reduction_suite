from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


AuditBlockScope = Literal["run", "aggregate", "dataset"]


@dataclass(frozen=True, slots=True)
class AuditBlock:
    block_id: str
    block_type: str
    title: str
    scope: AuditBlockScope
    purpose: str
    run_id: str | None = None
    status: str = "recorded"
    evidence_refs: dict[str, Any] = field(default_factory=dict)
    operation_refs: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    markers: dict[str, Any] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "title": self.title,
            "scope": self.scope,
            "run_id": self.run_id,
            "purpose": self.purpose,
            "status": self.status,
            "evidence_refs": self.evidence_refs,
            "operation_refs": self.operation_refs,
            "summary": self.summary,
            "tables": self.tables,
            "markers": self.markers,
            "links": self.links,
        }


@dataclass(frozen=True, slots=True)
class AuditRunPacket:
    run_id: str
    blocks: list[AuditBlock]

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": f"run_packet:{self.run_id}",
            "run_id": self.run_id,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True, slots=True)
class AuditAggregatePacket:
    blocks: list[AuditBlock]

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": "aggregate_packet",
            "blocks": [block.to_dict() for block in self.blocks],
        }
