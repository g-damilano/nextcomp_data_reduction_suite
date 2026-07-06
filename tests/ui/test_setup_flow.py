from __future__ import annotations

from pathlib import Path


def test_setup_action_bar_requires_real_inputs_before_readiness(tmp_path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MethodRunWindow()
    controller = MethodRunController(window)
    action = window.action_bars[WizardScenario.SETUP]

    assert action._label.text() == "Choose package"
    assert action._sub.text() == "select an MTDP package before choosing method or mapping"
    assert action._primary.text() == "Choose package"
    assert action._primary.isEnabled()
    assert window.setup_spotlight.metadata_task.isHidden()
    assert window.setup_spotlight.method_row.isHidden()
    assert window.setup_spotlight.method_combo.count() >= 1
    assert controller.state.method_path is None
    assert controller.state.mapping_path is None
    assert window.setup_spotlight.package_value.text() == "No package selected"
    assert window.setup_spotlight.package_tile.property("state") == "now"
    assert window.setup_spotlight.method_tile.property("state") == "todo"
    assert not window.setup_spotlight.method_button.isEnabled()
    assert not window.setup_spotlight.mapping_button.isEnabled()
    assert window.decor_top.pipeline._pills["package"].property("state") == "now"
    assert window.decor_top.pipeline._pills["mapping"].property("state") == "todo"

    window.close()

    state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.yaml",
        readiness_report={
            "status": "READY_WITH_WARNINGS",
            "run_count": 3,
            "missing_report_field_count": 2,
            "recommended_missing_count": 1,
            "bound_count": 4,
            "bound_examples": ["channel.load → load_N"],
            "missing_report_fields": [
                {"field": "Operator", "example": "A. Engineer"},
                {"field": "Laboratory", "example": "Composites Lab"},
            ],
        },
    )
    window = MethodRunWindow(package_path=state.input_package_path)
    controller = MethodRunController(window, state)
    action = window.action_bars[WizardScenario.SETUP]

    assert action._label.text() == "Ready · with warnings"
    assert action._sub.text() == "2 unmapped report bindings · 1 recommended field blank"
    assert action._primary.isEnabled()
    assert window.setup_spotlight.package_tile.property("state") == "ok"
    assert window.setup_spotlight.method_tile.property("state") == "ok"
    assert window.setup_spotlight.mapping_tile.property("state") == "ok"
    assert window.setup_spotlight.mapping_value.text() == "iso14126_manual.json"

    window.setup_spotlight.save_bindings.emit()

    assert action._label.text() == "Ready · with warnings"
    assert "2 unmapped report bindings" in action._sub.text()
    assert "1 recommended field blank" in action._sub.text()
    assert controller.state.mapping_decision_made is True
    assert controller.state.activity_log[-1].level == "ok"
    assert window.setup_spotlight.mapping_tile.property("state") == "ok"

    window.setup_spotlight.accept_metadata_warnings.emit()

    assert action._label.text() == "Ready · all decisions resolved"
    assert action._sub.text() == "no warnings — clean run"
    assert controller.state.metadata_decision_made is True

    action._primary.click()
    assert window.spotlight.body.currentIndex() == window._scenario_index[WizardScenario.RUNNING]

    controller.state.readiness_report = {"status": "BLOCKED", "blockers": ["source package missing"]}
    controller.state.scenario = WizardScenario.SETUP
    window.set_scenario(WizardScenario.SETUP)
    controller._update_setup_action_bar()

    assert action._label.text() == "Cannot run · readiness failed"
    assert action._sub.text() == "source package missing"
    assert action._primary.text() == "Check readiness"
    assert action._primary.isEnabled()
    assert window.setup_spotlight.mapping_task._header._title.text() == "Fix readiness blockers"
    assert not window.setup_spotlight.mapping_task.isHidden()
    assert window.setup_spotlight.metadata_task.isHidden()

    window.close()
    app.quit()


def test_setup_spotlight_surfaces_warning_only_readiness(tmp_path) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        input_package_path=tmp_path / "input.mtdp",
        method_path=tmp_path / "method.yaml",
        mapping_path=tmp_path / "mapping.yaml",
        readiness_report={
            "status": "READY_WITH_WARNINGS",
            "warnings": ["fixture compliance was inferred"],
        },
    )
    window = MethodRunWindow(package_path=state.input_package_path)
    MethodRunController(window, state)
    action = window.action_bars[WizardScenario.SETUP]

    assert action._label.text() == "Ready · with warnings"
    assert action._sub.text() == "fixture compliance was inferred"
    assert action._primary.text() == "▶ Run method"
    assert action._primary.isEnabled()
    assert window.setup_spotlight.mapping_task._header._title.text() == "Review readiness warnings"
    assert window.setup_spotlight.empty_state.isHidden()

    window.close()
    app.quit()


def test_setup_edit_mapping_opens_mapping_review_dialog(monkeypatch) -> None:
    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.state import WizardScenario
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(input_package_path=Path("selected.mtdp"))
    window = MethodRunWindow(package_path=state.input_package_path)
    controller = MethodRunController(window, state)

    assert not window.setup_spotlight.method_row.isHidden()
    assert controller.state.method_path is None

    window.action_bars[WizardScenario.SETUP].primary_button.click()
    assert controller.state.method_path is not None
    assert controller.state.mapping_path is not None

    captured: dict[str, object] = {}

    class FakeMappingDialog:
        def __init__(self, model, *, current_path, default_path=None, parent=None):
            captured["model"] = model
            captured["current_path"] = current_path
            captured["default_path"] = default_path
            captured["parent"] = parent
            self.selected_mapping_path = current_path

        def exec(self):
            return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr("ui.method_run_wizard.controller.MethodMappingDialog", FakeMappingDialog)

    window.decor_bottom.detail.edit_mapping_button.click()

    assert controller.state.scenario == WizardScenario.SETUP
    assert controller.state.mapping_path is not None
    assert controller.state.mapping_path.name == "iso14126_manual.json"
    assert captured["current_path"].name == "iso14126_manual.json"
    assert captured["default_path"].name == "iso14126_manual.json"
    assert captured["parent"] is window
    assert captured["model"]["schema_name"] == "mapping_preview_view_model"
    assert captured["model"]["rows"]
    assert "iso14126_manual.json" in window.setup_spotlight.mapping_label.text()
    assert controller.state.activity_log[-1].msg == "Mapping: reviewed profile iso14126_manual.json."

    window.close()
    app.quit()
