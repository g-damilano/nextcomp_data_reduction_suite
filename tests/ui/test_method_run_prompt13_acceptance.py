from __future__ import annotations

import re
from pathlib import Path


def test_window_chrome_shortcuts_accessibility_and_tab_order(tmp_path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    package = tmp_path / "example_package.mtdp"
    window = MethodRunWindow(package_path=package)
    MethodRunController(window)

    assert window.windowTitle() == "Run Method on MTDP Package \u2014 example_package.mtdp"
    assert window.minimumWidth() == 760
    assert window.minimumHeight() == 560
    assert window.size().width() == 1280
    assert window.size().height() == 820
    assert not window.demo_bar.isVisible()
    assert window.column.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Policy.Fixed
    assert window.column.maximumWidth() == 1120
    assert window.column.minimumWidth() == window.column.maximumWidth()
    assert window.scroll_area.widget().layout().itemAt(0).widget() is window.column
    assert window.scroll_area.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert window.scroll_area.viewport().objectName() == "methodRunViewportFrame"
    assert window.setup_spotlight.input_summary.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Policy.Fixed
    assert window.setup_spotlight.package_tile.maximumHeight() <= 110
    assert window.setup_spotlight.mapping_task.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Policy.Maximum
    assert window.decor_top.pipeline.layout().count() == 8
    assert window.decor_top.pipeline.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Policy.Expanding
    assert window.decor_top.crumb.minimumWidth() == 0
    window.resize(900, 620)
    window._sync_responsive_width()
    assert window.column.maximumWidth() == 868
    assert window.column.minimumWidth() == window.column.maximumWidth()
    assert window.spotlight.maximumWidth() == window.column.maximumWidth()
    window.resize(1800, 900)
    window._sync_responsive_width()
    assert window.column.maximumWidth() == 1120
    assert window.column.minimumWidth() == window.column.maximumWidth()
    assert window.spotlight.maximumWidth() == window.column.maximumWidth()

    window.resize(900, 620)
    before_height = window.height()
    window.decor_bottom.bar.context_line.toggle()
    window._fit_open_context_detail()
    assert window.height() >= before_height
    assert not window.decor_bottom.detail.isHidden()

    menu_labels = [action.text().replace("&", "") for action in window.method_run_menu_bar.actions()]
    assert menu_labels == ["File", "Method Run", "Output", "View", "Help"]
    assert [action.text().replace("&", "") for action in window.file_menu.actions() if not action.isSeparator()] == [
        "Choose Package...",
        "Close Wizard",
    ]
    assert [
        action.text().replace("&", "")
        for action in window.workflow_menu.actions()
        if not action.isSeparator()
    ] == [
        "Choose Method",
        "Edit Mapping...",
        "Check Readiness",
        "Run Method",
        "Cancel Run",
        "Confirm Review",
        "Finalize MTDA",
    ]
    assert [
        action.text().replace("&", "")
        for action in window.output_menu.actions()
        if not action.isSeparator()
    ] == [
        "Open Test Report",
        "Open Audit Report",
        "Open Workbench",
        "Open Output Folder",
        "Copy MTDA Path",
        "Review Missing Report Fields",
    ]
    assert [action.text().replace("&", "") for action in window.view_menu.actions()] == [
        "Context Details",
        "Activity Log",
    ]
    assert window.context_details_action.isChecked()

    help_actions = [action.text().replace("&", "") for action in window.help_menu.actions()]
    assert "Shortcuts" in help_actions

    assert window.setup_spotlight.mapping_task._header.focusPolicy() == QtCore.Qt.FocusPolicy.StrongFocus
    assert window.setup_spotlight.metadata_task._header.focusPolicy() == QtCore.Qt.FocusPolicy.StrongFocus
    assert window.decor_bottom.bar.context_line.focusPolicy() == QtCore.Qt.FocusPolicy.StrongFocus

    for button in window.findChildren(QtWidgets.QPushButton):
        if button.isVisible() and button.text():
            assert button.accessibleName(), button.text()
        if button.text() and button.property("class") != "link" and button.objectName() != "statusLogLink":
            assert button.minimumWidth() >= button.fontMetrics().horizontalAdvance(button.text()) + 30
            assert button.minimumHeight() >= 32

    window.close()
    app.quit()


def test_menu_actions_track_workflow_state(tmp_path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)

    assert window.choose_package_action.isEnabled()
    assert not window.choose_method_action.isEnabled()
    assert not window.refresh_mapping_action.isEnabled()
    assert not window.check_readiness_action.isEnabled()
    assert not window.run_method_action.isEnabled()
    assert not window.cancel_run_action.isEnabled()
    assert not window.confirm_review_action.isEnabled()
    assert not window.finalize_mtda_action.isEnabled()
    assert not window.output_menu.menuAction().isEnabled()
    assert not window.copy_mtda_path_action.isEnabled()
    assert not window.activity_log_action.isChecked()

    ready_state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.json",
        readiness_report={"status": "READY"},
    )
    ready_window = MethodRunWindow(package_path=ready_state.input_package_path)
    MethodRunController(ready_window, ready_state)

    assert ready_window.choose_package_action.isEnabled()
    assert ready_window.choose_method_action.isEnabled()
    assert ready_window.refresh_mapping_action.isEnabled()
    assert ready_window.check_readiness_action.isEnabled()
    assert ready_window.run_method_action.isEnabled()
    assert not ready_window.cancel_run_action.isEnabled()
    assert not ready_window.confirm_review_action.isEnabled()
    assert not ready_window.finalize_mtda_action.isEnabled()
    assert not ready_window.output_menu.menuAction().isEnabled()

    ready_window.activity_log_action.trigger()
    assert ready_window.activity_log_action.isChecked()
    ready_window.context_details_action.trigger()
    assert not ready_window.decor_bottom.detail.isHidden()
    assert ready_window.context_details_action.isChecked()

    controller._enter_running()
    assert not window.choose_package_action.isEnabled()
    assert window.cancel_run_action.isEnabled()
    assert not window.run_method_action.isEnabled()

    final_state = MethodRunWizardState(
        output_path=tmp_path / "result.mtda",
        service_result={"output_path": str(tmp_path / "result.mtda")},
    )
    final_window = MethodRunWindow()
    MethodRunController(final_window, final_state)._enter_finalize()

    assert final_window.output_menu.menuAction().isEnabled()
    assert final_window.copy_mtda_path_action.isEnabled()
    assert not final_window.finalize_mtda_action.isEnabled()

    final_window.finalize_spotlight.note_edit.setText("Reviewed with warnings.")
    assert final_window.finalize_mtda_action.isEnabled()

    window.close()
    ready_window.close()
    final_window.close()
    app.quit()


