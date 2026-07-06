from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtdp_enrichment.package.migrator import MTDPMigrator, MigrationRegistry
from mtdp_enrichment.schemas import SchemaRegistry


SCHEMA_PATH = ROOT / "src" / "mtdp_enrichment" / "schema_library" / "mechanical" / "compression" / "0.3.0.yaml"
MIGRATION_PATH = (
    ROOT
    / "src"
    / "mtdp_enrichment"
    / "schema_library"
    / "mechanical"
    / "compression"
    / "migrations"
    / "0.2.0_to_0.3.0.yaml"
)


def test_compression_schema_0_3_adds_structured_failure_observation_fields() -> None:
    assert SCHEMA_PATH.exists()
    assert MIGRATION_PATH.exists()
    schema = SchemaRegistry().get("mechanical.compression", "0.3.0")
    fields = {field.field_id: field for field in schema.run_fields}
    section = next(item for item in schema.metadata_sections if item.id == "user_validity_failure_observation")

    assert list(section.field_refs) == [
        "primary_failure_mode",
        "failure_location",
        "invalid_specimen_reason",
        "invalid_specimen_reason_other",
        "visible_buckling_or_bending_observation",
        "visible_buckling_or_bending_observation_other",
        "failure_analysis_notes",
        "failure_image_reference",
        "validity",
        "requires_review",
        "rejection_reason",
    ]
    assert set(fields["primary_failure_mode"].allowed_values) >= {
        "in_plane_shear",
        "complex",
        "through_thickness_shear",
        "splitting",
        "delamination",
        "not_recorded",
    }
    assert fields["primary_failure_mode"].report_role == "failure_mode"
    assert fields["failure_location"].report_role == "failure_location"
    assert fields["invalid_specimen_reason"].display_labels["bending_non_compliance"] == "Bending non-compliance"
    assert fields["invalid_specimen_reason"].display_labels["grip_end_block_failure"] == "Grip/end block failure"
    assert fields["invalid_specimen_reason_other"].required_when == {"field": "invalid_specimen_reason", "equals": "other"}
    assert fields["visible_buckling_or_bending_observation"].display_labels["none_observed"] == "None observed"
    assert (
        fields["visible_buckling_or_bending_observation"].display_labels["suspected_euler_buckling"]
        == "Suspected Euler buckling"
    )
    assert fields["visible_buckling_or_bending_observation_other"].visible_when == {
        "field": "visible_buckling_or_bending_observation",
        "equals": "other",
    }
    assert fields["failure_analysis_notes"].report_role == "failure_analysis_notes"
    assert fields["failure_mode"].report_role == "failure_mode"


def test_compression_schema_0_3_uses_iso_controlled_choices_with_optional_other() -> None:
    schema = SchemaRegistry().get("mechanical.compression", "0.3.0")
    dataset_fields = {field.field_id: field for field in schema.dataset_fields}
    run_fields = {field.field_id: field for field in schema.run_fields}
    section = next(item for item in schema.metadata_sections if item.id == "test_identification")
    geometry_section = next(item for item in schema.metadata_sections if item.id == "specimen_geometry")

    assert dataset_fields["loading_method"].type == "enum"
    assert dataset_fields["loading_method"].allowed_values == (
        "method_1_shear_loading",
        "method_2_combined_loading",
        "other_specified",
    )
    assert dataset_fields["loading_method"].display_labels["method_1_shear_loading"] == "Shear loading (Method 1)"
    assert dataset_fields["loading_method"].iso_compliant_values == (
        "method_1_shear_loading",
        "method_2_combined_loading",
    )
    assert dataset_fields["loading_method"].deviation_values == ("other_specified",)
    assert dataset_fields["specimen_type"].allowed_values == ("type_a", "type_b1", "type_b2", "other_specified")
    assert dataset_fields["specimen_type"].display_labels["type_b1"] == "Type B1"
    assert "loading_method_other" in section.field_refs
    assert "specimen_type_other" in section.field_refs
    assert run_fields["gauge_length"].label == "Strain-measurement gauge length"
    assert "extension or crosshead displacement" in run_fields["gauge_length"].description
    assert {"distance_between_end_tabs", "tab_length", "tab_thickness"} <= set(geometry_section.field_refs)


def test_conditional_other_fields_are_required_only_when_other_is_selected() -> None:
    schema = SchemaRegistry().get("mechanical.compression", "0.3.0")
    fields = {field.field_id: field for field in schema.dataset_fields}
    definitions = (fields["loading_method"], fields["loading_method_other"])

    normalized, validation = schema.validate_field_set(
        definitions,
        {
            "loading_method": "method_1_shear_loading",
            "loading_method_other": "stale hidden detail",
        },
    )
    assert validation.ok
    assert "loading_method_other" not in normalized

    normalized, validation = schema.validate_field_set(definitions, {"loading_method": "other_specified"})
    assert not validation.ok
    assert any(message.field == "loading_method_other" for message in validation.errors)

    normalized, validation = schema.validate_field_set(
        definitions,
        {"loading_method": "other_specified", "loading_method_other": "fixture-specific loading"},
    )
    assert validation.ok
    assert normalized["loading_method_other"].value == "fixture-specific loading"


def test_compression_schema_0_3_migration_maps_legacy_failure_mode() -> None:
    plan = MigrationRegistry().plan("mechanical.compression", "0.2.0", "0.3.0")
    payload = yaml.safe_load(MIGRATION_PATH.read_text(encoding="utf-8"))

    assert plan is not None
    assert plan.status == "automatic_migration"
    failure_operation = next(item for item in payload["operations"] if item.get("target_field") == "primary_failure_mode")
    loading_operation = next(item for item in payload["operations"] if item.get("target_field") == "loading_method")

    assert failure_operation["operation"] == "map_enum_value"
    assert failure_operation["value_map"]["In-plane shear"] == "in_plane_shear"
    assert loading_operation["value_map"]["Method 1"] == "method_1_shear_loading"
    assert "end-loaded compression" not in loading_operation["value_map"]


def test_compression_schema_0_3_migration_maps_only_explicit_iso_method_values() -> None:
    schema = SchemaRegistry().get("mechanical.compression", "0.3.0")
    plan = MigrationRegistry().plan("mechanical.compression", "0.2.0", "0.3.0")
    assert plan is not None

    migrated = MTDPMigrator().apply_plan_to_files(
        {
            "dataset.json": _json_bytes(
                {
                    "report": {
                        "test_identification": {
                            "loading_method": "Method 1",
                            "specimen_type": "Type B2",
                        }
                    }
                }
            ),
            "provenance.json": _json_bytes({}),
        },
        schema,
        plan,
    )
    dataset = yaml.safe_load(migrated["dataset.json"].decode("utf-8"))

    assert dataset["report"]["test_identification"]["loading_method"] == "method_1_shear_loading"
    assert dataset["report"]["test_identification"]["specimen_type"] == "type_b2"

    ambiguous = MTDPMigrator().apply_plan_to_files(
        {
            "dataset.json": _json_bytes(
                {
                    "report": {
                        "test_identification": {
                            "loading_method": "end-loaded compression",
                            "specimen_type": "rectangular coupon",
                        }
                    }
                }
            ),
            "provenance.json": _json_bytes({}),
        },
        schema,
        plan,
    )
    ambiguous_dataset = yaml.safe_load(ambiguous["dataset.json"].decode("utf-8"))

    assert "loading_method" not in ambiguous_dataset["report"]["test_identification"]
    assert "specimen_type" not in ambiguous_dataset["report"]["test_identification"]


def _json_bytes(payload: dict[str, object]) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")
