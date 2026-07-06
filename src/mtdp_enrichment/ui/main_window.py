from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.grouping import GroupingInput, SampleTypeGrouper
from mtdp_enrichment.image_gateway import ImageEvidenceImporter, RunImageEvidence
from mtdp_enrichment.index import FolderIndex
from mtdp_enrichment.models import EnrichedFieldValue, ValidationResult
from mtdp_enrichment.package import MTDPPackageReader, MTDPPackageValidator, MTDPPackageWriter, MTDPSchema, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.services import GroupExporter, GroupLoader, GroupReprocessor, ValidationService
from mtdp_enrichment.services.group_state import GroupState, RunState
from mtdp_enrichment.supplemental import SupplementalFile
from mtdp_enrichment.ui.about_dialog import AboutDialog
from mtdp_enrichment.ui.bundle_builder import BundleBuilder, BundleRunState, BundleState
from mtdp_enrichment.ui.folder_tree import FolderTreeBrowser
from mtdp_enrichment.ui.image_evidence_dialog import ImageEvidenceDialog
from mtdp_enrichment.ui.menu_bar import install_menu_bar
from mtdp_enrichment.ui.mtda_dashboard_dialog import MTDADashboardDialog, MTDASurfaceEntry, MTDASurfacePackage
from mtdp_enrichment.ui.parser_review_dialog import ParserReviewDialog
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from mtdp_enrichment.ui.resources import app_icon
from mtdp_enrichment.ui.schema_form import SchemaForm
from mtdp_enrichment.ui.schema_selector import SchemaSelector
from mtdp_enrichment.ui.supplemental_files_dialog import (
    SupplementalFilesDialog,
    open_supplemental_file,
    supplemental_file_from_dialog,
)
from mtdp_enrichment.ui.yaml_mapping_dialog import YamlMappingDialog
from ui.method_run_wizard._tokens import Color
from ui.method_run_wizard.controller import MethodRunController
from ui.method_run_wizard.state import MethodRunWizardState
from ui.method_run_wizard.window import MethodRunWindow


