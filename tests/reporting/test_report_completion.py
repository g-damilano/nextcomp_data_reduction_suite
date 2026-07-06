from __future__ import annotations

import json
import hashlib
import zipfile
from pathlib import Path

import pytest

from archives.core.layouts import MTDAAlignedLayout, report_member
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from mtdp_enrichment.package import MTDPPackageWriter, RunInput
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from reporting.completion import (
    build_report_field_catalog,
    normalize_report_overrides,
    report_completion_status,
)
from reporting.report_recipe_loader import load_report_recipe


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RAW_FIXTURE = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"


def test_report_field_catalog_uses_recipe_and_schema_importance() -> None:
    schema = SchemaRegistry().get("mechanical.compression")
    recipe = load_report_recipe(METHOD / "report_recipe.yaml")

    catalog = {entry.field_key: entry for entry in build_report_field_catalog(recipe, schema.to_dict())}

    assert catalog["loading_method"].section_id == "test_identification"
    assert catalog["loading_method"].report_importance == "required"
    assert catalog["specimen_type"].report_importance == "required"
    assert catalog["operator"].report_importance == "recommended"


def test_report_completion_status_classifies_required_and_recommended_missing() -> None:
    status = report_completion_status(
        [
            {"field": "loading_method", "report_importance": "required"},
            {"field": "operator", "report_importance": "recommended"},
        ]
    )

    assert status["status"] == "INCOMPLETE"
    assert status["required_missing_count"] == 1
    assert status["recommended_missing_count"] == 1

    warnings = report_completion_status([{"field": "operator", "report_importance": "recommended"}])
    assert warnings["status"] == "COMPLETE_WITH_WARNINGS"


def test_report_override_requires_reason() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        normalize_report_overrides([{"field_key": "loading_method", "value": "override"}])


def test_report_completion_checker_records_provenance(tmp_path: Path) -> None:
    service = MethodRunService()
    package = _package_with_metadata(
        tmp_path / "input.mtdp",
        {
            "sample_type": "stage18",
            "loading_method": "method_1_shear_loading",
            "specimen_type": "type_a",
            "strain_measurement_method": "dual strain gauges",
        },
    )
    before_hash = hashlib.sha256(package.read_bytes()).hexdigest()
    output = tmp_path / "completion_provenance.mtda"
    result = service.run(
        MethodRunRequest(
            input_package_path=package,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            report_overrides=(
                {
                    "field_key": "loading_method",
                    "value": "method_2_combined_loading",
                    "reason": "Report completion review",
                    "reviewer": "QA",
                },
            ),
        )
    )

    assert result.status == "completed"
    report = _json_member(output, report_member("test_report.json"))
    catalog = report["report_field_catalog_resolved"]
    overrides = report["report_field_overrides"]
    ledger = report["report_override_ledger"]
    audit = _json_member(output, report_member("audit_report.json"))
    provenance = _json_member(output, MTDAAlignedLayout.provenance)

    used = {row["field"]: row for row in report["report_values_used"]}
    assert used["loading_method"]["value"] == "method_2_combined_loading"
    assert used["loading_method"]["source_type"] == "report_override"
    assert used["loading_method"]["source_path"] == "report_overrides.loading_method"
    assert used["specimen_type"]["source_type"] == "source_mtdp_dataset"
    assert any(row["field_key"] == "loading_method" for row in catalog)
    assert overrides[0]["field_key"] == "loading_method"
    assert ledger["records"][0]["decision_type"] == "set_report_value"
    assert audit["report_completion"]["override_count"] == 1
    assert audit["report_completion"]["mtdp_mutated"] is False
    assert audit["report_overrides"]["mtdp_mutation"] == "not_mutated"
    assert any(event["event"] == "report_overrides_applied" and event["mtdp_mutated"] is False for event in provenance["events"])
    assert result.report_summary["report_completion_status"] in {"COMPLETE", "COMPLETE_WITH_WARNINGS", "INCOMPLETE"}
    assert result.report_summary["override_count"] == 1
    assert hashlib.sha256(package.read_bytes()).hexdigest() == before_hash