def test_primary_scenarios_fit_default_viewport(tmp_path: Path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.json",
        output_path=tmp_path / "output.mtda",
        readiness_report={"status": "READY_WITH_WARNINGS"},
        package_summary={"run_count": 7, "schema_id": "mechanical.compression"},
        method_summary={"method_name": "BS EN ISO 14126:2023 compression properties", "version": "0.1.0"},
        mapping_summary={"mapping_name": "iso14126_manual.json", "critical_bound_count": 35},
        acceptance_summary={
            "total_runs": 7,
            "final_report_count": 5,
            "flagged_runs": [
                {"run_id": "run_003", "default_call": "Remove", "reason": "bending ratio"},
                {"run_id": "run_006", "default_call": "Remove", "reason": "late-window bending"},
            ],
        },
        service_result={"output_path": str(tmp_path / "output.mtda")},
    )
    window = MethodRunWindow(package_path=state.input_package_path)
    controller = MethodRunController(window, state)
    window.resize(1280, 820)
    window.show()
    app.processEvents()

    checks = (
        ("setup", lambda: controller._update_setup_action_bar(), 560),
        ("running", controller._enter_running, 700),
        ("review", controller._enter_review, 560),
        ("finalize", controller._enter_finalize, 700),
    )
    for _name, enter, max_spotlight_height in checks:
        enter()
        app.processEvents()
        window._sync_responsive_width()
        app.processEvents()
        assert window.scroll_area.verticalScrollBar().maximum() == 0
        assert window.spotlight.height() <= max_spotlight_height

    window.close()
    app.quit()


