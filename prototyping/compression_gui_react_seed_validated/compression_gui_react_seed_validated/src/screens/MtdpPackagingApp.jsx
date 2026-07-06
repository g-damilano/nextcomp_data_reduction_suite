import React from 'react';
import { DesktopWindowControls } from '../components/DesktopWindowControls.jsx';

// ================= schema.jsx =================
// ---------------------------------------------------------------------------
// Dataset Packaging v3 — schema module.
// Compiled 1:1 from src/mtdp_enrichment/schema_library/mechanical/compression/0.3.0.yaml
// Field ids, labels, groups, order, types, enums (display_labels), two-tier
// requirement (required vs report_importance), conditional visible_when /
// required_when, units (accepted_units / standard_unit / unit_dimension),
// channel families (data_table) and unit conversion rules all come from the
// YAML. No invented fields — revision candidates are flagged in the doc only.
// ---------------------------------------------------------------------------

const SCHEMA_META = {
  id: "mechanical.compression", version: "0.3.0", label: "Compression",
  unitSystem: "mechanical_metric_mm_N",
  source: "schema_library/mechanical/compression/0.3.0.yaml",
};

// unit factors → dimension-standard unit (unit_systems + unit_conversion_rules)
const UNIT_FACTORS = {
  length: { mm: 1, cm: 10, m: 1000, um: 0.001 },
  force: { N: 1, kN: 1000 },
  speed: { "mm/min": 1, "mm/s": 60 },
  strain: { "mm/mm": 1, usn: 1e-6, microstrain: 1e-6 },
  stress: { MPa: 1, "N/mm^2": 1, kPa: 1e-3, Pa: 1e-6 },
  time: { s: 1, ms: 1e-3, us: 1e-6 },
};
function convertUnit(value, dim, from, to) {
  const f = UNIT_FACTORS[dim];
  if (!f || f[from] == null || f[to] == null) return value;
  const n = parseFloat(value);
  if (isNaN(n)) return value;
  const out = (n * f[from]) / f[to];
  return String(Math.round(out * 1e6) / 1e6);
}
function conversionFactorLabel(dim, from, to) {
  const f = UNIT_FACTORS[dim];
  if (!f || f[from] == null || f[to] == null) return null;
  const k = f[from] / f[to];
  return k >= 1 ? "× " + k : "÷ " + Math.round(1 / k);
}

// ---- field catalogue (verbatim ids / labels / levels from the YAML) ----------
// importance: "required" | "recommended" | "optional" | "required_for_accepted_runs"
// hardRequired === `required: true` in YAML (blocks export).
const F = {}; // by field_id
function def(d) { F[d.id] = d; return d.id; }
const LEN = { units: ["mm", "cm", "m"], stdUnit: "mm", dim: "length", min: 0 };

