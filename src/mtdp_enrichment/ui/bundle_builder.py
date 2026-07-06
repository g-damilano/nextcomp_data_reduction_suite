from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import import FieldConflict, ImportedFieldCandidate
from mtdp_enrichment.grouping import GroupingInput, GroupingProposal, SampleNameCanonicalizer, build_source_identities
from mtdp_enrichment.grouping.source_identity import SourceIdentity
from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.supplemental import SupplementalFile
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets


STATUS_COLORS = {
    "ready": "#dff3e4",
    "needs input": "#f7d6d1",
    "validation issue": "#f6e5b8",
    "packaged": "#d8ece8",
    "excluded": "#e5e7eb",
    "parsed": "#eef2f7",
    "unassigned": "#e5e7eb",
    "unknown": "#f3f4f6",
}


@dataclass(slots=True)
class BundleRunState:
    run_id: str
    source_path: Path
    parsed: ParsedSampleRecord
    enrichment: dict[str, EnrichedFieldValue] = field(default_factory=dict)
    field_units: dict[str, str | None] = field(default_factory=dict)
    status: str = "parsed"
    confidence: float = 0.0
    reason: str = ""
    evidence: tuple[str, ...] = ()
    sidecar_path: Path | None = None
    sidecar_import_status: str = "No YAML"
    sidecar_conflicts: list[FieldConflict] = field(default_factory=list)
    sidecar_unknown_keys: list[str] = field(default_factory=list)
    sidecar_mapping_profile_id: str | None = None
    sidecar_mapping_profile_path: Path | None = None
    sidecar_import_mode: str | None = None
    images: list[RunImageEvidence] = field(default_factory=list)
    supplemental_files: list[SupplementalFile] = field(default_factory=list)


@dataclass(slots=True)
class BundleState:
    bundle_key: str
    display_name: str
    runs: list[BundleRunState] = field(default_factory=list)
    dataset_enrichment: dict[str, EnrichedFieldValue] = field(default_factory=dict)
    dataset_units: dict[str, str | None] = field(default_factory=dict)
    supplemental_files: list[SupplementalFile] = field(default_factory=list)
    removed_runs: list[dict[str, str]] = field(default_factory=list)
    manual_corrections: int = 0
    status: str = "parsed"
    reason: str = ""


class BundleTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, owner: "BundleBuilder") -> None:
        super().__init__()
        self.owner = owner

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
        try:
            point = event.position().toPoint()
        except AttributeError:
            point = event.pos()
        target = self.itemAt(point)
        target_key = None
        if target is not None:
            target_key = target.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if target.parent() is not None:
                target_key = target.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
        if event.mimeData().hasUrls():
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            self.owner.source_files_dropped.emit(paths, target_key)
            event.acceptProposedAction()
            return
        sources = [
            Path(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
            for item in self.selectedItems()
            if item.parent() is not None and item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        ]
        if not sources:
            return super().dropEvent(event)
        if target is None:
            return super().dropEvent(event)
        if target_key == "__excluded__":
            self.owner.exclude_runs(sources)
        elif target_key:
            self.owner.move_runs_to_bundle(sources, str(target_key))
        event.acceptProposedAction()
        QtCore.QTimer.singleShot(0, self.owner.refresh)


class BundleBuilder(QtWidgets.QWidget):
    selection_changed = QtCore.pyqtSignal()
    bundles_changed = QtCore.pyqtSignal()
    source_files_dropped = QtCore.pyqtSignal(object, object)
    run_open_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.bundles: list[BundleState] = []
        self.excluded_runs: list[BundleRunState] = []
        self._canonicalizer = SampleNameCanonicalizer()
        self.tree = BundleTreeWidget(self)
        self.tree.setHeaderLabels(["Group / run", "Status", "Confidence", "Reason"])
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.tree.setAcceptDrops(True)
        self.tree.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.tree.itemSelectionChanged.connect(self.selection_changed)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        header = self.tree.header()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.new_button = QtWidgets.QPushButton("New Group...")
        self.rename_button = QtWidgets.QPushButton("Rename")
        self.exclude_button = QtWidgets.QPushButton("Unassign")
        self.include_button = QtWidgets.QPushButton("Restore...")
        self.move_button = QtWidgets.QPushButton("Move...")
        self.up_button = QtWidgets.QPushButton("Up")
        self.down_button = QtWidgets.QPushButton("Down")
        self.delete_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Del"), self.tree)
        self.delete_shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)

        self.new_button.clicked.connect(self.prompt_create_bundle)
        self.rename_button.clicked.connect(lambda: self.rename_selected_bundle())
        self.exclude_button.clicked.connect(self.exclude_selected_run)
        self.include_button.clicked.connect(self.include_selected_run)
        self.move_button.clicked.connect(self.move_selected_run_dialog)
        self.up_button.clicked.connect(lambda: self.reorder_selected_run(-1))
        self.down_button.clicked.connect(lambda: self.reorder_selected_run(1))
        self.delete_shortcut.activated.connect(self.delete_selected_items)

        buttons = QtWidgets.QHBoxLayout()
        for button in (
            self.new_button,
            self.rename_button,
            self.move_button,
            self.exclude_button,
            self.include_button,
            self.up_button,
            self.down_button,
        ):
            buttons.addWidget(button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)

    def load_proposal(self, proposal: GroupingProposal, inputs: list[GroupingInput]) -> None:
        input_by_path = {item.source_path: item for item in inputs}
        self.bundles.clear()
        self.excluded_runs.clear()
        for bundle in proposal.bundles:
            state = BundleState(bundle.bundle_key, bundle.display_name)
            for index, assignment in enumerate(bundle.assignments, start=1):
                grouping_input = input_by_path[assignment.source_path]
                state.runs.append(
                    _run_state_from_grouping(
                        grouping_input,
                        run_id=f"run_{index:03d}",
                        confidence=assignment.confidence,
                        reason=assignment.reason,
                        evidence=assignment.evidence,
                    )
                )
                _merge_dataset_enrichment(state, grouping_input)
            self.bundles.append(state)

        for item in proposal.unassigned:
            self.excluded_runs.append(
                BundleRunState(
                    run_id=f"run_{len(self.excluded_runs) + 1:03d}",
                    source_path=item.source_path,
                    parsed=item.parsed,
                    enrichment=_imported_enrichment(item),
                    status="unassigned",
                    reason="manual required",
                    sidecar_path=item.supplemental_import.source_path if item.supplemental_import is not None else None,
                    sidecar_import_status=_sidecar_status(item),
                    sidecar_conflicts=list(item.supplemental_import.conflicts) if item.supplemental_import is not None else [],
                    sidecar_unknown_keys=list(item.supplemental_import.unknown_keys) if item.supplemental_import is not None else [],
                )
            )
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def add_input_to_bundle(self, grouping_input: GroupingInput, bundle_key: str | None = None) -> BundleRunState:
        bundle = self.bundle_by_key(bundle_key) if bundle_key else (self.bundles[0] if self.bundles else None)
        if bundle is None:
            bundle = self.create_bundle(grouping_input.source_path.parent.name or "New group")
        run = _run_state_from_grouping(
            grouping_input,
            run_id=f"run_{len(bundle.runs) + 1:03d}",
            status="parsed",
            reason="manually added",
        )
        bundle.runs.append(run)
        _merge_dataset_enrichment(bundle, grouping_input)
        bundle.manual_corrections += 1
        self._renumber_runs(bundle)
        self.refresh()
        self.bundles_changed.emit()
        return run

    def selected_bundle(self) -> BundleState | None:
        item = self._selected_item()
        if item is None:
            return None
        bundle_key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if item.parent() is not None:
            bundle_key = item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
        return self.bundle_by_key(str(bundle_key)) if bundle_key else None

    def selected_bundles(self) -> list[BundleState]:
        bundles: list[BundleState] = []
        seen: set[str] = set()
        for item in self.tree.selectedItems():
            if item.parent() is not None:
                continue
            bundle_key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not bundle_key or str(bundle_key) == "__excluded__" or str(bundle_key) in seen:
                continue
            bundle = self.bundle_by_key(str(bundle_key))
            if bundle is not None:
                bundles.append(bundle)
                seen.add(str(bundle_key))
        if not bundles:
            item = self._selected_item()
            if item is not None and item.parent() is None:
                bundle_key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if bundle_key and str(bundle_key) != "__excluded__":
                    bundle = self.bundle_by_key(str(bundle_key))
                    if bundle is not None:
                        bundles.append(bundle)
        return bundles

    def selected_run(self) -> BundleRunState | None:
        item = self._selected_item()
        if item is None or item.parent() is None:
            return None
        source = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return self.run_by_source(Path(source)) if source else None

    def selected_runs(self) -> list[BundleRunState]:
        runs: list[BundleRunState] = []
        seen: set[Path] = set()
        for item in self.tree.selectedItems():
            if item.parent() is None:
                continue
            source = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not source:
                continue
            path = Path(source)
            if path in seen:
                continue
            run = self.run_by_source(path)
            if run is not None:
                runs.append(run)
                seen.add(path)
        if not runs:
            selected = self.selected_run()
            if selected is not None:
                runs.append(selected)
        return runs

    def selected_run_bundle(self) -> BundleState | None:
        item = self._selected_item()
        if item is None or item.parent() is None:
            return None
        parent_key = item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
        return self.bundle_by_key(str(parent_key)) if parent_key else None

    def selected_run_bundles(self) -> list[BundleState]:
        bundles: list[BundleState] = []
        seen: set[str] = set()
        for item in self.tree.selectedItems():
            if item.parent() is None:
                continue
            parent_key = item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not parent_key or str(parent_key) in seen:
                continue
            bundle = self.bundle_by_key(str(parent_key))
            if bundle is not None:
                bundles.append(bundle)
                seen.add(str(parent_key))
        if not bundles:
            selected = self.selected_run_bundle()
            if selected is not None:
                bundles.append(selected)
        return bundles

    def prompt_create_bundle(self) -> BundleState | None:
        suggestions = [bundle.display_name for bundle in self.bundles]
        default = suggestions[0] if suggestions else ""
        name, ok = QtWidgets.QInputDialog.getText(self, "Create group", "Group name:", text=default)
        if not ok:
            return None
        name = name.strip()
        if not name:
            return None
        return self.create_bundle(name)

    def create_bundle(self, name: str) -> BundleState:
        key = self._unique_key(name)
        bundle = BundleState(key, name, manual_corrections=1)
        self.bundles.append(bundle)
        self.refresh()
        self.bundles_changed.emit()
        return bundle

    def rename_selected_bundle(self, new_name: str | None = None) -> None:
        bundle = self.selected_bundle()
        if bundle is None:
            return
        if new_name is None:
            new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename group", "Group name:", text=bundle.display_name)
            if not ok:
                return
        self.rename_bundle(bundle.bundle_key, new_name)

    def rename_bundle(self, bundle_key: str, new_name: str) -> None:
        bundle = self.bundle_by_key(bundle_key)
        if bundle is None:
            return
        bundle.display_name = new_name.strip() or bundle.display_name
        bundle.bundle_key = self._unique_key(bundle.display_name, current=bundle)
        bundle.manual_corrections += 1
        self.refresh()
        self.bundles_changed.emit()

    def merge_bundles(self, source_key: str, target_key: str) -> None:
        source = self.bundle_by_key(source_key)
        target = self.bundle_by_key(target_key)
        if source is None or target is None or source is target:
            return
        target.runs.extend(source.runs)
        target.manual_corrections += source.manual_corrections + 1
        self.bundles.remove(source)
        self._renumber_runs(target)
        self.refresh()
        self.bundles_changed.emit()

    def split_run_to_new_bundle(self, source_path: Path, new_name: str) -> None:
        run, bundle = self._detach_run(source_path)
        if run is None:
            return
        new_bundle = self.create_bundle(new_name)
        new_bundle.runs.append(run)
        new_bundle.manual_corrections += 1
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def split_selected_run_dialog(self) -> None:
        run = self.selected_run()
        if run is None:
            return
        default = run.source_path.stem
        name, ok = QtWidgets.QInputDialog.getText(self, "Split run to new group", "New group name:", text=default)
        if ok and name.strip():
            self.split_run_to_new_bundle(run.source_path, name.strip())

    def merge_selected_bundles_dialog(self) -> None:
        return

    def move_run_to_bundle(self, source_path: Path, target_key: str) -> None:
        self.move_runs_to_bundle([source_path], target_key)

    def move_runs_to_bundle(self, source_paths: list[Path], target_key: str) -> None:
        target = self.bundle_by_key(target_key)
        if target is None:
            return
        moved = 0
        touched_sources: set[str] = set()
        for source_path in source_paths:
            run, source_bundle = self._detach_run(source_path)
            if run is None:
                continue
            target.runs.append(run)
            moved += 1
            if source_bundle is not None:
                source_bundle.manual_corrections += 1
                touched_sources.add(source_bundle.bundle_key)
        if moved == 0:
            return
        target.manual_corrections += moved
        if target.bundle_key in touched_sources:
            target.manual_corrections += 1
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def move_selected_run_dialog(self) -> None:
        run = self.selected_run()
        if run is None:
            return
        bundle_names = [bundle.display_name for bundle in self.bundles]
        if not bundle_names:
            return
        create_label = "<Create new group...>"
        choices = bundle_names + [create_label]
        name, ok = QtWidgets.QInputDialog.getItem(self, "Move run", "Group:", choices, 0, False)
        if ok:
            if name == create_label:
                bundle = self.prompt_create_bundle()
                if bundle is not None:
                    self.move_run_to_bundle(run.source_path, bundle.bundle_key)
                return
            target = next((bundle for bundle in self.bundles if bundle.display_name == name), None)
            if target is not None:
                self.move_run_to_bundle(run.source_path, target.bundle_key)

    def exclude_selected_run(self) -> None:
        runs = self.selected_runs()
        if runs:
            self.exclude_runs([run.source_path for run in runs])

    def delete_selected_items(self) -> None:
        bundles = self.selected_bundles()
        if bundles:
            self.remove_bundles_to_unassigned(bundles)
            return
        runs = self.selected_runs()
        if runs:
            self.exclude_runs([run.source_path for run in runs])

    def exclude_run(self, source_path: Path) -> None:
        self.exclude_runs([source_path])

    def exclude_runs(self, source_paths: list[Path]) -> None:
        moved = 0
        for source_path in source_paths:
            run, bundle = self._detach_run(source_path)
            if run is None:
                continue
            run.status = "unassigned"
            self.excluded_runs.append(run)
            moved += 1
            if bundle is not None:
                bundle.manual_corrections += 1
        if moved == 0:
            return
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def include_selected_run(self) -> None:
        run = self.selected_run()
        if run is None or run not in self.excluded_runs:
            return
        bundle_names = [bundle.display_name for bundle in self.bundles]
        create_label = "<Create new group...>"
        choices = bundle_names + [create_label]
        name, ok = QtWidgets.QInputDialog.getItem(self, "Restore unassigned run", "Target group:", choices, 0, False)
        if not ok:
            return
        if name == create_label:
            target = self.prompt_create_bundle()
        else:
            target = next((bundle for bundle in self.bundles if bundle.display_name == name), None)
        if target is not None:
            self.include_excluded_run(run.source_path, target.bundle_key)

    def include_excluded_run(self, source_path: Path, target_key: str) -> None:
        run = next((item for item in self.excluded_runs if item.source_path == source_path), None)
        target = self.bundle_by_key(target_key)
        if run is None or target is None:
            return
        self.excluded_runs.remove(run)
        run.status = "parsed"
        target.runs.append(run)
        target.manual_corrections += 1
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def reorder_selected_run(self, delta: int) -> None:
        run = self.selected_run()
        bundle = self.selected_run_bundle()
        if run is None or bundle is None:
            return
        index = bundle.runs.index(run)
        new_index = max(0, min(len(bundle.runs) - 1, index + delta))
        if new_index == index:
            return
        bundle.runs.pop(index)
        bundle.runs.insert(new_index, run)
        bundle.manual_corrections += 1
        self._renumber_runs(bundle)
        self.refresh()
        self.bundles_changed.emit()

    def set_run_id(self, source_path: Path, run_id: str) -> None:
        run = self.run_by_source(source_path)
        if run is None:
            return
        run.run_id = run_id
        self.refresh()
        self.bundles_changed.emit()

    def bundle_by_key(self, bundle_key: str) -> BundleState | None:
        if bundle_key == "__excluded__":
            return None
        return next((bundle for bundle in self.bundles if bundle.bundle_key == bundle_key), None)

    def run_by_source(self, source_path: Path) -> BundleRunState | None:
        for bundle in self.bundles:
            for run in bundle.runs:
                if run.source_path == source_path:
                    return run
        return next((run for run in self.excluded_runs if run.source_path == source_path), None)

    def all_runs(self) -> list[BundleRunState]:
        runs: list[BundleRunState] = []
        for bundle in self.bundles:
            runs.extend(bundle.runs)
        runs.extend(self.excluded_runs)
        return runs

    def refresh(self) -> None:
        state = self._capture_tree_state()
        self.tree.clear()
        source_identities = build_source_identities(run.source_path for run in self.all_runs())
        for bundle in self.bundles:
            bundle_status = self._bundle_status(bundle)
            bundle_reason = bundle.reason or bundle_status
            bundle_item = QtWidgets.QTreeWidgetItem([bundle.display_name, f"{len(bundle.runs)} run(s)", "", bundle_reason])
            bundle_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, bundle.bundle_key)
            bundle_item.setExpanded(True)
            self._apply_item_color(bundle_item, bundle_status)
            self.tree.addTopLevelItem(bundle_item)
            for run in bundle.runs:
                self._add_run_item(bundle_item, run, source_identities)
        excluded = QtWidgets.QTreeWidgetItem(["Unassigned", f"{len(self.excluded_runs)} run(s)", "", "not in a dataset"])
        excluded.setData(0, QtCore.Qt.ItemDataRole.UserRole, "__excluded__")
        excluded.setExpanded(True)
        self._apply_item_color(excluded, "unassigned")
        self.tree.addTopLevelItem(excluded)
        for run in self.excluded_runs:
            self._add_run_item(excluded, run, source_identities)
        self._resize_columns()
        self._restore_tree_state(state)

    def select_first_bundle(self) -> None:
        item = self.tree.topLevelItem(0)
        if item is not None:
            self.tree.setCurrentItem(item)
            item.setSelected(True)

    def expand_all(self) -> None:
        self.tree.expandAll()

    def collapse_all(self) -> None:
        self.tree.collapseAll()

    def _add_run_item(
        self,
        parent: QtWidgets.QTreeWidgetItem,
        run: BundleRunState,
        source_identities: dict[Path, SourceIdentity] | None = None,
    ) -> None:
        status = run.status
        if run.sidecar_conflicts:
            status = f"{status}; YAML review"
        elif run.sidecar_import_status not in {"No YAML", ""}:
            status = f"{status}; {run.sidecar_import_status}"
        if run.images:
            status = f"{status}; {len(run.images)} image(s)"
        identity = (source_identities or {}).get(run.source_path.resolve())
        display_name = identity.source_display_name if identity is not None else run.source_path.name
        item = QtWidgets.QTreeWidgetItem(
            [
                f"{run.run_id}  {display_name}",
                status,
                f"{run.confidence:.0%}" if run.confidence else "",
                run.reason,
            ]
        )
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(run.source_path))
        if identity is not None:
            item.setToolTip(
                0,
                f"{identity.source_relative_path}\n{identity.source_path}",
            )
        else:
            item.setToolTip(0, str(run.source_path))
        self._apply_item_color(item, run.status)
        parent.addChild(item)

    def _bundle_status(self, bundle: BundleState) -> str:
        if bundle.status in STATUS_COLORS and bundle.status != "parsed":
            return bundle.status
        if not bundle.runs:
            return "unknown"
        statuses = {run.status for run in bundle.runs}
        if statuses == {"packaged"}:
            return "packaged"
        if statuses <= {"ready", "packaged"}:
            return "ready"
        if "needs input" in statuses:
            return "needs input"
        if "validation issue" in statuses:
            return "validation issue"
        return "unknown"

    def _apply_item_color(self, item: QtWidgets.QTreeWidgetItem, status: str) -> None:
        key = status.split(";", 1)[0].strip().casefold() or "unknown"
        color = QtGui.QColor(STATUS_COLORS.get(key, STATUS_COLORS["unknown"]))
        for column in range(self.tree.columnCount()):
            item.setBackground(column, QtGui.QBrush(color))

    def _resize_columns(self) -> None:
        for column in range(1, self.tree.columnCount()):
            self.tree.resizeColumnToContents(column)

    def _capture_tree_state(self) -> dict[str, object]:
        expanded = set()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item is not None and item.isExpanded():
                expanded.add(str(item.data(0, QtCore.Qt.ItemDataRole.UserRole)))
        selected = None
        selected_items: set[str] = set()
        item = self._selected_item()
        if item is not None:
            selected = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        for item in self.tree.selectedItems():
            selected_items.add(str(item.data(0, QtCore.Qt.ItemDataRole.UserRole)))
        return {
            "expanded": expanded,
            "selected": selected,
            "selected_items": selected_items,
            "vertical": self.tree.verticalScrollBar().value(),
            "horizontal": self.tree.horizontalScrollBar().value(),
        }

    def _restore_tree_state(self, state: dict[str, object]) -> None:
        expanded = state.get("expanded", set())
        selected = state.get("selected")
        selected_items = {str(item) for item in state.get("selected_items", set()) or set()}
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item is None:
                continue
            key = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
            item.setExpanded(key in expanded or not expanded)
            if selected == key:
                self.tree.setCurrentItem(item)
            if key in selected_items:
                item.setSelected(True)
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                child_key = str(child.data(0, QtCore.Qt.ItemDataRole.UserRole))
                if selected == child_key:
                    self.tree.setCurrentItem(child)
                if child_key in selected_items:
                    child.setSelected(True)
        self.tree.blockSignals(False)
        self.tree.verticalScrollBar().setValue(int(state.get("vertical", 0)))
        self.tree.horizontalScrollBar().setValue(int(state.get("horizontal", 0)))

    def _show_context_menu(self, point) -> None:
        item = self.tree.itemAt(point)
        if item is None:
            return
        if not item.isSelected():
            self.tree.setCurrentItem(item)
        menu = QtWidgets.QMenu(self)
        is_bundle = item.parent() is None
        is_excluded = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole)) == "__excluded__" or (
            item.parent() is not None
            and str(item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)) == "__excluded__"
        )
        if is_bundle and not is_excluded:
            menu.addAction("Rename group...", self.rename_selected_bundle)
            menu.addAction("Create new group...", self.prompt_create_bundle)
            if item.childCount() == 0:
                menu.addAction("Delete empty group", self.delete_selected_empty_bundle)
            else:
                menu.addAction("Remove group and unassign runs", self.remove_selected_bundle_to_unassigned)
        elif is_excluded:
            menu.addAction("Restore to group...", self.include_selected_run)
        else:
            menu.addAction("Move to group...", self.move_selected_run_dialog)
            menu.addAction("Unassign from group", self.exclude_selected_run)
            menu.addAction("Move up", lambda: self.reorder_selected_run(-1))
            menu.addAction("Move down", lambda: self.reorder_selected_run(1))
        menu.exec(self.tree.viewport().mapToGlobal(point))

    def delete_selected_empty_bundle(self) -> None:
        bundle = self.selected_bundle()
        if bundle is None or bundle.runs:
            return
        self.bundles.remove(bundle)
        self.refresh()
        self.bundles_changed.emit()

    def remove_selected_bundle_to_unassigned(self) -> None:
        bundles = self.selected_bundles()
        if not bundles:
            bundle = self.selected_bundle()
            bundles = [bundle] if bundle is not None else []
        self.remove_bundles_to_unassigned(bundles)

    def remove_bundles_to_unassigned(self, bundles: list[BundleState]) -> None:
        changed = False
        for bundle in list(bundles):
            if bundle not in self.bundles:
                continue
            if bundle.runs:
                runs = list(bundle.runs)
                bundle.runs.clear()
                for run in runs:
                    run.status = "unassigned"
                    self.excluded_runs.append(run)
            self.bundles.remove(bundle)
            changed = True
        if not changed:
            return
        self._renumber_all_runs()
        self.refresh()
        self.bundles_changed.emit()

    def _detach_run(self, source_path: Path) -> tuple[BundleRunState | None, BundleState | None]:
        for bundle in self.bundles:
            for run in list(bundle.runs):
                if run.source_path == source_path:
                    bundle.runs.remove(run)
                    return run, bundle
        for run in list(self.excluded_runs):
            if run.source_path == source_path:
                self.excluded_runs.remove(run)
                return run, None
        return None, None

    def _renumber_all_runs(self) -> None:
        for bundle in self.bundles:
            self._renumber_runs(bundle)
        for index, run in enumerate(self.excluded_runs, start=1):
            run.run_id = f"run_{index:03d}"

    def _renumber_runs(self, bundle: BundleState) -> None:
        for index, run in enumerate(bundle.runs, start=1):
            run.run_id = f"run_{index:03d}"

    def _unique_key(self, name: str, current: BundleState | None = None) -> str:
        base = self._canonicalizer.canonicalize(name).canonical_key or "group"
        key = base
        counter = 2
        existing = {bundle.bundle_key for bundle in self.bundles if bundle is not current}
        while key in existing:
            key = f"{base} {counter}"
            counter += 1
        return key

    def _selected_item(self) -> QtWidgets.QTreeWidgetItem | None:
        current = self.tree.currentItem()
        if current is not None and current.isSelected():
            return current
        items = self.tree.selectedItems()
        return items[0] if items else current

    def _double_clicked(self, item: QtWidgets.QTreeWidgetItem, _column: int = 0) -> None:
        if item.parent() is None and item.data(0, QtCore.Qt.ItemDataRole.UserRole) != "__excluded__":
            self.rename_selected_bundle()
            return
        if item.parent() is not None:
            source = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            run = self.run_by_source(Path(source)) if source else None
            if run is not None:
                self.run_open_requested.emit(run)


