from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import audit.aggregate_packet_renderer as aggregate_packet_module
import audit.run_packet_renderer as run_packet_module
from audit.aggregate_packet_renderer import _legacy_render_aggregate_packet, render_aggregate_packet
from audit.run_packet_renderer import _legacy_render_run_index, _legacy_render_run_packets, render_run_index, render_run_packets
from html_renderer.context_models import (
    AuditAggregatePacketContext,
    AuditRunIndexContext,
    AuditRunPacketContext,
    AuditRunPacketsContext,
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind, projection_for
from html_renderer.render import render_audit_aggregate_packet, render_audit_run_index, render_audit_run_packets


def test_audit_run_index_jinja_matches_legacy_renderer_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_blocks = _audit_blocks()
    result = _result()

    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)
    jinja_html = render_run_index(audit_blocks, result=result)
    legacy_html = _legacy_render_run_index(audit_blocks, result=result)

    assert jinja_html == legacy_html
    assert 'id="evidence_navigation_run_index"' in jinja_html
    assert 'class="run-index-table"' in jinja_html
    assert 'href="#packet-run_001"' in jinja_html
    assert '<div class="table-wrap"><table>' in jinja_html


def test_audit_run_packet_wrappers_preserve_block_fragments_and_spec_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_blocks = _audit_blocks()
    result = _result()

    monkeypatch.setattr(run_packet_module, "render_block", _spec_seed_block_renderer)
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    jinja_specs: dict[str, dict[str, object]] = {}
    legacy_specs: dict[str, dict[str, object]] = {}
    jinja_html = render_run_packets(audit_blocks, result=result, specs=jinja_specs)
    legacy_html = _legacy_render_run_packets(audit_blocks, result=result, specs=legacy_specs)

    assert jinja_html == legacy_html
    assert jinja_specs == legacy_specs
    assert 'id="run_wise_evidence_packets"' in jinja_html
    assert 'class="run-packet" id="packet-run_001"' in jinja_html
    assert 'class="status-badge status-warn">Curve Shape Outlier</span>' in jinja_html
    assert 'data-block-type="run_technical_trace_links"' not in jinja_html
    assert jinja_html.count('class="audit-block"') == 2


def test_audit_aggregate_packet_jinja_matches_legacy_and_keeps_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_blocks = _audit_blocks()
    result = _result()
    monkeypatch.setattr(aggregate_packet_module, "render_block", _spec_seed_block_renderer)
    monkeypatch.delenv("MTDA_HTML_RENDERER", raising=False)

    jinja_specs: dict[str, dict[str, object]] = {}
    legacy_specs: dict[str, dict[str, object]] = {}
    jinja_html = render_aggregate_packet(audit_blocks, result=result, specs=jinja_specs)
    legacy_html = _legacy_render_aggregate_packet(audit_blocks, result=result, specs=legacy_specs)

    assert jinja_html == legacy_html
    assert jinja_specs == legacy_specs
    assert 'id="aggregate_evidence_packet"' in jinja_html
    assert 'data-block-type="aggregate_evidence_summary"' not in jinja_html
    assert 'data-block-type="aggregate_curve_family"' in jinja_html


def test_audit_packet_renderers_keep_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_blocks = _audit_blocks()
    result = _result()

    monkeypatch.setenv("MTDA_HTML_RENDERER", "legacy")
    assert render_run_index(audit_blocks, result=result) == _legacy_render_run_index(audit_blocks, result=result)
    assert render_run_packets(audit_blocks, result=result, specs={}) == _legacy_render_run_packets(
        audit_blocks,
        result=result,
        specs={},
    )
    assert render_aggregate_packet(audit_blocks, result=result, specs={}) == _legacy_render_aggregate_packet(
        audit_blocks,
        result=result,
        specs={},
    )


