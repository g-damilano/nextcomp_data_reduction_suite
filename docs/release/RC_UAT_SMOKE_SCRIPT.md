# RC UAT Smoke Script

Use this script for a controlled operator smoke test of a release candidate.

## Setup

- Launch the MTDP Enrichment Tool from the RC build or from source.
- Confirm the app opens without console errors.
- Confirm the method registry lists `ISO 14126 Compression`.

## Smoke Path

1. Select a canonical compression input folder.
2. Build and export an MTDP package.
3. Open the Method Run Wizard.
4. Select the exported MTDP package.
5. Select `ISO 14126 Compression`.
6. Confirm the mapping profile without editing JSON.
7. Run readiness.
8. Confirm the readiness gate is `READY` or `READY_WITH_WARNINGS`.
9. Run the method and write an MTDA archive.
10. Open the Test Report from the wizard output page.
11. Open the Audit Report from the wizard output page.
12. Open the Method Development Workbench from the wizard output page.
13. Export a production bundle with the `full_html` profile.
14. Confirm the export folder contains reports, tables, figures, manifest,
    provenance, and checksums.
15. If finalization is part of the test, apply a report-only override to a copy
    of the MTDA and confirm the source MTDP is unchanged.

## Pass Criteria

- The GUI remains responsive.
- Readiness and execution do not freeze the interface.
- Test Report, Audit Report, Workbench, and export links open.
- `surface_manifest.json` and `report/report_quality_gate.json` are present.
- No MTDP or source data files are modified during method run, finalization, or
  export.
