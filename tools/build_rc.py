from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from runtime.rc_manifest import build_rc_release_manifest, write_rc_release_manifest
from runtime.resources import default_resolver


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a release-candidate handoff directory.")
    parser.add_argument("--output", type=Path, default=ROOT / "release_candidate")
    parser.add_argument("--run-pyinstaller", action="store_true", help="Build the PyInstaller executable before writing the RC manifest.")
    parser.add_argument("--smoke-test-status", default="not_run", choices=["not_run", "passed", "failed", "blocked"])
    args = parser.parse_args()

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(exist_ok=True)
    (output / "docs").mkdir(exist_ok=True)

    if args.run_pyinstaller:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "mtdp_enrichment.spec", "--clean", "--noconfirm"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        (output / "logs" / "pyinstaller.log").write_text(
            result.stdout + "\n" + result.stderr,
            encoding="utf-8",
        )
        if result.returncode != 0:
            manifest = build_rc_release_manifest(
                resolver=default_resolver(),
                smoke_test_status="blocked",
                git_state_note={"pyinstaller": "failed"},
            )
            write_rc_release_manifest(output / "rc_release_manifest.json", manifest)
            return result.returncode
        dist = ROOT / "dist" / "mtdp_enrichment"
        if dist.exists():
            target = output / "app"
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(dist, target)

    for source in (
        ROOT / "docs" / "release" / "RC_UAT_SMOKE_SCRIPT.md",
        ROOT / "docs" / "release" / "RC_UAT_FEEDBACK_FORM.md",
    ):
        if source.exists():
            shutil.copy2(source, output / "docs" / source.name)

    manifest = build_rc_release_manifest(
        resolver=default_resolver(),
        smoke_test_status=args.smoke_test_status,
    )
    write_rc_release_manifest(output / "rc_release_manifest.json", manifest)
    print(f"RC handoff written to {output}")
    print(f"Manifest: {output / 'rc_release_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
