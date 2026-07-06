from __future__ import annotations

from plotting.models import PlotTheme


def default_theme(theme_id: str = "compression_default") -> PlotTheme:
    return PlotTheme(
        theme_id=theme_id,
        font="Arial",
        default_width="container",
        default_height=300,
        axis_label_conventions={"quantity_unit_separator": " / "},
        opacity_conventions={
            "primary_line": 0.95,
            "secondary_line": 0.5,
            "context_line": 0.18,
            "envelope": 0.16,
            "band": 0.22,
        },
        status_colors={
            "normal": "#1f78b4",
            "supporting": "#78aeda",
            "warning": "#b77a00",
            "fail": "#c83f49",
            "muted": "#7d8794",
            "pass": "#207245",
        },
        tooltip_conventions={"include_units": True, "verbosity": "standard"},
    )


def vega_config(theme: PlotTheme | None = None) -> dict[str, object]:
    theme = theme or default_theme()
    return {
        "axis": {"labelFontSize": 11, "titleFontSize": 12, "labelFont": theme.font, "titleFont": theme.font},
        "legend": {"labelLimit": 160, "titleFontSize": 12, "labelFontSize": 11, "labelFont": theme.font, "titleFont": theme.font},
        "title": {"font": theme.font, "fontSize": 14},
        "view": {"stroke": "#d7dde5"},
    }
