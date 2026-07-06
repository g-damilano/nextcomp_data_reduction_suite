# MTDA Output Structure

An MTDA archive is the analysed dataset package produced by Method Analysis.
It is intended to be opened through its archive `index.html` entry point.

Production MTDA surfaces:

- `index.html`: archive browser and artifact catalogue.
- `dataset/03_aggregate/dataset_plot.html`: aggregate plot viewer.
- `dataset/02_processed/*_browser.html`: run-wise browser pages.
- `dataset/04_reports/test_report_shell.html`: formal report shell.
- `dataset/04_reports/audit_report_shell.html`: audit report shell.
- `metadata/ui/support.js`: browser runtime used by generated HTML pages.
- canonical CSV/JSON members under the dataset, reports, audit, and software
  folders.

Removed stale surfaces:

- `dataset_report.html` is not emitted.
- run `*_summary.html` pages are not emitted.
- generated MTDA workbench folders are not part of the source release.

The retained handoff assets under
`docs/design_handoff_dataset_plot_studio` are writer inputs only. Generated
MTDA pages are hydrated from the analysed dataset at runtime and should not use
static mock-up data blobs.
