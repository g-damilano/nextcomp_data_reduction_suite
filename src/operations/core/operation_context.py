from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any


class OperationCancelled(RuntimeError):
    """Raised by operations when a cancellation request is observed."""


@dataclass(slots=True)
class OperationRun:
    source_run: Any
    scalars: dict[str, Any] = field(default_factory=dict)
    series: dict[str, list[float | None]] = field(default_factory=dict)
    units: dict[str, str | None] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OperationContext:
    source: Any
    mapping: dict[str, Any]
    runs: dict[str, OperationRun]
    inspector: Any
    phase: str
    inspections: list[dict[str, Any]] = field(default_factory=list)
    cancel_requested: Callable[[], bool] | None = None

    def record_inspection(self, report: Any) -> str:
        payload = report.to_dict()
        self.inspections.append(payload)
        return str(payload.get("inspection_id", ""))

    def check_cancelled(self) -> None:
        if self.cancel_requested is not None and self.cancel_requested():
            raise OperationCancelled("Method run cancellation requested.")
