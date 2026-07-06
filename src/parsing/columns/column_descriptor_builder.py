from __future__ import annotations

from collections import defaultdict

from parsing.columns.family_classifier import (
    canonical_unit_from_text,
    classify_channel_family,
    extract_embedded_unit,
    infer_alias,
)
from parsing.models import ColumnDescriptor, TableLayoutRecord


class ColumnClassificationPass:
    """Pass P4: convert raw headers into canonical column descriptors."""

    def run(
        self,
        header_row: list[str],
        units_row: list[str] | None,
        layout: TableLayoutRecord,
    ) -> list[ColumnDescriptor]:
        counters: dict[str, int] = defaultdict(int)
        descriptors: list[ColumnDescriptor] = []
        for idx, name in enumerate(header_row):
            original_name = name.strip()
            explicit_unit_text = units_row[idx].strip() if units_row and idx < len(units_row) else None
            embedded_unit_text = extract_embedded_unit(original_name)
            unit_text = explicit_unit_text or embedded_unit_text
            family = "record_id" if idx == 0 and not original_name else classify_channel_family(original_name, unit_text)
            counters[family] += 1
            ordinal = counters[family]
            canonical_name = f"{family}_{ordinal}"
            source_notes: list[str] = ["classified from header"]
            if embedded_unit_text and not explicit_unit_text:
                source_notes.append("unit inferred from header")
            descriptors.append(
                ColumnDescriptor(
                    column_index=idx,
                    original_name=original_name,
                    original_unit_text=unit_text,
                    family=family,
                    ordinal=ordinal,
                    canonical_name=canonical_name,
                    alias=infer_alias(original_name),
                    canonical_unit=canonical_unit_from_text(unit_text, family),
                    source_notes=tuple(source_notes),
                )
            )
        return descriptors
