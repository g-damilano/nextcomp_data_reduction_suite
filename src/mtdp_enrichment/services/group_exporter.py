from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.models import ValidationResult
from mtdp_enrichment.package import MTDPPackageWriter, RunInput

from .group_state import GroupState


class GroupExporter:
    """Backend facade for writing editable group state to a clean .mtdp archive."""

    def __init__(self, writer: MTDPPackageWriter | None = None) -> None:
        self.writer = writer or MTDPPackageWriter()

    def export_group(self, group: GroupState, output_path: str | Path) -> ValidationResult:
        run_inputs = [
            RunInput(
                run.run_id,
                run.parsed,
                run.enrichment,
                run.field_units,
                supplemental_yaml=run.sidecar_path,
                images=tuple(run.images),
                import_conflicts=tuple(run.sidecar_conflicts),
                unknown_supplemental_keys=tuple(run.sidecar_unknown_keys),
                supplemental_import_mode=run.sidecar_import_mode,
                mapping_profile_id=run.sidecar_mapping_profile_id,
                mapping_profile_path=run.sidecar_mapping_profile_path,
                supplemental_files=tuple(run.supplemental_files),
            )
            for run in group.runs
        ]
        return self.writer.create_dataset_package(
            run_inputs,
            group.schema,
            output_path,
            group.dataset_enrichment,
            dataset_field_units=group.dataset_units,
            grouping_confirmation={
                "group_name": group.display_name,
                "run_count": len(group.runs),
                "manual_corrections": group.manual_corrections,
                "removed_runs": list(group.removed_runs),
            },
            supplemental_files=tuple(group.supplemental_files),
        )
