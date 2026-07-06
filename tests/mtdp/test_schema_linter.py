from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mtdp_enrichment.package import MTDPPackageWriter, MTDPSchema, RunInput
from mtdp_enrichment.package.validator import MTDPPackageValidator
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.schemas.linter import lint_schema


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_bundled_schemas_pass_lint():
    registry = SchemaRegistry()

    for schema in registry.all():
        assert lint_schema(schema).ok, schema.label()


def test_linter_detects_alias_collision():
    schema = SchemaRegistry().get("mechanical.compression").to_dict()
    schema["run_fields"][0]["import_aliases"] = ["duplicate_alias"]
    schema["run_fields"][1]["import_aliases"] = ["duplicate_alias"]

    result = lint_schema(MTDPSchema.from_dict(schema))

    assert not result.ok
    assert any(issue.code == "import_alias_collision" for issue in result.errors)


def test_linter_detects_bad_enum_value_map_and_image_policy():
    schema = SchemaRegistry().get("mechanical.compression").to_dict()
    validity = next(field for field in schema["run_fields"] if field["field_id"] == "validity")
    validity["value_map"]["maybe"] = "not_allowed"
    schema["image_evidence"]["accepted_formats"].append("jpg")

    result = lint_schema(MTDPSchema.from_dict(schema))

    assert not result.ok
    assert any(issue.code == "value_map_target_outside_enum" for issue in result.errors)
    assert any(issue.code == "invalid_image_extension" for issue in result.errors)


def test_linter_detects_bad_date_format_and_supplemental_policy():
    schema = SchemaRegistry().get("mechanical.compression").to_dict()
    test_date = next(field for field in schema["run_fields"] if field["field_id"] == "test_date")
    test_date["date_formats"]["accepted"].append("ambiguous-human-date")
    schema["supplemental_files"]["accepted_scopes"] = []

    result = lint_schema(MTDPSchema.from_dict(schema))

    assert not result.ok
    assert any(issue.code == "unsupported_date_format" for issue in result.errors)
    assert any(issue.code == "missing_supplemental_scopes" for issue in result.errors)


def test_linter_prevents_validity_aliases_on_failure_mode():
    schema = SchemaRegistry().get("mechanical.compression").to_dict()
    failure = next(field for field in schema["run_fields"] if field["field_id"] == "failure_mode")
    failure["import_aliases"] = [*failure.get("import_aliases", ()), "valid"]

    result = lint_schema(MTDPSchema.from_dict(schema))

    assert not result.ok
    assert any(issue.code == "validity_failure_mode_alias_overlap" for issue in result.errors)


def test_registry_rejects_invalid_schema_file(tmp_path: Path):
    schema = SchemaRegistry().get("mechanical.compression").to_dict()
    schema["run_fields"][0]["import_aliases"] = ["duplicate_alias"]
    schema["run_fields"][1]["import_aliases"] = ["duplicate_alias"]
    path = tmp_path / "bad.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_id: mechanical.bad",
                "schema_version: 0.1.0",
                "label: Bad",
                "status: active",
                "test: {family: mechanical, mode: compression}",
                "ui: {groups: [Dataset, Run analysis inputs]}",
                "run_fields:",
                "  - field_id: a",
                "    label: A",
                "    role: x",
                "    required: false",
                "    type: string",
                "    ui_group: Run analysis inputs",
                "    import_aliases: [same]",
                "    storage: {location: token_preamble, token: A}",
                "  - field_id: b",
                "    label: B",
                "    role: x",
                "    required: false",
                "    type: string",
                "    ui_group: Run analysis inputs",
                "    import_aliases: [same]",
                "    storage: {location: token_preamble, token: B}",
                "data_table: {columns: []}",
            ]
        ),
        encoding="utf-8",
    )

    try:
        SchemaRegistry(schema_dirs=[tmp_path])
    except ValueError as exc:
        assert "import_alias_collision" in str(exc)
    else:
        raise AssertionError("Invalid schema loaded successfully.")


def test_package_validator_rejects_invalid_embedded_schema(tmp_path: Path):
    parsed = ParserAdapter().parse(FIXTURE)
    schema = SchemaRegistry().get("mechanical.compression")
    valid = tmp_path / "valid.mtdp"
    broken = tmp_path / "broken.mtdp"
    assert MTDPPackageWriter().create_dataset_package(
        [RunInput("run_001", parsed)],
        schema,
        valid,
        {"sample_type": "linted"},
    ).ok

    with zipfile.ZipFile(valid) as source, zipfile.ZipFile(broken, "w") as target:
        schema_payload = json.loads(source.read("metadata/schema.json"))
        schema_payload["image_evidence"]["accepted_formats"].append("jpg")
        for name in source.namelist():
            target.writestr(
                name,
                json.dumps(schema_payload).encode("utf-8") if name == "metadata/schema.json" else source.read(name),
            )

    result = MTDPPackageValidator().validate(broken)

    assert not result.ok
    assert any(issue.code == "invalid_image_extension" for issue in result.errors)
