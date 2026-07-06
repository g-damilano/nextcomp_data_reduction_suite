from __future__ import annotations

DEFAULT_UNIT_SYSTEM = {
    "length": {
        "standard_unit": "mm",
        "accepted_units": ("m", "cm", "mm", "um"),
    },
    "force": {
        "standard_unit": "N",
        "accepted_units": ("N", "kN"),
    },
    "area": {
        "standard_unit": "mm^2",
        "accepted_units": ("m^2", "cm^2", "mm^2"),
    },
    "speed": {
        "standard_unit": "mm/min",
        "accepted_units": ("mm/min", "m/s"),
    },
    "strain": {
        "standard_unit": "mm/mm",
        "accepted_units": ("mm/mm", "usn", "microstrain"),
    },
    "stress": {
        "standard_unit": "MPa",
        "accepted_units": ("Pa", "kPa", "MPa", "N/mm^2", "N/mm2"),
    },
    "time": {
        "standard_unit": "s",
        "accepted_units": ("s", "ms", "us"),
    },
}


class UnitSystemRegistry:
    def __init__(self, systems: dict[str, dict[str, object]] | None = None) -> None:
        self._systems = {"mechanical_metric_mm_N": DEFAULT_UNIT_SYSTEM}
        if systems:
            self._systems.update(systems)

    def dimension_policy(self, dimension: str, system_name: str = "mechanical_metric_mm_N") -> dict[str, object] | None:
        system = self._systems.get(system_name, {})
        if isinstance(system, dict) and isinstance(system.get("dimensions"), dict):
            system = system["dimensions"]
        return system.get(dimension) if isinstance(system, dict) else None
