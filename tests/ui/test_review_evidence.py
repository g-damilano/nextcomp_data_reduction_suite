from __future__ import annotations

import json
import zipfile

import pytest


def test_flagged_run_row_toggles_evidence(monkeypatch) -> None:
    window, controller, qt_test, qt_core, app = _review_window(monkeypatch)
    row = window.review_spotlight.rows["run_001"]

    assert row._detail.isHidden()

    qt_test.QTest.mouseClick(row._row, qt_core.Qt.MouseButton.LeftButton)

    assert not row._detail.isHidden()
    assert controller.state.expanded_run == "run_001"

    window.close()
    app.quit()


def test_keep_shows_justify_and_remove_hides(monkeypatch) -> None:
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch)
    row = window.review_spotlight.rows["run_001"]

    row._row.keep_button.click()

    assert controller.state.acceptance_keep["run_001"] is True
    assert not row.justify.isHidden()

    row._row.remove_button.click()

    assert controller.state.acceptance_keep["run_001"] is False
    assert row.justify.isHidden()

    window.close()
    app.quit()


def test_review_builds_rows_from_acceptance_report_flags(monkeypatch) -> None:
    acceptance_report = {
        "summary": {"total_runs": 7, "default_selected_runs": 5, "review_required": 1, "excluded": 1},
        "run_states": {"run_002": "excluded", "run_005": "accepted"},
        "flags": [
            {
                "run_id": "run_002",
                "severity": "exclude",
                "category": "user_validity",
                "message": "Operator marked this run invalid.",
                "selection_effect": "excluded_from_default",
                "evidence_refs": ["acceptance/run_flags.csv"],
            },
            {
                "run_id": "run_005",
                "severity": "warning",
                "category": "informational",
                "message": "Included with a note.",
                "selection_effect": "included_with_warning",
            },
        ],
    }
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch, acceptance_report=acceptance_report)

    assert set(window.review_spotlight.rows) == {"run_002"}
    assert controller.state.acceptance_keep["run_002"] is False
    assert window.review_spotlight.total_value.text() == "7"
    assert window.review_spotlight.flagged_value.text() == "1"
    assert window.review_spotlight.final_value.text() == "5"
    assert "Operator marked" in window.review_spotlight.rows["run_002"]._row._reason.text()
    assert controller._review_models[0].has_bending_evidence is False
    assert controller._review_models[0].bending_peak is None

    window.review_spotlight.rows["run_002"]._row.keep_button.click()

    assert window.review_spotlight.override_value.text() == "1"
    assert window.review_spotlight.override_sub.text() == "missing reasons"

    window.close()
    app.quit()


def test_review_clusters_multiple_acceptance_flags_per_run(monkeypatch) -> None:
    acceptance_report = {
        "summary": {"total_runs": 3, "default_selected_runs": 1, "review_required": 1},
        "run_states": {"run_002": "review_required"},
        "flags": [
            {
                "flag_id": "bending:run_002",
                "run_id": "run_002",
                "severity": "review",
                "category": "bending",
                "message": "Bending diagnostic indicates sustained bending above the persistence threshold.",
                "selection_effect": "requires_review_excluded_from_default",
            },
            {
                "flag_id": "curve_shape:run_002",
                "run_id": "run_002",
                "severity": "review",
                "category": "curve_shape",
                "message": "Curve-shape diagnostic identified a cohort-shape outlier.",
                "selection_effect": "requires_review_excluded_from_default",
            },
        ],
    }

    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch, acceptance_report=acceptance_report)
    row = window.review_spotlight.rows["run_002"]

    assert set(window.review_spotlight.rows) == {"run_002"}
    assert controller.state.acceptance_keep["run_002"] is False
    assert "(+1 more)" in row._row._reason.text()
    assert len(controller._review_models[0].acceptance_flags) == 2
    assert controller._review_models[0].diagnostic_cockpit is not None
    assert controller._review_models[0].diagnostic_cockpit.view_id == "iso14126_bending_wizard_acceptance"
    assert controller._review_models[0].defect_labels == ["Bending", "Curve shape"]
    assert row._row._defects.text() == "Bending + Curve shape"
    assert row._row._defects.toolTip() == "Override covers: Bending + Curve shape"
    assert row._row.keep_button.text() == "Keep run"
    assert row._row.remove_button.text() == "Remove run"
    assert [
        cockpit.view_id
        for cockpit in controller._review_models[0].diagnostic_cockpits
    ] == [
        "iso14126_bending_wizard_acceptance",
        "iso14126_curve_family_wizard_acceptance",
    ]

    row.set_expanded(True)
    app.processEvents()

    from mtdp_enrichment.ui.qt_compat import QtWidgets

    tabs = row._detail.findChild(QtWidgets.QTabWidget, "diagnosticCockpitTabs")
    assert tabs is not None
    assert tabs.count() == 2
    assert [tabs.tabText(index) for index in range(tabs.count())] == ["Bending", "Curve shape"]

    flag_lines = [
        label.text()
        for label in row._detail.findChildren(type(window.review_spotlight.total_value))
        if label.objectName() == "acceptanceFlagLine"
    ]
    assert len(flag_lines) == 2
    assert any("Bending diagnostic" in text for text in flag_lines)
    assert any("Curve-shape diagnostic" in text for text in flag_lines)

    row._row.remove_button.click()
    assert row.justify.isHidden()

    row._row.keep_button.click()
    assert not row.justify.isHidden()
    assert row.justify.line_edit.placeholderText() == "Motivate keeping this run despite Bending + Curve shape"
    assert controller.state.acceptance_override_defects["run_002"] == ["Bending", "Curve shape"]

    window.close()
    app.quit()


