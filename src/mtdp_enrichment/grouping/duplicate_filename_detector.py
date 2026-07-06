from __future__ import annotations

from pathlib import Path
from typing import Iterable

from mtdp_enrichment.grouping.source_identity import repeated_basenames


def duplicate_source_basenames(paths: Iterable[str | Path]) -> set[str]:
    """Return case-insensitive basenames that occur in more than one physical path."""

    return repeated_basenames(paths)
