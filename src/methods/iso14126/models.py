from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISO14126SpecimenResult:
    run_id: str
    max_load_N: float | None
    compressive_strength_MPa: float | None
    compressive_failure_strain: float | None
    compressive_modulus_MPa: float | None

