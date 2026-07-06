from __future__ import annotations


class PintBackend:
    name = "pint"

    def __init__(self) -> None:
        try:
            import pint
        except Exception as exc:  # pragma: no cover - depends on optional environment
            raise RuntimeError("Pint is not available.") from exc
        self._ureg = pint.UnitRegistry()
        self._ureg.define("usn = 1e-6 = microstrain")

    def factor(self, from_unit: str, to_unit: str) -> float:
        return float((1 * self._ureg(from_unit)).to(to_unit).magnitude)
