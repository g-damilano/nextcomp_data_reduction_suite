# Analysis [MTDA] Process Flows

## Scope

This document describes the current MTDA analysis process. The goal is to make explicit how a prepared `.mtdp` package becomes a `.mtda` archive with reports, audit evidence, workbench output, validation outputs, and acceptance information.

This document should be expanded over time into finer drill-downs for method packages, mapping resolution, readiness, operations, validation, acceptance, report generation, archive layout, and finalization.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Method wizard controller | `src/ui/method_run_wizard/controller.py` |
| Method wizard service adapter | `src/ui/method_run_wizard/service_adapter.py` |
| Method run worker | `src/ui/method_run_wizard/worker.py` |
| Method run backend service | `src/methods/core/method_run_service.py` |
| Readiness checker | `src/readiness/readiness_checker.py` |
| Method executor | `src/methods/core/method_executor.py` |
| Method package loader | `src/methods/core/method_package.py` |
| Operation registry | `src/operations/core/operation_registry.py` |
| Validation engine | `src/validation/validation_engine.py` |
| Acceptance engine | `src/acceptance/acceptance_engine.py` |
| Selection editor | `src/acceptance/selection_editor.py` |
| MTDA writer | `src/archives/mtda/writer.py` |
| MTDA finalization | `src/mtda_finalization/` |

---

## L1 — MTDA analysis overview

```mermaid
flowchart TB
    AnalysisTile["Launcher Analysis tile"] --> Window["MethodRunWindow"]
    Window --> Controller["MethodRunController"]

    Controller --> Setup["SETUP<br/>package · method · mapping · readiness"]
    Setup --> Running["RUNNING<br/>service worker execution"]
    Running --> Review["REVIEW<br/>acceptance decisions"]
    Review --> Finalize["FINALIZE<br/>report completion / MTDA finalization"]

    Setup --> Service["MethodRunService"]
    Running --> Service
    Service --> Executor["MethodExecutor"]
    Executor --> Writer["MTDAWriter"]
    Writer --> MTDA[".mtda archive"]

    Finalize --> Surfaces["Open surfaces<br/>test report · audit report · workbench · output folder"]
```

---

## L2 — Wizard setup and readiness route

```mermaid
flowchart TB
    Start["Open Analysis"] --> Package{"Package selected?"}
    Package -->|No| ChangePackage["_change_package<br/>choose .mtdp / .mtda"]
    ChangePackage --> LoadPackage["_load_package_context<br/>schema · run_count · sample_type"]

    LoadPackage --> Method{"Method selected?"}
    Method -->|No| MethodPicker["_ensure_method_selection<br/>registry defaults"]
    MethodPicker --> ApplyMethod["_apply_method_entry<br/>load method package"]

    ApplyMethod --> MappingDefault["_sync_mapping_from_method<br/>default mapping path"]
    MappingDefault --> LoadMapping["_load_mapping_context"]

    LoadMapping --> Candidate["MappingCandidateDiscovery"]
    LoadMapping --> Compatibility["SchemaMethodCompatibilityChecker"]
    LoadMapping --> Resolution["build_mapping_resolution_report"]
    Candidate --> Summary["mapping_summary<br/>critical/report gaps"]
    Compatibility --> Summary
    Resolution --> Summary

    Summary --> Blockers{"Execution-critical blockers?"}
    Blockers -->|Yes| Choice["_mapping_resolution_choice"]
    Choice --> ApplyDefaults["_apply_mapping_default_suggestions"]
    Choice --> Edit["_change_mapping"]
    Choice --> Cancel["Cancel readiness"]
    ApplyDefaults --> LoadMapping
    Edit --> LoadMapping

    Blockers -->|No| Readiness["check_readiness_async"]
    Summary --> ReportGaps{"Only report/metadata gaps?"}
    ReportGaps -->|Accepted / resolved| Readiness
```

### Current behaviour

The wizard does not move directly from package selection to execution. It first resolves method and mapping context, exposes mapping blockers, permits suggested repair or mapping editing, and then runs readiness asynchronously.

### Follow-up drill-downs required

- Method registry defaults.
- Mapping dialog model and suggested default repair.
- Metadata/report-completion gaps vs execution-critical blockers.
- Setup task cards and action-bar logic.

---

## L2 — Readiness check

