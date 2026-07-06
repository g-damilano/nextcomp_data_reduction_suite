from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from methods.core.method_result import MethodRunResult


@dataclass(frozen=True, slots=True)
class ReportContext:
    """Resolved data surface shared by report blocks and providers."""

    result: MethodRunResult
    recipe: dict[str, Any]
    selection_set: str
    selection_run_ids: set[str]
    curve_policy: dict[str, Any]
    selection_source: str = "machine_acceptance"
    tables: dict[str, Any] = field(default_factory=dict)
    values_by_key: dict[str, Any] = field(default_factory=dict)

    def table(self, name: str) -> Any:
        return self.tables.get(name, [])

    def value(self, key: str, default: Any = "") -> Any:
        return self.values_by_key.get(key, default)
