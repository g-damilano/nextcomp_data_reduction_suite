# Method Package and Operation Execution Flow

## Scope

This document describes how a method package is loaded and executed through resolve/reduce recipes, operation registry dispatch, operation result logging, evidence contracts, validation, acceptance, and `MethodRunResult` assembly.

It focuses on the computation/evidence spine after readiness has passed. It does not fully document each individual operation implementation.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Method package loader | `src/methods/core/method_package.py` |
| Method executor | `src/methods/core/method_executor.py` |
| Method run context | `src/methods/core/method_context.py` |
| Operation registry | `src/operations/core/operation_registry.py` |
| Operation interface | `src/operations/core/operation.py` |
| Operation context/run model | `src/operations/core/operation_context.py` |
| Operation result model | `src/operations/core/operation_result.py` |
| Operation evidence contracts | `src/operations/core/operation_contract_registry.py` |
| Validation engine | `src/validation/validation_engine.py` |
| Acceptance engine | `src/acceptance/acceptance_engine.py` |
| Selection editor | `src/acceptance/selection_editor.py` |

---

## L2 — Method package load contract

```mermaid
flowchart TB
    Root["Method package root"] --> Load["MethodPackage.load"]

    Load --> Manifest["method_manifest.yaml"]
    Load --> Resolve["resolve_recipe.yaml"]
    Load --> Reduce["reduce_recipe.yaml"]
    Load --> Audit["audit_recipe.yaml"]
    Load --> Validation["validation_recipe.yaml if present"]
    Load --> Acceptance["acceptance_recipe.yaml if present"]
    Load --> Inputs["method_inputs.yaml if present"]
    Load --> Report["report_recipe.yaml if present"]
    Load --> CurvePolicy["curve_aggregation_policy.yaml if present"]
    Load --> CurveAcceptance["curve_family_acceptance_recipe.yaml if present"]

    Manifest --> Package["MethodPackage"]
    Resolve --> Package
    Reduce --> Package
    Audit --> Package
    Validation --> Package
    Acceptance --> Package
    Inputs --> Package
    Report --> Package
    CurvePolicy --> Package
    CurveAcceptance --> Package
```

## Method package file roles

| File | Current role |
|---|---|
| `method_manifest.yaml` | Method id, version, name, status, analysis type, standard reference, expected outputs, limitations. |
| `method_inputs.yaml` | Declares method input requirements used by mapping and readiness. |
| `resolve_recipe.yaml` | Recipe steps for binding source data and deriving prerequisite resolved inputs. |
| `reduce_recipe.yaml` | Recipe steps for reducing method outputs such as strength, modulus, strain, bending diagnostics. |
| `validation_recipe.yaml` | Validation policy input. |
| `acceptance_recipe.yaml` | Acceptance policy input. |
| `audit_recipe.yaml` | Audit/report evidence configuration input. |
| `report_recipe.yaml` | Test-report structure/input. |
| `curve_aggregation_policy.yaml` | Curve aggregation policy. |
| `curve_family_acceptance_recipe.yaml` | Curve-family acceptance and diagnostic policy. |
| Additional package files | `bending_assessment_policy.yaml`, `export_recipe.yaml`, and `plot_style_recipe.yaml` may be included in recipe_files if present. |

---

## L2 — Execution context creation

```mermaid
flowchart TB
    Source["MTDPPackageInput"] --> Context["MethodRunContext"]
    MethodPackage["MethodPackage"] --> Context
    Mapping["Mapping profile"] --> Context
    Registry["default_operation_registry"] --> Context
    Inspector["CurveInspector"] --> Context

    Context --> Runs["OperationRun per source run"]
    Runs --> RunState["scalars · series · units · metadata · diagnostics"]
    Context --> OperationLog["operation_log"]
    Context --> Inspections["inspections"]
    Context --> Warnings["warnings"]

    Context --> OperationContext["operation_context(phase)"]
    OperationContext --> OperationInputs["source · mapping · runs · inspector · phase · inspections"]
```

## Current context responsibility

`MethodRunContext` converts each source run into an `OperationRun` with mutable analysis state. Operations add scalars, series, units, diagnostics, metadata, warnings, inspections, and operation records as the recipes execute.

---

## L2 — Resolve/reduce recipe execution