def test_report_override_decreases_missing_field_count_without_mutating_mtdp(tmp_path: Path) -> None:
    service = MethodRunService()
    package = _package_with_metadata(tmp_path / "input.mtdp", {"sample_type": "stage19"})
    before_hash = hashlib.sha256(package.read_bytes()).hexdigest()
    baseline_output = tmp_path / "baseline.mtda"
    override_output = tmp_path / "override.mtda"

    baseline = service.run(MethodRunRequest(package, METHOD, MAPPING, baseline_output))
    override = service.run(
        MethodRunRequest(
            package,
            METHOD,
            MAPPING,
            override_output,
            report_overrides=(
                {
                    "field_key": "loading_method",
                    "value": "method_1_shear_loading",
                    "reason": "Authoring review before final report",
                },
            ),
        )
    )

    assert baseline.status == "completed"
    assert override.status == "completed"
    assert override.report_summary["missing_report_field_count"] < baseline.report_summary["missing_report_field_count"]
    used = {row["field"]: row for row in _json_member(override_output, report_member("test_report.json"))["report_values_used"]}
    assert used["loading_method"]["source_type"] == "report_override"
    assert hashlib.sha256(package.read_bytes()).hexdigest() == before_hash


def test_report_only_missing_fields_do_not_block_readiness_or_execution() -> None:
    service = MethodRunService()
    request = MethodRunRequest(INPUT, METHOD, MAPPING, ROOT / "unused.mtda")

    readiness = service.check_readiness(request)

    assert readiness.status.value in {"READY", "READY_WITH_WARNINGS"}
    assert readiness.blocks_execution is False


def test_other_specified_controlled_choices_are_complete_but_report_deviations(tmp_path: Path) -> None:
    service = MethodRunService()
    package = _package_with_metadata(
        tmp_path / "other_specified.mtdp",
        {
            "sample_type": "stage19_other",
            "loading_method": "other_specified",
            "loading_method_other": "Compression between calibrated platens",
            "specimen_type": "other_specified",
            "specimen_type_other": "Custom coupon geometry",
            "strain_measurement_method": "dual strain gauges",
        },
    )
    output = tmp_path / "other_specified.mtda"

    result = service.run(MethodRunRequest(package, METHOD, MAPPING, output))

    assert result.status == "completed"
    report = _json_member(output, report_member("test_report.json"))
    document = report["report_document"]
    missing = {row["field"] for row in report["missing_report_fields"]}
    deviations = report["deviations_from_standard"]
    test_fields = next(
        block["data"]
        for section in document["sections"]
        if section["id"] == "test_identification"
        for block in section["blocks"]
        if block["id"] == "test_identification_fields"
    )
    values = {row["key"]: row["value"] for row in test_fields}

    assert "loading_method" not in missing
    assert "loading_method_other" not in missing
    assert "specimen_type" not in missing
    assert "specimen_type_other" not in missing
    assert values["loading_method"] == "Other specified: Compression between calibrated platens"
    assert values["specimen_type"] == "Other specified: Custom coupon geometry"
    assert any(row["Affected item"] == "Loading method" and "outside the ISO-controlled choices" in row["Report treatment"] for row in deviations)
    assert any(row["Affected item"] == "Specimen type" and "outside the ISO-controlled choices" in row["Report treatment"] for row in deviations)


def test_ambiguous_controlled_choice_override_remains_missing(tmp_path: Path) -> None:
    service = MethodRunService()
    package = _package_with_metadata(tmp_path / "ambiguous.mtdp", {"sample_type": "stage19_ambiguous"})
    output = tmp_path / "ambiguous.mtda"

    result = service.run(
        MethodRunRequest(
            package,
            METHOD,
            MAPPING,
            output,
            report_overrides=(
                {
                    "field_key": "loading_method",
                    "value": "fixture-guided compression",
                    "reason": "Ambiguous legacy wording",
                },
            ),
        )
    )

    assert result.status == "completed"
    report = _json_member(output, report_member("test_report.json"))

    assert "loading_method" in {row["field"] for row in report["missing_report_fields"]}
    assert not any(row["Affected item"] == "Loading method" for row in report["deviations_from_standard"])


def _json_member(path: Path, member: str):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def _package_with_metadata(output: Path, metadata: dict[str, str]) -> Path:
    parsed = ParserAdapter().parse(RAW_FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    validation = MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        output,
        metadata,
    )
    assert validation.ok, validation.messages()
    return output
