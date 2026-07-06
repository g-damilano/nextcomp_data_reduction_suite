from __future__ import annotations

import sys

from mtdp_enrichment.ui.launcher_window import LauncherWindow
from mtdp_enrichment.ui.qt_compat import QtWidgets
from mtdp_enrichment.ui.resources import app_icon


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    window = LauncherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
