from __future__ import annotations

from mtdp_enrichment.models import ValidationResult
from mtdp_enrichment.package import MTDPPackageWriter

from .group_state import GroupState


class ValidationService:
    """Schema/table validation for editable group state without Qt."""

    def __init__(self, writer: MTDPPackageWriter | None = None) -> None:
        self.writer = writer or MTDPPackageWriter()

    def validate_group(self, group: GroupState) -> ValidationResult:
        _, validation = group.schema.validate_dataset_fields(group.dataset_enrichment)
        if not group.runs:
            validation.add_error("Group has no included runs.", code="missing_runs")
        for run in group.runs:
            existing = self.writer._existing_fields(run.parsed, group.schema)
            _, run_validation = group.schema.validate_run_fields(run.enrichment, existing_tokens=existing)
            validation.extend(run_validation)
            validation.extend(self.writer.normalizer.normalize(run.parsed, group.schema).validation)
        return validation
