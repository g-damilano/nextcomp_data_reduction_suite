from __future__ import annotations

import pytest


def test_about_dialog_and_icon_resources(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.about_dialog import AboutDialog
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from mtdp_enrichment.ui.resources import app_icon, icon_path

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = AboutDialog()

    labels = "\n".join(label.text() for label in dialog.findChildren(QtWidgets.QLabel))
    assert "Data Reduction Pipeline" in labels
    assert "Giacomo Damilano" in labels
    assert "giacomo.damilano@gmail.com" in labels
    assert "EP/T011653/1" in labels
    assert "NextCOMP" in labels
    assert "Qt backend" not in labels
    assert "Python" not in labels
    assert "Schema library" not in labels
    assert "Package format" not in labels
    assert "Status" not in labels
    assert dialog.findChildren(QtWidgets.QLabel, "nextcompLogo")
    assert icon_path() is not None
    assert not app_icon().isNull()

    dialog.close()
    app.quit()


def test_main_window_has_menu_tabs_about_and_no_backend_label(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert {"File", "Edit", "View", "Group", "Run", "Tools", "Help"}.issubset(menu_titles)
    assert "about" in window.actions
    assert window.tabs.count() == 2
    assert window.tabs.tabText(0) == "Dataset"
    assert window.tabs.tabText(1) == "Run analysis inputs"
    assert not window.tabs.isTabEnabled(1)
    assert not window.windowIcon().isNull()
    assert not window.findChildren(QtWidgets.QLabel, "stateLabel")

    window.close()
    app.quit()
