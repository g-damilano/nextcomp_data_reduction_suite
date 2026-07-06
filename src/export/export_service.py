from __future__ import annotations

import json
import os
from pathlib import Path

from markupsafe import Markup

from archives.core.checksums import build_checksums
from archives.core.json_io import json_bytes
from export.artifact_collector import MTDAArtifactCollector
from export.export_manifest import build_export_manifest
from export.export_policy import export_warnings, profile_includes_figures, profile_includes_full_html, validate_profile
from export.export_request import ExportRequest
from export.export_result import ExportResult
from export.figure_exporter import FigureExporter
from export.report_exporter import ReportExporter
from export.table_exporter import TableExporter
from html_renderer.context_models import ExportReadmeContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_export_readme


class ExportService:
    def __init__(
        self,
        *,
        report_exporter: ReportExporter | None = None,
        table_exporter: TableExporter | None = None,
        figure_exporter: FigureExporter | None = None,
    ) -> None:
        self.report_exporter = report_exporter or ReportExporter()
        self.table_exporter = table_exporter or TableExporter()
        self.figure_exporter = figure_exporter or FigureExporter()

    def export(self, request: ExportRequest) -> ExportResult:
        profile = validate_profile(request.profile)
        collector = MTDAArtifactCollector(request.input_path)
        files: dict[str, bytes] = {}
        files.update(self.report_exporter.export(collector, profile=profile))
        files.update(self.table_exporter.export(collector, profile=profile))
        if profile_includes_figures(profile):
            files.update(self.figure_exporter.export(collector, profile=profile))
        selection = collector.final_selection()
        report_completion = collector.report_completion_status()
        archive_state = collector.json("finalization/archive_state.json")
        warnings = export_warnings(profile)
        if profile_includes_full_html(profile):
            files["README.html"] = _readme_html(
                profile,
                selection=selection,
                warnings=warnings,
                report_completion=report_completion,
                archive_state=archive_state,
            )
        manifest = build_export_manifest(
            source_mtda=collector.path,
            profile=profile,
            source_reference=collector.source_reference(),
            manifest=collector.manifest(),
            artifacts=_artifact_rows(files),
            selection=selection,
            warnings=warnings,
        )
        files["export_manifest.json"] = json_bytes(manifest)
        files["export_provenance.json"] = json_bytes(
            {
                "schema_id": "mtda.export_provenance.v0_1",
                "source_mtda_checksum": manifest["source_mtda"]["checksum"],
                "profile": profile,
                "events": [
                    {
                        "event": "production_export_created",
                        "profile": profile,
                        "mtdp_mutated": False,
                        "mtda_mutated": False,
                    }
                ],
            }
        )
        files["export_checksums.json"] = json_bytes(build_checksums(files))
        self._write_files(request.output_dir, files)
        return ExportResult(
            status="exported",
            output_dir=request.output_dir,
            manifest_path=request.output_dir / "export_manifest.json",
            profile=profile,
            artifacts=tuple(sorted(files)),
            warnings=tuple(warnings),
        )

    def _write_files(self, output_dir: Path, files: dict[str, bytes]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for relative, content in files.items():
            target = output_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def _artifact_rows(files: dict[str, bytes]) -> list[dict[str, object]]:
    return [
        {
            "path": path,
            "bytes": len(content),
            "kind": _kind(path),
        }
        for path, content in sorted(files.items())
    ]


def _kind(path: str) -> str:
    if path.endswith(".html"):
        return "html"
    if path.endswith(".csv"):
        return "table"
    if path.endswith(".json"):
        return "json"
    return "artifact"


def _readme_html(
    profile: str,
    *,
    selection: dict[str, object] | None = None,
    warnings: list[str] | None = None,
    report_completion: dict[str, object] | None = None,
    archive_state: dict[str, object] | None = None,
) -> bytes:
    profile_label = _escape(profile.replace("_", " ").title().replace("Html", "HTML"))
    selection = selection or {}
    warnings = warnings or []
    report_completion = report_completion or {}
    archive_state = archive_state or {}
    selected_count = _escape(selection.get("selected_run_count", "unknown"))
    selection_source = _operator_label(selection.get("selection_source", "unknown"))
    selection_set = _operator_label(selection.get("selection_set", "final_report_runs"))
    completion_status = _operator_label(report_completion.get("status", "unknown"))
    finalization_state = _operator_label(archive_state.get("archive_state") or archive_state.get("state") or "draft / not finalized")
    warning_count = len(warnings)
    if os.environ.get("MTDA_HTML_RENDERER", "").casefold() != "legacy":
        return render_export_readme(
            ExportReadmeContext(
                projection_plane=ProjectionPlane.EXPORT_BUNDLE,
                recipe_result_kind=RecipeResultKind.EXPORT_README,
                page_title="MTDA Export Bundle",
                profile_label=Markup(profile_label),
                selected_count=Markup(selected_count),
                selection_source=Markup(selection_source),
                completion_status=Markup(completion_status),
                finalization_state=Markup(finalization_state),
                selection_set=Markup(selection_set),
                warning_count=warning_count,
            )
        ).encode("utf-8")
    return _legacy_readme_html(
        profile_label=profile_label,
        selected_count=selected_count,
        selection_source=selection_source,
        completion_status=completion_status,
        finalization_state=finalization_state,
        selection_set=selection_set,
        warning_count=warning_count,
    )


def _legacy_readme_html(
    *,
    profile_label: object,
    selected_count: object,
    selection_source: object,
    completion_status: object,
    finalization_state: object,
    selection_set: object,
    warning_count: int,
) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MTDA Export Bundle</title>
  <style>
    :root {{ --ink: #18252e; --muted: #536472; --line: #d8e0e6; --soft: #f6f8fa; --brand: #22566f; --ok: #217346; --warn: #9a6700; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; color: var(--ink); background: #f6f7f8; }}
    header {{ background: #26343b; color: white; padding: 28px 36px; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 26px; }}
    h1, h2 {{ margin: 0 0 10px; }}
    .meta {{ color: #d6e1e7; margin: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .card p {{ color: var(--muted); min-height: 40px; }}
    .handoff {{ background: white; border: 1px solid var(--line); border-left: 6px solid var(--brand); border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    .handoff p {{ margin: 4px 0 0; color: var(--muted); }}
    .journey {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 8px; margin: 14px 0; }}
    .step {{ background: var(--soft); border: 1px solid var(--line); border-radius: 999px; padding: 8px 10px; font-size: 13px; font-weight: 700; color: var(--brand); text-align: center; }}
    .facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 12px 0 0; }}
    .fact {{ background: var(--soft); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }}
    .fact small {{ display: block; color: var(--muted); font-weight: 700; }}
    .fact strong {{ display: block; margin-top: 3px; font-size: 18px; }}
    .fact.warn strong {{ color: var(--warn); }}
    a.button {{ display: inline-block; border: 1px solid var(--brand); border-radius: 6px; padding: 8px 10px; color: var(--brand); text-decoration: none; font-weight: 700; }}
    .secondary {{ border-color: var(--line); color: var(--ink); }}
    .note {{ margin-top: 18px; color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>MTDA Export Bundle</h1>
    <p class="meta">Profile: {profile_label}. This folder is a shareable view of an existing MTDA; method calculations were not rerun.</p>
  </header>
  <main>
    <section class="handoff" aria-label="Export closure summary">
      <h2>Export handoff</h2>
      <p>This is the distribution copy of the method-run MTDA. Use it to review formal results, verify the process, inspect evidence, and share selected tables without reopening the analysis workflow. Final approval is shown separately as the archive state.</p>
      <div class="journey" aria-label="Operator journey state">
        <span class="step">Loaded</span>
        <span class="step">Mapped</span>
        <span class="step">Checked</span>
        <span class="step">Accepted</span>
        <span class="step">Completed</span>
        <span class="step">Exported</span>
      </div>
      <div class="facts">
        <div class="fact"><small>Final report runs</small><strong>{selected_count}</strong></div>
        <div class="fact"><small>Selection source</small><strong>{selection_source}</strong></div>
        <div class="fact"><small>Report completion</small><strong>{completion_status}</strong></div>
        <div class="fact"><small>Archive state</small><strong>{finalization_state}</strong></div>
        <div class="fact"><small>Selection set</small><strong>{selection_set}</strong></div>
        <div class="fact warn"><small>Export warnings</small><strong>{warning_count}</strong></div>
      </div>
    </section>
    <section class="grid" aria-label="Export handoff links">
      <article class="card">
        <h2>Test Report</h2>
        <p>Formal method results, completion status, final report runs, and aggregate evidence.</p>
        <a class="button" href="reports/test_report.html">Open Test Report</a>
      </article>
      <article class="card">
        <h2>Audit Report</h2>
        <p>Process-verification evidence for source, method, readiness, validation, acceptance, and finalization.</p>
        <a class="button secondary" href="reports/audit_report.html">Open Audit Report</a>
      </article>
      <article class="card">
        <h2>Aggregate Figure</h2>
        <p>Standalone stress-strain evidence figure with individual replicates, mean, range, and variability.</p>
        <a class="button secondary" href="figures/aggregate_stress_strain.html">Open Figure</a>
      </article>
      <article class="card">
        <h2>Tables and Manifest</h2>
        <p>CSV tables, export provenance, checksums, and a manifest of every exported artifact.</p>
        <a class="button secondary" href="tables/individual_results.csv">Individual Results</a>
        <a class="button secondary" href="export_manifest.json">Export Manifest</a>
      </article>
    </section>
    <p class="note">Raw MTDA evidence remains in the source archive. This export is read-only and does not mutate the MTDP or MTDA.</p>
  </main>
</body>
</html>
""".encode("utf-8")


def _operator_label(value: object) -> str:
    text = str(value).replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Unknown"
    replacements = {
        "complete with warnings": "Complete with warnings",
        "final report runs": "Final report runs",
        "human final": "Human final",
        "machine default confirmed": "Machine default confirmed",
        "draft / not finalized": "Draft / not finalized",
    }
    normalized = " ".join(text.casefold().split())
    if normalized in replacements:
        return _escape(replacements[normalized])
    return _escape(" ".join(part[:1].upper() + part[1:].lower() if part else part for part in text.split(" ")))


def _escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
