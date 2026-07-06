# Schema Migration

Schema migration is handled by `MTDPMigrator` and `MigrationRegistry`.

## Modes

- Automatic migration: deterministic operations can be applied without user input.
- Semi-automatic migration: ambiguous operations produce `MigrationReviewState` and require user values or confirmation.
- Blocked migration: unsupported paths remain readable when possible but are not rewritten.

## Operation Types

Supported operation identifiers include:

- `rename_field`
- `move_field_storage`
- `map_enum_value`
- `split_field`
- `merge_fields`
- `set_default`
- `drop_deprecated_field`
- `rename_token`
- `convert_unit`
- `copy_to_provenance`
- `require_user_value`

The current implemented package rewrite supports token rename, enum value mapping, defaults, and user-required dataset values. Other operation names are reserved in the plan model and must become explicit code before use in active migrations.

## Current Real Path

`mechanical.compression@0.1.0 -> mechanical.compression@0.2.0` is registered in:

```text
src/mtdp_enrichment/schema_library/mechanical/compression/migrations/0.1.0_to_0.2.0.yaml
```

It maps legacy `Failure mode` acceptance values to canonical `Validity`, renames legacy `Machine` token semantics toward `instrument_model`, and requires a user-confirmed dataset `sample_type`.

## Provenance

Migrated packages record `schema_migrated` in `provenance.json` with source schema, target schema, migration status, operation types, and user-resolved fields.