```mermaid
flowchart TB
    Executor["MethodExecutor.execute"] --> ReadinessAgain["ReadinessChecker.check"]
    ReadinessAgain --> Blocked{"blocks_execution?"}
    Blocked -->|Yes| Error["Raise MethodReadinessError"]
    Blocked -->|No| Context["Create MethodRunContext"]

    Context --> ResolvePhase["method_resolve"]
    ResolvePhase --> ResolveRecipe["method_package.resolve_recipe['resolve']"]
    ResolveRecipe --> ResolveLoop["For each recipe step"]
    ResolveLoop --> RegistryRun["OperationRegistry.run(context, step)"]
    RegistryRun --> ResolveResults["OperationResult list"]
    ResolveResults --> RecordResolve["context.record"]
    RecordResolve --> ResolveSummary["_build_resolve_summary"]

    ResolveSummary --> ReducePhase["method_reduce"]
    ReducePhase --> ReduceRecipe["method_package.reduce_recipe['reduce']"]
    ReduceRecipe --> ReduceLoop["For each recipe step"]
    ReduceLoop --> RegistryRun2["OperationRegistry.run(context, step)"]
    RegistryRun2 --> ReduceResults["OperationResult list"]
    ReduceResults --> RecordReduce["context.record"]
    RecordReduce --> ReduceSummary["_build_reduce_summary"]
```

## Recipe step contract

Each recipe step must be a mapping and must include an `op` value. The registry looks up the operation by `op`, runs it, then annotates the returned operation results with recipe/evidence/report metadata.

---

## L3 — Operation registry dispatch and evidence annotation

```mermaid
flowchart TB
    Step["Recipe step"] --> OpID["Read step['op']"]
    OpID --> Exists{"Operation registered?"}
    Exists -->|No| Unknown["KeyError: Unknown operation"]
    Exists -->|Yes| Operation["operation.run(context, step)"]

    Operation --> Results["OperationResult list"]
    Results --> StepMeta["step id / label / audit_view"]
    Results --> Contract["get_evidence_contract(operation_type)"]
    Results --> Annotations["step evidence/report/surface_policy annotations"]

    Contract --> Patch["Patch OperationResult"]
    Annotations --> Patch
    StepMeta --> Patch

    Patch --> PatchedResult["OperationResult with<br/>procedure_step_id · evidence_contract_id · audit block/view · workbench view · report roles · evidence refs"]
```

## Default operation registry

The current default registry registers these operations:

| Operation class | Purpose area |
|---|---|
| `MapChannelOperation` | Bind package channels into operation state. |
| `MapScalarOperation` | Bind scalar/token/package values. |
| `DeriveAreaOperation` | Derive cross-sectional area. |
| `OrientStrainChannelsOperation` | Orient strain channels. |
| `DeriveSeriesMeanOperation` | Construct mean series. |
| `ResolveExperimentBoundariesOperation` | Resolve analysis interval boundaries. |
| `DeriveSeriesByScalarOperation` | Derive series such as stress from load/area. |
| `MaxPointOperation` | Find maximum point. |
| `AcceptedPeakPointOperation` | Resolve accepted peak point. |
| `ValueAtIndexOperation` | Sample value at an index. |
| `ChordSlopeOperation` | Compute chord-slope modulus. |
| `BendingDiagnosticOperation` | Compute bending diagnostics. |

---

## L3 — Operation result and operation log record

```mermaid
flowchart TB
    OperationResult["OperationResult"] --> ToRecord["to_record(sequence)"]

    ToRecord --> OperationID["stable operation_id<br/>sequence_phase_run_operation"]
    ToRecord --> Status["Normalized status<br/>pass · pass_with_warning · failed"]
    ToRecord --> Inputs["inputs"]
    ToRecord --> Parameters["parameters"]
    ToRecord --> Outputs["outputs"]
    ToRecord --> Units["units"]
    ToRecord --> Evidence["evidence"]
    ToRecord --> Refs["default evidence refs"]
    ToRecord --> ContractMeta["evidence contract / role / audit block / report roles"]

    OperationID --> Log["audit/operation_log.json row"]
    Status --> Log
    Inputs --> Log
    Parameters --> Log
    Outputs --> Log
    Units --> Log
    Evidence --> Log
    Refs --> Log
    ContractMeta --> Log
```

## OperationResult record importance

Operation results are the core bridge between computation and audit/report surfaces. They carry both computational outputs and evidence routing metadata.

| Field group | Why it matters |
|---|---|
| `inputs`, `parameters`, `outputs`, `units` | Reconstructs what the operation did. |
| `warnings`, `status` | Feeds warning/failed operation evidence. |
| `evidence`, `inspection_refs` | Links operation to deeper diagnostic evidence. |
| `procedure_step_id`, `recipe_step_id`, `recipe_step_label` | Links operation back to method recipe/procedure. |
| `evidence_contract_id`, `evidence_role` | Controls audit/report interpretation. |
| `default_audit_block`, `default_audit_view`, `workbench_view` | Controls how evidence surfaces are grouped/displayed. |
| `report_roles` | Links operation evidence to formal report values. |
| `evidence_refs` | Links operation to archive members and report/workbench artifacts. |

