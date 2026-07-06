from __future__ import annotations

import re
import unicodedata
from typing import Optional


_BRACKETED_TEXT_RE = re.compile(r"[\[(]([^\]\)]*)[\])]")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")
_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")

_UNIT_ALIASES = {
    "%": "%",
    "c": "C",
    "celsius": "C",
    "cm": "cm",
    "degc": "C",
    "degreec": "C",
    "degreesc": "C",
    "degreecelsius": "C",
    "degreescelsius": "C",
    "kilo newton": "kN",
    "kilonewton": "kN",
    "kilonewtons": "kN",
    "kn": "kN",
    "kpa": "kPa",
    "in": "in",
    "inch": "in",
    "inches": "in",
    "m": "m",
    "micro strain": "usn",
    "microstrain": "usn",
    "mm": "mm",
    "mm/mm": "mm/mm",
    "mpa": "MPa",
    "n": "N",
    "n/mm2": "N/mm2",
    "n/mm^2": "N/mm2",
    "newton": "N",
    "newtons": "N",
    "pa": "Pa",
    "s": "s",
    "sec": "s",
    "secs": "s",
    "second": "s",
    "seconds": "s",
    "strain": "mm/mm",
    "ue": "usn",
    "um": "um",
    "usn": "usn",
}

_FORCE_UNITS = {"N", "kN"}
_LENGTH_UNITS = {"m", "cm", "mm", "um", "in"}
_STRAIN_UNITS = {"usn", "mm/mm", "%"}
_STRESS_UNITS = {"Pa", "kPa", "MPa", "N/mm2"}
_TIME_UNITS = {"s"}


def normalize_header_text(raw: str) -> str:
    """Return a matching-oriented header string with units and accents removed."""
    text = _split_camel(_repair_mojibake(str(raw or "")))
    text = _BRACKETED_TEXT_RE.sub(" ", text)
    text = _ascii_fold(text)
    text = _SEPARATOR_RE.sub(" ", text)
    return " ".join(text.split())


def normalize_unit_text(unit_text: str | None) -> str | None:
    """Normalize parser-level unit spellings without importing MTDP packaging code."""
    if unit_text is None:
        return None
    text = _ascii_fold(str(unit_text))
    text = text.strip().strip("[](){}").strip()
    if not text:
        return None
    text = text.replace("micro strain", "microstrain")
    text = text.replace(" per ", "/")
    text = re.sub(r"\s+", " ", text)
    candidates = [
        text,
        text.replace(" ", ""),
        text.replace(" ", "").replace("^", ""),
    ]
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate in _UNIT_ALIASES:
            return _UNIT_ALIASES[candidate]
    return None


