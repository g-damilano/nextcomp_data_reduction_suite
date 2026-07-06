import React from 'react';
import { DesktopWindowControls } from '../components/DesktopWindowControls.jsx';
import { SectionGuidelinesModal } from '../components/SectionGuidelines.jsx';

// ===== runtime defaults =====
/* ============================================================
   Design-time defaults for the PySide6 React shell.
   Production package/run state is loaded through the desktop bridge.
   ============================================================ */

window.WIZ = (function () {
  const APP_VERSION = "v0.6.0";

  // Bindable variables discovered in the package — used by the mapping editor's
  // custom-binding dropdown (pick an existing source, never free-typed).
  const AVAILABLE_SOURCES = {
    channel: ["load_N", "front_strain", "rear_strain", "transverse_strain", "crosshead_mm", "time_s", "strain_2", "strain_axial_2"],
    field: ["specimen.width", "specimen.thickness", "specimen.gauge_length", "fixture.free_length", "fixture.type"],
    metadata: ["fields.Operator Name", "fields.Test Engineer", "fields.Fixture", "fields.Conditioning", "fields.Environment", "fields.Test Speed", "fields.Lab Reference"],
  };

  const PACKAGE = {
    name: "CAG-CF-Modied-ULV20.mtdp",
    family: "mechanical.compression",
    runs: 7,
    schema: "Compression · v0.3.0",
    path: "…\\datasets\\Compression\\CAG-CF-Modied-ULV20.mtdp",
    channels: ["load_N", "front_strain", "rear_strain", "crosshead_mm", "time_s"],
  };

  const METHOD = {
    id: "iso14126_2023",
    short: "ISO 14126 Compression — v0.1.0",
    title: "BS EN ISO 14126:2023 compression properties",
    version: "v0.1.0",
    standard: "ISO 14126",
    summary: "Determines compressive strength, modulus and failure mode for fibre-reinforced plastic laminates.",
    registry: "3 in registry",
  };

  // ---- Readiness: the real app reports 35 critical inputs bound ----
  const BOUND_CRITICAL_COUNT = 35;
  const BOUND_EXAMPLES = [
    "channel.load → load_N",
    "channel.strain → strain_axial",
    "geometry.width → specimen.width_mm",
    "geometry.thickness → specimen.thickness_mm",
    "failure_mode → failure_mode_iso",
  ];

  // ---- Report-binding gaps (the "Bind 7 report fields" decision) ----
  // requirement_level recovered from report_authoring importance vocabulary
  const REPORT_BIND_FIELDS = [
    { field: "report.operator", example: "G. Macori", level: "required", sources: ["fields.Operator Name", "fields.Test Engineer"] },
    { field: "report.fixture_description", example: "4-pt CLC fixture", level: "required", sources: ["fields.Fixture"] },
    { field: "report.conditioning", example: "23 °C / 50 % RH", level: "recommended", sources: ["fields.Conditioning", "fields.Environment"] },
    { field: "report.testing_speed", example: "1 mm/min", level: "recommended", sources: ["fields.Test Speed"] },
    { field: "report.strain_measurement_method", example: "video extensometer", level: "recommended", sources: [] },
    { field: "report.specimen_type", example: "rectangular bar", level: "recommended", sources: [] },
    { field: "report.loading_method", example: "end-loaded", level: "recommended", sources: [] },
  ];

  // Fixed value lists for report fields with a closed vocabulary (no free text)
  const REPORT_FIELD_OPTIONS = {
    "report.strain_measurement_method": ["video extensometer", "clip-on extensometer", "strain gauge", "DIC"],
    "report.specimen_type": ["rectangular bar", "waisted (necked)", "tabbed"],
    "report.loading_method": ["end-loaded", "shear-loaded", "mixed (combined)"],
  };

  const METADATA_BLANK_COUNT = 38;

  // Vocabulary recovered from report_authoring.py
  const SOURCE_TYPE_LABEL = {
    missing: "Not recorded in source package",
    report_override: "Report-only amendment",
    source_mtdp_dataset: "Source package dataset metadata",
    source_mtdp_run: "Source package run metadata",
    mtda_method_output: "Computed method output",
  };
  const IMPORTANCE_LABEL = {
    required: "Required for complete report",
    recommended: "Recommended report field",
    optional: "Optional report field",
  };

  // ---- Mapping editor model (the "Edit mapping profile" deep dive) ----
  // status: matched (auto, has `via` provenance) · manual (user-assigned) · ambiguous (≥2 plausible families) · unmapped
  const BINDINGS = [
    { id: "channel.load", input: "channel.load", desc: "Compressive load channel", req: "required", kind: "channel", status: "matched", binding: "load_N", coverage: "7/7 runs", unit: "N", via: "header token “Kraft” + unit N",
      candidates: [{ source: "load_N", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.96, example: "0 … 41 200 N", reason: "Name + unit exact match", via: "header token “Kraft” + unit N" }] },
    { id: "channel.front_strain", input: "channel.front_strain", desc: "Front-face strain gauge", req: "required", kind: "channel", status: "matched", binding: "front_strain", coverage: "7/7 runs", unit: "µε", via: "role + gauge position",
      candidates: [{ source: "front_strain", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.93, example: "0 … 11 800 µε", reason: "Role + position match", via: "role + gauge position" }, { source: "rear_strain", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.41, example: "0 … 11 200 µε", reason: "Same kind, opposite face" }] },
    { id: "channel.rear_strain", input: "channel.rear_strain", desc: "Rear-face strain gauge", req: "required", kind: "channel", status: "matched", binding: "rear_strain", coverage: "7/7 runs", unit: "µε", via: "role + gauge position",
      candidates: [{ source: "rear_strain", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.93, example: "0 … 11 200 µε", reason: "Role + position match", via: "role + gauge position" }, { source: "front_strain", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.41, example: "0 … 11 800 µε", reason: "Same kind, opposite face" }] },
    { id: "channel.transverse_strain", input: "channel.transverse_strain", desc: "Transverse strain (Poisson)", req: "recommended", kind: "channel", status: "ambiguous", binding: "", coverage: "7/7 runs", unit: "µε",
      note: "two strain dimensions plausible for header “Dehnung 2”",
      candidates: [{ source: "strain_2", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.58, example: "0 … 3 900 µε", reason: "Header “Dehnung 2” — transverse gauge", via: "parser found 2 plausible families" }, { source: "strain_axial_2", kind: "channel", scope: "package", coverage: "7/7 runs", confidence: 0.54, example: "0 … 10 400 µε", reason: "Header “Dehnung 2” — second axial gauge", via: "parser found 2 plausible families" }] },
    { id: "specimen.gauge_length_mm", input: "specimen.gauge_length_mm", desc: "Gauge length", req: "required", kind: "field", status: "matched", binding: "specimen.gauge_length", coverage: "7/7 runs", unit: "mm", via: "token alias",
      candidates: [{ source: "specimen.gauge_length", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.88, example: "10.0 mm", reason: "Token alias match", via: "token alias" }, { source: "fixture.free_length", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.52, example: "12.5 mm", reason: "Related length field" }] },
    { id: "specimen.width_mm", input: "specimen.width_mm", desc: "Specimen width", req: "required", kind: "field", status: "matched", binding: "specimen.width", coverage: "7/7 runs", unit: "mm", via: "exact token",
      candidates: [{ source: "specimen.width", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.91, example: "25.0 mm", reason: "Exact token match", via: "exact token" }] },
    { id: "specimen.thickness_mm", input: "specimen.thickness_mm", desc: "Specimen thickness", req: "required", kind: "field", status: "matched", binding: "specimen.thickness", coverage: "7/7 runs", unit: "mm", via: "exact token",
      candidates: [{ source: "specimen.thickness", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.91, example: "2.0 mm", reason: "Exact token match", via: "exact token" }] },
    { id: "report.operator", input: "report.operator", desc: "Operator / analyst name", req: "recommended", kind: "field", status: "unmapped", binding: "", coverage: "—", unit: "",
      candidates: [{ source: "fields.Operator Name", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.74, example: "G. Macori", reason: "Label similarity to ‘operator’" }, { source: "fields.Test Engineer", kind: "field", scope: "package metadata", coverage: "5/7 runs", confidence: 0.55, example: "G. Macori", reason: "Partial label match" }] },
    { id: "report.fixture_description", input: "report.fixture_description", desc: "Test fixture description", req: "recommended", kind: "field", status: "unmapped", binding: "", coverage: "—", unit: "",
      candidates: [{ source: "fields.Fixture", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.68, example: "4-pt CLC fixture", reason: "Label similarity" }] },
    { id: "report.conditioning", input: "report.conditioning", desc: "Conditioning environment", req: "recommended", kind: "field", status: "unmapped", binding: "", coverage: "—", unit: "",
      candidates: [{ source: "fields.Conditioning", kind: "field", scope: "package metadata", coverage: "6/7 runs", confidence: 0.62, example: "23 °C / 50 % RH", reason: "Label similarity" }, { source: "fields.Environment", kind: "field", scope: "package metadata", coverage: "7/7 runs", confidence: 0.49, example: "Lab ambient", reason: "Related label" }] },
  ];

  // ---- Running stages (matches RUNNING_STAGES in source; Workbench stage removed) ----
  const STAGES = ["Input", "Method", "Mapping", "Ready", "Resolve", "Reduce", "Validate", "Accept", "Write", "Report", "Done"];

  const TRACE_SCRIPT = [
    { pct: 100, stage: "Done", level: "info", msg: "No backend execution trace is available." },
  ];

  const RUN_TABLE = [];

  // ---- Diagnostic evidence helpers ----
  function bendSeries(seed, peak, n = 46) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const x = i / (n - 1);
      const base = peak * Math.pow(x, 0.85) * (1 - 0.18 * Math.sin(x * 7 + seed));
      out.push(Math.max(0, base + Math.sin(i * 1.7 + seed) * peak * 0.015));
    }
    return out;
  }
  function curve(seed, scale, n = 40) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const x = i / (n - 1);
      out.push({ x: x * 1.05, y: scale * (1 - Math.exp(-3.1 * x)) * (1 + 0.04 * Math.sin(seed + x * 5)) });
    }
    return out;
  }
  const REFERENCE_CURVE = curve(0, 1.0);

  // ---- Cockpit factories (mirror diagnostic_cockpit.py card specs) ----
  function bendingCockpit({ peak, threshold, pointsAbove, assessed, longest, call, action, window }) {
    const share = assessed ? pointsAbove / assessed : 0;
    return {
      kind: "bending", tab: "Bending", title: "Bending defect",
      series: bendSeries(peak * 30, peak), threshold, peak, window,
      segments: pointsAbove > 0 ? [[0.52, 0.52 + Math.min(0.34, share + 0.06)]] : [],
      cards: [
        { key: "bending.classification", label: "Bending call", value: call, sub: "pattern in 10–90 % Fmax window", level: "warn" },
        { key: "bending.max_percent", label: "Peak imbalance", value: peak.toFixed(3) + "%", sub: "max opposite-face strain imbalance", level: "warn" },
        { key: "bending.threshold_percent", label: "Review limit", value: threshold.toFixed(2) + "%", sub: "configured ISO 14126 bending threshold", level: "info" },
        { key: "bending.points_above_threshold", label: "Persistence", value: String(pointsAbove), sub: `${pointsAbove} of ${assessed} assessed points above limit`, level: "warn" },
        { key: "bending.fraction_above_threshold", label: "Window share", value: (share * 100).toFixed(1) + "%", sub: "share of assessed load window", level: "warn" },
        { key: "bending.longest_exceedance_segment", label: "Longest segment", value: longest, sub: "contiguous exceedance evidence", level: "info" },
        { key: "selection.consequence_summary", label: "Scientist action", value: action, sub: "final report consequence", level: "info" },
      ],
    };
  }
  function curveCockpit({ metric, value, threshold, rank, robustZ, robustThr, masking, dixon, limit, classification, action, focus }) {
    return {
      kind: "curve_family", tab: "Curve shape", title: "Curve-shape defect",
      points: focus, reference: REFERENCE_CURVE,
      cohort: [curve(1.2, 0.97), curve(2.4, 1.02), curve(3.1, 0.99), curve(4.0, 1.01)],
      cards: [
        { key: "curve_family.classification", label: "Scientific call", value: classification, sub: "curve-shape assessment", level: "info" },
        { key: "curve_family.metric", label: "Primary metric", value: `${metric} ${value}`, sub: `threshold ${threshold}`, level: "warn" },
        { key: "curve_family.rank", label: "Distance rank", value: rank, sub: "rank within assessed cohort", level: "info" },
        { key: "curve_family.robust_z", label: "Robust screen", value: `z ${robustZ} vs ${robustThr}; masking ${masking}`, sub: "masking-risk companion evidence", level: "info" },
        { key: "curve_family.dixon_decision", label: "Outlier test", value: `${dixon}; limit ${limit}`, sub: "formal upper-tail screen", level: "info" },
        { key: "selection.consequence_summary", label: "Scientist action", value: action, sub: "final report consequence", level: "info" },
      ],
    };
  }

  // ---- Flagged runs (acceptance review) ----
  const KEEP_INCLUDED = "Included in final report unless removed by operator";
  const REMOVE_EXCLUDED = "Excluded from final report unless kept with justification";

  const FLAGGED = [
    {
      run: "demo_run_001", defaultCall: "Remove", excluded: false,
      defects: ["Bending"], reason: "Demo acceptance finding",
      flags: [{ severity: "review", category: "bending", message: "Demo bending review" }],
      narrative: "Demo-only acceptance evidence. Production review rows are loaded from the analysed dataset.",
      cockpits: [bendingCockpit({ peak: 0.12, threshold: 0.10, pointsAbove: 3, assessed: 40, longest: "3 points", call: "Demo review", action: REMOVE_EXCLUDED, window: [0.10, 0.90] })],
    },
  ];

  // ---- Finalize / output ----
  const OUTPUT = {
    mtda: "CAG-CF-Modied-ULV20.mtda",
    path: "…\\datasets\\Compression\\CAG-CF-Modied-ULV20.mtda",
    archiveMembers: 47,
    requiredMissing: 2,
    recommendedMissing: 5,
    amendments: 0,
    reviewerNotes: 0,
    mtdaVersion: "v1.0.0",        // amendment version on finalize (Method-Editor versioning ritual)
    sourceVersion: "draft",
    artifacts: [
      { id: "test_report", title: "Test Report", role: "Formal ISO 14126 results & report-ready tables", icon: "report", status: "warn", statusLabel: "Has warnings" },
      { id: "audit_report", title: "Audit Report", role: "Process-verification evidence for gates & execution", icon: "audit", status: "ok", statusLabel: "Available" },
      { id: "browser", title: "MTDA Browser", role: "Browsable overview that links every artifact in the archive", icon: "book", status: "ok", statusLabel: "Available" },
      { id: "folder", title: "Output folder", role: "Browse the MTDA archive on disk", icon: "folder", status: "ok", statusLabel: "47 members" },
      { id: "open_mtda", title: "Open MTDA", role: "Open extracted archive browser", icon: "package", status: "ok", statusLabel: "draft" },
    ],
  };

  // ---- Pre-finalize checks (recovered from Dataset Packaging F7 — validation drawer / live checks) ----
  const FINAL_CHECKS = {
    passed: [
      "Execution completed for all 7 runs",
      "Output deviation & tolerance checks within limits",
      "Acceptance policy applied · every flagged run reviewed",
      "35/35 critical method inputs bound",
      "MTDA archive written · 47 members",
    ],
    outOfScope: [
      "Raw-data plausibility (operator responsibility)",
      "Image-evidence completeness (not gated at finalize)",
    ],
    issues: [
      { level: "error", label: "2 required report fields missing — operator, fixture", jump: "report" },
      { level: "report", label: "5 recommended report fields blank", jump: "report" },
    ],
  };

  // ---- Finalization reason kinds (recovered from Method-Editor versioning contract) ----
  const FINAL_REASON_KINDS = [
    ["review_decisions", "Acceptance / review decisions"],
    ["report_completion", "Report-completion amendments"],
    ["mapping_repair", "Mapping repair"],
    ["other", "Other (describe in note)"],
  ];

  // Report-completion dialog fields — typed schema mirroring the MTDP schema
  // (type: string | float | date | enum | bool; units/min for float; enum choices).
  const REPORT_FIELDS = [
    { field: "report.operator", label: "Operator", section: "Test Identification", example: "G. Macori", level: "required", source: "missing", value: "",
      type: "string" },
    { field: "report.test_date", label: "Test date", section: "Test Identification", example: "2026-04-18", level: "recommended", source: "missing", value: "",
      type: "date" },
    { field: "report.fixture_description", label: "Fixture", section: "Loading Fixture", example: "4-pt CLC fixture", level: "required", source: "missing", value: "",
      type: "enum", choices: ["CLC (combined loading)", "4-pt CLC fixture", "end-loaded block", "shear-loaded (IITRI)"] },
    { field: "report.conditioning", label: "Conditioning", section: "Test Conditions", example: "23 °C / 50 % RH", level: "recommended", source: "missing", value: "",
      type: "enum", choices: ["23 °C / 50 % RH", "dry (as received)", "85 °C / 85 % RH", "not recorded"] },
    { field: "report.testing_speed", label: "Test speed", section: "Test Conditions", example: "1.0", level: "recommended", source: "missing", value: "",
      type: "float", unit: "mm/min", units: ["mm/min", "in/min"], min: 0 },
    { field: "report.strain_measurement_method", label: "Strain method", section: "Measurement Method", example: "video extensometer", level: "recommended", source: "missing", value: "",
      type: "enum", choices: ["video extensometer", "clip-on extensometer", "strain gauge", "DIC"] },
    { field: "report.specimen_type", label: "Specimen type", section: "Overview", example: "rectangular bar", level: "recommended", source: "missing", value: "",
      type: "enum", choices: ["rectangular bar", "waisted (necked)", "tabbed"] },
    { field: "report.loading_method", label: "Loading method", section: "Overview", example: "end-loaded", level: "recommended", source: "missing", value: "",
      type: "enum", choices: ["end-loaded", "shear-loaded", "mixed (combined)"] },
    { field: "report.tabbed", label: "Tabbed specimen", section: "Overview", example: "yes", level: "recommended", source: "missing", value: "",
      type: "bool" },
  ];

  // type → format hint chip (mirrors the MTDP under-row format chip)
  const TYPE_HINT = { string: "text", float: "number > 0", date: "date · yyyy-MM-dd", enum: "choices", bool: "yes / no" };

  return {
    APP_VERSION, PACKAGE, METHOD, AVAILABLE_SOURCES,
    BOUND_CRITICAL_COUNT, BOUND_EXAMPLES, REPORT_BIND_FIELDS, REPORT_FIELD_OPTIONS, METADATA_BLANK_COUNT,
    SOURCE_TYPE_LABEL, IMPORTANCE_LABEL,
    BINDINGS, STAGES, TRACE_SCRIPT, RUN_TABLE, FLAGGED, OUTPUT, REPORT_FIELDS, TYPE_HINT,
    FINAL_CHECKS, FINAL_REASON_KINDS,
  };
})();

const WIZ = window.WIZ;
const KEEP_INCLUDED_CONSEQUENCE = "Included in final report unless removed by operator";
const REMOVE_EXCLUDED_CONSEQUENCE = "Excluded from final report unless kept with justification";

// ===== components.jsx =====
/* ============================================================
   Shared components & icons
   ============================================================ */
const { useState, useEffect, useRef, useMemo, useCallback } = React;

/* ---- Icon set: simple geometric strokes only ---- */
function Icon({ name, className }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" };
  const paths = {
    package: <><path {...p} d="M3 6.5 9 3l6 3.5v5L9 15l-6-3.5z"/><path {...p} d="M3 6.5 9 10l6-3.5M9 10v5"/></>,
    method:  <><rect {...p} x="3.5" y="3" width="11" height="12" rx="1.5"/><path {...p} d="M6 6.5h6M6 9h6M6 11.5h3.5"/></>,
    mapping: <><circle {...p} cx="5" cy="5" r="1.8"/><circle {...p} cx="13" cy="13" r="1.8"/><path {...p} d="M6.7 5h3.3a2 2 0 0 1 2 2v4.3"/></>,
    report:  <><path {...p} d="M5 2.5h5L14 6v9.5H5z"/><path {...p} d="M9.5 2.5V6H14M7 9h5M7 11.5h5M7 6.5h2"/></>,
    audit:   <><rect {...p} x="3" y="3" width="12" height="12" rx="1.5"/><path {...p} d="M6 11l2-2.5 2 1.5 3-4"/></>,
    workbench: <><path {...p} d="M3.5 14.5 9 3l5.5 11.5z"/><path {...p} d="M6 11h6"/></>,
    folder:  <><path {...p} d="M2.5 5.5A1 1 0 0 1 3.5 4.5H7l1.3 1.4h6.2a1 1 0 0 1 1 1V13a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1z"/></>,
    copy:    <><rect {...p} x="5.5" y="5.5" width="8" height="9" rx="1.2"/><path {...p} d="M3.5 10.5V3.5a1 1 0 0 1 1-1h6"/></>,
    check:   <path {...p} d="M3.5 9.5 7 13l7-8"/>,
    warn:    <><path {...p} d="M9 2.8 16 14.5H2z"/><path {...p} d="M9 7v3.4M9 12.4v.1"/></>,
    info:    <><circle {...p} cx="9" cy="9" r="6.5"/><path {...p} d="M9 8.2v4M9 5.9v.1"/></>,
    x:       <path {...p} d="M4 4l10 10M14 4 4 14"/>,
    chevron: <path {...p} d="M4 7l5 5 5-5"/>,
    arrowR:  <path {...p} d="M3.5 9h11M10 4.5 14.5 9 10 13.5"/>,
    play:    <path {...p} d="M5 3.5 14 9l-9 5.5z" fill="currentColor"/>,
    pulse:   <path {...p} d="M2 9h3l2-5 4 10 2-5h3"/>,
    save:    <><path {...p} d="M3.5 3.5h8L15 7v7.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z"/><path {...p} d="M6 3.5v3.5h5M6 15v-4h6v4"/></>,
    edit:    <><path {...p} d="M11.5 3.5 14.5 6.5 6 15H3v-3z"/><path {...p} d="M10 5 13 8"/></>,
    link:    <><path {...p} d="M7.5 10.5 10.5 7.5"/><path {...p} d="M8 5.5 9.8 3.7a2.6 2.6 0 0 1 3.7 3.7l-1.8 1.8M10 12.5l-1.8 1.8a2.6 2.6 0 0 1-3.7-3.7L6.3 8.6"/></>,
    plus:    <path {...p} d="M9 4v10M4 9h10"/>,
    trash:   <><path {...p} d="M3.5 5h11M7 5V3.5h4V5M5 5l.7 9.5h6.6L13 5"/></>,
    filter:  <path {...p} d="M3 4h12l-4.5 5.5V14L7.5 12.5V9.5z"/>,
    book:    <><path {...p} d="M3 4.2C4.8 3 7 3 9 4.2 11 3 13.2 3 15 4.2V14c-1.8-1.2-4-1.2-6 0-2-1.2-4.2-1.2-6 0z"/><path {...p} d="M9 4.2V14"/></>,
    undo:    <><path {...p} d="M5 7H10.5a3.5 3.5 0 0 1 0 7H6"/><path {...p} d="M7 4 4 7l3 3"/></>,
    users:   <><circle {...p} cx="7" cy="6.5" r="2.4"/><path {...p} d="M2.5 14.5a4.5 4.5 0 0 1 9 0"/><path {...p} d="M12 4.4a2.4 2.4 0 0 1 0 4.6M13 14.5a4.5 4.5 0 0 0-2-3.6"/></>,
  };
  return (
    <svg className={className} viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
      {paths[name] || null}
    </svg>
  );
}

/* ---- Status chip ---- */
function Chip({ tone = "idle", children, dot = true }) {
  return (
    <span className="chip" data-tone={tone}>
      {dot && <span className="cdot" />}
      {children}
    </span>
  );
}

/* ---- Confidence meter: visual, not just a word ---- */
function Confidence({ value }) {
  const pct = Math.round(value * 100);
  const tone = value >= 0.8 ? "ok" : value >= 0.55 ? "warn" : "err";
  const label = value >= 0.8 ? "high" : value >= 0.55 ? "medium" : "low";
  const color = tone === "ok" ? "var(--ok-accent)" : tone === "warn" ? "var(--warn-accent)" : "var(--danger)";
  return (
    <div className="conf" title={`Match confidence ${pct}%`}>
      <div className="conf-bars">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} style={{ background: i < Math.round(value * 5) ? color : "var(--surface-3)" }} />
        ))}
      </div>
      <span className="conf-label" style={{ color }}>{label} · {pct}%</span>
    </div>
  );
}

/* ---- Bending sparkline: threshold line + assessment window + exceedance segments ---- */
function Sparkline({ series, threshold, peak, window, segments, width = 250, height = 96 }) {
  const values = Array.isArray(series) ? series.map(Number).filter(Number.isFinite) : [];
  const safeThreshold = Number.isFinite(Number(threshold)) ? Number(threshold) : 0;
  const safePeak = Number.isFinite(Number(peak)) ? Number(peak) : Math.max(safeThreshold, ...values, 0);
  const n = values.length;
  if (n < 2) {
    return <PlotGap message="Evidence gap: missing plot.bending_curve." />;
  }
  const max = Math.max(safePeak * 1.15, safeThreshold * 1.3, ...values, 0.01);
  const x = (i) => (i / (n - 1)) * (width - 8) + 4;
  const xf = (frac) => frac * (width - 8) + 4;
  const y = (v) => height - 10 - (v / max) * (height - 20);
  const line = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(n - 1).toFixed(1)} ${height - 10} L${x(0).toFixed(1)} ${height - 10} Z`;
  const ty = y(safeThreshold);
  const breach = safePeak > safeThreshold;
  const col = breach ? "var(--warn-accent)" : "var(--ok-accent)";
  const win = window || null;
  return (
    <div className="spark">
      <div className="spark-cap label-caps">bending % vs load · 10–90 % window</div>
      <svg width={width} height={height} className="spark-svg">
        <defs>
          <linearGradient id={`g-${safeThreshold}-${safePeak}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={col} stopOpacity="0.22" />
            <stop offset="100%" stopColor={col} stopOpacity="0" />
          </linearGradient>
        </defs>
        {win && <rect x={xf(win[0])} y="2" width={xf(win[1]) - xf(win[0])} height={height - 12} fill="var(--info-accent)" opacity="0.06" />}
        {win && [win[0], win[1]].map((w, i) => <line key={i} x1={xf(w)} y1="2" x2={xf(w)} y2={height - 10} stroke="var(--info-accent)" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />)}
        {(segments || []).map((s, i) => <rect key={i} x={xf(s[0])} y="2" width={xf(s[1]) - xf(s[0])} height={height - 12} fill="var(--warn-accent)" opacity="0.14" />)}
        <line x1="4" y1={ty} x2={width - 4} y2={ty} stroke="var(--danger)" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
        <text x={width - 6} y={ty - 4} textAnchor="end" fontSize="9" fill="var(--danger)" fontFamily="var(--mono)">thr {formatSignificantNumber(safeThreshold)}</text>
        <path d={area} fill={`url(#g-${safeThreshold}-${safePeak})`} />
        <path d={line} fill="none" stroke={col} strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

/* ---- Metric tile (review evidence) ---- */
function Metric({ k, v, sub, tone }) {
  return (
    <div className="metric" data-tone={tone || ""}>
      <div className="metric-k label-caps">{k}</div>
      <div className="metric-v">{v}</div>
      <div className="metric-sub">{sub}</div>
    </div>
  );
}

/* ---- Generic button ---- */
function Btn({ variant, size, icon, children, className, ...rest }) {
  const cls = ["btn", variant, size, className].filter(Boolean).join(" ");
  return (
    <button className={cls} {...rest}>
      {icon && <Icon name={icon} className="ic" />}
      {children}
    </button>
  );
}

