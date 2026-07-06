from __future__ import annotations


def test_pipeline_strip_pills_and_state(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.components.decor_top import PipelineStrip

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    strip = PipelineStrip()

    assert isinstance(strip.layout(), QtWidgets.QHBoxLayout)
    assert strip.layout().count() == 8
    for pill in strip._pills.values():
        label = pill._label
        assert label.minimumWidth() >= label.fontMetrics().horizontalAdvance(label.text())
        assert pill.minimumWidth() >= pill.sizeHint().width()
    assert strip.labels() == [
        "Package",
        "Method",
        "Mapping",
        "Ready",
        "Run",
        "Validate",
        "Accept",
        "Output",
    ]
    assert len(strip._pills) == 8

    strip.set_state({"mapping": "warn", "exec": "now", "validate": "ok"})

    assert strip._pills["mapping"].property("state") == "warn"
    assert strip._pills["mapping"]._dot.property("state") == "warn"
    assert strip._pills["exec"].property("state") == "now"
    assert strip._pills["exec"]._pulse_timer.isActive()
    assert strip._pills["validate"].property("state") == "ok"

    strip.close()
    app.quit()