def extract_embedded_unit(header_text: str) -> str | None:
    """Return a unit embedded in a header, for forms like ``Load [N]`` or ``... kN``."""
    raw = _repair_mojibake(str(header_text or ""))
    for match in reversed(list(_BRACKETED_TEXT_RE.finditer(raw))):
        unit = normalize_unit_text(match.group(1))
        if unit is not None:
            return unit

    folded = _ascii_fold(_split_camel(raw))
    folded = _BRACKETED_TEXT_RE.sub(" ", folded)
    folded = re.sub(r"[_\t\r\n]+", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    tokens = folded.split()
    for width in range(min(3, len(tokens)), 0, -1):
        unit = normalize_unit_text(" ".join(tokens[-width:]))
        if unit is not None:
            return unit
    return None


def looks_like_unit_text(text: str | None) -> bool:
    return normalize_unit_text(text) is not None


def classify_channel_family(header_text: str, unit_text: str | None = None) -> str:
    text = normalize_header_text(header_text)
    tokens = set(text.split())
    unit = normalize_unit_text(unit_text) or extract_embedded_unit(header_text)

    if _is_record_index(text):
        return "record_id"
    if _is_timestamp(text):
        return "timestamp"
    if _has_any(text, ("stress", "tensile stress", "eng stress", "node stress", "spannung", "contrainte")) or "sigma" in tokens:
        return "stress"
    if _is_strain(text, tokens, unit):
        return "strain"
    if _has_any(text, ("load", "force", "maximum force", "kraft")) or (text == "f" and unit in _FORCE_UNITS):
        return "load"
    if _is_extension(text, tokens):
        return "extension"
    if _is_displacement(text, tokens):
        return "displacement"
    if _is_time(text):
        return "time"
    if _is_temperature(text):
        return "temperature"
    return "unknown"


def infer_alias(header_text: str) -> Optional[str]:
    text = normalize_header_text(header_text)
    aliases = {
        "front": "front",
        "rear": "rear",
        "back": "rear",
        "left": "left",
        "right": "right",
        "top": "top",
        "bottom": "bottom",
        "side": "side",
    }
    for key, alias in aliases.items():
        if re.search(rf"\b{re.escape(key)}\b", text):
            return alias

    match = re.search(r"\bgage\s+(\d+)\b", text) or re.search(r"\bgauge\s+(\d+)\b", text)
    if match:
        return f"gage_{match.group(1)}"
    match = re.search(r"\bch\s*(\d+)\b", text)
    if match:
        return f"ch{match.group(1)}"
    return None


def canonical_unit_from_text(unit_text: str | None, family: str) -> str | None:
    unit = normalize_unit_text(unit_text)
    if unit is None:
        return None
    if family == "load" and unit in _FORCE_UNITS:
        return "N"
    if family in {"extension", "displacement"} and unit == "in":
        return "mm"
    if family in {"extension", "displacement"} and unit in _LENGTH_UNITS:
        return unit
    if family == "time" and unit in _TIME_UNITS:
        return "s"
    if family == "strain" and unit in _STRAIN_UNITS:
        return "mm/mm"
    if family == "stress" and unit in _STRESS_UNITS:
        return "MPa"
    if family == "temperature" and unit == "C":
        return "C"
    return unit


def _repair_mojibake(text: str) -> str:
    if not any(marker in text for marker in (chr(0x00C3), chr(0x00C2))):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


def _split_camel(text: str) -> str:
    return _CAMEL_BOUNDARY_RE.sub(" ", text)


def _ascii_fold(text: str) -> str:
    text = _repair_mojibake(text)
    replacements = {
        chr(0x00B0): "deg ",
        chr(0x00B2): "2",
        chr(0x00B3): "3",
        chr(0x00B5): "u",
        chr(0x03BC): "u",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").casefold()


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(phrase)}\b", text) for phrase in phrases)


def _is_record_index(text: str) -> bool:
    compact = text.replace(" ", "")
    if compact in {"index", "record", "rn", "scan", "scanno", "scannumber", "sno", "hiddenindex"}:
        return True
    return text.startswith("scan ")


def _is_strain(text: str, tokens: set[str], unit: str | None) -> bool:
    if _has_any(text, ("strain", "tensile strain", "eng strain", "true strain", "microstrain")):
        return True
    if _has_any(text, ("e true", "dms", "dehnung", "delta e", "e cumsum")):
        return True
    if tokens & {"epsilon", "eps"}:
        return True
    if tokens & {"exx", "eyy", "exy", "e1", "e2", "gamma"}:
        return True
    if unit in _STRAIN_UNITS and any(token.startswith("deform") or token.startswith("dehn") for token in tokens):
        return True
    if unit in _STRAIN_UNITS and (tokens & {"gage", "gauge", "uniaxial"}):
        return True
    return False


def _is_extension(text: str, tokens: set[str]) -> bool:
    if _has_any(text, ("extension", "extensometer", "extensom", "elongation", "crosshead separation")):
        return True
    return any(token.startswith("deform") for token in tokens)


def _is_displacement(text: str, tokens: set[str]) -> bool:
    if _has_any(text, ("displacement", "distance", "stroke", "travel", "weg", "verschiebung")):
        return True
    if "dcdt" in text:
        return True
    return bool(tokens & {"disp", "deplacement"})


def _is_timestamp(text: str) -> bool:
    return _has_any(text, ("timestamp", "date time", "datetime", "system date"))


def _is_time(text: str) -> bool:
    if _has_any(text, ("time", "elapsed", "zeit")):
        return True
    return False


def _is_temperature(text: str) -> bool:
    return _has_any(text, ("temp", "temperature"))
