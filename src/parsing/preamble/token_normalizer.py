from __future__ import annotations

import re


def normalise_metadata_key(raw_key: str) -> str:
    """Return a stable snake_case metadata key for parser-level tokens."""
    text = raw_key.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def coerce_metadata_value(raw_value: str) -> str:
    """Keep metadata values textual but remove wrapping whitespace/quotes."""
    return raw_value.strip().strip('"').strip()
