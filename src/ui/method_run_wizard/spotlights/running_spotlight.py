from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._tokens import Color


RUNNING_STAGES = (
    ("load_input_package", "Input"),
    ("load_method_package", "Method"),
    ("load_mapping", "Mapping"),
    ("readiness_check", "Ready"),
    ("method_resolve", "Resolve"),
    ("method_reduce", "Reduce"),
    ("validation", "Validate"),
    ("acceptance", "Accept"),
    ("write_mtda", "Write"),
    ("build_audit_report", "Report"),
    ("build_workbench_optional", "Workbench"),
    ("complete", "Done"),
)


class RunningSpotlight(QtWidgets.QWidget):
    view_log_clicked = QtCore.pyqtSignal()
    back_to_setup_clicked = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("runningSpotlight")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 12)
        layout.setSpacing(8)

        head = QtWidgets.QHBoxLayout()
        phase_layout = QtWidgets.QVBoxLayout()
        phase_layout.setSpacing(2)

        self._phase = QtWidgets.QLabel("")
        self._phase.setObjectName("runningPhase")
        self._meta = QtWidgets.QLabel("")
        self._meta.setObjectName("runningMeta")
        self._meta.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._pct = QtWidgets.QLabel("0%")
        self._pct.setObjectName("runningPct")

        phase_layout.addWidget(self._phase)
        phase_layout.addWidget(self._meta)
        head.addLayout(phase_layout, 1)
        head.addWidget(self._pct)
        layout.addLayout(head)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        layout.addWidget(self._bar)

        self._stage_strip = QtWidgets.QFrame()
        self._stage_strip.setObjectName("runningStageStrip")
        self._stage_strip.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        stage_layout = QtWidgets.QGridLayout(self._stage_strip)
        stage_layout.setContentsMargins(0, 1, 0, 1)
        stage_layout.setHorizontalSpacing(5)
        stage_layout.setVerticalSpacing(5)
        self._stage_labels: dict[str, QtWidgets.QLabel] = {}
        for index, (phase, label) in enumerate(RUNNING_STAGES):
            stage = QtWidgets.QLabel(label)
            stage.setObjectName("runningStage")
            stage.setProperty("state", "todo")
            stage.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            stage.setMinimumHeight(20)
            self._stage_labels[phase] = stage
            stage_layout.addWidget(stage, index // 6, index % 6)
        layout.addWidget(self._stage_strip)

        self._summary = QtWidgets.QFrame()
        self._summary.setObjectName("runningSummary")
        self._summary.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        summary_layout = QtWidgets.QGridLayout(self._summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setHorizontalSpacing(8)
        summary_layout.setVerticalSpacing(8)
        self._summary_values: dict[str, QtWidgets.QLabel] = {}
        for column, (key, label, value) in enumerate(
            (
                ("stage", "Active stage", "Waiting"),
                ("runs", "Run rows", "0 tracked"),
                ("event", "Latest event", "No worker events yet"),
            )
        ):
            tile, value_label = _summary_tile(label, value)
            self._summary_values[key] = value_label
            summary_layout.addWidget(tile, 0, column)
        layout.addWidget(self._summary)

        trace_head = QtWidgets.QLabel("LIVE ANALYSIS TRACE")
        trace_head.setObjectName("runningTraceHead")
        layout.addWidget(trace_head)
        self._trace = QtWidgets.QListWidget()
        self._trace.setObjectName("runningTrace")
        self._trace.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._trace.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self._trace.setMinimumHeight(68)
        self._trace.setMaximumHeight(86)
        self._last_event_message = ""
        layout.addWidget(self._trace)

        self._error_panel = QtWidgets.QFrame()
        error_layout = QtWidgets.QVBoxLayout(self._error_panel)
        error_layout.setContentsMargins(0, 0, 0, 0)
        error_layout.setSpacing(8)
        self._error = QtWidgets.QLabel("")
        self._error.setObjectName("runningError")
        self._error.setWordWrap(True)
        error_layout.addWidget(self._error)
        error_buttons = QtWidgets.QHBoxLayout()
        error_buttons.addStretch(1)
        self.view_log_button = QtWidgets.QPushButton("View full log")
        self.view_log_button.setProperty("class", "link")
        self.view_log_button.setAccessibleName("View full activity log")
        self.back_to_setup_button = QtWidgets.QPushButton("Back to setup")
        self.back_to_setup_button.setProperty("class", "subtle")
        self.back_to_setup_button.setAccessibleName("Back to setup")
        self.view_log_button.clicked.connect(self.view_log_clicked.emit)
        self.back_to_setup_button.clicked.connect(self.back_to_setup_clicked.emit)
        error_buttons.addWidget(self.view_log_button)
        error_buttons.addWidget(self.back_to_setup_button)
        error_layout.addLayout(error_buttons)
        self._error_panel.setVisible(False)
        layout.addWidget(self._error_panel)

        self._table = QtWidgets.QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Run", "Status", "Notes"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self._table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(118)
        self._table.setMaximumHeight(168)
        self._table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(self._table)

    def set_phase(self, name: str, meta_html: str) -> None:
        self._phase.setText(name)
        self._meta.setText(meta_html)

    def set_stage(self, phase: str) -> None:
        if phase not in self._stage_labels:
            return
        current_index = [item[0] for item in RUNNING_STAGES].index(phase)
        for index, (stage_phase, _label) in enumerate(RUNNING_STAGES):
            if index < current_index:
                state = "done"
            elif index == current_index:
                state = "now"
            else:
                state = "todo"
            widget = self._stage_labels[stage_phase]
            widget.setProperty("state", state)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self._summary_values["stage"].setText(RUNNING_STAGES[current_index][1])

    def set_progress(self, pct: int) -> None:
        pct = max(0, min(100, int(pct)))
        self._bar.setValue(pct)
        self._pct.setText(f"{pct}%")

    def set_run_status(self, runs: dict[str, str], notes: dict[str, str] | None = None) -> None:
        notes = notes or {}
        self._table.setRowCount(len(runs))
        for row, (run_id, status) in enumerate(sorted(runs.items())):
            self._table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(run_id)))
            status_item = QtWidgets.QTableWidgetItem(str(status))
            status_item.setForeground(QtGui.QColor(_status_color(str(status))))
            self._table.setItem(row, 1, status_item)
            self._table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(notes.get(run_id, ""))))
        self._table.resizeRowsToContents()
        self._summary_values["runs"].setText(_run_status_summary(runs))

    def reset_activity(self) -> None:
        self._trace.clear()
        self._last_event_message = ""
        self._summary_values["event"].setText("No worker events yet")

    def append_event(
        self,
        message: str,
        *,
        phase: str = "",
        status: str = "info",
        progress: int | None = None,
    ) -> None:
        message = str(message).strip()
        if not message or message == self._last_event_message:
            return
        self._last_event_message = message
        stamp = QtCore.QTime.currentTime().toString("HH:mm:ss")
        parts = [stamp]
        if progress is not None:
            parts.append(f"{max(0, min(100, int(progress)))}%")
        if phase:
            parts.append(_phase_label(phase))
        parts.append(message)
        item = QtWidgets.QListWidgetItem(" - ".join(parts))
        item.setForeground(QtGui.QColor(_status_color(status)))
        self._trace.addItem(item)
        while self._trace.count() > 8:
            self._trace.takeItem(0)
        self._trace.scrollToBottom()
        self._summary_values["event"].setText(message)

    def show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error_panel.setVisible(True)

    def clear_error(self) -> None:
        self._error.clear()
        self._error_panel.setVisible(False)


