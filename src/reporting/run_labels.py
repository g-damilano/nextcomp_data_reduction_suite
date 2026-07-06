from __future__ import annotations

import re
from typing import Any


RUN_ID_PATTERN = re.compile(r"\brun[ _-]0*(\d+)\b", re.IGNORECASE)


def run_display_label(value: Any) -> str:
    """Return the compact report-facing label for an internal run id."""

    text = str(value or "").strip()
    match = RUN_ID_PATTERN.fullmatch(text)
    if not match:
        return text
    return f"#{int(match.group(1))}"


def replace_run_ids_for_display(value: Any) -> str:
    """Replace report-visible run identifiers with compact labels in prose."""

    text = str(value or "")
    return RUN_ID_PATTERN.sub(lambda match: f"#{int(match.group(1))}", text)


def run_list_display(values: Any, *, separator: str = "; ") -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        values = [item.strip() for item in re.split(r"[,;]", values) if item.strip()]
    try:
        items = list(values)
    except TypeError:
        items = [values]
    return separator.join(run_display_label(item) for item in items if str(item or "").strip())
