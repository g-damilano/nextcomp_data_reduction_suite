# Modular Plotting Architecture

The plotting package owns reusable plot generation for report, audit, workbench,
export, and future wizard surfaces. Evidence-producing operations and methods
provide structured data; this package converts that data into validated
Vega-Lite specifications with semantic layers, theme defaults, quality checks,
and fallback messages.

Current responsibilities:

- `models.py` defines plot requests, results, themes, layer contracts, and
  future customisation profiles.
- `registry.py` maps `plot_type` values to builders.
- `vega_lite.py` applies common Vega-Lite defaults and returns `PlotResult`.
- `quality.py` performs deterministic JSON-level quality checks.
- `labels.py` and `units.py` keep visible labels and units out of individual
  plot builders.
- `evidence_adapters.py` converts existing surface evidence blocks into
  `PlotRequest` objects.
- `plots/` contains method-independent builders for current plot types.

The `PlotCustomizationProfile` is an architectural seam for a later plot
customisation/export add-on. It is intentionally not exposed in the GUI in this
stage.

Deferred:

- advanced force-directed label placement;
- GUI plot customisation;
- print/PDF/DOCX rendering profiles;
- exhaustive migration of every historical helper plot.
