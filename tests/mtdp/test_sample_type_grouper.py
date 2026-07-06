from __future__ import annotations

import shutil
from pathlib import Path

from mtdp_enrichment.grouping import GroupingInput, SampleNameCanonicalizer, SampleTypeGrouper
from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.parsing_gateway import ParserAdapter
from mtdp_enrichment.schemas import SchemaRegistry


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "Specimen_RawData_1.csv"


def test_explicit_parsed_token_groups_files_correctly(tmp_path: Path):
    first = _write_with_sample_type(tmp_path / "anything_E1.csv", "Untreated")
    second = _write_with_sample_type(tmp_path / "anything_E2.csv", "Untreated")
    schema = SchemaRegistry().get("mechanical.compression")
    proposal = SampleTypeGrouper().propose(_inputs(first, second), schema)

    assert len(proposal.bundles) == 1
    assert proposal.bundles[0].display_name == "Untreated"
    assert proposal.bundles[0].assignments[0].reason == "explicit parsed token"
    assert proposal.bundles[0].assignments[0].confidence == 0.95
    assert not proposal.unassigned


def test_filename_pattern_groups_replicates_correctly(tmp_path: Path):
    first = _copy_fixture(tmp_path / "CAG-CF-ER-Comp-E1.csv")
    second = _copy_fixture(tmp_path / "CAG_CF_ER_Comp_E2.csv")
    schema = SchemaRegistry().get("mechanical.compression")
    proposal = SampleTypeGrouper().propose(_inputs(first, second), schema)

    assert len(proposal.bundles) == 1
    assert proposal.bundles[0].bundle_key == "cag cf er"
    assert {item.source_path.name for item in proposal.bundles[0].assignments} == {
        "CAG-CF-ER-Comp-E1.csv",
        "CAG_CF_ER_Comp_E2.csv",
    }
    assert proposal.bundles[0].assignments[0].reason == "filename pattern"


def test_folder_name_is_weak_fallback_when_filename_has_no_candidate(tmp_path: Path):
    folder = tmp_path / "Untreated"
    folder.mkdir()
    source = _copy_fixture(folder / "Comp-E1.csv")
    schema = SchemaRegistry().get("mechanical.compression")
    proposal = SampleTypeGrouper().propose(_inputs(source), schema)

    assert len(proposal.bundles) == 1
    assert proposal.bundles[0].display_name == "Untreated"
    assert proposal.bundles[0].assignments[0].reason == "parent folder name"
    assert proposal.bundles[0].assignments[0].confidence == 0.60


def test_manual_only_grouping_marks_unknown_as_unassigned(tmp_path: Path):
    source = _copy_fixture(tmp_path / "Comp-E1.csv")
    schema = _schema_with_grouping({"enabled": True, "source_priority": ["manual"]})

    proposal = SampleTypeGrouper().propose(_inputs(source), schema)

    assert not proposal.bundles
    assert proposal.unassigned[0].source_path == source


def test_canonicalization_collapses_case_and_spacing_variants():
    canonicalizer = SampleNameCanonicalizer(
        {
            "casefold": True,
            "replace_separators_with_space": True,
            "collapse_whitespace": True,
        }
    )

    assert canonicalizer.canonicalize(" CAG-CF__ER  ").canonical_key == "cag cf er"


def test_fuzzy_typo_creates_suggestion_not_silent_merge(tmp_path: Path):
    first = _write_with_sample_type(tmp_path / "a.csv", "Untreated")
    second = _write_with_sample_type(tmp_path / "b.csv", "Untreted")
    schema = SchemaRegistry().get("mechanical.compression")

    proposal = SampleTypeGrouper().propose(_inputs(first, second), schema)

    assert len(proposal.bundles) == 2
    assert proposal.suggested_merges
    assert proposal.suggested_merges[0].similarity >= 0.86
    assert proposal.suggested_merges[0].reason


def test_schema_grouping_config_controls_filename_tokens(tmp_path: Path):
    source = _copy_fixture(tmp_path / "CAG-CF-ER-Comp-E1.csv")
    schema = _schema_with_grouping(
        {
            "enabled": True,
            "source_priority": ["filename_pattern"],
            "filename_grouping": {
                "delimiter_pattern": "[-_ ]+",
                "remove_tokens": [],
                "replicate_patterns": ["E\\d+$"],
            },
            "canonicalization": {
                "casefold": True,
                "replace_separators_with_space": True,
                "collapse_whitespace": True,
            },
        }
    )

    proposal = SampleTypeGrouper().propose(_inputs(source), schema)

    assert proposal.bundles[0].bundle_key == "cag cf er comp"


def _inputs(*paths: Path) -> list[GroupingInput]:
    parser = ParserAdapter()
    registry = SchemaRegistry()
    return [
        GroupingInput(path, parser.parse(path), registry.infer(parser.parse(path), path))
        for path in paths
    ]


def _copy_fixture(path: Path) -> Path:
    shutil.copyfile(FIXTURE, path)
    return path


def _write_with_sample_type(path: Path, sample_type: str) -> Path:
    text = FIXTURE.read_text(encoding="utf-8-sig")
    path.write_text(f"Sample type,\"{sample_type}\"\n{text}", encoding="utf-8")
    return path


def _schema_with_grouping(grouping: dict[str, object]) -> MTDPSchema:
    payload = SchemaRegistry().get("mechanical.compression").to_dict()
    payload["dataset_grouping"] = grouping
    return MTDPSchema.from_dict(payload)

