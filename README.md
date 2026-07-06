# NextCOMP Data Reduction Suite

The NextCOMP Data Reduction Suite is a desktop application for preparing,
running, reviewing, and archiving compression-test data reductions. It is
centred on Mechanical Test Data Package (`.mtdp`) inputs and Method Trace Data
Archive (`.mtda`) outputs.

The release-candidate interface contains:

- Dataset Packaging: import raw compression-test files, group runs, complete
  metadata, attach supplemental files, and export an MTDP package.
- Method Editor: create, import, edit, save, export, and delete editable
  methods while keeping the ISO 14126 reference method read-only.
- Method Analysis: choose an MTDP package, select a method, map package fields
  to method inputs, run the reduction, inspect validation and acceptance
  evidence, and finalise the MTDA output.
- MTDA browser and generated HTML reports: browse the analysed dataset archive,
  formal test report, audit report, plot evidence, canonical CSV/JSON members,
  and decision records.

The scientific intent is traceability: raw files are not modified, every method
run is bound to its input package and method configuration, and the generated
archive records the evidence used for inclusion, exclusion, and reporting
decisions.

## Repository layout

```text
nextcomp_data_reduction_suite/
  src/                         Python packages for MTDP, methods, reports, archives, UI bridge
  prototyping/.../             React/PySide6 desktop shell used by the wired interface
  mappings/                    Canonical ISO 14126 mapping fixtures
  datasets/                    Small raw/MTDP fixtures for smoke tests and examples
  docs/                        User guidance, screenshots, architecture notes, release notes
  tests/                       Regression tests covering archives, reports, methods, and UI bridge
  templates/                   Contract/schema templates used by development and tests
  tools/                       CLI helpers for archive finalisation, export, and validation
```

Generated user methods are intentionally not shipped. The Method Editor writes
new editable methods under `src/methods/generated` at runtime. The canonical ISO
14126 method is shipped under `src/methods/iso14126` and remains the read-only
reference method.

## Requirements

- Windows 10/11 is the primary desktop target.
- Python 3.11 or newer.
- Node.js and npm for building the React desktop shell.
- A virtual environment is recommended.

## Install and run

From a PowerShell prompt:

```powershell
cd C:\path\to\nextcomp_data_reduction_suite
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev,units]
```

Build the React assets used by the PySide6 shell:

```powershell
cd .\prototyping\compression_gui_react_seed_validated\compression_gui_react_seed_validated
npm install
npm run build
cd ..\..\..
```

Launch the wired desktop interface:

```powershell
python -m mtdp_enrichment.react_shell_app
```

The installed console entry point is also available after `pip install -e .`:

```powershell
nextcomp-suite
```

For the legacy Qt launcher, use:

```powershell
python -m mtdp_enrichment.react_shell_app --legacy-gui
```

## Basic workflow

1. Open Dataset Packaging from the launcher.
2. Choose raw test files or an existing MTDP package.
3. Review grouping, channels, metadata, and supplemental files.
4. Export or save the MTDP package.
5. Open Method Analysis.
6. Choose the MTDP package as the analysis input.
7. Select the ISO reference method or an editable generated method.
8. Confirm or repair mapping bindings.
9. Run the method.
10. Inspect validation and acceptance evidence.
11. Keep or remove flagged runs using the scientific evidence shown in the
    cockpit.
12. Finalise the output and open the MTDA browser, test report, or audit report.

See [GUIDELINES.md](GUIDELINES.md) for a screenshot-led walkthrough.

## Output model

The suite produces MTDA archives with a browsable `index.html` entry point and
separate report pages. The important output groups are:

- Formal test report: the user-facing report table, statistics, method
  references, and final selected runs.
- Audit report: traceable evidence packets, method decisions, run-wise
  reduction evidence, acceptance evidence, validation checks, and archive member
  references.
- Canonical data: CSV/JSON members used by the reports and plot viewers.
- Plot viewers: compact HTML surfaces that hydrate scientific plots from
  archive data, rather than static mock images.
- Decision records: inclusion/exclusion defaults, human overrides, amendment
  notes, and report-completion metadata.

Stale `dataset_report.html` and run `*_summary.html` pages are not part of the
production output model.

## Tests

Python tests:

```powershell
pytest tests
```

React shell validation:

```powershell
cd .\prototyping\compression_gui_react_seed_validated\compression_gui_react_seed_validated
npm run validate
```

Some GUI tests require a desktop session and may be skipped or need a display
backend when run headlessly.

## Public release cleanup

This public release folder intentionally excludes:

- `.pytest_cache`, `__pycache__`, and compiled Python files.
- `node_modules`, Vite `dist`, local dev-server logs, and build folders.
- temporary debug scripts and temporary MTDA payloads.
- generated local method drafts and method exports.
- generated `.mtda` files and bulky `_workbench` HTML output folders.
- historical prompt bundles and mockup folders that are not production inputs.

The MTDA archive browser still depends on the compact handoff assets under
`docs/design_handoff_dataset_plot_studio`, so those production input files are
retained.

Small raw/MTDP fixtures remain so regression tests and examples can run.

## Licence and notices

This project is distributed under the Apache License, Version 2.0. See
[LICENSE](LICENSE), [NOTICE.md](NOTICE.md), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The Apache-2.0 project licence does not grant rights over third-party standards
documents, institutional marks, third-party logos, generated user outputs, or
dependencies installed from package managers.
