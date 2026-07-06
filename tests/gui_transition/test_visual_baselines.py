from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "docs" / "gui_transition" / "visual_baselines"
STRUCTURAL_BASELINE = (
    REPO_ROOT
    / "prototyping"
    / "compression_gui_react_seed_validated"
    / "compression_gui_react_seed_validated"
    / "src"
    / "__tests__"
    / "fixtures"
    / "visual-baseline.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", header[16:24])


def test_visual_screenshot_baselines_have_manifest_and_integrity() -> None:
    manifest_path = BASELINE_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    structural = json.loads(STRUCTURAL_BASELINE.read_text(encoding="utf-8"))

    assert manifest["schema"] == "gui-transition-pyside6-screenshot-baselines/v1"
    assert manifest["renderer"] == "PySide6 QWebEngine"
    assert manifest["comparison"]["mode"] == "pixel-delta"
    assert manifest["comparison"]["max_changed_channel_ratio"] > 0
    assert manifest["comparison"]["max_mean_abs_channel_delta"] > 0

    structural_screens = set(structural["screenConfig"])
    records = manifest["screens"]
    assert {item["screen"] for item in records} == structural_screens

    for item in records:
        path = BASELINE_DIR / item["file"]
        assert path.is_file(), item["file"]
        assert path.suffix == ".png"
        assert path.stat().st_size == item["bytes"]
        assert _sha256(path) == item["sha256"]
        assert _png_dimensions(path) == (item["width"], item["height"])
        assert item["mode"] in {"launcher", "child"}
        assert item["screen_config"]["width"] == structural["screenConfig"][item["screen"]]["width"]
        assert item["screen_config"]["height"] == structural["screenConfig"][item["screen"]]["height"]
