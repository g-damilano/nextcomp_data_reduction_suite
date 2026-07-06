from __future__ import annotations

from html import escape

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from ui.method_run_wizard._log import LogEntry
from ui.method_run_wizard._tokens import Color


class ActivityLogDrawer(QtWidgets.QWidget):
    close_requested = QtCore.pyqtSignal()

    WIDTH = 460

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._open = False
        self._animation = QtCore.QPropertyAnimation(self, b"geometry", self)
        self._animation.setDuration(200)
        self._animation.finished.connect(self._on_animation_finished)
        self._hide_timer = QtCore.QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_if_closed)
        self.setObjectName("activityLogDrawer")
        self.setFixedWidth(self.WIDTH)
        self.setAutoFillBackground(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QtWidgets.QLabel("Activity log")
        title.setObjectName("activityLogTitle")
        self._count = QtWidgets.QLabel("")
        self._count.setObjectName("activityLogCount")
        self.close_button = QtWidgets.QPushButton("Close ×")
        self.close_button.setObjectName("logClose")
        self.close_button.setAccessibleName("Close activity log")
        self.close_button.clicked.connect(self.close_requested.emit)

        header.addWidget(title)
        header.addWidget(self._count, 1)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self._log = QtWidgets.QPlainTextEdit()
        self._log.setObjectName("activityLog")
        self._log.setAccessibleName("Activity log entries")
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            f"background: transparent; border: none; color: {Color.LOG_FG};"
        )
        layout.addWidget(self._log, 1)

        self.set_count(0)
        self.setGeometry(self._closed_geometry())
        self.hide()

    def append(self, entry: LogEntry) -> None:
        scroll = self._log.verticalScrollBar()
        at_bottom = scroll.value() >= scroll.maximum() - 2
        color = {
            "info": Color.LOG_INFO,
            "ok": Color.LOG_OK,
            "warn": Color.LOG_WARN,
            "err": Color.LOG_ERR,
            "now": Color.LOG_NOW,
        }.get(entry.level, Color.LOG_INFO)
        html = (
            f"<span style='color:{Color.LOG_TS}'>{escape(entry.ts)}</span> "
            f"<span style='color:{color}'>{escape(entry.msg)}</span>"
        )
        self._log.appendHtml(html)
        if at_bottom:
            scroll.setValue(scroll.maximum())

    def set_count(self, count: int) -> None:
        self._count.setText(f"{int(count)} entries")

    def is_open(self) -> bool:
        return self._open

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        # Keep the overlay opaque when the parent window is repainted or grabbed.
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(Color.LOG_BG))
        painter.setPen(QtGui.QColor(Color.LOG_BORDER))
        painter.drawLine(0, 0, 0, self.height())
        super().paintEvent(event)

    def slide_in(self) -> None:
        self._open = True
        self._hide_timer.stop()
        self._animation.stop()
        self.setGeometry(self._closed_geometry())
        self.show()
        self.raise_()
        self._animation.setStartValue(self._closed_geometry())
        self._animation.setEndValue(self._open_geometry())
        self._animation.start()

    def slide_out(self) -> None:
        self._open = False
        self._animation.stop()
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(self._closed_geometry())
        self._animation.start()
        self._hide_timer.start(self._animation.duration() + 40)

    def sync_to_parent(self) -> None:
        self.setFixedHeight(self.parentWidget().height())
        if self._open:
            self.setGeometry(self._open_geometry())
        else:
            self.setGeometry(self._closed_geometry())

    def _on_animation_finished(self) -> None:
        self._hide_if_closed()

    def _hide_if_closed(self) -> None:
        if not self._open:
            self.hide()

    def _open_geometry(self) -> QtCore.QRect:
        parent = self.parentWidget()
        return QtCore.QRect(max(0, parent.width() - self.WIDTH), 0, self.WIDTH, parent.height())

    def _closed_geometry(self) -> QtCore.QRect:
        parent = self.parentWidget()
        return QtCore.QRect(parent.width(), 0, self.WIDTH, parent.height())
