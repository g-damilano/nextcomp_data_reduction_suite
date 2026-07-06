# %%
from __future__ import annotations

import json
from pathlib import Path
import sys

try:
    ipython = get_ipython()  # type: ignore[name-defined]
except NameError:
    ipython = None

if ipython is not None:
    ipython.run_line_magic("load_ext", "autoreload")
    ipython.run_line_magic("autoreload", "2")

# %%
ROOT = Path.cwd()
if not (ROOT / "src").exists():
    ROOT = Path(__file__).resolve().parents[1]

src_path = str(ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from parsing.inspection import build_parser_inspection_report, to_standard_data_structure
from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser

ROOT

# %%
# Change this path to inspect another CSV file.
file_path = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"
head = 5
tail = 5

file_path

# %%
parser = DelimitedMechanicalCsvParser(file_path)
record = parser.parse()

record

# %%
# Faithful translation of the full custom ParsedSampleRecord dataclass tree.
record_as_dict = to_standard_data_structure(record)

record_as_dict

# %%
# Focused views for auditing the nested data structures.
file_sniff_as_dict = record_as_dict["file_sniff"]
table_layout_as_dict = record_as_dict["table_layout"]
preamble_as_dict = record_as_dict["preamble_tokens"]
channels_as_dict = record_as_dict["channels"]

channels_as_dict

# %%
# Audit report: summarized flags plus head/tail rows, JSON serialisable.
report = build_parser_inspection_report(record, head=head, tail=tail)

report

# %%
print(json.dumps(record_as_dict, indent=2))

# %%
print(json.dumps(report, indent=2))
