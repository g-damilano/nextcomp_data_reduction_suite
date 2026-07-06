from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class InspectionReport:
    inspection_id: str
    inspection_type: str
    curve_id: str
    run_id: str | None
    x_channel: str | None
    y_channel: str | None
    metrics: dict[str, Any]
    notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "inspection_id": self.inspection_id,
            "inspection_type": self.inspection_type,
            "curve_id": self.curve_id,
            "run_id": self.run_id,
            "x_channel": self.x_channel,
            "y_channel": self.y_channel,
            "warnings": list(self.warnings),
            "notes": list(self.notes),
        }
        payload.update(self.metrics)
        return payload
