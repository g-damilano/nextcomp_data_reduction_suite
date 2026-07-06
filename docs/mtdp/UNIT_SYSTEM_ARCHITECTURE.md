# Unit System Architecture

The MTDP unit layer owns the application unit contract. It may use Pint internally, but application code calls MTDP services only.

## Modules

```text
src/mtdp_enrichment/units/
  aliases.py
  dimensions.py
  systems.py
  normaliser.py
  pint_backend.py
  validation.py
```

## API

Use `UnitNormaliser` for conversion:

```python
result = unit_normaliser.convert(
    value=50,
    from_unit="kN",
    to_unit="N",
    dimension="force",
)
```

Use `FieldUnitPolicyResolver` to resolve field or table-column policy from schema declarations.

Resolution order:

1. field or table `standard_unit`
2. schema unit-system dimension default
3. global fallback mechanical metric system

## Integration Points

The same unit layer is used by:

- schema linting
- schema field coercion
- YAML reconciliation unit handling
- YAML key-unit inference
- data-table normalization
- provenance conversion records
- package validation

Invalid dimensional conversions return no factor or raise `UnitValidationError`; they are not silently coerced.

## Compatibility Shims

Older code may still import `normalize_unit_text` or `unit_conversion_factor` from `mtdp_enrichment.package.schema`. Those functions are compatibility wrappers only and delegate to `UnitNormaliser`.

New unit-aware code must call `mtdp_enrichment.units.UnitNormaliser` or `FieldUnitPolicyResolver` directly. Conversion logic must not be added to the compatibility wrappers or to package/UI/YAML modules.