def test_review_uses_real_mtda_bending_evidence_for_acceptance_flags(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mtda_path = tmp_path / "real_bending.mtda"
    _write_review_evidence_mtda(mtda_path)
    acceptance_report = {
        "summary": {"total_runs": 2, "default_selected_runs": 1, "review_required": 1},
        "run_states": {"run_002": "review_required"},
        "flags": [
            {
                "run_id": "run_002",
                "severity": "review",
                "category": "method_diagnostic",
                "message": "Bending diagnostic indicates sustained bending above the persistence threshold.",
                "selection_effect": "requires_review_excluded_from_default",
                "evidence_refs": ["report/individual_results.csv:run_002"],
            },
        ],
    }
    state = MethodRunWizardState(
        readiness_report={"status": "READY_WITH_WARNINGS"},
        acceptance_summary=acceptance_report,
        output_path=mtda_path,
    )
    window = MethodRunWindow()
    controller = MethodRunController(window, state)
    controller._enter_review()

    model = controller._review_models[0]
    assert model.has_bending_evidence is True
    assert abs((model.bending_peak or 0) - 15.472360309204419) < 1e-9
    assert model.bending_threshold == 10.0
    assert model.bending_points_above_threshold == 138
    assert model.bending_assessed_points == 138
    assert abs((model.peak_load_N or 0) - 3848.7) < 1e-9
    assert abs((model.modulus_GPa or 0) - 53.5926037519374) < 1e-9
    assert model.bending_series[-1] == model.bending_peak
    assert "Bending threshold exceedance persists" in model.narrative_html
    assert model.diagnostic_cockpit is not None
    assert model.diagnostic_cockpit.view_id == "iso14126_bending_wizard_acceptance"
    card_keys = {card.evidence_key for card in model.diagnostic_cockpit.cards}
    assert {
        "bending.max_percent",
        "bending.threshold_percent",
        "bending.points_above_threshold",
        "bending.fraction_above_threshold",
        "bending.longest_exceedance_segment",
        "bending.classification",
        "selection.consequence_summary",
    } <= card_keys

    window.close()
    app.quit()


def test_review_missing_diagnostic_view_placeholder_has_room(monkeypatch) -> None:
    acceptance_report = {
        "summary": {"total_runs": 1, "default_selected_runs": 0, "review_required": 1},
        "run_states": {"run_009": "review_required"},
        "flags": [
            {
                "run_id": "run_009",
                "severity": "review",
                "category": "method_diagnostic",
                "message": "Review flag without archive-backed bending evidence.",
                "selection_effect": "requires_review_excluded_from_default",
            },
        ],
    }
    window, _controller, _qt_test, _qt_core, app = _review_window(
        monkeypatch,
        acceptance_report=acceptance_report,
    )
    row = window.review_spotlight.rows["run_009"]
    row.set_expanded(True)
    app.processEvents()

    placeholders = [
        label
        for label in row._detail.findChildren(type(window.review_spotlight.total_value))
        if label.text().startswith("Evidence gap:")
    ]

    assert placeholders
    assert placeholders[0].minimumHeight() >= 86
    assert row._detail.minimumHeight() >= 126
    assert row._detail.sizeHint().height() >= 110

    window.close()
    app.quit()


def test_bending_cockpit_cards_are_specific_and_do_not_use_silent_na(monkeypatch) -> None:
    acceptance_report = {
        "total_runs": 2,
        "final_report_count": 1,
        "flagged_runs": [
            {
                "run_id": "run_001",
                "default_call": "Remove",
                "reason": "bending ratio persisted above threshold",
                "bending_series": [0.0, 4.2, 11.4, 15.1],
                "bending_peak": 15.1,
                "bending_threshold": 10.0,
                "bending_points_above_threshold": 2,
                "bending_assessed_points": 4,
                "bending_fraction_above_threshold": 0.5,
                "bending_longest_segment_points": 2,
                "bending_longest_segment_fraction": 0.5,
                "bending_longest_segment_classification": "sustained_region",
                "bending_classification": "FAIL_SUSTAINED_BENDING",
                "narrative_html": "Bending threshold exceedance persists.",
            }
        ],
    }
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch, acceptance_report=acceptance_report)
    row = window.review_spotlight.rows["run_001"]
    row.set_expanded(True)
    app.processEvents()

    cockpit = controller._review_models[0].diagnostic_cockpit
    assert cockpit is not None
    assert cockpit.view_id == "iso14126_bending_wizard_acceptance"
    assert cockpit.evidence_packet.missing_required_keys == ()
    labels = [
        label.text()
        for label in row._detail.findChildren(type(window.review_spotlight.total_value))
        if label.objectName() in {"metricKey", "metricValue", "metricSub"}
    ]
    assert "BENDING CALL" in labels
    assert "PEAK IMBALANCE" in labels
    assert "REVIEW LIMIT" in labels
    assert "PERSISTENCE" in labels
    assert "WINDOW SHARE" in labels
    assert "LONGEST SEGMENT" in labels
    assert "SCIENTIST ACTION" in labels
    assert "15.1%" in labels
    assert "50%" in labels
    assert "2 of 4 assessed points above limit" in labels
    assert "2 points (50% of window) - sustained region" in labels
    assert "Evidence unavailable" not in labels
    assert all(text.lower() != "n/a" for text in labels)

    window.close()
    app.quit()


