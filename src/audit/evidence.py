from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditEvidence:
    specimen_results: list[dict[str, Any]]
    curve_family: list[dict[str, Any]]
    operation_log: list[dict[str, Any]]
    warnings: list[dict[str, Any]]

