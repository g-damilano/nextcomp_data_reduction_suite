# Test Specifications

## test_procedure_evidence_index.py

Assertions:

```text
- canonical run produces audit/procedure_evidence_index.json
- every run has entries for output-affecting operations
- each indexed step has operation_type, default_audit_block, default_audit_view, workbench_view, evidence_refs
- formal report values have report_roles
```

## test_grouped_audit_blocks.py

Assertions:

```text
- audit/audit_blocks.json exists
- each run has run_identity_and_status
- each run has run_stress_strain_reduction
- each run has run_bending_evidence
- stress-strain block collects boundary, mean strain/stress, max, failure strain, chord evidence
- bending block collects threshold/window/segments/classification evidence
- aggregate blocks exist after run blocks
```

## test_stage26_audit_report_structure.py

Assertions:

```text
- audit report html exists
- audit overview appears first
- run-wise packet section appears before aggregate packet section
- run section contains stress-strain reduction evidence heading
- run section contains bending evidence heading
- aggregate section contains final run-set or aggregate curve/statistics evidence
```

## test_stage26_wizard_action_contracts.py

Assertions:

```text
- all wizard pages have contracts
- every contract has a primary action
- readiness page has repair actions
- acceptance page has keep/remove/restore actions
- output page has open Test Report, open Audit Report, open Workbench actions
```

## test_stage26_surface_role_separation.py

Assertions:

```text
- Test Report does not contain the full run-wise audit packet structure
- Audit Report links to Test Report and Workbench
- Workbench link/action remains available
- surface_manifest classifies surfaces separately
```
