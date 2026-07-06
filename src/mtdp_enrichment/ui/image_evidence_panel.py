from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class ImageEvidencePanel(QtWidgets.QWidget):
    add_requested = QtCore.pyqtSignal()
    remove_requested = QtCore.pyqtSignal(int)
    preview_requested = QtCore.pyqtSignal(int)
    images_dropped = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._images: list[RunImageEvidence] = []
        self.setAcceptDrops(True)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["View", "File", "Role", "Metrology"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = QtWidgets.QPushButton("Add Image")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.preview_button = QtWidgets.QPushButton("Preview")
        self.add_button.clicked.connect(self.add_requested)
        self.remove_button.clicked.connect(self._remove_clicked)
        self.preview_button.clicked.connect(self._preview_clicked)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.preview_button)
        buttons.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

    def set_images(self, images: list[RunImageEvidence] | tuple[RunImageEvidence, ...]) -> None:
        self._images = list(images)
        self.refresh()

    def selected_index(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def refresh(self) -> None:
        self.table.setRowCount(len(self._images))
        for row, image in enumerate(self._images):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(image.view))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(Path(image.source_path).name))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(image.role))
            self.table.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem("yes" if image.used_for_metrology else "no"),
            )
        self.table.resizeColumnsToContents()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.images_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _remove_clicked(self) -> None:
        index = self.selected_index()
        if index is not None:
            self.remove_requested.emit(index)

    def _preview_clicked(self) -> None:
        index = self.selected_index()
        if index is not None:
            self.preview_requested.emit(index)
