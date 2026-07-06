from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_run_service import MethodRunRequest, MethodRunService
from ui.method_run_wizard.view_models.gate_summary import (
    acceptance_gate_view_model,
    readiness_gate_view_model,
    validation_gate_view_model,
)
from ui.method_run_wizard.view_models.mapping_preview import mapping_preview_view_model
from ui.method_run_wizard.view_models.method_preview import method_preview_view_model
from ui.method_run_wizard.view_models.output_review import output_review_view_model
from ui.method_run_wizard.view_models.package_preview import package_preview_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def service() -> MethodRunService:
    return MethodRunService()


@pytest.fixture(scope="module")
def stage11_mtda(service: MethodRunService, tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage11_method_run") / "stage11.mtda"
    result = service.run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output


def test_package_page_summary_generation(service: MethodRunService) -> None:
    model = package_preview_view_model(service.load_package(INPUT))

    assert model["analysis_type"] == "mechanical.compression"
    assert model["run_count"] == 7
    assert model["source_file_count"] == 7
    assert {"load", "strain", "extension", "time"} <= {
        row["family"] for row in model["channel_families"]
    }
    assert model["validity_summary"]["valid"] >= 1
    assert model["source_files"][0]["run_id"] == "run_001"


def test_method_page_uses_method_manifest(service: MethodRunService) -> None:
    model = method_preview_view_model(service.load_method(METHOD))

    assert model["method_id"] == "iso14126_2023"
    assert model["standard_name"].startswith("BS EN ISO 14126")
    assert model["standard_reference"]
    assert "resolve_recipe" in model["available_recipes"]
    assert "report_recipe" in model["available_recipes"]
    assert any("Calculate specimen-level" in item for item in model["process_summary"])
    assert "specimen_properties.compressive_strength_MPa" in model["declared_outputs"]


def test_mapping_page_resolves_example_values(service: MethodRunService) -> None:
    model = mapping_preview_view_model(service.load_mapping(MAPPING, METHOD, INPUT))
    rows = {row["method_field"]: row for row in model["rows"]}

    assert "Mapping tells the method" in model["why_required"]
    assert rows["specimen.width_mm"]["source"] == "Width"
    assert rows["specimen.width_mm"]["example_value"] not in {"", None}
    assert rows["channel.load_N"]["source"] == "Load"
    assert rows["channel.load_N"]["coverage"] == "7/7 runs"
    assert rows["channel.front_strain"]["unit"] == "mm/mm"


def test_gate_summaries_group_operator_evidence(stage11_mtda: Path) -> None:
    readiness = readiness_gate_view_model(_json_member(stage11_mtda, "readiness/readiness_report.json"))
    validation = validation_gate_view_model(_json_member(stage11_mtda, "validation/validation_report.json"))
    acceptance = acceptance_gate_view_model(_json_member(stage11_mtda, "acceptance/acceptance_report.json"))

    assert {"execution_critical", "report_completeness", "per_run_warnings"} <= {
        group["group_id"] for group in readiness["groups"]
    }
    assert {"checks_by_run", "checks_by_type"} <= {
        group["group_id"] for group in validation["groups"]
    }
    assert acceptance["selection_cards"]
    assert {"selection_sets", "bending_pattern_flags"} <= {
        group["group_id"] for group in acceptance["groups"]
    }


def test_output_page_exposes_report_audit_workbench_and_key_csvs(stage11_mtda: Path) -> None:
    with zipfile.ZipFile(stage11_mtda) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    model = output_review_view_model(
        {
            "output_path": str(stage11_mtda),
            "archive_members": members,
            "workbench_path": str(stage11_mtda.with_suffix("")) + "_workbench",
        }
    )

    actions = {action["action_id"]: action for action in model["actions"]}
    assert actions["open_iso_report"]["enabled"] is True
    assert actions["open_audit_report"]["enabled"] is True
    assert actions["open_workbench"]["enabled"] is True
    assert "report/aggregate_statistics.csv" in model["key_csvs"]
    assert "validation/deviations.csv" in model["key_csvs"]
    assert "acceptance/discharged_runs.csv" in model["key_csvs"]


def test_report_html_contains_renderable_vega_plot_block(stage11_mtda: Path) -> None:
    with zipfile.ZipFile(stage11_mtda) as archive:
        html = archive.read("report/iso14126_report.html").decode("utf-8")
        document = json.loads(archive.read("report/report_document.json"))

    assert "data-vega-block" in html
    assert "vegaEmbed" in html
    assert "Stress-strain aggregate" in html
    assert '"$schema": "https://vega.github.io/schema/vega-lite/v5.json"' in html
    assert any(
        block["type"] == "vega_plot" and "vega_lite_spec" in block["data"]
        for section in document["sections"]
        for block in section["blocks"]
    )


def _json_member(path: Path, member: str):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))

