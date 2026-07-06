from __future__ import annotations

from typing import Any

from methods.core.method_run_service import PackageLoadResult
from ui.method_run_wizard.view_models.action_contracts import wizard_page_action_contract


def package_preview_view_model(result: PackageLoadResult) -> dict[str, Any]:
    runs = list(result.runs)
    available_channels = list(result.available_channels or result.channel_roles)
    return {
        "schema_name": "package_preview_view_model",
        "version": "0.1.0",
        "page_action_contract": wizard_page_action_contract("package"),
        "package_path": str(result.path),
        "package_name": result.path.name,
        "package_id": result.manifest_id or "",
        "schema_id": result.schema_id or "",
        "schema_version": result.schema_version or "",
        "analysis_type": result.schema_id or result.sample_type or "",
        "sample_type": result.sample_type or "",
        "run_count": result.run_count,
        "group_count": result.group_count,
        "source_file_count": result.source_file_count,
        "normalized_file_count": getattr(result, "normalized_file_count", 0) or result.source_file_count,
        "raw_file_count": getattr(result, "raw_file_count", 0),
        "included_count": result.included_count,
        "excluded_count": result.excluded_count,
        "available_channels": available_channels,
        "channel_families": _channel_families(available_channels),
        "metadata_coverage": list(result.metadata_coverage),
        "metadata_summary": _metadata_summary(list(result.metadata_coverage)),
        "report_completion": dict(getattr(result, "report_completion", {}) or {}),
        "runs": runs,
        "source_files": [
            {
                "run_id": row.get("run_id", ""),
                "source_relative_path": row.get("source_relative_path", ""),
                "normalized_package_path": row.get("normalized_package_path", ""),
                "raw_package_path": row.get("raw_package_path", ""),
                "original_filename": row.get("original_filename", ""),
                "display_name": row.get("display_name", ""),
            }
            for row in runs
        ],
        "validity_summary": _validity_summary(runs),
        "failure_mode_summary": _value_counts(runs, "failure_mode"),
        "source_identity_summary": _source_identity_summary(runs, list(result.source_identity_warnings)),
        "provenance": {
            "status": getattr(result, "provenance_status", "") or "unknown",
            "checksum_status": getattr(result, "checksum_status", "") or "unknown",
            "sha256": getattr(result, "checksum_sha256", "") or "",
        },
        "warnings": list(result.warnings or result.source_identity_warnings),
        "summary_cards": [
            {"label": "Schema", "value": f"{result.schema_id or ''} {result.schema_version or ''}".strip()},
            {"label": "Runs", "value": str(result.run_count)},
            {"label": "Sources", "value": str(result.source_file_count)},
            {"label": "Normalized files", "value": str(getattr(result, "normalized_file_count", 0) or result.source_file_count)},
            {"label": "Channels", "value": str(len(available_channels))},
            {"label": "Report completion", "value": str((getattr(result, "report_completion", {}) or {}).get("status", "unknown"))},
        ],
    }


def _channel_families(channels: list[str]) -> list[dict[str, Any]]:
    families: dict[str, list[str]] = {}
    for channel in channels:
        family = _family_for_channel(channel)
        families.setdefault(family, []).append(channel)
    return [
        {"family": family, "channels": sorted(names), "count": len(names)}
        for family, names in sorted(families.items())
    ]


def _family_for_channel(channel: str) -> str:
    folded = channel.casefold()
    if "strain" in folded:
        return "strain"
    if "load" in folded or "force" in folded:
        return "load"
    if "extension" in folded or "displacement" in folded:
        return "extension"
    if "time" in folded:
        return "time"
    if "stress" in folded:
        return "stress"
    return "other"


def _metadata_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    complete = sum(1 for row in rows if row.get("status") == "pass")
    warning = sum(1 for row in rows if row.get("status") == "warn")
    missing = sum(1 for row in rows if row.get("status") == "fail")
    return {
        "field_count": total,
        "complete": complete,
        "partial": warning,
        "missing": missing,
    }


def _validity_summary(runs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"valid": 0, "invalid": 0, "review": 0, "unspecified": 0}
    for row in runs:
        raw = str(row.get("validity_flag") or "").strip().casefold()
        if raw in {"valid", "accepted", "accept", "true", "1", "yes", "x"}:
            counts["valid"] += 1
        elif raw in {"invalid", "false", "0", "no", "failed", "fail"}:
            counts["invalid"] += 1
        elif raw in {"review", "requires_review"}:
            counts["review"] += 1
        else:
            counts["unspecified"] += 1
    return counts


def _value_counts(runs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in runs:
        value = str(row.get(key) or "unspecified").strip() or "unspecified"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _source_identity_summary(runs: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    basenames: dict[str, int] = {}
    for row in runs:
        source = str(row.get("source_relative_path") or row.get("original_filename") or "")
        name = source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if source else ""
        if name:
            basenames[name] = basenames.get(name, 0) + 1
    repeated = sorted(name for name, count in basenames.items() if count > 1)
    return {
        "distinct_sources": len({str(row.get("source_relative_path") or "") for row in runs if row.get("source_relative_path")}),
        "repeated_basenames": repeated,
        "warning_count": len(warnings),
        "status": "warning" if warnings or repeated else "ok",
    }
