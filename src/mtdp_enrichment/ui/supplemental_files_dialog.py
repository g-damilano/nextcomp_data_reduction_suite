from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.supplemental import SupplementalFile
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from mtdp_enrichment.ui.resources import app_icon


class SupplementalFilesDialog(QtWidgets.QDialog):
    add_requested = QtCore.pyqtSignal()
    remove_requested = QtCore.pyqtSignal(int)
    preview_requested = QtCore.pyqtSignal(int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage supplemental files")
        self.setWindowIcon(app_icon())
        self.resize(760, 380)
        self._files: list[SupplementalFile] = []

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Scope", "Role", "File", "Notes"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = QtWidgets.QPushButton("Add supplemental file...")
        self.remove_button = QtWidgets.QPushButton("Remove supplemental file")
        self.preview_button = QtWidgets.QPushButton("Preview/open")
        self.close_button = QtWidgets.QPushButton("Close")
        self.add_button.clicked.connect(self.add_requested)
        self.remove_button.clicked.connect(self._remove_clicked)
        self.preview_button.clicked.connect(self._preview_clicked)
        self.close_button.clicked.connect(self.accept)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.preview_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)

    def set_files(self, files: list[SupplementalFile] | tuple[SupplementalFile, ...]) -> None:
        self._files = list(files)
        self.refresh()

    def selected_index(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def refresh(self) -> None:
        self.table.setRowCount(len(self._files))
        for row, item in enumerate(self._files):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.scope))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.role))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(Path(item.source_path).name))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.notes or ""))
        self.table.resizeColumnsToContents()

    def _remove_clicked(self) -> None:
        index = self.selected_index()
        if index is not None:
            self.remove_requested.emit(index)

    def _preview_clicked(self) -> None:
        index = self.selected_index()
        if index is not None:
            self.preview_requested.emit(index)


def supplemental_file_from_dialog(
    parent: QtWidgets.QWidget,
    path: Path,
    *,
    run_id: str | None = None,
) -> SupplementalFile | None:
    scopes = ["dataset", "run", "schema/mapping support", "calibration/equipment evidence", "other"]
    scope, ok = QtWidgets.QInputDialog.getItem(parent, "Supplemental file scope", "Scope:", scopes, 0, False)
    if not ok:
        return None
    roles = {
        "dataset": "documents",
        "run": "run_evidence",
        "schema/mapping support": "mapping_support",
        "calibration/equipment evidence": "calibration",
        "other": "other",
    }
    notes, notes_ok = QtWidgets.QInputDialog.getText(parent, "Supplemental file notes", "Notes:", text="")
    return SupplementalFile(
        source_path=path,
        scope=scope,
        role=roles.get(scope, "other"),
        run_id=run_id if scope == "run" else None,
        notes=notes if notes_ok and notes.strip() else None,
    )


def open_supplemental_file(file: SupplementalFile) -> None:
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(file.source_path)))
