from __future__ import annotations

import math
import re
from typing import Any


PASS_STATUSES = {"pass", "corrected"}
DEVIATION_STATUSES = {"corrected", "fail", "missing", "not_checkable"}

_FAILURE_MODE_VALUES = {
    "in-plane shear",
    "complex",
    "through-thickness shear",
    "splitting",
    "delamination",
}


def build_iso14126_resolve_checks(
    *,
    result: Any,
    missing_report_fields: list[dict[str, Any]],
    report_values_used: list[dict[str, Any]],
    selection_run_ids: set[str],
) -> list[dict[str, Any]]:
    """Resolve ISO 14126 report-facing method and validity checks.

    The generated records are factual report inputs. Rendering code should not
    infer ISO satisfaction from raw values that were not resolved here.
    """

    values = _values_by_key(report_values_used)
    missing_fields = {str(row.get("field") or row.get("field_key") or "") for row in missing_report_fields}
    specimen_rows = [row for row in getattr(result, "specimen_results", []) or [] if isinstance(row, dict)]
    run_ids = [str(row.get("run_id") or "") for row in specimen_rows if row.get("run_id")]
    records: list[dict[str, Any]] = []

    records.append(_loading_method_record(values, missing_fields))
    records.append(_specimen_type_record(values, missing_fields))
    records.append(_back_to_back_strain_record(result, run_ids))
    records.append(_mounting_prestrain_record(values))
    records.append(_speed_of_testing_record(values, missing_fields))
    records.append(_acquisition_through_test_record(result, run_ids))
    records.append(_fmax_record(specimen_rows))
    records.extend(_validity_records(specimen_rows, getattr(result, "acceptance_report", {}) or {}))
    records.extend(_failure_mode_records(specimen_rows, selection_run_ids))
    records.append(_minimum_specimen_count_record(specimen_rows, selection_run_ids))
    records.extend(_discard_replacement_records(specimen_rows, getattr(result, "acceptance_report", {}) or {}, selection_run_ids))
    records.append(_fixture_alignment_record(values, missing_fields))
    records.extend(_boundary_policy_records(getattr(result, "experiment_boundaries", []) or []))
    return records


def deviation_rows_from_checks(
    checks: list[dict[str, Any]],
    missing_report_fields: list[dict[str, Any]],
    validation_deviations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_validation_deviation_rows(validation_deviations))
    rows.extend(_standard_deviation_rows(checks))
    aggregate_use_row = _aggregate_use_deviation_row(checks)
    if aggregate_use_row:
        rows.append(aggregate_use_row)
    return _deduplicate_rows(rows)


def method_boundary_note(checks: list[dict[str, Any]]) -> str:
    setup_ids = {
        "iso14126.clause_9_3_back_to_back_strain",
        "iso14126.clause_9_4_mounting_prestrain_face_difference",
        "iso14126.clause_9_5_speed_of_testing",
        "iso14126.clause_9_6_acquisition_through_test",
    }
    setup_checks = [check for check in checks if str(check.get("requirement_id")) in setup_ids]
    setup_satisfied = bool(setup_checks) and all(str(check.get("status")) in PASS_STATUSES for check in setup_checks)
    if setup_satisfied:
        return (
            "Acquisition: specimen seated with pre-strain < 0.05 % and face-strain difference < 150 µε, "
            "loaded at 1 mm/min to failure. Bending validity: 10-90 % Fmax. "
            "Modulus chord: ε = 0.0005 to 0.0025. Strength/failure strain: at Fmax."
        )
    return (
        "Acquisition boundary: setup/loading-to-failure requirements resolved in method checks. "
        "Bending validity: 10-90 % Fmax. Modulus chord: ε = 0.0005 to 0.0025. "
        "Strength/failure strain: at Fmax."
    )


def analysis_interval_remark(boundaries: list[dict[str, Any]]) -> str:
    if not boundaries:
        return ""
    start_policies = sorted({str(row.get("start_policy") or "") for row in boundaries if isinstance(row, dict) and row.get("start_policy")})
    end_policies = sorted({str(row.get("end_policy") or "") for row in boundaries if isinstance(row, dict) and row.get("end_policy")})
    start_text = _boundary_policy_phrase(start_policies, boundary="start")
    end_text = _boundary_policy_phrase(end_policies, boundary="end")
    run_count = len([row for row in boundaries if isinstance(row, dict)])
    scope = f"{run_count} run" + ("" if run_count == 1 else "s")
    truncation_note = ""
    if "slope_break_pre_negative" in end_policies:
        truncation_note = (
            " The endpoint is placed at the last stable point before a significant strain-domain load reversal, "
            "so the reported reduction excludes post-break drops and spike recovery beyond that boundary."
        )
    return (
        f"Analysis interval: reported calculations use the resolved test interval for {scope}: "
        f"{start_text} to {end_text}.{truncation_note}"
    )


