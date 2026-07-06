from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
from ui.method_run_wizard._icons import chev_down, chev_right


class TaskHeader(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def __init__(self, badge: str, title: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"{badge.upper()} {title}")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(10)

        self._badge = QtWidgets.QLabel(badge.upper())
        self._badge.setObjectName("badge")
        self._badge.setProperty("kind", "needs" if badge == "needs you" else "optional")

        self._title = QtWidgets.QLabel(title)
        self._title.setObjectName("title")
        self._title.setProperty("class", "title")
        self._title.setWordWrap(True)

        self._chev = QtWidgets.QLabel(chev_right())
        self._chev.setObjectName("chev")

        layout.addWidget(self._badge)
        layout.addWidget(self._title, 1)
        layout.addWidget(self._chev)

    def mousePressEvent(self, event: object) -> None:
        button = event.button() if hasattr(event, "button") else None
        if button == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: object) -> None:
        key = event.key() if hasattr(event, "key") else None
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space):
            self.clicked.emit()
            if hasattr(event, "accept"):
                event.accept()
            return
        super().keyPressEvent(event)

    def set_chevron(self, text: str) -> None:
        self._chev.setText(text)

    def set_text(self, badge: str, title: str) -> None:
        self._badge.setText(badge.upper())
        self._badge.setProperty("kind", "needs" if badge == "needs you" else "optional")
        self._title.setText(title)
        self.setAccessibleName(f"{badge.upper()} {title}")
        self._polish(self._badge)

    @staticmethod
    def _polish(widget: QtWidgets.QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)


class TaskCard(QtWidgets.QFrame):
    expanded_changed = QtCore.pyqtSignal(bool)
    content_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        key: str,
        badge: str,
        title: str,
        why_html: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setProperty("class", "taskCard")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        self._key = key
        self._expanded = False

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = TaskHeader(badge, title)
        self._header.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._header.setMaximumHeight(48)
        self._header.clicked.connect(self._on_header_clicked)
        self.setFocusProxy(self._header)

        self._why = QtWidgets.QLabel(why_html)
        self._why.setWordWrap(True)
        self._why.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._why.setObjectName("taskWhy")
        self._why.setContentsMargins(14, 0, 14, 11)
        self._why.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )

        self._body = QtWidgets.QWidget()
        self._body.setObjectName("taskBody")
        self._body.setVisible(False)
        self._body.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        body_layout = QtWidgets.QVBoxLayout(self._body)
        body_layout.setContentsMargins(14, 0, 14, 14)
        body_layout.setSpacing(0)

        outer.addWidget(self._header)
        outer.addWidget(self._why)
        outer.addWidget(self._body)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_body_widget(self, widget: QtWidgets.QWidget) -> None:
        layout = self._body.layout()
        while layout is not None and layout.count():
            item = layout.takeAt(0)
            old = item.widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        if layout is not None:
            layout.addWidget(widget)
        self._notify_layout_changed()

    def set_chrome(self, badge: str, title: str, why_html: str) -> None:
        self._header.set_text(badge, title)
        self._why.setText(why_html)
        self._notify_layout_changed()

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._why.setVisible(not expanded)
        self._body.setVisible(expanded)
        self._header.set_chevron(chev_down() if expanded else chev_right())
        self.expanded_changed.emit(expanded)
        self._notify_layout_changed()

    def _on_header_clicked(self) -> None:
        self.set_expanded(not self._expanded)

    def _notify_layout_changed(self) -> None:
        self.updateGeometry()
        parent = self.parentWidget()
        while parent is not None:
            parent.updateGeometry()
            parent = parent.parentWidget()
        self.content_changed.emit()
