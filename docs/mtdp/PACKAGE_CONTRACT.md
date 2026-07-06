# MTDP Package Contract

This document describes the `.mtdp` package contract used by the MTDP normalisation layer.

The current MTDP enrichment writer emits the aligned layout by default: package metadata lives under `metadata/` and run data lives under `dataset/`.
During the transition, readers and validators must continue to accept legacy root-level MTDP archives.

## Archive Type

An `.mtdp` file is a ZIP archive containing a dataset-level mechanical test data package.

## Aligned Required Files

Aligned MTDP archives contain:

```text
.mtdp
├── dataset/
│   ├── raw/
│   │   └── run_001_raw.<original_ext>
│   └── normalized/
│       └── run_001_normalized.csv
└── metadata/
    ├── manifest.json
    ├── schema.json
    ├── dataset.json
    ├── provenance.json
    └── checksums.json
```

Required aligned members:

- `metadata/manifest.json`
- `metadata/schema.json`
- `metadata/dataset.json`
- `metadata/provenance.json`
- `metadata/checksums.json`
- `dataset/raw/` with at least one run file
- `dataset/normalized/` with at least one run CSV

## Optional Folders

- `images/`
- `supplemental/`

Optional folders exist only when used.

## Run Naming

Runs use stable generated IDs:

```text
dataset/raw/run_001_raw.<original_ext>
dataset/normalized/run_001_normalized.csv
```

Matching is by shared run stem. Original external filenames are recorded in run provenance.

Legacy archives use:

```text
raw/run_001.<original_ext>
normalized/run_001.csv
```

Readers must normalize both naming styles to the same `run_001` run ID.

## Manifest

`metadata/manifest.json` is minimal:

```json
{
  "package_format": "mtdp",
  "format_version": "0.2.0",
  "schema_id": "mechanical.compression",
  "schema_version": "0.2.0"
}
```

Run paths are discovered from fixed folders and shared stems, not duplicated in the manifest.

## Schema

`metadata/schema.json` embeds canonical JSON derived from file-backed schema YAML. Downstream tools should read schema ID/version from the manifest and the full active contract from `metadata/schema.json`.

## Dataset

`metadata/dataset.json` stores dataset/group-level fields once, including `sample_type`, optional identity fields, and `run_order`.

It must not duplicate run metrology.

## Normalized Data

Each normalized run CSV contains schema-routed token preamble fields and a normalized data table. Unit normalization follows the embedded schema and MTDP unit layer.

## Provenance

`metadata/provenance.json` records dataset events, migration events, and per-run provenance. It includes raw/normalized package paths, original filenames, acquisition context, processing events, optional image evidence, and optional supplemental inputs.

Events should follow `docs/mtdp/PROVENANCE_EVENT_TAXONOMY.md`.

## Checksums

`metadata/checksums.json` uses SHA-256 and covers every internal package member except checksum members such as `metadata/checksums.json`, legacy `checksums.json`, and related transition checksum locations. The checksum payload records `checksum_member` so validators know which archive member is authoritative.

## Image Evidence

Image evidence is optional. If present, files live under `images/` and provenance records package path, original filename, view, role, and whether the image was used for metrology. v1.0 does not execute image metrology.

## Supplemental Files

Supplemental files are optional support/evidence files under `supplemental/`, including sidecar YAML, mapping profiles, notes, calibration documents, or support documents. Referenced supplemental files must exist and be checksummed.

## Legacy Read Support

Legacy MTDP archives remain readable and validatable during migration. MTDP readers, validators, and migration helpers classify an archive as aligned when `metadata/manifest.json` is present, otherwise as legacy when root `manifest.json` is present.

Legacy required members:

- `manifest.json`
- `schema.json`
- `dataset.json`
- `provenance.json`
- `checksums.json`
- `raw/`
- `normalized/`

New package-writing work targets the aligned layout unless a compatibility job explicitly preserves legacy output.

## Migration and Validation

Packages may be opened and migrated when a registered schema migration path exists. Ambiguous migrations require review. `MTDPPackageValidator` checks required files, manifest/schema consistency, raw/normalized run pairing, required fields, optional evidence references, provenance structure, and checksums for both aligned and legacy MTDP layouts.
