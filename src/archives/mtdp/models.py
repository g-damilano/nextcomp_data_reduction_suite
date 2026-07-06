from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_CHANNEL_ALIASES: dict[str, tuple[str, ...]] = {
    "load": ("force", "load_n", "force_n"),
    "force": ("load", "load_n", "force_n"),
}

_TOKEN_ALIASES: dict[str, tuple[str, ...]] = {
    "failure_mode": ("primary_failure_mode", "primary failure mode", "failure mode"),
    "primary_failure_mode": ("failure_mode", "failure mode", "primary failure mode"),
}


@dataclass(frozen=True, slots=True)
class RunToken:
    name: str
    value: str
    unit: str | None = None

    @property
    def numeric(self) -> float | None:
        try:
            return float(str(self.value))
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True, slots=True)
class RunChannel:
    name: str
    unit: str | None
    values: tuple[float | None, ...]

    @property
    def point_count(self) -> int:
        return len(self.values)


@dataclass(frozen=True, slots=True)
class MTDPRun:
    run_id: str
    normalized_package_path: str
    raw_package_path: str | None
    original_filename: str | None
    tokens: dict[str, RunToken]
    channels: dict[str, RunChannel]
    provenance: dict[str, Any] = field(default_factory=dict)

    def token(self, name: str) -> RunToken | None:
        return _lookup_named(self.tokens, name, aliases=_TOKEN_ALIASES)

    def channel(self, name: str) -> RunChannel | None:
        return _lookup_named(self.channels, name, aliases=_CHANNEL_ALIASES)


@dataclass(frozen=True, slots=True)
class MTDPPackageInput:
    path: Path
    manifest: dict[str, Any]
    schema: dict[str, Any]
    dataset: dict[str, Any]
    provenance: dict[str, Any]
    checksums: dict[str, Any]
    runs: tuple[MTDPRun, ...]

    @property
    def run_ids(self) -> tuple[str, ...]:
        return tuple(run.run_id for run in self.runs)


def _lookup_named(
    values: dict[str, RunToken] | dict[str, RunChannel],
    name: str,
    *,
    aliases: dict[str, tuple[str, ...]],
) -> RunToken | RunChannel | None:
    if name in values:
        return values[name]

    folded = name.casefold()
    for key, value in values.items():
        if key.casefold() == folded:
            return value

    normalized = _normalise_key(name)
    for key, value in values.items():
        if _normalise_key(key) == normalized:
            return value

    for alias in aliases.get(normalized, ()):
        candidate = _lookup_named(values, alias, aliases={})
        if candidate is not None:
            return candidate
    return None


def _normalise_key(value: object) -> str:
    text = str(value or "").strip().casefold()
    parts: list[str] = []
    previous_was_sep = False
    for char in text:
        if char.isalnum():
            parts.append(char)
            previous_was_sep = False
        elif not previous_was_sep:
            parts.append("_")
            previous_was_sep = True
    return "".join(parts).strip("_")
