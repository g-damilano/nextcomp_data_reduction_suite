from __future__ import annotations

import pytest


def test_image_evidence_dialog_contains_disabled_future_controls(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.image_evidence_dialog import FUTURE_TOOLTIP, ImageEvidenceDialog
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = ImageEvidenceDialog()
    dialog.set_run_id("run_001")

    assert dialog.panel is not None
    assert "run_001" in dialog.windowTitle()
    assert not dialog.extract_button.isEnabled()
    assert not dialog.run_metrology_button.isEnabled()
    assert dialog.extract_button.toolTip() == FUTURE_TOOLTIP
    assert dialog.run_metrology_button.toolTip() == FUTURE_TOOLTIP

    dialog.close()
    app.quit()
