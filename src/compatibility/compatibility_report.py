from __future__ import annotations

from archives.core.csv_io import write_dict_rows
from archives.core.json_io import json_bytes
from compatibility.compatibility_models import CompatibilityReport


def compatibility_artifacts(report: CompatibilityReport) -> dict[str, bytes]:
    files = {
        "compatibility/schema_method_compatibility_report.json": json_bytes(report.to_dict()),
        "compatibility/schema_method_compatibility_summary.csv": write_dict_rows(report.summary_rows()).encode("utf-8"),
    }
    stub = report.schema_extension_stub()
    if stub.get("status") == "proposal_required":
        files["compatibility/schema_extension_proposal_stub.json"] = json_bytes(stub)
    return files
