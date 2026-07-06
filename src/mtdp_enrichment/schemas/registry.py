from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml
from parsing.models import ParsedSampleRecord

from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.schemas.linter import lint_schema
from runtime.resources import default_resolver


SCHEMA_LIBRARY_ROOT = default_resolver().schema_library_root()


@dataclass(frozen=True, slots=True)
class SchemaInference:
    schema: MTDPSchema
    confidence: float
    reasons: tuple[str, ...]


class SchemaRegistry:
    """File-backed registry for schema-driven UI/package behavior."""

    def __init__(
        self,
        schemas: Iterable[MTDPSchema] | None = None,
        *,
        schema_dirs: Iterable[str | Path] | None = None,
    ) -> None:
        loaded = tuple(schemas) if schemas is not None else self._load_schema_dirs(schema_dirs)
        self._schemas = {(schema.schema_id, schema.schema_version): schema for schema in loaded}
        if not self._schemas:
            raise RuntimeError("No MTDP schemas were loaded.")

    def all(self) -> list[MTDPSchema]:
        return sorted(
            self._schemas.values(),
            key=lambda item: (
                item.display_label.casefold(),
                _status_rank(item.status),
                _reverse_semantic_version_key(item.schema_version),
            ),
        )

    def selectable(self) -> list[MTDPSchema]:
        """Schemas shown for new work: one current version per schema family."""

        return sorted(
            (self.latest(schema_id) for schema_id in self.schema_ids()),
            key=lambda item: item.display_label.casefold(),
        )

    def schema_ids(self) -> list[str]:
        return sorted({schema.schema_id for schema in self._schemas.values()})

    def versions_for(self, schema_id: str) -> list[MTDPSchema]:
        versions = [schema for schema in self._schemas.values() if schema.schema_id == schema_id]
        return sorted(versions, key=lambda item: _semantic_version_key(item.schema_version), reverse=True)

    def latest(self, schema_id: str) -> MTDPSchema:
        candidates = [schema for schema in self.versions_for(schema_id) if schema.status == "active"]
        if not candidates:
            candidates = self.versions_for(schema_id)
        if not candidates:
            raise KeyError(schema_id)
        return candidates[0]

    def effective_status(self, schema: MTDPSchema) -> str:
        """Return the lifecycle status users should see for this registry.

        Older versions are deprecated once a newer active version exists, even
        when the historical schema file still says active.
        """

        latest = self.latest(schema.schema_id)
        if schema.schema_version != latest.schema_version:
            return "deprecated"
        return schema.status

    def is_current(self, schema: MTDPSchema) -> bool:
        return self.effective_status(schema) == "active"

    def get(self, schema_id: str, schema_version: str | None = None) -> MTDPSchema:
        if schema_version is not None:
            return self._schemas[(schema_id, str(schema_version))]
        return self.latest(schema_id)

    def infer(self, parsed: ParsedSampleRecord, source_path: str | Path | None = None) -> SchemaInference:
        path_text = str(source_path or parsed.source_file).lower()
        token_text = " ".join(
            str(item.coerced_value_text or item.raw_value or "") for item in parsed.preamble_tokens
        ).lower()
        header_text = " ".join(parsed.raw_header).lower()
        families = {channel.descriptor.family for channel in parsed.channels.all_channels()}

        scores: dict[str, tuple[float, list[str]]] = {
            schema_id: (0.0, []) for schema_id in self.schema_ids()
        }

        def add(schema_id: str, amount: float, reason: str) -> None:
            if schema_id not in scores:
                return
            score, reasons = scores[schema_id]
            reasons.append(reason)
            scores[schema_id] = (score + amount, reasons)

        if "comp" in path_text or "compression" in path_text or "comp" in token_text:
            add("mechanical.compression", 0.55, "compression text found in filename or tokens")
        if "tensile" in path_text or "tension" in path_text or "tensile" in token_text:
            add("mechanical.tensile", 0.55, "tensile text found in filename or tokens")
        if "flex" in path_text or "bend" in path_text or "flexural" in token_text:
            add("mechanical.flexural", 0.55, "flexural text found in filename or tokens")
        if {"load", "extension", "strain", "time"}.issubset(families):
            add("mechanical.compression", 0.20, "load/extension/strain/time channels detected")
            add("mechanical.tensile", 0.15, "load/extension/strain/time channels detected")
        if "stress" in families or "stress" in header_text:
            add("mechanical.generic_stress_strain", 0.30, "stress-strain channel context detected")
        if "failure mode" in header_text or any(
            item.normalized_key == "failure_mode" for item in parsed.preamble_tokens
        ):
            add("mechanical.compression", 0.10, "failure-mode token detected")

        best_schema_id, (best_score, reasons) = max(scores.items(), key=lambda item: item[1][0])
        if best_score <= 0:
            best_schema_id = (
                "mechanical.generic_stress_strain"
                if "mechanical.generic_stress_strain" in scores
                else self.schema_ids()[0]
            )
            best_score = 0.25
            reasons = ["no strong method clues; generic/default schema selected"]

        return SchemaInference(
            schema=self.latest(best_schema_id),
            confidence=min(0.95, best_score),
            reasons=tuple(reasons),
        )

    def _load_schema_dirs(self, schema_dirs: Iterable[str | Path] | None) -> tuple[MTDPSchema, ...]:
        dirs = [Path(item) for item in (schema_dirs or (SCHEMA_LIBRARY_ROOT,))]
        schemas: list[MTDPSchema] = []
        for directory in dirs:
            if not directory.exists():
                continue
            for path in sorted(directory.rglob("*")):
                if path.parent.name == "migrations":
                    continue
                if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                    continue
                schemas.append(self._load_schema_file(path))
        return tuple(schemas)

    def _load_schema_file(self, path: Path) -> MTDPSchema:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Schema file {path} did not contain a mapping.")
        schema = MTDPSchema.from_dict(payload)
        lint_schema(schema).raise_for_errors(schema_label=f"{schema.schema_id} v{schema.schema_version}")
        return schema


def _semantic_version_key(version: str) -> tuple[int, int, int, str]:
    pieces = str(version).split(".", 2)
    nums: list[int] = []
    suffix = ""
    for piece in pieces:
        numeric = ""
        rest = ""
        for char in piece:
            if char.isdigit() and not rest:
                numeric += char
            else:
                rest += char
        nums.append(int(numeric or 0))
        suffix += rest
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2], suffix


def _reverse_semantic_version_key(version: str) -> tuple[int, int, int, str]:
    major, minor, patch, suffix = _semantic_version_key(version)
    return -major, -minor, -patch, suffix


def _status_rank(status: str) -> int:
    return {
        "active": 0,
        "experimental": 1,
        "deprecated": 2,
        "legacy_read_only": 3,
    }.get(status, 9)
