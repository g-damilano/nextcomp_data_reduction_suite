from __future__ import annotations


def test_task_card_toggle_and_body_replacement(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard._icons import chev_down, chev_right
    from ui.method_run_wizard.components.task_card import TaskCard

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    card = TaskCard("mapping", "needs you", "Bind fields", "Why text")
    card.resize(420, 120)
    card.show()
    app.processEvents()

    assert card.expanded is False
    assert card._header._chev.text() == chev_right()

    QtTest.QTest.mouseClick(card._header, QtCore.Qt.MouseButton.LeftButton)
    assert card.expanded is True
    assert card._header._chev.text() == chev_down()

    QtTest.QTest.mouseClick(card._header, QtCore.Qt.MouseButton.LeftButton)
    assert card.expanded is False
    assert card._header._chev.text() == chev_right()

    old_body = QtWidgets.QLabel("old")
    new_body = QtWidgets.QLabel("new")
    card.set_body_widget(old_body)
    assert old_body.parent() is card._body

    card.set_body_widget(new_body)
    assert old_body.parent() is None
    assert new_body.parent() is card._body

    card.close()
    app.quit()
