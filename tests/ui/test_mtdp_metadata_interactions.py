from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.ui.metadata_section_panel import FIELD_MARKER_LEGEND, metadata_section_panel_model
from tests.ui.helpers.qt_interaction import process_events_until


def test_mtdp_main_window_launches_with_operator_actions(monkeypatch) -> None:
    app, _QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    assert process_events_until(app, window.isVisible)
    assert window.windowTitle() == "MTDP Enrichment Tool"
    assert window.schema_selector.combo.currentText()
    assert window.tabs.tabText(0) == "Dataset"
    assert not window.tabs.isTabEnabled(1)
    assert window.validate_button.text() == "Validate"
    assert not window.validate_button.isEnabled()
    assert window.export_button.text() == "Export selected"
    assert not window.export_button.isEnabled()
    assert "tools_run_method" not in window.actions
    assert "create_bundle" in window.actions
    assert "remove_bundle" in window.actions

    window.close()


def test_metadata_section_tabs_markers_and_keyboard_entry(monkeypatch) -> None:
    app, QtWidgets, QtCore, QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.schema_form import SchemaForm

    schema = SchemaRegistry().get("mechanical.compression")
    form = SchemaForm()
    form.build(schema, scope="dataset")
    form.show()

    tabs = form.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    assert tabs.count() >= 3
    assert any("required missing" in tabs.tabToolTip(index) for index in range(tabs.count()))
    assert any("recommended missing" in tabs.tabToolTip(index) for index in range(tabs.count()))

    legend = form.findChild(QtWidgets.QLabel, "metadata_marker_legend")
    assert legend is not None
    assert legend.text() == FIELD_MARKER_LEGEND

    labels = [label.text() for label in form.findChildren(QtWidgets.QLabel)]
    assert any(text.endswith(" *") for text in labels)
    assert any(text.endswith(" **") for text in labels)

    sample_widget = form._value_widgets["sample_type"]
    sample_widget.setFocus()
    QtTest.QTest.keyClicks(sample_widget, "SS85_100_60")
    assert process_events_until(app, lambda: form.values()[0]["sample_type"].value == "SS85_100_60")

    # Mouse-like tab navigation keeps the user in the metadata section model.
    if tabs.count() > 1:
        tab_rect = tabs.tabBar().tabRect(1)
        QtTest.QTest.mouseClick(tabs.tabBar(), QtCore.Qt.MouseButton.LeftButton, pos=tab_rect.center())
        assert tabs.currentIndex() == 1

    values, _units = form.values()
    assert values["sample_type"].value == "SS85_100_60"

    form.close()


def test_metadata_section_tab_counts_follow_visible_values(monkeypatch) -> None:
    app, QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.schema_form import SchemaForm

    schema = SchemaRegistry().get("mechanical.compression")
    form = SchemaForm()
    form.build(schema, scope="run")
    form.show()

    tabs = form.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    specimen_index = next(
        index for index in range(tabs.count()) if tabs.tabText(index).startswith("Specimen Geometry")
    )
    assert "0/8 filled" in tabs.tabText(specimen_index)

    for field_id, value, unit in [
        ("specimen_name", "CAG-CF-ER-Comp-E4", None),
        ("sample_id", "CAG-CF-Modied-ULV20-E4", None),
        ("width", "9.73", "mm"),
        ("thickness", "2.17", "mm"),
        ("gauge_length", "20", "mm"),
    ]:
        form.set_field_value(field_id, value, unit)

    assert process_events_until(app, lambda: "5/8 filled" in tabs.tabText(specimen_index))
    assert "Complete" in tabs.tabToolTip(specimen_index)

    form.set_field_value("gauge_length", "", None)
    assert process_events_until(app, lambda: "4/8 filled" in tabs.tabText(specimen_index))

    form.close()