def test_no_exceedance_bending_cockpit_reports_absence_as_evidence() -> None:
    from ui.method_run_wizard.view_models.diagnostic_cockpit import diagnostic_cockpit_from_payload

    cockpit = diagnostic_cockpit_from_payload(
        {
            "run_id": "run_006",
            "default_call": "Keep",
            "bending_series": [2.0, 4.5, 6.57],
            "bending_peak": 6.57,
            "bending_threshold": 10.0,
            "bending_points_above_threshold": 0,
            "bending_assessed_points": 100,
            "bending_fraction_above_threshold": 0,
            "bending_classification": "PASS",
        }
    )

    cards = {card.evidence_key: card for card in cockpit.cards}
    assert cockpit.evidence_packet.missing_required_keys == ()
    assert cards["bending.fraction_above_threshold"].value == "0%"
    assert cards["bending.fraction_above_threshold"].subtext == "0 of 100 assessed points above limit"
    assert cards["bending.longest_exceedance_segment"].state == "ok"
    assert cards["bending.longest_exceedance_segment"].value == "0 points - no contiguous exceedance"


def test_curve_family_cockpit_surfaces_scientist_assessment_cards() -> None:
    from ui.method_run_wizard.view_models.diagnostic_cockpit import diagnostic_cockpit_from_payload

    cockpit = diagnostic_cockpit_from_payload(
        {
            "run_id": "run_005",
            "evidence_kind": "curve_family",
            "default_call": "Remove",
            "curve_family_metric": "distance_rms",
            "curve_family_value": 1.5522407044943216,
            "curve_family_rank": 2,
            "curve_family_classification": "CURVE_SHAPE_OUTLIER",
            "curve_family_reason": "RMS standardized residual distance.",
            "curve_family_masking_risk": True,
            "curve_family_robust_z": 165.09117288950543,
            "curve_family_robust_threshold": 3.5,
            "curve_family_dixon_decision": "no_outlier",
            "curve_family_outlier_limit": 0.534,
            "curve_family_points": [
                {"run_id": "run_005", "x": 10.0, "stress": 100.0},
                {"run_id": "run_006", "x": 10.0, "stress": 98.0},
            ],
        }
    )

    cards = {card.label: card for card in cockpit.cards}
    assert cockpit.evidence_packet.missing_required_keys == ()
    assert cards["Scientific call"].value == "CURVE SHAPE OUTLIER"
    assert cards["Primary metric"].value == "distance rms 1.55"
    assert cards["Primary metric"].subtext == "RMS standardized residual distance."
    assert cards["Distance rank"].value == "2"
    assert cards["Robust screen"].value == "z 165 vs 3.5; masking yes"
    assert cards["Outlier test"].value == "no outlier; limit 0.534"
    assert cards["Scientist action"].value == "Excluded from final report unless kept with justification"