---

## L2 — Post-operation result assembly

```mermaid
flowchart TB
    ReduceSummary["Reduce phase complete"] --> Boundaries["_build_experiment_boundaries"]
    Boundaries --> BoundaryEvents["_build_boundary_events"]
    BoundaryEvents --> Specimens["_build_specimen_results"]
    Specimens --> CurveFamily["_build_curve_family bounded"]
    Specimens --> FullCurveFamily["_build_curve_family full"]
    Specimens --> DatasetSummary["_build_dataset_summary"]

    DatasetSummary --> Validation["MethodValidationEngine.validate"]
    Validation --> Acceptance["AcceptanceEngine.evaluate"]
    Acceptance --> Selection["SelectionEditor.apply<br/>machine default selection"]

    Selection --> Evidence["_build_evidence"]
    Evidence --> Result["MethodRunResult"]
```

## Result assembly outputs

| Output | Producer | Purpose |
|---|---|---|
| `resolve_summary` | `_build_resolve_summary` | Summarises bound scalars/series and source metadata after resolve. |
| `reduce_summary` | `_build_reduce_summary` | Summarises key reduced outputs and diagnostics. |
| `experiment_boundaries` | `_build_experiment_boundaries` | Captures analysis interval definitions. |
| `boundary_events` | `_build_boundary_events` | Flattens boundary events for audit/report surfaces. |
| `specimen_results` | `_build_specimen_results` | Per-run reduced result rows. |
| `curve_family` | `_build_curve_family` | Bounded stress/strain family table. |
| `full_curve_family` | `_build_curve_family(bounded=False)` | Full curve table. |
| `dataset_summary` | `_build_dataset_summary` | Aggregate summary rows. |
| `validation_report` | `MethodValidationEngine` | Validation status and deviations. |
| `acceptance_report` | `AcceptanceEngine` | Acceptance flags, selection sets, curve-family diagnostics. |
| `final selection structures` | `SelectionEditor` | Machine/default selection and future human override structures. |
| `evidence` | `_build_evidence` | Summary evidence index inputs. |

---

## L3 — Evidence contract layer

```mermaid
flowchart TB
    OperationType["operation_type"] --> ContractLookup["get_evidence_contract"]
    ContractLookup --> Registered{"Registered contract?"}
    Registered -->|Yes| Contract["EvidenceContract"]
    Registered -->|No| Fallback["Fallback supporting evidence contract"]

    Contract --> AuditBlock["default_audit_block"]
    Contract --> AuditView["default_audit_view"]
    Contract --> WorkbenchView["workbench_view"]
    Contract --> RequiredRefs["required_evidence_refs"]
    Contract --> Narrative["default_narrative"]
    Contract --> IO["input/output schema expectations"]
    Contract --> ReportRoles["report_roles"]

    AuditBlock --> OperationRecord["Annotated operation record"]
    AuditView --> OperationRecord
    WorkbenchView --> OperationRecord
    RequiredRefs --> OperationRecord
    ReportRoles --> OperationRecord
```

## Evidence-contract implications

Evidence contracts are currently the key mechanism preventing the audit report from becoming just one plot per operation. They allow operations to be grouped into human-auditable blocks such as:

- run identity and status
- run stress-strain reduction
- run bending evidence
- run validation evidence
- run selection consequence
- aggregate curve family
- aggregate curve diagnostics
- aggregate statistics

---

## L4 — Operation execution data contract

| Source | Transformation | Destination | Failure/gate behaviour |
|---|---|---|---|
| Method recipe step | `OperationRegistry.run` | Operation class dispatch | Missing `op` raises `ValueError`; unknown op raises `KeyError`. |
| Operation context state | Operation implementation | OperationResult list | Operation-specific failures/warnings become result status/warnings or exceptions. |
| OperationResult | Registry evidence patching | Annotated OperationResult | Missing contract uses fallback evidence contract. |
| Annotated OperationResult | `context.record` | `operation_log` record | Warnings copied into context warnings list. |
| Operation state | Result builders | specimen/dataset/curve/evidence outputs | Missing expected scalars/series can propagate to validation/acceptance/report gaps. |
| Validation/acceptance outputs | MethodRunResult | MTDA writer inputs | Archive/report generation depends on these structured results. |

## Open drill-downs

1. Individual operation flows and input/output contracts.
2. Resolve recipe for the current ISO 14126 compression method.
3. Reduce recipe for the current ISO 14126 compression method.
4. Boundary-resolution operation internals.
5. Bending diagnostic operation internals.
6. Validation engine policy and output rows.
7. Acceptance engine policy, discharge logic, and selection-set creation.
8. Evidence contract completeness versus report/audit/workbench surfaces.