def test_schema_form_enum_dropdowns_show_human_labels(monkeypatch) -> None:
    _app, QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.schema_form import SchemaForm

    schema = SchemaRegistry().get("mechanical.compression")
    form = SchemaForm()
    form.build(schema, scope="run")
    form.show()
    tabs = form.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    tabs.setCurrentIndex(next(index for index in range(tabs.count()) if tabs.tabText(index).startswith("User Validity")))

    failure_mode = form._value_widgets["primary_failure_mode"]
    failure_location = form._value_widgets["failure_location"]
    invalid_reason = form._value_widgets["invalid_specimen_reason"]
    invalid_reason_other = form._value_widgets["invalid_specimen_reason_other"]
    bending_observation = form._value_widgets["visible_buckling_or_bending_observation"]
    bending_observation_other = form._value_widgets["visible_buckling_or_bending_observation_other"]
    requires_review = form._value_widgets["requires_review"]

    assert isinstance(failure_mode, QtWidgets.QComboBox)
    assert isinstance(failure_location, QtWidgets.QComboBox)
    assert isinstance(invalid_reason, QtWidgets.QComboBox)
    assert isinstance(bending_observation, QtWidgets.QComboBox)
    assert isinstance(requires_review, QtWidgets.QComboBox)
    labels = [label.text() for label in form.findChildren(QtWidgets.QLabel)]
    assert "Primary failure mode *" in labels
    assert "Failure location *" in labels
    assert "Invalid specimen reason" in labels
    assert "Visible buckling / bending observation" in labels
    assert failure_mode.itemText(failure_mode.findData("in_plane_shear")) == "In-plane shear"
    assert failure_location.itemText(failure_location.findData("within_gauge_length")) == "Within gauge length"
    assert invalid_reason.itemText(invalid_reason.findData("bending_non_compliance")) == "Bending non-compliance"
    assert invalid_reason.itemText(invalid_reason.findData("grip_end_block_failure")) == "Grip/end block failure"
    assert invalid_reason.itemText(invalid_reason.findData("end_tab_failure")) == "End tab failure"
    assert bending_observation.itemText(bending_observation.findData("none_observed")) == "None observed"
    assert bending_observation.itemText(bending_observation.findData("suspected_euler_buckling")) == "Suspected Euler buckling"
    assert not invalid_reason_other.isVisible()
    assert not bending_observation_other.isVisible()
    form.set_field_value("invalid_specimen_reason", "other", None)
    form.set_field_value("visible_buckling_or_bending_observation", "other", None)
    assert invalid_reason_other.isVisible()
    assert bending_observation_other.isVisible()
    labels = [label.text() for label in form.findChildren(QtWidgets.QLabel)]
    assert "Other invalid specimen reason *" in labels
    assert "Other buckling / bending observation *" in labels
    assert requires_review.itemText(requires_review.findData(True)) == "Yes"
    assert requires_review.itemText(requires_review.findData(False)) == "No"
    assert all("_" not in invalid_reason.itemText(index) for index in range(invalid_reason.count()))
    assert all("_" not in bending_observation.itemText(index) for index in range(bending_observation.count()))

    form.close()


def test_schema_form_other_choices_reveal_detail_fields(monkeypatch) -> None:
    _app, QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.schema_form import SchemaForm

    schema = SchemaRegistry().get("mechanical.compression")
    form = SchemaForm()
    form.build(schema, scope="dataset")
    form.show()
    tabs = form.findChild(QtWidgets.QTabWidget)
    assert tabs is not None
    tabs.setCurrentIndex(next(index for index in range(tabs.count()) if tabs.tabText(index).startswith("Test Identification")))

    loading_method = form._value_widgets["loading_method"]
    loading_method_other = form._value_widgets["loading_method_other"]
    specimen_type = form._value_widgets["specimen_type"]
    specimen_type_other = form._value_widgets["specimen_type_other"]

    assert isinstance(loading_method, QtWidgets.QComboBox)
    assert isinstance(specimen_type, QtWidgets.QComboBox)
    assert not loading_method_other.isVisible()
    assert not specimen_type_other.isVisible()

    form.set_field_value("loading_method", "other_specified", None)
    form.set_field_value("specimen_type", "other_specified", None)

    assert loading_method_other.isVisible()
    assert specimen_type_other.isVisible()
    labels = [label.text() for label in form.findChildren(QtWidgets.QLabel)]
    assert "Other loading method *" in labels
    assert "Other specimen type *" in labels
    loading_method_other.setText("Fixture-specific loading")
    specimen_type_other.setText("Short tabbed coupon")
    values, _units = form.values()
    assert values["loading_method"].value == "other_specified"
    assert values["loading_method_other"].value == "Fixture-specific loading"
    assert values["specimen_type_other"].value == "Short tabbed coupon"

    form.close()


def test_schema_form_field_detail_filter_controls_visible_importance(monkeypatch) -> None:
    _app, _QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.ui.metadata_section_panel import is_recommended_importance, is_required_importance
    from mtdp_enrichment.ui.schema_form import SchemaForm

    schema = SchemaRegistry().get("mechanical.compression")
    required_ids = {
        field.field_id
        for field in schema.run_fields
        if field.required or field.required_when or is_required_importance(field.report_importance)
    }
    recommended_ids = {
        field.field_id
        for field in schema.run_fields
        if is_recommended_importance(field.report_importance)
    }
    optional_ids = {
        field.field_id
        for field in schema.run_fields
        if field.field_id not in required_ids and field.field_id not in recommended_ids
    }
    assert required_ids and recommended_ids and optional_ids

    form = SchemaForm()
    form.build(schema, scope="run", importance_filter="required")
    assert required_ids & set(form._value_widgets)
    assert not recommended_ids & set(form._value_widgets)
    assert not optional_ids & set(form._value_widgets)

    form.build(schema, scope="run", importance_filter="recommended")
    visible = set(form._value_widgets)
    assert required_ids & visible
    assert recommended_ids & visible
    assert not optional_ids & visible

    form.build(schema, scope="run", importance_filter="all")
    visible = set(form._value_widgets)
    assert required_ids & visible
    assert recommended_ids & visible
    assert optional_ids & visible

    form.close()


