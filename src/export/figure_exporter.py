from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from archives.core.layouts import aggregate_member
from export.artifact_collector import MTDAArtifactCollector
from export.renderers.vega_static_renderer import aggregate_stress_strain_spec, vega_html


class FigureExporter:
    def export(self, collector: MTDAArtifactCollector, *, profile: str) -> dict[str, bytes]:
        rows = collector.first_csv_rows(aggregate_member("stress_strain_aligned.csv"), "report/aligned_curves.csv")
        if not rows:
            return {}
        spec = aggregate_stress_strain_spec(rows)
        files = {
            "figures/aggregate_stress_strain.html": vega_html(spec, title="Aggregate Stress-Strain"),
            "figures/aggregate_stress_strain_vega.json": json.dumps(spec, indent=2, sort_keys=True).encode("utf-8"),
        }
        dataset_plot_spec = _hydrated_dataset_plot_spec(collector)
        if dataset_plot_spec:
            files["figures/dataset_plot.full_vegalite_spec_with_data.vl.json"] = json.dumps(
                dataset_plot_spec,
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
        return files


def _hydrated_dataset_plot_spec(collector: MTDAArtifactCollector) -> dict[str, Any]:
    package_member = aggregate_member("dataset_plot.plot_package.json")
    package = collector.json(package_member)
    if package:
        template_member = str(package.get("template_member") or "")
        if not template_member:
            template_member = _resolve_relative_member(package_member, str(package.get("template_path") or ""))
        template = collector.json(template_member)
        datasets = {
            str(dataset.get("dataset_id")): collector.csv_rows(
                str(dataset.get("member") or _resolve_relative_member(package_member, str(dataset.get("path") or "")))
            )
            for dataset in package.get("datasets", [])
            if isinstance(dataset, dict) and dataset.get("dataset_id")
        }
        return _hydrate_compact_template(template, datasets)

    legacy = collector.first_json(aggregate_member("dataset_plot.vl.json"), "report/aggregate_plot_spec.json")
    return legacy


def _hydrate_compact_template(value: Any, datasets: dict[str, list[dict[str, str]]]) -> Any:
    if isinstance(value, dict):
        ref = value.get("__compact_dataset_ref__")
        if ref:
            return {"values": datasets.get(str(ref), [])}
        return {key: _hydrate_compact_template(item, datasets) for key, item in value.items()}
    if isinstance(value, list):
        return [_hydrate_compact_template(item, datasets) for item in value]
    return value


def _resolve_relative_member(base_member: str, relative: str) -> str:
    if not relative:
        return ""
    if relative.startswith(("dataset/", "metadata/", "report/", "audit/")):
        return relative
    base = PurePosixPath(base_member).parent
    parts: list[str] = []
    for part in (base / relative).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)