def _boundary_policy_phrase(policies: list[str], *, boundary: str) -> str:
    labels = {
        "first_point": "the first recorded point",
        "load_fraction_of_max": "the first point reaching the configured fraction of maximum load",
        "slope_break_pre_negative": "the pre-break endpoint",
        "max_load": "the maximum-load point",
        "last_point": "the last recorded point",
    }
    readable = [labels.get(policy, policy.replace("_", " ")) for policy in policies if policy]
    if not readable:
        return f"the resolved {boundary} boundary"
    if len(readable) == 1:
        return readable[0]
    return "; ".join(readable)


def standard_required_missing_count(checks: list[dict[str, Any]]) -> int:
    return sum(
        1
        for check in checks
        if (
            str(check.get("requirement_id")) == "iso14126.clause_9_7_fmax"
            or str(check.get("requirement_id")).startswith("iso14126.clause_9_9_failure_mode:")
        )
        and str(check.get("status")) in {"missing", "not_checkable"}
    )


def standard_deviation_count(checks: list[dict[str, Any]]) -> int:
    return sum(1 for check in checks if _include_check_in_deviation_register(check))


def _loading_method_record(values: dict[str, Any], missing_fields: set[str]) -> dict[str, Any]:
    return _controlled_choice_record(
        values=values,
        missing_fields=missing_fields,
        field="loading_method",
        detail_field="loading_method_other",
        requirement_id="iso14126.report.loading_method",
        standard_basis="ISO 14126 Clause 12",
        category="Test identification",
        affected_item="Loading method",
        iso_choices="Method 1 shear loading or Method 2 combined loading",
    )


def _specimen_type_record(values: dict[str, Any], missing_fields: set[str]) -> dict[str, Any]:
    return _controlled_choice_record(
        values=values,
        missing_fields=missing_fields,
        field="specimen_type",
        detail_field="specimen_type_other",
        requirement_id="iso14126.report.specimen_type",
        standard_basis="ISO 14126 Table 1 / Clause 12",
        category="Specimen geometry",
        affected_item="Specimen type",
        iso_choices="Type A, Type B1, or Type B2",
    )


def _controlled_choice_record(
    *,
    values: dict[str, Any],
    missing_fields: set[str],
    field: str,
    detail_field: str,
    requirement_id: str,
    standard_basis: str,
    category: str,
    affected_item: str,
    iso_choices: str,
) -> dict[str, Any]:
    raw = _first_value(values, field)
    detail = _first_value(values, detail_field)
    canonical = _canonical_controlled_choice(field, raw)
    display = _controlled_choice_display(field, canonical, detail)
    if field in missing_fields or detail_field in missing_fields or not canonical:
        status = "missing"
        consequence = "report_deviation"
        resolved = "not resolved"
        treatment = f"{affected_item} is missing or not resolved to a controlled ISO choice."
    elif canonical == "other_specified":
        status = "fail"
        consequence = "report_deviation"
        resolved = display
        treatment = f"{affected_item} is recorded as {display}; this is outside the ISO-controlled choices ({iso_choices})."
    else:
        status = "pass"
        consequence = "method_condition_satisfied"
        resolved = display
        treatment = f"{affected_item} uses an ISO-controlled choice."
    return _record(
        requirement_id=requirement_id,
        standard_basis=standard_basis,
        source="report_values_used",
        resolved_value=resolved,
        status=status,
        consequence=consequence,
        aggregate_eligible="not_applicable",
        report_target="Section 1; Section 11.1 if missing; Section 11.2 if Other specified",
        category=category,
        affected_item=affected_item,
        report_treatment=treatment,
    )


