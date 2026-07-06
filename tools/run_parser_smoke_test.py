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
fixture = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"
record = DelimitedMechanicalCsvParser(fixture).parse()
report = build_parser_inspection_report(record, head=2, tail=2)
record_as_dict = to_standard_data_structure(record)

record

# %%
# Faithful plain-Python translation of the full ParsedSampleRecord.
record_as_dict

# %%
# Focused custom-structure views kept in memory for auditing.
file_sniff_as_dict = record_as_dict["file_sniff"]
table_layout_as_dict = record_as_dict["table_layout"]
preamble_as_dict = record_as_dict["preamble_tokens"]
channels_as_dict = record_as_dict["channels"]

channels_as_dict

# %%
assert record_as_dict["sample_id"] == "CAG-CF-ER-Comp-E1"
assert record_as_dict["validity_hint"] is True
assert record_as_dict["channels"]["load_channels"][0]["values"][1] == 100.0
assert record_as_dict["channels"]["strain_channels"][0]["descriptor"]["alias"] == "front"

assert report["sample_id"] == "CAG-CF-ER-Comp-E1"
assert report["validity_hint"] is True
assert report["header_flags"]["failure_mode"]["value"] == "Valid"
assert report["header_flags"]["width"]["unit"] == "mm"
assert [c["canonical_name"] for c in report["channel_flags"]] == [
    "load_1",
    "extension_1",
    "strain_1",
    "strain_2",
    "time_1",
]
assert report["row_count"] == 7
assert len(report["data_head"]) == 2
assert len(report["data_tail"]) == 2

"SMOKE TEST PASSED"

# %%
out = ROOT / "tests" / "data" / "parser_inspection_report.sample.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

out

# %%
print(json.dumps(record_as_dict, indent=2))

# %%
print(json.dumps(report, indent=2))
