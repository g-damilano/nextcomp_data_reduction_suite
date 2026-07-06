from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mtda_finalization.amendment_request import AmendmentRequest


@dataclass(frozen=True, slots=True)
class AmendmentDecision:
    accepted: bool
    amendment_classes: tuple[str, ...]
    rejected_reasons: tuple[str, ...] = ()
    new_run_required: bool = False
    disallowed_changes: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "amendment_classes": list(self.amendment_classes),
            "rejected_reasons": list(self.rejected_reasons),
            "new_run_required": self.new_run_required,
            "disallowed_changes": self.disallowed_changes or {},
        }


class AmendmentPolicy:
    """Classify archive amendments and protect method-calculation boundaries."""

    def classify(self, request: AmendmentRequest) -> AmendmentDecision:
        disallowed = request.disallowed_changes()
        if disallowed:
            return AmendmentDecision(
                accepted=False,
                amendment_classes=request.amendment_classes(),
                rejected_reasons=(
                    "Method-impacting changes require a new method run and cannot be applied in-place to an MTDA.",
                ),
                new_run_required=True,
                disallowed_changes=disallowed,
            )
        classes = request.amendment_classes()
        return AmendmentDecision(
            accepted=True,
            amendment_classes=classes or ("finalization_note",),
            rejected_reasons=(),
            new_run_required=False,
            disallowed_changes={},
        )
