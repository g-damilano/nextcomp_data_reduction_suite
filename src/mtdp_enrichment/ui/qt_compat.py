from __future__ import annotations

import os

_REQUESTED_QT_API = os.environ.get("MTDP_QT_API", "").strip()
QT_API = _REQUESTED_QT_API or "PyQt6"

if QT_API == "PySide6":
    from PySide6 import QtCore, QtGui, QtWidgets

    QtCore.pyqtSignal = QtCore.Signal
    QtCore.pyqtSlot = QtCore.Slot
else:
    try:
        QT_API = "PyQt6"
        from PyQt6 import QtCore, QtGui, QtWidgets
    except ModuleNotFoundError:
        if _REQUESTED_QT_API == "PyQt6":
            raise
        QT_API = "PySide6"
        from PySide6 import QtCore, QtGui, QtWidgets

        QtCore.pyqtSignal = QtCore.Signal
        QtCore.pyqtSlot = QtCore.Slot

__all__ = ["QT_API", "QtCore", "QtGui", "QtWidgets"]
