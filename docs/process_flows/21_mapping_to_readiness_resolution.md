# Mapping to Readiness Resolution

## Scope

This document describes how the analysis side moves from a selected MTDP package, method package, and mapping profile into a readiness decision.

It focuses on mapping candidate discovery, mapping resolution, readiness requirement evaluation, and wizard gate behaviour. It does not document the detailed method execution operations after readiness passes.

## Source anchors

| Flow area | Code anchor |
|---|---|
| Wizard setup/controller | `src/ui/method_run_wizard/controller.py` |
| Service adapter readiness worker creation | `src/ui/method_run_wizard/service_adapter.py` |
| Backend method run service | `src/methods/core/method_run_service.py` |
| Mapping profile loading | `src/methods/core/method_run_service.py::load_mapping` |
| Candidate discovery | `src/mapping/mapping_candidate_discovery.py` |
| Mapping resolution report | `src/mapping/mapping_disambiguation.py` |
| Compatibility checker | `src/compatibility/` |
| Readiness checker | `src/readiness/readiness_checker.py` |
| Readiness models/report | `src/readiness/readiness_models.py`, `src/readiness/readiness_report.py` |
| Method package input declaration | `src/methods/core/method_package.py`, method package `method_inputs.yaml` |

---

## L2 — Wizard-side mapping context

```mermaid
flowchart TB
    Package["Selected MTDP package"] --> LoadPackage["MethodRunService.load_package"]
    LoadPackage --> PackageSummary["package_summary<br/>schema_id · schema_version · sample_type · run_count"]

    PackageSummary --> MethodDefaults["MethodRegistry.defaults_for_analysis_type"]
    MethodDefaults --> MethodEntry["Selected MethodRegistryEntry"]
    MethodEntry --> LoadMethod["MethodRunService.load_method"]
    LoadMethod --> MethodSummary["method_summary<br/>method_id · version · standard · analysis_type"]

    MethodEntry --> DefaultMapping["default_mapping_path"]
    DefaultMapping --> LoadMappingContext["_load_mapping_context"]

    LoadMappingContext --> ServiceLoadMapping["MethodRunService.load_mapping"]
    ServiceLoadMapping --> MappingSummary["mapping_summary"]
    MappingSummary --> SetupUI["Setup spotlight and action bar"]
```

### Current behaviour

The wizard chooses method defaults based on the selected package analysis type. Once a method entry is selected, its default mapping is loaded and analysed against both the package and the method declaration.

---

## L2 — Backend mapping load and analysis

```mermaid
flowchart TB
    MappingPath["Mapping profile path"] --> LoadRaw["load_mapping<br/>YAML/JSON read"]
    LoadRaw --> Normalize["normalize_mapping_profile"]

    MethodPath["Method package path"] --> MethodPackage["MethodPackage.load"]
    PackagePath["MTDP package path"] --> Source["package_reader.read"]

    Normalize --> Rows["_mapping_rows"]
    MethodPackage --> MethodInputs["method.method_inputs"]
    MethodInputs --> Rows
    Source --> CandidateDiscovery["MappingCandidateDiscovery.discover"]
    MethodPackage --> CandidateDiscovery
    Source --> Compatibility["SchemaMethodCompatibilityChecker.check"]
    MethodPackage --> Compatibility

    CandidateDiscovery --> CandidateReport["mapping_candidate_report"]
    CandidateReport --> Resolution["build_mapping_resolution_report"]
    Normalize --> Resolution
    Resolution --> ResolutionReport["mapping_resolution_report"]

    Rows --> MappingStatus["_mapping_status"]
    Rows --> MappingSummary["_mapping_summary"]
    CandidateReport --> LoadResult["MappingLoadResult"]
    ResolutionReport --> LoadResult
    Compatibility --> LoadResult
    MappingSummary --> LoadResult
    MappingStatus --> LoadResult
```

## Mapping load output contract

| Output | Purpose |
|---|---|
| `mapped_fields` | Per-requirement mapping rows consumed by wizard summaries. |
| `status` | Complete/incomplete-style status derived from mapping rows. |
| `summary` | Counts for execution-critical and report mappings. |
| `compatibility_report` | Package/schema compatibility against method requirements. |
| `candidate_report` | Package-backed candidate sources for method inputs. |
| `resolution_report` | Whether mapped sources are confirmed, ambiguous, unmapped, or manual overrides. |

