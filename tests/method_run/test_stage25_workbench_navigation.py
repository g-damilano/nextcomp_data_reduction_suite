from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.layouts import MTDAAlignedLayout

INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_finalized_mtda_workbench_has_contextual_evidence_routes(tmp_path: Path) -> None:
    from methods.core.method_run_service import MethodRunRequest, MethodRunService
    from mtda_finalization import AmendmentRequest, MTDAFinalizationService

    base_mtda = tmp_path / "canonical.mtda"
    finalized_mtda = tmp_path / "canonical_finalized.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=base_mtda,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"

    request = AmendmentRequest.from_payload(
        {
            "report_overrides": [
                {
                    "field_key": "loading_method",
                    "value": "Compression between calibrated platens",
                    "reason": "Workbench evidence routing regression coverage",
                    "reviewer": "operator",
                    "source_surface": "method_run_wizard.report_completion_editor",
                    "section": "loading_fixture",
                }
            ],
            "reviewer": "operator",
            "reason": "Workbench evidence routing regression coverage",
            "reviewer_notes": ["Ensure finalized workbench links can route to amendments."],
            "source_surface": "method_run_wizard.finalization_dialog",
        }
    )
    finalization = MTDAFinalizationService().finalize(
        input_path=base_mtda,
        request=request,
        output_path=finalized_mtda,
    )
    assert finalization.status == "finalized"

    with zipfile.ZipFile(finalized_mtda) as archive:
        names = set(archive.namelist())
        method_outputs = json.loads(archive.read(MTDAAlignedLayout.method_outputs))
        test_report_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}test_report.html").decode("utf-8")
        audit_report_html = archive.read(f"{MTDAAlignedLayout.reports_prefix}audit_report.html").decode("utf-8")

    assert MTDAAlignedLayout.method_outputs in names
    assert f"{MTDAAlignedLayout.reports_prefix}test_report.html" in names
    assert f"{MTDAAlignedLayout.reports_prefix}audit_report.html" in names
    assert not any(name.startswith(("workbench/", "report/", "audit/", "acceptance/")) for name in names)
    trace = method_outputs["operation_trace"]
    assert trace["operations"]

    assert trace["report_completion"]["required_missing_count"] == 2
    assert trace["report_completion"]["recommended_missing_count"] >= 1
    assert trace["report_override_ledger"]["records"][0]["field_key"] == "loading_method"
    assert trace["finalization"]["archive_state"]["archive_state"] == "finalized"

    assert "../workbench/index.html#tab=evidence&context=report" not in test_report_html
    assert "Related report surfaces" not in test_report_html
    assert _contains_href(audit_report_html, "test_report.html")
    assert "#tab=validation&context=validation" not in audit_report_html
    assert "#tab=acceptance&context=acceptance" not in audit_report_html
    assert "#tab=evidence&context=amendments&field=loading_method" not in audit_report_html


def _contains_href(html: str, target: str) -> bool:
    return target in html or target.replace("&", "&amp;") in html
