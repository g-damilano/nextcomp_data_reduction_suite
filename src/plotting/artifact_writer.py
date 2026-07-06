from __future__ import annotations

import json
from pathlib import Path

from plotting.models import PlotResult


def write_plot_artifact(result: PlotResult, root: Path, relative_path: str) -> dict[str, str]:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return {"plot_id": result.plot_id, "plot_type": result.plot_type, "artifact": relative_path}
