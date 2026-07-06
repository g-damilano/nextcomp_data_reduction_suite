from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Mapping


class ZipArchiveWriter:
    """Small deterministic ZIP writer for method-run archives."""

    def write(self, output_path: str | Path, files: Mapping[str, bytes]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for member, content in sorted(files.items()):
                archive.writestr(member, content)

