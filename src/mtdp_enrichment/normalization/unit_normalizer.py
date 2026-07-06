from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from parsing.models import ChannelRecord, ParsedSampleRecord

from mtdp_enrichment.models import ValidationResult
from mtdp_enrichment.package.schema import MTDPSchema
from mtdp_enrichment.package.provenance_taxonomy import UNIT_NORMALIZED, build_event
from mtdp_enrichment.units import UnitNormaliser


@dataclass(frozen=True, slots=True)
class NormalizationEvent:
    event: str
    field: str
    from_unit: str
    to_unit: str
    factor: float
    dimension: str | None = None
    backend: str = "static"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = build_event(
            UNIT_NORMALIZED,
            scope="run",
            details={
                "field": self.field,
                "from_unit": self.from_unit,
                "to_unit": self.to_unit,
                "factor": self.factor,
                "backend": self.backend,
                "dimension": self.dimension or "",
            },
        )
        payload.update(
            {
                "field": self.field,
                "from_unit": self.from_unit,
                "to_unit": self.to_unit,
                "factor": self.factor,
                "backend": self.backend,
            }
        )
        if self.dimension:
            payload["dimension"] = self.dimension
        return payload


@dataclass(frozen=True, slots=True)
class NormalizedColumn:
    header: str
    unit: str | None
    values: tuple[float | None, ...]
    source_column_index: int
    family: str


@dataclass(slots=True)
class NormalizationResult:
    columns: list[NormalizedColumn] = field(default_factory=list)
    events: list[NormalizationEvent] = field(default_factory=list)
    validation: ValidationResult = field(default_factory=ValidationResult)

    @property
    def row_count(self) -> int:
        if not self.columns:
            return 0
        return max(len(column.values) for column in self.columns)


class UnitNormalizer:
    """Normalize parser-provided channel values to the selected schema units."""

    def __init__(self, unit_normaliser: UnitNormaliser | None = None) -> None:
        self.unit_normaliser = unit_normaliser or UnitNormaliser()

    def normalize(self, parsed: ParsedSampleRecord, schema: MTDPSchema) -> NormalizationResult:
        result = NormalizationResult()
        channels = sorted(parsed.channels.all_channels(), key=lambda item: item.source_column_index)
        present_families = {channel.descriptor.family for channel in channels}
        family_counts = Counter(channel.descriptor.family for channel in channels)

        for expected in schema.expected_table:
            if expected.required and expected.family not in present_families:
                result.validation.add_error(
                    f"Required table channel family '{expected.family}' is missing.",
                    field=expected.family,
                    code="missing_table_channel",
                )
            if not expected.repeatable and family_counts.get(expected.family, 0) > 1:
                result.validation.add_error(
                    f"Table channel family '{expected.family}' appears more than once but is not repeatable.",
                    field=expected.family,
                    code="non_repeatable_table_channel",
                )

        for channel in channels:
            normalized = self._normalize_channel(channel, schema, result.validation)
            if normalized is not None:
                column, event = normalized
                result.columns.append(column)
                if event is not None:
                    result.events.append(event)

        return result

    def _normalize_channel(
        self,
        channel: ChannelRecord,
        schema: MTDPSchema,
        validation: ValidationResult,
    ) -> tuple[NormalizedColumn, NormalizationEvent | None] | None:
        definition = schema.table_definition_for_family(channel.descriptor.family)
        source_unit = self.unit_normaliser.normalize_unit_text(channel.original_unit_text)
        parsed_unit = self.unit_normaliser.normalize_unit_text(channel.canonical_unit) or source_unit
        target_unit = self.unit_normaliser.normalize_unit_text(definition.standard_unit) if definition else parsed_unit

        if definition and target_unit and not parsed_unit:
            parsed_unit = target_unit
            validation.add_warning(
                f"{channel.descriptor.original_name} unit is missing; assuming schema standard unit '{target_unit}'.",
                field=channel.descriptor.original_name,
                code="assumed_table_unit",
            )

        if definition and definition.accepted_units:
            accepted = {self.unit_normaliser.normalize_unit_text(unit) for unit in definition.accepted_units}
            if source_unit not in accepted and parsed_unit not in accepted:
                validation.add_error(
                    f"{channel.descriptor.original_name} unit '{channel.original_unit_text}' is not accepted by schema.",
                    field=channel.descriptor.original_name,
                    code="unsupported_table_unit",
                )
                return None

        if target_unit is None:
            target_unit = parsed_unit

        values = tuple(channel.values)
        dimension = definition.unit_dimension if definition and definition.unit_dimension else _dimension_for_family(channel.descriptor.family)
        parser_scale_factor = (
            1.0
            if source_unit == parsed_unit
            else self.unit_normaliser.conversion_factor(source_unit, parsed_unit, dimension=dimension)
        )
        additional_factor = (
            1.0
            if parsed_unit == target_unit
            else self.unit_normaliser.conversion_factor(parsed_unit, target_unit, dimension=dimension)
        )
        if additional_factor is None:
            validation.add_error(
                f"{channel.descriptor.original_name} cannot be converted from {parsed_unit} to {target_unit}.",
                field=channel.descriptor.original_name,
                code="unsupported_table_unit_conversion",
            )
            return None

        if additional_factor != 1.0:
            values = tuple(None if value is None else value * additional_factor for value in values)

        event = None
        if source_unit and target_unit and source_unit != target_unit:
            total_factor = self.unit_normaliser.conversion_factor(source_unit, target_unit, dimension=dimension)
            if total_factor is None and parser_scale_factor is not None:
                total_factor = parser_scale_factor * additional_factor
            if total_factor is not None:
                event = NormalizationEvent(
                    event="unit_normalized",
                    field=channel.descriptor.original_name,
                    from_unit=source_unit,
                    to_unit=target_unit,
                    factor=total_factor,
                    dimension=dimension,
                )

        return (
            NormalizedColumn(
                header=_normalized_header(channel, definition),
                unit=target_unit,
                values=values,
                source_column_index=channel.source_column_index,
                family=channel.descriptor.family,
            ),
            event,
        )


def _dimension_for_family(family: str) -> str | None:
    return {
        "load": "force",
        "force": "force",
        "extension": "length",
        "displacement": "length",
        "strain": "strain",
        "stress": "stress",
        "time": "time",
    }.get(family)


def _normalized_header(channel: ChannelRecord, definition) -> str:
    if definition is not None and not definition.repeatable and definition.label:
        return str(definition.label)
    return channel.descriptor.original_name
