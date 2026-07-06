from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mtdp_enrichment.units.aliases import normalize_unit_text
from mtdp_enrichment.units.dimensions import DimensionRegistry
from mtdp_enrichment.units.systems import UnitSystemRegistry


class UnitValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuantityValue:
    value: float
    unit: str
    dimension: str | None = None


@dataclass(frozen=True, slots=True)
class FieldUnitPolicy:
    dimension: str | None
    standard_unit: str | None
    accepted_units: tuple[str, ...] = ()


class FieldUnitPolicyResolver:
    """Resolve schema field/table unit declarations into one MTDP unit policy."""

    def __init__(self, unit_normaliser: "UnitNormaliser | None" = None) -> None:
        self.unit_normaliser = unit_normaliser or UnitNormaliser(prefer_pint=False)

    def resolve_field(self, schema: Any, field: Any) -> FieldUnitPolicy:
        return self._resolve(
            schema=schema,
            unit_dimension=getattr(field, "unit_dimension", None),
            accepted_units=tuple(getattr(field, "accepted_units", ()) or ()),
            standard_unit=getattr(field, "standard_unit", None),
        )

    def resolve_table_column(self, schema: Any, column: Any) -> FieldUnitPolicy:
        return self._resolve(
            schema=schema,
            unit_dimension=getattr(column, "unit_dimension", None),
            accepted_units=tuple(getattr(column, "accepted_units", ()) or ()),
            standard_unit=getattr(column, "standard_unit", None),
        )

    def _resolve(
        self,
        *,
        schema: Any,
        unit_dimension: str | None,
        accepted_units: tuple[str, ...],
        standard_unit: str | None,
    ) -> FieldUnitPolicy:
        dimension = unit_dimension
        normalized_standard = normalize_unit_text(standard_unit)
        if dimension is None and normalized_standard:
            dimension = self.unit_normaliser.dimensions.dimension_for_unit(normalized_standard)
        if dimension is None:
            for unit in accepted_units:
                dimension = self.unit_normaliser.dimensions.dimension_for_unit(unit)
                if dimension is not None:
                    break

        policy = self._dimension_policy(schema, dimension)
        system_standard = normalize_unit_text(policy.get("standard_unit")) if policy else None
        system_accepted = tuple(
            unit
            for unit in (normalize_unit_text(item) for item in (policy.get("accepted_units", ()) if policy else ()))
            if unit
        )

        resolved_standard = normalized_standard or system_standard
        resolved_accepted = tuple(
            unit for unit in (normalize_unit_text(item) for item in accepted_units) if unit
        ) or system_accepted
        return FieldUnitPolicy(dimension=dimension, standard_unit=resolved_standard, accepted_units=resolved_accepted)

    def _dimension_policy(self, schema: Any, dimension: str | None) -> dict[str, Any] | None:
        if dimension is None:
            return None
        registry = UnitSystemRegistry(getattr(schema, "unit_systems", None))
        system_name = getattr(schema, "unit_system", None) or "mechanical_metric_mm_N"
        return registry.dimension_policy(dimension, system_name)


@dataclass(frozen=True, slots=True)
class UnitConversionResult:
    original_value: float
    original_unit: str
    canonical_value: float
    canonical_unit: str
    dimension: str
    factor: float
    conversion_backend: str
    warnings: tuple[str, ...] = ()


