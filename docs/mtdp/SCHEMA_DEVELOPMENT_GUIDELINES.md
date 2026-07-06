# Schema Development Guidelines

MTDP schemas are human-authored YAML files loaded from `src/mtdp_enrichment/schema_library/` and embedded as canonical JSON in each package.

## Required Shape

Current schemas should define:

- `schema_id`, `schema_version`, `label`, `status`
- `test`: `family` and `mode`
- `package`: fixed folder and run-ID conventions
- `unit_system`: the active named unit system
- `unit_systems`: optional schema-local unit-system definitions
- `ui.groups`: the group names used by schema-driven forms
- `dataset_grouping`: deterministic sample-group proposal rules
- `sidecar_import`: same-stem YAML and mapping-profile import policy
- `image_evidence`: accepted image formats and views
- `supplemental_files`: accepted support-file scopes
- `dataset_fields`: fields stored once in `dataset.json`
- `run_fields`: fields stored per run in token preamble or provenance
- `data_table.columns`: expected parser channel families and units
- `unit_conversion_rules`: legacy compatibility metadata only
- `migration`: compatible prior schema versions and migration status

## Field Rules

- Dataset identity fields such as `sample_type` belong in `dataset.json`.
- Run metrology belongs in each normalized run CSV token preamble.
- Acquisition context belongs in run-level provenance.
- Use `instrument_model`, `instrument_id`, and `instrument_location`; keep `machine`, `instrument`, and `location` as import aliases only.
- Use `validity` for accepted/rejected/requires-review state.
- Use `failure_mode` only for optional failure detail or mechanism text.

Field definitions support:

- `field_id`: stable canonical identifier
- `label`: UI label
- `role`: semantic role
- `required`: validation requirement
- `type`: `string`, `float`, `int`, `date`, `enum`, `bool`, `path`, or `file`
- `ui_group`: one of `ui.groups`
- `accepted_units`, `standard_unit`, `unit_dimension`: unit policy
- `allowed_values`: required for enum fields
- `validation`: numeric min/max or string pattern rules
- `default`: schema default used when no value exists
- `suggestion_key`: autocomplete cache key
- `import_aliases`: canonical, legacy, source-specific, weak, and dotted YAML import aliases
- `value_map`: deterministic legacy value conversion
- `date_formats`: accepted and canonical date parsing/display contract
- `storage`: one of `token_preamble`, `dataset_json`, or `provenance`

Storage mappings use:

- `token` for token-preamble storage
- `path` for `dataset_json` or `provenance` dotted paths

## Units

Declare `unit_dimension` for unit-bearing fields and data-table columns. Field-level `standard_unit` overrides the schema unit-system default. Field-level `accepted_units` narrows the accepted set.

Schema-local `unit_conversion_rules` are legacy compatibility data. Runtime conversion is performed through `UnitNormaliser`.

Data-table column definitions support:

- `family`: parser channel family such as `load`, `strain`, or `time`
- `label`: display/output label
- `required`: at least one channel of that family must be present
- `repeatable`: whether multiple channels of that family are allowed
- `accepted_units`, `standard_unit`, `unit_dimension`: table unit policy
- `aliases`: optional family/header aliases

## Linting

Every bundled schema must pass `SchemaLinter` before it is available through `SchemaRegistry`. The linter checks field IDs, storage mappings, UI groups, enum values, date formats, value maps, import aliases, unit compatibility, data-table structure, image/supplemental policies, and known semantic drift such as active `machine` fields.

Invalid bundled schemas fail closed during registry loading.

## Structured Import Aliases

Flat alias lists remain supported for older schemas:

```yaml
import_aliases:
  - run.acquisition.instrument_model
  - test_setup.machine
  - machine
```

New schemas may use a structured taxonomy:

```yaml
import_aliases:
  canonical_paths: [run.acquisition.instrument_model]
  local_paths: [acquisition.instrument_model]
  field_ids: [instrument_model]
  source_specific: [test_setup.machine]
  legacy_keys: [machine, Machine]
  weak_keys: [instrument]
```

The loader normalizes both forms to alias entries with kind and confidence. Weak/deprecated aliases are review-only in reconciliation. The linter rejects collisions and prevents `valid`/`validity` aliases from mapping to `failure_mode` in active schemas.

Default confidence:

```text
canonical_path 1.00
field_id 0.95
local_path 0.90
source_specific 0.85
legacy_key 0.75
unit_encoded_key 0.70
weak_key 0.55
deprecated 0.40
```
