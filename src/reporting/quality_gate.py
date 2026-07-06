from __future__ import annotations

import csv
import io
import json
from typing import Any

from archives.core.layouts import MTDAAlignedLayout, aggregate_member, report_member


EXPECTED_ISO14126_SECTIONS = [
    "test_identification",
    "material_identification",
    "specimen_preparation",
    "loading_fixture",
    "specimen_geometry",
    "test_conditions",
    "measurement_method",
    "individual_test_results",
    "aggregated_results",
    "failure_analysis",
    "deviations_from_standard",
    "remarks",
]

SECTION_STATUSES = {"complete", "complete_with_warnings", "incomplete", "not_applicable"}


def build_report_quality_gate(files: dict[str, bytes]) -> dict[str, Any]:
    if MTDAAlignedLayout.manifest in files:
        return _build_aligned_report_quality_gate(files)

    names = set(files)
    report = _json_member(files, "report/test_report.json")
    audit = _json_member(files, "audit/audit_report.json")
    sections = report.get("report_sections", []) if isinstance(report.get("report_sections"), list) else []
    completion = _json_member(files, "report/report_completion_status.json")
    final_rows = _csv_member(files, "acceptance/final_report_runs.csv")
    report_html = _text_member(files, "report/test_report.html")
    audit_html = _text_member(files, "audit/audit_report.html")

    checks: list[dict[str, Any]] = []
    checks.append(_check_members("test_report_artifacts", names, ["report/test_report.html", "report/test_report.json", "report/report_completion_status.json"]))
    checks.append(_check_members("audit_report_artifacts", names, ["audit/audit_report.html", "audit/audit_report.json"]))
    checks.append(_check_members("workbench_artifacts", names, ["workbench/index.html", "workbench/operation_trace.json"]))
    checks.append(_check_iso_sections(report))
    checks.append(_check_section_statuses(sections))
    checks.append(_check_report_completion(completion))
    checks.append(_check_vega_rendering(files, report_html))
    checks.append(_check_plot_data_freshness(files, report))
    checks.append(_check_final_selection(report, audit, final_rows))
    checks.append(_check_audit_payload(audit, names, audit_html))

    test_failures = [check for check in checks if check["surface"] == "test_report" and check["status"] == "fail"]
    test_warnings = [check for check in checks if check["surface"] == "test_report" and check["status"] == "warn"]
    audit_failures = [check for check in checks if check["surface"] == "audit_report" and check["status"] == "fail"]
    audit_warnings = [check for check in checks if check["surface"] == "audit_report" and check["status"] == "warn"]
    overall_failures = [check for check in checks if check["status"] == "fail"]
    overall_warnings = [check for check in checks if check["status"] == "warn"]

    return {
        "schema_id": "report.rc_quality_gate.v0_1",
        "overall_status": _rc_status(overall_failures, overall_warnings),
        "surfaces": {
            "test_report": {
                "rc_status": _rc_status(test_failures, test_warnings),
                "failed_checks": [check["check_id"] for check in test_failures],
                "warning_checks": [check["check_id"] for check in test_warnings],
            },
            "audit_report": {
                "rc_status": _rc_status(audit_failures, audit_warnings),
                "failed_checks": [check["check_id"] for check in audit_failures],
                "warning_checks": [check["check_id"] for check in audit_warnings],
            },
        },
        "section_statuses": _section_status_payload(sections),
        "missing_fields_by_section": _missing_fields_by_section(report.get("missing_report_fields", [])),
        "cross_surface_agreement": {
            "source_package": report.get("source_package") or _nested(audit, "source_mtdp", "path") or "",
            "method_id": report.get("method_id") or _nested(audit, "method_package", "method_id") or "",
            "mapping_id": report.get("mapping_id") or _nested(audit, "mapping_profile", "mapping_id") or "",
            "final_report_run_ids": _selected_run_ids(final_rows),
            "selected_run_count": len(_selected_run_ids(final_rows)),
            "selection_set": report.get("selection_set") or "",
            "selection_source": report.get("selection_source") or _nested(audit, "acceptance", "selection_source") or "",
            "readiness_status": _nested(audit, "readiness", "status") or "",
            "validation_status": _nested(audit, "validation", "status") or "",
            "report_completion_status": completion.get("status") or "",
        },
        "checks": checks,
    }