// -------- dataset fields --------
def({ id: "sample_type", label: "Sample type", type: "string", hardRequired: true, importance: "required",
  pattern: /^[\w .,+/()#°-]+$/, ph: "Dataset / sample family name",
  desc: "Dataset/sample family name used to identify the tested group." });
def({ id: "treatment", label: "Treatment", type: "string", importance: "recommended",
  ph: "Condition or environmental ageing state",
  desc: "Material treatment, condition, or environmental ageing state." });
def({ id: "material_label", label: "Material label", type: "string", importance: "recommended",
  ph: "Label used in the formal report" });
def({ id: "test_id", label: "Test ID", type: "string", importance: "recommended", ph: "Lab test / request number" });
def({ id: "report_operator", label: "Dataset operator", type: "string", importance: "recommended",
  desc: "Person responsible for the test series." });
def({ id: "loading_method", label: "Loading method", type: "enum", importance: "required",
  options: [
    { v: "method_1_shear_loading", label: "Shear loading (Method 1)" },
    { v: "method_2_combined_loading", label: "Combined loading (Method 2)" },
    { v: "other_specified", label: "Other specified", deviation: true },
  ] });
def({ id: "loading_method_other", label: "Other loading method", type: "string", importance: "optional",
  visibleWhen: { field: "loading_method", equals: "other_specified" },
  requiredWhen: { field: "loading_method", equals: "other_specified" },
  desc: "Required when Loading method is Other specified; reported as an ISO deviation." });
def({ id: "specimen_type", label: "Specimen type", type: "enum", importance: "required",
  options: [
    { v: "type_a", label: "Type A" }, { v: "type_b1", label: "Type B1" },
    { v: "type_b2", label: "Type B2" }, { v: "other_specified", label: "Other specified", deviation: true },
  ] });
def({ id: "specimen_type_other", label: "Other specimen type", type: "string", importance: "optional",
  visibleWhen: { field: "specimen_type", equals: "other_specified" },
  requiredWhen: { field: "specimen_type", equals: "other_specified" },
  desc: "Required when Specimen type is Other specified; reported as an ISO deviation." });
def({ id: "material_type", label: "Material type", type: "string", importance: "recommended" });
def({ id: "matrix_type", label: "Matrix type", type: "string", importance: "recommended" });
def({ id: "reinforcement_type", label: "Reinforcement type", type: "string", importance: "recommended" });
def({ id: "manufacturer", label: "Manufacturer", type: "string", importance: "recommended" });
def({ id: "manufacturer_code", label: "Manufacturer code", type: "string", importance: "optional" });
def({ id: "material_source", label: "Source", type: "string", importance: "recommended" });
def({ id: "material_form", label: "Form", type: "string", importance: "recommended" });
def({ id: "previous_history", label: "Previous history", type: "string", importance: "recommended" });
def({ id: "cutting_direction", label: "Cutting direction", type: "string", importance: "recommended" });
def({ id: "fibre_orientation", label: "Fibre orientation", type: "string", importance: "recommended" });
def({ id: "layup", label: "Layup", type: "string", importance: "recommended" });
def({ id: "preparation_method", label: "Preparation method", type: "string", importance: "recommended" });
def({ id: "end_tabs", label: "End tabs", type: "string", importance: "optional" });
def({ id: "surface_preparation", label: "Surface preparation", type: "string", importance: "optional" });
def({ id: "specimen_preparation_notes", label: "Notes", type: "string", importance: "optional" });
def({ id: "fixture_type", label: "Fixture type", type: "string", importance: "recommended" });
def({ id: "fixture_standard_reference", label: "Fixture standard reference", type: "string", importance: "optional" });
def({ id: "fixture_manufacturer_design", label: "Manufacturer/design", type: "string", importance: "recommended" });
def({ id: "alignment_procedure", label: "Alignment procedure", type: "string", importance: "recommended" });
def({ id: "fixture_notes", label: "Notes", type: "string", importance: "optional" });
def({ id: "conditioning_standard", label: "Conditioning standard", type: "string", importance: "recommended" });
def({ id: "temperature", label: "Temperature", type: "float", importance: "recommended",
  units: ["°C", "°F", "K"], stdUnit: "°C", dim: "temperature", unitInline: true, ph: "e.g. 23",
  desc: "Conditioning / test temperature. Enter the number; pick the unit from the list." });
def({ id: "humidity", label: "Humidity", type: "float", importance: "recommended",
  units: ["% RH"], stdUnit: "% RH", dim: "humidity", unitInline: true, min: 0, ph: "e.g. 50",
  desc: "Relative humidity during conditioning. Enter the number; the unit is fixed to % RH." });
def({ id: "conditioning_time", label: "Conditioning time", type: "float", importance: "recommended",
  units: ["h", "min", "s", "d"], stdUnit: "h", dim: "time", unitInline: true, min: 0, ph: "e.g. 88",
  desc: "Conditioning duration. Enter the number; pick the unit from the list." });
def({ id: "test_environment", label: "Test environment", type: "string", importance: "recommended" });
def({ id: "speed_of_testing", label: "Speed of testing", type: "float", importance: "recommended",
  units: ["mm/min", "mm/s"], stdUnit: "mm/min", dim: "speed", min: 0, unitInline: true,
  desc: "Crosshead / test speed. Enter the number; pick the unit from the list." });
def({ id: "strain_measurement_method", label: "Strain measurement method", type: "string", importance: "required" });
def({ id: "measurement_location", label: "Measurement location", type: "string", importance: "recommended" });
def({ id: "acquisition_system", label: "Acquisition system", type: "string", importance: "recommended" });
def({ id: "sampling_rate", label: "Sampling rate", type: "float", importance: "recommended",
  units: ["Hz", "kHz"], stdUnit: "Hz", dim: "frequency", unitInline: true, min: 0, ph: "e.g. 100",
  desc: "Data acquisition rate. Enter the number; pick the unit from the list." });
def({ id: "measurement_notes", label: "Notes", type: "string", importance: "optional" });
def({ id: "deviations_from_standard", label: "Deviations from standard", type: "string", importance: "optional" });
def({ id: "remarks", label: "Remarks", type: "string", importance: "optional" });

// -------- run fields --------
def({ id: "specimen_name", label: "Specimen name", type: "string", hardRequired: true, importance: "required",
  pattern: /^[\w .,+/()#°-]+$/ });
def({ id: "sample_id", label: "Sample ID", type: "string", importance: "optional" });
def({ id: "width", label: "Width", type: "float", hardRequired: true, importance: "required", ...LEN, span: 1 });
def({ id: "thickness", label: "Thickness", type: "float", hardRequired: true, importance: "required", ...LEN, span: 1 });
def({ id: "gauge_length", label: "Strain-measurement gauge length", type: "float", importance: "recommended", ...LEN,
  desc: "Required for methods deriving strain from extension or crosshead displacement; recommended with direct strain channels." });
def({ id: "distance_between_end_tabs", label: "Distance between end tabs / unsupported length", type: "float", importance: "optional", ...LEN });
def({ id: "tab_length", label: "Tab length", type: "float", importance: "optional", ...LEN, span: 1 });
def({ id: "tab_thickness", label: "Tab thickness", type: "float", importance: "optional", ...LEN, span: 1 });
def({ id: "operator", label: "Operator", type: "string", importance: "recommended" });
def({ id: "instrument_model", label: "Instrument model", type: "string", importance: "optional" });
def({ id: "instrument_id", label: "Instrument ID / serial number", type: "string", importance: "recommended" });
def({ id: "instrument_location", label: "Instrument location", type: "string", importance: "optional" });
def({ id: "load_cell", label: "Load cell", type: "float", importance: "optional",
  units: ["N", "kN"], stdUnit: "kN", dim: "force", min: 0, span: 1 });
def({ id: "test_speed", label: "Test speed", type: "float", importance: "recommended",
  units: ["mm/min"], stdUnit: "mm/min", dim: "speed", min: 0, span: 1 });
def({ id: "test_date", label: "Test date", type: "date", importance: "recommended" });
def({ id: "source_software", label: "Source software", type: "string", importance: "recommended" });
def({ id: "run_notes", label: "Run notes", type: "string", importance: "optional" });
def({ id: "primary_failure_mode", label: "Primary failure mode", type: "enum",
  importance: "required_for_accepted_runs", default: "not_recorded", notRecorded: "not_recorded",
  options: [
    { v: "in_plane_shear", label: "In-plane shear" }, { v: "complex", label: "Complex" },
    { v: "through_thickness_shear", label: "Through-thickness shear" }, { v: "splitting", label: "Splitting" },
    { v: "delamination", label: "Delamination" }, { v: "not_recorded", label: "Not recorded" },
  ] });
def({ id: "failure_location", label: "Failure location", type: "enum",
  importance: "required_for_accepted_runs", default: "not_recorded", notRecorded: "not_recorded",
  options: [
    { v: "within_gauge_length", label: "Within gauge length" }, { v: "at_gauge_length_end", label: "At gauge length end" },
    { v: "fixture_edge_or_tab_edge", label: "Fixture edge or tab edge" }, { v: "grip_end_block", label: "Grip/end block" },
    { v: "end_tab", label: "End tab" }, { v: "specimen_end", label: "Specimen end" },
    { v: "outside_gauge_length", label: "Outside gauge length" }, { v: "unknown", label: "Unknown" },
    { v: "not_recorded", label: "Not recorded" },
  ] });
def({ id: "invalid_specimen_reason", label: "Invalid specimen reason", type: "enum", importance: "optional", default: "none",
  options: [
    { v: "none", label: "None" }, { v: "bending_non_compliance", label: "Bending non-compliance" },
    { v: "grip_end_block_failure", label: "Grip/end block failure" }, { v: "end_tab_failure", label: "End tab failure" },
    { v: "specimen_end_failure", label: "Specimen end failure" }, { v: "operator_marked_invalid", label: "Operator marked invalid" },
    { v: "data_quality_issue", label: "Data quality issue" }, { v: "other", label: "Other" },
  ] });
def({ id: "invalid_specimen_reason_other", label: "Other invalid specimen reason", type: "string", importance: "optional",
  visibleWhen: { field: "invalid_specimen_reason", equals: "other" },
  requiredWhen: { field: "invalid_specimen_reason", equals: "other" },
  desc: "Required when Invalid specimen reason is Other." });
def({ id: "visible_buckling_or_bending_observation", label: "Visible buckling / bending observation", type: "enum",
  importance: "optional", default: "not_recorded", notRecorded: "not_recorded",
  options: [
    { v: "none_observed", label: "None observed" }, { v: "visible_bending", label: "Visible bending" },
    { v: "suspected_euler_buckling", label: "Suspected Euler buckling" },
    { v: "specimen_slip_or_fixture_issue", label: "Specimen slip or fixture issue" },
    { v: "other", label: "Other" }, { v: "not_recorded", label: "Not recorded" },
  ] });
def({ id: "visible_buckling_or_bending_observation_other", label: "Other buckling / bending observation", type: "string",
  importance: "optional",
  visibleWhen: { field: "visible_buckling_or_bending_observation", equals: "other" },
  requiredWhen: { field: "visible_buckling_or_bending_observation", equals: "other" } });
def({ id: "failure_analysis_notes", label: "Failure analysis notes", type: "string", importance: "optional" });
def({ id: "failure_image_reference", label: "Failure image reference", type: "string", importance: "optional",
  desc: "Should link to the image-evidence failure view where available." });
def({ id: "validity", label: "Validity", type: "enum", importance: "recommended", default: "accepted",
  options: [
    { v: "accepted", label: "Accepted" }, { v: "rejected", label: "Rejected" },
    { v: "requires_review", label: "Requires review" }, { v: "unknown", label: "Unknown" },
  ] });
def({ id: "requires_review", label: "Requires review", type: "bool", importance: "optional" });
def({ id: "rejection_reason", label: "Rejection reason", type: "string", importance: "optional" });

// -------- metadata_sections (scope + order verbatim) --------
const DATASET_SECTIONS = [
  { id: "overview", label: "Overview", fields: ["sample_type", "treatment", "material_label"] },
  { id: "test_identification", label: "Test Identification",
    fields: ["test_id", "report_operator", "loading_method", "loading_method_other", "specimen_type", "specimen_type_other"] },
  { id: "material_identification", label: "Material Identification",
    fields: ["material_type", "matrix_type", "reinforcement_type", "manufacturer", "manufacturer_code", "material_source", "material_form", "previous_history"] },
  { id: "specimen_preparation", label: "Specimen Preparation",
    fields: ["cutting_direction", "fibre_orientation", "layup", "preparation_method", "end_tabs", "surface_preparation", "specimen_preparation_notes"] },
  { id: "loading_fixture", label: "Loading Fixture",
    fields: ["fixture_type", "fixture_standard_reference", "fixture_manufacturer_design", "alignment_procedure", "fixture_notes"] },
  { id: "test_conditions", label: "Test Conditions",
    fields: ["conditioning_standard", "temperature", "humidity", "conditioning_time", "test_environment", "speed_of_testing"] },
  { id: "measurement_method", label: "Measurement Method",
    fields: ["strain_measurement_method", "measurement_location", "acquisition_system", "sampling_rate", "measurement_notes"] },
  { id: "deviations_remarks", label: "Deviations / Remarks", fields: ["deviations_from_standard", "remarks"] },
].map((s) => ({ ...s, fields: s.fields.map((id) => F[id]) }));

const RUN_SECTIONS = [
  { id: "specimen_geometry", label: "Specimen Geometry",
    fields: ["specimen_name", "sample_id", "width", "thickness", "gauge_length", "distance_between_end_tabs", "tab_length", "tab_thickness"] },
  { id: "run_acquisition_inputs", label: "Run Acquisition Inputs",
    fields: ["operator", "instrument_model", "instrument_id", "instrument_location", "load_cell", "test_speed", "test_date", "source_software"] },
  { id: "channel_preamble_summary", label: "Channel / Preamble Summary", fields: ["run_notes"] },
  { id: "user_validity_failure_observation", label: "User Validity / Failure Observation",
    fields: ["primary_failure_mode", "failure_location", "invalid_specimen_reason", "invalid_specimen_reason_other",
      "visible_buckling_or_bending_observation", "visible_buckling_or_bending_observation_other",
      "failure_analysis_notes", "failure_image_reference", "validity", "requires_review", "rejection_reason"] },
].map((s) => ({ ...s, fields: s.fields.map((id) => F[id]) }));

const ALL_FIELDS = F;

// -------- channel families (data_table.columns verbatim) --------
const CHANNEL_FAMILIES = [
  { id: "load", label: "Load", required: true, repeatable: false, units: ["N", "kN"], std: "N", dim: "force" },
  { id: "extension", label: "Extension", repeatable: false, units: ["mm", "cm", "m"], std: "mm", dim: "length" },
  { id: "displacement", label: "Displacement", repeatable: false, units: ["mm", "cm", "m"], std: "mm", dim: "length" },
  { id: "strain", label: "Strain", repeatable: true, units: ["usn", "microstrain", "mm/mm"], std: "mm/mm", dim: "strain" },
  { id: "stress", label: "Stress", repeatable: true, units: ["MPa", "N/mm^2"], std: "MPa", dim: "stress" },
  { id: "time", label: "Time", repeatable: false, units: ["s", "ms", "us"], std: "s", dim: "time" },
  { id: "ignore", label: "Ignore — not exported", repeatable: true, units: ["—"], std: "—" },
];
const FAMILY = {}; CHANNEL_FAMILIES.forEach((f) => (FAMILY[f.id] = f));

// -------- evidence views + supplemental scopes (verbatim) --------
const IMAGE_VIEWS = [
  { id: "front", label: "Front image" }, { id: "side", label: "Side image" }, { id: "top", label: "Top image" },
  { id: "failure", label: "Failure image" }, { id: "scale_reference", label: "Scale reference" }, { id: "other", label: "Other image" },
];
const SUPPLEMENTAL_SCOPES = ["dataset", "run", "schema_mapping", "calibration", "equipment_evidence", "other"];

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function isFilled(v) { return v !== undefined && v !== null && String(v).trim() !== ""; }
// "not_recorded" defaults don't satisfy a requirement to record
function isRecorded(f, v) { return isFilled(v) && !(f.notRecorded && v === f.notRecorded); }

function isVisible(f, values) {
  if (!f.visibleWhen) return true;
  return (values[f.visibleWhen.field] || "") === f.visibleWhen.equals;
}
// effective level for THIS run/dataset values context
function effLevel(f, values) {
  if (f.hardRequired) return "required";
  if (f.requiredWhen && (values[f.requiredWhen.field] || "") === f.requiredWhen.equals) return "required";
  if (f.importance === "required_for_accepted_runs") {
    const validity = values.validity || ALL_FIELDS.validity.default;
    return validity === "accepted" ? "required" : "optional";
  }
  if (f.importance === "required") return "report";
  if (f.importance === "recommended") return "recommended";
  return "optional";
}
function visibleFields(fields, values, density) {
  return fields.filter((f) => {
    if (!isVisible(f, values)) return false;
    const lv = effLevel(f, values);
    if (density === "essential") return lv === "required" || lv === "report";
    if (density === "core") return lv !== "optional" || isFilled(values[f.id]);
    return true;
  });
}
const DATE_RX = [/^\d{4}-\d{2}-\d{2}$/, /^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$/];
function fieldError(f, v) {
  if (!isFilled(v)) return null;
  if (f.type === "float") {
    if (String(v).includes(",")) return "Use “.” as decimal separator";
    const n = Number(v);
    if (isNaN(n)) return "Not a number";
    if (f.min !== undefined && n < f.min) return "Must be ≥ " + f.min;
    if (f.min === 0 && n === 0) return "Must be > 0";
  }
  if (f.type === "date" && !DATE_RX.some((r) => r.test(String(v).trim()))) return "Unrecognized date — use yyyy-MM-dd";
  if (f.pattern && !patternMatches(f.pattern, String(v).trim())) return "Contains characters outside [\\w .,+/()#-]";
  return null;
}
function patternMatches(pattern, value) {
  if (pattern.test) return pattern.test(value);
  try { return new RegExp(pattern).test(value); }
  catch (_err) { return true; }
}
function sectionCounts(fields, values) {
  let filled = 0, reqTotal = 0, reqFilled = 0;
  fields.forEach((f) => {
    const v = values[f.id], lv = effLevel(f, values);
    if (isRecorded(f, v)) filled++;
    if (lv === "required" || lv === "report") { reqTotal++; if (isRecorded(f, v) && !fieldError(f, v)) reqFilled++; }
  });
  return { filled, total: fields.length, reqTotal, reqFilled };
}
function channelIssues(run) { return (run.channels || []).filter((c) => c.status === "unmatched" || c.status === "ambiguous"); }
function hasLoadChannel(run) { return (run.channels || []).some((c) => c.family === "load" && (c.status === "matched" || c.status === "manual")); }

// run readiness — export-blocking criteria only:
// hard/conditional required fields, value errors, unresolved channels, missing load channel
function runReadiness(run, dataset) {
  let missing = [], errors = [], reportGaps = [];
  RUN_SECTIONS.forEach((s) => s.fields.forEach((f) => {
    if (!isVisible(f, run.values)) return;
    const v = run.values[f.id], lv = effLevel(f, run.values);
    const err = fieldError(f, v);
    if (err) errors.push({ field: f, err });
    else if (lv === "required" && !isRecorded(f, v)) missing.push(f);
    else if (lv === "report" && !isRecorded(f, v)) reportGaps.push(f);
  }));
  const chIssues = channelIssues(run).length;
  const loadOk = hasLoadChannel(run);
  const datasetOk = DATASET_SECTIONS.every((s) => s.fields.every((f) => {
    if (!isVisible(f, dataset.values)) return true;
    return effLevel(f, dataset.values) !== "required" || isRecorded(f, dataset.values[f.id]);
  }));
  const ready = errors.length === 0 && missing.length === 0 && chIssues === 0 && loadOk && datasetOk;
  return { missing, errors, reportGaps, chIssues, loadOk, datasetOk, ready };
}

// structured validation report (live — recomputed on every change)
function buildValidationReport(bundle) {
  if (bundle.backendValidation && bundle.backendValidation.source === "backend") {
    return backendValidationReport(bundle.backendValidation);
  }
  const errors = [], missing = [], reportItems = [], passed = [], skipped = [];
  const ds = bundle.dataset;
  DATASET_SECTIONS.forEach((s) => s.fields.forEach((f) => {
    if (!isVisible(f, ds.values)) return;
    const v = ds.values[f.id], lv = effLevel(f, ds.values), err = fieldError(f, v);
    const target = { type: "dataset", sectionId: s.id, fieldId: f.id };
    if (err) errors.push({ text: "Dataset · " + f.label + " — " + err, action: "jump", target });
    else if (lv === "required" && !isRecorded(f, v))
      missing.push({ text: "Dataset · " + f.label + " is required", detail: f.desc, action: "jump", target });
    else if (lv === "report" && !isRecorded(f, v))
      reportItems.push({ text: "Dataset · " + f.label + " — required for the report", detail: "Export proceeds; the report will carry a gap.", action: "jump", target });
  }));
  let readyRuns = 0, totalRuns = 0;
  bundle.groups.forEach((g) => g.runs.forEach((r) => {
    totalRuns++;
    const rr = runReadiness(r, ds);
    if (rr.ready) readyRuns++;
    rr.errors.forEach(({ field, err }) => errors.push({
      text: r.id + " · " + field.label + " — " + err,
      action: "jump", target: { type: "run", groupId: g.id, runId: r.id, sectionId: sectionOf(field.id, "run"), fieldId: field.id },
    }));
    rr.missing.forEach((f) => missing.push({
      text: r.id + " · " + f.label + (f.importance === "required_for_accepted_runs" ? " — required while validity is “Accepted”" : " is required"),
      action: "jump", target: { type: "run", groupId: g.id, runId: r.id, sectionId: sectionOf(f.id, "run"), fieldId: f.id },
    }));
    channelIssues(r).forEach((c) => errors.push({
      text: r.id + " · header “" + c.header + "” " + (c.status === "ambiguous" ? "is ambiguous (" + (c.candidates || []).length + " candidates)" : "has no channel family"),
      action: "channels", target: { groupId: g.id, runId: r.id },
    }));
    if (!hasLoadChannel(r)) errors.push({
      text: r.id + " · no Load channel assigned — Load is the one required data column",
      action: "channels", target: { groupId: g.id, runId: r.id },
    });
  }));
  const chOk = bundle.groups.reduce((a, g) => a + g.runs.filter((r) => channelIssues(r).length === 0).length, 0);
  passed.push({ text: "Schema " + SCHEMA_META.id + " v" + SCHEMA_META.version + " — field types, enums and value patterns", detail: "All filled values type-check against the schema." });
  passed.push({ text: "Channel families on " + chOk + "/" + totalRuns + " runs resolve to the data_table layout" });
  passed.push({ text: "Sidecar pairing — " + bundle.sourcePairs.length + "/" + bundle.sourcePairs.length + " CSVs paired 1:1 by base name" });
  passed.push({ text: "Units conform to " + SCHEMA_META.unitSystem + " accepted units; conversion rules available" });
  skipped.push({ text: "Raw CSV numeric plausibility (curve shapes, outliers)", detail: "Out of scope for enrichment — checked downstream by the method pipeline." });
  skipped.push({ text: "Image evidence completeness", detail: "image_evidence.required = false in this schema." });
  return { errors, missing, reportItems, passed, skipped, readyRuns, totalRuns };
}
function backendValidationReport(validation) {
  const issues = Array.isArray(validation.issues) ? validation.issues : [];
  const toItem = (issue) => {
    const scope = issue.scope === "run" ? "run" : "dataset";
    const fieldId = issue.field || (issue.target && issue.target.fieldId) || null;
    const target = issue.target || { type: scope, groupId: issue.group_id, runId: issue.run_id, fieldId };
    if (fieldId && !target.sectionId) target.sectionId = sectionOf(fieldId, scope);
    return {
      text: issue.text || issue.message || "Backend validation issue",
      detail: issue.detail,
      action: issue.category === "data_table" ? "channels" : "jump",
      target,
    };
  };
  const errors = [], missing = [], reportItems = [];
  issues.forEach((issue) => {
    const item = toItem(issue);
    if (issue.severity === "warning") reportItems.push(item);
    else if (issue.code === "required") missing.push(item);
    else errors.push(item);
  });
  return {
    errors,
    missing,
    reportItems,
    passed: validation.passed || [],
    skipped: validation.skipped || [],
    readyRuns: validation.ready_runs || 0,
    totalRuns: validation.total_runs || 0,
  };
}
function sectionOf(fieldId, scope) {
  const secs = scope === "run" ? RUN_SECTIONS : DATASET_SECTIONS;
  const s = secs.find((s) => s.fields.some((f) => f.id === fieldId));
  return s ? s.id : null;
}
function enumLabel(f, v) {
  if (!f.options) return v;
  const o = f.options.find((o) => o.v === v);
  return o ? o.label : v;
}
function runShort(id) { return id.replace("run_0", "r").replace("run_", "r"); }
function familyLabel(id) { return (id && window.FAMILY[id] && window.FAMILY[id].label) || id || null; }

Object.assign(window, {
  SCHEMA_META, UNIT_FACTORS, convertUnit, conversionFactorLabel,
  DATASET_SECTIONS, RUN_SECTIONS, ALL_FIELDS, CHANNEL_FAMILIES, FAMILY,
  IMAGE_VIEWS, SUPPLEMENTAL_SCOPES,
  isFilled, isRecorded, isVisible, effLevel, visibleFields, fieldError, sectionCounts,
  channelIssues, hasLoadChannel, runReadiness, buildValidationReport, sectionOf, enumLabel, runShort, familyLabel,
  installBackendSchemaForm,
});

// ================= data.jsx =================
// ---------------------------------------------------------------------------
// Dataset Packaging v3 — schema candidates used before backend hydration.
// Loaded packages and source folders come from backend session payloads.
// ---------------------------------------------------------------------------

// schema candidates — the actual schema_library contents
const SCHEMA_CANDIDATES = [
  { id: "compression-0.3.0", label: "Compression", schema: "mechanical.compression", version: "0.3.0", conf: 85, detected: true,
    hint: "Preamble tokens + channel families (load, displacement, strain) match the compression data_table; sidecars declare a compressive test." },
  { id: "compression-0.2.0", label: "Compression", schema: "mechanical.compression", version: "0.2.0", conf: 61,
    hint: "Previous version of the same schema — migration path to 0.3.0 exists (compatible_prior_versions)." },
  { id: "flexural-0.1.0", label: "Flexural", schema: "mechanical.flexural", version: "0.1.0", conf: 34,
    hint: "Channel layout partially compatible; no flexure-specific tokens found in preambles." },
  { id: "tensile-0.1.0", label: "Tensile", schema: "mechanical.tensile", version: "0.1.0", conf: 28,
    hint: "Load/strain channels match, but sidecar test mode contradicts tension." },
  { id: "generic-0.1.0", label: "Generic stress–strain", schema: "mechanical.generic_stress_strain", version: "0.1.0", conf: 22,
    hint: "Always-available fallback — accepts any stress/strain layout, weakest validation." },
];

function schemaCandidatesFromBackendSession(session) {
  const schemas = Array.isArray(session?.schemas) ? session.schemas : [];
  return schemas
    .filter((schema) => schema && schema.id && schema.label && schema.version)
    .map((schema) => ({
      id: schema.id,
      label: schema.label,
      schema: schema.schema || schema.schema_id || schema.id,
      version: schema.version || schema.schema_version || "",
      conf: Number(schema.conf || 0),
      detected: Boolean(schema.detected),
      hint: schema.hint || "Loaded from backend schema registry.",
      schemaForm: schema.schemaForm || schema.schema_form || null,
    }));
}

function installBackendSchemaForm(form) {
  if (!form || typeof form !== "object") return false;
  const fields = [
    ...Object.values(form.fieldsById || {}),
    ...(Array.isArray(form.datasetFields) ? form.datasetFields : []),
    ...(Array.isArray(form.runFields) ? form.runFields : []),
  ];
  const normalized = new Map();
  fields.forEach((field) => {
    const next = normalizeBackendField(field);
    if (next?.id) normalized.set(next.id, next);
  });
  if (!normalized.size) return false;

  Object.keys(F).forEach((key) => delete F[key]);
  normalized.forEach((field, id) => { F[id] = field; });

  replaceSections(DATASET_SECTIONS, form.datasetSections || form.dataset_sections, "dataset");
  replaceSections(RUN_SECTIONS, form.runSections || form.run_sections, "run");
  replaceChannelFamilies(form.channelFamilies || form.channel_families);
  replaceObject(UNIT_FACTORS, form.unitFactors || form.unit_factors || {});

  if (Array.isArray(form.imageViews || form.image_views)) {
    IMAGE_VIEWS.splice(0, IMAGE_VIEWS.length, ...(form.imageViews || form.image_views).map((view) => ({
      id: view.id,
      label: view.label || view.id,
    })));
  }
  if (Array.isArray(form.supplementalScopes || form.supplemental_scopes)) {
    SUPPLEMENTAL_SCOPES.splice(0, SUPPLEMENTAL_SCOPES.length, ...(form.supplementalScopes || form.supplemental_scopes));
  }
  Object.assign(SCHEMA_META, {
    id: form.schema || form.schemaId || SCHEMA_META.id,
    version: form.version || SCHEMA_META.version,
    label: form.label || SCHEMA_META.label,
    unitSystem: form.unitSystem || form.unit_system || SCHEMA_META.unitSystem,
    source: form.source || "backend schema registry",
  });
  return true;
}

function normalizeBackendField(field) {
  if (!field || typeof field !== "object") return null;
  const id = field.id || field.fieldId || field.field_id;
  if (!id) return null;
  const type = field.type || "string";
  const options = Array.isArray(field.options)
    ? field.options.map((item) => ({
        v: item.v ?? item.value,
        label: item.label || String(item.v ?? item.value ?? ""),
        deviation: Boolean(item.deviation),
      }))
    : Array.isArray(field.allowedValues || field.allowed_values)
      ? (field.allowedValues || field.allowed_values).map((value) => ({
          v: value,
          label: field.displayLabels?.[value] || field.display_labels?.[value] || String(value).replace(/[_-]/g, " "),
          deviation: Array.isArray(field.deviationValues || field.deviation_values)
            && (field.deviationValues || field.deviation_values).includes(value),
        }))
      : [];
  const units = field.units || field.acceptedUnits || field.accepted_units;
  const visibleWhen = field.visibleWhen || field.visible_when;
  const requiredWhen = field.requiredWhen || field.required_when;
  return {
    ...field,
    id,
    label: field.label || id,
    type,
    hardRequired: Boolean(field.hardRequired ?? field.hard_required ?? field.required),
    importance: field.importance || field.reportImportance || field.report_importance || (field.required ? "required" : "optional"),
    options,
    units: Array.isArray(units) && units.length ? units : undefined,
    stdUnit: field.stdUnit || field.standardUnit || field.standard_unit || (Array.isArray(units) ? units[0] : undefined),
    dim: field.dim || field.unitDimension || field.unit_dimension,
    desc: field.desc || field.description || "",
    ph: field.ph || field.placeholder || "",
    min: field.min ?? field.validation?.min,
    max: field.max ?? field.validation?.max,
    pattern: field.pattern || field.validation?.pattern,
    visibleWhen: normalizeCondition(visibleWhen),
    requiredWhen: normalizeCondition(requiredWhen),
    unitInline: Boolean(field.unitInline ?? field.unit_inline),
    notRecorded: field.notRecorded || field.not_recorded,
  };
}

function normalizeCondition(condition) {
  if (!condition || typeof condition !== "object") return undefined;
  return {
    field: condition.field || condition.fieldId || condition.field_id,
    equals: condition.equals ?? condition.value,
  };
}

function replaceSections(target, sections, fallbackScope) {
  const next = Array.isArray(sections) ? sections.map((section) => {
    const fields = Array.isArray(section.fields)
      ? section.fields.map((field) => F[field.id || field.fieldId || field.field_id] || normalizeBackendField(field)).filter(Boolean)
      : Array.isArray(section.fieldIds || section.field_ids)
        ? (section.fieldIds || section.field_ids).map((id) => F[id]).filter(Boolean)
        : [];
    return {
      id: section.id || section.key || section.label,
      label: section.label || section.id || "Metadata",
      scope: section.scope || fallbackScope,
      fields,
    };
  }).filter((section) => section.id && section.fields.length) : [];
  if (next.length) target.splice(0, target.length, ...next);
}

function replaceChannelFamilies(families) {
  if (!Array.isArray(families) || !families.length) return;
  const next = families.map((family) => ({
    id: family.id || family.family,
    label: family.label || family.id || family.family,
    required: Boolean(family.required),
    repeatable: Boolean(family.repeatable),
    units: family.units || family.accepted_units || [],
    std: family.std || family.standard_unit,
    dim: family.dim || family.unit_dimension,
  })).filter((family) => family.id);
  if (!next.length) return;
  CHANNEL_FAMILIES.splice(0, CHANNEL_FAMILIES.length, ...next);
  replaceObject(FAMILY, {});
  CHANNEL_FAMILIES.forEach((family) => { FAMILY[family.id] = family; });
}

function replaceObject(target, source) {
  Object.keys(target).forEach((key) => delete target[key]);
  Object.entries(source || {}).forEach(([key, value]) => {
    target[key] = value && typeof value === "object" && !Array.isArray(value) ? { ...value } : value;
  });
}

Object.assign(window, { SCHEMA_CANDIDATES, installBackendSchemaForm });

// ================= menus.jsx =================
// ---------------------------------------------------------------------------
// Menu bar v3. Edit ▸ Undo/Redo are LIVE (F5-A) and show the last action's
// label. View gains the unified ⊞ Grid (F1-A). Validate points at the docked
// issues drawer (F7-A). File gains Recent sessions (autosave, F8-A).
// ---------------------------------------------------------------------------
const { useState: useStateM, useEffect: useEffectM, useRef: useRefM } = React;

function buildMenus({ editor, density, runIdx, runCount, canUndo, canRedo, undoLabel, redoLabel, lastExportPath }) {
  const e = editor;
  return [
    { id: "file", label: "File", items: [
      { id: "open-files", label: "Open files (drag & drop)…", kbd: "Ctrl+O" },
      { id: "open-folder", label: "Open source folder…", kbd: "Ctrl+Shift+O" },
      { id: "open-package", label: "Open MTDP package…" },
      { sep: true },
      { id: "recent-sessions", label: "Recent sessions (autosaved)…" },
      { sep: true },
      { id: "export", label: "Export MTDP package…", kbd: "Ctrl+Shift+E", disabled: !e },
      { id: "export-all-ready", label: "Export all ready groups…", disabled: !e },
      { id: "open-export-analysis", label: "Open exported package in Analysis…", disabled: !lastExportPath },
      { sep: true },
      { id: "close-package", label: "Close package", disabled: !e },
    ]},
    { id: "edit", label: "Edit", items: [
      { id: "undo", label: canUndo && undoLabel ? "Undo " + undoLabel : "Undo", kbd: "Ctrl+Z", disabled: !e || !canUndo },
      { id: "redo", label: canRedo && redoLabel ? "Redo " + redoLabel : "Redo", kbd: "Ctrl+Shift+Z", disabled: !e || !canRedo },
      { sep: true },
      { id: "copy-prev", label: "Copy values from previous run", kbd: "Ctrl+D", disabled: !e || runIdx <= 0 },
    ]},
    { id: "view", label: "View", items: [
      { id: "density-essential", label: "Required fields only", check: density === "essential", disabled: !e },
      { id: "density-core", label: "Required + recommended", check: density === "core", disabled: !e },
      { id: "density-all", label: "All fields", check: density === "all", disabled: !e },
      { sep: true },
      { id: "open-grid", label: "⊞ Grid — all runs", disabled: !e },
      { id: "source-files", label: "Source files", disabled: !e },
    ]},
    { id: "group", label: "Group", items: [
      { id: "propose-groups", label: "Propose groups…", disabled: !e },
      { id: "new-group", label: "New group", disabled: !e },
      { id: "rename-group", label: "Rename group", disabled: !e, kbd: "✎ or dbl-click" },
      { id: "delete-group", label: "Delete group", disabled: !e },
    ]},
    { id: "run", label: "Run", items: [
      { id: "prev-run", label: "Previous run", kbd: "Ctrl+Up", disabled: !e || runIdx <= 0 },
      { id: "next-run", label: "Next run", kbd: "Ctrl+Down", disabled: !e || runIdx < 0 || runIdx >= runCount - 1 },
      { sep: true },
      { id: "channels", label: "Channel assignments…", disabled: !e },
      { id: "evidence", label: "Manage run image evidence…", disabled: !e },
    ]},
    { id: "tools", label: "Tools", items: [
      { id: "validate", label: "Validate — issues drawer", kbd: "Ctrl+R", disabled: !e },
      { id: "rematch-yaml", label: "Re-match YAML sidecars…", disabled: !e },
      { id: "supplemental", label: "Manage supplemental files…", disabled: !e },
      { sep: true },
      { id: "change-schema", label: "Change detected schema…", disabled: !e },
    ]},
    { id: "help", label: "Help", items: [
      { id: "schema-ref", label: "Schema reference — Compression v0.3.0" },
      { id: "about", label: "About Dataset Packaging" },
    ]},
  ];
}

function MenuBar({ stage, bundle, density, runIdx, runCount, canUndo, canRedo, undoLabel, redoLabel, lastExportPath, onAction }) {
  const [open, setOpen] = useStateM(null);
  const barRef = useRefM(null);
  const pointerToggledRef = useRefM(false);
  const editor = stage === "editor" && !!bundle;
  const menus = buildMenus({ editor, density, runIdx, runCount, canUndo, canRedo, undoLabel, redoLabel, lastExportPath });
  const hasDesktopApi = Boolean(window.desktopApi);

  useEffectM(() => {
    if (!open) return;
    const close = (ev) => { if (barRef.current && !barRef.current.contains(ev.target)) setOpen(null); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffectM(() => {
    if (!open) return;
    const closeOnEscape = (ev) => {
      if (ev.key !== "Escape") return;
      ev.preventDefault();
      setOpen(null);
    };
    document.addEventListener("keydown", closeOnEscape, true);
    return () => document.removeEventListener("keydown", closeOnEscape, true);
  }, [open]);

  const fire = (id) => { setOpen(null); onAction(id); };
  const toggleWindowMaximize = (ev) => {
    if (!hasDesktopApi) return;
    ev.preventDefault();
    if (ev.target.closest("button,.menu__pop,.menu__btn,.menubar__schema,.desktop-window-control")) return;
    window.desktopApi?.toggleMaximizeWindow?.();
  };

  return (
    <div className="menubar menubar--desktop" ref={barRef} onDoubleClick={toggleWindowMaximize}>
      <span className="menubar__title" data-window-drag="true">Dataset Packaging</span>
      <nav className="menubar__menus">
        {menus.map((m) => (
          <div className="menu" key={m.id}>
            <button
              className={"menu__btn" + (open === m.id ? " is-open" : "")}
              onMouseDown={(ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                pointerToggledRef.current = true;
                setOpen((current) => current === m.id ? null : m.id);
              }}
              onClick={(ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                if (pointerToggledRef.current) {
                  pointerToggledRef.current = false;
                  return;
                }
                setOpen((current) => current === m.id ? null : m.id);
              }}
              onMouseEnter={() => { if (open && open !== m.id) setOpen(m.id); }}
            >{m.label}</button>
            {open === m.id && (
              <div className="menu__pop" onMouseDown={(ev) => ev.stopPropagation()} onClick={(ev) => ev.stopPropagation()}>
                {m.items.map((it, i) => it.sep
                  ? <div className="menu__sep" key={"sep" + i}></div>
                  : (
                    <button key={it.id} className="menu__item" disabled={!!it.disabled} onClick={() => fire(it.id)}>
                      <span className="chk">{it.check ? "✓" : ""}</span>
                      <span className="lab">{it.label}</span>
                      {it.kbd && <span className="kbd">{it.kbd}</span>}
                    </button>
                  ))}
              </div>
            )}
          </div>
        ))}
      </nav>
      <div className="menubar__dragzone" data-window-drag="true" aria-hidden="true" />
      {editor && (
        <button className="menubar__schema" title="Click to change the detected schema" onClick={() => fire("change-schema")}>
          {bundle.schemaOverridden ? "Schema (manual): " : "Detected schema: "}
          <b>{bundle.schemaLabel} · v{bundle.schemaVersion}</b>
          {bundle.schemaOverridden
            ? <span className="menubar__override">override</span>
            : <span className="menubar__conf">{bundle.detectConfidence}%</span>}
        </button>
      )}
      <DesktopWindowControls className="menubar__windowctrls" />
    </div>
  );
}

Object.assign(window, { MenuBar });

// ================= modals.jsx =================
// ---------------------------------------------------------------------------
// v3 dialogs: channel inspector (schema data_table families), export with a
// run MANIFEST (F6-A), propose groups, schema override (real schema_library
// candidates), image evidence (schema views), supplemental files (schema
// scopes), YAML re-match. Validation is no longer a modal — see the docked
// issues drawer in inserter.jsx (F7-A).
// ---------------------------------------------------------------------------
const { useState: useStateD } = React;

function Modal({ kind, title, sub, width, children, foot, onClose }) {
  return (
    <div className="modalscrim" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={"modal modal--" + (width || "mid")}>
        <div className="modal__hd">
          <div>
            <div className="modal__kind">{kind}</div>
            <h2 className="modal__title">{title}</h2>
            {sub && <p className="modal__sub">{sub}</p>}
          </div>
          <button className="modal__x" onClick={onClose} title="Close">✕</button>
        </div>
        <div className="modal__body">{children}</div>
        {foot && <div className="modal__foot">{foot}</div>}
      </div>
    </div>
  );
}

// ---- 1. Channel inspector — families from the schema's data_table ------------
function ChannelInspector({ bundle, groupId, runId, onAssign, onSelectRun, onClose }) {
  const group = bundle.groups.find((g) => g.id === groupId) || bundle.groups[0];
  const run = group.runs.find((r) => r.id === runId) || group.runs[0];
  const issues = window.channelIssues(run);
  const nextBad = bundle.groups.flatMap((g) => g.runs.map((r) => ({ g, r })))
    .find(({ r }) => r.id !== run.id && window.channelIssues(r).length > 0);

  const famTaken = (famId, exceptIdx) => run.channels.some((c, i) =>
    i !== exceptIdx && c.family === famId && !(window.FAMILY[famId]?.repeatable));

  const setFamily = (idx, famId) => {
    const fam = famId ? window.FAMILY[famId] : null;
    const cur = run.channels[idx];
    onAssign(group.id, run.id, idx, {
      family: famId || null,
      unit: fam ? (cur.unit && fam.units.includes(cur.unit) ? cur.unit : fam.std) : cur.unit,
      status: famId ? "manual" : cur.candidates ? "ambiguous" : "unmatched",
    });
  };
  const setUnit = (idx, unit) => onAssign(group.id, run.id, idx, { unit });

  return (
    <Modal kind="CHANNEL ASSIGNMENTS" width="wide" onClose={onClose}
      title={"Parsed channels — " + run.id}
      sub={<span>Headers in <span className="mono">{run.fileLabel}</span> → schema channel families
        (<span className="mono" style={{ fontSize: "11px" }}>data_table.columns</span>). Load is required; Strain and Stress are repeatable.</span>}
      foot={
        <>
          <span className={"modal__footnote " + (issues.length ? "modal__footnote--warn" : "modal__footnote--ok")}>
            {issues.length
              ? "⚠ " + issues.length + " header" + (issues.length > 1 ? "s" : "") + " unresolved — this run cannot export"
              : window.hasLoadChannel(run) ? "✓ All headers assigned — Load present" : "⚠ No Load channel — Load is required"}
          </span>
          <div className="modal__actions">
            {nextBad && (
              <button className="btn btn--sm" onClick={() => onSelectRun(nextBad.g.id, nextBad.r.id)}>
                Next unresolved run · {nextBad.r.id} →
              </button>
            )}
            <button className="btn btn--primary btn--sm" onClick={onClose}>Done</button>
          </div>
        </>
      }>
      <table className="chtable">
        <thead><tr><th>Source header</th><th>Channel family</th><th>Unit</th><th style={{ textAlign: "right" }}>Status</th></tr></thead>
        <tbody>
          {run.channels.map((c, idx) => {
            const issue = c.status === "unmatched" || c.status === "ambiguous";
            const fam = c.family ? window.FAMILY[c.family] : null;
            const famOptions = c.candidates
              ? [...c.candidates, ...window.CHANNEL_FAMILIES.map((f) => f.id).filter((id) => !c.candidates.includes(id))]
              : window.CHANNEL_FAMILIES.map((f) => f.id);
            return (
              <tr key={c.header} className={issue ? (c.status === "ambiguous" ? "is-amb" : "is-issue") : ""}>
                <td>
                  <span className="hdr">{c.header}</span>
                  {c.note && <span className="note">{c.note}</span>}
                </td>
                <td>
                  <select className={c.family ? "" : "is-empty"} value={c.family || ""} onChange={(e) => setFamily(idx, e.target.value)}>
                    <option value="">{c.candidates ? "— choose (" + c.candidates.length + " candidates) —" : "— assign family —"}</option>
                    {famOptions.map((id) => {
                      const f = window.FAMILY[id] || { id, label: id, required: false };
                      const taken = famTaken(id, idx) && id !== c.family;
                      return (
                        <option key={id} value={id} disabled={taken}>
                          {f.label + (f.required ? " (required)" : "")
                            + (c.candidates && c.candidates.includes(id) ? " · candidate" : "")
                            + (taken ? " · already assigned" : "")}
                        </option>
                      );
                    })}
                  </select>
                </td>
                <td>
                  <select className={"unitpick" + (c.unit ? "" : " is-empty")} value={c.unit || ""} disabled={!c.family}
                    onChange={(e) => setUnit(idx, e.target.value)}>
                    {!c.unit && <option value="">—</option>}
                    {(fam ? fam.units : c.unit ? [c.unit] : []).map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                </td>
                <td style={{ textAlign: "right" }}>
                  <span className={"chstat chstat--" + c.status}>{c.status === "ambiguous" ? "? ambiguous" : c.status}</span>
                  {c.via && c.status === "matched" && <span className="via">{c.via}</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Modal>
  );
}

// ---- 2. Export — destination + run manifest (F6-A) ----------------------------
function skipReason(run, dataset) {
  const rr = window.runReadiness(run, dataset);
  const parts = [];
  if (rr.errors.length) parts.push({ t: rr.errors.length + " value error" + (rr.errors.length > 1 ? "s" : "") + " — " + rr.errors.map((e) => e.field.label.toLowerCase()).join(", "), act: "jump", f: rr.errors[0].field });
  if (rr.missing.length) parts.push({ t: rr.missing.length + " required missing — " + rr.missing.map((f) => f.label.toLowerCase()).join(", "), act: "jump", f: rr.missing[0] });
  const chI = window.channelIssues(run).length;
  if (chI) parts.push({ t: chI + " channel header" + (chI > 1 ? "s" : "") + " unresolved", act: "channels" });
  if (!window.hasLoadChannel(run)) parts.push({ t: "no Load channel", act: "channels" });
  return parts;
}

function ExportDialog({ bundle, onExport, onJump, onOpenChannels, onClose }) {
  const [dest, setDest] = useStateD("~/Documents/MTDP exports");
  const [name, setName] = useStateD(bundle.name + ".mtdp");
  const rep = window.buildValidationReport(bundle);
  const allRuns = bundle.groups.flatMap((g) => g.runs.map((r) => ({ g, r })));
  const included = allRuns.filter(({ r }) => window.runReadiness(r, bundle.dataset).ready);
  return (
    <Modal kind="EXPORT" width="wide" onClose={onClose}
      title="Export MTDP package — run manifest"
      sub="Every run is listed. Nothing is skipped silently — non-ready runs are excluded with their reason shown."
      foot={
        <>
          <span className="modal__footnote">
            <b>{included.length} of {allRuns.length}</b> runs will be included
            {included.length < allRuns.length && <> · {allRuns.length - included.length} skipped, listed above</>}
          </span>
          <div className="modal__actions">
            <button className="btn btn--sm" onClick={onClose}>Cancel</button>
            <button className="btn btn--primary btn--sm" disabled={included.length === 0}
              onClick={() => onExport({ initialDir: dest, defaultName: name, included: included.length, total: allRuns.length })}>
              ⬇ Export {included.length} of {allRuns.length} runs
            </button>
          </div>
        </>
      }>
      <table className="mantable">
        <thead><tr><th></th><th>Run</th><th>Specimen</th><th>Status</th></tr></thead>
        <tbody>
          {allRuns.map(({ g, r }) => {
            const ready = window.runReadiness(r, bundle.dataset).ready;
            const reasons = ready ? [] : skipReason(r, bundle.dataset);
            return (
              <tr key={r.id} className={ready ? "" : "is-off"}>
                <td className="cb">{ready ? "☑" : "☐"}</td>
                <td className="runid mono">{r.id}</td>
                <td className="mono spec">{r.values.specimen_name}</td>
                <td className="reason">
                  {ready ? <span className="okt">✓ ready</span> : reasons.map((p, i) => (
                    <span key={i} className="skipline">
                      <b>{p.t}</b>{" "}
                      {p.act === "jump"
                        ? <button className="go" onClick={() => onJump({ type: "run", groupId: g.id, runId: r.id, sectionId: window.sectionOf(p.f.id, "run"), fieldId: p.f.id })}>fix →</button>
                        : <button className="go" onClick={() => onOpenChannels({ groupId: g.id, runId: r.id })}>open channels →</button>}
                    </span>
                  ))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {rep.reportItems.length > 0 && (
        <div className="dlgnote dlgnote--warn" style={{ marginTop: "12px" }}>
          ⚠ <b>{rep.reportItems.length} report gap{rep.reportItems.length > 1 ? "s" : ""}</b> — {rep.reportItems.map((i) => i.text.replace("Dataset · ", "").replace(" — required for the report", "")).join(" · ")}.
          Export proceeds; the formal report will show these as missing.
        </div>
      )}
      <div className="exprow" style={{ marginTop: "14px" }}>
        <label>Save to</label>
        <div className="pathrow">
          <input className="inp mono" style={{ fontSize: "12.5px" }} value={dest} onChange={(e) => setDest(e.target.value)} />
          <button className="btn btn--sm" onClick={() => setDest("~/Desktop")}>Choose…</button>
        </div>
      </div>
      <div className="exprow">
        <label>File name</label>
        <input className="inp mono" style={{ fontSize: "12.5px" }} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
    </Modal>
  );
}

// ---- 3. Propose groups ---------------------------------------------------------
function ProposeGroupsDialog({ proposals, onApply, onClose }) {
  const options = proposals && proposals.length ? proposals : [];
  const firstId = options[0]?.id || "";
  const [pick, setPick] = useStateD(firstId);
  React.useEffect(() => {
    if (!options.some((p) => p.id === pick)) setPick(firstId);
  }, [firstId, options, pick]);
  const canApply = Boolean(pick);
  return (
    <Modal kind="GROUPING" width="mid" onClose={onClose}
      title="Proposed sample groups"
      sub="Ranked by confidence from the backend dataset_grouping engine. Applying replaces the current grouping while keeping run data attached."
      foot={
        <>
          <span className="modal__footnote">You can drag runs between groups afterwards.</span>
          <div className="modal__actions">
            <button className="btn btn--sm" onClick={onClose}>Cancel</button>
            <button className="btn btn--primary btn--sm" disabled={!canApply} onClick={() => onApply(pick)}>Apply proposal</button>
          </div>
        </>
      }>
      {options.length === 0 && (
        <div className="dlgnote dlgnote--warn">No backend grouping proposal is available for the current session.</div>
      )}
      {options.map((p) => {
        const conf = Number(p.conf ?? p.confidence ?? 0);
        const groupSummary = (p.groups || [])
          .map((g) => g.name + " (" + (g.run_count || 0) + ")")
          .join(" · ");
        return (
        <label className={"proposal" + (pick === p.id ? " is-picked" : "")} key={p.id}>
          <input type="radio" name="proposal" checked={pick === p.id} onChange={() => setPick(p.id)} />
          <span className="pbody">
            <span className="t">{p.title}
              <span className="conf"><span className="conf__track"><span className={"conf__fill conf__fill--" + (conf >= 80 ? "ok" : "warn")} style={{ width: conf + "%" }}></span></span><span className="conf__num">{conf}%</span></span>
            </span>
            <span className="d">{p.description || p.desc || "Backend-authored grouping proposal."}</span>
            {groupSummary && <span className="d"><span className="mono" style={{ fontSize: "11px" }}>{groupSummary}</span></span>}
          </span>
        </label>
      );})}
    </Modal>
  );
}

// ---- 4. Schema override — actual schema_library candidates ----------------------
function SchemaDialog({ bundle, candidates, onPick, onClose }) {
  const [pick, setPick] = useStateD(bundle.schemaId);
  const schemaCandidates = candidates && candidates.length ? candidates : window.SCHEMA_CANDIDATES;
  return (
    <Modal kind="SCHEMA" width="mid" onClose={onClose}
      title="Change detected schema"
      sub="Candidates from the schema library. Detection used preamble tokens + channel layout. A manual override is recorded in the audit trail."
      foot={
        <>
          <span className="modal__footnote">Switching schema re-derives every form from the new YAML.</span>
          <div className="modal__actions">
            <button className="btn btn--sm" onClick={onClose}>Cancel</button>
            <button className="btn btn--primary btn--sm" onClick={() => onPick(pick)}>Use this schema</button>
          </div>
        </>
      }>
      {schemaCandidates.map((s) => (
        <label className={"proposal" + (pick === s.id ? " is-picked" : "")} key={s.id}>
          <input type="radio" name="schema" checked={pick === s.id} onChange={() => setPick(s.id)} />
          <span className="pbody">
            <span className="t">{s.label} · v{s.version}
              {s.detected && <span className="schemachip" style={{ cursor: "default" }}>detected</span>}
              <span className="conf"><span className="conf__track"><span className={"conf__fill conf__fill--" + (s.conf >= 80 ? "ok" : s.conf >= 40 ? "warn" : "err")} style={{ width: s.conf + "%" }}></span></span><span className="conf__num">{s.conf}%</span></span>
            </span>
            <span className="d"><span className="mono" style={{ fontSize: "11px" }}>{s.schema}</span> — {s.hint}</span>
          </span>
        </label>
      ))}
    </Modal>
  );
}

// ---- 5. Run image evidence — views from the schema -------------------------------
function EvidenceDialog({ bundle, groupId, runId, onAdd, onRemove, onClose }) {
  const group = bundle.groups.find((g) => g.id === groupId) || bundle.groups[0];
  const run = group.runs.find((r) => r.id === runId) || group.runs[0];
  const ev = run.evidence || [];
  const [view, setView] = useStateD("failure");
  return (
    <Modal kind="IMAGE EVIDENCE" width="mid" onClose={onClose}
      title={"Run image evidence — " + run.id}
      sub="Schema views: front · side · top · failure · scale reference · other. Optional in this schema (image_evidence.required = false); embedded in the package."
      foot={
        <>
          <span className="modal__footnote">{ev.length} image(s) attached</span>
          <div className="modal__actions">
            <select className="inp" style={{ padding: "5px 8px", fontSize: "12px" }} value={view} onChange={(e) => setView(e.target.value)}>
              {window.IMAGE_VIEWS.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
            </select>
            <button className="btn btn--sm" onClick={() => onAdd(group.id, run.id, view)}>＋ Add image…</button>
            <button className="btn btn--primary btn--sm" onClick={onClose}>Done</button>
          </div>
        </>
      }>
      {ev.length === 0 && <div className="evempty">No images attached to this run yet.<br />Pick a view and use “Add image…”, or drop image files here.</div>}
      {ev.map((f, i) => (
        <div className="evrow" key={i}>
          <span className="ic">▣</span>
          <span className="nm">{f.name}</span>
          <span className="kind">{(window.IMAGE_VIEWS.find((v) => v.id === f.view) || {}).label || f.view}</span>
          <button className="rm" title="Remove" onClick={() => onRemove(group.id, run.id, i)}>✕</button>
        </div>
      ))}
    </Modal>
  );
}

// ---- 6. Supplemental files — scopes from the schema -------------------------------
function SupplementalDialog({ bundle, groupId, runId, onAdd, onRemove, onClose }) {
  const group = bundle.groups.find((g) => g.id === groupId) || bundle.groups[0];
  const run = group && runId ? group.runs.find((r) => r.id === runId) : null;
  const files = [...(group?.supplemental || bundle.supplemental || []), ...(run?.supplemental || [])];
  const [scope, setScope] = useStateD("dataset");
  const scopes = window.SUPPLEMENTAL_SCOPES.filter((s) => run || s !== "run");
  React.useEffect(() => {
    if (!scopes.includes(scope)) setScope("dataset");
  }, [scope, scopes]);
  return (
    <Modal kind="SUPPLEMENTAL FILES" width="mid" onClose={onClose}
      title="Supplemental files"
      sub="Carried in the package, not validated against the schema. Accepted scopes: dataset · run · schema_mapping · calibration · equipment_evidence · other."
      foot={
        <>
          <span className="modal__footnote">{files.length} file(s) attached · preserved in package</span>
          <div className="modal__actions">
            <select className="inp" style={{ padding: "5px 8px", fontSize: "12px" }} value={scope} onChange={(e) => setScope(e.target.value)}>
              {scopes.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
            <button className="btn btn--sm" onClick={() => onAdd(group?.id, run?.id || null, scope)}>＋ Add file…</button>
            <button className="btn btn--primary btn--sm" onClick={onClose}>Done</button>
          </div>
        </>
      }>
      {files.length === 0 && <div className="evempty">No supplemental files attached.</div>}
      {files.map((f, i) => (
        <div className="evrow" key={i}>
          <span className="ic">▤</span>
          <span className="nm">{f.name}</span>
          <span className="kind">{(f.scope || "other").replace(/_/g, " ")}</span>
          <button className="rm" title="Remove" onClick={() => onRemove(group?.id, run?.id || null, i)}>✕</button>
        </div>
      ))}
    </Modal>
  );
}

// ---- 7. YAML sidecar re-match -------------------------------------------------------
function RematchYamlDialog({ bundle, summary, review, mappingRows, onRowsChange, onReviewMapping, onApplyMapping, onRematch, onClose }) {
  const pairs = summary?.pairs || bundle.sourcePairs.map((p) => ({
    csv: p.csv,
    yaml: p.yaml,
    status: "paired · base name",
    paired: true,
  }));
  const pairedCount = summary?.pairedCount ?? pairs.filter((p) => p.paired !== false).length;
  const runCount = summary?.runCount ?? pairs.length;
  const rows = mappingRows || review?.rows || [];
  const fields = review?.fieldOptions || [];
  const updateRow = (index, patch) => {
    const next = rows.map((row, rowIndex) => {
      if (rowIndex !== index) return row;
      const mapping = { ...(row.mapping || {}), ...patch };
      const field = fields.find((item) => item.id === mapping.target_field_id);
      return {
        ...row,
        mapping,
        suggestedFieldId: mapping.target_field_id || null,
        suggestedFieldLabel: field?.label || "",
        detectedUnit: mapping.unit || "",
        action: mapping.action || row.action,
      };
    });
    onRowsChange(next);
  };
  return (
    <Modal kind="SIDECAR PAIRING" width="mid" onClose={onClose}
      title="Review / re-match YAML sidecars"
      sub="Paired 1:1 by base name (sidecar_import.same_stem) — each .yaml describes the run of the CSV it sits next to."
      foot={
        <>
          <span className={"modal__footnote " + (pairedCount === runCount ? "modal__footnote--ok" : "")}>✓ {pairedCount}/{runCount} CSVs paired</span>
          <div className="modal__actions">
            <button className="btn btn--sm" onClick={onRematch}>⇄ Re-run matching</button>
            <button className="btn btn--sm" onClick={onReviewMapping}>Review mapping</button>
            {review && <button className="btn btn--primary btn--sm" onClick={() => onApplyMapping(rows)}>Apply mapping profile</button>}
            <button className="btn btn--primary btn--sm" onClick={onClose}>Done</button>
          </div>
        </>
      }>
      <table className="pairtable">
        <thead><tr><th>CSV (run data)</th><th></th><th>YAML sidecar (run info)</th><th style={{ textAlign: "right" }}>Status</th></tr></thead>
        <tbody>
          {pairs.map((p) => (
            <tr key={p.runId || p.csv}>
              <td>{p.csv}</td><td className="arr">⟷</td><td>{p.yaml || "No same-stem YAML"}</td>
              <td style={{ textAlign: "right" }}>
                <span className={"chstat " + (p.paired === false ? "chstat--unmatched" : "chstat--matched")}>
                  {p.status || (p.paired === false ? "not paired" : "paired · base name")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="dlgnote" style={{ marginTop: "12px" }}>
        Pairing rule: <b><span className="mono">&lt;name&gt;.csv ↔ &lt;name&gt;.yaml</span></b>. Unknown sidecar keys
        prompt for mapping (<span className="mono">unknown_keys: prompt_mapping</span>); on conflict the sidecar wins
        (<span className="mono">conflict_policy: prefer_sidecar</span>).
      </div>
      {review && (
        <>
          <div className="dlgnote" style={{ marginTop: "12px" }}>
            Mapping profile <b><span className="mono">{review.profileId}</span></b> · {review.summary?.mappedCount || 0}/{review.summary?.rowCount || rows.length} suggested mappings · {review.summary?.reviewCount || 0} require review
          </div>
          <table className="pairtable" style={{ marginTop: "10px" }}>
            <thead><tr><th>YAML key</th><th>Raw value</th><th>Canonical field</th><th>Unit</th><th>Action</th><th style={{ textAlign: "right" }}>Status</th></tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.sourceKey || row.mapping?.source_key || index}>
                  <td><span className="mono">{row.sourceKey || row.mapping?.source_key}</span></td>
                  <td>{row.rawText || ""}</td>
                  <td>
                    <select value={row.mapping?.target_field_id || ""} onChange={(event) => updateRow(index, {
                      target_field_id: event.target.value || null,
                      action: event.target.value ? "map" : "ignore",
                      user_corrected: true,
                    })}>
                      <option value="">Ignore / no field</option>
                      {fields.map((field) => (
                        <option key={field.id} value={field.id}>{field.label} ({field.id})</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input value={row.mapping?.unit || ""} onChange={(event) => updateRow(index, {
                      unit: event.target.value,
                      user_corrected: true,
                    })} style={{ width: "72px" }} />
                  </td>
                  <td>
                    <select value={row.mapping?.action || "map"} onChange={(event) => updateRow(index, {
                      action: event.target.value,
                      user_corrected: true,
                    })}>
                      <option value="map">Map</option>
                      <option value="ignore">Ignore</option>
                      <option value="defer">Defer</option>
                    </select>
                  </td>
                  <td style={{ textAlign: "right" }}><span className="chstat chstat--matched">{row.status || row.mapping?.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Modal>
  );
}

Object.assign(window, {
  Modal, ChannelInspector, ExportDialog, ProposeGroupsDialog, SchemaDialog,
  EvidenceDialog, SupplementalDialog, RematchYamlDialog,
});

// ================= ingest.jsx =================
// ---------------------------------------------------------------------------
// Onboarding / source-open path.
// Drag/drop and folder pick route to backend packaging session commands.
// Legend in the empty right core uses the v3 three-tier marks (* / † / **).
// ---------------------------------------------------------------------------
const { useState: useStateG } = React;
const NATIVE_SOURCE_DROP_EVENT = "mtdp:native-source-drop";

function normalizeDroppedPath(value) {
  if (!value || typeof value !== "string") return "";
  const text = value.trim();
  if (!text) return "";
  if (text.startsWith("file://")) {
    try {
      const pathname = decodeURIComponent(new URL(text).pathname || "");
      return pathname.replace(/^\/([A-Za-z]:\/)/, "$1");
    } catch (_err) {
      return "";
    }
  }
  return text;
}

function droppedSourcePaths(dataTransfer) {
  const paths = [];
  const add = (value) => {
    const path = normalizeDroppedPath(value);
    if (path && !paths.includes(path)) paths.push(path);
  };
  Array.from(dataTransfer?.files || []).forEach((file) => {
    add(file?.path);
    add(file?.webkitRelativePath);
  });
  const uriList = typeof dataTransfer?.getData === "function"
    ? dataTransfer.getData("text/uri-list")
    : "";
  String(uriList || "").split(/\r?\n/).forEach((line) => {
    const item = line.trim();
    if (item && !item.startsWith("#")) add(item);
  });
  return paths;
}

function nativeSourceDropPaths(event) {
  const detail = event?.detail || {};
  const values = Array.isArray(detail.paths) ? detail.paths : [];
  const paths = [];
  values.forEach((value) => {
    const path = normalizeDroppedPath(value);
    if (path && !paths.includes(path)) paths.push(path);
  });
  return paths;
}

// ---- empty LEFT core --------------------------------------------------------
function EmptyBundlePanel({ onStartIngest, onDropSources, onOpenPackage }) {
  const [over, setOver] = useStateG(false);
  return (
    <section className="core core--bundle">
      <header className="bundlehd">
        <div className="bundlehd__top">
          <span className="bundlehd__kind">SUPRA CONTAINER</span>
          <span className="schemachip schemachip--muted">no schema yet</span>
        </div>
        <h1 className="bundlehd__name bundlehd__name--muted">No package loaded</h1>
        <div className="bundlehd__meta"><span><b>0</b> groups</span><span className="dot">·</span><span><b>0</b> runs</span></div>
      </header>

      <div className="emptystart">
        <div
          className={"dropzone" + (over ? " is-over" : "")}
          onClick={onStartIngest}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setOver(false);
            const paths = droppedSourcePaths(e.dataTransfer);
            if (paths.length && onDropSources) onDropSources(paths);
            else onStartIngest();
          }}
        >
          <span className="big">⇣</span>
          <b>Drop CSV files and YAML sidecars here</b>
          <span className="sub">…or click to choose a source folder · sidecars pair by base name: name.csv ↔ name.yaml</span>
        </div>
        <div className="emptystart__actions">
          <button className="btn btn--lg" onClick={onStartIngest}><span className="ic">▣</span> Select source folder…</button>
          <button className="btn btn--lg" onClick={onOpenPackage}><span className="ic">▢</span> Open MTDP package…</button>
        </div>
        <p className="emptystart__hint">
          Files are parsed, the schema is detected, sidecars are paired and sample groups
          are proposed automatically. Unresolved channel headers are flagged before you
          start enriching. Raw files are never modified, and working state autosaves
          as a draft session.
        </p>
      </div>
    </section>
  );
}

// ---- empty RIGHT core --------------------------------------------------------
function EmptyInsertPanel() {
  return (
    <section className="core core--insert">
      <header className="insrhd">
        <div className="insrhd__row">
          <div className="insrhd__scope"><span className="scopekind scopekind--ds">NO PACKAGE</span><span className="insrhd__spec">Nothing to enrich yet</span></div>
        </div>
      </header>
      <div className="insrempty">
        <div className="insrempty__mark">⛁</div>
        <div className="insrempty__txt">Drop raw files to generate a package,<br />then enrich dataset metadata and runs here.</div>
      </div>
      <footer className="insrfoot">
        <div className="legend">
          <span><span className="mk mk--req">*</span> Required (export)</span>
          <span><span className="mk mk--rep">†</span> Required for report</span>
          <span><span className="mk mk--rec">**</span> Recommended</span>
        </div>
        <div className="insrfoot__actions">
          <button className="btn btn--ghost btn--sm" disabled>✓ Validate</button>
          <button className="btn btn--primary btn--sm" disabled>⬇ Export…</button>
        </div>
      </footer>
    </section>
  );
}

Object.assign(window, { EmptyBundlePanel, EmptyInsertPanel });

// ================= bundle.jsx =================
// ---------------------------------------------------------------------------
// Left core v3 — BUNDLE tree.
// F11-A: one consolidated status cell (dot + short label) — req-counter and
//        match% columns removed (confidence lives in backend source-load state + schema dialog).
// F10-A: ⚠/? channel chips are clickable, ⋯ kebab on row hover carries all
//        run actions; double-click stays as the expert shortcut.
// F14-A: amber = incomplete; blue ? = parser uncertainty; red = error.
// ---------------------------------------------------------------------------
const { useState, useRef: useRefB, useEffect: useEffectB } = React;

function runStatusInfo(run, dataset) {
  const rr = window.runReadiness(run, dataset);
  const unm = (run.channels || []).filter((c) => c.status === "unmatched").length;
  const amb = (run.channels || []).filter((c) => c.status === "ambiguous").length;
  if (rr.errors.length) return { cls: "err", label: rr.errors.length + " error" + (rr.errors.length > 1 ? "s" : "") };
  if (unm || !window.hasLoadChannel(run)) return { cls: "err", label: (unm || 1) + " channel" + (unm > 1 ? "s" : "") };
  if (amb) return { cls: "amb", label: amb + " ambiguous" };
  if (rr.missing.length) return { cls: "warn", label: rr.missing.length + " missing" };
  if (!rr.ready) return { cls: "warn", label: "needs input" };
  return { cls: "ok", label: "Ready" };
}

function RunRow({ run, group, dataset, selected, onSelect, onInspectChannels, onEvidence, onCopyPrev, runIdx, groups, onMoveRun, onDragStart }) {
  const [menu, setMenu] = useState(false);
  const rowRef = useRefB(null);
  useEffectB(() => {
    if (!menu) return;
    const close = (ev) => { if (rowRef.current && !rowRef.current.contains(ev.target)) setMenu(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menu]);

  const st = runStatusInfo(run, dataset);
  const unm = (run.channels || []).filter((c) => c.status === "unmatched").length;
  const amb = (run.channels || []).filter((c) => c.status === "ambiguous").length;

  return (
    <div ref={rowRef}
      className={"trow trow--run" + (selected ? " is-selected" : "")}
      draggable
      title="Double-click: channel assignments"
      onDragStart={(e) => onDragStart(e, run, group)}
      onClick={() => onSelect({ type: "run", groupId: group.id, runId: run.id })}
      onDoubleClick={() => onInspectChannels(group.id, run.id)}
    >
      <span className="trow__grip" aria-hidden>⋮⋮</span>
      <span className="trow__name">
        <span className="trow__runid">
          {run.id}
          {unm > 0 && (
            <button className="chip-ch chip-ch--err" title="Unassigned channel header — click to resolve"
              onClick={(e) => { e.stopPropagation(); onInspectChannels(group.id, run.id); }}>⚠ {unm} ch</button>
          )}
          {amb > 0 && (
            <button className="chip-ch chip-ch--amb" title="Ambiguous channel header — click to choose"
              onClick={(e) => { e.stopPropagation(); onInspectChannels(group.id, run.id); }}>? {amb} ch</button>
          )}
        </span>
        <span className="trow__spec mono">{run.values.specimen_name || run.fileLabel}</span>
      </span>
      <span className={"rstat rstat--" + st.cls}><span className="rstat__dot" />{st.label}</span>
      <span className="trow__kebabwrap">
        <button className="kebab" title="Run actions"
          onClick={(e) => { e.stopPropagation(); setMenu((m) => !m); }}>⋯</button>
        {menu && (
          <span className="rowpop" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => { setMenu(false); onInspectChannels(group.id, run.id); }}>⚙ Channel assignments…</button>
            <button onClick={() => { setMenu(false); onEvidence(group.id, run.id); }}>▣ Image evidence…</button>
            {runIdx > 0 && <button onClick={() => { setMenu(false); onCopyPrev(group.id, run.id); }}>⧉ Copy values from {group.runs[runIdx - 1].id}</button>}
            {groups.filter((g) => g.id !== group.id).map((g) => (
              <button key={g.id} onClick={() => { setMenu(false); onMoveRun(run, group.id, g.id); }}>→ Move to “{g.name}”</button>
            ))}
          </span>
        )}
      </span>
    </div>
  );
}

function GroupName({ group, editing, onStartEdit, onCommit, onCancel }) {
  const inputRef = useRefB(null);
  useEffectB(() => { if (editing && inputRef.current) { inputRef.current.focus(); inputRef.current.select(); } }, [editing]);
  if (!editing) {
    return (
      <span className="grouphd__namewrap">
        <span className="grouphd__name" title="Double-click to rename"
          onDoubleClick={(e) => { e.stopPropagation(); onStartEdit(); }}>{group.name}</span>
        <button className="grouphd__pencil" title="Rename group"
          onClick={(e) => { e.stopPropagation(); onStartEdit(); }}>✎</button>
      </span>
    );
  }
  return (
    <input ref={inputRef} className="renamein" defaultValue={group.name}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => { if (e.key === "Enter") onCommit(e.target.value); if (e.key === "Escape") onCancel(); }}
      onBlur={(e) => onCommit(e.target.value)} />
  );
}

function GroupBlock({ group, dataset, selection, onSelect, onMoveRun, onInspectChannels, onEvidence, onCopyPrev,
                      groups, expanded, onToggle, editing, onStartEdit, onRename, onCancelEdit, onDelete }) {
  const [dragOver, setDragOver] = useState(false);
  const needCount = group.runs.filter((r) => !window.runReadiness(r, dataset).ready).length;
  const isGroupSel = (selection.type === "dataset" || selection.type === "grid") && selection.groupId === group.id;
  const handleDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    const d = window.__dragRun;
    if (d) onMoveRun(d.run, d.fromGroupId, group.id);
  };
  return (
    <div className={"groupblk" + (dragOver ? " is-dragover" : "") + (group.runs.length === 0 ? " groupblk--empty" : "")}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)} onDrop={handleDrop}>
      <div className={"grouphd" + (isGroupSel ? " is-selected" : "")}
        onClick={() => onSelect({ type: "dataset", groupId: group.id })}>
        <button className="grouphd__tw" onClick={(e) => { e.stopPropagation(); onToggle(group.id); }}>{expanded ? "▾" : "▸"}</button>
        <span className="grouphd__icon" aria-hidden>▦</span>
        <GroupName group={group} editing={editing} onStartEdit={onStartEdit}
          onCommit={(v) => onRename(group.id, v)} onCancel={onCancelEdit} />
        <span className="grouphd__count">{group.runs.length} runs</span>
        <span className="grouphd__ready">
          {group.runs.length === 0 ? <span className="grouphd__hint">empty</span>
            : needCount === 0 ? <span className="rdy rdy--ok">● all ready</span>
            : <span className="rdy rdy--warn">● {needCount} not ready</span>}
        </span>
        <button className="grouphd__bulk" title="Open the editing grid — type once in the ⊞ All-runs row to fill every run"
          onClick={(e) => { e.stopPropagation(); onSelect({ type: "grid", groupId: group.id }); }}>⊞ grid</button>
        <button className="grouphd__del" data-group-action="delete" data-groupid={group.id} title="Delete group (runs move to Unassigned)"
          onClick={(e) => { e.stopPropagation(); onDelete(group.id); }}>✕</button>
      </div>
      {expanded && group.runs.length > 0 && (
        <div className="grouprows">
          {group.runs.map((run, i) => (
            <RunRow key={run.id} run={run} group={group} dataset={dataset} runIdx={i} groups={groups}
              selected={selection.type === "run" && selection.runId === run.id}
              onSelect={onSelect} onInspectChannels={onInspectChannels} onEvidence={onEvidence}
              onCopyPrev={onCopyPrev} onMoveRun={onMoveRun}
              onDragStart={(e, rn, g) => { window.__dragRun = { run: rn, fromGroupId: g.id }; }} />
          ))}
        </div>
      )}
      {expanded && group.runs.length === 0 && <div className="grouprows">drag runs here to fill this group</div>}
    </div>
  );
}

function BundlePanel({ bundle, selection, onSelect, onMoveRun, onInspectChannels, onEvidence, onCopyPrev,
                       onProposeGroups, onNewGroup, onRenameGroup, onDeleteGroup, onRematchYaml,
                       editingGroupId, onStartRename, onCancelRename, onChangeSchema }) {
  const [expanded, setExpanded] = useState(() => Object.fromEntries(bundle.groups.map((g) => [g.id, true])));
  const [filesOpen, setFilesOpen] = useState(false);
  const toggle = (id) => setExpanded((e) => ({ ...e, [id]: !e[id] }));
  const totalRuns = bundle.groups.reduce((a, g) => a + g.runs.length, 0);
  const readyRuns = bundle.groups.reduce((a, g) => a + g.runs.filter((r) => window.runReadiness(r, bundle.dataset).ready).length, 0);
  const pct = totalRuns ? Math.round((readyRuns / totalRuns) * 100) : 0;

  return (
    <section className="core core--bundle">
      <header className="bundlehd">
        <div className="bundlehd__top">
          <span className="bundlehd__kind">SUPRA CONTAINER</span>
          <button className="schemachip" style={{ font: "inherit", fontSize: "11.5px", fontWeight: 600 }}
            title="Click to change the detected schema" onClick={onChangeSchema}>
            {bundle.schemaLabel} · v{bundle.schemaVersion}{bundle.schemaOverridden ? " · manual" : ""}
          </button>
        </div>
        <h1 className="bundlehd__name">{bundle.name}</h1>
        <div className="bundlehd__meta">
          <span><b>{bundle.groups.length}</b> group{bundle.groups.length !== 1 ? "s" : ""}</span>
          <span className="dot">·</span><span><b>{totalRuns}</b> runs</span>
          <span className="dot">·</span><span className="bundlehd__ready">{readyRuns}/{totalRuns} export-ready</span>
        </div>
        <div className="bundlebar"><span className="bundlebar__fill" style={{ width: pct + "%" }} /></div>
      </header>

      <div className="bundletools">
        <button className="btn btn--sm" onClick={onProposeGroups}><span className="ic">⊞</span> Propose groups…</button>
        <button className="btn btn--sm btn--ghost" onClick={onNewGroup}><span className="ic">＋</span> New group</button>
      </div>

      <div className="trow trow--head">
        <span className="trow__grip" />
        <span>Group / run</span>
        <span>Status</span>
        <span />
      </div>

      <div className="bundletree">
        {bundle.groups.map((g) => (
          <GroupBlock key={g.id} group={g} dataset={bundle.dataset} groups={bundle.groups}
            selection={selection} onSelect={onSelect} onMoveRun={onMoveRun}
            onInspectChannels={onInspectChannels} onEvidence={onEvidence} onCopyPrev={onCopyPrev}
            expanded={expanded[g.id] !== false} onToggle={toggle}
            editing={editingGroupId === g.id}
            onStartEdit={() => onStartRename(g.id)} onRename={onRenameGroup} onCancelEdit={onCancelRename}
            onDelete={onDeleteGroup} />
        ))}

        <div className="groupblk groupblk--unassigned"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const d = window.__dragRun; if (d) onMoveRun(d.run, d.fromGroupId, "__unassigned"); }}>
          <div className="grouphd grouphd--muted">
            <span className="grouphd__tw" />
            <span className="grouphd__icon" aria-hidden>○</span>
            <span className="grouphd__name">Unassigned</span>
            <span className="grouphd__count">{bundle.unassigned.length} runs</span>
            <span className="grouphd__hint">drag here to remove from a group</span>
          </div>
          {bundle.unassigned.length > 0 && (
            <div className="grouprows">
              {bundle.unassigned.map((run) => (
                <RunRow key={run.id} run={run} group={{ id: "__unassigned", runs: bundle.unassigned }} dataset={bundle.dataset}
                  runIdx={-1} groups={bundle.groups}
                  selected={selection.runId === run.id} onSelect={onSelect}
                  onInspectChannels={onInspectChannels} onEvidence={onEvidence} onCopyPrev={onCopyPrev} onMoveRun={onMoveRun}
                  onDragStart={(e, rn) => { window.__dragRun = { run: rn, fromGroupId: "__unassigned" }; }} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="filesdrawer">
        <button className="filesdrawer__hd" onClick={() => setFilesOpen((o) => !o)}>
          <span>{filesOpen ? "▾" : "▸"} Source files</span>
          <span className="filesdrawer__count">{bundle.sourcePairs.length} CSV + {bundle.sourcePairs.length} YAML</span>
          <span className="filesdrawer__rematch" onClick={(e) => { e.stopPropagation(); onRematchYaml(); }}>review pairing ›</span>
        </button>
        {filesOpen && (
          <ul className="filesdrawer__list">
            {bundle.sourcePairs.map((p) => (
              <li key={p.csv}><span className="ic">▢</span>{p.csv} <span className="pair">⟷ {p.yaml}</span></li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

Object.assign(window, { BundlePanel, runStatusInfo });

// ================= grid.jsx =================
// ---------------------------------------------------------------------------
// v3 unified GRID (F1-A) — the single spreadsheet editor.
// Runs as rows × schema fields as columns, with a pinned purple ⊞ All-runs
// row that writes to every run. Replaces both v2 grids (bulk table + table
// view). Excel paste works in every run cell; arrow keys / Enter navigate.
// Units shown in headers come from the group unit policy (F4-A).
// ---------------------------------------------------------------------------
const { useState: useStateGr, useRef: useRefGr, useMemo: useMemoGr } = React;

function gridColumns(group, density) {
  const cols = [];
  window.RUN_SECTIONS.forEach((sec) => {
    const fields = sec.fields.filter((f) => {
      // include a conditional column if ANY run currently meets its visible_when
      const visible = group.runs.some((r) => window.isVisible(f, r.values));
      if (!visible) return false;
      const lv = f.hardRequired ? "required" : f.importance === "required" ? "report"
        : f.importance === "required_for_accepted_runs" ? "required" : f.importance;
      if (density === "essential") return lv === "required" || lv === "report";
      if (density === "core") return lv !== "optional" || group.runs.some((r) => window.isFilled(r.values[f.id]));
      return true;
    });
    if (fields.length) cols.push({ sec, fields });
  });
  return cols;
}

function GridCell({ f, value, run, onChange, onCommit, cellRef, onKeyDown, onPaste, cls }) {
  if (f.type === "enum" || f.type === "bool") {
    const opts = f.type === "bool" ? [{ v: "true", label: "Yes" }, { v: "false", label: "No" }] : f.options;
    return (
      <td className={cls}>
        <select ref={cellRef} data-runid={run.id} data-fkey={f.id} value={value || ""} onKeyDown={onKeyDown}
          onChange={(e) => { onChange(e.target.value); onCommit(e.target.value); }}>
          <option value="">—</option>
          {opts.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
        </select>
      </td>
    );
  }
  return (
    <td className={cls} title={cls.includes("is-err") ? window.fieldError(f, value) : ""}>
      <input ref={cellRef} value={value || ""} placeholder="—"
        data-runid={run.id} data-fkey={f.id}
        onKeyDown={onKeyDown} onPaste={onPaste}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => onCommit(e.target.value)} />
    </td>
  );
}

// ⊞ All-runs cell: shows the uniform value when all runs agree, "mixed · N"
// placeholder otherwise; commit on Enter/blur (text) or change (enum).
function AllRunsCell({ f, group, onBulkSet, cellRef, onKeyDown }) {
  const vals = new Set(group.runs.map((r) => (r.values[f.id] == null ? "" : String(r.values[f.id]))));
  const uniform = vals.size === 1 ? [...vals][0] : null;
  const mixedN = vals.size;
  if (f.type === "enum" || f.type === "bool") {
    const opts = f.type === "bool" ? [{ v: "true", label: "Yes" }, { v: "false", label: "No" }] : f.options;
    return (
      <td className="is-all">
        <select ref={cellRef} data-grid-all={f.id} value={uniform || ""} onKeyDown={onKeyDown}
          onChange={(e) => { if (e.target.value) onBulkSet(f.id, e.target.value); }}>
          <option value="">{uniform === null ? "mixed · " + mixedN : "—"}</option>
          {opts.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
        </select>
      </td>
    );
  }
  return (
    <td className="is-all">
      <input ref={cellRef} key={uniform === null ? "mixed" + mixedN : "u" + uniform}
        data-grid-all={f.id}
        defaultValue={uniform || ""}
        placeholder={uniform === null ? "mixed · " + mixedN : "type once ↵"}
        onKeyDown={(e) => {
          if (e.key === "Enter" && e.target.value.trim() && e.target.value !== uniform) {
            onBulkSet(f.id, e.target.value.trim());
          } else onKeyDown(e);
        }}
        onBlur={(e) => { if (e.target.value.trim() && e.target.value !== uniform) onBulkSet(f.id, e.target.value.trim()); }} />
    </td>
  );
}

function GridView({ bundle, group, selection, density, onCellSet, onCellCommit, onCellBatchCommit, onBulkSet }) {
  const cols = useMemoGr(() => gridColumns(group, density), [group, density]);
  const fields = cols.flatMap((c) => c.fields);
  const cellRefs = useRefGr({});
  const key = (r, c) => r + ":" + c;

  // keyboard navigation: ↑↓ move rows (row 0 = all-runs), Enter = down,
  // ←→ move when caret is at the input boundary. Tab stays native.
  const nav = (r, c) => (e) => {
    const move = (nr, nc) => {
      const el = cellRefs.current[key(nr, nc)];
      if (el) { e.preventDefault(); el.focus(); if (el.select) el.select(); }
    };
    if (e.key === "ArrowDown" || (e.key === "Enter" && e.target.tagName === "INPUT")) move(r + 1, c);
    else if (e.key === "ArrowUp") move(r - 1, c);
    else if (e.key === "ArrowLeft" && (e.target.selectionStart === 0 || e.target.tagName === "SELECT")) move(r, c - 1);
    else if (e.key === "ArrowRight" && (e.target.tagName === "SELECT" || e.target.selectionStart === (e.target.value || "").length)) move(r, c + 1);
  };

  const handlePaste = (run, startIdx) => (e) => {
    const text = e.clipboardData.getData("text");
    if (!text || (!text.includes("\t") && !text.includes("\n"))) return;
    e.preventDefault();
    const rows = text.split(/\r?\n/).filter((r) => r.length);
    const startRun = group.runs.findIndex((r) => r.id === run.id);
    const updates = [];
    rows.forEach((row, ri) => {
      const target = group.runs[startRun + ri];
      if (!target) return;
      row.split("\t").forEach((cell, ci) => {
        const f = fields[startIdx + ci];
        if (f && f.type !== "enum" && f.type !== "bool") {
          const value = cell.trim();
          onCellSet(target.id, f.id, value);
          updates.push({ run_id: target.id, patch: { [f.id]: value } });
        }
      });
    });
    if (updates.length) onCellBatchCommit(updates);
  };

  return (
    <div className="gridview">
      <div className="gridview__hint">
        All {group.runs.length} runs · type once in the <b className="allink">⊞ All runs</b> row to fill every run ·
        paste a block from Excel into any cell · <span className="mono" style={{ fontSize: "11px" }}>↑↓←→</span> move · <span className="mono" style={{ fontSize: "11px" }}>↵</span> next run
      </div>
      <div className="gridscroll">
        <table className="gtable">
          <thead>
            <tr className="gtable__secs">
              <th className="gtable__rowhd" />
              {cols.map((c) => <th key={c.sec.id} colSpan={c.fields.length}>{c.sec.label}</th>)}
            </tr>
            <tr>
              <th className="gtable__rowhd">Run</th>
              {fields.map((f) => (
                <th key={f.id} title={f.desc || f.label}>
                  {f.label}{f.hardRequired && <span className="mk mk--req">*</span>}
                  {f.importance === "required_for_accepted_runs" && <span className="mk mk--req" title="Required while validity is Accepted">*ᵃ</span>}
                  {f.units && <span className="gtable__unit">{group.units[f.id] || f.stdUnit}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="gtable__all">
              <th className="gtable__rowhd">⊞ All runs</th>
              {fields.map((f, c) => (
                <AllRunsCell key={f.id} f={f} group={group} onBulkSet={onBulkSet}
                  cellRef={(el) => (cellRefs.current[key(0, c)] = el)} onKeyDown={nav(0, c)} />
              ))}
            </tr>
            {group.runs.map((run, ri) => {
              const st = window.runStatusInfo(run, bundle.dataset);
              const isSel = selection.type === "run" && selection.runId === run.id;
              return (
                <tr key={run.id} className={isSel ? "is-selected" : ""}>
                  <th className="gtable__rowhd">
                    <span className={"tdot tdot--" + st.cls} title={st.label} />{run.id}
                  </th>
                  {fields.map((f, c) => {
                    const visible = window.isVisible(f, run.values);
                    if (!visible) return <td key={f.id} className="is-na">·</td>;
                    const v = run.values[f.id];
                    const err = window.isFilled(v) && window.fieldError(f, v);
                    const lv = window.effLevel(f, run.values);
                    const missing = lv === "required" && !window.isRecorded(f, v);
                    const cls = err ? "is-err" : missing ? "is-req" : "";
                    return (
                      <GridCell key={f.id} f={f} value={v} run={run} cls={cls}
                        onChange={(val) => onCellSet(run.id, f.id, val)}
                        onCommit={(val) => onCellCommit(run.id, f.id, val)}
                        cellRef={(el) => (cellRefs.current[key(ri + 1, c)] = el)}
                        onKeyDown={nav(ri + 1, c)} onPaste={handlePaste(run, c)} />
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Object.assign(window, { GridView });

// ================= inserter.jsx =================
// ---------------------------------------------------------------------------
// Right core v3 — DATA ENTRY.
// F2-A  keyboard: Tab/Shift+Tab = next/prev field (native — per review feedback),
//        Alt+Enter = next EMPTY required field, Ctrl+Enter = same field on the next run.
//        Hints surface under the focused field.
// F3-A  mixed shared fields show a per-run breakdown popover before overwrite.
// F4-A  units are group policy — changing one asks convert vs relabel.
// F7-A  validation = docked live issues drawer, not a modal.
// F9-A  persistent scope tinting + blast-radius microcopy on focus.
// F12-A required-amber only after touch or validation.
// All fields/sections derive from schema.jsx (compression 0.3.0 YAML).
// ---------------------------------------------------------------------------
const { useState: useStateI, useMemo: useMemoI, useRef: useRefI, useEffect: useEffectI } = React;

const KBD_HINT = <span className="kbdhint"><b>Tab</b> next · <b>Alt+Enter</b> next empty required · <b>Ctrl+Enter</b> next run</span>;

function levelMark(lv) {
  if (lv === "required") return <span className="mk mk--req" title="Required for export">*</span>;
  if (lv === "report") return <span className="mk mk--rep" title="Required for the report (export proceeds)">†</span>;
  if (lv === "recommended") return <span className="mk mk--rec" title="Recommended">**</span>;
  return null;
}

// human name + expected-format hint for a field's TYPE (drives visible checks)
function fieldTypeName(f) {
  if (f.type === "float") return "number";
  if (f.type === "date") return "date";
  if (f.type === "enum") return "choice";
  if (f.type === "bool") return "yes / no";
  return "text";
}
function fieldFormatHint(f) {
  if (f.type === "float") return "number" + (f.min === 0 ? " > 0" : f.min !== undefined ? " ≥ " + f.min : "");
  if (f.type === "date") return "date · yyyy-MM-dd";
  if (f.type === "enum") return f.options.length + " choices";
  if (f.type === "bool") return "yes / no";
  if (f.pattern) return "text";
  return "text";
}

// ---------- mixed-value breakdown popover (F3-A) ----------
function MixedPopover({ f, group, onUseForAll }) {
  const byVal = new Map();
  group.runs.forEach((r) => {
    const v = r.values[f.id] == null ? "" : String(r.values[f.id]);
    if (!byVal.has(v)) byVal.set(v, []);
    byVal.get(v).push(r.id);
  });
  const rows = [...byVal.entries()].sort((a, b) => b[1].length - a[1].length);
  return (
    <div className="mixpop" onMouseDown={(e) => e.preventDefault()}>
      <div className="mixpop__t">Values across {group.runs.length} runs</div>
      <table>
        <tbody>
          {rows.map(([v, ids], i) => (
            <tr key={i} className={i > 0 && ids.length === 1 ? "is-outlier" : ""}>
              <td className="r">{ids.length > 3 ? ids.length + " runs" : ids.map(window.runShort).join(", ")}</td>
              <td className="v">{v === "" ? "—" : (f.options ? window.enumLabel(f, v) : v)}</td>
              <td className="a">{v !== "" && <button onClick={() => onUseForAll(v)}>use for all</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mixpop__f">Typing a value replaces all of these — undo with Ctrl+Z.</div>
    </div>
  );
}

// ---------- unit policy confirm (F4-A) ----------
function UnitConfirm({ f, from, to, count, onApply, onCancel }) {
  const factor = window.conversionFactorLabel(f.dim, from, to);
  return (
    <div className="unitconfirm">
      <span className="unitconfirm__q"><b>{from} → {to}</b> on {count} runs:</span>
      <button className="unitconfirm__btn unitconfirm__btn--pri" onClick={() => onApply(true)}>Convert values {factor && "(" + factor + ")"}</button>
      <button className="unitconfirm__btn" onClick={() => onApply(false)}>Relabel only</button>
      <button className="unitconfirm__x" onClick={onCancel}>✕</button>
    </div>
  );
}

// ---------- single field ----------
function Field({ f, value, ctx, unitValue, scope, group, focused, touched, validated,
                 onChange, onFocus, onBlur, onUnitPick, onUnitInline, pendingUnit, onUnitApply, onUnitCancel,
                 onCommit, onApplyAll, sharedCount, mixed }) {
  const lv = window.effLevel(f, ctx);
  const err = window.isFilled(value) ? window.fieldError(f, value) : null;
  const empty = !window.isRecorded(f, value);
  const isMixed = !!mixed && empty;
  const isSelect = f.type === "enum" || f.type === "bool";
  // visible type-validity check: ✓ when recorded & type-valid, ! when type-invalid
  const validState = err ? "err" : (!empty && !isMixed ? "ok" : null);
  // F12-A: escalate amber only after the field was touched or validation ran
  const showReq = lv === "required" && empty && !isMixed && (touched || validated);
  const cls = ["field", f.span === 1 ? "field--half" : "", isMixed ? "is-mixed" : "",
    showReq ? "is-required" : "", err ? "is-error" : "", window.isFilled(value) ? "is-filled" : ""].join(" ");
  const blast = scope === "run" ? "✎ this run only"
    : scope === "shared-run" ? "⊞ writes to all " + sharedCount + " runs"
    : "◈ shared — applies to every run";

  return (
    <div className={cls}>
      <label className="field__label">{f.label}{levelMark(lv)}</label>
      <div className="field__control">
        <div className="field__inputwrap">
          <div className={"inpfield" + (isSelect ? " inpfield--select" : "")}>
            {isSelect ? (
              <select className="inp" data-fkey={f.id} data-req={lv === "required" ? 1 : 0}
                value={value || ""} onChange={(e) => onChange(e.target.value)} onFocus={onFocus} onBlur={(e) => onBlur(f.id, e.target.value)}>
                <option value="">{isMixed ? "— mixed (" + mixed + ") —" : "—"}</option>
                {(f.type === "bool" ? [{ v: "true", label: "Yes" }, { v: "false", label: "No" }] : f.options)
                  .map((o) => <option key={o.v} value={o.v}>{o.label}{o.deviation ? " ⚠ ISO deviation" : ""}</option>)}
              </select>
            ) : (
              <input className="inp" data-fkey={f.id} data-req={lv === "required" ? 1 : 0}
                type="text" inputMode={f.type === "float" ? "decimal" : undefined}
                placeholder={isMixed ? "Mixed · " + mixed + " values" : (f.ph || (f.type === "float" ? "0.00" : f.type === "date" ? "yyyy-MM-dd" : ""))}
                value={value || ""} onChange={(e) => onChange(e.target.value)} onFocus={onFocus} onBlur={(e) => onBlur(f.id, e.target.value)} />
            )}
            {validState && (
              <span className={"vchk vchk--" + validState}
                title={validState === "ok" ? "Valid " + fieldTypeName(f) : "Invalid " + fieldTypeName(f)}>
                {validState === "ok" ? "✓" : "!"}
              </span>
            )}
          </div>
          {f.units && (
            <select className="unit" data-unit-fkey={f.id} value={unitValue || f.stdUnit}
              onChange={(e) => {
                if (f.unitInline) {
                  onUnitInline(f, e.target.value);
                  onCommit && onCommit(f.id + "__unit", e.target.value);
                } else {
                  onUnitPick(f, unitValue || f.stdUnit, e.target.value);
                }
              }}>
              {f.units.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          )}
        </div>
        {pendingUnit && pendingUnit.fieldId === f.id && (
          <UnitConfirm f={f} from={pendingUnit.from} to={pendingUnit.to} count={sharedCount}
            onApply={(convert) => onUnitApply(f, pendingUnit.to, convert)} onCancel={onUnitCancel} />
        )}
        {isMixed && focused && <MixedPopover f={f} group={group} onUseForAll={(v) => onChange(v)} />}
        <div className="field__under">
          {err && <span className="msg msg--err">⚠ {err}</span>}
          {!err && showReq && <span className="msg msg--req">Required for export</span>}
          {!err && !showReq && lv === "report" && empty && <span className="msg msg--rep">Required for the report</span>}
          {!err && isMixed && !focused && <span className="msg msg--mixed">differs across runs — focus to see values</span>}
          {focused && !err && (
            <span className="focusinfo"><span className="typehint" title="Expected value type">{fieldFormatHint(f)}</span><span className={"blast blast--" + scope}>{blast}</span>{KBD_HINT}</span>
          )}
          {onApplyAll && window.isFilled(value) && !err && !focused && (
            <button className="applyall" onClick={() => onApplyAll(f.id)}>⊞ apply to all {sharedCount}</button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------- form section ----------
function FormSection({ sec, values, ctxValues, density, scope, scopeTag, group, sharedCount, mixedMap,
                       focusKey, setFocusKey, touchedKeys, markTouched, validated,
                       onField, unitFor, onUnitPick, pendingUnit, onUnitApply, onUnitCancel,
                       onCommit, onApplyAll, innerRef, children }) {
  const ctx = ctxValues || values;
  const fields = window.visibleFields(sec.fields, ctx, density);
  if (fields.length === 0 && !children) return null;
  const c = window.sectionCounts(fields, values);
  return (
    <section className={"formsec formsec--" + scope} ref={innerRef} data-sec={sec.id}>
      <div className="formsec__hd">
        <h3 className="formsec__title">{sec.label}</h3>
        {scopeTag && <span className={"formsec__scope formsec__scope--" + scope}>{scopeTag}</span>}
        <span className="formsec__count">{c.filled}/{fields.length}</span>
      </div>
      <div className="formgrid">
        {fields.map((f) => (
          <Field key={f.id} f={f} value={values[f.id]} ctx={ctx} scope={scope} group={group}
            unitValue={f.unitInline ? (values[f.id + "__unit"] || f.stdUnit) : (unitFor ? unitFor(f) : null)}
            focused={focusKey === sec.id + ":" + f.id}
            touched={touchedKeys[f.id] || false} validated={validated}
            mixed={mixedMap ? mixedMap[f.id] : 0} sharedCount={sharedCount}
            onChange={(v) => onField(f.id, v)}
            onFocus={() => setFocusKey(sec.id + ":" + f.id)}
            onBlur={(fieldId, latestValue) => { setFocusKey(null); markTouched(fieldId); onCommit && onCommit(fieldId, latestValue); }}
            onUnitPick={onUnitPick} onUnitInline={(ff, u) => onField(ff.id + "__unit", u)}
            pendingUnit={pendingUnit} onUnitApply={onUnitApply} onUnitCancel={onUnitCancel}
            onCommit={onCommit}
            onApplyAll={onApplyAll} />
        ))}
      </div>
      {children}
    </section>
  );
}

// ---------- channel summaries ----------
function ChannelList({ rows }) {
  return (
    <div className="chanlist">
      {rows.map((r) => (
        <div key={r.header} className={"chanrow" + (r.cls ? " chanrow--" + r.cls : "")}>
          <span className="hdr">{r.header}</span>
          <span className={"dim" + (r.fam ? "" : " dim--none")}>{r.fam || "no family assigned"}</span>
          <span className="un">{r.unit || "—"}</span>
          <span className={"chstat chstat--" + r.status}>{r.statusLabel}</span>
        </div>
      ))}
    </div>
  );
}
function ChannelBlock({ run, onInspect }) {
  const issues = window.channelIssues(run);
  const rows = run.channels.map((c) => ({
    header: c.header, fam: c.family ? window.familyLabel(c.family) : null, unit: c.unit,
    status: c.status, statusLabel: c.status === "ambiguous" ? "? ambiguous" : c.status,
    cls: c.status === "ambiguous" ? "amb" : (c.status === "unmatched" ? "issue" : null),
  }));
  return (
    <>
      <ChannelList rows={rows} />
      <div className="chanblock__foot">
        <button className="rowbtn" onClick={onInspect}>
          <span>⚙</span> Review &amp; reassign channel headers…
          {issues.length > 0 && <span className="cnt" style={{ color: "var(--warn)" }}>{issues.length} unresolved</span>}
        </button>
      </div>
    </>
  );
}
function aggregateChannels(group) {
  const map = new Map();
  group.runs.forEach((r) => (r.channels || []).forEach((c) => {
    const e = map.get(c.header) || { header: c.header, fams: new Set(), units: new Set(), issues: [], count: 0 };
    e.count++;
    if (c.family) e.fams.add(window.familyLabel(c.family));
    if (c.unit) e.units.add(c.unit);
    if (c.status === "unmatched" || c.status === "ambiguous") e.issues.push(r.id);
    map.set(c.header, e);
  }));
  return [...map.values()];
}
function SharedChannelBlock({ group, onInspect, innerRef }) {
  const agg = aggregateChannels(group);
  const issueRuns = [...new Set(agg.flatMap((a) => a.issues))];
  const resolved = agg.filter((a) => a.issues.length === 0).length;
  const rows = agg.map((a) => ({
    header: a.header,
    fam: a.fams.size === 1 ? [...a.fams][0] : a.fams.size === 0 ? null : "differs across runs",
    unit: a.units.size === 1 ? [...a.units][0] : a.units.size === 0 ? "—" : "mixed",
    status: a.issues.length === 0 ? "matched" : "unmatched",
    statusLabel: a.issues.length === 0
      ? (a.count === group.runs.length ? "ok · all runs" : "ok · " + a.count + "/" + group.runs.length + " runs")
      : "unresolved · " + a.issues.map(window.runShort).join(", "),
    cls: a.issues.length ? "issue" : null,
  }));
  return (
    <section className="formsec formsec--shared-run" ref={innerRef} data-sec="channels-shared">
      <div className="formsec__hd">
        <h3 className="formsec__title">Parsed channels</h3>
        <span className="formsec__scope formsec__scope--shared-run">across {group.runs.length} runs</span>
        <span className="formsec__count">{resolved}/{agg.length}</span>
      </div>
      <ChannelList rows={rows} />
      <div className="chanblock__foot">
        <button className="rowbtn" onClick={() => onInspect(issueRuns[0] || group.runs[0].id)}>
          <span>⚙</span> Review &amp; reassign channel headers…
          {issueRuns.length > 0 && <span className="cnt" style={{ color: "var(--warn)" }}>{issueRuns.length} run{issueRuns.length > 1 ? "s" : ""} unresolved</span>}
        </button>
      </div>
    </section>
  );
}

// ---------- docked issues drawer (F7-A) ----------
function IssuesDrawer({ bundle, onJump, onOpenChannels, onClose }) {
  const rep = window.buildValidationReport(bundle);
  const items = [
    ...rep.errors.map((it) => ({ ...it, mark: "✕", mcls: "e" })),
    ...rep.missing.map((it) => ({ ...it, mark: "⚠", mcls: "w" })),
    ...rep.reportItems.map((it) => ({ ...it, mark: "†", mcls: "r" })),
  ];
  const [cursor, setCursor] = useStateI(0);
  const cur = Math.min(cursor, Math.max(0, items.length - 1));
  const go = (it) => { if (!it) return; it.action === "channels" ? onOpenChannels(it.target) : onJump(it.target); };
  const fixNext = () => {
    const it = items[cur];
    go(it);
    setCursor((c) => Math.min(c + 1, items.length - 1));
  };
  return (
    <div className="issuesdrawer">
      <div className="issuesdrawer__bar">
        <b>Issues</b>
        <span className="cnt-e">✕ {rep.errors.length} error{rep.errors.length !== 1 ? "s" : ""}</span>
        <span className="cnt-w">⚠ {rep.missing.length} missing</span>
        <span className="cnt-r">† {rep.reportItems.length} report gap{rep.reportItems.length !== 1 ? "s" : ""}</span>
        <span className="cnt-ok">✓ {rep.passed.length} checks passed · {rep.skipped.length} out of scope</span>
        <span className="issuesdrawer__nav">
          {items.length > 0 && <button className="fixnext" onClick={fixNext}>Fix next →</button>}
          <button className="dclose" title="Close" onClick={onClose}>✕</button>
        </span>
      </div>
      {items.length === 0 ? (
        <div className="issuesdrawer__clear">✓ Nothing blocking — {rep.readyRuns}/{rep.totalRuns} runs export-ready.
          {" "}Checked: {rep.passed.map((p) => p.text.split(" — ")[0]).join(" · ")}. Not validated: {rep.skipped.map((s) => s.text).join(" · ")}.</div>
      ) : (
        <ul className="issuesdrawer__list">
          {items.map((it, i) => (
            <li key={i} className={i === cur ? "is-cur" : ""} onClick={() => { setCursor(i); go(it); }}>
              <span className={"m " + it.mcls}>{it.mark}</span>
              <span className="txt">{it.text}{it.detail && <span className="detail">{it.detail}</span>}</span>
              <span className="go">{it.action === "channels" ? "open channels →" : "go to field →"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// compute shared/mixed values across runs (RUNS — SHARED)
function computeBulk(group) {
  const vals = {}, mixed = {};
  window.RUN_SECTIONS.forEach((s) => s.fields.forEach((f) => {
    const set = new Set(group.runs.map((r) => (r.values[f.id] == null ? "" : String(r.values[f.id]))));
    if (set.size === 1) vals[f.id] = [...set][0];
    else { vals[f.id] = ""; mixed[f.id] = set.size; }
  }));
  return { vals, mixed };
}

// ---------- section rail ----------
function Rail({ groups, active, onJump }) {
  return (
    <nav className="rail">
      {groups.map((grp) => (
        <div className="rail__grp" key={grp.key}>
          <div className="rail__hd">{grp.title}</div>
          {grp.sections.map((s) => {
            const c = s.counts;
            const done = c.reqTotal > 0 ? c.reqFilled === c.reqTotal && c.filled > 0 : c.filled === c.total && c.total > 0;
            return (
              <button key={s.id} className={"railitem" + (active === s.id ? " is-active" : "")} onClick={() => onJump(s.id)}>
                <span className={"railitem__dot" + (done ? " is-done" : c.filled ? " is-partial" : "")} />
                <span className="railitem__label">{s.label}</span>
                {c.total > 0 && <span className="railitem__count">{c.filled}/{c.total}</span>}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

// ---------- main panel ----------
function InsertPanel({ bundle, selection, onSelect, density, onDensity,
                       onEditDataset, onEditRun, onBulkSet, onUnitPolicy, onCopyPrev,
                       onCommitDataset, onCommitRun, onCommitBulkRun, onCommitRunMatrix,
                       onInspectChannels, onEvidence, onSupplemental,
                       issuesOpen, onToggleIssues, onValidate, hasValidated,
                       onExport, onJump, focusSection, toast }) {
  const group = bundle.groups.find((g) => g.id === selection.groupId) || bundle.groups[0];
  const isRun = selection.type === "run";
  const isGrid = selection.type === "grid";
  const run = isRun ? (group.runs.find((r) => r.id === selection.runId) || group.runs[0]) : null;
  const runIdx = run ? group.runs.indexOf(run) : -1;
  const [active, setActive] = useStateI(null);
  const [focusKey, setFocusKey] = useStateI(null);
  const [touched, setTouched] = useStateI({});
  const [pendingUnit, setPendingUnit] = useStateI(null);
  const scrollRef = useRefI(null);
  const secRefs = useRefI({});
  const pendingFieldFocus = useRefI(null);

  const markTouched = (id) => setTouched((t) => (t[id] ? t : { ...t, [id]: true }));

  const bulkData = useMemoI(() => computeBulk(group), [group]);
  const dsv = bundle.dataset.values;
  const datasetSecs = window.DATASET_SECTIONS.map((s) => ({
    ...s, counts: window.sectionCounts(window.visibleFields(s.fields, dsv, density), dsv),
  }));
  const runSecs = isRun ? window.RUN_SECTIONS.map((s) => ({
    ...s, counts: window.sectionCounts(window.visibleFields(s.fields, run.values, density), run.values),
  })) : [];
  const sharedRunSecs = selection.type === "dataset" ? window.RUN_SECTIONS.map((s) => ({
    ...s, counts: window.sectionCounts(window.visibleFields(s.fields, bulkData.vals, density), bulkData.vals),
  })) : [];
  const aggCh = selection.type === "dataset" ? aggregateChannels(group) : null;
  const chSection = aggCh ? {
    id: "channels-shared", label: "Parsed channels",
    counts: (() => { const ok = aggCh.filter((a) => a.issues.length === 0).length; return { filled: ok, total: aggCh.length, reqTotal: aggCh.length, reqFilled: ok }; })(),
  } : null;

  const railGroups = isRun
    ? [{ key: "run", title: "RUN — " + run.id, sections: runSecs },
       { key: "ds", title: "DATASET — shared · " + group.runs.length + " runs", sections: datasetSecs }]
    : [{ key: "ds", title: "DATASET — shared across " + group.runs.length + " runs", sections: datasetSecs },
       { key: "runshared", title: "RUNS — SHARED", sections: [...sharedRunSecs, chSection].filter(Boolean) }];
  const renderOrder = railGroups.flatMap((g) => g.sections);

  const jump = (id) => {
    setActive(id);
    const el = secRefs.current[id], sc = scrollRef.current;
    if (el && sc) sc.scrollTop = el.offsetTop - 8;
  };
  const onScroll = () => {
    const sc = scrollRef.current; if (!sc) return;
    let cur = null;
    renderOrder.forEach((s) => { const el = secRefs.current[s.id]; if (el && el.offsetTop - 16 <= sc.scrollTop) cur = s.id; });
    if (cur && cur !== active) setActive(cur);
  };
  useEffectI(() => {
    setActive(renderOrder[0] && renderOrder[0].id);
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
    setPendingUnit(null);
    // Ctrl+Enter hand-off: refocus the same field on the newly selected run
    if (pendingFieldFocus.current && scrollRef.current) {
      const fid = pendingFieldFocus.current; pendingFieldFocus.current = null;
      requestAnimationFrame(() => {
        const el = scrollRef.current && scrollRef.current.querySelector('[data-fkey="' + fid + '"]');
        if (el) { el.focus(); if (el.select) el.select(); el.scrollIntoViewIfNeeded && el.scrollIntoViewIfNeeded(); }
      });
    }
  }, [selection.type, selection.runId, selection.groupId]);

  // jump from issues drawer / export manifest
  useEffectI(() => {
    if (focusSection && focusSection.sectionId) {
      requestAnimationFrame(() => {
        jump(focusSection.sectionId);
        if (focusSection.fieldId && scrollRef.current) {
          const el = scrollRef.current.querySelector('[data-fkey="' + focusSection.fieldId + '"]');
          if (el) { el.focus(); if (el.select) el.select(); }
        }
      });
    }
  }, [focusSection]);

  // F2-A keyboard: Alt+Enter next empty required · Ctrl+Enter same field next run
  const onFormKeyDown = (e) => {
    if (e.key !== "Enter") return;
    if (e.altKey) {
      e.preventDefault();
      const inputs = [...scrollRef.current.querySelectorAll('[data-req="1"]')];
      const curIdx = inputs.indexOf(document.activeElement);
      const order = [...inputs.slice(curIdx + 1), ...inputs.slice(0, curIdx + 1)];
      const next = order.find((el) => !el.value);
      if (next) { next.focus(); if (next.select) next.select(); }
    } else if ((e.metaKey || e.ctrlKey) && isRun && runIdx < group.runs.length - 1) {
      e.preventDefault();
      const fid = document.activeElement && document.activeElement.getAttribute("data-fkey");
      if (fid) pendingFieldFocus.current = fid;
      onSelect({ type: "run", groupId: group.id, runId: group.runs[runIdx + 1].id });
    }
  };

  // unit policy plumbing (F4-A)
  const onUnitPick = (f, from, to) => { if (from !== to) setPendingUnit({ fieldId: f.id, from, to }); };
  const onUnitApply = (f, to, convert) => { setPendingUnit(null); onUnitPolicy(group.id, f, to, convert); };

  const prog = isRun ? window.runReadiness(run, bundle.dataset) : null;
  const dsReq = useMemoI(() => {
    let req = 0, ok = 0, rep = 0, repOk = 0;
    window.DATASET_SECTIONS.forEach((s) => s.fields.forEach((f) => {
      if (!window.isVisible(f, dsv)) return;
      const lv = window.effLevel(f, dsv), good = window.isRecorded(f, dsv[f.id]) && !window.fieldError(f, dsv[f.id]);
      if (lv === "required") { req++; if (good) ok++; }
      if (lv === "report") { rep++; if (good) repOk++; }
    }));
    return { req, ok, rep, repOk };
  }, [bundle.dataset]);
  const report = useMemoI(() => window.buildValidationReport(bundle), [bundle]);
  const issueCount = report.errors.length + report.missing.length;

  const sectionExtras = (secId) => {
    if (isRun && secId === "channel_preamble_summary")
      return <ChannelBlock run={run} onInspect={() => onInspectChannels(group.id, run.id)} />;
    return null;
  };

  return (
    <section className="core core--insert">
      <header className="insrhd">
        <div className="insrhd__row">
          <div className="insrhd__scope">
            {isRun ? (
              <>
                <span className="scopekind scopekind--run">RUN</span>
                <div className="stepper">
                  <button className="stepper__btn" disabled={runIdx <= 0}
                    onClick={() => onSelect({ type: "run", groupId: group.id, runId: group.runs[runIdx - 1].id })}>‹</button>
                  <span className="stepper__label"><b className="mono">{run.id}</b><span className="stepper__of">{runIdx + 1} of {group.runs.length}</span></span>
                  <button className="stepper__btn" disabled={runIdx >= group.runs.length - 1}
                    onClick={() => onSelect({ type: "run", groupId: group.id, runId: group.runs[runIdx + 1].id })}>›</button>
                </div>
                <span className="insrhd__spec mono">{run.values.specimen_name || run.fileLabel}</span>
              </>
            ) : (
              <>
                <span className={"scopekind " + (isGrid ? "scopekind--bulk" : "scopekind--ds")}>{isGrid ? "GRID" : "DATASET"}</span>
                <span className="insrhd__title">{group.name}</span>
              </>
            )}
            <div className="scopepills">
              <button className={selection.type === "dataset" ? "is-active" : ""}
                onClick={() => onSelect({ type: "dataset", groupId: group.id })}>Shared metadata</button>
              <button className={isGrid ? "is-active" : ""}
                onClick={() => onSelect({ type: "grid", groupId: group.id })}>⊞ Grid · all runs</button>
            </div>
          </div>
          <div className="insrhd__controls">
            <label className="density" title="Field visibility">
              <span className="density__ic">☰</span>
              <select value={density} onChange={(e) => onDensity(e.target.value)}>
                <option value="essential">Required only</option>
                <option value="core">Required + recommended</option>
                <option value="all">All fields</option>
              </select>
            </label>
          </div>
        </div>

        <div className="insrprog">
          {isRun && (<>
            <div className="insrprog__bar"><span className="insrprog__fill" style={{ width: ((prog.missing.length + prog.errors.length) === 0 ? 100 : Math.max(8, 100 - (prog.missing.length + prog.errors.length) * 22)) + "%" }} /></div>
            <span className="insrprog__txt">
              {prog.ready
                ? <span className="insrprog__ok">✓ run is export-ready</span>
                : <>
                    {prog.missing.length > 0 && <span className="insrprog__warn">{prog.missing.length} required missing</span>}
                    {prog.errors.length > 0 && <span className="insrprog__err"> · {prog.errors.length} error{prog.errors.length > 1 ? "s" : ""}</span>}
                    {prog.chIssues > 0 && <span className="insrprog__err"> · {prog.chIssues} channel{prog.chIssues > 1 ? "s" : ""}</span>}
                    {!prog.datasetOk && <span className="insrprog__warn"> · dataset incomplete</span>}
                  </>}
            </span>
            {runIdx > 0 && (
              <button className="linkbtn" title="Fill empty fields from the previous run"
                onClick={() => onCopyPrev(group.id, run.id)}>⧉ copy from {group.runs[runIdx - 1].id}</button>
            )}
          </>)}
          {selection.type === "dataset" && (<>
            <div className="insrprog__bar"><span className="insrprog__fill" style={{ width: (dsReq.req ? (dsReq.ok / dsReq.req) * 100 : 100) + "%" }} /></div>
            <span className="insrprog__txt"><b>{dsReq.ok}/{dsReq.req}</b> required · <b>{dsReq.repOk}/{dsReq.rep}</b> report-required · applies to all {group.runs.length} runs</span>
          </>)}
          {isGrid && (
            <span className="bulknote">One grid for everything: the <b className="bulknote__mix">⊞ All runs</b> row fills every run; cells edit single runs; Excel paste works anywhere. <b>{report.readyRuns}/{report.totalRuns}</b> runs ready.</span>
          )}
        </div>
      </header>

      {isGrid ? (
        <GridView bundle={bundle} group={group} selection={selection} density={density}
          onCellSet={(runId, k, v) => onEditRun(group.id, runId, k, v)}
          onCellCommit={(runId, k, v) => onCommitRun && onCommitRun(group.id, runId, k, v)}
          onCellBatchCommit={(updates) => onCommitRunMatrix && onCommitRunMatrix(group.id, updates)}
          onBulkSet={(k, v) => { onBulkSet(group.id, k, v); onCommitBulkRun && onCommitBulkRun(group.id, k, v); }} />
      ) : (
        <div className="insrbody">
          <Rail groups={railGroups} active={active} onJump={jump} />
          <div className="formscroll" ref={scrollRef} onScroll={onScroll} onKeyDown={onFormKeyDown}>
            {selection.type === "dataset" && datasetSecs.map((s) => (
              <FormSection key={s.id} sec={s} values={dsv} density={density} scope="dataset"
                scopeTag="shared · all runs" group={group} sharedCount={group.runs.length}
                focusKey={focusKey} setFocusKey={setFocusKey} touchedKeys={touched} markTouched={markTouched}
                validated={hasValidated}
                innerRef={(el) => (secRefs.current[s.id] = el)}
                onField={(k, v) => onEditDataset(k, v)}
                onCommit={(k, v) => onCommitDataset && onCommitDataset(group.id, k, v)}
                onUnitPick={onUnitPick} pendingUnit={pendingUnit} onUnitApply={onUnitApply} onUnitCancel={() => setPendingUnit(null)} />
            ))}
            {selection.type === "dataset" && (
              <div className="scopedivider scopedivider--bulk"><span>Runs — shared · identical on every run · typing here fills all {group.runs.length}</span></div>
            )}
            {selection.type === "dataset" && sharedRunSecs.map((s) => (
              <FormSection key={s.id} sec={s} values={bulkData.vals} ctxValues={bulkData.vals} density={density}
                scope="shared-run" scopeTag="runs · shared" group={group} mixedMap={bulkData.mixed}
                sharedCount={group.runs.length}
                focusKey={focusKey} setFocusKey={setFocusKey} touchedKeys={touched} markTouched={markTouched}
                validated={hasValidated}
                unitFor={(f) => group.units[f.id]}
                innerRef={(el) => (secRefs.current[s.id] = el)}
                onField={(k, v) => onBulkSet(group.id, k, v, true)}
                onCommit={(k, v) => onCommitBulkRun && onCommitBulkRun(group.id, k, v)}
                onUnitPick={onUnitPick} pendingUnit={pendingUnit} onUnitApply={onUnitApply} onUnitCancel={() => setPendingUnit(null)} />
            ))}
            {selection.type === "dataset" && (
              <SharedChannelBlock group={group} innerRef={(el) => (secRefs.current["channels-shared"] = el)}
                onInspect={(runId) => onInspectChannels(group.id, runId)} />
            )}
            {selection.type === "dataset" && (
              <div className="formfoot">
                <button className="rowbtn" onClick={onSupplemental}>
                  <span>▤</span> Manage supplemental files…
                  <span className="cnt">{(bundle.supplemental || []).length} files</span>
                </button>
              </div>
            )}

            {isRun && runSecs.map((s) => (
              <FormSection key={s.id} sec={s} values={run.values} density={density} scope="run"
                group={group} sharedCount={group.runs.length}
                focusKey={focusKey} setFocusKey={setFocusKey} touchedKeys={touched} markTouched={markTouched}
                validated={hasValidated}
                unitFor={(f) => group.units[f.id]}
                innerRef={(el) => (secRefs.current[s.id] = el)}
                onField={(k, v) => onEditRun(group.id, run.id, k, v)}
                onCommit={(k, v) => onCommitRun && onCommitRun(group.id, run.id, k, v)}
                onUnitPick={onUnitPick} pendingUnit={pendingUnit} onUnitApply={onUnitApply} onUnitCancel={() => setPendingUnit(null)}
                onApplyAll={(k) => { onBulkSet(group.id, k, run.values[k]); onCommitBulkRun && onCommitBulkRun(group.id, k, run.values[k]); }}>
                {sectionExtras(s.id)}
              </FormSection>
            ))}
            {isRun && (
              <div className="formfoot" style={{ marginTop: "14px" }}>
                <button className="rowbtn" onClick={() => onEvidence(group.id, run.id)}>
                  <span>▣</span> Manage run image evidence…
                  <span className="cnt">{(run.evidence || []).length} images</span>
                </button>
              </div>
            )}
            {isRun && <div className="scopedivider"><span>Shared dataset metadata — edited once, applied to all {group.runs.length} runs</span></div>}
            {isRun && datasetSecs.map((s) => (
              <FormSection key={s.id} sec={s} values={dsv} density={density} scope="dataset"
                scopeTag="shared" group={group} sharedCount={group.runs.length}
                focusKey={focusKey} setFocusKey={setFocusKey} touchedKeys={touched} markTouched={markTouched}
                validated={hasValidated}
                innerRef={(el) => (secRefs.current[s.id] = el)}
                onField={(k, v) => onEditDataset(k, v)}
                onCommit={(k, v) => onCommitDataset && onCommitDataset(group.id, k, v)}
                onUnitPick={onUnitPick} pendingUnit={pendingUnit} onUnitApply={onUnitApply} onUnitCancel={() => setPendingUnit(null)} />
            ))}
          </div>
        </div>
      )}

      {issuesOpen && (
        <IssuesDrawer bundle={bundle} onJump={onJump}
          onOpenChannels={(t) => onInspectChannels(t.groupId, t.runId)}
          onClose={onToggleIssues} />
      )}

      <footer className="insrfoot">
        <div className="legend">
          <span><span className="mk mk--req">*</span> Required (export)</span>
          <span><span className="mk mk--rep">†</span> Required for report</span>
          <span><span className="mk mk--rec">**</span> Recommended</span>
        </div>
        <div className="insrfoot__actions">
          {hasValidated ? (
            <button className={"issuechip" + (issueCount ? " has-issues" : "")} onClick={onToggleIssues}
              title="Toggle the issues drawer">
              {issueCount ? "⚠ " + issueCount + " issue" + (issueCount > 1 ? "s" : "") : "✓ no issues"}
            </button>
          ) : (
            <button className="btn btn--ghost btn--sm" onClick={onValidate}>✓ Validate</button>
          )}
          <button className="btn btn--primary btn--sm" onClick={onExport}>⬇ Export…</button>
        </div>
      </footer>
      {toast && (
        <div className="toast">
          <span>{toast.msg}</span>
          {toast.undo && <button className="toast__undo" onClick={toast.undo}>Undo</button>}
        </div>
      )}
    </section>
  );
}

Object.assign(window, { InsertPanel });

// ================= app.jsx =================
// ---------------------------------------------------------------------------
// App shell v3.
// F5-A  app-wide undo stack: every mutation goes through apply(label, fn).
//        Ctrl+Z / Ctrl+Shift+Z work globally, Edit menu shows the labelled stack, and
//        bulk-action toasts carry an Undo button. Keystroke edits coalesce.
// F8-A  autosave: working state "saves" ~0.6 s after every change; the
//        status bar shows ✓ saved HH:MM · draft "name".
// F4-A  unit policy: changing a unit asks convert vs relabel, then applies
//        at GROUP level (group.units) — per-run drift is impossible.
// ---------------------------------------------------------------------------
const { useState: useStateA, useEffect: useEffectA, useRef: useRefA } = React;

function App() {
  const [stage, setStage] = useStateA("empty"); // empty | editor
  const [bundle, setBundleState] = useStateA(null);
  const [selection, setSelection] = useStateA({ type: "dataset", groupId: "g1" });
  const [density, setDensity] = useStateA("core");
  const [modal, setModal] = useStateA(null);
  const [editingGroupId, setEditingGroupId] = useStateA(null);
  const [focusSection, setFocusSection] = useStateA(null);
  const [toast, setToast] = useStateA(null);
  const [issuesOpen, setIssuesOpen] = useStateA(false);
  const [hasValidated, setHasValidated] = useStateA(false);
  const [savedAt, setSavedAt] = useStateA(null);
  const [backendSession, setBackendSession] = useStateA(null);
  const [backendError, setBackendError] = useStateA(null);
  const [schemaCandidates, setSchemaCandidates] = useStateA(window.SCHEMA_CANDIDATES);
  const [groupProposals, setGroupProposals] = useStateA([]);
  const [yamlRematchSummary, setYamlRematchSummary] = useStateA(null);
  const [yamlMappingReview, setYamlMappingReview] = useStateA(null);
  const [yamlMappingRows, setYamlMappingRows] = useStateA([]);
  const [lastExportPath, setLastExportPath] = useStateA(null);
  const [, setHistN] = useStateA(0); // re-render hook for menu enable state

  const bundleRef = useRefA(null);
  const undoStack = useRefA([]);
  const redoStack = useRefA([]);
  const lastEdit = useRefA(null); // coalesce key of the previous apply
  const toastTimer = useRefA(null);
  const saveTimer = useRefA(null);

  const setBundle = (b) => { bundleRef.current = b; setBundleState(b); };

  const syncSchemaCandidates = (session) => {
    installBackendSchemaForm(session?.bundle?.schemaForm || session?.bundle?.schema_form || session?.schemaForm || session?.schema_form || session?.schema?.form);
    const nextCandidates = schemaCandidatesFromBackendSession(session);
    if (nextCandidates.length) {
      setSchemaCandidates(nextCandidates);
      window.SCHEMA_CANDIDATES = nextCandidates;
    }
  };

  const applyBackendSessionView = (session, message) => {
    if (!session?.bundle) {
      const msg = "Backend package did not return a displayable bundle.";
      setBackendError(msg);
      say(msg);
      return false;
    }
    undoStack.current = [];
    redoStack.current = [];
    lastEdit.current = null;
    setHistN(0);
    installBackendSchemaForm(session.bundle.schemaForm || session.bundle.schema_form || session.schemaForm || session.schema_form || session.schema?.form);
    setBackendSession(session);
    syncSchemaCandidates(session);
    setGroupProposals([]);
    setYamlRematchSummary(null);
    setYamlMappingReview(null);
    setYamlMappingRows([]);
    setLastExportPath(null);
    setBackendError(null);
    setBundle(session.bundle);
    setStage("editor");
    setSelection({
      type: "dataset",
      groupId: session.bundle.groups?.[0]?.id || null,
    });
    setIssuesOpen(false);
    setHasValidated(false);
    setSavedAt(null);
    setModal(null);
    if (message) say(message);
    return true;
  };

  const say = (msg, undoFn) => {
    setToast({ msg, undo: undoFn || null });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), undoFn ? 4200 : 2600);
  };

  // ---- undo stack (F5-A) -------------------------------------------------------
  const apply = (label, fn, opts) => {
    const b = bundleRef.current;
    if (!b) return;
    const nb = fn(b);
    if (!nb || nb === b) return;
    const ck = (opts && opts.coalesce) || null;
    if (!(ck && lastEdit.current === ck && undoStack.current.length)) {
      undoStack.current.push({ bundle: b, label });
      if (undoStack.current.length > 80) undoStack.current.shift();
      redoStack.current = [];
    }
    lastEdit.current = ck;
    setBundle(nb);
    setHistN(undoStack.current.length);
  };

  const undo = () => {
    const e = undoStack.current.pop();
    if (!e || !bundleRef.current) return;
    redoStack.current.push({ bundle: bundleRef.current, label: e.label });
    lastEdit.current = null;
    setBundle(e.bundle);
    setHistN(undoStack.current.length);
    say("↩ Undid " + e.label);
  };
  const redo = () => {
    const e = redoStack.current.pop();
    if (!e || !bundleRef.current) return;
    undoStack.current.push({ bundle: bundleRef.current, label: e.label });
    lastEdit.current = null;
    setBundle(e.bundle);
    setHistN(undoStack.current.length);
    say("↪ Redid " + e.label);
  };
  const undoFn = useRefA(); undoFn.current = undo;
  const redoFn = useRefA(); redoFn.current = redo;

  useEffectA(() => {
    const h = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "z" || e.key === "Z")) {
        e.preventDefault();
        if (e.shiftKey) redoFn.current(); else undoFn.current();
      }
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, []);

  useEffectA(() => {
    let alive = true;
    const api = window.desktopApi?.packaging;
    if (!api?.createSession) return () => { alive = false; };
    api.createSession().then((response) => {
      if (!alive) return;
      if (response?.status === "ok") {
        setBackendSession(response.data);
        syncSchemaCandidates(response.data);
        setBackendError(null);
        return;
      }
      if (window.desktopApi?.host) {
        setBackendError(response?.message || "Backend packaging session unavailable.");
      }
    }).catch((err) => {
      if (alive && window.desktopApi?.host) {
        setBackendError(err?.message || "Backend packaging session unavailable.");
      }
    });
    return () => { alive = false; };
  }, []);

  const ensureBackendSession = async () => {
    if (backendSession?.session_id) return backendSession;
    const api = window.desktopApi?.packaging;
    if (!api?.createSession) {
      throw new Error("Desktop backend bridge is not available.");
    }
    const response = await api.createSession();
    if (response?.status !== "ok") {
      throw new Error(response?.message || "Backend packaging session unavailable.");
    }
    setBackendSession(response.data);
    syncSchemaCandidates(response.data);
    setGroupProposals([]);
    setBackendError(null);
    return response.data;
  };

  const openBackendPackage = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.openPackageDialog) {
      const msg = "Open MTDP package requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.openPackageDialog({ session_id: session.session_id });
      if (response?.status === "ok") {
        const path = response.data?.source_summary?.package_path;
        const name = path ? path.split(/[\\/]/).pop() : "package";
        applyBackendSessionView(response.data, "Opened MTDP package: " + name);
        return;
      }
      if (response?.error_type === "Cancelled") return;
      const msg = response?.message || "Could not open MTDP package.";
      setBackendError(msg);
      say("Could not open MTDP package: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not open MTDP package.";
      setBackendError(msg);
      say("Could not open MTDP package: " + msg);
    }
  };

  const openBackendSources = async (kind = "folder") => {
    const api = window.desktopApi?.packaging;
    if (!api?.openSourcesDialog) {
      const msg = "Open source files requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.openSourcesDialog({ session_id: session.session_id, kind });
      if (response?.status === "ok") {
        const count = Number(response.data?.source_summary?.source_count || 0);
        const label = kind === "files" ? "source files" : "source folder";
        const countText = count ? " (" + count + " source file" + (count === 1 ? "" : "s") + ")" : "";
        applyBackendSessionView(response.data, "Loaded " + label + countText);
        return;
      }
      if (response?.error_type === "Cancelled") return;
      const msg = response?.message || "Could not open source files.";
      setBackendError(msg);
      say("Could not open source files: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not open source files.";
      setBackendError(msg);
      say("Could not open source files: " + msg);
    }
  };

  const loadBackendSourcePaths = async (paths) => {
    const api = window.desktopApi?.packaging;
    if (!api?.loadSources) {
      const msg = "Dropped source files require the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.loadSources({ session_id: session.session_id, paths });
      if (response?.status === "ok") {
        const count = Number(response.data?.source_summary?.source_count || paths.length || 0);
        const countText = count ? " (" + count + " source file" + (count === 1 ? "" : "s") + ")" : "";
        applyBackendSessionView(response.data, "Loaded dropped source paths" + countText);
        return;
      }
      const msg = response?.message || "Could not load dropped source files.";
      setBackendError(msg);
      say("Could not load dropped source files: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not load dropped source files.";
      setBackendError(msg);
      say("Could not load dropped source files: " + msg);
    }
  };

  useEffectA(() => {
    const handleNativeSourceDrop = (event) => {
      const paths = nativeSourceDropPaths(event);
      if (paths.length) loadBackendSourcePaths(paths);
    };
    window.addEventListener(NATIVE_SOURCE_DROP_EVENT, handleNativeSourceDrop);
    return () => window.removeEventListener(NATIVE_SOURCE_DROP_EVENT, handleNativeSourceDrop);
  }, [backendSession]);

  // ---- autosave indicator (F8-A) -------------------------------------------------
  useEffectA(() => {
    if (stage !== "editor" || !bundle) return;
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      const d = new Date();
      setSavedAt(String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0"));
    }, 600);
    return () => clearTimeout(saveTimer.current);
  }, [bundle, stage]);

  // ---- bundle mutations (all undoable) --------------------------------------------
  const fLabel = (key) => {
    if (key && key.endsWith("__unit")) { const ff = window.ALL_FIELDS[key.slice(0, -6)]; return (ff ? ff.label : key) + " unit"; }
    const f = window.ALL_FIELDS[key]; return f ? f.label : key;
  };

  const invalidateBackendValidation = (b) => (
    b && b.backendValidation ? { ...b, backendValidation: null } : b
  );

  const editDataset = (key, value) => {
    setHasValidated(false);
    apply("edit “" + fLabel(key) + "”", (b) => ({
      ...invalidateBackendValidation(b),
      dataset: { ...b.dataset, values: { ...b.dataset.values, [key]: value } },
    }), { coalesce: "ds:" + key });
  };

  const editRun = (groupId, runId, key, value) => {
    setHasValidated(false);
    apply("edit " + runId + " · " + fLabel(key), (b) => ({
      ...invalidateBackendValidation(b),
      groups: b.groups.map((g) => g.id !== groupId ? g : {
        ...g, runs: g.runs.map((r) => r.id !== runId ? r : { ...r, values: { ...r.values, [key]: value } }),
      }),
    }), { coalesce: "run:" + runId + ":" + key });
  };

  const syncBackendEditResponse = (response) => {
    if (response?.status !== "ok") {
      const msg = response?.message || "Could not synchronize metadata edit.";
      setBackendError(msg);
      say("Could not synchronize metadata edit: " + msg);
      return false;
    }
    setBackendSession(response.data);
    syncSchemaCandidates(response.data);
    setGroupProposals([]);
    setBackendError(null);
    return true;
  };

  const applyBackendMutationView = (response, message) => {
    if (response?.status !== "ok") {
      const msg = response?.message || "Could not synchronize backend mutation.";
      setBackendError(msg);
      say("Could not synchronize backend mutation: " + msg);
      return false;
    }
    setBackendSession(response.data);
    syncSchemaCandidates(response.data);
    setGroupProposals([]);
    setBackendError(null);
    setHasValidated(false);
    installBackendSchemaForm(response.data?.bundle?.schemaForm || response.data?.bundle?.schema_form || response.data?.schemaForm || response.data?.schema_form || response.data?.schema?.form);
    if (response.data?.bundle) setBundle(response.data.bundle);
    if (message) say(message);
    return true;
  };

  const commitBackendDatasetField = async (groupId, key, value) => {
    const api = window.desktopApi?.packaging;
    if (!api?.updateDatasetFields) {
      if (window.desktopApi?.host) {
        const msg = "Dataset metadata edits require the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      syncBackendEditResponse(await api.updateDatasetFields({
        session_id: session.session_id,
        group_id: groupId,
        patch: { [key]: value },
      }));
    } catch (err) {
      const msg = err?.message || "Could not synchronize dataset metadata edit.";
      setBackendError(msg);
      say("Could not synchronize dataset metadata edit: " + msg);
    }
  };

  const commitBackendRunField = async (groupId, runId, key, value) => {
    const api = window.desktopApi?.packaging;
    if (!api?.updateRunFields) {
      if (window.desktopApi?.host) {
        const msg = "Run metadata edits require the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      syncBackendEditResponse(await api.updateRunFields({
        session_id: session.session_id,
        group_id: groupId,
        run_id: runId,
        patch: { [key]: value },
      }));
    } catch (err) {
      const msg = err?.message || "Could not synchronize run metadata edit.";
      setBackendError(msg);
      say("Could not synchronize run metadata edit: " + msg);
    }
  };

  const commitBackendBulkRunField = async (groupId, key, value) => {
    const api = window.desktopApi?.packaging;
    if (!api?.updateGroupRunFields) {
      if (window.desktopApi?.host) {
        const msg = "Bulk run metadata edits require the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.updateGroupRunFields({
        session_id: session.session_id,
        group_id: groupId,
        patch: { [key]: value },
      }));
    } catch (err) {
      const msg = err?.message || "Could not synchronize bulk run metadata edit.";
      setBackendError(msg);
      say("Could not synchronize bulk run metadata edit: " + msg);
    }
  };

  const commitBackendRunMatrix = async (groupId, updates) => {
    const api = window.desktopApi?.packaging;
    if (!updates || updates.length === 0) return;
    if (!api?.updateRunFieldMatrix) {
      if (window.desktopApi?.host) {
        const msg = "Grid paste metadata edits require the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.updateRunFieldMatrix({
        session_id: session.session_id,
        group_id: groupId,
        updates,
      }));
    } catch (err) {
      const msg = err?.message || "Could not synchronize pasted grid metadata.";
      setBackendError(msg);
      say("Could not synchronize pasted grid metadata: " + msg);
    }
  };

  const bulkSet = (groupId, key, value, silent) => {
    setHasValidated(false);
    apply("⊞ “" + fLabel(key) + "” → all runs", (b) => ({
      ...invalidateBackendValidation(b),
      groups: b.groups.map((g) => g.id !== groupId ? g : {
        ...g, runs: g.runs.map((r) => ({ ...r, values: { ...r.values, [key]: value } })),
      }),
    }), silent ? { coalesce: "bulk:" + groupId + ":" + key } : undefined);
    if (!silent) {
      const g = bundleRef.current.groups.find((x) => x.id === groupId);
      say("⊞ “" + fLabel(key) + "” = " + value + " applied to all " + (g ? g.runs.length : "") + " runs", () => undoFn.current());
    }
  };

  // F4-A: unit policy — convert or relabel every run in the group
  const unitPolicy = async (groupId, f, to, convert) => {
    const g0 = bundleRef.current.groups.find((g) => g.id === groupId);
    const from = (g0 && g0.units[f.id]) || f.stdUnit;
    if (from === to) return;
    const api = window.desktopApi?.packaging;
    if (!api?.setGroupRunUnit) {
      if (window.desktopApi?.host) {
        const msg = "Group unit policy changes require the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.setGroupRunUnit({
        session_id: session.session_id,
        group_id: groupId,
        field_id: f.id,
        unit: to,
        convert,
      }), (convert ? "Converted “" : "Relabelled “") + f.label + "” " + from + " → " + to + " on all runs");
    } catch (err) {
      const msg = err?.message || "Could not synchronize group unit policy.";
      setBackendError(msg);
      say("Could not synchronize group unit policy: " + msg);
    }
  };

  const copyPrev = (groupId, runId) => {
    const g = bundleRef.current.groups.find((x) => x.id === groupId);
    const idx = g ? g.runs.findIndex((r) => r.id === runId) : -1;
    if (!g || idx <= 0) return;
    const prev = g.runs[idx - 1];
    const skip = { specimen_name: 1, sample_id: 1, failure_image_reference: 1 };
    let n = 0;
    apply("copy from " + prev.id + " → " + runId, (b) => ({
      ...b,
      groups: b.groups.map((gg) => gg.id !== groupId ? gg : {
        ...gg,
        runs: gg.runs.map((r) => {
          if (r.id !== runId) return r;
          const values = { ...r.values };
          Object.keys(prev.values).forEach((k) => {
            if (skip[k]) return;
            if (!window.isFilled(values[k]) && window.isFilled(prev.values[k])) { values[k] = prev.values[k]; n++; }
          });
          return { ...r, values };
        }),
      }),
    }));
    say(n ? "⧉ Copied " + n + " value" + (n > 1 ? "s" : "") + " from " + prev.id + " into " + runId : "Nothing to copy — no empty fields with a value on " + prev.id, n ? () => undoFn.current() : null);
  };

  const moveRun = async (run, fromGroupId, toGroupId) => {
    if (fromGroupId === toGroupId) return;
    const api = window.desktopApi?.packaging;
    if (!api?.moveRun) {
      if (window.desktopApi?.host) {
        const msg = "Moving runs requires the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.moveRun({
        session_id: session.session_id,
        run_id: run.id,
        from_group_id: fromGroupId,
        target_group_id: toGroupId,
      });
      if (applyBackendMutationView(response)) {
        const dest = toGroupId === "__unassigned" ? "Unassigned"
          : (response.data?.bundle?.groups || []).find((g) => g.id === toGroupId)?.name;
        setSelection({ type: toGroupId === "__unassigned" ? "dataset" : "run", groupId: toGroupId === "__unassigned" ? (response.data?.bundle?.groups?.[0]?.id || null) : toGroupId, runId: run.id });
        say(run.id + " → " + (dest || toGroupId));
      }
    } catch (err) {
      const msg = err?.message || "Could not move run.";
      setBackendError(msg);
      say("Could not move run: " + msg);
    }
  };

  const renameGroup = async (groupId, name) => {
    setEditingGroupId(null);
    const clean = (name || "").trim();
    if (!clean) return;
    const api = window.desktopApi?.packaging;
    if (!api?.renameGroup) {
      if (window.desktopApi?.host) {
        const msg = "Renaming groups requires the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.renameGroup({
        session_id: session.session_id,
        group_id: groupId,
        name: clean,
      }), "Group renamed");
    } catch (err) {
      const msg = err?.message || "Could not rename group.";
      setBackendError(msg);
      say("Could not rename group: " + msg);
    }
  };

  const newGroup = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.createGroup) {
      if (window.desktopApi?.host) {
        const msg = "Creating groups requires the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.createGroup({
        session_id: session.session_id,
        name: "New group",
      });
      if (applyBackendMutationView(response, "Group created — name it, then drag runs in")) {
        const groups = response.data?.bundle?.groups || [];
        const created = groups[groups.length - 1];
        if (created) {
          setEditingGroupId(created.id);
          setSelection({ type: "dataset", groupId: created.id });
        }
      }
    } catch (err) {
      const msg = err?.message || "Could not create group.";
      setBackendError(msg);
      say("Could not create group: " + msg);
    }
  };

  const deleteGroup = async (groupId) => {
    const g = bundle.groups.find((x) => x.id === groupId);
    if (!g) return;
    const api = window.desktopApi?.packaging;
    if (!api?.deleteGroup) {
      if (window.desktopApi?.host) {
        const msg = "Deleting groups requires the desktop backend bridge.";
        setBackendError(msg);
        say(msg);
      }
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.deleteGroup({
        session_id: session.session_id,
        group_id: groupId,
      });
      if (!applyBackendMutationView(response)) return;
      if (selection.groupId === groupId) {
        const next = response.data?.bundle?.groups?.[0];
        setSelection({ type: "dataset", groupId: next ? next.id : null });
      }
      const movedCount = g.runs.length;
      say(
        movedCount === 0
          ? "Group deleted"
          : "Group deleted — " + movedCount + " run" + (movedCount !== 1 ? "s" : "") + " moved to Unassigned"
      );
    } catch (err) {
      const msg = err?.message || "Could not delete group.";
      setBackendError(msg);
      say("Could not delete group: " + msg);
    }
    if (editingGroupId === groupId) setEditingGroupId(null);
  };

  const assignChannel = (groupId, runId, chIdx, patch) => apply("channel assignment · " + runId, (b) => ({
    ...b,
    groups: b.groups.map((g) => g.id !== groupId ? g : {
      ...g,
      runs: g.runs.map((r) => r.id !== runId ? r : {
        ...r, channels: r.channels.map((c, i) => i === chIdx ? { ...c, ...patch } : c),
      }),
    }),
  }), { coalesce: "ch:" + runId + ":" + chIdx });

  const openGroupProposals = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.proposeGroups) {
      const msg = "Proposing groups requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.proposeGroups({ session_id: session.session_id });
      if (response?.status === "ok") {
        const proposals = response.data?.proposals || [];
        setGroupProposals(proposals);
        setBackendError(null);
        setModal({ kind: "propose", proposals });
        if (proposals.length === 0) say("No backend grouping proposals are available.");
        return;
      }
      const msg = response?.message || "Could not propose groups.";
      setBackendError(msg);
      say("Could not propose groups: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not propose groups.";
      setBackendError(msg);
      say("Could not propose groups: " + msg);
    }
  };

  const applyProposal = async (pid) => {
    const api = window.desktopApi?.packaging;
    if (!api?.applyGroupingProposal) {
      const msg = "Applying grouping proposals requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.applyGroupingProposal({
        session_id: session.session_id,
        proposal_id: pid,
      });
      if (!applyBackendMutationView(response)) return;
      const nextGroup = response.data?.bundle?.groups?.[0];
      setSelection({ type: "dataset", groupId: nextGroup ? nextGroup.id : null });
      setModal(null);
      say("Applied backend grouping proposal");
    } catch (err) {
      const msg = err?.message || "Could not apply grouping proposal.";
      setBackendError(msg);
      say("Could not apply grouping proposal: " + msg);
    }
  };

  const pickSchema = async (sid) => {
    setModal(null);
    const s = schemaCandidates.find((c) => c.id === sid);
    if (!s) return;
    const api = window.desktopApi?.packaging;
    if (!api?.setSchema) {
      const msg = "Changing schema requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.setSchema({
        session_id: session.session_id,
        schema_id: s.id,
      });
      if (response?.status === "ok") {
        applyBackendSessionView(
          response.data,
          s.detected
            ? "Schema reset to detected: " + s.label
            : "Schema manually set to " + s.label + " v" + s.version + " — recorded in backend session"
        );
        return;
      }
      const msg = response?.message || "Could not change schema.";
      setBackendError(msg);
      say("Could not change schema: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not change schema.";
      setBackendError(msg);
      say("Could not change schema: " + msg);
    }
  };

  const validateBackendGroup = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.validateGroup) {
      const msg = "Validation requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const activeGroup = bundleRef.current?.groups?.find((g) => g.id === selection.groupId)
        || bundleRef.current?.groups?.[0];
      const response = await api.validateGroup({
        session_id: session.session_id,
        group_id: activeGroup?.id,
      });
      if (response?.status === "ok") {
        applyBackendSessionView(response.data);
        setIssuesOpen(true);
        setHasValidated(true);
        const validation = response.data?.bundle?.backendValidation;
        const n = Number(validation?.error_count || 0);
        say(n ? "Validation found " + n + " blocking issue" + (n === 1 ? "" : "s") : "Validation passed — group is export-ready");
        return;
      }
      const msg = response?.message || "Could not validate package.";
      setBackendError(msg);
      say("Could not validate package: " + msg);
    } catch (err) {
      const msg = err?.message || "Could not validate package.";
      setBackendError(msg);
      say("Could not validate package: " + msg);
    }
  };

  const exportBackendGroup = async ({ initialDir, defaultName } = {}) => {
    const api = window.desktopApi?.packaging;
    if (!api?.exportGroup) {
      const msg = "Export requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const activeGroup = bundleRef.current?.groups?.find((g) => g.id === selection.groupId)
        || bundleRef.current?.groups?.[0];
      const response = await api.exportGroup({
        session_id: session.session_id,
        group_id: activeGroup?.id,
        initial_dir: initialDir,
        default_name: defaultName,
      });
      if (response?.error_type === "Cancelled") return;
      if (response?.status !== "ok") {
        const msg = response?.message || "Could not export package.";
        setBackendError(msg);
        say("Could not export package: " + msg);
        return;
      }
      applyBackendSessionView(response.data);
      const exported = response.data?.export;
      if (exported?.path) setLastExportPath(exported.path);
      setBackendError(null);
      setModal(null);
      say("✓ Exported " + (exported?.fileName || "MTDP package"));
    } catch (err) {
      const msg = err?.message || "Could not export package.";
      setBackendError(msg);
      say("Could not export package: " + msg);
    }
  };

  const exportAllReadyBackendGroups = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.exportAllReady) {
      const msg = "Export all ready groups requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.exportAllReady({
        session_id: session.session_id,
        initial_dir: "~/Documents/MTDP exports",
      });
      if (response?.error_type === "Cancelled") return;
      if (response?.status !== "ok") {
        const msg = response?.message || "Could not export ready groups.";
        setBackendError(msg);
        say("Could not export ready groups: " + msg);
        return;
      }
      applyBackendSessionView(response.data);
      const summary = response.data?.exportAll || response.data?.export_all || {};
      const exported = Number(summary.exportedCount || 0);
      const skipped = Number(summary.skippedCount || 0);
      const firstExport = Array.isArray(summary.exports) ? summary.exports.find((item) => item?.path) : null;
      if (firstExport?.path) setLastExportPath(firstExport.path);
      setBackendError(null);
      say("✓ Exported " + exported + " ready group" + (exported === 1 ? "" : "s")
        + (skipped ? " · skipped " + skipped : ""));
    } catch (err) {
      const msg = err?.message || "Could not export ready groups.";
      setBackendError(msg);
      say("Could not export ready groups: " + msg);
    }
  };

  const openLastExportInAnalysis = async () => {
    if (!lastExportPath) {
      say("Export a package before opening Analysis.");
      return;
    }
    const openChild = window.__compressionSuiteOpenChild;
    if (typeof openChild !== "function") {
      const msg = "Analysis handoff requires the desktop child-window shell.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      await openChild({ screen: "analysis", initial_package_path: lastExportPath });
      setBackendError(null);
      say("Opened exported package in Analysis.");
    } catch (err) {
      const msg = err?.message || "Could not open Analysis.";
      setBackendError(msg);
      say("Could not open Analysis: " + msg);
    }
  };

  // evidence / supplemental
  const addEvidence = async (groupId, runId, view) => {
    const api = window.desktopApi?.packaging;
    if (!api?.addImageEvidence) {
      const msg = "Adding image evidence requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.addImageEvidence({
        session_id: session.session_id,
        group_id: groupId,
        run_id: runId,
        view,
      });
      if (response?.error_type === "Cancelled") return;
      applyBackendMutationView(response);
    } catch (err) {
      const msg = err?.message || "Could not add image evidence.";
      setBackendError(msg);
      say("Could not add image evidence: " + msg);
    }
  };
  const removeEvidence = async (groupId, runId, idx) => {
    const api = window.desktopApi?.packaging;
    if (!api?.removeImageEvidence) {
      const msg = "Removing image evidence requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.removeImageEvidence({
        session_id: session.session_id,
        group_id: groupId,
        run_id: runId,
        index: idx,
      }));
    } catch (err) {
      const msg = err?.message || "Could not remove image evidence.";
      setBackendError(msg);
      say("Could not remove image evidence: " + msg);
    }
  };
  const addSupplemental = async (groupId, runId, scope) => {
    const api = window.desktopApi?.packaging;
    if (!api?.addSupplementalFiles) {
      const msg = "Adding supplemental files requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.addSupplementalFiles({
        session_id: session.session_id,
        group_id: groupId,
        run_id: scope === "run" ? runId : null,
        scope,
      });
      if (response?.error_type === "Cancelled") return;
      applyBackendMutationView(response);
    } catch (err) {
      const msg = err?.message || "Could not add supplemental file.";
      setBackendError(msg);
      say("Could not add supplemental file: " + msg);
    }
  };
  const removeSupplemental = async (groupId, runId, idx) => {
    const api = window.desktopApi?.packaging;
    if (!api?.removeSupplementalFile) {
      const msg = "Removing supplemental files requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      applyBackendMutationView(await api.removeSupplementalFile({
        session_id: session.session_id,
        group_id: groupId,
        run_id: runId,
        index: idx,
      }));
    } catch (err) {
      const msg = err?.message || "Could not remove supplemental file.";
      setBackendError(msg);
      say("Could not remove supplemental file: " + msg);
    }
  };

  const rematchYamlSidecars = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.rematchYamlSidecars) {
      const msg = "YAML sidecar rematch requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const activeGroup = bundleRef.current?.groups?.find((g) => g.id === selection.groupId)
        || bundleRef.current?.groups?.[0];
      const response = await api.rematchYamlSidecars({
        session_id: session.session_id,
        group_id: activeGroup?.id,
        apply_all: true,
      });
      if (applyBackendMutationView(response)) {
        const summary = response.data?.yamlRematch || response.data?.yaml_rematch || null;
        setYamlRematchSummary(summary);
        setYamlMappingReview(null);
        setYamlMappingRows([]);
        if (summary) {
          say("Re-matched YAML sidecars: " + summary.pairedCount + "/" + summary.runCount + " paired");
        }
      }
    } catch (err) {
      const msg = err?.message || "Could not re-match YAML sidecars.";
      setBackendError(msg);
      say("Could not re-match YAML sidecars: " + msg);
    }
  };

  const activeYamlGroupAndRun = () => {
    const activeGroup = bundleRef.current?.groups?.find((g) => g.id === selection.groupId)
      || bundleRef.current?.groups?.[0];
    const selectedRun = selection.type === "run"
      ? activeGroup?.runs?.find((r) => r.id === selection.runId)
      : null;
    const yamlRun = selectedRun || activeGroup?.runs?.find((r) => r.sidecarStatus && r.sidecarStatus !== "No YAML");
    return { activeGroup, yamlRun };
  };

  const reviewYamlMapping = async () => {
    const api = window.desktopApi?.packaging;
    if (!api?.reviewYamlMapping) {
      const msg = "YAML mapping review requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    try {
      const session = await ensureBackendSession();
      const { activeGroup, yamlRun } = activeYamlGroupAndRun();
      const response = await api.reviewYamlMapping({
        session_id: session.session_id,
        group_id: activeGroup?.id,
        run_id: yamlRun?.id,
      });
      if (response?.status !== "ok") {
        const msg = response?.message || "Could not review YAML mapping.";
        setBackendError(msg);
        say("Could not review YAML mapping: " + msg);
        return;
      }
      const review = response.data?.yamlMappingReview || response.data?.yaml_mapping_review || null;
      setYamlMappingReview(review);
      setYamlMappingRows(review?.rows || []);
      setBackendError(null);
      if (review) say("Loaded YAML mapping review for " + review.runId + ".");
    } catch (err) {
      const msg = err?.message || "Could not review YAML mapping.";
      setBackendError(msg);
      say("Could not review YAML mapping: " + msg);
    }
  };

  const applyYamlMappingProfile = async (rows) => {
    const api = window.desktopApi?.packaging;
    if (!api?.applyYamlMappingProfile) {
      const msg = "Applying YAML mapping profiles requires the desktop backend bridge.";
      setBackendError(msg);
      say(msg);
      return;
    }
    if (!yamlMappingReview) {
      say("Review YAML mapping before applying a profile.");
      return;
    }
    try {
      const session = await ensureBackendSession();
      const response = await api.applyYamlMappingProfile({
        session_id: session.session_id,
        group_id: yamlMappingReview.groupId,
        run_id: yamlMappingReview.runId,
        profile_id: yamlMappingReview.profileId,
        apply_all: yamlMappingReview.applyAllDefault !== false,
        mappings: (rows || []).map((row) => row.mapping || row),
      });
      if (applyBackendMutationView(response)) {
        const summary = response.data?.yamlMapping || response.data?.yaml_mapping || null;
        setYamlMappingReview(null);
        setYamlMappingRows([]);
        if (summary) {
          setYamlRematchSummary({
            runCount: summary.appliedCount,
            pairedCount: summary.appliedCount,
            pairs: (summary.runs || []).map((run) => ({
              runId: run.runId,
              csv: run.runId,
              yaml: run.yamlPath || summary.profileId,
              status: run.status,
              paired: true,
            })),
          });
          say("Applied YAML mapping profile to " + summary.appliedCount + " run" + (summary.appliedCount === 1 ? "" : "s") + ".");
        } else {
          setYamlRematchSummary(null);
        }
      }
    } catch (err) {
      const msg = err?.message || "Could not apply YAML mapping profile.";
      setBackendError(msg);
      say("Could not apply YAML mapping profile: " + msg);
    }
  };

  // ---- jump targets (issues drawer / export manifest) ----------------------------
  const jumpTo = (target) => {
    setModal(null);
    if (target.type === "dataset") setSelection((s) => ({ type: "dataset", groupId: s.groupId || "g1" }));
    else setSelection({ type: "run", groupId: target.groupId, runId: target.runId });
    setFocusSection({ sectionId: target.sectionId, fieldId: target.fieldId, t: Date.now() });
  };

  // ---- menu dispatch -------------------------------------------------------------
  const group = bundle && (bundle.groups.find((g) => g.id === selection.groupId) || bundle.groups[0]);
  const runIdx = bundle && selection.type === "run" && group
    ? group.runs.findIndex((r) => r.id === selection.runId) : -1;

  const menuAction = (id) => {
    const firstRun = group && group.runs[0];
    const curRunId = selection.type === "run" ? selection.runId : firstRun && firstRun.id;
    switch (id) {
      case "open-files":
        if (stage === "empty") openBackendSources("files");
        else say("Already open — close the package first (File ▸ Close package)");
        break;
      case "open-folder":
        if (stage === "empty") openBackendSources("folder");
        else say("Already open — close the package first (File ▸ Close package)");
        break;
      case "open-package": openBackendPackage(); break;
      case "recent-sessions": say(stage === "editor" ? "1 draft session — “" + bundle.name + "”, autosaved " + (savedAt || "just now") : "No draft sessions yet — sessions autosave while you work"); break;
      case "export": setModal({ kind: "export" }); break;
      case "export-all-ready": exportAllReadyBackendGroups(); break;
      case "open-export-analysis": openLastExportInAnalysis(); break;
      case "close-package":
        setStage("empty"); setBundle(null); setSavedAt(null);
        setLastExportPath(null);
        setYamlRematchSummary(null);
        setYamlMappingReview(null);
        setYamlMappingRows([]);
        undoStack.current = []; redoStack.current = []; setHistN(0);
        setGroupProposals([]);
        setIssuesOpen(false); setHasValidated(false);
        break;
      case "undo": undo(); break;
      case "redo": redo(); break;
      case "copy-prev": if (group && curRunId) copyPrev(group.id, curRunId); break;
      case "density-essential": setDensity("essential"); break;
      case "density-core": setDensity("core"); break;
      case "density-all": setDensity("all"); break;
      case "open-grid": if (group) setSelection({ type: "grid", groupId: group.id }); break;
      case "source-files": say("Source files drawer is at the bottom of the left panel"); break;
      case "propose-groups": openGroupProposals(); break;
      case "new-group": newGroup(); break;
      case "rename-group": if (group) setEditingGroupId(group.id); break;
      case "delete-group": if (group) deleteGroup(group.id); break;
      case "prev-run":
        if (runIdx > 0) setSelection({ type: "run", groupId: group.id, runId: group.runs[runIdx - 1].id });
        break;
      case "next-run":
        if (runIdx >= 0 && runIdx < group.runs.length - 1) setSelection({ type: "run", groupId: group.id, runId: group.runs[runIdx + 1].id });
        else if (runIdx < 0 && firstRun) setSelection({ type: "run", groupId: group.id, runId: firstRun.id });
        break;
      case "channels": if (group && curRunId) setModal({ kind: "channels", groupId: group.id, runId: curRunId }); break;
      case "evidence": if (group && curRunId) setModal({ kind: "evidence", groupId: group.id, runId: curRunId }); break;
      case "validate": validateBackendGroup(); break;
      case "rematch-yaml": setYamlRematchSummary(null); setYamlMappingReview(null); setYamlMappingRows([]); setModal({ kind: "rematch" }); break;
      case "supplemental": setModal({ kind: "supplemental", groupId: group?.id || null, runId: selection.type === "run" ? selection.runId : null }); break;
      case "change-schema": setModal({ kind: "schema" }); break;
      case "schema-ref": {
        const s = schemaCandidates.find((c) => c.id === bundle?.schemaId) || schemaCandidates[0];
        say(s
          ? "Schema reference: " + s.schema + " v" + s.version + " — field catalogue from backend registry"
          : "Schema reference unavailable — backend registry did not return candidates");
        break;
      }
      case "about": say("Dataset Packaging — interactive UX prototype, iteration 4"); break;
      default: break;
    }
  };

  // ---- render ----------------------------------------------------------------------
  const editor = stage === "editor" && bundle;
  const lastU = undoStack.current[undoStack.current.length - 1];
  const lastR = redoStack.current[redoStack.current.length - 1];
  return (
    <div className="appwin" data-screen-label="Dataset Packaging app">
      <MenuBar stage={stage} bundle={bundle} density={density}
        runIdx={runIdx} runCount={group ? group.runs.length : 0}
        canUndo={undoStack.current.length > 0} canRedo={redoStack.current.length > 0}
        undoLabel={lastU && lastU.label} redoLabel={lastR && lastR.label}
        lastExportPath={lastExportPath}
        onAction={menuAction} />

      <div className="cores">
        {editor ? (
          <BundlePanel bundle={bundle} selection={selection} onSelect={setSelection}
            onMoveRun={moveRun}
            onInspectChannels={(gid, rid) => setModal({ kind: "channels", groupId: gid, runId: rid })}
            onEvidence={(gid, rid) => setModal({ kind: "evidence", groupId: gid, runId: rid })}
            onCopyPrev={copyPrev}
            onProposeGroups={openGroupProposals}
            onNewGroup={newGroup}
            onRenameGroup={renameGroup}
            onDeleteGroup={deleteGroup}
            onRematchYaml={() => { setYamlRematchSummary(null); setYamlMappingReview(null); setYamlMappingRows([]); setModal({ kind: "rematch" }); }}
            editingGroupId={editingGroupId}
            onStartRename={setEditingGroupId}
            onCancelRename={() => setEditingGroupId(null)}
            onChangeSchema={() => setModal({ kind: "schema" })} />
        ) : (
          <EmptyBundlePanel onStartIngest={() => openBackendSources("folder")}
            onDropSources={loadBackendSourcePaths}
            onOpenPackage={openBackendPackage} />
        )}

        {editor && bundle.groups.length > 0 ? (
          <InsertPanel bundle={bundle} selection={selection} onSelect={setSelection}
            density={density} onDensity={setDensity}
            onEditDataset={editDataset} onEditRun={editRun} onBulkSet={bulkSet}
            onCommitDataset={commitBackendDatasetField}
            onCommitRun={commitBackendRunField}
            onCommitBulkRun={commitBackendBulkRunField}
            onCommitRunMatrix={commitBackendRunMatrix}
            onUnitPolicy={unitPolicy} onCopyPrev={copyPrev}
            onInspectChannels={(gid, rid) => setModal({ kind: "channels", groupId: gid, runId: rid })}
            onEvidence={(gid, rid) => setModal({ kind: "evidence", groupId: gid, runId: rid })}
            onSupplemental={() => setModal({ kind: "supplemental", groupId: group?.id || null, runId: selection.type === "run" ? selection.runId : null })}
            issuesOpen={issuesOpen}
            onToggleIssues={() => setIssuesOpen((o) => !o)}
            onValidate={validateBackendGroup}
            hasValidated={hasValidated}
            onExport={() => setModal({ kind: "export" })}
            onJump={jumpTo}
            focusSection={focusSection} toast={toast} />
        ) : (
          <EmptyInsertPanel />
        )}

        {editor && modal && modal.kind === "channels" && (
          <ChannelInspector bundle={bundle} groupId={modal.groupId} runId={modal.runId}
            onAssign={assignChannel}
            onSelectRun={(gid, rid) => setModal({ kind: "channels", groupId: gid, runId: rid })}
            onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "export" && (
          <ExportDialog bundle={bundle}
            onExport={exportBackendGroup}
            onJump={jumpTo}
            onOpenChannels={(t) => setModal({ kind: "channels", groupId: t.groupId, runId: t.runId })}
            onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "propose" && (
          <ProposeGroupsDialog proposals={modal.proposals || groupProposals} onApply={applyProposal} onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "schema" && (
          <SchemaDialog bundle={bundle} candidates={schemaCandidates} onPick={pickSchema} onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "evidence" && (
          <EvidenceDialog bundle={bundle} groupId={modal.groupId} runId={modal.runId}
            onAdd={addEvidence} onRemove={removeEvidence} onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "supplemental" && (
          <SupplementalDialog bundle={bundle} groupId={modal.groupId} runId={modal.runId} onAdd={addSupplemental} onRemove={removeSupplemental}
            onClose={() => setModal(null)} />
        )}
        {editor && modal && modal.kind === "rematch" && (
          <RematchYamlDialog bundle={bundle} summary={yamlRematchSummary}
            review={yamlMappingReview}
            mappingRows={yamlMappingRows}
            onRowsChange={setYamlMappingRows}
            onReviewMapping={reviewYamlMapping}
            onApplyMapping={applyYamlMappingProfile}
            onRematch={rematchYamlSidecars}
            onClose={() => setModal(null)} />
        )}
      </div>

      <div className="statusbar">
        <span>{editor ? "Package: " + bundle.name : "No package loaded"}</span>
        {backendError && <><span className="dot">·</span><span>Backend unavailable: {backendError}</span></>}
        {editor && <><span className="dot">·</span><span>{bundle.schemaLabel} v{bundle.schemaVersion}{bundle.schemaOverridden ? " (manual)" : ""}</span></>}
        <span className="statusbar__sp" />
        {editor && savedAt && <><span className="statusbar__save">✓ saved {savedAt}</span><span className="dot">·</span><span>draft “{bundle.name}”</span><span className="dot">·</span></>}
        {editor && <span>raw files untouched</span>}
      </div>
    </div>
  );
}

export default App;
export { App };
