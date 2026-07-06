from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export import ExportRequest, ExportService
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from ui.method_run_wizard.view_models.output_review import output_review_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
CLI = ROOT / "tools" / "export_mtda.py"


@pytest.fixture(scope="module")
def canonical_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage22_export") / "canonical.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
        )
    )
    assert result.status == "completed"
    return output


def test_full_html_export_from_canonical_mtda_does_not_mutate_inputs(canonical_mtda: Path, tmp_path: Path) -> None:
    before_mtda = _sha256(canonical_mtda)
    before_mtdp = _sha256(INPUT)
    output = tmp_path / "full_export"

    result = ExportService().export(ExportRequest(canonical_mtda, output, "full_html"))
    manifest = json.loads((output / "export_manifest.json").read_text(encoding="utf-8"))

    assert result.status == "exported"
    assert _sha256(canonical_mtda) == before_mtda
    assert _sha256(INPUT) == before_mtdp
    assert (output / "reports" / "test_report.html").exists()
    assert (output / "reports" / "audit_report.html").exists()
    assert not (output / "workbench" / "index.html").exists()
    assert (output / "tables" / "final_report_runs.csv").exists()
    assert (output / "figures" / "aggregate_stress_strain.html").exists()
    assert (output / "figures" / "aggregate_stress_strain_vega.json").exists()
    assert (output / "export_provenance.json").exists()
    assert (output / "export_checksums.json").exists()
    with zipfile.ZipFile(canonical_mtda) as archive:
        names = set(archive.namelist())
    assert {name.split("/", 1)[0] for name in names} <= {"index.html", "dataset", "metadata"}
    assert "metadata/software/method_outputs.json" in names
    assert manifest["source_mtda"]["checksum"] == before_mtda
    assert manifest["source_mtdp"]["checksum"] == _source_mtdp_checksum(canonical_mtda)
    assert manifest["selection"]["selection_set"] == "final_report_runs"
    assert manifest["selection"]["selected_run_count"] == 3
    assert manifest["mtdp_mutated"] is False
    assert manifest["mtda_mutated"] is False
    assert "pdf" in manifest["deferred_formats"]
    assert any("PDF/DOCX" in warning for warning in manifest["warnings"])
    assert "vegaEmbed" in (output / "figures" / "aggregate_stress_strain.html").read_text(encoding="utf-8")


def test_export_cli_writes_figures_profile(canonical_mtda: Path, tmp_path: Path) -> None:
    output = tmp_path / "cli_export"
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input",
            str(canonical_mtda),
            "--output",
            str(output),
            "--profile",
            "figures",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Exported" in completed.stdout
    assert (output / "reports" / "test_report.html").exists()
    assert (output / "figures" / "aggregate_stress_strain.html").exists()
    assert not (output / "reports" / "audit_report.html").exists()


def test_output_review_model_exposes_production_export_action(canonical_mtda: Path, tmp_path: Path) -> None:
    output = tmp_path / "export_for_model"
    ExportService().export(ExportRequest(canonical_mtda, output, "minimal"))
    model = output_review_view_model(
        {
            "output_path": str(canonical_mtda),
            "archive_members": [
                "dataset/04_reports/test_report.html",
                "dataset/04_reports/audit_report.html",
                "metadata/surface_manifest.json",
            ],
            "last_export_status": "exported",
            "last_export_path": str(output),
        }
    )
    actions = {action["action_id"]: action for action in model["actions"]}

    assert actions["export_production_bundle"]["enabled"] is True
    assert actions["open_export_folder"]["enabled"] is True
    assert actions["open_test_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_surface_manifest"]["enabled"] is True
    assert model["surface_members"]["test_report"] == "dataset/04_reports/test_report.html"
    assert model["surface_members"]["audit_report"] == "dataset/04_reports/audit_report.html"
    assert model["status_summary"]["last_export_path"] == str(output)
    assert model["status_summary"]["last_export_status"] == "exported"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_mtdp_checksum(path: Path) -> str:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        source = json.loads(archive.read("metadata/provenance.json"))
    return str(source["source_mtdp"]["checksum"])
