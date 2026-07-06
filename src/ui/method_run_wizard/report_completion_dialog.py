from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from archives.core.layouts import MTDAAlignedLayout, aggregate_member, metadata_member, report_member
from mtda_finalization import AmendmentRequest, MTDAFinalizationService
from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from ui.method_run_wizard._tokens import Color
from ui.method_run_wizard.components.report_dialog_helpers import (
    add_status_cards,
    choose_save_file,
    fill_named_rows_table,
    section_note,
)
from ui.method_run_wizard.view_models.report_authoring import (
    build_report_override_payload,
    filter_report_authoring_fields,
    report_authoring_view_model_from_report_payload,
    report_authoring_view_model,
)


class ReportCompletionDialog(QtWidgets.QDialog):
    """Report-only field amendment surface for an existing MTDA."""

    def __init__(self, mtda_path: str | Path, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Report Completion")
        self.resize(1040, 720)
        self.mtda_path = Path(mtda_path)
        self.result_path: Path | None = None
        self._visible_fields: list[dict[str, Any]] = []
        self._model = _authoring_model_from_mtda(self.mtda_path)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(section_note("Complete report-only metadata without changing the source MTDP package. Amendments are recorded in the MTDA ledger."))
        self.cards_holder = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_holder)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.cards_holder)
        add_status_cards(
            self.cards_layout,
            [
                {"label": "Missing Fields", "value": str(self._summary("missing_count")), "status": "warn" if self._summary("missing_count") else "pass"},
                {"label": "Required Missing", "value": str(self._summary("required_missing_count")), "status": "fail" if self._summary("required_missing_count") else "pass"},
                {"label": "Recommended Missing", "value": str(self._summary("recommended_missing_count")), "status": "warn" if self._summary("recommended_missing_count") else "pass"},
                {"label": "Overrides", "value": str(self._summary("override_count")), "status": "available" if self._summary("override_count") else "neutral"},
            ],
            columns=4,
        )

        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("Show"))
        self.filter_combo = QtWidgets.QComboBox()
        for filter_id, label in (
            ("missing", "Missing fields"),
            ("required", "Required fields"),
            ("recommended", "Recommended fields"),
            ("overridden", "Overrides"),
            ("all", "All report fields"),
        ):
            self.filter_combo.addItem(label, filter_id)
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self.fields_table = QtWidgets.QTableWidget()
        layout.addWidget(self.fields_table, 1)

        editor_group = QtWidgets.QGroupBox("Selected field amendment")
        editor_layout = QtWidgets.QGridLayout(editor_group)
        self.selected_label = QtWidgets.QLabel("Select a missing field to amend.")
        self.selected_label.setWordWrap(True)
        self.mode_combo = QtWidgets.QComboBox()
        for mode_id, label in (
            ("value", "Provide report value"),
            ("not_applicable", "Mark as not applicable"),
            ("external_required", "External information required"),
            ("not_recorded", "Not recorded in source package"),
        ):
            self.mode_combo.addItem(label, mode_id)
        self.value_edit = QtWidgets.QLineEdit()
        self.value_edit.setPlaceholderText("Enter the report value")
        self.reason_edit = QtWidgets.QLineEdit()
        self.reason_edit.setPlaceholderText("Amendment rationale required")
        self.reviewer_edit = QtWidgets.QLineEdit()
        self.reviewer_edit.setPlaceholderText("Reviewer/operator")
        self.output_edit = QtWidgets.QLineEdit(str(_default_finalized_path(self.mtda_path)))
        self.output_browse = QtWidgets.QPushButton("Browse...")
        editor_layout.addWidget(self.selected_label, 0, 0, 1, 3)
        editor_layout.addWidget(QtWidgets.QLabel("Resolution"), 1, 0)
        editor_layout.addWidget(self.mode_combo, 1, 1, 1, 2)
        editor_layout.addWidget(QtWidgets.QLabel("Value / status"), 2, 0)
        editor_layout.addWidget(self.value_edit, 2, 1, 1, 2)
        editor_layout.addWidget(QtWidgets.QLabel("Reviewer note"), 3, 0)
        editor_layout.addWidget(self.reason_edit, 3, 1, 1, 2)
        editor_layout.addWidget(QtWidgets.QLabel("Reviewer"), 4, 0)
        editor_layout.addWidget(self.reviewer_edit, 4, 1, 1, 2)
        editor_layout.addWidget(QtWidgets.QLabel("Finalized MTDA"), 5, 0)
        editor_layout.addWidget(self.output_edit, 5, 1)
        editor_layout.addWidget(self.output_browse, 5, 2)
        layout.addWidget(editor_group)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.apply_button = QtWidgets.QPushButton("Apply selected amendment and finalize")
        self.close_button = QtWidgets.QPushButton("Close")
        button_row.addWidget(self.apply_button)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.filter_combo.currentIndexChanged.connect(self._refresh_table)
        self.fields_table.itemSelectionChanged.connect(self._selection_changed)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.output_browse.clicked.connect(self._choose_output)
        self.apply_button.clicked.connect(self.apply_amendment)
        self.close_button.clicked.connect(self.reject)

        self._refresh_table()
        self._mode_changed()

    def selected_field(self) -> dict[str, Any] | None:
        row = self.fields_table.currentRow()
        if row < 0 or row >= len(self._visible_fields):
            return None
        return self._visible_fields[row]

    def apply_amendment(self, *, show_messages: bool = True) -> Path | None:
        field = self.selected_field()
        if not field:
            return self._warn("Select a report field to amend.", show_messages)
        value = self._amendment_value()
        reason = self.reason_edit.text().strip()
        reviewer = self.reviewer_edit.text().strip()
        if value in (None, ""):
            return self._warn("Enter a report value or choose a resolution status.", show_messages)
        if not reason:
            return self._warn("Enter an amendment rationale before finalizing.", show_messages)
        payload = build_report_override_payload(
            field_key=str(field.get("field_key") or ""),
            value=value,
            reason=reason,
            reviewer=reviewer,
            section=str(field.get("section_id") or ""),
            source_surface="method_run_wizard.report_completion_editor",
        )
        output_path = Path(self.output_edit.text().strip() or _default_finalized_path(self.mtda_path))
        result = MTDAFinalizationService().finalize(
            input_path=self.mtda_path,
            output_path=output_path,
            request=AmendmentRequest(
                report_overrides=(payload,),
                reviewer=reviewer,
                reason=reason,
                reviewer_notes=(reason,),
                source_surface="method_run_wizard.report_completion_editor",
            ),
        )
        if result.status != "finalized" or result.output_path is None:
            return self._warn("; ".join(result.errors) or "Finalization failed.", show_messages)
        self.result_path = result.output_path
        if show_messages:
            QtWidgets.QMessageBox.information(self, "MTDA finalized", f"Finalized MTDA written to {result.output_path}.")
        self.accept()
        return result.output_path

    def _summary(self, key: str) -> Any:
        summary = self._model.get("summary", {})
        return summary.get(key, "") if isinstance(summary, dict) else ""

    def _refresh_table(self) -> None:
        filter_id = str(self.filter_combo.currentData() or "missing")
        self._visible_fields = filter_report_authoring_fields(self._model, filter_id)
        fill_named_rows_table(
            self.fields_table,
            self._visible_fields,
            [
                ("section_title", "Section"),
                ("label", "Field"),
                ("report_importance_label", "Importance"),
                ("status_label", "Status"),
                ("guidance", "Guidance"),
            ],
            max_chars=90,
        )
        header = self.fields_table.horizontalHeader()
        for index in range(max(0, self.fields_table.columnCount() - 1)):
            header.setSectionResizeMode(index, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        if self.fields_table.columnCount():
            header.setSectionResizeMode(self.fields_table.columnCount() - 1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        if self._visible_fields:
            self.fields_table.selectRow(0)

    def _selection_changed(self) -> None:
        field = self.selected_field()
        if not field:
            self.selected_label.setText("Select a missing field to amend.")
            return
        current = field.get("current_value") or "No current value"
        reason = field.get("missing_reason") or "No missing reason recorded"
        self.selected_label.setText(
            f"<b>{field.get('label')}</b><br>"
            f"{field.get('report_importance_label')} - {field.get('guidance')}<br>"
            f"<span style='color:{Color.TEXT_2}'>Current value: {current}; missing reason: {reason}</span>"
        )
        self.value_edit.setText(str(field.get("override_value") or ""))
        self.reason_edit.setText(str(field.get("override_reason") or ""))
        self.reviewer_edit.setText(str(field.get("override_reviewer") or self.reviewer_edit.text()))
        self._mode_changed()

    def _mode_changed(self) -> None:
        mode = str(self.mode_combo.currentData() or "value")
        presets = {
            "not_applicable": "Not applicable",
            "external_required": "External information required",
            "not_recorded": "Not recorded in source package",
        }
        if mode in presets:
            self.value_edit.setText(presets[mode])
            self.value_edit.setReadOnly(True)
        else:
            if self.value_edit.text() in presets.values():
                self.value_edit.clear()
            self.value_edit.setReadOnly(False)

    def _amendment_value(self) -> str:
        return self.value_edit.text().strip()

    def _choose_output(self) -> None:
        path = choose_save_file(self, "Choose finalized MTDA", self.output_edit.text() or ".", "MTDA archives (*.mtda)")
        if path:
            self.output_edit.setText(path)

    def _warn(self, message: str, show: bool) -> None:
        if show:
            QtWidgets.QMessageBox.warning(self, "Report completion", message)
        return None


class FinalizationDialog(QtWidgets.QDialog):
    """Safe finalization confirmation for report/selection state."""

    def __init__(self, mtda_path: str | Path, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Finalize MTDA")
        self.resize(760, 460)
        self.mtda_path = Path(mtda_path)
        self.result_path: Path | None = None
        self.status = _archive_status(self.mtda_path)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(section_note("Finalize the MTDA review state without rerunning calculations or mutating the source MTDP package."))
        cards = [
            {"label": "Current State", "value": _human_archive_state(self.status.get("archive_state")), "status": "warn" if self.status.get("archive_state") == "not_finalized" else "pass"},
            {"label": "Required Missing", "value": str(self.status.get("required_missing_count", 0)), "status": "fail" if self.status.get("required_missing_count", 0) else "pass"},
            {"label": "Recommended Missing", "value": str(self.status.get("recommended_missing_count", 0)), "status": "warn" if self.status.get("recommended_missing_count", 0) else "pass"},
            {"label": "Final Report Runs", "value": str(self.status.get("final_report_run_count", 0)), "status": "pass"},
            {"label": "Amendments", "value": str(self.status.get("amendment_count", 0)), "status": "available" if self.status.get("amendment_count", 0) else "neutral"},
        ]
        self.cards_holder = QtWidgets.QWidget()
        self.cards_holder.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_holder)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.cards_holder)
        add_status_cards(self.cards_layout, cards, columns=3)
        if int(self.status.get("recommended_missing_count", 0) or 0):
            layout.addWidget(section_note("Recommended fields are still missing. You can finalize with warnings, or return to Review missing fields to record report-only amendments."))
        self.reason_edit = QtWidgets.QLineEdit()
        self.reason_edit.setPlaceholderText("Finalization rationale required")
        self.reviewer_edit = QtWidgets.QLineEdit()
        self.reviewer_edit.setPlaceholderText("Reviewer/operator")
        self.output_edit = QtWidgets.QLineEdit(str(_default_finalized_path(self.mtda_path)))
        self.output_browse = QtWidgets.QPushButton("Browse...")
        form = QtWidgets.QGridLayout()
        form.addWidget(QtWidgets.QLabel("Reviewer note"), 0, 0)
        form.addWidget(self.reason_edit, 0, 1, 1, 2)
        form.addWidget(QtWidgets.QLabel("Reviewer"), 1, 0)
        form.addWidget(self.reviewer_edit, 1, 1, 1, 2)
        form.addWidget(QtWidgets.QLabel("Finalized MTDA"), 2, 0)
        form.addWidget(self.output_edit, 2, 1)
        form.addWidget(self.output_browse, 2, 2)
        layout.addLayout(form)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.finalize_button = QtWidgets.QPushButton("Finalize MTDA")
        self.close_button = QtWidgets.QPushButton("Close")
        buttons.addWidget(self.finalize_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.output_browse.clicked.connect(self._choose_output)
        self.finalize_button.clicked.connect(self.finalize)
        self.close_button.clicked.connect(self.reject)

    def finalize(self, *, show_messages: bool = True) -> Path | None:
        if int(self.status.get("required_missing_count", 0) or 0) > 0:
            return self._warn("Required report fields remain unresolved. Finalization is blocked.", show_messages)
        reason = self.reason_edit.text().strip()
        reviewer = self.reviewer_edit.text().strip()
        if not reason:
            return self._warn("Enter a finalization rationale before finalizing.", show_messages)
        result = MTDAFinalizationService().finalize(
            input_path=self.mtda_path,
            output_path=Path(self.output_edit.text().strip() or _default_finalized_path(self.mtda_path)),
            request=AmendmentRequest(
                reviewer=reviewer,
                reason=reason,
                reviewer_notes=(reason,),
                source_surface="method_run_wizard.finalization_dialog",
            ),
        )
        if result.status != "finalized" or result.output_path is None:
            return self._warn("; ".join(result.errors) or "Finalization failed.", show_messages)
        self.result_path = result.output_path
        if show_messages:
            QtWidgets.QMessageBox.information(self, "MTDA finalized", f"Finalized MTDA written to {result.output_path}.")
        self.accept()
        return result.output_path

    def _choose_output(self) -> None:
        path = choose_save_file(self, "Choose finalized MTDA", self.output_edit.text() or ".", "MTDA archives (*.mtda)")
        if path:
            self.output_edit.setText(path)

    def _warn(self, message: str, show: bool) -> None:
        if show:
            QtWidgets.QMessageBox.warning(self, "MTDA finalization", message)
        return None


def _authoring_model_from_mtda(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if MTDAAlignedLayout.manifest in names:
            report = _json_member(archive, names, report_member("test_report.json"), default={})
            if isinstance(report, dict) and report:
                return report_authoring_view_model_from_report_payload(report)
        catalog = _json_member(archive, names, "report/report_field_catalog_resolved.json", default=[])
        overrides = _json_member(archive, names, "report/report_field_overrides.json", default={})
        values = _csv_member(archive, names, "report/report_values_used.csv")
        missing = _csv_member(archive, names, "report/missing_report_fields.csv")
    return report_authoring_view_model(
        catalog=catalog if isinstance(catalog, list) else [],
        values_used=values,
        missing_fields=missing,
        overrides=overrides if isinstance(overrides, dict) else {},
    )


def _archive_status(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if MTDAAlignedLayout.manifest in names:
            report = _json_member(archive, names, report_member("test_report.json"), default={})
            completion = report.get("report_completion_status", {}) if isinstance(report, dict) else {}
            final_runs = _csv_member(archive, names, aggregate_member("run_decision_registry.csv"))
            archive_state = _json_member(archive, names, metadata_member("finalization/archive_state.json"), default={})
            ledger = _json_member(archive, names, metadata_member("finalization/amendment_ledger.json"), default={})
        else:
            completion = _json_member(archive, names, "report/report_completion_status.json", default={})
            final_runs = _csv_member(archive, names, "acceptance/final_report_runs.csv")
            archive_state = _json_member(archive, names, "finalization/archive_state.json", default={})
            ledger = _json_member(archive, names, "finalization/amendment_ledger.json", default={})
    records = ledger.get("records", []) if isinstance(ledger, dict) and isinstance(ledger.get("records"), list) else []
    return {
        "archive_state": archive_state.get("archive_state", "not_finalized") if isinstance(archive_state, dict) else "not_finalized",
        "required_missing_count": int(completion.get("required_missing_count", 0) or 0) if isinstance(completion, dict) else 0,
        "recommended_missing_count": int(completion.get("recommended_missing_count", 0) or 0) if isinstance(completion, dict) else 0,
        "final_report_run_count": sum(1 for row in final_runs if _truthy(row.get("included", row.get("final_included", True)))),
        "amendment_count": len(records),
    }


def _json_member(archive: zipfile.ZipFile, names: set[str], member: str, default: Any = None) -> Any:
    if member not in names:
        return {} if default is None else default
    return json.loads(archive.read(member))


def _csv_member(archive: zipfile.ZipFile, names: set[str], member: str) -> list[dict[str, Any]]:
    if member not in names:
        return []
    return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _default_finalized_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.stem}_finalized{path.suffix}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_finalized_{index}{path.suffix}")
        index += 1
    return candidate


def _human_archive_state(value: Any) -> str:
    return "Finalized" if str(value) == "finalized" else "Draft, not finalized"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
