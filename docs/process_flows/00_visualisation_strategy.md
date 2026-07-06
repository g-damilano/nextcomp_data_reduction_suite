# Visualisation Strategy for Process Flow Documentation

## Purpose

The compression module needs a durable way to describe how the software behaves: what enters a workflow, which gates are crossed, what decisions branch the route, what artifacts are produced, and which code units own each responsibility.

Mermaid is a good baseline, but it should not be the only visual language used forever. Different questions require different representations.

## Recommended baseline: Mermaid

Mermaid should remain the default process-flow language for this repository because it is:

- Markdown-native and easy to review in GitHub.
- Version-control friendly.
- Quick to edit during design discussions.
- Good for layered flowcharts, sequence diagrams, state diagrams, and entity relationships.
- Good enough for most workflow, artifact, and decision-flow documentation.

Mermaid should be used for:

| Scope | Mermaid diagram type | Why |
|---|---|---|
| Process overview | `flowchart` | Shows main steps, branches, and archive handoff. |
| Wizard states | `stateDiagram-v2` | Shows SETUP/RUNNING/REVIEW/FINALIZE transitions. |
| UI-to-service calls | `sequenceDiagram` | Shows signal/controller/service/worker interactions. |
| Archive structure | `flowchart` or `mindmap` | Shows output artifacts and their grouping. |
| Data model relationships | `erDiagram` or `classDiagram` | Shows package/result/report object relationships. |
| Roadmap dependency | `flowchart` | Shows which flows depend on which modules. |

## Mermaid limitations

Mermaid is not ideal for every job. It becomes less effective when:

- The flow is very large and needs collapsible drill-down navigation.
- Spatial grouping matters more than directed arrows.
- The question is about timing, concurrency, or UI layout rather than process order.
- The diagram needs rich annotations, screenshots, or side-by-side design alternatives.
- The audience needs a polished visual for presentation rather than editable engineering documentation.

## Alternative visualisation modes

### 1. PlantUML

Use PlantUML when the documentation needs stronger software-engineering diagrams, especially:

- Detailed class diagrams.
- Component diagrams.
- Package/module dependency diagrams.
- More formal sequence diagrams.

Trade-off: better expressiveness, but less GitHub-native and less lightweight than Mermaid.

### 2. Graphviz / DOT

Use DOT when the graph is dense and auto-layout matters more than hand-written readability.

Good for:

- Large dependency graphs.
- Import/module relationships.
- Operation registry maps.
- Archive-member provenance graphs.

Trade-off: powerful for generated graphs, less comfortable for manual documentation.

### 3. C4 model diagrams

Use C4-style diagrams for architecture communication:

- Context diagram: user, app, archives, external file system.
- Container diagram: UI, service layer, parser, method engine, archive writer.
- Component diagram: internal classes and services.
- Code-level diagram: selected critical implementation units.

C4 can be written in Mermaid, PlantUML, or plain structured Markdown. The value is the abstraction discipline, not the syntax.

### 4. BPMN-style process tables

Use BPMN-like tables when the key issue is governance, ownership, gate logic, or compliance rather than visual arrows.

Good for:

- ISO/reporting gates.
- Human decision points.
- Validation and acceptance workflows.
- Auditability requirements.

Recommended table columns:

| Step | Actor | Input | Action | Gate/decision | Output | Failure mode | Code anchor |
|---|---|---|---|---|---|---|---|

### 5. Data-contract matrices

Use matrices when the key question is whether a value is preserved, transformed, validated, or routed correctly.

Good for:

- Parser output to MTDP normalized CSV.
- MTDP package fields to readiness requirements.
- Mapping roles to method inputs.
- Method result fields to test report/audit report/workbench.

Recommended table columns:

| Source | Internal role | Transformation | Validation | Destination | Missing/ambiguous behaviour | Code anchor |
|---|---|---|---|---|---|---|

### 6. Archive tree maps

Use explicit archive trees when the concern is package structure.

Good for:

- `.mtdp` archive contents.
- `.mtda` archive contents.
- Report surface relationships.
- Backward-compatible vs recommended archive layouts.

Example:

```text
mtda/
  report/
    test_report.html
    test_report.json
  audit/
    audit_report.html
    procedure_evidence_index.json
  workbench/
    index.html
```

### 7. UI journey maps

Use journey maps when the issue is operator experience rather than backend processing.

Good for:

- Dataset packaging interface.
- Method wizard setup path.
- Review/finalize experience.
- Error recovery paths.

Recommended table columns:

| Screen/state | Operator sees | Operator action | System response | Error/recovery branch | Backend anchor |
|---|---|---|---|---|---|

## Recommended documentation pattern

For each substantial workflow, use a paired structure:

1. **Mermaid process diagram** for the route.
2. **Responsibility table** for code anchors and ownership.
3. **Data/artifact contract** if values cross an archive or method boundary.
4. **Known gaps** for unverified branches or missing drill-downs.

This avoids the weakness of diagrams that look clear but do not prove that every branch, artifact, and validation gate is covered.

## Decision rule

Use Mermaid first unless the question is specifically about:

- Module dependency density → use Graphviz/DOT or generated dependency tables.
- Formal software architecture → use C4 and/or PlantUML.
- Compliance/gate ownership → use BPMN-style tables.
- Field/value preservation → use data-contract matrices.
- Archive contents → use archive tree maps.
- Operator experience → use UI journey maps.

## Practical recommendation for this repository

The best long-term approach is not to replace Mermaid. It is to use Mermaid as the backbone and add complementary tabular/contract representations wherever a flow crosses a critical boundary.

Critical boundaries for this project:

1. Raw parser output → MTDP internal run model.
2. MTDP enriched state → `.mtdp` archive.
3. `.mtdp` archive → analysis package input model.
4. Method input declarations + mapping → readiness result.
5. Resolve/reduce recipes → method result.
6. Method result → validation/acceptance/report outputs.
7. Method result → `.mtda` archive.
8. MTDA draft → finalized MTDA.