def test_pipeline_context_and_review_gating_acceptance() -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        input_package_path=Path("input.mtdp"),
        method_path=Path("method.yaml"),
        mapping_path=Path("mapping.yaml"),
        readiness_report={
            "status": "READY_WITH_WARNINGS",
            "missing_report_field_count": 7,
            "recommended_missing_count": 38,
        },
        acceptance_summary={
            "final_report_count": 4,
            "flagged_runs": [
                {
                    "run_id": "run_003",
                    "default_call": "Remove",
                    "reason": "bending ratio persisted above threshold",
                    "bending_series": [0.02, 0.04, 0.07, 0.12, 0.16],
                },
                {
                    "run_id": "run_006",
                    "default_call": "Remove",
                    "reason": "late-window bending spike",
                    "bending_series": [0.01, 0.03, 0.04, 0.08, 0.14],
                },
            ],
        },
    )
    window = MethodRunWindow()
    controller = MethodRunController(window, state)

    assert window.decor_top.pipeline._pills["mapping"].property("state") == "ok"
    assert "7 report gaps" in window.decor_bottom.bar.context_line._label.text()

    window.setup_spotlight.save_bindings.emit()
    assert window.decor_top.pipeline._pills["mapping"].property("state") == "ok"
    assert "7 report gaps" in window.decor_bottom.bar.context_line._label.text()
    assert window.spotlight.head.title.text() == "1 thing to decide first"

    controller._enter_running()
    assert window.decor_top.pipeline._pills["exec"].property("state") == "now"

    controller._enter_review()
    assert window.decor_top.pipeline._pills["accept"].property("state") == "warn"
    first_row = next(iter(window.review_spotlight.rows.values()))
    first_row._row.keep_button.click()
    assert not window.action_bars[WizardScenario.REVIEW].primary_button.isEnabled()
    first_row.justify.line_edit.setText("Operator inspected the fixture trace.")
    assert window.action_bars[WizardScenario.REVIEW].primary_button.isEnabled()

    rows = list(window.review_spotlight.rows.values())
    rows[0].set_expanded(True)
    rows[1].set_expanded(True)
    assert rows[0]._detail.isHidden()
    assert not rows[1]._detail.isHidden()

    controller._enter_finalize()
    assert window.decor_top.pipeline._pills["output"].property("state") == "warn"

    window.close()
    app.quit()


def test_run_action_invokes_method_worker_hook(monkeypatch, tmp_path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard import service_adapter
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.yaml",
        output_path=tmp_path / "output.mtda",
        readiness_report={"status": "READY"},
    )
    calls: list[MethodRunWizardState] = []

    def fake_run_method_async(state_arg, *, parent=None, service=None):
        calls.append(state_arg)
        return None

    monkeypatch.setattr(service_adapter, "run_method_async", fake_run_method_async)
    window = MethodRunWindow(package_path=state.input_package_path)
    MethodRunController(window, state)

    window.action_bars[WizardScenario.SETUP].primary_button.click()

    assert calls == [state]
    assert state.scenario == WizardScenario.RUNNING
    assert window.spotlight.body.currentWidget() is window.running_spotlight

    window.close()
    app.quit()


def test_mapping_prompt_default_suggestions_repair_missing_critical_channels(tmp_path) -> None:
    from ui.method_run_wizard.controller import (
        _default_mapping_suggestions,
        _mapping_payload_with_suggestions,
    )

    mapping_summary = {
        "blocking_fields": ["channel.front_strain", "channel.rear_strain"],
        "candidate_report": {
            "requirements": [
                {
                    "method_field": "channel.front_strain",
                    "source_role": "front_strain",
                    "severity": "execution_critical",
                    "candidates": [
                        {
                            "source_kind": "channel",
                            "source_name": "Uniaxial Gage 1 on S1-Ch2 microstrain",
                            "confidence": 0.82,
                            "reason": "unit-compatible strain channel; first strain channel default",
                        },
                        {
                            "source_kind": "channel",
                            "source_name": "Uniaxial Gage 2 on S1-Ch1 microstrain",
                            "confidence": 0.66,
                            "reason": "unit-compatible strain channel",
                        },
                    ],
                },
                {
                    "method_field": "channel.rear_strain",
                    "source_role": "rear_strain",
                    "severity": "execution_critical",
                    "candidates": [
                        {
                            "source_kind": "channel",
                            "source_name": "Uniaxial Gage 2 on S1-Ch1 microstrain",
                            "confidence": 0.82,
                            "reason": "unit-compatible strain channel; second strain channel default",
                        },
                        {
                            "source_kind": "channel",
                            "source_name": "Uniaxial Gage 1 on S1-Ch2 microstrain",
                            "confidence": 0.66,
                            "reason": "unit-compatible strain channel",
                        },
                    ],
                },
            ],
        },
    }

    suggestions = _default_mapping_suggestions(mapping_summary)
    assert [row["source_role"] for row in suggestions] == ["front_strain", "rear_strain"]
    assert [row["source_name"] for row in suggestions] == [
        "Uniaxial Gage 1 on S1-Ch2 microstrain",
        "Uniaxial Gage 2 on S1-Ch1 microstrain",
    ]

    repaired = _mapping_payload_with_suggestions(
        {
            "mapping_id": "iso14126_manual",
            "method_id": "iso14126_2023",
            "channels": {"front_strain": "Front Strain", "rear_strain": "Rear Strain"},
            "fields": {"width": "Width"},
            "validation": {},
        },
        suggestions,
    )

    assert repaired["mapping_id"] == "iso14126_manual_wizard_edit"
    assert repaired["channels"]["front_strain"] == "Uniaxial Gage 1 on S1-Ch2 microstrain"
    assert repaired["channels"]["rear_strain"] == "Uniaxial Gage 2 on S1-Ch1 microstrain"
    assert repaired["fields"]["width"] == "Width"


