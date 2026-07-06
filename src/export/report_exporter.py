from __future__ import annotations

from archives.core.layouts import report_member
from export.artifact_collector import MTDAArtifactCollector


class ReportExporter:
    def export(self, collector: MTDAArtifactCollector, *, profile: str) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        test_report_html = collector.first_bytes(report_member("test_report.html"), "report/test_report.html")
        test_report_json = collector.first_bytes(report_member("test_report.json"), "report/test_report.json")
        if test_report_html is not None:
            files["reports/test_report.html"] = test_report_html
        if test_report_json is not None:
            files["reports/test_report.json"] = test_report_json
        if profile == "full_html":
            audit_report_html = collector.first_bytes(report_member("audit_report.html"), "audit/audit_report.html")
            workbench_html = collector.first_bytes("workbench/index.html")
            if audit_report_html is not None:
                files["reports/audit_report.html"] = audit_report_html
            if workbench_html is not None:
                files["workbench/index.html"] = workbench_html
        return files