Object.assign(window, { Icon, Chip, Confidence, Sparkline, Metric, Btn,
  useState, useEffect, useRef, useMemo, useCallback });

// ===== setup.jsx =====
/* ============================================================
   Setup spotlight — "Choose workflow inputs"
   Faithful to src setup_spotlight.py: input-summary tiles +
   collapsible decision task cards (bind report fields / accept
   warnings; recommended metadata) with an all-resolved empty state.
   ============================================================ */

function TaskCard({ badge, badgeTone, title, why, defaultOpen = true, collapsible = true, children, right }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="task">
      <div className={"task-head" + (open ? "" : " bare")} onClick={() => collapsible && setOpen((v) => !v)} style={{ cursor: collapsible ? "pointer" : "default" }}>
        <span className="task-flag" data-tone={badgeTone}>{badge}</span>
        <div className="col" style={{ gap: 1, minWidth: 0 }}>
          <span className="task-title">{title}</span>
          {why && <span className="taskWhy">{why}</span>}
        </div>
        <span className="spacer" />
        {right}
        {collapsible && <Icon name="chevron" className="task-chev" style={{ width: 15, height: 15, transform: open ? "none" : "rotate(-90deg)", color: "var(--ink-3)" }} />}
      </div>
      {open && <div className="task-body fade-in">{children}</div>}
    </div>
  );
}

function ReqMark({ level }) {
  // Requirement markers recovered from Dataset Packaging: * required-export, † report-required, ** recommended
  if (level === "required") return <span className="reqmark req" title="Required for complete report">*</span>;
  if (level === "report") return <span className="reqmark rep" title="Required for report">†</span>;
  return <span className="reqmark rec" title="Recommended report field">**</span>;
}

function InputTiles({ pkg, method, mappingState, mappingSummary, methodCount, onChangePackage, onChangeMethod, onEditMapping }) {
  const methodSub = method
    ? [method.version, method.standard].filter(Boolean).join(" · ")
    : (pkg ? `${methodCount || 1} implemented method${(methodCount || 1) === 1 ? "" : "s"} available` : "selected after package");
  const mappingSub = method
    ? (mappingSummary?.label || (mappingSummary ? `${mappingSummary.bound_count || 0}/${mappingSummary.critical_total || 0} critical bound` : "selected from method default"))
    : "selected after method";
  const tiles = [
    { k: "PACKAGE", v: pkg ? pkg.name : "not selected", sub: pkg ? `${pkg.runs} runs · ${pkg.family}` : "required", state: pkg ? "ok" : "pending", action: pkg ? "Change package" : "Choose package", on: onChangePackage, enabled: true },
    { k: "METHOD", v: method ? method.title : "not selected", sub: methodSub, state: method ? "ok" : "pending", action: method ? "Change method" : "Choose method", on: onChangeMethod, enabled: !!pkg },
    { k: "MAPPING", v: method ? (mappingSummary?.mapping_name || "default mapping") : "not selected", sub: mappingSub, state: method ? mappingState : "pending", action: "Review mapping", on: onEditMapping, enabled: !!method },
  ];
  return (
    <div className="inputs-row">
      {tiles.map((t) => (
        <div key={t.k} className="input-tile" data-state={t.state}>
          <div className="tile-k"><span className="tile-dot" />{t.k}</div>
          <div className="tile-v" title={t.v}>{t.v}</div>
          <div className="tile-meta">{t.sub}</div>
          {t.enabled && <div className="tile-link" onClick={t.on}>{t.action}</div>}
        </div>
      ))}
    </div>
  );
}

