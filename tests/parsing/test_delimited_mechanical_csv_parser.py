from __future__ import annotations

import json
from pathlib import Path

import pytest

from parsing.inspection import build_parser_inspection_report
from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_parser_imports_preamble_channels_and_validity_hint():
    record = DelimitedMechanicalCsvParser(FIXTURE).parse()

    assert record.sample_id == "CAG-CF-ER-Comp-E1"
    assert record.validity_hint is True
    assert record.get_metadata_value("width") == "9.80000"
    assert record.get_metadata_value("thickness") == "2.30000"

    assert [ch.descriptor.canonical_name for ch in record.channels.load_channels] == ["load_1"]
    assert [ch.descriptor.canonical_name for ch in record.channels.extension_channels] == ["extension_1"]
    assert [ch.descriptor.canonical_name for ch in record.channels.strain_channels] == ["strain_1", "strain_2"]
    assert [ch.descriptor.alias for ch in record.channels.strain_channels] == ["front", "rear"]
    assert [ch.descriptor.canonical_name for ch in record.channels.time_channels] == ["time_1"]

    assert record.channels.load_channels[0].values[1] == 100.0
    assert record.channels.strain_channels[0].values[1] == pytest.approx(100e-6)


def test_parser_inspection_report_returns_header_flags_and_head_tail():
    record = DelimitedMechanicalCsvParser(FIXTURE).parse()
    report = build_parser_inspection_report(record, head=2, tail=2)

    assert report["sample_id"] == "CAG-CF-ER-Comp-E1"
    assert report["validity_hint"] is True
    assert report["header_flags"]["failure_mode"]["value"] == "Valid"
    assert report["header_flags"]["width"]["unit"] == "mm"
    # Row indexes are zero-based physical line indexes in the source file.
    assert report["layout"]["data_start_row_index"] == 7

    channel_names = [item["canonical_name"] for item in report["channel_flags"]]
    assert channel_names == ["load_1", "extension_1", "strain_1", "strain_2", "time_1"]

    assert report["row_count"] == 7
    assert len(report["data_head"]) == 2
    assert len(report["data_tail"]) == 2
    assert report["data_head"][0]["load_1"] == 0.0
    assert report["data_tail"][-1]["load_1"] == 600.0

    # Demonstrates that the report is directly JSON-serialisable for debugging handoff.
    json.dumps(report)


def test_parser_accepts_logger_headers_with_embedded_units(tmp_path: Path):
    path = tmp_path / "logger.csv"
    path.write_text(
        "\n".join(
            [
                "Scan #,Time,Uniaxial Gage 1 on S1-Ch2 microstrain,Uniaxial Gage 2 on S1-Ch1 microstrain,Load on S1-Ch3 kN",
                "11,1100000,-2,1,0.0010",
                "12,1200000,-4,3,0.0020",
            ]
        ),
        encoding="utf-8",
    )

    record = DelimitedMechanicalCsvParser(path).parse()

    assert record.table_layout.header_row_index == 0
    assert record.raw_units_row is None
    assert record.channels.load_channels[0].original_unit_text == "kN"
    assert record.channels.load_channels[0].canonical_unit == "N"
    assert record.channels.load_channels[0].values == pytest.approx([1.0, 2.0])
    assert [channel.descriptor.alias for channel in record.channels.strain_channels] == ["gage_1", "gage_2"]
    assert record.channels.strain_channels[0].values == pytest.approx([-2e-6, -4e-6])
    assert [channel.descriptor.family for channel in record.channels.unknown_channels] == ["record_id"]


def test_parser_accepts_german_lis_table_with_plain_unit_row(tmp_path: Path):
    path = tmp_path / "tensile_d_01.lis.txt"
    path.write_text(
        "\n".join(
            [
                "BAM 5.2 *ZUG01-V03* VH5204_D_01.lis",
                "[Daten]",
                "Zeit\tWeg\tKraft\tDehnung\tSpannung",
                "sec\tmm\tkN\t%\tMPa",
                "0\t0\t0,10022628\t0,00887073588681103\t5,10239169169679",
                "0,05\t0,001\t0,2\t0,01\t6,5",
            ]
        ),
        encoding="cp1252",
    )

    record = DelimitedMechanicalCsvParser(path).parse()

    assert record.file_sniff.delimiter == "\t"
    assert record.table_layout.header_row_index == 2
    assert record.table_layout.units_row_index == 3
    assert record.channels.time_channels[0].values == pytest.approx([0.0, 0.05])
    assert record.channels.load_channels[0].values == pytest.approx([100.22628, 200.0])
    assert record.channels.strain_channels[0].values == pytest.approx(
        [0.0000887073588681103, 0.0001]
    )
    assert record.channels.stress_channels[0].values == pytest.approx([5.10239169169679, 6.5])


