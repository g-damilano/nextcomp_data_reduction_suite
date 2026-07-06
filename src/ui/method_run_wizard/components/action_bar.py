from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class ActionBar(QtWidgets.QFrame):
    primary_clicked = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionBar")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 12)
        layout.setSpacing(14)

        self._info = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(self._info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)

        self._label = QtWidgets.QLabel("")
        self._label.setObjectName("actionLabel")
        self._sub = QtWidgets.QLabel("")
        self._sub.setObjectName("actionSub")
        self._sub.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._sub.setWordWrap(True)

        info_layout.addWidget(self._label)
        info_layout.addWidget(self._sub)

        self._primary = QtWidgets.QPushButton("")
        self._primary.setObjectName("actionPrimary")
        self._primary.setProperty("class", "primary")
        self._primary.setVisible(False)
        self._primary.clicked.connect(self.primary_clicked.emit)

        layout.addWidget(self._info, 1)
        layout.addWidget(self._primary)

    @property
    def primary_button(self) -> QtWidgets.QPushButton:
        return self._primary

    def set_state(
        self,
        label: str,
        sub_html: str,
        primary_text: str,
        primary_class: str = "primary",
        primary_enabled: bool = True,
        *,
        enabled: bool | None = None,
    ) -> None:
        if enabled is not None:
            primary_enabled = enabled
        self._label.setText(label)
        self._sub.setText(sub_html)
        display_text = primary_text.replace("&", "&&")
        self._primary.setText(display_text)
        self._primary.setAccessibleName(primary_text)
        self._primary.setProperty("class", primary_class)
        self._primary.setEnabled(primary_enabled)
        self._primary.setVisible(True)
        self._primary.style().unpolish(self._primary)
        self._primary.style().polish(self._primary)
        text_width = self._primary.fontMetrics().horizontalAdvance(primary_text)
        hint = self._primary.sizeHint()
        self._primary.setMinimumSize(max(hint.width(), text_width + 38), max(hint.height(), 34))
