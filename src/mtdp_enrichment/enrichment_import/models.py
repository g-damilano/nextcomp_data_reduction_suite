from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SupplementalYamlDocument:
    source_path: Path
    raw_payload: dict[str, Any]
    is_canonical: bool
    version: str | None
    structure_signature: str
    key_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImportedFieldCandidate:
    field_id: str
    value: Any
    unit: str | None
    source_path: Path
    source_key: str
    source_format: str = "supplemental_yaml"


@dataclass(frozen=True, slots=True)
class ImportedImageReference:
    path: Path
    view: str
    role: str = "audit_evidence"
    used_for_metrology: bool = False
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class FieldConflict:
    field_id: str
    existing_value: Any
    existing_unit: str | None
    imported_value: Any
    imported_unit: str | None
    existing_source: str
    imported_source: str
    message: str


@dataclass(frozen=True, slots=True)
class ValueTransformResult:
    raw_value: Any
    canonical_value: Any
    raw_unit: str | None
    canonical_unit: str | None
    transform_name: str
    confidence: float
    requires_confirmation: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconciledMappingRow:
    source_key: str
    raw_value: Any
    target_field_id: str | None
    transformed: ValueTransformResult | None
    storage_preview: str | None
    status: str
    action: str


@dataclass(frozen=True, slots=True)
class SupplementalImportResult:
    document: SupplementalYamlDocument | None
    imported_fields: dict[str, ImportedFieldCandidate]
    conflicts: tuple[FieldConflict, ...]
    unknown_keys: tuple[str, ...]
    requires_mapping: bool
    mapping_profile_id: str | None
    mapping_profile_path: Path | None
    warnings: tuple[str, ...]
    image_references: tuple[ImportedImageReference, ...] = ()

    @property
    def source_path(self) -> Path | None:
        return self.document.source_path if self.document is not None else None
