from __future__ import annotations

from mtdp_enrichment.ui.about_dialog import AboutDialog
from mtdp_enrichment.ui.main_window import MainWindow
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from mtdp_enrichment.ui.resources import app_icon, logo_path
from ui.method_run_wizard._tokens import Color
from ui.method_run_wizard.controller import MethodRunController
from ui.method_run_wizard.window import MethodRunWindow


def _polish(widget: QtWidgets.QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class DotMatrixPanel(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("launcherBrandPanel")
        self.setMinimumHeight(132)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        painter.fillPath(path, QtGui.QColor("#064f16"))
        painter.setClipPath(path)

        step = 28
        cols = max(8, min(28, rect.width() // step))
        rows = max(4, rect.height() // step + 2)
        for row in range(rows):
            for col in range(cols):
                fade = max(0.0, 1.0 - (col / cols) - (row / (rows * 1.7)))
                if fade <= 0.04:
                    continue
                painter.setBrush(QtGui.QColor(255, 255, 255, int(18 + fade * 88)))
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                radius = max(2, int(9 * fade))
                painter.drawEllipse(QtCore.QPointF(22 + col * step, 16 + row * step), radius, radius)

        super().paintEvent(event)


class ModuleTile(QtWidgets.QFrame):
    activated = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        role: str,
        title: str,
        summary: str,
        detail: str,
        action: str,
        accent: str,
        badge: str,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self.setObjectName("moduleTile")
        self.setProperty("role", role)
        self.setProperty("compact", "false")
        self.setAccessibleName(title)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if enabled else QtCore.Qt.CursorShape.ArrowCursor)
        self.setMinimumHeight(112)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._icon_panel = QtWidgets.QFrame()
        self._icon_panel.setObjectName("moduleIconPanel")
        self._icon_panel.setProperty("role", role)
        self._icon_panel.setStyleSheet(f"QFrame#moduleIconPanel[role='{role}'] {{ background: {accent}; }}")
        self._icon_panel.setFixedWidth(150)
        icon_layout = QtWidgets.QVBoxLayout(self._icon_panel)
        icon_layout.setContentsMargins(12, 12, 12, 12)
        icon_layout.addStretch(1)
        self._icon_label = QtWidgets.QLabel(title.upper())
        self._icon_label.setObjectName("moduleIconText")
        self._icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setWordWrap(True)
        icon_layout.addWidget(self._icon_label)
        icon_layout.addStretch(1)
        layout.addWidget(self._icon_panel)

        content = QtWidgets.QFrame()
        content.setObjectName("moduleContent")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(18, 14, 18, 14)
        content_layout.setSpacing(7)

        title_row = QtWidgets.QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("moduleTitle")
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {accent if enabled else '#7f858b'};")

        badge_label = QtWidgets.QLabel(badge)
        badge_label.setObjectName("moduleBadge")
        badge_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        title_row.addWidget(title_label, 1)
        title_row.addWidget(badge_label, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        summary_label = QtWidgets.QLabel(summary)
        summary_label.setObjectName("moduleSummary")
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(f"color: {Color.TEXT if enabled else '#8d8d8d'};")

        detail_label = QtWidgets.QLabel(detail)
        detail_label.setObjectName("moduleDetail")
        detail_label.setWordWrap(True)
        detail_label.setStyleSheet(f"color: {Color.TEXT_2 if enabled else '#8d8d8d'};")

        self.action_button = QtWidgets.QPushButton(action)
        self.action_button.setObjectName("moduleAction")
        self.action_button.setAccessibleName(action)
        self.action_button.setMinimumWidth(166)
        self.action_button.clicked.connect(self.activated.emit)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setContentsMargins(0, 2, 0, 0)
        action_row.setSpacing(12)
        action_row.addWidget(detail_label, 1)
        action_row.addWidget(self.action_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        content_layout.addLayout(title_row)
        content_layout.addWidget(summary_label)
        content_layout.addLayout(action_row)
        layout.addWidget(content, 1)

        self.setEnabled(enabled)
        self.action_button.setEnabled(enabled)

    def set_compact(self, compact: bool) -> None:
        self.setProperty("compact", "true" if compact else "false")
        self._icon_panel.setFixedWidth(10 if compact else 150)
        self._icon_label.setVisible(not compact)
        self.action_button.setMinimumWidth(142 if compact else 166)
        _polish(self)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if self.isEnabled() and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.activated.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class LauncherWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mtdpLauncherWindow")
        self.setWindowTitle("MTDP Compression Testing")
        self.setWindowIcon(app_icon())
        self.resize(960, 680)
        self.setMinimumSize(680, 520)
        self._child_windows: list[QtWidgets.QWidget] = []
        self._child_controllers: list[MethodRunController] = []

        self._install_menu()
        self._build_ui()
        self.setStyleSheet(_launcher_qss())

    def open_packaging_interface(self) -> None:
        self._show_child(MainWindow())

    def open_method_wizard(self) -> None:
        window = MethodRunWindow()
        controller = MethodRunController(window)
        self._child_controllers.append(controller)
        self._show_child(window)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("launcherCentral")
        self.setCentralWidget(central)

        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("launcherScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        shell = QtWidgets.QWidget()
        shell.setObjectName("launcherShell")
        scroll.setWidget(shell)

        self._shell_layout = QtWidgets.QVBoxLayout(shell)
        self._shell_layout.setContentsMargins(32, 24, 32, 22)
        self._shell_layout.setSpacing(12)

        self._brand_panel = DotMatrixPanel()
        brand_layout = QtWidgets.QHBoxLayout(self._brand_panel)
        brand_layout.setContentsMargins(24, 16, 24, 16)
        brand_layout.setSpacing(22)

        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(5)
        brand_text.addStretch(1)
        eyebrow = QtWidgets.QLabel("NEXTCOMP - COMPRESSION TESTING")
        eyebrow.setObjectName("brandEyebrow")
        title = QtWidgets.QLabel("MTDP compression testing")
        title.setObjectName("launcherTitle")
        title.setWordWrap(True)
        subtitle = QtWidgets.QLabel("Prepare MTDP packages or analyse an existing package.")
        subtitle.setObjectName("launcherSubtitle")
        subtitle.setWordWrap(True)
        brand_text.addWidget(eyebrow)
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand_text.addStretch(1)
        brand_layout.addLayout(brand_text, 1)

        self._logo_label = QtWidgets.QLabel()
        self._logo_label.setObjectName("launcherLogo")
        self._logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        logo = logo_path()
        if logo is not None:
            pixmap = QtGui.QPixmap(str(logo))
            self._logo_label.setPixmap(
                pixmap.scaled(
                    108,
                    98,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self._logo_label.setText("NextCOMP")
        brand_layout.addWidget(self._logo_label, 0)
        self._shell_layout.addWidget(self._brand_panel)

        self.dataset_tile = ModuleTile(
            role="dataset",
            title="Dataset",
            summary="Create MTDP packages from compression test measurements.",
            detail="Specimens, geometry, metadata, and evidence.",
            action="Open Dataset",
            accent="#b40d2e",
            badge="Ready",
        )
        self.method_tile = ModuleTile(
            role="method",
            title="Method",
            summary="Define compression test methods.",
            detail="Planned for a later release.",
            action="Unavailable",
            accent="#8d959d",
            badge="Planned",
            enabled=False,
        )
        self.analysis_tile = ModuleTile(
            role="analysis",
            title="Analysis",
            summary="Analyse an MTDP package with the Method Wizard.",
            detail="Readiness, results, evidence review, output.",
            action="Open Analysis",
            accent="#0b6b38",
            badge="Ready",
        )
        self.dataset_tile.activated.connect(self.open_packaging_interface)
        self.analysis_tile.activated.connect(self.open_method_wizard)

        for tile in (self.dataset_tile, self.method_tile, self.analysis_tile):
            self._shell_layout.addWidget(tile)
        self._shell_layout.addStretch(1)
        self._apply_responsive_width(self.width())

    def _install_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        mtdp_menu = self.menuBar().addMenu("MTDP")
        dataset_action = mtdp_menu.addAction("Open Dataset")
        dataset_action.triggered.connect(self.open_packaging_interface)
        analysis_action = mtdp_menu.addAction("Open Analysis")
        analysis_action.triggered.connect(self.open_method_wizard)
        method_action = mtdp_menu.addAction("Method unavailable")
        method_action.setEnabled(False)

        help_menu = self.menuBar().addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        AboutDialog(
            self,
            tool_name="Data Reduction Pipeline",
            purpose="Data reduction pipeline for compression testing.",
            module_label="Compression testing",
        ).exec()

    def _show_child(self, window: QtWidgets.QWidget) -> None:
        self._child_windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_responsive_width(event.size().width())

    def _apply_responsive_width(self, width: int) -> None:
        compact = width < 980
        narrow = width < 760
        self._shell_layout.setContentsMargins(
            16 if narrow else 24 if compact else 32,
            16 if compact else 24,
            16 if narrow else 24 if compact else 32,
            18 if compact else 22,
        )
        self._brand_panel.setMinimumHeight(112 if compact else 132)
        self._logo_label.setVisible(not narrow)
        for tile in (self.dataset_tile, self.method_tile, self.analysis_tile):
            tile.set_compact(compact)


def _launcher_qss() -> str:
    return f"""
    QMainWindow#mtdpLauncherWindow, QWidget#launcherCentral, QScrollArea#launcherScroll {{
        background: {Color.BG};
        color: {Color.TEXT};
    }}
    QWidget#launcherShell {{
        background: {Color.BG};
    }}
    QMenuBar {{
        background: #f2f2f2;
        color: {Color.TEXT};
        border-bottom: 1px solid #d8d8d8;
        padding: 4px 10px;
    }}
    QMenuBar::item {{
        padding: 5px 11px;
    }}
    QMenuBar::item:selected {{
        background: {Color.ACCENT_SOFT};
    }}
    QMenu {{
        background: {Color.SURFACE};
        color: {Color.TEXT};
        border: 1px solid {Color.BORDER};
    }}
    QMenu::item {{
        padding: 6px 22px;
    }}
    QMenu::item:selected {{
        background: {Color.ACCENT_SOFT};
    }}
    QMenu::item:disabled {{
        color: {Color.TEXT_3};
    }}
    QFrame#launcherBrandPanel {{
        border: 1px solid #0b5b20;
        border-radius: 8px;
    }}
    QLabel#brandEyebrow {{
        color: rgba(255, 255, 255, 190);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0;
    }}
    QLabel#launcherTitle {{
        color: white;
        font-size: 28px;
        font-weight: 700;
    }}
    QLabel#launcherSubtitle {{
        color: rgba(255, 255, 255, 218);
        font-size: 13px;
    }}
    QLabel#launcherLogo {{
        min-width: 116px;
    }}
    QFrame#moduleTile {{
        background: {Color.SURFACE};
        border: 1px solid {Color.BORDER};
        border-radius: 6px;
    }}
    QFrame#moduleTile:hover {{
        border-color: #aab3bb;
        background: #fbfbfb;
    }}
    QFrame#moduleTile:disabled {{
        background: #eeeeee;
        border-color: #dddddd;
    }}
    QFrame#moduleTile[compact="true"] {{
        border-left: 7px solid #b7b7b7;
    }}
    QFrame#moduleTile[role="dataset"][compact="true"] {{
        border-left-color: #b40d2e;
    }}
    QFrame#moduleTile[role="analysis"][compact="true"] {{
        border-left-color: #0b6b38;
    }}
    QLabel#moduleIconText {{
        color: white;
        font-size: 18px;
        font-weight: 700;
    }}
    QFrame#moduleContent {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f3f3f3);
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }}
    QFrame#moduleTile:disabled QFrame#moduleContent {{
        background: #eeeeee;
    }}
    QLabel#moduleTitle {{
        font-size: 21px;
        font-weight: 700;
    }}
    QLabel#moduleBadge {{
        background: {Color.OK_BG};
        color: {Color.OK_INK};
        border: 1px solid {Color.OK_BORDER};
        border-radius: 10px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QFrame#moduleTile:disabled QLabel#moduleBadge {{
        background: #eeeeee;
        color: #777777;
        border-color: #d2d2d2;
    }}
    QLabel#moduleSummary {{
        font-size: 13px;
    }}
    QLabel#moduleDetail {{
        font-size: 12px;
    }}
    QPushButton#moduleAction {{
        background: {Color.ACCENT};
        color: white;
        border: 1px solid {Color.ACCENT};
        border-radius: 4px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton#moduleAction:hover {{
        background: {Color.ACCENT_HOVER};
        border-color: {Color.ACCENT_HOVER};
    }}
    QPushButton#moduleAction:disabled {{
        background: #dedede;
        color: #858585;
        border-color: #c6c6c6;
    }}
    """
