from __future__ import annotations


def test_method_run_window_smoke(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()

    assert window.objectName() == ""
    assert window.findChild(QtWidgets.QFrame, "spotlight") is not None
    assert window.statusBar().findChildren(QtWidgets.QLabel)

    window.close()
    app.quit()
