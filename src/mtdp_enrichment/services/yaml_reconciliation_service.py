from __future__ import annotations

from pathlib import Path
from typing import Mapping

from parsing.models import ParsedSampleRecord

from mtdp_enrichment.enrichment_import import SidecarYamlImporter, SupplementalImportResult, YamlMappingProfile
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.package import MTDPSchema


class YamlReconciliationService:
    """Headless supplemental YAML import/reconciliation facade."""

    def __init__(self, importer: SidecarYamlImporter | None = None) -> None:
        self.importer = importer or SidecarYamlImporter()

    def import_for_run(
        self,
        source_file: str | Path,
        parsed: ParsedSampleRecord,
        schema: MTDPSchema,
        *,
        existing_values: Mapping[str, EnrichedFieldValue] | None = None,
        mapping_profile: YamlMappingProfile | None = None,
    ) -> SupplementalImportResult:
        return self.importer.import_for_run(
            source_file,
            parsed,
            schema,
            existing_values=existing_values,
            mapping_profile=mapping_profile,
        )
