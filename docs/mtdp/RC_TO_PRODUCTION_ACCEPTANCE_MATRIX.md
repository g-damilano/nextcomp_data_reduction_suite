# RC To Production Acceptance Matrix

| Gate | Implemented Contract |
| --- | --- |
| P0 validity semantics | Boolean/numeric validity maps to `validity`; `failure_mode` is failure detail only. |
| Compatibility shims | `package.schema` unit helpers are labelled wrappers; active code uses `UnitNormaliser`. |
| Backend/frontend separation | `services/` owns group load, reprocess, validation, export, YAML, and supplemental workflows. |
| Migration | `MTDPMigrator` supports registered plans, automatic operations, review state, and migration provenance. |
| Structured aliases | Flat and structured alias forms load into alias entries with kind/confidence. |
| Empirical YAML matching | Deterministic matcher proposes non-LLM mappings and keeps weak matches review-only. |
| Provenance taxonomy | Event constants and helpers define stable names and minimum event fields. |
| Future hooks | Extension points document owner module, current status, future contract, and non-scope boundary. |
| Documentation | Current architecture, schema guidelines, unit system, YAML reconciliation, reprocessing, migration, provenance, and extension docs describe active behavior. |
| Release checks | Full tests plus static searches must pass before production-ready verdict. |

Production-ready means all gates pass with the intended `modulus-gui` environment.
