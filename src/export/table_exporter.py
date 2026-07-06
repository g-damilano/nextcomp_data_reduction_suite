from __future__ import annotations

from archives.core.layouts import aggregate_member, report_member
from export.artifact_collector import MTDAArtifactCollector


KEY_TABLES = (
    ((aggregate_member("run_decision_registry.csv"), "acceptance/final_report_runs.csv"), "tables/final_report_runs.csv"),
    ((aggregate_member("results_table.csv"), "report/individual_results.csv"), "tables/individual_results.csv"),
    ((aggregate_member("statistics.csv"), "report/aggregate_statistics.csv"), "tables/aggregate_statistics.csv"),
    ((aggregate_member("characteristic_points.csv"), "report/characteristic_points.csv"), "tables/characteristic_points.csv"),
    ((aggregate_member("stress_strain_aligned.csv"), "report/aligned_curves.csv"), "tables/aligned_curves.csv"),
    ((aggregate_member("missing_metadata_table.csv"), "report/missing_report_fields.csv"), "tables/missing_report_fields.csv"),
    ((aggregate_member("report_completion_table.csv"), "report/report_completeness_summary.csv"), "tables/report_completeness_summary.csv"),
    ((aggregate_member("bending_summary_table.csv"), "report/bending_distribution_summary.csv"), "tables/bending_summary_table.csv"),
    ((aggregate_member("dataset_plot_manifest.csv"),), "tables/dataset_plot_manifest.csv"),
    ((report_member("audit_report.csv"),), "tables/audit_report.csv"),
)


class TableExporter:
    def export(self, collector: MTDAArtifactCollector, *, profile: str) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for candidates, output_path in KEY_TABLES:
            content = collector.first_bytes(*candidates)
            if content is not None:
                files[output_path] = content
        return files
