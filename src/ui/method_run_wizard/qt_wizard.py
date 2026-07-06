from __future__ import annotations

from pathlib import Path
from typing import Any

from mtdp_enrichment.ui.qt_compat import QtWidgets
from ui.method_run_wizard.controller import MethodRunController
from ui.method_run_wizard.method_registry import MethodRegistry
from ui.method_run_wizard.state import MethodRunWizardState
from ui.method_run_wizard.window import MethodRunWindow


class MethodRunWizardDialog(MethodRunWindow):
    """Compatibility shim for callers that still import the old dialog name."""

    def __init__(
        self,
        *,
        package_path: str | Path | None = None,
        service: Any | None = None,
        registry: MethodRegistry | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(package_path=package_path, parent=parent)
        self.service = service
        self.registry = registry
        self.state = MethodRunWizardState(
            input_package_path=Path(package_path) if package_path is not None else None
        )
        self.controller = MethodRunController(self, self.state, service=service, registry=registry)

    def exec(self) -> int:
        self.show()
        self.raise_()
        self.activateWindow()
        return 0


QtMethodRunWizard = MethodRunWindow


def launch_wizard(
    *,
    package_path: str | Path | None = None,
    parent: QtWidgets.QWidget | None = None,
) -> MethodRunWindow:
    window = MethodRunWindow(package_path=package_path, parent=parent)
    window.controller = MethodRunController(
        window,
        MethodRunWizardState(input_package_path=Path(package_path) if package_path is not None else None),
    )
    window.show()
    window.raise_()
    window.activateWindow()
    return window


__all__ = ["MethodRunWizardDialog", "QtMethodRunWizard", "launch_wizard"]
