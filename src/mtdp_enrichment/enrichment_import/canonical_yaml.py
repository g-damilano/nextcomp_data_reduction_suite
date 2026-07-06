from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from mtdp_enrichment.enrichment_import.models import ImportedImageReference, SupplementalYamlDocument


CANONICAL_VERSION = "0.1.0"
CANONICAL_META_KEYS = {
    "mtdp_supplemental_version",
    "scope",
    "schema_hint",
    "images",
    "notes",
}


def build_document(source_path: Path, payload: dict[str, Any]) -> SupplementalYamlDocument:
    key_paths = tuple(sorted(flatten_key_paths(payload)))
    return SupplementalYamlDocument(
        source_path=source_path,
        raw_payload=payload,
        is_canonical=is_canonical_payload(payload),
        version=_version_text(payload.get("mtdp_supplemental_version")),
        structure_signature=structure_signature(key_paths),
        key_paths=key_paths,
    )


def is_canonical_payload(payload: Mapping[str, Any]) -> bool:
    return (
        str(payload.get("mtdp_supplemental_version", "")).strip() == CANONICAL_VERSION
        and str(payload.get("scope", "")).strip() == "run"
        and isinstance(payload.get("run"), dict)
    )


def canonical_import_items(payload: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    for section in ("dataset", "run"):
        value = payload.get(section)
        if isinstance(value, dict):
            yield from iter_value_items(value, section)


def iter_value_items(payload: Mapping[str, Any], prefix: str = "") -> Iterable[tuple[str, Any]]:
    for key, value in payload.items():
        source_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and not is_value_unit_mapping(value):
            yield from iter_value_items(value, source_key)
        else:
            yield source_key, value


def flatten_key_paths(payload: Mapping[str, Any], prefix: str = "") -> Iterable[str]:
    for key, value in payload.items():
        source_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and not is_value_unit_mapping(value):
            yield from flatten_key_paths(value, source_key)
        elif isinstance(value, list):
            yield source_key
            for item in value:
                if isinstance(item, dict):
                    yield from flatten_key_paths(item, source_key)
        else:
            yield source_key


def structure_signature(key_paths: Iterable[str]) -> str:
    normalized = "|".join(sorted(str(item) for item in key_paths))
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def is_value_unit_mapping(value: Mapping[str, Any]) -> bool:
    keys = {str(key).casefold() for key in value}
    return "value" in keys


def extract_value_and_unit(raw_value: Any) -> tuple[Any, str | None]:
    if isinstance(raw_value, dict) and is_value_unit_mapping(raw_value):
        lookup = {str(key).casefold(): value for key, value in raw_value.items()}
        unit = lookup.get("unit")
        return lookup.get("value"), None if unit in (None, "") else str(unit).strip().strip("()")
    return raw_value, None


def image_references(payload: Mapping[str, Any], source_path: Path) -> tuple[ImportedImageReference, ...]:
    raw_images = payload.get("images", ())
    if not isinstance(raw_images, list):
        return ()
    references: list[ImportedImageReference] = []
    for item in raw_images:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        path = Path(str(item["path"]))
        if not path.is_absolute():
            path = source_path.parent / path
        references.append(
            ImportedImageReference(
                path=path,
                view=str(item.get("view") or "other"),
                role=str(item.get("role") or "audit_evidence"),
                used_for_metrology=bool(item.get("used_for_metrology", False)),
                notes=None if item.get("notes") in (None, "") else str(item.get("notes")),
            )
        )
    return tuple(references)


def _version_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip()
