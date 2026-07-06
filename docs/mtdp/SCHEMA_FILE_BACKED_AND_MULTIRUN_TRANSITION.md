# Schema File-Backed and Multi-Run Transition

## Summary

The MTDP enrichment tool now treats schemas as human-authored files and treats an `.mtdp` package as a dataset containing one or more runs.

YAML is the schema authoring format. A package embeds the selected schema as canonical JSON in `schema.json`.

## Schema Library

Bundled schemas live under:

```text
src/mtdp_enrichment/schema_library/
```

Each schema version is one YAML file:

```text
mechanical/compression/0.2.0.yaml
mechanical/compression/0.1.0.yaml
mechanical/tensile/0.1.0.yaml
mechanical/flexural/0.1.0.yaml
mechanical/generic_stress_strain/0.1.0.yaml
```

The registry discovers `.yaml`, `.yml`, and `.json` schema files, validates required fields, groups versions by `schema_id`, and selects the highest active version by default. Deprecated versions remain selectable.

## Dataset Package Structure

The current dataset-level package shape is:

```text
dataset.mtdp
├── manifest.json
├── schema.json
├── dataset.json
├── provenance.json
├── checksums.json
├── raw/
│   ├── run_001.csv
│   └── run_002.txt
└── normalized/
    ├── run_001.csv
    └── run_002.csv
```

Raw and normalized files are linked by the shared run stem. Raw extensions are preserved. Normalized files use `.csv`.

## Field Levels

`dataset_fields` apply once to the package and are routed to `dataset.json`.

`run_fields` apply to each run. Analytical fields such as specimen name, width, thickness, and failure mode can be routed to the normalized CSV token preamble. Acquisition provenance fields such as operator, instrument, load cell, test speed, and test date can be routed to `provenance.json`.

The schema decides storage through:

```yaml
storage:
  location: token_preamble
  token: Width
```

```yaml
storage:
  location: provenance
  path: runs.{run_id}.acquisition_context.instrument
```

```yaml
storage:
  location: dataset_json
  path: sample_type
```

## Manifest Policy

The manifest remains minimal:

```json
{
  "package_format": "mtdp",
  "format_version": "0.2.0",
  "schema_id": "mechanical.compression",
  "schema_version": "0.2.0"
}
```

It does not repeat run paths, raw files, normalized files, or lifecycle stage.

## Provenance

`provenance.json` is hierarchical:

```text
dataset_events
runs.<run_id>.acquisition_context
runs.<run_id>.processing_events
migration_events
```

Per-run processing events record parsing and unit normalization. Original external filenames are recorded per run.

## Migration Foundation

Schema versions are explicit. The package embeds the schema used at creation. Migration files may live under a schema version's `migrations/` directory. The system must not invent missing scientific information during future migrations; ambiguous upgrades should be recorded or resolved by the user.