YAML_SIDECAR_SUFFIXES = {".yaml", ".yml"}


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mtdpMainWindow")
        self.setWindowTitle("MTDP Enrichment Tool")
        self.setWindowIcon(app_icon())
        self.setAcceptDrops(True)
        self.resize(1480, 860)
        self.setMinimumSize(1160, 700)

        self.registry = SchemaRegistry()
        self.parser = ParserAdapter()
        self.sidecar_importer = SidecarYamlImporter()
        self.image_importer = ImageEvidenceImporter()
        self.grouper = SampleTypeGrouper()
        self.package_writer = MTDPPackageWriter(self.parser)
        self.package_reader = MTDPPackageReader()
        self.package_validator = MTDPPackageValidator()
        self.group_loader = GroupLoader(registry=self.registry, parser=self.parser, validator=self.package_validator)
        self.group_exporter = GroupExporter(self.package_writer)
        self.group_reprocessor = GroupReprocessor(self.parser, self.sidecar_importer)
        self.validation_service = ValidationService(self.package_writer)
        self.folder_index: FolderIndex | None = None
        self.current_folder: Path | None = None
        self.grouping_inputs: list[GroupingInput] = []
        self.current_bundle_key: str | None = None
        self.current_run_source: Path | None = None
        self.current_run_sources: list[Path] = []
        self.current_package_path: Path | None = None
        self.last_exported_package_path: Path | None = None
        self._package_workspaces: list[tempfile.TemporaryDirectory[str]] = []
        self._last_mapping_apply_all = False
        self.activity_log: list[str] = []
        self.activity_log_dialog: QtWidgets.QDialog | None = None
        self.activity_log_view: QtWidgets.QPlainTextEdit | None = None
        self.dirty = False

        self.propose_button = QtWidgets.QPushButton("Propose Groups")
        self.propose_button.setToolTip("Regenerate package grouping suggestions for the selected folder.")
        self.propose_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.propose_button.setEnabled(False)
        self.propose_button.clicked.connect(self.propose_folder_bundles)
        self.tree = FolderTreeBrowser()
        self.tree.file_selected.connect(self.open_file)
        self.tree.paths_dropped.connect(self.process_dropped_paths)

        left = QtWidgets.QWidget()
        left.setObjectName("leftPane")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addWidget(self.propose_button)
        left_layout.addWidget(self.tree, 1)

        self.bundle_builder = BundleBuilder()
        self.bundle_builder.selection_changed.connect(self._bundle_selection_changed)
        self.bundle_builder.bundles_changed.connect(self._mark_dirty)
        self.bundle_builder.source_files_dropped.connect(self._source_files_dropped)
        self.bundle_builder.run_open_requested.connect(self.open_parser_review_for_run)

        middle = QtWidgets.QWidget()
        middle.setObjectName("middlePane")
        middle_layout = QtWidgets.QVBoxLayout(middle)
        middle_layout.addWidget(QtWidgets.QLabel("Groups"))
        self.empty_state_panel = self._build_empty_state_panel()
        middle_layout.addWidget(self.empty_state_panel)
        middle_layout.addWidget(self.bundle_builder, 1)

        self.schema_selector = SchemaSelector(self.registry)
        self.schema_selector.schema_changed.connect(self.rebuild_forms_for_schema)
        self.field_detail_combo = QtWidgets.QComboBox()
        self.field_detail_combo.setAccessibleName("Displayed metadata field detail")
        self.field_detail_combo.setToolTip("Choose how many metadata fields are displayed in the package editor.")
        self.field_detail_combo.addItem("Required", "required")
        self.field_detail_combo.addItem("Required + recommended", "recommended")
        self.field_detail_combo.addItem("Required + recommended + optional", "all")
        self.field_detail_combo.setCurrentIndex(2)
        self.field_detail_combo.currentIndexChanged.connect(self._field_detail_changed)

        self.dataset_form = SchemaForm()
        self.dataset_form.changed.connect(self._mark_dirty)
        self.run_form = SchemaForm()
        self.run_form.changed.connect(self._mark_dirty)
        self.image_dialog = ImageEvidenceDialog(self)
        self.image_panel = self.image_dialog.panel
        self.image_panel.add_requested.connect(self.add_images_to_selected_run)
        self.image_panel.remove_requested.connect(self.remove_image_from_selected_run)
        self.image_panel.preview_requested.connect(self.preview_selected_run_image)
        self.image_panel.images_dropped.connect(self.attach_dropped_images_to_selected_run)
        self.supplemental_dialog = SupplementalFilesDialog(self)
        self.supplemental_dialog.add_requested.connect(self.add_supplemental_file)
        self.supplemental_dialog.remove_requested.connect(self.remove_supplemental_file)
        self.supplemental_dialog.preview_requested.connect(self.preview_supplemental_file)

        self.yaml_status_label = QtWidgets.QLabel("No run selected.")
        self.yaml_status_label.setWordWrap(True)
        self.rematch_yaml_button = QtWidgets.QPushButton("Review / re-match YAML...")
        self.rematch_yaml_button.setEnabled(False)
        self.rematch_yaml_button.clicked.connect(self.rematch_selected_run_yaml)
        self.status_label = QtWidgets.QLabel("Drop raw files, a folder, YAML metadata, or an MTDP package to begin.")
        self.status_label.setWordWrap(True)
        self.review_label = QtWidgets.QLabel("No group selected.")
        self.review_label.setWordWrap(True)

        self.validate_button = QtWidgets.QPushButton("Validate")
        self.validate_button.setToolTip("Validate selected group")
        self.validate_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton))
        self.validate_button.setEnabled(False)
        self.validate_button.clicked.connect(self.validate_selected_bundle)
        self.export_button = QtWidgets.QPushButton("Export selected")
        self.export_button.setToolTip("Export selected group as .mtdp")
        self.export_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_selected_bundle)
        self.export_all_button = QtWidgets.QPushButton("Export all ready")
        self.export_all_button.setToolTip("Export all groups that pass validation")
        self.export_all_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        self.export_all_button.setEnabled(False)
        self.export_all_button.clicked.connect(self.export_all_ready_bundles)

        self.manage_images_button = QtWidgets.QPushButton("Manage run image evidence...")
        self.manage_images_button.setEnabled(False)
        self.manage_images_button.clicked.connect(self.open_image_evidence_dialog)
        self.manage_supplemental_button = QtWidgets.QPushButton("Manage supplemental files...")
        self.manage_supplemental_button.setEnabled(False)
        self.manage_supplemental_button.clicked.connect(self.open_supplemental_files_dialog)

        self.tabs = QtWidgets.QTabWidget()
        self.dataset_tab = QtWidgets.QWidget()
        dataset_tab_layout = QtWidgets.QVBoxLayout(self.dataset_tab)
        dataset_tab_layout.setContentsMargins(0, 0, 0, 0)
        dataset_tab_layout.addWidget(self._scroll_for(self.dataset_form), 1)
        self.run_tab = QtWidgets.QWidget()
        run_tab_layout = QtWidgets.QVBoxLayout(self.run_tab)
        run_tab_layout.setContentsMargins(0, 0, 0, 0)
        run_tab_layout.addWidget(self._scroll_for(self.run_form), 1)
        run_tab_layout.addWidget(self.manage_images_button)
        run_tab_layout.addWidget(self.manage_supplemental_button)
        run_tab_layout.addWidget(self.rematch_yaml_button)
        self.tabs.addTab(self.dataset_tab, "Dataset")
        self.tabs.addTab(self.run_tab, "Run analysis inputs")
        self.tabs.setTabEnabled(1, False)

        right = QtWidgets.QWidget()
        right.setObjectName("rightPane")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.addWidget(self.schema_selector)
        detail_row = QtWidgets.QHBoxLayout()
        detail_row.setContentsMargins(0, 0, 0, 0)
        detail_row.addWidget(QtWidgets.QLabel("Show fields"))
        detail_row.addWidget(self.field_detail_combo, 1)
        right_layout.addLayout(detail_row)
        right_layout.addWidget(self.yaml_status_label)
        right_layout.addWidget(self.tabs, 1)
        right_layout.addWidget(QtWidgets.QLabel("Review"))
        right_layout.addWidget(self.review_label)
        right_layout.addWidget(self.status_label)
        action_row = QtWidgets.QHBoxLayout()
        for button in (self.validate_button, self.export_button, self.export_all_button):
            action_row.addWidget(button, 1)
        right_layout.addLayout(action_row)

        splitter = QtWidgets.QSplitter()
        splitter.setObjectName("mainWorkspace")
        splitter.addWidget(left)
        splitter.addWidget(middle)
        splitter.addWidget(right)
        splitter.setSizes([330, 470, 680])
        self.setCentralWidget(splitter)
        self.setStyleSheet(
            f"""
            QMainWindow#mtdpMainWindow,
            QSplitter#mainWorkspace,
            QWidget#leftPane,
            QWidget#middlePane,
            QWidget#rightPane {{
                background: {Color.BG};
            }}
            QMenuBar {{
                background: {Color.BG};
            }}
            QSplitter::handle {{
                background: {Color.BG};
            }}
            QTreeWidget, QTableWidget {{
                outline: 0;
                background: {Color.SURFACE};
            }}
            QGroupBox {{
                font-weight: 600;
                margin-top: 12px;
                background: {Color.BG};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                background: {Color.BG};
            }}
            QTabWidget::pane {{
                background: {Color.BG};
                border: 1px solid {Color.BORDER};
            }}
            QTabBar::tab {{
                background: {Color.SURFACE_3};
                border: 1px solid {Color.BORDER};
                padding: 5px 12px;
            }}
            QTabBar::tab:selected {{
                background: {Color.SURFACE};
            }}
            QScrollArea {{
                background: {Color.BG};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: {Color.BG};
            }}
            QPushButton {{ min-height: 28px; }}
            QFrame#emptyStatePanel {{
                background: {Color.SURFACE};
                border: 1px solid {Color.BORDER};
                border-radius: 6px;
            }}
            QLabel#emptyStateTitle {{
                color: {Color.TEXT};
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#emptyStateHint {{
                color: {Color.TEXT_2};
            }}
            """
        )
        self.dataset_form.build(
            self.schema_selector.current_schema(),
            scope="dataset",
            importance_filter=self._field_importance_filter(),
        )
        self.run_form.build(
            self.schema_selector.current_schema(),
            scope="run",
            importance_filter=self._field_importance_filter(),
        )
        self.dataset_form.setEnabled(False)
        self.run_form.setEnabled(False)
        self.actions = install_menu_bar(self)

    def _build_empty_state_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("emptyStatePanel")
        panel.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Drop compression data here")
        title.setObjectName("emptyStateTitle")
        title.setWordWrap(True)
        body = QtWidgets.QLabel(
            "Drop raw files, a source folder, a same-name YAML metadata file, or an existing MTDP package. "
            "Folder drops are scanned recursively and raw-file drops automatically look for same-stem YAML metadata."
        )
        body.setWordWrap(True)

        hint = QtWidgets.QLabel(
            "File-menu loading remains available through File > Select source folder... and File > Open MTDP package..."
        )
        hint.setObjectName("emptyStateHint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(hint)
        return panel

    def _set_empty_state_visible(self, visible: bool) -> None:
        if hasattr(self, "empty_state_panel"):
            self.empty_state_panel.setVisible(visible)

    def choose_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.open_folder(Path(folder))

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if self._mime_has_supported_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._mime_has_supported_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = self._paths_from_mime(event.mimeData())
        if paths:
            self.process_dropped_paths(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def open_folder(self, folder: Path) -> None:
        self._prepare_source_folder(folder)
        self.propose_folder_bundles()

    def _prepare_source_folder(self, folder: Path) -> None:
        self.current_folder = folder
        self.current_package_path = None
        self.schema_selector.clear_loaded_schema()
        self.folder_index = FolderIndex(folder)
        self.folder_index.open()
        self.sidecar_importer.load_mapping_profiles(folder / ".mtdp_mapping_profiles")
        self.dataset_form.set_suggestion_provider(self.folder_index)
        self.run_form.set_suggestion_provider(self.folder_index)
        package_statuses = {item["path"]: str(item["status"]) for item in self.folder_index.packages()}
        self.tree.scan_folder(
            folder,
            supported_suffixes=self.parser.supported_suffixes(),
            package_statuses=package_statuses,
        )
        self.propose_button.setEnabled(True)

    def propose_folder_bundles(self) -> None:
        if self.current_folder is None:
            return
        self._save_current_forms()
        paths = [
            path
            for path in sorted(self.current_folder.rglob("*"), key=lambda item: item.as_posix().lower())
            if path.is_file() and self.parser.can_parse(path)
        ]
        inputs, first_inference = self._grouping_inputs_from_paths(paths)
        self.grouping_inputs = list(inputs)
        if not inputs:
            self._set_empty_state_visible(True)
            self.show_message("No supported raw files were parsed.")
            return
        self._load_grouping_inputs_as_proposal(inputs, first_inference)

    def open_file(self, path: Path) -> None:
        if path.suffix.lower() == ".mtdp":
            self.load_existing_package(path)
            return
        self.add_source_file_to_selected_bundle(path)

    def process_dropped_paths(self, paths: list[Path], bundle_key: str | None = None) -> None:
        paths = _dedupe_paths(Path(path) for path in paths)
        if not paths:
            return
        if bundle_key == "__excluded__":
            bundle_key = None

        if bundle_key:
            sources = self._resolve_dropped_source_files(paths)
            for source in sources:
                self.add_source_file_to_selected_bundle(source, bundle_key)
            if sources:
                self.show_message(f"Added {len(sources)} dropped source file(s) to the selected group.")
            else:
                self.show_message("Drop raw files, folders, or YAML sidecars with matching raw files onto a group.")
            return

        if len(paths) == 1 and paths[0].is_dir():
            self.open_folder(paths[0])
            return

        packages = [path for path in paths if path.is_file() and path.suffix.lower() == ".mtdp"]
        sources = self._resolve_dropped_source_files(paths)
        if sources:
            folder = self._common_source_folder(sources)
            if folder is not None:
                self._prepare_source_folder(folder)
            self._load_source_files_as_proposal(sources)
            return

        if packages:
            self.load_existing_package(packages[0])
            if len(packages) > 1:
                self.show_message(f"Opened {packages[0].name}; drop one MTDP package at a time for review.")
            return

        if any(path.suffix.lower() in YAML_SIDECAR_SUFFIXES for path in paths if path.is_file()):
            self.show_message("Dropped YAML did not match a same-name raw source file in its folder.")
            return

        self.show_message("Drop raw files, folders, same-name YAML sidecars, or an MTDP package.")

    def _load_source_files_as_proposal(self, paths: list[Path]) -> None:
        self._save_current_forms()
        inputs, first_inference = self._grouping_inputs_from_paths(paths)
        self.grouping_inputs = list(inputs)
        if not inputs:
            self._set_empty_state_visible(True)
            self.show_message("No supported raw files were parsed from the dropped item(s).")
            return
        self._load_grouping_inputs_as_proposal(inputs, first_inference)

    def _load_grouping_inputs_as_proposal(self, inputs: list[GroupingInput], first_inference) -> None:
        if first_inference is not None:
            self.schema_selector.set_detected(first_inference)
        schema = self.schema_selector.current_schema()
        proposal = self.grouper.propose(inputs, schema)
        self.bundle_builder.load_proposal(proposal, inputs)
        self.bundle_builder.select_first_bundle()
        self._set_empty_state_visible(False)
        self.validate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.export_all_button.setEnabled(True)
        merge_text = f" {len(proposal.suggested_merges)} possible merge(s)." if proposal.suggested_merges else ""
        self.show_message(f"Proposed {len(proposal.bundles)} group(s) from {len(inputs)} file(s).{merge_text}")

    def _grouping_inputs_from_paths(self, paths: list[Path]) -> tuple[list[GroupingInput], object | None]:
        inputs: list[GroupingInput] = []
        first_inference = None
        for path in sorted(_dedupe_paths(paths), key=lambda item: item.as_posix().lower()):
            if not path.is_file() or not self.parser.can_parse(path):
                continue
            try:
                parsed = self.parser.parse(path)
            except Exception:
                self.tree.set_file_state(path, "error")
                continue
            inference = self.registry.infer(parsed, path)
            first_inference = first_inference or inference
            inputs.append(self._build_grouping_input(path, parsed, inference.schema, inference))
            self.tree.set_file_state(path, "parsed")
        return inputs, first_inference

    def _resolve_dropped_source_files(self, paths: list[Path]) -> list[Path]:
        sources: list[Path] = []
        for path in paths:
            if path.is_dir():
                sources.extend(self._source_files_in_folder(path))
                continue
            if not path.is_file():
                continue
            if self.parser.can_parse(path):
                sources.append(path)
                continue
            if path.suffix.lower() in YAML_SIDECAR_SUFFIXES:
                source = self._source_file_for_sidecar(path)
                if source is not None:
                    sources.append(source)
        return _dedupe_paths(sources)

    def _source_files_in_folder(self, folder: Path) -> list[Path]:
        return [
            path
            for path in sorted(folder.rglob("*"), key=lambda item: item.as_posix().lower())
            if path.is_file() and self.parser.can_parse(path)
        ]

    def _source_file_for_sidecar(self, sidecar: Path) -> Path | None:
        supported = {suffix.lower() for suffix in self.parser.supported_suffixes()}
        try:
            siblings = sorted(sidecar.parent.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            return None
        for candidate in siblings:
            if (
                candidate.is_file()
                and candidate.stem.casefold() == sidecar.stem.casefold()
                and candidate.suffix.lower() in supported
                and self.parser.can_parse(candidate)
            ):
                return candidate
        return None

    def _common_source_folder(self, paths: list[Path]) -> Path | None:
        if not paths:
            return None
        parents = [path.parent.resolve() for path in paths]
        try:
            return Path(os.path.commonpath([str(parent) for parent in parents]))
        except ValueError:
            return parents[0]

    def _mime_has_supported_drop(self, mime: QtCore.QMimeData) -> bool:
        for path in self._paths_from_mime(mime):
            if path.is_dir() or path.suffix.lower() == ".mtdp" or path.suffix.lower() in YAML_SIDECAR_SUFFIXES:
                return True
            if path.is_file() and self.parser.can_parse(path):
                return True
        return False

    def _paths_from_mime(self, mime: QtCore.QMimeData) -> list[Path]:
        if not mime.hasUrls():
            return []
        return [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]

    def open_existing_package(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open MTDP package",
            str(self.current_folder or Path.cwd()),
            "MTDP packages (*.mtdp)",
        )
        if path:
            self.load_existing_package(Path(path))

    def load_existing_package(self, path: Path) -> None:
        try:
            group = self.group_loader.load_package(path)
            self.schema_selector.set_loaded_schema(group.schema)
            bundle = _bundle_from_group_state(group)
        except Exception as exc:
            self.show_message(f"Could not open package for reprocessing: {exc}")
            return

        self.current_package_path = path
        self.current_folder = path.parent
        self.bundle_builder.bundles = [bundle]
        self.bundle_builder.excluded_runs.clear()
        self.bundle_builder.refresh()
        self.bundle_builder.select_first_bundle()
        self._set_empty_state_visible(False)
        self.validate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.export_all_button.setEnabled(True)
        self.show_message(f"Opened group package for reprocessing: {path.name}")

    def add_source_file_to_selected_bundle(self, path: Path, bundle_key: str | None = None) -> None:
        self._save_current_forms()
        try:
            parsed = self.parser.parse(path)
        except Exception as exc:
            self.show_message(f"Parse error: {exc}")
            self.tree.set_file_state(path, "error")
            return
        inference = self.registry.infer(parsed, path)
        grouping_input = self._build_grouping_input(path, parsed, inference.schema, inference)
        self.grouping_inputs.append(grouping_input)
        selected_bundle = self.bundle_builder.bundle_by_key(bundle_key) if bundle_key else self.bundle_builder.selected_bundle()
        run = self.bundle_builder.add_input_to_bundle(
            grouping_input,
            selected_bundle.bundle_key if selected_bundle is not None else None,
        )
        self.tree.set_file_state(path, "parsed")
        self._select_run(run)
        self._set_empty_state_visible(False)
        self.validate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.export_all_button.setEnabled(True)
        self.show_message(f"Added {path.name} to group review.")

    def add_raw_files_to_selected_group(self) -> None:
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            self.show_message("Select a group before adding raw files.")
            return
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add raw file(s) to selected group",
            str(self.current_folder or Path.cwd()),
            "Raw test files (*.*)",
        )
        for item in files:
            group = _group_from_bundle_state(bundle, self.schema_selector.current_schema())
            run_state = self.group_reprocessor.add_raw_file(group, Path(item))
            updated = _bundle_from_group_state(group)
            bundle.runs = updated.runs
            bundle.removed_runs = updated.removed_runs
            bundle.manual_corrections = updated.manual_corrections
            self.tree.set_file_state(Path(item), "parsed")
            self.grouping_inputs.append(
                self._build_grouping_input(Path(item), run_state.parsed, self.schema_selector.current_schema())
            )
            self.bundle_builder.refresh()
            target = next((run for run in bundle.runs if run.source_path == Path(item)), None)
            if target is not None:
                self._select_run(target)
        if files:
            self._mark_dirty()

    def remove_selected_run_from_group(self) -> None:
        run = self.bundle_builder.selected_run()
        bundle = self.bundle_builder.selected_run_bundle()
        if run is None or bundle is None:
            self.show_message("Select a run to remove from the group.")
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Remove run from group",
            f"Remove {run.run_id} from the editable group? The raw source is not deleted.",
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        group = _group_from_bundle_state(bundle, self.schema_selector.current_schema())
        self.group_reprocessor.remove_run(group, run.run_id)
        updated = _bundle_from_group_state(group)
        bundle.runs = updated.runs
        bundle.removed_runs = updated.removed_runs
        bundle.manual_corrections = updated.manual_corrections
        self.bundle_builder.refresh()
        self._mark_dirty()
        self.show_message(f"Removed {run.run_id} from the editable group.")

    def _source_files_dropped(self, paths: list[Path], bundle_key: str | None) -> None:
        self.process_dropped_paths(paths, bundle_key)

    def inspect_package(self, path: Path) -> None:
        validation = self.package_validator.validate(path)
        try:
            package = self.package_reader.inspect(path)
            schema_text = f"{package.manifest.get('schema_id')} v{package.manifest.get('schema_version')}"
        except Exception as exc:
            self.show_message(f"Could not inspect package: {exc}")
            self.tree.set_file_state(path, "corrupt")
            return
        state = "valid" if validation.ok else "corrupt"
        self.tree.set_file_state(path, state)
        self.show_message(f"Package {path.name}: {state}, {schema_text}")

    def _bundle_from_package_members(
        self,
        package_path: Path,
        archive: zipfile.ZipFile,
        names: set[str],
        schema: MTDPSchema,
        dataset: dict[str, object],
        provenance: dict[str, object],
        workspace: Path,
    ) -> BundleState:
        run_order = [str(item) for item in dataset.get("run_order", ()) or ()]
        raw_by_stem = {Path(name).stem: name for name in names if name.startswith("raw/")}
        normalized_by_stem = {
            Path(name).stem: name for name in names if name.startswith("normalized/") and name.endswith(".csv")
        }
        run_ids = run_order or sorted(normalized_by_stem)
        display_name = str(dataset.get("sample_type") or package_path.stem)
        bundle_key = str(dataset.get("sample_type_key") or display_name.casefold())
        bundle = BundleState(bundle_key=bundle_key, display_name=display_name)
        bundle.dataset_enrichment = self._dataset_enrichment_from_json(schema, dataset)
        provenance_runs = provenance.get("runs", {}) if isinstance(provenance.get("runs", {}), dict) else {}

        for run_id in run_ids:
            raw_member = raw_by_stem.get(run_id)
            if raw_member is None:
                continue
            source_path = self._extract_member_for_reprocess(archive, raw_member, workspace)
            parsed = self.parser.parse(source_path)
            run = BundleRunState(run_id=run_id, source_path=source_path, parsed=parsed, status="parsed")
            normalized_member = normalized_by_stem.get(run_id)
            if normalized_member:
                run.enrichment.update(self._run_enrichment_from_normalized_csv(schema, archive.read(normalized_member).decode("utf-8-sig")))
            run_payload = provenance_runs.get(run_id, {})
            if isinstance(run_payload, dict):
                run.enrichment.update(self._run_enrichment_from_provenance(schema, run_id, run_payload))
                self._load_optional_reprocess_files(archive, names, workspace, run, run_payload)
            bundle.runs.append(run)

        for record in provenance.get("supplemental_files", ()) or ():
            if isinstance(record, dict):
                supplemental = self._supplemental_from_record(archive, names, workspace, record)
                if supplemental is not None:
                    bundle.supplemental_files.append(supplemental)
        return bundle

    def _extract_member_for_reprocess(self, archive: zipfile.ZipFile, member: str, workspace: Path) -> Path:
        target = workspace / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(member))
        return target

    def _dataset_enrichment_from_json(
        self,
        schema: MTDPSchema,
        dataset: dict[str, object],
    ) -> dict[str, EnrichedFieldValue]:
        values: dict[str, EnrichedFieldValue] = {}
        for field in schema.dataset_fields:
            if field.storage.location != "dataset_json" or not field.storage.path:
                continue
            value = _get_dotted_value(dataset, field.storage.path)
            if value not in (None, ""):
                unit = value.get("unit") if isinstance(value, dict) else None
                actual = value.get("value") if isinstance(value, dict) else value
                values[field.field_id] = EnrichedFieldValue(actual, unit, "package")
        return values

    def _run_enrichment_from_normalized_csv(self, schema: MTDPSchema, text: str) -> dict[str, EnrichedFieldValue]:
        values: dict[str, EnrichedFieldValue] = {}
        for row in csv.reader(io.StringIO(text)):
            if not row:
                break
            field = schema.field_by_token(row[0])
            if field is None or len(row) < 2:
                continue
            unit = row[2] if len(row) > 2 else None
            values[field.field_id] = EnrichedFieldValue(row[1], unit, "package")
        return values

    def _run_enrichment_from_provenance(
        self,
        schema: MTDPSchema,
        run_id: str,
        run_payload: dict[str, object],
    ) -> dict[str, EnrichedFieldValue]:
        values: dict[str, EnrichedFieldValue] = {}
        for field in schema.run_fields:
            if field.storage.location != "provenance" or not field.storage.path:
                continue
            path = field.storage.path.format(run_id=run_id)
            prefix = f"runs.{run_id}."
            if path.startswith(prefix):
                path = path[len(prefix):]
            value = _get_dotted_value(run_payload, path)
            if value not in (None, ""):
                unit = value.get("unit") if isinstance(value, dict) else None
                actual = value.get("value") if isinstance(value, dict) else value
                values[field.field_id] = EnrichedFieldValue(actual, unit, "package")
        return values

    def _load_optional_reprocess_files(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        workspace: Path,
        run: BundleRunState,
        run_payload: dict[str, object],
    ) -> None:
        for record in run_payload.get("supplemental_inputs", ()) or ():
            if not isinstance(record, dict):
                continue
            if record.get("type") == "sidecar_yaml" and isinstance(record.get("package_path"), str):
                if record["package_path"] in names:
                    run.sidecar_path = self._extract_member_for_reprocess(archive, str(record["package_path"]), workspace)
                    run.sidecar_import_status = "YAML imported"
                    run.sidecar_import_mode = str(record.get("import_mode") or "")
            elif record.get("type") == "supplemental_file":
                supplemental = self._supplemental_from_record(archive, names, workspace, record, run_id=run.run_id)
                if supplemental is not None:
                    run.supplemental_files.append(supplemental)
        for record in run_payload.get("image_evidence", ()) or ():
            if not isinstance(record, dict) or not isinstance(record.get("package_path"), str):
                continue
            package_path = str(record["package_path"])
            if package_path not in names:
                continue
            image_path = self._extract_member_for_reprocess(archive, package_path, workspace)
            run.images.append(
                RunImageEvidence(
                    source_path=image_path,
                    view=str(record.get("view", "other")),
                    role=str(record.get("role", "audit_evidence")),
                    used_for_metrology=bool(record.get("used_for_metrology", False)),
                    notes=str(record.get("notes")) if record.get("notes") else None,
                )
            )

    def _supplemental_from_record(
        self,
        archive: zipfile.ZipFile,
        names: set[str],
        workspace: Path,
        record: dict[str, object],
        *,
        run_id: str | None = None,
    ) -> SupplementalFile | None:
        package_path = record.get("package_path")
        if not isinstance(package_path, str) or package_path not in names:
            return None
        source_path = self._extract_member_for_reprocess(archive, package_path, workspace)
        return SupplementalFile(
            source_path=source_path,
            scope=str(record.get("scope", "run" if run_id else "dataset")),
            role=str(record.get("role", "other")),
            run_id=run_id,
            notes=str(record.get("notes")) if record.get("notes") else None,
        )

    def rebuild_forms_for_schema(self, schema: MTDPSchema) -> None:
        self._save_current_forms()
        bundle_cache = _bundle_metadata_cache(self.bundle_builder.bundles, self.bundle_builder.excluded_runs)
        if self.grouping_inputs:
            proposal = self.grouper.propose(self.grouping_inputs, schema)
            self.bundle_builder.load_proposal(proposal, self.grouping_inputs)
            _restore_bundle_metadata_cache(self.bundle_builder.bundles, bundle_cache, self.bundle_builder.excluded_runs)
            self._carry_metadata_for_schema(schema)
            self.bundle_builder.select_first_bundle()
        else:
            self._carry_metadata_for_schema(schema)
            self._load_bundle_form(self.bundle_builder.selected_bundle())
            self._load_run_form(self.bundle_builder.selected_run())
        self.dirty = True

    def _field_importance_filter(self) -> str:
        data = self.field_detail_combo.currentData() if hasattr(self, "field_detail_combo") else "all"
        return str(data or "all")

    def _field_detail_changed(self) -> None:
        self._save_current_forms()
        bundle = self.bundle_builder.selected_bundle()
        run = self.bundle_builder.selected_run()
        self._load_bundle_form(bundle)
        runs = self.bundle_builder.selected_runs()
        if not runs and bundle is not None and run is None:
            runs = list(bundle.runs)
        if len(runs) > 1 and run is None:
            self._load_run_form(None, bulk_count=len(runs), bulk_label="dataset")
        elif len(runs) > 1:
            self._load_run_form(None, bulk_count=len(runs), bulk_label="selected runs")
        else:
            self._load_run_form(runs[0] if runs else run)
        self.show_message(f"Showing {self.field_detail_combo.currentText().lower()} metadata fields.")

    def validate_selected_bundle(self) -> bool:
        self._save_current_forms()
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            self.show_message("Select a group to validate.")
            return False
        ok = self._validate_bundle(bundle)
        self.bundle_builder.refresh()
        self._update_review(bundle)
        self.show_message(_bundle_ready_message(bundle) if ok else _bundle_needs_input_message(bundle))
        return ok

    def export_selected_bundle(self) -> None:
        self._save_current_forms()
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            self.show_message("Select a group to export.")
            return
        if not self._validate_bundle(bundle):
            self.bundle_builder.refresh()
            self._update_review(bundle)
            self.show_message(_bundle_needs_input_message(bundle, before_export=True))
            return
        self.bundle_builder.refresh()
        self._update_review(bundle)
        note = _bundle_note_summary(bundle)
        if note:
            self._append_activity_log(f"Validation note: {note}")
        output_path = self._request_output_path_for_bundle(bundle)
        if output_path is None:
            self.show_message("Export cancelled.")
            return
        validation = self._write_bundle(bundle, output_path)
        if validation.ok:
            self.last_exported_package_path = output_path
            self._mark_bundle_packaged(bundle)
            self.show_message(f"Wrote and validated {output_path.name}. Use Analysis to process it through the Method Wizard.")
        else:
            self.show_message("; ".join(validation.messages()))

    def export_all_ready_bundles(self) -> None:
        self._save_current_forms()
        exported = 0
        for bundle in list(self.bundle_builder.bundles):
            if not self._validate_bundle(bundle):
                continue
            note = _bundle_note_summary(bundle)
            if note:
                self._append_activity_log(f"Validation note for {bundle.display_name}: {note}")
            validation = self._write_bundle(bundle, self._output_path_for_bundle(bundle))
            if validation.ok:
                self._mark_bundle_packaged(bundle)
                exported += 1
        self.bundle_builder.refresh()
        self.show_message(f"Exported {exported} ready group(s).")

    def open_parser_review_for_run(self, run: BundleRunState | None = None) -> None:
        target = run or self.bundle_builder.selected_run()
        if target is None:
            self.show_message("Select a run before reviewing parsed channels.")
            return
        dialog = ParserReviewDialog(target, self.schema_selector.current_schema(), self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        target.status = "parsed"
        target.reason = "parsed channel review updated"
        self.bundle_builder.refresh()
        self._select_run(target)
        self._update_review(self.bundle_builder.selected_bundle())
        self._mark_dirty()
        self.show_message(f"Updated parsed channel review for {target.run_id}. Validate again.")

    def show_message(self, message: str) -> None:
        self.status_label.setText(message)
        self._append_activity_log(message)
        QtCore.QTimer.singleShot(5000, lambda: self.status_label.setText(""))

    def show_activity_log(self) -> None:
        if self.activity_log_dialog is None:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Activity Log")
            dialog.resize(760, 420)
            layout = QtWidgets.QVBoxLayout(dialog)
            view = QtWidgets.QPlainTextEdit()
            view.setReadOnly(True)
            layout.addWidget(view, 1)
            buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dialog.hide)
            layout.addWidget(buttons)
            self.activity_log_dialog = dialog
            self.activity_log_view = view
        self._refresh_activity_log()
        self.activity_log_dialog.show()
        self.activity_log_dialog.raise_()
        self.activity_log_dialog.activateWindow()

    def _append_activity_log(self, message: str) -> None:
        text = str(message or "").strip()
        if not text:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"{timestamp}  {text}")
        self._refresh_activity_log()

    def _refresh_activity_log(self) -> None:
        if self.activity_log_view is None:
            return
        self.activity_log_view.setPlainText("\n".join(self.activity_log))
        cursor = self.activity_log_view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.activity_log_view.setTextCursor(cursor)

    def show_about_dialog(self) -> None:
        AboutDialog(self).exec()

    def run_method_wizard(self, package_path: Path | None = None) -> None:
        selected = package_path or self.current_package_path or self.last_exported_package_path
        window = MethodRunWindow(package_path=selected, parent=self)
        self._method_run_controller = MethodRunController(
            window,
            MethodRunWizardState(input_package_path=selected),
        )
        self._method_run_window = window
        window.show()
        window.raise_()
        window.activateWindow()

    def open_mtda_archive_or_report(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open MTDA package dashboard",
            str(self.current_folder or Path.cwd()),
            "MTDA archives and reports (*.mtda *.html *.json)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() == ".mtda":
            try:
                package = self._extract_mtda_surface_package(target)
            except zipfile.BadZipFile:
                self.show_message(f"{target.name} is not a valid MTDA archive.")
                return
            if package is None:
                self.show_message(f"No report surfaces found in {target.name}.")
                return
            MTDADashboardDialog(package, self).exec()
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(target)))

    def _extract_mtda_surface_package(self, path: Path) -> MTDASurfacePackage | None:
        target_root = Path(tempfile.gettempdir()) / "compression_module_mtda_dashboard" / path.stem
        target_root.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, object] = {}
        with zipfile.ZipFile(path) as archive:
            members = {member for member in archive.namelist() if not member.endswith("/")}
            if "surface_manifest.json" in members:
                try:
                    manifest = json.loads(archive.read("surface_manifest.json").decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    manifest = {}
            for member in sorted(members):
                if self._should_extract_mtda_dashboard_member(member):
                    self._extract_mtda_member(archive, member, target_root)
        entries = self._mtda_surface_entries(manifest, members, target_root)
        if not any(entry.available for entry in entries):
            return None
        manifest_path = target_root / "surface_manifest.json"
        return MTDASurfacePackage(
            archive_path=path,
            extract_root=target_root,
            entries=tuple(entries),
            manifest_path=manifest_path if manifest_path.exists() else None,
        )

    def _extract_mtda_member(self, archive: zipfile.ZipFile, member: str, target_root: Path) -> Path | None:
        relative = self._safe_mtda_member_path(member)
        if relative is None:
            return None
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(member))
        return destination

    def _mtda_surface_entries(
        self,
        manifest: dict[str, object],
        members: set[str],
        target_root: Path,
    ) -> list[MTDASurfaceEntry]:
        surfaces = manifest.get("surfaces", {}) if isinstance(manifest.get("surfaces"), dict) else {}
        entries: list[MTDASurfaceEntry] = []
        defaults = {
            "test_report": ("Test Report", "Formal method/result report.", "report/test_report.html"),
            "audit_report": ("Audit Report", "Grouped analysis evidence and traceability report.", "audit/audit_report.html"),
            "method_development_workbench": (
                "Method Development Workbench",
                "Operation-level replay and debugging surface.",
                "workbench/index.html",
            ),
        }
        for surface_id, (label, role, default_member) in defaults.items():
            surface = surfaces.get(surface_id, {}) if isinstance(surfaces.get(surface_id), dict) else {}
            member = str(surface.get("html_member") or default_member)
            entries.append(
                MTDASurfaceEntry(
                    surface_id=surface_id,
                    label=str(surface.get("label") or label),
                    role=str(surface.get("role") or role),
                    member=member,
                    local_path=(target_root / Path(*PurePosixPath(member).parts)) if member in members else None,
                    status=str(surface.get("status") or ("available" if member in members else "missing")),
                    rc_status=str(surface.get("rc_status") or ""),
                )
            )
        if "interactive_report/index.html" in members and "audit_report" not in {
            entry.surface_id for entry in entries if entry.available
        }:
            entries.append(
                MTDASurfaceEntry(
                    surface_id="interactive_report",
                    label="Interactive Report",
                    role="Legacy interactive report surface.",
                    member="interactive_report/index.html",
                    local_path=target_root / "interactive_report" / "index.html",
                    status="available",
                )
            )
        for surface_id, label, role, member in (
            ("surface_manifest", "Surface Manifest", "Surface index and archive handoff metadata.", "surface_manifest.json"),
            ("report_quality_gate", "Report Quality Gate", "Report surface quality-control summary.", "report/report_quality_gate.json"),
        ):
            entries.append(
                MTDASurfaceEntry(
                    surface_id=surface_id,
                    label=label,
                    role=role,
                    member=member,
                    local_path=(target_root / Path(*PurePosixPath(member).parts)) if member in members else None,
                    status="available" if member in members else "missing",
                )
            )
        return entries

    def _should_extract_mtda_dashboard_member(self, member: str) -> bool:
        if self._safe_mtda_member_path(member) is None:
            return False
        return (
            member in {"manifest.json", "surface_manifest.json", "checksums.json", "provenance.json"}
            or member.startswith(("report/", "audit/", "workbench/", "interactive_report/", "acceptance/curve_family/"))
        )

    def _safe_mtda_member_path(self, member: str) -> Path | None:
        path = PurePosixPath(member)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            return None
        return Path(*path.parts)

    def open_image_evidence_dialog(self) -> None:
        run = self.bundle_builder.selected_run()
        if run is None:
            self.show_message("Select a run before managing image evidence.")
            return
        self._load_image_panel(run)
        self.image_dialog.set_run_id(run.run_id)
        self.image_dialog.exec()

    def open_supplemental_files_dialog(self) -> None:
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            self.show_message("Select a group before managing supplemental files.")
            return
        self.supplemental_dialog.set_files(self._current_supplemental_files())
        self.supplemental_dialog.exec()

    def add_supplemental_file(self) -> None:
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            self.show_message("Select a group before adding supplemental files.")
            return
        run = self.bundle_builder.selected_run()
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add supplemental file",
            str(self.current_folder or Path.cwd()),
            "All files (*.*)",
        )
        added = 0
        for item in files:
            supplemental = supplemental_file_from_dialog(self, Path(item), run_id=run.run_id if run else None)
            if supplemental is None:
                continue
            if supplemental.scope == "run" and run is not None:
                run.supplemental_files.append(supplemental)
            else:
                bundle.supplemental_files.append(supplemental)
            added += 1
        if added:
            self.supplemental_dialog.set_files(self._current_supplemental_files())
            self._mark_dirty()
            self.show_message(f"Added {added} supplemental file(s).")

    def remove_supplemental_file(self, index: int) -> None:
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            return
        run = self.bundle_builder.selected_run()
        dataset_count = len(bundle.supplemental_files)
        if 0 <= index < dataset_count:
            bundle.supplemental_files.pop(index)
        elif run is not None and 0 <= index - dataset_count < len(run.supplemental_files):
            run.supplemental_files.pop(index - dataset_count)
        self.supplemental_dialog.set_files(self._current_supplemental_files())
        self._mark_dirty()

    def preview_supplemental_file(self, index: int) -> None:
        files = self._current_supplemental_files()
        if 0 <= index < len(files):
            open_supplemental_file(files[index])

    def _current_supplemental_files(self) -> list[SupplementalFile]:
        bundle = self.bundle_builder.selected_bundle()
        if bundle is None:
            return []
        files = list(bundle.supplemental_files)
        run = self.bundle_builder.selected_run()
        if run is not None:
            files.extend(run.supplemental_files)
        return files

    def refresh_folder_index(self) -> None:
        if self.current_folder is None:
            self.show_message("Select a folder before refreshing the index.")
            return
        self.folder_index = FolderIndex(self.current_folder)
        self.folder_index.open()
        self.folder_index.sync()
        self.dataset_form.set_suggestion_provider(self.folder_index)
        self.run_form.set_suggestion_provider(self.folder_index)
        self.show_message("Folder index and suggestions refreshed.")

    def expand_selected_bundle(self) -> None:
        item = self.bundle_builder.tree.currentItem()
        if item is None:
            return
        if item.parent() is not None:
            item = item.parent()
        item.setExpanded(True)

    def collapse_selected_bundle(self) -> None:
        item = self.bundle_builder.tree.currentItem()
        if item is None:
            return
        if item.parent() is not None:
            item = item.parent()
        item.setExpanded(False)

    def rematch_selected_run_yaml(self) -> None:
        run = self.bundle_builder.selected_run()
        if run is None:
            self.show_message("Select a run before reviewing supplemental YAML.")
            return
        if run.sidecar_path is None:
            self.show_message("Selected run has no supplemental YAML sidecar.")
            return
        schema = self.schema_selector.current_schema()
        result = self.sidecar_importer.import_file(run.sidecar_path, run.parsed, schema, existing_values=run.enrichment)
        if result.document is None:
            self.show_message("; ".join(result.warnings) or "Could not load supplemental YAML.")
            return
        profile = self._request_yaml_mapping_profile(result.document, schema)
        if profile is None:
            return
        saved_profile_path = self._save_mapping_profile(profile)
        profile = type(profile).load(saved_profile_path)
        self.sidecar_importer.add_mapping_profile(profile)
        targets = [run]
        if self._last_mapping_apply_all:
            signature = result.document.structure_signature
            targets = []
            for candidate in self.bundle_builder.all_runs():
                if candidate.sidecar_path is None:
                    continue
                candidate_result = self.sidecar_importer.import_file(candidate.sidecar_path, candidate.parsed, schema)
                if candidate_result.document is not None and candidate_result.document.structure_signature == signature:
                    targets.append(candidate)
        for target in targets:
            mapped = self.sidecar_importer.import_file(
                target.sidecar_path,
                target.parsed,
                schema,
                existing_values=target.enrichment,
                mapping_profile=profile,
            )
            self._apply_sidecar_result_to_run(target, mapped)
        self.bundle_builder.refresh()
        self._select_run(run)
        self._load_run_form(run)
        self._load_image_panel(run)
        self._update_yaml_status(run)
        self._mark_dirty()
        self.show_message(f"Applied YAML mapping to {len(targets)} run(s).")

    def _write_bundle(self, bundle: BundleState, output_path: Path):
        schema = self.schema_selector.current_schema()
        validation = self.group_exporter.export_group(_group_from_bundle_state(bundle, schema), output_path)
        if self.folder_index is not None and validation.ok:
            self.folder_index.sync()
        return validation

    def _validate_bundle(self, bundle: BundleState) -> bool:
        schema = self.schema_selector.current_schema()
        self._ensure_bundle_dataset_defaults(bundle)
        _, dataset_validation = schema.validate_dataset_fields(bundle.dataset_enrichment)
        if not bundle.runs:
            dataset_validation.add_error("Group has no included runs.", code="missing_runs")
        validation = ValidationResult()
        validation.extend(dataset_validation)
        for run in bundle.runs:
            existing = self.package_writer._existing_fields(run.parsed, schema)
            _, run_validation = schema.validate_run_fields(run.enrichment, existing_tokens=existing)
            table = self.package_writer.normalizer.normalize(run.parsed, schema)
            if run.sidecar_conflicts:
                run_validation.add_error(
                    f"{run.run_id} has supplemental YAML fields that need confirmation.",
                    field=str(run.source_path),
                    code="sidecar_requires_confirmation",
                )
            run.status = "ready" if run_validation.ok and table.validation.ok else "needs input"
            if run.status == "ready":
                run.reason = _run_validation_warning_reason(run_validation, table.validation) or "ready"
            else:
                run.reason = _run_validation_reason(run_validation, table.validation)
            validation.extend(run_validation)
            validation.extend(table.validation)
        bundle.status = "ready" if validation.ok else "needs input"
        if validation.ok:
            bundle.reason = _bundle_warning_summary(bundle) or "ready"
        else:
            bundle.reason = _bundle_validation_reason(dataset_validation, bundle)
        return validation.ok

    def _bundle_selection_changed(self) -> None:
        self._save_current_forms()
        bundle = self.bundle_builder.selected_bundle()
        run = self.bundle_builder.selected_run()
        selected_runs = self.bundle_builder.selected_runs()
        bulk_runs = selected_runs
        if not bulk_runs and bundle is not None and run is None:
            bulk_runs = list(bundle.runs)
        self.current_bundle_key = bundle.bundle_key if bundle is not None else None
        self.current_run_sources = [item.source_path for item in bulk_runs]
        self.current_run_source = run.source_path if run is not None and len(selected_runs) <= 1 else None
        self._load_bundle_form(bundle)
        if len(bulk_runs) > 1 and run is None:
            self._load_run_form(None, bulk_count=len(bulk_runs), bulk_label="dataset")
            self._load_image_panel(None)
        elif len(selected_runs) > 1:
            self._load_run_form(None, bulk_count=len(selected_runs), bulk_label="selected runs")
            self._load_image_panel(None)
        else:
            self._load_run_form(run)
            self._load_image_panel(run)
        self._update_review(bundle)
        if len(bulk_runs) > 1 and run is None:
            self._update_yaml_status(None, bulk_count=len(bulk_runs), bulk_label="dataset")
        else:
            self._update_yaml_status(run if len(selected_runs) <= 1 else None, bulk_count=len(selected_runs), bulk_label="selected runs")
        self.dataset_form.setEnabled(bundle is not None)
        self.run_form.setEnabled(bool(bulk_runs))
        self.tabs.setTabEnabled(1, bool(bulk_runs))
        self.manage_images_button.setEnabled(run is not None and len(selected_runs) <= 1)
        self.manage_supplemental_button.setEnabled(bundle is not None)
        self.rematch_yaml_button.setEnabled(run is not None and len(selected_runs) <= 1 and run.sidecar_path is not None)
        self.tabs.setCurrentWidget(self.run_tab if bulk_runs else self.dataset_tab)

    def _load_bundle_form(self, bundle: BundleState | None) -> None:
        schema = self.schema_selector.current_schema()
        self.dataset_form.build(schema, scope="dataset", importance_filter=self._field_importance_filter())
        if bundle is None:
            return
        self._ensure_bundle_dataset_defaults(bundle)
        for field_id, value in bundle.dataset_enrichment.items():
            self.dataset_form.set_field_value(field_id, value.value, value.unit)

    def _load_run_form(self, run: BundleRunState | None, *, bulk_count: int = 0, bulk_label: str = "selected runs") -> None:
        schema = self.schema_selector.current_schema()
        self.run_form.build(
            schema,
            run.parsed if run is not None else None,
            scope="run",
            importance_filter=self._field_importance_filter(),
        )
        if run is None:
            if bulk_count > 1:
                self.yaml_status_label.setText(
                    f"Bulk edit: {bulk_count} runs in {bulk_label}. Filled fields will be applied to those runs; blank untouched fields are ignored."
                )
            return
        for field_id, value in run.enrichment.items():
            self.run_form.set_field_value(field_id, value.value, value.unit)
        if run.sidecar_conflicts:
            self.show_message("; ".join(conflict.message for conflict in run.sidecar_conflicts[:2]))

    def _load_image_panel(self, run: BundleRunState | None) -> None:
        self.image_panel.set_images(run.images if run is not None else [])
        self.image_dialog.set_run_id(run.run_id if run is not None else None)

    def _update_yaml_status(self, run: BundleRunState | None, *, bulk_count: int = 0, bulk_label: str = "selected runs") -> None:
        if bulk_count > 1:
            self.yaml_status_label.setText(
                f"Bulk edit: {bulk_count} runs in {bulk_label}. Only fields you fill in this form will be applied."
            )
            return
        if run is None:
            self.yaml_status_label.setText("No run selected.")
            return
        status = run.sidecar_import_status or "No YAML"
        if run.sidecar_conflicts:
            status = f"{status}: {len(run.sidecar_conflicts)} field(s) need review"
        if run.sidecar_unknown_keys:
            status = f"{status}; {len(run.sidecar_unknown_keys)} unknown key(s)"
        self.yaml_status_label.setText(f"YAML: {status}")

    def _save_current_forms(self) -> None:
        if self.current_bundle_key:
            bundle = self.bundle_builder.bundle_by_key(self.current_bundle_key)
            if bundle is not None:
                values, units = self.dataset_form.values()
                bundle.dataset_enrichment = _merge_visible_form_values(bundle.dataset_enrichment, values)
                bundle.dataset_units = _merge_visible_form_units(bundle.dataset_units, units, values)
        if self.current_run_source:
            run = self.bundle_builder.run_by_source(self.current_run_source)
            if run is not None:
                values, units = self.run_form.values()
                run.enrichment = _merge_visible_form_values(run.enrichment, values)
                run.field_units = _merge_visible_form_units(run.field_units, units, values)
                self._clear_confirmed_sidecar_conflicts(run, values, units)
        elif self.current_run_sources:
            values, units = self.run_form.values(only_filled=True)
            if values:
                for source in self.current_run_sources:
                    run = self.bundle_builder.run_by_source(source)
                    if run is None:
                        continue
                    run.enrichment = _merge_visible_form_values(run.enrichment, values)
                    run.field_units = _merge_visible_form_units(run.field_units, units, values)
                    self._clear_confirmed_sidecar_conflicts(run, values, units)

    def _carry_metadata_for_schema(self, schema: MTDPSchema) -> None:
        field_index = _schema_field_index(self.registry.all())
        for bundle in self.bundle_builder.bundles:
            _repurpose_missing_values(bundle.dataset_enrichment, bundle.dataset_units, schema.dataset_fields, field_index)
            for run in bundle.runs:
                _repurpose_missing_values(run.enrichment, run.field_units, schema.run_fields, field_index)
        for run in self.bundle_builder.excluded_runs:
            _repurpose_missing_values(run.enrichment, run.field_units, schema.run_fields, field_index)

    def _ensure_bundle_dataset_defaults(self, bundle: BundleState) -> None:
        if "sample_type" not in bundle.dataset_enrichment:
            bundle.dataset_enrichment["sample_type"] = EnrichedFieldValue(bundle.display_name, source="grouping_proposal")
        if "sample_type_key" not in bundle.dataset_enrichment:
            bundle.dataset_enrichment["sample_type_key"] = EnrichedFieldValue(bundle.bundle_key, source="grouping_proposal")

    def _select_run(self, target_run: BundleRunState) -> None:
        iterator = QtWidgets.QTreeWidgetItemIterator(self.bundle_builder.tree)
        while iterator.value():
            item = iterator.value()
            raw = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if raw and str(raw) == str(target_run.source_path):
                self.bundle_builder.tree.setCurrentItem(item)
                item.setSelected(True)
                return
            iterator += 1

    def _update_review(self, bundle: BundleState | None) -> None:
        if bundle is None:
            self.review_label.setText("No group selected.")
            return
        missing = sum(1 for run in bundle.runs if run.status not in {"ready", "packaged"})
        review = (
            f"Group: {bundle.display_name}\n"
            f"Schema: {self.schema_selector.current_schema().schema_id} "
            f"v{self.schema_selector.current_schema().schema_version}\n"
            f"Runs: {len(bundle.runs)}\n"
            f"Runs needing input: {missing}"
        )
        issue_summary = _bundle_issue_summary(bundle)
        if issue_summary:
            review += f"\nIssue: {issue_summary}"
        else:
            note_summary = _bundle_note_summary(bundle)
            if note_summary:
                review += f"\nNote: {note_summary}"
        self.review_label.setText(review)

    def _mark_bundle_packaged(self, bundle: BundleState) -> None:
        for run in bundle.runs:
            run.status = "packaged"
            run.reason = "packaged"
            self.tree.set_file_state(run.source_path, "packaged")
        bundle.status = "packaged"
        bundle.reason = "packaged"
        self.bundle_builder.refresh()

    def _output_path_for_bundle(self, bundle: BundleState) -> Path:
        if self.current_package_path is not None:
            stem = self.current_package_path.stem
            return self.current_package_path.with_name(f"{stem}_revised.mtdp")
        folder = self.current_folder or (bundle.runs[0].source_path.parent if bundle.runs else Path.cwd())
        safe_stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in bundle.display_name).strip("_")
        return folder / f"{safe_stem or 'mtdp_dataset'}.mtdp"

    def _request_output_path_for_bundle(self, bundle: BundleState) -> Path | None:
        default_path = self._output_path_for_bundle(bundle)
        path_text, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export selected group",
            str(default_path),
            "MTDP packages (*.mtdp)",
        )
        if not path_text:
            return None
        output_path = Path(path_text)
        if output_path.suffix.lower() != ".mtdp":
            output_path = output_path.with_suffix(".mtdp")
        return output_path

    def _mark_dirty(self) -> None:
        self.dirty = True

    def _build_grouping_input(
        self,
        path: Path,
        parsed,
        schema: MTDPSchema,
        inference=None,
    ) -> GroupingInput:
        supplemental = self.sidecar_importer.import_for_run(path, parsed, schema)
        if supplemental.requires_mapping and supplemental.document is not None:
            profile = self._request_yaml_mapping_profile(supplemental.document, schema)
            if profile is not None:
                saved_profile_path = self._save_mapping_profile(profile)
                profile = type(profile).load(saved_profile_path)
                self.sidecar_importer.add_mapping_profile(profile)
                supplemental = self.sidecar_importer.import_for_run(path, parsed, schema, mapping_profile=profile)
        return GroupingInput(path, parsed, inference, supplemental)

    def _request_yaml_mapping_profile(self, document, schema: MTDPSchema):
        dialog = YamlMappingDialog(document, schema, self)
        self._last_mapping_apply_all = False
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        self._last_mapping_apply_all = bool(getattr(dialog, "apply_all_checkbox", None) and dialog.apply_all_checkbox.isChecked())
        return dialog.mapping_profile()

    def _save_mapping_profile(self, profile) -> Path:
        root = (self.current_folder or Path.cwd()) / ".mtdp_mapping_profiles"
        target = root / f"{profile.mapping_profile_id}.yaml"
        return profile.save(target)

    def _apply_sidecar_result_to_run(self, run: BundleRunState, result) -> None:
        for field_id, candidate in result.imported_fields.items():
            run.enrichment[field_id] = EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
            run.field_units[field_id] = candidate.unit
        run.sidecar_path = result.source_path or run.sidecar_path
        run.sidecar_conflicts = list(result.conflicts)
        run.sidecar_unknown_keys = list(result.unknown_keys)
        run.sidecar_mapping_profile_id = result.mapping_profile_id
        run.sidecar_mapping_profile_path = result.mapping_profile_path
        if result.mapping_profile_id:
            run.sidecar_import_mode = "mapping_profile"
        elif result.document is not None and result.document.is_canonical:
            run.sidecar_import_mode = "canonical"
        elif result.requires_mapping:
            run.sidecar_import_mode = "mapping_required"
        elif result.source_path:
            run.sidecar_import_mode = "alias"
        else:
            run.sidecar_import_mode = None
        if result.mapping_profile_id:
            run.sidecar_import_status = "Mapping applied"
        elif result.conflicts:
            run.sidecar_import_status = "YAML needs review"
        elif result.imported_fields:
            run.sidecar_import_status = "YAML imported"
        elif result.source_path:
            run.sidecar_import_status = "YAML detected"
        if result.image_references:
            known = {Path(image.source_path) for image in run.images}
            for item in result.image_references:
                if item.path in known:
                    continue
                run.images.append(
                    RunImageEvidence(
                        source_path=item.path,
                        view=item.view,
                        role=item.role,
                        used_for_metrology=item.used_for_metrology,
                        notes=item.notes,
                    )
                )
                known.add(item.path)

    def _clear_confirmed_sidecar_conflicts(
        self,
        run: BundleRunState,
        values: dict[str, EnrichedFieldValue],
        units: dict[str, str | None],
    ) -> None:
        if not run.sidecar_conflicts:
            return
        remaining = []
        for conflict in run.sidecar_conflicts:
            value = values.get(conflict.field_id)
            unit = units.get(conflict.field_id)
            if value is None or value.value in (None, "") or (conflict.imported_unit is None and not unit):
                remaining.append(conflict)
        run.sidecar_conflicts = remaining
        run.sidecar_import_status = "YAML imported" if not remaining and run.sidecar_path else run.sidecar_import_status

    def add_images_to_selected_run(self) -> None:
        run = self.bundle_builder.selected_run()
        if run is None:
            self.show_message("Select a run before adding image evidence.")
            return
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add image evidence",
            str(run.source_path.parent),
            "Images (*.jpg *.jpeg *.png *.tif *.tiff)",
        )
        self._attach_images_to_run(run, [Path(item) for item in files])

    def attach_dropped_images_to_selected_run(self, paths: list[Path]) -> None:
        run = self.bundle_builder.selected_run()
        if run is None:
            self.show_message("Drop images after selecting a run.")
            return
        self._attach_images_to_run(run, paths)

    def _attach_images_to_run(self, run: BundleRunState, paths: list[Path]) -> None:
        schema = self.schema_selector.current_schema()
        added = 0
        messages: list[str] = []
        for path in paths:
            evidence, validation = self.image_importer.make_evidence(path, schema)
            if not validation.ok or evidence is None:
                messages.extend(validation.messages())
                continue
            run.images.append(evidence)
            added += 1
        self.image_panel.set_images(run.images)
        self.bundle_builder.refresh()
        self._select_run(run)
        self._mark_dirty()
        if messages:
            self.show_message("; ".join(messages))
        elif added:
            self.show_message(f"Added {added} image evidence file(s) to {run.run_id}.")

    def remove_image_from_selected_run(self, index: int) -> None:
        run = self.bundle_builder.selected_run()
        if run is None or index < 0 or index >= len(run.images):
            return
        run.images.pop(index)
        self.image_panel.set_images(run.images)
        self.bundle_builder.refresh()
        self._select_run(run)
        self._mark_dirty()

    def preview_selected_run_image(self, index: int) -> None:
        run = self.bundle_builder.selected_run()
        if run is None or index < 0 or index >= len(run.images):
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(run.images[index].source_path)))

    def _scroll_for(self, widget: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll


def _run_validation_reason(run_validation: ValidationResult, table_validation: ValidationResult) -> str:
    parts = [
        part
        for part in (
            _validation_issue_summary(run_validation, field_kind="run"),
            _validation_issue_summary(table_validation, field_kind="table"),
        )
        if part
    ]
    return "; ".join(parts) or "needs input"


def _run_validation_warning_reason(run_validation: ValidationResult, table_validation: ValidationResult) -> str:
    parts = [
        part
        for part in (
            _validation_warning_summary(run_validation),
            _validation_warning_summary(table_validation),
        )
        if part
    ]
    return "; ".join(parts)


def _bundle_validation_reason(dataset_validation: ValidationResult, bundle: BundleState) -> str:
    parts: list[str] = []
    dataset_summary = _validation_issue_summary(dataset_validation, field_kind="dataset")
    if dataset_summary:
        parts.append(f"Dataset: {dataset_summary}")
    run_summary = _bundle_run_issue_summary(bundle)
    if run_summary:
        parts.append(run_summary)
    return "; ".join(parts) or "needs input"


def _bundle_warning_summary(bundle: BundleState) -> str:
    run_summary = _bundle_run_note_summary(bundle)
    return run_summary


def _bundle_issue_summary(bundle: BundleState) -> str:
    if bundle.status == "needs input" and bundle.reason:
        return bundle.reason
    if any(run.status == "needs input" for run in bundle.runs):
        return _bundle_run_issue_summary(bundle)
    return ""


def _bundle_note_summary(bundle: BundleState) -> str:
    if bundle.status == "ready" and bundle.reason and bundle.reason != "ready":
        return bundle.reason
    return _bundle_run_note_summary(bundle)


def _bundle_run_issue_summary(bundle: BundleState) -> str:
    runs = [run for run in bundle.runs if run.status == "needs input"]
    if not runs:
        return ""
    reason_counts = Counter((run.reason or "needs input") for run in runs)
    if len(reason_counts) == 1:
        reason, _count = reason_counts.most_common(1)[0]
        if len(runs) == 1:
            return f"{runs[0].run_id}: {reason}"
        return f"{len(runs)} run(s): {reason}"
    examples = [f"{run.run_id}: {run.reason or 'needs input'}" for run in runs[:2]]
    if len(runs) > len(examples):
        examples.append(f"+{len(runs) - len(examples)} more run(s)")
    return "; ".join(examples)


def _bundle_run_note_summary(bundle: BundleState) -> str:
    runs = [run for run in bundle.runs if run.status == "ready" and run.reason not in {"", "ready"}]
    if not runs:
        return ""
    reason_counts = Counter(run.reason for run in runs)
    if len(reason_counts) == 1:
        reason, _count = reason_counts.most_common(1)[0]
        if len(runs) == 1:
            return f"{runs[0].run_id}: {reason}"
        return f"{len(runs)} run(s): {reason}"
    examples = [f"{run.run_id}: {run.reason}" for run in runs[:2]]
    if len(runs) > len(examples):
        examples.append(f"+{len(runs) - len(examples)} more run(s)")
    return "; ".join(examples)


def _bundle_ready_message(bundle: BundleState) -> str:
    note = _bundle_note_summary(bundle)
    if note:
        return _with_terminal_period(f"Selected group is ready. Note: {note}")
    return "Selected group is ready."


def _bundle_needs_input_message(bundle: BundleState, *, before_export: bool = False) -> str:
    summary = _bundle_issue_summary(bundle)
    if summary:
        prefix = "Selected group needs input before export" if before_export else "Selected group needs input"
        return _with_terminal_period(f"{prefix}: {summary}")
    return "Selected group needs input before export." if before_export else "Selected group needs input."


def _validation_issue_summary(
    validation: ValidationResult,
    *,
    field_kind: str,
    max_items: int = 3,
) -> str:
    if validation.ok:
        return ""
    required: list[str] = []
    other: list[str] = []
    for issue in validation.errors:
        if issue.code == "required":
            required.append(_required_issue_label(issue.message))
        elif issue.code == "missing_table_channel" and issue.field:
            other.append(f"missing required table channel: {issue.field}")
        elif issue.code == "sidecar_requires_confirmation":
            other.append("YAML fields need confirmation")
        elif issue.code == "missing_runs":
            other.append("no included runs")
        else:
            other.append(issue.message.rstrip("."))

    parts: list[str] = []
    if required:
        parts.append(f"missing required {field_kind} fields: {_limited_join(required, max_items)}")
    parts.extend(_dedupe_text(other))
    return "; ".join(parts)


def _validation_warning_summary(validation: ValidationResult) -> str:
    if not validation.warnings:
        return ""
    warnings: list[str] = []
    has_parser_default = False
    for issue in validation.warnings:
        if issue.code == "assumed_table_unit":
            has_parser_default = True
            unit = _quoted_unit_from_message(issue.message)
            label = issue.field or "Channel"
            if unit:
                warnings.append(f"{label} unit missing; assuming {unit}")
            else:
                warnings.append(issue.message.rstrip("."))
        else:
            warnings.append(issue.message.rstrip("."))
    text = "; ".join(_dedupe_text(warnings))
    if has_parser_default:
        text = _with_terminal_period(text) + " Double-click run to edit parser defaults."
    return text


def _quoted_unit_from_message(message: str) -> str:
    parts = str(message).split("'")
    return parts[1] if len(parts) >= 3 else ""


def _required_issue_label(message: str) -> str:
    text = message.strip().rstrip(".")
    suffix = " is required"
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def _limited_join(items: list[str], limit: int) -> str:
    unique = _dedupe_text(items)
    if len(unique) <= limit:
        return ", ".join(unique)
    return f"{', '.join(unique[:limit])}, +{len(unique) - limit} more"


def _dedupe_text(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = " ".join(str(item or "").split())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        unique.append(text)
    return unique


def _with_terminal_period(text: str) -> str:
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _get_dotted_value(payload: object, path: str) -> object:
    cursor = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _merge_visible_form_values(
    existing: dict[str, EnrichedFieldValue],
    values: dict[str, EnrichedFieldValue],
) -> dict[str, EnrichedFieldValue]:
    merged = dict(existing)
    for field_id, value in values.items():
        if _empty_enriched_value(value):
            merged.pop(field_id, None)
        else:
            merged[field_id] = value
    return merged


def _merge_visible_form_units(
    existing: dict[str, str | None],
    units: dict[str, str | None],
    values: dict[str, EnrichedFieldValue],
) -> dict[str, str | None]:
    merged = dict(existing)
    for field_id, value in values.items():
        if _empty_enriched_value(value):
            merged.pop(field_id, None)
        else:
            merged[field_id] = units.get(field_id)
    return merged


def _empty_enriched_value(value: EnrichedFieldValue | object) -> bool:
    raw = value.value if isinstance(value, EnrichedFieldValue) else value
    return raw in (None, "")


def _dedupe_paths(paths) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        item = Path(path)
        try:
            key = str(item.resolve()).casefold()
        except OSError:
            key = str(item).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _bundle_metadata_cache(bundles: list[BundleState], excluded_runs: list[BundleRunState] | None = None) -> dict[str, dict[str, object]]:
    bundle_cache: dict[str, object] = {}
    run_cache: dict[str, object] = {}
    for bundle in bundles:
        snapshot = (
            dict(bundle.dataset_enrichment),
            dict(bundle.dataset_units),
        )
        bundle_cache[f"key:{bundle.bundle_key}"] = snapshot
        bundle_cache[f"name:{bundle.display_name.casefold()}"] = snapshot
        for run in bundle.runs:
            run_cache[_source_key(run.source_path)] = (
                dict(run.enrichment),
                dict(run.field_units),
            )
    for run in excluded_runs or []:
        run_cache[_source_key(run.source_path)] = (
            dict(run.enrichment),
            dict(run.field_units),
        )
    return {"bundles": bundle_cache, "runs": run_cache}


def _restore_bundle_metadata_cache(
    bundles: list[BundleState],
    cache: dict[str, dict[str, object]],
    excluded_runs: list[BundleRunState] | None = None,
) -> None:
    bundle_cache = cache.get("bundles", {})
    run_cache = cache.get("runs", {})
    for bundle in bundles:
        snapshot = bundle_cache.get(f"key:{bundle.bundle_key}") or bundle_cache.get(f"name:{bundle.display_name.casefold()}")
        if isinstance(snapshot, tuple) and len(snapshot) == 2:
            values, units = snapshot
            if isinstance(values, dict):
                bundle.dataset_enrichment.update({key: value for key, value in values.items() if not _empty_enriched_value(value)})
            if isinstance(units, dict):
                bundle.dataset_units.update(units)
        for run in bundle.runs:
            run_snapshot = run_cache.get(_source_key(run.source_path))
            if isinstance(run_snapshot, tuple) and len(run_snapshot) == 2:
                values, units = run_snapshot
                if isinstance(values, dict):
                    run.enrichment.update({key: value for key, value in values.items() if not _empty_enriched_value(value)})
                if isinstance(units, dict):
                    run.field_units.update(units)
    for run in excluded_runs or []:
        run_snapshot = run_cache.get(_source_key(run.source_path))
        if isinstance(run_snapshot, tuple) and len(run_snapshot) == 2:
            values, units = run_snapshot
            if isinstance(values, dict):
                run.enrichment.update({key: value for key, value in values.items() if not _empty_enriched_value(value)})
            if isinstance(units, dict):
                run.field_units.update(units)


def _source_key(path: Path) -> str:
    try:
        return str(path.expanduser().resolve()).casefold()
    except OSError:
        return str(path).casefold()


def _schema_field_index(schemas: list[MTDPSchema]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for schema in schemas:
        for field in (*schema.dataset_fields, *schema.run_fields):
            fields.setdefault(field.field_id, field)
    return fields


def _repurpose_missing_values(
    values: dict[str, EnrichedFieldValue],
    units: dict[str, str | None],
    target_fields: tuple[object, ...],
    field_index: dict[str, object],
) -> None:
    for target in target_fields:
        target_id = getattr(target, "field_id", "")
        if target_id in values and not _empty_enriched_value(values[target_id]):
            continue
        candidate = _best_repurpose_candidate(target, values, field_index)
        if candidate is None:
            continue
        source_id, source_value = candidate
        coerced = _coerce_for_target_field(target, source_value)
        if coerced is None:
            continue
        values[target_id] = coerced
        if source_id in units:
            units[target_id] = units.get(source_id)


def _best_repurpose_candidate(
    target: object,
    values: dict[str, EnrichedFieldValue],
    field_index: dict[str, object],
) -> tuple[str, EnrichedFieldValue] | None:
    ranked: list[tuple[int, str, EnrichedFieldValue]] = []
    for source_id, source_value in values.items():
        if source_id == getattr(target, "field_id", "") or _empty_enriched_value(source_value):
            continue
        source = field_index.get(source_id)
        if source is None:
            continue
        score = _field_similarity_score(source, target)
        if score > 0:
            ranked.append((score, source_id, source_value))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    _score, source_id, source_value = ranked[0]
    return source_id, source_value


def _field_similarity_score(source: object, target: object) -> int:
    if _norm(getattr(source, "field_id", "")) == _norm(getattr(target, "field_id", "")):
        return 100
    if getattr(source, "report_role", None) and getattr(source, "report_role", None) == getattr(target, "report_role", None):
        return 90
    if getattr(source, "method_role", None) and getattr(source, "method_role", None) == getattr(target, "method_role", None):
        return 80
    if _norm(getattr(source, "label", "")) and _norm(getattr(source, "label", "")) == _norm(getattr(target, "label", "")):
        return 70
    source_token = getattr(getattr(source, "storage", None), "token", None)
    target_token = getattr(getattr(target, "storage", None), "token", None)
    if _norm(source_token) and _norm(source_token) == _norm(target_token):
        return 70
    source_aliases = {_norm(item) for item in getattr(source, "import_aliases", ()) or () if _norm(item)}
    target_aliases = {_norm(item) for item in getattr(target, "import_aliases", ()) or () if _norm(item)}
    source_aliases.add(_norm(getattr(source, "field_id", "")))
    target_aliases.add(_norm(getattr(target, "field_id", "")))
    if source_aliases & target_aliases:
        return 60
    return 0


def _coerce_for_target_field(target: object, value: EnrichedFieldValue) -> EnrichedFieldValue | None:
    raw = value.value
    allowed = tuple(getattr(target, "allowed_values", ()) or ())
    if allowed:
        mapped = _mapped_enum_value(target, raw)
        if mapped not in allowed:
            return None
        return EnrichedFieldValue(mapped, value.unit, value.source)
    return value


def _mapped_enum_value(target: object, raw: object) -> str:
    text = str(raw or "").strip()
    value_map = getattr(target, "value_map", {}) or {}
    for key in (text, text.casefold()):
        if key in value_map:
            return str(value_map[key])
    allowed = tuple(getattr(target, "allowed_values", ()) or ())
    if text in allowed:
        return text
    normalized = _norm(text)
    for value, label in (getattr(target, "display_labels", {}) or {}).items():
        if normalized == _norm(label):
            return str(value)
    return text


def _norm(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").casefold().split())


def _bundle_from_group_state(group: GroupState) -> BundleState:
    bundle = BundleState(group.group_key, group.display_name)
    bundle.dataset_enrichment = dict(group.dataset_enrichment)
    bundle.dataset_units = dict(group.dataset_units)
    bundle.supplemental_files = list(group.supplemental_files)
    bundle.removed_runs = list(group.removed_runs)
    bundle.manual_corrections = group.manual_corrections
    bundle.runs = [_bundle_run_from_run_state(run) for run in group.runs]
    return bundle


def _bundle_run_from_run_state(run: RunState) -> BundleRunState:
    return BundleRunState(
        run_id=run.run_id,
        source_path=run.source_path,
        parsed=run.parsed,
        enrichment=dict(run.enrichment),
        field_units=dict(run.field_units),
        status=run.status,
        sidecar_path=run.sidecar_path,
        sidecar_import_status=run.sidecar_import_status,
        sidecar_conflicts=list(run.sidecar_conflicts),
        sidecar_unknown_keys=list(run.sidecar_unknown_keys),
        sidecar_mapping_profile_id=run.sidecar_mapping_profile_id,
        sidecar_mapping_profile_path=run.sidecar_mapping_profile_path,
        sidecar_import_mode=run.sidecar_import_mode,
        images=list(run.images),
        supplemental_files=list(run.supplemental_files),
    )


def _group_from_bundle_state(bundle: BundleState, schema: MTDPSchema) -> GroupState:
    group = GroupState(
        group_key=bundle.bundle_key,
        display_name=bundle.display_name,
        schema=schema,
        dataset_enrichment=dict(bundle.dataset_enrichment),
        dataset_units=dict(bundle.dataset_units),
        supplemental_files=list(bundle.supplemental_files),
        removed_runs=list(bundle.removed_runs),
        manual_corrections=bundle.manual_corrections,
    )
    group.runs = [_run_state_from_bundle_run(run) for run in bundle.runs]
    return group


def _run_state_from_bundle_run(run: BundleRunState) -> RunState:
    return RunState(
        run_id=run.run_id,
        source_path=run.source_path,
        parsed=run.parsed,
        enrichment=dict(run.enrichment),
        field_units=dict(run.field_units),
        status=run.status,
        sidecar_path=run.sidecar_path,
        sidecar_import_status=run.sidecar_import_status,
        sidecar_conflicts=list(run.sidecar_conflicts),
        sidecar_unknown_keys=list(run.sidecar_unknown_keys),
        sidecar_mapping_profile_id=run.sidecar_mapping_profile_id,
        sidecar_mapping_profile_path=run.sidecar_mapping_profile_path,
        sidecar_import_mode=run.sidecar_import_mode,
        images=list(run.images),
        supplemental_files=list(run.supplemental_files),
    )