def _imported_enrichment(grouping_input: GroupingInput) -> dict[str, EnrichedFieldValue]:
    if grouping_input.supplemental_import is None:
        return {}
    values: dict[str, EnrichedFieldValue] = {}
    for field_id, candidate in grouping_input.supplemental_import.imported_fields.items():
        if isinstance(candidate, ImportedFieldCandidate):
            values[field_id] = EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
    return values


def _run_state_from_grouping(
    grouping_input: GroupingInput,
    *,
    run_id: str,
    status: str = "parsed",
    confidence: float = 0.0,
    reason: str = "",
    evidence: tuple[str, ...] = (),
) -> BundleRunState:
    result = grouping_input.supplemental_import
    return BundleRunState(
        run_id=run_id,
        source_path=grouping_input.source_path,
        parsed=grouping_input.parsed,
        enrichment=_imported_enrichment(grouping_input),
        status=status,
        confidence=confidence,
        reason=reason,
        evidence=evidence,
        sidecar_path=result.source_path if result is not None else None,
        sidecar_import_status=_sidecar_status(grouping_input),
        sidecar_conflicts=list(result.conflicts) if result is not None else [],
        sidecar_unknown_keys=list(result.unknown_keys) if result is not None else [],
        sidecar_mapping_profile_id=result.mapping_profile_id if result is not None else None,
        sidecar_mapping_profile_path=result.mapping_profile_path if result is not None else None,
        sidecar_import_mode=_import_mode(result),
        images=[
            RunImageEvidence(
                source_path=item.path,
                view=item.view,
                role=item.role,
                used_for_metrology=item.used_for_metrology,
                notes=item.notes,
            )
            for item in (result.image_references if result is not None else ())
        ],
    )


