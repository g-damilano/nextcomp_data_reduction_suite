from __future__ import annotations

import html
import os
from typing import Any

from audit.audit_block_renderers import render_block
from html_renderer.context_models import (
    AuditBadgeContext,
    AuditRunIndexContext,
    AuditRunPacketContext,
    AuditRunPacketsContext,
    AuditTableCellContext,
    AuditTableContext,
    AuditTableRowContext,
)
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import (
    render_audit_run_index,
    render_audit_run_packets,
    render_report_empty_paragraph,
    render_report_heading_fragment,
)
from markupsafe import Markup
from reporting.run_labels import run_display_label


def render_run_index(audit_blocks: dict[str, Any], *, result: Any = None) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_render_run_index(audit_blocks, result=result)
    return render_audit_run_index(_audit_run_index_context(audit_blocks, result=result))


def _legacy_render_run_index(audit_blocks: dict[str, Any], *, result: Any = None) -> str:
    rows = _run_index_rows(audit_blocks, result=result)
    return (
        "<section id=\"evidence_navigation_run_index\">"
        "<h2>Evidence Navigation / Run Evidence Index</h2>"
        f"<div class=\"run-index-table\">{_legacy_render_run_index_table(rows)}</div>"
        "</section>"
    )


def _audit_run_index_context(audit_blocks: dict[str, Any], *, result: Any = None) -> AuditRunIndexContext:
    rows = _run_index_rows(audit_blocks, result=result)
    return AuditRunIndexContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_RUN_INDEX,
        section_heading_html=_audit_heading("Evidence Navigation / Run Evidence Index", heading_level=2),
        table=_audit_run_index_table_context(rows),
        empty_message_html=Markup(
            render_report_empty_paragraph(
                projection_plane=ProjectionPlane.AUDIT,
                message_html=Markup("No runs recorded."),
            )
        ),
    )


def _run_index_rows(audit_blocks: dict[str, Any], *, result: Any = None) -> list[dict[str, Any]]:
    packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    rows = []
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        run_id = str(packet.get("run_id") or "")
        blocks = [block for block in packet.get("blocks", []) if isinstance(block, dict)]
        identity = _block(blocks, "run_identity_and_status")
        bending = _block(blocks, "run_bending_evidence")
        curve_shape = _block(blocks, "run_curve_shape_diagnostic")
        validation = _block(blocks, "run_validation_evidence")
        stress = _block(blocks, "run_stress_strain_reduction")
        identity_summary = identity.get("summary") if isinstance(identity.get("summary"), dict) else {}
        bending_summary = bending.get("summary") if isinstance(bending.get("summary"), dict) else {}
        curve_shape_summary = curve_shape.get("summary") if isinstance(curve_shape.get("summary"), dict) else {}
        validation_summary = validation.get("summary") if isinstance(validation.get("summary"), dict) else {}
        flags = _flags_for_run(result, run_id)
        alerts = _evidence_alerts(bending_summary, curve_shape_summary, validation_summary, flags)
        rows.append(
            {
                "run_id": f'<a href="#packet-{html.escape(run_id)}">{html.escape(run_display_label(run_id))}</a>',
                "specimen_name": identity_summary.get("specimen_name", ""),
                "source_identity": identity_summary.get("sample_id", ""),
                "stress_strain_evidence": _stress_state(stress),
                "bending_evidence": _bending_state(bending_summary),
                "curve_shape_evidence": _curve_shape_state(curve_shape_summary),
                "validation": _validation_state(validation_summary),
                "evidence_alerts": ", ".join(alerts),
            }
        )
    return rows


def render_run_packets(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
) -> str:
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() == "legacy":
        return _legacy_render_run_packets(audit_blocks, result=result, specs=specs)
    return render_audit_run_packets(_audit_run_packets_context(audit_blocks, result=result, specs=specs))


def _legacy_render_run_packets(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
) -> str:
    packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    parts = [
        "<section id=\"run_wise_evidence_packets\"><h2>Run-wise Evidence Packets</h2>"
    ]
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        run_id_raw = str(packet.get("run_id") or "run")
        run_id = html.escape(run_id_raw)
        blocks = [block for block in packet.get("blocks", []) if isinstance(block, dict)]
        badges = _packet_badges(blocks, result=result, run_id=run_id_raw)
        badge_text = " ".join(
            f"<span class=\"status-badge status-{_badge_status(badge)}\">{html.escape(badge)}</span>"
            for badge in badges
        )
        parts.append(
            f"<article class=\"run-packet\" id=\"packet-{run_id}\">"
            "<header>"
            f"<div><div class=\"packet-label\">Run-wise evidence packet</div><h3>{html.escape(run_display_label(run_id_raw))}</h3></div>"
            f"<div>{badge_text}</div>"
            "</header>"
            "<div class=\"run-packet-body\">"
        )
        for block in blocks:
            if isinstance(block, dict):
                block_type = str(block.get("block_type") or "")
                if block_type == "run_technical_trace_links":
                    continue
                if block_type == "run_validation_evidence" and not _validation_has_problem(block):
                    continue
                parts.append(render_block(block, result=result, specs=specs, force_open=True))
        parts.append("</div></article>")
    parts.append("</section>")
    return "".join(parts)


