from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import import SupplementalImportResult
from mtdp_enrichment.schemas import SchemaInference


@dataclass(frozen=True, slots=True)
class GroupingInput:
    source_path: Path
    parsed: ParsedSampleRecord
    schema_inference: SchemaInference | None = None
    supplemental_import: SupplementalImportResult | None = None


@dataclass(frozen=True, slots=True)
class ProposedRunAssignment:
    source_path: Path
    proposed_bundle_key: str
    proposed_bundle_name: str
    confidence: float
    reason: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProposedBundle:
    bundle_key: str
    display_name: str
    assignments: tuple[ProposedRunAssignment, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SuggestedMerge:
    source_key: str
    target_key: str
    source_name: str
    target_name: str
    similarity: float
    reason: str


@dataclass(frozen=True, slots=True)
class GroupingProposal:
    bundles: tuple[ProposedBundle, ...]
    unassigned: tuple[GroupingInput, ...]
    suggested_merges: tuple[SuggestedMerge, ...]