def test_aligned_mtda_evidence_feeds_scientist_cockpit(stage26_canonical_mtda) -> None:
    from ui.method_run_wizard import controller as controller_module

    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        method_outputs = json.loads(archive.read("metadata/software/method_outputs.json"))
        acceptance_report = method_outputs["acceptance_report"]
    evidence = controller_module._review_evidence_from_mtda(stage26_canonical_mtda)

    bending = evidence["run_005"]
    assert bending["bending_trace_points"]
    assert bending["bending_exceedance_segments"]
    assert bending["bending_longest_segment_points"] is not None
    assert bending["bending_longest_segment_fraction"] is not None
    assert bending["bending_longest_segment_classification"]

    curve_shape = evidence["run_002"]
    assert curve_shape["curve_family_metric"] == "distance_rms"
    assert curve_shape["curve_family_value"] is not None
    assert curve_shape["curve_family_rank"]
    assert curve_shape["curve_family_robust_z"] is not None
    assert curve_shape["curve_family_robust_threshold"] == pytest.approx(3.5)
    assert curve_shape["curve_family_dixon_decision"] == "no_outlier"
    assert curve_shape["curve_family_outlier_limit"] == pytest.approx(0.568)
    assert curve_shape["curve_family_points"]

    models = controller_module._row_models_from_acceptance_report(
        acceptance_report,
        evidence_by_run=evidence,
    )
    model = next(
        item
        for item in models
        if any(cockpit.view_id == "iso14126_curve_family_wizard_acceptance" for cockpit in item.diagnostic_cockpits)
    )
    cockpit = model.diagnostic_cockpit
    assert cockpit is not None
    assert "iso14126_curve_family_wizard_acceptance" in {item.view_id for item in model.diagnostic_cockpits}
    curve_cockpit = next(item for item in model.diagnostic_cockpits if item.view_id == "iso14126_curve_family_wizard_acceptance")
    cards = {card.label: card for card in curve_cockpit.cards}
    assert cards["Scientific call"].value
    assert cards["Primary metric"].value.startswith("distance rms ")
    assert " vs 3.5" in cards["Robust screen"].value
    assert cards["Outlier test"].value == "no outlier; limit 0.568"


def test_missing_required_bending_evidence_renders_explicit_gap(monkeypatch) -> None:
    acceptance_report = {
        "total_runs": 1,
        "final_report_count": 0,
        "flagged_runs": [
            {
                "run_id": "run_010",
                "default_call": "Remove",
                "reason": "bending ratio persisted above threshold",
                "bending_series": [0.0, 14.0],
                "bending_peak": 14.0,
                "bending_threshold": 10.0,
                "narrative_html": "Bending threshold exceedance persists.",
            }
        ],
    }
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch, acceptance_report=acceptance_report)
    row = window.review_spotlight.rows["run_010"]
    row.set_expanded(True)
    app.processEvents()

    cockpit = controller._review_models[0].diagnostic_cockpit
    assert cockpit is not None
    assert "bending.points_above_threshold" in cockpit.evidence_packet.missing_required_keys
    labels = [
        label.text()
        for label in row._detail.findChildren(type(window.review_spotlight.total_value))
        if label.objectName() in {"metricValue", "metricSub"}
    ]
    assert "Evidence unavailable" in labels
    assert "Missing required evidence: bending.points_above_threshold" in labels
    assert all(text.lower() != "n/a" for text in labels)

    window.close()
    app.quit()


def test_compact_bending_plot_contract_preserves_decision_layers(monkeypatch) -> None:
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch)
    cockpit = controller._review_models[0].diagnostic_cockpit

    assert cockpit is not None
    plot = cockpit.plot_contract
    assert plot.plot_kind == "bending_evidence"
    assert plot.x_axis_label == "Load / N"
    assert plot.y_axis_label == "Bending / %"
    assert {
        "bending_percent_series",
        "threshold_line",
        "assessment_window_10_90_fmax",
        "exceedance_points",
        "exceedance_segments",
    } <= set(plot.required_layers)
    assert plot.layout_policy["prevent_axis_label_clipping"] is True
    assert plot.layout_policy["left_axis_margin_px"] >= 44
    assert plot.layout_policy["bottom_axis_margin_px"] >= 34

    window.close()
    app.quit()


