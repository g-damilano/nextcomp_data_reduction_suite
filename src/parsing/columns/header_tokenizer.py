"""Legacy parser scaffold.

This module is classified in docs/project_control/SCAFFOLD_CLASSIFICATION.yaml.
It is not part of the active MTDP packaging or method-run architecture.
"""

from __future__ import annotations


def tokenize_header_cell(raw: str) -> list[str]:
    raise NotImplementedError(
        "tokenize_header_cell() is an obsolete legacy parser stub and is not used by "
        "the active delimited parser. Use parsing.columns.family_classifier for header "
        "normalization/classification, or remove the legacy caller that invoked this "
        "function. Classification record: docs/project_control/SCAFFOLD_CLASSIFICATION.yaml."
    )
