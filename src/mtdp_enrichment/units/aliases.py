from __future__ import annotations


ALIASES = {
    "kn": "kN",
    "n": "N",
    "pa": "Pa",
    "kpa": "kPa",
    "mpa": "MPa",
    "n/mm2": "MPa",
    "n/mm^2": "MPa",
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "um": "um",
    "µm": "um",
    "s": "s",
    "sec": "s",
    "second": "s",
    "seconds": "s",
    "ms": "ms",
    "msec": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "us": "us",
    "usec": "us",
    "Âµs": "us",
    "µs": "us",
    "μs": "us",
    "microsecond": "us",
    "microseconds": "us",
    "usn": "usn",
    "µsn": "usn",
    "ue": "usn",
    "µe": "usn",
    "microstrain": "usn",
    "strain": "mm/mm",
    "mm/mm": "mm/mm",
    "mm/min": "mm/min",
    "mm_min": "mm/min",
    "mm-min": "mm/min",
    "mm per min": "mm/min",
    "m/s": "m/s",
    "mm2": "mm^2",
    "mm^2": "mm^2",
    "cm2": "cm^2",
    "cm^2": "cm^2",
    "m2": "m^2",
    "m^2": "m^2",
    "kn/s": "kN/s",
}


def normalize_unit_text(unit: str | None) -> str | None:
    if unit is None:
        return None
    text = str(unit).strip().strip("()").strip()
    return ALIASES.get(text.casefold(), text)
