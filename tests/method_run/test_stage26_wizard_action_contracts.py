from __future__ import annotations

from ui.method_run_wizard.view_models.action_contracts import (
    wizard_page_action_contract,
    wizard_page_action_contracts,
)
from ui.method_run_wizard.view_models.output_review import output_review_view_model


def test_wizard_action_contracts_exist_for_all_required_scenarios() -> None:
    records = wizard_page_action_contracts()
    expected = {
        "package",
        "method",
        "mapping",
        "readiness",
        "report_metadata",
        "execution",
        "validation",
        "acceptance",
        "output",
    }

    assert expected <= set(records)
    for page_id in expected:
        contract = records[page_id]
        assert contract["purpose"]
        assert contract["operator_decision"]
        assert contract["allowed_actions"]
        assert contract["downstream_consequence"]


def test_output_contract_exposes_separate_surface_and_archive_actions() -> None:
    contract = wizard_page_action_contract("output")
    actions = set(contract["allowed_actions"])

    assert "open_test_report" in actions
    assert "open_audit_report" in actions
    assert "open_workbench" in actions
    assert "finalize_mtda" in actions
    assert "export_production_bundle" in actions


def test_wizard_view_models_surface_action_contracts() -> None:
    payload = output_review_view_model({"archive_members": ["surface_manifest.json"], "surface_manifest": {}})
    action_contract = payload["page_action_contract"]

    assert action_contract["page_id"] == "output"
    assert action_contract["allowed_actions"]
    assert "open_test_report" in action_contract["allowed_actions"]
    assert "open_audit_report" in action_contract["allowed_actions"]
    assert "open_workbench" in action_contract["allowed_actions"]
