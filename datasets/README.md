# Dataset fixtures

This folder contains small raw and MTDP fixtures used by smoke tests and
examples. Bulky generated MTDA archives and extracted `_workbench` folders are
not shipped in the public release copy.

Included fixture groups:

- `Compression/`: raw CAG-CF compression CSV/YAML files plus a small MTDP
  package used by UI and report-surface tests.
- `Packed/`: compact canonical CAG-CF MTDP package used by method-run
  regression tests.
- `BZ_Compression_20250325/`: raw BZ CSV files and MTDP package used by
  boundary-resolution regression tests.

Generated `.mtda` archives should be produced locally by running Method
Analysis. They are intentionally ignored by version control.
