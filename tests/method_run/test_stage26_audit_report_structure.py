from __future__ import annotations

import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout


AUDIT_HTML = f"{MTDAAlignedLayout.reports_prefix}audit_report.html"


def test_audit_report_is_runwise_first_then_aggregate(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    overview_pos = html.index('id="audit_overview"')
    run_index_pos = html.index('id="evidence_navigation_run_index"')
    runwise_pos = html.index('id="run_wise_evidence_packets"')
    run001_pos = html.index('id="packet-run_001"')
    aggregate_pos = html.index('id="aggregate_evidence_packet"')
    final_trace_pos = html.index('id="decision_register"')

    assert overview_pos < run_index_pos < runwise_pos < run001_pos < aggregate_pos < final_trace_pos
    assert "Artifact Links" not in html
    assert "Stress-strain reduction evidence" in html
    assert "Bending evidence" in html


def test_audit_report_keeps_stress_and_bending_as_distinct_blocks(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    stress_pos = html.index('data-block-type="run_stress_strain_reduction"')
    bending_pos = html.index('data-block-type="run_bending_evidence"', stress_pos)
    assert stress_pos < bending_pos
    stress_section = html[stress_pos:bending_pos]
    assert 'data-audit-plot="run_stress_strain_reduction"' in stress_section
    assert "Reduction results" in stress_section
    assert "bending_diagnostic" not in stress_section


def test_audit_report_uses_margin_notes_for_method_context(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, AUDIT_HTML)

    assert "GRAFTED: scrollspy nav + inline note popovers" in html
    assert 'class="audit-block aggregate_dataset_cohort_population note-anchor"' in html
    assert 'class="audit-block aggregate_curve_family visual-first note-anchor"' in html
    assert 'class="audit-block aggregate_curve_shape_diagnostics visual-first note-anchor"' in html
    assert "left: calc(100% + 18px)" not in html
    assert ".note-anchor h3:hover ~ aside.note" in html
    assert 'aria-label="Show method note"' in html
    assert '<div class="note-label">Definition</div>' in html
    assert html.count('<div class="note-label">Method &amp; Figure</div>') >= 2
    assert '<p class="audit-purpose">Comparable curve cohort used for whole-dataset curve-shape evidence.</p>' not in html
    assert '<p class="plot-caption">' not in html
    assert '<section class="methods-appendix" aria-hidden="true">' in html
    assert "A.1 Dataset / cohort population" in html
    assert "A.2 Aggregate curve-family evidence" in html
    assert "A.3 Curve-shape outlier diagnostics" in html
    assert 'href="#packet-run_001"' in html
    assert 'id="packet-run_001"' in html


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
