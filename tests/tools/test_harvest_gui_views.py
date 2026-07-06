from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_harvest_module():
    module_path = ROOT / "tools" / "harvest_gui_views.py"
    spec = importlib.util.spec_from_file_location("harvest_gui_views_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harvest = _load_harvest_module()


def _all_screens_harvested() -> dict[str, object]:
    return {screen_id: {"summary_cards": [{"label": "Status", "value": "ok"}]} for screen_id in harvest.SCREEN_IDS}


def test_diagnostic_card_rows_capture_gap_cards_and_plot_evidence() -> None:
    review_rows = [
        {
            "run_id": "run_001",
            "diagnostic_cockpit": {
                "view_id": "bending.curve_shape",
                "plot_contract": {
                    "plot_kind": "load_strain",
                    "missing_required_keys": ["compressive_strain"],
                },
                "evidence_packet": {"missing_required_keys": ["bending_peak"]},
                "cards": [
                    {
                        "evidence_key": "bending.max_percent",
                        "label": "Bending peak",
                        "value": "--",
                        "subtext": "required evidence missing",
                        "state": "gap",
                        "level": "warn",
                        "required": True,
                    }
                ],
            },
        }
    ]

    card_rows = harvest.diagnostic_card_rows("case-a", review_rows)
    findings = harvest.unattended_findings("case-a", {"flags": [{"run_id": "run_001"}]}, review_rows, _all_screens_harvested())

    assert card_rows == [
        {
            "case_id": "case-a",
            "run_id": "run_001",
            "defect_index": 1,
            "view_id": "bending.curve_shape",
            "plot_kind": "load_strain",
            "evidence_key": "bending.max_percent",
            "label": "Bending peak",
            "value": "--",
            "subtext": "required evidence missing",
            "state": "gap",
            "level": "warn",
            "required": True,
        }
    ]
    finding_types = {row["finding_type"] for row in findings}
    assert "acceptance_flags_not_surfaced" not in finding_types
    assert "diagnostic_card_evidence_gap" in finding_types
    assert "missing_required_evidence" in finding_types
    assert "missing_plot_evidence" in finding_types


def test_unattended_findings_report_missing_screens_and_unsurfaced_flags() -> None:
    findings = harvest.unattended_findings(
        "case-b",
        {"flags": [{"run_id": "run_002", "message": "review required"}]},
        [],
        {"package_preview": {"summary_cards": []}},
    )

    finding_types = {row["finding_type"] for row in findings}
    assert "acceptance_flags_not_surfaced" in finding_types
    assert "screen_cards_empty" in finding_types
    assert "screen_not_harvested" in finding_types


def test_unattended_findings_treat_not_ready_report_authoring_as_not_applicable() -> None:
    view_models = _all_screens_harvested()
    view_models.pop("report_authoring")

    findings = harvest.unattended_findings("case-not-ready", {}, [], view_models, case_status="not_ready")

    assert all(row["screen_id"] != "report_authoring" for row in findings)


def test_screen_inventory_tracks_harvested_card_and_row_counts() -> None:
    cockpit_view = harvest.acceptance_diagnostic_cockpit_harvest_view(
        [{"run_id": "run_001", "label": "Max bending"}],
        [{"run_id": "run_001", "diagnostic_cockpit": {"view_id": "bending.curve_shape"}}],
    )
    inventory = harvest.screen_inventory(
        {
            "package_preview": {
                "schema_name": "package_preview_view_model",
                "summary_cards": [{"label": "Runs", "value": "7"}],
                "source_files": [{"run_id": "run_001"}, {"run_id": "run_002"}],
            },
            "acceptance_gate": {
                "status": "warn",
                "summary_cards": [{"label": "Review Required", "value": "1"}],
                "selection_cards": [{"label": "Final", "value": "5 included"}],
                "run_rows": [{"run_id": "run_001"}],
            },
            "acceptance_diagnostic_cockpit": cockpit_view,
        }
    )

    by_screen = {row["screen_id"]: row for row in inventory}
    assert by_screen["package_preview"]["harvested"] is True
    assert by_screen["package_preview"]["card_count"] == 1
    assert by_screen["package_preview"]["row_count"] == 2
    assert by_screen["acceptance_gate"]["card_count"] == 2
    assert by_screen["acceptance_gate"]["row_count"] == 1
    assert by_screen["acceptance_diagnostic_cockpit"]["card_count"] == 1
    assert by_screen["acceptance_diagnostic_cockpit"]["row_count"] == 0
    assert by_screen["method_preview"]["harvested"] is False


def test_render_index_html_includes_relative_run_links_and_findings(tmp_path: Path) -> None:
    output_root = tmp_path / "harvest"
    run_dir = output_root / "runs" / "case-c"
    run_dir.mkdir(parents=True)
    (run_dir / "unattended_findings.json").write_text(
        json.dumps(
            [
                {
                    "case_id": "case-c",
                    "screen_id": "bending.curve_shape",
                    "run_id": "run_003",
                    "finding_type": "diagnostic_card_evidence_gap",
                    "detail": "Bending peak missing",
                }
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "diagnostic_cards.json").write_text("[]", encoding="utf-8")
    manifest = {
        "created_at": "2026-06-12T00:00:00Z",
        "input_count": 1,
        "completed_count": 1,
        "failed_count": 0,
        "unattended_count": 1,
        "records": [
            {
                "case_id": "case-c",
                "input_name": "case-c.mtdp",
                "run_dir": str(run_dir),
                "run_dir_ref": "runs/case-c/",
                "status": "completed",
                "readiness_status": "READY",
                "screen_inventory": [],
                "review_row_count": 1,
                "diagnostic_card_count": 1,
                "unattended_count": 1,
                "diagnostic_cards": "runs/case-c/diagnostic_cards.json",
                "unattended_findings": "runs/case-c/unattended_findings.json",
                "view_models": {},
            }
        ],
    }

    html = harvest.render_index_html(manifest)

    assert 'href="runs/case-c/"' in html
    assert "diagnostic_card_evidence_gap" in html
    assert "Bending peak missing" in html