```mermaid
flowchart TB
    Readiness["ReadinessChecker.check"] --> Declaration["MethodInputsDeclaration.from_payload"]
    Declaration --> Requirements{"Any requirements?"}
    Requirements -->|No| Empty["ReadinessReport.empty"]
    Requirements -->|Yes| ForEach["For each MethodInputRequirement"]

    ForEach --> Conditional{"required_when applies?"}
    Conditional -->|No| Skip["Skip requirement"]
    Conditional -->|Yes| Resolve["_resolve_mapping<br/>channels / fields / dataset fallback"]

    Resolve --> MissingMap{"Mapped source exists?"}
    MissingMap -->|No| MappingMissing["ResolvedInput<br/>status = mapping_missing"]
    MissingMap -->|Yes| Scope{"Requirement scope"}

    Scope -->|per_run| RunCheck["_evaluate_run_requirement"]
    Scope -->|per_dataset| DatasetCheck["_evaluate_dataset_requirement"]
    Scope -->|per_package| PackageCheck["_evaluate_package_requirement"]

    RunCheck --> Kind{"source_kind"}
    Kind -->|channel| ChannelCheck["run.channel<br/>values + unit check"]
    Kind -->|field| TokenCheck["run.token<br/>value + unit check"]

    DatasetCheck --> DatasetValue["dataset dotted path / aliases / schema field match"]
    PackageCheck --> PackageValue["manifest/schema value"]

    MappingMissing --> Records["ResolvedInput records"]
    ChannelCheck --> Records
    TokenCheck --> Records
    DatasetValue --> Records
    PackageValue --> Records

    Records --> Status["_status"]
    Status --> Report["ReadinessReport"]
```

### Status meaning

| Status | Meaning |
|---|---|
| `MAPPING_REQUIRED` | At least one execution-critical requirement has no mapping. |
| `NOT_READY` | An execution-critical requirement is present in mapping but missing/empty/failed in the package. |
| `READY_WITH_WARNINGS` | Execution can proceed, but report/completeness/warning inputs are missing or imperfect. |
| `READY` | All evaluated requirements pass. |

### Follow-up drill-downs required

- Method input declaration schema.
- Mapping profile schema.
- Dataset fallback resolution.
- Unit-compatibility policy.
- Reporting of per-run vs per-dataset readiness rows.

---

## L2 — Service execution phases

```mermaid
flowchart TB
    Request["MethodRunRequest"] --> OutputGate{"Output exists and overwrite false?"}
    OutputGate -->|Yes| OutputError["Return error"]
    OutputGate -->|No| LoadPackage["load_input_package<br/>package_reader.read"]

    LoadPackage --> LoadMethod["load_method_package<br/>MethodPackage.load"]
    LoadMethod --> LoadMapping["load_mapping<br/>YAML/JSON + normalize"]
    LoadMapping --> Compatibility["SchemaMethodCompatibilityChecker.check"]
    Compatibility --> SchemaBlock{"Schema extension required?"}
    SchemaBlock -->|Yes| NotReady["Return not_ready"]
    SchemaBlock -->|No| Readiness["ReadinessChecker.check"]

    Readiness --> ReadinessBlock{"blocks_execution?"}
    ReadinessBlock -->|Yes| NotReady2["Return not_ready<br/>readiness summary + errors"]
    ReadinessBlock -->|No| Execute["MethodExecutor.execute"]

    Execute --> HumanDecisions{"Human decisions supplied?"}
    HumanDecisions -->|Yes| SelectionEdit["SelectionEditor.apply<br/>operator overrides"]
    HumanDecisions -->|No| ReportOverrides
    SelectionEdit --> ReportOverrides{"Report overrides supplied?"}

    ReportOverrides -->|Yes| ApplyOverrides["Attach report_overrides"]
    ReportOverrides -->|No| Write
    ApplyOverrides --> Write["MTDAWriter.write"]

    Write --> Workbench{"generate_workbench?"}
    Workbench -->|Yes| BuildWorkbench["_write_workbench"]
    Workbench -->|No| Result
    BuildWorkbench --> Result["MethodRunServiceResult"]
```

### Current phase sequence

The UI adapter defines the execution phases as:

