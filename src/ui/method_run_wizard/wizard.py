from __future__ import annotations

from dataclasses import dataclass

from methods.core.method_run_service import MethodRunService
from ui.method_run_wizard.state import MethodRunWizardState


@dataclass(slots=True)
class MethodRunWizard:
    """Compatibility state holder kept for non-Qt imports during the UI migration."""

    service: MethodRunService
    state: MethodRunWizardState

    @classmethod
    def create(cls, service: MethodRunService | None = None) -> "MethodRunWizard":
        return cls(service=service or MethodRunService(), state=MethodRunWizardState())
