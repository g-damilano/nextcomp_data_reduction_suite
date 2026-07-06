from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from archives.core.checksums import sha256_file
from archives.core.layouts import MTDAAlignedLayout, aggregate_member


class MTDAArtifactCollector:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as archive:
            self.files = {
                name: archive.read(name)
                for name in archive.namelist()
                if not name.endswith("/")
            }

    @property
    def source_checksum(self) -> str:
        return sha256_file(self.path)

    def has(self, member: str) -> bool:
        return member in self.files

    def bytes(self, member: str) -> bytes:
        return self.files[member]

    def first_member(self, *members: str) -> str:
        for member in members:
            if member in self.files:
                return member
        return ""

    def first_bytes(self, *members: str) -> bytes | None:
        member = self.first_member(*members)
        return self.files[member] if member else None

    def first_json(self, *members: str) -> dict[str, Any]:
        for member in members:
            payload = self.json(member)
            if payload:
                return payload
        return {}

    def first_csv_rows(self, *members: str) -> list[dict[str, str]]:
        for member in members:
            rows = self.csv_rows(member)
            if rows:
                return rows
        return []

    def text(self, member: str) -> str:
        return self.bytes(member).decode("utf-8")

    def json(self, member: str) -> dict[str, Any]:
        try:
            payload = json.loads(self.bytes(member))
        except (KeyError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def csv_rows(self, member: str) -> list[dict[str, str]]:
        if member not in self.files:
            return []
        return list(csv.DictReader(io.StringIO(self.text(member))))

    def source_reference(self) -> dict[str, Any]:
        provenance = self.json(MTDAAlignedLayout.provenance)
        source_mtdp = provenance.get("source_mtdp") if isinstance(provenance, dict) else None
        if isinstance(source_mtdp, dict) and source_mtdp:
            return {"source_package": source_mtdp}
        return self.json("source_reference.json")

    def manifest(self) -> dict[str, Any]:
        return self.first_json(MTDAAlignedLayout.manifest, "manifest.json")

    def final_selection(self) -> dict[str, Any]:
        rows = self.first_csv_rows(aggregate_member("run_decision_registry.csv"), "acceptance/final_report_runs.csv")
        selected = [
            str(row.get("run_id"))
            for row in rows
            if _truthy(row.get("final_included", row.get("included")))
        ]
        final_sets = self.json("acceptance/selection_sets_final.json")
        selection_set = _first_row_value(rows, "selection_set") or final_sets.get("default_selection_set") or "final_report_runs"
        selection_source = (
            _first_row_value(rows, "selection_source")
            or final_sets.get("selection_source")
            or "machine_default_confirmed"
        )
        return {
            "selection_set": selection_set,
            "selection_source": selection_source,
            "selected_run_ids": selected,
            "selected_run_count": len(selected),
        }

    def report_completion_status(self) -> dict[str, Any]:
        report = self.first_json("dataset/04_reports/test_report.json", "report/test_report.json")
        completion = report.get("report_completion_status") if isinstance(report, dict) else None
        if isinstance(completion, dict):
            return completion
        completion = self.json("report/report_completion_status.json")
        if completion:
            return completion
        validation = self.first_json(MTDAAlignedLayout.validation, "software/validation.json")
        quality_gate = validation.get("report_quality_gate") if isinstance(validation, dict) else None
        completion = quality_gate.get("report_completion_status") if isinstance(quality_gate, dict) else None
        return completion if isinstance(completion, dict) else {}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y", "included"}


def _first_row_value(rows: list[dict[str, str]], key: str) -> str:
    return next((str(row.get(key) or "") for row in rows if str(row.get(key) or "").strip()), "")
