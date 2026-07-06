from __future__ import annotations

import zipfile
from pathlib import Path


def read_archive_files(path: str | Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def write_archive_files(path: str | Path, files: dict[str, bytes]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            archive.writestr(name, files[name])
    return output
