from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"
RUNNER = ROOT / "tools" / "run_method_manual.py"


def test_mtda_aligned_checksums_cover_members_and_exclude_self(tmp_path: Path) -> None:
    output = tmp_path / "analysis.mtda"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--input",
            str(INPUT),
            "--method",
            str(METHOD),
            "--mapping",
            str(MAPPING),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    with zipfile.ZipFile(output) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        checksums = json.loads(archive.read(MTDAAlignedLayout.checksums))

        assert checksums["schema_id"] == "archive.checksums"
        assert checksums["schema_version"] == "0.1.0"
        assert checksums["algorithm"] == "sha256"
        assert checksums["checksum_member"] == MTDAAlignedLayout.checksums
        assert MTDAAlignedLayout.checksums not in checksums["files"]
        assert set(checksums["files"]) == names - {MTDAAlignedLayout.checksums}
        assert "checksums.json" not in names
        assert "software/checksums.json" not in names

        for member, expected_digest in checksums["files"].items():
            assert hashlib.sha256(archive.read(member)).hexdigest() == expected_digest
