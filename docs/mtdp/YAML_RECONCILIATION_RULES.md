# YAML Reconciliation Rules

Version: `0.1`

The reconciliation popup is used when supplemental YAML is readable but needs review before values are accepted into `.mtdp` enrichment state. The schema remains the authority.

## Dates

Canonical output is ISO:

```text
yyyy-MM-dd
```

Accepted v0 inputs:

```text
yyyy-MM-dd
dd/MM/yyyy
d/M/yyyy
dd-MM-yyyy
d-M-yyyy
dd.MM.yyyy
d.M.yyyy
```

Slash dates default to UK-style `dd/MM/yyyy`; ambiguous dates such as `07/06/2014` require confirmation.

## Units

Units may be explicit or inferred from key suffixes:

```text
specimen.width_mm -> width, mm
test_setup.load_cell_kN -> load_cell, kN
test_setup.test_speed_mm_min -> test_speed, mm/min
```

Unit-bearing fields always expose a unit selector in the reconciliation dialog. Missing or unsupported units block acceptance until corrected or confirmed.

## Validity

Boolean/numeric validity values map through a visible transform:

```text
1 / true / valid -> validity = accepted
0 / false / invalid -> validity = rejected
```

Users can override these rows to `requires_review`, `unknown`, or ignore them. `failure_mode` is reserved for actual physical/mechanical failure detail and is not the canonical acceptance flag.

## Instrument Metadata

Preferred canonical fields are:

```text
instrument_model
instrument_id
instrument_location
```

Legacy aliases:

```text
test_setup.machine -> instrument_model
serial_number -> instrument_id
location -> instrument_location
```

## Preview

The dialog shows every YAML key and a live debounced acceptance preview. The Accept button commits the current preview state only.

## Deterministic Matching

When a YAML key does not directly match a canonical path or alias, `EmpiricalYamlMatcher` may propose a mapping using key tokens, dotted-path context, unit suffixes, value type compatibility, field role, and historical mapping profiles.

Weak empirical matches are review-only. The tool must never silently commit low-confidence mappings or one-to-many/two-to-one conflicts without user confirmation.