def _audit_run_packets_context(
    audit_blocks: dict[str, Any],
    *,
    result: Any = None,
    specs: dict[str, dict[str, Any]] | None = None,
) -> AuditRunPacketsContext:
    packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    packet_contexts: list[AuditRunPacketContext] = []
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        run_id_raw = str(packet.get("run_id") or "run")
        blocks = [block for block in packet.get("blocks", []) if isinstance(block, dict)]
        badges = tuple(
            AuditBadgeContext(
                status_class=_badge_status(badge),
                label_html=Markup(html.escape(badge)),
            )
            for badge in _packet_badges(blocks, result=result, run_id=run_id_raw)
        )
        block_fragments = []
        for block in blocks:
            block_type = str(block.get("block_type") or "")
            if block_type == "run_technical_trace_links":
                continue
            if block_type == "run_validation_evidence" and not _validation_has_problem(block):
                continue
            block_fragments.append(Markup(render_block(block, result=result, specs=specs, force_open=True)))
        packet_contexts.append(
            AuditRunPacketContext(
                run_id_html=Markup(html.escape(run_id_raw)),
                run_label_html=Markup(html.escape(run_display_label(run_id_raw))),
                badges=badges,
                blocks_html=tuple(block_fragments),
            )
        )
    return AuditRunPacketsContext(
        projection_plane=ProjectionPlane.AUDIT,
        recipe_result_kind=RecipeResultKind.AUDIT_RUN_PACKETS,
        section_heading_html=_audit_heading("Run-wise Evidence Packets", heading_level=2),
        packets=tuple(packet_contexts),
    )


def _audit_heading(title: str, *, heading_level: int) -> Markup:
    return Markup(
        render_report_heading_fragment(
            projection_plane=ProjectionPlane.AUDIT,
            title_html=Markup(html.escape(title)),
            heading_level=heading_level,
        )
    )


def _block(blocks: list[dict[str, Any]], block_type: str) -> dict[str, Any]:
    for block in blocks:
        if block.get("block_type") == block_type:
            return block
    return {}


