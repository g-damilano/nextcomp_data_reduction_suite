from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


REACT_FRONTEND_RELATIVE = Path(
    "prototyping",
    "compression_gui_react_seed_validated",
    "compression_gui_react_seed_validated",
)
REACT_SHELL_SCRIPT = Path("desktop", "run_pyside6_shell.py")
LEGACY_ENTRY_VALUES = {"legacy", "qt", "classic", "old"}
REACT_ENTRY_VALUES = {"react", "pyside6", "transition", "default"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    mode, forwarded_args = _select_entry(args)
    if mode == "legacy":
        return _run_legacy_launcher(forwarded_args)
    return _run_script(_resolve_react_shell_script(), forwarded_args)


def _select_entry(argv: list[str]) -> tuple[str, list[str]]:
    mode = os.environ.get("MTDP_GUI_ENTRY", "react").strip().lower() or "react"
    forwarded: list[str] = []

    for arg in argv:
        lowered = arg.lower()
        if lowered in {"--legacy-gui", "--qt-gui"}:
            mode = "legacy"
            continue
        if lowered in {"--react-gui", "--pyside6-gui"}:
            mode = "react"
            continue
        if lowered.startswith("--gui="):
            mode = lowered.split("=", 1)[1].strip()
            continue
        forwarded.append(arg)

    if mode in LEGACY_ENTRY_VALUES:
        return "legacy", forwarded
    if mode in REACT_ENTRY_VALUES:
        return "react", forwarded
    raise SystemExit(f"Unsupported MTDP GUI entry '{mode}'. Use 'react' or 'legacy'.")


def _resolve_react_shell_script() -> Path:
    for script in _candidate_react_shell_scripts():
        if script.exists():
            return script
    searched = ", ".join(str(path) for path in _candidate_react_shell_scripts())
    raise SystemExit(f"React/PySide6 shell entry not found. Searched: {searched}")


def _candidate_react_shell_scripts() -> list[Path]:
    scripts: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        scripts.append(Path(bundle_root) / "react_gui" / REACT_SHELL_SCRIPT)
    scripts.append(_repo_root() / REACT_FRONTEND_RELATIVE / REACT_SHELL_SCRIPT)
    return scripts


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_legacy_launcher(argv: list[str]) -> int:
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0], *argv]
    try:
        from mtdp_enrichment.app import main as legacy_main

        return legacy_main()
    finally:
        sys.argv = original_argv


def _run_script(script: Path, argv: list[str]) -> int:
    script = script.resolve()
    original_argv = sys.argv[:]
    script_dir = str(script.parent)
    added_path = False
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        added_path = True
    sys.argv = [str(script), *argv]
    try:
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            return _exit_code(exc)
        return 0
    finally:
        sys.argv = original_argv
        if added_path:
            try:
                sys.path.remove(script_dir)
            except ValueError:
                pass


def _exit_code(exc: SystemExit) -> int:
    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    raise exc


if __name__ == "__main__":
    raise SystemExit(main())
