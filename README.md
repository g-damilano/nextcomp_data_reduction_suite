# NextCOMP Data Reduction Suite

The NextCOMP Data Reduction Suite is a desktop application for reducing and
reviewing compression-test data. It helps scientists move from raw measurement
files to a traceable analysed archive that contains results, evidence plots,
reports, provenance, and acceptance decisions.

The suite works around two package types:

- MTDP: the input Mechanical Test Data Package containing the source dataset.
- MTDA: the output Method Trace Data Archive containing analysed results.

The central principle is traceability. Raw files are not modified. Each method
run is tied to the selected package, method version, mapping, validation state,
acceptance decisions, and generated report archive.

## Download And Run

Most users should use the packaged Windows distribution rather than installing
Python or Node.js.

1. Download the latest Windows release asset from this repository.
2. Unzip the distribution.
3. Run:

```text
NextCOMP_data_reduction_suite/NextCOMP_data_reduction_suite.exe
```

The distribution folder includes the executable together with `LICENSE`,
`NOTICE.md`, `THIRD_PARTY_NOTICES.md`, `README.md`, and `GUIDELINES.md`.

On first run, the application creates editable working defaults in the user
app-data folder:

```text
%APPDATA%\NextCOMP\mtdp_enrichment
```

## What The Application Does

Dataset Packaging creates or inspects MTDP input packages. Use it to import raw
compression-test files, group runs, complete metadata, assign channels, attach
evidence, validate package completeness, and export the package for analysis.

Method manages method versions. Use it to create editable method versions,
rename them, adjust controlled analysis rules, save changes, import or export
method packages, and keep the ISO 14126 reference method protected as a
read-only baseline.

Analysis runs one MTDP package through one selected method. Use it to check
mapping, run the method, inspect validation, review flagged specimens, decide
which runs are included in the final report, complete report-only fields, and
create the MTDA archive.

The MTDA browser opens the analysed archive. Use it to review the archive
index, formal test report, audit report, plot viewers, canonical CSV/JSON
members, provenance, and decision records.

## Basic Workflow

1. Open Dataset Packaging.
2. Choose raw test files, a source folder, or an existing MTDP package.
3. Review grouping, channels, metadata, and supplemental evidence.
4. Export the MTDP package.
5. Open Analysis.
6. Choose the MTDP package as the input.
7. Select the ISO reference method or an editable generated method.
8. Confirm or repair mapping bindings.
9. Run the method.
10. Inspect validation and acceptance evidence.
11. Keep or remove flagged runs using the scientific evidence shown.
12. Finalise the output and open the MTDA browser, test report, or audit report.

See [GUIDELINES.md](GUIDELINES.md) for the usage guide and screenshots.

## Scientific Review Points

Before sharing results, check that:

- the selected input is the intended MTDP package;
- run count, run names, channels, and required metadata are correct;
- the selected method version is the one intended for reporting;
- mapping warnings have been reviewed;
- validation warnings are understood;
- flagged runs have been reviewed using dataset-derived plots and metrics;
- Accept and Output list the same included and excluded runs;
- reviewer and finalisation fields are complete;
- the MTDA browser opens the archive `index.html`;
- the formal test report and audit report open from the same archive.

Results and generated outputs remain the user's responsibility and should be
reviewed before they are used for engineering, certification, or commercial
decisions.

## Output Contents

An MTDA archive is expected to contain:

- an archive `index.html` entry point;
- a formal test report with selected runs, results, statistics, and method
  context;
- an audit report with run-wise evidence, aggregate evidence, validation,
  acceptance, and decision records;
- plot viewers hydrated from archive data members;
- canonical CSV and JSON evidence members;
- provenance, checksums, report-completion metadata, and finalisation notes.

Stale dataset summary pages and run summary pages are not production outputs.

## Optional Source Run

The packaged distribution is recommended for normal use. If you need to run the
application from source, use a Python environment with the project dependencies
installed, build the React shell, and launch:

```powershell
python -m mtdp_enrichment.react_shell_app
```

This source path is mainly useful for local validation or controlled research
deployment. It is not required for ordinary use of the downloadable
distribution.

## Licence And Notices

The project-authored source code, documentation, configuration, templates, and
packaging scripts in this repository are distributed under the Apache License,
Version 2.0. See [LICENSE](LICENSE), [NOTICE.md](NOTICE.md), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The in-app "Licensing & notices" panel mirrors the repository notice summary.
Binary release folders also include the licence and notice files beside the
executable.

The Apache-2.0 project licence does not grant rights over third-party standards
documents, institutional marks, third-party logos, generated user outputs, or
dependencies installed from package managers.

## Funding

This work was developed with support from the UK Engineering and Physical
Sciences Research Council (EPSRC) programme Grant EP/T011653/1, Next Generation
Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression,
Imperial College London and the University of Bristol.