class UnitNormaliser:
    def __init__(self, *, prefer_pint: bool = True) -> None:
        self.dimensions = DimensionRegistry()
        self._pint = None
        if prefer_pint:
            try:
                from mtdp_enrichment.units.pint_backend import PintBackend

                self._pint = PintBackend()
            except RuntimeError:
                self._pint = None

    def normalize_unit_text(self, unit: str | None) -> str | None:
        return normalize_unit_text(unit)

    def conversion_factor(
        self,
        from_unit: str | None,
        to_unit: str | None,
        *,
        dimension: str | None = None,
    ) -> float | None:
        source = normalize_unit_text(from_unit)
        target = normalize_unit_text(to_unit)
        if source is None or target is None:
            return None
        if source == target:
            return 1.0
        resolved_dimension = dimension or self.dimensions.dimension_for_unit(source)
        if not self.dimensions.compatible(source, target, resolved_dimension):
            return None
        factor = _STATIC_FACTORS.get((source, target))
        if factor is not None:
            return factor
        if self._pint is not None:
            try:
                return self._pint.factor(_pint_unit(source), _pint_unit(target))
            except Exception:
                return None
        return None

    def convert(
        self,
        *,
        value: Any,
        from_unit: str,
        to_unit: str,
        dimension: str,
    ) -> UnitConversionResult:
        source = normalize_unit_text(from_unit)
        target = normalize_unit_text(to_unit)
        if source is None or target is None:
            raise UnitValidationError("Both source and target units are required.")
        factor = self.conversion_factor(source, target, dimension=dimension)
        if factor is None:
            raise UnitValidationError(f"Cannot convert {source} to {target} as {dimension}.")
        original_value = float(value)
        backend = "static"
        if self._pint is not None and (source, target) not in _STATIC_FACTORS and source != target:
            backend = "pint"
        return UnitConversionResult(
            original_value=original_value,
            original_unit=source,
            canonical_value=original_value * factor,
            canonical_unit=target,
            dimension=dimension,
            factor=factor,
            conversion_backend=backend,
        )

    def normalise_field(
        self,
        *,
        value: Any,
        from_unit: str,
        field_policy: FieldUnitPolicy,
    ) -> UnitConversionResult:
        if field_policy.standard_unit is None:
            raise UnitValidationError("Field policy does not define a standard unit.")
        dimension = field_policy.dimension or self.dimensions.dimension_for_unit(field_policy.standard_unit)
        if dimension is None:
            raise UnitValidationError(f"Cannot infer dimension for {field_policy.standard_unit}.")
        return self.convert(
            value=value,
            from_unit=from_unit,
            to_unit=field_policy.standard_unit,
            dimension=dimension,
        )


_STATIC_FACTORS = {
    ("kN", "N"): 1000.0,
    ("N", "kN"): 0.001,
    ("cm", "mm"): 10.0,
    ("m", "mm"): 1000.0,
    ("um", "mm"): 0.001,
    ("mm", "cm"): 0.1,
    ("mm", "m"): 0.001,
    ("mm", "um"): 1000.0,
    ("cm^2", "mm^2"): 100.0,
    ("m^2", "mm^2"): 1_000_000.0,
    ("mm^2", "cm^2"): 0.01,
    ("mm^2", "m^2"): 0.000001,
    ("usn", "mm/mm"): 1e-6,
    ("mm/mm", "usn"): 1e6,
    ("Pa", "MPa"): 1e-6,
    ("kPa", "MPa"): 0.001,
    ("MPa", "Pa"): 1_000_000.0,
    ("MPa", "kPa"): 1000.0,
    ("m/s", "mm/min"): 60000.0,
    ("mm/min", "m/s"): 1 / 60000.0,
    ("ms", "s"): 0.001,
    ("s", "ms"): 1000.0,
    ("us", "s"): 0.000001,
    ("s", "us"): 1_000_000.0,
    ("us", "ms"): 0.001,
    ("ms", "us"): 1000.0,
}


def _pint_unit(unit: str) -> str:
    return {
        "um": "micrometer",
        "mm^2": "millimeter ** 2",
        "cm^2": "centimeter ** 2",
        "m^2": "meter ** 2",
        "mm/min": "millimeter / minute",
        "m/s": "meter / second",
        "mm/mm": "dimensionless",
        "usn": "usn",
        "ms": "millisecond",
        "us": "microsecond",
    }.get(unit, unit)


default_unit_normaliser = UnitNormaliser()
