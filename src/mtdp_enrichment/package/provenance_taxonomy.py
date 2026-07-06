from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping

from mtdp_enrichment import __version__


PACKAGE_CREATED = "package_created"
PACKAGE_REPROCESSED = "package_reprocessed"
SCHEMA_MIGRATED = "schema_migrated"
RUN_ADDED = "run_added"
RUN_REMOVED = "run_removed"
RUN_REPLACED = "run_replaced"
RAW_FILE_IMPORTED = "raw_file_imported"
NORMALIZED_FILE_WRITTEN = "normalized_file_written"
YAML_SIDECAR_IMPORTED = "yaml_sidecar_imported"
YAML_MAPPING_PROFILE_APPLIED = "yaml_mapping_profile_applied"
YAML_RECONCILIATION_CONFIRMED = "yaml_reconciliation_confirmed"
UNIT_NORMALIZED = "unit_normalized"
IMAGE_EVIDENCE_ADDED = "image_evidence_added"
IMAGE_EVIDENCE_REMOVED = "image_evidence_removed"
SUPPLEMENTAL_FILE_ADDED = "supplemental_file_added"
SUPPLEMENTAL_FILE_REMOVED = "supplemental_file_removed"
GROUPING_CONFIRMED = "grouping_confirmed"
VALIDATION_RUN = "validation_run"
USER_OVERRIDE_RECORDED = "user_override_recorded"

KNOWN_EVENTS = {
    PACKAGE_CREATED,
    PACKAGE_REPROCESSED,
    SCHEMA_MIGRATED,
    RUN_ADDED,
    RUN_REMOVED,
    RUN_REPLACED,
    RAW_FILE_IMPORTED,
    NORMALIZED_FILE_WRITTEN,
    YAML_SIDECAR_IMPORTED,
    YAML_MAPPING_PROFILE_APPLIED,
    YAML_RECONCILIATION_CONFIRMED,
    UNIT_NORMALIZED,
    IMAGE_EVIDENCE_ADDED,
    IMAGE_EVIDENCE_REMOVED,
    SUPPLEMENTAL_FILE_ADDED,
    SUPPLEMENTAL_FILE_REMOVED,
    GROUPING_CONFIRMED,
    VALIDATION_RUN,
    USER_OVERRIDE_RECORDED,
    # Legacy names still accepted by the validator for readable older packages.
    "parsed",
    "sidecar_yaml_imported",
    "supplemental_mapping_profile_applied",
    "supplemental_yaml_reconciled",
    "run_removed_from_group",
    "user_enrichment_confirmed",
    "image_metrology",
}


def utcish_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_event(
    event: str,
    *,
    scope: str,
    actor: str = "mtdp_enrichment_tool",
    run_id: str | None = None,
    details: Mapping[str, object] | None = None,
    inputs: Iterable[str] = (),
    outputs: Iterable[str] = (),
    warnings: Iterable[str] = (),
) -> dict[str, object]:
    payload: dict[str, object] = {
        "event": event,
        "timestamp": utcish_now_iso(),
        "software_version": __version__,
        "actor": actor,
        "scope": scope,
        "details": dict(details or {}),
    }
    if run_id:
        payload["run_id"] = run_id
    if inputs:
        payload["inputs"] = list(inputs)
    if outputs:
        payload["outputs"] = list(outputs)
    if warnings:
        payload["warnings"] = list(warnings)
    return payload


def event_has_minimum_shape(event: object) -> bool:
    if not isinstance(event, dict):
        return False
    return bool(event.get("event")) and bool(event.get("timestamp") or event.get("parser"))
