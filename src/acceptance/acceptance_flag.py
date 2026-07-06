from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AcceptanceFlag:
    flag_id: str
    run_id: str
    source: str
    severity: str
    category: str
    message: str
    evidence_refs: tuple[str, ...] = ()
    operation_ids: tuple[str, ...] = ()
    validation_check_ids: tuple[str, ...] = ()
    inspection_ids: tuple[str, ...] = ()
    selection_effect: str = "informational"
    rule_id: str | None = None
    value: Any = None
    threshold: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "flag_id": self.flag_id,
            "run_id": self.run_id,
            "source": self.source,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "evidence_refs": list(self.evidence_refs),
            "operation_ids": list(self.operation_ids),
            "validation_check_ids": list(self.validation_check_ids),
            "inspection_ids": list(self.inspection_ids),
            "selection_effect": self.selection_effect,
            "rule_id": self.rule_id,
            "value": self.value,
            "threshold": self.threshold,
        }


def severity_rank(severity: str | None) -> int:
    return {
        "info": 0,
        "warn": 1,
        "warning": 1,
        "review": 2,
        "exclude": 3,
    }.get(str(severity or "").lower(), 0)


def state_from_flags(flags: list[AcceptanceFlag]) -> str:
    if not flags:
        return "accepted"
    rank = max(severity_rank(flag.severity) for flag in flags)
    if rank >= 3:
        return "excluded"
    if rank == 2:
        return "review_required"
    if rank == 1:
        return "accepted_with_warning"
    return "accepted"


def strongest_flag(flags: list[AcceptanceFlag]) -> AcceptanceFlag | None:
    if not flags:
        return None
    return max(flags, key=lambda flag: severity_rank(flag.severity))
