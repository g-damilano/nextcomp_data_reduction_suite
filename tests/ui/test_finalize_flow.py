from __future__ import annotations

import zipfile
from pathlib import Path


def test_finalize_button_enabled_only_when_note_has_content(monkeypatch) -> None:
    window, _controller, app = _finalize_window(monkeypatch, Path("C:/tmp/example.mtda"))

    button = window.finalize_spotlight.finalize_button
    assert not button.isEnabled()

    window.finalize_spotlight.note_edit.setText("Reviewed with warnings.")
    assert button.isEnabled()

    window.finalize_spotlight.note_edit.clear()
    assert not button.isEnabled()

    window.close()
    app.quit()


def test_copy_mtda_path_puts_path_on_clipboard(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "result.mtda"
    window, _controller, app = _finalize_window(monkeypatch, output_path)

    window.finalize_spotlight.copy_path_button.click()

    assert app.clipboard().text() == str(output_path)

    window.close()
    app.quit()


def test_open_mtda_button_launches_extracted_archive_index(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "result.mtda"
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr("index.html", "<html>archive home</html>")
        archive.writestr("dataset/example.txt", "payload")

    window, _controller, app = _finalize_window(monkeypatch, output_path)

    from mtdp_enrichment.ui.qt_compat import QtGui

    opened: list[Path] = []

    def fake_open_url(url) -> bool:
        opened.append(Path(url.toLocalFile()))
        return True

    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", fake_open_url)

    window.finalize_spotlight.open_mtda_button.click()

    assert len(opened) == 1
    assert opened[0].name == "index.html"
    assert opened[0] != output_path
    assert opened[0].read_text(encoding="utf-8") == "<html>archive home</html>"
    assert (opened[0].parent / "dataset" / "example.txt").read_text(encoding="utf-8") == "payload"

    window.close()
    app.quit()


def test_finalize_handoff_summary_and_path_are_compact(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "result.mtda"
    window, _controller, app = _finalize_window(monkeypatch, output_path)
    finalize = window.finalize_spotlight

    assert finalize.missing_value.text() == "38"
    assert finalize.review_value.text() == "2 / 0"
    assert finalize.path_label.text() == "result.mtda"
    assert finalize.path_edit.text() == str(output_path)
    assert finalize.path_edit.toolTip() == str(output_path)
    assert finalize.open_mtda_button.text() == "Open MTDA"
    assert finalize.copy_path_button.toolTip() == "Copy MTDA path"

    finalize.note_edit.setText("Reviewed with warnings.")
    app.processEvents()
    assert finalize.review_value.text() == "2 / 1"

    window.close()
    app.quit()


def test_open_report_buttons_launch_aligned_mtda_members(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "result.mtda"
    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr("dataset/04_reports/test_report.html", "<html>test report</html>")
        archive.writestr("dataset/04_reports/audit_report.html", "<html>audit report</html>")

    window, _controller, app = _finalize_window(monkeypatch, output_path)

    from mtdp_enrichment.ui.qt_compat import QtGui

    opened: list[Path] = []

    def fake_open_url(url) -> bool:
        opened.append(Path(url.toLocalFile()))
        return True

    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", fake_open_url)

    window.finalize_spotlight.test_report_button.click()
    window.finalize_spotlight.audit_report_button.click()

    assert len(opened) == 2
    assert opened[0].name == "test_report.html"
    assert opened[0].read_text(encoding="utf-8") == "<html>test report</html>"
    assert opened[1].name == "audit_report.html"
    assert opened[1].read_text(encoding="utf-8") == "<html>audit report</html>"

    window.close()
    app.quit()


def test_finalize_layout_stacks_when_narrow(monkeypatch, tmp_path) -> None:
    window, _controller, app = _finalize_window(monkeypatch, tmp_path / "result.mtda")
    finalize = window.finalize_spotlight

    finalize.resize(700, 520)
    finalize._sync_layout_mode()
    assert finalize.grid.getItemPosition(finalize.grid.indexOf(finalize.finalize_panel))[:2] == (1, 0)

    finalize.resize(900, 520)
    finalize._sync_layout_mode()
    assert finalize.grid.getItemPosition(finalize.grid.indexOf(finalize.finalize_panel))[:2] == (0, 1)

    window.close()
    app.quit()


def test_close_action_emits_window_closed(monkeypatch, tmp_path) -> None:
    window, _controller, app = _finalize_window(monkeypatch, tmp_path / "result.mtda")
    from ui.method_run_wizard.state import WizardScenario

    closed = []
    window.closed.connect(lambda: closed.append(True))

    window.action_bars[WizardScenario.FINALIZE]._primary.click()
    app.processEvents()

    assert closed

    app.quit()


def _finalize_window(monkeypatch, output_path: Path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.controller import MethodRunController
    from ui.method_run_wizard.state import MethodRunWizardState
    from ui.method_run_wizard.window import MethodRunWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    state = MethodRunWizardState(
        readiness_report={"status": "READY_WITH_WARNINGS"},
        output_path=output_path,
        service_result={
            "status": "completed",
            "output_path": str(output_path),
            "mtda_path": str(output_path),
            "report_override_count": 2,
            "report_summary": {"recommended_missing_count": 38},
        },
    )
    window = MethodRunWindow()
    controller = MethodRunController(window, state)
    controller._enter_finalize()
    window.show()
    app.processEvents()
    return window, controller, app
