from __future__ import annotations

from mtdp_enrichment.units.aliases import normalize_unit_text
from mtdp_enrichment.units.systems import DEFAULT_UNIT_SYSTEM


class DimensionRegistry:
    def __init__(self) -> None:
        self._unit_dimensions: dict[str, str] = {}
        for dimension, policy in DEFAULT_UNIT_SYSTEM.items():
            for unit in policy["accepted_units"]:
                normalized = normalize_unit_text(str(unit))
                if normalized:
                    self._unit_dimensions[normalized] = dimension

    def dimension_for_unit(self, unit: str | None) -> str | None:
        normalized = normalize_unit_text(unit)
        if normalized is None:
            return None
        return self._unit_dimensions.get(normalized)

    def compatible(self, from_unit: str | None, to_unit: str | None, dimension: str | None = None) -> bool:
        source_dimension = self.dimension_for_unit(from_unit)
        target_dimension = self.dimension_for_unit(to_unit)
        if dimension:
            return source_dimension == dimension and target_dimension == dimension
        return source_dimension is not None and source_dimension == target_dimension
