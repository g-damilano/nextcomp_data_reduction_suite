from __future__ import annotations

import os
import sys
from pathlib import Path


def set_hidden_if_possible(path: str | Path) -> None:
    """Best-effort native hidden flag for platforms that support one."""

    target = Path(path)
    if sys.platform != "win32":
        return
    try:
        import ctypes

        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(target), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        return


def index_path_for_folder(folder: str | Path) -> Path:
    return Path(folder) / ".mtdp_index.sqlite"

