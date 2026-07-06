from __future__ import annotations

import csv
import html
import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from archives.core.layouts import MTDAAlignedLayout
from mapping import normalize_mapping_profile, write_mapping_profile
from methods.core.method_run_service import MethodRunService, load_mapping
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._log import LogEntry, now_entry
from ui.method_run_wizard._tokens import Color
from ui.method_run_wizard import service_adapter
from ui.method_run_wizard.components.task_card import TaskCard
from ui.method_run_wizard.mapping_dialog import MethodMappingDialog
from ui.method_run_wizard.method_registry import MethodRegistry, MethodRegistryEntry
from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
from ui.method_run_wizard.view_models.mapping_preview import mapping_preview_view_model
from ui.method_run_wizard.window import MethodRunWindow
from ui.method_run_wizard.spotlights.review_spotlight import RunRowModel
from ui.method_run_wizard.view_models.diagnostic_cockpit import diagnostic_cockpit_from_payload


class MethodRunController(QtCore.QObject):
    """Controller placeholder for the feature-flagged Method Run window."""

    def __init__(
        self,
        window: MethodRunWindow,
        state: MethodRunWizardState | None = None,
        *,
        service: MethodRunService | None = None,
        registry: MethodRegistry | None = None,
    ) -> None:
        super().__init__(window)
        self.window = window
        self.state = state or MethodRunWizardState(input_package_path=getattr(window, "package_path", None))
        self.service = service or MethodRunService()
        self.registry = registry or MethodRegistry.load()
        if self.state.input_package_path is not None:
            self.window.set_package_path(self.state.input_package_path)
            if self.state.package_summary is None and Path(self.state.input_package_path).exists():
                self._load_package_context()
        if self.state.method_path is not None:
            self._ensure_method_selection(reset_readiness=False)
        self._ensure_output_path()
        self._worker: Any | None = None
        self._running_started_at = ""
        self._review_models: list[RunRowModel] = []
        self._connect_setup_spotlight()
        self._connect_setup_action_bar()
        self._connect_context_controls()
        self._connect_running_spotlight()
        self._connect_running_action_bar()
        self._connect_review_spotlight()
        self._connect_review_action_bar()
        self._connect_finalize_spotlight()
        self._connect_finalize_action_bar()
        self._connect_activity_log_controls()
        self._connect_menu_actions()
        self._connect_process_spine()
        self._connect_shortcuts()
        self._sync_activity_log()
        self._sync_decor()
        self._update_setup_action_bar()

    def _connect_setup_spotlight(self) -> None:
        setup = self.window.setup_spotlight
        setup.change_package.connect(self._change_package)
        setup.change_method.connect(self._change_method)
        setup.method_selected.connect(self._method_selected)
        setup.save_bindings.connect(self._resolve_mapping_from_save)
        setup.skip_bindings.connect(self._resolve_mapping_from_skip)
        setup.edit_mapping_profile.connect(self._edit_mapping_profile)
        setup.open_metadata_dialog.connect(self._resolve_metadata_from_dialog)
        setup.accept_metadata_warnings.connect(self._resolve_metadata_from_warning)

    def _connect_setup_action_bar(self) -> None:
        self.window.action_bars[WizardScenario.SETUP].primary_clicked.connect(self._setup_primary_clicked)

    def _connect_running_action_bar(self) -> None:
        self.window.action_bars[WizardScenario.RUNNING].primary_clicked.connect(self._cancel_run)

    def _connect_running_spotlight(self) -> None:
        self.window.running_spotlight.view_log_clicked.connect(lambda: self._set_log_open(True))
        self.window.running_spotlight.back_to_setup_clicked.connect(self._back_to_setup_from_error)

    def _connect_review_spotlight(self) -> None:
        review = self.window.review_spotlight
        review.keep_clicked.connect(self._review_keep)
        review.remove_clicked.connect(self._review_remove)
        review.expanded.connect(self._review_expanded)
        review.reason_changed.connect(self._review_reason_changed)

    def _connect_review_action_bar(self) -> None:
        self.window.action_bars[WizardScenario.REVIEW].primary_clicked.connect(self._confirm_review)

    def _connect_finalize_spotlight(self) -> None:
        finalize = self.window.finalize_spotlight
        finalize.open_mtda.connect(self._open_mtda_output)
        finalize.open_test_report.connect(self._open_test_report)
        finalize.open_audit_report.connect(self._open_audit_report)
        finalize.open_workbench.connect(self._open_workbench)
        finalize.open_output_folder.connect(self._open_output_folder)
        finalize.copy_mtda_path.connect(self._copy_mtda_path)
        finalize.open_report_completion.connect(self._open_report_completion)
        finalize.finalize_clicked.connect(self._finalize_mtda)
        finalize.reviewer_changed.connect(self._finalize_reviewer_changed)
        finalize.note_changed.connect(self._finalize_note_changed)

    def _connect_finalize_action_bar(self) -> None:
        self.window.action_bars[WizardScenario.FINALIZE].primary_clicked.connect(self.window.close)

    def _connect_context_controls(self) -> None:
        detail = self.window.decor_bottom.detail
        detail.change_package_button.clicked.connect(self._change_package)
        detail.change_method_button.clicked.connect(self._change_method)
        detail.edit_mapping_button.clicked.connect(self._change_mapping)

    def _connect_activity_log_controls(self) -> None:
        self.window.status_log_button.clicked.connect(self.toggle_log)
        self.window.decor_bottom.bar.activity_log_clicked.connect(self.toggle_log)
        self.window.log_drawer.close_requested.connect(lambda: self._set_log_open(False))

    def _connect_menu_actions(self) -> None:
        self.window.choose_package_action.triggered.connect(lambda _checked=False: self._change_package())
        self.window.choose_method_action.triggered.connect(lambda _checked=False: self._change_method())
        self.window.refresh_mapping_action.triggered.connect(lambda _checked=False: self._change_mapping())
        self.window.check_readiness_action.triggered.connect(lambda _checked=False: self._check_readiness_from_setup())
        self.window.run_method_action.triggered.connect(lambda _checked=False: self._setup_primary_clicked())
        self.window.cancel_run_action.triggered.connect(lambda _checked=False: self._cancel_run())
        self.window.confirm_review_action.triggered.connect(lambda _checked=False: self._confirm_review())
        self.window.finalize_mtda_action.triggered.connect(lambda _checked=False: self._finalize_mtda())
        self.window.open_test_report_action.triggered.connect(lambda _checked=False: self._open_test_report())
        self.window.open_audit_report_action.triggered.connect(lambda _checked=False: self._open_audit_report())
        self.window.open_workbench_action.triggered.connect(lambda _checked=False: self._open_workbench())
        self.window.open_output_folder_action.triggered.connect(lambda _checked=False: self._open_output_folder())
        self.window.copy_mtda_path_action.triggered.connect(lambda _checked=False: self._copy_mtda_path())
        self.window.open_report_completion_action.triggered.connect(lambda _checked=False: self._open_report_completion())
        self.window.activity_log_action.triggered.connect(lambda _checked=False: self.toggle_log())
        self.window.context_details_action.triggered.connect(self._set_context_details_open)
        self.window.decor_bottom.bar.context_line.toggled.connect(self._context_details_toggled)

    def _connect_process_spine(self) -> None:
        self.window.decor_top.pipeline.step_clicked.connect(self._process_step_clicked)

    def _process_step_clicked(self, step_id: str) -> None:
        if step_id == "package":
            self._change_package()
        elif step_id == "method":
            self._change_method()
        elif step_id == "mapping":
            self._change_mapping()
        elif step_id == "ready":
            self._check_readiness_from_setup()
        elif step_id == "exec" and self.state.scenario == WizardScenario.SETUP and self.state.run_enabled:
            self._run_from_setup()
        elif step_id == "accept" and self.state.scenario == WizardScenario.REVIEW:
            self._confirm_review()
        elif step_id == "output" and self.state.service_result is not None:
            self._enter_finalize()

    def _connect_shortcuts(self) -> None:
        self._log_shortcut = QtGui.QShortcut(QtGui.QKeySequence("L"), self.window)
        self._log_shortcut.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        self._log_shortcut.activated.connect(self.toggle_log)
        self._escape_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Esc"), self.window)
        self._escape_shortcut.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        self._escape_shortcut.activated.connect(self._escape_pressed)

    def toggle_log(self) -> None:
        self._set_log_open(not self.state.log_open)

    def _set_log_open(self, open_: bool) -> None:
        self.state.log_open = bool(open_)
        if self.state.log_open:
            self.window.show_activity_log()
        else:
            self.window.hide_activity_log()
        self._sync_menu_actions()

    def _set_context_details_open(self, open_: bool) -> None:
        self.window.decor_bottom.bar.context_line.set_open(bool(open_))

    def _context_details_toggled(self, open_: bool) -> None:
        blocked = self.window.context_details_action.blockSignals(True)
        self.window.context_details_action.setChecked(bool(open_))
        self.window.context_details_action.blockSignals(blocked)

    def _sync_menu_actions(self) -> None:
        setup = self.state.scenario == WizardScenario.SETUP
        running = self.state.scenario == WizardScenario.RUNNING
        review = self.state.scenario == WizardScenario.REVIEW
        finalize = self.state.scenario == WizardScenario.FINALIZE
        missing = self._missing_run_inputs()
        package_selected = self.state.input_package_path is not None
        method_selected = self.state.method_path is not None
        can_check = setup and not missing and not self._mapping_blocker_items()
        can_run = setup and not missing and self.state.run_enabled
        output_path = _state_mtda_path(self.state)
        has_output = output_path is not None and (
            finalize or self.state.finalized or self.state.service_result is not None
        )

        self.window.choose_package_action.setEnabled(setup)
        self.window.choose_method_action.setEnabled(setup and package_selected)
        self.window.refresh_mapping_action.setEnabled(setup and method_selected)
        self.window.check_readiness_action.setEnabled(can_check)
        self.window.run_method_action.setEnabled(can_run)
        self.window.cancel_run_action.setEnabled(running)
        self.window.confirm_review_action.setEnabled(
            review and self.window.action_bars[WizardScenario.REVIEW].primary_button.isEnabled()
        )
        self.window.finalize_mtda_action.setEnabled(
            finalize and bool(self.state.finalize_note.strip()) and not self.state.finalized
        )
        self.window.open_test_report_action.setEnabled(has_output)
        self.window.open_audit_report_action.setEnabled(has_output)
        self.window.open_workbench_action.setEnabled(has_output)
        self.window.open_output_folder_action.setEnabled(has_output)
        self.window.copy_mtda_path_action.setEnabled(has_output)
        self.window.open_report_completion_action.setEnabled(finalize and has_output and not self.state.finalized)
        self.window.output_menu.menuAction().setEnabled(has_output)

        blocked = self.window.activity_log_action.blockSignals(True)
        self.window.activity_log_action.setChecked(self.state.log_open or self.window.log_drawer.is_open())
        self.window.activity_log_action.blockSignals(blocked)

        blocked = self.window.context_details_action.blockSignals(True)
        self.window.context_details_action.setChecked(self.window.decor_bottom.bar.context_line._open)
        self.window.context_details_action.blockSignals(blocked)

    def _escape_pressed(self) -> None:
        if self.state.log_open or self.window.log_drawer.is_open():
            self._set_log_open(False)
            return
        self._collapse_expanded_task()

    def _collapse_expanded_task(self) -> bool:
        for task in self.window.findChildren(TaskCard):
            chevron = getattr(getattr(task, "_header", None), "_chev", None)
            is_user_collapsible = bool(chevron is not None and chevron.text())
            if task.isVisible() and task.expanded and is_user_collapsible:
                task.set_expanded(False)
                return True
        return False

    def _sync_activity_log(self) -> None:
        for entry in self.state.activity_log:
            self.window.append_log_entry(entry)
        self.window.set_activity_log_count(len(self.state.activity_log))

    def _method_entries(self) -> list[MethodRegistryEntry]:
        analysis_type = None
        if isinstance(self.state.package_summary, dict):
            analysis_type = self.state.package_summary.get("schema_id")
        return self.registry.defaults_for_analysis_type(str(analysis_type or ""))

    def _current_method_id(self) -> str | None:
        if isinstance(self.state.method_summary, dict) and self.state.method_summary.get("method_id"):
            return str(self.state.method_summary["method_id"])
        for entry in self.registry.active_entries():
            if self.state.method_path is not None and Path(self.state.method_path) == entry.method_path:
                return entry.method_id
        return None

    def _ensure_method_selection(self, *, reset_readiness: bool) -> None:
        entries = self._method_entries()
        current_id = self._current_method_id()
        selected = next((entry for entry in entries if entry.method_id == current_id), None)
        if selected is None and entries:
            selected = entries[0]
        if selected is not None:
            self._apply_method_entry(selected, reset_readiness=reset_readiness, log=False)
        else:
            self._sync_method_picker()

    def _method_selected(self, entry_obj: object) -> None:
        if not isinstance(entry_obj, MethodRegistryEntry):
            return
        self._apply_method_entry(entry_obj, reset_readiness=True, log=True)
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._update_setup_action_bar()

    def _apply_method_entry(self, entry: MethodRegistryEntry, *, reset_readiness: bool, log: bool) -> None:
        changed = self.state.method_path != entry.method_path
        self.state.method_path = entry.method_path
        self.state.method_summary = {
            "method_id": entry.method_id,
            "method_name": entry.label,
            "version": entry.version,
            "analysis_type": entry.analysis_type,
            "method_path": str(entry.method_path),
        }
        if entry.method_path.exists():
            try:
                result = self.service.load_method(entry.method_path)
            except Exception as exc:
                if log:
                    self._push_log(f"Method: could not load {entry.label}: {exc}", "err")
            else:
                self.state.method_summary.update(
                    {
                        "method_id": result.method_id,
                        "method_name": result.method_name,
                        "version": result.version,
                        "analysis_type": result.analysis_type,
                        "standard_reference": result.standard_reference,
                        "method_path": str(result.path),
                    }
                )
        self._sync_mapping_from_method(entry, reset_readiness=reset_readiness)
        if reset_readiness and changed:
            self.state.mapping_decision_made = False
            self.state.metadata_decision_made = False
            self.state.readiness_report = None
        if log and changed:
            self._push_log(f"Method: selected {entry.label}.", "info")
        self._sync_method_picker()

    def _sync_mapping_from_method(self, entry: MethodRegistryEntry | None = None, *, reset_readiness: bool) -> None:
        selected = entry or self._selected_registry_entry()
        if selected is None or selected.default_mapping_path is None:
            self.state.mapping_path = None
            self.state.mapping_summary = None
            return
        changed = self.state.mapping_path != selected.default_mapping_path
        self.state.mapping_path = selected.default_mapping_path
        self._load_mapping_context()
        if reset_readiness and changed:
            self.state.mapping_decision_made = False
            self.state.metadata_decision_made = False
            self.state.readiness_report = None

    def _selected_registry_entry(self) -> MethodRegistryEntry | None:
        current_id = self._current_method_id()
        for entry in self.registry.active_entries():
            if current_id and entry.method_id == current_id:
                return entry
            if self.state.method_path is not None and Path(self.state.method_path) == entry.method_path:
                return entry
        return None

    def _sync_method_picker(self) -> None:
        self.window.setup_spotlight.set_method_picker_visible(self.state.input_package_path is not None)
        self.window.setup_spotlight.set_method_entries(self._method_entries(), self._current_method_id())
        self.window.setup_spotlight.set_mapping_label(self._mapping_label())

    def _mapping_label(self) -> str:
        if self.state.input_package_path is None:
            return "Mapping: available after package and method selection"
        if self.state.method_path is None:
            return "Mapping: selected from the method default after method confirmation"
        if self.state.mapping_path is None:
            return "Mapping: no registered mapping for selected method"
        mapping_name = Path(self.state.mapping_path).name
        if isinstance(self.state.mapping_summary, dict):
            mapped = self.state.mapping_summary.get("bound_count")
            total = self.state.mapping_summary.get("critical_total")
            if mapped is not None and total is not None:
                return f"Mapping: {mapping_name} · {mapped}/{total} critical inputs bound"
        return f"Mapping: {mapping_name} · from selected method package"

    def _load_package_context(self) -> None:
        if self.state.input_package_path is None or not Path(self.state.input_package_path).exists():
            return
        try:
            result = self.service.load_package(self.state.input_package_path)
        except Exception as exc:
            self._push_log(f"Package: could not load summary: {exc}", "err")
            return
        self.state.package_summary = {
            "path": str(result.path),
            "schema_id": result.schema_id,
            "schema_version": result.schema_version,
            "sample_type": result.sample_type,
            "run_count": result.run_count,
        }

    def _load_mapping_context(self) -> None:
        if self.state.mapping_path is None or not Path(self.state.mapping_path).exists():
            self.state.mapping_summary = None
            return
        try:
            result = self.service.load_mapping(
                self.state.mapping_path,
                method_path=self.state.method_path,
                package_path=self.state.input_package_path if self.state.input_package_path and Path(self.state.input_package_path).exists() else None,
            )
        except Exception as exc:
            self.state.mapping_summary = {"path": str(self.state.mapping_path), "load_error": str(exc)}
            return
        mapped_fields = list(result.mapped_fields)
        critical_total = int(result.summary.get("execution_critical_total", 0) or 0)
        critical_mapped = int(result.summary.get("execution_critical_mapped", 0) or 0)
        critical_missing = int(result.summary.get("execution_critical_missing", max(0, critical_total - critical_mapped)) or 0)
        critical_ambiguous = int(result.summary.get("execution_critical_ambiguous", 0) or 0)
        report_total = int(result.summary.get("report_fields_total", 0) or 0)
        report_mapped = int(result.summary.get("report_fields_mapped", 0) or 0)
        report_missing = int(result.summary.get("report_fields_missing", max(0, report_total - report_mapped)) or 0)
        blocking_fields = [
            str(row.get("method_field") or row.get("requirement_id") or "")
            for row in mapped_fields
            if str(row.get("severity") or "") == "execution_critical"
            and str(row.get("status") or "") in {"fail", "missing", "ambiguous"}
        ]
        compatibility_summary = (
            result.compatibility_report.get("summary", {})
            if isinstance(result.compatibility_report, dict)
            else {}
        )
        self.state.mapping_summary = {
            "path": str(result.path),
            "mapping_id": result.mapping_id,
            "method_id": result.method_id,
            "status": result.status,
            "bound_count": critical_mapped,
            "critical_total": critical_total,
            "critical_missing_count": critical_missing,
            "ambiguous_count": critical_ambiguous,
            "report_ambiguous_count": int(result.summary.get("report_ambiguous", 0) or 0),
            "blocking_fields": [field for field in blocking_fields if field],
            "compatibility_status": str(compatibility_summary.get("status") or ""),
            "missing_report_field_count": report_missing,
            "mapped_fields": mapped_fields,
            "summary": dict(result.summary),
            "candidate_report": dict(result.candidate_report),
            "resolution_report": dict(result.resolution_report),
        }

    def _sync_decor(self) -> None:
        self._sync_method_picker()
        self.window.set_pipeline_state(
            self.state.scenario,
            package_selected=self.state.input_package_path is not None,
            method_selected=self.state.method_path is not None,
            mapping_selected=self.state.mapping_path is not None,
            mapping_resolved=self.state.mapping_decision_made
            or (self.state.mapping_path is not None and not self._mapping_blocker_items() and self._mapping_gap_count() <= 0),
            readiness_status=self.state.readiness_status,
            finalized=self.state.finalized,
        )
        package = _display_path(self.state.input_package_path, self.window.package_label)
        method = self._method_display_text()
        mapping = _display_path(self.state.mapping_path, "not selected")
        output = _display_path(_state_mtda_path(self.state), "No output path selected")
        self.window.set_context(
            package=package,
            method=method,
            mapping=mapping,
            output=output,
            report_gaps=0 if self.state.metadata_decision_made else self._report_gap_count(),
        )
        self._sync_setup_status()
        self._sync_menu_actions()

    def _method_display_text(self) -> str:
        if isinstance(self.state.method_summary, dict):
            name = self.state.method_summary.get("method_name") or self.state.method_summary.get("method_id")
            if name:
                return str(name)
        return _display_path(self.state.method_path, "not selected")

    def _sync_setup_status(self) -> None:
        if self.state.scenario != WizardScenario.SETUP:
            return
        missing = self._missing_run_inputs()
        if missing:
            self.window.status_dot.set_color(Color.WARN_ACCENT)
            self.window.status_message.setText("Choose inputs")
        elif self.state.readiness_report is None:
            self.window.status_dot.set_color(Color.INFO_ACCENT)
            self.window.status_message.setText("Ready to check")
        elif self.state.run_enabled:
            self.window.status_dot.set_color(Color.OK_ACCENT)
            self.window.status_message.setText("Ready to run")
        else:
            self.window.status_dot.set_color(Color.ERR_ACCENT)
            self.window.status_message.setText("Readiness failed")

    def _ensure_output_path(self) -> None:
        if self.state.output_path is None and self.state.input_package_path is not None:
            package_path = Path(self.state.input_package_path)
            self.state.output_path = package_path.with_suffix(".mtda")

    def _missing_run_inputs(self) -> list[str]:
        missing: list[str] = []
        if self.state.input_package_path is None:
            missing.append("package")
            return missing
        if Path(self.state.input_package_path).suffix.lower() != ".mtdp":
            missing.append("MTDP package")
            return missing
        if self.state.method_path is None:
            missing.append("method")
            return missing
        if self.state.mapping_path is None:
            missing.append("mapping")
        return missing

    def _setup_primary_clicked(self) -> None:
        missing = self._missing_run_inputs()
        if missing:
            self._open_next_missing_input(missing)
            return
        if self.state.readiness_report is None or not self.state.run_enabled:
            self._check_readiness_from_setup()
            return
        self._run_from_setup()

    def _open_next_missing_input(self, missing: list[str]) -> None:
        first = missing[0]
        if first == "package":
            self._change_package()
        elif first == "method":
            self._confirm_selected_method()
        else:
            self._change_mapping()

    def _append_log_entry(self, entry: LogEntry) -> None:
        self.state.activity_log.append(entry)
        self.window.append_log_entry(entry)
        self.window.set_activity_log_count(len(self.state.activity_log))

    def _push_log(self, message: str, level: str = "info") -> None:
        self._append_log_entry(now_entry(message, level))

    def _update_setup_action_bar(self) -> None:
        missing = self._missing_run_inputs()
        if missing:
            first = missing[0]
            if first == "package":
                label = "Choose package"
                sub = "select an MTDP package before choosing method or mapping"
                primary = "Choose package"
            elif first == "method":
                label = "Choose method"
                sub = "select one implemented method for this package"
                primary = "Confirm method"
            else:
                label = "Check mapping"
                sub = "choose or review the method mapping before readiness"
                primary = "Edit mapping"
            enabled = True
        elif self.state.readiness_report is None:
            blockers = self._mapping_blocker_items()
            if blockers:
                label = "Mapping needs attention"
                sub = " · ".join(blockers[:3])
                primary = "Review mapping"
            elif self._report_gap_count() > 0:
                count = self._report_gap_count()
                label = "Ready to check"
                sub = f"critical inputs bound; {count} report field{'s' if count != 1 else ''} can be reviewed later"
                primary = "Check readiness"
            else:
                label = "Ready to check"
                sub = "package, method, and mapping selected"
                primary = "Check readiness"
            enabled = True
        elif not self.state.run_enabled:
            label = "Cannot run · readiness failed"
            sub = self._readiness_blocker_text()
            primary = "Check readiness"
            enabled = True
        else:
            primary = "▶ Run method"
            enabled = True
            open_tasks = self._open_setup_tasks()
            warnings = self._setup_warning_text(open_tasks) or self._readiness_warning_text()
            if warnings:
                label = "Ready · with warnings"
                sub = warnings
            else:
                label = "Ready · all decisions resolved"
                sub = "no warnings — clean run"
        self.window.action_bars[WizardScenario.SETUP].set_state(
            label,
            sub,
            primary,
            "primary",
            enabled=enabled,
        )
        self._sync_setup_spotlight()
        self._update_setup_head()
        self._sync_decor()

    def _update_setup_head(self) -> None:
        missing = self._missing_run_inputs()
        if missing:
            first = missing[0]
            if first == "package":
                title = "Choose package"
                subtitle = "Start with a real MTDP package; method and mapping are selected after the package is known."
            elif first == "method":
                title = "Choose method"
                subtitle = f"Select an implemented method for <b>{self.window.package_label}</b>; the mapping check follows."
            else:
                title = "Check mapping"
                subtitle = "Review the selected mapping profile against the package and method before readiness."
            self.window.spotlight.head.set_text(
                title,
                subtitle,
            )
            return
        if self.state.readiness_report is None:
            self.window.spotlight.head.set_text(
                "Check readiness",
                f"ISO 14126 on <b>{self.window.package_label}</b> · {self._run_count_text()} · readiness not checked",
            )
            return
        open_count = len(self._open_setup_tasks())
        title = {
            0: "Ready to run",
            1: "1 thing to decide first",
        }.get(open_count, "2 things to decide first")
        self.window.spotlight.head.set_text(
            title,
            f"ISO 14126 on <b>{self.window.package_label}</b> · {self._run_count_text()} · mechanical.compression",
        )

    def _open_setup_tasks(self) -> list[str]:
        tasks: list[str] = []
        if self._missing_run_inputs() or self.state.readiness_report is None:
            return tasks
        if self._mapping_gap_count() > 0 and not self.state.mapping_decision_made:
            tasks.append("mapping")
        if self._metadata_gap_count() > 0 and not self.state.metadata_decision_made:
            tasks.append("metadata")
        return tasks

    def _sync_setup_spotlight(self) -> None:
        setup = self.window.setup_spotlight
        self._sync_setup_input_summary()
        missing = self._missing_run_inputs()
        if missing:
            setup.show_prerequisites(missing, package_selected=self.state.input_package_path is not None)
            return
        if self.state.readiness_report is None:
            setup.show_mapping_check(
                blockers=self._mapping_blocker_items(),
                report_gap_count=self._report_gap_count(),
                bound_count=self._bound_count(),
                bound_examples=self._bound_examples(),
                missing_rows=self._missing_report_rows(),
                mapping_name=_display_path(self.state.mapping_path, "method default mapping"),
            )
            return
        if not self.state.run_enabled:
            setup.show_readiness_blocked(self._readiness_blocker_items())
            return
        mapping_gap_count = self._mapping_gap_count()
        metadata_gap_count = self._metadata_gap_count()
        warning_items = self._readiness_warning_items()
        if mapping_gap_count <= 0 and metadata_gap_count <= 0 and warning_items:
            setup.show_readiness_warnings(warning_items)
            return
        setup.show_decisions(
            mapping_gap_count=mapping_gap_count,
            metadata_gap_count=metadata_gap_count,
            bound_count=self._bound_count(),
            bound_examples=self._bound_examples(),
            missing_rows=self._missing_report_rows(),
        )
        setup.set_mapping_resolved(mapping_gap_count <= 0 or self.state.mapping_decision_made)
        setup.set_metadata_resolved(metadata_gap_count <= 0 or self.state.metadata_decision_made)

    def _sync_setup_input_summary(self) -> None:
        package_selected = self.state.input_package_path is not None
        method_selected = self.state.method_path is not None
        mapping_selected = self.state.mapping_path is not None
        blockers = self._mapping_blocker_items()
        mapping_gaps = self._mapping_gap_count()

        package_value = _display_path(self.state.input_package_path, "No package selected")
        package_sub = self._package_summary_text() if package_selected else "required first"
        package_state = "ok" if package_selected else "now"

        method_value = self._method_display_text()
        method_sub = self._method_summary_text()
        if not package_selected:
            method_state = "todo"
        elif method_selected:
            method_state = "ok"
        else:
            method_state = "now"

        mapping_value = _display_path(self.state.mapping_path, "not selected")
        mapping_sub = self._mapping_summary_text(blockers=blockers, mapping_gaps=self._report_gap_count())
        if not method_selected:
            mapping_state = "todo"
        elif not mapping_selected:
            mapping_state = "now"
        elif blockers:
            mapping_state = "err"
        else:
            mapping_state = "ok"

        self.window.setup_spotlight.set_input_summary(
            package_value=package_value,
            package_sub=package_sub,
            package_state=package_state,
            method_value=method_value,
            method_sub=method_sub,
            method_state=method_state,
            mapping_value=mapping_value,
            mapping_sub=mapping_sub,
            mapping_state=mapping_state,
            method_enabled=package_selected,
            mapping_enabled=method_selected,
        )

    def _package_summary_text(self) -> str:
        summary = self.state.package_summary if isinstance(self.state.package_summary, dict) else {}
        parts: list[str] = []
        run_count = summary.get("run_count")
        if run_count not in (None, ""):
            parts.append(f"{_int(run_count, 0)} run(s)")
        sample_type = summary.get("sample_type")
        if sample_type:
            parts.append(str(sample_type))
        schema_id = summary.get("schema_id")
        if schema_id:
            parts.append(str(schema_id))
        return " · ".join(parts) if parts else "package selected"

    def _method_summary_text(self) -> str:
        if self.state.input_package_path is None:
            return "available after package"
        if not isinstance(self.state.method_summary, dict):
            entries = self._method_entries()
            return f"{len(entries)} implemented method(s) available" if entries else "no implemented methods registered"
        parts: list[str] = []
        version = self.state.method_summary.get("version")
        if version:
            parts.append(f"v{version}")
        standard = self.state.method_summary.get("standard_reference")
        if standard:
            parts.append(str(standard))
        analysis = self.state.method_summary.get("analysis_type")
        if analysis:
            parts.append(str(analysis))
        return " · ".join(parts) if parts else "method selected"

    def _mapping_summary_text(self, *, blockers: list[str], mapping_gaps: int) -> str:
        if self.state.method_path is None:
            return "selected after method"
        if self.state.mapping_path is None:
            return "no mapping selected"
        if blockers:
            return blockers[0]
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        mapped = mapping.get("bound_count")
        total = mapping.get("critical_total")
        if mapped is not None and total is not None:
            base = f"{_int(mapped, 0)}/{_int(total, 0)} critical inputs bound"
        else:
            base = "mapping selected"
        if mapping_gaps:
            return f"{base} · {mapping_gaps} report gap(s)"
        return base

    def _setup_warning_text(self, open_tasks: list[str]) -> str:
        parts: list[str] = []
        if "mapping" in open_tasks:
            count = self._mapping_gap_count()
            parts.append(f"{count} critical mapping issue{'s' if count != 1 else ''}")
        if "metadata" in open_tasks:
            report_count = self._report_gap_count()
            metadata_count = self._raw_metadata_gap_count()
            if report_count:
                parts.append(f"{report_count} unmapped report binding{'s' if report_count != 1 else ''}")
            if metadata_count:
                parts.append(f"{metadata_count} recommended field{'s' if metadata_count != 1 else ''} blank")
        return " · ".join(parts)

    def _readiness_warning_items(self) -> list[str]:
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        warnings = report.get("warnings")
        if isinstance(warnings, (list, tuple)) and warnings:
            return [str(item) for item in warnings if str(item)]
        if isinstance(warnings, str) and warnings:
            return [warnings]
        return []

    def _readiness_warning_text(self) -> str:
        return " · ".join(self._readiness_warning_items()[:3])

    def _readiness_blocker_items(self) -> list[str]:
        report = self.state.readiness_report or {}
        items: list[str] = []
        for key in ("blockers", "blocking_fields", "failed_fields", "errors"):
            value = report.get(key)
            if isinstance(value, (list, tuple)):
                items.extend(str(item) for item in value if str(item))
            elif isinstance(value, str) and value:
                items.append(value)
        if not items:
            requirements = report.get("requirements")
            if isinstance(requirements, (list, tuple)):
                for row in requirements:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("status") or "").casefold() in {"pass", "ok", "found"}:
                        continue
                    severity = str(row.get("severity") or row.get("importance") or "").casefold()
                    if "critical" not in severity and row.get("required") is not True:
                        continue
                    name = str(row.get("method_field") or row.get("requirement_id") or row.get("field") or "requirement")
                    reason = str(row.get("message") or row.get("reason") or row.get("status") or "failed")
                    items.append(f"{name}: {reason}")
        return items

    def _readiness_blocker_text(self) -> str:
        items = self._readiness_blocker_items()
        if items:
            return " · ".join(items)
        return "resolve readiness blockers before running"

    def _mapping_blocker_items(self) -> list[str]:
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        items: list[str] = []
        load_error = mapping.get("load_error")
        if load_error:
            items.append(f"mapping could not load: {load_error}")
        critical_missing = _int(mapping.get("critical_missing_count"), 0)
        ambiguous = _int(mapping.get("ambiguous_count"), 0)
        if critical_missing:
            fields = mapping.get("blocking_fields")
            if isinstance(fields, (list, tuple)) and fields:
                items.append("missing critical inputs: " + ", ".join(str(field) for field in fields[:4]))
            else:
                items.append(f"{critical_missing} execution-critical inputs missing")
        if ambiguous:
            items.append(f"{ambiguous} ambiguous mapping choice{'s' if ambiguous != 1 else ''}")
        compatibility = str(mapping.get("compatibility_status") or "").upper()
        if "INCOMPATIBLE" in compatibility:
            items.append("method/package compatibility failed")
        return items

    def _check_readiness_from_setup(self) -> None:
        if self._missing_run_inputs():
            self._update_setup_action_bar()
            return
        mapping_blockers = self._mapping_blocker_items()
        if mapping_blockers:
            suggestions = _default_mapping_suggestions(self.state.mapping_summary)
            choice = self._mapping_resolution_choice(mapping_blockers, suggestions=suggestions)
            if choice == "apply_defaults":
                if not self._apply_mapping_default_suggestions(suggestions):
                    self._update_setup_action_bar()
                    return
                mapping_blockers = self._mapping_blocker_items()
                if mapping_blockers:
                    self._push_log(
                        "Mapping: suggested defaults were applied, but unresolved critical bindings remain.",
                        "warn",
                    )
                    self._update_setup_action_bar()
                    return
            if choice == "edit":
                self._change_mapping()
                self._update_setup_action_bar()
                return
            if choice != "apply_defaults":
                self._push_log("Readiness check cancelled while mapping blockers are unresolved.", "warn")
                self._update_setup_action_bar()
                return
        self._push_log("Checking readiness.", "now")
        self.window.action_bars[WizardScenario.SETUP].set_state(
            "Checking readiness",
            "inspecting package, method, and mapping",
            "Checking…",
            "subtle",
            primary_enabled=False,
        )
        worker = service_adapter.check_readiness_async(self.state, service=self.service, parent=self.window)
        if worker is None:
            self._push_log("Readiness check could not start; choose all workflow inputs first.", "err")
            self.state.readiness_report = {
                "status": "BLOCKED",
                "errors": ["choose package, method, and mapping before readiness"],
            }
            self._update_setup_action_bar()
            return
        self.attach_worker(worker)

    def _mapping_resolution_choice(self, blockers: list[str], *, suggestions: list[dict[str, Any]] | None = None) -> str:
        box = QtWidgets.QMessageBox(self.window)
        box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        box.setWindowTitle("Mapping needs attention")
        box.setText("The selected mapping has conflicts or missing method inputs before readiness.")
        details = "\n".join(f"- {item}" for item in blockers[:5])
        suggestion_rows = _format_mapping_suggestions(suggestions or [])
        if suggestion_rows:
            box.setInformativeText(
                f"{details}\n\nSuggested default repair:\n{suggestion_rows}\n\n"
                "Apply the suggested mapping profile now, or open the editor to inspect and change it first."
            )
        else:
            box.setInformativeText(
                f"{details}\n\nNo safe default repair was found. Open the mapping editor to choose compatible package sources before readiness."
            )
        apply_button = None
        if suggestions:
            apply_button = box.addButton(
                f"Apply suggested mapping ({len(suggestions)})",
                QtWidgets.QMessageBox.ButtonRole.AcceptRole,
            )
        edit_button = box.addButton("Open edit mapping", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        box.addButton("Cancel", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if apply_button is not None and clicked is apply_button:
            return "apply_defaults"
        if clicked is edit_button:
            return "edit"
        return "cancel"

    def _apply_mapping_default_suggestions(self, suggestions: list[dict[str, Any]]) -> bool:
        if not suggestions:
            return False
        if self.state.mapping_path is None or not Path(self.state.mapping_path).exists():
            self._push_log("Mapping: cannot apply suggested defaults because no mapping profile is selected.", "err")
            return False
        try:
            payload = load_mapping(self.state.mapping_path)
            repaired = _mapping_payload_with_suggestions(payload, suggestions)
            output = _default_edited_mapping_path(self.state.mapping_path)
            saved = write_mapping_profile(repaired, output)
        except Exception as exc:
            self._push_log(f"Mapping: could not apply suggested defaults: {exc}", "err")
            return False
        self.state.mapping_path = saved
        self.state.readiness_report = None
        self.state.mapping_decision_made = False
        self._load_mapping_context()
        if not self._mapping_blocker_items():
            self.state.mapping_decision_made = True
            self._push_log(f"Mapping: applied suggested defaults in {saved.name}.", "info")
        else:
            self._push_log(f"Mapping: saved partial suggested defaults in {saved.name}.", "warn")
        self._sync_method_picker()
        self._sync_decor()
        return True

    def _mapping_gap_count(self) -> int:
        if self.state.mapping_decision_made:
            return 0
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        for key in (
            "execution_critical_missing",
            "critical_missing_count",
            "missing_critical_mapping_count",
            "execution_critical_ambiguous",
            "critical_ambiguous_count",
        ):
            value = _lookup_nested_int(mapping, report, key=key)
            if value is not None:
                return value
        return len(self._mapping_blocker_items())

    def _report_gap_count(self) -> int:
        if self.state.metadata_decision_made:
            return 0
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        if report:
            for key in (
                "report_missing_total",
                "missing_report_field_count",
                "unmapped_report_binding_count",
                "report_fields_missing",
                "recommended_missing_count",
                "metadata_gap_count",
                "blank_recommended_field_count",
            ):
                value = _lookup_nested_int(report, key=key)
                if value is not None:
                    return max(0, value)
            return len(self._missing_report_rows())
        for key in (
            "report_missing_total",
            "missing_report_field_count",
            "unmapped_report_binding_count",
            "report_fields_missing",
            "recommended_missing_count",
            "metadata_gap_count",
            "blank_recommended_field_count",
        ):
            value = _lookup_nested_int(report, mapping, key=key)
            if value is not None:
                return max(0, value)
        return len(self._missing_report_rows())

    def _metadata_gap_count(self) -> int:
        if self.state.metadata_decision_made:
            return 0
        return max(self._raw_metadata_gap_count(), self._report_gap_count())

    def _raw_metadata_gap_count(self) -> int:
        if self.state.metadata_decision_made:
            return 0
        result = self.state.service_result if isinstance(self.state.service_result, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        for key in (
            "recommended_missing_count",
            "metadata_gap_count",
            "missing_metadata_count",
            "blank_recommended_field_count",
        ):
            value = _lookup_nested_int(result, report, key=key)
            if value is not None:
                return max(0, value)
        fields = report.get("missing_metadata_fields") or report.get("recommended_missing_fields")
        if isinstance(fields, (list, tuple)):
            return len(fields)
        return 0

    def _bound_count(self) -> int:
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        if report:
            for key in ("bound_count", "mapped_count", "critical_bound_count", "resolved_mapping_count"):
                value = _lookup_nested_int(report, key=key)
                if value is not None:
                    return value
        for key in ("bound_count", "mapped_count", "critical_bound_count", "resolved_mapping_count"):
            value = _lookup_nested_int(mapping, report, key=key)
            if value is not None:
                return value
        return len(self._bound_examples())

    def _bound_examples(self) -> list[str]:
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        if report:
            examples = report.get("bound_examples") or report.get("mapped_fields") or report.get("bindings")
            parsed = _binding_labels(examples)
            if parsed:
                return parsed
        for container in (mapping, report):
            examples = container.get("bound_examples") or container.get("mapped_fields") or container.get("bindings")
            parsed = _binding_labels(examples)
            if parsed:
                return parsed
        return []

    def _missing_report_rows(self) -> list[tuple[str, str]]:
        mapping = self.state.mapping_summary if isinstance(self.state.mapping_summary, dict) else {}
        report = self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {}
        report_rows = (
            report.get("missing_report_fields")
            or report.get("unmapped_report_bindings")
            or report.get("missing_fields")
        )
        parsed_report_rows = _field_rows(report_rows)
        if parsed_report_rows:
            return parsed_report_rows
        if report:
            for key in (
                "missing_report_field_count",
                "unmapped_report_binding_count",
                "mapping_gap_count",
                "missing_mapping_count",
            ):
                value = _lookup_nested_int(report, key=key)
                if value is not None and value <= 0:
                    return []
                if value is not None:
                    break
            else:
                return []
        for container in (mapping,):
            rows = (
                container.get("missing_report_fields")
                or container.get("unmapped_report_bindings")
                or container.get("missing_fields")
            )
            parsed = _field_rows(rows)
            if parsed:
                return parsed
            mapped_fields = container.get("mapped_fields")
            if isinstance(mapped_fields, (list, tuple)):
                parsed = []
                for row in mapped_fields:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("severity") or "") == "execution_critical":
                        continue
                    if str(row.get("status") or "").casefold() in {"pass", "found", "ok"}:
                        continue
                    field = str(row.get("method_field") or row.get("requirement_id") or "")
                    reason = str(row.get("operator_status") or row.get("status") or "needs review")
                    if field:
                        parsed.append((field, reason))
                if parsed:
                    return parsed
        return []

    def _run_count_text(self) -> str:
        count = self._run_count()
        return f"{count} run{'s' if count != 1 else ''}" if count else "runs unknown"

    def _run_count(self) -> int:
        for container in (
            self.state.package_summary if isinstance(self.state.package_summary, dict) else {},
            self.state.readiness_report if isinstance(self.state.readiness_report, dict) else {},
        ):
            for key in ("run_count", "runs_count", "specimen_count", "test_count"):
                value = container.get(key)
                if value not in (None, ""):
                    return _int(value, 0)
            runs = container.get("runs")
            if isinstance(runs, (list, tuple, dict)):
                return len(runs)
        return 0

    def _resolve_mapping_from_save(self) -> None:
        self.state.mapping_decision_made = True
        self._push_log("Mapping: user-provided bindings recorded.", "ok")
        print("Mapping: user-provided bindings recorded.")
        self._update_setup_action_bar()
        self.window.setup_spotlight.set_mapping_resolved(True)

    def _resolve_mapping_from_skip(self) -> None:
        count = self._mapping_gap_count()
        self.state.mapping_decision_made = True
        self._push_log(f"Mapping: accepted warnings ({count} unmapped fields → report).", "warn")
        print("Mapping: accepted warnings.")
        self._update_setup_action_bar()
        self.window.setup_spotlight.set_mapping_resolved(True)

    def _edit_mapping_profile(self) -> None:
        self._change_mapping()

    def _change_package(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Choose MTDP package",
            str(self.state.input_package_path or Path.cwd()),
            "MTDP packages (*.mtdp);;All files (*)",
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".mtdp":
            self.window.status_dot.set_color(Color.ERR_ACCENT)
            self.window.status_message.setText("Choose an MTDP package")
            return
        self.state.input_package_path = Path(path)
        self.state.output_path = None
        self._ensure_output_path()
        self.state.readiness_report = None
        self.state.method_path = None
        self.state.method_summary = None
        self.state.mapping_path = None
        self.state.mapping_summary = None
        self.state.mapping_decision_made = False
        self.state.metadata_decision_made = False
        self.window.set_package_path(path)
        self._load_package_context()
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._push_log("Context: package changed.", "info")
        self._update_setup_action_bar()

    def _confirm_selected_method(self) -> None:
        entry = self.window.setup_spotlight.selected_method_entry()
        if isinstance(entry, MethodRegistryEntry):
            self._method_selected(entry)
            return
        self._change_method()

    def _change_method(self) -> None:
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._sync_method_picker()
        combo = self.window.setup_spotlight.method_combo
        combo.setFocus()
        combo.showPopup()
        self._update_setup_action_bar()

    def _change_mapping(self) -> None:
        if self.state.method_path is None:
            self._change_method()
            return

        selected = self._selected_registry_entry()
        default_path = selected.default_mapping_path if selected is not None else None
        if self.state.mapping_path is None and default_path is not None:
            self.state.mapping_path = default_path
            self._load_mapping_context()

        current_path = Path(self.state.mapping_path) if self.state.mapping_path is not None else None
        model: dict[str, Any]
        if current_path is not None and current_path.exists():
            try:
                result = self.service.load_mapping(
                    current_path,
                    method_path=self.state.method_path,
                    package_path=self.state.input_package_path
                    if self.state.input_package_path and Path(self.state.input_package_path).exists()
                    else None,
                )
            except Exception as exc:
                self._push_log(f"Mapping: could not load profile for review: {exc}", "err")
                model = _empty_mapping_dialog_model(str(exc))
            else:
                model = mapping_preview_view_model(result)
        else:
            model = _empty_mapping_dialog_model()

        dialog = MethodMappingDialog(
            model,
            current_path=current_path,
            default_path=default_path,
            parent=self.window,
        )
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        chosen = Path(dialog.selected_mapping_path) if dialog.selected_mapping_path is not None else None
        if chosen is None:
            self._push_log("Mapping: no profile selected.", "warn")
            return

        changed = self.state.mapping_path != chosen
        self.state.mapping_path = chosen
        self._load_mapping_context()
        if changed:
            self.state.mapping_decision_made = False
            self.state.metadata_decision_made = False
            self.state.readiness_report = None
        self.window.setup_spotlight.set_mapping_resolved(False)
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        action = "selected" if changed else "reviewed"
        self._push_log(f"Mapping: {action} profile {chosen.name}.", "info")
        self._update_setup_action_bar()

    def _resolve_metadata_from_dialog(self) -> None:
        self.state.metadata_decision_made = True
        self._push_log("Metadata: report-completion dialog requested.", "info")
        print("Metadata: report-completion dialog requested.")
        self._update_setup_action_bar()
        self.window.setup_spotlight.set_metadata_resolved(True)

    def _resolve_metadata_from_warning(self) -> None:
        self.state.metadata_decision_made = True
        self._push_log("Metadata: accepted warnings.", "warn")
        print("Metadata: accepted warnings.")
        self._update_setup_action_bar()
        self.window.setup_spotlight.set_metadata_resolved(True)

    def _run_from_setup(self) -> None:
        if self._missing_run_inputs() or not self.state.run_enabled:
            self._update_setup_action_bar()
            return
        self._push_log("Operator: run requested.", "now")
        self._push_log("Starting execution", "info")
        self._enter_running()
        worker = service_adapter.run_method_async(self.state, service=self.service, parent=self.window)
        if worker is not None:
            self.attach_worker(worker)

    def _enter_running(self) -> None:
        self.state.scenario = WizardScenario.RUNNING
        self.state.execution_status = "running"
        self.state.last_error = None
        self._running_started_at = datetime.now().strftime("%H:%M")
        if not self.state.per_run_status:
            run_count = self._run_count()
            self.state.per_run_status = {f"run_{index:03d}": "queued" for index in range(1, run_count + 1)}
            if self.state.per_run_status:
                self.state.per_run_status["run_001"] = "running"
        self.window.set_scenario(WizardScenario.RUNNING)
        self.window.running_spotlight.clear_error()
        self.window.running_spotlight.reset_activity()
        self.window.running_spotlight.set_phase(
            self.state.running_phase_label or "Resolving method inputs",
            self._running_meta(),
        )
        self.window.running_spotlight.set_stage(self.state.current_phase or "load_input_package")
        self.window.running_spotlight.set_progress(self.state.running_progress_pct)
        self.window.running_spotlight.set_run_status(self.state.per_run_status)
        self.window.running_spotlight.append_event(
            "Execution requested",
            phase=self.state.current_phase or "load_input_package",
            status="running",
            progress=self.state.running_progress_pct,
        )
        self._update_running_action_bar()
        self._sync_decor()

    def attach_worker(self, worker: Any) -> None:
        self._worker = worker
        self._connect_signal(worker, "phase_changed", self._worker_phase_changed)
        self._connect_signal(worker, "progress", self._worker_progress)
        self._connect_signal(worker, "run_status", self._worker_run_status)
        has_log_line = self._connect_signal(worker, "log_line", self._worker_log_line)
        if not has_log_line:
            self._connect_signal(worker, "log", self._worker_log_line)
        self._connect_signal(worker, "completed", self._worker_completed)
        self._connect_signal(worker, "failed", self._worker_failed)
        self._connect_signal(worker, "cancelled", self._worker_cancelled)

    def _connect_signal(self, worker: Any, name: str, slot: Any) -> bool:
        signal = getattr(worker, name, None)
        if signal is not None and hasattr(signal, "connect"):
            if isinstance(worker, QtCore.QObject) and worker.thread() != self.thread():
                signal.connect(slot, QtCore.Qt.ConnectionType.QueuedConnection)
            else:
                signal.connect(slot)
            return True
        return False

    def _update_running_action_bar(self) -> None:
        self.window.action_bars[WizardScenario.RUNNING].set_state(
            "Method execution in progress",
            self._running_meta(),
            "Cancel run",
            "danger",
        )

    def _running_meta(self) -> str:
        output = self.state.output_path.name if self.state.output_path else "…mtda"
        started = self._running_started_at or datetime.now().strftime("%H:%M")
        return f"started {started} · output → {output} · {len(self.state.activity_log)} log events"

    @QtCore.pyqtSlot(str)
    def _worker_phase_changed(self, name: str) -> None:
        self.state.running_phase_label = str(name)
        self._push_log(str(name), "info")
        self.window.running_spotlight.set_phase(str(name), self._running_meta())
        self._update_running_action_bar()

    @QtCore.pyqtSlot(object)
    def _worker_progress(self, payload: object) -> None:
        pct = int(payload if isinstance(payload, int) else 0)
        phase_key = self.state.current_phase or ""
        message = f"Progress updated to {pct}%"
        status = "running"
        if isinstance(payload, dict):
            pct = int(payload.get("progress_percent") or payload.get("pct") or 0)
            phase_key = str(payload.get("phase") or phase_key)
            message = str(payload.get("message") or phase_key or message)
            status = str(payload.get("status") or status)
            if message:
                self.state.running_phase_label = message
            if phase_key:
                self.state.current_phase = phase_key
                self.window.running_spotlight.set_stage(phase_key)
        self.state.running_progress_pct = max(0, min(100, pct))
        self.window.running_spotlight.set_progress(self.state.running_progress_pct)
        self.window.running_spotlight.append_event(
            message,
            phase=phase_key,
            status=status,
            progress=self.state.running_progress_pct,
        )
        self.window.running_spotlight.set_phase(
            self.state.running_phase_label or "Running method",
            self._running_meta(),
        )
        self._update_running_action_bar()

    @QtCore.pyqtSlot(dict)
    def _worker_run_status(self, payload: dict[str, Any]) -> None:
        phase = payload.get("phase")
        if phase:
            self.state.current_phase = str(phase)
            self.window.running_spotlight.set_stage(str(phase))
        runs = payload.get("runs")
        if runs is None:
            runs = payload
        if isinstance(runs, dict) and runs:
            self.state.per_run_status = {str(run_id): str(status) for run_id, status in runs.items()}
            notes = payload.get("notes") if isinstance(payload.get("notes"), dict) else None
            self.window.running_spotlight.set_run_status(self.state.per_run_status, notes)
            self.window.running_spotlight.append_event(
                f"Run rows updated: {_run_status_counts(self.state.per_run_status)}",
                phase=str(phase or self.state.current_phase or ""),
                status=str(payload.get("status") or "running"),
                progress=self.state.running_progress_pct,
            )

    @QtCore.pyqtSlot(str)
    def _worker_log_line(self, message: str) -> None:
        self._push_log(str(message), "info")
        self.window.running_spotlight.append_event(
            str(message),
            phase=self.state.current_phase or "",
            status="info",
            progress=self.state.running_progress_pct,
        )
        self.window.running_spotlight.set_phase(
            self.state.running_phase_label or "Running method",
            self._running_meta(),
        )
        self._update_running_action_bar()

    @QtCore.pyqtSlot(dict)
    def _worker_completed(self, payload: dict[str, Any]) -> None:
        if isinstance(payload, dict) and payload.get("task") == "readiness":
            readiness = payload.get("readiness")
            self.state.readiness_report = dict(readiness) if isinstance(readiness, dict) else {}
            if not self.state.readiness_report.get("status") and payload.get("readiness_status"):
                self.state.readiness_report["status"] = payload.get("readiness_status")
            self._push_log(str(payload.get("message") or "Readiness check complete"), "ok")
            self.state.scenario = WizardScenario.SETUP
            self.window.set_scenario(WizardScenario.SETUP)
            self._update_setup_action_bar()
            return
        result = payload.get("result") if isinstance(payload, dict) else None
        self.state.service_result = dict(result) if isinstance(result, dict) else payload
        if isinstance(self.state.service_result, dict):
            self.state.validation_summary = self.state.service_result.get("validation_summary") or {}
            acceptance_report = self.state.service_result.get("acceptance_report") or {}
            self.state.acceptance_summary = acceptance_report or self.state.service_result.get("acceptance_summary") or {}
            output_path = self.state.service_result.get("mtda_path") or self.state.service_result.get("output_path")
            if output_path:
                self.state.output_path = Path(str(output_path))
        self.state.execution_status = "completed"
        self.state.running_progress_pct = 100
        self.window.running_spotlight.set_progress(100)
        self.window.running_spotlight.set_stage("complete")
        self.window.running_spotlight.append_event(
            str(payload.get("message") or "Method run complete"),
            phase="complete",
            status="ok",
            progress=100,
        )
        self._push_log(str(payload.get("message") or "Method run complete"), "ok")
        self._update_running_action_bar()
        QtCore.QTimer.singleShot(700, self._show_review_after_completion)

    @QtCore.pyqtSlot(dict)
    def _worker_failed(self, payload: dict[str, Any]) -> None:
        self.state.last_error = dict(payload)
        message = str(payload.get("message") or payload)
        self._push_log(message, "err")
        if payload.get("task") == "readiness" and self.state.scenario == WizardScenario.SETUP:
            self.state.readiness_report = {"status": "BLOCKED", "errors": [message]}
            self._update_setup_action_bar()
            return
        self.state.execution_status = "failed"
        self.window.running_spotlight.show_error(message)
        self.window.running_spotlight.append_event(
            message,
            phase=str(payload.get("phase") or self.state.current_phase or ""),
            status="err",
            progress=self.state.running_progress_pct,
        )
        self._update_running_action_bar()

    @QtCore.pyqtSlot(dict)
    def _worker_cancelled(self, payload: dict[str, Any]) -> None:
        self.state.execution_status = "cancelled"
        self._push_log(str(payload.get("message") or "Operator cancelled the run."), "err")
        self.window.running_spotlight.append_event(
            str(payload.get("message") or "Operator cancelled the run."),
            phase=str(payload.get("phase") or self.state.current_phase or ""),
            status="warn",
            progress=self.state.running_progress_pct,
        )
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._sync_decor()

    def _cancel_run(self) -> None:
        if self._worker is not None:
            if hasattr(self._worker, "request_cancel"):
                self._worker.request_cancel()
            elif hasattr(self._worker, "cancel"):
                self._worker.cancel()
        self.state.execution_status = "cancelled"
        self._push_log("Operator cancelled the run.", "err")
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._sync_decor()

    def _back_to_setup_from_error(self) -> None:
        self.state.scenario = WizardScenario.SETUP
        self.window.set_scenario(WizardScenario.SETUP)
        self._sync_decor()

    def _show_review_after_completion(self) -> None:
        self._enter_review()

    def _enter_review(self) -> None:
        self.state.scenario = WizardScenario.REVIEW
        self._review_models = self._review_models_from_summary(
            self.state.acceptance_summary,
            evidence_by_run=self._acceptance_evidence_by_run(),
        )
        self.window.review_spotlight.set_runs(self._review_models)
        for model in self._review_models:
            self.state.acceptance_keep.setdefault(model.run_id, _default_keep(model))
            self.state.acceptance_override_defects[model.run_id] = _defect_labels_for_model(model)
            self.window.review_spotlight.set_decision(model.run_id, self.state.acceptance_keep[model.run_id])
            reason = self.state.acceptance_override_reason.get(model.run_id)
            if reason:
                self.window.review_spotlight.rows[model.run_id].justify.line_edit.setText(reason)
        self.window.set_scenario(WizardScenario.REVIEW)
        self._update_review_action_bar()
        self._sync_decor()

    def _review_keep(self, run_id: str) -> None:
        self.state.acceptance_keep[run_id] = True
        model = next((item for item in self._review_models if item.run_id == run_id), None)
        if model is not None:
            self.state.acceptance_override_defects[run_id] = _defect_labels_for_model(model)
        self.window.review_spotlight.set_decision(run_id, True)
        self.window.review_spotlight.focus_reason(run_id)
        self._push_log(f"Acceptance: keeping flagged run {run_id}.", "warn")
        self._update_review_action_bar()

    def _review_remove(self, run_id: str) -> None:
        self.state.acceptance_keep[run_id] = False
        self.state.acceptance_override_reason.pop(run_id, None)
        self.state.acceptance_override_defects.pop(run_id, None)
        self.window.review_spotlight.set_decision(run_id, False)
        self._push_log(f"Acceptance: removing flagged run {run_id}.", "info")
        self._update_review_action_bar()

    def _review_expanded(self, run_id: str, is_open: bool) -> None:
        self.state.expanded_run = run_id if is_open else None

    def _review_reason_changed(self, run_id: str, text: str) -> None:
        self.state.acceptance_override_reason[run_id] = text
        if self.state.acceptance_keep.get(run_id) is True:
            model = next((item for item in self._review_models if item.run_id == run_id), None)
            if model is not None:
                self.state.acceptance_override_defects[run_id] = _defect_labels_for_model(model)
        self._update_review_action_bar()

    def _update_review_action_bar(self) -> None:
        models_by_id = {model.run_id: model for model in self._review_models}
        override_count = sum(
            1
            for run_id, keep in self.state.acceptance_keep.items()
            if keep is True and run_id in models_by_id and not _default_keep(models_by_id[run_id])
        )
        missing_reasons = [
            run_id
            for run_id, keep in self.state.acceptance_keep.items()
            if keep is True
            and run_id in models_by_id
            and not _default_keep(models_by_id[run_id])
            and not self.state.acceptance_override_reason.get(run_id, "").strip()
        ]
        final_count = self._review_final_report_count()
        self._sync_review_summary(override_count=override_count, missing_reason_count=len(missing_reasons))
        if missing_reasons:
            label = "Review needs justification"
            sub = f"{len(missing_reasons)} override(s) still need a reason"
        elif override_count:
            label = f"{override_count} override(s) justified · {final_count} runs in final report"
            sub = "Confirm will persist acceptance decisions and open output"
        elif self._review_models:
            label = f"{len(self._review_models)} flagged run(s) follow safe defaults · {final_count} runs in final report"
            sub = "review evidence or confirm the default selection"
        else:
            label = f"No flagged runs · {final_count} runs in final report"
            sub = "click Confirm to open the output bundle"
        self.window.action_bars[WizardScenario.REVIEW].set_state(
            label,
            sub,
            "Confirm & open output",
            "primary",
            primary_enabled=not missing_reasons,
        )
        self._sync_menu_actions()

    def _confirm_review(self) -> None:
        for model in self._review_models:
            if self.state.acceptance_keep.get(model.run_id) is True and not _default_keep(model):
                reason = self.state.acceptance_override_reason.get(model.run_id, "").strip()
                if not reason:
                    self.window.review_spotlight.focus_reason(model.run_id)
                    self.window.action_bars[WizardScenario.REVIEW].set_state(
                        "Review needs justification",
                        "add a justification for each override before confirming",
                        "Confirm & open output",
                        "primary",
                    )
                    return
        service_adapter.persist_acceptance(self.state)
        self._enter_finalize()

    def _enter_finalize(self) -> None:
        self.state.scenario = WizardScenario.FINALIZE
        self.window.set_scenario(WizardScenario.FINALIZE)
        self._sync_finalize_spotlight()
        self._update_finalize_action_bar()
        self._sync_decor()

    def _sync_finalize_spotlight(self) -> None:
        finalize = self.window.finalize_spotlight
        finalize.set_mtda_path(_state_mtda_path(self.state))
        finalize.set_missing_fields(_missing_field_count(self.state))
        finalize.set_review_counts(_amendment_count(self.state), _reviewer_note_count(self.state))
        if finalize.reviewer_edit.text() != self.state.finalize_reviewer:
            finalize.reviewer_edit.setText(self.state.finalize_reviewer)
        if finalize.note_edit.text() != self.state.finalize_note:
            finalize.note_edit.setText(self.state.finalize_note)
        finalize.set_finalized(self.state.finalized)
        if self.state.finalized:
            self.window.set_finalized_head()

    def _update_finalize_action_bar(self) -> None:
        label = "Finalized" if self.state.finalized else "MTDA · Draft, not finalized"
        amendments = _amendment_count(self.state)
        reviewer_notes = _reviewer_note_count(self.state)
        self.window.finalize_spotlight.set_review_counts(amendments, reviewer_notes)
        sub = f"amendments {amendments} · reviewer notes {reviewer_notes}"
        self.window.action_bars[WizardScenario.FINALIZE].set_state(
            label,
            sub,
            "Close wizard",
            "plain",
        )
        self._sync_menu_actions()

    def _finalize_reviewer_changed(self, text: str) -> None:
        self.state.finalize_reviewer = text
        self._update_finalize_action_bar()

    def _finalize_note_changed(self, text: str) -> None:
        self.state.finalize_note = text
        self._update_finalize_action_bar()

    def _finalize_mtda(self) -> None:
        note = self.state.finalize_note.strip()
        if not note:
            self.window.finalize_spotlight.show_error("Enter a note before finalizing.")
            return
        result = service_adapter.finalize_mtda(
            self.state,
            reviewer=self.state.finalize_reviewer.strip(),
            note=note,
        )
        if str(result.get("status") or "") != "finalized":
            errors = result.get("errors") or []
            message = "; ".join(str(error) for error in errors) if isinstance(errors, list) else str(errors)
            self.state.finalize_error = message or "Finalization failed."
            self.window.finalize_spotlight.show_error(self.state.finalize_error)
            return
        output_path = result.get("output_path")
        if output_path:
            self.state.output_path = Path(str(output_path))
        self.state.finalized = True
        self.state.finalize_error = None
        self.window.finalize_spotlight.show_error("")
        self.window.finalize_spotlight.set_finalized(True)
        self.window.finalize_spotlight.set_mtda_path(_state_mtda_path(self.state))
        self._push_log("MTDA finalized.", "ok")
        self.window.status_dot.set_color(Color.OK_ACCENT)
        self.window.status_message.setText("Finalized")
        self.window.set_finalized_head()
        self._update_finalize_action_bar()
        self._sync_decor()

    def _open_test_report(self) -> None:
        self._open_archive_surface(
            "report",
            ("test_report.html", "iso14126_report.html"),
            member_candidates=(
                "dataset/04_reports/test_report.html",
                "report/test_report.html",
                "report/iso14126_report.html",
            ),
        )

    def _open_audit_report(self) -> None:
        self._open_archive_surface(
            "audit",
            ("audit_report.html", "index.html"),
            member_candidates=(
                "dataset/04_reports/audit_report.html",
                "audit/audit_report.html",
                "interactive_report/index.html",
            ),
        )

    def _open_workbench(self) -> None:
        service_result = self.state.service_result if isinstance(self.state.service_result, dict) else {}
        workbench = service_result.get("workbench_path")
        if workbench:
            path = Path(str(workbench))
            self._open_local_path(path / "index.html" if path.is_dir() else path)
            return
        self._open_archive_surface(
            "workbench",
            ("index.html",),
            member_candidates=("workbench/index.html",),
        )

    def _open_output_folder(self) -> None:
        path = _state_mtda_path(self.state)
        if path is not None:
            self._open_local_path(path.parent)

    def _open_mtda_output(self) -> None:
        path = _state_mtda_path(self.state)
        if path is None or not path.exists():
            self.window.finalize_spotlight.show_error("No MTDA output is available to open.")
            return
        browser_index = _extract_mtda_browser_index(path)
        if browser_index is None:
            self.window.finalize_spotlight.show_error("MTDA output is not a readable archive with an index.html entry point.")
            return
        self._open_local_path(browser_index)

    def _copy_mtda_path(self) -> None:
        path = _state_mtda_path(self.state)
        if path is None:
            self.window.finalize_spotlight.show_error("No MTDA path is available to copy.")
            return
        QtWidgets.QApplication.clipboard().setText(str(path))
        self.window.finalize_spotlight.show_toast("Copied")

    def _open_report_completion(self) -> None:
        path = _state_mtda_path(self.state)
        if path is None or not path.exists():
            self.window.finalize_spotlight.show_error("No MTDA output is available for report completion.")
            return
        from ui.method_run_wizard.report_completion_dialog import ReportCompletionDialog

        dialog = ReportCompletionDialog(path, self.window)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted and dialog.result_path:
            self.state.output_path = dialog.result_path
            if isinstance(self.state.service_result, dict):
                self.state.service_result["output_path"] = str(dialog.result_path)
                self.state.service_result["mtda_path"] = str(dialog.result_path)
            self._sync_finalize_spotlight()

    def _open_archive_surface(
        self,
        prefix: str,
        preferred_names: tuple[str, ...],
        *,
        member_candidates: tuple[str, ...] = (),
    ) -> None:
        path = _state_mtda_path(self.state)
        if path is None or not path.exists():
            self.window.finalize_spotlight.show_error(f"No MTDA output is available for {prefix}.")
            return
        for member in member_candidates:
            candidate = _extract_archive_member_group(path, prefix, member)
            if candidate is not None and candidate.exists():
                self._open_local_path(candidate)
                return
        target = _extract_archive_prefix(path, prefix)
        for name in preferred_names:
            candidate = target / name
            if candidate.exists():
                self._open_local_path(candidate)
                return
        html_files = sorted(target.glob("*.html"))
        if html_files:
            self._open_local_path(html_files[0])

    @staticmethod
    def _open_local_path(path: Path) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

    def _review_final_report_count(self) -> int:
        summary = _acceptance_counts(self.state.acceptance_summary)
        base = summary.get("final_report_count") or summary.get("kept_count") or 0
        if not base:
            base = summary.get("default_selected_runs") or summary.get("accepted") or 0
        overrides = sum(
            1
            for model in self._review_models
            if self.state.acceptance_keep.get(model.run_id) is True and not _default_keep(model)
        )
        return int(base) + overrides

    def _sync_review_summary(self, *, override_count: int, missing_reason_count: int) -> None:
        summary = _acceptance_counts(self.state.acceptance_summary)
        final_count = self._review_final_report_count()
        total_runs = _int(summary.get("total_runs"), final_count + len(self._review_models))
        self.window.review_spotlight.set_summary(
            total_runs=total_runs,
            flagged_runs=len(self._review_models),
            final_runs=final_count,
            overrides=override_count,
            missing_reasons=missing_reason_count,
        )

    def _review_models_from_summary(
        self,
        summary: Any,
        *,
        evidence_by_run: dict[str, dict[str, Any]] | None = None,
    ) -> list[RunRowModel]:
        evidence_by_run = evidence_by_run or {}
        if isinstance(summary, dict):
            models = _row_models_from_acceptance_report(summary, evidence_by_run=evidence_by_run)
            if models:
                return models
            rows = summary.get("flagged_runs") or summary.get("runs") or summary.get("acceptance_rows") or []
            excluded = summary.get("excluded_runs") or []
            models = [
                _row_model_from_payload(_merge_review_evidence(row, evidence_by_run))
                for row in list(rows) + list(excluded)
                if isinstance(row, dict)
            ]
            if models:
                return models
        if isinstance(summary, list):
            models = [
                _row_model_from_payload(_merge_review_evidence(row, evidence_by_run))
                for row in summary
                if isinstance(row, dict)
            ]
            if models:
                return models
        return []

    def _acceptance_evidence_by_run(self) -> dict[str, dict[str, Any]]:
        path = _state_mtda_path(self.state)
        if path is None or not path.exists():
            return {}
        return _review_evidence_from_mtda(path)


def _default_keep(model: RunRowModel) -> bool:
    return str(model.default_call).strip().lower().startswith("keep")


def _defect_labels_for_model(model: RunRowModel) -> list[str]:
    labels = _normalised_labels(model.defect_labels)
    if labels:
        return labels
    labels = [
        _defect_label_from_plot_kind(getattr(cockpit.plot_contract, "plot_kind", ""))
        for cockpit in model.diagnostic_cockpits
    ]
    labels = _normalised_labels(labels)
    if labels:
        return labels
    if model.diagnostic_cockpit is not None:
        label = _defect_label_from_plot_kind(getattr(model.diagnostic_cockpit.plot_contract, "plot_kind", ""))
        labels = _normalised_labels([label])
    return labels or ["Acceptance finding"]


def _acceptance_counts(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    nested = summary.get("summary")
    return nested if isinstance(nested, dict) else summary


def _row_models_from_acceptance_report(
    report: dict[str, Any],
    *,
    evidence_by_run: dict[str, dict[str, Any]] | None = None,
) -> list[RunRowModel]:
    evidence_by_run = evidence_by_run or {}
    flags = report.get("flags")
    if not isinstance(flags, list):
        return []
    run_states = report.get("run_states") if isinstance(report.get("run_states"), dict) else {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        run_id = str(flag.get("run_id") or "")
        if run_id:
            grouped.setdefault(run_id, []).append(flag)

    models: list[RunRowModel] = []
    for run_id in sorted(grouped):
        run_flags = sorted(grouped[run_id], key=_acceptance_flag_rank, reverse=True)
        primary = run_flags[0]
        state = str(run_states.get(run_id) or "").lower()
        rank = _acceptance_flag_rank(primary)
        selection_effect = str(primary.get("selection_effect") or "").lower()
        if state not in {"review_required", "excluded"} and rank < 2 and "excluded" not in selection_effect:
            continue
        default_call = "Remove" if state in {"review_required", "excluded"} or "excluded" in selection_effect else "Keep"
        message = str(primary.get("message") or primary.get("reason") or "Acceptance flag requires review")
        reason = message if len(run_flags) == 1 else f"{message} (+{len(run_flags) - 1} more)"
        category = str(primary.get("category") or "acceptance")
        severity = str(primary.get("severity") or state or "review")
        evidence_refs = primary.get("evidence_refs") if isinstance(primary.get("evidence_refs"), list) else []
        refs = ", ".join(str(ref) for ref in evidence_refs[:4])
        narrative = (
            f"<b>{html.escape(category)}</b> · {html.escape(severity)}<br>"
            f"{html.escape(message)}"
            + (f"<br><span>Evidence: {html.escape(refs)}</span>" if refs else "")
        )
        payload = {
            **evidence_by_run.get(run_id, {}),
            "run_id": run_id,
            "default_call": default_call,
            "reason": reason,
            "is_excluded": state == "excluded",
            "narrative_html": narrative,
            "acceptance_flags": _acceptance_flag_details(run_flags),
            "defect_labels": _defect_labels_for_flags(run_flags),
            "evidence_kind": _evidence_kind_for_flags(run_flags),
            "diagnostic_evidence_kinds": _diagnostic_evidence_kinds_for_flags(run_flags),
        }
        curve_payload_flag = _curve_flag_payload(run_flags)
        for target, source in (
            ("curve_family_metric", "metric"),
            ("curve_family_value", "value"),
            ("curve_family_threshold", "threshold"),
        ):
            value = curve_payload_flag.get(source)
            if value not in (None, "") and payload.get(target) in (None, ""):
                payload[target] = value
        bending_payload_flag = _bending_flag_payload(run_flags)
        for target, source in (
            ("bending_peak", "value"),
            ("bending_threshold", "threshold"),
            ("bending_points_above_threshold", "points_above_threshold"),
            ("bending_assessed_points", "assessed_points"),
        ):
            value = bending_payload_flag.get(source)
            if value not in (None, "") and payload.get(target) in (None, ""):
                payload[target] = value
        models.append(_row_model_from_payload(payload))
    return models


def _acceptance_flag_rank(flag: dict[str, Any]) -> int:
    severity = str(flag.get("severity") or "").lower()
    if severity in {"exclude", "error", "critical", "invalid"}:
        return 3
    if severity in {"review", "warn_review", "requires_review"}:
        return 2
    if severity in {"warn", "warning"}:
        return 1
    return 0


def _acceptance_flag_details(flags: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for flag in flags:
        evidence_refs = flag.get("evidence_refs") if isinstance(flag.get("evidence_refs"), list) else []
        rows.append(
            {
                "flag_id": str(flag.get("flag_id") or ""),
                "severity": str(flag.get("severity") or "flag"),
                "category": str(flag.get("category") or "acceptance"),
                "message": str(flag.get("message") or flag.get("reason") or "Acceptance flag requires review"),
                "selection_effect": str(flag.get("selection_effect") or ""),
                "evidence_refs": "; ".join(str(ref) for ref in evidence_refs[:4]),
            }
        )
    return rows


def _defect_labels_for_flags(flags: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for flag in flags:
        if _is_bending_flag(flag):
            label = "Bending"
        elif _is_curve_family_flag(flag):
            label = "Curve shape"
        else:
            label = _title_label(flag.get("category") or flag.get("flag_id") or "acceptance finding")
        if label and label not in labels:
            labels.append(label)
    return labels


def _evidence_kind_for_flags(flags: list[dict[str, Any]]) -> str:
    kinds = _diagnostic_evidence_kinds_for_flags(flags)
    if kinds:
        return kinds[0]
    return "decision_context"


def _diagnostic_evidence_kinds_for_flags(flags: list[dict[str, Any]]) -> list[str]:
    kinds: list[str] = []
    for flag in flags:
        kind = ""
        if _is_bending_flag(flag):
            kind = "bending"
        elif _is_curve_family_flag(flag):
            kind = "curve_family"
        if kind and kind not in kinds:
            kinds.append(kind)
    return kinds


def _curve_flag_payload(flags: list[dict[str, Any]]) -> dict[str, Any]:
    for flag in flags:
        if _is_curve_family_flag(flag):
            return flag
    return {}


def _bending_flag_payload(flags: list[dict[str, Any]]) -> dict[str, Any]:
    for flag in flags:
        if _is_bending_flag(flag):
            return flag
    return {}


def _flag_signature(flag: dict[str, Any]) -> str:
    refs = flag.get("evidence_refs") if isinstance(flag.get("evidence_refs"), list) else []
    text = " ".join(
        str(value)
        for value in (
            flag.get("category"),
            flag.get("source"),
            flag.get("rule_id"),
            flag.get("flag_id"),
            flag.get("message"),
            flag.get("reason"),
            flag.get("severity"),
            flag.get("metric"),
            flag.get("value"),
        )
        if value not in (None, "")
    )
    refs_text = " ".join(str(ref) for ref in refs)
    return " ".join((text + " " + refs_text).replace("_", " ").replace("-", " ").casefold().split())


def _is_curve_family_flag(flag: dict[str, Any]) -> bool:
    text = _flag_signature(flag)
    return (
        "curve family" in text
        or "curve shape" in text
        or "curvefamily" in text
        or "acceptance/curve family/" in text
    )


def _is_bending_flag(flag: dict[str, Any]) -> bool:
    text = _flag_signature(flag)
    message = str(flag.get("message") or flag.get("reason") or flag.get("value") or "").replace("-", " ").replace("_", " ").casefold()
    return (
        "bending" in text
        or "opposite face strain" in text
        or "sustained" in text
        or "persist" in text
        or "bending" in message
    )


def _defect_labels_from_payload(row: dict[str, Any], diagnostic_cockpits: list[Any]) -> list[str]:
    labels = row.get("defect_labels")
    if isinstance(labels, (list, tuple)):
        explicit = _normalised_labels([str(label) for label in labels])
        if explicit:
            return explicit
    flags = [dict(flag) for flag in (row.get("acceptance_flags") or []) if isinstance(flag, dict)]
    if flags:
        from_flags = _normalised_labels(_defect_labels_for_flags(flags))
        if from_flags:
            return from_flags
    from_cockpits = _normalised_labels(
        [
            _defect_label_from_plot_kind(getattr(cockpit.plot_contract, "plot_kind", ""))
            for cockpit in diagnostic_cockpits
        ]
    )
    if from_cockpits:
        return from_cockpits
    evidence_kind = str(row.get("evidence_kind") or "")
    return _normalised_labels([_defect_label_from_evidence_kind(evidence_kind)]) or ["Acceptance finding"]


def _defect_label_from_plot_kind(plot_kind: str) -> str:
    kind = str(plot_kind or "").casefold()
    if kind == "bending_evidence":
        return "Bending"
    if kind == "curve_family":
        return "Curve shape"
    return _title_label(kind or "acceptance finding")


def _defect_label_from_evidence_kind(evidence_kind: str) -> str:
    kind = str(evidence_kind or "").casefold()
    if kind == "bending":
        return "Bending"
    if kind == "curve_family":
        return "Curve shape"
    return _title_label(kind or "acceptance finding")


def _normalised_labels(labels: list[str]) -> list[str]:
    normalised: list[str] = []
    for label in labels:
        text = str(label or "").strip()
        if text and text not in normalised:
            normalised.append(text)
    return normalised


def _title_label(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Acceptance finding"
    return " ".join(part.capitalize() for part in text.split())


def _state_mtda_path(state: MethodRunWizardState) -> Path | None:
    if state.output_path is not None:
        return Path(state.output_path)
    if isinstance(state.service_result, dict):
        path = state.service_result.get("mtda_path") or state.service_result.get("output_path")
        if path:
            return Path(str(path))
    return None


def _run_status_counts(runs: dict[str, str]) -> str:
    counts: dict[str, int] = {}
    for status in runs.values():
        key = str(status).lower()
        counts[key] = counts.get(key, 0) + 1
    order = ("running", "done", "completed", "queued", "failed", "cancelled")
    parts = [f"{counts[key]} {key}" for key in order if counts.get(key)]
    parts.extend(f"{count} {key}" for key, count in sorted(counts.items()) if key not in order)
    return ", ".join(parts) if parts else "no rows"


def _display_path(path: Path | str | None, fallback: str) -> str:
    if path is None:
        return fallback
    return Path(path).name


def _lookup_nested_int(*containers: dict[str, Any], key: str) -> int | None:
    for container in containers:
        value = container.get(key)
        if value not in (None, ""):
            return _int(value, 0)
        for nested_key in ("summary", "readiness_summary", "mapping_summary", "report_summary"):
            nested = container.get(nested_key)
            if isinstance(nested, dict):
                value = nested.get(key)
                if value not in (None, ""):
                    return _int(value, 0)
    return None


def _binding_labels(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [f"{source} → {target}" for source, target in value.items()]
    if isinstance(value, (list, tuple)):
        labels: list[str] = []
        for item in value:
            if isinstance(item, dict):
                source = (
                    item.get("source")
                    or item.get("from")
                    or item.get("field")
                    or item.get("input")
                    or item.get("method_field")
                )
                target = (
                    item.get("target")
                    or item.get("to")
                    or item.get("resolution")
                    or item.get("output")
                    or item.get("mapped_source")
                )
                if source and target:
                    labels.append(f"{source} → {target}")
                elif source:
                    labels.append(str(source))
            elif item:
                labels.append(str(item))
        return labels
    return []


def _field_rows(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return [(str(field), str(example or "")) for field, example in value.items()]
    if isinstance(value, (list, tuple)):
        rows: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                field = item.get("field") or item.get("name") or item.get("key") or item.get("source")
                example = item.get("example") or item.get("example_value") or item.get("value") or ""
                if field:
                    rows.append((str(field), str(example)))
            elif item:
                rows.append((str(item), ""))
        return rows
    return []


def _missing_field_count(state: MethodRunWizardState) -> int:
    result = state.service_result if isinstance(state.service_result, dict) else {}
    report_summary = result.get("report_summary") if isinstance(result.get("report_summary"), dict) else {}
    for key in (
        "missing_field_count",
        "recommended_missing_count",
        "missing_report_field_count",
    ):
        value = result.get(key, report_summary.get(key))
        if value not in (None, ""):
            return _int(value, 0)
    return 0


def _amendment_count(state: MethodRunWizardState) -> int:
    result = state.service_result if isinstance(state.service_result, dict) else {}
    return _int(result.get("report_override_count"), len(state.report_overrides))


def _reviewer_note_count(state: MethodRunWizardState) -> int:
    return 1 if state.finalize_note.strip() else 0


def _extract_archive_prefix(path: Path, prefix: str) -> Path:
    normalized_prefix = str(prefix).strip("/")
    target_key = normalized_prefix or "mtda_browser"
    target = Path(tempfile.gettempdir()) / f"compression_module_{target_key}" / path.stem
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            member_prefix = f"{normalized_prefix}/" if normalized_prefix else ""
            if member.endswith("/") or (member_prefix and not member.startswith(member_prefix)):
                continue
            relative = PurePosixPath(member[len(member_prefix):] if member_prefix else member)
            if not _safe_archive_relative_path(relative):
                continue
            destination = target.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as handle:
                shutil.copyfileobj(source, handle)
    return target


def _extract_mtda_browser_index(path: Path) -> Path | None:
    try:
        target = _extract_archive_prefix(path, "")
    except (OSError, zipfile.BadZipFile):
        return None
    index = target / MTDAAlignedLayout.index
    return index if index.exists() else None


def _extract_archive_member_group(path: Path, target_key: str, member: str) -> Path | None:
    target = Path(tempfile.gettempdir()) / f"compression_module_{target_key}" / path.stem
    member_path = PurePosixPath(member)
    member_parent = str(member_path.parent)
    member_prefix = "" if member_parent == "." else f"{member_parent}/"
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if member not in names:
                return None
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                if name.endswith("/") or not name.startswith(member_prefix):
                    continue
                relative_name = name[len(member_prefix):] if member_prefix else name
                relative = PurePosixPath(relative_name)
                if not _safe_archive_relative_path(relative):
                    continue
                destination = target.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, destination.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
    except (OSError, zipfile.BadZipFile):
        return None
    candidate = target.joinpath(*PurePosixPath(member_path.name).parts)
    return candidate if candidate.exists() else None


def _mtda_zip_view_path(path: Path) -> Path | None:
    if not zipfile.is_zipfile(path):
        return None
    target = Path(tempfile.gettempdir()) / "compression_module_mtda_zip_view" / path.stem / f"{path.name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        try:
            target.chmod(0o666)
        except OSError:
            pass
        target.unlink()
    shutil.copy2(path, target)
    try:
        target.chmod(0o444)
    except OSError:
        pass
    return target


def _safe_archive_relative_path(path: PurePosixPath) -> bool:
    return bool(path.parts) and all(part not in {"", ".", ".."} for part in path.parts)


def _review_evidence_from_mtda(path: Path) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            individual_rows = _csv_member_rows(archive, "report/individual_results.csv")
            if not individual_rows:
                individual_rows = _csv_member_rows(archive, "dataset/03_aggregate/results_table.csv")
            distribution_rows = _csv_member_rows(archive, "report/bending_distribution_summary.csv")
            if not distribution_rows:
                distribution_rows = _csv_member_rows(archive, "dataset/03_aggregate/bending_summary_table.csv")
            curve_family_rows = _csv_member_rows(archive, "acceptance/curve_family/aligned_curve_family.csv")
            curve_family_reference_rows = _csv_member_rows(archive, "acceptance/curve_family/reference_curves.csv")
            curve_family_score_rows = _csv_member_rows(archive, "acceptance/curve_family/curve_family_scores.csv")
            reduce_summary = _json_member(archive, "audit/reduce_summary.json")
            audit_plot_evidence = _review_evidence_from_audit_plot_specs(archive)
            method_outputs = _json_member(archive, "metadata/software/method_outputs.json")
    except (OSError, zipfile.BadZipFile):
        return {}

    final_rows = [row for row in individual_rows if _truthy(row.get("final_included"))]
    if not final_rows:
        final_rows = [row for row in individual_rows if _truthy(row.get("included_in_selection"))]
    mean_load = _mean(_optional_float(row.get("max_load_N")) for row in final_rows)
    mean_modulus_gpa = _mean(
        _mpa_to_gpa(_optional_float(row.get("compressive_modulus_MPa")))
        for row in final_rows
    )

    for row in individual_rows:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        item = evidence.setdefault(run_id, {})
        item.update(_review_evidence_from_individual_row(row))
        item["kept_mean_load"] = mean_load
        item["kept_mean_modulus"] = mean_modulus_gpa

    for row in distribution_rows:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        evidence.setdefault(run_id, {}).update(_review_evidence_from_distribution_row(row))

    runs = reduce_summary.get("runs") if isinstance(reduce_summary.get("runs"), dict) else {}
    for run_id, payload in runs.items():
        if isinstance(payload, dict):
            evidence.setdefault(str(run_id), {}).update(_review_evidence_from_reduce_payload(payload))

    for run_id, payload in audit_plot_evidence.items():
        evidence.setdefault(run_id, {}).update(payload)

    curve_family_evidence = _review_curve_family_evidence(
        curve_family_rows,
        curve_family_reference_rows,
        curve_family_score_rows,
    )
    for run_id, payload in curve_family_evidence.items():
        evidence.setdefault(run_id, {}).update(payload)

    for run_id, payload in _review_evidence_from_method_outputs(method_outputs).items():
        evidence.setdefault(run_id, {}).update(payload)

    for item in evidence.values():
        item["has_bending_evidence"] = bool(
            item.get("bending_series")
            or item.get("bending_trace_points")
            or item.get("bending_peak") is not None
            or item.get("bending_points_above_threshold") is not None
        )
    return evidence


def _review_evidence_from_method_outputs(method_outputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(method_outputs, dict):
        return {}
    evidence: dict[str, dict[str, Any]] = {}
    specimen_rows = [
        dict(row)
        for row in method_outputs.get("specimen_results", [])
        if isinstance(row, dict)
    ]
    final_rows = [
        dict(row)
        for row in method_outputs.get("final_report_runs", [])
        if isinstance(row, dict) and _truthy(row.get("final_included", row.get("included", True)))
    ]
    if not final_rows:
        final_rows = [row for row in specimen_rows if str(row.get("validity") or "").casefold() != "rejected"]
    mean_load = _mean(_optional_float(row.get("max_load_N")) for row in final_rows)
    mean_modulus_gpa = _mean(
        _mpa_to_gpa(_optional_float(row.get("compressive_modulus_MPa")))
        for row in final_rows
    )
    trace_rows_by_run = _method_output_curve_rows_by_run(method_outputs)
    diagnostic_by_run = _method_output_bending_diagnostic_by_run(method_outputs)
    for row in specimen_rows:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        item = evidence.setdefault(run_id, {})
        item.update(_review_evidence_from_individual_row(row))
        if run_id in diagnostic_by_run:
            item.update(_review_evidence_from_bending_diagnostic(diagnostic_by_run[run_id]))
        item["kept_mean_load"] = mean_load
        item["kept_mean_modulus"] = mean_modulus_gpa
        trace_payload = _bending_trace_payload(row, trace_rows_by_run.get(run_id, []))
        if trace_payload:
            item.update(trace_payload)

    operation_trace = method_outputs.get("operation_trace") if isinstance(method_outputs.get("operation_trace"), dict) else {}
    score_rows = _method_output_score_rows(method_outputs)
    curve_family_rows = _curve_rows_with_scored_runs(
        _list_of_dicts(
            operation_trace.get("curve_family_aligned_rows")
            or method_outputs.get("curve_family_aligned_rows")
        ),
        _list_of_dicts(
            method_outputs.get("bounded_curve_family")
            or operation_trace.get("bounded_curve_family")
            or method_outputs.get("curve_family")
            or operation_trace.get("curve_family")
        ),
        score_rows,
    )
    if not curve_family_rows:
        curve_family_rows = _list_of_dicts(
            operation_trace.get("curve_family_aligned_rows")
            or method_outputs.get("curve_family_aligned_rows")
            or method_outputs.get("bounded_curve_family")
            or method_outputs.get("curve_family")
        )
    reference_rows = _list_of_dicts(operation_trace.get("curve_family_reference_rows") or method_outputs.get("curve_family_reference_rows"))
    for run_id, payload in _review_curve_family_evidence(curve_family_rows, reference_rows, score_rows).items():
        evidence.setdefault(run_id, {}).update(payload)
    for run_id, payload in _curve_score_only_evidence(score_rows).items():
        evidence.setdefault(run_id, {}).update(payload)
    return evidence


def _method_output_curve_rows_by_run(method_outputs: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    operation_trace = method_outputs.get("operation_trace") if isinstance(method_outputs.get("operation_trace"), dict) else {}
    by_run = operation_trace.get("curve_rows_by_run")
    if isinstance(by_run, dict):
        return {
            str(run_id): [dict(row) for row in rows if isinstance(row, dict)]
            for run_id, rows in by_run.items()
            if isinstance(rows, list)
        }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in _list_of_dicts(method_outputs.get("bounded_curve_family") or method_outputs.get("curve_family")):
        run_id = str(row.get("run_id") or "")
        if run_id:
            grouped.setdefault(run_id, []).append(row)
    return grouped


def _method_output_bending_diagnostic_by_run(method_outputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operation_trace = method_outputs.get("operation_trace") if isinstance(method_outputs.get("operation_trace"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for row in _list_of_dicts(operation_trace.get("operations")):
        if str(row.get("operation_type") or row.get("operation") or "") != "bending_diagnostic":
            continue
        run_id = str(row.get("run_id") or "")
        outputs = row.get("outputs") if isinstance(row.get("outputs"), dict) else {}
        diagnostic = outputs.get("bending_diagnostic") if isinstance(outputs.get("bending_diagnostic"), dict) else {}
        if run_id and diagnostic:
            out[run_id] = diagnostic
    return out


def _method_output_score_rows(method_outputs: dict[str, Any]) -> list[dict[str, Any]]:
    operation_trace = method_outputs.get("operation_trace") if isinstance(method_outputs.get("operation_trace"), dict) else {}
    sources = (
        operation_trace.get("curve_family_scores"),
        method_outputs.get("curve_family_scores"),
        operation_trace.get("curve_shape_diagnostic_scores"),
        method_outputs.get("curve_shape_diagnostic_scores"),
    )
    by_run: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for source in sources:
        for row in _list_of_dicts(source):
            run_id = str(row.get("run_id") or "")
            if not run_id:
                continue
            if run_id not in by_run:
                by_run[run_id] = {}
                order.append(run_id)
            by_run[run_id].update(row)
    return [by_run[run_id] for run_id in order]


def _curve_rows_with_scored_runs(
    primary_rows: list[dict[str, Any]],
    fallback_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not primary_rows:
        return fallback_rows
    primary_run_ids = {str(row.get("run_id") or "") for row in primary_rows if row.get("run_id")}
    scored_run_ids = {str(row.get("run_id") or "") for row in score_rows if row.get("run_id")}
    missing_run_ids = scored_run_ids - primary_run_ids
    if not missing_run_ids:
        return primary_rows
    extended = list(primary_rows)
    extended.extend(row for row in fallback_rows if str(row.get("run_id") or "") in missing_run_ids)
    return extended


def _bending_trace_payload(specimen_row: dict[str, Any], curve_rows: list[dict[str, Any]]) -> dict[str, Any]:
    threshold = _optional_float(specimen_row.get("bending_threshold_percent"))
    max_load = _optional_float(specimen_row.get("max_load_N"))
    trace_points: list[dict[str, Any]] = []
    for row in curve_rows:
        load = _optional_float(row.get("load_N"))
        bending = _bending_percent_from_curve_row(row)
        if load is None or bending is None:
            continue
        trace_points.append(
            {
                "load_N": load,
                "bending_percent": bending,
                "point_index": _optional_int(row.get("point_index")),
            }
        )
    if not trace_points:
        return {}
    lower = max_load * 0.1 if max_load is not None else None
    upper = max_load * 0.9 if max_load is not None else None
    payload: dict[str, Any] = {
        "bending_trace_points": _downsample_trace_points(trace_points, limit=360),
        "bending_series": _downsample_numbers([point["bending_percent"] for point in trace_points], limit=60),
        "bending_assessment_window": (lower, upper),
        "has_bending_evidence": True,
    }
    if threshold is not None:
        payload["bending_threshold"] = threshold
        payload["bending_exceedance_segments"] = _bending_exceedance_segments(trace_points, threshold, lower, upper)
    return payload


def _bending_percent_from_curve_row(row: dict[str, Any]) -> float | None:
    if row.get("bending_percent") not in (None, ""):
        return _optional_float(row.get("bending_percent"))
    front = _first_optional_float(row, "front_strain_abs", "front_strain_oriented", "front_strain", "front_strain_raw")
    rear = _first_optional_float(row, "rear_strain_abs", "rear_strain_oriented", "rear_strain", "rear_strain_raw")
    if front is None or rear is None:
        return None
    denominator = abs(front + rear)
    if denominator == 0:
        return None
    return abs(front - rear) / denominator * 100.0


def _bending_exceedance_segments(
    trace_points: list[dict[str, Any]],
    threshold: float,
    lower: float | None,
    upper: float | None,
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    start: dict[str, Any] | None = None
    previous: dict[str, Any] | None = None
    for point in trace_points:
        load = _optional_float(point.get("load_N"))
        value = _optional_float(point.get("bending_percent"))
        in_window = (
            load is not None
            and (lower is None or load >= lower)
            and (upper is None or load <= upper)
        )
        above = bool(in_window and value is not None and value > threshold)
        if above and start is None:
            start = point
        if not above and start is not None and previous is not None:
            segments.append(_segment_record(start, previous))
            start = None
        if above:
            previous = point
    if start is not None and previous is not None:
        segments.append(_segment_record(start, previous))
    return segments


def _segment_record(start: dict[str, Any], end: dict[str, Any]) -> dict[str, Any]:
    return {
        "start_load_N": start.get("load_N"),
        "end_load_N": end.get("load_N"),
        "start_point_index": start.get("point_index"),
        "end_point_index": end.get("point_index"),
    }


def _downsample_trace_points(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if len(rows) <= limit:
        return rows
    step = max(1, len(rows) // limit)
    sampled = rows[::step]
    if sampled[-1] != rows[-1]:
        sampled.append(rows[-1])
    return sampled[:limit]


def _downsample_numbers(values: list[float], *, limit: int) -> list[float]:
    if len(values) <= limit:
        return values
    step = max(1, len(values) // limit)
    sampled = values[::step]
    if sampled[-1] != values[-1]:
        sampled.append(values[-1])
    return sampled[:limit]


def _curve_score_only_evidence(score_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for score in score_rows:
        run_id = str(score.get("run_id") or "")
        if not run_id:
            continue
        metric, value = _primary_curve_family_metric(score)
        evidence[run_id] = {
            "evidence_kind": "curve_family",
            "curve_family_metric": metric,
            "curve_family_value": value,
            "curve_family_threshold": _first_optional_float(score, "threshold", "threshold_value"),
            "curve_family_outlier_limit": _first_optional_float(score, "Qcrit_95", "critical_value"),
            "curve_family_robust_threshold": _first_optional_float(score, "threshold_value", "robust_threshold"),
            "curve_family_rank": str(score.get("distance_rank") or score.get("rank") or ""),
            "curve_family_classification": str(score.get("classification") or score.get("diagnostic_classification") or ""),
            "curve_family_reason": str(score.get("primary_reason") or score.get("distance_note") or score.get("Qcrit_note") or ""),
            "curve_family_masking_risk": score.get("masking_risk"),
            "curve_family_robust_z": _first_optional_float(score, "robust_z", "z_mad", "z_mad_upper"),
            "curve_family_dixon_decision": str(score.get("dixon_decision") or ""),
        }
    return evidence


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _review_curve_family_evidence(
    curve_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    points = _curve_family_points_from_rows(curve_rows)
    if not points:
        return {}
    references = _curve_family_reference_points_from_rows(reference_rows)
    scores_by_run = {str(row.get("run_id") or ""): row for row in score_rows if str(row.get("run_id") or "")}
    run_ids = sorted({str(row.get("run_id") or "") for row in points if row.get("run_id")})
    evidence: dict[str, dict[str, Any]] = {}
    for run_id in run_ids:
        score = scores_by_run.get(run_id, {})
        metric, value = _primary_curve_family_metric(score)
        evidence[run_id] = {
            "evidence_kind": "curve_family",
            "curve_family_points": points,
            "curve_family_reference_points": references,
            "curve_family_focus_run_id": run_id,
            "curve_family_metric": metric,
            "curve_family_value": value,
            "curve_family_threshold": _first_optional_float(score, "threshold", "threshold_value"),
            "curve_family_outlier_limit": _first_optional_float(score, "Qcrit_95", "critical_value"),
            "curve_family_robust_threshold": _first_optional_float(score, "threshold_value", "robust_threshold"),
            "curve_family_rank": str(score.get("distance_rank") or ""),
            "curve_family_classification": str(score.get("classification") or score.get("diagnostic_classification") or ""),
            "curve_family_reason": str(score.get("primary_reason") or score.get("distance_note") or score.get("Qcrit_note") or ""),
            "curve_family_masking_risk": score.get("masking_risk"),
            "curve_family_robust_z": _first_optional_float(score, "robust_z", "z_mad", "z_mad_upper"),
            "curve_family_dixon_decision": str(score.get("dixon_decision") or ""),
        }
    return evidence


def _curve_family_points_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for row in rows:
        run_id = str(row.get("run_id") or "")
        x_value = _first_optional_float(row, "x_common", "experiment_progress", "strain_percent", "strain_mm_per_mm")
        stress = _first_optional_float(row, "y_observed", "y_aligned", "stress_MPa")
        if not run_id or x_value is None or stress is None:
            continue
        points.append({"run_id": run_id, "x": _x_common_display_value(x_value), "stress": stress})
    return points


def _curve_family_reference_points_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for row in rows:
        x_value = _optional_float(row.get("x_common"))
        stress = _optional_float(row.get("y_reference"))
        if x_value is None or stress is None:
            continue
        points.append({"x": _x_common_display_value(x_value), "stress": stress})
    return points


def _primary_curve_family_metric(row: dict[str, Any]) -> tuple[str, float | None]:
    if row.get("diagnostic_classification") or row.get("distance_rms") not in (None, ""):
        value = _optional_float(row.get("distance_rms"))
        if value is not None:
            return "distance_rms", value
    for key in ("normalized_rmse", "derivative_rmse", "leave_one_out_mean_shift", "curve_correlation", "distance_rms"):
        value = _optional_float(row.get(key))
        if value is not None:
            return key, value
    return "", None


def _first_optional_float(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _optional_float(row.get(key))
        if value is not None:
            return value
    return None


def _x_common_display_value(value: float) -> float:
    return value * 100.0 if abs(value) <= 1.5 else value


def _csv_member_rows(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    if member not in archive.namelist():
        return []
    text = archive.read(member).decode("utf-8-sig")
    return [dict(row) for row in csv.DictReader(text.splitlines())]


def _json_member(archive: zipfile.ZipFile, member: str) -> dict[str, Any]:
    if member not in archive.namelist():
        return {}
    payload = json.loads(archive.read(member).decode("utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _text_member(archive: zipfile.ZipFile, member: str) -> str:
    if member not in archive.namelist():
        return ""
    return archive.read(member).decode("utf-8-sig", errors="replace")


def _review_evidence_from_audit_plot_specs(archive: zipfile.ZipFile) -> dict[str, dict[str, Any]]:
    specs = _embedded_audit_specs(_text_member(archive, "audit/audit_report.html"))
    if not specs:
        specs = _embedded_audit_specs(_text_member(archive, "dataset/04_reports/audit_report.html"))
    evidence: dict[str, dict[str, Any]] = {}
    suffix = "_bending_evidence_plot"
    for spec_id, spec in specs.items():
        if not spec_id.startswith("run_") or not spec_id.endswith(suffix) or not isinstance(spec, dict):
            continue
        run_id = spec_id[len("run_") : -len(suffix)]
        trace_points = _plot_layer_values(spec, "bending percent series outside assessment window")
        if not trace_points:
            trace_points = _plot_layer_values(spec, "bending percent series")
        threshold_values = _plot_layer_values(spec, "threshold line")
        threshold = _optional_float(threshold_values[0].get("threshold")) if threshold_values else None
        window_values = _plot_layer_values(spec, "10-90% window")
        window: tuple[float | None, float | None] = (None, None)
        if window_values:
            window = (
                _optional_float(window_values[0].get("x1")),
                _optional_float(window_values[0].get("x2")),
            )
        segments = _plot_layer_values(spec, "exceedance segments")
        if trace_points:
            evidence[run_id] = {
                "bending_trace_points": trace_points,
                "bending_threshold": threshold,
                "bending_assessment_window": window,
                "bending_exceedance_segments": segments,
                "has_bending_evidence": True,
            }
    return evidence


def _embedded_audit_specs(html_text: str) -> dict[str, Any]:
    token = "const specs = "
    start = html_text.find(token)
    if start < 0:
        return {}
    index = start + len(token)
    while index < len(html_text) and html_text[index].isspace():
        index += 1
    if index >= len(html_text) or html_text[index] != "{":
        return {}
    depth = 0
    in_string = False
    escape = False
    for end in range(index, len(html_text)):
        char = html_text[end]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    payload = json.loads(html_text[index : end + 1])
                except json.JSONDecodeError:
                    return {}
                return payload if isinstance(payload, dict) else {}
    return {}


def _plot_layer_values(spec: dict[str, Any], name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    layers = spec.get("layer") if isinstance(spec.get("layer"), list) else []
    for layer in layers:
        if not isinstance(layer, dict) or layer.get("name") != name:
            continue
        data = layer.get("data") if isinstance(layer.get("data"), dict) else {}
        values = data.get("values") if isinstance(data.get("values"), list) else []
        out.extend(dict(value) for value in values if isinstance(value, dict))
    return out


def _review_evidence_from_individual_row(row: dict[str, Any]) -> dict[str, Any]:
    modulus = _mpa_to_gpa(_optional_float(row.get("compressive_modulus_MPa")))
    pattern = str(row.get("bending_pattern") or "")
    reason = str(row.get("bending_pattern_reason") or "")
    return {
        "bending_peak": _optional_float(row.get("bending_max_percent")),
        "bending_threshold": _optional_float(row.get("bending_threshold_percent")),
        "bending_points_above_threshold": _optional_int(row.get("bending_points_above_threshold")),
        "bending_assessed_points": _optional_int(row.get("bending_point_count")),
        "bending_fraction_above_threshold": _optional_float(row.get("bending_fraction_above_threshold")),
        "bending_longest_segment_points": _optional_int(row.get("bending_longest_segment_points")),
        "bending_longest_segment_fraction": _optional_float(row.get("bending_longest_segment_fraction")),
        "bending_longest_segment_classification": str(row.get("bending_longest_segment_classification") or ""),
        "bending_classification": pattern,
        "peak_load_N": _optional_float(row.get("max_load_N")),
        "modulus_GPa": modulus,
        "failure_mode": str(row.get("failure_mode") or row.get("primary_failure_mode") or pattern or ""),
        "bending_pattern_reason": reason,
    }


def _review_evidence_from_bending_diagnostic(diagnostic: dict[str, Any]) -> dict[str, Any]:
    longest = diagnostic.get("longest_segment") if isinstance(diagnostic.get("longest_segment"), dict) else {}
    pattern = diagnostic.get("pattern") if isinstance(diagnostic.get("pattern"), dict) else {}
    return {
        "bending_peak": _optional_float(diagnostic.get("max_bending_percent")),
        "bending_threshold": _optional_float(diagnostic.get("threshold_percent")),
        "bending_points_above_threshold": _optional_int(diagnostic.get("points_above_threshold")),
        "bending_assessed_points": _optional_int(diagnostic.get("point_count")),
        "bending_fraction_above_threshold": _optional_float(diagnostic.get("fraction_above_threshold")),
        "bending_longest_segment_points": _optional_int(longest.get("point_count")),
        "bending_longest_segment_fraction": _optional_float(longest.get("fraction_of_window")),
        "bending_longest_segment_classification": str(longest.get("segment_classification") or ""),
        "bending_classification": str(diagnostic.get("pattern_classification") or pattern.get("classification") or ""),
        "bending_pattern_reason": str(diagnostic.get("pattern_reason") or pattern.get("reason") or ""),
    }


def _review_evidence_from_distribution_row(row: dict[str, Any]) -> dict[str, Any]:
    series = [
        _optional_float(row.get(key))
        for key in (
            "min_bending_percent",
            "q1_bending_percent",
            "median_bending_percent",
            "q3_bending_percent",
            "p95_bending_percent",
            "max_bending_percent",
        )
    ]
    return {
        "bending_series": [value for value in series if value is not None],
        "bending_threshold": _optional_float(row.get("threshold_percent")),
        "bending_points_above_threshold": _optional_int(row.get("points_above_threshold")),
        "bending_assessed_points": _optional_int(row.get("assessed_point_count") or row.get("point_count")),
        "bending_fraction_above_threshold": _optional_float(row.get("fraction_above_threshold")),
    }


def _review_evidence_from_reduce_payload(payload: dict[str, Any]) -> dict[str, Any]:
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    bending = diagnostics.get("bending_diagnostic") if isinstance(diagnostics.get("bending_diagnostic"), dict) else {}
    outputs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {}
    max_load = outputs.get("max_load_N") if isinstance(outputs.get("max_load_N"), dict) else {}
    modulus = outputs.get("compressive_modulus_MPa") if isinstance(outputs.get("compressive_modulus_MPa"), dict) else {}
    return {
        "bending_peak": _optional_float(bending.get("max_bending_percent")),
        "bending_threshold": _optional_float(bending.get("threshold_percent")),
        "bending_points_above_threshold": _optional_int(bending.get("points_above_threshold")),
        "bending_assessed_points": _optional_int(bending.get("point_count")),
        "bending_fraction_above_threshold": _optional_float(bending.get("fraction_above_threshold")),
        "bending_longest_segment_points": _longest_segment_point_count(bending),
        "bending_longest_segment_fraction": _longest_segment_fraction(bending),
        "bending_longest_segment_classification": _longest_segment_classification(bending),
        "bending_classification": str(
            bending.get("pattern_classification")
            or (bending.get("pattern") or {}).get("classification")
            if isinstance(bending.get("pattern"), dict)
            else bending.get("pattern_classification") or ""
        ),
        "peak_load_N": _optional_float(max_load.get("value")),
        "modulus_GPa": _mpa_to_gpa(_optional_float(modulus.get("value"))),
        "bending_pattern_reason": str(bending.get("pattern_reason") or ""),
    }


def _merge_review_evidence(row: dict[str, Any], evidence_by_run: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run_id = str(row.get("run_id") or row.get("id") or row.get("run") or "")
    if not run_id:
        return dict(row)
    return {**evidence_by_run.get(run_id, {}), **row}


def _row_model_from_payload(row: dict[str, Any]) -> RunRowModel:
    run_id = str(row.get("run_id") or row.get("id") or row.get("run") or "run")
    series = [_float(value, 0.0) for value in (row.get("bending_series") or row.get("series") or [])]
    threshold = _optional_float(row.get("bending_threshold"))
    peak = _optional_float(row.get("bending_peak"))
    series, threshold, peak = _normalise_bending_percent(series, threshold, peak)
    trace_points = [
        dict(point)
        for point in (row.get("bending_trace_points") or [])
        if isinstance(point, dict)
    ]
    assessment_window = row.get("bending_assessment_window")
    if isinstance(assessment_window, tuple) and len(assessment_window) == 2:
        bending_assessment_window = assessment_window
    elif isinstance(assessment_window, list) and len(assessment_window) == 2:
        bending_assessment_window = (
            _optional_float(assessment_window[0]),
            _optional_float(assessment_window[1]),
        )
    else:
        bending_assessment_window = (None, None)
    has_bending_evidence = bool(
        row.get("has_bending_evidence")
        or series
        or trace_points
        or peak is not None
        or row.get("bending_points_above_threshold") not in (None, "")
    )
    pattern_reason = str(row.get("bending_pattern_reason") or "").strip()
    narrative = str(
        row.get("narrative_html")
        or row.get("narrative")
        or "Acceptance evidence requires operator review."
    )
    if pattern_reason and pattern_reason not in narrative:
        narrative = f"{narrative}<br><span>Bending: {html.escape(pattern_reason)}</span>"
    default_call = str(row.get("default_call") or row.get("default") or "Remove")
    reason = str(row.get("reason") or row.get("diagnostic_reason") or "bending persistence exceeded threshold")
    bending_peak = peak if peak is not None else max(series) if series else None
    normalized_payload = {
        **row,
        "run_id": run_id,
        "default_call": default_call,
        "reason": reason,
        "bending_series": series,
        "bending_peak": bending_peak,
        "bending_threshold": threshold,
        "bending_trace_points": trace_points,
        "bending_assessment_window": bending_assessment_window,
        "bending_exceedance_segments": row.get("bending_exceedance_segments") or [],
        "has_bending_evidence": has_bending_evidence,
    }
    diagnostic_kinds = [
        str(kind)
        for kind in (row.get("diagnostic_evidence_kinds") or [])
        if str(kind)
    ]
    if not diagnostic_kinds:
        diagnostic_kinds = [str(normalized_payload.get("evidence_kind") or "bending")]
    diagnostic_cockpits = [
        diagnostic_cockpit_from_payload({**normalized_payload, "evidence_kind": kind})
        for kind in diagnostic_kinds
    ]
    primary_cockpit = diagnostic_cockpits[0] if diagnostic_cockpits else diagnostic_cockpit_from_payload(normalized_payload)
    defect_labels = _defect_labels_from_payload(normalized_payload, diagnostic_cockpits)
    return RunRowModel(
        run_id=run_id,
        default_call=default_call,
        reason=reason,
        is_excluded=bool(row.get("is_excluded", False)),
        bending_series=series,
        bending_peak=bending_peak,
        bending_threshold=threshold,
        bending_points_above_threshold=_optional_int(row.get("bending_points_above_threshold")),
        bending_assessed_points=_optional_int(row.get("bending_assessed_points")),
        peak_load_N=_optional_float(row.get("peak_load_N")),
        kept_mean_load=_optional_float(row.get("kept_mean_load")),
        modulus_GPa=_optional_float(row.get("modulus_GPa")),
        kept_mean_modulus=_optional_float(row.get("kept_mean_modulus")),
        failure_mode=str(row.get("failure_mode") or "valid compression failure"),
        narrative_html=narrative,
        has_bending_evidence=has_bending_evidence,
        acceptance_flags=[
            dict(flag)
            for flag in (row.get("acceptance_flags") or [])
            if isinstance(flag, dict)
        ],
        defect_labels=defect_labels,
        bending_trace_points=trace_points,
        bending_assessment_window=bending_assessment_window,
        bending_exceedance_segments=[
            dict(segment)
            for segment in (row.get("bending_exceedance_segments") or [])
            if isinstance(segment, dict)
        ],
        curve_family_points=[
            dict(point)
            for point in (row.get("curve_family_points") or [])
            if isinstance(point, dict)
        ],
        curve_family_reference_points=[
            dict(point)
            for point in (row.get("curve_family_reference_points") or [])
            if isinstance(point, dict)
        ],
        curve_family_focus_run_id=str(row.get("curve_family_focus_run_id") or ""),
        curve_family_metric=str(row.get("curve_family_metric") or ""),
        curve_family_value=_optional_float(row.get("curve_family_value")),
        curve_family_threshold=_optional_float(row.get("curve_family_threshold")),
        curve_family_rank=str(row.get("curve_family_rank") or ""),
        curve_family_classification=str(row.get("curve_family_classification") or ""),
        diagnostic_cockpit=primary_cockpit,
        diagnostic_cockpits=diagnostic_cockpits,
    )


def _longest_segment_point_count(bending: dict[str, Any]) -> int | None:
    longest = bending.get("longest_segment")
    if isinstance(longest, dict):
        return _optional_int(longest.get("point_count"))
    return None


def _longest_segment_fraction(bending: dict[str, Any]) -> float | None:
    longest = bending.get("longest_segment")
    if isinstance(longest, dict):
        return _optional_float(longest.get("fraction_of_window"))
    return None


def _longest_segment_classification(bending: dict[str, Any]) -> str:
    longest = bending.get("longest_segment")
    if isinstance(longest, dict):
        return str(longest.get("segment_classification") or "")
    return ""


def _normalise_bending_percent(
    series: list[float],
    threshold: float | None,
    peak: float | None,
) -> tuple[list[float], float | None, float | None]:
    values = list(series)
    if threshold is not None:
        values.append(threshold)
    if peak is not None:
        values.append(peak)
    if values and max(abs(value) for value in values) <= 1.5:
        return [value * 100.0 for value in series], (
            threshold * 100.0 if threshold is not None else None
        ), (
            peak * 100.0 if peak is not None else None
        )
    return series, threshold, peak


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _mean(values: Any) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _mpa_to_gpa(value: float | None) -> float | None:
    return value / 1000.0 if value is not None else None


def _truthy(value: Any) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _default_mapping_suggestions(mapping_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(mapping_summary, dict):
        return []
    blocking_fields = {str(field) for field in mapping_summary.get("blocking_fields", []) or [] if str(field)}
    if not blocking_fields:
        return []
    candidate_report = mapping_summary.get("candidate_report")
    if not isinstance(candidate_report, dict):
        return []
    suggestions: list[dict[str, Any]] = []
    used_sources: set[tuple[str, str]] = set()
    for requirement in candidate_report.get("requirements", []) or []:
        if not isinstance(requirement, dict):
            continue
        method_field = str(requirement.get("method_field") or "")
        if method_field not in blocking_fields:
            continue
        if str(requirement.get("severity") or "") != "execution_critical":
            continue
        candidate = _obvious_default_candidate(requirement)
        if candidate is None:
            continue
        source_kind = _suggestion_source_kind(candidate)
        source_name = _suggestion_source_name(candidate)
        if not source_name:
            continue
        source_key = (source_kind, source_name)
        if source_key in used_sources:
            continue
        used_sources.add(source_key)
        suggestions.append(
            {
                "method_field": method_field,
                "source_role": str(requirement.get("source_role") or method_field.rsplit(".", 1)[-1]),
                "source_kind": source_kind,
                "source_name": source_name,
                "confidence": _candidate_confidence(candidate),
                "reason": str(candidate.get("reason") or ""),
                "unit": str(candidate.get("unit") or ""),
                "coverage": str(candidate.get("coverage") or ""),
            }
        )
    return suggestions


def _obvious_default_candidate(requirement: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [candidate for candidate in requirement.get("candidates", []) or [] if isinstance(candidate, dict)]
    if not candidates:
        return None
    ranked = sorted(candidates, key=_candidate_confidence, reverse=True)
    top = ranked[0]
    top_confidence = _candidate_confidence(top)
    second_confidence = _candidate_confidence(ranked[1]) if len(ranked) > 1 else 0.0
    source_kind = _suggestion_source_kind(top)
    if top_confidence >= 0.95:
        return top
    if top_confidence >= 0.80 and top_confidence - second_confidence >= 0.10:
        return top
    if len(ranked) == 1 and source_kind == "channel" and top_confidence >= 0.78:
        return top
    return None


def _mapping_payload_with_suggestions(payload: dict[str, Any], suggestions: list[dict[str, Any]]) -> dict[str, Any]:
    repaired = normalize_mapping_profile(payload)
    mapping_id = str(repaired.get("mapping_id") or "mapping_profile")
    if not mapping_id.endswith("_wizard_edit"):
        repaired["mapping_id"] = f"{mapping_id}_wizard_edit"
    for suggestion in suggestions:
        role = str(suggestion.get("source_role") or "").strip()
        source = str(suggestion.get("source_name") or "").strip()
        if not role or not source:
            continue
        for section in ("channels", "fields", "tokens"):
            existing = repaired.get(section)
            if isinstance(existing, dict):
                existing.pop(role, None)
        section = "channels" if str(suggestion.get("source_kind") or "").casefold() == "channel" else "fields"
        target = repaired.setdefault(section, {})
        if isinstance(target, dict):
            target[role] = source
    return repaired


def _format_mapping_suggestions(suggestions: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for suggestion in suggestions[:6]:
        field = str(suggestion.get("method_field") or suggestion.get("source_role") or "method input")
        kind = str(suggestion.get("source_kind") or "source")
        source = str(suggestion.get("source_name") or "")
        confidence = _candidate_confidence(suggestion)
        detail = f"{kind}:{source}"
        if confidence:
            detail = f"{detail} ({confidence:.0%})"
        rows.append(f"- {field} -> {detail}")
    return "\n".join(rows)


def _suggestion_source_kind(candidate: dict[str, Any]) -> str:
    text = str(candidate.get("source_kind") or "").strip().casefold()
    if text in {"channel", "channels"}:
        return "channel"
    if text in {"dataset", "package"}:
        return text
    return "field"


def _suggestion_source_name(candidate: dict[str, Any]) -> str:
    source = str(candidate.get("source_name") or "").strip()
    if source:
        return source
    source = str(candidate.get("candidate_source") or candidate.get("source_path") or "").strip()
    for prefix in ("channels.", "tokens.", "fields."):
        if source.startswith(prefix):
            return source[len(prefix):]
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _candidate_confidence(candidate: dict[str, Any]) -> float:
    try:
        return float(candidate.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _default_edited_mapping_path(path: Path | str) -> Path:
    base = Path(path)
    parent = base.parent
    stem = base.stem
    candidate = parent / f"{stem}_wizard_edit.json"
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{stem}_wizard_edit_{suffix}.json"
        suffix += 1
    return candidate


def _empty_mapping_dialog_model(error: str | None = None) -> dict[str, Any]:
    headline = (
        f"Could not load the selected mapping profile: {error}. Browse for another profile or use the method default."
        if error
        else "No mapping profile is selected. Browse for a profile or use the registered method default."
    )
    return {
        "schema_name": "mapping_preview_view_model",
        "why_required": (
            "Choose a mapping profile so the wizard can compare method requirements with package data before readiness."
        ),
        "summary": {
            "execution_critical_total": 0,
            "execution_critical_mapped": 0,
            "report_fields_total": 0,
            "report_fields_mapped": 0,
            "ambiguous": 0,
        },
        "compatibility_status": "load error" if error else "not selected",
        "rows": [],
        "candidate_rows": [],
        "disambiguation_rows": [],
        "action_guidance": {
            "severity": "warn",
            "headline": headline,
        },
    }


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
