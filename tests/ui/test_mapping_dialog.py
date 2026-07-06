from __future__ import annotations

import json


def _model(*, can_confirm: bool = True) -> dict[str, object]:
    return {
        "schema_name": "mapping_preview_view_model",
        "why_required": "Review mappings before readiness.",
        "summary": {
            "execution_critical_total": 2,
            "execution_critical_mapped": 1,
            "report_fields_total": 3,
            "report_fields_mapped": 2,
            "ambiguous": 1,
        },
        "compatibility_status": "WARNING",
        "action_guidance": {
            "severity": "warn",
            "can_confirm": can_confirm,
            "headline": "Execution-critical mapping is usable; report fields still need attention.",
            "primary_actions": ["Review report field warnings.", "Continue to readiness if report gaps are acceptable."],
            "blocking_fields": [] if can_confirm else ["channel.strain"],
            "warning_fields": ["report.operator"],
            "confirm_tooltip": "Resolve channel.strain before confirming this mapping.",
        },
        "rows": [
            {
                "operator_status": "found",
                "required_or_recommended": "required",
                "severity": "execution_critical",
                "method_field": "channel.load",
                "source_role": "load",
                "mapped_source": "load_N",
                "source_kind": "channel",
                "source_location": "channel:load_N",
                "example_value": "1180",
                "unit": "N",
                "candidate_count": 1,
            },
            {
                "operator_status": "missing",
                "required_or_recommended": "recommended",
                "severity": "report_completeness",
                "method_field": "report.operator",
                "source_role": "operator",
                "mapped_source": "",
                "source_kind": "field",
                "source_location": "",
                "example_value": "",
                "unit": "",
                "candidate_count": 1,
            },
        ],
        "candidate_rows": [
            {
                "method_field": "channel.load",
                "source_role": "load",
                "candidate_source": "load_N",
                "source_name": "load_N",
                "source_kind": "channel",
                "coverage": "all runs",
                "confidence": "high",
                "reason": "role match",
            },
            {
                "method_field": "report.operator",
                "source_role": "operator",
                "candidate_source": "fields.Operator Name",
                "source_name": "Operator Name",
                "source_kind": "field",
                "coverage": "package metadata",
                "confidence": "high",
                "reason": "metadata label match",
            },
        ],
        "disambiguation_rows": [
            {
                "method_field": "channel.strain",
                "mapped_source": "strain_axial",
                "candidate_count": 2,
                "confidence": "medium",
                "status": "ambiguous",
                "message": "two strain-like channels",
            }
        ],
    }


def _missing_strain_model() -> dict[str, object]:
    model = _model(can_confirm=False)
    model["rows"] = [
        {
            "operator_status": "missing",
            "required_or_recommended": "required",
            "severity": "execution_critical",
            "method_field": "channel.front_strain",
            "source_role": "front_strain",
            "mapped_source": "Front Strain",
            "source_kind": "channel",
            "source_location": "channel:Front Strain",
            "example_value": "",
            "unit": "mm/mm",
            "candidate_count": 2,
        }
    ]
    model["candidate_rows"] = [
        {
            "method_field": "channel.front_strain",
            "source_role": "front_strain",
            "candidate_source": "channels.Uniaxial Gage 1 on S1-Ch2 microstrain",
            "source_name": "Uniaxial Gage 1 on S1-Ch2 microstrain",
            "source_kind": "channel",
            "coverage": "10/10 runs",
            "confidence": 0.82,
            "reason": "unit-compatible strain channel; first strain channel default",
        },
        {
            "method_field": "channel.front_strain",
            "source_role": "front_strain",
            "candidate_source": "channels.Uniaxial Gage 2 on S1-Ch1 microstrain",
            "source_name": "Uniaxial Gage 2 on S1-Ch1 microstrain",
            "source_kind": "channel",
            "coverage": "10/10 runs",
            "confidence": 0.66,
            "reason": "unit-compatible strain channel",
        },
    ]
    model["action_guidance"] = {
        "severity": "block",
        "can_confirm": False,
        "headline": "Missing execution-critical mapping: channel.front_strain.",
        "primary_actions": ["Choose a compatible channel candidate."],
        "blocking_fields": ["channel.front_strain"],
        "warning_fields": [],
        "confirm_tooltip": "Confirm is disabled until all execution-critical inputs are mapped.",
    }
    return model


