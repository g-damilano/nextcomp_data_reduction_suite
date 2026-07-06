from __future__ import annotations

import pytest


def test_supplemental_files_dialog_can_list_files(monkeypatch, tmp_path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.supplemental import SupplementalFile
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from mtdp_enrichment.ui.supplemental_files_dialog import SupplementalFilesDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    note = tmp_path / "operator_notes.txt"
    note.write_text("notes", encoding="utf-8")

    dialog = SupplementalFilesDialog()
    dialog.set_files([SupplementalFile(note, scope="dataset", role="documents")])

    assert dialog.windowTitle() == "Manage supplemental files"
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "dataset"
    assert dialog.table.item(0, 2).text() == "operator_notes.txt"

    dialog.close()
    app.quit()