1. `load_input_package`
2. `load_method_package`
3. `load_mapping`
4. `readiness_check`
5. `method_resolve`
6. `method_reduce`
7. `validation`
8. `acceptance`
9. `write_mtda`
10. `build_audit_report`
11. `build_workbench_optional`
12. `complete`

### Follow-up drill-downs required

- Worker signal behaviour.
- Progress event payloads.
- Error and cancellation paths.
- Difference between service-level acceptance decisions and wizard review persistence.

---

## L2 — Method executor internals

```mermaid
flowchart TB
    Executor["MethodExecutor.execute"] --> ReadyAgain["ReadinessChecker.check"]
    ReadyAgain --> Block{"Blocks execution?"}
    Block -->|Yes| Raise["raise MethodReadinessError"]
    Block -->|No| Context["MethodRunContext<br/>source · method_package · mapping · registry"]

    Context --> ResolvePhase["method_resolve phase"]
    ResolvePhase --> ResolveSteps["For each resolve_recipe step"]
    ResolveSteps --> OperationRegistry1["OperationRegistry.run"]
    OperationRegistry1 --> Record1["context.record(operation result)"]
    Record1 --> ResolveSummary["_build_resolve_summary"]

    ResolveSummary --> ReducePhase["method_reduce phase"]
    ReducePhase --> ReduceSteps["For each reduce_recipe step"]
    ReduceSteps --> OperationRegistry2["OperationRegistry.run"]
    OperationRegistry2 --> Record2["context.record(operation result)"]
    Record2 --> ReduceSummary["_build_reduce_summary"]

    ReduceSummary --> Boundaries["_build_experiment_boundaries"]
    Boundaries --> BoundaryEvents["_build_boundary_events"]
    BoundaryEvents --> Specimens["_build_specimen_results"]
    Specimens --> Curves["_build_curve_family<br/>bounded + full"]
    Curves --> DatasetSummary["_build_dataset_summary"]

    DatasetSummary --> Validation["MethodValidationEngine.validate"]
    Validation --> Acceptance["AcceptanceEngine.evaluate"]
    Acceptance --> Selection["SelectionEditor.apply<br/>machine defaults"]

    Selection --> Result["MethodRunResult"]
```

### Current responsibility

The executor is the core analysis engine. It converts a source package, method package, and mapping into a structured `MethodRunResult` containing:

- Readiness report and resolved/missing inputs.
- Per-specimen results.
- Dataset summary.
- Bounded and full curve-family data.
- Operation log.
- Evidence index inputs.
- Validation report and deviations.
- Acceptance report and selection sets.
- Boundary events.
- Human-decision and final-selection structures.

### Follow-up drill-downs required

- `MethodRunContext` data model.
- Operation registry and operation contracts.
- Resolve recipe step semantics.
- Reduce recipe step semantics.
- Boundary detection and bounded/full curve-family distinction.
- Bending diagnostic data path.

---

## L2 — Review and finalization route

```mermaid
flowchart TB
    Completed["Worker completed execution"] --> StoreResult["state.service_result"]
    StoreResult --> AcceptanceSummary["state.acceptance_summary / acceptance_report"]
    AcceptanceSummary --> EnterReview["_enter_review"]

    EnterReview --> BuildRows["_review_models_from_summary"]
    BuildRows --> Defaults["Set default keep/remove decisions"]
    Defaults --> OperatorChoice{"Operator changes flagged run decision?"}

    OperatorChoice -->|Keep flagged run| NeedReason["Require override reason"]
    OperatorChoice -->|Remove / default| NoReason["No override reason needed"]
    NeedReason --> ReasonGate{"Reason supplied?"}
    ReasonGate -->|No| BlockConfirm["Block Confirm & open output"]
    ReasonGate -->|Yes| Confirm
    NoReason --> Confirm["_confirm_review"]

    Confirm --> Persist["service_adapter.persist_acceptance"]
    Persist --> Finalize["_enter_finalize"]
    Finalize --> OpenSurfaces["Open test report / audit report / workbench / folder"]
    Finalize --> ReportCompletion["ReportCompletionDialog"]
    Finalize --> FinalizeMTDA["_finalize_mtda"]
    FinalizeMTDA --> FinalizationService["MTDAFinalizationService.finalize"]
    FinalizationService --> FinalizedArchive["*_finalized.mtda"]
```

### Current responsibility

The review stage is an execution-output review stage, not a method-definition stage and not a package-preparation stage. Its main concern is acceptance decisions and final report membership.