def _summary_tile(key: str, value: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("runningSummaryTile")
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(2)
    key_label = QtWidgets.QLabel(key)
    key_label.setObjectName("runningSummaryKey")
    value_label = QtWidgets.QLabel(value)
    value_label.setObjectName("runningSummaryValue")
    value_label.setWordWrap(True)
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    return frame, value_label


def _run_status_summary(runs: dict[str, str]) -> str:
    if not runs:
        return "0 tracked"
    counts: dict[str, int] = {}
    for status in runs.values():
        key = str(status).lower()
        counts[key] = counts.get(key, 0) + 1
    order = ("running", "done", "completed", "queued", "failed", "cancelled")
    parts = [f"{counts[key]} {key}" for key in order if counts.get(key)]
    parts.extend(f"{count} {key}" for key, count in sorted(counts.items()) if key not in order)
    return " - ".join(parts)


def _phase_label(phase: str) -> str:
    for stage_phase, label in RUNNING_STAGES:
        if stage_phase == phase:
            return label
    return phase.replace("_", " ").title()


def _status_color(status: str) -> str:
    return {
        "done": Color.OK_ACCENT,
        "completed": Color.OK_ACCENT,
        "ok": Color.OK_ACCENT,
        "running": Color.INFO_ACCENT,
        "info": Color.INFO_ACCENT,
        "queued": Color.TEXT_3,
        "failed": Color.ERR_ACCENT,
        "err": Color.ERR_ACCENT,
        "cancelled": Color.WARN_ACCENT,
        "warn": Color.WARN_ACCENT,
    }.get(status, Color.TEXT_2)
