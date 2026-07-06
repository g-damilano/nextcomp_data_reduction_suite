from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from mapping import normalize_mapping_profile, write_mapping_profile
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._qss import build_global_qss
from ui.method_run_wizard._tokens import Color


class MethodMappingDialog(QtWidgets.QDialog):
    """Operator-facing editor for method mapping profiles."""

    def __init__(
        self,
        model: dict[str, Any],
        *,
        current_path: Path | None,
        default_path: Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.current_path = Path(current_path) if current_path is not None else None
        self.default_path = Path(default_path) if default_path is not None else None
        self.selected_mapping_path = self.current_path
        self._rows = sorted(
            [dict(row) for row in model.get("rows", []) if isinstance(row, dict)],
            key=_row_attention_sort_key,
        )
        self._candidate_rows = [dict(row) for row in model.get("candidate_rows", []) if isinstance(row, dict)]
        self._resolution_rows = [dict(row) for row in model.get("disambiguation_rows", []) if isinstance(row, dict)]
        self._mapping_payload = _load_mapping_payload(self.current_path) or _mapping_payload_from_model(model)
        self._dirty = False
        guidance = model.get("action_guidance") if isinstance(model.get("action_guidance"), dict) else {}
        self._can_confirm_current = bool(guidance.get("can_confirm", True))
        self._confirm_tooltip = str(guidance.get("confirm_tooltip") or "")

        self.setWindowTitle("Edit Method Mapping")
        self.setMinimumSize(1040, 680)
        self.resize(1240, 780)
        self.setStyleSheet(parent.styleSheet() if parent is not None and parent.styleSheet() else build_global_qss())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Method mapping")
        title.setObjectName("mappingDialogTitle")
        title.setStyleSheet("font-size: 17pt; font-weight: 600; background: transparent;")
        layout.addWidget(title)

        intro = QtWidgets.QLabel(str(model.get("why_required") or "Resolve method input bindings before readiness."))
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {Color.TEXT_2}; background: transparent;")
        layout.addWidget(intro)

        layout.addLayout(self._make_path_row())

        self.summary = QtWidgets.QFrame()
        self.summary.setObjectName("mappingSummary")
        self.summary_layout = QtWidgets.QHBoxLayout(self.summary)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_layout.setSpacing(8)
        self._summary_tiles: list[QtWidgets.QFrame] = []
        layout.addWidget(self.summary)

        self.guidance = QtWidgets.QLabel()
        self.guidance.setWordWrap(True)
        self.guidance.setObjectName("mappingGuidance")
        layout.addWidget(self.guidance)

        self.action_panel = self._make_action_panel(guidance)
        layout.addWidget(self.action_panel)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._make_editor_tab(), "Edit bindings")
        self.all_candidate_table = self._make_table(
            ["Method input", "Candidate source", "Kind", "Coverage", "Example", "Confidence", "Reason"],
            self._all_candidate_table_rows(),
        )
        self.tabs.addTab(self.all_candidate_table, "All candidates")
        self.resolution_table = self._make_table(
            ["Method input", "Mapped source", "Candidates", "Confidence", "Status", "Message"],
            self._resolution_table_rows(),
        )
        self.tabs.addTab(self.resolution_table, "Resolution report")
        layout.addWidget(self.tabs, 1)

        layout.addLayout(self._make_button_row())

        self._refresh_summary()
        self._refresh_guidance()
        self._refresh_accept_state()
        self._select_first_attention_row()

    def _make_path_row(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setAccessibleName("Current mapping profile path")
        self.path_edit.setText(str(self.selected_mapping_path or "No mapping profile selected"))
        self.browse_button = QtWidgets.QPushButton("Browse profile...")
        self.browse_button.setProperty("class", "subtle")
        self.browse_button.setAccessibleName("Browse for mapping profile")
        self.default_button = QtWidgets.QPushButton("Use method default")
        self.default_button.setProperty("class", "subtle")
        self.default_button.setAccessibleName("Use method default mapping profile")
        self.open_file_button = QtWidgets.QPushButton("Open profile file")
        self.open_file_button.setProperty("class", "subtle")
        self.open_file_button.setAccessibleName("Open selected mapping profile file")
        self.browse_button.clicked.connect(self._browse_profile)
        self.default_button.clicked.connect(self._use_default_profile)
        self.open_file_button.clicked.connect(self._open_profile_file)
        self.default_button.setEnabled(self.default_path is not None)
        self.open_file_button.setEnabled(self.selected_mapping_path is not None)
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_button)
        row.addWidget(self.default_button)
        row.addWidget(self.open_file_button)
        return row

    def _make_editor_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.binding_table = self._make_binding_table()
        self.binding_table.itemSelectionChanged.connect(self._on_binding_selection_changed)
        layout.addWidget(self.binding_table, 2)

        editor = QtWidgets.QFrame()
        editor.setObjectName("mappingBindingEditor")
        editor.setStyleSheet(
            f"QFrame#mappingBindingEditor {{ background: {Color.SURFACE_2}; border: 1px solid {Color.BORDER}; border-radius: 8px; }}"
        )
        editor_layout = QtWidgets.QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 10, 12, 10)
        editor_layout.setSpacing(8)

        self.editor_title = QtWidgets.QLabel("Select a method input")
        self.editor_title.setStyleSheet("font-weight: 700; font-size: 12pt; background: transparent;")
        editor_layout.addWidget(self.editor_title)

        self.editor_current = QtWidgets.QLabel("Choose a binding row to review candidates or enter a source.")
        self.editor_current.setWordWrap(True)
        self.editor_current.setStyleSheet(f"color: {Color.TEXT_2}; background: transparent;")
        editor_layout.addWidget(self.editor_current)

        candidate_label = _caps_label("Candidates for selected input")
        editor_layout.addWidget(candidate_label)
        self.candidate_table = self._make_table(
            ["Candidate", "Example", "Confidence"],
            [],
        )
        self.candidate_table.itemDoubleClicked.connect(lambda _item: self._use_selected_candidate())
        self.candidate_table.itemSelectionChanged.connect(self._on_candidate_selection_changed)
        editor_layout.addWidget(self.candidate_table, 1)

        candidate_buttons = QtWidgets.QHBoxLayout()
        self.use_candidate_button = QtWidgets.QPushButton("Use selected candidate")
        self.use_candidate_button.setProperty("class", "primary")
        self.use_candidate_button.clicked.connect(self._use_selected_candidate)
        self.clear_binding_button = QtWidgets.QPushButton("Clear binding")
        self.clear_binding_button.setProperty("class", "subtle")
        self.clear_binding_button.clicked.connect(self._clear_current_binding)
        candidate_buttons.addWidget(self.use_candidate_button)
        candidate_buttons.addWidget(self.clear_binding_button)
        editor_layout.addLayout(candidate_buttons)

        custom_label = _caps_label("Custom binding")
        editor_layout.addWidget(custom_label)
        custom_row = QtWidgets.QHBoxLayout()
        self.custom_kind = QtWidgets.QComboBox()
        self.custom_kind.addItems(["channel", "field", "dataset", "package"])
        self.custom_source = QtWidgets.QComboBox()
        self.custom_source.setEditable(True)
        self.custom_source.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.custom_source.setAccessibleName("Custom binding source suggestions")
        if self.custom_source.lineEdit() is not None:
            self.custom_source.lineEdit().setPlaceholderText("Source name, token, or dataset path")
        completer = self.custom_source.completer()
        if completer is not None:
            completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.apply_custom_button = QtWidgets.QPushButton("Apply custom")
        self.apply_custom_button.setProperty("class", "subtle")
        self.apply_custom_button.clicked.connect(self._apply_custom_binding)
        self.custom_kind.currentIndexChanged.connect(lambda _index: self._on_custom_kind_changed())
        self.custom_source.currentTextChanged.connect(lambda text: self._on_custom_source_changed(text))
        custom_row.addWidget(self.custom_kind)
        custom_row.addWidget(self.custom_source, 1)
        custom_row.addWidget(self.apply_custom_button)
        editor_layout.addLayout(custom_row)

        self.preview_label = QtWidgets.QLabel("Preview: select a candidate or enter a custom source.")
        self.preview_label.setObjectName("mappingPreview")
        self.preview_label.setWordWrap(True)
        editor_layout.addWidget(self.preview_label)

        self.consequence_label = QtWidgets.QLabel("")
        self.consequence_label.setObjectName("mappingConsequence")
        self.consequence_label.setWordWrap(True)
        editor_layout.addWidget(self.consequence_label)

        editor_layout.addStretch(1)
        layout.addWidget(editor, 2)
        return widget

    def _make_button_row(self) -> QtWidgets.QHBoxLayout:
        buttons = QtWidgets.QHBoxLayout()
        self.save_as_button = QtWidgets.QPushButton("Save profile as...")
        self.save_as_button.setProperty("class", "subtle")
        self.save_as_button.clicked.connect(self._save_as_profile)
        buttons.addWidget(self.save_as_button)
        buttons.addStretch(1)
        self.accept_button = QtWidgets.QPushButton("Use selected profile")
        self.accept_button.setProperty("class", "primary")
        self.accept_button.setAccessibleName("Use selected mapping profile")
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setProperty("class", "subtle")
        self.close_button.setAccessibleName("Close mapping editor")
        self.close_button.clicked.connect(self.reject)
        self.accept_button.clicked.connect(self._accept_current)
        buttons.addWidget(self.close_button)
        buttons.addWidget(self.accept_button)
        return buttons

    def _make_binding_table(self) -> QtWidgets.QTableWidget:
        headers = ["Status", "Req", "Method input", "Current binding", "Candidates"]
        table = QtWidgets.QTableWidget(len(self._rows), len(headers))
        table.setObjectName("mappingBindingTable")
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        for row_index in range(len(self._rows)):
            self._refresh_binding_row(row_index, table)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        for column in (0, 1, 4):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        for column in (2, 3):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.Stretch)
        return table

    def _make_action_panel(self, guidance: dict[str, Any]) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("mappingActionPanel")
        panel.setStyleSheet(
            f"QFrame#mappingActionPanel {{ border: 1px solid {Color.BORDER}; border-radius: 8px; background: {Color.SURFACE_2}; }}"
        )
        layout = QtWidgets.QGridLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(6)

        layout.addWidget(_caps_label("Next actions"), 0, 0)
        self.next_actions_list = QtWidgets.QListWidget()
        self.next_actions_list.setObjectName("mappingActionList")
        self.next_actions_list.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.next_actions_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.next_actions_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.next_actions_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        actions = guidance.get("primary_actions") if isinstance(guidance.get("primary_actions"), list) else []
        if not actions:
            actions = [guidance.get("safe_next_step") or "Resolve mapping evidence before continuing."]
        for action in actions[:3]:
            item = QtWidgets.QListWidgetItem(str(action))
            self.next_actions_list.addItem(item)
        self.next_actions_list.setMaximumHeight(86)
        layout.addWidget(self.next_actions_list, 1, 0)

        layout.addWidget(_caps_label("Issues"), 0, 1)
        issue_rows = _issue_rows(guidance)
        self.issue_table = self._make_table(["Level", "Method input"], issue_rows)
        self.issue_table.setObjectName("mappingIssueTable")
        self.issue_table.setMaximumHeight(96)
        layout.addWidget(self.issue_table, 1, 1)
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        return panel

    def _summary_cards(self) -> list[tuple[str, str, str]]:
        summary = self._computed_summary()
        compatibility = str(self.model.get("compatibility_status") or "unknown")
        return [
            (
                "critical inputs",
                f"{summary['execution_critical_mapped']}/{summary['execution_critical_total']}",
                "ok" if summary["execution_critical_mapped"] >= summary["execution_critical_total"] else "err",
            ),
            (
                "report fields",
                f"{summary['report_fields_mapped']}/{summary['report_fields_total']}",
                "ok" if summary["report_fields_mapped"] >= summary["report_fields_total"] else "warn",
            ),
            ("ambiguous", str(summary["ambiguous"]), "ok" if summary["ambiguous"] == 0 else "warn"),
            ("compatibility", compatibility or "unknown", "ok" if compatibility.upper() in {"PASS", "COMPATIBLE", "OK"} else "warn"),
        ]

    def _computed_summary(self) -> dict[str, int]:
        critical = [row for row in self._rows if str(row.get("severity") or "") == "execution_critical"]
        report = [row for row in self._rows if str(row.get("severity") or "") != "execution_critical"]
        return {
            "execution_critical_total": len(critical),
            "execution_critical_mapped": sum(1 for row in critical if _row_is_mapped(row)),
            "report_fields_total": len(report),
            "report_fields_mapped": sum(1 for row in report if _row_is_mapped(row)),
            "ambiguous": sum(1 for row in self._rows if str(row.get("status") or "") == "ambiguous"),
        }

    def _refresh_summary(self) -> None:
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._summary_tiles = []
        for key, value, level in self._summary_cards():
            tile = _summary_tile(key, value, level)
            self._summary_tiles.append(tile)
            self.summary_layout.addWidget(tile)

    def _refresh_guidance(self) -> None:
        if self._has_blocking_rows():
            text = "Resolve red execution-critical inputs before readiness. Select a row, choose a candidate, or apply a custom source."
            level = "err"
        elif self._dirty:
            text = "Edited bindings are ready to save. Report-completeness warnings can be handled later if the method can run."
            level = "warn" if self._has_warning_rows() else "ok"
        else:
            guidance = self.model.get("action_guidance") if isinstance(self.model.get("action_guidance"), dict) else {}
            text = str(guidance.get("headline") or "Review or edit binding status before continuing.")
            raw_level = str(guidance.get("severity") or "warn")
            level = "ok" if raw_level == "pass" else "err" if raw_level == "block" else "warn"
        self.guidance.setText(text)
        self.guidance.setProperty("level", level)
        self.guidance.setStyleSheet(_guidance_style(level))

    def _binding_rows(self) -> list[list[str]]:
        return [_binding_values(row) for row in self._rows]

    def _candidate_table_rows(self, rows: list[dict[str, Any]]) -> list[list[str]]:
        return [
            [
                _candidate_summary(row),
                str(row.get("example_value") or row.get("example") or ""),
                _confidence_display(row.get("confidence")),
            ]
            for row in rows
        ]

    def _all_candidate_table_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("method_field") or ""),
                _candidate_label(row),
                str(row.get("source_kind") or ""),
                str(row.get("coverage") or ""),
                str(row.get("example_value") or row.get("example") or ""),
                _confidence_display(row.get("confidence")),
                str(row.get("reason") or ""),
            ]
            for row in self._candidate_rows
        ]

    def _resolution_table_rows(self) -> list[list[str]]:
        return [
            [
                str(row.get("method_field") or ""),
                str(row.get("mapped_source") or ""),
                str(row.get("candidate_count") or ""),
                str(row.get("confidence") or ""),
                str(row.get("status") or ""),
                str(row.get("message") or ""),
            ]
            for row in self._resolution_rows
        ]

    def _make_table(self, headers: list[str], rows: list[list[str]]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setWordWrap(True)
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column == 0:
                    item.setForeground(QtGui.QColor(_status_color(value)))
                table.setItem(row_index, column, item)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        for column in range(max(0, len(headers) - 1)):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.resizeRowsToContents()
        return table

    def _refresh_binding_row(self, row_index: int, table: QtWidgets.QTableWidget | None = None) -> None:
        row = self._rows[row_index]
        target = table or self.binding_table
        for column, value in enumerate(_binding_values(row)):
            item = QtWidgets.QTableWidgetItem(value)
            if column == 0:
                item.setForeground(QtGui.QColor(_status_color(value)))
            if column == 2:
                item.setToolTip(str(row.get("description") or row.get("required_for") or ""))
            target.setItem(row_index, column, item)

    def _select_first_attention_row(self) -> None:
        target = 0
        for index, row in enumerate(self._rows):
            status = str(row.get("operator_status") or row.get("status") or "").lower()
            if status in {"missing", "unmapped", "warning", "warn", "ambiguous"}:
                target = index
                break
        if self._rows:
            self.binding_table.selectRow(target)
            self._on_binding_selection_changed()

    def _on_binding_selection_changed(self) -> None:
        index = self._current_row_index()
        if index is None:
            self.editor_title.setText("Select a method input")
            self.editor_current.setText("Choose a binding row to review candidates or enter a source.")
            self._fill_candidate_table([])
            self._set_custom_source_text("")
            self.preview_label.setText("Preview: select a candidate or enter a custom source.")
            self.consequence_label.clear()
            return
        row = self._rows[index]
        self.editor_title.setText(str(row.get("method_field") or "Method input"))
        current = row.get("mapped_source") or "not mapped"
        status = row.get("operator_status") or row.get("status") or "unmapped"
        self.editor_current.setText(
            f"Current binding: {current} ({row.get('source_kind') or 'source'}). Status: {status}."
        )
        kind = str(row.get("source_kind") or "")
        if not kind or kind == "missing":
            kind = "dataset" if str(row.get("scope") or "").casefold() in {"per_dataset", "per_package"} else "field"
        self._set_custom_kind_text(kind if kind in {"channel", "field", "dataset", "package"} else "field")
        self._set_custom_source_text(str(row.get("mapped_source") or ""))
        self.consequence_label.setText(_binding_consequence(row))
        self._fill_candidate_table(self._candidates_for_row(row))
        self._refresh_binding_preview()

    def _on_candidate_selection_changed(self) -> None:
        candidate = self._current_candidate()
        if candidate is not None:
            kind = _normalize_kind(str(candidate.get("source_kind") or "field"))
            if kind in {"channel", "field", "dataset", "package"}:
                self._set_custom_kind_text(kind)
            index = self._current_row_index()
            candidates = self._candidates_for_row(self._rows[index]) if index is not None else []
            self._refresh_custom_source_suggestions(candidates)
            self._set_custom_source_text(_candidate_source_name(candidate))
        self._refresh_binding_preview()

    def _on_custom_kind_changed(self) -> None:
        index = self._current_row_index()
        candidates = self._candidates_for_row(self._rows[index]) if index is not None else []
        self._refresh_custom_source_suggestions(candidates)
        self._sync_candidate_selection_to_custom_source(self._custom_source_text())
        self._refresh_binding_preview()

    def _on_custom_source_changed(self, text: str) -> None:
        self._sync_candidate_selection_to_custom_source(text)
        self._refresh_binding_preview()

    def _fill_candidate_table(self, candidates: list[dict[str, Any]]) -> None:
        rows = self._candidate_table_rows(candidates)
        self.candidate_table.setRowCount(len(rows))
        self.candidate_table.setColumnCount(3)
        self.candidate_table.setHorizontalHeaderLabels(["Candidate", "Example", "Confidence"])
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, candidates[row_index])
                self.candidate_table.setItem(row_index, column, item)
        header = self.candidate_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.candidate_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.candidate_table.resizeRowsToContents()
        self.use_candidate_button.setEnabled(bool(rows))
        self._refresh_custom_source_suggestions(candidates)
        if rows:
            self.candidate_table.selectRow(0)
            self._on_candidate_selection_changed()
        else:
            self._refresh_binding_preview()

    def _refresh_custom_source_suggestions(self, candidates: list[dict[str, Any]]) -> None:
        current = self._custom_source_text()
        suggestions = _candidate_source_suggestions(candidates, self.custom_kind.currentText())
        blocker = QtCore.QSignalBlocker(self.custom_source)
        self.custom_source.clear()
        self.custom_source.addItems(suggestions)
        self.custom_source.setCurrentText(current)
        del blocker
        if self.custom_source.lineEdit() is not None:
            placeholder = (
                "Choose a compatible MTDP source or type manually"
                if suggestions
                else "No compatible suggestion for this kind; type manually"
            )
            self.custom_source.lineEdit().setPlaceholderText(placeholder)
        tooltip = (
            "Suggestions are compatible candidates from the selected MTDP package."
            if suggestions
            else "No compatible candidates were found for this source kind."
        )
        self.custom_source.setToolTip(tooltip)

    def _custom_source_text(self) -> str:
        return self.custom_source.currentText().strip()

    def _set_custom_source_text(self, value: str) -> None:
        blocker = QtCore.QSignalBlocker(self.custom_source)
        self.custom_source.setCurrentText(value)
        del blocker

    def _set_custom_kind_text(self, value: str) -> None:
        blocker = QtCore.QSignalBlocker(self.custom_kind)
        self.custom_kind.setCurrentText(value)
        del blocker

    def _sync_candidate_selection_to_custom_source(self, source: str) -> None:
        text = source.strip()
        if not text:
            self.candidate_table.clearSelection()
            return
        kind = _normalize_kind(self.custom_kind.currentText())
        for row_index in range(self.candidate_table.rowCount()):
            item = self.candidate_table.item(row_index, 0)
            if item is None:
                continue
            candidate = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not isinstance(candidate, dict):
                continue
            candidate_kind = _normalize_kind(str(candidate.get("source_kind") or "field"))
            if candidate_kind == kind and _candidate_source_name(candidate) == text:
                current = self.candidate_table.currentRow()
                if current != row_index:
                    self.candidate_table.selectRow(row_index)
                return
        self.candidate_table.clearSelection()

    def _current_row_index(self) -> int | None:
        selected = self.binding_table.selectionModel().selectedRows() if self.binding_table.selectionModel() else []
        if not selected:
            return None
        index = selected[0].row()
        return index if 0 <= index < len(self._rows) else None

    def _current_candidate(self) -> dict[str, Any] | None:
        selected = self.candidate_table.selectionModel().selectedRows() if self.candidate_table.selectionModel() else []
        if not selected:
            return None
        item = self.candidate_table.item(selected[0].row(), 0)
        value = item.data(QtCore.Qt.ItemDataRole.UserRole) if item is not None else None
        return dict(value) if isinstance(value, dict) else None

    def _candidates_for_row(self, row: dict[str, Any]) -> list[dict[str, Any]]:
        field = str(row.get("method_field") or "")
        role = str(row.get("source_role") or "")
        return [
            candidate
            for candidate in self._candidate_rows
            if str(candidate.get("method_field") or "") == field
            or (role and str(candidate.get("source_role") or "") == role)
        ]

    def _use_selected_candidate(self) -> None:
        index = self._current_row_index()
        candidate = self._current_candidate()
        if index is None or candidate is None:
            return
        source = _candidate_source_name(candidate)
        if not source:
            return
        self._set_row_binding(index, str(candidate.get("source_kind") or "field"), source, candidate=candidate)

    def _apply_custom_binding(self) -> None:
        index = self._current_row_index()
        source = self._custom_source_text()
        if index is None or not source:
            return
        self._set_row_binding(index, self.custom_kind.currentText(), source)

    def _clear_current_binding(self) -> None:
        index = self._current_row_index()
        if index is None:
            return
        row = self._rows[index]
        self._remove_mapping_for_role(_row_source_role(row))
        row["mapped_source"] = ""
        row["source_kind"] = "missing"
        row["source_location"] = ""
        row["coverage"] = "not mapped"
        row["example_value"] = ""
        row["confidence"] = ""
        row["status"] = "fail" if row.get("severity") == "execution_critical" else "warn"
        row["operator_status"] = "missing" if row.get("severity") == "execution_critical" else "warning"
        self._dirty = True
        self._refresh_after_binding_change(index)

    def _set_row_binding(
        self,
        index: int,
        source_kind: str,
        source: str,
        *,
        candidate: dict[str, Any] | None = None,
    ) -> None:
        row = self._rows[index]
        kind = _normalize_kind(source_kind)
        source_role = _row_source_role(row)
        self._write_mapping_for_role(source_role, kind, source)
        row["mapped_source"] = source
        row["source_kind"] = kind
        row["source_location"] = f"{kind}:{source}"
        row["coverage"] = str((candidate or {}).get("coverage") or row.get("coverage") or "mapping declared")
        row["example_value"] = str((candidate or {}).get("example_value") or row.get("example_value") or "")
        row["confidence"] = str((candidate or {}).get("confidence") or "manual")
        row["status"] = "pass"
        row["operator_status"] = "found"
        self._dirty = True
        self._refresh_after_binding_change(index)

    def _refresh_after_binding_change(self, index: int) -> None:
        selected_field = str(self._rows[index].get("method_field") or "")
        self._resort_rows_and_refresh(selected_field)
        self._refresh_summary()
        self._refresh_guidance()
        self._refresh_accept_state()
        self._on_binding_selection_changed()

    def _resort_rows_and_refresh(self, selected_field: str | None = None) -> None:
        self._rows.sort(key=_row_attention_sort_key)
        self.binding_table.setRowCount(len(self._rows))
        selected_index = 0
        for row_index in range(len(self._rows)):
            self._refresh_binding_row(row_index)
            if selected_field and str(self._rows[row_index].get("method_field") or "") == selected_field:
                selected_index = row_index
        if self._rows:
            self.binding_table.selectRow(selected_index)

    def _refresh_binding_preview(self) -> None:
        if not hasattr(self, "preview_label"):
            return
        index = self._current_row_index()
        if index is None:
            self.preview_label.setText("Preview: select a candidate or enter a custom source.")
            return
        row = self._rows[index]
        field = str(row.get("method_field") or "method input")
        candidate = self._current_candidate()
        if candidate is not None:
            source = _candidate_source_name(candidate)
            kind = _normalize_kind(str(candidate.get("source_kind") or "field"))
            confidence = _confidence_display(candidate.get("confidence"))
            self.preview_label.setText(
                f"Preview: {field} will bind to {kind}:{source} ({confidence})."
            )
            return
        custom_source = self._custom_source_text()
        if custom_source:
            self.preview_label.setText(
                f"Preview: {field} will bind to {self.custom_kind.currentText()}:{custom_source} as a manual override."
            )
            return
        candidates = self._candidates_for_row(row)
        if not candidates and str(row.get("severity") or "") != "execution_critical":
            self.preview_label.setText(
                f"Preview: no automatic candidate was found for {field}. You may leave it blank as a report warning, "
                "or enter a dataset/report source manually."
            )
            return
        if not candidates:
            self.preview_label.setText(
                f"Preview: no automatic candidate was found for {field}; readiness remains blocked until a source is bound."
            )
            return
        self.preview_label.setText(f"Preview: {field} is unchanged.")

    def _write_mapping_for_role(self, source_role: str, source_kind: str, source: str) -> None:
        self._remove_mapping_for_role(source_role)
        section = "channels" if _normalize_kind(source_kind) == "channel" else "fields"
        payload = self._mapping_payload.setdefault(section, {})
        if isinstance(payload, dict):
            payload[source_role] = source

    def _remove_mapping_for_role(self, source_role: str) -> None:
        for section in ("channels", "fields", "tokens"):
            payload = self._mapping_payload.get(section)
            if isinstance(payload, dict):
                payload.pop(source_role, None)

    def _browse_profile(self) -> None:
        start_path = self.selected_mapping_path or self.default_path
        start = str(start_path.parent if start_path is not None else Path.cwd())
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose method mapping profile",
            start,
            "Mapping profiles (*.json *.yaml *.yml);;All files (*)",
        )
        if path:
            self._set_selected_mapping_path(Path(path))

    def _use_default_profile(self) -> None:
        if self.default_path is not None:
            self._set_selected_mapping_path(self.default_path)

    def _open_profile_file(self) -> None:
        if self.selected_mapping_path is not None:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.selected_mapping_path)))

    def _set_selected_mapping_path(self, path: Path) -> None:
        self.selected_mapping_path = path
        self.path_edit.setText(str(path))
        self.open_file_button.setEnabled(True)
        self._dirty = False
        self._refresh_accept_state()

    def _save_as_profile(self) -> None:
        default_path = self._default_edited_profile_path()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save repaired mapping profile",
            str(default_path),
            "Mapping profiles (*.json);;All files (*)",
        )
        if not path:
            return
        self._save_edited_profile(Path(path))

    def _save_edited_profile(self, path: Path | None = None) -> Path:
        output = path or self._default_edited_profile_path()
        payload = dict(self._mapping_payload)
        mapping_id = str(payload.get("mapping_id") or output.stem)
        if output != self.current_path and not mapping_id.endswith("_wizard_edit"):
            payload["mapping_id"] = f"{mapping_id}_wizard_edit"
        saved = write_mapping_profile(normalize_mapping_profile(payload), output)
        self.selected_mapping_path = saved
        self.path_edit.setText(str(saved))
        self.open_file_button.setEnabled(True)
        self._dirty = False
        self._refresh_accept_state()
        return saved

    def _default_edited_profile_path(self) -> Path:
        base = self.current_path or self.default_path or Path.cwd() / "mapping_profile.json"
        stem = base.stem
        parent = base.parent
        candidate = parent / f"{stem}_wizard_edit.json"
        suffix = 2
        while candidate.exists() and candidate != self.selected_mapping_path:
            candidate = parent / f"{stem}_wizard_edit_{suffix}.json"
            suffix += 1
        return candidate

    def _accept_current(self) -> None:
        if self._dirty:
            self._save_edited_profile()
        self.accept()

    def _refresh_accept_state(self) -> None:
        can_accept = self._can_accept_selected_profile()
        self.accept_button.setEnabled(can_accept)
        self.accept_button.setText("Save edits and use profile" if self._dirty else "Use selected profile")
        if can_accept:
            self.accept_button.setToolTip(
                "Save the edited mapping profile and use it for the method run."
                if self._dirty
                else "Use this mapping profile for the method run."
            )
            return
        if self._has_blocking_rows():
            self.accept_button.setToolTip("Resolve red execution-critical mapping rows before continuing.")
        elif self.selected_mapping_path is None and not self._dirty:
            self.accept_button.setToolTip("Choose or edit a mapping profile before continuing.")
        else:
            self.accept_button.setToolTip(
                self._confirm_tooltip
                or "This profile has blocking mapping issues. Choose or repair the profile before continuing."
            )

    def _can_accept_selected_profile(self) -> bool:
        if self._has_blocking_rows():
            return False
        if self._dirty:
            return True
        if self.selected_mapping_path is None:
            return False
        if (
            self.current_path is not None
            and self.selected_mapping_path == self.current_path
            and not self._can_confirm_current
        ):
            return False
        return True

    def _has_blocking_rows(self) -> bool:
        return any(
            row.get("severity") == "execution_critical"
            and (not _row_is_mapped(row) or str(row.get("status") or "") == "ambiguous")
            for row in self._rows
        )

    def _has_warning_rows(self) -> bool:
        return any(
            row.get("severity") != "execution_critical"
            and (not _row_is_mapped(row) or str(row.get("status") or "") in {"warn", "warning", "ambiguous"})
            for row in self._rows
        )


