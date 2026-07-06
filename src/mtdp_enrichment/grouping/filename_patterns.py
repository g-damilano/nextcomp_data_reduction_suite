from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class FilenameGroupingStrategy:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.delimiter_pattern = str(self.config.get("delimiter_pattern", r"[-_ ]+"))
        self.remove_tokens = {str(item).casefold() for item in self.config.get("remove_tokens", ())}
        self.replicate_patterns = [re.compile(str(pattern), re.IGNORECASE) for pattern in self.config.get("replicate_patterns", ())]

    def candidate_from_path(self, source_path: str | Path) -> tuple[str | None, tuple[str, ...]]:
        path = Path(source_path)
        stem = path.stem
        tokens = [token for token in re.split(self.delimiter_pattern, stem) if token]
        evidence = [f"filename stem: {stem}"]
        kept: list[str] = []
        removed: list[str] = []
        for token in tokens:
            if token.casefold() in self.remove_tokens:
                removed.append(token)
                continue
            if any(pattern.fullmatch(token) for pattern in self.replicate_patterns):
                removed.append(token)
                continue
            kept.append(token)
        if removed:
            evidence.append(f"removed method/replicate tokens: {', '.join(removed)}")
        if not kept:
            return None, tuple(evidence)
        return "-".join(kept), tuple(evidence)

