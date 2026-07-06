from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import shutil
import subprocess
import sys
import threading
import zipfile
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
DEFAULT_METHOD = ROOT / "src" / "methods" / "iso14126"
DEFAULT_MAPPING = ROOT / "mappings" / "iso14126_manual.json"
DEFAULT_HANDOFF = ROOT / "docs" / "design_handoff_dataset_plot_studio"
DEFAULT_RUNNER = ROOT / "tools" / "run_method_manual.py"


@dataclass(frozen=True)
class StudioState:
    state_id: str
    label: str
    actions: tuple[tuple[str, str], ...]
    required_text: tuple[str, ...]


STATES: tuple[StudioState, ...] = (
    StudioState(
        "01-stress-strain-style",
        "Stress-strain style view",
        (),
        ("Stress-strain", "Style", "Titles", "Axis", "Legend"),
    ),
    StudioState(
        "02-layers-panel",
        "Layers panel",
        (("click_text", "Layers"),),
        ("Layers", "Show all", "Hide context"),
    ),
    StudioState(
        "03-data-spec-panel",
        "Data and spec panel",
        (("click_text", "Data & spec"),),
        ("Data", "Spec", "Open data", "Open spec"),
    ),
    StudioState(
        "04-bending-candle",
        "Bending candle",
        (("click_text", "Bending candle"),),
        ("Bending candle", "Bending", "Run"),
    ),
    StudioState(
        "05-export-menu",
        "Export menu",
        (("click_text", "Export"),),
        ("Style profile", "Dataset CSV", "Figure SVG", "Figure PNG", "Vega-Lite spec", "Compact plot package"),
    ),
    StudioState(
        "06-data-sheet",
        "Data sheet overlay",
        (("click_text", "Data & spec"), ("click_text", "Open data table")),
        ("Data data only", "Dataset", "Download CSV"),
    ),
    StudioState(
        "07-spec-editor",
        "Spec editor overlay",
        (("click_text", "Data & spec"), ("click_text", "Open spec editor")),
        ("Vega-Lite spec", "Validate", "Apply spec", "Regenerate"),
    ),
)


