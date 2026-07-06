from __future__ import annotations

from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class PipelinePill(QtWidgets.QFrame):
    """Small status pill used in the persistent pipeline strip."""

    clicked = QtCore.pyqtSignal(str)

    def __init__(self, label: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pipePill")
        self.setProperty("class", "pipePill")
        self._step_id = ""
        self._phase = "0"
        self._pulse_timer = QtCore.QTimer(self)
        self._pulse_timer.setInterval(600)
        self._pulse_timer.timeout.connect(self._advance_pulse)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 3, 3)
        layout.setSpacing(5)

        self._dot = QtWidgets.QFrame()
        self._dot.setObjectName("pipeDot")
        self._dot.setProperty("class", "pipeDot")
        self._dot.setFixedSize(8, 8)

        self._label = QtWidgets.QLabel(label)
        self._label.setProperty("class", "pipePill")
        self._label.setMinimumWidth(self._label.fontMetrics().horizontalAdvance(label) + 4)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._connector = QtWidgets.QFrame()
        self._connector.setObjectName("pipeConnector")
        self._connector.setProperty("class", "pipeConnector")
        self._connector.setFixedHeight(2)
        self._connector.setMinimumWidth(14)
        self._connector.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addWidget(self._connector, 1)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.set_level("todo")
        self.setMinimumWidth(self.sizeHint().width())

    @property
    def label(self) -> str:
        return self._label.text()

    def set_step_id(self, step_id: str) -> None:
        self._step_id = step_id
        self.setAccessibleName(f"Method run step: {self.label}")

    def set_terminal(self, terminal: bool) -> None:
        self._connector.setVisible(not terminal)

    def set_level(self, level: str) -> None:
        self.setProperty("state", level)
        self._dot.setProperty("state", level)
        self._label.setProperty("state", level)
        self._connector.setProperty("state", level)
        if level == "now":
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._phase = "0"
            self._dot.setProperty("phase", self._phase)
        self._polish(self)
        self._polish(self._dot)
        self._polish(self._label)
        self._polish(self._connector)

    def mousePressEvent(self, event: object) -> None:
        button = event.button() if hasattr(event, "button") else None
        if button == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self._step_id)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: object) -> None:
        key = event.key() if hasattr(event, "key") else None
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space):
            self.clicked.emit(self._step_id)
            if hasattr(event, "accept"):
                event.accept()
            return
        super().keyPressEvent(event)

    def _advance_pulse(self) -> None:
        self._phase = "1" if self._phase == "0" else "0"
        self._dot.setProperty("phase", self._phase)
        self._polish(self._dot)

    @staticmethod
    def _polish(widget: QtWidgets.QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)


class PipelineStrip(QtWidgets.QWidget):
    step_clicked = QtCore.pyqtSignal(str)

    STEPS = [
        ("package", "Package"),
        ("method", "Method"),
        ("mapping", "Mapping"),
        ("ready", "Ready"),
        ("exec", "Run"),
        ("validate", "Validate"),
        ("accept", "Accept"),
        ("output", "Output"),
    ]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self._pills: dict[str, PipelinePill] = {}
        for index, (step_id, label) in enumerate(self.STEPS):
            pill = PipelinePill(label)
            pill.set_step_id(step_id)
            pill.set_terminal(index == len(self.STEPS) - 1)
            pill.clicked.connect(self.step_clicked.emit)
            self._pills[step_id] = pill
            layout.addWidget(pill)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.setMinimumWidth(min(600, self.sizeHint().width()))

    def set_state(self, states: dict[str, str]) -> None:
        for step_id, level in states.items():
            pill = self._pills.get(step_id)
            if pill is not None:
                pill.set_level(level)

    def labels(self) -> list[str]:
        return [self._pills[step_id].label for step_id, _label in self.STEPS]


class DecorTopBar(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.crumb = QtWidgets.QLabel("METHOD RUN · ISO 14126")
        self.crumb.setObjectName("crumb")
        self.crumb.setMinimumWidth(0)
        self.crumb.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.pipeline = PipelineStrip()

        layout.addWidget(self.crumb)
        layout.addStretch(1)
        layout.addWidget(self.pipeline)
