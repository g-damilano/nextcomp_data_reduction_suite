from __future__ import annotations


def test_drawer_hidden_by_default(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    MethodRunController(window)
    window.show()
    app.processEvents()

    assert window.log_drawer.isHidden()

    window.close()
    app.quit()


def test_l_shortcut_toggles_drawer(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    MethodRunController(window)
    window.show()
    app.processEvents()

    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_L)
    app.processEvents()
    assert window.log_drawer.isVisible()

    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_L)
    QtTest.QTest.qWait(320)
    assert window.log_drawer.isHidden()

    window.close()
    app.quit()


def test_append_entry_writes_html_with_level_color(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard._log import LogEntry
    from ui.method_run_wizard._tokens import Color
    from ui.method_run_wizard.components.activity_log_drawer import ActivityLogDrawer

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    parent = QtWidgets.QWidget()
    parent.resize(900, 600)
    drawer = ActivityLogDrawer(parent)

    drawer.append(LogEntry("12:34:56", "kept flagged run", "warn"))
    html = drawer._log.document().toHtml()

    assert "12:34:56" in html
    assert Color.LOG_WARN.lower() in html.lower()

    parent.close()
    app.quit()


def test_escape_closes_drawer_then_collapses_task(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    MethodRunController(window)
    window.show()
    app.processEvents()

    window.show_activity_log()
    app.processEvents()
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Escape)
    QtTest.QTest.qWait(320)
    assert window.log_drawer.isHidden()

    window.setup_spotlight.mapping_task.set_expanded(True)
    assert window.setup_spotlight.mapping_task.expanded
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Escape)
    assert not window.setup_spotlight.mapping_task.expanded

    window.close()
    app.quit()


def test_drawer_paints_opaque_background_in_parent_grab(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtGui, QtWidgets
    from ui.method_run_wizard._tokens import Color
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    MethodRunController(window)
    window.resize(1000, 720)
    window.show()
    app.processEvents()

    window.show_activity_log()
    QtTest.QTest.qWait(320)
    app.processEvents()
    pixmap = window.grab()
    inside_drawer = pixmap.toImage().pixelColor(window.width() - 20, 160)

    assert inside_drawer == QtGui.QColor(Color.LOG_BG)

    window.close()
    app.quit()


def test_log_push_updates_count_labels(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)

    window.setup_spotlight.save_bindings.emit()

    assert len(controller.state.activity_log) == 1
    assert window.status_log_button.text() == "Activity log · 1"
    assert window.decor_bottom.bar.activity_log_button.text() == "Activity log · 1"

    window.close()
    app.quit()
