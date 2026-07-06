from __future__ import annotations

from typing import Iterable

from mtdp_enrichment.package.provenance_taxonomy import (
    GROUPING_CONFIRMED,
    IMAGE_EVIDENCE_ADDED,
    PACKAGE_CREATED,
    RAW_FILE_IMPORTED,
    RUN_REMOVED,
    SUPPLEMENTAL_FILE_ADDED,
    USER_OVERRIDE_RECORDED,
    YAML_MAPPING_PROFILE_APPLIED,
    YAML_RECONCILIATION_CONFIRMED,
    YAML_SIDECAR_IMPORTED,
    build_event,
    utcish_now_iso,
)


def package_created_event() -> dict[str, object]:
    event = build_event(PACKAGE_CREATED, scope="dataset", details={"package_format": "mtdp"})
    event["software"] = "mtdp_enrichment_tool"
    return event


def parsed_event(parser_name: str, parser_version: str) -> dict[str, object]:
    event = build_event(
        RAW_FILE_IMPORTED,
        scope="run",
        details={"parser": parser_name, "parser_version": parser_version},
    )
    event["parser"] = parser_name
    event["parser_version"] = parser_version
    return event


def user_confirmation_event(field_ids: Iterable[str]) -> dict[str, object] | None:
    fields = sorted(set(field_ids))
    if not fields:
        return None
    event = build_event(USER_OVERRIDE_RECORDED, scope="run", details={"fields": fields})
    event["fields"] = fields
    return event


def grouping_confirmed_event(
    *,
    group_name: str | None = None,
    bundle_name: str | None = None,
    run_count: int,
    manual_corrections: int = 0,
    grouping_engine: str = "SampleTypeGrouper",
    grouping_engine_version: str = "0.1.0",
) -> dict[str, object]:
    name = group_name if group_name is not None else str(bundle_name or "")
    event = build_event(
        GROUPING_CONFIRMED,
        scope="dataset",
        details={
            "grouping_engine": grouping_engine,
            "grouping_engine_version": grouping_engine_version,
            "group_name": name,
            "run_count": run_count,
            "manual_corrections": manual_corrections,
        },
    )
    event.update(
        {
            "grouping_engine": grouping_engine,
            "grouping_engine_version": grouping_engine_version,
            "group_name": name,
            "run_count": run_count,
            "manual_corrections": manual_corrections,
        }
    )
    return event


def supplemental_input_record(
    *,
    original_filename: str,
    package_path: str,
    used_for_prefill: bool = True,
    conflicts: int = 0,
    unknown_keys: Iterable[str] = (),
    import_mode: str | None = None,
    mapping_profile_id: str | None = None,
    mapping_profile_path: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "type": "sidecar_yaml",
        "original_filename": original_filename,
        "package_path": package_path,
        "used_for_prefill": used_for_prefill,
        "conflicts_detected": conflicts,
        "unknown_keys": sorted(set(unknown_keys)),
    }
    if import_mode:
        record["import_mode"] = import_mode
    if mapping_profile_id:
        record["mapping_profile_id"] = mapping_profile_id
    if mapping_profile_path:
        record["mapping_profile_path"] = mapping_profile_path
    return record


def sidecar_import_event(
    *,
    package_path: str,
    imported_fields: Iterable[str],
    unknown_keys: Iterable[str] = (),
    import_mode: str | None = None,
    mapping_profile_id: str | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        **build_event(
            YAML_SIDECAR_IMPORTED,
            scope="run",
            details={
                "package_path": package_path,
                "imported_fields": sorted(set(imported_fields)),
                "unknown_keys": sorted(set(unknown_keys)),
            },
            inputs=[package_path],
        ),
        "package_path": package_path,
        "imported_fields": sorted(set(imported_fields)),
        "unknown_keys": sorted(set(unknown_keys)),
    }
    if import_mode:
        event["import_mode"] = import_mode
    if mapping_profile_id:
        event["mapping_profile_id"] = mapping_profile_id
    return event


