from __future__ import annotations

import pytest


def test_unit_normaliser_converts_force_and_rejects_bad_dimensions():
    from mtdp_enrichment.units import UnitNormaliser, UnitValidationError

    normaliser = UnitNormaliser(prefer_pint=False)
    result = normaliser.convert(value=50, from_unit="kN", to_unit="N", dimension="force")

    assert result.canonical_value == 50000
    assert result.factor == 1000
    assert result.dimension == "force"

    with pytest.raises(UnitValidationError):
        normaliser.convert(value=50, from_unit="kN", to_unit="mm", dimension="force")


def test_unit_normaliser_handles_aliases_without_package_schema_helpers():
    from mtdp_enrichment.units import default_unit_normaliser

    assert default_unit_normaliser.normalize_unit_text("(kn)") == "kN"
    assert default_unit_normaliser.normalize_unit_text("mm_min") == "mm/min"
    assert default_unit_normaliser.normalize_unit_text("microseconds") == "us"
    assert default_unit_normaliser.conversion_factor("cm", "mm", dimension="length") == 10
    assert default_unit_normaliser.conversion_factor("kN", "mm", dimension="force") is None
    assert default_unit_normaliser.conversion_factor("ms", "s", dimension="time") == 0.001
    assert default_unit_normaliser.conversion_factor("us", "s", dimension="time") == 0.000001


def test_field_unit_policy_resolver_uses_schema_dimensions():
    from mtdp_enrichment.schemas import SchemaRegistry
    from mtdp_enrichment.units import FieldUnitPolicyResolver

    schema = SchemaRegistry().get("mechanical.compression")
    width = schema.field_by_id("width")

    policy = FieldUnitPolicyResolver().resolve_field(schema, width)

    assert policy.dimension == "length"
    assert policy.standard_unit == "mm"
    assert set(policy.accepted_units) >= {"mm", "cm", "m"}


def test_data_table_rejects_duplicate_non_repeatable_family():
    from copy import copy

    from mtdp_enrichment.normalization import UnitNormalizer
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry

    parsed = ParserAdapter().parse("tests/data/Specimen_RawData_1.csv")
    duplicate = copy(parsed.channels.load_channels[0])
    parsed.channels.load_channels.append(duplicate)
    schema = SchemaRegistry().get("mechanical.compression")

    result = UnitNormalizer().normalize(parsed, schema)

    assert any(issue.code == "non_repeatable_table_channel" for issue in result.validation.errors)


def test_data_table_reports_missing_required_and_allows_repeatable_family():
    from mtdp_enrichment.normalization import UnitNormalizer
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry

    parsed = ParserAdapter().parse("tests/data/Specimen_RawData_1.csv")
    schema = SchemaRegistry().get("mechanical.compression")

    repeatable_result = UnitNormalizer().normalize(parsed, schema)
    assert not any(
        issue.code == "non_repeatable_table_channel" and issue.field == "strain"
        for issue in repeatable_result.validation.errors
    )

    missing = ParserAdapter().parse("tests/data/Specimen_RawData_1.csv")
    missing.channels.load_channels.clear()
    missing_result = UnitNormalizer().normalize(missing, schema)
    assert any(issue.code == "missing_table_channel" and issue.field == "load" for issue in missing_result.validation.errors)


def test_data_table_assumes_schema_standard_unit_when_table_unit_is_missing():
    from mtdp_enrichment.normalization import UnitNormalizer
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry

    parsed = ParserAdapter().parse("tests/data/Specimen_RawData_1.csv")
    time_channel = parsed.channels.time_channels[0]
    time_channel.original_unit_text = None
    time_channel.canonical_unit = None
    schema = SchemaRegistry().get("mechanical.compression")

    result = UnitNormalizer().normalize(parsed, schema)

    assert result.validation.ok
    assert any(issue.code == "assumed_table_unit" and issue.field == "Time" for issue in result.validation.warnings)
    normalized_time = next(column for column in result.columns if column.family == "time")
    assert normalized_time.unit == "s"


def test_bz_time_without_unit_does_not_block_table_normalization():
    from pathlib import Path

    from mtdp_enrichment.normalization import UnitNormalizer
    from mtdp_enrichment.parsing_gateway import ParserAdapter
    from mtdp_enrichment.schemas import SchemaRegistry

    source = Path("datasets/BZ_Compression_20250325/a10.csv")
    if not source.exists():
        pytest.skip("BZ sample dataset is not present in this checkout.")
    parsed = ParserAdapter().parse(source)
    schema = SchemaRegistry().get("mechanical.compression")

    result = UnitNormalizer().normalize(parsed, schema)

    assert result.validation.ok
    assert not any(issue.code == "unsupported_table_unit" and issue.field == "Time" for issue in result.validation.errors)
    assert any(issue.code == "assumed_table_unit" and issue.field == "Time" for issue in result.validation.warnings)
    normalized_time = next(column for column in result.columns if column.family == "time")
    assert normalized_time.unit == "s"


def test_active_modules_do_not_import_package_schema_unit_shims():
    from pathlib import Path

    root = Path("src/mtdp_enrichment")
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.as_posix().endswith("package/schema.py"):
            continue
        text = path.read_text(encoding="utf-8")
        if "from mtdp_enrichment.package.schema import normalize_unit_text" in text:
            offenders.append(path.as_posix())
        if "from mtdp_enrichment.package.schema import unit_conversion_factor" in text:
            offenders.append(path.as_posix())
    assert offenders == []
