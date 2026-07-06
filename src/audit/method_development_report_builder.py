from __future__ import annotations

import html
import json
from typing import Any


class MethodDevelopmentReportBuilder:
    """Build the operation-wise method development workbench."""

    def build(self, trace: dict[str, Any], *, api_enabled: bool = False) -> str:
        payload = json.dumps(trace)
        api_flag = "true" if api_enabled else "false"
        title = f"Method Development Workbench - {trace.get('method', {}).get('method_id', 'method')}"
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <script src=\"https://cdn.jsdelivr.net/npm/vega@5\"></script>
  <script src=\"https://cdn.jsdelivr.net/npm/vega-lite@5\"></script>
  <script src=\"https://cdn.jsdelivr.net/npm/vega-embed@6\"></script>
  <style>
    :root {{ --blue:#1559c7; --ink:#172033; --muted:#667085; --line:#d9dee7; --panel:#fff; --bg:#f5f7fb; --violet:#7651d7; --ok:#167043; --warn:#9a5b00; --bad:#a12626; --timeline-width:282px; --details-width:342px; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Arial,sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ min-height:64px; background:#071321; color:#fff; display:flex; align-items:center; justify-content:space-between; gap:18px; padding:10px 18px; box-shadow:0 2px 12px #0003; }}
    header .sub {{ color:#b9c4d4; font-size:12px; }}
    button, select {{ font:inherit; }}
    .run-selector {{ display:grid; grid-template-columns:auto minmax(260px,420px); align-items:center; gap:8px 12px; min-width:420px; }}
    .run-selector label {{ font-size:12px; font-weight:700; color:#d7e1f0; text-transform:uppercase; letter-spacing:.02em; }}
    .run-selector select {{ width:100%; border:1px solid #31445f; background:#101d2e; color:#fff; border-radius:8px; padding:8px 10px; }}
    .run-meta-header {{ grid-column:2; color:#aebbd0; font-size:12px; min-height:16px; }}
    .layout {{ display:grid; grid-template-columns:var(--timeline-width) minmax(620px,1fr) var(--details-width); gap:10px; padding:10px; height:calc(100vh - 64px); transition:grid-template-columns .18s ease; }}
    body.timeline-collapsed {{ --timeline-width:44px; }}
    body.details-collapsed {{ --details-width:44px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; overflow:hidden; min-height:0; display:flex; flex-direction:column; }}
    .panel h2 {{ font-size:14px; margin:0; }}
    .panel-heading {{ min-height:45px; display:flex; align-items:center; justify-content:space-between; gap:8px; padding:0 10px 0 14px; border-bottom:1px solid var(--line); }}
    .collapse-btn {{ border:1px solid var(--line); background:#fff; color:var(--muted); border-radius:7px; min-width:30px; height:30px; cursor:pointer; }}
    .collapse-btn:hover {{ color:var(--ink); border-color:#b8c2d3; }}
    .rail-label {{ display:none; flex:1; align-items:center; justify-content:center; color:var(--muted); font-size:12px; font-weight:800; writing-mode:vertical-rl; transform:rotate(180deg); letter-spacing:.04em; text-transform:uppercase; }}
    .side-panel.collapsed .panel-heading, .side-panel.collapsed .scroll {{ display:none; }}
    .side-panel.collapsed .rail-label {{ display:flex; }}
    .scroll {{ overflow:auto; min-height:0; }}
    .run {{ padding:12px 14px; border-bottom:1px solid #edf0f5; cursor:pointer; }}
    .run.active {{ outline:2px solid var(--blue); outline-offset:-2px; background:#eef5ff; }}
    .run-title {{ font-weight:700; font-size:13px; }}
    .run-meta {{ font-size:12px; color:var(--muted); margin-top:3px; }}
    .badge {{ display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; background:#eef2f6; margin-left:4px; }}
    .badge.warn {{ background:#fff4df; color:var(--warn); }} .badge.bad {{ background:#ffe8e8; color:var(--bad); }} .badge.ok {{ background:#e8f8ee; color:var(--ok); }}
    .phase {{ padding:12px 14px 4px; font-weight:800; color:var(--blue); font-size:13px; }}
    .step {{ display:flex; gap:8px; align-items:flex-start; padding:8px 12px; cursor:pointer; border-left:4px solid transparent; }}
    .step.active {{ background:#f0ebff; border-left-color:var(--violet); }}
    .dot {{ width:16px; height:16px; border-radius:50%; border:2px solid var(--blue); background:#fff; flex:0 0 auto; margin-top:1px; box-shadow:0 0 0 2px #fff; }}
    .step.reduce .dot {{ border-color:var(--violet); }}
    .dot.ok {{ background:var(--ok); border-color:var(--ok); }}
    .dot.warn {{ background:var(--warn); border-color:var(--warn); }}
    .dot.bad {{ background:var(--bad); border-color:var(--bad); }}
    .dot.idle {{ background:#98a2b3; border-color:#98a2b3; }}
    .step-title {{ font-size:12px; font-weight:650; }}
    .step-sub {{ font-size:11px; color:var(--muted); margin-top:2px; }}
    .tabs {{ display:flex; gap:18px; padding:0 16px; height:48px; align-items:end; border-bottom:1px solid var(--line); }}
    .tab {{ padding:0 0 12px; color:var(--muted); cursor:pointer; }}
    .tab.active {{ color:var(--blue); border-bottom:3px solid var(--blue); font-weight:700; }}
    .chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:14px; }}
    .stepwise-plot-list {{ display:grid; grid-template-columns:1fr; gap:12px; padding:0 14px 14px; }}
    .chart-card {{ border:1px solid var(--line); border-radius:10px; background:#fff; padding:12px; min-height:330px; }}
    .chart-card h3 {{ margin:0 0 8px; font-size:13px; }}
    .chart {{ width:100%; min-height:280px; }}
    .hint {{ color:var(--muted); font-size:12px; margin:8px 0 0; }}
    .context-banner {{ display:none; margin:12px 14px 0; padding:12px; border:1px solid var(--line); border-left:5px solid var(--blue); border-radius:10px; background:#f8fbff; }}
    .context-banner h3 {{ margin:0 0 6px; font-size:14px; }}
    .context-banner p {{ margin:0 0 8px; color:var(--muted); font-size:12px; line-height:1.4; }}
    .pill-row {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }}
    .context-pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:3px 8px; background:#fff; color:var(--ink); font-size:11px; }}
    .evidence-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin:10px 0 14px; }}
    .evidence-card {{ border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:10px; background:#fff; padding:10px; min-height:92px; }}
    .evidence-card h3 {{ margin:0 0 5px; font-size:13px; }}
    .context-link {{ display:inline-block; margin:3px 5px 3px 0; border:1px solid var(--line); border-radius:6px; padding:5px 7px; color:var(--blue); text-decoration:none; background:#fff; font-weight:700; font-size:12px; }}
    .data-summary {{ display:flex; gap:8px; flex-wrap:wrap; margin:0 0 12px; }}
    .data-pill {{ border:1px solid var(--line); border-radius:999px; padding:4px 9px; background:#fff; color:var(--muted); font-size:12px; }}
    .new-column-note {{ border-left:4px solid var(--ok); background:#f0fbf4; padding:9px 11px; margin:0 0 12px; border-radius:8px; font-size:12px; }}
    th.new-col, td.new-col {{ background:#e8f8ee; }}
    .details {{ padding:12px 14px; border-bottom:1px solid #edf0f5; }}
    .details h3 {{ font-size:12px; text-transform:uppercase; color:var(--muted); margin:0 0 7px; }}
    .kv {{ display:grid; grid-template-columns:112px 1fr; gap:5px; font-size:12px; margin-bottom:4px; }}
    .kv .k {{ color:var(--muted); }}
    pre {{ white-space:pre-wrap; background:#f7f9fc; border:1px solid var(--line); padding:10px; border-radius:8px; font-size:11px; max-height:230px; overflow:auto; }}
    textarea {{ width:100%; height:310px; font-family:Consolas,Menlo,monospace; font-size:12px; border:1px solid var(--line); border-radius:8px; padding:10px; }}
    .editor-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:14px; }}
    .recipe-shell {{ display:grid; grid-template-columns:minmax(420px,1fr) 340px; gap:12px; padding:14px; }}
    .recipe-shell .editor-grid {{ padding:0; }}
    .operation-guide {{ border:1px solid var(--line); border-radius:10px; background:#fff; min-height:0; overflow:auto; padding:12px; }}
    .operation-guide h3 {{ margin:0 0 8px; font-size:13px; }}
    .guide-op {{ border-top:1px solid #edf0f5; padding:10px 0; }}
    .guide-op:first-of-type {{ border-top:0; }}
    .toolbar {{ padding:10px 14px; border-top:1px solid var(--line); display:flex; gap:8px; align-items:center; }}
    .btn {{ border:1px solid var(--line); background:#fff; border-radius:8px; padding:7px 10px; cursor:pointer; }}
    .btn.primary {{ background:var(--blue); border-color:var(--blue); color:#fff; }}
    table {{ width:100%; border-collapse:collapse; font-size:12px; }} th,td {{ border-bottom:1px solid #edf0f5; padding:6px; text-align:left; }} th {{ background:#f7f9fc; }}
    .vg-tooltip {{ max-width:340px !important; white-space:normal !important; overflow-wrap:anywhere !important; pointer-events:none !important; }}
    .vg-tooltip table {{ width:auto !important; table-layout:auto !important; border-collapse:collapse !important; font-size:12px !important; background:#fff !important; }}
    .vg-tooltip th, .vg-tooltip td {{ padding:2px 6px !important; border:0 !important; white-space:nowrap !important; overflow-wrap:normal !important; }}
    @media (max-width: 1200px) {{ :root {{ --details-width:44px; }} .layout {{ grid-template-columns:var(--timeline-width) minmax(500px,1fr) var(--details-width); }} body:not(.details-collapsed) {{ --details-width:44px; }} .details-panel .panel-heading, .details-panel .scroll {{ display:none; }} .details-panel .rail-label {{ display:flex; }} .recipe-shell {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<header>
  <div class=\"run-selector\"><label for=\"runSelect\">Run / Specimen</label><select id=\"runSelect\"></select><div id=\"runMeta\" class=\"run-meta-header\"></div></div>
  <div class=\"sub\" id=\"status\">Static trace loaded</div>
</header>
<div class=\"layout\">
  <aside id=\"timelinePanel\" class=\"panel side-panel timeline-panel\"><div class=\"panel-heading\"><h2>Operation Timeline</h2><button id=\"toggleTimeline\" class=\"collapse-btn\" title=\"Collapse operation timeline\">‹</button></div><div id=\"steps\" class=\"scroll\"></div><div class=\"rail-label\">Timeline</div></aside>
  <main class=\"panel\">
    <div class=\"tabs\"><div class=\"tab active\" data-tab=\"graph\">Graph</div><div class=\"tab\" data-tab=\"data\">Data</div><div class=\"tab\" data-tab=\"readiness\">Readiness</div><div class=\"tab\" data-tab=\"validation\">Validation</div><div class=\"tab\" data-tab=\"acceptance\">Acceptance</div><div class=\"tab\" data-tab=\"evidence\">Evidence</div><div class=\"tab\" data-tab=\"recipes\">Recipe editor</div></div>
    <div id=\"contextBanner\" class=\"context-banner\"></div>
    <section id=\"graphTab\" class=\"scroll\"><div class=\"chart-grid\"><div class=\"chart-card\"><h3>Before operation</h3><div id=\"beforeChart\" class=\"chart\"></div><p class=\"hint\">Hover for values. Drag/pinch/scroll to zoom using Vega controls.</p></div><div class=\"chart-card\"><h3>After operation</h3><div id=\"afterChart\" class=\"chart\"></div><p class=\"hint\">Operation-specific overlays show anchors, windows, and selected points.</p></div></div><div id=\"stepwisePlots\" class=\"stepwise-plot-list\"></div></section>
    <section id=\"dataTab\" class=\"scroll\" style=\"display:none;padding:14px;\"><div id=\"dataTable\"></div></section>
    <section id=\"readinessTab\" class=\"scroll\" style=\"display:none;padding:14px;\"><div id=\"readinessPanel\"></div></section>
    <section id=\"validationTab\" class=\"scroll\" style=\"display:none;padding:14px;\"><div id=\"validationPanel\"></div></section>
    <section id=\"acceptanceTab\" class=\"scroll\" style=\"display:none;padding:14px;\"><div id=\"acceptancePanel\"></div></section>
    <section id=\"evidenceTab\" class=\"scroll\" style=\"display:none;padding:14px;\"><div id=\"evidencePanel\"></div></section>
    <section id=\"recipesTab\" class=\"scroll\" style=\"display:none;\"><div class=\"recipe-shell\"><div><div class=\"editor-grid\"><div><h3>resolve_recipe.yaml</h3><textarea id=\"resolveEditor\"></textarea></div><div><h3>reduce_recipe.yaml</h3><textarea id=\"reduceEditor\"></textarea></div></div><div class=\"toolbar\"><button class=\"btn primary\" id=\"rerunBtn\">Run edited recipes</button><button class=\"btn\" id=\"resetBtn\">Reset editors</button><span id=\"apiNote\" class=\"hint\"></span></div></div><aside class=\"operation-guide\"><h3>Operation Guide</h3><p class=\"hint\">Available operations from this method trace, with observed inputs, parameters, outputs, and implementation paths.</p><div id=\"operationGuide\"></div></aside></div></section>
  </main>
  <aside id=\"detailsPanel\" class=\"panel side-panel details-panel right\"><div class=\"panel-heading\"><h2>Operation Details</h2><button id=\"toggleDetails\" class=\"collapse-btn\" title=\"Collapse operation details\">›</button></div><div id=\"details\" class=\"scroll\"></div><div class=\"rail-label\">Details</div></aside>
</div>
<script>
let TRACE = {payload};
const API_ENABLED = {api_flag};
let selectedRun = (TRACE.runs && TRACE.runs[0] && TRACE.runs[0].run_id) || null;
let selectedStep = null;
const statusEl = document.getElementById('status');
const $ = id => document.getElementById(id);
function esc(v) {{ return String(v ?? '').replace(/[&<>\"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[c])); }}
function fmt(v) {{ if (v === null || v === undefined) return ''; if (typeof v === 'number') return Number.isFinite(v) ? v.toPrecision(6) : String(v); if (typeof v === 'object') return JSON.stringify(v); return String(v); }}
function readable(v) {{ return String(v ?? '').replaceAll('_',' '); }}
function rowsFrom(value) {{ if (Array.isArray(value)) return value; if (value && Array.isArray(value.records)) return value.records; if (value && typeof value === 'object') return [value]; return []; }}
function routeParams() {{ const raw = String(location.hash || '').replace(/^#/, ''); return new URLSearchParams(raw); }}
function contextHref(params) {{ return '#' + new URLSearchParams(params).toString(); }}
function contextLink(label, params) {{ return `<a class=\"context-link\" href=\"${{contextHref(params)}}\">${{esc(label)}}</a>`; }}
function activateTab(name) {{ const selected = name || 'graph'; document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === selected)); ['graph','data','readiness','validation','acceptance','evidence','recipes'].forEach(tab => {{ const panel=$(tab+'Tab'); if(panel) panel.style.display = selected===tab ? '' : 'none'; }}); }}
function applyRoute() {{
  const route = routeParams();
  const previousRun = selectedRun;
  const run = route.get('run');
  if (run && (TRACE.runs || []).some(r => r.run_id === run)) selectedRun = run;
  if (selectedRun !== previousRun) selectedStep = null;
  const opRef = route.get('operation') || route.get('operation_id') || route.get('step');
  if (opRef) {{
    const ops = opsForRun(selectedRun);
    selectedStep = ops.find(o => String(o.operation_id) === opRef || String(o.recipe_step_id) === opRef || String(o.sequence) === opRef || String(o.operation_type) === opRef) || selectedStep;
  }} else if (['report','amendments','audit','overview'].includes(route.get('context') || '')) {{
    selectedStep = null;
  }}
}}
function contextSummary() {{
  const route = routeParams();
  const context = route.get('context') || route.get('tab') || 'overview';
  const run = route.get('run') || (['report','amendments','audit','overview'].includes(context) ? '' : (selectedRun || ''));
  const check = route.get('check') || '';
  const flag = route.get('flag') || '';
  const field = route.get('field') || '';
  const operation = route.get('operation') || route.get('operation_id') || route.get('step') || '';
  let title = 'Workbench evidence navigator';
  let reason = 'Use this page for operation-level replay and evidence inspection. Reports and the wizard link here for detailed context.';
  if (context === 'validation') {{ title = 'Validation evidence context'; reason = 'Review validation checks, deviations, and linked method operations for the selected run.'; }}
  if (context === 'acceptance') {{ title = 'Acceptance and selection context'; reason = 'Review run flags, discharge reasons, selection membership, and curve-family evidence.'; }}
  if (context === 'readiness') {{ title = 'Readiness evidence context'; reason = 'Review method-input readiness, missing inputs, and resolved package bindings.'; }}
  if (context === 'report' || context === 'amendments') {{ title = 'Report completion and amendment context'; reason = 'Review report-only missing fields, overrides, finalization records, and values used without changing MTDP.'; }}
  if (context === 'aggregate') {{ title = 'Aggregate/report evidence context'; reason = 'Review final report runs, selected aggregate evidence, and the dataset acceptance trail.'; }}
  return {{title, reason, run, check, flag, field, operation, context}};
}}
function renderContextBanner() {{
  const ctx = contextSummary();
  const banner = $('contextBanner');
  const pills = [];
  if (ctx.run) pills.push(['Run', ctx.run]);
  if (ctx.check) pills.push(['Check/field', ctx.check]);
  if (ctx.flag) pills.push(['Flag', ctx.flag]);
  if (ctx.field) pills.push(['Report field', ctx.field.replaceAll('_',' ')]);
  if (ctx.operation) pills.push(['Operation', ctx.operation]);
  const links = [
    contextLink('Overview', {{tab:'evidence', context:'overview', run:ctx.run}}),
    contextLink('Run checks', {{tab:'validation', context:'validation', run:ctx.run, check:ctx.check}}),
    contextLink('Acceptance flags', {{tab:'acceptance', context:'acceptance', run:ctx.run, flag:ctx.flag}}),
    contextLink('Report amendments', {{tab:'evidence', context:'amendments', field:ctx.field || 'loading_method'}}),
  ].join('');
  banner.innerHTML = `<h3>${{esc(ctx.title)}}</h3><p>${{esc(ctx.reason)}}</p><div class=\"pill-row\">${{pills.map(([k,v])=>`<span class=\"context-pill\"><b>${{esc(k)}}:</b> ${{esc(v)}}</span>`).join('')}}${{links}}</div>`;
  banner.style.display = 'block';
}}
function runRows(runId) {{ return (TRACE.curve_rows_by_run && TRACE.curve_rows_by_run[runId]) || []; }}
function fullRunRows(runId) {{ return (TRACE.full_curve_rows_by_run && TRACE.full_curve_rows_by_run[runId]) || runRows(runId); }}
function opsForRun(runId) {{ return (TRACE.operations || []).filter(o => o.run_id === runId); }}
function currentOp() {{ return selectedStep; }}
function currentRows() {{ return runRows(selectedRun); }}
function fieldRows(rows, fields) {{ return rows.map(r => Object.fromEntries(fields.map(f => [f, r[f]]))); }}
function selectedRunRecord() {{ return (TRACE.runs || []).find(r => r.run_id === selectedRun) || {{}}; }}
function runOptionLabel(r) {{
  const specimen = r.specimen_name ? ` - ${{r.specimen_name}}` : '';
  const selection = r.included_in_default ? 'default' : 'not default';
  const acceptance = r.acceptance_state || 'accepted';
  return `${{r.run_id}}${{specimen}} - ${{acceptance}} - ${{selection}}`;
}}
function renderRunSelector() {{
  const selector = $('runSelect');
  if(!selector) return;
  selector.innerHTML = (TRACE.runs || []).map(r => `<option value=\"${{esc(r.run_id)}}\" ${{r.run_id===selectedRun?'selected':''}}>${{esc(runOptionLabel(r))}}</option>`).join('');
  selector.value = selectedRun || '';
  selector.onchange = () => {{ selectedRun = selector.value; selectedStep = null; renderAll(); }};
  const r = selectedRunRecord();
  const meta = [];
  if (r.validation_status) meta.push(`validation ${{validationLabel(r.validation_status)}}`);
  if (r.acceptance_state) meta.push(`acceptance ${{r.acceptance_state}}`);
  if (r.acceptance_flags) meta.push(`${{r.acceptance_flags}} flags`);
  meta.push(r.included_in_default ? 'included in default set' : 'outside default set');
  $('runMeta').textContent = meta.join(' - ');
}}
function statusDotClass(op) {{
  const status = String(op.validation_status || op.status || '').toLowerCase();
  if (status.includes('fail') || status.includes('error')) return 'bad';
  if (status.includes('warn') || (op.warnings || []).length) return 'warn';
  if (status.includes('pass') || status === 'completed') return 'ok';
  return 'idle';
}}
function outputColumnNames(op) {{
  const out = op && op.outputs && typeof op.outputs === 'object' ? op.outputs : {{}};
  return Object.keys(out).filter(k => !['boundary_record','experiment_boundaries','bending_diagnostic'].includes(k));
}}
function cumulativeColumns(op) {{
  const rows = currentRows();
  const available = new Set(Object.keys(rows[0] || {{}}));
  const columns = ['point_index'];
  for (const item of opsForRun(selectedRun)) {{
    for (const key of outputColumnNames(item)) if (available.has(key) && !columns.includes(key)) columns.push(key);
    if (op && item.sequence === op.sequence) break;
  }}
  if (columns.length === 1) {{
    for (const key of ['load_N','load_N_raw','time_s','extension_mm','front_strain_raw','rear_strain_raw','front_strain_abs','rear_strain_abs','mean_strain','stress_MPa']) {{
      if (available.has(key) && !columns.includes(key)) columns.push(key);
    }}
  }}
  return columns.filter(c => available.has(c));
}}
function newColumnsFor(op) {{
  const available = new Set(Object.keys((currentRows()[0] || {{}})));
  return outputColumnNames(op).filter(c => available.has(c));
}}
function tableWithColumns(rows, columns, highlights) {{
  const highlightSet = new Set(highlights || []);
  if(!rows.length || !columns.length) return '<p>No rows.</p>';
  return '<table><thead><tr>'+columns.map(k=>`<th class=\"${{highlightSet.has(k)?'new-col':''}}\">${{esc(k)}}</th>`).join('')+'</tr></thead><tbody>'+rows.slice(0,500).map(r=>'<tr>'+columns.map(k=>`<td class=\"${{highlightSet.has(k)?'new-col':''}}\">${{esc(fmt(r[k]))}}</td>`).join('')+'</tr>').join('')+'</tbody></table>';
}}
function renderGraphSequence() {{
  const target = $('stepwisePlots');
  if(!target) return;
  const ops = opsForRun(selectedRun);
  target.innerHTML = `<div class=\"chart-card\"><h3>Stepwise plot sequence</h3><p class=\"hint\">Plots below follow the selected run through the method process. Select any operation in the timeline to focus the paired before/after view above.</p></div>` + ops.map(op => `<div class=\"chart-card\"><h3>${{String(op.sequence).padStart(2,'0')}} ${{esc(op.recipe_step_label || op.operation_type)}}</h3><div id=\"stepChart_${{op.sequence}}\" class=\"chart\"></div></div>`).join('');
  ops.forEach(op => embed(`stepChart_${{op.sequence}}`, specFor(op,false)));
}}
function operationGuideRows() {{
  const grouped = new Map();
  (TRACE.operations || []).forEach(op => {{
    const key = op.operation_type || 'operation';
    const row = grouped.get(key) || {{operation:key, implementation_path:op.implementation_path || '', inputs:new Set(), parameters:new Set(), outputs:new Set()}};
    Object.keys(op.inputs || {{}}).forEach(k => row.inputs.add(k));
    Object.keys(op.parameters || {{}}).forEach(k => row.parameters.add(k));
    Object.keys(op.outputs || {{}}).forEach(k => row.outputs.add(k));
    if (!row.implementation_path && op.implementation_path) row.implementation_path = op.implementation_path;
    grouped.set(key, row);
  }});
  return [...grouped.values()].map(row => ({{operation:row.operation, implementation_path:row.implementation_path, inputs:[...row.inputs].join(', '), parameters:[...row.parameters].join(', '), outputs:[...row.outputs].join(', ')}})).sort((a,b)=>a.operation.localeCompare(b.operation));
}}
function renderOperationGuide() {{
  const guide = $('operationGuide');
  if(!guide) return;
  guide.innerHTML = operationGuideRows().map(row => `<div class=\"guide-op\"><b>${{esc(row.operation)}}</b><div class=\"hint\">Inputs: ${{esc(row.inputs || 'none observed')}}</div><div class=\"hint\">Parameters: ${{esc(row.parameters || 'none observed')}}</div><div class=\"hint\">Outputs: ${{esc(row.outputs || 'none observed')}}</div><div class=\"hint\">${{esc(row.implementation_path || '')}}</div></div>`).join('');
}}
function baseSpec(values, x, y, title, colorField=null) {{ return {{ '$schema':'https://vega.github.io/schema/vega-lite/v5.json', width:'container', height:280, data:{{values}}, mark:{{type:'line', clip:true, point:false}}, params:[{{name:'grid', select:'interval', bind:'scales'}}], encoding:{{ x:{{field:x,type:'quantitative',title:x}}, y:{{field:y,type:'quantitative',title:y}}, color: colorField ? {{field:colorField,type:'nominal'}} : undefined, tooltip:Object.keys(values[0] || {{}}).slice(0,12).map(f=>({{field:f,type: typeof (values[0]||{{}})[f] === 'number' ? 'quantitative':'nominal'}})) }} }}; }}
function overlaySeries(rows, series, x='point_index') {{ const values=[]; rows.forEach(r => series.forEach(s => {{ if (r[s] !== '' && r[s] !== null && r[s] !== undefined) values.push({{x:r[x] ?? r.point_index, value:Number(r[s]), series:s, point_index:r.point_index}}); }})); return baseSpec(values, 'x', 'value', 'overlay', 'series'); }}
function stressSpec(rows) {{ return baseSpec(rows.filter(r=>r.mean_strain!=null && r.stress_MPa!=null), 'mean_strain', 'stress_MPa'); }}
function loadSpec(rows) {{ return overlaySeries(rows, ['load_N','load_N_raw']); }}
function maxMarkerSpec(rows, op) {{ const idx = Number(Object.values(op.outputs||{{}}).find(v => Number.isInteger(v)) ?? (op.evidence||{{}}).selected_index); const values=rows.filter(r=>r.mean_strain!=null && r.stress_MPa!=null); const pt=values.find(r=>Number(r.point_index)===idx); return {{ '$schema':'https://vega.github.io/schema/vega-lite/v5.json', width:'container', height:280, layer:[ stressSpec(values), {{data:{{values:pt?[pt]:[]}}, mark:{{type:'point', filled:true, size:110, color:'#d9480f'}}, encoding:{{x:{{field:'mean_strain',type:'quantitative'}}, y:{{field:'stress_MPa',type:'quantitative'}}, tooltip:[{{field:'point_index'}},{{field:'mean_strain'}},{{field:'stress_MPa'}}]}} }} ] }}; }}
function chordSpec(rows, op) {{ const p=op.parameters||{{}}; const x1=Number(p.x1 ?? 0.0005), x2=Number(p.x2 ?? 0.0025); const ev=op.evidence||{{}}; const a=ev.left_anchor, b=ev.right_anchor; const anchors=[a?{{mean_strain:a.x,stress_MPa:a.y,anchor:'x1'}}:null,b?{{mean_strain:b.x,stress_MPa:b.y,anchor:'x2'}}:null].filter(Boolean); return {{ '$schema':'https://vega.github.io/schema/vega-lite/v5.json', width:'container', height:280, layer:[ stressSpec(rows), {{data:{{values:[{{x:x1}},{{x:x2}}]}}, mark:{{type:'rule',strokeDash:[6,4],color:'#167043'}}, encoding:{{x:{{field:'x',type:'quantitative'}}}}}}, {{data:{{values:anchors}}, mark:{{type:'point',filled:true,size:90,color:'#167043'}}, encoding:{{x:{{field:'mean_strain',type:'quantitative'}}, y:{{field:'stress_MPa',type:'quantitative'}}, tooltip:[{{field:'anchor'}},{{field:'mean_strain'}},{{field:'stress_MPa'}}]}}}}, {{data:{{values:anchors}}, mark:{{type:'line',strokeDash:[4,3],color:'#333'}}, encoding:{{x:{{field:'mean_strain',type:'quantitative'}}, y:{{field:'stress_MPa',type:'quantitative'}}}}}} ] }}; }}
function bendingSpec(rows, op) {{
  const diag = ((op.outputs||{{}}).bending_diagnostic||{{}});
  const win = diag.load_window_N || ((op.evidence||{{}}).load_window_N) || [];
  const threshold = Number(diag.threshold_percent ?? ((diag.pointwise||{{}}).threshold_percent) ?? 10);
  const values=[];
  rows.forEach(r=>{{
    const f=Number(r.front_strain_abs ?? Math.abs(Number(r.front_strain_raw ?? r.front_strain)));
    const rr=Number(r.rear_strain_abs ?? Math.abs(Number(r.rear_strain_raw ?? r.rear_strain)));
    const load=Number(r.load_N);
    if(Number.isFinite(f)&&Number.isFinite(rr)&&Number.isFinite(load)&&Math.abs(f+rr)>0) {{
      const bending = Math.abs(f-rr)/Math.abs(f+rr)*100;
      values.push({{load_N:load,bending_percent:bending,point_index:r.point_index,exceeds_threshold:bending>threshold}});
    }}
  }});
  const exceedanceValues = values.filter(v=>v.exceeds_threshold);
  const segmentValues = (diag.segments||[]).map(s=>({{segment_id:s.segment_id, start_load_N:Number(s.start_load_N), end_load_N:Number(s.end_load_N), segment_classification:s.segment_classification, max_bending_percent:s.max_bending_percent, point_count:s.point_count}})).filter(s=>Number.isFinite(s.start_load_N)&&Number.isFinite(s.end_load_N));
  return {{ '$schema':'https://vega.github.io/schema/vega-lite/v5.json', width:'container', height:280, layer:[
    {{data:{{values:segmentValues}}, mark:{{type:'rect',opacity:0.12,color:'#a12626'}}, encoding:{{x:{{field:'start_load_N',type:'quantitative'}}, x2:{{field:'end_load_N'}}, tooltip:[{{field:'segment_id'}},{{field:'segment_classification'}},{{field:'point_count'}},{{field:'max_bending_percent'}}]}}}},
    baseSpec(values,'load_N','bending_percent'),
    {{data:{{values:exceedanceValues}}, mark:{{type:'point',filled:true,size:55,color:'#a12626'}}, encoding:{{x:{{field:'load_N',type:'quantitative'}}, y:{{field:'bending_percent',type:'quantitative'}}, tooltip:[{{field:'point_index'}},{{field:'load_N'}},{{field:'bending_percent'}}]}}}},
    {{data:{{values:win.length?[{{x:win[0]}},{{x:win[1]}}]:[]}}, mark:{{type:'rule',strokeDash:[6,4],color:'#d9480f'}}, encoding:{{x:{{field:'x',type:'quantitative'}}}}}},
    {{data:{{values:[{{y:threshold}}]}}, mark:{{type:'rule',strokeDash:[4,4],color:'#a12626'}}, encoding:{{y:{{field:'y',type:'quantitative'}}}}}}
  ] }}; }}
function boundarySpec(rows, op) {{
  const record = ((op.evidence||{{}}).boundary_record || (op.outputs||{{}}).experiment_boundaries || {{}});
  const interval = record.analysis_interval || {{}};
  const start = Number(interval.start_index ?? record.start_index ?? 0);
  const end = Number(interval.end_index ?? record.end_index ?? 0);
  const events = (record.events || []).map(e => ({{point_index:Number(e.index), event_id:e.event_id, value:e.value, diagnostic_only:e.diagnostic_only}})).filter(e => Number.isFinite(e.point_index));
  const values = rows.filter(r=>r.point_index!=null && r.load_N!=null);
  const post = values.filter(r=>Number(r.point_index) >= end);
  const maxEvent = events.filter(e=>e.event_id==='max_abs_load');
  const firstNegative = events.filter(e=>e.event_id==='first_negative_slope');
  const prebreak = events.filter(e=>e.event_id==='prebreak_curvature');
  const decline = events.filter(e=>e.event_id==='sustained_post_peak_decline');
  return {{ '$schema':'https://vega.github.io/schema/vega-lite/v5.json', width:'container', height:280, layer:[
    {{data:{{values}}, mark:{{type:'line',clip:true,color:'#1559c7'}}, encoding:{{x:{{field:'point_index',type:'quantitative',title:'point index'}}, y:{{field:'load_N',type:'quantitative',title:'Load / N'}}, tooltip:[{{field:'point_index'}},{{field:'load_N'}},{{field:'mean_strain'}}]}}}},
    {{data:{{values:post}}, mark:{{type:'area',opacity:0.12,color:'#a12626'}}, encoding:{{x:{{field:'point_index',type:'quantitative'}}, y:{{field:'load_N',type:'quantitative'}}, y2:{{value:0}}}}}},
    {{data:{{values:[{{x:start,label:'start'}},{{x:end,label:'end'}}]}}, mark:{{type:'rule',strokeDash:[6,4],color:'#d9480f'}}, encoding:{{x:{{field:'x',type:'quantitative'}}, tooltip:[{{field:'label'}},{{field:'x'}}]}}}},
    {{data:{{values:maxEvent}}, mark:{{type:'point',filled:true,size:120,color:'#167043'}}, encoding:{{x:{{field:'point_index',type:'quantitative'}}, y:{{field:'value',type:'quantitative'}}, tooltip:[{{field:'event_id'}},{{field:'point_index'}},{{field:'value'}}]}}}},
    {{data:{{values:prebreak}}, mark:{{type:'point',filled:true,size:120,color:'#d9480f',shape:'diamond'}}, encoding:{{x:{{field:'point_index',type:'quantitative'}}, y:{{field:'value',type:'quantitative'}}, tooltip:[{{field:'event_id'}},{{field:'point_index'}},{{field:'value'}}]}}}},
    {{data:{{values:firstNegative}}, mark:{{type:'point',filled:true,size:100,color:'#a12626',shape:'cross'}}, encoding:{{x:{{field:'point_index',type:'quantitative'}}, y:{{field:'value',type:'quantitative'}}, tooltip:[{{field:'event_id'}},{{field:'point_index'}},{{field:'value'}}]}}}},
    {{data:{{values:decline}}, mark:{{type:'point',filled:true,size:100,color:'#7651d7',shape:'triangle'}}, encoding:{{x:{{field:'point_index',type:'quantitative'}}, y:{{field:'value',type:'quantitative'}}, tooltip:[{{field:'event_id'}},{{field:'point_index'}},{{field:'value'}}]}}}}
  ] }}; }}
function meanAbsoluteSpec(rows, after=false) {{ return after ? overlaySeries(rows,['front_strain_abs','rear_strain_abs','mean_strain']) : overlaySeries(rows,['front_strain_raw','rear_strain_raw']); }}
function specFor(op, before=false) {{ const rows=currentRows(); const vt=op.view_type || op.audit_view_hint || op.operation_type; if (op.operation_type==='resolve_experiment_boundaries' || vt==='experiment_boundary_resolution') return before ? loadSpec(fullRunRows(selectedRun)) : boundarySpec(fullRunRows(selectedRun), op); if (before) {{ if (['derive_stress','max_point','value_at_max','chord_slope','bending_diagnostic'].includes(op.operation_type)) return stressSpec(rows); if (op.operation_type==='construct_mean_series') return meanAbsoluteSpec(rows,false); if (op.operation_type==='map_channel') return loadSpec(rows); return overlaySeries(rows,['load_N','load_N_raw','front_strain_raw','rear_strain_raw','extension_mm']); }} if (op.operation_type==='construct_mean_series' || vt.includes('mean_absolute')) return meanAbsoluteSpec(rows,true); if (vt.includes('mean')) return overlaySeries(rows,['front_strain_abs','rear_strain_abs','mean_strain']); if (op.operation_type==='derive_stress') return stressSpec(rows); if (op.operation_type==='max_point' || op.operation_type==='value_at_max') return maxMarkerSpec(rows, op); if (op.operation_type==='chord_slope') return chordSpec(rows, op); if (op.operation_type==='bending_diagnostic') return bendingSpec(rows, op); if (op.operation_type==='map_channel') {{ const outs=Object.keys(op.outputs||{{}}); return overlaySeries(rows, outs.length ? outs : ['load_N']); }} return overlaySeries(rows,['load_N','load_N_raw','front_strain_raw','rear_strain_raw','front_strain_abs','rear_strain_abs','mean_strain','stress_MPa']); }}
async function embed(id, spec) {{ document.getElementById(id).innerHTML=''; try {{ await vegaEmbed('#'+id, spec, {{actions:true}}); }} catch(e) {{ document.getElementById(id).innerHTML='<pre>'+esc(e.message)+'</pre>'; }} }}
function renderCharts() {{ const op=currentOp(); if (!op) return; embed('beforeChart', specFor(op,true)); embed('afterChart', specFor(op,false)); renderGraphSequence(); }}
function bendingPatternCard(op) {{ const diag=((op.outputs||{{}}).bending_diagnostic||{{}}); if(op.operation_type!=='bending_diagnostic' || !diag.pattern) return ''; const p=diag.pattern||{{}}; const rows=(diag.segments||[]).map(s=>({{segment:s.segment_id, classification:s.segment_classification, start_index:s.start_index, end_index:s.end_index, points:s.point_count, max_percent:s.max_bending_percent}})); return `<div class=\"details\"><h3>Bending Pattern</h3><div class=\"kv\"><div class=\"k\">Classification</div><div>${{esc(p.classification || '')}}</div></div><div class=\"kv\"><div class=\"k\">Confidence</div><div>${{esc(p.confidence || '')}}</div></div><div class=\"kv\"><div class=\"k\">Threshold</div><div>${{esc(diag.threshold_percent ?? '')}}%</div></div><div class=\"kv\"><div class=\"k\">Exceedance</div><div>${{esc(diag.points_above_threshold ?? 0)}} points, ${{esc(fmt(diag.fraction_above_threshold ?? 0))}} fraction</div></div><p class=\"hint\">${{esc(p.reason || '')}}</p><h3>Exceedance Segments</h3>${{table(rows)}}</div>`; }}
function boundaryCard(op) {{ const record=((op.evidence||{{}}).boundary_record || (op.outputs||{{}}).experiment_boundaries || {{}}); if(op.operation_type!=='resolve_experiment_boundaries' && (op.view_type||'')!=='experiment_boundary_resolution') return ''; const interval=record.analysis_interval||{{}}; return `<div class=\"details\"><h3>Experiment Boundary</h3><div class=\"kv\"><div class=\"k\">Start</div><div>${{esc(interval.start_index ?? record.start_index ?? '')}} - ${{esc(record.start_policy || '')}}</div></div><div class=\"kv\"><div class=\"k\">End</div><div>${{esc(interval.end_index ?? record.end_index ?? '')}} - ${{esc(record.end_policy || '')}}</div></div><div class=\"kv\"><div class=\"k\">Confidence</div><div>${{esc(record.confidence || '')}}</div></div><p class=\"hint\">${{esc(record.reason || '')}}</p><h3>Events</h3>${{table(record.events || [])}}</div>`; }}
function renderDetails() {{ const op=currentOp(); if(!op) return; const impl = op.implementation_path ? `<a href=\"#\" onclick=\"showImpl('${{esc(op.implementation_path)}}');return false;\">Open operation implementation: ${{esc(op.implementation_path)}}</a>` : ''; $('details').innerHTML = `<div class=\"details\"><h3>Operation</h3><div class=\"kv\"><div class=\"k\">Step</div><div>${{esc(op.recipe_step_id || '')}}</div></div><div class=\"kv\"><div class=\"k\">Type</div><div>${{esc(op.operation_type)}}</div></div><div class=\"kv\"><div class=\"k\">Phase</div><div>${{esc(op.phase)}}</div></div><div class=\"kv\"><div class=\"k\">Status</div><div>${{esc(op.status)}}</div></div>${{impl}}</div>${{boundaryCard(op)}}${{bendingPatternCard(op)}}<div class=\"details\"><h3>Inputs</h3><pre>${{esc(JSON.stringify(op.inputs,null,2))}}</pre></div><div class=\"details\"><h3>Parameters</h3><pre>${{esc(JSON.stringify(op.parameters,null,2))}}</pre></div><div class=\"details\"><h3>Outputs</h3><pre>${{esc(JSON.stringify(op.outputs,null,2))}}</pre></div><div class=\"details\"><h3>Evidence</h3><pre>${{esc(JSON.stringify(op.evidence,null,2))}}</pre></div><div class=\"details\"><h3>Warnings</h3><pre>${{esc(JSON.stringify(op.warnings || [],null,2))}}</pre></div>`; }}
function table(rows) {{ if(!rows.length) return '<p>No rows.</p>'; const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))]; return '<table><thead><tr>'+keys.map(k=>`<th>${{esc(k)}}</th>`).join('')+'</tr></thead><tbody>'+rows.slice(0,500).map(r=>'<tr>'+keys.map(k=>`<td>${{esc(fmt(r[k]))}}</td>`).join('')+'</tr>').join('')+'</tbody></table>'; }}
function renderData() {{
  const op=currentOp();
  const columns = cumulativeColumns(op);
  const newCols = newColumnsFor(op);
  const rows = currentRows();
  const note = newCols.length ? `<div class=\"new-column-note\"><b>Newly introduced columns:</b> ${{esc(newCols.join(', '))}}</div>` : '<div class=\"new-column-note\"><b>Newly introduced columns:</b> none for this selected step.</div>';
  $('dataTable').innerHTML = `<h3>Data</h3><div class=\"data-summary\"><span class=\"data-pill\">Run ${{esc(selectedRun)}}</span><span class=\"data-pill\">Step ${{esc(op ? op.recipe_step_id : '')}}</span><span class=\"data-pill\">${{rows.length}} rows</span><span class=\"data-pill\">${{columns.length}} visible columns</span></div>${{note}}<h3>Cumulative operation data</h3>${{tableWithColumns(rows, columns, newCols)}}<h3>Selected operation record</h3><pre>${{esc(JSON.stringify(op,null,2))}}</pre>`;
}}
function validationClass(status) {{ return status === 'fail' ? 'bad' : status === 'warn' ? 'warn' : status === 'pass' ? 'ok' : ''; }}
function validationLabel(status) {{ return status === 'not_applicable' ? 'no validation' : (status || 'unknown'); }}
function validationChecksForRun(runId) {{ return (((TRACE.validation || {{}}).checks) || []).filter(c => c.run_id === runId); }}
function readinessClass(status) {{ return status === 'READY' ? 'ok' : status === 'READY_WITH_WARNINGS' ? 'warn' : 'bad'; }}
function acceptanceClass(state) {{ return state === 'excluded' ? 'bad' : state === 'review_required' ? 'warn' : state === 'accepted_with_warning' ? 'warn' : 'ok'; }}
function runAcceptanceFlags(runId) {{ return (TRACE.run_flags || []).filter(f => f.run_id === runId); }}
function selectedSelectionId() {{ const sets = ((TRACE.selection_sets || {{}}).selection_sets) || []; const selector = document.getElementById('selectionFilter'); return (selector && selector.value) || ((TRACE.acceptance || {{}}).default_selection_set) || (sets[0] && sets[0].selection_id) || 'all_runs'; }}
function curveFamilySpec() {{ const values=[]; (TRACE.curve_family_aligned_rows || []).forEach(r => {{ if(r.y_aligned !== null && r.y_aligned !== undefined) values.push({{x_common:Number(r.x_common), value:Number(r.y_aligned), series:String(r.run_id), kind:'aligned'}}); }}); (TRACE.curve_family_reference_rows || []).forEach(r => {{ if(r.y_reference !== null && r.y_reference !== undefined) values.push({{x_common:Number(r.x_common), value:Number(r.y_reference), series:'reference', kind:'reference'}}); }}); return baseSpec(values, 'x_common', 'value', 'curve_family_reference_overlay', 'series'); }}
function renderRuns() {{ renderRunSelector(); }}
function renderSteps() {{ const ops = opsForRun(selectedRun); if (!selectedStep && ops.length) selectedStep = ops[0]; let lastPhase=''; let html=''; for (const op of ops) {{ if (op.phase !== lastPhase) {{ lastPhase = op.phase; html += `<div class=\"phase\">${{op.phase === 'method_resolve' ? 'Resolve' : 'Reduce'}}</div>`; }} const active = selectedStep && op.sequence === selectedStep.sequence; const dot = statusDotClass(op); const phaseLabel = op.phase === 'method_resolve' ? 'resolve' : 'reduce'; html += `<div class=\"step ${{op.phase==='method_reduce'?'reduce':''}} ${{active?'active':''}}\" data-seq=\"${{op.sequence}}\"><div class=\"dot ${{dot}}\"></div><div><div class=\"step-title\">${{String(op.sequence).padStart(2,'0')}} ${{esc(op.recipe_step_label || op.operation_type)}}</div><div class=\"step-sub\">${{esc(phaseLabel)}} - ${{esc(op.operation_type)}}</div></div></div>`; }} $('steps').innerHTML = html; document.querySelectorAll('.step').forEach(el => el.onclick = () => {{ selectedStep = ops.find(o => String(o.sequence) === el.dataset.seq); renderAll(false); }}); }}
function renderValidation() {{ const checks = validationChecksForRun(selectedRun); const op = currentOp(); const opChecks = (op && op.validation_checks) || []; const target = checks.find(c => c.status === 'fail' || c.status === 'warn'); const summary = (TRACE.validation || {{}}).summary || {{}}; $('validationPanel').innerHTML = `<h3>Validation Summary</h3>${{table(TRACE.validation_summary || [])}}<p class=\"hint\">Selected run: ${{esc(selectedRun)}}. Overall status: ${{esc(summary.status || 'unknown')}}.</p><button class=\"btn\" id=\"jumpValidationBtn\">Jump to first failed/warned validation</button><h3>Selected Operation Checks</h3>${{table(opChecks)}}<h3>Run Checks</h3>${{table(checks)}}`; const btn=$('jumpValidationBtn'); if(btn) btn.onclick=()=>{{ if(!target) return; const ops=opsForRun(selectedRun); selectedStep = ops.find(o => (o.validation_checks||[]).some(c => c.check_id === target.check_id)) || selectedStep; renderAll(false); document.querySelector('[data-tab=\"graph\"]').click(); }}; }}
function renderReadiness() {{ const report = TRACE.readiness || {{}}; const summary = report.summary || {{}}; const runMissing = (TRACE.missing_inputs || []).filter(r => !r.run_id || r.run_id === selectedRun); const runResolved = (TRACE.resolved_inputs || []).filter(r => !r.run_id || r.run_id === selectedRun); const cls = readinessClass(report.status); $('readinessPanel').innerHTML = `<h3>Pre-run Package Readiness</h3><p>Status: <span class=\"badge ${{cls}}\">${{esc(report.status || 'UNKNOWN')}}</span>. Blocks execution: ${{esc(report.blocks_execution || false)}}.</p><p class=\"hint\">Execution-critical passed: ${{esc(summary.execution_critical_passed || 0)}} / ${{esc(summary.execution_critical_total || 0)}}. Missing inputs: ${{esc(summary.missing_total || 0)}}. Selected run filter: ${{esc(selectedRun)}}.</p><h3>Readiness Summary</h3>${{table(TRACE.readiness_summary || [])}}<h3>Missing / Warning Method Inputs</h3>${{table(runMissing)}}<h3>Resolved Method Inputs</h3>${{table(runResolved)}}`; }}
function renderAcceptance() {{ const summary = (TRACE.acceptance || {{}}).summary || {{}}; const sets = ((TRACE.selection_sets || {{}}).selection_sets) || []; const currentSelection = selectedSelectionId(); const options = sets.map(s => `<option value=\"${{esc(s.selection_id)}}\" ${{s.selection_id===currentSelection?'selected':''}}>${{esc(s.label || s.selection_id)}}</option>`).join(''); const membership = (TRACE.selection_membership || []).filter(r => r.selection_set === currentSelection); const datasetRows = (TRACE.dataset_summary_by_selection || []).filter(r => r.selection_set === currentSelection); const flags = runAcceptanceFlags(selectedRun); const discharged = (TRACE.discharged_runs || []).filter(r => !selectedRun || r.run_id === selectedRun); const cf = TRACE.curve_family_assessment || {{}}; const cfSummary = cf.summary ? [cf.summary] : []; const cfScores = (TRACE.curve_family_scores || []).filter(r => !selectedRun || r.run_id === selectedRun); const cfResiduals = (TRACE.curve_family_residual_rows || []).filter(r => !selectedRun || r.run_id === selectedRun).slice(0,250); $('acceptancePanel').innerHTML = `<h3>Dataset Acceptance</h3>${{table(TRACE.acceptance_summary || [])}}<p class=\"hint\">Selected run: ${{esc(selectedRun)}}. Default selection: ${{esc(summary.default_selection_set || '')}}. Accepted: ${{esc(summary.accepted || 0)}}; review: ${{esc(summary.review_required || 0)}}; excluded: ${{esc(summary.excluded || 0)}}.</p><label class=\"hint\">Selection set filter <select id=\"selectionFilter\">${{options}}</select></label><h3>Selected Run Flags</h3>${{table(flags)}}<h3>Curve-Family Assessment</h3>${{table(cfSummary)}}<div id=\"curveFamilyChart\" class=\"chart\"></div><h3>Curve-Family Metric Ranking</h3>${{table(cfScores)}}<h3>Flagged Curve Residuals</h3>${{table(cfResiduals)}}<h3>Selection Membership</h3>${{table(membership)}}<h3>Dataset Summary By Selection</h3>${{table(datasetRows)}}<h3>Discharge Report</h3>${{table(discharged.length ? discharged : (TRACE.discharged_runs || []))}}`; const selector = $('selectionFilter'); if(selector) selector.onchange = renderAcceptance; if((TRACE.curve_family_aligned_rows || []).length) embed('curveFamilyChart', curveFamilySpec()); }}
function renderEvidence() {{
  const ctx = contextSummary();
  const runRecord = (TRACE.runs || []).find(r => r.run_id === selectedRun) || {{}};
  const validationChecks = validationChecksForRun(selectedRun);
  const runFlags = runAcceptanceFlags(selectedRun);
  const selectedMembership = (TRACE.selection_membership || []).filter(r => r.run_id === selectedRun);
  const dischargedRows = (TRACE.discharged_runs || []).filter(r => r.run_id === selectedRun);
  const reportStatus = TRACE.report_completion || {{}};
  const reportValues = TRACE.report_values_used || [];
  const missingFields = TRACE.missing_report_fields || [];
  const reportOverrides = rowsFrom((TRACE.report_overrides || {{}}).overrides || TRACE.report_overrides);
  const reportOverrideLedger = rowsFrom((TRACE.report_override_ledger || {{}}).records || TRACE.report_override_ledger);
  const boundaries = (TRACE.experiment_boundaries || []).filter(r => !selectedRun || r.run_id === selectedRun);
  const finalization = TRACE.finalization || {{}};
  const archiveState = finalization.archive_state || {{}};
  const amendmentLedger = rowsFrom((finalization.amendment_ledger || {{}}).records || finalization.amendment_ledger);
  const finalizationReport = finalization.finalization_report || {{}};
  const routeField = ctx.field && ctx.field !== 'missing_report_fields' ? ctx.field : '';
  const fieldMatches = r => !routeField || [r.field_key, r.key, r.report_role, r.field, r.section].some(v => String(v || '').toLowerCase().includes(String(routeField).toLowerCase()));
  const fieldValues = reportValues.filter(fieldMatches).slice(0,120);
  const fieldMissing = missingFields.filter(fieldMatches).slice(0,120);
  const worstChecks = validationChecks.filter(c => c.status === 'fail' || c.status === 'warn');
  const cards = [
    `<div class=\"evidence-card\"><h3>Run context</h3><p class=\"hint\">${{esc(selectedRun || 'No run selected')}} · validation ${{esc(validationLabel(runRecord.validation_status))}} · acceptance ${{esc(runRecord.acceptance_state || 'accepted')}}</p>${{contextLink('Open validation for this run', {{tab:'validation', context:'validation', run:selectedRun}})}}${{contextLink('Open acceptance for this run', {{tab:'acceptance', context:'acceptance', run:selectedRun}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Validation evidence</h3><p class=\"hint\">${{validationChecks.length}} checks for selected run; ${{worstChecks.length}} warning/failure rows.</p>${{contextLink('Validation tab', {{tab:'validation', context:'validation', run:selectedRun, check:(worstChecks[0]||{{}}).check_id || ''}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Acceptance evidence</h3><p class=\"hint\">${{runFlags.length}} flags, ${{dischargedRows.length}} discharge records, ${{selectedMembership.length}} selection memberships.</p>${{contextLink('Acceptance tab', {{tab:'acceptance', context:'acceptance', run:selectedRun, flag:(runFlags[0]||{{}}).flag_id || ''}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Boundary evidence</h3><p class=\"hint\">${{boundaries.length}} resolved boundary records for selected run. Reduction and aggregation use the bounded interval.</p>${{contextLink('Boundary operation', {{tab:'graph', context:'audit', run:selectedRun, operation:'resolve.experiment_boundaries'}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Report completion</h3><p class=\"hint\">${{esc(reportStatus.status || reportStatus.completion_status || 'unknown')}} · required missing ${{esc(reportStatus.required_missing_count ?? '')}} · recommended missing ${{esc(reportStatus.recommended_missing_count ?? '')}}</p>${{contextLink('Report fields', {{tab:'evidence', context:'report', field:routeField || 'missing_report_fields'}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Amendments and finalization</h3><p class=\"hint\">Archive state: ${{esc(archiveState.archive_state || archiveState.state || 'draft/unknown')}} · amendments ${{amendmentLedger.length}} · report override records ${{reportOverrideLedger.length || reportOverrides.length}}</p>${{contextLink('Amendment evidence', {{tab:'evidence', context:'amendments', field:routeField || 'loading_method'}})}}</div>`,
    `<div class=\"evidence-card\"><h3>Report/export evidence</h3><p class=\"hint\">Use this area to connect formal report outputs back to the method-run evidence trail.</p>${{contextLink('Aggregate evidence', {{tab:'acceptance', context:'aggregate', run:selectedRun}})}}</div>`,
  ].join('');
  $('evidencePanel').innerHTML = `
    <h3>Evidence Navigator</h3>
    <p class=\"hint\">This Workbench page is the deep-inspection destination for report, audit, wizard, validation, acceptance, and amendment references. Raw evidence remains below the summary cards.</p>
    <div class=\"evidence-grid\">${{cards}}</div>
    <h3>Selected Run Context</h3>${{table([runRecord])}}
    <h3>Validation Checks for Selected Run</h3>${{table(validationChecks)}}
    <h3>Acceptance Flags and Discharge Evidence</h3>${{table(runFlags.concat(dischargedRows))}}
    <h3>Experiment Boundary Resolution</h3>${{table(boundaries)}}
    <h3>Selection Membership for Selected Run</h3>${{table(selectedMembership)}}
    <h3>Report Completion Status</h3>${{table([reportStatus])}}
    <h3>Report Values Used${{routeField ? ' - '+esc(readable(routeField)) : ''}}</h3>${{table(fieldValues)}}
    <h3>Missing Report Fields${{routeField ? ' - '+esc(readable(routeField)) : ''}}</h3>${{table(fieldMissing)}}
    <h3>Report Override Ledger</h3>${{table(reportOverrideLedger.length ? reportOverrideLedger : reportOverrides)}}
    <h3>Finalization State</h3>${{table([archiveState])}}
    <h3>Finalization Amendments</h3>${{table(amendmentLedger)}}
    <details open><summary>Finalization report raw evidence</summary><pre>${{esc(JSON.stringify(finalizationReport,null,2))}}</pre></details>
  `;
}}
function renderEditors() {{ $('resolveEditor').value = TRACE.recipes.resolve_text || ''; $('reduceEditor').value = TRACE.recipes.reduce_text || ''; $('apiNote').textContent = API_ENABLED ? 'Server mode: edits can be re-run through Python.' : 'Static mode: run with --serve to re-execute Python from this page.'; $('rerunBtn').disabled = !API_ENABLED; renderOperationGuide(); }}
function showImpl(path) {{ alert('Implementation path: '+path+'\\nOpen this file in your editor. Server-side source opening can be added later.'); }}
function setPanelCollapsed(panelId, bodyClass, collapsed) {{
  document.body.classList.toggle(bodyClass, collapsed);
  const panel = $(panelId);
  if(panel) panel.classList.toggle('collapsed', collapsed);
}}
function togglePanel(panelId, bodyClass) {{ setPanelCollapsed(panelId, bodyClass, !document.body.classList.contains(bodyClass)); }}
function renderAll(resetEditors=true) {{ renderRuns(); renderSteps(); renderCharts(); renderDetails(); renderData(); renderReadiness(); renderValidation(); renderAcceptance(); renderEvidence(); renderContextBanner(); if(resetEditors) renderEditors(); statusEl.textContent = `${{TRACE.method.method_id}} - ${{selectedRun}} - ${{(TRACE.operations||[]).length}} operation records`; }}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>activateTab(t.dataset.tab));
window.addEventListener('hashchange', () => {{ applyRoute(); renderAll(false); activateTab(routeParams().get('tab') || 'evidence'); }});
$('toggleTimeline').onclick=()=>togglePanel('timelinePanel','timeline-collapsed');
$('toggleDetails').onclick=()=>togglePanel('detailsPanel','details-collapsed');
$('resetBtn').onclick=()=>renderEditors();
$('rerunBtn').onclick=async()=>{{ if(!API_ENABLED) return; statusEl.textContent='Running edited recipes through Python...'; const res=await fetch('/api/run',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{resolve_recipe:$('resolveEditor').value, reduce_recipe:$('reduceEditor').value}})}}); if(!res.ok) {{ statusEl.textContent='Run failed'; alert(await res.text()); return; }} TRACE=await res.json(); selectedRun=(TRACE.runs&&TRACE.runs[0]&&TRACE.runs[0].run_id)||selectedRun; selectedStep=null; renderAll(false); statusEl.textContent='Edited recipes executed'; }};
applyRoute();
renderAll();
activateTab(routeParams().get('tab') || 'graph');
</script>
</body>
</html>"""