---

## L3 — Candidate discovery

```mermaid
flowchart TB
    MethodInputs["MethodInputsDeclaration"] --> ReqLoop["For each MethodInputRequirement"]
    ReqLoop --> FieldType{"method_field starts with channel.?"}

    FieldType -->|Yes| ChannelCandidates["_channel_candidates"]
    ChannelCandidates --> FirstRunChannels["Inspect first run channels"]
    FirstRunChannels --> NameMatch["Name/source-role confidence"]
    FirstRunChannels --> UnitFallback["Unit-compatible fallback candidates"]
    NameMatch --> ChannelSet["MappingCandidateSet"]
    UnitFallback --> ChannelSet

    FieldType -->|No| FieldCandidates["_field_candidates"]
    FieldCandidates --> RunTokens["Run token candidates"]
    FieldCandidates --> SchemaFields["Dataset/run schema field candidates"]
    RunTokens --> FieldSet["MappingCandidateSet"]
    SchemaFields --> FieldSet

    ChannelSet --> CandidateReport["mapping_candidate_report.requirements"]
    FieldSet --> CandidateReport
    CandidateReport --> Summary["resolved / ambiguous / missing counts"]
```

### Candidate selection notes

Candidate discovery is not the same as readiness. It proposes package-backed sources for declared method roles. Readiness later checks whether the selected/mapped source is actually present, non-empty, unit-compatible enough, and scoped correctly.

### Current candidate heuristics

| Candidate type | Current basis |
|---|---|
| Channel exact match | Source role equals package channel name. |
| Channel name containment | Role appears in channel name or vice versa. |
| Front/rear strain | Name tokens include front/rear and strain, or unit-compatible strain fallback. |
| Load/force | Name or unit-compatible force dimension. |
| Extension/displacement | Unit-compatible length dimension. |
| Time | Unit-compatible time dimension. |
| Run tokens | Token name match or unit-compatible fallback. |
| Schema fields | Field id, role, report_role, aliases, unit-compatible fallback. |

---

## L3 — Mapping resolution report

```mermaid
flowchart TB
    CandidateReport["Candidate report"] --> ReqLoop["For each requirement"]
    Mapping["Normalized mapping profile"] --> Lookup["Find mapped source role in channels / fields / tokens"]
    ReqLoop --> Lookup

    Lookup --> CandidateNames["Candidate source names"]
    CandidateNames --> Confirmed{"Mapped source in candidates?"}

    Confirmed -->|Yes| StatusConfirmed["status = confirmed"]
    Confirmed -->|No| EntryStatus{"Mapping entry ambiguous/unresolved?"}
    EntryStatus -->|Yes| StatusAmbiguous["status = ambiguous"]
    EntryStatus -->|No| HasMapped{"Mapped source exists?"}
    HasMapped -->|Yes| StatusManual["status = manual_override"]
    HasMapped -->|No| StatusUnmapped["status = unmapped"]

    StatusConfirmed --> Row["resolution row"]
    StatusAmbiguous --> Row
    StatusManual --> Row
    StatusUnmapped --> Row
    Row --> Summary["confirmed · ambiguous · unmapped · manual_override totals"]
```

## Resolution meanings

| Status | Meaning |
|---|---|
| `confirmed` | Mapping points to one of the discovered package-backed candidates. |
| `ambiguous` | Mapping entry or candidate set is ambiguous/unresolved. |
| `manual_override` | Mapping points to a source that was not among discovered candidates. |
| `unmapped` | No source is mapped for the requirement. |

---

## L2 — Readiness evaluation

