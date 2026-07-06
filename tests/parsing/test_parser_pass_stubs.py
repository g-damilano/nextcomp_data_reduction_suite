from __future__ import annotations

from pathlib import Path

from parsing.columns.column_descriptor_builder import ColumnClassificationPass
from parsing.layout.table_layout_detector import TableLayoutDetectionPass
from parsing.preamble.token_extractor import PreambleExtractionPass
from parsing.readers.delimited_numeric_reader import NumericIngestionPass
from parsing.sniffing.file_sniffer import FileSniffPass


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_parser_passes_execute_on_fixture():
    lines = FIXTURE.read_text(encoding="utf-8-sig").splitlines()
    sniff = FileSniffPass().run(FIXTURE)
    tokens = PreambleExtractionPass().run(lines, sniff)
    layout = TableLayoutDetectionPass().run(lines, sniff)
    header = ["Load", "Extension", "Front Strain", "Rear Strain", "Time"]
    units = ["(kN)", "(mm)", "(usn)", "(usn)", "(s)"]
    descriptors = ColumnClassificationPass().run(header, units, layout)
    channels = NumericIngestionPass().run(
        FIXTURE,
        layout,
        descriptors,
        delimiter=sniff.delimiter,
        quotechar=sniff.quotechar,
        encoding=sniff.encoding,
    )

    # Parser pass row indexes are zero-based physical line indexes in the raw file.
    assert sniff.likely_header_row_index == 5
    assert len(tokens) == 4
    assert layout.data_start_row_index == 7
    assert len(descriptors) == 5
    assert len(channels.strain_channels) == 2