def _back_to_back_strain_record(result: Any, run_ids: list[str]) -> dict[str, Any]:
    traces = _run_trace_availability(getattr(result, "bounded_curve_family", None) or getattr(result, "curve_family", []) or [])
    available = sum(1 for run_id in run_ids if traces.get(run_id) == "front_rear")
    single_face = sum(1 for run_id in run_ids if traces.get(run_id) == "single_face")
    if run_ids and available == len(run_ids):
        status = "pass"
        consequence = "method_condition_satisfied"
        eligible = "yes"
    else:
        status = "not_checkable" if single_face else "missing"
        consequence = "validity_unresolved"
        eligible = "review"
    return _record(
        requirement_id="iso14126.clause_9_3_back_to_back_strain",
        standard_basis="ISO 14126 Clause 9.3",
        source="bounded_curve_family",
        resolved_value=f"{available}/{len(run_ids)} runs with front/rear strain traces",
        status=status,
        consequence=consequence,
        aggregate_eligible=eligible,
        report_target="Section 7 when available; Section 11.2 when missing/not checkable",
        category="Measurement method",
        affected_item="Back-to-back strain availability",
        report_treatment="Back-to-back strain evidence is required before bending evidence can be treated as resolved.",
    )


def _mounting_prestrain_record(values: dict[str, Any]) -> dict[str, Any]:
    prestrain = _number(_first_value(values, "mounting_pre_strain_percent", "pre_strain_percent", "prestrain_percent"))
    face_difference = _number(
        _first_value(
            values,
            "face_strain_difference_microstrain",
            "fixture_face_strain_difference_microstrain",
            "mounting_face_strain_difference_microstrain",
        )
    )
    corrected = _truthy(_first_value(values, "slow_unloading_correction", "unloaded_until_requirement_met"))
    if prestrain is None or face_difference is None:
        status = "not_checkable"
        consequence = "validity_unresolved"
        resolved = "pre-strain or face-strain difference not recorded"
        treatment = "Setup condition is unresolved; the report does not claim the fixture-tightening condition was satisfied."
    elif prestrain < 0.05 and face_difference < 150.0:
        status = "pass"
        consequence = "method_condition_satisfied"
        resolved = f"pre-strain {prestrain:g} %, face difference {face_difference:g} microstrain"
        treatment = "Setup condition satisfied."
    elif corrected:
        status = "corrected"
        consequence = "method_condition_satisfied_after_correction"
        resolved = f"pre-strain {prestrain:g} %, face difference {face_difference:g} microstrain; slow unloading documented"
        treatment = "Correction is reported as a standard-facing method condition."
    else:
        status = "fail"
        consequence = "method_non_compliant"
        resolved = f"pre-strain {prestrain:g} %, face difference {face_difference:g} microstrain; no correction evidence"
        treatment = "Method condition not satisfied by available evidence."
    return _record(
        requirement_id="iso14126.clause_9_4_mounting_prestrain_face_difference",
        standard_basis="ISO 14126 Clause 9.4",
        source="report_values_used",
        resolved_value=resolved,
        status=status,
        consequence=consequence,
        aggregate_eligible="review" if status not in PASS_STATUSES else "yes",
        report_target="Section 11.2 for failed, corrected, missing, or not-checkable cases",
        category="Setup method condition",
        affected_item="Mounting pre-strain and face-strain difference",
        report_treatment=treatment,
    )


def _speed_of_testing_record(values: dict[str, Any], missing_fields: set[str]) -> dict[str, Any]:
    raw = _first_value(values, "speed_of_testing", "crosshead_speed", "test_speed")
    speed = _number_from_text(raw)
    if raw in (None, "") or "speed_of_testing" in missing_fields:
        status = "missing"
        consequence = "validity_unresolved"
        resolved = "speed of testing not recorded"
        treatment = "Listed in Section 11.1 and reported here as an unresolved ISO method condition."
    elif speed is None:
        status = "not_checkable"
        consequence = "validity_unresolved"
        resolved = str(raw)
        treatment = "Speed value is present but cannot be compared to 1 mm/min +/- 0.5 mm/min."
    elif 0.5 <= speed <= 1.5:
        status = "pass"
        consequence = "method_condition_satisfied"
        resolved = f"{speed:g} mm/min"
        treatment = "Speed condition satisfied."
    else:
        status = "fail"
        consequence = "method_non_compliant"
        resolved = f"{speed:g} mm/min"
        treatment = "Speed is outside 1 mm/min +/- 0.5 mm/min."
    return _record(
        requirement_id="iso14126.clause_9_5_speed_of_testing",
        standard_basis="ISO 14126 Clause 9.5",
        source="report_values_used",
        resolved_value=resolved,
        status=status,
        consequence=consequence,
        aggregate_eligible="review" if status not in PASS_STATUSES else "yes",
        report_target="Section 11.1 if absent; Section 11.2 if absent/not checkable/outside range",
        category="Setup method condition",
        affected_item="Speed of testing",
        report_treatment=treatment,
    )