def test_review_stress_expanded_flagged_run_reflows_without_overlap(monkeypatch) -> None:
    flags = []
    for index in range(1, 11):
        reason = (
            "Bending diagnostic indicates sustained bending above the persistence threshold."
            if index not in {4, 9}
            else f"derivative_rmse {4.77061 if index == 4 else 165.989} > 2.5"
        )
        flags.append(
            {
                "run_id": f"run_{index:03d}",
                "default_call": "Remove",
                "reason": reason,
                "bending_series": [0.0, 1.5, 4.2, 7.7, 12.2, 15.1, 10.5],
                "bending_peak": 15.1,
                "bending_threshold": 10.0,
                "bending_points_above_threshold": 60,
                "bending_assessed_points": 120,
                "peak_load_N": 4000,
                "kept_mean_load": 4100,
                "modulus_GPa": 48,
                "kept_mean_modulus": 50,
                "failure_mode": "angled fracture",
                "narrative_html": "Bending threshold exceedance persists over a sustained portion of the load window.",
            }
        )
    acceptance_report = {"total_runs": 10, "final_report_count": 0, "flagged_runs": flags}
    window, _controller, _qt_test, _qt_core, app = _review_window(
        monkeypatch,
        acceptance_report=acceptance_report,
    )
    window.resize(1080, 620)
    app.processEvents()

    row = window.review_spotlight.rows["run_002"]
    next_row = window.review_spotlight.rows["run_003"]
    row.set_expanded(True)
    app.processEvents()
    app.processEvents()

    assert not row._detail.isHidden()
    assert row._detail.geometry().bottom() <= row.rect().bottom()
    assert row.geometry().bottom() < next_row.geometry().top()
    assert window.scroll_area.verticalScrollBar().maximum() > 0

    window.close()
    app.quit()


def test_confirm_keep_without_reason_stays_in_review_and_focuses_input(monkeypatch) -> None:
    window, _controller, _qt_test, _qt_core, app = _review_window(monkeypatch)
    from ui.method_run_wizard.state import WizardScenario

    row = window.review_spotlight.rows["run_001"]
    row._row.keep_button.click()
    window.action_bars[WizardScenario.REVIEW]._primary.click()
    app.processEvents()

    assert window.spotlight.body.currentIndex() == window._scenario_index[WizardScenario.REVIEW]
    assert row.justify.line_edit.hasFocus()

    window.close()
    app.quit()


def test_confirm_with_reasons_transitions_to_finalize(monkeypatch) -> None:
    window, _controller, _qt_test, _qt_core, app = _review_window(monkeypatch)
    from ui.method_run_wizard import controller as controller_module
    from ui.method_run_wizard.state import WizardScenario

    persisted = []
    monkeypatch.setattr(
        controller_module.service_adapter,
        "persist_acceptance",
        lambda state: persisted.append(dict(state.acceptance_override_reason)),
    )

    row = window.review_spotlight.rows["run_001"]
    row._row.keep_button.click()
    row.justify.line_edit.setText("Fixture slip explains the bending diagnostic.")
    window.action_bars[WizardScenario.REVIEW]._primary.click()
    app.processEvents()

    assert persisted == [{"run_001": "Fixture slip explains the bending diagnostic."}]
    assert window.spotlight.body.currentIndex() == window._scenario_index[WizardScenario.FINALIZE]

    window.close()
    app.quit()


def test_acceptance_persistence_records_override_defect_scope(monkeypatch) -> None:
    acceptance_report = {
        "summary": {"total_runs": 3, "default_selected_runs": 1, "review_required": 1},
        "run_states": {"run_002": "review_required"},
        "flags": [
            {
                "flag_id": "bending:run_002",
                "run_id": "run_002",
                "severity": "review",
                "category": "bending",
                "message": "Bending diagnostic indicates sustained bending above the persistence threshold.",
                "selection_effect": "requires_review_excluded_from_default",
            },
            {
                "flag_id": "curve_shape:run_002",
                "run_id": "run_002",
                "severity": "review",
                "category": "curve_shape",
                "message": "Curve-shape diagnostic identified a cohort-shape outlier.",
                "selection_effect": "requires_review_excluded_from_default",
            },
        ],
    }
    window, controller, _qt_test, _qt_core, app = _review_window(monkeypatch, acceptance_report=acceptance_report)

    row = window.review_spotlight.rows["run_002"]
    row._row.keep_button.click()
    row.justify.line_edit.setText("Scientist accepts both bending and curve-shape findings.")

    from ui.method_run_wizard import service_adapter

    payload = service_adapter.persist_acceptance(controller.state)

    assert payload["acceptance_override_defects"] == {"run_002": ["Bending", "Curve shape"]}
    assert payload["acceptance_override_records"] == [
        {
            "run_id": "run_002",
            "final_included": True,
            "reason": "Scientist accepts both bending and curve-shape findings.",
            "defects": ["Bending", "Curve shape"],
        }
    ]

    window.close()
    app.quit()


