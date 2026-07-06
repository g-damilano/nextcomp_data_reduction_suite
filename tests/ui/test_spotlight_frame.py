from __future__ import annotations


def test_spotlight_frame_structure(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.components.spotlight_frame import SpotlightFrame, SpotlightHead

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    frame = SpotlightFrame()

    assert frame.objectName() == "spotlight"
    assert isinstance(frame.head, SpotlightHead)
    assert isinstance(frame.body, QtWidgets.QStackedWidget)
    assert isinstance(frame.foot, QtWidgets.QStackedWidget)
    assert frame.graphicsEffect() is not None

    frame.close()
    app.quit()


def test_method_run_window_set_scenario_updates_stacks(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.state import WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()

    assert window.spotlight.body.currentIndex() == 0
    assert window.spotlight.foot.currentIndex() == 0

    window.set_scenario(WizardScenario.REVIEW)

    assert window.spotlight.body.currentIndex() == 2
    assert window.spotlight.foot.currentIndex() == 2
    assert window.status_message.text() == "Review required"

    window.close()
    app.quit()
