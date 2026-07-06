from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SelectionSet:
    selection_id: str
    label: str
    description: str
    run_ids: tuple[str, ...]
    excluded_run_ids: tuple[str, ...]
    policy_id: str
    created_by: str = "acceptance_engine"

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "label": self.label,
            "description": self.description,
            "run_ids": list(self.run_ids),
            "excluded_run_ids": list(self.excluded_run_ids),
            "policy_id": self.policy_id,
            "created_by": self.created_by,
        }
