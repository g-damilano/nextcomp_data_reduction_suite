from __future__ import annotations

from collections.abc import Mapping, Sequence

from mtdp_enrichment.ui.qt_compat import QtWidgets
from ui.method_run_wizard._tokens import Color


def add_status_cards(
    layout: QtWidgets.QBoxLayout,
    cards: Sequence[Mapping[str, object]],
    *,
    columns: int = 4,
) -> None:
    grid = QtWidgets.QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)
    for index, card in enumerate(cards):
        widget = _status_card(
            str(card.get("label") or ""),
            str(card.get("value") or ""),
            str(card.get("status") or "neutral"),
        )
        grid.addWidget(widget, index // columns, index % columns)
    layout.addLayout(grid)


def choose_save_file(parent: QtWidgets.QWidget, title: str, start: str, filter_text: str) -> str | None:
    path, _ = QtWidgets.QFileDialog.getSaveFileName(parent, title, start, filter_text)
    return path or None


def fill_named_rows_table(
    table: QtWidgets.QTableWidget,
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[tuple[str, str]],
    *,
    limit: int = 200,
    max_chars: int = 96,
) -> None:
    visible = list(rows[:limit])
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([label for _, label in columns])
    table.setRowCount(len(visible))
    for row_index, row in enumerate(visible):
        for column, (key, _) in enumerate(columns):
            value = str(row.get(key) or "")
            item = QtWidgets.QTableWidgetItem(_elide_middle(value, max_chars=max_chars))
            if len(value) > max_chars:
                item.setToolTip(value)
            table.setItem(row_index, column, item)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)


def section_note(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color:{Color.TEXT_2};")
    return label


def _status_card(label: str, value: str, status: str) -> QtWidgets.QFrame:
    colors = {
        "pass": (Color.OK_BG, Color.OK_INK),
        "available": (Color.OK_BG, Color.OK_INK),
        "warn": (Color.WARN_BG, Color.WARN_INK),
        "fail": (Color.ERR_BG, Color.ERR_INK),
        "neutral": (Color.SURFACE_3, Color.TEXT_2),
    }
    background, accent = colors.get(status, colors["neutral"])
    frame = QtWidgets.QFrame()
    frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    frame.setStyleSheet(
        f"QFrame {{ background:{background}; border:1px solid {Color.BORDER_STRONG}; border-left:4px solid {accent}; border-radius:4px; }}"
        "QLabel { border:0; background:transparent; }"
    )
    box = QtWidgets.QVBoxLayout(frame)
    box.setContentsMargins(10, 8, 10, 8)
    box.addWidget(QtWidgets.QLabel(f"<span style='color:{Color.TEXT_2}'>{label}</span>"))
    box.addWidget(QtWidgets.QLabel(f"<b style='font-size:16px; color:{accent}'>{value or '-'}</b>"))
    return frame


def _elide_middle(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    keep = max(8, (max_chars - 3) // 2)
    return f"{value[:keep]}...{value[-keep:]}"
