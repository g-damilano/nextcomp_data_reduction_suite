from __future__ import annotations

from typing import Any

from plotting.labels import is_raw_internal_label
from plotting.models import PlotLayerContract, PlotQualityReport, PlotRequest


def evaluate_spec(
    spec: dict[str, Any] | None,
    request: PlotRequest,
    layer_contracts: list[PlotLayerContract],
    *,
    warnings: list[str] | None = None,
) -> PlotQualityReport:
    warnings = list(warnings or [])
    if not spec:
        return PlotQualityReport(
            has_data=False,
            has_required_layers=False,
            axis_labels_present=False,
            units_present=False,
            tooltip_present=False,
            legend_state="missing",
            clipping_state="not_applicable",
            warnings=warnings or ["plot specification is missing"],
        )

    layer_names = set(_layer_names(spec))
    required = {contract.layer_id for contract in layer_contracts if contract.required}
    missing_required = sorted(required - layer_names)
    if missing_required:
        warnings.append("missing required semantic layers: " + ", ".join(missing_required))

    titles = _visible_titles(spec)
    raw_titles = [title for title in titles if is_raw_internal_label(title)]
    if raw_titles:
        warnings.append("raw internal field names in visible titles: " + ", ".join(sorted(set(raw_titles))))

    axis_labels_present = _axis_titles_present(spec)
    tooltip_present = _tooltip_present(spec)
    has_data = bool(_data_values(spec))
    legend_state = "present" if _legend_titles(spec) else "not_required"
    units_present = _units_present(spec)
    clipping_state = "clipped" if _marks_are_clipped(spec) else "not_declared"
    visible_label_suppression = [
        warning for warning in warnings if "visible annotation labels suppressed" in warning
    ]
    return PlotQualityReport(
        has_data=has_data,
        has_required_layers=not missing_required,
        axis_labels_present=axis_labels_present,
        units_present=units_present,
        tooltip_present=tooltip_present,
        legend_state=legend_state,
        clipping_state=clipping_state,
        annotation_conflicts=[],
        visible_label_suppression=visible_label_suppression,
        warnings=warnings,
    )


def _layers(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(spec.get("layer"), list):
        return [layer for layer in spec["layer"] if isinstance(layer, dict)]
    if isinstance(spec.get("hconcat"), list):
        layers: list[dict[str, Any]] = []
        for item in spec["hconcat"]:
            if isinstance(item, dict):
                layers.extend(_layers(item))
        return layers
    return [spec]


def _layer_names(spec: dict[str, Any]) -> list[str]:
    semantic = spec.get("usermeta", {}).get("semantic_layers") if isinstance(spec.get("usermeta"), dict) else None
    names = [str(item) for item in semantic] if isinstance(semantic, list) else []
    names.extend(str(layer.get("name")) for layer in _layers(spec) if layer.get("name"))
    return names


def _data_values(spec: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    data = spec.get("data")
    if isinstance(data, dict) and isinstance(data.get("values"), list):
        values.extend(row for row in data["values"] if isinstance(row, dict))
    for layer in _layers(spec):
        layer_data = layer.get("data")
        if isinstance(layer_data, dict) and isinstance(layer_data.get("values"), list):
            values.extend(row for row in layer_data["values"] if isinstance(row, dict))
    datasets = spec.get("datasets")
    if isinstance(datasets, dict):
        for rows in datasets.values():
            if isinstance(rows, list):
                values.extend(row for row in rows if isinstance(row, dict))
    return values


def _visible_titles(spec: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for layer in _layers(spec):
        encoding = layer.get("encoding") if isinstance(layer.get("encoding"), dict) else {}
        for channel in ("x", "y", "color", "shape"):
            value = encoding.get(channel)
            if isinstance(value, dict) and value.get("title"):
                titles.append(str(value["title"]))
    return titles


def _axis_titles_present(spec: dict[str, Any]) -> bool:
    axes: list[str] = []
    for layer in _layers(spec):
        encoding = layer.get("encoding") if isinstance(layer.get("encoding"), dict) else {}
        for channel in ("x", "y"):
            value = encoding.get(channel)
            if isinstance(value, dict) and value.get("title"):
                axes.append(channel)
    return "x" in axes and "y" in axes


def _tooltip_present(spec: dict[str, Any]) -> bool:
    for layer in _layers(spec):
        encoding = layer.get("encoding") if isinstance(layer.get("encoding"), dict) else {}
        if "tooltip" in encoding:
            return True
    return False


def _legend_titles(spec: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for layer in _layers(spec):
        encoding = layer.get("encoding") if isinstance(layer.get("encoding"), dict) else {}
        for channel in ("color", "shape"):
            value = encoding.get(channel)
            if isinstance(value, dict) and value.get("title"):
                titles.append(str(value["title"]))
    return titles


def _units_present(spec: dict[str, Any]) -> bool:
    titles = _visible_titles(spec)
    unit_titles = [title for title in titles if "/" in title or "%" in title or "z(x)" in title or "distance" in title]
    return bool(unit_titles)


def _marks_are_clipped(spec: dict[str, Any]) -> bool:
    for layer in _layers(spec):
        mark = layer.get("mark")
        if isinstance(mark, dict) and mark.get("clip"):
            return True
    return False
