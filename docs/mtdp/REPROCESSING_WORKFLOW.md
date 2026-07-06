# Reprocessing Workflow

Existing `.mtdp` group packages can be opened for review and revised export.

## Open

`File -> Open existing group/package...` verifies the archive, reads manifest/schema/dataset/provenance/checksums, extracts package members into a temporary editable workspace, and loads a group state into the UI.

## Edit

Supported edits include:

- add raw files to the selected group
- remove runs from the editable group
- rerun YAML reconciliation
- attach or remove image evidence
- attach or remove general supplemental files
- edit dataset-level fields
- edit run-level fields
- validate the group

Removing a run omits it from the next export and records a `run_removed` provenance event.

## Export

Reprocessed output is written as a clean package through `MTDPPackageWriter`. Existing package internals are not patched in place by the UI. For v0, the default output path uses a `_revised.mtdp` suffix to avoid silent overwrite.

Checksums are regenerated for intentional rewrites.

## Backend Services

Qt widgets are clients of the backend workflow services:

- `GroupLoader` loads raw folders or existing `.mtdp` archives into editable `GroupState`.
- `GroupReprocessor` adds/removes/replaces run state without touching archive internals.
- `YamlReconciliationService` delegates supplemental YAML import and mapping.
- `SupplementalService` manages general support files.
- `ValidationService` validates editable group state headlessly.
- `GroupExporter` writes a clean archive through `MTDPPackageWriter`.

This separation lets reprocessing be tested without launching Qt.
