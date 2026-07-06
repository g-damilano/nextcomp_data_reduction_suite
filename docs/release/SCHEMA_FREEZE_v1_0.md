# Schema Freeze v1.0

The MTDP Normalisation Foundation v1.0 release freezes the bundled schema set as the current authoring and package contract baseline.

## Stable/Current Schema

| Schema | Version | Runtime status | v1.0 release status |
| --- | --- | --- | --- |
| `mechanical.compression` | `0.2.0` | `active` | stable/current |

`mechanical.compression@0.2.0` is the stable v1.0 schema for compression group packages.

## Additional Bundled Schemas

| Schema | Version | Runtime status | v1.0 release status |
| --- | --- | --- | --- |
| `mechanical.compression` | `0.1.0` | `deprecated` | migration-supported legacy read |
| `mechanical.tensile` | `0.1.0` | `active` | available, not v1.0 stable target |
| `mechanical.flexural` | `0.1.0` | `active` | available, not v1.0 stable target |
| `mechanical.generic_stress_strain` | `0.1.0` | `active` | available, generic support schema |

## Migration Support

Registered migration:

```text
mechanical.compression@0.1.0 -> mechanical.compression@0.2.0
```

This migration maps legacy acceptance-style `Failure mode` values to canonical `Validity`, preserves machine metadata as instrument-model context where possible, and requires user-confirmed `sample_type`.

## Linter Summary

Release schema-lint command:

```powershell
$env:PYTHONPATH='src'
conda run -n modulus-gui python -c "from mtdp_enrichment.schemas import SchemaRegistry; from mtdp_enrichment.schemas.linter import lint_schema; registry=SchemaRegistry(); bad=[schema.label() for schema in registry.all() if not lint_schema(schema).ok]; print('schemas', len(registry.all()), 'bad', bad); raise SystemExit(1 if bad else 0)"
```

Expected output:

```text
schemas 5 bad []
```
