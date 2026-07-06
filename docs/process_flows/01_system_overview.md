# System Overview Process Flows

## Scope

This document captures the current top-level process layout of the compression module. It is intentionally high-level and should be used as the entry point before drilling down into MTDP aggregation or MTDA analysis.

## Source anchors

Current uptake was derived from these implementation anchors:

| Area | Code anchor |
|---|---|
| Console/script entry point | `src/mtdp_enrichment/app.py` |
| Launcher window | `src/mtdp_enrichment/ui/launcher_window.py` |
| MTDP aggregation UI | `src/mtdp_enrichment/ui/main_window.py` |
| Analysis wizard controller | `src/ui/method_run_wizard/controller.py` |
| Analysis service adapter | `src/ui/method_run_wizard/service_adapter.py` |
| Method run backend service | `src/methods/core/method_run_service.py` |
| Method executor | `src/methods/core/method_executor.py` |
| MTDA writer | `src/archives/mtda/writer.py` |

## L0 — Application entry and workflow library

```mermaid
flowchart LR
    Script["mtdp-enrichment script"] --> AppMain["mtdp_enrichment.app:main"]
    AppMain --> QApplication["QApplication"]
    QApplication --> Launcher["LauncherWindow<br/>MTDP Compression Testing"]

    Launcher --> Dataset["Dataset<br/>Ready"]
    Launcher --> Method["Method<br/>planned / disabled"]
    Launcher --> Analysis["Analysis<br/>Ready"]

    Dataset --> MainWindow["MainWindow<br/>MTDP aggregation"]
    Analysis --> MethodWizard["MethodRunWindow + MethodRunController<br/>MTDA analysis"]
```

## L0 — Artifact lifecycle

```mermaid
flowchart LR
    Raw["Raw mechanical test files<br/>.csv / .txt / .dat"] --> Parser["ParserAdapter<br/>external parsing suite"]
    Parser --> Parsed["ParsedSampleRecord"]
    Parsed --> Aggregation["MTDP aggregation interface"]

    YAML["Same-stem YAML sidecars"] --> Aggregation
    Images["Image evidence"] --> Aggregation
    Supplemental["Supplemental documents/files"] --> Aggregation

    Aggregation --> MTDP[".mtdp archive"]

    MTDP --> Analysis["Analysis wizard"]
    MethodPackage["Method package"] --> Analysis
    Mapping["Mapping profile"] --> Analysis

    Analysis --> Readiness["Readiness report"]
    Readiness --> Execution["Resolve + reduce method execution"]
    Execution --> Validation["Validation report"]
    Validation --> Acceptance["Acceptance report + selection sets"]
    Acceptance --> MTDA[".mtda archive"]

    MTDA --> TestReport["Test report"]
    MTDA --> AuditReport["Audit report"]
    MTDA --> Workbench["Method Development Workbench"]
```

## L1 — Major chunks

```mermaid
flowchart TB
    subgraph MTDP["Aggregation [MTDP]"]
        A1["Input discovery"] --> A2["Parsing"]
        A2 --> A3["Schema inference"]
        A3 --> A4["Grouping proposal"]
        A4 --> A5["Operator enrichment / evidence review"]
        A5 --> A6["Validation"]
        A6 --> A7["Package writing"]
    end

    subgraph MTDA["Analysis [MTDA]"]
        B1["Package selection"] --> B2["Method selection"]
        B2 --> B3["Mapping resolution"]
        B3 --> B4["Readiness check"]
        B4 --> B5["Method execution"]
        B5 --> B6["Validation + acceptance"]
        B6 --> B7["Archive/report writing"]
        B7 --> B8["Review/finalize"]
    end

    A7 --> Package[".mtdp"]
    Package --> B1
    B8 --> Archive[".mtda"]
```

## Current architectural reading

The launcher has correctly separated the two working chunks:

- **Dataset** opens the MTDP package preparation interface.
- **Analysis** opens the method run wizard.
- **Method** is structurally present but disabled, which indicates the future place for method-definition workflows without forcing them into the Dataset or Analysis screens.

This is important because it preserves a clean future split between:

1. Data aggregation and packaging.
2. Method definition or editing.
3. Method execution and reporting.

## Known coverage limits

This overview does not yet fully document:

- The parser internals under `parsing.parsers`.
- The operation registry and individual operation implementations.
- The full method package YAML structure.
- The report builder internals.
- The validation and acceptance policy internals.
- The finalization amendment service internals.

Those should be added as scoped drill-downs rather than expanding this overview into a large unreadable diagram.
