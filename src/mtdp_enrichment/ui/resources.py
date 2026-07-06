from __future__ import annotations

from pathlib import Path

from mtdp_enrichment.ui.qt_compat import QtGui
from runtime.resources import default_resolver


def package_root() -> Path:
    return default_resolver().resource_path("src", "mtdp_enrichment", required=False)


def icon_path() -> Path | None:
    icons = default_resolver().package_asset_root() / "icons"
    for name in (
        "nextcomp_app_icon.ico",
        "nextcomp_icon_256.png",
        "nextcomp_icon_128.png",
        "nextcomp_icon_64.png",
    ):
        path = icons / name
        if path.exists():
            return path
    return None


def logo_path() -> Path | None:
    path = default_resolver().package_asset_root() / "logos" / "nextcomp-w.png"
    return path if path.exists() else None


def app_icon() -> QtGui.QIcon:
    path = icon_path()
    return QtGui.QIcon(str(path)) if path is not None else QtGui.QIcon()