### Follow-up drill-downs required

- Difference between machine selection, human override, and final report runs.
- Persistence of review decisions into MTDA.
- Finalization amendment request structure.
- Report-completion dialog behaviour.

---

## L3 — MTDA archive writing

```mermaid
flowchart TB
    Result["MethodRunResult"] --> MethodReport["ReportBuilder.build<br/>test report files"]
    Result --> EvidenceIndex["build_procedure_evidence_index"]
    EvidenceIndex --> AuditBlocks["build_audit_blocks"]
    AuditBlocks --> AuditPayload["AuditReportBuilder.build_payload"]
    AuditBlocks --> AuditHTML["AuditReportBuilder.build"]
    Result --> WorkbenchTrace["build_operation_trace"]
    WorkbenchTrace --> WorkbenchHTML["MethodDevelopmentReportBuilder"]

    Result --> Compatibility["compatibility_artifacts"]
    Result --> MappingReports["mapping profile · candidates · resolution"]
    Result --> ReadinessFiles["readiness_report.json<br/>summary/resolved/missing CSV"]
    Result --> OutputFiles["specimen results · dataset summary · curve family · boundaries"]
    Result --> ValidationFiles["validation report · deviations · reference values"]
    Result --> AcceptanceFiles["acceptance report · flags · selection sets · human decisions · final report runs"]

    MethodReport --> Files["MTDA file map"]
    AuditPayload --> Files
    AuditHTML --> Files
    WorkbenchHTML --> Files
    Compatibility --> Files
    MappingReports --> Files
    ReadinessFiles --> Files
    OutputFiles --> Files
    ValidationFiles --> Files
    AcceptanceFiles --> Files

    Files --> Recommended["_recommended_mtda_files<br/>recommended archive layout"]
    Recommended --> SurfaceManifest["software/surface_manifest.json"]
    SurfaceManifest --> Checksums["software/checksums.json"]
    Checksums --> ArchiveIndex["archive_index.csv"]
    ArchiveIndex --> Zip["ZipArchiveWriter.write"]
    Zip --> MTDA[".mtda"]
```

## L4 — MTDA archive contract matrix

| Member / area | Producer | Purpose |
|---|---|---|
| `manifest.json` | `build_mtda_manifest` | Top-level MTDA archive metadata. |
| `source_reference.json` | `_source_reference` | Links MTDA output to source MTDP package. |
| `mapping_profile.json` | `MTDAWriter.write` | Captures mapping used by run. |
| `mapping/*` | Mapping report builders | Stores used mapping, candidate discovery, resolution report. |
| `readiness/*` | `ReadinessChecker` output | Stores readiness report, summary, resolved and missing inputs. |
| `method_outputs/*` | `MethodExecutor` result | Stores specimen results, dataset summary, curves, boundaries. |
| `validation/*` | `MethodValidationEngine` | Stores validation report, deviations, reference values. |
| `acceptance/*` | `AcceptanceEngine` / `SelectionEditor` | Stores acceptance report, flags, selection sets, human decisions, final report runs. |
| `audit/procedure_evidence_index.json` | `build_procedure_evidence_index` | Index from outputs/procedures to evidence. |
| `audit/audit_blocks.json` | `build_audit_blocks` | Human-facing audit block grouping. |
| `audit/audit_report.html/json` | `AuditReportBuilder` | Audit report surface and data payload. |
| `workbench/index.html` | `MethodDevelopmentReportBuilder` | Operation-level development/debug surface. |
| `report/test_report.html/json/pdf` | `ReportBuilder` / recommended layout | Formal result-facing test report. |
| `software/surface_manifest.json` | `build_surface_manifest` | Surface discovery metadata. |
| `software/checksums.json` | `build_checksums` | Archive integrity metadata. |
| `archive_index.csv` | `_archive_index_rows` | Flat archive member index. |

## Known missing drill-downs

The following should be documented next:

1. Method package structure and recipe YAML contracts.
2. Mapping profile schema and candidate/resolution report structure.
3. Readiness report row model.
4. Operation registry and individual operation flow.
5. Validation engine policies.
6. Acceptance engine policies and selection-set logic.
7. Procedure evidence index and audit block construction.
8. Test report builder structure.
9. MTDA finalization and amendment flow.
