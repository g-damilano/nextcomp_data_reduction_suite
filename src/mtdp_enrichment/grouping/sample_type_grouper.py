from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

from mtdp_enrichment.grouping.canonicalizer import SampleNameCanonicalizer
from mtdp_enrichment.grouping.duplicate_filename_detector import duplicate_source_basenames
from mtdp_enrichment.grouping.filename_patterns import FilenameGroupingStrategy
from mtdp_enrichment.grouping.models import (
    GroupingInput,
    GroupingProposal,
    ProposedBundle,
    ProposedRunAssignment,
    SuggestedMerge,
)
from mtdp_enrichment.package import MTDPSchema


class SampleTypeGrouper:
    engine_name = "SampleTypeGrouper"
    engine_version = "0.1.0"

    def propose(self, inputs: Sequence[GroupingInput], schema: MTDPSchema) -> GroupingProposal:
        config = schema.dataset_grouping or {}
        if not config.get("enabled", True):
            return GroupingProposal(bundles=(), unassigned=tuple(inputs), suggested_merges=())

        canonicalizer = SampleNameCanonicalizer(config.get("canonicalization", {}))
        filename_strategy = FilenameGroupingStrategy(config.get("filename_grouping", {}))
        duplicate_basenames = duplicate_source_basenames(item.source_path for item in inputs)
        assignments_by_key: dict[str, list[ProposedRunAssignment]] = defaultdict(list)
        unassigned: list[GroupingInput] = []

        for item in inputs:
            assignment = self._assignment_for(item, config, canonicalizer, filename_strategy, duplicate_basenames)
            if assignment is None:
                unassigned.append(item)
            else:
                assignments_by_key[assignment.proposed_bundle_key].append(assignment)

        bundles = tuple(
            ProposedBundle(
                bundle_key=key,
                display_name=assignments[0].proposed_bundle_name,
                assignments=tuple(sorted(assignments, key=lambda item: item.source_path.as_posix().lower())),
            )
            for key, assignments in sorted(assignments_by_key.items(), key=lambda item: item[1][0].proposed_bundle_name.casefold())
        )
        return GroupingProposal(
            bundles=bundles,
            unassigned=tuple(unassigned),
            suggested_merges=self._suggest_merges(bundles, config),
        )

    def _assignment_for(
        self,
        item: GroupingInput,
        config: dict[str, Any],
        canonicalizer: SampleNameCanonicalizer,
        filename_strategy: FilenameGroupingStrategy,
        duplicate_basenames: set[str],
    ) -> ProposedRunAssignment | None:
        priority = config.get("source_priority", ("parsed_token", "filename_pattern", "folder_name", "manual"))
        repeated_anonymous_name = item.source_path.name.casefold() in duplicate_basenames
        for source in priority:
            if source == "sidecar_field":
                candidate, evidence = self._candidate_from_sidecar(item, config)
                if candidate:
                    canonical = canonicalizer.canonicalize(candidate)
                    return ProposedRunAssignment(
                        source_path=item.source_path,
                        proposed_bundle_key=canonical.canonical_key,
                        proposed_bundle_name=canonical.display_name,
                        confidence=0.96,
                        reason="supplemental YAML field",
                        evidence=evidence,
                    )
            elif source == "parsed_token":
                candidate, evidence = self._candidate_from_tokens(item, config)
                if candidate:
                    canonical = canonicalizer.canonicalize(candidate)
                    return ProposedRunAssignment(
                        source_path=item.source_path,
                        proposed_bundle_key=canonical.canonical_key,
                        proposed_bundle_name=canonical.display_name,
                        confidence=0.95,
                        reason="explicit parsed token",
                        evidence=evidence,
                    )
            elif source == "filename_pattern":
                if repeated_anonymous_name:
                    continue
                candidate, evidence = filename_strategy.candidate_from_path(item.source_path)
                if candidate:
                    canonical = canonicalizer.canonicalize(candidate)
                    return ProposedRunAssignment(
                        source_path=item.source_path,
                        proposed_bundle_key=canonical.canonical_key,
                        proposed_bundle_name=canonical.display_name,
                        confidence=0.82,
                        reason="filename pattern",
                        evidence=evidence,
                    )
            elif source == "folder_name":
                candidate = item.source_path.parent.name.strip()
                if candidate:
                    canonical = canonicalizer.canonicalize(candidate)
                    return ProposedRunAssignment(
                        source_path=item.source_path,
                        proposed_bundle_key=canonical.canonical_key,
                        proposed_bundle_name=canonical.display_name,
                        confidence=0.60,
                        reason="parent folder name",
                        evidence=(f"parent folder: {candidate}",),
                    )
        return None

    def _candidate_from_tokens(
        self,
        item: GroupingInput,
        config: dict[str, Any],
    ) -> tuple[str | None, tuple[str, ...]]:
        wanted = {str(token).casefold() for token in config.get("parsed_tokens", ())}
        for token in item.parsed.preamble_tokens:
            if token.raw_key.strip().casefold() in wanted:
                value = (token.coerced_value_text or token.raw_value).strip()
                if value:
                    return value, (f"token {token.raw_key}: {value}",)
        return None, ()

    def _candidate_from_sidecar(
        self,
        item: GroupingInput,
        config: dict[str, Any],
    ) -> tuple[str | None, tuple[str, ...]]:
        if item.supplemental_import is None:
            return None, ()
        grouping_field = str(config.get("grouping_field", "sample_type"))
        candidate = item.supplemental_import.imported_fields.get(grouping_field)
        if candidate is None:
            return None, ()
        value = str(candidate.value).strip()
        if not value:
            return None, ()
        return value, (f"supplemental YAML {candidate.source_key}: {value}",)

    def _suggest_merges(
        self,
        bundles: tuple[ProposedBundle, ...],
        config: dict[str, Any],
    ) -> tuple[SuggestedMerge, ...]:
        matching = config.get("matching", {}) or {}
        if not matching.get("fuzzy_suggestions", True):
            return ()
        threshold = float(matching.get("suggest_merge_threshold", 0.86))
        suggestions: list[SuggestedMerge] = []
        for index, left in enumerate(bundles):
            for right in bundles[index + 1:]:
                similarity = SequenceMatcher(None, left.bundle_key, right.bundle_key).ratio()
                if threshold <= similarity < 1.0:
                    source, target = sorted((left, right), key=lambda item: len(item.display_name))
                    suggestions.append(
                        SuggestedMerge(
                            source_key=source.bundle_key,
                            target_key=target.bundle_key,
                            source_name=source.display_name,
                            target_name=target.display_name,
                            similarity=similarity,
                            reason="similar canonical sample-type names",
                        )
                    )
        return tuple(sorted(suggestions, key=lambda item: item.similarity, reverse=True))
