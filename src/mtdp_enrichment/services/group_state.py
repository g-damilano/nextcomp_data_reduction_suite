from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import import FieldConflict
from mtdp_enrichment.image_gateway import RunImageEvidence
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package.schema import MTDPSchema
from mtdp_enrichment.supplemental import SupplementalFile


@dataclass(slots=True)
class RunState:
    run_id: str
    source_path: Path
    parsed: ParsedSampleRecord
    enrichment: dict[str, EnrichedFieldValue] = field(default_factory=dict)
    field_units: dict[str, str | None] = field(default_factory=dict)
    status: str = "parsed"
    sidecar_path: Path | None = None
    sidecar_import_status: str = "No YAML"
    sidecar_conflicts: list[FieldConflict] = field(default_factory=list)
    sidecar_unknown_keys: list[str] = field(default_factory=list)
    sidecar_mapping_profile_id: str | None = None
    sidecar_mapping_profile_path: Path | None = None
    sidecar_import_mode: str | None = None
    images: list[RunImageEvidence] = field(default_factory=list)
    supplemental_files: list[SupplementalFile] = field(default_factory=list)


@dataclass(slots=True)
class GroupState:
    group_key: str
    display_name: str
    schema: MTDPSchema
    runs: list[RunState] = field(default_factory=list)
    dataset_enrichment: dict[str, EnrichedFieldValue] = field(default_factory=dict)
    dataset_units: dict[str, str | None] = field(default_factory=dict)
    run_units: dict[str, str | None] = field(default_factory=dict)
    supplemental_files: list[SupplementalFile] = field(default_factory=list)
    removed_runs: list[dict[str, str]] = field(default_factory=list)
    manual_corrections: int = 0
    source_package_path: Path | None = None
    workspace: object | None = None
