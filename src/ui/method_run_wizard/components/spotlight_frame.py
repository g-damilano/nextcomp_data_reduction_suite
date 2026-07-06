from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets


def make_spotlight_shadow(widget: QtWidgets.QWidget) -> None:
    effect = QtWidgets.QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(28)
    effect.setOffset(0, 8)
    effect.setColor(QtGui.QColor(40, 35, 25, int(255 * 0.06)))
    widget.setGraphicsEffect(effect)


class CurrentPageStack(QtWidgets.QStackedWidget):
    """Stacked widget that sizes to the visible scenario, not hidden pages."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.currentChanged.connect(self._current_page_changed)

    def _current_page_changed(self, _index: int) -> None:
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.updateGeometry()

    def sizeHint(self) -> QtCore.QSize:
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        current = self.currentWidget()
        return current.minimumSizeHint() if current is not None else super().minimumSizeHint()


class SpotlightHead(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("spotlightHead")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 2)
        layout.setSpacing(3)

        self.title = QtWidgets.QLabel("")
        self.title.setObjectName("h1")
        self.subtitle = QtWidgets.QLabel("")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.subtitle.setWordWrap(True)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

    def set_text(self, title: str, subtitle_html: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle_html)


class SpotlightFrame(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("spotlight")
        self.setMinimumHeight(320)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.head = SpotlightHead()
        self.body = CurrentPageStack()
        self.body.setObjectName("spotlightBody")
        self.body.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        self.foot = CurrentPageStack()
        self.foot.setObjectName("spotlightFoot")
        self.foot.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        layout.addWidget(self.head)
        layout.addWidget(self.body)
        layout.addWidget(self.foot)
        make_spotlight_shadow(self)

    def sizeHint(self) -> QtCore.QSize:
        return self._content_size_hint(use_minimum_footer=True)

    def minimumSizeHint(self) -> QtCore.QSize:
        return self._content_size_hint(use_minimum_footer=True)

    def _content_size_hint(self, *, use_minimum_footer: bool) -> QtCore.QSize:
        head_hint = self.head.minimumSizeHint()
        body_hint = self.body.sizeHint()
        foot_hint = self.foot.minimumSizeHint() if use_minimum_footer else self.foot.sizeHint()
        width = max(head_hint.width(), body_hint.width(), foot_hint.width()) + 2
        height = head_hint.height() + body_hint.height() + foot_hint.height() + 2
        return QtCore.QSize(width, max(self.minimumHeight(), height))
