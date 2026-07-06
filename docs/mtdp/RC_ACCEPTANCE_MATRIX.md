# RC Acceptance Matrix

| Area | RC Requirement | Verification |
| --- | --- | --- |
| Parser contract | Parser tests pass; row-index semantics documented | `tests/parsing`, `docs/mtdp/PARSER_CONTRACT.md` |
| File-backed schemas | Bundled schemas load from YAML and old versions remain selectable | `tests/mtdp/test_mtdp_package.py` |
| Schema linter | Invalid schema contracts are rejected before registry use | `tests/mtdp/test_schema_linter.py` |
| Unit layer | Conversion goes through `UnitNormaliser` and dimensional errors are rejected | `tests/mtdp/test_units.py` |
| Data table rules | Required channels and non-repeatable channels are enforced | `tests/mtdp/test_units.py` |
| Group terminology | User-facing UI labels use group terminology | UI smoke tests and source review |
| Multi-run packages | Groups export to one package with parallel raw/normalized run files | `tests/mtdp/test_mtdp_package.py` |
| Supplemental files | Supplemental files are packaged, checksummed, and recorded in provenance | `tests/mtdp/test_supplemental_files.py` |
| Image evidence | Image evidence is optional, packaged, checksummed, and validated | `tests/mtdp/test_image_evidence.py` |
| YAML reconciliation | Dates, units, validity, aliases, mapping, and preview are supported | `tests/mtdp/test_yaml_reconciliation.py` |
| Reprocessing | Existing packages can be loaded and revised as editable group state | `tests/mtdp/test_group_reprocess.py` |
| Provenance | Imports, conversions, grouping, removals, images, and supplemental records are captured | package tests |
| About dialog | Email, acknowledgement, backend, package format, and logo are shown | `tests/mtdp/test_about_dialog.py` |
| Documentation | Current architecture, schema, unit, parser, and reprocessing docs exist | `docs/mtdp/` |

Current regression command:

```powershell
$env:PYTHONPATH='src'
& "$env:USERPROFILE\anaconda3\Scripts\conda.exe" run -n modulus-gui python -m pytest -q
```
