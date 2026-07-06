from __future__ import annotations

from ui.method_run_wizard import _icons, _log, _qss, _tokens


def test_token_modules_import_and_qss_contains_spotlight() -> None:
    assert _tokens.Color.BG == "#f3f3f3"
    assert _tokens.Color.CANVAS == _tokens.Color.BG
    assert _tokens.Font.BODY == 9
    assert _tokens.Spacing.MD == 12
    assert _tokens.Radius.LG == 8

    entry = _log.now_entry("hello", "ok")
    assert entry.msg == "hello"
    assert entry.level == "ok"
    assert len(entry.ts) == 8

    assert _icons.chev_right() == "▸"
    assert _icons.chev_down() == "▾"

    qss = _qss.build_global_qss()
    assert len(qss) > 1000
    assert "QFrame#spotlight" in qss
    assert "QWidget#methodRunViewportContents" in qss
    assert "QWidget#methodRunViewportFrame" in qss