def _build_aligned_report_quality_gate(files: dict[str, bytes]) -> dict[str, Any]:
    names = set(files)
    report = _json_member(files, report_member("test_report.json"))
    audit = _json_member(files, report_member("audit_report.json"))
    sections = report.get("report_sections", []) if isinstance(report.get("report_sections"), list) else []
    completion = report.get("report_completion_status") if isinstance(report.get("report_completion_status"), dict) else {}
    final_rows = _csv_member(files, aggregate_member("run_decision_registry.csv"))
    report_html = _text_member(files, report_member("test_report.html"))
    audit_html = _text_member(files, report_member("audit_report.html"))

    checks: list[dict[str, Any]] = []
    checks.append(
        _check_members(
            "test_report_artifacts",
            names,
            [report_member("test_report.html"), report_member("test_report.json")],
        )
    )
    checks.append(
        _check_members(
            "audit_report_artifacts",
            names,
            [report_member("audit_report.html"), report_member("audit_report.json"), report_member("audit_report.csv")],
        )
    )
    checks.append(
        _check_members(
            "aligned_metadata_artifacts",
            names,
            [MTDAAlignedLayout.manifest, MTDAAlignedLayout.provenance, MTDAAlignedLayout.validation, MTDAAlignedLayout.method_outputs],
        )
    )
    checks.append(_check_iso_sections(report))
    checks.append(_check_section_statuses(sections))
    checks.append(_check_report_completion(completion))
    checks.append(_check_vega_rendering(files, report_html, aligned=True))
    checks.append(_check_plot_data_freshness(files, report))
    checks.append(_check_final_selection(report, audit, final_rows))
    checks.append(_check_audit_payload(audit, names, audit_html, aligned=True))

    test_failures = [check for check in checks if check["surface"] == "test_report" and check["status"] == "fail"]
    test_warnings = [check for check in checks if check["surface"] == "test_report" and check["status"] == "warn"]
    audit_failures = [check for check in checks if check["surface"] == "audit_report" and check["status"] == "fail"]
    audit_warnings = [check for check in checks if check["surface"] == "audit_report" and check["status"] == "warn"]
    overall_failures = [check for check in checks if check["status"] == "fail"]
    overall_warnings = [check for check in checks if check["status"] == "warn"]

    return {
        "schema_id": "report.rc_quality_gate.v0_3",
        "layout_version": MTDAAlignedLayout.name,
        "overall_status": _rc_status(overall_failures, overall_warnings),
        "surfaces": {
            "test_report": {
                "rc_status": _rc_status(test_failures, test_warnings),
                "failed_checks": [check["check_id"] for check in test_failures],
                "warning_checks": [check["check_id"] for check in test_warnings],
            },
            "audit_report": {
                "rc_status": _rc_status(audit_failures, audit_warnings),
                "failed_checks": [check["check_id"] for check in audit_failures],
                "warning_checks": [check["check_id"] for check in audit_warnings],
            },
        },
        "section_statuses": _section_status_payload(sections),
        "missing_fields_by_section": _missing_fields_by_section(report.get("missing_report_fields", [])),
        "report_completion_status": completion,
        "cross_surface_agreement": {
            "source_package": report.get("source_package") or _nested(audit, "source_mtdp", "path") or "",
            "method_id": report.get("method_id") or _nested(audit, "method_package", "method_id") or "",
            "mapping_id": report.get("mapping_id") or _nested(audit, "mapping_profile", "mapping_id") or "",
            "final_report_run_ids": _selected_run_ids(final_rows),
            "selected_run_count": len(_selected_run_ids(final_rows)),
            "selection_set": report.get("selection_set") or "",
            "selection_source": report.get("selection_source") or _nested(audit, "acceptance", "selection_source") or "",
            "readiness_status": _nested(audit, "readiness", "status") or "",
            "validation_status": _nested(audit, "validation", "status") or "",
            "report_completion_status": completion.get("status") or "",
        },
        "checks": checks,
    }


def _check_members(check_id: str, names: set[str], required: list[str]) -> dict[str, Any]:
    missing = [member for member in required if member not in names]
    return {
        "check_id": check_id,
        "surface": "shared" if check_id == "workbench_artifacts" else check_id.removesuffix("_artifacts"),
        "status": "fail" if missing else "pass",
        "severity": "error" if missing else "info",
        "message": "Missing required artifact(s)." if missing else "Required artifacts are present.",
        "evidence": {"required": required, "missing": missing},
    }


