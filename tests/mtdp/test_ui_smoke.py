from __future__ import annotations

import shutil
from pathlib import Path

import pytest


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_main_window_constructs_with_available_qt_backend(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QT_API, QtWidgets
    from ui.method_run_wizard._tokens import Color

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    assert QT_API == "PySide6"
    assert window.objectName() == "mtdpMainWindow"
    assert window.windowTitle() == "MTDP Enrichment Tool"
    assert Color.BG in window.styleSheet()
    assert window.centralWidget().objectName() == "mainWorkspace"
    assert window.schema_selector.combo.count() == 4
    selector_labels = [
        window.schema_selector.combo.itemText(index)
        for index in range(window.schema_selector.combo.count())
    ]
    assert "Compression - v0.3.0" in selector_labels
    assert all("active" not in label and "deprecated" not in label for label in selector_labels)
    assert window.bundle_builder is not None
    assert window.image_dialog is not None
    assert window.image_panel is window.image_dialog.panel
    assert window.tabs.tabText(0) == "Dataset"
    assert window.tabs.tabText(1) == "Run analysis inputs"
    assert not window.tabs.isTabEnabled(1)
    assert window.menuBar().actions()
    assert window.validate_button.text() == "Validate"
    assert window.export_button.text() == "Export selected"
    assert not window.export_button.isEnabled()
    assert not window.validate_button.isEnabled()
    assert "activity_log" in window.actions
    empty_title = window.empty_state_panel.findChild(QtWidgets.QLabel, "emptyStateTitle")
    assert empty_title is not None
    assert empty_title.text() == "Drop compression data here"

    window.close()
    app.quit()


def test_main_window_activity_log_retains_status_messages(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    window.show_message("Verification used parser default for Time.")
    window.show_activity_log()

    assert window.activity_log_dialog is not None
    assert window.activity_log_dialog.isVisible()
    assert window.activity_log_view is not None
    assert "Verification used parser default for Time." in window.activity_log_view.toPlainText()

    window.close()
    app.quit()


def test_bundle_builder_moves_and_excludes_runs(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.grouping import GroupingInput, SampleTypeGrouper
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry
    from mtdp_enrichment.ui.bundle_builder import BundleBuilder
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    first = tmp_path / "Untreated-Comp-E1.csv"
    second = tmp_path / "Heated-Comp-E1.csv"
    shutil.copyfile(FIXTURE, first)
    shutil.copyfile(FIXTURE, second)
    parser = ParserAdapter()
    registry = SchemaRegistry()
    schema = registry.get("mechanical.compression")
    inputs = [
        GroupingInput(first, parser.parse(first), registry.infer(parser.parse(first), first)),
        GroupingInput(second, parser.parse(second), registry.infer(parser.parse(second), second)),
    ]
    proposal = SampleTypeGrouper().propose(inputs, schema)

    builder = BundleBuilder()
    builder.load_proposal(proposal, inputs)

    assert len(builder.bundles) == 2
    untreated = next(bundle for bundle in builder.bundles if bundle.display_name == "Untreated")
    heated = next(bundle for bundle in builder.bundles if bundle.display_name == "Heated")
    builder.move_run_to_bundle(heated.runs[0].source_path, untreated.bundle_key)
    assert len(untreated.runs) == 2
    assert len(heated.runs) == 0
    builder.exclude_run(untreated.runs[0].source_path)
    assert len(builder.excluded_runs) == 1
    builder.include_excluded_run(builder.excluded_runs[0].source_path, untreated.bundle_key)
    assert not builder.excluded_runs
    builder.rename_bundle(untreated.bundle_key, "Control")
    assert any(bundle.display_name == "Control" for bundle in builder.bundles)

    builder.close()
    app.quit()


def test_main_window_dropped_folder_recurses_and_imports_same_stem_yaml(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    root = tmp_path / "drop_root"
    nested = root / "batch_a"
    nested.mkdir(parents=True)
    source = nested / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    source.with_suffix(".yaml").write_text("sample_type: Dropped Control\noperator: G. Damilano\n", encoding="utf-8")

    window = MainWindow()
    window.process_dropped_paths([root])

    assert window.current_folder == root
    assert len(window.grouping_inputs) == 1
    assert window.bundle_builder.bundles[0].display_name == "Dropped Control"
    run = window.bundle_builder.all_runs()[0]
    assert run.source_path == source
    assert run.sidecar_path == source.with_suffix(".yaml")
    assert "YAML" in run.sidecar_import_status
    assert run.enrichment["operator"].value == "G. Damilano"

    window.close()
    app.quit()


def test_main_window_dropped_yaml_resolves_omonimous_raw_source(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    sidecar = source.with_suffix(".yaml")
    sidecar.write_text("sample_type: YAML First\nspecimen_width:\n  value: 9.75\n  unit: mm\n", encoding="utf-8")

    window = MainWindow()
    window.process_dropped_paths([sidecar])

    assert window.current_folder == tmp_path
    assert len(window.grouping_inputs) == 1
    assert window.bundle_builder.bundles[0].display_name == "YAML First"
    run = window.bundle_builder.all_runs()[0]
    assert run.source_path == source
    assert run.sidecar_path == sidecar
    assert run.enrichment["width"].value == 9.75
    assert run.enrichment["width"].unit == "mm"

    window.close()
    app.quit()


def test_main_window_validation_reason_names_missing_run_fields(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.preamble_tokens.clear()
    run = BundleRunState("run_001", source, parsed, confidence=0.82, reason="filename pattern")
    bundle = BundleState("comp", "Comp", runs=[run])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()

    assert not window.validate_selected_bundle()
    assert run.status == "needs input"
    assert "missing required run fields" in run.reason
    assert "Specimen name" in run.reason
    assert "Width" in run.reason
    assert "filename pattern" not in run.reason
    assert "Issue:" in window.review_label.text()
    assert "missing required run fields" in window.status_label.text()
    run_item = window.bundle_builder.tree.topLevelItem(0).child(0)
    assert run_item.text(3) == run.reason

    window.close()
    app.quit()


def test_main_window_validation_reason_names_table_channel_issue(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.channels.load_channels.clear()
    run = BundleRunState("run_001", source, parsed, confidence=0.82, reason="filename pattern")
    bundle = BundleState("comp", "Comp", runs=[run])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()

    assert not window.validate_selected_bundle()
    assert run.status == "needs input"
    assert "missing required table channel: load" in run.reason
    assert "filename pattern" not in run.reason
    assert "missing required table channel: load" in window.review_label.text()

    window.close()
    app.quit()


def test_main_window_validation_updates_after_run_fields_are_filled(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.preamble_tokens.clear()
    run = BundleRunState("run_001", source, parsed)
    bundle = BundleState("comp", "Comp", runs=[run])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    window._select_run(run)
    window._bundle_selection_changed()
    window.run_form.set_field_value("specimen_name", "Filled specimen", None)
    window.run_form.set_field_value("width", "9.8", "mm")
    window.run_form.set_field_value("thickness", "2.3", "mm")

    assert window.validate_selected_bundle()
    assert run.status == "ready"
    assert run.reason == "ready"
    assert "Selected group is ready." == window.status_label.text()
    assert "Runs needing input: 0" in window.review_label.text()

    window.close()
    app.quit()


def test_main_window_validation_warns_for_missing_time_unit_without_blocking(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.channels.time_channels[0].original_unit_text = None
    parsed.channels.time_channels[0].canonical_unit = None
    run = BundleRunState("run_001", source, parsed)
    bundle = BundleState("comp", "Comp", runs=[run])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()

    assert window.validate_selected_bundle()
    assert run.status == "ready"
    assert "Time unit missing; assuming s" in run.reason
    assert "Double-click run to edit parser defaults" in run.reason
    assert "Note:" in window.review_label.text()
    assert "Time unit missing; assuming s" in window.status_label.text()

    window.close()
    app.quit()


def test_parser_review_dialog_updates_missing_time_unit_for_normalization(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.normalization import UnitNormalizer
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry
    from mtdp_enrichment.ui.bundle_builder import BundleRunState
    from mtdp_enrichment.ui.parser_review_dialog import ParserReviewDialog
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    time_channel = parsed.channels.time_channels[0]
    time_channel.original_unit_text = None
    time_channel.canonical_unit = None
    run = BundleRunState("run_001", source, parsed)
    schema = SchemaRegistry().get("mechanical.compression")

    dialog = ParserReviewDialog(run, schema)
    time_row = next(index for index, row in enumerate(dialog.rows) if row.channel is time_channel)
    unit_combo = dialog.rows[time_row].unit_combo
    assert unit_combo.findText("ms") >= 0
    assert unit_combo.findText("us") >= 0
    assert "Missing unit" in dialog.rows[time_row].status_item.text()
    assert "Parsed" in dialog.rows[time_row].quality_item.text()
    assert "numeric.plain_dot_decimal" in dialog.rows[time_row].quality_item.text()

    unit_combo.setCurrentText("ms")
    dialog.apply_changes()
    result = UnitNormalizer().normalize(parsed, schema)
    normalized_time = next(column for column in result.columns if column.family == "time")

    assert time_channel.original_unit_text == "ms"
    assert result.validation.ok
    assert normalized_time.unit == "s"
    assert normalized_time.values[1] == pytest.approx(0.0001)

    dialog.close()
    app.quit()


def test_bundle_builder_double_click_run_requests_parser_review(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleBuilder, BundleRunState, BundleState
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    run = BundleRunState("run_001", source, ParserAdapter().parse(source))
    builder = BundleBuilder()
    builder.bundles = [BundleState("comp", "Comp", runs=[run])]
    builder.refresh()
    emitted = []
    builder.run_open_requested.connect(lambda item: emitted.append(item))

    builder._double_clicked(builder.tree.topLevelItem(0).child(0))

    assert emitted == [run]

    builder.close()
    app.quit()


def test_main_window_validation_names_remaining_run_when_selected_run_is_filled(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    parser = ParserAdapter()
    source_a = tmp_path / "Comp-E1.csv"
    source_b = tmp_path / "Comp-E2.csv"
    shutil.copyfile(FIXTURE, source_a)
    shutil.copyfile(FIXTURE, source_b)
    parsed_a = parser.parse(source_a)
    parsed_b = parser.parse(source_b)
    parsed_a.preamble_tokens.clear()
    parsed_b.preamble_tokens.clear()
    run_a = BundleRunState("run_001", source_a, parsed_a)
    run_b = BundleRunState("run_002", source_b, parsed_b)
    bundle = BundleState("comp", "Comp", runs=[run_a, run_b])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    window._select_run(run_a)
    window._bundle_selection_changed()
    window.run_form.set_field_value("specimen_name", "Filled specimen", None)
    window.run_form.set_field_value("width", "9.8", "mm")
    window.run_form.set_field_value("thickness", "2.3", "mm")

    assert not window.validate_selected_bundle()
    assert run_a.status == "ready"
    assert run_b.status == "needs input"
    assert "run_002" in window.status_label.text()
    assert "run_002" in window.review_label.text()
    assert "Specimen name" in window.review_label.text()

    window.close()
    app.quit()


def test_main_window_validation_reason_names_invalid_numeric_input(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.models import EnrichedFieldValue
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.preamble_tokens.clear()
    run = BundleRunState(
        "run_001",
        source,
        parsed,
        enrichment={
            "specimen_name": EnrichedFieldValue("Bad width", source="test"),
            "width": EnrichedFieldValue("wide", "mm", source="test"),
            "thickness": EnrichedFieldValue("2.3", "mm", source="test"),
        },
    )
    bundle = BundleState("comp", "Comp", runs=[run])

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()

    assert not window.validate_selected_bundle()
    assert "Width has invalid float input" in run.reason
    assert "Width has invalid float input" in window.review_label.text()

    window.close()
    app.quit()


def test_main_window_export_blocks_before_save_dialog_when_validation_fails(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    parsed.preamble_tokens.clear()
    run = BundleRunState("run_001", source, parsed)
    bundle = BundleState("comp", "Comp", runs=[run])
    prompted = False

    def fail_if_prompted(*_args):
        nonlocal prompted
        prompted = True
        return "", ""

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", fail_if_prompted)

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    window.export_selected_bundle()

    assert not prompted
    assert "missing required run fields" in window.status_label.text()

    window.close()
    app.quit()


def test_main_window_export_selected_cancel_does_not_write(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    run = BundleRunState("run_001", source, parsed)
    bundle = BundleState("comp", "Comp", runs=[run])
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *_args: ("", ""))

    window = MainWindow()
    monkeypatch.setattr(window, "_write_bundle", lambda *_args: pytest.fail("export should not write after cancel"))
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    window.export_selected_bundle()

    assert window.status_label.text() == "Export cancelled."
    assert window.last_exported_package_path is None

    window.close()
    app.quit()


def test_main_window_export_selected_prompts_for_path_and_appends_extension(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = tmp_path / "Comp-E1.csv"
    shutil.copyfile(FIXTURE, source)
    parsed = ParserAdapter().parse(source)
    run = BundleRunState("run_001", source, parsed)
    bundle = BundleState("comp", "Comp", runs=[run])
    output_without_suffix = tmp_path / "chosen_export_name"
    dialog_defaults: list[str] = []

    def choose_path(_parent, _title, default_path, _filter):
        dialog_defaults.append(default_path)
        return str(output_without_suffix), ""

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", choose_path)

    window = MainWindow()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    window.export_selected_bundle()

    expected_output = output_without_suffix.with_suffix(".mtdp")
    assert Path(dialog_defaults[0]).name == "Comp.mtdp"
    assert window.last_exported_package_path == expected_output
    assert expected_output.exists()
    assert "Wrote and validated chosen_export_name.mtdp" in window.status_label.text()

    window.close()
    app.quit()


def test_bundle_builder_can_unassign_full_group_and_move_multiple_runs(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleBuilder, BundleRunState, BundleState
    from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
    from PySide6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    parser = ParserAdapter()
    sources = [tmp_path / f"Comp-E{index}.csv" for index in range(1, 7)]
    for source in sources:
        shutil.copyfile(FIXTURE, source)
    source_bundle = BundleState(
        "source",
        "Source",
        runs=[
            BundleRunState(f"run_{index:03d}", source, parser.parse(source))
            for index, source in enumerate(sources[:3], start=1)
        ],
    )
    target_bundle = BundleState(
        "target",
        "Target",
        runs=[
            BundleRunState(f"run_{index:03d}", source, parser.parse(source))
            for index, source in enumerate(sources[3:], start=1)
        ],
    )
    builder = BundleBuilder()
    builder.bundles = [source_bundle, target_bundle]
    builder.refresh()
    builder.show()
    builder.tree.setFocus()
    QtTest.QTest.qWait(50)

    builder.move_runs_to_bundle([run.source_path for run in source_bundle.runs], target_bundle.bundle_key)
    assert len(source_bundle.runs) == 0
    assert len(target_bundle.runs) == 6
    target_item = builder.tree.topLevelItem(1)
    assert target_item.text(1) == "6 run(s)"
    assert target_item.childCount() == 6

    builder.tree.setCurrentItem(builder.tree.topLevelItem(1))
    builder.tree.topLevelItem(1).setSelected(True)
    QtTest.QTest.keyClick(builder.tree, QtCore.Qt.Key.Key_Delete)
    QtTest.QTest.qWait(50)
    assert target_bundle not in builder.bundles
    assert len(builder.excluded_runs) == 6
    assert {run.status for run in builder.excluded_runs} == {"unassigned"}
    unassigned = builder.tree.topLevelItem(builder.tree.topLevelItemCount() - 1)
    assert unassigned.text(1) == "6 run(s)"
    assert unassigned.childCount() == 6

    builder.close()
    app.quit()


def test_schema_selector_exposes_legacy_schema_only_for_loaded_package(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.schemas import SchemaRegistry
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from mtdp_enrichment.ui.schema_selector import SchemaSelector

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    registry = SchemaRegistry()
    selector = SchemaSelector(registry)

    labels = [selector.combo.itemText(index) for index in range(selector.combo.count())]
    assert "Compression - v0.3.0" in labels
    assert not any("Compression - v0.2.0" in label for label in labels)
    assert all("active" not in label and "deprecated" not in label for label in labels)

    legacy_schema = registry.get("mechanical.compression", "0.2.0")
    selector.set_loaded_schema(legacy_schema)

    labels = [selector.combo.itemText(index) for index in range(selector.combo.count())]
    assert "Compression - v0.3.0 - active" in labels
    assert "Compression - v0.2.0 - deprecated" in labels
    assert not any("Compression - v0.1.0" in label for label in labels)
    assert selector.current_schema().schema_version == "0.2.0"

    selector.close()
    app.quit()


def test_image_evidence_panel_add_remove_model(monkeypatch, tmp_path: Path):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.image_gateway import RunImageEvidence
    from mtdp_enrichment.ui.image_evidence_panel import ImageEvidencePanel
    from mtdp_enrichment.ui.qt_compat import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    image = tmp_path / "front.jpg"
    image.write_bytes(b"jpeg evidence")

    panel = ImageEvidencePanel()
    panel.set_images([RunImageEvidence(image, "front")])

    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "front"
    assert panel.table.item(0, 1).text() == "front.jpg"

    panel.close()
    app.quit()


def test_wheel_guard_consumes_unfocused_combo_wheel(monkeypatch):
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
    from mtdp_enrichment.ui.wheel_guard import install_wheel_guard

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    combo = QtWidgets.QComboBox()
    combo.addItems(["A", "B"])
    install_wheel_guard(combo)
    event = QtGui.QWheelEvent(
        QtCore.QPointF(1, 1),
        QtCore.QPointF(1, 1),
        QtCore.QPoint(0, 0),
        QtCore.QPoint(0, 120),
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.Qt.ScrollPhase.ScrollUpdate,
        False,
    )

    assert combo._mtdp_wheel_guard.eventFilter(combo, event)
    assert combo.currentText() == "A"

    combo.close()
    app.quit()