def test_mapping_dialog_renders_mapping_evidence(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mapping_path = tmp_path / "mapping.json"
    default_path = tmp_path / "default.json"

    dialog = MethodMappingDialog(_model(), current_path=mapping_path, default_path=default_path)

    assert dialog.path_edit.text() == str(mapping_path)
    assert dialog.binding_table.rowCount() == 2
    assert dialog.binding_table.item(0, 2).text() == "report.operator"
    assert dialog.candidate_table.rowCount() == 1
    assert "[" in dialog.candidate_table.item(0, 2).text()
    assert dialog.custom_source.count() == 1
    assert dialog.custom_source.itemText(0) == "Operator Name"
    assert "Preview:" in dialog.preview_label.text()
    assert "report binding" in dialog.consequence_label.text()
    assert dialog.all_candidate_table.rowCount() == 2
    assert dialog.resolution_table.rowCount() == 1
    assert dialog.next_actions_list.count() == 2
    assert dialog.issue_table.rowCount() == 1
    assert dialog.accept_button.isEnabled()

    dialog.default_button.click()
    assert dialog.selected_mapping_path == default_path
    assert dialog.path_edit.text() == str(default_path)

    dialog.close()
    app.quit()


def test_mapping_dialog_custom_binding_shows_compatible_source_suggestions(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mapping_path = tmp_path / "manual.json"
    mapping_path.write_text(
        json.dumps(
            {
                "mapping_id": "manual",
                "method_id": "iso14126",
                "version": 1,
                "channels": {"front_strain": "Front Strain"},
                "fields": {},
                "tokens": {},
                "validation": {},
            }
        ),
        encoding="utf-8",
    )

    dialog = MethodMappingDialog(_missing_strain_model(), current_path=mapping_path, default_path=None)

    assert dialog.candidate_table.rowCount() == 2
    assert dialog.custom_kind.currentText() == "channel"
    assert dialog.custom_source.count() == 2
    assert dialog.custom_source.itemText(0) == "Uniaxial Gage 1 on S1-Ch2 microstrain"
    assert dialog.custom_source.itemText(1) == "Uniaxial Gage 2 on S1-Ch1 microstrain"
    assert dialog.custom_source.currentText() == "Uniaxial Gage 1 on S1-Ch2 microstrain"

    dialog.custom_source.setCurrentText("Uniaxial Gage 2 on S1-Ch1 microstrain")

    assert dialog.candidate_table.currentRow() == 1

    dialog.apply_custom_button.click()

    assert dialog.binding_table.item(0, 0).text() == "found"
    assert dialog.binding_table.item(0, 3).text() == "channel:Uniaxial Gage 2 on S1-Ch1 microstrain"

    dialog.close()
    app.quit()


def test_mapping_dialog_repairs_binding_and_saves_profile(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mapping_path = tmp_path / "manual.json"
    mapping_path.write_text(
        json.dumps(
            {
                "mapping_id": "manual",
                "method_id": "iso14126",
                "version": 1,
                "channels": {"load": "load_N"},
                "fields": {},
                "tokens": {},
                "validation": {},
            }
        ),
        encoding="utf-8",
    )

    dialog = MethodMappingDialog(_model(), current_path=mapping_path, default_path=None)

    assert dialog.editor_title.text() == "report.operator"
    assert dialog.candidate_table.rowCount() == 1

    dialog.use_candidate_button.click()

    assert dialog.binding_table.item(1, 0).text() == "found"
    assert dialog.binding_table.item(1, 3).text() == "field:Operator Name"
    assert dialog.accept_button.text() == "Save edits and use profile"

    dialog.accept_button.click()

    assert dialog.selected_mapping_path is not None
    assert dialog.selected_mapping_path != mapping_path
    saved = json.loads(dialog.selected_mapping_path.read_text(encoding="utf-8"))
    assert saved["fields"]["operator"] == "Operator Name"
    assert saved["channels"]["load"] == "load_N"

    dialog.close()
    app.quit()


def test_mapping_dialog_clearing_critical_binding_blocks_save(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mapping_path = tmp_path / "manual.json"
    mapping_path.write_text(
        json.dumps(
            {
                "mapping_id": "manual",
                "method_id": "iso14126",
                "version": 1,
                "channels": {"load": "load_N"},
                "fields": {},
                "tokens": {},
                "validation": {},
            }
        ),
        encoding="utf-8",
    )

    dialog = MethodMappingDialog(_model(), current_path=mapping_path, default_path=None)
    critical_row = next(
        row
        for row in range(dialog.binding_table.rowCount())
        if dialog.binding_table.item(row, 2).text() == "channel.load"
    )
    dialog.binding_table.selectRow(critical_row)
    dialog.clear_binding_button.click()

    assert dialog.binding_table.item(0, 0).text() == "missing"
    assert not dialog.accept_button.isEnabled()
    assert "execution-critical" in dialog.accept_button.toolTip()

    dialog.close()
    app.quit()


def test_mapping_dialog_blocks_current_profile_until_new_profile_selected(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mapping_path = tmp_path / "blocked.json"
    repaired_path = tmp_path / "repaired.json"

    def fake_open_file_name(*args, **kwargs):
        return (str(repaired_path), "Mapping profiles (*.json *.yaml *.yml)")

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", fake_open_file_name)

    dialog = MethodMappingDialog(_model(can_confirm=False), current_path=mapping_path, default_path=mapping_path)

    assert not dialog.accept_button.isEnabled()
    assert "channel.strain" in dialog.accept_button.toolTip()
    assert dialog.issue_table.item(0, 0).text() == "blocker"
    assert dialog.issue_table.item(0, 1).text() == "channel.strain"

    dialog.browse_button.click()

    assert dialog.selected_mapping_path == repaired_path
    assert dialog.accept_button.isEnabled()

    dialog.close()
    app.quit()


def test_mapping_dialog_browse_selects_profile(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.mapping_dialog import MethodMappingDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    chosen = tmp_path / "chosen.yaml"

    def fake_open_file_name(*args, **kwargs):
        return (str(chosen), "Mapping profiles (*.json *.yaml *.yml)")

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", fake_open_file_name)

    dialog = MethodMappingDialog(_model(), current_path=None, default_path=None)

    assert not dialog.accept_button.isEnabled()
    dialog.browse_button.click()

    assert dialog.selected_mapping_path == chosen
    assert dialog.path_edit.text() == str(chosen)
    assert dialog.accept_button.isEnabled()

    dialog.close()
    app.quit()
