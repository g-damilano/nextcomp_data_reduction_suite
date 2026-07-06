from __future__ import annotations

import json
import zipfile
from pathlib import Path

from methods.core.method_run_service import MethodRunRequest, MethodRunService
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_report_consumes_schema_metadata_roles_and_reduces_missing_fields(tmp_path: Path) -> None:
    baseline = _run_package(tmp_path / "baseline", {})
    enriched = _run_package(
        tmp_path / "enriched",
        {
            "material_label": "SS85_100_60",
            "test_id": "T-17",
            "report_operator": "G. Damilano",
            "loading_method": "method_1_shear_loading",
            "specimen_type": "type_a",
            "strain_measurement_method": "dual strain gauges",
        },
    )

    baseline_report = _json_member(baseline, "report/test_report.json")
    enriched_report = _json_member(enriched, "report/test_report.json")
    used = {
        row["field"]: row
        for row in enriched_report["report_values_used"]
    }
    missing = {row["field"] for row in enriched_report["missing_report_fields"]}

    assert enriched_report["summary"]["missing_report_field_count"] < baseline_report["summary"]["missing_report_field_count"]
    assert used["loading_method"]["value"] == "method_1_shear_loading"
    assert used["specimen_type"]["value"] == "type_a"
    assert used["strain_measurement_method"]["source"] == "source_mtdp_dataset"
    assert used["material_name"]["value"] == "SS85_100_60"
    assert not {"loading_method", "specimen_type", "strain_measurement_method", "operator", "test_id"} & missing


def test_report_only_metadata_does_not_block_readiness_or_execution(tmp_path: Path) -> None:
    package = _package_with_metadata(tmp_path / "report_only.mtdp", {})
    service = MethodRunService()
    request = MethodRunRequest(package, METHOD, MAPPING, tmp_path / "report_only.mtda", overwrite=True)

    readiness = service.check_readiness(request)
    result = service.run(request)

    assert readiness.status.value in {"READY", "READY_WITH_WARNINGS"}
    assert result.status == "completed"
    assert result.output_path is not None
    assert "report/test_report.html" in result.archive_members


def _run_package(directory: Path, metadata: dict[str, str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    package = _package_with_metadata(directory / "input.mtdp", metadata)
    output = directory / "output.mtda"
    result = MethodRunService().run(MethodRunRequest(package, METHOD, MAPPING, output, overwrite=True))
    assert result.status == "completed", result.errors
    return output


def _package_with_metadata(output: Path, metadata: dict[str, str]) -> Path:
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    dataset_fields = {"sample_type": "stage17", **metadata}
    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output,
        dataset_fields,
    )
    assert validation.ok, validation.messages()
    return output


def _json_member(path: Path, member: str) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))