def test_dataset_selection_bulk_edits_all_run_fields_without_blank_overwrite(monkeypatch, tmp_path: Path) -> None:
    app, _QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow

    parser = ParserAdapter()
    source_a = tmp_path / "Comp-E1.csv"
    source_b = tmp_path / "Comp-E2.csv"
    source_bytes = (ROOT / "tests" / "data" / "Specimen_RawData_1.csv").read_bytes()
    source_a.write_bytes(source_bytes)
    source_b.write_bytes(source_bytes)

    run_a = BundleRunState("run_001", source_a, parser.parse(source_a))
    run_b = BundleRunState("run_002", source_b, parser.parse(source_b))
    run_a.enrichment["primary_failure_mode"] = EnrichedFieldValue("end_crushing", source="existing")
    bundle = BundleState("sample", "Sample", runs=[run_a, run_b])

    window = MainWindow()
    window.show()
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()

    assert process_events_until(app, lambda: window.current_run_sources == [source_a, source_b])
    assert window.run_form.isEnabled()
    specimen_name = window.run_form._value_widgets["specimen_name"]
    specimen_name.setText("Bulk specimen")
    window._save_current_forms()

    assert run_a.enrichment["specimen_name"].value == "Bulk specimen"
    assert run_b.enrichment["specimen_name"].value == "Bulk specimen"
    assert run_a.enrichment["primary_failure_mode"].value == "end_crushing"
    assert "primary_failure_mode" not in run_b.enrichment

    window.close()


def test_main_window_schema_switch_preserves_hidden_metadata(monkeypatch, tmp_path: Path) -> None:
    app, _QtWidgets, _QtCore, _QtTest = _qt(monkeypatch)

    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.ui.bundle_builder import BundleRunState, BundleState
    from mtdp_enrichment.ui.main_window import MainWindow

    source = tmp_path / "Comp-E1.csv"
    source.write_bytes((ROOT / "tests" / "data" / "Specimen_RawData_1.csv").read_bytes())
    parsed = ParserAdapter().parse(source)
    window = MainWindow()
    window.show()
    bundle = BundleState("sample", "Sample")
    run = BundleRunState("run_001", source, parsed)
    bundle.runs.append(run)
    window.bundle_builder.bundles = [bundle]
    window.bundle_builder.refresh()
    window.bundle_builder.select_first_bundle()
    assert process_events_until(app, lambda: window.current_bundle_key == "sample")
    window._select_run(run)
    assert process_events_until(app, lambda: window.current_run_source == source)

    window.dataset_form.set_field_value("loading_method", "other_specified", None)
    window.dataset_form.set_field_value("loading_method_other", "Fixture-specific loading", None)
    window.run_form.set_field_value("invalid_specimen_reason", "other", None)
    window.run_form.set_field_value("invalid_specimen_reason_other", "operator narrative", None)
    window._save_current_forms()

    window.schema_selector.select_schema(window.registry.get("mechanical.compression", "0.2.0"))
    window.schema_selector.select_schema(window.registry.get("mechanical.compression", "0.3.0"))

    assert bundle.dataset_enrichment["loading_method"].value == "other_specified"
    assert bundle.dataset_enrichment["loading_method_other"].value == "Fixture-specific loading"
    assert run.enrichment["invalid_specimen_reason"].value == "other"
    assert run.enrichment["invalid_specimen_reason_other"].value == "operator narrative"

    window.close()


def test_metadata_completion_model_updates_visible_missing_counts() -> None:
    schema = SchemaRegistry().get("mechanical.compression")

    empty_model = metadata_section_panel_model(schema, scope="dataset", values={})
    filled_model = metadata_section_panel_model(
        schema,
        scope="dataset",
        values={
            "sample_type": EnrichedFieldValue("SS85_100_60"),
            "material_label": EnrichedFieldValue("CAG-CF"),
            "treatment": EnrichedFieldValue("aged"),
        },
    )

    assert empty_model.completion_summary["required_missing_count"] > filled_model.completion_summary["required_missing_count"]
    assert filled_model.completion_summary["present_count"] == 3
    assert all(row.display_label.endswith("*") for row in filled_model.missing_fields("required"))


def _qt(monkeypatch):
    from tests.ui.helpers.qt_interaction import ensure_qt_app

    return ensure_qt_app(monkeypatch)
