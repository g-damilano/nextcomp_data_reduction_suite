# Stage 26 Acceptance Matrix

| Requirement | Verification |
|---|---|
| Every output-affecting operation has evidence contract | Unit test scans operation registry/contracts |
| MTDA writes procedure evidence index | Canonical method run creates `audit/procedure_evidence_index.json` |
| MTDA writes grouped audit blocks | Canonical method run creates `audit/audit_blocks.json` |
| Audit Report is run-wise first | HTML/order test checks run sections before aggregate section |
| Stress-strain block is grouped | `audit_blocks.json` has `run_stress_strain_reduction` collecting boundary, stress, max, failure strain, chord operations |
| Bending block is separate | `audit_blocks.json` has `run_bending_evidence` with bending diagnostics/classification |
| Test Report is formal-result only | HTML/content test confirms no run-wise audit packet duplication |
| Wizard pages have action contracts | Test checks every page contract has purpose, decision, primary action |
| Output page exposes separate surfaces | View model test checks Test Report, Audit Report, Workbench actions |
| Surface manifest updated | `surface_manifest.json` references new audit surfaces |
| Full suite passes | `python -m pytest -q` |
