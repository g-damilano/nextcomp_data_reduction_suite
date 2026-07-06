from __future__ import annotations

from typing import Any

from audit.audit_block_models import AuditAggregatePacket, AuditBlock, AuditRunPacket
from methods.core.method_result import MethodRunResult


RUN_BLOCK_ORDER = (
    "run_identity_and_status",
    "run_stress_strain_reduction",
    "run_bending_evidence",
    "run_curve_shape_diagnostic",
    "run_validation_evidence",
    "run_technical_trace_links",
)

AGGREGATE_BLOCK_ORDER = (
    "aggregate_dataset_cohort_population",
    "aggregate_curve_family",
    "aggregate_curve_shape_diagnostics",
    "aggregate_evidence_summary",
)

def build_audit_blocks(
    result: MethodRunResult,
    procedure_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    procedure_index = procedure_index or {}
    run_packets = [
        AuditRunPacket(run_id=run_id, blocks=_run_blocks(result, run_id, procedure_index))
        for run_id in result.source.run_ids
    ]
    aggregate_packet = AuditAggregatePacket(blocks=_aggregate_blocks(result))
    return {
        "schema_id": "audit.audit_blocks.v0_1",
        "schema_version": "0.1.0",
        "method_id": result.method_package.method_id,
        "method_version": result.method_package.version,
        "source_index_member": "audit/procedure_evidence_index.json",
        "run_packets": [packet.to_dict() for packet in run_packets],
        "aggregate_packet": aggregate_packet.to_dict(),
        "block_order": {
            "run": list(RUN_BLOCK_ORDER),
            "aggregate": list(AGGREGATE_BLOCK_ORDER),
        },
    }


def build_audit_block_index_from_blocks(audit_blocks: dict[str, Any]) -> dict[str, Any]:
    run_packets = audit_blocks.get("run_packets", []) if isinstance(audit_blocks.get("run_packets"), list) else []
    aggregate_packet = audit_blocks.get("aggregate_packet", {}) if isinstance(audit_blocks.get("aggregate_packet"), dict) else {}
    blocks: list[dict[str, Any]] = []
    for packet in run_packets:
        for block in packet.get("blocks", []) if isinstance(packet, dict) else []:
            if isinstance(block, dict):
                blocks.append(_block_index_row(block))
    aggregate_blocks = []
    for block in aggregate_packet.get("blocks", []) if isinstance(aggregate_packet.get("blocks"), list) else []:
        if isinstance(block, dict):
            row = _block_index_row(block)
            aggregate_blocks.append(row)
            blocks.append(row)
    return {
        "schema_id": "audit.audit_block_index.v0_1",
        "schema_version": "0.1.0",
        "method_id": audit_blocks.get("method_id", ""),
        "method_version": audit_blocks.get("method_version", ""),
        "source_index_member": "audit/procedure_evidence_index.json",
        "audit_blocks_member": "audit/audit_blocks.json",
        "run_packets": [
            {
                "run_id": packet.get("run_id"),
                "packet_id": packet.get("packet_id"),
                "blocks": [_block_index_row(block) for block in packet.get("blocks", []) if isinstance(block, dict)],
            }
            for packet in run_packets
            if isinstance(packet, dict)
        ],
        "aggregate_packet": {
            "packet_id": aggregate_packet.get("packet_id", "aggregate_packet"),
            "blocks": aggregate_blocks,
        },
        "blocks": blocks,
        "summary": {
            "run_packet_count": len(run_packets),
            "aggregate_block_count": len(aggregate_blocks),
            "block_count": len(blocks),
            "stress_strain_grouping": "boundary, stress derivation, max point, failure strain, and chord slope evidence grouped per run",
            "bending_separate": True,
        },
    }


def _block_index_row(block: dict[str, Any]) -> dict[str, Any]:
    evidence_refs = block.get("evidence_refs") if isinstance(block.get("evidence_refs"), dict) else {}
    operation_refs = block.get("operation_refs") if isinstance(block.get("operation_refs"), list) else []
    links = block.get("links") if isinstance(block.get("links"), dict) else {}
    operation_types = [
        str(row.get("operation_type") or "")
        for row in operation_refs
        if isinstance(row, dict) and row.get("operation_type")
    ]
    return {
        "block_id": block.get("block_id"),
        "block_type": block.get("block_type"),
        "block_role": block.get("block_type"),
        "scope": block.get("scope"),
        "run_id": block.get("run_id"),
        "title": block.get("title"),
        "status": block.get("status", "recorded"),
        "operation_types": operation_types,
        "operation_refs": operation_refs,
        "artifact_refs": [
            str(value)
            for value in evidence_refs.values()
            if value not in (None, "")
        ],
        "workbench_links": [
            str(value)
            for value in links.values()
            if value not in (None, "")
        ],
        "summary_keys": sorted(str(key) for key in (block.get("summary") or {}).keys())
        if isinstance(block.get("summary"), dict)
        else [],
    }


def _run_blocks(result: MethodRunResult, run_id: str, procedure_index: dict[str, Any]) -> list[AuditBlock]:
    specimen = _row_by_run(result.specimen_results, run_id)
    steps = _procedure_steps_for_run(procedure_index, run_id)
    return [
        _identity_block(run_id, specimen, steps, result),
        _stress_strain_block(run_id, specimen, steps, result),
        _bending_block(run_id, specimen, steps, result),
        _curve_shape_block(run_id, specimen, steps, result),
        _validation_block(run_id, steps, result),
        _technical_trace_block(run_id, steps, result),
    ]


def _identity_block(run_id: str, specimen: dict[str, Any], steps: list[dict[str, Any]], result: MethodRunResult) -> AuditBlock:
    failure_observation = _failure_observation_evidence(specimen, result, run_id)
    return AuditBlock(
        block_id=f"{run_id}:run_identity_and_status",
        block_type="run_identity_and_status",
        title="Run identity and acquisition context",
        scope="run",
        run_id=run_id,
        purpose="Identify the specimen, sample, geometry, and operator validity metadata before reading calculation evidence.",
        evidence_refs={
            "specimen_results": "method_outputs/specimen_results.csv",
        },
        operation_refs=_operation_refs(steps, {"map_scalar", "derive_area"}),
        summary={
            "specimen_name": specimen.get("specimen_name", ""),
            "sample_id": specimen.get("sample_id", ""),
            "validity": specimen.get("validity", ""),
            "failure_mode": specimen.get("failure_mode", ""),
            "primary_failure_mode": failure_observation.get("Failure mode", ""),
            "failure_location": failure_observation.get("Failure location", ""),
            "invalid_specimen_reason": failure_observation.get("Invalid specimen reason", ""),
            "failure_analysis_notes": failure_observation.get("Notes", ""),
        },
        tables={
            "geometry": [
                {
                    "width_mm": specimen.get("width_mm"),
                    "thickness_mm": specimen.get("thickness_mm"),
                    "area_mm2": specimen.get("area_mm2"),
                }
            ],
            "failure_observation": [failure_observation],
        },
        links={"workbench": _workbench_link(run_id, "run_identity_and_status")},
    )


def _stress_strain_block(
    run_id: str,
    specimen: dict[str, Any],
    steps: list[dict[str, Any]],
    result: MethodRunResult,
) -> AuditBlock:
    boundary = _boundary_for_run(result, run_id)
    chord_step = _operation_for_run(result, run_id, "chord_slope")
    chord_evidence = chord_step.get("evidence", {}) if isinstance(chord_step.get("evidence"), dict) else {}
    left_anchor = chord_evidence.get("left_anchor", {}) if isinstance(chord_evidence.get("left_anchor"), dict) else {}
    right_anchor = chord_evidence.get("right_anchor", {}) if isinstance(chord_evidence.get("right_anchor"), dict) else {}
    calculation_row = {
        "width_mm": specimen.get("width_mm"),
        "thickness_mm": specimen.get("thickness_mm"),
        "area_mm2": specimen.get("area_mm2"),
        "Fmax_N": specimen.get("max_load_N"),
        "strength_MPa": specimen.get("compressive_strength_MPa"),
        "failure_strain": specimen.get("compressive_failure_strain"),
        "modulus_MPa": specimen.get("compressive_modulus_MPa"),
        "chord_stress_at_0_0005_MPa": left_anchor.get("y"),
        "chord_stress_at_0_0025_MPa": right_anchor.get("y"),
    }
    end_index = _boundary_interval_value(boundary, "end_index", specimen.get("boundary_end_index"))
    start_index = _boundary_interval_value(boundary, "start_index", specimen.get("boundary_start_index"))
    return AuditBlock(
        block_id=f"{run_id}:run_stress_strain_reduction",
        block_type="run_stress_strain_reduction",
        title="Stress-strain reduction evidence",
        scope="run",
        run_id=run_id,
        purpose="Grouped evidence for the bounded stress-strain reduction and derived ISO 14126 values.",
        evidence_refs={
            "bounded_curve": f"method_outputs/curves/{_safe_run(run_id)}_stress_strain_bounded.csv",
            "full_curve_context": f"method_outputs/curves/{_safe_run(run_id)}_stress_strain_full.csv",
            "boundary": "audit/boundary_resolution.json",
            "max_point": _operation_ref(result, run_id, "max_point"),
            "failure_strain": _operation_ref(result, run_id, "value_at_max"),
            "chord_slope": _operation_ref(result, run_id, "chord_slope"),
            "calculation_table": f"audit/audit_blocks.json#/runs/{run_id}/run_stress_strain_reduction/tables/calculation",
            "workbench": _workbench_link(run_id, "run_stress_strain_reduction"),
        },
        operation_refs=_operation_refs(
            steps,
            {
                "resolve_experiment_boundaries",
                "construct_mean_series",
                "derive_stress",
                "max_point",
                "value_at_max",
                "value_at_index",
                "chord_slope",
            },
        ),
        summary={
            "bounded_reduction": specimen.get("bounded_reduction", bool(boundary)),
            "end_policy": specimen.get("boundary_end_policy") or boundary.get("end_policy", ""),
            "strength_MPa": specimen.get("compressive_strength_MPa"),
            "failure_strain": specimen.get("compressive_failure_strain"),
            "modulus_MPa": specimen.get("compressive_modulus_MPa"),
        },
        markers={
            "experiment_start": {"index": start_index},
            "experiment_end": {"index": end_index},
            "max_load_strength": {
                "index": (
                    specimen.get("max_stress_point_index")
                    or specimen.get("max_load_point_index")
                    or specimen.get("max_stress_index")
                    or specimen.get("max_load_index")
                ),
                "bounded_index": specimen.get("max_stress_index") or specimen.get("max_load_index"),
                "load_N": specimen.get("max_load_N"),
                "stress_MPa": specimen.get("compressive_strength_MPa"),
            },
            "failure_strain": {"strain": specimen.get("compressive_failure_strain")},
            "chord_anchors": {
                "start": left_anchor or {"x": 0.0005},
                "end": right_anchor or {"x": 0.0025},
            },
            "chord_line": {
                "x_start": (left_anchor or {}).get("x", 0.0005),
                "y_start": (left_anchor or {}).get("y"),
                "x_end": (right_anchor or {}).get("x", 0.0025),
                "y_end": (right_anchor or {}).get("y"),
            },
        },
        tables={"calculation": [calculation_row]},
        links={"workbench": _workbench_link(run_id, "run_stress_strain_reduction")},
    )


def _bending_block(
    run_id: str,
    specimen: dict[str, Any],
    steps: list[dict[str, Any]],
    result: MethodRunResult,
) -> AuditBlock:
    operation = _operation_for_run(result, run_id, "bending_diagnostic")
    output = operation.get("outputs", {}).get("bending_diagnostic", {}) if isinstance(operation.get("outputs"), dict) else {}
    output = output if isinstance(output, dict) else {}
    window = output.get("window", {}) if isinstance(output.get("window"), dict) else {}
    return AuditBlock(
        block_id=f"{run_id}:run_bending_evidence",
        block_type="run_bending_evidence",
        title="Bending evidence",
        scope="run",
        run_id=run_id,
        purpose="Bending diagnostic evidence remains separate from stress-strain reduction.",
        evidence_refs={
            "operation_record": _operation_ref(result, run_id, "bending_diagnostic"),
            "inspection_record": (operation.get("inspection_refs") or [""])[0] if isinstance(operation.get("inspection_refs"), list) else "",
            "workbench": _workbench_link(run_id, "run_bending_evidence"),
        },
        operation_refs=_operation_refs(steps, {"bending_diagnostic", "bending_pattern_assessment"}),
        summary={
            "classification": specimen.get("bending_pattern") or output.get("pattern_classification"),
            "threshold_percent": specimen.get("bending_threshold_percent") or output.get("threshold_percent"),
            "max_bending_percent": specimen.get("bending_max_percent") or output.get("max_bending_percent"),
            "points_above_threshold": specimen.get("bending_points_above_threshold") or output.get("points_above_threshold"),
            "fraction_above_threshold": specimen.get("bending_fraction_above_threshold") or output.get("fraction_above_threshold"),
        },
        markers={
            "threshold_line": {"bending_percent": specimen.get("bending_threshold_percent") or output.get("threshold_percent")},
            "assessment_window_10_90_fmax": {
                "window_percent_of_max_load": output.get("window_percent_of_max_load", [10, 90]),
                "load_window_N": output.get("load_window_N"),
                "lower_load_N": window.get("lower_load_N"),
                "upper_load_N": window.get("upper_load_N"),
            },
            "exceedance_points": {"count": output.get("points_above_threshold")},
            "exceedance_segments": output.get("segments", []),
        },
        tables={
            "summary": [
                {
                    "threshold_percent": specimen.get("bending_threshold_percent") or output.get("threshold_percent"),
                    "points_above_threshold": specimen.get("bending_points_above_threshold") or output.get("points_above_threshold"),
                    "fraction_above_threshold": specimen.get("bending_fraction_above_threshold") or output.get("fraction_above_threshold"),
                    "longest_segment_points": specimen.get("bending_longest_segment_points") or _longest_segment_points(output),
                    "max_bending_percent": specimen.get("bending_max_percent") or output.get("max_bending_percent"),
                    "classification": specimen.get("bending_pattern") or output.get("pattern_classification"),
                }
            ]
        },
        links={"workbench": _workbench_link(run_id, "run_bending_evidence")},
    )


def _curve_shape_block(
    run_id: str,
    specimen: dict[str, Any],
    steps: list[dict[str, Any]],
    result: MethodRunResult,
) -> AuditBlock:
    score = _curve_shape_score_for_run(result, run_id)
    if not score:
        score = {
            "run_id": run_id,
            "specimen": specimen.get("specimen_name", ""),
            "cohort_id": "",
            "cohort_label": "",
            "evaluable": False,
            "distance_note": "Curve-shape diagnostic evidence unavailable: missing acceptance/curve_family/curve_diagnostic_scores.csv.",
            "diagnostic_classification": "CURVE_SHAPE_NOT_ASSESSED",
        }
    return AuditBlock(
        block_id=f"{run_id}:run_curve_shape_diagnostic",
        block_type="run_curve_shape_diagnostic",
        title="Curve-shape diagnostic evidence",
        scope="run",
        run_id=run_id,
        purpose="Show how this run compares to the comparable cohort characteristic curve.",
        evidence_refs={
            "curve_diagnostic_report": "acceptance/curve_family/curve_diagnostic_report.json",
            "scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
            "reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
            "residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
            "policy": "acceptance/curve_family/curve_diagnostic_policy.json",
        },
        operation_refs=[_virtual_operation_ref("curve_family_diagnostic")],
        summary={
            "cohort_id": score.get("cohort_id", ""),
            "cohort_label": score.get("cohort_label", ""),
            "evaluable": score.get("evaluable", ""),
            "distance_rms": score.get("distance_rms", ""),
            "distance_rank": score.get("distance_rank", ""),
            "threshold_method": score.get("threshold_method", ""),
            "secondary_threshold_method": score.get("secondary_threshold_method", ""),
            "secondary_threshold_available": score.get("secondary_threshold_available", ""),
            "Qexp": score.get("Qexp", ""),
            "Qcrit_95": score.get("Qcrit_95", ""),
            "dixon_decision": score.get("dixon_decision", ""),
            "masking_companion_flag": score.get("masking_companion_flag", ""),
            "masking_risk": score.get("masking_risk", ""),
            "threshold_decision_sources": score.get("threshold_decision_sources", ""),
            "robust_z": score.get("robust_z", score.get("z_mad", "")),
            "z_mad": score.get("z_mad", score.get("robust_z", "")),
            "mad_upper_z": score.get("mad_upper_z", score.get("z_mad_upper", "")),
            "z_mad_upper": score.get("z_mad_upper", score.get("mad_upper_z", "")),
            "threshold_value": score.get("threshold_value", ""),
            "distance_note": score.get("distance_note", ""),
            "curve_shape_classification": score.get("diagnostic_classification", "CURVE_SHAPE_NOT_ASSESSED"),
            "diagnostic_consequence": _curve_shape_evidence_consequence(score),
        },
        tables={"score": [score]},
        links={"workbench": _workbench_link(run_id, "curve_family_diagnostic_view")},
    )


def _validation_block(run_id: str, steps: list[dict[str, Any]], result: MethodRunResult) -> AuditBlock:
    checks = [
        row for row in result.validation_report.get("checks", [])
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id
    ]
    failed = [row for row in checks if row.get("status") == "fail"]
    warned = [row for row in checks if row.get("status") == "warn"]
    return AuditBlock(
        block_id=f"{run_id}:run_validation_evidence",
        block_type="run_validation_evidence",
        title="Data compliance evidence",
        scope="run",
        run_id=run_id,
        purpose="ISO 14126 reference deviations and warnings affecting the run values.",
        evidence_refs={
            "validation_report": "validation/validation_report.json",
            "deviations": "validation/deviations.csv",
        },
        operation_refs=_operation_refs(steps, {"validation_summary", "validation_check"}),
        summary={"checks": len(checks), "failed": len(failed), "warnings": len(warned)},
        tables={"summary": [{"checks": len(checks), "failed": len(failed), "warnings": len(warned)}], "details": checks},
        links={"workbench": _workbench_link(run_id, "run_validation_evidence")},
    )


def _technical_trace_block(run_id: str, steps: list[dict[str, Any]], result: MethodRunResult) -> AuditBlock:
    return AuditBlock(
        block_id=f"{run_id}:run_technical_trace_links",
        block_type="run_technical_trace_links",
        title="Technical trace links",
        scope="run",
        run_id=run_id,
        purpose="Collapsed artifact and operation trace links for detailed replay in the Method Development Workbench.",
        evidence_refs={
            "operation_log": "audit/operation_log.json",
            "procedure_evidence_index": "audit/procedure_evidence_index.json",
            "bounded_curve": f"method_outputs/curves/{_safe_run(run_id)}_stress_strain_bounded.csv",
            "full_curve": f"method_outputs/curves/{_safe_run(run_id)}_stress_strain_full.csv",
        },
        operation_refs=_operation_refs(
            steps,
            {
                "resolve_experiment_boundaries",
                "construct_mean_series",
                "derive_stress",
                "max_point",
                "value_at_max",
                "value_at_index",
                "chord_slope",
                "bending_diagnostic",
                "bending_pattern_assessment",
                "curve_family_diagnostic",
                "validation_summary",
                "validation_check",
            },
        ),
        summary={"operation_refs": len(steps)},
        tables={},
        links={"workbench": _workbench_link(run_id, "technical_trace")},
    )


def _selection_block(run_id: str, steps: list[dict[str, Any]], result: MethodRunResult) -> AuditBlock:
    selection = _selection_for_run(result, run_id)
    flags = [row for row in result.run_flags if str(row.get("run_id") or "") == run_id]
    return AuditBlock(
        block_id=f"{run_id}:run_selection_consequence",
        block_type="run_selection_consequence",
        title="Report inclusion evidence",
        scope="run",
        run_id=run_id,
        purpose="Show whether this run is used in the reported results and why.",
        evidence_refs={
            "acceptance_report": "acceptance/acceptance_report.json",
            "run_flags": "acceptance/run_flags.csv",
            "final_report_runs": "acceptance/final_report_runs.csv",
        },
        operation_refs=_operation_refs(steps, {"final_selection", "selection_set_build"}),
        summary={
            "machine_state": selection.get("machine_state") or selection.get("machine_included", ""),
            "human_decision": selection.get("human_decision") or selection.get("human_decision_type", ""),
            "final_included": selection.get("final_included", selection.get("included", "")),
            "reason": selection.get("human_decision_reason") or selection.get("override_reason", ""),
        },
        tables={"selection": [selection], "flags": flags},
        links={"workbench": _workbench_link(run_id, "run_selection_consequence")},
    )


def _aggregate_blocks(result: MethodRunResult) -> list[AuditBlock]:
    curve_summary = {}
    if isinstance(result.curve_family_assessment, dict):
        curve_summary = result.curve_family_assessment.get("summary", {}) if isinstance(result.curve_family_assessment.get("summary"), dict) else {}
    diagnostic_report = result.curve_shape_diagnostic_report if isinstance(result.curve_shape_diagnostic_report, dict) else {}
    diagnostic_summary = diagnostic_report.get("summary", {}) if isinstance(diagnostic_report.get("summary"), dict) else {}
    cohorts = diagnostic_report.get("cohorts", []) if isinstance(diagnostic_report.get("cohorts"), list) else []
    return [
        AuditBlock(
            block_id="aggregate:aggregate_dataset_cohort_population",
            block_type="aggregate_dataset_cohort_population",
            title="Dataset / cohort population",
            scope="aggregate",
            purpose="Comparable curve cohort used for whole-dataset curve-shape evidence.",
            evidence_refs={
                "curve_diagnostic_report": "acceptance/curve_family/curve_diagnostic_report.json",
                "curve_diagnostic_policy": "acceptance/curve_family/curve_diagnostic_policy.json",
            },
            operation_refs=[_virtual_operation_ref("curve_family_diagnostic")],
            summary=diagnostic_summary,
            tables={"cohorts": cohorts},
            links={"workbench": "workbench/index.html#tab=acceptance&context=curve_family_diagnostic"},
        ),
        AuditBlock(
            block_id="aggregate:aggregate_curve_family",
            block_type="aggregate_curve_family",
            title="Aggregate curve-family evidence",
            scope="aggregate",
            purpose="Boundary-aligned whole-dataset curve-family evidence with diagnostic rank and state context.",
            evidence_refs={
                "aligned_curves": "report/aligned_curves.csv",
                "plot_spec": "report/vega_specs/aggregate_stress_strain_mean_variability.json",
                "curve_family_report": "acceptance/curve_family/curve_family_report.json",
                "curve_diagnostic_scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
            },
            operation_refs=[_virtual_operation_ref("aggregate_curve_family")],
            summary=curve_summary,
            tables={"curve_shape_scores": result.curve_shape_diagnostic_scores or []},
            links={"workbench": "workbench/index.html#tab=acceptance&context=curve_family"},
        ),
        AuditBlock(
            block_id="aggregate:aggregate_curve_shape_diagnostics",
            block_type="aggregate_curve_shape_diagnostics",
            title="Curve-shape outlier diagnostics",
            scope="aggregate",
            purpose="RMS standardized residual distance ranking and threshold evidence for shape outliers.",
            evidence_refs={
                "curve_diagnostic_report": "acceptance/curve_family/curve_diagnostic_report.json",
                "curve_diagnostic_scores": "acceptance/curve_family/curve_diagnostic_scores.csv",
                "curve_diagnostic_reference_curve": "acceptance/curve_family/curve_diagnostic_reference_curve.csv",
                "curve_diagnostic_residuals": "acceptance/curve_family/curve_diagnostic_residuals.csv",
                "curve_diagnostic_policy": "acceptance/curve_family/curve_diagnostic_policy.json",
            },
            operation_refs=[_virtual_operation_ref("curve_family_diagnostic")],
            summary=diagnostic_summary,
            tables={"scores": result.curve_shape_diagnostic_scores or [], "cohorts": cohorts},
            links={"workbench": "workbench/index.html#tab=acceptance&context=curve_family_diagnostic"},
        ),
        AuditBlock(
            block_id="aggregate:aggregate_evidence_summary",
            block_type="aggregate_evidence_summary",
            title="Evidence summary for downstream decision-making",
            scope="aggregate",
            purpose="Concise evidence categories consumed later by the Decision Register.",
            evidence_refs={
                "run_flags": "acceptance/run_flags.csv",
                "curve_diagnostic_flags": "acceptance/curve_family/curve_diagnostic_flags.csv",
                "validation_deviations": "validation/deviations.csv",
            },
            operation_refs=[_virtual_operation_ref("curve_family_diagnostic")],
            summary={
                "flag_count": len(result.run_flags or []),
                "curve_shape_flag_count": len(result.curve_shape_diagnostic_flags or []),
                "validation_deviation_count": len(result.validation_deviations or []),
            },
            tables={"evidence_flags": _evidence_flag_rows(result)},
            links={"workbench": "workbench/index.html#tab=acceptance&context=evidence_flags"},
        ),
    ]


def _procedure_steps_for_run(procedure_index: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    runs = procedure_index.get("runs") if isinstance(procedure_index.get("runs"), dict) else {}
    payload = runs.get(run_id, {})
    if isinstance(payload, dict):
        steps = payload.get("steps", [])
        return [step for step in steps if isinstance(step, dict)]
    if isinstance(payload, list):
        return [step for step in payload if isinstance(step, dict)]
    return []


def _failure_observation_evidence(
    specimen: dict[str, Any],
    result: MethodRunResult,
    run_id: str,
) -> dict[str, Any]:
    return {
        "Failure mode": _failure_mode_label(specimen),
        "Failure location": _failure_location_label(specimen),
        "Invalid specimen reason": "; ".join(_invalid_specimen_reasons(specimen, result, run_id)),
        "Bending/failure observation": _enum_label_with_detail(
            specimen.get("visible_buckling_or_bending_observation"),
            specimen.get("visible_buckling_or_bending_observation_other"),
        ),
        "Bending evidence": _bending_evidence_label(specimen),
        "Notes": _first_present(
            specimen,
            ("failure_analysis_notes", "rejection_reason", "human_decision_reason", "run_notes"),
        ),
    }


def _failure_mode_label(specimen: dict[str, Any]) -> str:
    for key in ("primary_failure_mode", "failure_mode"):
        mode = _iso_failure_mode_value(specimen.get(key))
        if mode != "not recorded":
            return mode
    return "not recorded"


def _iso_failure_mode_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "not recorded"
    normalized = text.casefold().replace("-", "_").replace(" ", "_")
    normalized = "_".join(part for part in normalized.split("_") if part)
    mapping = {
        "in_plane_shear": "in-plane shear",
        "inplaneshear": "in-plane shear",
        "complex": "complex",
        "through_thickness_shear": "through-thickness shear",
        "throughthicknessshear": "through-thickness shear",
        "splitting": "splitting",
        "delamination": "delamination",
        "not_recorded": "not recorded",
        "unknown": "not recorded",
        "valid": "not recorded",
        "invalid": "not recorded",
        "accepted": "not recorded",
        "rejected": "not recorded",
        "0": "not recorded",
        "1": "not recorded",
    }
    return mapping.get(normalized, "not recorded")


def _failure_location_label(specimen: dict[str, Any]) -> str:
    text = str(specimen.get("failure_location") or "").strip()
    if not text:
        return "not recorded"
    normalized = text.casefold().replace("-", "_").replace(" ", "_")
    if normalized in {"not_recorded", "unknown", "none", "null"}:
        return "not recorded"
    return _enum_label(normalized)


def _invalid_specimen_reasons(
    specimen: dict[str, Any],
    result: MethodRunResult,
    run_id: str,
) -> list[str]:
    reasons: list[str] = []
    validity = str(specimen.get("validity") or "").casefold()
    invalid_reason = str(specimen.get("invalid_specimen_reason") or "").strip()
    bending = str(specimen.get("bending_pattern") or "")
    location = str(specimen.get("failure_location") or "").casefold()
    flag_text = " ".join(
        str(flag.get(key) or "")
        for flag in _run_flags(result, run_id)
        for key in ("flag_id", "rule_id", "message", "reason")
    ).casefold()
    if validity in {"invalid", "rejected", "false", "0"} or "user_validity_invalid" in flag_text:
        reasons.append("operator marked invalid")
    if invalid_reason and invalid_reason.casefold() not in {"none", "not_recorded", "not recorded"}:
        reasons.append(_enum_label_with_detail(invalid_reason, specimen.get("invalid_specimen_reason_other")))
    if bending == "FAIL_SUSTAINED_BENDING":
        reasons.append("bending non-compliance")
    elif bending in {"PASS_WITH_SPIKES", "WARN_TRANSIENT_BENDING"}:
        reasons.append("bending review")
    if any(token in location for token in ("grip", "end_block")):
        reasons.append("grip/end block failure")
    if "tab" in location:
        reasons.append("end tab failure")
    return _dedupe_text(reasons)


def _run_flags(result: MethodRunResult, run_id: str) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    payload = result.acceptance_report if isinstance(result.acceptance_report, dict) else {}
    for flag in payload.get("flags", []) or []:
        if isinstance(flag, dict) and str(flag.get("run_id") or "") == run_id:
            flags.append(flag)
    for flag in result.run_flags or []:
        if isinstance(flag, dict) and str(flag.get("run_id") or "") == run_id and flag not in flags:
            flags.append(flag)
    return flags


def _bending_evidence_label(specimen: dict[str, Any]) -> str:
    threshold = _as_float(specimen.get("bending_threshold_percent")) or 10.0
    points_above = _as_float(specimen.get("bending_points_above_threshold"))
    point_count = _as_float(specimen.get("bending_point_count"))
    max_bending = _as_float(specimen.get("bending_max_percent"))
    if (points_above is None or points_above <= 0) and (max_bending is None or max_bending <= threshold):
        return ""
    parts: list[str] = []
    if point_count is not None and points_above is not None:
        parts.append(f"{int(points_above)}/{int(point_count)} points > {_format_plain_number(threshold)} %")
    elif points_above is not None and points_above > 0:
        parts.append(f"{int(points_above)} points > {_format_plain_number(threshold)} %")
    if max_bending is not None:
        parts.append(f"max {_format_plain_number(max_bending)} %")
    return "; ".join(parts)


def _enum_label_with_detail(value: Any, detail: Any) -> str:
    label = _enum_label(value)
    detail_text = str(detail or "").strip()
    if label.casefold() in {"other", "other specified"} and detail_text:
        return f"Other: {detail_text}"
    if label.casefold() in {"not recorded", "none observed"}:
        return label
    return label


def _enum_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("_", " ").replace("-", " ").strip()


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return str(value).strip()
    return ""


def _dedupe_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_plain_number(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _operation_refs(steps: list[dict[str, Any]], operation_types: set[str]) -> list[dict[str, Any]]:
    refs = []
    for step in steps:
        if str(step.get("operation_type") or "") in operation_types:
            refs.append(
                {
                    "procedure_step_id": step.get("procedure_step_id") or step.get("step_id"),
                    "operation_type": step.get("operation_type"),
                    "operation_record": (step.get("evidence_refs") or {}).get("operation_record") or step.get("operation_result_ref"),
                    "workbench_link": step.get("workbench_link"),
                    "audit_view": step.get("default_audit_view") or step.get("audit_view_type"),
                }
            )
    return refs


def _operation_for_run(result: MethodRunResult, run_id: str, operation_type: str) -> dict[str, Any]:
    for record in result.operation_log:
        if str(record.get("run_id") or "") == run_id and str(record.get("operation_type") or "") == operation_type:
            return record
    return {}


def _operation_ref(result: MethodRunResult, run_id: str, operation_type: str) -> str:
    record = _operation_for_run(result, run_id, operation_type)
    if not record and operation_type == "value_at_max":
        record = _operation_for_run(result, run_id, "value_at_index")
    if record:
        return f"audit/operation_log.json#/sequence/{record.get('sequence')}"
    return ""


def _curve_shape_score_for_run(result: MethodRunResult, run_id: str) -> dict[str, Any]:
    for row in result.curve_shape_diagnostic_scores or []:
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id:
            return dict(row)
    return {}


def _curve_shape_evidence_consequence(score: dict[str, Any]) -> str:
    classification = str(score.get("diagnostic_classification") or "")
    if classification == "CURVE_SHAPE_OUTLIER":
        return "evidence flag for decision register"
    if classification in {"INSUFFICIENT_CURVE_DATA", "INSUFFICIENT_COHORT_SIZE"}:
        return "diagnostic limitation surfaced for decision register"
    if classification == "CURVE_SHAPE_NORMAL":
        return "no curve-shape alert"
    return "not assessed"


def _evidence_flag_rows(result: MethodRunResult) -> list[dict[str, Any]]:
    rows = []
    for row in result.run_flags or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "run_id": row.get("run_id"),
                "evidence_category": row.get("category") or row.get("source"),
                "evidence_flag": row.get("flag_id") or row.get("rule_id"),
                "severity": row.get("severity"),
                "reason": row.get("message") or row.get("reason"),
                "evidence_anchor": _evidence_anchor_for_flag(row),
            }
        )
    return rows


def _evidence_anchor_for_flag(flag: dict[str, Any]) -> str:
    run_id = str(flag.get("run_id") or "")
    category = str(flag.get("category") or flag.get("source") or "")
    if "curve_shape" in category or "curve_family" in category:
        return f"#{run_id}:run_curve_shape_diagnostic"
    if "bending" in category:
        return f"#{run_id}:run_bending_evidence"
    if "validation" in category:
        return f"#{run_id}:run_validation_evidence"
    if "statistical" in category:
        return "#aggregate:aggregate_evidence_summary"
    return f"#{run_id}:run_identity_and_status" if run_id else "#aggregate:aggregate_evidence_summary"


def _virtual_operation_ref(operation_type: str) -> dict[str, Any]:
    return {
        "procedure_step_id": operation_type,
        "operation_type": operation_type,
        "operation_record": "",
        "workbench_link": "workbench/index.html#tab=acceptance",
    }


def _row_by_run(rows: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("run_id") or "") == run_id:
            return row
    return {"run_id": run_id}


def _boundary_for_run(result: MethodRunResult, run_id: str) -> dict[str, Any]:
    for record in result.experiment_boundaries or []:
        if isinstance(record, dict) and str(record.get("run_id") or "") == run_id:
            return record
    return {}


def _boundary_interval_value(boundary: dict[str, Any], key: str, fallback: Any = "") -> Any:
    interval = boundary.get("analysis_interval") if isinstance(boundary.get("analysis_interval"), dict) else {}
    return interval.get(key, boundary.get(key, fallback))


def _selection_for_run(result: MethodRunResult, run_id: str) -> dict[str, Any]:
    for row in result.final_report_runs or []:
        if isinstance(row, dict) and str(row.get("run_id") or "") == run_id:
            return dict(row)
    default_selection = str(result.acceptance_report.get("default_selection_set") or "")
    for row in result.selection_membership:
        if (
            isinstance(row, dict)
            and str(row.get("run_id") or "") == run_id
            and str(row.get("selection_set") or "") == default_selection
        ):
            return dict(row)
    return {"run_id": run_id, "included": ""}


def _longest_segment_points(output: dict[str, Any]) -> Any:
    longest = output.get("longest_segment")
    if isinstance(longest, dict):
        return longest.get("point_count") or longest.get("length_points")
    return ""


def _workbench_link(run_id: str, context: str) -> str:
    return f"workbench/index.html#tab=evidence&run={run_id}&context={context}"


def _safe_run(run_id: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in run_id).strip("_") or run_id


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
