from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class FolderTreeBrowser(QtWidgets.QTreeWidget):
    file_selected = QtCore.pyqtSignal(Path)
    paths_dropped = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["File", "State"])
        self.setColumnWidth(0, 280)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.itemActivated.connect(self._emit_file)
        self.itemClicked.connect(self._emit_file)
        self._folder: Path | None = None

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def scan_folder(
        self,
        folder: str | Path,
        *,
        supported_suffixes: tuple[str, ...],
        package_statuses: dict[str, str] | None = None,
    ) -> None:
        self.clear()
        self._folder = Path(folder)
        package_statuses = package_statuses or {}
        root = QtWidgets.QTreeWidgetItem([self._folder.name, "folder"])
        root.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(self._folder))
        root.setExpanded(True)
        self.addTopLevelItem(root)
        self._add_children(root, self._folder, supported_suffixes, package_statuses)

    def set_file_state(self, path: str | Path, state: str) -> None:
        target = str(Path(path).resolve())
        iterator = QtWidgets.QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            item_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if item_path and str(Path(item_path).resolve()) == target:
                item.setText(1, state)
                return
            iterator += 1

    def _add_children(
        self,
        parent: QtWidgets.QTreeWidgetItem,
        folder: Path,
        supported_suffixes: tuple[str, ...],
        package_statuses: dict[str, str],
    ) -> None:
        try:
            children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError:
            return
        for child in children:
            if child.name == ".mtdp_index.sqlite":
                continue
            if child.is_dir():
                item = QtWidgets.QTreeWidgetItem([child.name, "folder"])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(child))
                parent.addChild(item)
                self._add_children(item, child, supported_suffixes, package_statuses)
                if item.childCount() == 0:
                    parent.removeChild(item)
                continue
            suffix = child.suffix.lower()
            if suffix not in supported_suffixes and suffix != ".mtdp":
                continue
            rel = child.relative_to(self._folder).as_posix() if self._folder else child.name
            state = package_statuses.get(rel, "packaged" if suffix == ".mtdp" else "unprocessed")
            if suffix in supported_suffixes and (child.with_suffix(".yaml").exists() or child.with_suffix(".yml").exists()):
                state = f"{state}; YAML"
            item = QtWidgets.QTreeWidgetItem([child.name, state])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(child))
            parent.addChild(item)

    def _emit_file(self, item: QtWidgets.QTreeWidgetItem) -> None:
        raw_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not raw_path:
            return
        path = Path(raw_path)
        if path.is_file():
            self.file_selected.emit(path)

    def mimeData(self, items: list[QtWidgets.QTreeWidgetItem]):  # type: ignore[override]
        mime = QtCore.QMimeData()
        urls = []
        for item in items:
            raw_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if raw_path and Path(raw_path).is_file():
                urls.append(QtCore.QUrl.fromLocalFile(str(raw_path)))
        mime.setUrls(urls)
        return mime