def _write_review_evidence_mtda(path) -> None:
    individual_results = (
        "run_id,max_load_N,compressive_modulus_MPa,bending_max_percent,bending_threshold_percent,"
        "bending_points_above_threshold,bending_point_count,bending_pattern,bending_pattern_reason,"
        "failure_mode,final_included,included_in_selection\n"
        "run_002,3848.7,53592.6037519374,15.472360309204419,10,138,138,"
        "FAIL_SUSTAINED_BENDING,Bending threshold exceedance persists over a sustained portion of the load window.,"
        "angled fracture,False,False\n"
        "run_003,4909.11,54732.0641883469,7.60652700974222,10,0,171,"
        "PASS,No bending values exceed the configured threshold in the assessment window.,"
        "valid compression failure,True,True\n"
    )
    bending_distribution = (
        "run_id,threshold_percent,assessed_point_count,min_bending_percent,q1_bending_percent,"
        "median_bending_percent,q3_bending_percent,p95_bending_percent,max_bending_percent,"
        "points_above_threshold\n"
        "run_002,10,138,11.1191405384762,11.4803957052574,11.9325185946098,"
        "13.4618806788625,15.2864209508571,15.472360309204419,138\n"
    )
    reduce_summary = {
        "runs": {
            "run_002": {
                "diagnostics": {
                    "bending_diagnostic": {
                        "max_bending_percent": 15.472360309204419,
                        "threshold_percent": 10.0,
                        "points_above_threshold": 138,
                        "point_count": 138,
                        "pattern_reason": "Bending threshold exceedance persists over a sustained portion of the load window.",
                    }
                },
                "outputs": {
                    "max_load_N": {"value": 3848.7},
                    "compressive_modulus_MPa": {"value": 53592.6037519374},
                },
            }
        }
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("report/individual_results.csv", individual_results)
        archive.writestr("report/bending_distribution_summary.csv", bending_distribution)
        archive.writestr("audit/reduce_summary.json", json.dumps(reduce_summary))


def _review_window(monkeypatch, acceptance_report: dict | None = None):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    acceptance_summary = acceptance_report or {
            "final_report_count": 4,
            "flagged_runs": [
                {
                    "run_id": "run_001",
                    "default_call": "Remove",
                    "reason": "bending ratio persisted above threshold",
                    "bending_series": [0.02, 0.04, 0.08, 0.13, 0.12],
                    "bending_peak": 0.13,
                    "bending_threshold": 0.10,
                    "bending_above_s": 1.9,
                    "persistence_s": 1.0,
                    "peak_load_N": 4300,
                    "kept_mean_load": 4450,
                    "modulus_GPa": 34.1,
                    "kept_mean_modulus": 35.0,
                    "failure_mode": "valid compression failure",
                    "narrative_html": "The run exceeded the bending persistence threshold.",
                },
                {
                    "run_id": "run_002",
                    "default_call": "Remove",
                    "reason": "late bending spike",
                    "bending_series": [0.01, 0.03, 0.05, 0.11, 0.14],
                    "bending_peak": 0.14,
                    "bending_threshold": 0.10,
                    "bending_above_s": 1.4,
                    "persistence_s": 1.0,
                    "peak_load_N": 4210,
                    "kept_mean_load": 4450,
                    "modulus_GPa": 33.6,
                    "kept_mean_modulus": 35.0,
                    "failure_mode": "angled fracture",
                    "narrative_html": "The run shows late-window bending.",
                },
            ],
        }
    state = MethodRunWizardState(
        readiness_report={"status": "READY_WITH_WARNINGS"},
        acceptance_summary=acceptance_summary,
    )
    window = MethodRunWindow()
    controller = MethodRunController(window, state)
    controller._enter_review()
    window.show()
    app.processEvents()
    return window, controller, QtTest, QtCore, app
