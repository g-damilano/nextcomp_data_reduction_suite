from __future__ import annotations


class Color:
    # Surfaces
    BG = "#f3f3f3"
    CANVAS = "#f3f3f3"
    SURFACE = "#ffffff"
    SURFACE_2 = "#f8f8f8"
    SURFACE_3 = "#ededed"

    # Borders
    BORDER = "#dedede"
    BORDER_STRONG = "#c8c8c8"

    # Text
    TEXT = "#1a1a1a"
    TEXT_2 = "#5f5f5f"
    TEXT_3 = "#949494"

    # Accent
    ACCENT = "#0067c0"
    ACCENT_HOVER = "#005ba6"
    ACCENT_SOFT = "#e5eff8"

    # Status - warning
    WARN_BG = "#fbf6e6"
    WARN_BORDER = "#e2cf8a"
    WARN_INK = "#7a5c12"
    WARN_ACCENT = "#c79613"

    # Status - success
    OK_BG = "#ebf2e1"
    OK_BORDER = "#aac489"
    OK_INK = "#3d5c1c"
    OK_ACCENT = "#5a7a3d"

    # Status - error
    ERR_BG = "#f8e1d9"
    ERR_BORDER = "#d99a8d"
    ERR_INK = "#6e2a1a"
    ERR_ACCENT = "#a8412a"

    # Status - info
    INFO_BG = "#e8f1f9"
    INFO_BORDER = "#a3c4dd"
    INFO_INK = "#1d4974"
    INFO_ACCENT = "#2c6da3"

    # Danger button
    DANGER = "#c42b1c"
    DANGER_HOVER = "#a82515"

    # Activity log
    LOG_BG = "#1e1e1e"
    LOG_FG = "#d6d6d6"
    LOG_TS = "#7a8492"
    LOG_INFO = "#b3c7e6"
    LOG_OK = "#98c887"
    LOG_WARN = "#e5c890"
    LOG_ERR = "#e07c6e"
    LOG_NOW = "#ffffff"
    LOG_BORDER = "#3f3f3f"
    LOG_HOVER = "#2b2b2b"
    WHITE = "#ffffff"


class Font:
    FAMILY = '"Segoe UI Variable", "Segoe UI", "Inter", system-ui, sans-serif'
    FAMILY_MONO = '"JetBrains Mono", "Cascadia Code", Consolas, monospace'

    BODY = 9
    BODY_SMALL = 9
    BODY_LARGE = 10
    H1 = 17
    H2 = 13
    H_TASK = 11
    PCT = 24
    CAPS = 9

    WEIGHT_REGULAR = 400
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 22
    XXL = 28


class Radius:
    SM = 4
    MD = 6
    LG = 8
    PILL = 999


def status_palette(level: str) -> tuple[str, str, str, str]:
    """Return (background, border, ink, accent) colors for a status level."""
    palette = {
        "ok": (Color.OK_BG, Color.OK_BORDER, Color.OK_INK, Color.OK_ACCENT),
        "warn": (Color.WARN_BG, Color.WARN_BORDER, Color.WARN_INK, Color.WARN_ACCENT),
        "err": (Color.ERR_BG, Color.ERR_BORDER, Color.ERR_INK, Color.ERR_ACCENT),
        "info": (Color.INFO_BG, Color.INFO_BORDER, Color.INFO_INK, Color.INFO_ACCENT),
        "now": (Color.INFO_BG, Color.INFO_BORDER, Color.INFO_INK, Color.INFO_ACCENT),
        "todo": (Color.SURFACE, Color.BORDER, Color.TEXT_3, Color.TEXT_3),
    }
    return palette[level]
