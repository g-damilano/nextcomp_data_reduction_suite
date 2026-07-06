from __future__ import annotations


def test_setup_spotlight_tasks_and_signals(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QT_API, QtCore, QtWidgets
    from ui.method_run_wizard.components.task_card import TaskCard
    from ui.method_run_wizard.spotlights.setup_spotlight import SetupSpotlight

    if QT_API == "PySide6":
        from PySide6 import QtTest
    else:
        from PyQt6 import QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    spotlight = SetupSpotlight()
    spotlight.show()
    app.processEvents()

    tasks = spotlight.findChildren(TaskCard)
    assert len(tasks) == 2
    assert spotlight.mapping_task in tasks
    assert spotlight.metadata_task in tasks

    spotlight.show_decisions(
        mapping_gap_count=1,
        metadata_gap_count=1,
        bound_count=1,
        bound_examples=["channel.load → load_N"],
        missing_rows=[("Operator", "A. Engineer")],
    )

    events: list[str] = []
    spotlight.save_bindings.connect(lambda: events.append("save"))
    QtTest.QTest.mouseClick(spotlight.save_bindings_button, QtCore.Qt.MouseButton.LeftButton)
    assert events == ["save"]

    spotlight.set_mapping_resolved(True)
    assert spotlight.mapping_task.isHidden()
    assert not spotlight.metadata_task.isHidden()

    spotlight.set_metadata_resolved(True)
    assert spotlight.metadata_task.isHidden()
    assert spotlight.empty_state.isVisible()

    spotlight.close()
    app.processEvents()


def test_setup_spotlight_input_summary_updates(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.spotlights.setup_spotlight import SetupSpotlight

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    spotlight = SetupSpotlight()

    spotlight.set_input_summary(
        package_value="sample.mtdp",
        package_sub="7 run(s) · mechanical.compression",
        package_state="ok",
        method_value="ISO 14126 Compression",
        method_sub="v0.1.0 · ISO 14126",
        method_state="ok",
        mapping_value="iso14126_manual.json",
        mapping_sub="6/6 critical inputs bound · 7 report gap(s)",
        mapping_state="warn",
        method_enabled=True,
        mapping_enabled=True,
    )

    assert spotlight.package_value.text() == "sample.mtdp"
    assert spotlight.package_tile.property("state") == "ok"
    assert spotlight.method_value.text() == "ISO 14126 Compression"
    assert spotlight.mapping_sub.text() == "6/6 critical inputs bound · 7 report gap(s)"
    assert spotlight.mapping_tile.property("state") == "warn"
    assert spotlight.method_button.isEnabled()
    assert spotlight.mapping_button.isEnabled()

    spotlight.close()
    app.processEvents()
