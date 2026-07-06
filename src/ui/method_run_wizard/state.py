from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ui.method_run_wizard._log import LogEntry


RUN_ENABLED_READINESS_STATUSES = {"READY", "READY_WITH_WARNINGS"}


class WizardScenario(str, Enum):
    SETUP = "setup"
    RUNNING = "running"
    REVIEW = "review"
    FINALIZE = "finalize"


@dataclass(slots=True)
class MethodRunWizardState:
    input_package_path: Path | None = None
    method_path: Path | None = None
    mapping_path: Path | None = None
    output_path: Path | None = None
    package_summary: dict[str, Any] | None = None
    method_summary: dict[str, Any] | None = None
    mapping_summary: dict[str, Any] | None = None
    readiness_report: dict[str, Any] | None = None
    service_result: Any | None = None
    execution_status: str = "not_started"
    current_phase: str | None = None
    validation_summary: dict[str, Any] | None = None
    acceptance_summary: dict[str, Any] | None = None
    last_error: dict[str, Any] | None = None
    current_page: str = "select_package"
    messages: list[str] = field(default_factory=list)
    report_overrides: list[dict[str, Any]] = field(default_factory=list)
    scenario: WizardScenario = WizardScenario.SETUP
    mapping_decision_made: bool = False
    metadata_decision_made: bool = False
    activity_log: list[LogEntry] = field(default_factory=list)
    log_open: bool = False
    running_phase_label: str = ""
    running_progress_pct: int = 0
    per_run_status: dict[str, str] = field(default_factory=dict)
    acceptance_keep: dict[str, bool] = field(default_factory=dict)
    acceptance_override_reason: dict[str, str] = field(default_factory=dict)
    acceptance_override_defects: dict[str, list[str]] = field(default_factory=dict)
    expanded_run: str | None = None
    finalize_reviewer: str = ""
    finalize_note: str = ""
    finalized: bool = False
    finalize_error: str | None = None

    @property
    def readiness_status(self) -> str | None:
        if not self.readiness_report:
            return None
        return str(self.readiness_report.get("status") or "")

    @property
    def run_enabled(self) -> bool:
        return self.readiness_status in RUN_ENABLED_READINESS_STATUSES
