from __future__ import annotations

import os
from typing import Any

from audit.audit_block_renderers import render_block
from html_renderer.context_models import AuditAggregatePacketContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_audit_aggregate_packet, render_report_heading_fragment
from markupsafe import Markup
from reporting.renderers.formatting_standard import ReportNoteCollector


def render_aggregate_packet(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_render_aggregate_packet(
            audit_blocks,
            result=result,
            specs=specs,
            note_collector=note_collector,
        )
    return render_audit_aggregate_packet(
        _audit_aggregate_packet_context(
            audit_blocks,
            result=result,
            specs=specs,
            note_collector=note_collector,
        )
    )


def _legacy_render_aggregate_packet(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
    note_collector: ReportNoteCollector | None = None,
) -> str:
    packet = audit_blocks.get("aggregate_packet", {}) if isinstance(audit_blocks.get("aggregate_packet"), dict) else {}
    parts = [
        "<section id=\"aggregate_evidence_packet\"><h2>Aggregate Evidence Packet</h2>"
    ]
    for block in packet.get("blocks", []) or []:
        if isinstance(block, dict):
            if str(block.get("block_type") or "") == "aggregate_evidence_summary":
                continue
            parts.append(render_block(block, result=result, specs=specs, force_open=True, note_collector=note_collector))
    parts.append("</section>")
    return "".join(parts)


def _audit_aggregate_packet_context(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
    note_collector: ReportNoteCollector | None = None,
) -> AuditAggregatePacketContext:
    packet = audit_blocks.get("aggregate_packet", {}) if isinstance(audit_blocks.get("aggregate_packet"), dict) else {}
    blocks_html = []
    for block in packet.get("blocks", []) or []:
        if isinstance(block, dict):
            if str(block.get("block_type") or "") == "aggregate_evidence_summary":
                continue
            blocks_html.append(
                Markup(render_block(block, result=result, specs=specs, force_open=True, note_collector=note_collector))
            )
    return AuditAggregatePacketContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_AGGREGATE_PACKET,
        section_heading_html=Markup(
            render_report_heading_fragment(
                projection_plane=ProjectionPlane.AUDIT,
                title_html=Markup("Aggregate Evidence Packet"),
                heading_level=2,
            )
        ),
        blocks_html=tuple(blocks_html),
    )
