from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from ui.method_run_wizard.components.task_card import TaskCard


class SetupSpotlight(QtWidgets.QWidget):
    change_package = QtCore.pyqtSignal()
    change_method = QtCore.pyqtSignal()
    method_selected = QtCore.pyqtSignal(object)
    save_bindings = QtCore.pyqtSignal()
    skip_bindings = QtCore.pyqtSignal()
    edit_mapping_profile = QtCore.pyqtSignal()
    open_metadata_dialog = QtCore.pyqtSignal()
    accept_metadata_warnings = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("setupSpotlight")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        self._mapping_resolved = False
        self._metadata_resolved = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 16)
        layout.setSpacing(12)

        self.input_summary = self._make_input_summary()
        self.input_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.input_summary.setMinimumHeight(104)
        self.input_summary.setMaximumHeight(122)

        self.method_row = QtWidgets.QFrame()
        self.method_row.setObjectName("methodPicker")
        method_layout = QtWidgets.QHBoxLayout(self.method_row)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(10)
        method_label = QtWidgets.QLabel("Method")
        method_label.setObjectName("setupCaps")
        method_label.setProperty("kind", "neutral")
        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.setAccessibleName("Implemented method")
        self.method_combo.setToolTip("Choose one of the implemented method packages registered in the software.")
        self.mapping_label = QtWidgets.QLabel("Mapping: waiting for method")
        self.mapping_label.setObjectName("taskWhy")
        self.mapping_label.setWordWrap(True)
        self.method_combo.currentIndexChanged.connect(self._method_index_changed)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo, 1)
        method_layout.addWidget(self.mapping_label, 1)
        self.method_row.setVisible(False)

        self.mapping_task = TaskCard(
            "mapping",
            "needs you",
            "Choose workflow inputs",
            "Select the real package, method, and mapping before readiness can be checked.",
        )
        self.mapping_task.set_body_widget(self._make_prerequisite_body(["package", "method", "mapping"]))

        self.metadata_task = TaskCard(
            "metadata",
            "optional",
            "Readiness warnings",
            "Metadata warnings appear here after readiness has inspected the selected workflow inputs.",
        )
        self.metadata_task.set_body_widget(self._make_metadata_body(0))

        self.empty_state = QtWidgets.QLabel("All decisions resolved \u2713")
        self.empty_state.setObjectName("setupEmptyState")
        self.empty_state.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setVisible(False)

        layout.addWidget(self.input_summary)
        layout.addWidget(self.method_row)
        layout.addWidget(self.mapping_task)
        layout.addWidget(self.metadata_task)
        layout.addWidget(self.empty_state)

    def set_input_summary(
        self,
        *,
        package_value: str,
        package_sub: str,
        package_state: str,
        method_value: str,
        method_sub: str,
        method_state: str,
        mapping_value: str,
        mapping_sub: str,
        mapping_state: str,
        method_enabled: bool,
        mapping_enabled: bool,
    ) -> None:
        self._set_summary_tile(
            self.package_tile,
            self.package_value,
            self.package_sub,
            self.package_button,
            value=package_value,
            sub=package_sub,
            state=package_state,
            action_text="Change package" if package_state == "ok" else "Choose package",
            action_enabled=True,
        )
        self._set_summary_tile(
            self.method_tile,
            self.method_value,
            self.method_sub,
            self.method_button,
            value=method_value,
            sub=method_sub,
            state=method_state,
            action_text="Change method" if method_state == "ok" else "Choose method",
            action_enabled=method_enabled,
        )
        self._set_summary_tile(
            self.mapping_tile,
            self.mapping_value,
            self.mapping_sub,
            self.mapping_button,
            value=mapping_value,
            sub=mapping_sub,
            state=mapping_state,
            action_text="Review mapping" if mapping_state in {"ok", "warn", "err"} else "Choose mapping",
            action_enabled=mapping_enabled,
        )

    def set_method_entries(self, entries: list[object], current_id: str | None = None) -> None:
        blocked = self.method_combo.blockSignals(True)
        self.method_combo.clear()
        selected_index = 0
        for index, entry in enumerate(entries):
            method_id = str(getattr(entry, "method_id", ""))
            label = str(getattr(entry, "label", method_id or "Method"))
            version = str(getattr(entry, "version", ""))
            suffix = f" · {version}" if version else ""
            self.method_combo.addItem(f"{label}{suffix}", entry)
            if current_id and method_id == current_id:
                selected_index = index
        self.method_combo.setEnabled(bool(entries))
        self.method_combo.setMaxVisibleItems(max(3, min(8, len(entries) or 3)))
        if entries:
            self.method_combo.setCurrentIndex(selected_index)
        self.method_combo.blockSignals(blocked)

    def selected_method_entry(self) -> object | None:
        return self.method_combo.currentData()

    def set_mapping_label(self, text: str) -> None:
        self.mapping_label.setText(text)

    def set_method_picker_visible(self, visible: bool) -> None:
        self.method_row.setVisible(visible)

    def show_prerequisites(self, missing: list[str], *, package_selected: bool = False) -> None:
        missing_text = ", ".join(missing) if missing else "workflow inputs"
        self._mapping_resolved = False
        self._metadata_resolved = False
        self.mapping_task.setVisible(True)
        self.metadata_task.setVisible(False)
        self.empty_state.setVisible(False)
        first_missing = missing[0] if missing else "workflow inputs"
        if first_missing == "package":
            title = "Choose package"
            why = "Select a real MTDP package first; method and mapping remain unset until the package is known."
            body = self._make_prerequisite_body(missing, package_selected=package_selected)
        elif first_missing == "method":
            title = "Choose method"
            why = "Choose one implemented method registered for this package, then the method default mapping will be checked."
            body = self._make_method_body()
        else:
            title = "Check mapping"
            why = f"Missing: {missing_text}. Confirm the method default mapping before readiness can run."
            body = self._make_prerequisite_body(missing, package_selected=package_selected)
        self.mapping_task.set_chrome(
            "needs you",
            title,
            why,
        )
        self.mapping_task.set_body_widget(body)
        self.mapping_task.set_expanded(True)

    def show_readiness_pending(self) -> None:
        self._mapping_resolved = False
        self._metadata_resolved = False
        self.mapping_task.setVisible(True)
        self.metadata_task.setVisible(False)
        self.empty_state.setVisible(False)
        self.mapping_task.set_chrome(
            "needs you",
            "Check readiness",
            "Inputs are selected. Run readiness before method execution so warnings and blockers come from the package.",
        )
        self.mapping_task.set_body_widget(self._make_readiness_body())
        self.mapping_task.set_expanded(False)

    def show_mapping_check(
        self,
        *,
        blockers: list[str],
        report_gap_count: int,
        bound_count: int,
        bound_examples: list[str],
        missing_rows: list[tuple[str, str]],
        mapping_name: str,
    ) -> None:
        self._mapping_resolved = not blockers and report_gap_count <= 0
        self._metadata_resolved = True
        self.mapping_task.setVisible(True)
        self.metadata_task.setVisible(False)
        self.empty_state.setVisible(False)
        if blockers:
            badge = "needs you"
            title = "Fix mapping blockers"
            why = "The selected method default mapping has execution-critical gaps or inconsistencies against this package."
        elif report_gap_count:
            badge = "needs you"
            title = "Review mapping warnings"
            why = "Execution-critical inputs are bound; report-completeness gaps should be filled or accepted."
        else:
            badge = "optional"
            title = "Mapping is ready"
            why = "The method default mapping covers the selected package and can move to readiness."
        self.mapping_task.set_chrome(badge, title, why)
        self.mapping_task.set_body_widget(
            self._make_mapping_check_body(
                blockers=blockers,
                report_gap_count=report_gap_count,
                bound_count=bound_count,
                bound_examples=bound_examples,
                missing_rows=missing_rows,
                mapping_name=mapping_name,
            )
        )
        self.mapping_task.set_expanded(bool(blockers or report_gap_count))
        self._sync_empty_state()

    def show_readiness_blocked(self, blockers: list[str]) -> None:
        self._mapping_resolved = False
        self._metadata_resolved = True
        self.mapping_task.setVisible(True)
        self.metadata_task.setVisible(False)
        self.empty_state.setVisible(False)
        self.mapping_task.set_chrome(
            "needs you",
            "Fix readiness blockers",
            "Readiness failed. Update the selected inputs, then check readiness again.",
        )
        self.mapping_task.set_body_widget(
            self._make_readiness_messages_body(
                blockers,
                heading="Readiness blockers",
                fallback="Readiness failed but did not include blocker details.",
                include_context_buttons=True,
            )
        )
        self.mapping_task.set_expanded(True)

    def show_readiness_warnings(self, warnings: list[str]) -> None:
        self._mapping_resolved = False
        self._metadata_resolved = True
        self.mapping_task.setVisible(True)
        self.metadata_task.setVisible(False)
        self.empty_state.setVisible(False)
        self.mapping_task.set_chrome(
            "optional",
            "Review readiness warnings",
            "Run is enabled, but readiness returned warnings worth checking before execution.",
        )
        self.mapping_task.set_body_widget(
            self._make_readiness_messages_body(
                warnings,
                heading="Readiness warnings",
                fallback="Readiness reported warnings without details.",
                include_context_buttons=True,
            )
        )
        self.mapping_task.set_expanded(True)

    def show_decisions(
        self,
        *,
        mapping_gap_count: int,
        metadata_gap_count: int,
        bound_count: int,
        bound_examples: list[str],
        missing_rows: list[tuple[str, str]],
    ) -> None:
        self._mapping_resolved = mapping_gap_count <= 0 or self._mapping_resolved
        self._metadata_resolved = metadata_gap_count <= 0 or self._metadata_resolved
        self.mapping_task.setVisible(not self._mapping_resolved)
        self.metadata_task.setVisible(not self._metadata_resolved)
        self.mapping_task.set_chrome(
            "needs you",
            f"Bind {mapping_gap_count} report fields, or accept the warnings",
            f"{mapping_gap_count} report bindings are missing. Save field values now or accept the warnings and continue.",
        )
        self.mapping_task.set_body_widget(
            self._make_mapping_body(
                mapping_gap_count=mapping_gap_count,
                bound_count=bound_count,
                bound_examples=bound_examples,
                missing_rows=missing_rows,
            )
        )
        self.metadata_task.set_chrome(
            "optional",
            f"{metadata_gap_count} recommended metadata fields are blank",
            "Recommended report metadata can be completed now, or acknowledged and left blank for this run.",
        )
        self.metadata_task.set_body_widget(self._make_metadata_body(metadata_gap_count))
        self._sync_empty_state()

    def set_mapping_resolved(self, resolved: bool) -> None:
        self._mapping_resolved = resolved
        self.mapping_task.setVisible(not resolved)
        self._sync_empty_state()

    def set_metadata_resolved(self, resolved: bool) -> None:
        self._metadata_resolved = resolved
        self.metadata_task.setVisible(not resolved)
        self._sync_empty_state()

    def set_empty_state(self, visible: bool) -> None:
        self.empty_state.setVisible(visible)

    def _sync_empty_state(self) -> None:
        self.set_empty_state(self._mapping_resolved and self._metadata_resolved)

    def _make_prerequisite_body(self, missing: list[str], *, package_selected: bool = False) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QtWidgets.QLabel("This wizard starts from the package, then narrows method and mapping choices from that package context.")
        label.setWordWrap(True)
        label.setObjectName("taskWhy")
        layout.addWidget(label)
        if package_selected:
            layout.addWidget(self._body_note("Package selected. Choose an implemented method next."))
        if package_selected:
            specs = (
                ("Choose package\u2026", "subtle", self.change_package),
                ("Choose method\u2026", "subtle", self.change_method),
                ("Choose mapping\u2026", "subtle", self.edit_mapping_profile),
            )
        else:
            specs = (("Choose package\u2026", "subtle", self.change_package),)
        layout.addLayout(self._button_row(specs))
        return body

    def _make_method_body(self) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(
            self._body_note(
                "Use the method dropdown above. Confirming the method loads its package details and applies the registered default mapping for checking."
            )
        )
        layout.addLayout(
            self._button_row(
                (
                    ("Choose method\u2026", "subtle", self.change_method),
                    ("Choose package\u2026", "subtle", self.change_package),
                )
            )
        )
        return body

    def _make_mapping_check_body(
        self,
        *,
        blockers: list[str],
        report_gap_count: int,
        bound_count: int,
        bound_examples: list[str],
        missing_rows: list[tuple[str, str]],
        mapping_name: str,
    ) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._caps_label(f"Mapping profile \u00b7 {mapping_name}", "ok" if not blockers else "warn"))
        if blockers:
            layout.addWidget(self._caps_label("Execution-critical issues", "warn"))
            for blocker in blockers:
                layout.addWidget(self._chip(blocker, "warn"))
        layout.addWidget(self._caps_label(f"Already bound \u00b7 {bound_count} critical inputs", "ok"))
        if bound_examples:
            layout.addWidget(self._chip_flow(tuple(bound_examples[:6]), "ok", max_per_row=2))
        else:
            layout.addWidget(self._body_note("The mapping check did not report bound examples."))
        if report_gap_count:
            layout.addWidget(self._caps_label(f"Report-completeness gaps \u00b7 {report_gap_count}", "warn"))
            if missing_rows:
                layout.addWidget(self._make_missing_table(missing_rows))
            else:
                layout.addWidget(self._body_note("Readiness did not provide field-level report-gap details."))
        else:
            layout.addWidget(self._caps_label("Report-completeness gaps \u00b7 0", "ok"))
        layout.addLayout(
            self._button_row(
                (
                    ("Edit mapping profile\u2026", "subtle", self.edit_mapping_profile),
                    ("Change method\u2026", "subtle", self.change_method),
                    ("Choose package\u2026", "subtle", self.change_package),
                )
            )
        )
        return body

    def _make_readiness_body(self) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        label = QtWidgets.QLabel("Readiness will inspect the selected package, method, and mapping before Run is enabled.")
        label.setWordWrap(True)
        label.setObjectName("taskWhy")
        layout.addWidget(label)
        return body

    def _make_readiness_messages_body(
        self,
        messages: list[str],
        *,
        heading: str,
        fallback: str,
        include_context_buttons: bool,
    ) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._caps_label(heading, "warn"))
        if messages:
            for message in messages:
                layout.addWidget(self._chip(str(message), "warn"))
        else:
            layout.addWidget(self._body_note(fallback))
        if include_context_buttons:
            layout.addLayout(
                self._button_row(
                    (
                        ("Change package\u2026", "subtle", self.change_package),
                        ("Change method\u2026", "subtle", self.change_method),
                        ("Edit mapping\u2026", "subtle", self.edit_mapping_profile),
                    )
                )
            )
        return body

    def _make_mapping_body(
        self,
        *,
        mapping_gap_count: int = 7,
        bound_count: int = 35,
        bound_examples: list[str] | None = None,
        missing_rows: list[tuple[str, str]] | None = None,
    ) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        if bound_examples is None:
            bound_examples = [
                "channel.load \u2192 load_N",
                "channel.strain \u2192 strain_axial",
                "geometry.width \u2192 specimen.width_mm",
                "geometry.thickness \u2192 specimen.thickness_mm",
                "failure_mode \u2192 failure_mode_iso",
            ]

        layout.addWidget(self._caps_label(f"Already bound \u00b7 {bound_count} critical inputs", "ok"))

        if bound_examples:
            chip_flow = self._chip_flow(
                tuple(bound_examples[:5]),
                "ok",
                max_per_row=2,
            )
            extra_count = max(0, bound_count - min(bound_count, 5))
            if extra_count:
                show_all = QtWidgets.QPushButton(f"+ {extra_count} more bound \u00b7 show all")
                show_all.setProperty("class", "link")
                show_all.setAccessibleName("Show all bound critical inputs")
                chip_flow.layout().addWidget(show_all)
            layout.addWidget(chip_flow)
        else:
            layout.addWidget(self._body_note("No bound mapping examples were reported by readiness."))

        layout.addWidget(self._caps_label(f"Missing report fields \u00b7 {mapping_gap_count}", "warn"))
        if not missing_rows:
            layout.addWidget(self._body_note("Readiness did not provide field-level missing-binding details."))
        layout.addWidget(self._make_missing_table(missing_rows))
        layout.addLayout(
            self._button_row(
                (
                    ("Save bindings", "primary", self.save_bindings),
                    ("Skip \u2014 accept warnings", "subtle", self.skip_bindings),
                    ("Edit mapping profile\u2026", "subtle", self.edit_mapping_profile),
                )
            )
        )
        return body

    def _make_metadata_body(self, metadata_gap_count: int = 38) -> QtWidgets.QWidget:
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        chips = (f"Recommended report fields \u00b7 {metadata_gap_count} blank",)
        layout.addWidget(self._chip_flow(chips, "neutral", max_per_row=2))
        layout.addLayout(
            self._button_row(
                (
                    ("Open report-completion dialog", "primary", self.open_metadata_dialog),
                    ("Run anyway \u2014 accept warnings", "subtle", self.accept_metadata_warnings),
                )
            )
        )
        return body

    def _make_missing_table(self, rows: list[tuple[str, str]] | None = None) -> QtWidgets.QTableWidget:
        if rows is None:
            rows = [
                ("Operator", "A. Engineer"),
                ("Laboratory", "Cambridge Composites Lab"),
                ("Test date", "2026-05-28"),
                ("Conditioning", "23 C / 50 % RH"),
                ("Machine ID", "Instron 5985"),
                ("Load cell", "10 kN"),
                ("Remarks", "No visible pre-test damage"),
            ]
        table = QtWidgets.QTableWidget(len(rows), 3)
        table.setHorizontalHeaderLabels(["Field", "Example value", "Resolution"])
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        table.setMinimumHeight(max(96, min(250, 72 + len(rows) * 32)))
        for row, (field, example) in enumerate(rows):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(field))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(example))
            resolution = QtWidgets.QLineEdit()
            resolution.setAccessibleName(f"Resolution for {field}")
            table.setCellWidget(row, 2, resolution)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        return table

    def _button_row(
        self,
        specs: tuple[tuple[str, str, QtCore.pyqtBoundSignal], ...],
    ) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        for text, button_class, signal in specs:
            button = QtWidgets.QPushButton(text)
            button.setProperty("class", button_class)
            button.setAccessibleName(text)
            button.clicked.connect(signal.emit)
            button.style().unpolish(button)
            button.style().polish(button)
            text_width = button.fontMetrics().horizontalAdvance(text)
            hint = button.sizeHint()
            button.setMinimumSize(max(hint.width(), text_width + 38), max(hint.height(), 34))
            if text == "Save bindings":
                self.save_bindings_button = button
            elif text.startswith("Skip"):
                self.skip_bindings_button = button
            elif text.startswith("Edit"):
                self.edit_mapping_profile_button = button
            elif text.startswith("Change method"):
                self.change_method_button = button
            elif text.startswith("Open"):
                self.open_metadata_dialog_button = button
            elif text.startswith("Run anyway"):
                self.accept_metadata_warnings_button = button
            row.addWidget(button)
        row.addStretch(1)
        return row

    def _method_index_changed(self) -> None:
        entry = self.selected_method_entry()
        if entry is not None:
            self.method_selected.emit(entry)

    def _make_input_summary(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setObjectName("setupInputSummary")
        frame.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        frame.setMinimumHeight(104)
        frame.setMaximumHeight(122)
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        (
            self.package_tile,
            self.package_value,
            self.package_sub,
            self.package_button,
        ) = self._summary_tile("PACKAGE", self.change_package)
        (
            self.method_tile,
            self.method_value,
            self.method_sub,
            self.method_button,
        ) = self._summary_tile("METHOD", self.change_method)
        (
            self.mapping_tile,
            self.mapping_value,
            self.mapping_sub,
            self.mapping_button,
        ) = self._summary_tile("MAPPING", self.edit_mapping_profile)

        for tile in (self.package_tile, self.method_tile, self.mapping_tile):
            layout.addWidget(tile)
        return frame

    def _summary_tile(
        self,
        key: str,
        signal: QtCore.pyqtBoundSignal,
    ) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel, QtWidgets.QLabel, QtWidgets.QPushButton]:
        tile = QtWidgets.QFrame()
        tile.setObjectName("setupInputTile")
        tile.setMinimumHeight(90)
        tile.setMaximumHeight(110)
        tile.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout = QtWidgets.QVBoxLayout(tile)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(3)
        key_label = QtWidgets.QLabel(key)
        key_label.setObjectName("setupInputKey")
        value_label = QtWidgets.QLabel("not selected")
        value_label.setObjectName("setupInputValue")
        value_label.setWordWrap(False)
        value_label.setMinimumHeight(18)
        sub_label = QtWidgets.QLabel("required")
        sub_label.setObjectName("setupInputSub")
        sub_label.setWordWrap(False)
        sub_label.setMinimumHeight(18)
        action = QtWidgets.QPushButton("Choose")
        action.setObjectName("setupInputAction")
        action.setProperty("class", "link")
        action.setAccessibleName(key.title())
        action.clicked.connect(signal.emit)
        layout.addWidget(key_label)
        layout.addWidget(value_label)
        layout.addWidget(sub_label)
        layout.addWidget(action, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return tile, value_label, sub_label, action

    @staticmethod
    def _set_summary_tile(
        tile: QtWidgets.QFrame,
        value_label: QtWidgets.QLabel,
        sub_label: QtWidgets.QLabel,
        button: QtWidgets.QPushButton,
        *,
        value: str,
        sub: str,
        state: str,
        action_text: str,
        action_enabled: bool,
    ) -> None:
        tile.setProperty("state", state)
        value_label.setText(value)
        sub_label.setText(sub)
        value_label.setToolTip(value)
        sub_label.setToolTip(sub)
        button.setText(action_text)
        button.setAccessibleName(action_text)
        button.setEnabled(action_enabled)
        for widget in (tile, value_label, sub_label, button):
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()

    @staticmethod
    def _caps_label(text: str, kind: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text.upper())
        label.setObjectName("setupCaps")
        label.setProperty("kind", kind)
        return label

    @staticmethod
    def _chip(text: str, kind: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("setupChip")
        label.setProperty("kind", kind)
        return label

    @staticmethod
    def _body_note(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("taskWhy")
        label.setWordWrap(True)
        return label

    def _chip_flow(
        self,
        texts: tuple[str, ...],
        kind: str,
        max_per_row: int,
    ) -> QtWidgets.QWidget:
        flow = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(flow)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for start in range(0, len(texts), max_per_row):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(6)
            for text in texts[start : start + max_per_row]:
                row.addWidget(self._chip(text, kind))
            row.addStretch(1)
            layout.addLayout(row)
        return flow
