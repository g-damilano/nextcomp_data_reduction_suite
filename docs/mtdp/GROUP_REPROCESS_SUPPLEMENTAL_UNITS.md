# Groups, Reprocessing, Supplemental Files, and Units

This transition keeps `.mtdp` as the Mechanical Test Data Package archive and uses
**group** as the user-facing term for a sample type / condition collection.

## Group Workflow

- A group contains one or more runs.
- A run is one physical tested specimen or measurement.
- Existing `.mtdp` group packages can be opened, validated, loaded into editable UI state, corrected, and exported as a revised package.
- Reprocessed exports use a revised output path by default to avoid silent overwrite.

## Supplemental Files

General supplemental files are optional package evidence under `supplemental/`.
They may be scoped to the dataset/group, a run, schema/mapping support, calibration/equipment evidence, or other supporting context.

All included supplemental files are:

- copied into `supplemental/`
- recorded in `provenance.json`
- included in `checksums.json`
- validated when referenced from provenance

Sidecar YAML and mapping profiles remain supported as specialized supplemental inputs.

## Unit Layer

Project code should use `mtdp_enrichment.units.UnitNormaliser` for unit conversion.
Pint, when available, is isolated behind the optional `pint_backend` module.

Schemas can declare:

- `unit_system`
- `unit_systems`
- field-level `unit_dimension`
- table-column `unit_dimension`

The compatibility functions `normalize_unit_text()` and `unit_conversion_factor()` delegate to the unit layer.
