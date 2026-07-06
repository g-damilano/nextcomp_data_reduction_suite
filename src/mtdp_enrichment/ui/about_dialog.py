from __future__ import annotations

from mtdp_enrichment import __version__
from mtdp_enrichment.ui.qt_compat import QtCore, QtGui, QtWidgets
from mtdp_enrichment.ui.resources import app_icon, logo_path
from ui.method_run_wizard._tokens import Color


ACKNOWLEDGEMENT = (
    "Funding: UK Engineering and Physical Sciences Research Council (EPSRC) programme Grant EP/T011653/1, "
    "Next Generation Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression, "
    "Imperial College London and the University of Bristol."
)


class AboutDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        tool_name: str = "Data Reduction Pipeline",
        purpose: str = "Data reduction pipeline for compression testing.",
        module_label: str = "Compression testing",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle(f"About {tool_name}")
        self.setWindowIcon(app_icon())
        self.resize(560, 560)
        self.setMinimumSize(460, 420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        hero = QtWidgets.QFrame()
        hero.setObjectName("aboutHero")
        hero_layout = QtWidgets.QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 14, 18, 14)
        hero_layout.setSpacing(16)

        text_stack = QtWidgets.QVBoxLayout()
        text_stack.setSpacing(4)
        project = QtWidgets.QLabel("NEXTCOMP")
        project.setObjectName("aboutProject")
        title = QtWidgets.QLabel(tool_name)
        title.setObjectName("aboutTitle")
        title.setWordWrap(True)
        purpose_label = QtWidgets.QLabel(purpose)
        purpose_label.setObjectName("aboutPurpose")
        purpose_label.setWordWrap(True)
        text_stack.addWidget(project)
        text_stack.addWidget(title)
        text_stack.addWidget(purpose_label)
        hero_layout.addLayout(text_stack, 1)

        logo_label = QtWidgets.QLabel()
        logo_label.setObjectName("nextcompLogo")
        logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        logo = logo_path()
        if logo is not None:
            pixmap = QtGui.QPixmap(str(logo))
            if not pixmap.isNull():
                logo_label.setPixmap(
                    pixmap.scaled(
                        96,
                        96,
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                        QtCore.Qt.TransformationMode.SmoothTransformation,
                    )
                )
        hero_layout.addWidget(logo_label, 0)
        layout.addWidget(hero)

        details = QtWidgets.QFrame()
        details.setObjectName("aboutDetails")
        details_layout = QtWidgets.QFormLayout(details)
        details_layout.setContentsMargins(14, 12, 14, 12)
        details_layout.setSpacing(8)
        details_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        for label, value in (
            ("Version", __version__),
            ("Scope", module_label),
            ("Developer", "Giacomo Damilano"),
            ("Email", "giacomo.damilano@gmail.com"),
            ("Project", "NextCOMP - Next Generation Fibre-Reinforced Composites"),
        ):
            item = QtWidgets.QLabel(value)
            item.setObjectName("aboutValue")
            item.setWordWrap(True)
            item.setTextInteractionFlags(
                item.textInteractionFlags() | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            details_layout.addRow(f"{label}:", item)
        layout.addWidget(details)

        acknowledgement = QtWidgets.QLabel(ACKNOWLEDGEMENT)
        acknowledgement.setObjectName("aboutAcknowledgement")
        acknowledgement.setWordWrap(True)
        acknowledgement.setTextInteractionFlags(
            acknowledgement.textInteractionFlags() | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(acknowledgement)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        close_button = QtWidgets.QPushButton("Close")
        close_button.setObjectName("aboutClose")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.setStyleSheet(_about_qss())


def _about_qss() -> str:
    return f"""
    QDialog#aboutDialog {{
        background: {Color.BG};
        color: {Color.TEXT};
    }}
    QFrame#aboutHero {{
        background: #064f16;
        border: 1px solid #0b5b20;
        border-radius: 8px;
    }}
    QLabel#aboutProject {{
        color: rgba(255, 255, 255, 190);
        font-size: 12px;
        font-weight: 700;
    }}
    QLabel#aboutTitle {{
        color: white;
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#aboutPurpose {{
        color: rgba(255, 255, 255, 220);
        font-size: 12px;
    }}
    QFrame#aboutDetails {{
        background: {Color.SURFACE};
        border: 1px solid {Color.BORDER};
        border-radius: 6px;
    }}
    QLabel#aboutValue {{
        color: {Color.TEXT};
    }}
    QLabel#aboutAcknowledgement {{
        color: {Color.TEXT_2};
        font-size: 12px;
    }}
    QPushButton#aboutClose {{
        background: {Color.ACCENT};
        color: white;
        border: 1px solid {Color.ACCENT};
        border-radius: 4px;
        padding: 7px 18px;
        font-weight: 600;
    }}
    QPushButton#aboutClose:hover {{
        background: {Color.ACCENT_HOVER};
        border-color: {Color.ACCENT_HOVER};
    }}
    """
