from __future__ import annotations

import pytest

from ui.method_run_wizard.view_models.report_authoring import (
    build_report_override_payload,
    filter_report_authoring_fields,
    report_authoring_view_model,
)


def test_report_authoring_view_model_groups_filters_and_marks_overrides() -> None:
    model = report_authoring_view_model(
        catalog=[
            {
                "field_key": "loading_method",
                "label": "Loading Method",
                "section_id": "test_identification",
                "section_title": "Test Identification",
                "report_importance": "required",
                "report_role": "loading_method",
                "required": True,
            },
            {
                "field_key": "operator",
                "label": "Operator",
                "section_id": "test_identification",
                "section_title": "Test Identification",
                "report_importance": "recommended",
                "report_role": "operator",
            },
        ],
        values_used=[
            {
                "field": "operator",
                "value": "QA",
                "source_type": "source_mtdp_dataset",
                "source_path": "dataset.report.operator",
            }
        ],
        missing_fields=[
            {
                "field": "loading_method",
                "section_id": "test_identification",
                "section_title": "Test Identification",
                "report_importance": "required",
            }
        ],
        overrides=[
            {
                "field_key": "loading_method",
                "value": "fixture-guided compression",
                "reason": "Known from lab sheet",
                "reviewer": "QA",
            }
        ],
    )

    assert model["summary"]["field_count"] == 2
    assert model["summary"]["missing_count"] == 0
    assert model["summary"]["override_count"] == 1
    assert model["sections"][0]["title"] == "Test Identification"

    overridden = filter_report_authoring_fields(model, "overridden")
    required = filter_report_authoring_fields(model, "required")
    recommended = filter_report_authoring_fields(model, "recommended")

    assert overridden[0]["field_key"] == "loading_method"
    assert overridden[0]["source_type"] == "report_override"
    assert overridden[0]["override_value"] == "fixture-guided compression"
    assert required[0]["field_key"] == "loading_method"
    assert recommended[0]["field_key"] == "operator"


def test_report_authoring_override_payload_requires_reason() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        build_report_override_payload(field_key="operator", value="QA", reason="")
