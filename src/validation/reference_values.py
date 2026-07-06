from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ReferenceValue:
    run_id: str
    field: str
    reference_value: float
    point_index: int | None = None
    unit: str | None = None
    tolerance_abs: float | None = None
    tolerance_rel: float | None = None
    source: str | None = None
    note: str | None = None

    @property
    def key(self) -> tuple[str, str, int | None]:
        return (self.run_id, self.field, self.point_index)

    def to_row(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "field": self.field,
            "point_index": self.point_index,
            "reference_value": self.reference_value,
            "unit": self.unit,
            "tolerance_abs": self.tolerance_abs,
            "tolerance_rel": self.tolerance_rel,
            "source": self.source,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class ReferenceValueSet:
    source_path: Path | None
    values: tuple[ReferenceValue, ...]

    @classmethod
    def from_csv(cls, path: str | Path) -> "ReferenceValueSet":
        source = Path(path)
        rows = csv.DictReader(source.read_text(encoding="utf-8-sig").splitlines())
        values = tuple(_reference_from_row(row) for row in rows)
        return cls(source_path=source, values=values)

    @classmethod
    def empty(cls) -> "ReferenceValueSet":
        return cls(source_path=None, values=())

    def to_rows(self) -> list[dict[str, Any]]:
        return [value.to_row() for value in self.values]


def _reference_from_row(row: dict[str, str]) -> ReferenceValue:
    return ReferenceValue(
        run_id=str(row.get("run_id") or "").strip(),
        field=str(row.get("field") or "").strip(),
        point_index=_optional_int(row.get("point_index")),
        reference_value=float(str(row.get("reference_value") or "").strip()),
        unit=_optional_text(row.get("unit")),
        tolerance_abs=_optional_float(row.get("tolerance_abs")),
        tolerance_rel=_optional_float(row.get("tolerance_rel")),
        source=_optional_text(row.get("source")),
        note=_optional_text(row.get("note")),
    )


def _optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float(value: str | None) -> float | None:
    text = str(value or "").strip()
    return float(text) if text else None


def _optional_int(value: str | None) -> int | None:
    text = str(value or "").strip()
    return int(text) if text else None