def _acquisition_through_test_record(result: Any, run_ids: list[str]) -> dict[str, Any]:
    availability = _run_load_strain_availability(getattr(result, "bounded_curve_family", None) or getattr(result, "curve_family", []) or [])
    confirmed = sum(1 for run_id in run_ids if availability.get(run_id) is True)
    if run_ids and confirmed == len(run_ids):
        status = "pass"
        consequence = "method_condition_satisfied"
        eligible = "yes"
        treatment = "Load and strain series are available through the resolved test interval."
    else:
        status = "not_checkable"
        consequence = "validity_unresolved"
        eligible = "review"
        treatment = "Load/strain acquisition-through-test evidence is incomplete or not checkable."
    return _record(
        requirement_id="iso14126.clause_9_6_load_strain_recorded",
        standard_basis="ISO 14126 Clause 9.6",
        source="bounded_curve_family",
        resolved_value=f"{confirmed}/{len(run_ids)} runs with load and strain series",
        status=status,
        consequence=consequence,
        aggregate_eligible=eligible,
        report_target="Section 11.2 when missing, failed, or not checkable",
        category="Acquisition method condition",
        affected_item="Load and strain recorded through test",
        report_treatment=treatment,
    )


def _fmax_record(specimen_rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = sum(1 for row in specimen_rows if _number(row.get("max_load_N")) is not None)
    status = "pass" if specimen_rows and available == len(specimen_rows) else "missing"
    return _record(
        requirement_id="iso14126.clause_9_7_fmax",
        standard_basis="ISO 14126 Clause 9.7 / 10.1",
        source="method_outputs.specimen_results.max_load_N",
        resolved_value=f"{available}/{len(specimen_rows)} runs with Fmax",
        status=status,
        consequence="method_condition_satisfied" if status == "pass" else "report_deviation",
        aggregate_eligible="yes" if status == "pass" else "review",
        report_target="Section 8 Max load / N; Section 9 aggregate max-load metric when present; Section 11.2 if missing",
        category="Report result",
        affected_item="Maximum load / Fmax",
        report_treatment="Fmax is reported in Section 8 when available; missing values are rendered as missing.",
    )


def _validity_records(specimen_rows: list[dict[str, Any]], acceptance_report: dict[str, Any]) -> list[dict[str, Any]]:
    states = acceptance_report.get("run_states", {}) if isinstance(acceptance_report.get("run_states"), dict) else {}
    rows: list[dict[str, Any]] = []
    for row in specimen_rows:
        run_id = str(row.get("run_id") or "")
        bending = str(row.get("bending_pattern") or "")
        state = str(states.get(run_id) or row.get("acceptance_state") or "")
        validity = str(row.get("validity") or "")
        if not bending:
            status = "not_checkable"
            consequence = "validity_unresolved"
            eligible = "review"
            treatment = "Bending validity cannot be confirmed from available evidence."
        elif state.casefold() == "excluded" or validity.casefold() in {"invalid", "rejected", "false", "0"} or bending.startswith("FAIL"):
            status = "fail"
            consequence = "invalid"
            eligible = "no"
            if bending.startswith("FAIL"):
                treatment = "Run invalid under the recorded bending validity logic and excluded from the reported aggregate."
            elif validity.casefold() in {"invalid", "rejected", "false", "0"}:
                treatment = "Run invalid under the recorded operator validity metadata and excluded from the reported aggregate."
            else:
                treatment = "Run invalid under the recorded acceptance logic and excluded from the reported aggregate."
        else:
            status = "pass"
            consequence = "method_condition_satisfied"
            eligible = "yes"
            treatment = "Run validity evidence is accepted by the existing acceptance logic."
        record = _record(
                requirement_id=f"iso14126.clause_9_8_validity:{run_id}",
                standard_basis="ISO 14126 Clause 9.8",
                source="acceptance_report.run_states + bending_diagnostic",
                resolved_value=f"acceptance_state={state or 'not recorded'}; bending={bending or 'not recorded'}",
                status=status,
                consequence=consequence,
                aggregate_eligible=eligible,
                report_target="Section 8 run status / acceptance; Section 11.2 for invalid or unresolved cases",
                category="Run validity",
                affected_item=run_id,
                report_treatment=treatment,
        )
        record["run_id"] = run_id
        rows.append(record)
    return rows


def _failure_mode_records(specimen_rows: list[dict[str, Any]], selection_run_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in specimen_rows:
        run_id = str(row.get("run_id") or "")
        if selection_run_ids and run_id not in selection_run_ids:
            continue
        raw = row.get("primary_failure_mode") or row.get("failure_mode")
        mode = failure_mode_display(raw)
        status = "pass" if mode != "missing" else "missing"
        rows.append(
            _record(
                requirement_id=f"iso14126.clause_9_9_failure_mode:{run_id}",
                standard_basis="ISO 14126 Clause 9.9 / Clause 12(l)",
                source="method_outputs.specimen_results.primary_failure_mode + legacy failure_mode",
                resolved_value=mode,
                status=status,
                consequence="method_condition_satisfied" if status == "pass" else "report_deviation",
                aggregate_eligible="not_applicable",
                report_target="Section 8 Failure mode; Section 11.1 if missing",
                category="Report result",
                affected_item=run_id,
                report_treatment="Failure mode is reported when one of the ISO-facing classes is available from the structured field or clean legacy fallback; otherwise Section 8 renders missing and Section 11.1 counts the report-data gap.",
            )
        )
    return rows


def _minimum_specimen_count_record(specimen_rows: list[dict[str, Any]], selection_run_ids: set[str]) -> dict[str, Any]:
    acquired = len(specimen_rows)
    included = len(selection_run_ids)
    excluded = max(0, acquired - included)
    status = "pass" if included >= 5 else "fail"
    return _record(
        requirement_id="iso14126.clause_7_1_minimum_specimen_count",
        standard_basis="ISO 14126 Clause 7.1",
        source="final_report_runs",
        resolved_value=f"acquired={acquired}; included={included}; excluded={excluded}",
        status=status,
        consequence="method_condition_satisfied" if status == "pass" else "standard_non_compliant",
        aggregate_eligible="yes" if status == "pass" else "review",
        report_target="Report-state summary or Section 11.2",
        category="Aggregate count",
        affected_item="Final report run set",
        report_treatment=(
            "Included specimen count satisfies the minimum count."
            if status == "pass"
            else "Aggregate includes fewer than five specimens; individual valid runs are not reclassified as invalid solely for this aggregate count."
        ),
    )


def _discard_replacement_records(
    specimen_rows: list[dict[str, Any]],
    acceptance_report: dict[str, Any],
    selection_run_ids: set[str],
) -> list[dict[str, Any]]:
    states = acceptance_report.get("run_states", {}) if isinstance(acceptance_report.get("run_states"), dict) else {}
    rows: list[dict[str, Any]] = []
    for row in specimen_rows:
        run_id = str(row.get("run_id") or "")
        if run_id in selection_run_ids:
            continue
        state = str(states.get(run_id) or row.get("acceptance_state") or "excluded")
        bending = str(row.get("bending_pattern") or "")
        if bending.startswith("FAIL"):
            reason = "invalid due to bending evidence"
            consequence = "invalid"
        elif str(row.get("validity") or "").casefold() in {"invalid", "rejected", "false", "0"}:
            reason = "invalid due to operator validity metadata"
            consequence = "invalid"
        else:
            reason = "excluded or review-required by acceptance state"
            consequence = "report_deviation"
        record = _record(
            requirement_id=f"iso14126.clause_7_2_discard_replacement:{run_id}",
            standard_basis="ISO 14126 Clause 7.2",
            source="acceptance_report + final_report_runs",
            resolved_value=f"{run_id}: {state}; {reason}; replacement not represented in aggregate",
            status="fail" if consequence == "invalid" else "not_checkable",
            consequence=consequence,
            aggregate_eligible="no" if consequence == "invalid" else "review",
            report_target="Section 8 acceptance; Section 11.2 data-use deviation",
            category="Run exclusion / aggregate-use basis",
            affected_item=run_id,
            report_treatment=(
                "This run is not included in the final aggregate result set. "
                "No replacement specimen is represented in the reported aggregate."
            ),
        )
        record["run_id"] = run_id
        record["acceptance_state"] = state
        record["aggregate_use_reason"] = reason
        rows.append(record)
    return rows


def _fixture_alignment_record(values: dict[str, Any], missing_fields: set[str]) -> dict[str, Any]:
    fixture = _first_value(values, "fixture_type", "fixture_manufacturer_design")
    alignment = _first_value(values, "alignment_procedure", "alignment_evidence", "fixture_alignment_evidence")
    failed = str(_first_value(values, "alignment_result", "fixture_alignment_result") or "").casefold() in {"fail", "failed", "non_compliant"}
    if failed:
        status = "fail"
        consequence = "method_non_compliant"
        resolved = "alignment evidence recorded as failed"
        treatment = "Fixture/alignment evidence is recorded as failed."
    elif fixture not in (None, "") and alignment not in (None, ""):
        status = "pass"
        consequence = "method_condition_satisfied"
        resolved = "fixture identity and alignment evidence available"
        treatment = "Fixture and alignment evidence available."
    else:
        status = "missing" if {"fixture_type", "alignment_procedure"} & missing_fields else "not_checkable"
        consequence = "validity_unresolved"
        resolved = "fixture identity or alignment evidence not recorded"
        treatment = "Fixture/alignment evidence is missing or not checkable."
    return _record(
        requirement_id="iso14126.annex_a_fixture_alignment",
        standard_basis="ISO 14126 Annex A / Clause 5.1 / Clause 5.4",
        source="report_values_used",
        resolved_value=resolved,
        status=status,
        consequence=consequence,
        aggregate_eligible="review" if status not in PASS_STATUSES else "yes",
        report_target="Section 11.1 for missing fixture/alignment fields; Section 11.2 for standard-facing consequence",
        category="Fixture and alignment",
        affected_item="Loading fixture identity and alignment evidence",
        report_treatment=treatment,
    )


def _boundary_policy_records(boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not boundaries:
        return []
    start_policies = sorted({str(row.get("start_policy") or "") for row in boundaries if isinstance(row, dict) and row.get("start_policy")})
    end_policies = sorted({str(row.get("end_policy") or "") for row in boundaries if isinstance(row, dict) and row.get("end_policy")})
    rows: list[dict[str, Any]] = []
    if start_policies or end_policies:
        rows.append(
            _record(
                requirement_id="iso14126.analysis_boundary_policy",
                standard_basis="Internal reduction/audit policy",
                source="method_resolve.experiment_boundaries",
                resolved_value=f"start_policy={', '.join(start_policies) or 'not recorded'}; end_policy={', '.join(end_policies) or 'not recorded'}",
                status="corrected",
                consequence="method_condition_satisfied_after_correction",
                aggregate_eligible="not_applicable",
                report_target="Section 12",
                category="Analysis interval policy",
                affected_item="Automatic boundary trimming and endpoint handling",
                report_treatment=(
                    "Reported calculations use the resolved analysis interval. The report remark records the "
                    "truncation mode; detailed boundary markers remain in the audit evidence."
                ),
            )
        )
    return rows


def _validation_deviation_rows(validation_deviations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in validation_deviations:
        status = str(item.get("status") or item.get("severity") or "").casefold()
        if status in {"pass", "passed", "ok", "success"}:
            continue
        rows.append(
            {
                "Category": "Validation check",
                "Standard basis": str(item.get("standard_basis") or "Method validation reference"),
                "Affected item": str(item.get("run_id") or item.get("field") or item.get("check_id") or ""),
                "Status/consequence": str(item.get("status") or item.get("severity") or ""),
                "Report treatment": str(item.get("message") or item.get("note") or "Validation deviation retained in report evidence."),
                "source": "validation",
            }
        )
    return rows


def _standard_deviation_rows(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for check in checks:
        if not _include_check_in_deviation_register(check):
            continue
        rows.append(
            {
                "Category": check.get("category") or "ISO 14126 check",
                "Standard basis": check.get("standard_basis") or "",
                "Affected item": check.get("affected_item") or "",
                "Status/consequence": _status_consequence(check),
                "Report treatment": check.get("report_treatment") or check.get("report_target") or "",
                "source": "iso14126_resolve_check",
                "requirement_id": check.get("requirement_id") or "",
            }
        )
    return rows


def _aggregate_use_deviation_row(checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    aggregate_checks = [
        check
        for check in checks
        if str(check.get("requirement_id") or "").startswith("iso14126.clause_7_2_discard_replacement:")
    ]
    if not aggregate_checks:
        return None
    affected = []
    status_labels = set()
    for check in aggregate_checks:
        run_id = str(check.get("run_id") or check.get("affected_item") or "")
        reason = str(check.get("aggregate_use_reason") or "not included in aggregate")
        state = str(check.get("acceptance_state") or "")
        if str(check.get("consequence")) == "invalid":
            status_labels.add("excluded from aggregate")
        else:
            status_labels.add("review required; not included in aggregate")
        label = run_id
        if state:
            label = f"{label} ({state})"
        affected.append(f"{label}: {reason}")
    return {
        "Category": "Run exclusion / aggregate-use basis",
        "Standard basis": "ISO 14126 Clause 7.2",
        "Affected item": "; ".join(affected),
        "Status/consequence": "; ".join(sorted(status_labels)),
        "Report treatment": (
            "Excluded or review-required runs are not used in the reported aggregate result set. "
            "No replacement specimen is represented in the reported aggregate."
        ),
        "source": "iso14126_aggregate_use_summary",
    }


def _required_missing_report_rows(missing_report_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in missing_report_fields:
        importance = str(field.get("report_importance") or field.get("requirement_level") or field.get("severity") or "").casefold()
        if importance not in {"required", "execution_critical", "critical"}:
            continue
        label = str(field.get("label") or field.get("field") or "")
        rows.append(
            {
                "Category": "Required report field",
                "Standard basis": "ISO 14126 Clause 12",
                "Affected item": label,
                "Status/consequence": "missing / report_deviation",
                "Report treatment": "Listed in Section 11.1 and retained as a standard-facing report gap.",
                "source": "report_completeness",
            }
        )
    return rows


def _include_check_in_deviation_register(check: dict[str, Any]) -> bool:
    requirement_id = str(check.get("requirement_id") or "")
    status = str(check.get("status") or "")
    if requirement_id in {"iso14126.report.loading_method", "iso14126.report.specimen_type"} and status == "missing":
        return False
    if requirement_id.startswith("iso14126.clause_9_9_failure_mode:") and status in {"missing", "not_checkable"}:
        return False
    if requirement_id == "iso14126.clause_9_7_fmax" and status in {"missing", "not_checkable"}:
        return False
    if requirement_id.startswith("iso14126.clause_9_8_validity:"):
        return False
    if requirement_id.startswith("iso14126.clause_7_2_discard_replacement:"):
        return False
    if requirement_id == "iso14126.analysis_boundary_policy":
        return False
    if status in DEVIATION_STATUSES:
        return True
    return str(check.get("consequence")) in {
        "method_condition_satisfied_after_correction",
        "method_non_compliant",
        "invalid",
        "validity_unresolved",
        "report_deviation",
        "standard_non_compliant",
    }


def _status_consequence(check: dict[str, Any]) -> str:
    status = str(check.get("status") or "")
    consequence = str(check.get("consequence") or "")
    if status and consequence:
        return f"{_status_label(status)} / {_consequence_label(consequence)}"
    return _status_label(status) or _consequence_label(consequence)


def _status_label(value: str) -> str:
    return {
        "pass": "pass",
        "corrected": "applied",
        "fail": "fail",
        "missing": "missing",
        "not_checkable": "not checkable",
    }.get(value, value.replace("_", " "))


def _consequence_label(value: str) -> str:
    return {
        "method_condition_satisfied": "method condition satisfied",
        "method_condition_satisfied_after_correction": "method condition satisfied after correction",
        "method_non_compliant": "method non-compliant",
        "invalid": "invalid",
        "validity_unresolved": "validity unresolved",
        "report_deviation": "report deviation",
        "standard_non_compliant": "standard non-compliant",
    }.get(value, value.replace("_", " "))


def failure_mode_display(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "missing"
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
    }
    display = mapping.get(normalized, "missing")
    return display if display in _FAILURE_MODE_VALUES else "missing"


_CONTROLLED_CHOICE_LABELS = {
    "loading_method": {
        "method_1_shear_loading": "Shear loading (Method 1)",
        "method_2_combined_loading": "Combined loading (Method 2)",
        "other_specified": "Other specified",
    },
    "specimen_type": {
        "type_a": "Type A",
        "type_b1": "Type B1",
        "type_b2": "Type B2",
        "other_specified": "Other specified",
    },
}

_CONTROLLED_CHOICE_SYNONYMS = {
    "loading_method": {
        "method_1_shear_loading": "method_1_shear_loading",
        "method 1": "method_1_shear_loading",
        "shear loading": "method_1_shear_loading",
        "shear loading method 1": "method_1_shear_loading",
        "shear loading (method 1)": "method_1_shear_loading",
        "method_2_combined_loading": "method_2_combined_loading",
        "method 2": "method_2_combined_loading",
        "combined loading": "method_2_combined_loading",
        "combined loading method 2": "method_2_combined_loading",
        "combined loading (method 2)": "method_2_combined_loading",
        "other_specified": "other_specified",
        "other specified": "other_specified",
    },
    "specimen_type": {
        "type_a": "type_a",
        "type a": "type_a",
        "a": "type_a",
        "type_b1": "type_b1",
        "type b1": "type_b1",
        "b1": "type_b1",
        "type_b2": "type_b2",
        "type b2": "type_b2",
        "b2": "type_b2",
        "other_specified": "other_specified",
        "other specified": "other_specified",
    },
}


def _canonical_controlled_choice(field: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = " ".join(text.replace("-", " ").replace("_", " ").casefold().split())
    synonyms = _CONTROLLED_CHOICE_SYNONYMS.get(field, {})
    return synonyms.get(text, synonyms.get(normalized, ""))


def _controlled_choice_display(field: str, canonical: str, detail: Any = None) -> str:
    label = _CONTROLLED_CHOICE_LABELS.get(field, {}).get(canonical, "")
    if canonical == "other_specified" and str(detail or "").strip():
        return f"{label}: {str(detail).strip()}"
    return label or "not resolved"


def _record(
    *,
    requirement_id: str,
    standard_basis: str,
    source: str,
    resolved_value: Any,
    status: str,
    consequence: str,
    aggregate_eligible: str,
    report_target: str,
    category: str,
    affected_item: str,
    report_treatment: str,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "standard_basis": standard_basis,
        "source": source,
        "resolved_value": resolved_value,
        "status": status,
        "consequence": consequence,
        "aggregate_eligible": aggregate_eligible,
        "report_target": report_target,
        "category": category,
        "affected_item": affected_item,
        "report_treatment": report_treatment,
    }


def _values_by_key(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for row in rows:
        field = str(row.get("field") or row.get("field_key") or "")
        if field:
            values.setdefault(field, row.get("value"))
        for alias in row.get("aliases", []) or []:
            values.setdefault(str(alias), row.get("value"))
    return values


def _first_value(values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return value
    return None


def _run_trace_availability(rows: list[dict[str, Any]]) -> dict[str, str]:
    traces: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        fields = traces.setdefault(run_id, set())
        for key in ("front_strain_abs", "front_strain_raw", "front_strain", "front_strain_oriented"):
            if row.get(key) not in (None, ""):
                fields.add("front")
        for key in ("rear_strain_abs", "rear_strain_raw", "rear_strain", "rear_strain_oriented"):
            if row.get(key) not in (None, ""):
                fields.add("rear")
    return {
        run_id: "front_rear" if {"front", "rear"} <= fields else "single_face" if fields else "missing"
        for run_id, fields in traces.items()
    }


def _run_load_strain_availability(rows: list[dict[str, Any]]) -> dict[str, bool]:
    traces: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        fields = traces.setdefault(run_id, set())
        if row.get("load_N") not in (None, ""):
            fields.add("load")
        if row.get("mean_strain") not in (None, ""):
            fields.add("strain")
    return {run_id: {"load", "strain"} <= fields for run_id, fields in traces.items()}


def _number_from_text(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    return _number(match.group(0))


def _number(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "corrected", "documented"}


def _deduplicate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = (
            str(row.get("Category") or ""),
            str(row.get("Standard basis") or ""),
            str(row.get("Affected item") or ""),
            str(row.get("Status/consequence") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
