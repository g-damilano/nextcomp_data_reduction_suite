from __future__ import annotations

import json
import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout
from audit.audit_block_renderers import _curve_shape_method_rows, _curve_shape_result_fields, _curve_shape_result_rows


AUDIT_HTML = f"{MTDAAlignedLayout.reports_prefix}audit_report.html"
AUDIT_JSON = f"{MTDAAlignedLayout.reports_prefix}audit_report.json"
METHOD_OUTPUTS = MTDAAlignedLayout.method_outputs


def test_curve_shape_diagnostic_artifacts_are_generic_and_visible(stage26_canonical_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        audit = json.loads(archive.read(AUDIT_JSON))
        method_outputs = json.loads(archive.read(METHOD_OUTPUTS))
        html = archive.read(AUDIT_HTML).decode("utf-8")
    report = method_outputs["curve_shape_diagnostic_report"]

    assert "curve_shape_diagnostic_scores" in method_outputs
    assert "curve_family" in method_outputs
    assert "curve_family_full" in method_outputs
    assert report["operation_type"] == "curve_family_diagnostic"
    assert report["cohorts"][0]["cohort_id"] == "whole_comparable_dataset"
    assert "gauge" not in json.dumps(report["cohorts"]).casefold()
    assert audit["audit_blocks"]["summary"]["aggregate_block_count"] == 4
    assert 'data-block-type="aggregate_curve_shape_diagnostics"' in html
    assert html.index("Curve-shape outlier diagnostics") < html.index('id="decision_register"')
    assert "Dixon high-outlier Q-test" in html
    assert 'data-audit-plot="curve_shape_distance_ranking"' in html
    assert "distance_rms" in html
    assert "distance_rank" in html
    assert "Qexp" in html
    assert "Qcrit_95" in html
    assert "threshold_method" in html


def test_run_packets_show_curve_shape_evidence_before_validation_and_decisions(stage26_canonical_mtda: Path) -> None:
    with zipfile.ZipFile(stage26_canonical_mtda) as archive:
        audit = json.loads(archive.read(AUDIT_JSON))
        html = archive.read(AUDIT_HTML).decode("utf-8")

    assert audit["audit_blocks"]["summary"]["run_packet_count"] == 7

    first_packet_start = html.index('id="packet-run_001"')
    second_packet_start = html.index('id="packet-run_002"')
    run_section = html[first_packet_start:second_packet_start]
    assert run_section.index('data-block-type="run_bending_evidence"') < run_section.index(
        'data-block-type="run_curve_shape_diagnostic"'
    )
    assert 'data-block-type="run_selection_consequence"' not in run_section
    assert "Final report run set" not in run_section
    assert "Included in final report runs" not in run_section


def test_mad_curve_shape_rows_use_mad_report_vocabulary() -> None:
    scores = [
        {
            "run_id": "run_001",
            "specimen": "Specimen 1",
            "cohort_id": "whole_comparable_dataset",
            "effective_sample_size": 14,
            "distance_rms": 1.67,
            "distance_rank": 1,
            "threshold_method": "robust_mad_zscore",
            "robust_z": 2.18,
            "z_mad": 2.18,
            "mad_upper_z": 2.18,
            "threshold_value": 3.5,
            "robust_center": 0.82,
            "robust_scaled_mad": 0.39,
            "is_curve_shape_outlier": False,
            "diagnostic_classification": "CURVE_SHAPE_NORMAL",
        }
    ]
    cohorts = [
        {
            "cohort_id": "whole_comparable_dataset",
            "evaluable_curves": 14,
            "threshold_branch_used": "robust_mad_zscore",
            "threshold_summary": {
                "robust_z_threshold": 3.5,
                "robust_center": 0.82,
                "robust_scaled_mad": 0.39,
            },
        }
    ]

    method_rows = dict(_curve_shape_method_rows(scores, cohorts, threshold_method="robust_mad_zscore"))
    result_rows = _curve_shape_result_rows(scores, threshold_method="robust_mad_zscore")

    assert "Upper-tail MAD cutoff (z_crit)" in method_rows
    assert "Critical Q at 95% (Qcrit_95)" not in method_rows
    assert _curve_shape_result_fields("robust_mad_zscore") == [
        "run_id",
        "specimen",
        "distance_rms",
        "distance_rank",
        "mad_upper_z",
        "robust_z",
        "threshold_value",
        "is_curve_shape_outlier",
        "diagnostic_classification",
    ]
    assert result_rows[0]["mad_upper_z"] == "2.18"
    assert result_rows[0]["robust_z"] == "2.18"
    assert "Qexp" not in result_rows[0]


def test_dixon_curve_shape_rows_show_masking_companion_evidence() -> None:
    scores = [
        {
            "run_id": "run_004",
            "specimen": "Specimen 4",
            "cohort_id": "whole_comparable_dataset",
            "effective_sample_size": 10,
            "distance_rms": 1.969,
            "distance_rank": 1,
            "threshold_method": "dixon_high_outlier_q_test",
            "secondary_threshold_method": "robust_mad_masking_screen",
            "dixon_variant": "r11",
            "dixon_gap": 0.337,
            "dixon_denominator": 1.5149,
            "Qexp": 0.22245,
            "Qcrit_95": 0.534,
            "dixon_decision": "no_outlier",
            "mad_upper_z": 11.29,
            "masking_companion_flag": True,
            "masking_companion_flag_count": 2,
            "is_curve_shape_outlier": True,
            "diagnostic_classification": "CURVE_SHAPE_OUTLIER",
        }
    ]
    cohorts = [
        {
            "cohort_id": "whole_comparable_dataset",
            "evaluable_curves": 10,
            "threshold_branch_used": "dixon_high_outlier_q_test",
            "threshold_summary": {
                "Qcrit_95": 0.534,
                "dixon_variant": "r11",
                "dixon_gap": 0.337,
                "dixon_denominator": 1.5149,
                "threshold_value": 3.5,
                "masking_companion_flag_count": 2,
                "masking_risk": True,
            },
        }
    ]

    method_rows = dict(_curve_shape_method_rows(scores, cohorts, threshold_method="dixon_high_outlier_q_test"))
    result_rows = _curve_shape_result_rows(scores, threshold_method="dixon_high_outlier_q_test")

    assert method_rows["Dixon scope"] == "Single highest distance only; no sequential retesting"
    assert "Companion screen" in method_rows
    assert method_rows["Companion MAD cutoff (z_crit)"] == "3.5"
    assert method_rows["Companion flags"] == 2
    assert method_rows["Masking risk"] == "Yes"
    assert _curve_shape_result_fields("dixon_high_outlier_q_test") == [
        "run_id",
        "specimen",
        "distance_rms",
        "distance_rank",
        "dixon_variant",
        "dixon_gap",
        "dixon_denominator",
        "Qexp",
        "dixon_decision",
        "mad_upper_z",
        "masking_companion_flag",
        "is_curve_shape_outlier",
        "diagnostic_classification",
    ]
    assert result_rows[0]["Qexp"] == "0.222"
    assert result_rows[0]["dixon_decision"] == "no_outlier"
    assert result_rows[0]["mad_upper_z"] == "11.3"
    assert result_rows[0]["masking_companion_flag"] == "Yes"
