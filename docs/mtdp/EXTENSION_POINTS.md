# Extension Points

This document distinguishes current production hooks from future work.

## Processing Pipeline Hook

Owner module: future processing pipeline.

Current status: input contract is a validated `.mtdp` group package. The enrichment tool does not calculate downstream reduced mechanical properties.

Future contract: consume validated group packages and write method-specific processed results with provenance.

## Image Metrology Hook

Owner modules: `mtdp_enrichment.image_gateway` and disabled UI buttons in the image evidence dialog.

Current status: images are preserved as evidence and future-analysis inputs. Buttons for image metrology are visible but disabled.

Future contract: external image/metrology module proposes measurements; UI displays proposals; user confirms; provenance records `image_metrology`.

## Schema Migration Hook

Owner modules: `mtdp_enrichment.package.migrator` and schema-library `migrations/`.

Current status: automatic/semi-automatic migration plans are implemented for registered paths. Ambiguous operations produce review state.

Future contract: add operation handlers only when tests and migration provenance exist.

## New Test Type Hook

Owner modules: `schema_library`, `schemas.registry`, `parsing_gateway`, and tests.

Current status: new mechanical modes are added by schema plus parser inference and validation tests.

Future contract: no UI parser shortcuts; parser boundary remains delegated.

## Empirical YAML Matching Hook

Owner module: `mtdp_enrichment.enrichment_import.empirical_matcher`.

Current status: deterministic non-LLM matching proposes mappings using aliases, key similarity, units, values, profiles, and roles.

Future contract: add evidence sources only if weak matches remain user-reviewable.

## Unit Backend Hook

Owner module: `mtdp_enrichment.units`.

Current status: project code calls `UnitNormaliser`; Pint may be used only behind the backend wrapper.

Future contract: Pint, unyt, or custom backends can be swapped without package/UI/YAML code calling them directly.
