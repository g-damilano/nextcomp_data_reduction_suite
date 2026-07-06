from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._log import LogEntry
from ui.method_run_wizard._qss import build_global_qss
from ui.method_run_wizard._tokens import Color
from ui.method_run_wizard.components.action_bar import ActionBar
from ui.method_run_wizard.components.activity_log_drawer import ActivityLogDrawer
from ui.method_run_wizard.components.decor_bottom import DecorBottom
from ui.method_run_wizard.components.decor_top import DecorTopBar
from ui.method_run_wizard.components.spotlight_frame import SpotlightFrame
from ui.method_run_wizard.components.task_card import TaskCard
from ui.method_run_wizard.state import WizardScenario
from ui.method_run_wizard.spotlights.finalize_spotlight import FinalizeSpotlight
from ui.method_run_wizard.spotlights.review_spotlight import ReviewSpotlight
from ui.method_run_wizard.spotlights.running_spotlight import RunningSpotlight
from ui.method_run_wizard.spotlights.setup_spotlight import SetupSpotlight


class StatusDot(QtWidgets.QFrame):
    """Small status indicator used in the Method Analysis window status bar."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor(Color.OK_ACCENT)
        self.setFixedSize(12, 12)

    def set_color(self, color: str) -> None:
        self._color = QtGui.QColor(color)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawEllipse(rect)


class MethodRunWindow(QtWidgets.QMainWindow):
    """Feature-flagged shell for the reworked Method Analysis workflow."""

    closed = QtCore.pyqtSignal()

    SCENARIO_ORDER = (
        WizardScenario.SETUP,
        WizardScenario.RUNNING,
        WizardScenario.REVIEW,
        WizardScenario.FINALIZE,
    )

    def __init__(
        self,
        *,
        dev: bool = False,
        package_path: str | Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.dev = dev
        self.package_path = Path(package_path) if package_path is not None else None
        self.package_label = self.package_path.name if self.package_path is not None else "No package selected"
        self._set_window_title()
        self.setMinimumSize(760, 560)
        self.resize(1280, 820)
        self.setStyleSheet(build_global_qss())
        self._build_menu_bar()

        central = QtWidgets.QWidget()
        central.setObjectName("methodRunRoot")
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.demo_bar = QtWidgets.QFrame()
        self.demo_bar.setVisible(bool(dev))
        layout.addWidget(self.demo_bar)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setObjectName("methodRunViewport")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.viewport().setObjectName("methodRunViewportFrame")
        self.scroll_area.viewport().setAutoFillBackground(True)

        scroll_contents = QtWidgets.QWidget()
        scroll_contents.setObjectName("methodRunViewportContents")
        scroll_contents.setAutoFillBackground(True)
        self.scroll_layout = QtWidgets.QVBoxLayout(scroll_contents)
        self.scroll_layout.setContentsMargins(24, 28, 24, 24)
        self.scroll_layout.setSpacing(0)

        self.column = QtWidgets.QWidget()
        self.column.setObjectName("methodRunColumn")
        self.column.setAutoFillBackground(True)
        self.column.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        column_layout = QtWidgets.QVBoxLayout(self.column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(12)

        self.decor_top = DecorTopBar()

        self.spotlight = SpotlightFrame()
        self.spotlight_bodies: dict[WizardScenario, QtWidgets.QWidget] = {}
        self.action_bars: dict[WizardScenario, ActionBar] = {}
        self._scenario_index: dict[WizardScenario, int] = {}
        self._build_scenario_stacks()

        self.decor_bottom = DecorBottom()
        self.decor_bottom.set_context_text(
            f"<b>ISO 14126</b> · {self.package_label} · method not selected · mapping not selected"
        )
        self.decor_bottom.bar.context_line.toggled.connect(self._context_detail_toggled)

        column_layout.addWidget(self.decor_top)
        column_layout.addWidget(self.spotlight)
        column_layout.addWidget(self.decor_bottom)
        self.scroll_layout.addWidget(
            self.column,
            0,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
        )
        self.scroll_layout.addStretch(1)
        self.scroll_area.setWidget(scroll_contents)
        layout.addWidget(self.scroll_area, 1)
        self.setCentralWidget(central)

        self._build_status_bar()
        self.log_drawer = ActivityLogDrawer(self)
        self._connect_dynamic_layout_sync()
        self.set_scenario(WizardScenario.SETUP)
        self._configure_accessibility()
        self._sync_responsive_width()

    def _set_window_title(self) -> None:
        self.setWindowTitle(f"Method Analysis \u2014 {self.package_label}")

    def _build_menu_bar(self) -> None:
        self.method_run_menu_bar = self.menuBar()
        self.file_menu = self.method_run_menu_bar.addMenu("&File")
        self.choose_package_action = QtGui.QAction("Choose Package...", self)
        self.choose_package_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.choose_package_action.setStatusTip("Choose an MTDP package for this method run")
        self.file_menu.addAction(self.choose_package_action)
        self.file_menu.addSeparator()
        self.close_action = QtGui.QAction("Close Analysis", self)
        self.close_action.setShortcut(QtGui.QKeySequence.StandardKey.Close)
        self.close_action.setStatusTip("Close Method Analysis")
        self.close_action.triggered.connect(lambda _checked=False: self.close())
        self.file_menu.addAction(self.close_action)

        self.workflow_menu = self.method_run_menu_bar.addMenu("&Analysis")
        self.choose_method_action = QtGui.QAction("Choose Method", self)
        self.choose_method_action.setShortcut(QtGui.QKeySequence("Ctrl+M"))
        self.choose_method_action.setStatusTip("Choose one implemented method for the selected package")
        self.refresh_mapping_action = QtGui.QAction("Edit Mapping...", self)
        self.refresh_mapping_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+M"))
        self.refresh_mapping_action.setStatusTip("Review or choose the mapping profile for the selected method/package")
        self.check_readiness_action = QtGui.QAction("Check Readiness", self)
        self.check_readiness_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+R"))
        self.check_readiness_action.setStatusTip("Inspect package, method, and mapping before execution")
        self.run_method_action = QtGui.QAction("Run Method", self)
        self.run_method_action.setShortcut(QtGui.QKeySequence("Ctrl+Return"))
        self.run_method_action.setStatusTip("Start method execution when readiness allows it")
        self.cancel_run_action = QtGui.QAction("Cancel Run", self)
        self.cancel_run_action.setStatusTip("Cancel the active method run and return to setup")
        self.confirm_review_action = QtGui.QAction("Confirm Review", self)
        self.confirm_review_action.setStatusTip("Confirm acceptance decisions and open the output handoff")
        self.finalize_mtda_action = QtGui.QAction("Finalize MTDA", self)
        self.finalize_mtda_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+F"))
        self.finalize_mtda_action.setStatusTip("Finalize the MTDA after a reviewer note has been entered")
        for action in (
            self.choose_method_action,
            self.refresh_mapping_action,
            self.check_readiness_action,
        ):
            self.workflow_menu.addAction(action)
        self.workflow_menu.addSeparator()
        self.workflow_menu.addAction(self.run_method_action)
        self.workflow_menu.addAction(self.cancel_run_action)
        self.workflow_menu.addAction(self.confirm_review_action)
        self.workflow_menu.addAction(self.finalize_mtda_action)

        self.output_menu = self.method_run_menu_bar.addMenu("&Output")
        self.open_test_report_action = QtGui.QAction("Open Test Report", self)
        self.open_test_report_action.setStatusTip("Open the generated test report from the MTDA output")
        self.open_audit_report_action = QtGui.QAction("Open Audit Report", self)
        self.open_audit_report_action.setStatusTip("Open the generated audit report from the MTDA output")
        self.open_workbench_action = QtGui.QAction("Open Workbench", self)
        self.open_workbench_action.setStatusTip("Open the Method Development Workbench for this output")
        self.open_output_folder_action = QtGui.QAction("Open Output Folder", self)
        self.open_output_folder_action.setStatusTip("Open the folder containing the MTDA output")
        self.copy_mtda_path_action = QtGui.QAction("Copy MTDA Path", self)
        self.copy_mtda_path_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+C"))
        self.copy_mtda_path_action.setStatusTip("Copy the current MTDA output path to the clipboard")
        self.open_report_completion_action = QtGui.QAction("Review Missing Report Fields", self)
        self.open_report_completion_action.setStatusTip("Open the report-completion dialog for missing fields")
        for action in (
            self.open_test_report_action,
            self.open_audit_report_action,
            self.open_workbench_action,
            self.open_output_folder_action,
            self.copy_mtda_path_action,
            self.open_report_completion_action,
        ):
            self.output_menu.addAction(action)

        self.view_menu = self.method_run_menu_bar.addMenu("&View")
        self.context_details_action = QtGui.QAction("Context Details", self)
        self.context_details_action.setCheckable(True)
        self.context_details_action.setStatusTip("Show or hide package, method, mapping, and output details")
        self.activity_log_action = QtGui.QAction("Activity Log", self)
        self.activity_log_action.setCheckable(True)
        self.activity_log_action.setStatusTip("Show or hide the activity log drawer; shortcut: L")
        self.view_menu.addAction(self.context_details_action)
        self.view_menu.addAction(self.activity_log_action)

        self.help_menu = self.method_run_menu_bar.addMenu("&Help")
        self.shortcuts_action = QtGui.QAction("Shortcuts", self)
        self.shortcuts_action.setStatusTip("Show Method Analysis keyboard shortcuts")
        self.shortcuts_action.triggered.connect(self._show_shortcuts)
        self.help_menu.addAction(self.shortcuts_action)

    def _show_shortcuts(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "Method Analysis Shortcuts",
            "Ctrl+O chooses a package.\n"
            "Ctrl+M moves to method selection.\n"
            "Ctrl+Shift+M opens mapping review.\n"
            "Ctrl+Shift+R checks readiness.\n"
            "Ctrl+Return runs the method when ready.\n"
            "Ctrl+Shift+F finalizes from the output view.\n"
            "L toggles the activity log.\n"
            "Esc closes the log drawer, then collapses the expanded task.",
        )

    def _build_status_bar(self) -> None:
        status_bar = self.statusBar()
        self.status_dot = StatusDot()
        self.status_message = QtWidgets.QLabel("Ready")
        self.status_log_button = QtWidgets.QPushButton("Activity log · 0")
        self.status_log_button.setObjectName("statusLogLink")
        self.status_log_button.setAccessibleName("Activity log, 0 entries")
        self.status_version = QtWidgets.QLabel("mtdp v0.2.0")

        status_bar.addWidget(self.status_dot)
        status_bar.addWidget(self.status_message, 1)
        status_bar.addPermanentWidget(self.status_log_button)
        status_bar.addPermanentWidget(self.status_version)

    def _build_scenario_stacks(self) -> None:
        for index, scenario in enumerate(self.SCENARIO_ORDER):
            if scenario == WizardScenario.SETUP:
                body = SetupSpotlight()
                self.setup_spotlight = body
            elif scenario == WizardScenario.RUNNING:
                body = RunningSpotlight()
                self.running_spotlight = body
            elif scenario == WizardScenario.REVIEW:
                body = ReviewSpotlight()
                self.review_spotlight = body
            elif scenario == WizardScenario.FINALIZE:
                body = FinalizeSpotlight()
                self.finalize_spotlight = body
            else:
                body = QtWidgets.QWidget()
            action_bar = ActionBar()
            self.spotlight.body.addWidget(body)
            self.spotlight.foot.addWidget(action_bar)
            self.spotlight_bodies[scenario] = body
            self.action_bars[scenario] = action_bar
            self._scenario_index[scenario] = index

    def set_scenario(self, scenario: WizardScenario) -> None:
        scenario = WizardScenario(scenario)
        index = self._scenario_index[scenario]
        self.spotlight.body.setCurrentIndex(index)
        self.spotlight.foot.setCurrentIndex(index)

        status_by_scenario = {
            WizardScenario.SETUP: (Color.WARN_ACCENT, "Choose inputs"),
            WizardScenario.RUNNING: (Color.INFO_ACCENT, "Method execution in progress"),
            WizardScenario.REVIEW: (Color.WARN_ACCENT, "Review required"),
            WizardScenario.FINALIZE: (Color.WARN_ACCENT, "Output ready"),
        }
        color, message = status_by_scenario[scenario]
        self.status_dot.set_color(color)
        self.status_message.setText(message)
        if scenario == WizardScenario.SETUP:
            self.spotlight.head.set_text(
                "Choose workflow inputs",
                f"ISO 14126 on <b>{self.package_label}</b> · readiness not checked",
            )
        elif scenario == WizardScenario.RUNNING:
            self.spotlight.head.set_text(
                "Running",
                "ISO 14126 · waiting for worker status",
            )
        elif scenario == WizardScenario.REVIEW:
            self.spotlight.head.set_text(
                "One decision before output",
                "Execution complete · review flagged runs from the service output",
            )
        elif scenario == WizardScenario.FINALIZE:
            self.spotlight.head.set_text(
                "Output is ready",
                "Test Report has warnings · MTDA is in draft",
            )
        self.set_pipeline_state(scenario)
        self._sync_responsive_width()

    def append_log_entry(self, entry: LogEntry) -> None:
        self.log_drawer.append(entry)

    def set_activity_log_count(self, count: int) -> None:
        label = f"Activity log · {int(count)}"
        self.status_log_button.setText(label)
        self.status_log_button.setAccessibleName(f"Activity log, {int(count)} entries")
        self.decor_bottom.set_activity_log_count(count)
        self.log_drawer.set_count(count)

    def set_package_path(self, package_path: str | Path | None) -> None:
        self.package_path = Path(package_path) if package_path is not None else None
        self.package_label = self.package_path.name if self.package_path is not None else "No package selected"
        self._set_window_title()

    def set_pipeline_state(
        self,
        scenario: WizardScenario | None = None,
        *,
        package_selected: bool = False,
        method_selected: bool = False,
        mapping_selected: bool = False,
        mapping_resolved: bool = False,
        readiness_status: str | None = None,
        finalized: bool = False,
    ) -> None:
        scenario = WizardScenario(scenario or self.SCENARIO_ORDER[self.spotlight.body.currentIndex()])
        ready_level = "todo"
        if readiness_status in {"READY", "READY_WITH_WARNINGS"}:
            ready_level = "ok"
        elif readiness_status:
            ready_level = "err"
        states = {
            "package": "ok" if package_selected else "todo",
            "method": "ok" if method_selected else "todo",
            "mapping": "ok" if mapping_selected and (mapping_resolved or scenario != WizardScenario.SETUP) else "warn" if mapping_selected else "todo",
            "ready": ready_level,
            "exec": "todo",
            "validate": "todo",
            "accept": "todo",
            "output": "todo",
        }
        if scenario == WizardScenario.SETUP:
            if not package_selected:
                states.update({"package": "now", "method": "todo", "mapping": "todo", "ready": "todo"})
            elif not method_selected:
                states.update({"package": "ok", "method": "now", "mapping": "todo", "ready": "todo"})
            elif not mapping_selected:
                states.update({"package": "ok", "method": "ok", "mapping": "now", "ready": "todo"})
            elif readiness_status is None:
                states["mapping"] = "ok" if mapping_resolved else "warn"
                states["ready"] = "now" if mapping_resolved else "todo"
        elif scenario == WizardScenario.RUNNING:
            states.update({"mapping": "ok", "exec": "now"})
        elif scenario == WizardScenario.REVIEW:
            states.update({"mapping": "ok", "exec": "ok", "validate": "ok", "accept": "warn"})
        elif scenario == WizardScenario.FINALIZE:
            states.update(
                {
                    "mapping": "ok",
                    "exec": "ok",
                    "validate": "ok",
                    "accept": "ok",
                    "output": "ok" if finalized else "warn",
                }
            )
        self.decor_top.pipeline.set_state(states)

    def set_context(
        self,
        *,
        package: str,
        method: str,
        mapping: str,
        output: str,
        report_gaps: int,
    ) -> None:
        gap_html = ""
        if report_gaps > 0:
            gap_html = f" <span style='color:{Color.WARN_INK}'>({int(report_gaps)} report gaps)</span>"
        self.decor_bottom.set_context_text(
            f"<b>ISO 14126</b> · {package} · method {method} · mapping {mapping}{gap_html}"
        )
        self.decor_bottom.detail.set_row_value("Package", package)
        self.decor_bottom.detail.set_row_value("Method", method)
        self.decor_bottom.detail.set_row_value("Mapping", mapping)
        self.decor_bottom.detail.set_row_value("Output", output)

    def set_finalized_head(self) -> None:
        self.spotlight.head.set_text(
            "Output is ready",
            "Finalized · MTDA archive state is locked",
        )

    def show_activity_log(self) -> None:
        self.log_drawer.sync_to_parent()
        self.log_drawer.slide_in()

    def hide_activity_log(self) -> None:
        self.log_drawer.slide_out()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_responsive_width()
        if hasattr(self, "log_drawer"):
            self.log_drawer.sync_to_parent()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)

    def _sync_responsive_width(self) -> None:
        if not hasattr(self, "column"):
            return
        if hasattr(self, "scroll_area") and self.isVisible():
            viewport_width = max(1, self.scroll_area.viewport().width())
            viewport_height = max(1, self.scroll_area.viewport().height())
        else:
            viewport_width = max(1, self.width())
            viewport_height = max(1, self.height())
        outer_margin = 24 if viewport_width >= 920 else 16
        vertical_margin = 28 if viewport_height >= 700 else 14
        bottom_margin = 24 if viewport_height >= 700 else 12
        self.scroll_layout.setContentsMargins(outer_margin, vertical_margin, outer_margin, bottom_margin)
        margin = 48 if viewport_width >= 920 else 32
        target = min(1120, max(620, viewport_width - margin))
        self.column.setMinimumWidth(target)
        self.column.setMaximumWidth(target)
        self.spotlight.setMaximumWidth(target)
        self.spotlight.updateGeometry()
        self.column.layout().activate()
        target_height = self.column.layout().sizeHint().height()
        if target_height < viewport_height and target_height + vertical_margin + bottom_margin > viewport_height:
            spare = max(0, viewport_height - target_height)
            vertical_margin = min(vertical_margin, spare // 2)
            bottom_margin = min(bottom_margin, spare - vertical_margin)
            self.scroll_layout.setContentsMargins(outer_margin, vertical_margin, outer_margin, bottom_margin)
        self.column.setMinimumHeight(target_height)
        self.column.setMaximumHeight(target_height)
        self.column.resize(target, target_height)
        contents_margins = self.scroll_layout.contentsMargins()
        contents_height = target_height + contents_margins.top() + contents_margins.bottom()
        contents_width = target + contents_margins.left() + contents_margins.right()
        scroll_widget = self.scroll_area.widget()
        scroll_widget.setMinimumHeight(contents_height)
        scroll_widget.setMinimumWidth(contents_width)
        scroll_widget.layout().activate()

    def _connect_dynamic_layout_sync(self) -> None:
        for task in self.findChildren(TaskCard):
            task.expanded_changed.connect(lambda _open, self=self: self._defer_layout_sync())
            task.content_changed.connect(self._defer_layout_sync)
        self.review_spotlight.expanded.connect(lambda _run_id, _open: self._defer_layout_sync())
        self.review_spotlight.keep_clicked.connect(lambda _run_id: self._defer_layout_sync())
        self.review_spotlight.remove_clicked.connect(lambda _run_id: self._defer_layout_sync())

    def _defer_layout_sync(self) -> None:
        QtCore.QTimer.singleShot(0, self._sync_responsive_width)

    def _context_detail_toggled(self, open_: bool) -> None:
        if open_:
            QtCore.QTimer.singleShot(0, self._fit_open_context_detail)

    def _fit_open_context_detail(self) -> None:
        self._sync_responsive_width()
        self.scroll_area.widget().layout().activate()
        self.column.layout().activate()
        detail_bottom = self.decor_bottom.mapTo(
            self,
            QtCore.QPoint(0, self.decor_bottom.height()),
        ).y()
        viewport_bottom = self.scroll_area.viewport().mapTo(
            self,
            QtCore.QPoint(0, self.scroll_area.viewport().height()),
        ).y()
        overflow = detail_bottom + 16 - viewport_bottom
        if overflow > 0:
            screen = self.screen()
            available = (
                screen.availableGeometry()
                if screen is not None
                else QtCore.QRect(0, 0, self.width(), self.height())
            )
            target_height = min(self.height() + overflow, available.height())
            if target_height > self.height():
                self.resize(self.width(), target_height)
        QtCore.QTimer.singleShot(0, self._scroll_context_detail_into_view)

    def _scroll_context_detail_into_view(self) -> None:
        if not self.decor_bottom.detail.isVisible():
            return
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(min(bar.maximum(), bar.value() + self.decor_bottom.detail.height()))

    def _configure_accessibility(self) -> None:
        self.status_message.setAccessibleName("Method run status")
        self.status_version.setAccessibleName("Method run UI version")
        self.setTabOrder(self.setup_spotlight.mapping_task._header, self.setup_spotlight.metadata_task._header)
        self.setTabOrder(
            self.setup_spotlight.metadata_task._header,
            self.action_bars[WizardScenario.SETUP].primary_button,
        )
        self.setTabOrder(
            self.action_bars[WizardScenario.SETUP].primary_button,
            self.decor_bottom.bar.context_line,
        )
        self.setTabOrder(self.decor_bottom.bar.context_line, self.decor_bottom.bar.activity_log_button)
        for button in self.findChildren(QtWidgets.QPushButton):
            if not button.accessibleName():
                button.setAccessibleName(button.text().replace("&", ""))
            if button.text() and button.property("class") != "link" and button.objectName() != "statusLogLink":
                text_width = button.fontMetrics().horizontalAdvance(button.text())
                hint = button.sizeHint()
                button.setMinimumSize(max(hint.width(), text_width + 38), max(hint.height(), 34))
