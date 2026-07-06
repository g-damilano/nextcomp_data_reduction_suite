from __future__ import annotations

from typing import Any

from plotting.models import PlotLayerContract, PlotRequest, PlotResult
from plotting.quality import evaluate_spec
from plotting.theme import default_theme, vega_config


SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"


def finalise_spec(
    spec: dict[str, Any],
    request: PlotRequest,
    layer_contracts: list[PlotLayerContract],
    *,
    warnings: list[str] | None = None,
) -> PlotResult:
    spec = dict(spec)
    spec.setdefault("$schema", SCHEMA)
    spec.setdefault("width", _width(request))
    spec.setdefault("height", _height(request))
    spec["config"] = {**vega_config(default_theme(request.theme_id)), **dict(spec.get("config") or {})}
    usermeta = dict(spec.get("usermeta") or {})
    usermeta.setdefault("plot_id", request.plot_id)
    usermeta.setdefault("plot_type", request.plot_type)
    usermeta.setdefault("semantic_layers", [contract.layer_id for contract in layer_contracts])
    usermeta.setdefault("layer_contracts", [contract.to_dict() for contract in layer_contracts])
    usermeta.setdefault("evidence_refs", dict(request.evidence_refs))
    spec["usermeta"] = usermeta
    quality = evaluate_spec(spec, request, layer_contracts, warnings=warnings)
    status = "degraded" if quality.warnings else "rendered"
    return PlotResult(
        plot_id=request.plot_id,
        plot_type=request.plot_type,
        status=status,
        spec=spec,
        warnings=list(quality.warnings),
        quality_report=quality,
        evidence_refs=dict(request.evidence_refs),
    )


def unavailable_result(request: PlotRequest, message: str) -> PlotResult:
    quality = evaluate_spec(None, request, [], warnings=[message])
    return PlotResult(
        plot_id=request.plot_id,
        plot_type=request.plot_type,
        status="unavailable",
        spec=None,
        warnings=[message],
        quality_report=quality,
        evidence_refs=dict(request.evidence_refs),
        fallback_message=message,
    )


def failed_result(request: PlotRequest, message: str) -> PlotResult:
    quality = evaluate_spec(None, request, [], warnings=[message])
    return PlotResult(
        plot_id=request.plot_id,
        plot_type=request.plot_type,
        status="failed",
        spec=None,
        warnings=[message],
        quality_report=quality,
        evidence_refs=dict(request.evidence_refs),
        fallback_message=message,
    )


def _width(request: PlotRequest) -> str | int:
    if request.customization and request.customization.width is not None:
        return request.customization.width
    return request.layout_policy.get("width") or "container"


def _height(request: PlotRequest) -> int:
    if request.customization and request.customization.height is not None:
        return request.customization.height
    return int(request.layout_policy.get("height") or default_theme(request.theme_id).default_height)
