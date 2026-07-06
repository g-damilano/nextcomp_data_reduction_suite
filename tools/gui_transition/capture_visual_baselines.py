from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCHEMA = "gui-transition-pyside6-screenshot-baselines/v1"
DEFAULT_SCREEN_ORDER = ("home", "packaging", "analysis", "method-editor")
MAX_CHANGED_CHANNEL_RATIO = 0.08
MAX_MEAN_ABS_CHANNEL_DELTA = 8.0
MIN_SIGNIFICANT_CHANNEL_DELTA = 8
SCREEN_MODES = {
    "home": "launcher",
    "packaging": "child",
    "analysis": "child",
    "method-editor": "child",
}
SCREEN_FILES = {
    "home": "home-launcher.png",
    "packaging": "packaging-child.png",
    "analysis": "analysis-child.png",
    "method-editor": "method-editor-child.png",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def react_project_root() -> Path:
    return repo_root() / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated"


def default_baseline_dir() -> Path:
    return repo_root() / "docs" / "gui_transition" / "visual_baselines"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_shell():
    project_root = react_project_root()
    desktop_root = project_root / "desktop"
    sys.path.insert(0, str(desktop_root))
    try:
        from run_pyside6_shell import MainWindow, SCREEN_CONFIG, StaticServer
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
    finally:
        try:
            sys.path.remove(str(desktop_root))
        except ValueError:
            pass
    return QApplication, QGuiApplication, Qt, MainWindow, SCREEN_CONFIG, StaticServer


def _require_dist(project_root: Path) -> Path:
    dist = project_root / "dist"
    index_html = dist / "index.html"
    if not index_html.exists():
        raise SystemExit(
            f"{index_html} is missing. Run "
            "`npm -C prototyping/compression_gui_react_seed_validated/compression_gui_react_seed_validated run build` first."
        )
    return dist


def _process_for(app, milliseconds: int) -> None:
    deadline = time.monotonic() + max(0, milliseconds) / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.025)


def _wait_for_mount(app, window, *, timeout_ms: int) -> None:
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        if getattr(window, "_mount_ready", False):
            return
        if getattr(window, "_mount_failed", False):
            raise RuntimeError(f"{window._screen} mount failed")
        time.sleep(0.05)
    raise TimeoutError(f"{window._screen} did not report React mount within {timeout_ms} ms")


def _prepare_visual_capture(window) -> None:
    window._sync_resize_state_to_page(True, force=True)
    window._sync_window_state_to_page(force=True)
    try:
        window.page.runJavaScript(
            """
            (() => {
              document.documentElement.dataset.visualBaselineCapture = 'true';
              window.__compressionSyncResizeState?.(true);
            })();
            """
        )
    except RuntimeError:
        return


def _normalise_screens(values: Iterable[str] | None) -> list[str]:
    if not values:
        return list(DEFAULT_SCREEN_ORDER)
    screens: list[str] = []
    for value in values:
        screen = str(value).strip()
        if screen not in SCREEN_MODES:
            known = ", ".join(DEFAULT_SCREEN_ORDER)
            raise SystemExit(f"Unknown screen {screen!r}; expected one of: {known}")
        if screen not in screens:
            screens.append(screen)
    return screens


def _window_record(
    *,
    screen: str,
    mode: str,
    image_path: Path,
    width: int,
    height: int,
    screen_config: dict,
    device_pixel_ratio: float,
) -> dict:
    return {
        "screen": screen,
        "mode": mode,
        "file": image_path.name,
        "sha256": _sha256(image_path),
        "bytes": image_path.stat().st_size,
        "width": width,
        "height": height,
        "device_pixel_ratio": device_pixel_ratio,
        "screen_config": {
            "title": screen_config.get("title"),
            "width": screen_config.get("width"),
            "height": screen_config.get("height"),
            "minWidth": screen_config.get("minWidth"),
            "minHeight": screen_config.get("minHeight"),
            "zoom": screen_config.get("zoom"),
        },
    }


