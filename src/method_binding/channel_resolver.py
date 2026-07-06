"""Legacy method-binding scaffold.

The active method-run rail uses mapping profiles plus readiness checks. This
module is classified in docs/project_control/SCAFFOLD_CLASSIFICATION.yaml and
remains only for legacy parser/method-binding tests until that older contract is
removed or redesigned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from parsing.models import ParsedSampleRecord


@dataclass(slots=True)
class ResolvedChannelSelection:
    primary_load: Optional[str] = None
    primary_extension: Optional[str] = None
    primary_time: Optional[str] = None
    selected_strains: list[str] = field(default_factory=list)
    bending_pair: tuple[str, str] | None = None
    notes: tuple[str, ...] = ()


class MethodChannelResolver:
    def run(self, parsed_sample: ParsedSampleRecord, policy: object) -> ResolvedChannelSelection:
        raise NotImplementedError(
            "Deferred legacy method-binding scaffold; see docs/project_control/SCAFFOLD_CLASSIFICATION.yaml."
        )
