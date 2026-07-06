from __future__ import annotations

import sys
from pathlib import Path

from mtdp_enrichment import react_shell_app


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "mtdp_enrichment.spec"
DESKTOP = ROOT / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated" / "desktop"
if str(DESKTOP) not in sys.path:
    sys.path.insert(0, str(DESKTOP))


def test_react_shell_app_defaults_to_react_and_keeps_legacy_escape_hatch(monkeypatch) -> None:
    monkeypatch.delenv("MTDP_GUI_ENTRY", raising=False)

    mode, forwarded = react_shell_app._select_entry(["--trace"])
    assert mode == "react"
    assert forwarded == ["--trace"]

    mode, forwarded = react_shell_app._select_entry(["--legacy-gui", "--trace"])
    assert mode == "legacy"
    assert forwarded == ["--trace"]

    monkeypatch.setenv("MTDP_GUI_ENTRY", "qt")
    mode, forwarded = react_shell_app._select_entry(["--react-gui"])
    assert mode == "react"
    assert forwarded == []


def test_react_shell_app_resolves_visual_golden_shell_source_layout() -> None:
    script = react_shell_app._resolve_react_shell_script()

    assert script.name == "run_pyside6_shell.py"
    assert script.parent.name == "desktop"
    assert (script.parent.parent / "package.json").exists()
    assert (script.parent.parent / "src").is_dir()


def test_react_shell_app_prefers_pyinstaller_bundled_react_shell(monkeypatch, tmp_path) -> None:
    bundled_script = tmp_path / "react_gui" / "desktop" / "run_pyside6_shell.py"
    bundled_script.parent.mkdir(parents=True)
    bundled_script.write_text("def main():\n    return 0\n", encoding="utf-8")

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert react_shell_app._resolve_react_shell_script() == bundled_script


def test_pyinstaller_spec_promotes_react_shell_and_bundles_fallback_assets() -> None:
    spec = SPEC.read_text(encoding="utf-8")

    assert '["src/mtdp_enrichment/react_shell_app.py"]' in spec
    assert '"gui_bridge"' in spec
    assert 'tree_datas_all(react_frontend / "dist", "react_gui/dist")' in spec
    assert 'tree_datas(react_frontend / "desktop", "react_gui/desktop", {".py"})' in spec
    assert 'SRC_ROOT = ROOT / "src"' in spec
    assert "sys.path.insert(0, str(SRC_ROOT))" in spec
    assert "qt_binding_excludes" in spec
    assert '"PyQt6"' in spec
    assert "excludes=qt_binding_excludes" in spec
    assert 'name="mtdp_enrichment"' in spec
    assert "exclude_binaries=False" in spec


def test_bridge_generated_methods_root_uses_runtime_resolver(monkeypatch, tmp_path) -> None:
    import bridge_dispatcher
    import runtime.resources

    class FrozenResolver:
        def method_packages_root(self) -> Path:
            return tmp_path / "Roaming" / "NextCOMP" / "mtdp_enrichment" / "src" / "methods"

    monkeypatch.setattr(runtime.resources, "default_resolver", lambda: FrozenResolver())

    assert bridge_dispatcher._generated_methods_root(tmp_path / "_MEIPASS") == (
        tmp_path / "Roaming" / "NextCOMP" / "mtdp_enrichment" / "src" / "methods" / "generated"
    )


def test_shell_startup_initializer_materializes_runtime_resources(monkeypatch, tmp_path) -> None:
    import run_pyside6_shell
    import runtime.resources

    backend = tmp_path / "_MEIPASS"
    shell_dir = backend / "react_gui" / "desktop"
    shell_dir.mkdir(parents=True)
    (backend / "config").mkdir()
    (backend / "config" / "method_registry.yaml").write_text("methods: []\n", encoding="utf-8")
    (backend / "src").mkdir()
    calls: list[str] = []

    class FrozenResolver:
        def materialize_external_resources(self) -> tuple[Path, ...]:
            calls.append("materialized")
            return ()

    monkeypatch.setattr(runtime.resources, "default_resolver", lambda: FrozenResolver())

    run_pyside6_shell.initialize_runtime_resources(shell_dir)

    assert calls == ["materialized"]
    assert str(backend / "src") in sys.path