VISUAL_REGION_NAMES: tuple[str, ...] = (
    "shell",
    "top_bar",
    "chart_canvas",
    "inspector",
    "overlay",
    "export_menu",
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


class SourceDomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[dict[str, Any]] = []
        self.stack: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._push(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._push(tag, attrs, self_closing=True)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            element_index = self.stack[index]
            if self.elements[element_index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and self.stack:
            current = self.elements[self.stack[-1]]
            current["text"] = " ".join([current.get("text", ""), text]).strip()

    def _push(self, tag: str, attrs: list[tuple[str, str | None]], *, self_closing: bool) -> None:
        attr_map = {name: value if value is not None else "" for name, value in attrs}
        classes = [item for item in attr_map.get("class", "").split() if item]
        path = self._path(tag)
        element = {
            "index": len(self.elements),
            "depth": len(self.stack),
            "path": path,
            "tag": tag,
            "id": attr_map.get("id", ""),
            "classes": classes,
            "role": attr_map.get("role", ""),
            "type": attr_map.get("type", ""),
            "href": attr_map.get("href", ""),
            "aria_label": attr_map.get("aria-label", ""),
            "placeholder": attr_map.get("placeholder", ""),
            "style": attr_map.get("style", ""),
            "attrs": attr_map,
            "text": "",
        }
        self.elements.append(element)
        if not self_closing and tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(element["index"])

    def _path(self, tag: str) -> str:
        parts = [self.elements[index]["tag"] for index in self.stack]
        parts.append(tag)
        return "/" + "/".join(parts) + f"[{len(self.elements)}]"


@contextlib.contextmanager
def serve_directory(path: Path):
    class Handler(QuietHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(path), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture MTDA Dataset Plot Studio alignment artifacts.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "mtda_plot_studio_alignment")
    parser.add_argument("--mtda", type=Path, default=None, help="Use an existing MTDA archive instead of generating one.")
    parser.add_argument(
        "--production-source",
        choices=("handoff-data", "generated-mtda"),
        default="handoff-data",
        help="Production capture source. Use handoff-data for golden parity steering; generated-mtda checks archive integration.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--method", type=Path, default=DEFAULT_METHOD)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--viewport", default="1440x900", help="Viewport as WIDTHxHEIGHT.")
    parser.add_argument("--skip-golden", action="store_true", help="Capture production only.")
    parser.add_argument("--strict-visual", action="store_true", help="Fail on any golden/production screenshot pixel delta.")
    parser.add_argument("--keep-extracted", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    width, height = parse_viewport(args.viewport)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    mtda = args.mtda.resolve() if args.mtda else production_mtda(args, out)
    production_root = out / "production_archive"
    if production_root.exists() and not args.keep_extracted:
        shutil.rmtree(production_root)
    production_root.mkdir(parents=True, exist_ok=True)
    extract_mtda(mtda, production_root)

    report: dict[str, Any] = {
        "job": "RJ-20260616-D4A1B7",
        "viewport": {"width": width, "height": height},
        "mtda": str(mtda),
        "production_source": args.production_source,
        "production_entry": "dataset/03_aggregate/dataset_plot.html",
        "golden_entry": "MTDA Dataset.dc.html",
        "states": [],
        "residuals": [],
    }
    report["residuals"].extend(
        source_dom_residuals(
            "source",
            production_root / "dataset" / "03_aggregate" / "dataset_plot.html",
            args.handoff.resolve() / "MTDA Dataset.dc.html",
            diagnostics_dir=out / "source_dom_diagnostics",
        )
    )

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - exercised manually when dependency missing
        report["residuals"].append({"category": "tooling", "detail": f"Playwright import failed: {exc}"})
        write_report(out, report)
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            with serve_directory(production_root) as prod_base:
                prod_url = f"{prod_base}/dataset/03_aggregate/dataset_plot.html"
                prod_results = capture_states(
                    browser,
                    prod_url,
                    out / "production",
                    width=width,
                    height=height,
                    state_prefix="production",
                )
            golden_results: list[dict[str, Any]] = []
            if not args.skip_golden:
                with serve_directory(args.handoff.resolve()) as golden_base:
                    golden_url = f"{golden_base}/MTDA%20Dataset.dc.html"
                    golden_results = capture_states(
                        browser,
                        golden_url,
                        out / "golden",
                        width=width,
                        height=height,
                        state_prefix="golden",
                    )
            report["states"] = merge_state_results(prod_results, golden_results)
            report["residuals"].extend(
                build_residuals(
                    report["states"],
                    strict_visual=args.strict_visual,
                    diagnostics_dir=out / "visual_diagnostics",
                )
            )
        finally:
            browser.close()

    write_report(out, report)
    print(out / "alignment_report.md")
    return 0 if not report["residuals"] else 1


def parse_viewport(raw: str) -> tuple[int, int]:
    try:
        width, height = raw.lower().split("x", 1)
        return int(width), int(height)
    except Exception as exc:
        raise SystemExit(f"Invalid viewport {raw!r}; expected WIDTHxHEIGHT") from exc


def generate_mtda(args: argparse.Namespace, out: Path) -> Path:
    mtda = out / "alignment_fixture.mtda"
    cmd = [
        sys.executable,
        str(DEFAULT_RUNNER),
        "--input",
        str(args.input),
        "--method",
        str(args.method),
        "--mapping",
        str(args.mapping),
        "--output",
        str(mtda),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True, text=True, capture_output=True)
    return mtda


def production_mtda(args: argparse.Namespace, out: Path) -> Path:
    if args.production_source == "generated-mtda":
        return generate_mtda(args, out)
    return build_handoff_data_mtda(args.handoff.resolve(), out)


def build_handoff_data_mtda(handoff: Path, out: Path) -> Path:
    data_dir = handoff / "data"
    archive_data = load_handoff_js_assignment(data_dir / "archive_data.js", "MTDA_DATA")
    bending_dist = load_handoff_js_assignment(data_dir / "bending_dist.js", "MTDA_BENDING_DIST")
    datasets = handoff_plot_datasets(archive_data, bending_dist)
    dataset_name = str((archive_data.get("meta") or {}).get("datasetName") or "8552-IM7")
    run_count = len(archive_data.get("runs") or [])
    title = f"Dataset report · {dataset_name} · aggregate of {run_count} runs"
    aggregate_dir = "dataset/03_aggregate"
    dataset_specs = [
        dataset_descriptor(
            "dataset_001",
            "aligned_replicates",
            f"{aggregate_dir}/dataset_plot_data/dataset_001.csv",
            datasets["replicates"],
        ),
        dataset_descriptor(
            "stress_aggregate",
            "stress_aggregate",
            f"{aggregate_dir}/dataset_plot_data/stress_aggregate.csv",
            datasets["stress_aggregate"],
        ),
        dataset_descriptor(
            "fmax_distribution",
            "fmax_distribution",
            f"{aggregate_dir}/dataset_plot_data/fmax_distribution.csv",
            datasets["fmax_distribution"],
        ),
        dataset_descriptor(
            "bending_summary",
            "bending_summary",
            f"{aggregate_dir}/dataset_plot_data/bending_summary.csv",
            datasets["bending_summary"],
        ),
    ]
    template = handoff_template_spec()
    package = {
        "package_type": "compact-vegalite-workbench",
        "schema_version": "0.1",
        "plot_id": "dataset_plot",
        "plot_type": "mtda_dataset_aggregate",
        "title": title,
        "data_mode": "external_csv",
        "view_data_mode": "embedded_rows_preferred",
        "template": template,
        "embedded_datasets": [
            {**dataset, "rows": datasets[dataset["dataset_id"] if dataset["dataset_id"] != "dataset_001" else "replicates"]}
            for dataset in dataset_specs
        ],
        "template_member": f"{aggregate_dir}/dataset_plot.template.json",
        "template_path": "dataset_plot.template.json",
        "html_member": f"{aggregate_dir}/dataset_plot.html",
        "datasets": dataset_specs,
        "data_refs": dataset_specs,
        "semantic_layers": [
            {"layer_id": "stress_strain_curves", "semantic_role": "individual replicates"},
        ],
        "source_refs": [
            f"{aggregate_dir}/stress_strain_aligned.csv",
            f"{aggregate_dir}/characteristic_points.csv",
            f"{aggregate_dir}/statistics.csv",
        ],
    }

    files: dict[str, bytes] = {
        "index.html": (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MTDA Archive</title></head>'
            '<body><main><h1>MTDA aligned archive</h1>'
            '<p><a href="dataset/03_aggregate/dataset_plot.html">Dataset aggregate plot</a></p>'
            "</main></body></html>"
        ).encode("utf-8"),
        f"{aggregate_dir}/support.js": (handoff / "support.js").read_bytes(),
        f"{aggregate_dir}/dataset_plot.html": (handoff / "MTDA Dataset.dc.html").read_bytes(),
        f"{aggregate_dir}/dataset_plot.plot_package.json": json.dumps(package, indent=2).encode("utf-8"),
        f"{aggregate_dir}/dataset_plot.template.json": json.dumps(template, indent=2).encode("utf-8"),
        f"{aggregate_dir}/data/archive_data.js": (data_dir / "archive_data.js").read_bytes(),
        f"{aggregate_dir}/data/bending_dist.js": (data_dir / "bending_dist.js").read_bytes(),
    }
    for dataset in dataset_specs:
        key = dataset["dataset_id"] if dataset["dataset_id"] != "dataset_001" else "replicates"
        files[str(dataset["member"])] = rows_to_csv_bytes(datasets[key])
    for name in ("stress_strain_aligned.csv", "characteristic_points.csv", "statistics.csv"):
        files[f"{aggregate_dir}/{name}"] = (data_dir / name).read_bytes()
        files[f"{aggregate_dir}/data/{name}"] = (data_dir / name).read_bytes()

    mtda = out / "handoff_alignment_fixture.mtda"
    with zipfile.ZipFile(mtda, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, payload in sorted(files.items()):
            archive.writestr(member, payload)
    return mtda

def load_handoff_js_assignment(path: Path, variable_name: str) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    prefix = f"window.{variable_name} = "
    if not raw.startswith(prefix) or not raw.endswith(";"):
        raise ValueError(f"{path} does not look like a window.{variable_name} assignment")
    value = raw[len(prefix) : -1]
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return parsed


def handoff_plot_datasets(archive_data: dict[str, Any], bending_dist: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grid = 250
    grid_x = [(index / (grid - 1)) * 100 for index in range(grid)]
    by_run: dict[str, list[dict[str, Any]]] = {}
    for point in archive_data.get("alignedSeries") or []:
        run = str(point.get("run") or "")
        if run:
            by_run.setdefault(run, []).append(point)
    run_ids = sorted(by_run)
    resampled: dict[str, list[float]] = {}
    peak_stress: dict[str, float] = {}
    for run_id in run_ids:
        points = sorted(by_run[run_id], key=lambda item: float(item.get("x") or 0))
        if not points:
            continue
        peak_index = max(range(len(points)), key=lambda index: float(points[index].get("y") or 0))
        peak_y = float(points[peak_index].get("y") or 0)
        peak_x = float(points[peak_index].get("x") or 1) or 1.0
        peak_stress[run_id] = peak_y
        truncated = [
            {"x": (float(point.get("x") or 0) / peak_x) * 100, "y": float(point.get("y") or 0)}
            for point in points[: peak_index + 1]
        ]
        if not truncated or truncated[0]["x"] > 0:
            truncated.insert(0, {"x": 0.0, "y": truncated[0]["y"] if truncated else 0.0})
        truncated[-1]["x"] = 100.0
        sampled: list[float] = []
        cursor = 0
        for x_query in grid_x:
            while cursor < len(truncated) - 2 and truncated[cursor + 1]["x"] < x_query:
                cursor += 1
            left = truncated[min(cursor, len(truncated) - 1)]
            right = truncated[min(cursor + 1, len(truncated) - 1)]
            span = right["x"] - left["x"]
            t = (x_query - left["x"]) / span if span > 1e-9 else 0.0
            sampled.append(left["y"] + t * (right["y"] - left["y"]))
        resampled[run_id] = sampled

    aggregate: list[dict[str, Any]] = []
    replicates: list[dict[str, Any]] = []
    for index, x_value in enumerate(grid_x):
        values = [resampled[run_id][index] for run_id in run_ids]
        mean = sum(values) / len(values) if values else 0.0
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1) if len(values) > 1 else 0.0
        std = variance**0.5
        aggregate.append(
            {
                "x_common": round(x_value, 3),
                "mean_stress_MPa": round(mean, 3),
                "std_stress_MPa": round(std, 3),
                "min_stress_MPa": round(min(values), 3) if values else 0.0,
                "max_stress_MPa": round(max(values), 3) if values else 0.0,
                "lo_stress_MPa": round(mean - std, 3),
                "hi_stress_MPa": round(mean + std, 3),
                "run_count": len(values),
            }
        )
        for run_id in run_ids:
            replicates.append({"run_id": run_id, "x_common": round(x_value, 3), "y_observed": round(resampled[run_id][index], 3)})

    strengths = sorted(peak_stress.values())
    stats = archive_data.get("stats") if isinstance(archive_data.get("stats"), dict) else {}
    strength_stats = stats.get("compressive_strength_MPa") if isinstance(stats.get("compressive_strength_MPa"), dict) else {}
    fmax = {
        "label": "Fmax",
        "x_position": 100,
        "run_count": len(strengths),
        "min_strength_MPa": round(strengths[0], 2) if strengths else 0.0,
        "q1_strength_MPa": round(quantile(strengths, 0.25), 2) if strengths else 0.0,
        "median_strength_MPa": round(quantile(strengths, 0.5), 2) if strengths else 0.0,
        "q3_strength_MPa": round(quantile(strengths, 0.75), 2) if strengths else 0.0,
        "max_strength_MPa": round(strengths[-1], 2) if strengths else 0.0,
        "mean_strength_MPa": round(float(strength_stats.get("mean") or (sum(strengths) / len(strengths) if strengths else 0)), 2),
    }

    bending: list[dict[str, Any]] = []
    for run in archive_data.get("runs") or []:
        run_id = str(run.get("id") or "")
        dist = bending_dist.get(run_id) if isinstance(bending_dist.get(run_id), dict) else {}
        pattern = str(run.get("bendPattern") or "")
        bending.append(
            {
                "run_id": run_id,
                "min_bending_percent": round(float(dist.get("min") or 0), 2),
                "q1_bending_percent": round(float(dist.get("q1") or 0), 2),
                "median_bending_percent": round(float(dist.get("median") if dist.get("median") is not None else run.get("bendMedian") or 0), 2),
                "q3_bending_percent": round(float(dist.get("q3") or 0), 2),
                "max_bending_percent": round(float(dist.get("max") if dist.get("max") is not None else run.get("bendMax") or 0), 2),
                "bending_threshold_percent": float(run.get("bendThreshold") if run.get("bendThreshold") is not None else 10),
                "bending_pattern": pattern,
                "bending_pattern_group": "FAIL" if pattern.startswith("FAIL") else "WARN" if pattern.startswith("WARN") else "PASS",
            }
        )

    return {
        "replicates": replicates,
        "stress_aggregate": aggregate,
        "fmax_distribution": [fmax],
        "bending_summary": bending,
    }


def quantile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    index = (len(values) - 1) * p
    low = int(index)
    high = min(len(values) - 1, low + (0 if index == int(index) else 1))
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (index - low)


def dataset_descriptor(dataset_id: str, role: str, member: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "format": "csv",
        "path": f"dataset_plot_data/{dataset_id}.csv",
        "member": member,
        "fields": field_order(rows),
        "row_count": len(rows),
        "role": role,
    }


def handoff_template_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Handoff 8552-IM7 aligned replicate curves for production Plot Studio comparison.",
        "data": {"__compact_dataset_ref__": "dataset_001"},
        "mark": {"type": "line", "clip": True, "color": "#8a9eb2", "strokeWidth": 0.9, "opacity": 0.5},
        "encoding": {
            "x": {"field": "x_common", "type": "quantitative", "title": "Normalised strain to failure / %"},
            "y": {"field": "y_observed", "type": "quantitative", "title": "Stress / MPa"},
            "detail": {"field": "run_id", "type": "nominal"},
            "order": {"field": "x_common", "type": "quantitative"},
        },
    }


def rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    fields = field_order(rows)
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def field_order(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(str(key))
    return fields


def extract_mtda(mtda: Path, destination: Path) -> None:
    with zipfile.ZipFile(mtda) as archive:
        archive.extractall(destination)


def source_html_inventory(path: Path) -> dict[str, Any]:
    parser = SourceDomParser()
    html = path.read_text(encoding="utf-8", errors="replace")
    parser.feed(html)
    elements = []
    for element in parser.elements:
        copied = dict(element)
        copied["text"] = " ".join(str(copied.get("text", "")).split())[:160]
        copied["label"] = source_element_label(copied)
        copied["signature"] = source_element_signature(copied)
        elements.append(copied)
    tag_counts = Counter(str(element["tag"]) for element in elements)
    class_counts = Counter(class_name for element in elements for class_name in element.get("classes", []))
    ids = sorted(str(element.get("id")) for element in elements if element.get("id"))
    controls = [element for element in elements if element["tag"] in {"button", "a", "input", "select", "textarea"}]
    return {
        "path": str(path),
        "element_count": len(elements),
        "tag_counts": dict(sorted(tag_counts.items())),
        "class_counts": dict(sorted(class_counts.items())),
        "ids": ids,
        "controls": [
            {
                "index": control["index"],
                "depth": control["depth"],
                "path": control["path"],
                "tag": control["tag"],
                "id": control.get("id", ""),
                "classes": control.get("classes", []),
                "label": control["label"],
                "signature": control["signature"],
            }
            for control in controls
        ],
        "elements": elements,
    }


def source_element_label(element: dict[str, Any]) -> str:
    for key in ("text", "aria_label", "placeholder", "id", "href", "type"):
        value = " ".join(str(element.get(key, "")).split())
        if value:
            return value[:160]
    return ""


def source_element_signature(element: dict[str, Any]) -> str:
    ident = f"#{element['id']}" if element.get("id") else ""
    classes = "".join(f".{class_name}" for class_name in element.get("classes", []))
    role = f"[role={element['role']}]" if element.get("role") else ""
    type_attr = f"[type={element['type']}]" if element.get("type") else ""
    return f"{element['tag']}{ident}{classes}{role}{type_attr}"


def source_dom_residuals(
    state_id: str,
    production_html: Path,
    golden_html: Path,
    *,
    diagnostics_dir: Path | None = None,
) -> list[dict[str, str]]:
    if not production_html.is_file() or not golden_html.is_file():
        return [
            {
                "state": state_id,
                "category": "source-dom",
                "detail": f"source HTML missing: production={production_html.is_file()} golden={golden_html.is_file()}",
            }
        ]

    production = source_html_inventory(production_html)
    golden = source_html_inventory(golden_html)
    diffs = source_dom_diff(production, golden)
    if diagnostics_dir is not None:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        (diagnostics_dir / "source-dom-diff.json").write_text(
            json.dumps({"production": production, "golden": golden, "diffs": diffs}, indent=2),
            encoding="utf-8",
        )
    residuals: list[dict[str, str]] = []
    for diff in diffs:
        residuals.append({"state": state_id, "category": diff["category"], "detail": diff["detail"]})
    return residuals


def source_dom_diff(production: dict[str, Any], golden: dict[str, Any]) -> list[dict[str, str]]:
    diffs: list[dict[str, str]] = []
    if production["element_count"] != golden["element_count"]:
        diffs.append(
            {
                "category": "source-dom",
                "detail": f"element count differs: production {production['element_count']}, golden {golden['element_count']}",
            }
        )

    tag_deltas = count_deltas(production["tag_counts"], golden["tag_counts"])
    if tag_deltas:
        diffs.append({"category": "source-dom", "detail": "tag count deltas: " + ", ".join(tag_deltas)})

    class_deltas = count_deltas(production["class_counts"], golden["class_counts"])
    if class_deltas:
        diffs.append({"category": "source-dom", "detail": "class count deltas: " + ", ".join(class_deltas[:30])})

    prod_ids = set(production["ids"])
    gold_ids = set(golden["ids"])
    missing_ids = sorted(gold_ids - prod_ids)
    extra_ids = sorted(prod_ids - gold_ids)
    if missing_ids:
        diffs.append({"category": "source-dom", "detail": "ids missing from production: " + ", ".join(missing_ids[:40])})
    if extra_ids:
        diffs.append({"category": "source-dom", "detail": "ids only in production: " + ", ".join(extra_ids[:40])})

    prod_controls = source_control_labels(production)
    gold_controls = source_control_labels(golden)
    missing_controls = sorted(set(gold_controls) - set(prod_controls))
    extra_controls = sorted(set(prod_controls) - set(gold_controls))
    if missing_controls:
        diffs.append(
            {
                "category": "source-control",
                "detail": "controls missing from production source: " + ", ".join(gold_controls[label] for label in missing_controls[:40]),
            }
        )
    if extra_controls:
        diffs.append(
            {
                "category": "source-control",
                "detail": "controls only in production source: " + ", ".join(prod_controls[label] for label in extra_controls[:40]),
            }
        )

    prod_signatures = Counter(element["signature"] for element in production["elements"])
    gold_signatures = Counter(element["signature"] for element in golden["elements"])
    signature_deltas = count_deltas(dict(prod_signatures), dict(gold_signatures))
    if signature_deltas:
        diffs.append({"category": "source-dom", "detail": "element signature deltas: " + ", ".join(signature_deltas[:35])})
    return diffs


def count_deltas(production: dict[str, int], golden: dict[str, int]) -> list[str]:
    deltas = []
    for key in sorted(set(production) | set(golden)):
        prod_count = int(production.get(key, 0))
        gold_count = int(golden.get(key, 0))
        if prod_count != gold_count:
            deltas.append(f"{key} production={prod_count} golden={gold_count}")
    return deltas


def source_control_labels(inventory: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for control in inventory.get("controls", []):
        label = str(control.get("label") or control.get("signature") or "")
        normalized = normalize_label(f"{control.get('tag')} {label}")
        if normalized:
            labels[normalized] = f"{control.get('tag')}:{label}"
    return labels


def capture_states(
    browser: Any,
    url: str,
    output_dir: Path,
    *,
    width: int,
    height: int,
    state_prefix: str,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
    try:
        for state in STATES:
            errors: list[str] = []
            page.goto(url, wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(600)
            for action, value in state.actions:
                try:
                    apply_action(page, action, value)
                    page.wait_for_timeout(350)
                except Exception as exc:
                    errors.append(f"{action}:{value}: {exc}")
            screenshot = output_dir / f"{state.state_id}.png"
            page.screenshot(path=str(screenshot), full_page=False)
            inventory = dom_inventory(page)
            missing = [text for text in state.required_text if not text_present(inventory, text)]
            results.append(
                {
                    "side": state_prefix,
                    "state_id": state.state_id,
                    "label": state.label,
                    "screenshot": str(screenshot),
                    "missing_required_text": missing,
                    "errors": errors,
                    "inventory": inventory,
                }
            )
    finally:
        page.close()
    return results


def apply_action(page: Any, action: str, value: str) -> None:
    if action != "click_text":
        raise ValueError(f"Unsupported action: {action}")
    locators = [
        page.get_by_role("button", name=value, exact=True),
        page.get_by_text(value, exact=True),
        page.get_by_text(value, exact=False),
    ]
    last_error: Exception | None = None
    for locator in locators:
        try:
            locator.first.click(timeout=2_000)
            return
        except Exception as exc:  # pragma: no cover - depends on browser DOM
            last_error = exc
    raise RuntimeError(f"Could not click text {value!r}") from last_error


def dom_inventory(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
        const text = document.body ? document.body.innerText : "";
        const visible = el => {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
        };
        const computedStyleMap = style => {
          const out = {};
          for (const key of Array.from(style)) out[key] = style.getPropertyValue(key);
          return out;
        };
        const selectedStyle = style => ({
          display: style.display,
          position: style.position,
          boxSizing: style.boxSizing,
          width: style.width,
          height: style.height,
          margin: style.margin,
          padding: style.padding,
          backgroundColor: style.backgroundColor,
          borderColor: style.borderColor,
          borderStyle: style.borderStyle,
          borderWidth: style.borderWidth,
          borderRadius: style.borderRadius,
          color: style.color,
          fontFamily: style.fontFamily,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          lineHeight: style.lineHeight,
          overflow: style.overflow,
          flexDirection: style.flexDirection,
          gridTemplateColumns: style.gridTemplateColumns,
          gridTemplateRows: style.gridTemplateRows,
        });
        const label = el => {
          const aria = el.getAttribute('aria-label');
          if (aria) return aria.trim();
          if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
            const explicit = el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null;
            const wrapped = el.closest('label');
            const labelled = (explicit || wrapped);
            if (labelled) {
              const strong = labelled.querySelector('strong');
              if (strong && strong.innerText.trim()) return strong.innerText.trim();
            }
            if (labelled && labelled.innerText.trim()) return labelled.innerText.trim();
            if (el.placeholder) return el.placeholder.trim();
            if (el.value) return String(el.value).trim();
          }
          return (el.innerText || el.value || el.id || '').trim();
        };
        const directText = el => Array.from(el.childNodes || [])
          .filter(node => node.nodeType === Node.TEXT_NODE)
          .map(node => node.textContent || '')
          .join(' ')
          .replace(/\\s+/g, ' ')
          .trim();
        const elementPath = el => {
          const parts = [];
          let current = el;
          while (current && current.nodeType === Node.ELEMENT_NODE) {
            const tag = current.tagName.toLowerCase();
            const parent = current.parentElement;
            if (!parent) {
              parts.unshift(tag);
              break;
            }
            const siblings = Array.from(parent.children).filter(child => child.tagName === current.tagName);
            const ordinal = siblings.indexOf(current) + 1;
            const ident = current.id ? `#${current.id}` : '';
            parts.unshift(`${tag}${ident}:nth-of-type(${ordinal})`);
            current = parent;
          }
          return '/' + parts.join('/');
        };
        const depthNodes = () => {
          if (!document.body) return [];
          const nodes = [];
          const visit = (el, depth, parentPath, childIndex) => {
            if (nodes.length >= 600) return;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const path = elementPath(el);
            nodes.push({
              index: nodes.length,
              depth,
              path,
              parentPath,
              childIndex,
              tag: el.tagName.toLowerCase(),
              id: el.id || '',
              classes: Array.from(el.classList || []),
              role: el.getAttribute('role') || '',
              type: el.getAttribute('type') || '',
              ariaLabel: el.getAttribute('aria-label') || '',
              label: label(el).slice(0, 140),
              directText: directText(el).slice(0, 140),
              childElementCount: el.children.length,
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              visible: visible(el),
              selectedStyle: selectedStyle(style),
              computedStyle: computedStyleMap(style),
            });
            Array.from(el.children).forEach((child, index) => visit(child, depth + 1, path, index));
          };
          visit(document.body, 0, '', 0);
          return nodes;
        };
        const entries = selector => Array.from(document.querySelectorAll(selector)).filter(visible).map(label).filter(Boolean);
        const elementSummary = (kind, selector) => Array.from(document.querySelectorAll(selector)).filter(visible).slice(0, 80).map((el, index) => {
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return {
            kind,
            index,
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            classes: Array.from(el.classList || []),
            label: label(el).slice(0, 120),
            role: el.getAttribute('role') || '',
            type: el.getAttribute('type') || '',
            ariaLabel: el.getAttribute('aria-label') || '',
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            display: style.display,
            position: style.position,
            backgroundColor: style.backgroundColor,
            borderColor: style.borderColor,
            borderRadius: style.borderRadius,
            color: style.color,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            padding: style.padding,
            computedStyle: computedStyleMap(style),
          };
        });
        const box = (name, selector) => Array.from(document.querySelectorAll(selector)).filter(visible).slice(0, 8).map(el => {
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return {
            name,
            selector,
            label: label(el).slice(0, 80),
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            classes: Array.from(el.classList || []),
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            display: style.display,
            position: style.position,
            backgroundColor: style.backgroundColor,
            borderColor: style.borderColor,
            borderRadius: style.borderRadius,
            color: style.color,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            padding: style.padding,
            computedStyle: computedStyleMap(style),
          };
        });
        const boxes = [
          ...box('studio', '[data-studio],.plot-studio'),
          ...box('top_bar', '.topbar,.studio-topbar,header'),
          ...box('workspace', '.workspace,.studio-main'),
          ...box('chart_canvas', '.canvas,.chart-card,#plot,.vega-embed'),
          ...box('inspector', '.inspector,.studio-inspector,aside'),
          ...box('footer', '.footer-strip,.saved-looks,footer'),
          ...box('overlay', '.modal-backdrop.open,.modal,.data-overlay,.spec-overlay,[role="dialog"]'),
          ...box('export_menu', '.export-menu.open,.export-menu,[aria-label="Export menu"]')
        ];
        return {
          title: document.title,
          bodyText: text,
          buttons: entries('button'),
          links: entries('a'),
          inputs: entries('input').length,
          selects: entries('select').length,
          textareas: entries('textarea').length,
          headings: entries('h1,h2,h3'),
          dataStudio: document.querySelector('[data-studio]')?.getAttribute('data-studio') || '',
          plotMounts: document.querySelectorAll('#plot,.vega-embed,canvas,svg').length,
          controls: [
            ...elementSummary('button', 'button'),
            ...elementSummary('link', 'a'),
            ...elementSummary('input', 'input'),
            ...elementSummary('select', 'select'),
            ...elementSummary('textarea', 'textarea'),
            ...elementSummary('table', 'table'),
            ...elementSummary('canvas', 'canvas'),
            ...elementSummary('svg', 'svg')
          ],
          boxes,
          domDepth: depthNodes()
        };
        }"""
    )


def text_present(inventory: dict[str, Any], text: str) -> bool:
    haystack = normalize_label(
        "\n".join(
            [
                str(inventory.get("bodyText", "")),
                "\n".join(str(item) for item in inventory.get("buttons", [])),
                "\n".join(str(item) for item in inventory.get("headings", [])),
            ]
        )
    )
    return normalize_label(text) in haystack


def normalize_label(value: str) -> str:
    normalized = (
        str(value)
        .replace("\u2190", "")
        .replace("\u230e", "")
        .replace("\u2922", "")
        .replace("\u25be", "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2026", "...")
    )
    return " ".join(normalized.lower().split())


def normalized_button_set(inventory: dict[str, Any]) -> set[str]:
    return {normalize_label(button) for button in inventory.get("buttons", []) if normalize_label(button)}


def display_button_set(inventory: dict[str, Any]) -> dict[str, str]:
    return {normalize_label(button): str(button) for button in inventory.get("buttons", []) if normalize_label(button)}


def stable_button_labels(labels: set[str], display: dict[str, str]) -> list[str]:
    return [display.get(label, label) for label in sorted(labels)]


def inventory_text(inventory: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(inventory.get("bodyText", "")),
            "\n".join(str(item) for item in inventory.get("buttons", [])),
            "\n".join(str(item) for item in inventory.get("headings", [])),
        ]
    )


def merge_state_results(production: list[dict[str, Any]], golden: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_state = {item["state_id"]: {"state_id": item["state_id"], "label": item["label"], "production": item} for item in production}
    for item in golden:
        by_state.setdefault(item["state_id"], {"state_id": item["state_id"], "label": item["label"]})["golden"] = item
    return [by_state[state.state_id] for state in STATES if state.state_id in by_state]


def build_residuals(
    states: list[dict[str, Any]],
    *,
    strict_visual: bool = False,
    diagnostics_dir: Path | None = None,
) -> list[dict[str, str]]:
    residuals: list[dict[str, str]] = []
    for state in states:
        production = state.get("production") or {}
        golden = state.get("golden") or {}
        for side_name, side in (("production", production), ("golden", golden)):
            for error in side.get("errors", []):
                residuals.append({"state": state["state_id"], "category": "behaviour", "detail": f"{side_name}: {error}"})
            for missing in side.get("missing_required_text", []):
                residuals.append(
                    {"state": state["state_id"], "category": "structural", "detail": f"{side_name} missing text: {missing}"}
                )
        if production and golden:
            if production["inventory"].get("plotMounts", 0) == 0:
                residuals.append({"state": state["state_id"], "category": "visual", "detail": "production plot mount is absent"})
            if "controls" in production["inventory"] and "controls" in golden["inventory"]:
                dom_dir = diagnostics_dir.parent / "dom_diagnostics" if diagnostics_dir is not None else None
                residuals.extend(
                    dom_residuals(
                        state["state_id"],
                        production["inventory"],
                        golden["inventory"],
                        diagnostics_dir=dom_dir,
                    )
                )
            if strict_visual:
                residuals.extend(strict_visual_residuals(state["state_id"], production, golden, diagnostics_dir=diagnostics_dir))
    return residuals


def dom_residuals(
    state_id: str,
    production: dict[str, Any],
    golden: dict[str, Any],
    *,
    diagnostics_dir: Path | None = None,
) -> list[dict[str, str]]:
    diffs = runtime_dom_diff(production, golden)
    depth_diffs = runtime_dom_depth_diff(production, golden)
    if diagnostics_dir is not None:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        (diagnostics_dir / f"{state_id}.dom-diff.json").write_text(
            json.dumps({"production": production, "golden": golden, "diffs": diffs}, indent=2),
            encoding="utf-8",
        )
        depth_dir = diagnostics_dir.parent / "dom_depth_diagnostics"
        depth_dir.mkdir(parents=True, exist_ok=True)
        (depth_dir / f"{state_id}.depth-diff.json").write_text(
            json.dumps(
                {
                    "state_id": state_id,
                    "production": production.get("domDepth", []),
                    "golden": golden.get("domDepth", []),
                    "diffs": depth_diffs,
                    "depth_summary": dom_depth_summary(production, golden),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    combined = diffs + depth_diffs
    return [{"state": state_id, "category": diff["category"], "detail": diff["detail"]} for diff in combined]


def dom_depth_summary(production: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    prod_by_depth = nodes_by_depth(production.get("domDepth", []))
    gold_by_depth = nodes_by_depth(golden.get("domDepth", []))
    summary: dict[str, Any] = {}
    for depth in sorted(set(prod_by_depth) | set(gold_by_depth)):
        prod_nodes = prod_by_depth.get(depth, [])
        gold_nodes = gold_by_depth.get(depth, [])
        summary[str(depth)] = {
            "production_count": len(prod_nodes),
            "golden_count": len(gold_nodes),
            "production_signatures": [node_signature(node) for node in prod_nodes[:24]],
            "golden_signatures": [node_signature(node) for node in gold_nodes[:24]],
        }
    return summary


def runtime_dom_depth_diff(production: dict[str, Any], golden: dict[str, Any], *, max_reported_depth: int = 2) -> list[dict[str, str]]:
    diffs: list[dict[str, str]] = []
    prod_nodes = production.get("domDepth", [])
    gold_nodes = golden.get("domDepth", [])
    if not prod_nodes or not gold_nodes:
        return diffs
    prod_by_depth = nodes_by_depth(prod_nodes)
    gold_by_depth = nodes_by_depth(gold_nodes)
    for depth in sorted(set(prod_by_depth) | set(gold_by_depth)):
        prod_depth_nodes = prod_by_depth.get(depth, [])
        gold_depth_nodes = gold_by_depth.get(depth, [])
        if len(prod_depth_nodes) != len(gold_depth_nodes):
            diffs.append(
                {
                    "category": "dom-depth",
                    "detail": (
                        f"depth {depth} node count differs: production={len(prod_depth_nodes)} "
                        f"golden={len(gold_depth_nodes)}"
                    ),
                }
            )
        if depth > max_reported_depth:
            continue
        max_len = max(len(prod_depth_nodes), len(gold_depth_nodes))
        for index in range(max_len):
            prod_node = prod_depth_nodes[index] if index < len(prod_depth_nodes) else None
            gold_node = gold_depth_nodes[index] if index < len(gold_depth_nodes) else None
            if prod_node is None or gold_node is None:
                continue
            node_delta = runtime_depth_node_delta(prod_node, gold_node)
            if node_delta:
                diffs.append({"category": "dom-depth", "detail": f"depth {depth} node {index}: {node_delta}"})
    return diffs


def nodes_by_depth(nodes: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for node in nodes:
        result.setdefault(int(node.get("depth", 0)), []).append(node)
    return result


def node_signature(node: dict[str, Any]) -> str:
    ident = f"#{node.get('id')}" if node.get("id") else ""
    classes = "".join(f".{class_name}" for class_name in node.get("classes", []))
    return f"{node.get('tag')}{ident}{classes}"


def runtime_depth_node_delta(production: dict[str, Any], golden: dict[str, Any]) -> str:
    deltas: list[str] = []
    for key in ("tag", "id", "role", "type"):
        prod_value = str(production.get(key, ""))
        gold_value = str(golden.get(key, ""))
        if prod_value != gold_value:
            deltas.append(f"{key} production={prod_value!r} golden={gold_value!r}")
    if production.get("classes", []) != golden.get("classes", []):
        deltas.append(f"classes production={production.get('classes', [])!r} golden={golden.get('classes', [])!r}")
    box_delta = runtime_box_delta(production, golden, tolerance=4)
    if box_delta:
        deltas.append("box " + box_delta)
    style_delta = selected_style_delta(production.get("selectedStyle", {}), golden.get("selectedStyle", {}))
    if style_delta:
        deltas.append("style " + style_delta)
    return "; ".join(deltas[:8])


def selected_style_delta(production: dict[str, Any], golden: dict[str, Any]) -> str:
    keys = (
        "display",
        "position",
        "boxSizing",
        "margin",
        "padding",
        "backgroundColor",
        "borderColor",
        "borderStyle",
        "borderWidth",
        "borderRadius",
        "color",
        "fontFamily",
        "fontSize",
        "fontWeight",
        "lineHeight",
        "overflow",
        "flexDirection",
        "gridTemplateColumns",
        "gridTemplateRows",
    )
    deltas: list[str] = []
    for key in keys:
        prod_value = str(production.get(key, ""))
        gold_value = str(golden.get(key, ""))
        if prod_value != gold_value:
            deltas.append(f"{key} production={prod_value!r} golden={gold_value!r}")
    return "; ".join(deltas[:6])


def runtime_dom_diff(production: dict[str, Any], golden: dict[str, Any]) -> list[dict[str, str]]:
    diffs: list[dict[str, str]] = []
    prod_controls = production.get("controls", [])
    gold_controls = golden.get("controls", [])
    prod_kind_counts = Counter(str(control.get("kind", "")) for control in prod_controls)
    gold_kind_counts = Counter(str(control.get("kind", "")) for control in gold_controls)
    kind_deltas = count_deltas(dict(prod_kind_counts), dict(gold_kind_counts))
    if kind_deltas:
        diffs.append({"category": "dom-control", "detail": "visible control count deltas: " + ", ".join(kind_deltas)})

    prod_labels = runtime_control_labels(prod_controls)
    gold_labels = runtime_control_labels(gold_controls)
    missing_controls = sorted(set(gold_labels) - set(prod_labels))
    extra_controls = sorted(set(prod_labels) - set(gold_labels))
    if missing_controls:
        diffs.append(
            {
                "category": "dom-control",
                "detail": "visible controls missing from production: "
                + ", ".join(str(gold_labels[label]["display"]) for label in missing_controls[:40]),
            }
        )
    if extra_controls:
        diffs.append(
            {
                "category": "dom-control",
                "detail": "visible controls only in production: "
                + ", ".join(str(prod_labels[label]["display"]) for label in extra_controls[:40]),
            }
        )

    prod_boxes = runtime_boxes_by_name(production.get("boxes", []))
    gold_boxes = runtime_boxes_by_name(golden.get("boxes", []))
    for name in sorted(set(prod_boxes) | set(gold_boxes)):
        prod_box = prod_boxes.get(name)
        gold_box = gold_boxes.get(name)
        if prod_box is None:
            diffs.append({"category": "dom-box", "detail": f"{name} box missing from production runtime DOM"})
            continue
        if gold_box is None:
            diffs.append({"category": "dom-box", "detail": f"{name} box only in production runtime DOM"})
            continue
        box_delta = runtime_box_delta(prod_box, gold_box)
        if box_delta:
            diffs.append({"category": "dom-box", "detail": f"{name} box differs: {box_delta}"})
        style_delta = runtime_style_delta(prod_box, gold_box)
        if style_delta:
            diffs.append({"category": "dom-style", "detail": f"{name} style differs: {style_delta}"})

    for label in sorted(set(prod_labels) & set(gold_labels)):
        prod_control = prod_labels[label]["control"]
        gold_control = gold_labels[label]["control"]
        box_delta = runtime_box_delta(prod_control, gold_control, tolerance=8)
        if box_delta:
            diffs.append({"category": "dom-box", "detail": f"control {prod_labels[label]['display']} box differs: {box_delta}"})
    return diffs


def runtime_control_labels(controls: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for control in controls:
        label = str(control.get("label") or control.get("ariaLabel") or control.get("id") or control.get("type") or "")
        normalized = normalize_label(f"{control.get('kind')} {label}")
        if not normalized:
            continue
        display = f"{control.get('kind')}:{label}"
        labels[normalized] = {"display": display, "control": control}
    return labels


def runtime_boxes_by_name(boxes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for box in boxes:
        name = str(box.get("name", ""))
        if name == "chart_canvas":
            result[name] = box
        elif name and name not in result:
            result[name] = box
    return result


def runtime_box_delta(production: dict[str, Any], golden: dict[str, Any], *, tolerance: int = 4) -> str:
    deltas = []
    for key in ("x", "y", "width", "height"):
        prod_value = int(production.get(key, 0))
        gold_value = int(golden.get(key, 0))
        delta = prod_value - gold_value
        if abs(delta) > tolerance:
            deltas.append(f"{key} production={prod_value} golden={gold_value} delta={delta}")
    return ", ".join(deltas)


def runtime_style_delta(production: dict[str, Any], golden: dict[str, Any]) -> str:
    keys = ("display", "position", "backgroundColor", "borderColor", "borderRadius", "color", "fontSize", "fontWeight", "padding")
    deltas = []
    for key in keys:
        prod_value = str(production.get(key, ""))
        gold_value = str(golden.get(key, ""))
        if prod_value != gold_value:
            deltas.append(f"{key} production={prod_value!r} golden={gold_value!r}")
    return "; ".join(deltas[:8])


def strict_visual_residuals(
    state_id: str,
    production: dict[str, Any],
    golden: dict[str, Any],
    *,
    diagnostics_dir: Path | None = None,
) -> list[dict[str, str]]:
    try:
        from PIL import Image, ImageChops
    except Exception as exc:  # pragma: no cover - dependency absence is environment-specific
        return [{"state": state_id, "category": "tooling", "detail": f"Pillow import failed: {exc}"}]

    prod_path = production.get("screenshot")
    golden_path = golden.get("screenshot")
    if not prod_path or not golden_path:
        return [{"state": state_id, "category": "visual", "detail": "missing screenshot path for strict visual comparison"}]

    with Image.open(prod_path) as prod_image, Image.open(golden_path) as golden_image:
        prod = prod_image.convert("RGB")
        gold = golden_image.convert("RGB")
        if prod.size != gold.size:
            return [
                {
                    "state": state_id,
                    "category": "visual",
                    "detail": f"screenshot size differs: production {prod.size[0]}x{prod.size[1]}, golden {gold.size[0]}x{gold.size[1]}",
                }
            ]
        diff = ImageChops.difference(prod, gold)
        bbox = diff.getbbox()
        if bbox is None:
            return []
        total = prod.size[0] * prod.size[1]
        mask = diff.convert("L").point(lambda value: 255 if value else 0)
        histogram = mask.histogram()
        changed = total - histogram[0]
        pct = (changed / total) * 100 if total else 0.0
        if diagnostics_dir is not None:
            write_visual_diagnostics(diagnostics_dir, state_id, prod, gold, diff, mask)
        residuals = [
            {
                "state": state_id,
                "category": "visual",
                "detail": f"strict screenshot delta: {changed}/{total} pixels ({pct:.4f}%) differ; bbox={bbox}",
            }
        ]
        residuals.extend(region_visual_residuals(state_id, mask))
        return residuals


def region_boxes(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    inspector_x = min(width - 1, max(0, int(round(width * 0.735))))
    top_h = min(height, max(1, int(round(height * 0.08))))
    footer_y = max(top_h, int(round(height * 0.965)))
    return {
        "shell": (0, 0, width, height),
        "top_bar": (0, 0, width, top_h),
        "chart_canvas": (0, top_h, inspector_x, footer_y),
        "inspector": (inspector_x, top_h, width, height),
        "overlay": (0, 0, width, height),
        "export_menu": (max(0, width - int(round(width * 0.25))), top_h, width, min(height, top_h + int(round(height * 0.36)))),
    }


def region_visual_residuals(state_id: str, mask: Any) -> list[dict[str, str]]:
    width, height = mask.size
    residuals: list[dict[str, str]] = []
    for name, box in region_boxes(width, height).items():
        crop = mask.crop(box)
        total = crop.size[0] * crop.size[1]
        if total == 0:
            continue
        histogram = crop.histogram()
        changed = total - histogram[0]
        if changed == 0:
            continue
        pct = (changed / total) * 100
        residuals.append(
            {
                "state": state_id,
                "category": "visual-region",
                "detail": f"{name}: {changed}/{total} pixels ({pct:.4f}%) differ; bbox={crop.getbbox()} viewport_box={box}",
            }
        )
    return residuals


def write_visual_diagnostics(diagnostics_dir: Path, state_id: str, prod: Any, gold: Any, diff: Any, mask: Any) -> None:
    from PIL import Image, ImageDraw

    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    width, height = prod.size
    heat = diff.convert("L").point(lambda value: min(255, value * 6))
    black = heat.point(lambda _value: 0)
    red_heatmap = Image.merge("RGB", (heat, black, black))
    region_map = red_heatmap.copy()
    draw = ImageDraw.Draw(region_map)
    for name, box in region_boxes(width, height).items():
        draw.rectangle(box, outline=(255, 220, 0), width=2)
        draw.text((box[0] + 4, box[1] + 4), name, fill=(255, 220, 0))
    sheet = Image.new("RGB", (width * 3, height), "white")
    sheet.paste(gold, (0, 0))
    sheet.paste(prod, (width, 0))
    sheet.paste(region_map, (width * 2, 0))
    red_heatmap.save(diagnostics_dir / f"{state_id}.diff-heatmap.png")
    region_map.save(diagnostics_dir / f"{state_id}.region-heatmap.png")
    sheet.save(diagnostics_dir / f"{state_id}.side-by-side.png")

    regions = []
    for name, box in region_boxes(width, height).items():
        crop = mask.crop(box)
        total = crop.size[0] * crop.size[1]
        histogram = crop.histogram()
        changed = total - histogram[0] if total else 0
        regions.append(
            {
                "region": name,
                "viewport_box": box,
                "changed_pixels": changed,
                "total_pixels": total,
                "changed_percent": (changed / total) * 100 if total else 0.0,
                "local_bbox": crop.getbbox(),
            }
        )
    (diagnostics_dir / f"{state_id}.regions.json").write_text(json.dumps(regions, indent=2), encoding="utf-8")


def write_report(out: Path, report: dict[str, Any]) -> None:
    (out / "alignment_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = report.get("residuals", [])
    with (out / "alignment_residuals.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["state", "category", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# MTDA Plot Studio Alignment Report",
        "",
        f"- Job: `{report.get('job')}`",
        f"- MTDA: `{report.get('mtda')}`",
        f"- Viewport: `{report['viewport']['width']}x{report['viewport']['height']}`",
        f"- Residual count: {len(rows)}",
        "",
        "## States",
        "",
    ]
    for state in report.get("states", []):
        lines.append(f"- `{state['state_id']}` — {state['label']}")
    lines.extend(["", "## Residuals", ""])
    if rows:
        for row in rows:
            lines.append(f"- `{row.get('state', '')}` `{row.get('category', '')}`: {row.get('detail', '')}")
    else:
        lines.append("- None recorded.")
    (out / "alignment_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
