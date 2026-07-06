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

from parsing.inspection import to_standard_data_structure
from parsing.parsers.delimited_mechanical_csv_parser import DelimitedMechanicalCsvParser

ROOT

# %%
# Change this to inspect another file.
file_path = ROOT / "tests" / "data" / "Specimen_RawData_1.csv"

record = DelimitedMechanicalCsvParser(file_path).parse()
record_as_dict = to_standard_data_structure(record)

record_as_dict

# %%
# Parsing execution flags, printed as stored inside the ParsedSampleRecord tree.
parsing_execution_flags = {
    "source_file": record_as_dict["source_file"],
    "sample_id": record_as_dict["sample_id"],
    "validity_hint": record_as_dict["validity_hint"],
    "validity_hint_source": record_as_dict["validity_hint_source"],
    "file_sniff": record_as_dict["file_sniff"],
    "table_layout": record_as_dict["table_layout"],
    "parse_warnings": record_as_dict["parse_warnings"],
}

print("=== PARSING EXECUTION FLAGS ===")
print(json.dumps(parsing_execution_flags, indent=2))

# %%
# Parsed content, printed in the same nested shape used by the stored record.
parsed_content = {
    "preamble_tokens": record_as_dict["preamble_tokens"],
    "raw_header": record_as_dict["raw_header"],
    "raw_units_row": record_as_dict["raw_units_row"],
    "channels": record_as_dict["channels"],
}

print("=== PARSED CONTENT ===")
print(json.dumps(parsed_content, indent=2))

# %%
# Full bulk structure, without separating flags from content.
print("=== FULL STORED STRUCTURE ===")
print(json.dumps(record_as_dict, indent=2))

# %%
