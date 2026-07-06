# Canonical Supplemental YAML Schema

Version: `0.1.0`

Supplemental YAML files are optional same-stem evidence files for `.mtdp` enrichment. They are not parser input and they are not the final authority; the UI-confirmed enrichment state remains authoritative.

## Canonical Run File

```yaml
mtdp_supplemental_version: 0.1.0
scope: run

schema_hint:
  schema_id: mechanical.compression
  schema_version: 0.2.0

dataset:
  sample_type: CAG-CF-Modied-ULV20
  treatment: modified
  material_label: CAG-CF
  condition: ULV20

run:
  specimen_name: CAG-CF-Modied-ULV20-E1
  replicate_label: E1

  metrology:
    width:
      value: 9.8
      unit: mm
      method: caliper
    thickness:
      value: 2.3
      unit: mm

  acquisition:
    operator: G. Damilano
    instrument: Instron 5969
    load_cell:
      value: 50
      unit: kN
    test_speed:
      value: 1.0
      unit: mm/min
    test_date: 2026-05-06

  review:
    validity: accepted
    failure_mode: null
    requires_review: false

images:
  - path: sample_001_front.jpg
    view: front
    role: audit_evidence
    used_for_metrology: false
```

Required canonical keys are `mtdp_supplemental_version`, `scope`, and `run`. Dataset fields are optional and are used for grouping/prefill when present.

## Import Behavior

- Canonical dotted paths such as `run.metrology.width` map through schema `import_aliases`.
- Alias-compatible flat keys such as `sample_width` also map through `import_aliases`.
- Unit-aware values use `{value, unit}`; extra keys such as `method` or `notes` are allowed.
- YAML values are treated as user-authored prefill values. Unit-bearing fields without YAML units are flagged for confirmation.
- `validity` is the review/acceptance state (`accepted`, `rejected`, `requires_review`, `unknown`). `failure_mode` is reserved for physical/mechanical failure detail and must not be used for boolean acceptance.
- Odd YAML structures produce a structure signature from sorted key paths and can be mapped once with a profile.

## Mapping Profiles

Mapping profiles live in `.mtdp_mapping_profiles/` while working and may be copied into packages under `supplemental/mapping_profiles/` when used.

```yaml
mapping_profile_version: 0.1.0
mapping_profile_id: legacy_compression_yaml_v1
target_schema_id: mechanical.compression
target_schema_version: 0.2.0
source:
  structure_signature: sha256:...
mappings:
  - source_key: dimension_a
    target_field_id: width
    value_path: dimension_a
    unit: mm
    action: map
```

The package preserves used supplemental YAML and mapping profiles as evidence, records import mode in provenance, and includes every supplemental file in checksums.