def _table_rows(block: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    tables = block.get("tables") if isinstance(block.get("tables"), dict) else {}
    rows = tables.get(table_name, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _validation_state(summary: dict[str, Any]) -> str:
    failed = int(summary.get("failed") or 0)
    warnings = int(summary.get("warnings") or 0)
    if failed:
        return "Failed"
    if warnings:
        return "Warning"
    return "No deviations"


def _validation_has_problem(block: dict[str, Any]) -> bool:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    if int(summary.get("failed") or 0) or int(summary.get("warnings") or 0):
        return True
    for row in _table_rows(block, "details"):
        if str(row.get("status") or "").casefold() in {"warn", "warning", "fail", "failed"}:
            return True
    return False


def _packet_has_problem(blocks: list[dict[str, Any]], *, result: Any = None, run_id: str = "") -> bool:
    bending = _block(blocks, "run_bending_evidence")
    bending_summary = bending.get("summary") if isinstance(bending.get("summary"), dict) else {}
    bending_classification = str(bending_summary.get("classification") or "").strip()
    if bending_classification and bending_classification != "PASS":
        return True
    curve_shape = _block(blocks, "run_curve_shape_diagnostic")
    curve_summary = curve_shape.get("summary") if isinstance(curve_shape.get("summary"), dict) else {}
    curve_classification = str(curve_summary.get("curve_shape_classification") or "").strip()
    if curve_classification and curve_classification not in {"CURVE_SHAPE_NORMAL"}:
        return True
    validation = _block(blocks, "run_validation_evidence")
    validation_summary = validation.get("summary") if isinstance(validation.get("summary"), dict) else {}
    if int(validation_summary.get("failed") or 0) or int(validation_summary.get("warnings") or 0):
        return True
    if _flags_for_run(result, run_id):
        return True
    return False


def _render_run_index_table(rows: list[dict[str, Any]]) -> str:
    return _legacy_render_run_index_table(rows)


def _legacy_render_run_index_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class=\"muted\">No runs recorded.</p>"
    fields = [
        "run_id",
        "specimen_name",
        "source_identity",
        "stress_strain_evidence",
        "bending_evidence",
        "curve_shape_evidence",
        "validation",
        "evidence_alerts",
    ]
    headers = "".join(f"<th>{html.escape(_header_label(field))}</th>" for field in fields)
    body_rows = []
    for row in rows:
        cells = []
        for field in fields:
            value = str(row.get(field) or "")
            if field == "run_id":
                cells.append(f"<td>{value}</td>")
            else:
                cells.append(f"<td>{html.escape(value)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<div class=\"table-wrap\"><table><thead><tr>{headers}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def _audit_run_index_table_context(rows: list[dict[str, Any]]) -> AuditTableContext | None:
    if not rows:
        return None
    fields = [
        "run_id",
        "specimen_name",
        "source_identity",
        "stress_strain_evidence",
        "bending_evidence",
        "curve_shape_evidence",
        "validation",
        "evidence_alerts",
    ]
    headers = tuple(
        AuditTableCellContext(html=Markup(html.escape(_header_label(field))))
        for field in fields
    )
    row_contexts: list[AuditTableRowContext] = []
    for row in rows:
        cells = []
        for field in fields:
            value = str(row.get(field) or "")
            cell_html = Markup(value) if field == "run_id" else Markup(html.escape(value))
            cells.append(AuditTableCellContext(html=cell_html))
        row_contexts.append(AuditTableRowContext(cells=tuple(cells)))
    return AuditTableContext(table_class="", headers=headers, rows=tuple(row_contexts))


def _header_label(field: str) -> str:
    labels = {
        "run_id": "Run #",
        "specimen_name": "Specimen",
        "source_identity": "Source identity",
        "stress_strain_evidence": "Stress-strain evidence",
        "bending_evidence": "Bending evidence",
        "curve_shape_evidence": "Curve-shape evidence",
        "validation": "Validation",
        "evidence_alerts": "Evidence alerts",
    }
    return labels.get(field, field.replace("_", " ").title())


def _stress_state(block: dict[str, Any]) -> str:
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    return "Available" if summary.get("bounded_reduction") not in (None, "", False) else "Not available"


def _bending_state(summary: dict[str, Any]) -> str:
    classification = str(summary.get("classification") or "").strip()
    labels = {
        "PASS": "Within limit",
        "PASS_WITH_SPIKES": "Within limit with short spikes",
        "WARN_TRANSIENT_BENDING": "Transient bending above limit",
        "FAIL_SUSTAINED_BENDING": "Sustained bending above limit",
    }
    return labels.get(classification, "Not assessed" if not classification else classification.replace("_", " ").title())


def _curve_shape_state(summary: dict[str, Any]) -> str:
    classification = str(summary.get("curve_shape_classification") or "").strip()
    labels = {
        "CURVE_SHAPE_NORMAL": "Matches cohort",
        "CURVE_SHAPE_OUTLIER": "Curve-shape outlier",
        "INSUFFICIENT_CURVE_DATA": "Insufficient curve data",
        "INSUFFICIENT_COHORT_SIZE": "Insufficient cohort size",
        "CURVE_SHAPE_NOT_ASSESSED": "Not assessed",
    }
    return labels.get(classification, "Curve-shape evidence unavailable" if not classification else classification.replace("_", " ").title())


def _flags_for_run(result: Any, run_id: str) -> list[dict[str, Any]]:
    return [
        row for row in getattr(result, "run_flags", None) or []
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id
    ]


def _evidence_alerts(
    bending: dict[str, Any],
    curve_shape: dict[str, Any],
    validation: dict[str, Any],
    flags: list[dict[str, Any]],
) -> list[str]:
    alerts = []
    bending_classification = str(bending.get("classification") or "").strip()
    if bending_classification and bending_classification != "PASS":
        alerts.append("Bending above limit")
    curve_classification = str(curve_shape.get("curve_shape_classification") or "").strip()
    if curve_classification and curve_classification != "CURVE_SHAPE_NORMAL":
        alerts.append(curve_classification.replace("_", " ").title())
    if int(validation.get("failed") or 0) or int(validation.get("warnings") or 0):
        alerts.append("Validation warning")
    return alerts


def _packet_badges(blocks: list[dict[str, Any]], *, result: Any, run_id: str) -> list[str]:
    bending = _block(blocks, "run_bending_evidence")
    curve_shape = _block(blocks, "run_curve_shape_diagnostic")
    validation = _block(blocks, "run_validation_evidence")
    return _evidence_alerts(
        bending.get("summary") if isinstance(bending.get("summary"), dict) else {},
        curve_shape.get("summary") if isinstance(curve_shape.get("summary"), dict) else {},
        validation.get("summary") if isinstance(validation.get("summary"), dict) else {},
        _flags_for_run(result, run_id),
    )


def _badge_status(label: str) -> str:
    text = label.casefold()
    if any(token in text for token in ("warning", "limit", "outlier", "insufficient", "above", "review")):
        return "warn"
    return "pass"
