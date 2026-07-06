from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Mapping
from typing import Any, Callable

from markupsafe import Markup

from html_renderer.context_models import MtdaHandoffPageContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_mtda_handoff_page


@dataclass(frozen=True, slots=True)
class MtdaPanelSpec:
    type: str
    values: dict[str, Any]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MtdaPanelSpec:
        panel_type = str(payload.get("type") or "").strip()
        if not panel_type:
            raise ValueError("MTDA page panel specs require a non-empty type")
        values = dict(payload)
        values.pop("type", None)
        return cls(type=panel_type, values=values)

    def get(self, key: str, default: Any = "") -> Any:
        return self.values.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.values}


@dataclass(frozen=True, slots=True)
class MtdaPageSpec:
    kind: str
    layout: str
    route: str
    panels: tuple[MtdaPanelSpec, ...]
    initial_state: dict[str, Any]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MtdaPageSpec:
        kind = str(payload.get("kind") or "").strip()
        layout = str(payload.get("layout") or "").strip()
        route = str(payload.get("route") or "").strip()
        panels_payload = payload.get("panels")
        if not kind:
            raise ValueError("MTDA page specs require a non-empty kind")
        if not layout:
            raise ValueError("MTDA page specs require a non-empty layout")
        if not route:
            raise ValueError("MTDA page specs require a non-empty route")
        if not isinstance(panels_payload, list) or not panels_payload:
            raise ValueError("MTDA page specs require a non-empty panels list")
        panels = tuple(MtdaPanelSpec.from_mapping(panel) for panel in panels_payload)
        initial_state = payload.get("initialState") if isinstance(payload.get("initialState"), dict) else {}
        spec = cls(kind=kind, layout=layout, route=route, panels=panels, initial_state=dict(initial_state))
        spec.validate()
        return spec

    def validate(self) -> None:
        missing = _REQUIRED_PANELS.get(self.kind, set()) - {panel.type for panel in self.panels}
        if missing:
            raise ValueError(f"MTDA page spec {self.kind} is missing required panels: {', '.join(sorted(missing))}")
        unknown = [panel.type for panel in self.panels if panel.type not in MTDA_HANDOFF_COMPONENTS]
        if unknown:
            raise ValueError(f"MTDA page spec {self.kind} uses unknown panels: {', '.join(unknown)}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "layout": self.layout,
            "route": self.route,
        }
        if self.initial_state:
            payload["initialState"] = self.initial_state
        payload["panels"] = [panel.to_dict() for panel in self.panels]
        return payload


@dataclass(frozen=True, slots=True)
class MtdaHandoffRenderRequest:
    source_html: str
    support_path: str
    globals: Mapping[str, Any]
    page_spec: Mapping[str, Any]
    dataset_name: str
    raw_root: str
    normalized_root: str
    processed_root: str
    aggregate_root: str
    reports_root: str


@dataclass(frozen=True, slots=True)
class _RenderContext:
    request: MtdaHandoffRenderRequest
    spec: MtdaPageSpec


ComponentRenderer = Callable[[str, MtdaPanelSpec, _RenderContext], str]


def render_mtda_handoff_from_spec(request: MtdaHandoffRenderRequest) -> str:
    spec = MtdaPageSpec.from_mapping(request.page_spec)
    html = _render_base_handoff_document(request, spec)
    context = _RenderContext(request=request, spec=spec)
    for panel in spec.panels:
        html = MTDA_HANDOFF_COMPONENTS[panel.type](html, panel, context)
    return html


def _render_base_handoff_document(request: MtdaHandoffRenderRequest, spec: MtdaPageSpec) -> str:
    globals_payload = dict(request.globals)
    globals_payload["MTDA_PAGE_SPEC"] = spec.to_dict()
    if spec.initial_state:
        globals_payload.setdefault("MTDA_INITIAL_STATE", spec.initial_state)
    globals_script = "\n".join(
        f"window.{name} = {json.dumps(_json_safe(payload), ensure_ascii=False)};"
        for name, payload in globals_payload.items()
    )
    globals_script = f"{globals_script}\n{_SVG_DATA_POINTS_SYNC_SCRIPT}"
    source = re.sub(r'\n\s*<script src="data/[^"]+\.js"></script>', "", request.source_html)
    prefix, marker, suffix = source.partition('<script src="./support.js"></script>')
    if not marker:
        raise ValueError("MTDA handoff source does not contain the expected support.js script tag")
    return render_mtda_handoff_page(
        MtdaHandoffPageContext(
            projection_plane=ProjectionPlane.MTDA_BUNDLE_VIEWER,
            recipe_result_kind=RecipeResultKind.MTDA_HANDOFF_PAGE,
            prefix_html=Markup(prefix),
            support_path=request.support_path,
            globals_script=Markup(_script_safe(globals_script)),
            suffix_html=Markup(suffix),
        )
    )


