from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.layouts import MTDAAlignedLayout, metadata_member, report_member

INPUT = ROOT / "datasets" / "Compression" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def canonical_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from methods.core.method_run_service import MethodRunRequest, MethodRunService

    output = tmp_path_factory.mktemp("stage25_completion_ui") / "canonical.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    assert output.exists()
    return output


def test_report_completion_dialog_applies_report_only_amendment_without_mutating_mtdp(
    monkeypatch: pytest.MonkeyPatch,
    canonical_mtda: Path,
    tmp_path: Path,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.report_completion_dialog import ReportCompletionDialog

    before_checksum = _sha256(INPUT)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = ReportCompletionDialog(canonical_mtda)
    _select_field(dialog, "loading_method")

    selected = dialog.selected_field()
    assert selected is not None
    assert selected["missing_reason"] == "Not recorded in source package."
    assert "external_or_not_recorded" not in dialog.selected_label.text()

    output = tmp_path / "amended_finalized.mtda"
    dialog.value_edit.setText("Compression between calibrated platens")
    dialog.reason_edit.setText("RC report metadata completion")
    dialog.reviewer_edit.setText("operator")
    dialog.output_edit.setText(str(output))

    result_path = dialog.apply_amendment(show_messages=False)

    assert result_path == output
    assert output.exists()
    assert _sha256(INPUT) == before_checksum
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {name.split("/", 1)[0] for name in names if not name.endswith("/")} <= {"index.html", "dataset", "metadata"}
        assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
        assert metadata_member("finalization/archive_state.json") in names
        assert report_member("test_report.html") in names
        report = json.loads(archive.read(report_member("test_report.json")))
        completion = report["report_completion_status"]
        archive_state = json.loads(archive.read(metadata_member("finalization/archive_state.json")))
        values = report["report_values_used"]
        ledger = report["report_override_ledger"]
        html = archive.read(report_member("test_report.html")).decode("utf-8")

    loading_method = next(row for row in values if row.get("field_key") == "loading_method")
    assert completion["required_missing_count"] == 2
    assert completion["recommended_missing_count"] == (
        completion["missing_field_count"] - completion["required_missing_count"]
    )
    assert completion["recommended_missing_count"] >= 1
    assert archive_state["archive_state"] == "finalized"
    assert loading_method["value"] == "Compression between calibrated platens"
    assert loading_method["source_type"] == "report_override"
    assert ledger["records"][0]["source_surface"] == "method_run_wizard.report_completion_editor"
    assert "Compression between calibrated platens" in html

    dialog.close()
    assert app is not None


def test_finalization_dialog_blocks_when_required_failure_observations_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    canonical_mtda: Path,
    tmp_path: Path,
) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("MTDP_QT_API", "PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from mtdp_enrichment.ui.qt_compat import QtWidgets
    from ui.method_run_wizard.report_completion_dialog import FinalizationDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = FinalizationDialog(canonical_mtda)
    output = tmp_path / "finalized.mtda"
    dialog.reason_edit.setText("Final RC review")
    dialog.reviewer_edit.setText("operator")
    dialog.output_edit.setText(str(output))

    result_path = dialog.finalize(show_messages=False)

    assert result_path is None
    assert not output.exists()

    dialog.close()
    assert app is not None


def _select_field(dialog: Any, field_key: str) -> None:
    for row_index, row in enumerate(dialog._visible_fields):
        if row.get("field_key") == field_key:
            dialog.fields_table.selectRow(row_index)
            return
    raise AssertionError(f"Field {field_key!r} was not visible in report completion dialog.")

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
