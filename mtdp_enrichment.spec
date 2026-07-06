# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the NextCOMP data-reduction desktop app.

The recipe intentionally mirrors the established NextCOMP compression-module
release shape: a one-file executable with editable defaults embedded in the
bundle and materialized under the OS user app-data folder on first run.

Build from the repository root after the React frontend has been compiled:

    python -m PyInstaller mtdp_enrichment.spec --clean --noconfirm
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None

ROOT = Path.cwd()
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

react_frontend = Path(
    "prototyping",
    "compression_gui_react_seed_validated",
    "compression_gui_react_seed_validated",
)


def tree_datas(root, target, suffixes):
    root = Path(root)
    if not root.exists():
        return []
    rows = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            rows.append((str(path), str(Path(target) / path.relative_to(root).parent)))
    return rows


def tree_datas_all(root, target):
    root = Path(root)
    if not root.exists():
        return []
    rows = []
    for path in root.rglob("*"):
        if path.is_file():
            rows.append((str(path), str(Path(target) / path.relative_to(root).parent)))
    return rows


datas = collect_data_files(
    "mtdp_enrichment",
    includes=[
        "schema_library/**/*.yaml",
        "schema_library/**/*.yml",
        "schema_library/**/*.json",
        "assets/icons/*",
        "assets/logos/*",
    ],
)
datas += tree_datas("src/html_renderer/templates", "html_renderer/templates", {".j2"})
datas += tree_datas("src/plotting/recipes/catalog", "plotting/recipes/catalog", {".yaml", ".yml"})
datas += tree_datas(
    "docs/design_handoff_dataset_plot_studio",
    "docs/design_handoff_dataset_plot_studio",
    {".html", ".js", ".md"},
)
datas += tree_datas("config", "config", {".yaml", ".yml", ".json"})
datas += tree_datas("mappings", "mappings", {".json", ".yaml", ".yml"})
datas += tree_datas("schemas", "schemas", {".json", ".yaml", ".yml"})
datas += tree_datas("src/methods", "src/methods", {".yaml", ".yml", ".json", ".md"})
datas += tree_datas("src/mtdp_enrichment/schema_library", "mtdp_enrichment/schema_library", {".yaml", ".yml", ".json"})
datas += tree_datas("src/mtdp_enrichment/assets", "mtdp_enrichment/assets", {".ico", ".png", ".jpg", ".jpeg", ".svg"})
datas += tree_datas_all(react_frontend / "dist", "react_gui/dist")
datas += tree_datas(react_frontend / "desktop", "react_gui/desktop", {".py"})
datas += [
    ("LICENSE", "legal"),
    ("NOTICE.md", "legal"),
    ("THIRD_PARTY_NOTICES.md", "legal"),
    ("README.md", "legal"),
    ("GUIDELINES.md", "legal"),
]

CONDA_RUNTIME_DLLS = (
    "zstd.dll",
    "libzstd.dll",
    "liblzma.dll",
    "LIBBZ2.dll",
    "libbz2.dll",
    "libmpdec-4.dll",
    "libcrypto-3-x64.dll",
    "libexpat.dll",
    "expat.dll",
    "libssl-3-x64.dll",
    "ffi.dll",
    "ffi-8.dll",
    "sqlite3.dll",
)


def conda_runtime_binaries():
    library_bin = Path(sys.prefix) / "Library" / "bin"
    if not library_bin.exists():
        return []
    binaries = []
    seen = set()
    for name in CONDA_RUNTIME_DLLS:
        path = library_bin / name
        if path.exists() and path not in seen:
            binaries.append((str(path), "."))
            seen.add(path)
    return binaries


def source_submodules(package):
    package_root = SRC_ROOT / Path(*package.split("."))
    if not package_root.exists():
        return collect_submodules(package)
    modules = set()
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(SRC_ROOT).with_suffix("")
        if relative.name == "__init__":
            relative = relative.parent
        if not relative.parts:
            continue
        modules.add(".".join(relative.parts))
    return sorted(modules)


hiddenimports = []
for package in (
    "acceptance",
    "archives",
    "audit",
    "compatibility",
    "diagnostics",
    "export",
    "gui_bridge",
    "html_renderer",
    "inspector",
    "mapping",
    "method_binding",
    "methods",
    "mtda_finalization",
    "mtdp_enrichment",
    "operations",
    "parsing",
    "plotting",
    "readiness",
    "reporting",
    "runtime",
    "ui",
    "validation",
):
    hiddenimports += source_submodules(package)

hiddenimports += [
    "dataclasses",
    "functools",
    "http",
    "http.server",
    "json",
    "platform",
    "threading",
    "time",
    "urllib",
    "urllib.parse",
    "uuid",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
]

qt_binding_excludes = [
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PySide2",
]

a = Analysis(
    ["src/mtdp_enrichment/react_shell_app.py"],
    pathex=["src"],
    binaries=conda_runtime_binaries(),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=qt_binding_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name="NextCOMP_data_reduction_suite",
    icon="src/mtdp_enrichment/assets/icons/nextcomp_app_icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest="build/windows_high_dpi.manifest",
)
