from __future__ import annotations

from mtdp_enrichment.enrichment_import import EmpiricalYamlMatcher
from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.schemas import SchemaRegistry
from mtdp_enrichment.schemas.linter import lint_schema


def test_structured_import_aliases_load_and_preserve_flat_compatibility():
    payload = SchemaRegistry().get("mechanical.compression").to_dict()
    operator = next(field for field in payload["run_fields"] if field["field_id"] == "operator")
    operator["import_aliases"] = {
        "canonical_paths": ["run.acquisition.operator"],
        "field_ids": ["operator"],
        "source_specific": ["tester"],
        "weak_keys": ["user"],
    }

    schema = MTDPSchema.from_dict(payload)
    field = schema.field_by_import_alias("tester")
    weak = schema.alias_entry_for_import_alias("user")

    assert field is not None
    assert field.field_id == "operator"
    assert weak is not None
    assert weak[0].field_id == "operator"
    assert weak[1].kind == "weak_key"
    assert "tester" in schema.field_by_id("operator").import_aliases


def test_linter_rejects_structured_alias_collisions():
    payload = SchemaRegistry().get("mechanical.compression").to_dict()
    width = next(field for field in payload["run_fields"] if field["field_id"] == "width")
    thickness = next(field for field in payload["run_fields"] if field["field_id"] == "thickness")
    width["import_aliases"] = {"weak_keys": ["ambiguous_dimension"]}
    thickness["import_aliases"] = {"weak_keys": ["ambiguous_dimension"]}

    result = lint_schema(MTDPSchema.from_dict(payload))

    assert not result.ok
    assert any(issue.code in {"weak_import_alias_collision", "import_alias_collision"} for issue in result.errors)


def test_empirical_yaml_matcher_proposes_review_only_matches_without_llm():
    schema = SchemaRegistry().get("mechanical.compression")
    matcher = EmpiricalYamlMatcher()

    width = matcher.propose(source_key="dimension_a", source_value=9.8, schema=schema)
    load_cell = matcher.propose(source_key="LC", source_value=50, schema=schema)
    valid = matcher.propose(source_key="valid", source_value=1, schema=schema)
    date = matcher.propose(source_key="date", source_value="16/07/2014", schema=schema)

    assert width.target_field_id == "width"
    assert width.requires_confirmation
    assert any("legacy dimension" in item for item in width.evidence)
    assert load_cell.target_field_id == "load_cell"
    assert valid.target_field_id == "validity"
    assert valid.transform == "value_map"
    assert date.target_field_id == "test_date"
    assert "ISO" in (date.transform or "")