```mermaid
flowchart TB
    Source["MTDPPackageInput"] --> Check["ReadinessChecker.check"]
    MethodPackage["MethodPackage"] --> Declaration["MethodInputsDeclaration.from_payload"]
    Mapping["Mapping profile"] --> Check
    Declaration --> Check

    Check --> ReqLoop["For each requirement"]
    ReqLoop --> Applies{"required_when applies?"}
    Applies -->|No| Skip["Skip"]
    Applies -->|Yes| ResolveMapping["_resolve_mapping"]

    ResolveMapping --> Mapped{"Mapped source exists?"}
    Mapped -->|No| MappingMissing["mapping_missing record"]
    Mapped -->|Yes| Scope{"scope"}

    Scope -->|per_run| RunReq["Evaluate every run"]
    Scope -->|per_dataset| DatasetReq["Evaluate dataset value"]
    Scope -->|per_package| PackageReq["Evaluate package manifest/schema value"]

    RunReq --> SourceKind{"source_kind"}
    SourceKind -->|channel| ChannelCheck["run.channel(mapped_source)"]
    SourceKind -->|field| TokenCheck["run.token(mapped_source)"]
    DatasetReq --> DatasetCheck["dataset dotted path + schema fallback candidates"]
    PackageReq --> PackageCheck["manifest/schema value"]

    ChannelCheck --> Records["ResolvedInput records"]
    TokenCheck --> Records
    DatasetCheck --> Records
    PackageCheck --> Records
    MappingMissing --> Records

    Records --> Status["_status"]
    Status --> Report["ReadinessReport"]
```

## Readiness gates

| Condition | Resulting status |
|---|---|
| Execution-critical mapping missing | `MAPPING_REQUIRED` |
| Execution-critical mapped input missing/empty/failed | `NOT_READY` |
| Non-critical/report inputs missing or warning states present | `READY_WITH_WARNINGS` |
| All evaluated inputs pass | `READY` |

---

## L3 — Wizard gate behaviour after mapping/readiness

```mermaid
flowchart TB
    SetupAction["Setup primary action"] --> MissingInputs{"Package/method/mapping missing?"}
    MissingInputs -->|Yes| OpenNext["Open next missing input selector"]
    MissingInputs -->|No| ReadinessState{"readiness_report exists and run_enabled?"}

    ReadinessState -->|No| MappingBlockers["_mapping_blocker_items"]
    MappingBlockers --> Blockers{"Any blockers?"}
    Blockers -->|Yes| Choice["Mapping resolution choice"]
    Choice --> ApplyDefaults["Apply suggested defaults"]
    Choice --> EditMapping["Open mapping editor"]
    Choice --> Cancel["Cancel readiness"]
    ApplyDefaults --> RecheckBlockers["Reload mapping context"]
    EditMapping --> RecheckBlockers
    RecheckBlockers --> MappingBlockers

    Blockers -->|No| StartReadiness["check_readiness_async"]
    StartReadiness --> Worker["MethodRunWorker task=readiness"]
    Worker --> Completed["readiness_report stored in state"]
    Completed --> SetupUI["Update setup spotlight/action bar"]

    ReadinessState -->|Yes| Run["Run method"]
```

## Important distinction

The wizard currently has two categories of unresolved items:

1. **Execution blockers**: prevent readiness or execution, usually missing critical mappings or critical package inputs.
2. **Report/metadata gaps**: can allow execution with warnings, but need explicit operator handling or report-completion handling.

These should remain visually and semantically separate in future UI and documentation.

---

## L4 — Data contract matrix

| Source | Transformation | Destination | Failure/gate behaviour |
|---|---|---|---|
| Method package `method_inputs.yaml` | `MethodInputsDeclaration.from_payload` | Requirement list | Empty declaration returns empty readiness report. |
| MTDP package channels/tokens/dataset | `MappingCandidateDiscovery` | Candidate report | Missing/ambiguous candidates become mapping summary concerns, not direct readiness results. |
| Mapping profile | `normalize_mapping_profile` | Normalized mapping | Load errors block setup mapping context. |
| Mapping + candidate report | `build_mapping_resolution_report` | Resolution report | Ambiguous/unmapped statuses feed mapping summary. |
| Source + method + mapping | `ReadinessChecker.check` | Readiness report | Execution-critical missing values block execution. |
| Readiness report | Controller state | Setup action bar / run enablement | Failed readiness keeps wizard in setup. |

## Open drill-downs

1. Exact mapping profile schema.
2. Method input declaration schema.
3. Mapping dialog interaction model.
4. Suggested default mapping repair logic.
5. Compatibility checker report structure.
6. Readiness report object and row model.
7. Run-enabled calculation and warning/metadata decision handling.
