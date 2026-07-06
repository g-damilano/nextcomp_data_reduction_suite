from __future__ import annotations

from mtdp_enrichment.ui.image_evidence_panel import ImageEvidencePanel
from mtdp_enrichment.ui.qt_compat import QtWidgets
from mtdp_enrichment.ui.resources import app_icon


FUTURE_TOOLTIP = "Function currently not implemented. Reserved for future development."


class ImageEvidenceDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run image evidence")
        self.setWindowIcon(app_icon())
        self.resize(760, 420)

        self.panel = ImageEvidencePanel(self)
        self.extract_button = QtWidgets.QPushButton("Extract metrology from selected image")
        self.run_metrology_button = QtWidgets.QPushButton("Run image metrology for this run")
        for button in (self.extract_button, self.run_metrology_button):
            button.setEnabled(False)
            button.setToolTip(FUTURE_TOOLTIP)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        future_row = QtWidgets.QHBoxLayout()
        future_row.addWidget(self.extract_button)
        future_row.addWidget(self.run_metrology_button)
        future_row.addStretch()
        future_row.addWidget(self.close_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.panel, 1)
        layout.addLayout(future_row)

    def set_run_id(self, run_id: str | None) -> None:
        suffix = f" - {run_id}" if run_id else ""
        self.setWindowTitle(f"Run image evidence{suffix}")
