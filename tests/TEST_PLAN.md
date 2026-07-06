# Stage 26 Test Plan

## 1. Operation evidence contract tests

Verify that relevant operations expose evidence contracts or equivalent metadata.

Target operations:

- experiment boundary resolution, if present
- mean compressive strain / mean absolute strain
- stress derivation
- max point / strength
- failure strain at max
- chord slope / modulus
- bending diagnostic / bending pattern
- curve-family aggregation, if present
- selection/final report run construction

Assertions:

- operation type has evidence role
- default audit fragment/view is present where relevant
- report role exists for formal report scalars
- workbench view link/type exists where relevant

## 2. Procedure evidence index tests

Run canonical method execution and assert MTDA contains:

- `audit/procedure_evidence_index.json`
- `audit/audit_block_index.json`

Assertions:

- each run has evidence entries for key reduce operations
- report-role outputs trace to operation results
- audit block memberships exist
- workbench refs exist where possible

## 3. Audit block grouping tests

Assert Audit Report / audit block index contains:

- per-run blocks
- stress-strain reduction block
- bending evidence block
- selection consequence block
- aggregate evidence block

Assertions:

- boundary/chord/max/failure evidence are grouped into stress-strain block
- bending is separate
- no one-plot-per-operation default bloat

## 4. Audit Report content tests

Assert `audit/audit_report.html` includes:

- audit overview
- per-run audit section
- at least one run stress-strain evidence block
- at least one bending evidence block
- aggregate evidence section
- final selection/override trace
- links to Test Report and Workbench

## 5. Wizard action page tests

Assert wizard page models expose actions rather than only passive state:

- package page has browse/reload/open metadata actions
- mapping page has edit/load/save mapping actions where supported
- readiness page has fix/continue/stop routing
- report metadata page has override actions
- acceptance page has keep/remove/restore reason actions
- output page has open/copy/finalization actions

## 6. Role boundary tests

Assert:

- Test Report remains formal result surface
- Audit Report is evidence surface
- Workbench remains operation-level surface
- Wizard does not duplicate full Audit Report content

## 7. Regression tests

Run current full suite.

Expected:

```text
python -m pytest -q
```

passes or documented residuals are recorded.
