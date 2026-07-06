from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from ui.method_run_wizard._icons import chev_down, chev_right


class ContextLine(QtWidgets.QFrame):
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._open = False
        self.setObjectName("ctxLine")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Method run context details")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        self._label = QtWidgets.QLabel("")
        self._label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._label.setWordWrap(False)

        self._chev = QtWidgets.QLabel(chev_right())
        self._chev.setObjectName("ctxChev")

        layout.addWidget(self._label, 1)
        layout.addWidget(self._chev)

    def set_text(self, html: str) -> None:
        self._label.setText(html)

    def mousePressEvent(self, event: object) -> None:
        button = event.button() if hasattr(event, "button") else None
        if button == QtCore.Qt.MouseButton.LeftButton:
            self.toggle()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: object) -> None:
        key = event.key() if hasattr(event, "key") else None
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space):
            self.toggle()
            if hasattr(event, "accept"):
                event.accept()
            return
        super().keyPressEvent(event)

    def toggle(self) -> None:
        self.set_open(not self._open)

    def set_open(self, open_: bool) -> None:
        open_ = bool(open_)
        if self._open == open_:
            return
        self._open = open_
        self._chev.setText(chev_down() if self._open else chev_right())
        self.toggled.emit(self._open)


class ContextDetail(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ctxDetail")
        self.setVisible(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(4)

        self._values: dict[str, QtWidgets.QLabel] = {}
        for key, value in (
            ("Package", "No package selected"),
            ("Method", "ISO 14126"),
            ("Mapping", "No mapping profile selected"),
            ("Output", "No output path selected"),
        ):
            layout.addWidget(self._make_row(key, value))

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.change_package_button = self._subtle_button("Change package...")
        self.change_method_button = self._subtle_button("Change method...")
        self.edit_mapping_button = self._subtle_button("Edit mapping...")
        for button in (self.change_package_button, self.change_method_button, self.edit_mapping_button):
            button_row.addWidget(button)
        layout.addLayout(button_row)

    def set_open(self, open_: bool) -> None:
        self.setVisible(open_)

    def set_row_value(self, key: str, value: str) -> None:
        label = self._values.get(key)
        if label is not None:
            label.setText(value)

    def _make_row(self, key: str, value: str) -> QtWidgets.QFrame:
        row = QtWidgets.QFrame()
        row.setProperty("class", "ctxRow")
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        key_label = QtWidgets.QLabel(key.upper())
        key_label.setProperty("class", "ctxKey")
        key_label.setFixedWidth(84)

        value_label = QtWidgets.QLabel(value)
        value_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._values[key] = value_label

        layout.addWidget(key_label)
        layout.addWidget(value_label, 1)
        return row

    @staticmethod
    def _subtle_button(text: str) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setProperty("class", "subtle")
        button.setAccessibleName(text)
        return button


class DecorBottomBar(QtWidgets.QWidget):
    activity_log_clicked = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(12)

        self.context_line = ContextLine()
        self.activity_log_button = QtWidgets.QPushButton("Activity log · 0")
        self.activity_log_button.setProperty("class", "link")
        self.activity_log_button.setAccessibleName("Activity log, 0 entries")
        self.activity_log_button.clicked.connect(self.activity_log_clicked.emit)

        layout.addWidget(self.context_line, 1)
        layout.addWidget(self.activity_log_button)

    def set_context_text(self, html: str) -> None:
        self.context_line.set_text(html)

    def set_activity_log_count(self, count: int) -> None:
        self.activity_log_button.setText(f"Activity log · {count}")
        self.activity_log_button.setAccessibleName(f"Activity log, {int(count)} entries")


class DecorBottom(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("decorBottom")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.bar = DecorBottomBar()
        self.detail = ContextDetail()
        self.bar.context_line.toggled.connect(self.detail.set_open)

        layout.addWidget(self.bar)
        layout.addWidget(self.detail)

    def set_context_text(self, html: str) -> None:
        self.bar.set_context_text(html)

    def set_activity_log_count(self, count: int) -> None:
        self.bar.set_activity_log_count(count)