def test_parser_accepts_whitespace_data_rows_after_tab_header(tmp_path: Path):
    path = tmp_path / "wood_raw.txt"
    path.write_text(
        "\n".join(
            [
                "Time (S)\tLoad (kN)\tStroke (mm)\tExtensom (in)",
                "  0.00000   0.48976  -0.04456  -0.00646",
                "  0.50000   0.50676  -0.04202  -0.00640",
            ]
        ),
        encoding="utf-8",
    )

    record = DelimitedMechanicalCsvParser(path).parse()

    assert record.file_sniff.delimiter == "\t"
    assert record.channels.time_channels[0].values == pytest.approx([0.0, 0.5])
    assert record.channels.load_channels[0].values == pytest.approx([489.76, 506.76])
    assert [channel.descriptor.original_name for channel in record.channels.displacement_channels] == [
        "Stroke (mm)",
    ]
    assert [channel.descriptor.original_name for channel in record.channels.extension_channels] == [
        "Extensom (in)",
    ]
    assert record.channels.extension_channels[0].canonical_unit == "mm"
    assert record.channels.extension_channels[0].values == pytest.approx(
        [-0.164084, -0.16256]
    )


def test_parser_retains_non_numeric_cells_as_nulls(tmp_path: Path):
    path = tmp_path / "sentinels.csv"
    path.write_text(
        "\n".join(
            [
                "Load,Extension,Front Strain,Rear Strain,Time",
                "(kN),(mm),(usn),(usn),(s)",
                "0,0,0,0,0",
                "1,Overflow,NaN,Inf,1",
            ]
        ),
        encoding="utf-8",
    )

    record = DelimitedMechanicalCsvParser(path).parse()
    report = build_parser_inspection_report(record, head=2, tail=0)

    assert record.channels.load_channels[0].values == pytest.approx([0.0, 1000.0])
    assert record.channels.extension_channels[0].values == [0.0, None]
    assert record.channels.extension_channels[0].null_count == 1
    assert record.channels.strain_channels[0].values == [0.0, None]
    assert record.channels.strain_channels[1].values == [0.0, None]
    assert record.channels.strain_channels[0].notes == (
        "1 missing or unparseable numeric cell(s) retained as None.",
    )
    assert record.channels.extension_channels[0].bad_cells[0].source_row_index == 3
    assert record.channels.extension_channels[0].bad_cells[0].data_row_index == 1
    assert record.channels.extension_channels[0].bad_cells[0].source_column_index == 1
    assert record.channels.extension_channels[0].bad_cells[0].raw_value == "Overflow"
    assert record.channels.extension_channels[0].bad_cells[0].reason == "text_in_numeric_column"
    assert record.channels.extension_channels[0].bad_cells[0].diagnostic_code == "text_in_numeric_column"
    assert record.channels.strain_channels[0].bad_cells[0].reason == "text_in_numeric_column"
    assert record.channels.strain_channels[1].bad_cells[0].reason == "text_in_numeric_column"
    extension_flag = next(
        item for item in report["channel_flags"] if item["canonical_name"] == "extension_1"
    )
    assert extension_flag["null_count"] == 1
    assert extension_flag["notes"] == ["1 missing or unparseable numeric cell(s) retained as None."]
    assert extension_flag["bad_cells"] == [
        {
            "source_row_index": 3,
            "data_row_index": 1,
            "source_column_index": 1,
            "raw_value": "Overflow",
            "reason": "text_in_numeric_column",
            "diagnostic_code": "text_in_numeric_column",
            "severity": "error",
            "parse_rule_id": "numeric.plain_dot_decimal",
            "detected_decimal_separator": ".",
            "detected_thousands_separator": None,
        }
    ]
