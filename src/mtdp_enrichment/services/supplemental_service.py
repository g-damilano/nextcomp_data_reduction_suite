from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.supplemental import SupplementalFile

from .group_state import GroupState, RunState


class SupplementalService:
    """Headless management for general supplemental files."""

    def add_dataset_file(
        self,
        group: GroupState,
        source_path: str | Path,
        *,
        scope: str = "dataset",
        role: str = "documents",
        notes: str | None = None,
    ) -> SupplementalFile:
        item = SupplementalFile(Path(source_path), scope=scope, role=role, notes=notes)
        group.supplemental_files.append(item)
        return item

    def add_run_file(
        self,
        run: RunState,
        source_path: str | Path,
        *,
        role: str = "documents",
        notes: str | None = None,
    ) -> SupplementalFile:
        item = SupplementalFile(Path(source_path), scope="run", role=role, run_id=run.run_id, notes=notes)
        run.supplemental_files.append(item)
        return item

    def remove_dataset_file(self, group: GroupState, index: int) -> SupplementalFile:
        return group.supplemental_files.pop(index)

    def remove_run_file(self, run: RunState, index: int) -> SupplementalFile:
        return run.supplemental_files.pop(index)
