# Validation Policy Flow

## Scope

This document describes the current validation flow after method reduction has produced specimen results and curve-family rows.

Validation here means reference-value validation against declared method-package validation recipe checks. It is separate from:

- MTDP package validation before export.
- Analysis readiness checks before execution.
- Acceptance/selection decisions after validation.
- Report-completion checks for formal report fields.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Validation engine | `src/validation/validation_engine.py` |
| Validation report model | `src/validation/validation_report.py` |
| Reference value loader | `src/validation/reference_values.py` |
| Validation check model | `src/validation/validation_check.py` |
| Tolerance policy | `src/validation/tolerance_policy.py` |
| Method executor call site | `src/methods/core/method_executor.py` |
| MTDA writer validation artifacts | `src/archives/mtda/writer.py` |

---

## L2 — Validation stage in method execution

```mermaid
flowchart TB
    MethodReduce["method_reduce complete"] --> Specimens["specimen_results"]
    MethodReduce --> Curves["curve_family"]
    MethodReduce --> OperationLog["operation_log"]

    Specimens --> Validate["MethodValidationEngine.validate"]
    Curves --> Validate
    OperationLog --> Validate
    MethodPackage["MethodPackage.validation_recipe"] --> Validate
    Mapping["Mapping profile"] --> Validate
    Source["MTDPPackageInput"] --> Validate

    Validate --> Report["ValidationReport"]
    Report --> ExecutorResult["MethodRunResult.validation_report"]
    Report --> SummaryRows["validation_summary"]
    Report --> DeviationRows["validation_deviations"]
    Report --> ReferenceRows["reference_values_used"]
```

## Current responsibility

Validation compares computed method outputs with external or declared reference values when a validation recipe and reference values are available. It does not decide final report inclusion directly; instead, validation failures become inputs to the later acceptance stage.

---

## L2 — Validation recipe and reference-value loading

```mermaid
flowchart TB
    MethodPackage["MethodPackage"] --> Recipe["_validation_recipe"]
    Recipe --> Checks["_checks_by_reference_field"]
    Checks --> ValidationCheck["ValidationCheck.from_recipe"]

    Recipe --> ReferencePath["_reference_path_text"]
    Mapping["Mapping profile"] --> ReferencePath
    ReferencePath --> HasPath{"Reference path found?"}
    HasPath -->|No| EmptyRefs["ReferenceValueSet.empty"]
    HasPath -->|Yes| ResolvePath["_resolve_reference_path"]

    ResolvePath --> CandidatePaths["Absolute path or method root / source folder / cwd"]
    CandidatePaths --> Exists{"Existing file found?"}
    Exists -->|No| EmptyRefs
    Exists -->|Yes| LoadCSV["ReferenceValueSet.from_csv"]
    LoadCSV --> References["ReferenceValue tuple"]
```

## Reference-value path priority

| Source | Meaning |
|---|---|
| `mapping.validation.reference_values_path` | Mapping can point to a validation reference CSV. |
| `validation_recipe.validation.reference_values.path` | Method package validation recipe can point to reference values. |
| None / missing file | Validation uses an empty reference set and produces no normal comparison checks. |

---

## L3 — Per-reference validation check

```mermaid
flowchart TB
    References["ReferenceValueSet.values"] --> RefLoop["For each reference value"]
    RefLoop --> CheckLookup{"Validation check declared for reference field?"}
    CheckLookup -->|No| NotApplicable["ValidationResult<br/>status = not_applicable"]
    CheckLookup -->|Yes| Compute["_computed_value"]

    Compute --> SourceKind{"check.source"}
    SourceKind -->|specimen_results| SpecimenLookup["specimen_by_run[run_id][computed_field]"]
    SourceKind -->|curve_family| CurveLookup["curves_by_run[run_id][point_index][computed_field]"]
    SourceKind -->|other| MissingComputed["computed = None"]

    SpecimenLookup --> Scale["Apply computed_scale"]
    CurveLookup --> Scale
    MissingComputed --> Tolerance

    Scale --> Tolerance["TolerancePolicy.evaluate"]
    Tolerance --> OperationLink["_find_operation"]
    OperationLink --> Result["ValidationResult"]
    NotApplicable --> Result
```