def test_mapping_prompt_does_not_offer_ambiguous_unit_only_defaults() -> None:
    from ui.method_run_wizard.controller import _default_mapping_suggestions

    mapping_summary = {
        "blocking_fields": ["specimen.width_mm"],
        "candidate_report": {
            "requirements": [
                {
                    "method_field": "specimen.width_mm",
                    "source_role": "width",
                    "severity": "execution_critical",
                    "candidates": [
                        {"source_kind": "field", "source_name": "Dimension A", "confidence": 0.62},
                        {"source_kind": "field", "source_name": "Dimension B", "confidence": 0.62},
                    ],
                }
            ],
        },
    }

    assert _default_mapping_suggestions(mapping_summary) == []


def test_mapping_attention_prompt_blocks_readiness_skip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.json",
        mapping_summary={
            "critical_missing_count": 1,
            "blocking_fields": ["channel.front_strain"],
            "candidate_report": {"requirements": []},
        },
    )
    window = MethodRunWindow(package_path=state.input_package_path)
    controller = MethodRunController(window, state)

    added_buttons: list[str] = []

    class FakeMessageBox:
        class Icon:
            Warning = object()

        class ButtonRole:
            ActionRole = object()
            AcceptRole = object()
            RejectRole = object()

        def __init__(self, parent=None) -> None:
            self._clicked = None

        def setIcon(self, icon) -> None:
            pass

        def setWindowTitle(self, title) -> None:
            pass

        def setText(self, text) -> None:
            pass

        def setInformativeText(self, text) -> None:
            self.informative_text = text

        def addButton(self, text, role):
            added_buttons.append(text)
            button = object()
            if text == "Cancel":
                self._clicked = button
            return button

        def exec(self) -> None:
            pass

        def clickedButton(self):
            return self._clicked

    monkeypatch.setattr(QtWidgets, "QMessageBox", FakeMessageBox)

    assert controller._mapping_resolution_choice(["missing critical inputs: channel.front_strain"]) == "cancel"
    assert "Continue to readiness" not in added_buttons
    assert "Open edit mapping" in added_buttons

    window.close()
    app.quit()


def test_method_run_colors_and_font_tokens_meet_prompt13_floor() -> None:
    from ui.method_run_wizard._tokens import Color, Font

    assert Font.BODY_SMALL >= 9
    assert Font.CAPS >= 9

    pairs = (
        (Color.TEXT, Color.SURFACE),
        (Color.TEXT_2, Color.SURFACE),
        (Color.WARN_INK, Color.WARN_BG),
        (Color.OK_INK, Color.OK_BG),
        (Color.ERR_INK, Color.ERR_BG),
        (Color.INFO_INK, Color.INFO_BG),
        (Color.LOG_FG, Color.LOG_BG),
    )
    for foreground, background in pairs:
        assert _contrast_ratio(foreground, background) >= 4.5

    root = Path("src/ui/method_run_wizard")
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.name in {"_tokens.py", "_qss.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"#[0-9a-fA-F]{6}\b", text):
            offenders.append(f"{path}:{match.group(0)}")
    assert offenders == []


def _contrast_ratio(foreground: str, background: str) -> float:
    fg = _relative_luminance(foreground)
    bg = _relative_luminance(background)
    lighter = max(fg, bg)
    darker = min(fg, bg)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(value: str) -> float:
    raw = value.lstrip("#")
    channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
