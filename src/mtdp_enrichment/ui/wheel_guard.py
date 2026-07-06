from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class WheelGuard(QtCore.QObject):
    """Prevent accidental combo/spin/date changes while scrolling a form."""

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Wheel and isinstance(watched, QtWidgets.QWidget):
            if not watched.hasFocus():
                event.ignore()
                return True
        return super().eventFilter(watched, event)


def install_wheel_guard(widget: QtWidgets.QWidget) -> None:
    guard = WheelGuard(widget)
    widget.installEventFilter(guard)
    setattr(widget, "_mtdp_wheel_guard", guard)
