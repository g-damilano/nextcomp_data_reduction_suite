from __future__ import annotations

import zipfile
from pathlib import Path

from archives.core.csv_io import parse_tokenized_csv
from archives.core.json_io import read_json_bytes
from archives.core.layouts import detect_mtdp_layout
from archives.mtdp.models import MTDPPackageInput, MTDPRun, RunChannel, RunToken


class MTDPPackageReader:
    """Read the downstream-safe contents of an existing .mtdp archive."""

    def read(self, package_path: str | Path) -> MTDPPackageInput:
        path = Path(package_path)
        with zipfile.ZipFile(path, "r") as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
            layout = detect_mtdp_layout(names)
            manifest = read_json_bytes(archive.read(layout.manifest))
            schema = read_json_bytes(archive.read(layout.schema))
            dataset = read_json_bytes(archive.read(layout.dataset))
            provenance = read_json_bytes(archive.read(layout.provenance))
            checksums = read_json_bytes(archive.read(layout.checksums)) if layout.checksums in names else {}
            normalized_members = sorted(
                name for name in names if name.startswith(layout.normalized_prefix) and name.endswith(".csv")
            )
            raw_by_stem = {
                layout.run_stem(name): name
                for name in names
                if name.startswith(layout.raw_prefix) and not name.endswith("/")
            }
            normalized_by_stem = {layout.run_stem(name): name for name in normalized_members}
            run_order = [str(item) for item in dataset.get("run_order", ()) or ()]
            if not run_order:
                run_order = sorted(normalized_by_stem)
            runs = tuple(
                self._read_run(
                    archive,
                    run_id,
                    normalized_by_stem[run_id],
                    raw_by_stem.get(run_id),
                    provenance,
                )
                for run_id in run_order
                if run_id in normalized_by_stem
            )
        return MTDPPackageInput(
            path=path,
            manifest=manifest,
            schema=schema,
            dataset=dataset,
            provenance=provenance,
            checksums=checksums,
            runs=runs,
        )

    def _read_run(
        self,
        archive: zipfile.ZipFile,
        run_id: str,
        normalized_member: str,
        raw_member: str | None,
        provenance: dict[str, object],
    ) -> MTDPRun:
        parsed = parse_tokenized_csv(archive.read(normalized_member).decode("utf-8-sig"))
        tokens = {
            name: RunToken(name=name, value=value, unit=unit)
            for name, (value, unit) in parsed.tokens.items()
        }
        channels = {
            name: RunChannel(name=name, unit=unit, values=tuple(values))
            for name, (unit, values) in parsed.channels.items()
        }
        run_provenance = provenance.get("runs", {}) if isinstance(provenance.get("runs"), dict) else {}
        payload = run_provenance.get(run_id, {}) if isinstance(run_provenance, dict) else {}
        if not isinstance(payload, dict):
            payload = {}
        return MTDPRun(
            run_id=run_id,
            normalized_package_path=normalized_member,
            raw_package_path=raw_member,
            original_filename=str(payload.get("original_filename")) if payload.get("original_filename") else None,
            tokens=tokens,
            channels=channels,
            provenance=payload,
        )