## Computed-value sources

| `check.source` | Computed value source |
|---|---|
| `specimen_results` | Per-run specimen result row. |
| `curve_family` | Per-run curve-family row at `point_index`. |
| Other/unknown | Treated as missing computed value. |

---

## L3 — Tolerance policy

```mermaid
flowchart TB
    Computed["computed value"] --> Missing{"Computed or reference missing?"}
    Reference["reference value"] --> Missing
    Missing -->|Yes| FailMissing["status = fail"]
    Missing -->|No| Difference["difference_abs = computed - reference<br/>difference_rel = difference_abs / reference"]

    Difference --> Limits["abs tolerance / relative tolerance"]
    Limits --> Tolerance["tolerance = max(available limits)<br/>or 0.0"]
    Tolerance --> Within{"abs(difference_abs) <= tolerance?"}
    Within -->|Yes| Pass["status = pass"]
    Within -->|No| Severity{"severity == warn?"}
    Severity -->|Yes| Warn["status = warn"]
    Severity -->|No| Fail["status = fail"]
```

## Validation statuses

| Status | Meaning |
|---|---|
| `pass` | Computed value is within tolerance. |
| `warn` | Computed value is outside tolerance but check severity is warning. |
| `fail` | Computed/reference missing or computed value is outside fail-severity tolerance. |
| `not_applicable` | Reference field has no declared validation check. |
| `missing_reference` | Counted by report model if present in checks, although the current engine mainly emits empty reference sets rather than explicit rows when no references exist. |

---

## L2 — Validation report and archive outputs

```mermaid
flowchart TB
    ValidationResults["ValidationResult tuple"] --> ValidationReport["ValidationReport"]
    ValidationReport --> Summary["summary property"]
    ValidationReport --> ToDict["to_dict"]
    ValidationReport --> SummaryRows["summary_rows"]
    ValidationReport --> DeviationRows["deviation_rows"]
    ValidationReport --> ReferenceRows["reference_rows"]

    ToDict --> Json["validation/validation_report.json"]
    SummaryRows --> SummaryCsv["validation/validation_summary.csv"]
    DeviationRows --> DeviationsCsv["validation/deviations.csv"]
    ReferenceRows --> ReferenceCsv["validation/reference_values_used.csv"]
```

## Validation output contract

| Artifact | Producer | Purpose |
|---|---|---|
| `validation/validation_report.json` | `ValidationReport.to_dict` | Complete validation report with checks and summary. |
| `validation/validation_summary.csv` | `summary_rows` | Single-row summary of validation status/counts. |
| `validation/deviations.csv` | `deviation_rows` | Non-pass checks and non-zero differences. |
| `validation/reference_values_used.csv` | `reference_rows` | Reference values loaded from CSV. |

---

## L4 — Validation data contract

| Source | Transformation | Destination | Failure/gate behaviour |
|---|---|---|---|
| `method_package.validation_recipe` | `_validation_recipe` | Recipe dictionary | Missing recipe produces empty checks. |
| Recipe checks | `ValidationCheck.from_recipe` | Check map keyed by reference field | Missing check for reference field yields `not_applicable`. |
| Mapping or recipe reference path | `_reference_path_text` and `_resolve_reference_path` | Reference CSV path | Missing path/file yields empty reference set. |
| Reference CSV | `ReferenceValueSet.from_csv` | `ReferenceValue` rows | Bad CSV/numeric parse would raise during loading. |
| Specimen results / curve family | `_computed_value` | Computed numeric value | Missing value yields fail through tolerance policy. |
| Operation log | `_find_operation` | Operation id / recipe step id | Missing operation link leaves trace fields blank. |
| Tolerance policy | `evaluate` | pass/warn/fail | Severity controls warn vs fail when outside tolerance. |

## Open drill-downs

1. Validation recipe schema and examples.
2. Reference CSV file contract and parser hardening.
3. How validation failures map into acceptance flags.
4. How validation deviations are surfaced in audit report and test report.
5. Whether missing reference values should produce explicit validation rows.
6. Unit handling between computed values and reference values.
