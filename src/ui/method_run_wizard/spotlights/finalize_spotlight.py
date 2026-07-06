from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets


class FinalizeSpotlight(QtWidgets.QWidget):
    open_mtda = QtCore.pyqtSignal()
    open_test_report = QtCore.pyqtSignal()
    open_audit_report = QtCore.pyqtSignal()
    open_workbench = QtCore.pyqtSignal()
    open_output_folder = QtCore.pyqtSignal()
    copy_mtda_path = QtCore.pyqtSignal()
    open_report_completion = QtCore.pyqtSignal()
    finalize_clicked = QtCore.pyqtSignal()
    reviewer_changed = QtCore.pyqtSignal(str)
    note_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("finalizeSpotlight")
        self._finalized = False
        self._compact_layout: bool | None = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 14)
        layout.setSpacing(10)

        self.summary_strip = self._make_summary_strip()
        layout.addWidget(self.summary_strip)

        self.grid = QtWidgets.QGridLayout()
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(10)

        self.open_panel = self._make_open_panel()
        self.finalize_panel = self._make_finalize_panel()
        self.grid.addWidget(self.open_panel, 0, 0)
        self.grid.addWidget(self.finalize_panel, 0, 1)
        layout.addLayout(self.grid)

        self.toast = QtWidgets.QLabel("")
        self.toast.setObjectName("finalizeToast")
        self.toast.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.toast.setVisible(False)
        layout.addWidget(self.toast)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("finalizeError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        layout.addStretch(1)
        QtCore.QTimer.singleShot(0, self._sync_layout_mode)

    def set_missing_fields(self, count: int) -> None:
        value = int(count)
        self.missing_value.setText(str(value))
        self.review_missing_button.setText(f"Review {value} missing fields...")
        self.review_missing_button.setAccessibleName(f"Review {value} missing fields")

    def set_mtda_path(self, path: Path | str | None) -> None:
        if path:
            output_path = Path(path)
            text = str(output_path)
            name = output_path.name or text
        else:
            text = "No MTDA output selected"
            name = text
        has_path = bool(path)
        self.path_label.setText(name)
        self.path_edit.setText(text)
        self.path_edit.setCursorPosition(0)
        self.path_edit.setToolTip(text)
        self.open_mtda_button.setEnabled(has_path)
        self.copy_path_button.setEnabled(has_path)

    def set_review_counts(self, amendments: int, reviewer_notes: int) -> None:
        self.review_value.setText(f"{int(amendments)} / {int(reviewer_notes)}")
        self.review_sub.setText("amendments / notes")

    def set_finalized(self, finalized: bool) -> None:
        self._finalized = bool(finalized)
        self.finalize_button.setEnabled(False if self._finalized else bool(self.note_edit.text().strip()))
        self.finalize_button.setText("Finalized" if finalized else "Finalize with warnings")
        self.status_value.setText("Finalized" if finalized else "Draft")
        self.status_sub.setText("archive locked" if finalized else "not finalized")
        self.status_tile.setProperty("state", "ok" if finalized else "warn")
        _repolish(self.status_tile)

    def show_toast(self, text: str, *, duration_ms: int = 1500) -> None:
        self.toast.setText(text)
        self.toast.setVisible(True)
        QtCore.QTimer.singleShot(duration_ms, lambda: self.toast.setVisible(False))

    def show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.setVisible(bool(text))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._sync_layout_mode()

    def _make_summary_strip(self) -> QtWidgets.QFrame:
        strip = QtWidgets.QFrame()
        strip.setObjectName("finalizeSummary")
        layout = QtWidgets.QHBoxLayout(strip)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self.status_tile, self.status_value, self.status_sub = _summary_tile("MTDA", "Draft", "not finalized")
        self.status_tile.setProperty("state", "warn")
        self.missing_tile, self.missing_value, self.missing_sub = _summary_tile("REPORT GAPS", "0", "missing fields")
        self.review_tile, self.review_value, self.review_sub = _summary_tile("REVIEW", "0 / 0", "amendments / notes")
        for tile in (self.status_tile, self.missing_tile, self.review_tile):
            layout.addWidget(tile)
        return strip

    def _make_open_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("finalizePanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        layout.addWidget(_caps_label("OPEN"))
        icon = QtWidgets.QStyle.StandardPixmap
        self.test_report_button = _button("Test Report", self.open_test_report, icon.SP_FileIcon)
        self.audit_report_button = _button("Audit Report", self.open_audit_report, icon.SP_FileDialogDetailedView)
        self.workbench_button = _button("Method Development Workbench", self.open_workbench, icon.SP_ComputerIcon)
        self.output_folder_button = _button("Output folder", self.open_output_folder, icon.SP_DirOpenIcon)
        self.open_mtda_button = _button("Open MTDA", self.open_mtda, icon.SP_DialogOpenButton)
        for button in (
            self.test_report_button,
            self.audit_report_button,
            self.workbench_button,
            self.output_folder_button,
            self.open_mtda_button,
        ):
            button.setObjectName("finalizeOpenButton")
            layout.addWidget(button)

        layout.addSpacing(8)
        layout.addWidget(_caps_label("MTDA OUTPUT"))
        self.path_label = QtWidgets.QLabel("No MTDA output selected")
        self.path_label.setObjectName("finalizePathName")
        layout.addWidget(self.path_label)
        self.path_edit = QtWidgets.QLineEdit("No MTDA output selected")
        self.path_edit.setObjectName("finalizePath")
        self.path_edit.setReadOnly(True)
        self.path_edit.setAccessibleName("MTDA output path")
        path_row = QtWidgets.QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(6)
        self.copy_path_button = QtWidgets.QToolButton()
        self.copy_path_button.setObjectName("finalizeCopyPathButton")
        self.copy_path_button.setIcon(_copy_icon(self.copy_path_button))
        self.copy_path_button.setIconSize(QtCore.QSize(18, 18))
        self.copy_path_button.setToolTip("Copy MTDA path")
        self.copy_path_button.setAccessibleName("Copy MTDA path")
        self.copy_path_button.clicked.connect(self.copy_mtda_path.emit)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.copy_path_button, 0)
        layout.addLayout(path_row)
        layout.addStretch(1)
        return panel

    def _make_finalize_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("finalizePanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(9)

        layout.addWidget(_caps_label("FINALIZE MTDA"))
        self.review_missing_button = _button(
            "Review 0 missing fields...",
            self.open_report_completion,
            QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning,
        )
        self.review_missing_button.setObjectName("finalizeOpenButton")
        layout.addWidget(self.review_missing_button)

        layout.addWidget(_field_label("Reviewer"))
        self.reviewer_edit = QtWidgets.QLineEdit()
        self.reviewer_edit.setPlaceholderText("Reviewer/operator")
        self.reviewer_edit.setAccessibleName("Reviewer")
        self.reviewer_edit.textChanged.connect(self.reviewer_changed.emit)
        layout.addWidget(self.reviewer_edit)

        layout.addWidget(_field_label("Note"))
        self.note_edit = QtWidgets.QLineEdit()
        self.note_edit.setPlaceholderText("Required finalization note")
        self.note_edit.setAccessibleName("Finalization note")
        self.note_edit.textChanged.connect(self._on_note_changed)
        layout.addWidget(self.note_edit)

        self.finalize_button = QtWidgets.QPushButton("Finalize with warnings")
        self.finalize_button.setProperty("class", "primary")
        self.finalize_button.setAccessibleName("Finalize with warnings")
        self.finalize_button.setEnabled(False)
        self.finalize_button.clicked.connect(self.finalize_clicked.emit)
        layout.addWidget(self.finalize_button)

        hint = QtWidgets.QLabel("Required fields must be resolved; recommended gaps can finalize with warnings.")
        hint.setObjectName("finalizeHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return panel

    def _sync_layout_mode(self) -> None:
        compact = self.width() < 760
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        self.grid.removeWidget(self.open_panel)
        self.grid.removeWidget(self.finalize_panel)
        if compact:
            self.grid.addWidget(self.open_panel, 0, 0)
            self.grid.addWidget(self.finalize_panel, 1, 0)
            self.grid.setColumnStretch(0, 1)
            self.grid.setColumnStretch(1, 0)
        else:
            self.grid.addWidget(self.open_panel, 0, 0)
            self.grid.addWidget(self.finalize_panel, 0, 1)
            self.grid.setColumnStretch(0, 3)
            self.grid.setColumnStretch(1, 2)

    def _on_note_changed(self, text: str) -> None:
        self.finalize_button.setEnabled(False if self._finalized else bool(text.strip()))
        self.note_changed.emit(text)


def _button(
    text: str,
    signal: QtCore.pyqtBoundSignal,
    icon: QtWidgets.QStyle.StandardPixmap | None = None,
) -> QtWidgets.QPushButton:
    button = QtWidgets.QPushButton(text)
    button.setProperty("class", "subtle")
    button.setAccessibleName(text)
    if icon is not None:
        button.setIcon(button.style().standardIcon(icon))
        button.setIconSize(QtCore.QSize(18, 18))
    button.clicked.connect(signal.emit)
    return button


def _copy_icon(widget: QtWidgets.QWidget) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(22, 22)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    try:
        pen = QtGui.QPen(widget.palette().color(QtGui.QPalette.ColorRole.ButtonText))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(7, 4, 10, 12, 1.5, 1.5)
        painter.drawRoundedRect(4, 7, 10, 12, 1.5, 1.5)
    finally:
        painter.end()
    return QtGui.QIcon(pixmap)


def _caps_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    label.setObjectName("finalizeCaps")
    return label


def _field_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    label.setObjectName("finalizeFieldLabel")
    return label


def _summary_tile(key: str, value: str, sub: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel, QtWidgets.QLabel]:
    tile = QtWidgets.QFrame()
    tile.setObjectName("finalizeSummaryTile")
    layout = QtWidgets.QVBoxLayout(tile)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(2)
    key_label = QtWidgets.QLabel(key)
    key_label.setObjectName("finalizeSummaryKey")
    value_label = QtWidgets.QLabel(value)
    value_label.setObjectName("finalizeSummaryValue")
    sub_label = QtWidgets.QLabel(sub)
    sub_label.setObjectName("finalizeSummarySub")
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    layout.addWidget(sub_label)
    return tile, value_label, sub_label


def _repolish(widget: QtWidgets.QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