def capture_baselines(
    *,
    output_dir: Path,
    screens: list[str],
    timeout_ms: int,
    settle_ms: int,
) -> dict:
    os.environ.setdefault("MTDP_STARTUP_SPLASH", "0")
    os.environ.setdefault("MTDP_PRELOAD_CHILDREN", "0")
    os.environ.setdefault("MTDP_WINDOW_SCREEN_MARGIN", "0")

    project_root = react_project_root()
    dist = _require_dist(project_root)
    QApplication, QGuiApplication, Qt, MainWindow, SCREEN_CONFIG, StaticServer = _load_shell()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication.instance() or QApplication([str(Path(__file__).name)])
    server = StaticServer(dist)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    open_windows = []

    try:
        for screen in screens:
            mode = SCREEN_MODES[screen]
            image_path = output_dir / SCREEN_FILES[screen]
            window = MainWindow(server.url, screen=screen, mode=mode)
            open_windows.append(window)
            window.show()
            window.raise_()
            window.activateWindow()
            _wait_for_mount(app, window, timeout_ms=timeout_ms)
            _prepare_visual_capture(window)
            _process_for(app, settle_ms)
            pixmap = window.grab()
            if pixmap.isNull():
                raise RuntimeError(f"{screen} screenshot capture returned a null pixmap")
            device_pixel_ratio = float(pixmap.devicePixelRatio())
            image = pixmap.toImage()
            if device_pixel_ratio > 0:
                logical_width = max(1, round(pixmap.width() / device_pixel_ratio))
                logical_height = max(1, round(pixmap.height() / device_pixel_ratio))
                if image.width() != logical_width or image.height() != logical_height:
                    image = image.scaled(
                        logical_width,
                        logical_height,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
            if not image.save(str(image_path), "PNG"):
                raise RuntimeError(f"failed to save screenshot {image_path}")
            records.append(
                _window_record(
                    screen=screen,
                    mode=mode,
                    image_path=image_path,
                    width=image.width(),
                    height=image.height(),
                    screen_config=SCREEN_CONFIG[screen],
                    device_pixel_ratio=device_pixel_ratio,
                )
            )
    finally:
        for window in reversed(open_windows):
            try:
                window.close()
            except RuntimeError:
                pass
        _process_for(app, 100)
        server.shutdown()

    manifest = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "renderer": "PySide6 QWebEngine",
        "react_project": str(project_root.relative_to(repo_root())).replace("\\", "/"),
        "dist": str(dist.relative_to(repo_root())).replace("\\", "/"),
        "capture": {
            "timeout_ms": timeout_ms,
            "settle_ms": settle_ms,
            "screen_order": screens,
        },
        "comparison": {
            "mode": "pixel-delta",
            "max_changed_channel_ratio": MAX_CHANGED_CHANNEL_RATIO,
            "max_mean_abs_channel_delta": MAX_MEAN_ABS_CHANNEL_DELTA,
            "min_significant_channel_delta": MIN_SIGNIFICANT_CHANNEL_DELTA,
        },
        "screens": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _pixel_delta(expected_path: Path, current_path: Path, *, significant_delta: int) -> dict:
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:  # pragma: no cover - depends on local validation env
        raise RuntimeError("Pillow is required for live screenshot comparison.") from exc

    expected = Image.open(expected_path).convert("RGBA")
    current = Image.open(current_path).convert("RGBA")
    if expected.size != current.size:
        return {
            "same_size": False,
            "expected_size": expected.size,
            "current_size": current.size,
            "changed_channel_ratio": 1.0,
            "mean_abs_channel_delta": 255.0,
        }
    diff = ImageChops.difference(expected, current)
    histogram = diff.histogram()
    channel_count = len(diff.getbands())
    total_channels = diff.width * diff.height * channel_count
    changed_channels = 0
    abs_delta_sum = 0
    for index, count in enumerate(histogram):
        delta = index % 256
        if delta:
            abs_delta_sum += delta * count
            if delta >= significant_delta:
                changed_channels += count
    return {
        "same_size": True,
        "expected_size": expected.size,
        "current_size": current.size,
        "changed_channel_ratio": changed_channels / max(total_channels, 1),
        "mean_abs_channel_delta": abs_delta_sum / max(total_channels, 1),
    }


def verify_against_manifest(
    *,
    baseline_dir: Path,
    screens: list[str],
    timeout_ms: int,
    settle_ms: int,
) -> list[str]:
    baseline_manifest_path = baseline_dir / "manifest.json"
    if not baseline_manifest_path.exists():
        raise SystemExit(f"{baseline_manifest_path} does not exist; capture baselines first.")
    baseline = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    expected_by_screen = {item.get("screen"): item for item in baseline.get("screens", [])}
    comparison = baseline.get("comparison") or {}
    max_changed_ratio = float(comparison.get("max_changed_channel_ratio", MAX_CHANGED_CHANNEL_RATIO))
    max_mean_delta = float(comparison.get("max_mean_abs_channel_delta", MAX_MEAN_ABS_CHANNEL_DELTA))
    significant_delta = int(comparison.get("min_significant_channel_delta", MIN_SIGNIFICANT_CHANNEL_DELTA))
    mismatches: list[str] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="gui-visual-verify-"))
    try:
        current = capture_baselines(
            output_dir=temp_dir,
            screens=screens,
            timeout_ms=timeout_ms,
            settle_ms=settle_ms,
        )
        for item in current["screens"]:
            expected = expected_by_screen.get(item["screen"])
            if expected is None:
                mismatches.append(f"{item['screen']}: missing from baseline manifest")
                continue
            for field in ("width", "height"):
                if item.get(field) != expected.get(field):
                    mismatches.append(
                        f"{item['screen']}: {field} changed from {expected.get(field)!r} to {item.get(field)!r}"
                    )
            delta = _pixel_delta(
                baseline_dir / expected["file"],
                temp_dir / item["file"],
                significant_delta=significant_delta,
            )
            if not delta["same_size"]:
                mismatches.append(
                    f"{item['screen']}: image size changed from {delta['expected_size']} to {delta['current_size']}"
                )
            if delta["changed_channel_ratio"] > max_changed_ratio:
                mismatches.append(
                    f"{item['screen']}: changed channel ratio {delta['changed_channel_ratio']:.4f} "
                    f"exceeds {max_changed_ratio:.4f}"
                )
            if delta["mean_abs_channel_delta"] > max_mean_delta:
                mismatches.append(
                    f"{item['screen']}: mean channel delta {delta['mean_abs_channel_delta']:.4f} "
                    f"exceeds {max_mean_delta:.4f}"
                )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture or verify PySide6/WebEngine screenshot baselines for the GUI transition."
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=default_baseline_dir(),
        help="Directory containing manifest.json and PNG baselines.",
    )
    parser.add_argument(
        "--screen",
        dest="screens",
        action="append",
        choices=DEFAULT_SCREEN_ORDER,
        help="Screen to capture; repeat to capture a subset. Defaults to all screens.",
    )
    parser.add_argument("--timeout-ms", type=int, default=15000, help="React mount timeout per screen.")
    parser.add_argument("--settle-ms", type=int, default=600, help="Post-mount settle time before capture.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Capture to a temporary directory and compare dimensions/hash against the existing manifest.",
    )
    args = parser.parse_args(argv)

    screens = _normalise_screens(args.screens)
    if args.verify:
        mismatches = verify_against_manifest(
            baseline_dir=args.baseline_dir,
            screens=screens,
            timeout_ms=args.timeout_ms,
            settle_ms=args.settle_ms,
        )
        if mismatches:
            print("Screenshot baseline verification failed:")
            for mismatch in mismatches:
                print(f"- {mismatch}")
            return 1
        print(f"Verified {len(screens)} screenshot baseline(s) against {args.baseline_dir / 'manifest.json'}")
        return 0

    manifest = capture_baselines(
        output_dir=args.baseline_dir,
        screens=screens,
        timeout_ms=args.timeout_ms,
        settle_ms=args.settle_ms,
    )
    print(f"Wrote {len(manifest['screens'])} screenshot baseline(s) to {args.baseline_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
