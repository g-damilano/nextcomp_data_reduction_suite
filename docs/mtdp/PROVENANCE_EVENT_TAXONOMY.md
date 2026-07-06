# Provenance Event Taxonomy

Production `.mtdp` packages use stable provenance event names so package history can be audited and queried.

## Minimum Shape

Events should include:

- `event`
- `timestamp`
- `software_version`
- `actor`
- `scope`
- `details`
- optional `run_id`, `inputs`, `outputs`, `warnings`

## Event Names

Current event vocabulary:

- `package_created`
- `package_reprocessed`
- `schema_migrated`
- `run_added`
- `run_removed`
- `run_replaced`
- `raw_file_imported`
- `normalized_file_written`
- `yaml_sidecar_imported`
- `yaml_mapping_profile_applied`
- `yaml_reconciliation_confirmed`
- `unit_normalized`
- `image_evidence_added`
- `image_evidence_removed`
- `supplemental_file_added`
- `supplemental_file_removed`
- `grouping_confirmed`
- `validation_run`
- `user_override_recorded`

Older package event names are accepted for readability, but new package writes should use the taxonomy names above.

## Semantics

`schema_migrated` records source schema, target schema, applied operation types, status, and user-resolved fields.

`yaml_reconciliation_confirmed` records accepted date transforms, value transforms, unit assumptions, and mapping profile context.

`unit_normalized` records field/channel, dimension, source unit, target unit, factor, backend, and confirmation status where known.

`supplemental_file_added` and `image_evidence_added` record evidence paths because these files are optional and must be auditable separately from raw/normalized data.
