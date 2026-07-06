# Processing Layer Handoff Contract

The MTDP Normalisation Foundation v1.0 release provides the upstream input contract for future method-specific processing.

## Downstream May Assume

- The `.mtdp` package validates with `MTDPPackageValidator`.
- `manifest.json` provides schema ID and schema version.
- `schema.json` embeds the canonical schema contract.
- `dataset.json` contains dataset/group-level fields and `run_order`.
- Each run has preserved raw data and one normalized run CSV.
- Run-level metrology and analysis inputs are available through token preambles.
- Acquisition provenance is available in `provenance.json`.
- Unit normalization has been applied according to schema and recorded where conversions occurred.
- Canonical `validity` status is available when supplied by schema/UI/YAML.
- Checksums are available for integrity verification.

## Downstream May Not Assume

- All mechanical test modes are equally mature.
- Image metrology has run.
- All legacy packages migrate without user review.
- Optional supplemental files or images exist.
- Compression/tensile/flexural property calculations already exist.
- Report generation exists.

## Likely Input API

Future processing should use a reader/service boundary, for example:

```python
from mtdp_enrichment.services import GroupLoader

group = GroupLoader().load_package("sample_group.mtdp")
```

or a future `ProcessingInput` adapter built on top of `MTDPPackageReader`/`GroupLoader`.

No method-specific processing algorithms are implemented as part of v1.0 normalisation foundation.