def _archive_header(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    return html


def _file_catalogue(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    request = context.request
    html = html.replace("dataset/01_raw", request.raw_root.rstrip("/"))
    html = html.replace("dataset/02_normalized", request.normalized_root.rstrip("/"))
    html = html.replace("dataset/03_processed", request.processed_root.rstrip("/"))
    html = html.replace("dataset/04_aggregate", request.aggregate_root.rstrip("/"))
    return html.replace(
        "href: (id === 'dataset/03_aggregate' ? 'data/' : 'data/pkg/') + f.name",
        "href: f.href || (id + '/' + f.name)",
    )


def _dataset_plate(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    href = str(panel.get("href") or "").strip()
    if not href:
        raise ValueError("dataset_plate panels require href")
    return html.replace("window.location.href = 'MTDA Dataset.dc.html';", f"window.location.href = '{href}';")


def _report_links(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    test_href = str(panel.get("testReportHref") or "").strip()
    audit_href = str(panel.get("auditReportHref") or "").strip()
    if not test_href or not audit_href:
        raise ValueError("report_links panels require testReportHref and auditReportHref")
    html = html.replace(
        '<div style="font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer;" style-hover="text-decoration: underline;">Test report ↗</div>',
        f'<a href="{test_href}" style="display: block; font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer; text-decoration: none;" style-hover="text-decoration: underline;">Test report ↗</a>',
    )
    return html.replace(
        '<div style="font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer;" style-hover="text-decoration: underline;">Audit report ↗</div>',
        f'<a href="{audit_href}" style="display: block; font-size: 14px; font-weight: 700; color: #185f8f; padding: 5px 0; cursor: pointer; text-decoration: none;" style-hover="text-decoration: underline;">Audit report ↗</a>',
    )


def _run_runtime(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    run_data_prefix = str(panel.get("runDataPrefix", "") or "")
    for suffix in ("stress_strain.csv", "stress_strain_experiment_bound.csv", "bending.csv"):
        html = html.replace(f"data/run_001_{suffix}", f"{run_data_prefix}run_001_{suffix}")
    return _adapt_handoff_archive_run_studio(html)


def _run_plate_grid(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    pattern = str(panel.get("hrefPattern") or "").strip()
    if not pattern:
        raise ValueError("run_plate_grid panels require hrefPattern")
    return html.replace(
        "on: () => this.activateRun(r)",
        f"on: () => {{ window.location.href = {_js_string_pattern(pattern, 'r.id')}; }}",
    )


def _run_navigation(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    archive_href = str(panel.get("archiveHref") or "").strip()
    if not archive_href:
        raise ValueError("run_navigation panels require archiveHref")
    return html.replace(
        "goHome: () => this.setState({ page: 'home', exportOpen: false, dataOpen: false, specOpen: false }),",
        f"goHome: () => {{ window.location.href = '{archive_href}'; }},",
    )


def _run_data_modal(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    if not panel.get("localCsvHrefs", False):
        return html
    return html.replace(
        "runStressHref: 'dataset/02_processed/' + this.runStressFile(), runBoundHref: 'dataset/02_processed/' + this.runBoundFile(), runBendingHref: 'dataset/02_processed/' + this.runBendingFile(),",
        "runStressHref: this.runStressFile(), runBoundHref: this.runBoundFile(), runBendingHref: this.runBendingFile(),",
    )


def _dataset_titles(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    dataset_name = context.request.dataset_name
    html = html.replace("8552-IM7 — dataset report · aggregate plot studio", f"{dataset_name} — dataset report · aggregate plot studio")
    html = html.replace("8552-IM7 — aggregate bending by run", f"{dataset_name} — aggregate bending by run")
    return html.replace("8552-IM7 — aggregate compressive stress–strain", f"{dataset_name} — aggregate compressive stress–strain")


def _dataset_navigation(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    archive_href = str(panel.get("archiveHref") or "").strip()
    if not archive_href:
        raise ValueError("dataset_navigation panels require archiveHref")
    return html.replace("window.location.href = 'MTDA Archive.dc.html';", f"window.location.href = '{archive_href}';")


def _dataset_data_links(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    for name in panel.get("localFiles", ()) or ():
        html = html.replace(f"data/{name}", str(name))
    return html


def _noop(html: str, panel: MtdaPanelSpec, context: _RenderContext) -> str:
    return html


MTDA_HANDOFF_COMPONENTS: dict[str, ComponentRenderer] = {
    "archive_header": _archive_header,
    "file_catalogue": _file_catalogue,
    "dataset_plate": _dataset_plate,
    "report_links": _report_links,
    "run_runtime": _run_runtime,
    "run_plate_grid": _run_plate_grid,
    "run_navigation": _run_navigation,
    "run_topbar": _noop,
    "run_plot_canvas": _noop,
    "run_data_modal": _run_data_modal,
    "dataset_titles": _dataset_titles,
    "dataset_navigation": _dataset_navigation,
    "dataset_data_links": _dataset_data_links,
    "plot_canvas": _noop,
    "plot_inspector": _noop,
    "export_menu": _noop,
}


_REQUIRED_PANELS: dict[str, set[str]] = {
    "mtda.archive.index": {"file_catalogue", "dataset_plate", "report_links", "run_runtime", "run_plate_grid"},
    "mtda.dataset.plot_studio": {"dataset_titles", "dataset_navigation", "dataset_data_links", "plot_canvas"},
    "mtda.run.browser": {
        "file_catalogue",
        "dataset_plate",
        "report_links",
        "run_runtime",
        "run_plate_grid",
        "run_navigation",
        "run_data_modal",
    },
}


def _adapt_handoff_archive_run_studio(source: str) -> str:
    replacements = {
        "<b>run_001</b>": "<b>{{ runId }}</b>",
        '← run_010 · run_002 → <span style="font-style: italic;">(prototype: run_001 only)</span>': "{{ runNavHint }}",
        '<option value="full">run_001_stress_strain (full, 889 rows)</option>': '<option value="full">{{ runStressFile }} (full, {{ runFullRows }} rows)</option>',
        '<option value="bound">run_001_stress_strain_experiment_bound (774 rows)</option>': '<option value="bound">{{ runBoundFile }} ({{ runBoundRows }} rows)</option>',
        '<option value="bending">run_001_bending (889 rows)</option>': '<option value="bending">{{ runBendingFile }} ({{ runFullRows }} rows)</option>',
        'href="dataset/02_processed/run_001_stress_strain.csv" download="run_001_stress_strain.csv"': 'href="{{ runStressHref }}" download="{{ runStressFile }}"',
        'href="dataset/02_processed/run_001_stress_strain_experiment_bound.csv" download="run_001_stress_strain_experiment_bound.csv"': 'href="{{ runBoundHref }}" download="{{ runBoundFile }}"',
        'href="dataset/02_processed/run_001_bending.csv" download="run_001_bending.csv"': 'href="{{ runBendingHref }}" download="{{ runBendingFile }}"',
        "⬇ run_001_stress_strain.csv": "⬇ {{ runStressFile }}",
        "⬇ run_001_…_experiment_bound.csv": "⬇ {{ runBoundShortFile }}",
        "⬇ run_001_bending.csv": "⬇ {{ runBendingFile }}",
        ">run_001_stress_strain.csv</a>": ">{{ runStressFile }}</a>",
        ">…_experiment_bound.csv</a>": ">{{ runBoundShortFile }}</a>",
        ">run_001_bending.csv</a>": ">{{ runBendingFile }}</a>",
        "title: 'run_001 — bending evidence'": "title: (this.run ? this.run.id : 'run') + ' — bending evidence'",
        "title: 'run_001 — compressive stress–strain'": "title: (this.run ? this.run.id : 'run') + ' — compressive stress–strain'",
        "rows.map(d => 'run_001,' + d.i + ',' + d.load + ',' + d.bend).join('\\n');": "rows.map(d => this.run.id + ',' + d.i + ',' + d.load + ',' + d.bend).join('\\n');",
        "rows.map(d => 'run_001,' + d.i + ',' + d.strain + ',' + d.stress + ',' + d.load).join('\\n');": "rows.map(d => this.run.id + ',' + d.i + ',' + d.strain + ',' + d.stress + ',' + d.load).join('\\n');",
        "const figName = 'run_001_' + st.figure;": "const figName = this.run.id + '_' + st.figure;",
        "this.download('run_001_' + st.datasetSel + '.csv', this.rowsToCsv(), 'text/csv')": "this.download(this.run.id + '_' + st.datasetSel + '.csv', this.rowsToCsv(), 'text/csv')",
        "downloadCsv: () => this.download('run_001_' + st.datasetSel + '.csv', this.rowsToCsv(), 'text/csv'),": "downloadCsv: () => this.download(this.run.id + '_' + st.datasetSel + '.csv', this.rowsToCsv(), 'text/csv'),",
        "exportSpec: () => this.download('run_001.full_vegalite_spec_with_data.vl.json', JSON.stringify(this.specOverride || this.buildSpec(), null, 2), 'application/json')": "exportSpec: () => this.download(this.run.id + '.full_vegalite_spec_with_data.vl.json', JSON.stringify(this.specOverride || this.buildSpec(), null, 2), 'application/json')",
        "This prototype builds run_001 in full; the remaining nine run pages share the same studio.": "This run has no hydrated curve payload in this MTDA package.",
        "? 'from run_001_bending.csv · threshold ' + (this.run.bendThreshold != null ? this.run.bendThreshold + ' %' : '—')": "? 'from ' + this.run.id + '_bending.csv · threshold ' + (this.run.bendThreshold != null ? this.run.bendThreshold + ' %' : '—')",
        ": 'from run_001_stress_strain.csv + …_experiment_bound.csv — one figure, two traces',": ": 'from ' + this.run.id + '_stress_strain.csv + …_experiment_bound.csv — one figure, two traces',",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    source = source.replace(
        "    this.run = D.runs.find(r => r.id === 'run_001') || D.runs[0];\n"
        "    this.boundaryEnd = D.run001.boundaryEnd;\n"
        "    this.original = D.run001.curve;\n"
        "    this.curveData = this.original.map(d => Object.assign({}, d));",
        "    const initialState = window.MTDA_INITIAL_STATE || {};\n"
        "    this.run = D.runs.find(r => r.id === (initialState.runId || this.state.runId || 'run_001')) || D.runs[0];\n"
        "    const runPayload = this.runPayload(this.run.id);\n"
        "    this.boundaryEnd = runPayload.boundaryEnd;\n"
        "    this.original = runPayload.curve;\n"
        "    this.curveData = this.original.map(d => Object.assign({}, d));",
    )
    source = source.replace(
        "    this.setState({ ready: true, presets });",
        "    this.setState(Object.assign({ ready: true, presets }, window.MTDA_INITIAL_STATE || {}));\n"
        "    if ((window.MTDA_INITIAL_STATE || {}).page === 'run') setTimeout(() => this.embed(), 60);",
    )
    source = source.replace(
        "  defaultStyle(fig) {",
        "  runPayload(runId) {\n"
        "    const payload = (this.D.runCurves && this.D.runCurves[runId]) || this.D.run001 || {};\n"
        "    return { boundaryEnd: payload.boundaryEnd || 0, curve: (payload.curve || []).map(d => Object.assign({}, d)) };\n"
        "  }\n"
        "  activateRun(run) {\n"
        "    const payload = this.runPayload(run.id);\n"
        "    if (!payload.curve.length) { this.setState({ page: 'stub', stub: run.id }); return; }\n"
        "    this.run = run;\n"
        "    this.boundaryEnd = payload.boundaryEnd;\n"
        "    this.original = payload.curve;\n"
        "    this.curveData = this.original.map(d => Object.assign({}, d));\n"
        "    this.styles = { summary: this.defaultStyle('summary'), bending: this.defaultStyle('bending') };\n"
        "    this.layersMap = { summary: this.defaultLayers('summary'), bending: this.defaultLayers('bending') };\n"
        "    this.specOverrides = { summary: null, bending: null };\n"
        "    this.setState({ page: 'run', runId: run.id, figure: 'summary', segment: 'style', dataOpen: false, specOpen: false, datasetSel: 'full', dataPage: 0, resetGen: (this.state.resetGen || 0) + 1 });\n"
        "    setTimeout(() => this.embed(), 60);\n"
        "  }\n"
        "  runNavigationHint() {\n"
        "    const runs = (this.D && this.D.runs) || [];\n"
        "    if (!runs.length || !this.run) return '';\n"
        "    const index = Math.max(0, runs.findIndex(r => r.id === this.run.id));\n"
        "    const prev = runs[(index - 1 + runs.length) % runs.length].id;\n"
        "    const next = runs[(index + 1) % runs.length].id;\n"
        "    return '← ' + prev + ' · ' + next + ' →';\n"
        "  }\n"
        "\n"
        "  defaultStyle(fig) {",
    )
    source = source.replace(
        "      id: r.id, spec: r.specimen, path: this.platePaths[r.id] || '',\n"
        "      on: r.id === 'run_001'\n"
        "        ? () => { this.setState({ page: 'run' }); setTimeout(() => this.embed(), 60); }\n"
        "        : () => this.setState({ page: 'stub', stub: r.id })",
        "      id: r.id, spec: r.specimen, path: this.platePaths[r.id] || '',\n"
        "      on: () => this.activateRun(r)",
    )
    source = source.replace(
        "    const layerSrc = { full: 'run_001_stress_strain.csv', bound: 'run_001_…_experiment_bound.csv', trace: 'run_001_bending.csv' };",
        "    const layerSrc = { full: this.runStressFile(), bound: this.runBoundShortFile(), trace: this.runBendingFile() };",
    )
    source = source.replace(
        "  runNavigationHint() {",
        "  runStressFile() { return this.run.id + '_stress_strain.csv'; }\n"
        "  runBoundFile() { return this.run.id + '_stress_strain_experiment_bound.csv'; }\n"
        "  runBoundShortFile() { return this.run.id + '_…_experiment_bound.csv'; }\n"
        "  runBendingFile() { return this.run.id + '_bending.csv'; }\n"
        "  runNavigationHint() {",
    )
    return source.replace(
        "      runId: this.run.id,\n",
        "      runId: this.run.id,\n"
        "      runNavHint: this.runNavigationHint(), runFullRows: this.curveData.length,\n"
        "      runBoundRows: this.curveData.filter(d => d.inBound).length,\n"
        "      runStressFile: this.runStressFile(), runBoundFile: this.runBoundFile(), runBoundShortFile: this.runBoundShortFile(), runBendingFile: this.runBendingFile(),\n"
        "      runStressHref: 'dataset/02_processed/' + this.runStressFile(), runBoundHref: 'dataset/02_processed/' + this.runBoundFile(), runBendingHref: 'dataset/02_processed/' + this.runBendingFile(),\n",
    )


def _js_string_pattern(pattern: str, expression: str) -> str:
    marker = "{run_id}"
    if marker not in pattern:
        return _js_single_quote(pattern)
    before, after = pattern.split(marker, 1)
    parts: list[str] = []
    if before:
        parts.append(_js_single_quote(before))
    parts.append(expression)
    if after:
        parts.append(_js_single_quote(after))
    return " + ".join(parts)


def _js_single_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r") + "'"


def _script_safe(script: str) -> str:
    return script.replace("<script", "<\\x73cript").replace("</script>", "<\\/script>")


_SVG_DATA_POINTS_SYNC_SCRIPT = r"""
(() => {
  const validPoints = (value) =>
    typeof value === 'string' &&
    /^[\d\s,.\-+eE]+$/.test(value.trim()) &&
    /\d/.test(value);
  const sync = (root = document) => {
    root.querySelectorAll('polyline[data-mtda-points]').forEach((node) => {
      const value = node.getAttribute('data-mtda-points') || '';
      if (validPoints(value)) node.setAttribute('points', value);
    });
  };
  sync();
  new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === 'attributes' && record.target?.matches?.('polyline[data-mtda-points]')) {
        sync(record.target.ownerDocument || document);
        return;
      }
      for (const node of record.addedNodes || []) {
        if (node?.querySelectorAll) {
          sync(node);
          return;
        }
      }
    }
  }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-mtda-points'] });
})();
"""


def _json_safe(value: Any) -> Any:
    import math

    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