def _row_attention_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    status = str(row.get("operator_status") or row.get("status") or "").casefold()
    severity = str(row.get("severity") or "").casefold()
    if severity == "execution_critical" and status in {"missing", "unmapped", "fail", "block", "blocker"}:
        rank = 0
    elif status in {"missing", "unmapped", "warning", "warn", "ambiguous", "fail"}:
        rank = 1
    elif severity == "execution_critical":
        rank = 2
    else:
        rank = 3
    return rank, str(row.get("method_field") or "")


def _binding_values(row: dict[str, Any]) -> list[str]:
    return [
        str(row.get("operator_status") or row.get("status") or ""),
        str(row.get("required_or_recommended") or ""),
        str(row.get("method_field") or ""),
        str(row.get("source_location") or row.get("mapped_source") or ""),
        str(row.get("candidate_count") or ""),
    ]


def _binding_consequence(row: dict[str, Any]) -> str:
    if str(row.get("severity") or "") == "execution_critical":
        return "Clearing this required binding blocks readiness until a replacement source is applied."
    return "Clearing this report binding leaves the field blank and records a warning in the formal output."


def _summary_tile(key: str, value: str, level: str) -> QtWidgets.QFrame:
    frame = QtWidgets.QFrame()
    frame.setObjectName("mappingSummaryTile")
    frame.setProperty("level", level)
    frame.setStyleSheet(_summary_tile_style(level))
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(3)
    key_label = QtWidgets.QLabel(key.upper())
    key_label.setObjectName("mappingSummaryKey")
    value_label = QtWidgets.QLabel(value)
    value_label.setObjectName("mappingSummaryValue")
    value_label.setStyleSheet("font-weight: 700; font-size: 11pt; background: transparent;")
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    return frame


