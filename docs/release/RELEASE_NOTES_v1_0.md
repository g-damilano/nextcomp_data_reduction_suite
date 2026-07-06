# Release Notes: MTDP Normalisation Foundation v1.0

## What This Release Is

MTDP Normalisation Foundation v1.0 is a stable upstream data-normalisation, curation, and packaging foundation for mechanical-test datasets.

It supports:

- schema-driven enrichment
- deterministic sample group construction
- supplemental YAML import and reconciliation
- optional image and supplemental evidence preservation
- unit normalization through the MTDP unit layer
- `.mtdp` package writing, validation, reopening, and reprocessing

## Stable Contract

- Stable target schema: `mechanical.compression@0.2.0`
- Package format: `.mtdp`
- Manifest format version: `0.2.0`
- Software release version: `1.0.0`

## Not In Scope

- method-specific compression/tensile/flexural property calculations
- image metrology execution
- report generation

## Migration Support

Registered migration:

```text
mechanical.compression@0.1.0 -> mechanical.compression@0.2.0
```

Ambiguous migration steps produce review state and require user-confirmed values.

## How To Run

Source release command:

```powershell
$env:PYTHONPATH='src'
conda run -n modulus-gui mtdp-enrichment
```

Automated tests:

```powershell
$env:PYTHONPATH='src'
conda run -n modulus-gui python -m pytest -q
```

## How To Validate A Package

Use `MTDPPackageValidator`:

```python
from mtdp_enrichment.package import MTDPPackageValidator

result = MTDPPackageValidator().validate("sample_group.mtdp")
assert result.ok, result.messages()
```

## Distribution Mode

v1.0 is a source-first release. `pyproject.toml` includes package data for schemas and UI assets. No executable build artifact is declared as the official v1.0 release artifact in this repository snapshot.

## Known Limitations

- Image metrology buttons are future hooks and remain disabled.
- Internal UI implementation names still include `Bundle*`; user-facing terminology is `group`.
- Manual smoke testing must be completed by a human operator before tagging.

## Test Evidence

See `docs/release/TEST_EVIDENCE_v1_0.md`.
