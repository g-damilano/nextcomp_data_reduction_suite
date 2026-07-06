# Manual Smoke Test v1.0

Run this protocol before tagging MTDP Normalisation Foundation v1.0.

## Environment

- Conda environment: `modulus-gui`
- Command: `conda run -n modulus-gui mtdp-enrichment`
- Suggested fixture: `tests/fixtures/mtdp/golden_compression_group/source/`

## Workflow

1. Launch the application.
2. Open a folder containing raw compression files.
3. Click `Propose Groups`.
4. Review proposed group names and run membership.
5. Select a run with same-stem YAML.
6. Open `Review / re-match YAML...`.
7. Confirm date, unit, and validity mappings in the live preview.
8. Add a supplemental file through `Manage supplemental files...`.
9. Add image evidence through `Manage run image evidence...`.
10. Validate the selected group.
11. Export the selected group.
12. Open the exported `.mtdp` with `Open existing group/package...`.
13. Validate the reopened package.
14. Remove one run from the group.
15. Add a missed raw file.
16. Re-export as a revised package.
17. Validate the revised package.
18. Inspect that `provenance.json` records reprocessing events and `checksums.json` covers all internal files except itself.

## Release Status

Manual smoke status for this repository snapshot: not manually executed in this automated pass. This is a release checklist item for the human operator before tagging.
