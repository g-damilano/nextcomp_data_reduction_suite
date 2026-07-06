# Current MTDP Architecture

The MTDP enrichment tool is a schema-driven Qt application for turning raw mechanical-test files into validated `.mtdp` archives.

## Flow

1. Raw machine files are parsed through `src/parsing/` via `ParserAdapter`.
2. Optional same-stem supplemental YAML is imported through `mtdp_enrichment.enrichment_import`.
3. Deterministic grouping proposes sample groups from parsed tokens, YAML candidates, filenames, and folder context.
4. The user confirms group membership, dataset fields, run fields, YAML reconciliation, image evidence, and supplemental files.
5. Backend services (`GroupLoader`, `GroupReprocessor`, `ValidationService`, `GroupExporter`) own headless workflow orchestration.
6. `MTDPPackageWriter` creates a clean archive with raw, normalized, schema, dataset, provenance, checksums, optional images, and optional supplemental files.
7. `MTDPPackageValidator` validates structure, run pairing, schema requirements, provenance references, and checksums.

## Boundaries

- Raw parsing is delegated to the parsing suite. UI, schema, package, grouping, and YAML import code do not parse raw machine CSVs.
- Schemas are loaded from `src/mtdp_enrichment/schema_library/` and linted before use.
- Unit conversion goes through `mtdp_enrichment.units.UnitNormaliser`; project code does not call Pint directly.
- The UI edits group state and asks package services to write archives. It does not mutate archive internals directly.
- Schema migration is handled by `MTDPMigrator` and `MigrationRegistry`; safe operations may run automatically and ambiguous operations produce review state.
- Provenance events use the documented event taxonomy so import, migration, reprocessing, conversion, and evidence events are queryable.

## Package Shape

```text
sample_group.mtdp
├── manifest.json
├── schema.json
├── dataset.json
├── provenance.json
├── checksums.json
├── raw/
├── normalized/
├── images/          optional
└── supplemental/    optional
```

The raw and normalized folders use shared run stems, for example `raw/run_001.csv` and `normalized/run_001.csv`.

## Terminology

- Group: user-facing sample-type or condition grouping.
- Run: one physical specimen measurement.
- Package/archive: exported `.mtdp` file.

## Active Documentation Spine

The current implementation authority is:

- `docs/mtdp/PARSER_CONTRACT.md`
- `docs/mtdp/PACKAGE_CONTRACT.md`
- `docs/mtdp/PROCESSING_LAYER_HANDOFF_CONTRACT.md`
- `docs/mtdp/SCHEMA_DEVELOPMENT_GUIDELINES.md`
- `docs/mtdp/UNIT_SYSTEM_ARCHITECTURE.md`
- `docs/mtdp/YAML_RECONCILIATION_RULES.md`
- `docs/mtdp/REPROCESSING_WORKFLOW.md`
- `docs/mtdp/PROVENANCE_EVENT_TAXONOMY.md`
- `docs/mtdp/SCHEMA_MIGRATION.md`
- `docs/mtdp/EXTENSION_POINTS.md`
- `docs/release/`

Development transition packs under `docs/development/` are historical design records, not current implementation authority.
