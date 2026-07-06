from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


DecisionType = Literal["keep", "remove", "restore", "confirm", "clear_override"]


@dataclass(frozen=True, slots=True)
class HumanAcceptanceDecision:
    run_id: str
    decision_type: DecisionType
    reason: str = ""
    reviewer: str = ""
    timestamp: str = ""
    source_surface: str = "method_run_wizard.acceptance_selection"
    ui_context: str = ""
    decision_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision_type not in {"keep", "remove", "restore", "confirm", "clear_override"}:
            raise ValueError(f"Unsupported human acceptance decision: {self.decision_type}")
        reason_required = self.decision_type in {"keep", "remove", "restore"}
        if reason_required and not self.reason.strip():
            raise ValueError(f"Reason is required for human decision '{self.decision_type}'.")
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
        if not self.decision_id:
            safe_time = self.timestamp.replace(":", "").replace("-", "").replace(".", "")
            object.__setattr__(self, "decision_id", f"{self.run_id}:{self.decision_type}:{safe_time}")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HumanAcceptanceDecision":
        return cls(
            run_id=str(payload.get("run_id") or ""),
            decision_type=str(payload.get("decision_type") or payload.get("decision") or "confirm"),  # type: ignore[arg-type]
            reason=str(payload.get("reason") or ""),
            reviewer=str(payload.get("reviewer") or ""),
            timestamp=str(payload.get("timestamp") or ""),
            source_surface=str(payload.get("source_surface") or "method_run_wizard.acceptance_selection"),
            ui_context=str(payload.get("ui_context") or ""),
            decision_id=str(payload.get("decision_id") or ""),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "decision_type": self.decision_type,
            "reason": self.reason,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "source_surface": self.source_surface,
            "ui_context": self.ui_context,
            "metadata": self.metadata,
        }


def decisions_from_payload(payload: Any) -> tuple[HumanAcceptanceDecision, ...]:
    if payload is None:
        return ()
    if isinstance(payload, dict) and isinstance(payload.get("decisions"), list):
        payload = payload["decisions"]
    if not isinstance(payload, list):
        raise ValueError("Human acceptance decisions must be a list or an object with a decisions list.")
    return tuple(
        HumanAcceptanceDecision.from_dict(item)
        for item in payload
        if isinstance(item, dict)
    )

