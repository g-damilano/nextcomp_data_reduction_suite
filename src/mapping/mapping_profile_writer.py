from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from mapping.mapping_profile import normalize_mapping_profile


def write_mapping_profile(payload: Mapping[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(normalize_mapping_profile(payload), indent=2, sort_keys=True), encoding="utf-8")
    return output
