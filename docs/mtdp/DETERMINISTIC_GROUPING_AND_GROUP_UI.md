# Deterministic Grouping and Group UI

## Summary

The enrichment tool proposes sample groups from a folder of raw files. Grouping is deterministic, schema-configured, and isolated in `mtdp_enrichment/grouping`.

The user remains the final authority. Proposed groups can be renamed, merged, split, moved, excluded, restored, validated, and exported.

## Grouping Rules

Schemas declare `dataset_grouping` rules. The compression schema uses:

- imported supplemental YAML sample-type candidates first
- explicit parsed tokens
- filename patterns
- parent folder name as weak fallback
- manual/unassigned status when no rule applies

Filename grouping removes method words such as `Comp` and replicate suffixes such as `E1`, `R1`, and `Run1`.

## Canonical Names

Grouping separates display names from canonical keys:

```text
display_name: CAG-CF-ER-Heat
canonical_key: cag cf er heat
```

Display names stay human-facing. Canonical keys are used for duplicate detection and merge suggestions.

## Group Builder

The UI has a visible group builder between the folder tree and forms.

Supported operations:

- propose groups from a selected folder
- create group
- rename group
- move runs between groups
- exclude and restore runs
- reorder runs
- validate selected group
- export selected group
- export all ready groups

Drag-and-drop is enabled for the group tree, with button/menu alternatives for the same operations.

Internal UI classes still use some `Bundle*` names as legacy implementation names. These names are not user-facing.

## Package Output

Package structure remains the multi-run dataset structure:

```text
dataset.mtdp
|-- manifest.json
|-- schema.json
|-- dataset.json
|-- provenance.json
|-- checksums.json
|-- raw/run_001.<ext>
`-- normalized/run_001.csv
```

Sample type is stored once in `dataset.json`, along with `sample_type_key`. Run metrology remains in each normalized run CSV token preamble.

## Provenance

Grouped export records a dataset-level event:

```json
{
  "event": "grouping_confirmed",
  "grouping_engine": "SampleTypeGrouper",
  "grouping_engine_version": "0.1.0",
  "group_name": "Untreated",
  "run_count": 8,
  "manual_corrections": 2
}
```

This records the confirmed grouping without duplicating every UI interaction.
