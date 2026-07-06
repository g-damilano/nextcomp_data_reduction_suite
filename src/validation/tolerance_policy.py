from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TolerancePolicy:
    tolerance_abs: float | None = None
    tolerance_rel: float | None = None
    severity: str = "fail"

    def evaluate(self, computed: float | None, reference: float | None) -> tuple[str, float | None, float | None]:
        if computed is None or reference is None:
            return ("fail", None, None)
        difference_abs = computed - reference
        difference_rel = None if reference == 0 else difference_abs / reference
        limit_abs = self.tolerance_abs
        limit_rel = None if self.tolerance_rel is None or reference == 0 else abs(reference) * self.tolerance_rel
        limits = [value for value in (limit_abs, limit_rel) if value is not None]
        tolerance = max(limits) if limits else 0.0
        if abs(difference_abs) <= tolerance:
            return ("pass", difference_abs, difference_rel)
        return ("warn" if self.severity == "warn" else "fail", difference_abs, difference_rel)
