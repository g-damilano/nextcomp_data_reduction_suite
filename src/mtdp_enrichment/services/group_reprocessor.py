from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.enrichment_import import SidecarYamlImporter
from mtdp_enrichment.models import EnrichedFieldValue
from mtdp_enrichment.parsing_gateway import ParserAdapter

from .group_state import GroupState, RunState


class GroupReprocessor:
    """Headless group-edit operations used by UI and tests."""

    def __init__(self, parser: ParserAdapter | None = None, sidecar_importer: SidecarYamlImporter | None = None) -> None:
        self.parser = parser or ParserAdapter()
        self.sidecar_importer = sidecar_importer or SidecarYamlImporter()

    def add_raw_file(self, group: GroupState, source_path: str | Path) -> RunState:
        path = Path(source_path)
        parsed = self.parser.parse(path)
        run_id = _next_run_id(group)
        run = RunState(run_id=run_id, source_path=path, parsed=parsed)
        supplemental = self.sidecar_importer.import_for_run(path, parsed, group.schema)
        for field_id, candidate in supplemental.imported_fields.items():
            run.enrichment[field_id] = EnrichedFieldValue(candidate.value, candidate.unit, candidate.source_format)
            run.field_units[field_id] = candidate.unit
        run.sidecar_path = supplemental.source_path
        run.sidecar_conflicts = list(supplemental.conflicts)
        run.sidecar_unknown_keys = list(supplemental.unknown_keys)
        run.sidecar_mapping_profile_id = supplemental.mapping_profile_id
        run.sidecar_mapping_profile_path = supplemental.mapping_profile_path
        run.sidecar_import_mode = "mapping_profile" if supplemental.mapping_profile_id else ("alias" if supplemental.source_path else None)
        group.runs.append(run)
        group.manual_corrections += 1
        return run

    def remove_run(self, group: GroupState, run_id: str) -> RunState:
        for index, run in enumerate(group.runs):
            if run.run_id == run_id:
                removed = group.runs.pop(index)
                group.removed_runs.append({"run_id": removed.run_id, "original_filename": removed.source_path.name})
                group.manual_corrections += 1
                return removed
        raise KeyError(f"No run with id {run_id}.")


def _next_run_id(group: GroupState) -> str:
    used = {run.run_id for run in group.runs}
    index = 1
    while f"run_{index:03d}" in used:
        index += 1
    return f"run_{index:03d}"
