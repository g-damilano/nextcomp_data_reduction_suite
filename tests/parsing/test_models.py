from pathlib import Path

from parsing.models import (
    ChannelBundle,
    ChannelRecord,
    ColumnDescriptor,
    FileSniffResult,
    ParsedSampleRecord,
    PreambleToken,
    TableLayoutRecord,
)
from parsing.inspection import to_standard_data_structure


def test_channel_bundle_all_channels_collects_all_families() -> None:
    descriptor = ColumnDescriptor(
        column_index=0,
        original_name='Load',
        original_unit_text='(kN)',
        family='load',
        ordinal=1,
        canonical_name='load_1',
    )
    record = ChannelRecord(
        descriptor=descriptor,
        values=[1.0, 2.0],
        source_column_index=0,
        non_null_count=2,
        null_count=0,
    )
    bundle = ChannelBundle(load_channels=[record])
    assert bundle.all_channels() == [record]


def test_parsed_sample_record_metadata_lookup_returns_matching_value() -> None:
    sniff = FileSniffResult(
        file_path=Path('example.csv'),
        delimiter=',',
        encoding='utf-8',
        has_preamble=True,
        likely_header_row_index=5,
        total_lines=20,
    )
    token = PreambleToken(
        source_line_index=0,
        raw_key='Specimen name',
        raw_value='A1',
        raw_unit=None,
        normalized_key='sample_id',
        coerced_value_text='A1',
    )
    layout = TableLayoutRecord(
        header_row_index=5,
        units_row_index=6,
        data_start_row_index=7,
        detected_column_count=5,
    )
    parsed = ParsedSampleRecord(
        source_file=Path('example.csv'),
        sample_id='A1',
        file_sniff=sniff,
        preamble_tokens=[token],
        table_layout=layout,
        channels=ChannelBundle(),
        raw_header=('Load',),
        raw_units_row=('(kN)',),
    )
    assert parsed.get_metadata_value('sample_id') == 'A1'


def test_to_standard_data_structure_preserves_model_fields() -> None:
    descriptor = ColumnDescriptor(
        column_index=0,
        original_name='Load',
        original_unit_text='(kN)',
        family='load',
        ordinal=1,
        canonical_name='load_1',
        source_notes=('classified from header',),
    )
    channel = ChannelRecord(
        descriptor=descriptor,
        values=[1.0, None],
        source_column_index=0,
        non_null_count=1,
        null_count=1,
        canonical_unit='N',
    )
    sniff = FileSniffResult(
        file_path=Path('example.csv'),
        delimiter=',',
        encoding='utf-8',
        has_preamble=False,
        likely_header_row_index=0,
        total_lines=3,
    )
    layout = TableLayoutRecord(
        header_row_index=0,
        units_row_index=1,
        data_start_row_index=2,
        detected_column_count=1,
    )
    parsed = ParsedSampleRecord(
        source_file=Path('example.csv'),
        sample_id='A1',
        file_sniff=sniff,
        preamble_tokens=[],
        table_layout=layout,
        channels=ChannelBundle(load_channels=[channel]),
        raw_header=('Load',),
        raw_units_row=('(kN)',),
    )

    plain = to_standard_data_structure(parsed)

    assert plain['source_file'] == 'example.csv'
    assert plain['file_sniff']['delimiter'] == ','
    assert plain['raw_header'] == ['Load']
    assert plain['channels']['load_channels'][0]['descriptor']['canonical_name'] == 'load_1'
    assert plain['channels']['load_channels'][0]['values'] == [1.0, None]
    assert plain['channels']['load_channels'][0]['descriptor']['source_notes'] == [
        'classified from header'
    ]
