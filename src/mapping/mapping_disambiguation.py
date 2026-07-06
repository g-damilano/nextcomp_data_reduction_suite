from __future__ import annotations

from typing import Any, Mapping


def build_mapping_resolution_report(
    *,
    mapping: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
) -> dict[str, Any]:
    rows = []
    for requirement in candidate_report.get("requirements", []) or []:
        if not isinstance(requirement, dict):
            continue
        source_role = str(requirement.get("source_role") or "")
        source_kind, mapped_source, entry_status = _mapped_source(mapping, source_role)
        candidates = requirement.get("candidates", []) if isinstance(requirement.get("candidates"), list) else []
        candidate_names = {str(candidate.get("source_name")) for candidate in candidates if isinstance(candidate, dict)}
        confirmed = bool(mapped_source) and mapped_source in candidate_names
        status = (
            "confirmed"
            if confirmed and entry_status not in {"ambiguous", "unresolved"}
            else "ambiguous"
            if entry_status in {"ambiguous", "unresolved"} or requirement.get("status") == "ambiguous"
            else "manual_override"
            if mapped_source
            else "unmapped"
        )
        rows.append(
            {
                "requirement_id": requirement.get("requirement_id", ""),
                "method_field": requirement.get("method_field", ""),
                "source_role": source_role,
                "severity": requirement.get("severity", ""),
                "mapped_source": mapped_source,
                "source_kind": source_kind,
                "candidate_count": len(candidates),
                "status": status,
                "confidence": _candidate_confidence(candidates, mapped_source),
            }
        )
    return {
        "schema_id": "method.mapping_resolution_report.v0_1",
        "mapping_id": mapping.get("mapping_id", ""),
        "method_id": mapping.get("method_id", ""),
        "summary": {
            "requirement_total": len(rows),
            "confirmed_total": sum(1 for row in rows if row["status"] == "confirmed"),
            "ambiguous_total": sum(1 for row in rows if row["status"] == "ambiguous"),
            "unmapped_total": sum(1 for row in rows if row["status"] == "unmapped"),
            "manual_override_total": sum(1 for row in rows if row["status"] == "manual_override"),
        },
        "resolutions": rows,
    }


def _mapped_source(mapping: Mapping[str, Any], source_role: str) -> tuple[str, str, str]:
    for section in ("channels", "fields", "tokens"):
        payload = mapping.get(section)
        if not isinstance(payload, Mapping) or source_role not in payload:
            continue
        value = payload[source_role]
        status = ""
        if isinstance(value, Mapping):
            status = str(value.get("status") or "")
            value = value.get("source") or value.get("field") or value.get("name") or value.get("token") or value.get("channel")
        return section.rstrip("s"), str(value or ""), status
    return "", "", ""


def _candidate_confidence(candidates: list[Any], mapped_source: str) -> float:
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("source_name")) == mapped_source:
            try:
                return float(candidate.get("confidence"))
            except (TypeError, ValueError):
                return 0.0
    return 0.0
