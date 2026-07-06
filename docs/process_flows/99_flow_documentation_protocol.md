# Process Flow Documentation Protocol

## Purpose

This protocol defines how the process-flow documentation should be maintained as the compression module evolves.

The aim is to keep a code-anchored map of how the software works so future implementation directives can target the correct workflow, gate, artifact, or code boundary.

## Core rules

1. Document current behaviour before target behaviour.
2. Keep MTDP aggregation and MTDA analysis separated unless the diagram is explicitly showing the archive handoff.
3. Prefer layered drill-downs over one oversized diagram.
4. Every process flow must include code anchors.
5. Every process flow must identify its output artifacts or state changes.
6. Every process flow must list known missing drill-downs or state that its scope is complete.
7. Operator decisions must be separated from automated gates.
8. Validation, readiness, acceptance, and finalization must not be collapsed into a single generic review step.

## Granularity ladder

| Level | Name | Meaning |
|---|---|---|
| L0 | System overview | Whole application and archive lifecycle. |
| L1 | Chunk overview | MTDP or MTDA as a broad process. |
| L2 | Scoped flow | One coherent process lane. |
| L3 | Decision drill-down | Branches, gates, error paths, operator choices. |
| L4 | Data or artifact contract | Archive members, field matrices, validation obligations. |
| L5 | Code-anchor map | Exact class, function, and test ownership. |

## Required sections for each flow file

Each flow file should contain:

1. Scope.
2. Source anchors.
3. One or more diagrams or justified alternative representations.
4. Plain-language flow reading.
5. Data or artifact contract where relevant.
6. Known missing drill-downs.

## Update triggers

Update this documentation when any of these change:

1. Archive members are added, removed, renamed, or moved.
2. A wizard state, UI route, or action-bar decision changes.
3. Parser behaviour changes in a way that affects structured parsed records.
4. MTDP grouping, validation, enrichment, or export rules change.
5. Method input declarations, mapping logic, or readiness rules change.
6. Resolve or reduce recipes change.
7. Operation outputs or operation diagnostics change.
8. Validation or acceptance policy changes.
9. Report, audit, or workbench surfaces change.
10. Finalization or amendment behaviour changes.
11. A bug reveals an undocumented process branch.

## Review checklist

Before accepting a process-flow documentation update, verify that:

- The documented behaviour matches implementation.
- The code anchors are explicit.
- The diagram is not hiding major branches.
- Error, blocked, cancelled, and warning routes are represented where important.
- Archive outputs and data products are named.
- The MTDP and MTDA responsibilities remain distinct.
- The diagram has a clear level of granularity.
- Missing drill-downs are listed.

## Relationship to development directives

The process-flow docs should become the reference base for future implementation prompts.

A strong directive should identify:

1. The documented flow being changed.
2. The current mismatch.
3. The target route.
4. The files/classes/functions expected to change.
5. The tests or output artifacts that prove the change.

The intended maintenance loop is:

1. Document current process.
2. Identify mismatch against the desired process.
3. Write a precise implementation directive.
4. Modify code.
5. Add or update tests.
6. Update process-flow documentation.