def test_audit_packet_recipe_projections_are_explicit_and_reuse_table_shape() -> None:
    run_index_projection = projection_for(RecipeResultKind.AUDIT_RUN_INDEX)
    run_packets_projection = projection_for(RecipeResultKind.AUDIT_RUN_PACKETS)
    aggregate_projection = projection_for(RecipeResultKind.AUDIT_AGGREGATE_PACKET)

    assert run_index_projection.context_model == "AuditRunIndexContext"
    assert run_index_projection.template_name == "sections/audit/run_index.html.j2"
    assert run_index_projection.projection_planes == (ProjectionPlane.AUDIT,)
    assert run_packets_projection.context_model == "AuditRunPacketsContext"
    assert aggregate_projection.context_model == "AuditAggregatePacketContext"

    table = AuditTableContext(
        table_class="",
        headers=(AuditTableCellContext(html=Markup("Run #")),),
        rows=(AuditTableRowContext(cells=(AuditTableCellContext(html=Markup('<a href="#packet-run_001">Run 1</a>')),)),),
    )
    index_html = render_audit_run_index(
        AuditRunIndexContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
            section_heading_html=Markup("<h2>Evidence Navigation / Run Evidence Index</h2>"),
            table=table,
            empty_message_html=Markup("<p></p>"),
        )
    )
    packets_html = render_audit_run_packets(
        AuditRunPacketsContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RUN_PACKETS,
            section_heading_html=Markup("<h2>Run-wise Evidence Packets</h2>"),
            packets=(
                AuditRunPacketContext(
                    run_id_html=Markup("run_001"),
                    run_label_html=Markup("Run 1"),
                    badges=(),
                    blocks_html=(Markup('<div class="audit-block"></div>'),),
                ),
            ),
        )
    )
    aggregate_html = render_audit_aggregate_packet(
        AuditAggregatePacketContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_AGGREGATE_PACKET,
            section_heading_html=Markup("<h2>Aggregate Evidence Packet</h2>"),
            blocks_html=(Markup('<div class="audit-block"></div>'),),
        )
    )

    assert '<div class="table-wrap"><table>' in index_html
    assert 'id="packet-run_001"' in packets_html
    assert 'id="aggregate_evidence_packet"' in aggregate_html


def test_audit_packet_contexts_reject_wrong_plane_kind_and_loose_fragments() -> None:
    with pytest.raises(ValueError, match="audit projection plane"):
        AuditRunIndexContext(
            projection_plane=ProjectionPlane.TEST,
            recipe_result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
            section_heading_html=Markup(""),
            table=None,
            empty_message_html=Markup("<p></p>"),
        )

    with pytest.raises(ValueError, match="audit_run_index"):
        AuditRunIndexContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_EVIDENCE_REPORT,
            section_heading_html=Markup(""),
            table=None,
            empty_message_html=Markup("<p></p>"),
        )

    with pytest.raises(ValueError, match="section_heading_html must be an HTML-safe Markup fragment"):
        AuditRunIndexContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
            section_heading_html="<h2>Evidence Navigation / Run Evidence Index</h2>",
            table=None,
            empty_message_html=Markup("<p></p>"),
        )

    with pytest.raises(ValueError, match="empty_message_html must be an HTML-safe Markup fragment"):
        AuditRunIndexContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
            section_heading_html=Markup(""),
            table=None,
            empty_message_html="<p></p>",
        )

    with pytest.raises(ValueError, match="run_id_html must be an HTML-safe Markup fragment"):
        AuditRunPacketContext(
            run_id_html="run_001",
            run_label_html=Markup("Run 1"),
            badges=(),
            blocks_html=(),
        )

    with pytest.raises(ValueError, match="blocks_html must be an HTML-safe Markup fragment"):
        AuditAggregatePacketContext(
            projection_plane=ProjectionPlane.AUDIT,
            recipe_result_kind=RecipeResultKind.AUDIT_AGGREGATE_PACKET,
            section_heading_html=Markup(""),
            blocks_html=("<div></div>",),
        )


def _audit_blocks() -> dict[str, object]:
    return {
        "run_packets": [
            {
                "run_id": "run_001",
                "blocks": [
                    {
                        "block_id": "run_001_identity",
                        "block_type": "run_identity_and_status",
                        "title": "Identity",
                        "summary": {"specimen_name": "Specimen A", "sample_id": "Panel A"},
                    },
                    {
                        "block_id": "run_001_curve",
                        "block_type": "run_curve_shape_diagnostic",
                        "title": "Curve shape",
                        "summary": {"curve_shape_classification": "CURVE_SHAPE_OUTLIER"},
                    },
                    {
                        "block_id": "run_001_trace",
                        "block_type": "run_technical_trace_links",
                        "title": "Trace links",
                    },
                ],
            }
        ],
        "aggregate_packet": {
            "blocks": [
                {
                    "block_id": "aggregate_summary",
                    "block_type": "aggregate_evidence_summary",
                    "title": "Aggregate summary",
                },
                {
                    "block_id": "aggregate_curve",
                    "block_type": "aggregate_curve_family",
                    "title": "Aggregate curve family",
                },
            ],
        },
    }


def _result() -> SimpleNamespace:
    return SimpleNamespace(run_flags=[])


def _spec_seed_block_renderer(
    block: dict[str, object],
    *,
    result: object = None,
    specs: dict[str, dict[str, object]] | None = None,
    force_open: bool = False,
    note_collector: object = None,
) -> str:
    block_id = str(block.get("block_id") or "audit-block")
    block_type = str(block.get("block_type") or "audit-block")
    if specs is not None:
        specs[block_id] = {"block_type": block_type, "force_open": force_open}
    return f'<div class="audit-block" id="{block_id}" data-block-type="{block_type}"></div>'
