# Parser Contract

The MTDP enrichment application delegates raw testing-machine parsing to the parsing suite under `src/parsing/`.

Parser row indexes are zero-based physical line indexes in the source file after decoding. This means indexes count every raw text line, including token-preamble rows, blank separator rows, header rows, and unit rows.

For the canonical compression fixture:

- `likely_header_row_index` points to the table header row.
- `data_start_row_index` points to the first numerical data row.
- the unit row between the header and numerical rows is not counted as data.

Floating-point numerical values emitted by the parser should be compared with tolerance in tests and downstream validation. The parser preserves the scientific value, not decimal-display identity.
