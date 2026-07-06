from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any, Mapping

from mtdp_enrichment.enrichment_import.canonical_yaml import extract_value_and_unit
from mtdp_enrichment.enrichment_import.value_normalizers import extract_unit_from_key, transform_value_for_field
from mtdp_enrichment.models import FieldDefinition
from mtdp_enrichment.package.schema import MTDPSchema, normalize_import_alias


@dataclass(frozen=True, slots=True)
class YamlFieldMatch:
    source_key: str
    source_value: Any
    target_field_id: str | None
    confidence: float
    evidence: tuple[str, ...]
    requires_confirmation: bool
    transform: str | None = None
    unit_candidate: str | None = None
    warnings: tuple[str, ...] = ()


class EmpiricalYamlMatcher:
    """Deterministic, non-LLM YAML-key matcher for reconciliation suggestions."""

    def propose(
        self,
        *,
        source_key: str,
        source_value: Any,
        schema: MTDPSchema,
        historical_profiles: tuple[Mapping[str, str], ...] = (),
    ) -> YamlFieldMatch:
        normalized_key, unit_candidate, unit_status = extract_unit_from_key(source_key)
        exact = self._alias_match(normalized_key, source_key, source_value, schema)
        if exact.target_field_id is not None:
            if unit_candidate and unit_status:
                evidence = (*exact.evidence, unit_status)
                return YamlFieldMatch(
                    source_key,
                    source_value,
                    exact.target_field_id,
                    min(1.0, exact.confidence + 0.03),
                    evidence,
                    exact.requires_confirmation,
                    exact.transform,
                    unit_candidate,
                    exact.warnings,
                )
            return exact

        profile_match = self._historical_profile_match(source_key, source_value, schema, historical_profiles)
        candidates = [profile_match] if profile_match.target_field_id else []
        candidates.extend(
            self._score_field(normalized_key, source_key, source_value, schema, field, unit_candidate)
            for field in schema.dataset_fields + schema.run_fields
        )
        best = max(candidates, key=lambda item: item.confidence, default=YamlFieldMatch(source_key, source_value, None, 0.0, (), True))
        if best.confidence < 0.45:
            return YamlFieldMatch(source_key, source_value, None, 0.0, ("no suitable deterministic match",), True)
        return best

    def _alias_match(self, normalized_key: str, source_key: str, source_value: Any, schema: MTDPSchema) -> YamlFieldMatch:
        for candidate in (source_key, normalized_key, normalized_key.split(".")[-1], source_key.split(".")[-1]):
            match = schema.alias_entry_for_import_alias(candidate)
            if match is None:
                continue
            field, entry = match
            confidence = entry.confidence if entry is not None else 0.75
            kind = entry.kind if entry is not None else "legacy_key"
            requires_confirmation = kind in {"weak_key", "deprecated"} or confidence < 0.70
            transformed = self._transform_text(source_key, source_value, field)
            return YamlFieldMatch(
                source_key=source_key,
                source_value=source_value,
                target_field_id=field.field_id,
                confidence=confidence,
                evidence=(f"alias:{kind}",),
                requires_confirmation=requires_confirmation,
                transform=transformed,
            )
        return YamlFieldMatch(source_key, source_value, None, 0.0, (), True)

    def _historical_profile_match(
        self,
        source_key: str,
        source_value: Any,
        schema: MTDPSchema,
        historical_profiles: tuple[Mapping[str, str], ...],
    ) -> YamlFieldMatch:
        for profile in historical_profiles:
            target_id = profile.get(source_key)
            if target_id and schema.field_by_id(target_id):
                return YamlFieldMatch(
                    source_key,
                    source_value,
                    target_id,
                    0.88,
                    ("historical mapping profile",),
                    False,
                    self._transform_text(source_key, source_value, schema.field_by_id(target_id)),
                )
        return YamlFieldMatch(source_key, source_value, None, 0.0, (), True)

    def _score_field(
        self,
        normalized_key: str,
        source_key: str,
        source_value: Any,
        schema: MTDPSchema,
        field: FieldDefinition,
        unit_candidate: str | None,
    ) -> YamlFieldMatch:
        key_tokens = _tokens(normalized_key)
        field_tokens = _tokens(field.field_id) | _tokens(field.label)
        role_tokens = _tokens(field.role)
        leaf = normalized_key.split(".")[-1]
        ratio = difflib.SequenceMatcher(a=normalize_import_alias(leaf), b=normalize_import_alias(field.field_id)).ratio()
        overlap = len(key_tokens & field_tokens) / max(1, len(field_tokens))
        role_overlap = len(key_tokens & role_tokens) / max(1, len(role_tokens))
        evidence: list[str] = []
        score = max(ratio * 0.55, overlap * 0.70, role_overlap * 0.45)

        semantic = self._semantic_hint(source_key, field.field_id)
        if semantic:
            score += semantic[0]
            evidence.append(semantic[1])
        if unit_candidate and field.accepted_units:
            accepted = {item.casefold() for item in field.accepted_units}
            if unit_candidate.casefold() in accepted:
                score += 0.12
                evidence.append(f"unit suffix:{unit_candidate}")
        if self._value_type_compatible(source_value, field):
            score += 0.08
            evidence.append(f"value compatible:{field.type}")
        if field.required:
            score += 0.03
            evidence.append("target field required")
        if ratio >= 0.80:
            evidence.append("key token similarity")
        confidence = min(score, 0.82)
        requires_confirmation = confidence < 0.86
        warnings: list[str] = []
        if confidence < 0.70:
            warnings.append("Low-confidence empirical match; user confirmation required.")
        return YamlFieldMatch(
            source_key=source_key,
            source_value=source_value,
            target_field_id=field.field_id,
            confidence=confidence,
            evidence=tuple(evidence or ("empirical key similarity",)),
            requires_confirmation=requires_confirmation,
            transform=self._transform_text(source_key, source_value, field),
            unit_candidate=unit_candidate,
            warnings=tuple(warnings),
        )

    def _semantic_hint(self, source_key: str, field_id: str) -> tuple[float, str] | None:
        leaf = source_key.split(".")[-1].casefold()
        if leaf in {"lc", "loadcell"} and field_id == "load_cell":
            return 0.55, "known source shorthand"
        if leaf in {"tester", "user"} and field_id == "operator":
            return 0.45, "known source role"
        if leaf == "date" and field_id == "test_date":
            return 0.55, "date-like key"
        if leaf == "valid" and field_id == "validity":
            return 0.60, "validity value-map key"
        if leaf in {"dimension_a", "width_a"} and field_id == "width":
            return 0.33, "legacy dimension-name pattern"
        if leaf in {"dimension_b", "thickness_b"} and field_id == "thickness":
            return 0.33, "legacy dimension-name pattern"
        return None

    def _value_type_compatible(self, raw_value: Any, field: FieldDefinition) -> bool:
        value, _unit = extract_value_and_unit(raw_value)
        if value in (None, ""):
            return False
        if field.type in {"float", "int"}:
            try:
                float(str(value).strip())
            except (TypeError, ValueError):
                return False
            return True
        if field.type == "date":
            return bool(re.search(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", str(value)))
        if field.type == "bool":
            return str(value).strip().casefold() in {"1", "0", "true", "false", "yes", "no"}
        if field.type == "enum":
            text = str(value).strip()
            return not field.allowed_values or text in field.allowed_values or text.casefold() in {item.casefold() for item in field.allowed_values}
        return True

    def _transform_text(self, source_key: str, source_value: Any, field: FieldDefinition | None) -> str | None:
        value, unit = extract_value_and_unit(source_value)
        transformed = transform_value_for_field(source_key=source_key, raw_value=value, raw_unit=unit, field=field, selected_unit=unit)
        return transformed.transform_name if transformed is not None else None


def _tokens(text: str) -> set[str]:
    return {item for item in re.split(r"[^a-z0-9]+", text.casefold()) if item}