def _check_iso_sections(report: dict[str, Any]) -> dict[str, Any]:
    section_ids = [str(section.get("section_id") or "") for section in report.get("report_sections", []) if isinstance(section, dict)]
    missing = [section for section in EXPECTED_ISO14126_SECTIONS if section not in section_ids]
    status = "fail" if missing else "pass"
    return {
        "check_id": "test_report_expected_iso14126_sections",
        "surface": "test_report",
        "status": status,
        "severity": "error" if missing else "info",
        "message": "ISO 14126 report sections are complete." if not missing else "ISO 14126 report sections are missing.",
        "evidence": {"expected": EXPECTED_ISO14126_SECTIONS, "actual": section_ids, "missing": missing},
    }


def _check_section_statuses(sections: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = [
        str(section.get("section_id") or section.get("title") or "")
        for section in sections
        if str(section.get("status") or "") not in SECTION_STATUSES
    ]
    return {
        "check_id": "test_report_section_statuses",
        "surface": "test_report",
        "status": "fail" if invalid else "pass",
        "severity": "error" if invalid else "info",
        "message": "All report sections have RC statuses." if not invalid else "Some report sections lack RC statuses.",
        "evidence": {"allowed_statuses": sorted(SECTION_STATUSES), "invalid_sections": invalid},
    }


def _check_report_completion(completion: dict[str, Any]) -> dict[str, Any]:
    status = str(completion.get("status") or "")
    failed = status == "INCOMPLETE" or not status
    warning = status == "COMPLETE_WITH_WARNINGS"
    return {
        "check_id": "test_report_completion_status",
        "surface": "test_report",
        "status": "fail" if failed else "warn" if warning else "pass",
        "severity": "error" if failed else "warning" if warning else "info",
        "message": f"Report completion status is {status or 'missing'}.",
        "evidence": completion,
    }


def _check_vega_rendering(files: dict[str, bytes], html: str, *, aligned: bool = False) -> dict[str, Any]:
    aligned_rows = _csv_member(files, aggregate_member("stress_strain_aligned.csv") if aligned else "report/aligned_curves.csv")
    requires_plot = bool(aligned_rows)
    has_spec = (
        all(
            member in files
            for member in [
                aggregate_member("dataset_plot.plot_package.json"),
                aggregate_member("dataset_plot.template.json"),
            ]
        )
        if aligned
        else "report/vega_specs/aggregate_stress_strain_mean_variability.json" in files
    )
    has_embed = ("data-vega-block" in html and "vegaEmbed" in html) or aligned
    failed = requires_plot and not (has_spec and has_embed)
    return {
        "check_id": "test_report_aggregate_vega_plot",
        "surface": "test_report",
        "status": "fail" if failed else "pass",
        "severity": "error" if failed else "info",
        "message": "Aggregate Vega plot is renderable when aligned curves exist." if not failed else "Aligned curves exist but the rendered Vega block or spec is missing.",
        "evidence": {
            "aligned_curve_rows": len(aligned_rows),
            "requires_plot": requires_plot,
            "has_vega_spec_or_compact_package": has_spec,
            "has_rendered_block": has_embed,
        },
    }


def _check_plot_data_freshness(files: dict[str, bytes], report: dict[str, Any]) -> dict[str, Any]:
    freshness = _json_member(files, "report/plot_data_freshness.json")
    if not freshness:
        freshness = report.get("plot_data_freshness") if isinstance(report.get("plot_data_freshness"), dict) else {}
    status = str(freshness.get("status") or "unavailable").casefold()
    failed = status == "stale"
    warning = status in {"warning", "unavailable"}
    return {
        "check_id": "test_report_plot_data_freshness",
        "surface": "test_report",
        "status": "fail" if failed else "warn" if warning else "pass",
        "severity": "error" if failed else "warning" if warning else "info",
        "message": (
            "Report plot data is current."
            if status == "current"
            else "Report plot data needs review."
            if warning
            else "Report plot data is stale."
        ),
        "evidence": freshness,
    }


def _check_final_selection(report: dict[str, Any], audit: dict[str, Any], final_rows: list[dict[str, Any]]) -> dict[str, Any]:
    run_ids = _selected_run_ids(final_rows)
    report_count = _as_int(_nested(report, "summary", "selected_run_count"))
    audit_selection = _nested(audit, "acceptance", "final_selection_set")
    failures: list[str] = []
    if report.get("selection_set") != "final_report_runs":
        failures.append("report_selection_set_not_final_report_runs")
    if audit_selection not in {"final_report_runs", ""}:
        failures.append("audit_final_selection_set_mismatch")
    if report_count is not None and report_count != len(run_ids):
        failures.append("selected_run_count_mismatch")
    return {
        "check_id": "final_selection_consistency",
        "surface": "shared",
        "status": "fail" if failures else "pass",
        "severity": "error" if failures else "info",
        "message": "Final report run selection is consistent." if not failures else "Final report run selection disagrees across artifacts.",
        "evidence": {
            "failures": failures,
            "report_selection_set": report.get("selection_set"),
            "audit_final_selection_set": audit_selection,
            "final_report_run_ids": run_ids,
            "report_selected_run_count": report_count,
        },
    }


def _check_audit_payload(audit: dict[str, Any], names: set[str], html: str, *, aligned: bool = False) -> dict[str, Any]:
    required_sections = [
        "source_mtdp",
        "method_package",
        "mapping_profile",
        "schema_method_compatibility",
        "readiness",
        "validation",
        "acceptance",
        "human_overrides",
        "mtda_finalization",
        "warnings",
        "artifact_links",
    ]
    missing_sections = [section for section in required_sections if section not in audit]
    links = audit.get("artifact_links", {}) if isinstance(audit.get("artifact_links"), dict) else {}
    required_links = (
        {
            "test_report": report_member("test_report.html"),
            "surface_manifest": MTDAAlignedLayout.surface_manifest,
        }
        if aligned
        else {
            "test_report": "report/test_report.html",
            "method_development_workbench": "workbench/index.html",
            "surface_manifest": "surface_manifest.json",
        }
    )
    missing_links = [
        key for key, member in required_links.items()
        if links.get(key) != member or (member not in names and member != "surface_manifest.json")
    ]
    missing_html = [
        phrase
        for phrase in (
            "Audit Overview",
            "Evidence Navigation / Run Evidence Index",
            "Run-wise Evidence Packets",
            "Aggregate Evidence Packet",
            "Decision Register",
            "Formal result values are in",
            "Test Report",
        )
        if phrase not in html
    ]
    failed = bool(missing_sections or missing_links or missing_html)
    return {
        "check_id": "audit_report_process_verification_content",
        "surface": "audit_report",
        "status": "fail" if failed else "pass",
        "severity": "error" if failed else "info",
        "message": "Audit report contains operator-facing ISO analysis evidence." if not failed else "Audit report operator-facing evidence content is incomplete.",
        "evidence": {
            "missing_sections": missing_sections,
            "missing_links": missing_links,
            "missing_html_phrases": missing_html,
        },
    }


def _rc_status(failures: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if failures:
        return "RC_BLOCKED"
    if warnings:
        return "RC_WITH_WARNINGS"
    return "RC_READY"


def _section_status_payload(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section_id": section.get("section_id"),
            "title": section.get("title"),
            "status": section.get("status"),
            "missing_required_count": section.get("missing_required_count", 0),
            "missing_recommended_count": section.get("missing_recommended_count", 0),
            "missing_optional_count": section.get("missing_optional_count", 0),
        }
        for section in sections
    ]


def _missing_fields_by_section(fields: Any) -> dict[str, dict[str, list[str]]]:
    if not isinstance(fields, list):
        return {}
    grouped: dict[str, dict[str, list[str]]] = {}
    for field in fields:
        if not isinstance(field, dict):
            continue
        section = str(field.get("section_id") or "unsectioned")
        importance = str(field.get("report_importance") or field.get("requirement_level") or "recommended")
        if importance not in {"required", "recommended", "optional", "none"}:
            importance = "recommended"
        grouped.setdefault(section, {"required": [], "recommended": [], "optional": [], "none": []})
        grouped[section][importance].append(str(field.get("field_key") or field.get("field") or ""))
    return grouped


def _json_member(files: dict[str, bytes], member: str) -> dict[str, Any]:
    try:
        payload = json.loads(files.get(member, b"{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _csv_member(files: dict[str, bytes], member: str) -> list[dict[str, Any]]:
    content = files.get(member)
    if not content:
        return []
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _text_member(files: dict[str, bytes], member: str) -> str:
    content = files.get(member)
    return content.decode("utf-8", errors="replace") if content else ""


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _selected_run_ids(final_report_runs: list[dict[str, Any]]) -> list[str]:
    run_ids: list[str] = []
    for row in final_report_runs:
        run_id = str(row.get("run_id") or "").strip()
        if run_id and _truthy(row.get("included", row.get("final_included", True))):
            run_ids.append(run_id)
    return run_ids


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