def _merge_dataset_enrichment(bundle: BundleState, grouping_input: GroupingInput) -> None:
    result = grouping_input.supplemental_import
    if result is None:
        return
    dataset_like_ids = {"sample_type", "sample_type_key", "treatment", "material_label", "condition", "batch"}
    for field_id, candidate in result.imported_fields.items():
        if field_id not in dataset_like_ids and not candidate.source_key.startswith("dataset."):
            continue
        bundle.dataset_enrichment.setdefault(
            field_id,
            EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format),
        )


def _import_mode(result) -> str | None:
    if result is None or result.source_path is None:
        return None
    if result.mapping_profile_id:
        return "mapping_profile"
    if result.document is not None and result.document.is_canonical:
        return "canonical"
    if result.requires_mapping:
        return "mapping_required"
    return "alias"


def _sidecar_status(grouping_input: GroupingInput) -> str:
    result = grouping_input.supplemental_import
    if result is None or result.source_path is None:
        return "No YAML"
    if result.requires_mapping:
        return "Mapping required"
    if result.mapping_profile_id:
        return "Mapping applied"
    if result.conflicts:
        return "YAML needs review"
    if result.document is not None and result.document.is_canonical and result.imported_fields:
        return "Canonical YAML imported"
    if result.unknown_keys:
        return "Alias YAML imported; unknown keys"
    if result.imported_fields:
        return "Alias YAML imported"
    return "YAML detected"
