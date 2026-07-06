from __future__ import annotations

from typing import Any

from plotting.models import PlotRequest


def stress_strain_reduction_request(
    *,
    plot_id: str,
    run_id: str,
    bounded_rows: list[dict[str, Any]],
    post_peak_rows: list[dict[str, Any]] | None = None,
    block: dict[str, Any],
    surface_context: str = "audit_report",
) -> PlotRequest:
    return PlotRequest(
        plot_type="stress_strain_reduction",
        plot_id=plot_id,
        title="Stress-strain reduction evidence",
        data_payload={
            "run_id": run_id,
            "bounded_rows": bounded_rows,
            "post_peak_rows": post_peak_rows or [],
            "block": block,
        },
        evidence_refs=_evidence_refs(block),
        surface_context=surface_context,  # type: ignore[arg-type]
    )


def bending_evidence_request(
    *,
    plot_id: str,
    run_id: str,
    bounded_rows: list[dict[str, Any]],
    block: dict[str, Any],
    surface_context: str = "audit_report",
) -> PlotRequest:
    return PlotRequest(
        plot_type="bending_evidence",
        plot_id=plot_id,
        title="Bending evidence",
        data_payload={"run_id": run_id, "bounded_rows": bounded_rows, "block": block},
        evidence_refs=_evidence_refs(block),
        surface_context=surface_context,  # type: ignore[arg-type]
    )


def aggregate_curve_family_request(
    *,
    plot_id: str,
    aligned_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    fallback_curves: list[dict[str, Any]] | None = None,
    diagnostic_scores: list[dict[str, Any]] | None = None,
    plot_data_freshness: dict[str, Any] | None = None,
    highlight_run_id: str | None = None,
    block: dict[str, Any] | None = None,
    surface_context: str = "audit_report",
) -> PlotRequest:
    return PlotRequest(
        plot_type="aggregate_curve_family",
        plot_id=plot_id,
        title="Aggregate curve-family evidence",
        data_payload={
            "aligned_rows": aligned_rows,
            "reference_rows": reference_rows,
            "fallback_curves": fallback_curves or [],
            "diagnostic_scores": diagnostic_scores or [],
            "plot_data_freshness": plot_data_freshness or {},
            "highlight_run_id": highlight_run_id or "",
        },
        evidence_refs=_evidence_refs(block or {}),
        surface_context=surface_context,  # type: ignore[arg-type]
    )


def curve_shape_distance_ranking_request(
    *,
    plot_id: str,
    scores: list[dict[str, Any]],
    block: dict[str, Any] | None = None,
    surface_context: str = "audit_report",
) -> PlotRequest:
    return PlotRequest(
        plot_type="curve_shape_distance_ranking",
        plot_id=plot_id,
        title="Curve-shape distance ranking",
        data_payload={"scores": scores},
        evidence_refs=_evidence_refs(block or {}),
        surface_context=surface_context,  # type: ignore[arg-type]
    )


def curve_shape_residuals_request(
    *,
    plot_id: str,
    residuals: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    block: dict[str, Any] | None = None,
    surface_context: str = "audit_report",
) -> PlotRequest:
    return PlotRequest(
        plot_type="curve_shape_residuals",
        plot_id=plot_id,
        title="Curve residual detail",
        data_payload={"residuals": residuals, "scores": scores},
        evidence_refs=_evidence_refs(block or {}),
        surface_context=surface_context,  # type: ignore[arg-type]
    )


def _evidence_refs(block: dict[str, Any]) -> dict[str, str]:
    refs = block.get("evidence_refs") if isinstance(block.get("evidence_refs"), dict) else {}
    return {str(key): str(value) for key, value in refs.items() if value not in (None, "")}
