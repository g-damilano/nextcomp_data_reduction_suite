from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets


@dataclass(frozen=True)
class MTDASurfaceEntry:
    surface_id: str
    label: str
    role: str
    member: str
    local_path: Path | None
    status: str = ""
    rc_status: str = ""

    @property
    def available(self) -> bool:
        return self.local_path is not None and self.local_path.exists()


@dataclass(frozen=True)
class MTDASurfacePackage:
    archive_path: Path
    extract_root: Path
    entries: tuple[MTDASurfaceEntry, ...]
    manifest_path: Path | None = None

    def entry(self, surface_id: str) -> MTDASurfaceEntry | None:
        for entry in self.entries:
            if entry.surface_id == surface_id:
                return entry
        return None


class MTDADashboardDialog(QtWidgets.QDialog):
    def __init__(self, package: MTDASurfacePackage, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.package = package
        self.surface_buttons: dict[str, QtWidgets.QPushButton] = {}
        self.setWindowTitle("MTDA package dashboard")
        self.resize(720, 460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel(f"<h2>{package.archive_path.name}</h2>")
        title.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "This archive contains multiple review surfaces. Choose the report or package view to open."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        path_label = QtWidgets.QLabel(str(package.archive_path))
        path_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        self.summary_table = QtWidgets.QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(["Surface", "Role", "Status", "Archive member"])
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.summary_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.summary_table, 1)
        self._populate_summary()

        button_grid = QtWidgets.QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(8)
        for index, entry in enumerate(package.entries):
            button = QtWidgets.QPushButton(f"Open {entry.label}")
            button.setEnabled(entry.available)
            button.setToolTip(entry.member if entry.available else f"{entry.member} is not available in this MTDA archive.")
            button.clicked.connect(lambda _checked=False, surface_id=entry.surface_id: self.open_surface(surface_id))
            self.surface_buttons[entry.surface_id] = button
            button_grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(button_grid)

        footer = QtWidgets.QHBoxLayout()
        open_folder = QtWidgets.QPushButton("Open extracted MTDA folder")
        open_folder.clicked.connect(lambda: self._open_path(package.extract_root))
        footer.addWidget(open_folder)
        footer.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)

    def open_surface(self, surface_id: str) -> None:
        entry = self.package.entry(surface_id)
        if entry is None or not entry.available or entry.local_path is None:
            return
        self._open_path(entry.local_path)

    def _populate_summary(self) -> None:
        self.summary_table.setRowCount(len(self.package.entries))
        for row, entry in enumerate(self.package.entries):
            status = entry.status or ("available" if entry.available else "missing")
            if entry.rc_status:
                status = f"{status} ({entry.rc_status})"
            values = (entry.label, entry.role, status, entry.member)
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(value)
                self.summary_table.setItem(row, column, item)

    def _open_path(self, path: Path) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