def _summary_tile_style(level: str) -> str:
    if level == "ok":
        return f"QFrame#mappingSummaryTile {{ background:{Color.OK_BG}; border:1px solid {Color.OK_BORDER}; border-radius:6px; }}"
    if level == "err":
        return f"QFrame#mappingSummaryTile {{ background:{Color.ERR_BG}; border:1px solid {Color.ERR_BORDER}; border-radius:6px; }}"
    return f"QFrame#mappingSummaryTile {{ background:{Color.WARN_BG}; border:1px solid {Color.WARN_BORDER}; border-radius:6px; }}"


def _caps_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text.upper())
    label.setObjectName("mappingActionKey")
    label.setStyleSheet(f"color: {Color.TEXT_2}; font-size: 9pt; font-weight: 700; background: transparent;")
    return label


def _issue_rows(guidance: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    blocking = guidance.get("blocking_fields") if isinstance(guidance.get("blocking_fields"), list) else []
    warnings = guidance.get("warning_fields") if isinstance(guidance.get("warning_fields"), list) else []
    for field in blocking:
        if str(field):
            rows.append(["blocker", str(field)])
    for field in warnings:
        if str(field):
            rows.append(["warning", str(field)])
    return rows or [["ok", "No blocking mapping issues"]]


def _status_color(status: str) -> str:
    status = status.lower()
    if status in {"found", "pass", "ok", "mapped", "confirmed"}:
        return Color.OK_ACCENT
    if status in {"missing", "unmapped", "fail", "block", "blocker"}:
        return Color.ERR_ACCENT
    if status in {"warning", "warn", "ambiguous"}:
        return Color.WARN_ACCENT
    return Color.TEXT_2


def _guidance_style(level: str) -> str:
    if level == "ok":
        return f"background:{Color.OK_BG}; color:{Color.OK_INK}; border:1px solid {Color.OK_BORDER}; border-radius:6px; padding:8px 10px;"
    if level == "err":
        return f"background:{Color.ERR_BG}; color:{Color.ERR_INK}; border:1px solid {Color.ERR_BORDER}; border-radius:6px; padding:8px 10px;"
    return f"background:{Color.WARN_BG}; color:{Color.WARN_INK}; border:1px solid {Color.WARN_BORDER}; border-radius:6px; padding:8px 10px;"


def _candidate_label(row: dict[str, Any]) -> str:
    return str(row.get("candidate_source") or row.get("source_name") or "")


def _candidate_summary(row: dict[str, Any]) -> str:
    label = _candidate_label(row)
    kind = str(row.get("source_kind") or "source")
    coverage = str(row.get("coverage") or "").strip()
    reason = str(row.get("reason") or "").strip()
    detail = " - ".join(part for part in (coverage, reason) if part)
    return f"{label} ({kind})" + (f"\n{detail}" if detail else "")


def _candidate_source_suggestions(candidates: list[dict[str, Any]], source_kind: str) -> list[str]:
    kind = _normalize_kind(source_kind)
    suggestions: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_kind = _normalize_kind(str(candidate.get("source_kind") or "field"))
        if candidate_kind != kind:
            continue
        source = _candidate_source_name(candidate)
        if not source or source in seen:
            continue
        seen.add(source)
        suggestions.append(source)
    return suggestions


def _confidence_display(value: Any) -> str:
    pct = _confidence_percent(value)
    filled = max(0, min(5, round(pct / 20)))
    meter = "#" * filled + "-" * (5 - filled)
    label = str(value or "manual").strip()
    return f"[{meter}] {pct}% - {label}"


def _confidence_percent(value: Any) -> int:
    text = str(value or "").strip().casefold()
    if not text:
        return 70
    try:
        number = float(text.rstrip("%"))
    except ValueError:
        pass
    else:
        return int(max(0, min(100, number if number > 1 else number * 100)))
    return {
        "exact": 96,
        "high": 88,
        "medium": 64,
        "med": 64,
        "manual": 72,
        "low": 38,
        "weak": 28,
    }.get(text, 70)


def _candidate_source_name(row: dict[str, Any]) -> str:
    source = str(row.get("source_name") or "").strip()
    if source:
        return source
    source = str(row.get("candidate_source") or "").strip()
    for prefix in ("channels.", "tokens.", "fields."):
        if source.startswith(prefix):
            return source[len(prefix):]
    if ":" in source:
        return source.split(":", 1)[1]
    return source


def _row_is_mapped(row: dict[str, Any]) -> bool:
    return bool(str(row.get("mapped_source") or "").strip()) and str(row.get("status") or "") != "ambiguous"


def _row_source_role(row: dict[str, Any]) -> str:
    role = str(row.get("source_role") or "").strip()
    if role:
        return role
    field = str(row.get("method_field") or "").strip()
    return field.rsplit(".", 1)[-1] if field else "source"


def _normalize_kind(value: str) -> str:
    text = str(value or "").strip().casefold()
    if text in {"channel", "channels"}:
        return "channel"
    if text in {"dataset", "package"}:
        return text
    return "field"


def _load_mapping_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(payload, dict):
        return None
    return normalize_mapping_profile(payload)


def _mapping_payload_from_model(model: dict[str, Any]) -> dict[str, Any]:
    return normalize_mapping_profile(
        {
            "mapping_id": model.get("mapping_id") or "wizard_mapping_profile",
            "method_id": model.get("method_id") or "",
            "channels": {},
            "fields": {},
            "validation": {},
        }
    )