function SetupSpotlight(props) {
  const { pkg, method, pkgSel, setPkgSel, onChoosePackage, methodEntry, onConfirmMethod,
    mappingResolved, metadataResolved, onSaveBindings, onSkipBindings, onEditMapping,
    onOpenMetadata, onAcceptMetadata, onChangePackage, onChangeMethod,
    backendPackageError, analysisSession, methodOptions = [], selectedMethodId,
    onSelectMethodId, mappingSummary, recentPackages = [], recentPackageLoading,
    recentPackageError, onOpenPackageDialog, runEnabled, readinessStatus } = props;

  const reportBinds = WIZ.REPORT_BIND_FIELDS;
  const requiredBinds = reportBinds.filter((f) => f.level === "required").length;
  const allResolved = pkg && method && mappingResolved && metadataResolved;
  const pickerOptions = methodOptions.length ? methodOptions : [methodEntry || WIZ.METHOD];
  const requestedMethodId = selectedMethodId || pickerOptions[0]?.id || "";
  const activeMethod = pickerOptions.find((option) => option.id === requestedMethodId) || pickerOptions[0] || WIZ.METHOD;
  const activeMethodId = activeMethod?.id || "";
  const methodCountLabel = `${pickerOptions.length} method${pickerOptions.length === 1 ? "" : "s"} match${pickerOptions.length === 1 ? "es" : ""} ${pkg?.family || "the package"}`;
  const selectedMappingSummary = mappingSummary || method?.mappingSummary || activeMethod?.mappingSummary;
  const channelStatus = selectedMappingSummary
    ? `${selectedMappingSummary.bound_count || 0}/${selectedMappingSummary.critical_total || 0} critical inputs bound`
    : "mapping selected from method default";
  const sessionRunEnabled = isAnalysisSessionRunEnabled(analysisSession, runEnabled);
  const displayedReadinessStatus = readinessStatus || analysisReadinessStatus(analysisSession) || (runEnabled ? "WORKFLOW_READY" : "NOT_CHECKED");

  return (
    <div className="spotlight fade-in">
      <div className="page-head">
        <h1>{allResolved ? "Ready to run" : pkg && method ? "2 things to decide first" : "Choose workflow inputs"}</h1>
        <div className="sub">ISO 14126 on <b>{pkg ? pkg.name : "no package selected"}</b> · {pkg ? `${pkg.runs} runs · mechanical.compression` : "readiness not checked"}</div>
      </div>

      {analysisSession?.package && (
        <div className="banner" data-tone="info" style={{ marginBottom: 12 }}>
          <Icon name="package" className="b-ic" />
          <div className="b-txt"><b>Loaded from Dataset Packaging.</b> {analysisSession.package.package_path}</div>
        </div>
      )}
      {backendPackageError && (
        <div className="banner" data-tone="warn" style={{ marginBottom: 12 }}>
          <Icon name="warn" className="b-ic" />
          <div className="b-txt"><b>Package handoff failed.</b> {backendPackageError}</div>
        </div>
      )}
      {analysisSession?.readiness && (
        <div className="banner" data-tone={sessionRunEnabled ? "ok" : "warn"} style={{ marginBottom: 12 }}>
          <Icon name={sessionRunEnabled ? "check" : "warn"} className="b-ic" />
          <div className="b-txt">
            <b>Readiness {analysisSession.readiness.status}.</b>{" "}
            {(analysisSession.readiness.summary?.execution_critical_passed ?? 0)}/{(analysisSession.readiness.summary?.execution_critical_total ?? 0)} critical inputs · {(analysisSession.readiness.summary?.report_missing_total ?? 0)} report gaps
          </div>
        </div>
      )}

      <InputTiles
        pkg={pkg}
        method={method}
        mappingState={selectedMappingSummary?.critical_missing_count ? "warn" : "ok"}
        mappingSummary={selectedMappingSummary}
        methodCount={pickerOptions.length}
        onChangePackage={onChangePackage}
        onChangeMethod={onChangeMethod}
        onEditMapping={onEditMapping}
      />

      {/* ---- Phase: no package ---- */}
      {!pkg && (
        <TaskCard badge="needs you" badgeTone="warn" title="Choose an MTDP package" collapsible={false}
          right={<span className="muted-3" style={{ fontSize: "var(--t-xs)" }}>{recentPackageLoading ? "loading recent packages" : `${recentPackages.length} recent package${recentPackages.length === 1 ? "" : "s"}`}</span>}>
          <div className="card" style={{ overflow: "hidden", marginBottom: 12 }}>
            {recentPackages.length > 0 ? (
              <div className="pick-list">
                {recentPackages.map((p) => (
                  <div key={p.path} className={"pick" + (pkgSel === p.path ? " sel" : "")} onClick={() => { setPkgSel(p.path); onChoosePackage(p); }}>
                    <div className="p-ic"><Icon name="package" /></div>
                    <div className="p-main"><div className="p-name">{p.name}</div><div className="p-meta">{p.note} · {p.mtime || "recent"}</div></div>
                    <div className="p-runs">{p.runs ? `${p.runs} runs` : p.family}</div>
                    <div className="p-check"><Icon name="arrowR" /></div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty" style={{ padding: 18 }}>
                <div className="empty-title">{recentPackageLoading ? "Loading recent packages..." : "No recent packages found"}</div>
                <div className="muted" style={{ marginTop: 4 }}>{recentPackageError || "Open a package from a folder to add it to this list."}</div>
                <div className="row" style={{ marginTop: 12 }}>
                  <Btn variant="primary" icon="package" onClick={onOpenPackageDialog}>Choose package...</Btn>
                </div>
              </div>
            )}
          </div>
        </TaskCard>
      )}

      {/* ---- Phase: package, no method ---- */}
      {pkg && !method && (
        <TaskCard badge="needs you" badgeTone="warn" title="Choose an implemented method" collapsible={false}
          right={<span className="muted-3" style={{ fontSize: "var(--t-xs)" }}>{methodCountLabel}</span>}>
          <div className="method-pick-row">
            <span className="label-caps" style={{ flex: "none" }}>Method</span>
            <select
              className="field-input"
              style={{ maxWidth: 360 }}
              value={activeMethodId}
              onChange={(event) => onSelectMethodId?.(event.target.value)}
            >
              {pickerOptions.map((option) => <option key={option.id} value={option.id}>{option.short || option.title}</option>)}
            </select>
            <span className="chip" data-tone={selectedMappingSummary?.critical_missing_count ? "warn" : "ok"}>
              <Icon name="check" style={{ width: 12, height: 12 }} />{channelStatus}
            </span>
          </div>
          <div className="banner" data-tone="info" style={{ marginTop: 12 }}>
            <Icon name="info" className="b-ic" />
            <div className="b-txt"><b>{activeMethod.title}.</b> {activeMethod.summary}</div>
          </div>
          <div className="row" style={{ marginTop: 12, gap: 8 }}>
            <Btn variant="primary" icon="arrowR" onClick={onConfirmMethod}>Confirm method</Btn>
            <Btn onClick={onChangePackage}>Choose package…</Btn>
          </div>
        </TaskCard>
      )}

      {/* ---- Phase: both selected → the two decisions ---- */}
      {pkg && method && !allResolved && (
        <>
          {!mappingResolved && (
            <TaskCard badge="needs you" badgeTone="warn" title={`Bind ${reportBinds.length} report fields, or accept the warnings`}
              why={`${requiredBinds} of ${reportBinds.length} required · method runs either way.`}>
              <details className="bound-summary">
                <summary><span className="bs-dot" /><b>{WIZ.BOUND_CRITICAL_COUNT}</b> critical inputs bound automatically</summary>
                <div className="bound-chips" style={{ marginTop: 10 }}>
                  {WIZ.BOUND_EXAMPLES.map((b) => <span key={b} className="chip" data-tone="ok"><Icon name="check" style={{ width: 12, height: 12 }} />{b}</span>)}
                  <span className="chip-link" onClick={onEditMapping}>open mapping editor →</span>
                </div>
              </details>
              <div className="label-caps" style={{ color: "var(--warn-ink)", margin: "14px 0 8px" }}>Unbound report fields · {reportBinds.length} <span className="muted-3" style={{ textTransform: "none", letterSpacing: 0 }}>(not in the source package)</span></div>
              <div className="card" style={{ overflow: "hidden" }}>
                <table className="tbl">
                  <thead><tr><th style={{ width: "34%" }}>Field</th><th>Example value</th><th style={{ width: "38%" }}>Resolution</th></tr></thead>
                  <tbody>
                    {reportBinds.map((g) => {
                      const opts = WIZ.REPORT_FIELD_OPTIONS[g.field];
                      return (
                        <tr key={g.field}>
                          <td className="mono">{g.field} <ReqMark level={g.level} /></td>
                          <td className="muted">{g.example}</td>
                          <td>
                            <select className="field-input" defaultValue="" style={{ padding: "5px 9px" }}>
                              <option value="">Leave blank — accept warning</option>
                              {g.sources && g.sources.length > 0 && (
                                <optgroup label="Bind to package source">
                                  {g.sources.map((s) => <option key={s} value={"src:" + s}>{s}</option>)}
                                </optgroup>
                              )}
                              {opts && opts.length > 0 && (
                                <optgroup label="Set value">
                                  {opts.map((o) => <option key={o} value={"val:" + o}>{o}</option>)}
                                </optgroup>
                              )}
                              <option value="manual">Enter manually…</option>
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="row" style={{ marginTop: 13, gap: 8 }}>
                <Btn variant="primary" icon="save" onClick={onSaveBindings}>Save bindings</Btn>
                <Btn onClick={onSkipBindings}>Skip — accept warnings</Btn>
                <Btn icon="edit" onClick={onEditMapping}>Edit mapping profile…</Btn>
                <span className="spacer" />
                <span className="muted-3" style={{ fontSize: "var(--t-xs)" }}>Method runs either way.</span>
              </div>
            </TaskCard>
          )}

          {!metadataResolved && (
            <TaskCard badge="optional" badgeTone="info" title={`${WIZ.METADATA_BLANK_COUNT} recommended report fields blank`}
              why="Report-only — they don't affect the calculation." defaultOpen={mappingResolved}>
              <div className="row" style={{ gap: 8 }}>
                <Btn variant="primary" icon="report" onClick={onOpenMetadata}>Complete report fields</Btn>
                <Btn onClick={onAcceptMetadata}>Leave blank — accept warnings</Btn>
              </div>
            </TaskCard>
          )}
        </>
      )}

      {allResolved && (
        <div className="setup-empty fade-in">
          <div className="se-ic"><Icon name="check" /></div>
          <div className="se-t">All decisions resolved</div>
          <div className="se-s">Readiness <span className="mono">{displayedReadinessStatus}</span> · run is {runEnabled ? "enabled" : "not enabled"}. Use <b>Run method</b> below.</div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { SetupSpotlight, TaskCard, InputTiles, ReqMark });

// ===== mapping.jsx =====
/* ============================================================
   Mapping editor — highest-priority surface
   Value uptake from the implemented mapping interface:
     • channel-status taxonomy — matched (auto, with `via`
       provenance) · manual (user-assigned) · ambiguous (parser
       found ≥2 plausible families, treated as BLUE uncertainty,
       not amber) · unmapped (required = blocker, recommended = gap)
     • coverage-across-runs, example values, match reasons
   Progressive disclosure:
     • compact status readout + one banner instead of 4 always-on tiles
     • attention bindings (ambiguous + unmapped) surfaced first;
       resolved bindings collapse behind a count
     • All-candidates and Resolution-report are on-demand tabs
   ============================================================ */

function isResolved(b) { return b.status === "matched" || b.status === "manual"; }
function attnKind(b) { // for unresolved bindings
  if (b.status === "ambiguous") return "ambiguous";
  return b.req === "required" ? "blocker" : "gap";
}

function MappingEditor({ initial = [], mappingSummary, onClose, onSave, onBrowse, onSaveAs, onDirtyChange }) {
  function normalizeEditorBindings(rows) {
    return (rows || []).map((b) => ({ ...b, candidates: Array.isArray(b.candidates) ? b.candidates : [] }));
  }

  const [bindings, setBindings] = useState(() => normalizeEditorBindings(initial));
  const [selId, setSelId] = useState(() => {
    const attn = initial.find((b) => !isResolved(b));
    return attn ? attn.id : initial[0]?.id || "";
  });
  const [tab, setTab] = useState("repair");
  const [showResolved, setShowResolved] = useState(true);
  const [railOpen, setRailOpen] = useState(true);
  const [hovering, setHovering] = useState(false);
  const expanded = railOpen || hovering;
  const [customKind, setCustomKind] = useState("field");
  const [customSrc, setCustomSrc] = useState("");
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const sel = bindings.find((b) => b.id === selId);
  const mappingLabel = mappingSummary?.path || mappingSummary?.mapping_name || "Backend mapping profile";
  const selectBinding = (id) => { setSelId(id); setRailOpen(false); setHovering(false); }; // pick → collapse rail immediately

  function replaceEditorBindings(nextBindings) {
    const normalized = normalizeEditorBindings(nextBindings);
    setBindings(normalized);
    setSelId((current) => {
      if (normalized.some((row) => row.id === current)) return current;
      const attention = normalized.find((row) => !isResolved(row));
      return attention ? attention.id : normalized[0]?.id || "";
    });
    setDirty(false);
  }

  async function browseProfile() {
    if (!onBrowse) return;
    const nextBindings = await onBrowse({ bindings, dirty });
    if (Array.isArray(nextBindings)) replaceEditorBindings(nextBindings);
  }

  async function saveProfileAs() {
    if (!onSaveAs) return;
    const nextBindings = await onSaveAs(bindings, dirty);
    if (Array.isArray(nextBindings)) replaceEditorBindings(nextBindings);
  }

  const summary = useMemo(() => {
    const critical = bindings.filter((b) => b.req === "required");
    const critBound = critical.filter(isResolved).length;
    const report = bindings.filter((b) => b.req === "recommended");
    const repBound = report.filter(isResolved).length;
    const blockers = critical.filter((b) => !isResolved(b)).length;
    const ambiguous = bindings.filter((b) => b.status === "ambiguous").length;
    const reportGaps = report.filter((b) => b.status === "unmapped").length;
    return { critTotal: critical.length, critBound, repTotal: report.length, repBound, blockers, ambiguous, reportGaps };
  }, [bindings]);

  const groups = useMemo(() => {
    const attention = bindings.filter((b) => !isResolved(b));
    const resolved = bindings.filter(isResolved);
    return { attention, resolved };
  }, [bindings]);

  function bindTo(src, kind, asManual) {
    setBindings((bs) => bs.map((b) => b.id === selId
      ? { ...b, status: asManual ? "manual" : "matched", binding: src, kind: kind || b.kind, coverage: b.coverage === "—" ? "7/7 runs" : b.coverage, _custom: false }
      : b));
    setDirty(true);
  }
  function apply(srcObj) {
    setBindings((bs) => bs.map((b) => b.id === selId
      ? { ...b, status: "manual", binding: srcObj.source, coverage: srcObj.coverage === "—" ? "7/7 runs" : srcObj.coverage, _custom: false }
      : b));
    setDirty(true);
  }
  function clearBinding() {
    setBindings((bs) => bs.map((b) => b.id === selId
      ? { ...b, status: "unmapped", binding: "", coverage: "—", _custom: false }
      : b));
    setDirty(true);
  }
  function applyCustom() {
    if (!customSrc.trim()) return;
    setBindings((bs) => bs.map((b) => b.id === selId
      ? { ...b, status: "manual", binding: customSrc.trim(), coverage: "custom", kind: customKind, _custom: true }
      : b));
    setCustomSrc("");
    setDirty(true);
  }

  const headTone = summary.blockers ? "err" : (summary.ambiguous || summary.reportGaps) ? "warn" : "ok";

  return (
    <div className="scrim no-flicker-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" style={{ width: "min(1120px, 95vw)", height: "auto", maxHeight: "min(740px, 92%)" }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <Icon name="mapping" />
          <div className="col" style={{ gap: 1 }}>
            <h2>Method mapping</h2>
          </div>
          <span className="spacer" />
          <div className="path-field" style={{ maxWidth: 300 }} title={mappingLabel}><Icon name="mapping" style={{ width: 14, height: 14, flex: "none", opacity: .6 }} /><span>{mappingSummary?.mapping_name || mappingLabel}</span></div>
          <Btn size="sm" icon="folder" disabled={!onBrowse} onClick={browseProfile} title="Choose a mapping profile through the desktop backend.">Browse…</Btn>
        </div>

        <div className="dialog-body" style={{ display: "flex", flexDirection: "column", gap: 12, paddingBottom: 0 }}>
          {/* progressive disclosure: ONE status line, not four tiles */}
          <div className="map-readout" data-tone={headTone}>
            <Icon name={summary.blockers ? "warn" : (summary.ambiguous || summary.reportGaps) ? "info" : "check"} className="mr-ic" />
            <div className="mr-text">
              {summary.blockers
                ? <><b>Map {summary.blockers} required input{summary.blockers > 1 ? "s" : ""}</b> to make this package runnable.</>
                : summary.ambiguous
                  ? <><b>Disambiguate {summary.ambiguous} binding{summary.ambiguous > 1 ? "s" : ""}</b>, or leave the report field blank — critical inputs are already bound.</>
                  : summary.reportGaps
                    ? <><b>Optionally map {summary.reportGaps} report field{summary.reportGaps > 1 ? "s" : ""}</b> — or resolve them at finalization.</>
                    : <><b>Every method input has a confident source.</b> Save to use this profile.</>}
            </div>
            <div className="mr-stats">
              <span className="mr-stat"><b>{summary.critBound}/{summary.critTotal}</b> critical</span>
              <span className="mr-stat"><b>{summary.repBound}/{summary.repTotal}</b> report</span>
              {summary.ambiguous > 0 && <span className="mr-stat amb"><b>{summary.ambiguous}</b> ambiguous</span>}
            </div>
          </div>

          <div className="map-tabs">
            {[["repair", "Repair bindings"], ["all", "All candidates"], ["report", "Resolution report"]].map(([k, l]) => (
              <div key={k} className={"map-tab" + (tab === k ? " on" : "")} onClick={() => setTab(k)}>{l}</div>
            ))}
          </div>

          {tab === "repair" && (
            <div className={"map-repair" + (expanded ? " rail-is-open" : "")}>
              {/* rail: a plain collapsed strip; click or hover reopens it */}
              <div className={"rail-float" + (expanded ? " open" : "")}
                onMouseEnter={() => setHovering(true)} onMouseLeave={() => setHovering(false)}>
                <button className="rail-strip" onClick={() => setRailOpen(true)} title="Show bindings">
                  <Icon name="chevron" className="rail-strip-hint" style={{ width: 13, height: 13, transform: "rotate(-90deg)" }} />
                  <span className="rail-strip-label">Bindings</span>
                  <span className="rail-strip-cap" data-tone={groups.attention.length ? "warn" : "ok"}>{groups.attention.length > 0 ? groups.attention.length : <Icon name="check" style={{ width: 12, height: 12 }} />}</span>
                </button>
                <div className="rail-panel card">
                  <div className="bind-rail-head">
                    {groups.attention.length > 0
                      ? <span className="brh-t" data-tone="warn">Needs attention <span className="gcount">{groups.attention.length}</span></span>
                      : <span className="brh-t" data-tone="ok"><Icon name="check" style={{ width: 13, height: 13 }} />All resolved</span>}
                    <button className="brh-close" title="Collapse" onClick={() => { setRailOpen(false); setHovering(false); }}><Icon name="chevron" style={{ width: 13, height: 13, transform: "rotate(90deg)" }} /></button>
                  </div>
                  <div className="bind-list">
                    {groups.attention.length > 0
                      ? groups.attention.map((b) => <BindRow key={b.id} b={b} sel={b.id === selId} onClick={() => selectBinding(b.id)} />)
                      : <div className="bind-allclear"><Icon name="check" style={{ width: 16, height: 16 }} />Every input is resolved</div>}
                    <button className="bind-group-toggle" onClick={() => setShowResolved((v) => !v)}>
                      <Icon name="chevron" style={{ width: 12, height: 12, transform: showResolved ? "none" : "rotate(-90deg)" }} />
                      Resolved <span className="gcount">{groups.resolved.length}</span>
                      <span className="muted-3" style={{ marginLeft: "auto", fontSize: 11, fontWeight: 500 }}>{showResolved ? "hide" : "show"}</span>
                    </button>
                    {showResolved && groups.resolved.map((b) => <BindRow key={b.id} b={b} sel={b.id === selId} onClick={() => selectBinding(b.id)} />)}
                  </div>
                </div>
              </div>

              {/* resolution workspace — full width; rail floats over its left edge */}
              <div className="card resolve workspace-full">
                {sel && <ResolvePanel key={sel.id} b={sel} onApply={apply} onClear={clearBinding}
                  customKind={customKind} setCustomKind={setCustomKind}
                  customSrc={customSrc} setCustomSrc={setCustomSrc} onApplyCustom={applyCustom} />}
              </div>
            </div>
          )}

          {tab === "all" && <AllCandidates bindings={bindings} />}
          {tab === "report" && <ResolutionReport bindings={bindings} summary={summary} />}
        </div>

        <div className="dialog-foot">
          <Btn icon="save" disabled={!onSaveAs} onClick={saveProfileAs} title="Save the edited mapping profile through the desktop backend.">Save profile as…</Btn>
          <span className="spacer" />
          {dirty && <span className="muted" style={{ fontSize: "var(--t-xs)" }}>Unsaved edits → <span className="mono">iso14126_manual_wizard_edit.json</span></span>}
          <Btn onClick={onClose}>Close</Btn>
          <Btn variant="primary" icon="check" disabled={summary.blockers > 0} onClick={() => onSave(bindings, dirty)} title={summary.blockers ? "Map all execution-critical inputs first" : "Save edits and use this profile"}>
            {dirty ? "Save edits & use profile" : "Use this profile"}
          </Btn>
        </div>
      </div>
    </div>
  );
}

function StateDot({ b }) {
  // matched/manual = green; ambiguous = blue (parser uncertainty); unmapped req = red ring; recommended = amber
  let s = b.status;
  if (s === "unmapped") s = b.req === "required" ? "blocker" : "gap";
  return <span className="b-state" data-s={s} title={s} />;
}

function statusChip(b) {
  if (b.status === "matched") return <Chip tone="ok" dot={false}>auto</Chip>;
  if (b.status === "manual") return <Chip tone="info" dot={false}>manual</Chip>;
  if (b.status === "ambiguous") return <Chip tone="info" dot={false}>ambiguous</Chip>;
  return <Chip tone={b.req === "required" ? "err" : "warn"} dot={false}>{b.req === "required" ? "blocker" : "unmapped"}</Chip>;
}

function BindRow({ b, sel, onClick }) {
  return (
    <div className={"bind" + (sel ? " sel" : "")} onClick={onClick}>
      <StateDot b={b} />
      <div className="b-main">
        <span className="b-input">{b.input}</span>
        <span className="b-bind">
          {b.binding
            ? <><span className="arrow">→</span><span className="val">{b.binding}</span></>
            : b.status === "ambiguous"
              ? <span className="amb">{b.candidates.length} plausible sources — choose one</span>
              : <span className="none">no source bound</span>}
        </span>
      </div>
      <div className="b-right">
        {statusChip(b)}
        <span className="muted-3" style={{ fontSize: 11, fontFamily: "var(--mono)" }}>{b.coverage}</span>
      </div>
    </div>
  );
}

function ResolvePanel({ b, onApply, onClear, customKind, setCustomKind, customSrc, setCustomSrc, onApplyCustom }) {
  const ambiguous = b.status === "ambiguous";
  const hdr = b.note ? (b.note.match(/“(.+)”/)?.[1] || null) : null;
  const tone = isResolved(b) ? "ok" : ambiguous ? "info" : b.req === "required" ? "err" : "warn";
  const candSources = new Set(b.candidates.map((c) => c.source));
  return (
    <>
      <div className="resolve-head" data-tone={tone}>
        <div className="rh-line">
          <span className="r-input">{b.input}</span>
          {statusChip(b)}
          <span className="rh-req" data-req={b.req}>{b.req}</span>
        </div>
        <div className="r-desc">
          {b.desc} · expects <b>{b.kind}</b>{b.unit ? <> in <span className="mono">{b.unit}</span></> : ""} · {b.coverage}
        </div>
        <div className="rh-state">
          {isResolved(b)
            ? <>Bound to <span className="rh-bound mono">{b.binding}</span>{b.status === "matched" && b.via ? <span className="rh-via"> · auto · {b.via}</span> : <span className="rh-via"> · manual</span>}</>
            : ambiguous
              ? <>Parser found <b>{b.candidates.length}</b> plausible sources{hdr ? <> for header <span className="mono">“{hdr}”</span></> : null} — choose one</>
              : <span style={{ color: b.req === "required" ? "var(--err-ink)" : "var(--warn-ink)" }}>{b.req === "required" ? "Unmapped — blocks readiness" : "Unmapped — report field will be blank"}</span>}
        </div>
      </div>
      <div className="resolve-body">
        <div className="label-caps">{ambiguous ? "Choose the correct source" : "Suggested sources"} · {b.candidates.length}</div>
        {b.candidates.map((c) => {
          const applied = b.binding === c.source;
          return (
            <div key={c.source} className={"cand" + (applied ? " applied" : "")} onClick={() => !applied && onApply(c)}>
              <div className="cand-top">
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="c-src">{c.kind}:{c.source}</div>
                  <div className="cand-meta">
                    <span className="cm-cov">{c.coverage}</span><span className="cm-sep">·</span>
                    <span className="ex mono">{c.example}</span>
                  </div>
                </div>
                <Confidence value={c.confidence} />
              </div>
              <div className="cand-foot">
                <span className="cand-reason">{c.reason}</span>
                {applied
                  ? <span className="cand-applied"><Icon name="check" style={{ width: 13, height: 13 }} />Applied</span>
                  : <span className="cand-cta">{ambiguous ? "Use this" : "Use source"}<Icon name="arrowR" style={{ width: 13, height: 13 }} /></span>}
              </div>
            </div>
          );
        })}

        <details className="custom-details">
          <summary>Bind to another variable in the package…</summary>
          <div className="custom-row" style={{ marginTop: 10 }}>
            <select className="field-input" value={customSrc ? `${customKind}:${customSrc}` : ""} onChange={(e) => {
              const v = e.target.value;
              if (!v) { setCustomSrc(""); return; }
              const [k, ...rest] = v.split(":");
              setCustomKind(k); setCustomSrc(rest.join(":"));
            }}>
              <option value="">Choose a source variable…</option>
              {Object.entries(WIZ.AVAILABLE_SOURCES).map(([kind, list]) => (
                <optgroup key={kind} label={kind === "metadata" ? "Metadata fields" : kind === "field" ? "Specimen / fixture fields" : "Channels"}>
                  {list.filter((s) => !candSources.has(s)).map((s) => <option key={s} value={`${kind}:${s}`}>{s}</option>)}
                </optgroup>
              ))}
            </select>
            <Btn size="sm" icon="link" disabled={!customSrc.trim()} onClick={onApplyCustom}>Bind</Btn>
          </div>
          <div className="custom-hint">Only variables present in this package are listed — bindings are validated on save.</div>
        </details>

        {b.binding && (
          <button className="clear-link" onClick={onClear}>Clear binding{b.req === "required" ? " — will block readiness" : ""}</button>
        )}
      </div>
    </>
  );
}

function AllCandidates({ bindings }) {
  const rows = bindings.flatMap((b) => b.candidates.map((c) => ({ ...c, input: b.input, req: b.req, applied: b.binding === c.source })));
  return (
    <div className="card" style={{ overflow: "auto", marginBottom: 16 }}>
      <table className="tbl">
        <thead><tr><th>Method input</th><th>Source</th><th>Kind</th><th>Coverage</th><th>Confidence</th><th>Provenance</th><th></th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="mono">{r.input}</td>
              <td className="mono">{r.source}</td>
              <td className="muted">{r.kind}</td>
              <td className="muted">{r.coverage}</td>
              <td><Confidence value={r.confidence} /></td>
              <td className="muted" style={{ fontSize: "var(--t-xs)" }}>{r.via || r.reason}</td>
              <td>{r.applied && <Chip tone="ok"><Icon name="check" style={{ width: 11, height: 11 }} />applied</Chip>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResolutionReport({ bindings, summary }) {
  const resLabel = (b) => isResolved(b) ? (b.status === "matched" ? "auto-matched" : "manual") : b.status === "ambiguous" ? "ambiguous" : b.req === "required" ? "missing" : "unmapped";
  const resTone = (b) => isResolved(b) ? "ok" : b.status === "ambiguous" ? "info" : b.req === "required" ? "err" : "warn";
  return (
    <div className="fade-in" style={{ marginBottom: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="rr-stats">
        <div className="rr-stat" data-tone={summary.blockers ? "err" : "ok"}>
          <div className="rr-v">{summary.critBound}<span className="rr-tot">/{summary.critTotal}</span></div>
          <div className="rr-k">critical inputs bound</div>
        </div>
        <div className="rr-stat" data-tone={summary.repBound < summary.repTotal ? "warn" : "ok"}>
          <div className="rr-v">{summary.repBound}<span className="rr-tot">/{summary.repTotal}</span></div>
          <div className="rr-k">report fields bound</div>
        </div>
        <div className="rr-stat" data-tone={summary.ambiguous ? "info" : "idle"}>
          <div className="rr-v">{summary.ambiguous}</div>
          <div className="rr-k">ambiguous resolutions</div>
        </div>
      </div>
      <div className="card" style={{ overflow: "hidden" }}>
        <table className="tbl rr-tbl">
          <thead><tr><th>Method input</th><th>Req.</th><th>Resolution</th><th>Bound source</th><th>Provenance</th><th>Coverage</th></tr></thead>
          <tbody>
            {bindings.map((b) => (
              <tr key={b.id}>
                <td className="mono">{b.input}</td>
                <td>{b.req === "required" ? <span className="reqmark req" title="Required">*</span> : <span className="reqmark rec" title="Recommended">**</span>}</td>
                <td><Chip tone={resTone(b)} dot={false}>{resLabel(b)}</Chip></td>
                <td className="mono muted">{b.binding ? `${b.kind}:${b.binding}` : "—"}</td>
                <td className="muted" style={{ fontSize: "var(--t-xs)" }}>{b.status === "matched" ? (b.via || "auto") : b.status === "manual" ? "user-assigned" : "—"}</td>
                <td className="muted mono" style={{ fontSize: "var(--t-xs)" }}>{b.coverage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Object.assign(window, { MappingEditor });

// ===== running.jsx =====
/* ============================================================
   Running spotlight — credible live execution
   ============================================================ */

function Running({ onComplete, onCancel, pushLog, backendRun = null, backendMode = false, demoMode = false }) {
  if (backendRun?.run_id || backendRun?.status) {
    return <BackendRunning backendRun={backendRun} onComplete={onComplete} />;
  }
  if (backendMode) {
    return <BackendRunning backendRun={{ status: "running", phase: "queued", progress_percent: 0, message: "Starting backend method run.", events: [], run_status: {} }} onComplete={onComplete} />;
  }
  if (!demoMode) {
    return (
      <div className="spotlight fade-in">
        <div className="page-head">
          <h1>Running method</h1>
          <div className="sub">No analysed backend run is available for this method execution.</div>
        </div>
        <div className="card card-pad">
          <div className="banner" data-tone="warn">
            <Icon name="warn" className="b-ic" />
            <div className="b-txt"><b>Backend analysis session required.</b> Start the method through the desktop bridge or open a dataset package first.</div>
          </div>
        </div>
      </div>
    );
  }
  const [idx, setIdx] = useState(0);           // index into TRACE_SCRIPT
  const [pct, setPct] = useState(0);
  const [trace, setTrace] = useState([]);
  const traceRef = useRef(null);
  const script = WIZ.TRACE_SCRIPT;
  const current = script[Math.min(idx, script.length - 1)];

  // run-table state derived from progress
  const runStates = useMemo(() => {
    const order = ["run_001", "run_002", "run_003", "run_004", "run_005", "run_006", "run_007"];
    return WIZ.RUN_TABLE.map((r, i) => {
      const reduceStart = 42, reduceEnd = 71;
      const slice = (reduceEnd - reduceStart) / order.length;
      const myStart = reduceStart + i * slice;
      let status = "queued";
      if (pct >= myStart + slice) status = r.status === "flagged" ? "flagged" : "complete";
      else if (pct >= myStart && pct < reduceEnd + 4) status = "running";
      if (pct >= 90) status = r.status === "flagged" ? "flagged" : "complete";
      return { ...r, liveStatus: status };
    });
  }, [pct]);

  useEffect(() => {
    if (idx >= script.length) { const t = setTimeout(onComplete, 900); return () => clearTimeout(t); }
    const ev = script[idx];
    const t = setTimeout(() => {
      setPct(ev.pct);
      setTrace((tr) => [...tr, { ...ev, ts: clock(idx) }]);
      pushLog && pushLog({ level: ev.level, msg: ev.msg });
      setIdx((i) => i + 1);
    }, idx === 0 ? 350 : 620);
    return () => clearTimeout(t);
  }, [idx]);

  useEffect(() => { if (traceRef.current) traceRef.current.scrollTop = traceRef.current.scrollHeight; }, [trace]);

  const stageState = (name) => {
    const ci = WIZ.STAGES.indexOf(current.stage);
    const ni = WIZ.STAGES.indexOf(name);
    if (ni < ci) return "done";
    if (ni === ci) return pct >= 100 ? "done" : "active";
    return "todo";
  };

  const running = pct < 100;
  const runRows = runStates.filter((r) => true);
  const counts = {
    complete: runStates.filter((r) => r.liveStatus === "complete").length,
    running: runStates.filter((r) => r.liveStatus === "running").length,
    queued: runStates.filter((r) => r.liveStatus === "queued").length,
    flagged: runStates.filter((r) => r.liveStatus === "flagged").length,
  };

  return (
    <div className="spotlight fade-in">
      <div className="page-head">
        <h1>Running method</h1>
        <div className="sub">ISO 14126 on <b>{WIZ.PACKAGE.name}</b> · {running ? "writing MTDA output" : "execution complete"}</div>
      </div>

      <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="run-head">
          <div className="rh-main">
            <div className="run-phase">{phaseLabel(current.stage, pct)}</div>
            <div className="run-meta">started 14:22 · output → {WIZ.OUTPUT.mtda} · {trace.length} log events</div>
          </div>
          <div className="run-pct">{pct}%</div>
        </div>
        <div className="progress"><div style={{ width: pct + "%" }} /></div>

        <div className="stage-strip">
          {WIZ.STAGES.map((s) => (
            <div key={s} className="stagebox" data-s={stageState(s)}>{s}</div>
          ))}
        </div>

        <div className="run-stats">
          <div className="run-stat"><div className="k">Active stage</div><div className="v">{current.stage}</div></div>
          <div className="run-stat"><div className="k">Run rows</div><div className="v">{counts.running} running · {counts.queued} queued · {counts.complete + counts.flagged} done</div></div>
          <div className="run-stat"><div className="k">Latest event</div><div className="v" style={{ fontSize: "var(--t-sm)", fontWeight: 500 }}>{current.msg}</div></div>
        </div>
      </div>

      <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        <div className="label-caps">Live analysis trace</div>
        <div className="trace" ref={traceRef}>
          {trace.map((t, i) => (
            <div key={i} className="trace-line" data-l={t.level}>
              <span className="t-ts">{t.ts}</span>
              <span className="t-pct">{t.pct}%</span>
              <span className="t-msg">{t.stage} · {t.msg}</span>
            </div>
          ))}
          {running && <div className="trace-line"><span className="t-ts">{clock(idx)}</span><span className="t-pct">{pct}%</span><span className="t-msg" style={{ color: "#6f7783" }}>▍</span></div>}
        </div>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "11px 16px", borderBottom: "1px solid var(--border)" }}><span className="label-caps">Per-run status</span></div>
        <div style={{ maxHeight: 220, overflow: "auto" }}>
          <table className="tbl">
            <thead><tr><th style={{ width: 110 }}>Run</th><th style={{ width: 120 }}>Status</th><th>Notes</th></tr></thead>
            <tbody>
              {runRows.map((r) => (
                <tr key={r.run}>
                  <td className="mono" style={{ fontWeight: 600 }}>{r.run}</td>
                  <td><span className="run-status-pill" data-s={r.liveStatus}>{r.liveStatus === "running" ? "● running" : r.liveStatus}</span></td>
                  <td className="muted">{r.liveStatus === "queued" ? "—" : r.liveStatus === "running" ? "Computing compression properties…" : r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function BackendRunning({ backendRun, onComplete }) {
  const status = backendRun?.status || "running";
  const pct = Number(backendRun?.progress_percent ?? 0);
  const phase = backendRun?.phase || "queued";
  const message = backendRun?.message || "Method run queued.";
  const events = backendRun?.events || [];
  const result = backendRun?.result || {};
  const traceRef = useRef(null);
  const runStatus = backendRun?.run_status || {};
  const runRows = Object.keys(runStatus).length
    ? Object.entries(runStatus).map(([run, liveStatus]) => ({ run, liveStatus, note: liveStatus }))
    : [];
  const counts = {
    complete: runRows.filter((r) => r.liveStatus === "complete" || r.liveStatus === "completed").length,
    running: runRows.filter((r) => r.liveStatus === "running").length,
    queued: runRows.filter((r) => r.liveStatus === "queued").length,
    flagged: runRows.filter((r) => r.liveStatus === "flagged").length,
  };

  useEffect(() => {
    if (status === "completed") {
      const t = setTimeout(onComplete, 250);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [status, onComplete]);

  useEffect(() => {
    if (traceRef.current) traceRef.current.scrollTop = traceRef.current.scrollHeight;
  }, [events.length]);

  const stageState = (name) => {
    const normalized = phase.toLowerCase();
    if (name.toLowerCase().includes(normalized.split("_")[0])) return "active";
    return pct >= 100 ? "done" : "todo";
  };

  return (
    <div className="spotlight fade-in">
      <div className="page-head">
        <h1>{status === "completed" ? "Method run complete" : status === "failed" ? "Method run failed" : "Running method"}</h1>
        <div className="sub">{phaseLabel(phase, pct)} · output <b>{result.output_path || backendRun?.output_path || WIZ.OUTPUT.mtda}</b></div>
      </div>

      <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="run-head">
          <div className="rh-main">
            <div className="run-phase">{message}</div>
            <div className="run-meta">{status} · {events.length} backend event{events.length === 1 ? "" : "s"}</div>
          </div>
          <div className="run-pct">{pct}%</div>
        </div>
        <div className="progress"><div style={{ width: pct + "%" }} /></div>

        <div className="stage-strip">
          {WIZ.STAGES.map((s) => (
            <div key={s} className="stagebox" data-s={stageState(s)}>{s}</div>
          ))}
        </div>

        <div className="run-stats">
          <div className="run-stat"><div className="k">Backend phase</div><div className="v">{phase}</div></div>
          <div className="run-stat"><div className="k">Run rows</div><div className="v">{counts.running} running · {counts.queued} queued · {counts.complete + counts.flagged} done</div></div>
          <div className="run-stat"><div className="k">Latest event</div><div className="v" style={{ fontSize: "var(--t-sm)", fontWeight: 500 }}>{message}</div></div>
        </div>
      </div>

      <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        <div className="label-caps">Backend analysis trace</div>
        <div className="trace" ref={traceRef}>
          {events.map((event, i) => {
            const data = event.data || {};
            return (
              <div key={event.event_id || i} className="trace-line" data-l={data.status === "failed" ? "err" : data.status === "completed" ? "ok" : "info"}>
                <span className="t-ts">{clock(i)}</span>
                <span className="t-pct">{data.progress_percent ?? pct}%</span>
                <span className="t-msg">{data.phase || event.event} · {data.message || event.event}</span>
              </div>
            );
          })}
          {status === "running" && <div className="trace-line"><span className="t-ts">{clock(events.length)}</span><span className="t-pct">{pct}%</span><span className="t-msg" style={{ color: "#6f7783" }}>waiting for backend event</span></div>}
        </div>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "11px 16px", borderBottom: "1px solid var(--border)" }}><span className="label-caps">Per-run status</span></div>
        <div style={{ maxHeight: 220, overflow: "auto" }}>
          <table className="tbl">
            <thead><tr><th style={{ width: 110 }}>Run</th><th style={{ width: 120 }}>Status</th><th>Notes</th></tr></thead>
            <tbody>
              {runRows.length ? runRows.map((r) => (
                <tr key={r.run}>
                  <td className="mono" style={{ fontWeight: 600 }}>{r.run}</td>
                  <td><span className="run-status-pill" data-s={r.liveStatus}>{r.liveStatus}</span></td>
                  <td className="muted">{r.note || (status === "completed" ? "Backend result ready" : "Waiting for backend progress")}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="3" className="muted">Per-run backend progress will appear when the analyser reports run status.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function phaseLabel(stage, pct) {
  if (pct >= 100) return "Execution complete";
  const map = {
    Input: "Loading package", Method: "Resolving method", Mapping: "Applying mapping",
    Ready: "Confirming readiness", Resolve: "Resolving method inputs", Reduce: "Reducing method runs",
    Validate: "Validating output", Accept: "Applying acceptance policy", Write: "Writing MTDA output",
    Report: "Generating reports", Workbench: "Building workbench", Done: "Finishing",
  };
  return map[stage] || stage;
}
function clock(i) {
  const base = 14 * 3600 + 22 * 60 + 1;
  const t = base + i * 2;
  const h = Math.floor(t / 3600) % 24, m = Math.floor((t % 3600) / 60), s = t % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

Object.assign(window, { Running });

// ===== review.jsx =====
/* ============================================================
   Review spotlight — "Confirm flagged runs"
   Faithful to src review_spotlight.py + diagnostic_cockpit.py:
   RUN · DEFAULT · DEFECTS · REASON · DECISION; expandable evidence
   with one-or-many diagnostic cockpits (Bending / Curve shape) in
   tabs, acceptance-findings cluster, scoped "WHY KEEP?" override,
   and excluded/restore rows.
   ============================================================ */

function CurveSparkline({ points, reference, cohort, width = 420, height = 168 }) {
  const all = [...(points || []), ...(reference || []), ...(cohort || []).flat()].filter((p) => Number.isFinite(Number(p?.x)) && Number.isFinite(Number(p?.y)));
  if (all.length < 2) {
    return <PlotGap message="Evidence gap: missing plot.curve_family_curve." />;
  }
  const maxY = Math.max(...all.map((p) => p.y)) * 1.08;
  const maxX = Math.max(...all.map((p) => p.x)) * 1.02;
  const X = (x) => 6 + (x / maxX) * (width - 12);
  const Y = (y) => height - 10 - (y / maxY) * (height - 20);
  const path = (pts) => pts.map((p, i) => `${i === 0 ? "M" : "L"}${X(p.x).toFixed(1)} ${Y(p.y).toFixed(1)}`).join(" ");
  return (
    <div className="spark">
      <div className="spark-cap label-caps">stress–strain · focus vs cohort</div>
      <svg width={width} height={height} className="spark-svg">
        {cohort.map((c, i) => <path key={i} d={path(c)} fill="none" stroke="var(--ink-4)" strokeWidth="1" opacity="0.5" />)}
        <path d={path(reference)} fill="none" stroke="var(--info-accent)" strokeWidth="1.4" strokeDasharray="4 3" opacity="0.85" />
        <path d={path(points)} fill="none" stroke="var(--warn-accent)" strokeWidth="2" />
      </svg>
      <div className="spark-legend">
        <span><i style={{ background: "var(--warn-accent)" }} />this run</span>
        <span><i style={{ background: "var(--info-accent)" }} />reference</span>
        <span><i style={{ background: "var(--ink-4)" }} />cohort</span>
      </div>
    </div>
  );
}

function PlotGap({ message }) {
  return (
    <div className="spark plot-gap">
      <div className="spark-cap label-caps">diagnostic plot</div>
      <div className="plot-gap-body">{message || "Evidence gap: diagnostic plot data unavailable."}</div>
    </div>
  );
}

function numericFlagField(flag, ...keys) {
  for (const key of keys) {
    const raw = flag?.[key];
    if (raw === null || raw === undefined || raw === "") continue;
    const number = Number(raw);
    if (Number.isFinite(number)) return number;
    const match = String(raw).match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/i);
    if (match) {
      const parsed = Number(match[0]);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function formatPercentLike(value, fallback = "not reported") {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return `${formatSignificantNumber(number)}%`;
}

function flagEvidenceText(flag) {
  const refs = Array.isArray(flag?.evidence_refs) ? flag.evidence_refs.map(String).filter(Boolean) : [];
  return refs.length ? refs.slice(0, 2).join(" · ") : "";
}

function flagKind(flag) {
  if (flagHasText(flag, "bending")) return "bending";
  if (flagHasText(flag, "curve family") || flagHasText(flag, "curve shape")) return "curve_family";
  return "decision_context";
}

function bendingSignalLabel(flag) {
  const valueText = String(flag?.value ?? "");
  if (valueText && !Number.isFinite(Number(valueText))) return titleLabel(valueText);
  const message = String(flag?.message || flag?.reason || "").toLowerCase();
  if (message.includes("sustained")) return "Sustained bending";
  if (message.includes("transient")) return "Transient bending";
  if (message.includes("window")) return "Windowed bending review";
  return "Bending review";
}

function parseFiniteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const text = String(value).trim().replace(/,/g, ".");
  const number = Number(text);
  if (Number.isFinite(number)) return number;
  const match = text.match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/i);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function pointNumber(point, ...keys) {
  for (const key of keys) {
    const value = parseFiniteNumber(point?.[key]);
    if (value !== null) return value;
  }
  return null;
}

function pointRunId(point, ...keys) {
  for (const key of keys) {
    const raw = point?.[key];
    if (raw === null || raw === undefined) continue;
    const value = String(raw).trim();
    if (value) return value;
  }
  return "";
}

function normalizePointPairs(points, xKeys, yKeys, runKeys = []) {
  if (!Array.isArray(points)) return [];
  return points.map((point) => {
    const x = pointNumber(point, ...xKeys);
    const y = pointNumber(point, ...yKeys);
    if (x === null || y === null) return null;
    const runId = pointRunId(point, ...runKeys);
    return { x, y, runId };
  }).filter(Boolean);
}

function compactTickLabel(value, suffix = "") {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  const abs = Math.abs(number);
  const text = abs >= 1000
    ? formatSignificantNumber(number / 1000) + "k"
    : formatSignificantNumber(number);
  return `${text}${suffix}`;
}

function linearTicks(min, max, count = 4) {
  const start = Number(min);
  const end = Number(max);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return [];
  const steps = Math.max(1, count - 1);
  return Array.from({ length: steps + 1 }, (_, index) => start + ((end - start) * index) / steps);
}

function PlotAxes({ xTicks, yTicks, xAt, yAt, xLabel, yLabel, plotLeft, plotRight, plotTop, plotBottom, xSuffix = "", ySuffix = "" }) {
  return (
    <g className="plot-axes">
      {yTicks.map((tick, index) => {
        const y = yAt(tick);
        return (
          <g key={`y-${index}`}>
            <line x1={plotLeft} y1={y} x2={plotRight} y2={y} stroke="var(--border)" strokeWidth="1" opacity={index === 0 ? "0.85" : "0.45"} />
            <text x={plotLeft - 7} y={y + 3} textAnchor="end" fontSize="9" fill="var(--ink-4)" fontFamily="var(--mono)">{compactTickLabel(tick, ySuffix)}</text>
          </g>
        );
      })}
      {xTicks.map((tick, index) => {
        const x = xAt(tick);
        return (
          <g key={`x-${index}`}>
            <line x1={x} y1={plotTop} x2={x} y2={plotBottom} stroke="var(--border)" strokeWidth="1" opacity="0.28" />
            <text x={x} y={plotBottom + 13} textAnchor="middle" fontSize="9" fill="var(--ink-4)" fontFamily="var(--mono)">{compactTickLabel(tick, xSuffix)}</text>
          </g>
        );
      })}
      <rect x={plotLeft} y={plotTop} width={plotRight - plotLeft} height={plotBottom - plotTop} fill="none" stroke="var(--border)" strokeWidth="1" />
      <text x={(plotLeft + plotRight) / 2} y={plotBottom + 29} textAnchor="middle" fontSize="10" fill="var(--ink-4)">{xLabel}</text>
      <text x={9} y={(plotTop + plotBottom) / 2} transform={`rotate(-90 9 ${(plotTop + plotBottom) / 2})`} textAnchor="middle" fontSize="10" fill="var(--ink-4)">{yLabel}</text>
    </g>
  );
}

function BendingEvidencePlot({ cockpit, width = 420, height = 176 }) {
  const plot = cockpit?.plot || {};
  const rawTrace = Array.isArray(plot.trace_points) ? plot.trace_points : (Array.isArray(cockpit?.trace_points) ? cockpit.trace_points : []);
  const trace = normalizePointPairs(rawTrace, ["load_N", "load", "x"], ["bending_percent", "bending", "y"]).map(({ x, y }) => ({ x, y }));
  if (trace.length < 2) {
    return (
      <Sparkline
        series={Array.isArray(plot.series) ? plot.series : (Array.isArray(cockpit.series) ? cockpit.series : [])}
        threshold={plot.threshold ?? cockpit.threshold ?? 0}
        peak={plot.peak ?? cockpit.peak ?? 0}
        window={cockpit.window}
        segments={cockpit.segments}
        width={width}
        height={height}
      />
    );
  }
  const threshold = Number(plot.threshold ?? 0);
  const xs = trace.map((point) => point.x);
  const ys = trace.map((point) => point.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs) > xMin ? Math.max(...xs) : xMin + 1;
  const yMin = Math.min(0, ...ys);
  const yMaxBase = Math.max(...ys, Number.isFinite(threshold) ? threshold : 0, 0.01);
  const yMax = yMaxBase > yMin ? yMaxBase * 1.08 : yMin + 1;
  const plotLeft = 52;
  const plotRight = width - 12;
  const plotTop = 12;
  const plotBottom = height - 34;
  const xAt = (value) => plotLeft + ((value - xMin) / (xMax - xMin)) * (plotRight - plotLeft);
  const yAt = (value) => plotBottom - ((value - yMin) / (yMax - yMin)) * (plotBottom - plotTop);
  const path = trace.map((point, index) => `${index === 0 ? "M" : "L"}${xAt(point.x).toFixed(1)} ${yAt(point.y).toFixed(1)}`).join(" ");
  const windowRange = Array.isArray(plot.assessment_window) ? plot.assessment_window.map(Number) : [];
  const segments = Array.isArray(plot.exceedance_segments) ? plot.exceedance_segments : [];
  const thresholdY = Number.isFinite(threshold) ? yAt(threshold) : null;
  const xTicks = linearTicks(xMin, xMax, 4);
  const yTicks = linearTicks(yMin, yMax, 4);
  return (
    <div className="spark" data-plot-source="mtda-bending-trace">
      <div className="spark-cap label-caps">bending % vs load · 10–90 % window</div>
      <svg width={width} height={height} className="spark-svg">
        <PlotAxes xTicks={xTicks} yTicks={yTicks} xAt={xAt} yAt={yAt} xLabel="Load / N" yLabel="Bending / %" plotLeft={plotLeft} plotRight={plotRight} plotTop={plotTop} plotBottom={plotBottom} ySuffix="%" />
        {windowRange.length === 2 && Number.isFinite(windowRange[0]) && Number.isFinite(windowRange[1]) && (
          <rect
            x={Math.max(plotLeft, Math.min(plotRight, xAt(Math.min(windowRange[0], windowRange[1]))))}
            y={plotTop}
            width={Math.max(0, Math.min(plotRight, xAt(Math.max(windowRange[0], windowRange[1]))) - Math.max(plotLeft, xAt(Math.min(windowRange[0], windowRange[1]))))}
            height={plotBottom - plotTop}
            fill="var(--info-accent)"
            opacity="0.07"
          />
        )}
        {segments.map((segment, index) => {
          const start = Number(segment.start_load_N);
          const end = Number(segment.end_load_N);
          if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
          const left = Math.max(plotLeft, Math.min(plotRight, xAt(Math.min(start, end))));
          const right = Math.max(plotLeft, Math.min(plotRight, xAt(Math.max(start, end))));
          return <rect key={index} x={left} y={plotTop} width={Math.max(0, right - left)} height={plotBottom - plotTop} fill="var(--warn-accent)" opacity="0.16" />;
        })}
        {thresholdY !== null && (
          <>
            <line x1={plotLeft} y1={thresholdY} x2={plotRight} y2={thresholdY} stroke="var(--danger)" strokeWidth="1" strokeDasharray="3 3" opacity="0.75" />
            <text x={plotRight - 2} y={thresholdY - 4} textAnchor="end" fontSize="9" fill="var(--danger)" fontFamily="var(--mono)">thr {formatSignificantNumber(threshold)}</text>
          </>
        )}
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function CurveFamilyEvidencePlot({ cockpit, width = 420, height = 168 }) {
  const plot = cockpit?.plot || {};
  const sourcePoints = Array.isArray(plot.points) ? plot.points : (Array.isArray(cockpit?.points) ? cockpit.points : []);
  const sourceReference = Array.isArray(plot.reference_points)
    ? plot.reference_points
    : (Array.isArray(cockpit?.reference_points) ? cockpit.reference_points : (Array.isArray(cockpit.reference) ? cockpit.reference : []));
  const normalizedPoints = normalizePointPairs(sourcePoints, ["x", "x_common", "experiment_progress", "strain_percent", "strain", "run_strain"], ["stress", "y", "y_reference", "stress_MPa", "y_observed", "y_aligned", "stress_mpa"], ["run_id", "run", "runId", "id"]);
  const orphanedPoints = [];
  const grouped = new Map();
  const focusRunIdCandidate = String(plot.focus_run_id || cockpit.focus_run_id || "");
  normalizedPoints.forEach((point) => {
    const runId = point.runId;
    if (!runId) {
      orphanedPoints.push({ x: point.x, y: point.y });
      return;
    }
    if (!grouped.has(runId)) grouped.set(runId, []);
    grouped.get(runId).push({ x: point.x, y: point.y });
  });
  if (grouped.size === 0 && orphanedPoints.length > 0) {
    grouped.set(focusRunIdCandidate || "run", orphanedPoints);
  }
  const reference = normalizePointPairs(sourceReference, ["x", "x_common", "experiment_progress", "strain_percent"], ["stress", "y", "y_reference", "stress_MPa"]).map((point) => ({ x: point.x, y: point.y }));
  if (!grouped.size) {
    return (
      <CurveSparkline
        points={sourcePoints}
        reference={sourceReference}
        cohort={Array.isArray(plot.cohort) ? plot.cohort : (Array.isArray(cockpit?.cohort) ? cockpit.cohort : [])}
        width={width}
        height={height}
      />
    );
  }
  const focusRunId = String(plot.focus_run_id || cockpit.focus_run_id || "");
  const all = [...Array.from(grouped.values()).flat(), ...reference];
  const xMin = Math.min(...all.map((point) => point.x));
  const xMax = Math.max(...all.map((point) => point.x)) > xMin ? Math.max(...all.map((point) => point.x)) : xMin + 1;
  const yMin = Math.min(0, ...all.map((point) => point.y));
  const yMaxBase = Math.max(0.01, ...all.map((point) => point.y));
  const yMax = yMaxBase > yMin ? yMaxBase * 1.08 : yMin + 1;
  const plotLeft = 52;
  const plotRight = width - 12;
  const plotTop = 12;
  const plotBottom = height - 36;
  const xAt = (value) => plotLeft + ((value - xMin) / (xMax - xMin)) * (plotRight - plotLeft);
  const yAt = (value) => plotBottom - ((value - yMin) / (yMax - yMin)) * (plotBottom - plotTop);
  const path = (points) => points.map((point, index) => `${index === 0 ? "M" : "L"}${xAt(point.x).toFixed(1)} ${yAt(point.y).toFixed(1)}`).join(" ");
  const xTicks = linearTicks(xMin, xMax, 4);
  const yTicks = linearTicks(yMin, yMax, 4);
  return (
    <div className="spark" data-plot-source="mtda-curve-family">
      <div className="spark-cap label-caps">stress-strain · focus vs cohort</div>
      <svg width={width} height={height} className="spark-svg">
        <PlotAxes xTicks={xTicks} yTicks={yTicks} xAt={xAt} yAt={yAt} xLabel="Normalised strain / %" yLabel="Stress" plotLeft={plotLeft} plotRight={plotRight} plotTop={plotTop} plotBottom={plotBottom} />
        {Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([runId, points]) => (
          points.length >= 2
            ? <path key={runId} d={path(points)} fill="none" stroke={runId === focusRunId ? "var(--danger)" : "var(--ink-4)"} strokeWidth={runId === focusRunId ? "2.4" : "1"} opacity={runId === focusRunId ? "0.95" : "0.48"} />
            : null
        ))}
        {reference.length >= 2 && <path d={path(reference)} fill="none" stroke="var(--ink-1)" strokeWidth="1.4" strokeDasharray="4 3" opacity="0.82" />}
      </svg>
      <div className="spark-legend">
        <span><i style={{ background: "var(--danger)" }} />this run</span>
        <span><i style={{ background: "var(--ink-1)" }} />reference</span>
        <span><i style={{ background: "var(--ink-4)" }} />cohort</span>
      </div>
    </div>
  );
}

function CockpitPane({ cockpit }) {
  return (
    <div className="cockpit">
      <div className="cockpit-plot">
        {cockpit.kind === "decision_context"
          ? (
            <div className="decision-context">
              <div className="label-caps">{cockpit.title || "Decision context"}</div>
              <div className="decision-context-summary">{cockpit.summary || "Review the run validity before accepting the final report selection."}</div>
              {cockpit.evidence && <div className="muted">{cockpit.evidence}</div>}
            </div>
          )
          : cockpit.kind === "bending"
          ? <BendingEvidencePlot cockpit={cockpit} />
          : cockpit.kind === "curve_family"
          ? <CurveFamilyEvidencePlot cockpit={cockpit} />
          : <PlotGap message={(cockpit.plot?.missing_required_keys || []).length ? `Evidence gap: missing ${cockpit.plot.missing_required_keys.join(", ")}.` : "Evidence gap: diagnostic plot data unavailable."} />}
      </div>
      <div className="cockpit-cards">
        {cockpit.cards.map((c) => (
          <div key={c.key} className="metric" data-tone={c.level === "warn" ? "warn" : ""}>
            <div className="metric-k label-caps">{c.label}</div>
            <div className="metric-v">{formatNumericText(c.value)}</div>
            <div className="metric-sub">{formatNumericText(c.sub)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidencePane({ f }) {
  const [tab, setTab] = useState(0);
  const cockpits = f.cockpits || [];
  return (
    <div className="evidence fade-in">
      {cockpits.length > 1 && (
        <div className="cockpit-tabs">
          {cockpits.map((c, i) => (
            <button key={i} className={"cockpit-tab" + (tab === i ? " on" : "")} onClick={() => setTab(i)}>{c.tab}</button>
          ))}
        </div>
      )}
      {cockpits.length >= 1 && <CockpitPane cockpit={cockpits[Math.min(tab, cockpits.length - 1)]} />}
      {f.narrative && <div className="ev-narrative" dangerouslySetInnerHTML={{ __html: formatNumericText(f.narrative) }} />}
    </div>
  );
}

function FlaggedRow({ f, open, decision, reason, onToggle, onDecide, onReason, onRestore }) {
  if (f.excluded) {
    return (
      <div className="acc-row-wrap excluded">
        <div className="acc-row">
          <div className="a-run">{f.run}</div>
          <div><span className="excluded-tag">excluded</span></div>
          <div className="a-defects">{f.defects.join(" + ")}</div>
          <div className="a-reason">{f.reason}</div>
          <div className="acc-decide"><Btn size="sm" icon="undo" onClick={onRestore}>Restore…</Btn></div>
        </div>
      </div>
    );
  }
  const isKeep = decision === "Keep";
  const needsReason = isKeep && f.defaultCall === "Remove";
  const defectText = f.defects.join(" + ");
  return (
    <div className="acc-row-wrap">
      <div className={"acc-row" + (open ? " open" : "")} onClick={onToggle}>
        <div className="a-run"><Icon name="chevron" className="exp" style={{ width: 13, height: 13 }} />{f.run}</div>
        <div><Chip tone={f.defaultCall === "Keep" ? "ok" : "err"} dot={false}>{f.defaultCall}</Chip></div>
        <div className="a-defects" title={defectText}>{f.defects.map((d) => <span key={d} className="defect-chip">{d}</span>)}</div>
        <div className="a-reason" title={formatNumericText(f.reason)}>{formatNumericText(f.reason)}</div>
        <div className="acc-decide" onClick={(e) => e.stopPropagation()}>
          <button className={"dbtn keep" + (isKeep ? " on" : "")} onClick={() => onDecide("Keep")}>Keep run</button>
          <button className={"dbtn remove" + (!isKeep ? " on" : "")} onClick={() => onDecide("Remove")}>Remove run</button>
        </div>
      </div>
      {open && <EvidencePane f={f} />}
      {open && needsReason && (
        <div className="justify fade-in">
          <div className="col" style={{ gap: 2, flex: "none", maxWidth: 220 }}>
            <span className="j-k">Why keep?</span>
            <span className="j-scope">Motivate every override covered by this run decision: {defectText}</span>
          </div>
          <input className="field-input" placeholder={`Motivate keeping this run despite ${defectText.toLowerCase()}`} value={reason} onChange={(e) => onReason(e.target.value)} autoFocus />
        </div>
      )}
    </div>
  );
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function titleLabel(value) {
  const text = String(value || "acceptance finding").replace(/[_-]+/g, " ").trim();
  return text ? text.split(/\s+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ") : "Acceptance finding";
}

function formatSignificantNumber(value, significant = 3) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "");
  if (number === 0) return "0";
  const abs = Math.abs(number);
  if (abs < 1) {
    const decimals = Math.max(0, significant - 1 - Math.floor(Math.log10(abs)));
    return number.toFixed(decimals).replace(/0+$/, "").replace(/\.$/, "");
  }
  const rounded = Number(number.toPrecision(significant));
  return String(rounded);
}

function formatNumericText(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return formatSignificantNumber(value);
  return String(value).replace(/-?\d+\.\d{4,}(?:e[+-]?\d+)?/gi, (match) => formatSignificantNumber(Number(match)));
}

function acceptanceFlagRank(flag) {
  const severity = String(flag?.severity || "").toLowerCase();
  if (["exclude", "error", "critical", "invalid"].includes(severity)) return 3;
  if (["review", "warn_review", "requires_review"].includes(severity)) return 2;
  if (["warn", "warning"].includes(severity)) return 1;
  return 0;
}

function flagHasText(flag, token) {
  const text = [
    flag?.category,
    flag?.source,
    flag?.rule_id,
    flag?.flag_id,
    flag?.message,
    flag?.reason,
    ...(Array.isArray(flag?.evidence_refs) ? flag.evidence_refs : []),
  ]
    .join(" ")
    .toLowerCase()
    .replace(/[_-]+/g, " ");
  return text.includes(String(token || "").toLowerCase().replace(/[_-]+/g, " "));
}

function defectLabelsForFlags(flags) {
  const labels = [];
  flags.forEach((flag) => {
    let label = "";
    if (flagHasText(flag, "bending")) label = "Bending";
    else if (flagHasText(flag, "curve family") || flagHasText(flag, "curve shape")) label = "Curve shape";
    else label = titleLabel(flag?.category || flag?.rule_id || flag?.flag_id);
    if (label && !labels.includes(label)) labels.push(label);
  });
  return labels.length ? labels : ["Acceptance finding"];
}

function selectionEffectRemoves(flag) {
  return String(flag?.selection_effect || "").toLowerCase().includes("excluded");
}

function normalizedFlagPayload(flag) {
  return {
    severity: String(flag?.severity || "flag"),
    category: String(flag?.category || "acceptance"),
    message: String(flag?.message || flag?.reason || "Acceptance flag requires review"),
    evidence_refs: Array.isArray(flag?.evidence_refs)
      ? flag.evidence_refs.map(String)
      : String(flag?.evidence_refs || "").split(";").map((item) => item.trim()).filter(Boolean),
    flag_id: String(flag?.flag_id || ""),
    rule_id: String(flag?.rule_id || ""),
    source: String(flag?.source || ""),
    selection_effect: String(flag?.selection_effect || ""),
    value: flag?.value,
    threshold: flag?.threshold,
    metric: flag?.metric,
    points_above_threshold: flag?.points_above_threshold,
    assessed_points: flag?.assessed_points,
  };
}

function normalizeBackendCockpit(cockpit) {
  const canonicalPoints = Array.isArray(cockpit?.points)
    ? cockpit.points
    : Array.isArray(cockpit?.plot?.points)
      ? cockpit.plot.points
      : [];
  const canonicalReferencePoints = Array.isArray(cockpit?.reference_points)
    ? cockpit.reference_points
    : Array.isArray(cockpit?.reference)
      ? cockpit.reference
      : Array.isArray(cockpit?.plot?.reference_points)
        ? cockpit.plot.reference_points
        : [];
  const canonicalSeries = Array.isArray(cockpit?.series)
    ? cockpit.series
    : Array.isArray(cockpit?.plot?.series)
      ? cockpit.plot.series
      : [];
  const canonicalTracePoints = Array.isArray(cockpit?.trace_points)
    ? cockpit.trace_points
    : Array.isArray(cockpit?.plot?.trace_points)
      ? cockpit.plot.trace_points
      : [];
  const plot = {
    ...(cockpit?.plot && typeof cockpit.plot === "object" ? cockpit.plot : {}),
    ...(canonicalTracePoints.length ? { trace_points: canonicalTracePoints } : {}),
    ...(canonicalSeries.length ? { series: canonicalSeries } : {}),
    ...(canonicalPoints.length ? { points: canonicalPoints } : {}),
    ...(canonicalReferencePoints.length ? { reference_points: canonicalReferencePoints } : {}),
    ...(cockpit?.focus_run_id ? { focus_run_id: String(cockpit.focus_run_id) } : {}),
    ...(Array.isArray(cockpit?.missing_required_keys) ? { missing_required_keys: cockpit.missing_required_keys } : {}),
  };
  const plotKind = String(plot.plot_kind || "").toLowerCase();
  const inferredKind = plotKind.includes("bending")
    ? "bending"
    : (plotKind.includes("curve_family") || plotKind.includes("curve_shape") || plotKind.includes("curve-family"))
    ? "curve_family"
    : Array.isArray(plot.points) || Array.isArray(plot.reference_points) || Array.isArray(cockpit?.points)
    ? "curve_family"
    : Array.isArray(plot.trace_points) || Array.isArray(plot.series) || Array.isArray(cockpit?.series)
    ? "bending"
    : "diagnostic";
  return {
    ...cockpit,
    kind: cockpit?.kind || inferredKind,
    tab: cockpit?.tab || titleLabel(plot.plot_kind || "Diagnostic"),
    title: cockpit?.title || plot.title || "Diagnostic evidence",
    plot,
    points: canonicalPoints,
    reference: canonicalReferencePoints,
    series: canonicalSeries,
    trace_points: canonicalTracePoints,
    cards: Array.isArray(cockpit?.cards)
      ? cockpit.cards.map((card, index) => ({
          key: String(card?.key || card?.evidence_key || `card-${index}`),
          label: String(card?.label || card?.key || "Evidence"),
          value: card?.value ?? "",
          sub: card?.sub ?? card?.subtext ?? "",
          level: String(card?.level || ""),
          state: String(card?.state || ""),
        }))
      : [],
  };
}

function clampEvidencePayloadValues(payload) {
  if (!payload || typeof payload !== "object") return {};
  const result = {};
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined) return;
    result[key] = value;
  });
  return result;
}

function hasDecisionPlotData(cockpit) {
  if (cockpit?.kind === "bending") {
    const plot = cockpit?.plot || {};
    const tracePoints = Array.isArray(plot.trace_points) ? plot.trace_points : (Array.isArray(cockpit?.trace_points) ? cockpit.trace_points : []);
    const usableTracePoints = tracePoints.filter((point) => {
      const x = pointNumber(point, "load_N", "load", "x");
      const y = pointNumber(point, "bending_percent", "bending", "y");
      return x !== null && y !== null;
    });
    const series = Array.isArray(plot.series)
      ? plot.series
      : Array.isArray(cockpit?.series)
        ? cockpit.series
        : [];
    const usableSeries = series.filter((value) => Number.isFinite(Number(value)));
    return usableTracePoints.length >= 2 || usableSeries.length >= 2;
  }
  if (cockpit?.kind === "curve_family") {
    const plot = cockpit?.plot || {};
    const points = Array.isArray(plot.points) ? plot.points : Array.isArray(cockpit?.points) ? cockpit.points : [];
    const referencePoints = Array.isArray(plot.reference_points)
      ? plot.reference_points
      : Array.isArray(cockpit?.reference_points)
        ? cockpit.reference_points
        : Array.isArray(cockpit?.reference)
          ? cockpit.reference
          : [];
    const usablePoints = points.filter((point) => {
      const x = pointNumber(point, "x", "x_common", "experiment_progress", "strain_percent", "strain", "run_strain");
      const y = pointNumber(point, "stress", "y", "y_reference", "stress_MPa", "y_observed", "y_aligned", "stress_mpa");
      return x !== null && y !== null;
    });
    const usableReferencePoints = referencePoints.filter((point) => {
      const x = pointNumber(point, "x", "x_common", "experiment_progress", "strain_percent", "strain", "run_strain");
      const y = pointNumber(point, "stress", "y", "y_reference", "stress_MPa", "y_observed", "y_aligned", "stress_mpa");
      return x !== null && y !== null;
    });
    return usablePoints.length >= 2 || usableReferencePoints.length >= 2;
  }
  return false;
}

function hasDecisionCockpit(cockpit) {
  return cockpit?.kind === "bending" || cockpit?.kind === "curve_family";
}

function evidenceCockpitFallback(row, flags, defaultCall) {
  const groupedFlags = new Map();
  flags.forEach((flag) => {
    const kind = flagKind(flag);
    if (!groupedFlags.has(kind)) groupedFlags.set(kind, []);
    groupedFlags.get(kind).push(flag);
  });
  const rowPayload = clampEvidencePayloadValues(row);
  const evidenceKinds = [];
  if (Array.isArray(rowPayload.bending_trace_points) ? rowPayload.bending_trace_points.length : 0) evidenceKinds.push("bending");
  if (Array.isArray(rowPayload.bending_series) ? rowPayload.bending_series.length : 0) evidenceKinds.push("bending");
  if (Array.isArray(rowPayload.curve_family_points) ? rowPayload.curve_family_points.length : 0) evidenceKinds.push("curve_family");
  if (Array.isArray(rowPayload.curve_family_reference_points) ? rowPayload.curve_family_reference_points.length : 0) evidenceKinds.push("curve_family");

  const preferredKinds = [];
  if (evidenceKinds.includes("bending")) preferredKinds.push("bending");
  if (evidenceKinds.includes("curve_family")) preferredKinds.push("curve_family");
  ["decision_context"].forEach((kind) => {
    if (groupedFlags.has(kind)) preferredKinds.push(kind);
  });

  const dedupedKinds = [];
  for (const kind of preferredKinds) {
    if (!dedupedKinds.includes(kind)) dedupedKinds.push(kind);
  }

  return dedupedKinds
    .map((kind) => {
      if (kind === "bending") {
        const flag = groupedFlags.get("bending")?.[0] || {};
        const threshold = numericFlagField(flag, "threshold", "bending_threshold") ?? rowPayload.bending_threshold ?? 0.1;
        const peak = numericFlagField(flag, "value", "bending_peak", "measured_value") ?? rowPayload.bending_peak ?? threshold * 1.35;
        const pointsAbove = numericFlagField(flag, "points_above_threshold") ?? rowPayload.bending_points_above_threshold ?? 1;
        const assessed = numericFlagField(flag, "assessed_points") ?? rowPayload.bending_assessed_points ?? 1;
        return {
          kind: "bending",
          tab: "Bending",
          title: "Bending evidence",
          plot: {
            plot_kind: "bending_evidence",
            series: Array.isArray(rowPayload.bending_series) ? rowPayload.bending_series : [],
            trace_points: Array.isArray(rowPayload.bending_trace_points) ? rowPayload.bending_trace_points : [],
            threshold,
            peak,
            assessment_window: Array.isArray(rowPayload.bending_assessment_window) ? rowPayload.bending_assessment_window : [0.1, 0.9],
            exceedance_segments: Array.isArray(rowPayload.bending_exceedance_segments) ? rowPayload.bending_exceedance_segments : [],
          },
          window: [0.1, 0.9],
          segments: (Array.isArray(rowPayload.bending_exceedance_segments) && rowPayload.bending_exceedance_segments.length > 0)
            ? rowPayload.bending_exceedance_segments
            : [],
          cards: [
            { key: "bending.call", label: "Observed signal", value: bendingSignalLabel(flag), sub: "opposite-face strain imbalance", level: "warn" },
            { key: "bending.max_percent", label: "Peak imbalance", value: formatPercentLike(peak), sub: flag?.value ? "reported by acceptance check" : "estimated from analysis evidence", level: "warn" },
            { key: "bending.threshold_percent", label: "Review limit", value: threshold ? formatPercentLike(threshold) : "not configured", sub: "method threshold for bending review", level: threshold ? "info" : "warn" },
            { key: "bending.points_above_threshold", label: "Persistence", value: String(pointsAbove), sub: `${pointsAbove} of ${assessed} assessed points above limit`, level: "warn" },
            { key: "selection.consequence_summary", label: "Recommended action", value: defaultCall === "Remove" ? REMOVE_EXCLUDED_CONSEQUENCE : KEEP_INCLUDED_CONSEQUENCE, sub: "final report consequence", level: "info" },
          ],
        };
      }
      if (kind === "curve_family") {
        const flag = groupedFlags.get("curve_family")?.[0] || {};
        const metric = numericFlagField(flag, "value", "curve_family_value") ?? rowPayload.curve_family_value;
        const threshold = numericFlagField(flag, "threshold", "curve_family_threshold") ?? rowPayload.curve_family_threshold;
        const value = numericFlagField(flag, "value", "curve_family_value") ?? metric;
        return {
          kind: "curve_family",
          tab: "Curve shape",
          title: "Curve-shape evidence",
          plot: {
            plot_kind: "curve_family",
            points: Array.isArray(rowPayload.curve_family_points) ? rowPayload.curve_family_points : [],
            reference_points: Array.isArray(rowPayload.curve_family_reference_points) ? rowPayload.curve_family_reference_points : [],
            focus_run_id: String(rowPayload.curve_family_focus_run_id || ""),
          },
          points: Array.isArray(rowPayload.curve_family_points) ? rowPayload.curve_family_points : [],
          reference: Array.isArray(rowPayload.curve_family_reference_points) ? rowPayload.curve_family_reference_points : [],
          cohort: [],
          cards: [
            { key: "curve_family.classification", label: "Scientific call", value: String(value > (threshold || 0) ? "Distance outlier" : "Within family"), sub: "curve-shape assessment", level: value > (threshold || 0) ? "warn" : "info" },
            { key: "curve_family.metric", label: "Primary metric", value: `${titleLabel(flag?.metric || "shape distance")} ${formatSignificantNumber(value)}`, sub: `review limit ${formatSignificantNumber(threshold)}`, level: value > (threshold || 0) ? "warn" : "info" },
            { key: "curve_family.source", label: "Comparison", value: "run vs cohort", sub: "stress-strain family", level: "info" },
            { key: "selection.consequence_summary", label: "Recommended action", value: defaultCall === "Remove" ? REMOVE_EXCLUDED_CONSEQUENCE : KEEP_INCLUDED_CONSEQUENCE, sub: "final report consequence", level: "info" },
          ],
        };
      }
      if (kind === "decision_context" && groupedFlags.has("decision_context")) {
        return cockpitFromAcceptanceFlag(groupedFlags.get("decision_context")[0], defaultCall, groupedFlags.get("decision_context"));
      }
      return null;
    })
    .filter(Boolean);
}

function scientificCockpits(existingCockpits, flags, defaultCall, row) {
  const existing = Array.isArray(existingCockpits) ? existingCockpits : [];
  const existingDecisionCockpits = existing.filter(hasDecisionCockpit);
  const existingNonDecision = existing.filter((cockpit) => !hasDecisionCockpit(cockpit));
  const fallbackFromEvidence = evidenceCockpitFallback(row, flags, defaultCall);
  const fallbackByKind = new Map(fallbackFromEvidence.map((cockpit) => [cockpit.kind, cockpit]));
  const seenKinds = new Set();
  const mergedDecisionCockpits = [];

  for (const cockpit of existingDecisionCockpits) {
    const kind = cockpit?.kind;
    if (hasDecisionPlotData(cockpit)) {
      mergedDecisionCockpits.push(cockpit);
      if (kind) seenKinds.add(kind);
      continue;
    }
    if (kind && fallbackByKind.has(kind)) {
      mergedDecisionCockpits.push(fallbackByKind.get(kind));
      fallbackByKind.delete(kind);
      seenKinds.add(kind);
      continue;
    }
    mergedDecisionCockpits.push(cockpit);
    if (kind) seenKinds.add(kind);
  }

  const fallbackCockpits = fallbackFromEvidence.filter((cockpit) => !seenKinds.has(cockpit.kind));
  if (mergedDecisionCockpits.length) return [...mergedDecisionCockpits, ...fallbackCockpits, ...existingNonDecision];
  if (fallbackCockpits.length) return [...fallbackCockpits, ...existingNonDecision];
  if (existing.length) return existing;
  return cockpitsFromAcceptanceFlags(flags, defaultCall);
}

function reviewRowsFromBackendRun(run) {
  const rows = run?.result?.review_rows || run?.review_rows || run?.result?.reviewRows || run?.reviewRows;
  if (!Array.isArray(rows) || !rows.length) return [];
  return rows.map((row, index) => {
    const flags = Array.isArray(row?.acceptance_flags) ? row.acceptance_flags : [];
    const flagsPayload = flags.map(normalizedFlagPayload);
    const defaultCall = String(row?.default_call || row?.defaultCall || row?.default_decision || row?.decision || "Remove");
    const runId = String(row?.run_id || row?.run || row?.runId || row?.id || "");
    const rowKey = String(row?.row_id || row?.key || row?.review_id || runId || `review-row-${index}`);
    return {
      rowKey,
      run: runId,
      defaultCall,
      excluded: Boolean(row?.is_excluded || row?.excluded),
      defects: Array.isArray(row?.defect_labels) && row.defect_labels.length ? row.defect_labels.map(String) : defectLabelsForFlags(flags),
      reason: String(row?.reason || "Acceptance flag requires review"),
      flags: flagsPayload,
      narrative: flagsPayload.length
        ? decisionNarrativeFromFlags(flagsPayload, defaultCall)
        : String(row?.narrative_html || escapeHtml(row?.reason || "Acceptance evidence requires operator review.")),
      cockpits: scientificCockpits(
        Array.isArray(row?.cockpits) ? row.cockpits.map(normalizeBackendCockpit) : [],
        flagsPayload,
        defaultCall,
        row,
      ),
    };
  }).filter((row) => row.run);
}

function cockpitsFromAcceptanceFlags(flags, defaultCall) {
  const grouped = new Map();
  flags.forEach((flag) => {
    const kind = flagKind(flag);
    if (!grouped.has(kind)) grouped.set(kind, []);
    grouped.get(kind).push(flag);
  });
  const orderedKinds = ["bending", "curve_family", "decision_context"].filter((kind) => grouped.has(kind));
  return orderedKinds.map((kind) => cockpitFromAcceptanceFlag(grouped.get(kind)[0], defaultCall, grouped.get(kind)));
}

function cockpitFromAcceptanceFlag(flag, defaultCall, relatedFlags = [flag]) {
  const kind = flagKind(flag);
  const consequence = defaultCall === "Remove" ? REMOVE_EXCLUDED_CONSEQUENCE : KEEP_INCLUDED_CONSEQUENCE;
  const message = String(flag?.message || flag?.reason || "Acceptance flag requires review.");
  if (kind === "bending") {
    const threshold = numericFlagField(flag, "threshold", "bending_threshold") ?? 0.1;
    const peak = numericFlagField(flag, "value", "bending_peak", "measured_value") ?? threshold * 1.35;
    const pointsAbove = numericFlagField(flag, "points_above_threshold") ?? (message.toLowerCase().includes("sustained") ? 6 : 1);
    const assessed = numericFlagField(flag, "assessed_points") ?? 41;
    const share = assessed ? pointsAbove / assessed : 0;
    return {
      kind: "bending",
      tab: "Bending",
      title: "Bending evidence",
      plot: {
        plot_kind: "bending_evidence",
        series: [],
        trace_points: [],
        threshold,
        peak,
        assessment_window: [0.1, 0.9],
        exceedance_segments: [],
      },
      window: [0.10, 0.90],
      segments: pointsAbove > 1 ? [[0.52, 0.52 + Math.min(0.32, share + 0.06)]] : [],
      cards: [
        { key: "bending.call", label: "Observed signal", value: bendingSignalLabel(flag), sub: "opposite-face strain imbalance", level: "warn" },
        { key: "bending.max_percent", label: "Peak imbalance", value: formatPercentLike(peak), sub: flag?.value ? "reported by acceptance check" : "estimated from review flag", level: "warn" },
        { key: "bending.threshold_percent", label: "Review limit", value: flag?.threshold ? formatPercentLike(threshold) : "not configured", sub: "method threshold for bending review", level: flag?.threshold ? "info" : "warn" },
        { key: "bending.points_above_threshold", label: "Persistence", value: String(pointsAbove), sub: `${pointsAbove} of ${assessed} assessed points above limit`, level: "warn" },
        { key: "selection.consequence_summary", label: "Recommended action", value: consequence, sub: "final report consequence", level: "info" },
      ],
    };
  }
  if (kind === "curve_family") {
    const value = numericFlagField(flag, "value", "metric") ?? 0.214;
    const threshold = numericFlagField(flag, "threshold") ?? 0.150;
    return {
      kind: "curve_family",
      tab: "Curve shape",
      title: "Curve-shape evidence",
      plot: {
        plot_kind: "curve_family",
        points: [],
        reference_points: [],
      },
      points: [],
      reference: [],
      cohort: [],
      cards: [
        { key: "curve_family.classification", label: "Scientific call", value: value > threshold ? "Distance outlier" : "Within family", sub: "curve-shape assessment", level: value > threshold ? "warn" : "info" },
        { key: "curve_family.metric", label: "Primary metric", value: `${titleLabel(flag?.metric || "shape distance")} ${formatSignificantNumber(value)}`, sub: `review limit ${formatSignificantNumber(threshold)}`, level: value > threshold ? "warn" : "info" },
        { key: "curve_family.source", label: "Comparison", value: "run vs cohort", sub: "stress-strain family", level: "info" },
        { key: "selection.consequence_summary", label: "Recommended action", value: consequence, sub: "final report consequence", level: "info" },
      ],
    };
  }
  const category = titleLabel(flag?.category || flag?.source || "run validity");
  return {
    kind: "decision_context",
    tab: category,
    title: category,
    summary: message,
    evidence: flagEvidenceText(flag),
    cards: [
      { key: "run.validity", label: "Validity call", value: titleLabel(flag?.value || flag?.severity || "review"), sub: category, level: acceptanceFlagRank(flag) >= 2 ? "warn" : "info" },
      { key: "selection.consequence_summary", label: "Recommended action", value: consequence, sub: "final report consequence", level: "info" },
      { key: "review.scope", label: "Review scope", value: relatedFlags.length > 1 ? `${relatedFlags.length} linked findings` : "single finding", sub: "same run decision", level: "info" },
    ],
  };
}

function decisionNarrativeFromFlags(flags, defaultCall) {
  const primary = flags[0] || {};
  const message = escapeHtml(primary.message || primary.reason || "Review this run before confirming the final report selection.");
  const action = defaultCall === "Remove"
    ? "Default is remove. Keep only if the scientific evidence supports inclusion and record the justification."
    : "Default is keep. Remove only if the evidence shows the run should not contribute to the final report.";
  return `${message}<br><span>${escapeHtml(action)}</span>`;
}

function reviewRowsFromAcceptanceReport(report, options = {}) {
  const flagCockpits = options.flagCockpits !== false;
  const flags = Array.isArray(report?.flags) ? report.flags.filter((flag) => flag && typeof flag === "object") : [];
  if (!flags.length) return [];
  const runStates = report?.run_states && typeof report.run_states === "object" ? report.run_states : {};
  const grouped = new Map();
  flags.forEach((flag) => {
    const runId = String(flag.run_id || "").trim();
    if (!runId) return;
    if (!grouped.has(runId)) grouped.set(runId, []);
    grouped.get(runId).push(flag);
  });
  return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([runId, runFlags]) => {
    const sortedFlags = [...runFlags].sort((a, b) => acceptanceFlagRank(b) - acceptanceFlagRank(a));
    const primary = sortedFlags[0] || {};
    const state = String(runStates[runId] || "").toLowerCase();
    const rank = acceptanceFlagRank(primary);
    const removedByEffect = sortedFlags.some(selectionEffectRemoves);
    if (!["review_required", "excluded"].includes(state) && rank < 2 && !removedByEffect) return null;
    const defaultCall = ["review_required", "excluded"].includes(state) || removedByEffect ? "Remove" : "Keep";
    const message = String(primary.message || primary.reason || "Acceptance flag requires review");
    const evidenceRefs = Array.isArray(primary.evidence_refs) ? primary.evidence_refs.map(String).filter(Boolean) : [];
    const flagsPayload = sortedFlags.map(normalizedFlagPayload);
    return {
      rowKey: `acceptance:${runId}`,
      run: runId,
      defaultCall,
      excluded: state === "excluded",
      defects: defectLabelsForFlags(sortedFlags),
      reason: sortedFlags.length === 1 ? message : `${message} (+${sortedFlags.length - 1} more)`,
      flags: flagsPayload,
      narrative: decisionNarrativeFromFlags(flagsPayload, defaultCall),
      cockpits: flagCockpits ? cockpitsFromAcceptanceFlags(flagsPayload, defaultCall) : [],
    };
  }).filter(Boolean);
}

function acceptanceReportFromSession(session) {
  return session?.run?.result?.acceptance_report || session?.run?.acceptance_report || session?.acceptance_report || null;
}

function backendReviewRowCount(run) {
  const rows = run?.result?.review_rows || run?.review_rows || run?.result?.reviewRows || run?.reviewRows;
  return Array.isArray(rows) ? rows.length : 0;
}

function needsBackendReviewRowsRefresh(session) {
  const run = session?.run || {};
  if (!session?.session_id || run.status !== "completed") return false;
  if (backendReviewRowCount(run) > 0) return false;
  const report = acceptanceReportFromSession(session);
  return Array.isArray(report?.flags) && report.flags.length > 0;
}

function acceptanceCounts(report) {
  const summary = report?.summary && typeof report.summary === "object" ? report.summary : {};
  return summary;
}

function reviewRowIdentity(row) {
  return row?.rowKey || row?.run || "";
}

function isDemoModeFromLocation() {
  try {
    return new URLSearchParams(window.location.search || "").has("demo");
  } catch (_) {
    return false;
  }
}

function arrayOfText(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? "").trim()).filter(Boolean);
}

function resultPayloadFromSession(session) {
  return session?.run?.result || session?.result || {};
}

function acceptanceDecisionsFromSession(session) {
  const result = resultPayloadFromSession(session);
  return session?.acceptance_decisions
    || session?.run?.acceptance_decisions
    || result?.acceptance_decisions
    || null;
}

function selectionSetsFromReport(report) {
  const raw = report?.selection_sets?.selection_sets || report?.selection_sets;
  return Array.isArray(raw) ? raw : [];
}

function selectionSetRunIds(report, selectionId) {
  const wanted = String(selectionId || "").trim();
  if (!wanted) return [];
  const found = selectionSetsFromReport(report).find((set) => String(set?.selection_id || set?.id || "").trim() === wanted);
  return arrayOfText(found?.run_ids || found?.runs);
}

function allRunIdsFromReport(report) {
  const fromAllSet = selectionSetRunIds(report, "all_runs");
  if (fromAllSet.length) return fromAllSet;
  const runStates = report?.run_states && typeof report.run_states === "object" ? Object.keys(report.run_states) : [];
  if (runStates.length) return runStates;
  return arrayOfText((Array.isArray(report?.flags) ? report.flags : []).map((flag) => flag?.run_id));
}

function defaultSelectedRunIdsFromReport(report) {
  const summary = report?.summary && typeof report.summary === "object" ? report.summary : {};
  const defaultSelectionId = report?.default_selection_set || summary.default_selection_set || "default_report";
  const fromDefaultSet = selectionSetRunIds(report, defaultSelectionId);
  if (fromDefaultSet.length) return fromDefaultSet;
  const runStates = report?.run_states && typeof report.run_states === "object" ? report.run_states : {};
  return Object.entries(runStates)
    .filter(([, state]) => !["excluded", "review_required", "removed", "invalid"].includes(String(state || "").toLowerCase()))
    .map(([runId]) => runId);
}

function finalSelectedRunIdsFromSession(session, report) {
  const decisions = acceptanceDecisionsFromSession(session);
  const fromDecisions = arrayOfText(decisions?.final_selected_run_ids);
  if (fromDecisions.length) return fromDecisions;
  const result = resultPayloadFromSession(session);
  const finalRows = Array.isArray(result?.final_report_runs) ? result.final_report_runs : [];
  const fromFinalRows = finalRows
    .filter((row) => row?.included !== false && row?.final_included !== false)
    .map((row) => row?.run_id || row?.run || row?.id);
  if (fromFinalRows.length) return arrayOfText(fromFinalRows);
  return defaultSelectedRunIdsFromReport(report);
}

function runDecisionRecordsByRun(session) {
  const decisions = acceptanceDecisionsFromSession(session);
  const records = Array.isArray(decisions?.records) ? decisions.records : [];
  const byRun = new Map();
  records.forEach((record) => {
    const runId = String(record?.run_id || record?.run || "").trim();
    if (runId) byRun.set(runId, record);
  });
  return byRun;
}

function specimenResultsByRun(session) {
  const result = resultPayloadFromSession(session);
  const rows = Array.isArray(result?.specimen_results) ? result.specimen_results : [];
  const byRun = new Map();
  rows.forEach((row, index) => {
    const runId = String(row?.run_id || row?.run || `run_${String(index + 1).padStart(3, "0")}`).trim();
    if (runId) byRun.set(runId, row);
  });
  return byRun;
}

function reviewRowsByRun(rows) {
  const byRun = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const runId = String(row?.run || row?.run_id || "").trim();
    if (runId) byRun.set(runId, row);
  });
  return byRun;
}

function runIdsFromSession(session, report, reviewRows, selectedRunIds) {
  const ids = [];
  const add = (items) => arrayOfText(items).forEach((runId) => { if (!ids.includes(runId)) ids.push(runId); });
  const decisions = acceptanceDecisionsFromSession(session);
  add(allRunIdsFromReport(report));
  add(decisions?.default_selected_run_ids);
  add(decisions?.final_selected_run_ids);
  add(selectedRunIds);
  add((Array.isArray(reviewRows) ? reviewRows : []).map((row) => row.run));
  add(Array.from(specimenResultsByRun(session).keys()));
  return ids.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
}

function runDecisionReason(runId, included, reviewRow, record, specimenRow) {
  const explicitReason = String(record?.reason || record?.override_reason || record?.review_note || "").trim();
  const rowReason = String(reviewRow?.reason || "").trim();
  const defects = Array.isArray(reviewRow?.defects) ? reviewRow.defects.join(" + ") : "";
  if (reviewRow?.excluded) return `excluded before final report${rowReason ? ` - ${rowReason}` : ""}`;
  if (record) {
    const defaultKeep = record?.default_keep ?? record?.default_included ?? record?.default_selected;
    if (included && defaultKeep === false) return `kept with justification${explicitReason ? ` - ${explicitReason}` : rowReason ? ` - ${rowReason}` : ""}`;
    if (!included && defaultKeep === true) return `removed by review${explicitReason ? ` - ${explicitReason}` : rowReason ? ` - ${rowReason}` : ""}`;
    if (!included) return `removed by method rule${rowReason ? ` - ${rowReason}` : ""}`;
    return `included after review${explicitReason ? ` - ${explicitReason}` : ""}`;
  }
  if (reviewRow) {
    const decision = String(reviewRow.defaultCall || "").toLowerCase();
    if (!included) return `removed${rowReason ? ` - ${rowReason}` : defects ? ` - ${defects}` : ""}`;
    if (decision === "remove") return `kept with justification${rowReason ? ` - ${rowReason}` : defects ? ` - ${defects}` : ""}`;
    return `kept${rowReason ? ` - ${rowReason}` : ""}`;
  }
  const strength = specimenRow?.compressive_strength_MPa ?? specimenRow?.strength_MPa ?? specimenRow?.compressive_strength;
  if (included && Number.isFinite(Number(strength))) return `complete - compressive strength ${formatSignificantNumber(strength)} MPa`;
  return included ? "included in final report" : "excluded from final report";
}

function buildOutputRunManifest({ session, report, reviewRows, demoRows = [] }) {
  const hasAnalysedDataset = Boolean(session?.session_id || session?.run?.run_id || report || resultPayloadFromSession(session)?.specimen_results);
  if (!hasAnalysedDataset && !demoRows.length) return [];
  const selected = new Set(finalSelectedRunIdsFromSession(session, report));
  const recordsByRun = runDecisionRecordsByRun(session);
  const rowsByRun = reviewRowsByRun(reviewRows);
  const specimenByRun = specimenResultsByRun(session);
  const runIds = runIdsFromSession(session, report, reviewRows, selected);
  const sourceIds = runIds.length ? runIds : arrayOfText(demoRows.map((row) => row.run));
  return sourceIds.map((runId) => {
    const record = recordsByRun.get(runId);
    const reviewRow = rowsByRun.get(runId);
    const specimenRow = specimenByRun.get(runId);
    const recordKeep = record?.keep ?? record?.included ?? record?.selected;
    const included = typeof recordKeep === "boolean" ? recordKeep : selected.has(runId);
    return {
      run: runId,
      included,
      reason: formatNumericText(runDecisionReason(runId, included, reviewRow, record, specimenRow)),
    };
  });
}

function Review({ rows, totalRuns, decisions, setDecisions, reasons, setReasons, expanded, setExpanded, onRestore, onDecisionPersist }) {
  const flagged = Array.isArray(rows) ? rows : [];
  const active = flagged.filter((f) => !f.excluded);
  const resolvedTotalRuns = Number.isFinite(Number(totalRuns)) ? Number(totalRuns) : 0;

  const summary = useMemo(() => {
    const overrides = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) !== f.defaultCall).length;
    const missing = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) === "Keep" && f.defaultCall === "Remove" && !(reasons[reviewRowIdentity(f)] || "").trim()).length;
    const removed = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) === "Remove").length + flagged.filter((f) => f.excluded).length;
    return { overrides, missing, finalRuns: Math.max(0, resolvedTotalRuns - removed) };
  }, [active, decisions, flagged, reasons, resolvedTotalRuns]);

  const tiles = [
    { k: "TOTAL RUNS", v: resolvedTotalRuns, sub: "in package" },
    { k: "FLAGGED", v: active.length, sub: "need review", tone: "warn" },
    { k: "FINAL REPORT", v: summary.finalRuns, sub: "selected runs" },
    { k: "OVERRIDES", v: summary.overrides, sub: summary.missing ? `${summary.missing} missing reason${summary.missing > 1 ? "s" : ""}` : summary.overrides ? "justified overrides" : "none", tone: summary.missing ? "warn" : summary.overrides ? "ok" : "idle" },
  ];

  return (
    <div className="spotlight fade-in">
      <div className="page-head">
        <h1>One decision before output</h1>
        <div className="sub">{active.length
          ? <>Execution and validation passed · <b>{active.length} runs flagged</b> for a decision.</>
          : <>Execution and validation passed · <b>no runs flagged</b> for a decision.</>}</div>
      </div>

      <div className="review-summary">
        {tiles.map((t) => (
          <div key={t.k} className="rev-tile" data-tone={t.tone || ""}>
            <div className="rev-k">{t.k}</div>
            <div className="rev-v">{t.v}</div>
            <div className="rev-sub">{t.sub}</div>
          </div>
        ))}
      </div>

      <div className="task">
        <div className="task-head bare">
          <span className="task-flag">needs you</span>
          <span className="task-title">Confirm flagged runs</span>
          <span className="spacer" />
          <span className="muted-3" style={{ fontSize: "var(--t-xs)" }}>Click a row to inspect diagnostic evidence</span>
        </div>
        <div className="acc-list">
          <div className="acc-head"><span>Run</span><span>Default</span><span>Defects</span><span>Reason</span><span style={{ textAlign: "right" }}>Decision</span></div>
          {flagged.map((f) => {
            const key = reviewRowIdentity(f);
            return (
              <FlaggedRow key={key} f={f}
                open={expanded === key}
                decision={decisions[key] ?? f.defaultCall}
                reason={reasons[key] || ""}
                onToggle={() => setExpanded((current) => current === key ? null : key)}
                onDecide={(d) => {
                  setDecisions((s) => ({ ...s, [key]: d }));
                  onDecisionPersist?.(f, d, reasons[key] || "");
                }}
                onReason={(r) => setReasons((s) => ({ ...s, [key]: r }))}
                onRestore={() => onRestore(f.run)} />
            );
          })}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Review });

// ===== finalize.jsx =====
/* ============================================================
   Finalize spotlight — artifact handoff + versioned finalization
   Progressive disclosure: artifacts + finalize panel are primary;
   run-inclusion manifest (Enricher F6) and pre-finalize checks
   (Enricher F7) collapse to a one-line summary so the surface
   reads calmly instead of all-at-once. Versioned amendment ritual
   recovered from the Method-Editor versioning contract.
   ============================================================ */

function Collapse({ title, summary, tone, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={"collapse" + (open ? " open" : "")}>
      <button className="collapse-head" onClick={() => setOpen((v) => !v)}>
        <span className="label-caps">{title}</span>
        <span className={"collapse-sum" + (tone ? " " + tone : "")}>{summary}</span>
        <Icon name="chevron" className="collapse-chev" style={{ width: 15, height: 15 }} />
      </button>
      {open && <div className="collapse-body fade-in">{children}</div>}
    </div>
  );
}

function Finalize({ onFinalized, finalized, note, setNote, reviewer, setReviewer, reasonKind, setReasonKind, onOpenArtifact, onCopyPath, onReviewFields, onJumpRun, fieldsResolved, reviewSummary, outputPath, runManifest = [] }) {
  const o = WIZ.OUTPUT;
  const displayPath = outputPath || "";
  const hasOutput = !!displayPath;
  const requiredMissing = Math.max(0, o.requiredMissing - (fieldsResolved.required || 0));
  const recommendedMissing = Math.max(0, o.recommendedMissing - (fieldsResolved.recommended || 0));
  const totalMissing = requiredMissing + recommendedMissing;
  const canFinalize = requiredMissing === 0 && note.trim().length > 0 && !finalized;

  const manifest = Array.isArray(runManifest) ? runManifest : [];
  const included = manifest.filter((m) => m.included).length;
  const excluded = manifest.length - included;
  const checks = WIZ.FINAL_CHECKS;
  const liveIssues = checks.issues.filter((i) => !(i.jump === "report" && i.level === "error" && requiredMissing === 0) && !(i.jump === "report" && i.level === "report" && recommendedMissing === 0));

  return (
    <div className="spotlight fade-in">
      <div className="page-head">
        <h1>{finalized ? "MTDA finalized" : "Output is ready"}</h1>
        <div className="sub">{!hasOutput && !finalized
          ? <>MTDA output will appear after an analysed dataset has produced artifacts.</>
          : finalized
          ? <>Review state locked · <b>{o.mtda}</b> issued as <b>{o.mtdaVersion}</b>.</>
          : <>Test Report has warnings · MTDA is in <b>draft</b>.</>}</div>
      </div>

      {/* primary: artifacts (handoff) + finalize panel (the goal) */}
      <div className="final-grid">
        <div className="card" style={{ overflow: "hidden" }}>
          <div style={{ padding: "11px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center" }}>
            <span className="label-caps">Open output artifacts</span>
            <span className="spacer" />
            <span className="muted-3" style={{ fontSize: "var(--t-xs)", fontFamily: "var(--mono)" }}>{hasOutput ? `${o.archiveMembers} archive members` : "analysis pending"}</span>
          </div>
          {hasOutput ? o.artifacts.filter((a) => a.id !== "folder" && a.id !== "open_mtda").map((a) => (
            <div key={a.id} className="artifact" onClick={() => onOpenArtifact(a)}>
              <div className="a-ic"><Icon name={a.icon} /></div>
              <div className="a-main">
                <div className="a-title">{a.title}</div>
                <div className="a-role">{a.role}</div>
              </div>
              <Chip tone={a.status === "warn" ? "warn" : "ok"} dot={false}>{a.statusLabel}</Chip>
              <Icon name="arrowR" className="a-go" />
            </div>
          )) : <div className="empty-state">Generated reports and archive browser links will appear after method execution.</div>}
          <div style={{ padding: "11px 16px", borderTop: "1px solid var(--border)" }}>
            <div className="label-caps" style={{ marginBottom: 6 }}>MTDA output</div>
            <div className="path-field">
              <Icon name="folder" style={{ width: 14, height: 14, flex: "none", opacity: .6 }} />
              <span>{displayPath || "No MTDA output generated"}</span>
              <div className="path-actions">
                <button className="path-act" title="Open MTDA archive browser" disabled={!hasOutput} onClick={() => onOpenArtifact({ title: "Open MTDA" })}><Icon name="package" style={{ width: 14, height: 14 }} /></button>
                <button className="path-act" title="Open output folder" disabled={!hasOutput} onClick={() => onOpenArtifact({ title: "Output folder" })}><Icon name="folder" style={{ width: 14, height: 14 }} /></button>
                <button className="path-act" title="Copy MTDA path" disabled={!hasOutput} onClick={onCopyPath}><Icon name="copy" style={{ width: 14, height: 14 }} /></button>
              </div>
            </div>
          </div>
        </div>

        <div className="card final-panel">
          <div className="row" style={{ gap: 8 }}>
            <span className="label-caps">Finalize MTDA</span>
            <span className="spacer" />
            <span className={"draft-badge" + (finalized ? " final" : "")} style={{ fontSize: 11 }}>{finalized ? <><Icon name="check" style={{ width: 12, height: 12 }} />{o.mtdaVersion}</> : <><Icon name="warn" style={{ width: 12, height: 12 }} />Draft</>}</span>
          </div>

          {!finalized && (
            <div className="finalize-readout">
              <button className="fr-item" onClick={onReviewFields}>
                <span className="fr-v" data-tone={totalMissing > 0 ? "warn" : "ok"}>{totalMissing}</span>
                <span className="fr-k">report gap{totalMissing === 1 ? "" : "s"}<br /><span className="muted-3">{requiredMissing} required</span></span>
              </button>
              <button className="fr-item" disabled={!manifest.length} onClick={() => onJumpRun && onJumpRun(manifest.find((m) => !m.included)?.run)}>
                <span className="fr-v">{manifest.length ? `${included}/${manifest.length}` : "—"}</span>
                <span className="fr-k">runs in report<br /><span className="muted-3">{manifest.length ? `${excluded} excluded` : "analysis pending"}</span></span>
              </button>
              <div className="fr-item static">
                <span className="fr-v" data-tone={liveIssues.length ? "warn" : "ok"}>{liveIssues.length ? liveIssues.length : <Icon name="check" style={{ width: 18, height: 18 }} />}</span>
                <span className="fr-k">{liveIssues.length ? "open checks" : "checks pass"}<br /><span className="muted-3">{checks.passed.length} passed</span></span>
              </div>
            </div>
          )}

          {requiredMissing > 0 && !finalized && (
            <div className="banner" data-tone="warn" style={{ cursor: "pointer" }} onClick={onReviewFields}>
              <Icon name="warn" className="b-ic" />
              <div className="b-txt"><b>{requiredMissing} required field{requiredMissing > 1 ? "s" : ""} must be resolved</b> before finalize.</div>
              <Icon name="arrowR" className="b-ic" style={{ alignSelf: "center" }} />
            </div>
          )}

          <div className="tw-group">
            <label className="label-caps">Reviewer</label>
            <input className="field-input" placeholder="Reviewer / operator" value={reviewer} onChange={(e) => setReviewer(e.target.value)} disabled={finalized} />
          </div>
          <div className="tw-group">
            <label className="label-caps">Amendment reason {!finalized && <span style={{ color: "var(--err-ink)" }}>*</span>}</label>
            <select className="field-input" value={reasonKind} onChange={(e) => setReasonKind(e.target.value)} disabled={finalized}>
              {WIZ.FINAL_REASON_KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </div>
          <div className="tw-group">
            <label className="label-caps">Finalization note {!finalized && <span style={{ color: "var(--err-ink)" }}>*</span>}</label>
            <textarea className="field-input" placeholder="Required note — summarize review decisions and any overrides" value={note} onChange={(e) => setNote(e.target.value)} disabled={finalized} />
          </div>

          <Btn variant="primary" className="lg" icon={requiredMissing > 0 ? "warn" : "check"} disabled={!canFinalize} onClick={onFinalized}>
            {finalized ? `Finalized · ${o.mtdaVersion}` : requiredMissing > 0 ? "Resolve required fields first" : `Finalize & issue ${o.mtdaVersion}`}
          </Btn>
          <div className="muted" style={{ fontSize: "var(--t-xs)", lineHeight: 1.5 }}>
            {finalized ? "MTDA is locked. Re-open the wizard to record a further amendment version." : <>Source package is never modified — the amendment is recorded against <b>{o.mtdaVersion}</b>.</>}
          </div>
        </div>
      </div>

      {/* secondary detail: collapsed by default so the surface stays calm */}
      <Collapse title="Run manifest" tone={excluded ? "warn" : "ok"}
        summary={manifest.length ? <><b>{included} of {manifest.length}</b> runs included · {excluded} excluded</> : <>No analysed run manifest available</>}>
        {manifest.length ? manifest.map((m) => (
          <div key={m.run} className={"manifest-row" + (m.included ? "" : " out")} onClick={() => !m.included && onJumpRun && onJumpRun(m.run)}>
            <span className="mf-check">{m.included ? <Icon name="check" style={{ width: 14, height: 14 }} /> : <Icon name="x" style={{ width: 13, height: 13 }} />}</span>
            <span className="mf-run mono">{m.run}</span>
            <span className="mf-reason">{m.reason}</span>
            {!m.included && <span className="mf-jump">review →</span>}
          </div>
        )) : <div className="empty-state">Run inclusion will appear after an analysed dataset has produced acceptance decisions.</div>}
      </Collapse>

      <Collapse title="Pre-finalize checks" tone={liveIssues.length ? "warn" : "ok"}
        summary={<><b>{checks.passed.length} passed</b> · {checks.outOfScope.length} out of scope{liveIssues.length > 0 && <> · {liveIssues.length} open</>}</>}>
        <div className="checks-list">
          {checks.passed.map((c) => <div key={c} className="check-line ok"><Icon name="check" style={{ width: 13, height: 13 }} />{c}</div>)}
          {liveIssues.map((i) => (
            <div key={i.label} className={"check-line " + (i.level === "error" ? "err" : "rep")} onClick={() => onReviewFields()} style={{ cursor: "pointer" }}>
              <Icon name={i.level === "error" ? "warn" : "info"} style={{ width: 13, height: 13 }} />{i.label}<span className="check-fix">fix →</span>
            </div>
          ))}
          {checks.outOfScope.map((c) => <div key={c} className="check-line oos"><span className="oos-dot">·</span>{c} <span className="oos-tag">out of scope</span></div>)}
        </div>
      </Collapse>
    </div>
  );
}

Object.assign(window, { Finalize });

// ===== shell.jsx =====
/* ============================================================
   Shell — menu bar, process spine, context + status bars,
   activity log drawer, design rationale, tweaks, report dialog
   ============================================================ */

const MENUS = {
  File: [
    ["New method run", "Ctrl+N"],
    ["Open package…", "Ctrl+O"],
    ["sep"],
    ["Close wizard", "Ctrl+W"],
  ],
  Workflow: [["Choose package…", ""], ["Choose method…", ""], ["Edit mapping…", ""], ["sep"], ["Check readiness", ""], ["Run method", "Ctrl+R"]],
  Output: [["Open Test Report", ""], ["Open Audit Report", ""], ["sep"], ["Open output folder", ""], ["Copy MTDA path", ""]],
  View: [["Back a step", ""], ["Next step", ""], ["sep"], ["Toggle activity log", "L"], ["Toggle context detail", ""], ["Tweaks…", ""]],
  Help: [["Shortcuts", ""], ["About Method Analysis", ""]],
};

function MenuBar({ onAction, openMenu, setOpenMenu }) {
  const hasDesktopApi = Boolean(window.desktopApi);
  const pointerToggledRef = useRef(false);
  const isMenubarInteractive = (event) => {
    const selectors = 'button,.menu-item,.menu-pop,[data-window-control],[role="button"]';
    const path = event?.nativeEvent?.composedPath?.() || [];
    if (event?.target?.closest && event.target.closest(selectors)) return true;
    return path.some((node) => node && node.nodeType === 1 && node.matches && node.matches(selectors));
  };

  const toggleWindowMaximize = (event) => {
    if (!hasDesktopApi) return;
    if (isMenubarInteractive(event)) return;
    event.preventDefault();
    const result = window.desktopApi?.toggleMaximizeWindow?.();
    Promise.resolve(result)
      .then((state) => {
        if (state && typeof state === "object") {
          window.__compressionSyncWindowState?.(state);
        }
      })
      .catch(() => {});
  };

  return (
    <div className="menubar" data-window-drag="true" onDoubleClick={toggleWindowMaximize}>
      <span className="menubar-title" data-window-drag="true">Method Analysis</span>
      <nav className="menubar-menus">
        {Object.keys(MENUS).map((m) => (
          <div key={m} className={"menu-item" + (openMenu === m ? " open" : "")}
            role="button"
            tabIndex={0}
            onMouseDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
              pointerToggledRef.current = true;
              setOpenMenu((current) => current === m ? null : m);
            }}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              if (pointerToggledRef.current) {
                pointerToggledRef.current = false;
                return;
              }
              setOpenMenu((current) => current === m ? null : m);
            }}
            onMouseEnter={() => openMenu && setOpenMenu(m)}>
            {m}
            {openMenu === m && (
              <div className="menu-pop" onMouseDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
                {MENUS[m].map((row, i) => {
                  const reason = row[2] || "";
                  return row[0] === "sep"
                  ? <div key={i} className="sep" />
                  : <button key={i} disabled={!!reason} title={reason || undefined} onClick={() => { setOpenMenu(null); onAction(row[0]); }}>{row[0]}{(row[1] || reason) && <span className="k">{reason ? "Deferred" : row[1]}</span>}</button>;
                })}
              </div>
            )}
          </div>
        ))}
      </nav>
      <span className="menubar-spacer" aria-hidden="true" />
      <DesktopWindowControls className="menubar-windowctrls" />
    </div>
  );
}

const PIPELINE = ["Package", "Method", "Mapping", "Ready", "Run", "Validate", "Accept", "Output"];

// Clean connected stepper: continuous rail, completed portion filled,
// active step emphasised. Replaces the cluttered lead + long-connector bar.
function Spine({ states, onJump, phase }) {
  const reached = (st) => st === "done" || st === "active" || st === "warn" || st === "error";
  return (
    <div className="spine">
      <div className="spine-track">
        {PIPELINE.map((s, i) => {
          const st = states[s] || "todo";
          const nextReached = i < PIPELINE.length - 1 && reached(states[PIPELINE[i + 1]]);
          return (
            <button key={s} className="step" data-state={st} onClick={() => onJump && onJump(s)} title={`Go to ${s}`}>
              {i > 0 && <span className="rail rail-l" data-on={reached(st)} />}
              {i < PIPELINE.length - 1 && <span className="rail rail-r" data-on={nextReached} />}
              <span className="node">{st === "done" ? "✓" : st === "warn" ? "!" : st === "error" ? "×" : i + 1}</span>
              <span className="lbl">{s}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ContextBar({ pkg, method, mapping, output, open, onToggle, onAction }) {
  return (
    <>
      <div className={"contextbar" + (open ? " open" : "")} onClick={onToggle}>
        <span className="cx"><b>ISO 14126</b></span><span className="dot">·</span>
        <span className="cx">{pkg ? pkg.name : "no package"}</span><span className="dot">·</span>
        <span className="cx">{method ? "method " + method.standard : "method not selected"}</span><span className="dot">·</span>
        <span className="cx cx-warn">{mapping ? "mapping iso14126_manual.json (7 report gaps)" : "mapping not selected"}</span>
        <Icon name="chevron" className="chev" style={{ width: 14, height: 14 }} />
      </div>
      {open && (
        <div className="context-detail fade-in">
          <span className="cd-k">Package</span><span className="cd-v">{pkg ? pkg.name : "—"}</span>
          <span className="cd-k">Method</span><span className="cd-v">{method ? method.title : "—"}</span>
          <span className="cd-k">Mapping</span><span className="cd-v">iso14126_manual.json</span>
          <span className="cd-k">Output</span><span className="cd-v mono">{output}</span>
          <div className="cd-actions">
            <Btn size="sm" onClick={() => onAction("Choose package…")}>Change package…</Btn>
            <Btn size="sm" onClick={() => onAction("Choose method…")}>Change method…</Btn>
            <Btn size="sm" icon="edit" onClick={() => onAction("Edit mapping…")}>Edit mapping…</Btn>
          </div>
        </div>
      )}
    </>
  );
}

function StatusBar({ tone, state, logCount, onLog }) {
  return (
    <div className="statusbar" data-tone={tone}>
      <span className="sb-dot" />
      <span>{state}</span>
      <span className="sb-spacer" />
      <span className="sb-note">draft · raw files untouched</span>
      <span className="sb-link" onClick={onLog}>Activity log · {logCount}</span>
      <span className="sb-ver">mtdp {WIZ.APP_VERSION}</span>
    </div>
  );
}

function LogDrawer({ entries, onClose }) {
  const [filter, setFilter] = useState("all");
  const bodyRef = useRef(null);
  useEffect(() => { if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight; }, [entries]);
  const shown = entries.filter((e) => filter === "all" || e.level === filter);
  return (
    <>
      <div className="drawer-scrim" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-head">
          <span className="dh-t">Activity log</span>
          <span className="dh-c">{entries.length} entries</span>
          <button className="dh-x" onClick={onClose}><Icon name="x" /></button>
        </div>
        <div className="drawer-filter">
          {["all", "info", "ok", "warn", "err"].map((f) => (
            <button key={f} className={filter === f ? "on" : ""} onClick={() => setFilter(f)}>{f === "ok" ? "success" : f === "err" ? "error" : f}</button>
          ))}
        </div>
        <div className="drawer-body" ref={bodyRef}>
          {shown.length === 0 && <div style={{ padding: "16px", color: "var(--log-ts)", fontSize: 12 }}>No entries at this level yet.</div>}
          {shown.map((e, i) => (
            <div key={i} className="log-entry" data-l={e.level}>
              <span className="l-ts">{e.ts}</span>
              <span className="l-msg"><span className="l-lvl">{e.level === "ok" ? "ok " : e.level}</span>  {e.msg}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function Tweaks({ density, setDensity, accent, setAccent, onClose }) {
  const accents = [["#0f6cbd", "Azure"], ["#2f6f5e", "Teal"], ["#5b53b8", "Indigo"], ["#9a5a2c", "Amber"]];
  return (
    <div className="tweaks" onMouseDown={(e) => e.stopPropagation()}>
      <div className="tw-h"><Icon name="edit" style={{ width: 15, height: 15 }} /><span className="t">Tweaks</span><button onClick={onClose}><Icon name="x" /></button></div>
      <div className="tw-group">
        <span className="label-caps">Density</span>
        <div className="tw-seg">
          {[["comfortable", "Comfort"], ["balanced", "Balanced"], ["dense", "Dense"]].map(([k, l]) => (
            <button key={k} className={density === k ? "on" : ""} onClick={() => setDensity(k)}>{l}</button>
          ))}
        </div>
      </div>
      <div className="tw-group">
        <span className="label-caps">Accent</span>
        <div className="tw-swatches">
          {accents.map(([c, name]) => (
            <div key={c} className={"tw-sw" + (accent === c ? " on" : "")} style={{ background: c }} title={name} onClick={() => setAccent(c)} />
          ))}
        </div>
      </div>
    </div>
  );
}

function TypedField({ f, onChange }) {
  if (f.type === "enum") {
    return (
      <select className="field-input" value={f.value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose…</option>
        {f.choices.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
    );
  }
  if (f.type === "bool") {
    return (
      <div className="seg" style={{ width: "fit-content" }}>
        {["yes", "no"].map((o) => <button key={o} className={f.value === o ? "on" : ""} onClick={() => onChange(o)}>{o}</button>)}
      </div>
    );
  }
  if (f.type === "float") {
    return (
      <div className="float-row">
        <input className="field-input" type="number" min={f.min} step="any" placeholder={f.example} value={f.value} onChange={(e) => onChange(e.target.value)} />
        {f.units && f.units.length > 1
          ? <select className="field-input float-unit" defaultValue={f.unit}>{f.units.map((u) => <option key={u}>{u}</option>)}</select>
          : <span className="float-unit-static mono">{f.unit}</span>}
      </div>
    );
  }
  if (f.type === "date") {
    return <input className="field-input" type="date" value={f.value} onChange={(e) => onChange(e.target.value)} />;
  }
  return <input className="field-input" placeholder={f.example} value={f.value} onChange={(e) => onChange(e.target.value)} />;
}

function backendReportFieldKey(field) {
  return String(field || "").replace(/^report\./, "");
}

function reportAmendmentRows(fields, note, reviewer) {
  const reason = note.trim() || "Report completion amendment recorded from Finalize report dialog.";
  return fields
    .filter((f) => String(f.value || "").trim())
    .map((f) => ({
      field_key: backendReportFieldKey(f.field),
      value: f.value,
      reason,
      reviewer: reviewer || "",
      section: f.section || "",
      source_surface: "method_run_wizard.report_completion_editor",
    }));
}

function ReportCompletionDialog({ onClose, onResolveAll, onApplyAmendments, reviewer = "" }) {
  const [fields, setFields] = useState(() => WIZ.REPORT_FIELDS.map((f) => ({ ...f })));
  const [filter, setFilter] = useState("missing");
  const [selId, setSelId] = useState(fields[0].field);
  const [reviewNote, setReviewNote] = useState("");
  const [applying, setApplying] = useState(false);
  const sel = fields.find((f) => f.field === selId);
  const requiredMissing = fields.filter((f) => f.level === "required" && !f.value.trim()).length;
  const recommendedMissing = fields.filter((f) => f.level === "recommended" && !f.value.trim()).length;
  const resolvedCounts = {
    required: WIZ.OUTPUT.requiredMissing - requiredMissing,
    recommended: WIZ.OUTPUT.recommendedMissing - recommendedMissing,
  };
  const report_overrides = reportAmendmentRows(fields, reviewNote, reviewer);

  function setVal(v) { setFields((fs) => fs.map((f) => f.field === selId ? { ...f, value: v, source: v.trim() ? "report_override" : "missing" } : f)); }
  async function applyAmendments() {
    setApplying(true);
    try {
      if (onApplyAmendments) {
        const applied = await onApplyAmendments({
          fields,
          counts: resolvedCounts,
          note: reviewNote.trim(),
          report_overrides,
        });
        if (applied === false) return;
      } else {
        onResolveAll(resolvedCounts);
      }
      onClose();
    } finally {
      setApplying(false);
    }
  }

  const filters = [
    ["missing", "Missing", fields.filter((f) => !f.value.trim()).length],
    ["required", "Required", fields.filter((f) => f.level === "required").length],
    ["recommended", "Recommended", fields.filter((f) => f.level === "recommended").length],
    ["overridden", "Overridden", fields.filter((f) => f.value.trim()).length],
    ["all", "All", fields.length],
  ];
  const shown = fields.filter((f) => filter === "all" || (filter === "missing" && !f.value.trim()) || (filter === "overridden" && f.value.trim()) || (filter === f.level));

  return (
    <div className="scrim no-flicker-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" style={{ width: "min(940px, 94vw)", height: "min(640px, 90%)" }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="dialog-head"><Icon name="report" /><div className="col" style={{ gap: 1 }}><h2>Report completion</h2><span className="dh-sub">Report-only · source package untouched.</span></div></div>
        <div className="dialog-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="seg" style={{ alignSelf: "flex-start" }}>
            {filters.map(([k, l, n]) => <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{l} · {n}</button>)}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 14, flex: 1, minHeight: 0 }}>
            <div className="card" style={{ overflow: "auto" }}>
              <table className="tbl">
                <thead><tr><th>Field</th><th>Type</th><th>Requirement</th><th>Status</th></tr></thead>
                <tbody>
                  {shown.map((f) => (
                    <tr key={f.field} className="click" onClick={() => setSelId(f.field)} style={selId === f.field ? { background: "var(--accent-soft)" } : null}>
                      <td className="mono">{f.field} <ReqMark level={f.level} /></td>
                      <td><span className="type-chip mono">{f.type}</span></td>
                      <td><Chip tone={f.level === "required" ? "warn" : "idle"} dot={false}>{f.level}</Chip></td>
                      <td><Chip tone={f.value.trim() ? "ok" : f.level === "required" ? "err" : "warn"}>{f.value.trim() ? "resolved" : "missing"}</Chip></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div><div className="r-input mono" style={{ fontWeight: 700 }}>{sel.field}</div><div className="muted" style={{ fontSize: "var(--t-xs)", marginTop: 3 }}>{WIZ.IMPORTANCE_LABEL[sel.level]} · example “{sel.example}”</div></div>
              <div className="banner" data-tone="info" style={{ padding: "8px 11px" }}>
                <Icon name="info" className="b-ic" style={{ width: 15, height: 15 }} />
                <div className="b-txt" style={{ fontSize: "var(--t-xs)" }}>{WIZ.SOURCE_TYPE_LABEL[sel.source]}. {sel.level === "required" ? "Resolve this before final issue." : "Add a value or status. Unresolved recommended fields finalize with warnings."}</div>
              </div>
              <div className="tw-group">
                <div className="row" style={{ gap: 7 }}>
                  <span className="label-caps">Value</span>
                  <span className="type-chip mono">{WIZ.TYPE_HINT[sel.type] || "text"}{sel.type === "enum" ? ` · ${sel.choices.length}` : ""}{sel.type === "float" && sel.unit ? ` · ${sel.unit}` : ""}</span>
                </div>
                <TypedField f={sel} onChange={setVal} />
              </div>
              <div className="tw-group"><span className="label-caps">Reviewer note</span>
                <textarea className="field-input" placeholder="Optional provenance note" value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} />
              </div>
              <div className="banner" data-tone={requiredMissing ? "warn" : "ok"} style={{ marginTop: "auto" }}>
                <Icon name={requiredMissing ? "warn" : "check"} className="b-ic" />
                <div className="b-txt" style={{ fontSize: "var(--t-xs)" }}>{requiredMissing} required · {recommendedMissing} recommended still missing.</div>
              </div>
            </div>
          </div>
        </div>
        <div className="dialog-foot">
          <span className="muted" style={{ fontSize: "var(--t-xs)" }}>Amendments recorded in the report override ledger.</span>
          <span className="spacer" />
          <Btn onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" icon="check" onClick={applyAmendments} disabled={applying}>{applying ? "Applying" : "Apply amendments"}</Btn>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MenuBar, Spine, ContextBar, StatusBar, LogDrawer, Tweaks, ReportCompletionDialog, PIPELINE });

// ===== app.jsx =====
/* ============================================================
   App — state machine wiring all surfaces together
   Phases: setup → running → review → finalize
   (setup internally tracks package / method / decisions)
   ============================================================ */

function nowTs(offsetSec = 0) {
  const base = 14 * 3600 + 22 * 60 + 1 + offsetSec;
  const h = Math.floor(base / 3600) % 24, m = Math.floor((base % 3600) / 60), s = base % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const SCENARIO_ORDER = ["setup", "running", "review", "finalize"];

function initialPackagePathFromLocation() {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search || "");
  return params.get("initial_package_path") || params.get("package_path") || "";
}

function packageFromBackendPreview(preview) {
  if (!preview) return null;
  const schema = [preview.schema_id, preview.schema_version ? "v" + preview.schema_version : ""].filter(Boolean).join(" · ");
  const packagePath = preview.package_path || "";
  return {
    name: preview.package_name || "Selected package",
    family: preview.analysis_type || preview.schema_id || "analysis package",
    runs: Number(preview.run_count || 0),
    schema: schema || "Package schema",
    path: packagePath,
    channels: Array.isArray(preview.available_channels) ? preview.available_channels : [],
    mtime: "loaded",
    note: parentDirectoryFromPath(packagePath) || "Opened package",
    backendPreview: preview,
  };
}

function recentPackageFromBackendRow(row) {
  if (!row) return null;
  const path = row.path || row.package_path || "";
  if (!path) return null;
  return {
    name: row.name || fileNameFromPath(path),
    family: row.kind || row.extension || "analysis package",
    runs: row.run_count || row.runs || null,
    path,
    mtime: row.modified_label || row.modified_at || "",
    note: row.parent || parentDirectoryFromPath(path),
  };
}

function recentPackageFromSession(session) {
  const preview = session?.package || {};
  const path = session?.package_path || preview.package_path || "";
  if (!path) return null;
  return {
    name: preview.package_name || fileNameFromPath(path),
    family: preview.analysis_type || preview.schema_id || "analysis package",
    runs: preview.run_count || null,
    path,
    mtime: "just opened",
    note: parentDirectoryFromPath(path),
  };
}

function mergeRecentPackage(packages, nextPackage, limit = 12) {
  if (!nextPackage?.path) return packages;
  const path = String(nextPackage.path);
  return [
    nextPackage,
    ...packages.filter((item) => String(item.path || "") !== path),
  ].slice(0, limit);
}

function versionLabel(version) {
  const value = String(version || "").trim();
  if (!value) return "";
  return value.startsWith("v") ? value : "v" + value;
}

function methodOptionsFromSession(session) {
  const entries = Array.isArray(session?.eligible_methods) && session.eligible_methods.length
    ? session.eligible_methods
    : (Array.isArray(session?.methods) ? session.methods : []);
  return entries.map((entry) => methodFromBackend(entry, session));
}

function methodFromBackend(entry, session = null) {
  if (!entry) return null;
  const selected = session?.selected_method?.method_id === entry.method_id ? session.selected_method : null;
  const merged = { ...entry, ...(selected || {}) };
  const label = merged.method_name || merged.label || merged.method_id || "Backend method";
  const standard = merged.standard_reference || (String(label).match(/ISO\s+\d+/i)?.[0]) || merged.analysis_type || "registered method";
  const version = versionLabel(merged.version);
  const requiredInputs = Array.isArray(merged.required_inputs) ? merged.required_inputs.length : 0;
  const recipeSteps = Array.isArray(merged.recipe_steps) ? merged.recipe_steps.length : 0;
  const summaryParts = [
    merged.analysis_type,
    requiredInputs ? `${requiredInputs} required inputs` : "",
    recipeSteps ? `${recipeSteps} recipe steps` : "",
  ].filter(Boolean);
  const mappingSummary = session?.selected_method?.method_id === entry.method_id ? session?.mapping : null;
  return {
    id: merged.method_id,
    title: label,
    short: [label, version].filter(Boolean).join(" — "),
    version: version || merged.version || "",
    standard,
    summary: summaryParts.length ? summaryParts.join(" · ") : "Backend registered method from MethodRegistry.",
    registry: "Backend MethodRegistry",
    backendSummary: merged,
    mappingSummary,
  };
}

function bindingsFromBackendMapping(mapping) {
  const preview = mapping?.preview || mapping?.mappingPreview || null;
  const rows = Array.isArray(preview?.rows)
    ? preview.rows
    : (Array.isArray(mapping?.mapped_fields) ? mapping.mapped_fields : []);
  const candidates = Array.isArray(preview?.candidate_rows) ? preview.candidate_rows : [];
  return rows.map((row, index) => bindingFromBackendRow(row, index, candidates)).filter(Boolean);
}

function bindingFromBackendRow(row, index, candidates) {
  if (!row) return null;
  const methodField = row.method_field || row.requirement_id || row.source_role || `mapping.${index + 1}`;
  const severity = String(row.severity || row.required_or_recommended || "").toLowerCase();
  const req = severity === "execution_critical" || severity === "required" ? "required" : "recommended";
  const rawStatus = String(row.status || row.operator_status || "").toLowerCase();
  const mappedSource = row.mapped_source || row.source || "";
  const status = rawStatus === "pass" || rawStatus === "found"
    ? "matched"
    : rawStatus === "ambiguous" || rawStatus === "warning"
      ? "ambiguous"
      : mappedSource
        ? "manual"
        : "unmapped";
  const sourceRole = row.source_role || methodField;
  const rowCandidates = candidates
    .filter((candidate) => {
      const candidateField = candidate.method_field || candidate.requirement_id || "";
      const candidateRole = candidate.source_role || "";
      return candidateField === methodField || candidateRole === sourceRole;
    })
    .map((candidate) => ({
      source: candidate.source_name || candidate.candidate_source || candidate.mapped_source || "",
      kind: candidate.source_kind || row.source_kind || "field",
      scope: candidate.scope || row.scope || "",
      coverage: candidate.coverage || row.coverage || "—",
      confidence: Number(candidate.confidence || row.confidence || 0),
      example: candidate.example_value || row.example_value || "",
      reason: candidate.reason || candidate.message || row.resolution_status || "",
      via: candidate.reason || "",
    }))
    .filter((candidate) => candidate.source);
  if (mappedSource && !rowCandidates.some((candidate) => candidate.source === mappedSource)) {
    rowCandidates.unshift({
      source: mappedSource,
      kind: row.source_kind || "field",
      scope: row.scope || "",
      coverage: row.coverage || "—",
      confidence: Number(row.confidence || 1),
      example: row.example_value || "",
      reason: row.resolution_status || "backend mapping profile",
      via: row.resolution_status || "",
    });
  }
  return {
    id: row.requirement_id || methodField,
    input: methodField,
    desc: row.description || methodField,
    req,
    kind: row.source_kind || "field",
    status,
    binding: mappedSource,
    coverage: row.coverage || (mappedSource ? "mapping declared" : "—"),
    unit: row.expected_unit || row.unit || row.source_unit || "",
    via: row.resolution_status || row.source_location || "",
    note: row.message || "",
    candidates: rowCandidates,
    backendRow: row,
  };
}

function mappingPatchRows(bindings) {
  return (bindings || []).map((binding) => {
    const backendRow = binding.backendRow || {};
    return {
      requirement_id: backendRow.requirement_id || binding.id || "",
      method_field: backendRow.method_field || binding.input || "",
      source_role: backendRow.source_role || binding.input?.split(".").at(-1) || "",
      source_kind: binding.kind || backendRow.source_kind || "field",
      mapped_source: binding.binding || "",
      status: binding.status || "",
    };
  });
}

function mappingRowsFingerprint(bindings = []) {
  const rows = Array.isArray(bindings) ? bindings : [];
  return JSON.stringify(
    rows
      .map((row) => ({
        id: row?.id || "",
        input: row?.input || "",
        req: row?.req || "",
        status: row?.status || "",
        binding: row?.binding || "",
        kind: row?.kind || "",
        coverage: row?.coverage || "",
        unit: row?.unit || "",
        via: row?.via || "",
        note: row?.note || "",
        desc: row?.desc || "",
        candidates: Array.isArray(row?.candidates)
          ? row.candidates
            .map((candidate) => ({
              source: candidate?.source || "",
              kind: candidate?.kind || "",
              scope: candidate?.scope || "",
              coverage: candidate?.coverage || "",
              confidence: Number(candidate?.confidence || 0),
              example: candidate?.example || "",
              reason: candidate?.reason || "",
            }))
            .sort((a, b) => a.source.localeCompare(b.source))
          : [],
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  );
}

function fileNameFromPath(path) {
  return path ? String(path).split(/[\\/]/).pop() : "";
}

function parentDirectoryFromPath(path) {
  const text = String(path || "");
  const index = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"));
  return index > 0 ? text.slice(0, index) : "";
}

function mappingSaveDefaultName(mapping) {
  const currentName = mapping?.mapping_name || fileNameFromPath(mapping?.path) || "mapping_profile.json";
  if (/_wizard_edit\.(json|ya?ml)$/i.test(currentName)) return currentName;
  const stem = currentName.replace(/\.(json|ya?ml)$/i, "");
  return `${stem || "mapping_profile"}_wizard_edit.json`;
}

function analysisReadinessStatus(session) {
  return String(session?.readiness?.status || session?.readiness_status || "")
    .trim()
    .replace(/[-\s]+/g, "_")
    .toUpperCase();
}

function isAnalysisSessionHardBlocked(session) {
  const status = analysisReadinessStatus(session);
  return ["NOT_READY", "BLOCKED", "FAILED", "ERROR", "INVALID"].includes(status);
}

function isAnalysisSessionRunEnabled(session, fallbackReady = false) {
  const status = analysisReadinessStatus(session);
  if (session?.run_enabled === true) return true;
  if (status === "READY" || status === "READY_WITH_WARNINGS") return true;
  if (isAnalysisSessionHardBlocked(session)) return false;
  return Boolean(fallbackReady);
}

function reviewDecisionRow(flaggedRun, decision, reason = "") {
  const finalDecision = decision || flaggedRun.defaultCall || "Remove";
  const finalIncluded = finalDecision === "Keep";
  const defaultIncluded = (flaggedRun.defaultCall || "Remove") === "Keep";
  return {
    run_id: flaggedRun.run,
    decision: finalIncluded ? "keep" : "remove",
    final_included: finalIncluded,
    default_call: flaggedRun.defaultCall || (defaultIncluded ? "Keep" : "Remove"),
    default_included: defaultIncluded,
    reason: reason || "",
    defects: Array.isArray(flaggedRun.defects) ? flaggedRun.defects : [],
    source_surface: "method_run_wizard.review_spotlight",
    ui_context: "analysis.review",
  };
}

function reviewDecisionRows(decisions, reasons, flaggedRows = []) {
  return (Array.isArray(flaggedRows) ? flaggedRows : [])
    .filter((flaggedRun) => !flaggedRun.excluded)
    .map((flaggedRun) => reviewDecisionRow(
      flaggedRun,
      decisions[reviewRowIdentity(flaggedRun)] ?? flaggedRun.defaultCall,
      reasons[reviewRowIdentity(flaggedRun)] || "",
    ));
}

function App() {
  const dbg = ((typeof location !== "undefined" && location.hash) || "").replace("#", "");
  const startPhase = SCENARIO_ORDER.includes(dbg) ? dbg : (dbg === "editor" ? "setup" : "setup");
  const initialPackagePath = useMemo(() => initialPackagePathFromLocation(), []);
  const demoMode = useMemo(() => isDemoModeFromLocation(), []);

  const [phase, setPhase] = useState(startPhase);
  const [pkg, setPkg] = useState(() => (demoMode ? WIZ.PACKAGE : null));
  const [pkgSel, setPkgSel] = useState(() => (demoMode ? WIZ.PACKAGE.path : ""));
  const [method, setMethod] = useState(() => (demoMode ? WIZ.METHOD : null));
  const [mappingResolved, setMappingResolved] = useState(() => demoMode);
  const [metadataResolved, setMetadataResolved] = useState(false);
  const [bindings, setBindings] = useState(WIZ.BINDINGS);
  const [mappingDirty, setMappingDirty] = useState(false);

  // review
  const [decisions, setDecisions] = useState({});
  const [reasons, setReasons] = useState({});
  const [expanded, setExpanded] = useState("run_004");

  // finalize
  const [note, setNote] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reasonKind, setReasonKind] = useState(WIZ.FINAL_REASON_KINDS[0][0]);
  const [finalized, setFinalized] = useState(false);
  const [fieldsResolved, setFieldsResolved] = useState({ required: 0, recommended: 0 });

  // UI
  const [openMenu, setOpenMenu] = useState(null);
  const [showLog, setShowLog] = useState(false);
  const [showMapping, setShowMapping] = useState(dbg === "editor");
  const [showTweaks, setShowTweaks] = useState(false);
  const [showReportDialog, setShowReportDialog] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [density, setDensity] = useState("balanced");
  const [accent, setAccent] = useState("#0f6cbd");
  const [toast, setToast] = useState(null);
  const [analysisSession, setAnalysisSession] = useState(null);
  const [backendPackageError, setBackendPackageError] = useState(null);
  const [recentPackages, setRecentPackages] = useState([]);
  const [recentPackageLoading, setRecentPackageLoading] = useState(false);
  const [recentPackageError, setRecentPackageError] = useState(null);
  const [selectedMethodId, setSelectedMethodId] = useState(() => (demoMode ? WIZ.METHOD.id : ""));

  const [log, setLog] = useState([{ ts: nowTs(0), level: "info", msg: "Method Analysis opened" }]);
  const logSeq = useRef(1);
  const runPollRef = useRef(null);
  const eventCursorRef = useRef(0);
  const eventSubscriptionRef = useRef(null);
  const mappingFingerprintRef = useRef("");
  const loggedEventIdsRef = useRef(new Set());
  const reviewRowsRefreshRef = useRef(new Set());
  const pushLog = useCallback((e) => setLog((l) => [...l, { ts: nowTs(logSeq.current++ * 3), ...e }]), []);
  const backendMethodOptions = useMemo(() => methodOptionsFromSession(analysisSession), [analysisSession]);
  const backendMappingBindings = useMemo(() => bindingsFromBackendMapping(analysisSession?.mapping), [analysisSession?.mapping]);
  const backendMappingFingerprint = useMemo(() => mappingRowsFingerprint(backendMappingBindings), [backendMappingBindings]);

  useEffect(() => { document.documentElement.setAttribute("data-density", density); }, [density]);
  useEffect(() => () => {
    if (runPollRef.current) clearTimeout(runPollRef.current);
    if (eventSubscriptionRef.current) {
      try { eventSubscriptionRef.current(); } catch (err) { /* host may already be gone */ }
      eventSubscriptionRef.current = null;
    }
  }, []);
  useEffect(() => {
    const r = document.documentElement.style;
    r.setProperty("--accent", accent);
    const dark = (c, f) => { try {
      const n = parseInt(c.slice(1), 16); let R = (n >> 16) & 255, G = (n >> 8) & 255, B = n & 255;
      R = Math.round(R * f); G = Math.round(G * f); B = Math.round(B * f);
      return "#" + ((1 << 24) + (R << 16) + (G << 8) + B).toString(16).slice(1);
    } catch (e) { return c; } };
    r.setProperty("--accent-hover", dark(accent, 0.85));
    r.setProperty("--accent-press", dark(accent, 0.72));
    r.setProperty("--accent-ink", dark(accent, 0.78));
  }, [accent]);

  const anyOverlay = showMapping || showReportDialog || showTweaks || showGuide;

  // keyboard: L log, Esc close, ← → scenario step
  useEffect(() => {
    const h = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
      if (e.key === "l" || e.key === "L") setShowLog((v) => !v);
      else if ((e.ctrlKey || e.metaKey) && (e.key === "n" || e.key === "N")) { e.preventDefault(); startNewMethodRun(); }
      else if ((e.ctrlKey || e.metaKey) && (e.key === "o" || e.key === "O")) { e.preventDefault(); openPackageDialog(); }
      else if ((e.ctrlKey || e.metaKey) && (e.key === "w" || e.key === "W")) { e.preventDefault(); closeWizard(); }
      else if (e.key === "ArrowRight" && !anyOverlay) stepScenario(1);
      else if (e.key === "ArrowLeft" && !anyOverlay) stepScenario(-1);
      else if (e.key === "Escape") {
        if (showMapping) setShowMapping(false);
        else if (showReportDialog) setShowReportDialog(false);
        else if (showTweaks) setShowTweaks(false);
        else if (showGuide) setShowGuide(false);
        else if (showLog) setShowLog(false);
        else if (contextOpen) setContextOpen(false);
        else if (openMenu) setOpenMenu(null);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  });

  function flash(msg) { setToast(msg); setTimeout(() => setToast((t) => (t === msg ? null : t)), 2200); }

  function applyBackendMappings(nextBindings) {
    const normalized = Array.isArray(nextBindings) ? nextBindings : [];
    setBindings(normalized);
    mappingFingerprintRef.current = mappingRowsFingerprint(normalized);
    setMappingDirty(false);
  }

  function applyAnalysisPackageSession(session) {
    setAnalysisSession(session);
    const loaded = packageFromBackendPreview(session?.package);
    if (!loaded) return null;
    const options = methodOptionsFromSession(session);
    setPkg(loaded);
    setPkgSel(loaded.path || loaded.name);
    setRecentPackages((packages) => mergeRecentPackage(packages, recentPackageFromSession(session)));
    setMethod(null);
    setSelectedMethodId(options[0]?.id || "");
    setMappingResolved(false);
    setMetadataResolved(false);
    setBindings(WIZ.BINDINGS);
    mappingFingerprintRef.current = mappingRowsFingerprint(WIZ.BINDINGS);
    setMappingDirty(false);
    setBackendPackageError(null);
    return loaded;
  }

  useEffect(() => {
    const api = window.desktopApi?.analysis;
    if (!api?.listRecentPackages) {
      setRecentPackages([]);
      setRecentPackageLoading(false);
      setRecentPackageError(null);
      return undefined;
    }
    let alive = true;
    setRecentPackageLoading(true);
    api.listRecentPackages({ limit: 12 }).then((response) => {
      if (!alive) return;
      if (response?.status === "ok") {
        const rows = Array.isArray(response.data?.packages) ? response.data.packages : [];
        setRecentPackages(rows.map(recentPackageFromBackendRow).filter(Boolean));
        setRecentPackageError(null);
      } else {
        setRecentPackages([]);
        setRecentPackageError(response?.message || "Recent packages are unavailable.");
      }
    }).catch((err) => {
      if (!alive) return;
      setRecentPackages([]);
      setRecentPackageError(err?.message || "Recent packages are unavailable.");
    }).finally(() => {
      if (alive) setRecentPackageLoading(false);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!initialPackagePath) return undefined;
    let alive = true;
    const api = window.desktopApi?.analysis;
    if (!api?.createSession) {
      setBackendPackageError("Analysis backend bridge is unavailable.");
      pushLog({ level: "warn", msg: "Analysis package handoff could not reach backend bridge" });
      return undefined;
    }
    api.createSession({ initial_package_path: initialPackagePath }).then((response) => {
      if (!alive) return;
      if (response?.status !== "ok") {
        const msg = response?.message || "Could not load handed-off package.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        return;
      }
      const loaded = applyAnalysisPackageSession(response.data);
      if (loaded) {
        pushLog({ level: "ok", msg: `Package loaded from Packaging · ${loaded.name}` });
      }
    }).catch((err) => {
      if (!alive) return;
      const msg = err?.message || "Could not load handed-off package.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    });
    return () => { alive = false; };
  }, [initialPackagePath, pushLog]);

  useEffect(() => {
    if (backendMethodOptions.length && !backendMethodOptions.some((option) => option.id === selectedMethodId)) {
      setSelectedMethodId(backendMethodOptions[0].id);
    }
  }, [backendMethodOptions, selectedMethodId]);
  useEffect(() => {
    if (!backendMappingBindings.length) return;
    if (mappingDirty && showMapping) return;
    if (backendMappingFingerprint === mappingFingerprintRef.current) return;
    applyBackendMappings(backendMappingBindings);
  }, [backendMappingBindings, backendMappingFingerprint, mappingDirty, showMapping]);

  const readinessStatus = analysisReadinessStatus(analysisSession);
  const criticalInputsResolved = !!(pkg && method && mappingResolved);
  const backendReady = !!analysisSession?.session_id && isAnalysisSessionRunEnabled(analysisSession);
  const backendHardBlocked = isAnalysisSessionHardBlocked(analysisSession);
  const runEnabled = !!(pkg && method) && !backendHardBlocked && (backendReady || criticalInputsResolved);

  function resetMethodRunState(nextSession = null) {
    if (runPollRef.current) {
      clearTimeout(runPollRef.current);
      runPollRef.current = null;
    }
    void stopBackendEventSubscription();
    eventCursorRef.current = 0;
    loggedEventIdsRef.current = new Set();
    setPhase("setup");
    setPkg(null);
    setPkgSel("");
    setMethod(null);
    setMappingResolved(false);
    setMetadataResolved(false);
    setBindings(WIZ.BINDINGS);
    mappingFingerprintRef.current = mappingRowsFingerprint(WIZ.BINDINGS);
    setMappingDirty(false);
    setDecisions({});
    setReasons({});
    setExpanded("run_004");
    setNote("");
    setReviewer("");
    setReasonKind(WIZ.FINAL_REASON_KINDS[0][0]);
    setFinalized(false);
    setFieldsResolved({ required: 0, recommended: 0 });
    setOpenMenu(null);
    setShowLog(false);
    setShowMapping(false);
    setShowTweaks(false);
    setShowReportDialog(false);
    setContextOpen(false);
    setToast(null);
    setAnalysisSession(nextSession);
    setBackendPackageError(null);
    setSelectedMethodId(methodOptionsFromSession(nextSession)[0]?.id || "");
    logSeq.current = 1;
    setLog([{ ts: nowTs(0), level: "info", msg: "New method run opened" }]);
  }

  async function startNewMethodRun() {
    const api = window.desktopApi?.analysis;
    if (!api?.createSession) {
      const msg = "Analysis backend bridge is unavailable.";
      resetMethodRunState(null);
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
      return;
    }
    try {
      const response = await api.createSession({});
      if (response?.status === "ok") {
        resetMethodRunState(response.data);
        pushLog({ level: "ok", msg: `Backend analysis session opened · ${response.data?.session_id || "new session"}` });
        flash("New method run ready.");
        return;
      }
      const msg = response?.message || "Could not start a new method run.";
      resetMethodRunState(null);
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    } catch (err) {
      const msg = err?.message || "Could not start a new method run.";
      resetMethodRunState(null);
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    }
  }

  function closeWizard() {
    window.desktopApi?.closeWindow?.();
  }

  async function loadPackagePath(packageRef) {
    const packagePath = typeof packageRef === "string" ? packageRef : packageRef?.path;
    const displayName = (typeof packageRef === "object" && packageRef?.name) || fileNameFromPath(packagePath);
    if (!packagePath) {
      const msg = "No package path was selected.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
      return;
    }
    const api = window.desktopApi?.analysis;
    if (!api?.createSession) {
      const msg = "Analysis backend bridge is unavailable.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
      return;
    }
    try {
      const response = analysisSession?.session_id && api?.loadPackage
        ? await api.loadPackage({ session_id: analysisSession.session_id, path: packagePath })
        : await api.createSession({ initial_package_path: packagePath });
      if (response?.status === "ok") {
        const loaded = applyAnalysisPackageSession(response.data);
        if (loaded) {
          pushLog({ level: "ok", msg: `Package loaded from recent files · ${loaded.name}` });
          flash(`Package loaded — ${loaded.name}`);
          setPhase("setup");
          return;
        }
        const msg = "Recent package did not return a package preview.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        flash(msg);
        return;
      }
      const msg = response?.message || `Could not load package ${displayName || packagePath}.`;
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    } catch (err) {
      const msg = err?.message || `Could not load package ${displayName || packagePath}.`;
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    }
  }

  async function openPackageDialog() {
    const api = window.desktopApi?.analysis;
    if (!api?.openPackageDialog) {
      const msg = "Native analysis package dialog is unavailable.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
      return;
    }
    try {
      const payload = analysisSession?.session_id ? { session_id: analysisSession.session_id } : {};
      const response = await api.openPackageDialog(payload);
      if (response?.status === "ok") {
        const loaded = applyAnalysisPackageSession(response.data);
        if (loaded) {
          pushLog({ level: "ok", msg: `Package loaded from native dialog · ${loaded.name}` });
          flash(`Package loaded — ${loaded.name}`);
          setPhase("setup");
          return;
        }
        const msg = "Analysis package dialog did not return a package preview.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        flash(msg);
        return;
      }
      const msg = response?.message || "Could not open analysis package.";
      if (response?.error_type === "Cancelled") {
        pushLog({ level: "info", msg });
        flash("Open package cancelled.");
        return;
      }
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    } catch (err) {
      const msg = err?.message || "Could not open analysis package.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      flash(msg);
    }
  }

  // ---- scenario navigation (prototype affordance) ----
  function gotoScenario(s) {
    if (s === "setup") { setPhase("setup"); return; }
    if (!pkg || !method) {
      setPhase("setup");
      flash("Choose package and method first.");
      return;
    }
    setPhase(s);
  }
  function stepScenario(dir) {
    const cur = SCENARIO_ORDER.indexOf(phase);
    const next = Math.max(0, Math.min(SCENARIO_ORDER.length - 1, cur + dir));
    gotoScenario(SCENARIO_ORDER[next]);
  }

  // ---- setup transitions ----
  async function confirmMethod() {
    const fallbackMethod = backendMethodOptions.find((option) => option.id === selectedMethodId) || WIZ.METHOD;
    const api = window.desktopApi?.analysis;
    if (analysisSession?.session_id && api?.selectMethod && fallbackMethod?.id) {
      try {
        const response = await api.selectMethod({
          session_id: analysisSession.session_id,
          method_id: fallbackMethod.id,
        });
        if (response?.status === "ok") {
          const session = response.data;
          setAnalysisSession(session);
          const selected = methodFromBackend(session?.selected_method, session)
            || methodOptionsFromSession(session).find((option) => option.id === session?.selected_method_id)
            || fallbackMethod;
          setSelectedMethodId(selected.id);
          setMethod(selected);
          setMappingResolved(false);
          setMetadataResolved(false);
          pushLog({ level: "info", msg: `Method confirmed · ${selected.standard} ${selected.version}`.trim() });
          if (session?.mapping?.label) {
            pushLog({ level: session.mapping.critical_missing_count ? "warn" : "ok", msg: `Default mapping applied · ${session.mapping.label}` });
          }
          return;
        }
        const msg = response?.message || "Could not select method through backend.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || "Could not select method through backend.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
    }
    setSelectedMethodId(fallbackMethod.id);
    setMethod(fallbackMethod);
    pushLog({ level: "info", msg: `Method confirmed · ${fallbackMethod.standard} ${fallbackMethod.version}`.trim() });
    pushLog({ level: "ok", msg: "Default mapping applied · 35/35 critical inputs bound" });
    pushLog({ level: "warn", msg: "Readiness READY_WITH_WARNINGS · 7 report gaps · 38 recommended blank" });
  }
  async function checkReadiness() {
    const api = window.desktopApi?.analysis;
    if (!analysisSession?.session_id || !api?.checkReadiness) {
      flash("Readiness READY_WITH_WARNINGS");
      pushLog({ level: "warn", msg: "Readiness check used prototype fallback" });
      return;
    }
    try {
      const response = await api.checkReadiness({ session_id: analysisSession.session_id });
      if (response?.status !== "ok") {
        const msg = response?.message || "Readiness check failed.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        return;
      }
      setAnalysisSession(response.data);
      const readiness = response.data?.readiness || {};
      const status = readiness.status || response.data?.readiness_status || "UNKNOWN";
      const summary = readiness.summary || {};
      const critical = `${summary.execution_critical_passed ?? 0}/${summary.execution_critical_total ?? 0}`;
      const reportMissing = summary.report_missing_total ?? 0;
      pushLog({ level: isAnalysisSessionRunEnabled(response.data) ? "ok" : "warn", msg: `Readiness ${status} · ${critical} critical inputs · ${reportMissing} report gaps` });
      flash(`Readiness ${status}`);
    } catch (err) {
      const msg = err?.message || "Readiness check failed.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    }
  }
  function saveBindings() { setMappingResolved(true); pushLog({ level: "ok", msg: "Report bindings saved · iso14126_manual_wizard_edit.json" }); flash("Report bindings saved."); }
  function skipBindings() { setMappingResolved(true); pushLog({ level: "warn", msg: "Report bindings skipped · warnings accepted" }); }
  function openMetadata() { setShowReportDialog(true); }
  function acceptMetadata() { setMetadataResolved(true); pushLog({ level: "warn", msg: "38 recommended metadata fields left blank · warnings accepted" }); }
  async function browseMapping() {
    const api = window.desktopApi?.analysis;
    if (!analysisSession?.session_id || !api?.openMappingDialog) {
      const msg = "Mapping profile browsing requires the desktop backend bridge.";
      pushLog({ level: "warn", msg });
      flash(msg);
      return null;
    }
    try {
      const payload = { session_id: analysisSession.session_id };
      const initialDir = parentDirectoryFromPath(analysisSession?.mapping?.path);
      if (initialDir) payload.initial_dir = initialDir;
      const response = await api.openMappingDialog(payload);
      if (response?.status === "ok") {
        setAnalysisSession(response.data);
        const nextBindings = bindingsFromBackendMapping(response.data?.mapping);
        applyBackendMappings(nextBindings);
        setMappingResolved(false);
        pushLog({ level: "ok", msg: `Mapping profile loaded · ${response.data?.mapping?.mapping_name || "backend profile"}` });
        return nextBindings;
      }
      const msg = response?.message || "Could not load mapping profile.";
      if (response?.error_type !== "Cancelled") setBackendPackageError(msg);
      pushLog({ level: response?.error_type === "Cancelled" ? "info" : "warn", msg });
    } catch (err) {
      const msg = err?.message || "Could not load mapping profile.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    }
    return null;
  }
  async function saveMappingAs(newBindings) {
    const api = window.desktopApi?.analysis;
    if (!analysisSession?.session_id || !api?.saveMappingDialog) {
      const msg = "Mapping profile Save-as requires the desktop backend bridge.";
      pushLog({ level: "warn", msg });
      flash(msg);
      return null;
    }
    try {
      const payload = {
        session_id: analysisSession.session_id,
        bindings: mappingPatchRows(newBindings),
        default_name: mappingSaveDefaultName(analysisSession?.mapping),
      };
      const initialDir = parentDirectoryFromPath(analysisSession?.mapping?.path);
      if (initialDir) payload.initial_dir = initialDir;
      const response = await api.saveMappingDialog(payload);
      if (response?.status === "ok") {
        setAnalysisSession(response.data);
        const nextBindings = bindingsFromBackendMapping(response.data?.mapping);
        applyBackendMappings(nextBindings);
        const blockers = nextBindings.filter((row) => row.req === "required" && !isResolved(row)).length;
        setMappingResolved(blockers === 0 && Boolean(response.data?.mapping_confirmed));
        pushLog({ level: "ok", msg: `Mapping profile saved · ${response.data?.mapping?.mapping_name || "backend profile"}` });
        return nextBindings;
      }
      const msg = response?.message || "Could not save mapping profile.";
      if (response?.error_type !== "Cancelled") setBackendPackageError(msg);
      pushLog({ level: response?.error_type === "Cancelled" ? "info" : "warn", msg });
    } catch (err) {
      const msg = err?.message || "Could not save mapping profile.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    }
    return null;
  }
  async function saveMapping(newBindings, dirty) {
    const normalizedBindings = Array.isArray(newBindings) ? newBindings : [];
    if (analysisSession?.session_id && dirty) {
      const api = window.desktopApi?.analysis;
      if (!api?.applyMappingPatch) {
        const msg = "Mapping edits need backend applyMappingPatch before they can be saved.";
        pushLog({ level: "warn", msg });
        flash(msg);
        return;
      }
      try {
        const response = await api.applyMappingPatch({
          session_id: analysisSession.session_id,
          bindings: mappingPatchRows(newBindings),
        });
        if (response?.status === "ok") {
          setAnalysisSession(response.data);
          const nextBindings = bindingsFromBackendMapping(response.data?.mapping);
          applyBackendMappings(nextBindings);
          setMappingResolved(true);
          setShowMapping(false);
          pushLog({ level: "ok", msg: `Mapping edits saved · ${response.data?.mapping?.mapping_name || "backend profile"}` });
          return;
        }
        const msg = response?.message || "Could not save mapping edits.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || "Could not save mapping edits.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
      return;
    }
    if (analysisSession?.session_id && window.desktopApi?.analysis?.confirmMapping) {
      try {
        const response = await window.desktopApi.analysis.confirmMapping({ session_id: analysisSession.session_id });
        if (response?.status === "ok") {
          setAnalysisSession(response.data);
          const nextBindings = bindingsFromBackendMapping(response.data?.mapping);
          if (nextBindings.length) {
            applyBackendMappings(nextBindings);
          } else {
            setMappingDirty(false);
          }
          setMappingResolved(true);
          setShowMapping(false);
          pushLog({ level: "ok", msg: `Mapping profile confirmed · ${response.data?.mapping?.mapping_name || "backend profile"}` });
          return;
        }
        const msg = response?.message || "Could not confirm mapping profile.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || "Could not confirm mapping profile.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
      return;
    }
    applyBackendMappings(normalizedBindings);
    setMappingResolved(!normalizedBindings.some((row) => row.req === "required" && !isResolved(row)));
    setShowMapping(false);
    pushLog({ level: dirty ? "ok" : "info", msg: dirty ? "Repaired mapping saved · iso14126_manual_wizard_edit.json" : "Mapping profile confirmed" });
  }

  function handleBackendRunSession(session) {
    setAnalysisSession(session);
    const run = session?.run || {};
    if (run.status === "completed") {
      const refreshKey = `${session?.session_id || ""}:${run.run_id || ""}`;
      if (needsBackendReviewRowsRefresh(session) && window.desktopApi?.analysis?.getSession && !reviewRowsRefreshRef.current.has(refreshKey)) {
        reviewRowsRefreshRef.current.add(refreshKey);
        refreshBackendRunSession(session.session_id);
        return true;
      }
      stopBackendEventSubscription();
      pushLog({ level: "ok", msg: `Method run complete · ${run.result?.output_path || run.output_path || "MTDA output ready"}` });
      setPhase("review");
      return true;
    }
    if (run.status === "failed") {
      stopBackendEventSubscription();
      const msg = run.errors?.[0] || run.message || "Method run failed.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
      return true;
    }
    if (run.status === "cancelled") {
      stopBackendEventSubscription();
      pushLog({ level: "warn", msg: run.message || "Run cancelled by operator · returned to setup" });
      setPhase("setup");
      return true;
    }
    return false;
  }

  function backendEventLogLevel(event) {
    const marker = String(event?.data?.status || event?.event || "").toLowerCase();
    if (marker.includes("fail") || marker.includes("cancel")) return "warn";
    if (marker.includes("complete") || marker.includes("finalized")) return "ok";
    return "info";
  }

  function backendEventKey(event, index = 0) {
    return event?.event_id || `${event?.event || "event"}:${event?.data?.phase || ""}:${event?.data?.message || ""}:${index}`;
  }

  function logBackendEventPage(data) {
    (data?.events || []).forEach((event, index) => {
      const key = backendEventKey(event, index);
      if (loggedEventIdsRef.current.has(key)) return;
      loggedEventIdsRef.current.add(key);
      const details = event?.data || {};
      const message = details.message || details.phase || event?.event || "backend event";
      pushLog({ level: backendEventLogLevel(event), msg: `Backend ${event?.event || "event"}: ${message}` });
    });
  }

  function mergeBackendEventPage(data) {
    const pageEvents = Array.isArray(data?.events) ? data.events : [];
    if (!pageEvents.length) return;
    setAnalysisSession((session) => {
      if (!session || (data?.session_id && session.session_id !== data.session_id)) return session;
      const run = session.run || {};
      const existing = Array.isArray(run.events) ? run.events : [];
      const seen = new Set(existing.map((event, index) => backendEventKey(event, index)));
      const merged = [...existing];
      pageEvents.forEach((event, index) => {
        const key = backendEventKey(event, index);
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(event);
        }
      });
      const last = pageEvents[pageEvents.length - 1] || {};
      const details = last.data || {};
      const nextRun = {
        ...run,
        events: merged,
        run_id: run.run_id || data?.run_id,
        phase: details.phase || run.phase,
        message: details.message || run.message,
      };
      if (details.progress_percent !== undefined) nextRun.progress_percent = Number(details.progress_percent);
      return { ...session, run: nextRun };
    });
  }

  async function refreshBackendRunSession(sessionId) {
    const api = window.desktopApi?.analysis;
    if (!sessionId || !api?.getSession) return;
    try {
      const response = await api.getSession({ session_id: sessionId });
      if (response?.status === "ok") {
        handleBackendRunSession(response.data);
        return;
      }
      const msg = response?.message || "Could not refresh method run state.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    } catch (err) {
      const msg = err?.message || "Could not refresh method run state.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    }
  }

  function handlePushedBackendEvents(payload) {
    if (payload?.status === "error") {
      const msg = payload.message || "Backend event stream failed.";
      pushLog({ level: "warn", msg });
      return;
    }
    const data = payload?.data || payload || {};
    const nextCursor = Number(data.next_cursor ?? eventCursorRef.current);
    if (Number.isFinite(nextCursor)) eventCursorRef.current = Math.max(eventCursorRef.current, nextCursor);
    mergeBackendEventPage(data);
    logBackendEventPage(data);
    const terminal = (data.events || []).some((event) => {
      const marker = String(event?.data?.status || event?.event || "").toLowerCase();
      return marker.includes("completed") || marker.includes("failed") || marker.includes("cancelled");
    });
    if (terminal) refreshBackendRunSession(data.session_id);
  }

  async function stopBackendEventSubscription() {
    const unsubscribe = eventSubscriptionRef.current;
    eventSubscriptionRef.current = null;
    if (!unsubscribe) return;
    try {
      await unsubscribe();
    } catch (err) {
      pushLog({ level: "warn", msg: err?.message || "Could not stop backend event stream." });
    }
  }

  async function subscribeBackendEvents(sessionId) {
    const api = window.desktopApi?.analysis;
    if (!sessionId || !api?.subscribeEvents) return;
    await stopBackendEventSubscription();
    const response = await api.subscribeEvents(
      {
        session_id: sessionId,
        cursor: eventCursorRef.current,
        limit: 100,
      },
      { onEvent: handlePushedBackendEvents },
    );
    if (response?.status === "ok" && typeof response.unsubscribe === "function") {
      eventSubscriptionRef.current = response.unsubscribe;
      pushLog({ level: "info", msg: "Backend event stream connected" });
      return;
    }
    if (response?.status === "error" && response?.error_type !== "BridgeUnavailable") {
      pushLog({ level: "warn", msg: response.message || "Backend event stream unavailable." });
    }
  }

  async function pollBackendEvents(sessionId) {
    const api = window.desktopApi?.analysis;
    if (!sessionId || !api?.getEvents) return;
    try {
      const response = await api.getEvents({
        session_id: sessionId,
        cursor: eventCursorRef.current,
        limit: 100,
      });
      if (response?.status !== "ok") return;
      const data = response.data || {};
      const nextCursor = Number(data.next_cursor ?? eventCursorRef.current);
      if (Number.isFinite(nextCursor)) eventCursorRef.current = nextCursor;
      mergeBackendEventPage(data);
      logBackendEventPage(data);
    } catch (err) {
      const msg = err?.message || "Could not read backend event stream.";
      pushLog({ level: "warn", msg });
    }
  }

  function pollBackendRun(sessionId) {
    if (runPollRef.current) clearTimeout(runPollRef.current);
    const tick = async () => {
      const api = window.desktopApi?.analysis;
      if (!api?.getSession) return;
      try {
        const response = await api.getSession({ session_id: sessionId });
        if (response?.status !== "ok") {
          const msg = response?.message || "Could not refresh method run state.";
          setBackendPackageError(msg);
          pushLog({ level: "warn", msg });
          return;
        }
        await pollBackendEvents(response.data?.session_id || sessionId);
        const terminal = handleBackendRunSession(response.data);
        if (!terminal) runPollRef.current = setTimeout(tick, 650);
      } catch (err) {
        const msg = err?.message || "Could not refresh method run state.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
    };
    runPollRef.current = setTimeout(tick, 450);
  }

  async function startRun() {
    const api = window.desktopApi?.analysis;
    if (analysisSession?.session_id && api?.startRun) {
      setPhase("running");
      eventCursorRef.current = 0;
      pushLog({ level: "info", msg: "Method execution requested through backend" });
      try {
        const response = await api.startRun({
          session_id: analysisSession.session_id,
          output_path: analysisSession.output_path,
          overwrite: true,
          generate_workbench: true,
        });
        if (response?.status !== "ok") {
          const msg = response?.message || "Could not start method run.";
          setBackendPackageError(msg);
          pushLog({ level: "warn", msg });
          setPhase("setup");
          return;
        }
        await subscribeBackendEvents(response.data?.session_id || analysisSession.session_id);
        await pollBackendEvents(response.data?.session_id || analysisSession.session_id);
        const terminal = handleBackendRunSession(response.data);
        if (!terminal) {
          pushLog({ level: "info", msg: `Backend method run started · ${response.data?.run?.run_id || "active run"}` });
          pollBackendRun(response.data.session_id);
        }
      } catch (err) {
        const msg = err?.message || "Could not start method run.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        setPhase("setup");
      }
      return;
    }
    setPhase("running"); pushLog({ level: "info", msg: "Method execution started" });
  }
  function runComplete() {
    setPhase("review");
    const run = analysisSession?.run || {};
    pushLog({ level: "ok", msg: run.result?.output_path ? `Reduction complete · ${run.result.output_path}` : "Reduction complete · 3 runs flagged for review" });
  }
  async function cancelRun() {
    const api = window.desktopApi?.analysis;
    if (runPollRef.current) clearTimeout(runPollRef.current);
    if (analysisSession?.session_id && api?.cancelRun && analysisSession?.run?.status === "running") {
      try {
        const response = await api.cancelRun({ session_id: analysisSession.session_id });
        if (response?.status === "ok") {
          await pollBackendEvents(response.data?.session_id || analysisSession.session_id);
          setAnalysisSession(response.data);
        }
      } catch (err) {
        const msg = err?.message || "Could not cancel backend method run.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
    }
    await stopBackendEventSubscription();
    setPhase("setup"); pushLog({ level: "warn", msg: "Run cancelled by operator · returned to setup" });
  }
  async function persistReviewDecision(flaggedRun, decision, reason = "") {
    const api = window.desktopApi?.analysis;
    if (!analysisSession?.session_id || !api?.updateAcceptanceDecision) return;
    try {
      const response = await api.updateAcceptanceDecision({
        session_id: analysisSession.session_id,
        method_run_id: analysisSession.run?.run_id,
        decision_patch: reviewDecisionRow(flaggedRun, decision, reason),
      });
      if (response?.status === "ok") {
        setAnalysisSession(response.data);
        return;
      }
      const msg = response?.message || "Could not persist acceptance decision.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    } catch (err) {
      const msg = err?.message || "Could not persist acceptance decision.";
      setBackendPackageError(msg);
      pushLog({ level: "warn", msg });
    }
  }
  async function confirmReview() {
    const api = window.desktopApi?.analysis;
    if (analysisSession?.session_id && api?.confirmReview) {
      try {
        const response = await api.confirmReview({
          session_id: analysisSession.session_id,
          method_run_id: analysisSession.run?.run_id,
          decisions: reviewDecisionRows(decisions, reasons, reviewRows),
        });
        if (response?.status === "ok") {
          setAnalysisSession(response.data);
          setPhase("finalize");
          pushLog({ level: "ok", msg: "Acceptance confirmed through backend · opening output" });
          return;
        }
        const msg = response?.message || "Could not confirm acceptance review.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || "Could not confirm acceptance review.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
      return;
    }
    setPhase("finalize"); pushLog({ level: "ok", msg: "Acceptance confirmed · opening output" });
  }
  function restoreRun(run) { pushLog({ level: "info", msg: `${run} restore requested · failure-mode re-classification` }); flash(`${run} — reopen failure-mode classification to restore.`); }
  async function applyReportAmendments({ report_overrides, counts, note: reportNote }) {
    const api = window.desktopApi?.analysis;
    const resolved = counts || { required: 0, recommended: 0 };
    if (analysisSession?.session_id && api?.applyReportAmendments) {
      try {
        const response = await api.applyReportAmendments({
          session_id: analysisSession.session_id,
          method_run_id: analysisSession.run?.run_id,
          report_overrides,
          reviewer,
          reason: reportNote || "Report completion amendment recorded from Finalize report dialog.",
        });
        if (response?.status === "ok") {
          setAnalysisSession(response.data);
          setFieldsResolved(resolved);
          setMetadataResolved(true);
          const amendmentPath = response.data?.report_amendments?.output_path || response.data?.output_path || "MTDA output";
          pushLog({ level: "ok", msg: `Report amendments applied through backend · ${amendmentPath}` });
          return true;
        }
        const msg = response?.message || "Could not apply report amendments.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        return false;
      } catch (err) {
        const msg = err?.message || "Could not apply report amendments.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        return false;
      }
    }
    setFieldsResolved(resolved);
    setMetadataResolved(true);
    pushLog({ level: "ok", msg: "Report amendments applied" });
    return true;
  }
  async function doFinalize() {
    const api = window.desktopApi?.analysis;
    if (analysisSession?.session_id && api?.finalizeMtda) {
      try {
        const response = await api.finalizeMtda({
          session_id: analysisSession.session_id,
          method_run_id: analysisSession.run?.run_id,
          reviewer,
          note,
          reason_kind: reasonKind,
        });
        if (response?.status === "ok") {
          setAnalysisSession(response.data);
          setFinalized(true);
          const finalizedPath = response.data?.finalization?.output_path || response.data?.output_path || WIZ.OUTPUT.mtdaVersion;
          pushLog({ level: "ok", msg: `MTDA finalized by ${reviewer || "operator"} · ${finalizedPath} · amendment recorded` });
          flash(`MTDA finalized — ${WIZ.OUTPUT.mtdaVersion} issued, review state locked.`);
          return;
        }
        const msg = response?.message || "Could not finalize MTDA.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || "Could not finalize MTDA.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
      return;
    }
    setFinalized(true); pushLog({ level: "ok", msg: `MTDA finalized by ${reviewer || "operator"} · ${WIZ.OUTPUT.mtdaVersion} · amendment recorded` }); flash(`MTDA finalized — ${WIZ.OUTPUT.mtdaVersion} issued, review state locked.`);
  }
  async function copyPath() {
    const api = window.desktopApi?.analysis;
    let path = analysisSession?.finalization?.output_path || analysisSession?.output_path || analysisSession?.run?.output_path || analysisSession?.run?.result?.output_path || "";
    if (analysisSession?.session_id && api?.copyOutputPath) {
      try {
        const response = await api.copyOutputPath({ session_id: analysisSession.session_id });
        if (response?.status === "ok") {
          path = response.data?.path || response.data?.output_path || path;
        } else {
          const msg = response?.message || "Could not read MTDA output path.";
          setBackendPackageError(msg);
          pushLog({ level: "warn", msg });
          return;
        }
      } catch (err) {
        const msg = err?.message || "Could not read MTDA output path.";
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        return;
      }
    }
    if (!path) {
      flash("No MTDA output path is available yet.");
      pushLog({ level: "warn", msg: "Copy MTDA path requested before output exists" });
      return;
    }
    try { await navigator.clipboard?.writeText?.(path); } catch {}
    flash("MTDA path copied to clipboard");
    pushLog({ level: "info", msg: `MTDA path copied to clipboard · ${path}` });
  }
  async function openArtifact(artifact) {
    const api = window.desktopApi?.analysis;
    const title = typeof artifact === "string" ? artifact : artifact?.title || "Output artifact";
    const artifactKind = artifact?.id || artifactKindFromTitle(title);
    if (!analysisSession?.session_id && !outputPath && !demoMode) {
      flash(`${title} is unavailable until method output exists.`);
      pushLog({ level: "warn", msg: `${title} requested before output exists` });
      return;
    }
    if (analysisSession?.session_id && api?.openArtifact) {
      try {
        const response = await api.openArtifact({
          session_id: analysisSession.session_id,
          artifact_kind: artifactKind,
        });
        if (response?.status === "ok") {
          const target = response.data?.path || response.data?.target_path || title;
          flash(`${title} opened`);
          pushLog({ level: "info", msg: `${title} opened · ${target}` });
          return;
        }
        const msg = response?.message || `Could not open ${title}.`;
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      } catch (err) {
        const msg = err?.message || `Could not open ${title}.`;
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
      }
      return;
    }
    flash(`${title} — opens generated artifact`);
    pushLog({ level: "info", msg: `${title} opened` });
  }
  function jumpRun(run) { setPhase("review"); setExpanded(run); pushLog({ level: "info", msg: `Jumped to ${run} in review` }); }

  // ---- derived ----
  const acceptanceReport = useMemo(() => acceptanceReportFromSession(analysisSession), [analysisSession]);
  const backendReviewRows = useMemo(() => {
    const serialized = reviewRowsFromBackendRun(analysisSession?.run);
    if (serialized.length) return serialized;
    if (!acceptanceReport) return demoMode ? WIZ.FLAGGED : [];
    return reviewRowsFromAcceptanceReport(
      acceptanceReport,
      { flagCockpits: true },
    );
  }, [acceptanceReport, demoMode, analysisSession]);
  const reviewRows = backendReviewRows.length ? backendReviewRows : (demoMode ? WIZ.FLAGGED : []);
  const outputRunManifest = useMemo(() => buildOutputRunManifest({
    session: analysisSession,
    report: acceptanceReport,
    reviewRows,
    demoRows: demoMode ? WIZ.FLAGGED : [],
  }), [acceptanceReport, analysisSession, demoMode, reviewRows]);
  const reviewTotalRuns = Number(acceptanceCounts(acceptanceReport).total_runs || outputRunManifest.length || pkg?.runs || (demoMode ? WIZ.PACKAGE.runs : 0));

  useEffect(() => {
    if (phase === "review" && reviewRows.length && expanded && !reviewRows.some((row) => reviewRowIdentity(row) === expanded)) {
      setExpanded(reviewRowIdentity(reviewRows[0]));
    }
  }, [expanded, phase, reviewRows]);

  const reviewSummary = useMemo(() => {
    const active = reviewRows.filter((f) => !f.excluded);
    const overrides = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) !== f.defaultCall).length;
    const missing = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) === "Keep" && f.defaultCall === "Remove" && !(reasons[reviewRowIdentity(f)] || "").trim()).length;
    const removed = active.filter((f) => (decisions[reviewRowIdentity(f)] ?? f.defaultCall) === "Remove").length + reviewRows.filter((f) => f.excluded).length;
    return { totalRuns: reviewTotalRuns, flaggedRuns: reviewRows.length, overrides, missing, finalRuns: Math.max(0, reviewTotalRuns - removed), amendments: 0, notes: 0 };
  }, [decisions, reasons, reviewRows, reviewTotalRuns]);

  const outputPath = analysisSession?.finalization?.output_path
    || analysisSession?.output_path
    || analysisSession?.run?.output_path
    || analysisSession?.run?.result?.output_path
    || (demoMode ? WIZ.OUTPUT.path : "");
  const spine = useMemo(() => computeSpine(phase, { pkg, method, mappingResolved, metadataResolved, runEnabled, finalized }), [phase, pkg, method, mappingResolved, metadataResolved, runEnabled, finalized]);

  const ab = actionBar(phase, {
    pkg, method, pkgSel, runEnabled, mappingResolved, metadataResolved,
    choosePackage: openPackageDialog,
    confirmMethod, startRun, cancelRun, confirmReview,
    reviewBlock: reviewSummary.missing, openMapping: () => setShowMapping(true),
    openLog: () => setShowLog(true), finalized,
    outputAvailable: !!outputPath,
    openTestReport: () => { openArtifact({ id: "test_report", title: "Test Report" }); },
  });

  const sb = statusBar(phase, { finalized, runEnabled, mappingResolved, metadataResolved });

  function menuAction(label) {
    switch (label) {
      case "Back a step": back(); break;
      case "Next step": stepScenario(1); break;
      case "Toggle activity log": setShowLog((v) => !v); break;
      case "Toggle context detail": setContextOpen((v) => !v); break;
      case "Tweaks…": setShowTweaks(true); break;
      case "New method run": startNewMethodRun(); break;
      case "Open package…": openPackageDialog(); break;
      case "Choose package…": setPhase("setup"); openPackageDialog(); break;
      case "Choose method…": setPhase("setup"); setMethod(null); setSelectedMethodId(backendMethodOptions[0]?.id || WIZ.METHOD.id); break;
      case "Edit mapping…": if (method) setShowMapping(true); break;
      case "Check readiness": checkReadiness(); break;
      case "Run method": if (phase === "setup" && runEnabled) startRun(); break;
      case "Close wizard": closeWizard(); break;
      case "Open Test Report": openArtifact({ id: "test_report", title: "Test Report" }); break;
      case "Open Audit Report": openArtifact({ id: "audit_report", title: "Audit Report" }); break;
      case "Open output folder": openArtifact({ id: "output_folder", title: "Output folder" }); break;
      case "Copy MTDA path": copyPath(); break;
      case "Shortcuts": flash("L · log   ← → or swipe · step   Esc · close"); break;
      case "About Method Analysis": setShowGuide(true); break;
      default: {
        const msg = `Unsupported menu action: ${label}`;
        setBackendPackageError(msg);
        pushLog({ level: "warn", msg });
        flash("Unsupported menu action.");
      }
    }
  }

  function back() {
    if (phase === "finalize") gotoScenario("review");
    else if (phase === "review") gotoScenario("running");
    else if (phase === "running") gotoScenario("setup");
  }

  // ---- swipe navigation (mirrors ← / → keys): left = forward, right = back ----
  const stageRef = useRef(null);
  const [swipeNudge, setSwipeNudge] = useState(0); // -1 back peek, +1 fwd peek
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    let x0 = 0, y0 = 0, t0 = 0, tracking = false;
    const onStart = (e) => {
      if (anyOverlay) return;
      const t = e.touches ? e.touches[0] : e;
      x0 = t.clientX; y0 = t.clientY; t0 = Date.now(); tracking = true;
    };
    const onMove = (e) => {
      if (!tracking) return;
      const t = e.touches ? e.touches[0] : e;
      const dx = t.clientX - x0, dy = t.clientY - y0;
      if (Math.abs(dx) > 24 && Math.abs(dx) > Math.abs(dy) * 1.6) {
        setSwipeNudge(dx < 0 ? 1 : -1);
      }
    };
    const onEnd = (e) => {
      if (!tracking) { setSwipeNudge(0); return; }
      tracking = false;
      const t = e.changedTouches ? e.changedTouches[0] : e;
      const dx = t.clientX - x0, dy = t.clientY - y0, dt = Date.now() - t0;
      setSwipeNudge(0);
      const horizontal = Math.abs(dx) > Math.abs(dy) * 1.6;
      const far = Math.abs(dx) > 70;
      const flick = Math.abs(dx) > 42 && dt < 320;
      if (horizontal && (far || flick)) {
        if (dx < 0) stepScenario(1); else stepScenario(-1);
      }
    };
    el.addEventListener("touchstart", onStart, { passive: true });
    el.addEventListener("touchmove", onMove, { passive: true });
    el.addEventListener("touchend", onEnd, { passive: true });
    return () => {
      el.removeEventListener("touchstart", onStart);
      el.removeEventListener("touchmove", onMove);
      el.removeEventListener("touchend", onEnd);
    };
  });

  function jump(step) {
    if (["Package", "Method", "Mapping", "Ready"].includes(step)) { if (phase === "setup") return; gotoScenario("setup"); }
    else if (step === "Run") gotoScenario("running");
    else if (["Validate", "Accept"].includes(step)) gotoScenario("review");
    else if (step === "Output") gotoScenario("finalize");
  }

  return (
    <div className="app" onClick={() => openMenu && setOpenMenu(null)}>
      <MenuBar onAction={menuAction} openMenu={openMenu} setOpenMenu={setOpenMenu} />
      <Spine states={spine} onJump={jump} phase={phase} />

      <div className="stage" ref={stageRef} data-nudge={swipeNudge}>
        {phase === "setup" && <SetupSpotlight
          pkg={pkg} method={method} pkgSel={pkgSel} setPkgSel={setPkgSel}
          backendPackageError={backendPackageError}
          analysisSession={analysisSession}
          recentPackages={recentPackages}
          recentPackageLoading={recentPackageLoading}
          recentPackageError={recentPackageError}
          runEnabled={runEnabled}
          readinessStatus={readinessStatus || (runEnabled ? "READY_WITH_WARNINGS" : "")}
          methodOptions={backendMethodOptions}
          selectedMethodId={selectedMethodId}
          onSelectMethodId={setSelectedMethodId}
          mappingSummary={method ? analysisSession?.mapping : null}
          onChoosePackage={loadPackagePath} onConfirmMethod={confirmMethod}
          mappingResolved={mappingResolved} metadataResolved={metadataResolved}
          onSaveBindings={saveBindings} onSkipBindings={skipBindings} onEditMapping={() => setShowMapping(true)}
          onOpenMetadata={openMetadata} onAcceptMetadata={acceptMetadata}
          onOpenPackageDialog={openPackageDialog}
          onChangePackage={openPackageDialog}
          onChangeMethod={() => { setMethod(null); setSelectedMethodId(backendMethodOptions[0]?.id || WIZ.METHOD.id); }} />}
        {phase === "running" && <Running onComplete={runComplete} onCancel={cancelRun} pushLog={pushLog} backendRun={analysisSession?.run} backendMode={!!analysisSession?.session_id} demoMode={demoMode} />}
        {phase === "review" && <Review rows={reviewRows} totalRuns={reviewTotalRuns} decisions={decisions} setDecisions={setDecisions} reasons={reasons} setReasons={setReasons} expanded={expanded} setExpanded={setExpanded} onRestore={restoreRun} onDecisionPersist={persistReviewDecision} />}
        {phase === "finalize" && <Finalize finalized={finalized} note={note} setNote={setNote} reviewer={reviewer} setReviewer={setReviewer} reasonKind={reasonKind} setReasonKind={setReasonKind} fieldsResolved={fieldsResolved} reviewSummary={reviewSummary} outputPath={outputPath} runManifest={outputRunManifest} onFinalized={doFinalize} onReviewFields={() => setShowReportDialog(true)} onCopyPath={copyPath} onJumpRun={jumpRun} onOpenArtifact={openArtifact} />}
      </div>

      <div className="actionbar">
        {phase !== "setup" && <Btn className="ab-back" icon="undo" onClick={back}>Back</Btn>}
        {ab.secondary && ab.secondary.length > 0 && (
          <div className="ab-left">{ab.secondary.map((s, i) => <Btn key={i} icon={s.icon} onClick={s.onClick} variant={s.variant}>{s.label}</Btn>)}</div>
        )}
        <div className="ab-status">
          <span className="ab-title">{ab.title}</span>
          <span className={"ab-hint" + (ab.hintTone ? " " + ab.hintTone : "")}>{ab.hint}</span>
        </div>
        <span className="ab-spacer" />
        {phase === "setup" && runEnabled && <span className="chip" data-tone="warn"><Icon name="check" style={{ width: 12, height: 12 }} />{readinessStatus || "READY_WITH_WARNINGS"}</span>}
        {ab.primary && <Btn variant={ab.primary.danger ? "danger solid" : "primary"} className="lg" icon={ab.primary.icon} disabled={ab.primary.disabled} onClick={ab.primary.onClick} title={ab.primary.title}>{ab.primary.label}</Btn>}
      </div>

      <ContextBar pkg={pkg} method={method} mapping={!!method} output={WIZ.OUTPUT.mtda} open={contextOpen} onToggle={() => setContextOpen((v) => !v)} onAction={menuAction} />
      <StatusBar tone={sb.tone} state={sb.state} logCount={log.length} onLog={() => setShowLog(true)} />

      {showMapping && <MappingEditor initial={bindings} mappingSummary={analysisSession?.mapping} onClose={() => setShowMapping(false)} onSave={saveMapping} onBrowse={browseMapping} onSaveAs={saveMappingAs} onDirtyChange={setMappingDirty} />}
      {showReportDialog && <ReportCompletionDialog onClose={() => setShowReportDialog(false)} onResolveAll={(r) => { setFieldsResolved(r); setMetadataResolved(true); pushLog({ level: "ok", msg: "Report amendments applied" }); }} onApplyAmendments={applyReportAmendments} reviewer={reviewer} />}
      {showGuide && <SectionGuidelinesModal section="analysis" onClose={() => setShowGuide(false)} />}
      {showLog && <LogDrawer entries={log} onClose={() => setShowLog(false)} />}
      {showTweaks && <div className="drawer-scrim" style={{ background: "transparent" }} onMouseDown={() => setShowTweaks(false)}><Tweaks density={density} setDensity={setDensity} accent={accent} setAccent={setAccent} onClose={() => setShowTweaks(false)} /></div>}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

function computeSpine(phase, { pkg, method, mappingResolved, metadataResolved, runEnabled, finalized }) {
  const order = ["setup", "running", "review", "finalize"];
  const pi = order.indexOf(phase);
  const s = {};
  s.Package = pkg ? "done" : (phase === "setup" ? "active" : "todo");
  s.Method = method ? "done" : (phase === "setup" && pkg ? "active" : "todo");
  s.Mapping = pi > 0 ? "done" : (method ? (mappingResolved && metadataResolved ? "done" : "warn") : (pkg ? "active" : "todo"));
  s.Ready = pi > 0 ? "done" : (runEnabled ? "warn" : "todo");
  s.Run = phase === "running" ? "active" : (pi > 1 ? "done" : "todo");
  s.Validate = pi > 1 ? "done" : "todo";
  s.Accept = phase === "review" ? "active" : (pi > 2 ? "done" : "todo");
  s.Output = phase === "finalize" ? (finalized ? "done" : "warn") : "todo";
  return s;
}

function actionBar(phase, ctx) {
  if (phase === "setup") {
    if (!ctx.pkg) return { title: "Choose package", hint: "",
      primary: { label: "Choose package...", icon: "package", onClick: ctx.choosePackage } };
    if (!ctx.method) return { title: "Choose method", hint: "",
      primary: { label: "Confirm method", icon: "arrowR", onClick: ctx.confirmMethod } };
    const unresolved = (!ctx.mappingResolved ? "7 unmapped report bindings" : "") + (!ctx.mappingResolved && !ctx.metadataResolved ? " · " : "") + (!ctx.metadataResolved ? "38 recommended fields blank" : "");
    return {
      title: ctx.mappingResolved && ctx.metadataResolved ? "Ready to run" : "Ready · with warnings",
      hint: ctx.mappingResolved && ctx.metadataResolved ? "" : unresolved + " · method runs either way.",
      hintTone: "warn",
      secondary: [{ label: "Edit mapping…", icon: "edit", onClick: ctx.openMapping }],
      primary: { label: "Run method", icon: "play", onClick: ctx.startRun, disabled: !ctx.runEnabled },
    };
  }
  if (phase === "running") return { title: "Method execution in progress", hint: "",
    secondary: [{ label: "View full log", onClick: ctx.openLog }],
    primary: { label: "Cancel run", danger: true, icon: "x", onClick: ctx.cancelRun } };
  if (phase === "review") return {
    title: "One decision before output",
    hint: ctx.reviewBlock ? `${ctx.reviewBlock} kept run${ctx.reviewBlock > 1 ? "s" : ""} need a justification` : "",
    hintTone: ctx.reviewBlock ? "block" : "",
    primary: { label: "Confirm & open output", icon: "arrowR", disabled: ctx.reviewBlock > 0, onClick: ctx.confirmReview, title: ctx.reviewBlock ? "Add a justification for every kept flagged run" : "Confirm acceptance and open output" } };
  if (phase === "finalize") return {
    title: ctx.finalized ? "MTDA finalized" : "Output ready — draft",
    hint: ctx.outputAvailable ? "" : "No analysed output is available yet.",
    hintTone: ctx.finalized ? "" : "warn",
    primary: { label: "Open Test Report", icon: "report", disabled: !ctx.outputAvailable, onClick: ctx.openTestReport } };
  return { title: "", hint: "" };
}

function statusBar(phase, { finalized, runEnabled }) {
  switch (phase) {
    case "setup": return runEnabled ? { tone: "warn", state: "Ready with warnings · run enabled" } : { tone: "", state: "Choose workflow inputs" };
    case "running": return { tone: "", state: "Method execution in progress" };
    case "review": return { tone: "warn", state: "Acceptance review pending" };
    case "finalize": return { tone: finalized ? "ok" : "warn", state: finalized ? "MTDA finalized" : "Output ready · draft" };
    default: return { tone: "", state: "" };
  }
}

function artifactKindFromTitle(title) {
  const value = String(title || "").toLowerCase();
  if (value.includes("test report")) return "test_report";
  if (value.includes("audit report")) return "audit_report";
  if (value.includes("folder")) return "output_folder";
  if (value.includes("mtda")) return "open_mtda";
  if (value.includes("browser") || value.includes("workbench")) return "workbench";
  return value.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

class ErrorBoundary extends React.Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  componentDidCatch(err, info) { console.error("BOUNDARY", err, info); }
  render() {
    if (this.state.err) {
      return <div style={{ position: "fixed", inset: 20, zIndex: 99999, background: "#fff", border: "3px solid red", padding: 16, font: "12px monospace", whiteSpace: "pre-wrap", overflow: "auto" }}>
        {"RENDER ERROR:\n" + (this.state.err && this.state.err.stack || String(this.state.err))}
      </div>;
    }
    return this.props.children;
  }
}



export default function MethodRunWizardApp(){
  return <ErrorBoundary><App /></ErrorBoundary>;
}
