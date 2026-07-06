from __future__ import annotations


def test_context_line_text_and_toggle(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard.components.decor_bottom import ContextLine

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    line = ContextLine()
    line.resize(360, 34)
    events: list[bool] = []
    line.toggled.connect(events.append)

    html = "<b>ISO 14126</b> · package.mtdp · mapping profile"
    line.set_text(html)
    line.show()
    app.processEvents()

    assert line._label.text() == html

    QtTest.QTest.mouseClick(line, QtCore.Qt.MouseButton.LeftButton)
    assert line._open is True
    assert events == [True]

    QtTest.QTest.mouseClick(line, QtCore.Qt.MouseButton.LeftButton)
    assert line._open is False
    assert events == [True, False]

    line.close()
