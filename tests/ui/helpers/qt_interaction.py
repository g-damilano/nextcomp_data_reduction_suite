from __future__ import annotations

import time
from typing import Callable

import pytest


def ensure_qt_app(monkeypatch: pytest.MonkeyPatch):
    """Return Qt modules and an offscreen QApplication for interaction tests."""

    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
    from PySide6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return app, QtWidgets, QtCore, QtTest


def process_events_until(app, predicate: Callable[[], bool], *, timeout_ms: int = 2500) -> bool:
    """Spin the Qt event loop until a predicate is true or the timeout expires."""

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return predicate()


def table_values(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in range(table.rowCount()):
        values: list[str] = []
        for column in range(table.columnCount()):
            item = table.item(row, column)
            values.append(item.text() if item is not None else "")
        rows.append(values)
    return rows