def yaml_mapping_profile_applied_event(
    *,
    mapping_profile_id: str,
    mapping_profile_path: str,
    applied_to_runs: Iterable[str],
) -> dict[str, object]:
    event = build_event(
        YAML_MAPPING_PROFILE_APPLIED,
        scope="dataset",
        details={
            "mapping_profile_id": mapping_profile_id,
            "mapping_profile_path": mapping_profile_path,
            "applied_to_runs": sorted(set(applied_to_runs)),
        },
        inputs=[mapping_profile_path],
    )
    event.update(
        {
            "mapping_profile_id": mapping_profile_id,
            "mapping_profile_path": mapping_profile_path,
            "applied_to_runs": sorted(set(applied_to_runs)),
        }
    )
    return event


def run_removed_event(
    *,
    run_id: str,
    original_filename: str | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        **build_event(RUN_REMOVED, scope="dataset", run_id=run_id, details={"original_filename": original_filename or ""}),
        "run_id": run_id,
    }
    if original_filename:
        event["original_filename"] = original_filename
    return event


def yaml_reconciliation_confirmed_event(
    *,
    run_id: str,
    mapping_profile_id: str | None = None,
    date_transforms: Iterable[dict[str, object]] = (),
    value_transforms: Iterable[dict[str, object]] = (),
    unit_assumptions: Iterable[dict[str, object]] = (),
    user_confirmed: bool = True,
) -> dict[str, object]:
    event: dict[str, object] = {
        **build_event(
            YAML_RECONCILIATION_CONFIRMED,
            scope="run",
            run_id=run_id,
            details={
                "mapping_profile_id": mapping_profile_id or "",
                "date_transforms": list(date_transforms),
                "value_transforms": list(value_transforms),
                "unit_assumptions": list(unit_assumptions),
                "user_confirmed": user_confirmed,
            },
        ),
        "run_id": run_id,
        "date_transforms": list(date_transforms),
        "value_transforms": list(value_transforms),
        "unit_assumptions": list(unit_assumptions),
        "user_confirmed": user_confirmed,
    }
    if mapping_profile_id:
        event["mapping_profile_id"] = mapping_profile_id
    return event


def image_evidence_record(
    *,
    package_path: str,
    original_filename: str,
    view: str,
    role: str,
    used_for_metrology: bool = False,
    notes: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "package_path": package_path,
        "original_filename": original_filename,
        "view": view,
        "role": role,
        "used_for_metrology": used_for_metrology,
    }
    if notes:
        record["notes"] = notes
    return record


def image_evidence_added_event(
    *,
    run_id: str,
    package_path: str,
    view: str,
    role: str,
) -> dict[str, object]:
    event = build_event(
        IMAGE_EVIDENCE_ADDED,
        scope="run",
        run_id=run_id,
        details={"package_path": package_path, "view": view, "role": role},
        outputs=[package_path],
    )
    event.update({"package_path": package_path, "view": view, "role": role})
    return event


def supplemental_file_added_event(
    *,
    package_path: str,
    scope: str,
    role: str,
    run_id: str | None = None,
) -> dict[str, object]:
    event = build_event(
        SUPPLEMENTAL_FILE_ADDED,
        scope=scope,
        run_id=run_id,
        details={"package_path": package_path, "role": role},
        outputs=[package_path],
    )
    event.update({"package_path": package_path, "role": role})
    return event


def image_metrology_event(
    *,
    module: str,
    module_version: str,
    inputs: Iterable[str],
    outputs: dict[str, object],
    status: str,
) -> dict[str, object]:
    return {
        "event": "image_metrology",
        "timestamp": utcish_now_iso(),
        "module": module,
        "module_version": module_version,
        "inputs": list(inputs),
        "outputs": outputs,
        "status": status,
    }
