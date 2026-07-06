from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.mtdp import MTDPPackageInput, MTDPPackageReader, MTDPRun, RunChannel, RunToken
from compatibility import CompatibilityStatus, SchemaMethodCompatibilityChecker
from mapping import MappingCandidateDiscovery, build_mapping_resolution_report, write_mapping_profile
from methods.core.method_package import MethodPackage
from methods.core.method_run_service import MethodRunRequest, MethodRunService, load_mapping
from readiness import ReadinessChecker
from ui.method_run_wizard.view_models.mapping_preview import mapping_preview_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def source() -> Any:
    return MTDPPackageReader().read(INPUT)


@pytest.fixture(scope="module")
def method() -> MethodPackage:
    return MethodPackage.load(METHOD)


def test_schema_method_compatibility_is_separate_from_readiness(source: Any, method: MethodPackage) -> None:
    compatibility = SchemaMethodCompatibilityChecker().check(source=source, method_package=method)
    mapping = load_mapping(MAPPING)
    readiness = ReadinessChecker().check(source=source, method_package=method, mapping=mapping)

    assert compatibility.status == CompatibilityStatus.COMPATIBLE_WITH_WARNINGS
    assert compatibility.summary["execution_critical_supported"] == compatibility.summary["execution_critical_total"]
    assert any(row.severity == "report_completeness" and not row.compatible for row in compatibility.requirements)
    assert readiness.status.value == "READY_WITH_WARNINGS"


def test_mapping_candidate_discovery_resolves_iso14126_critical_inputs(source: Any, method: MethodPackage) -> None:
    report = MappingCandidateDiscovery().discover(source=source, method_package=method)
    requirements = {row["source_role"]: row for row in report["requirements"]}

    assert report["summary"]["requirement_total"] >= 14
    assert requirements["load"]["status"] == "resolved"
    assert requirements["front_strain"]["status"] == "resolved"
    assert requirements["rear_strain"]["status"] == "resolved"
    assert requirements["width"]["candidates"][0]["source_name"] == "Width"
    assert requirements["thickness"]["candidates"][0]["source_name"] == "Thickness"
    assert requirements["load"]["candidates"][0]["coverage"] == "7/7 runs"


def test_mapping_candidate_discovery_surfaces_unit_compatible_bz_style_channels(method: MethodPackage) -> None:
    source = _bz_style_source()
    report = MappingCandidateDiscovery().discover(source=source, method_package=method)
    requirements = {row["source_role"]: row for row in report["requirements"]}

    front = requirements["front_strain"]
    rear = requirements["rear_strain"]

    assert front["status"] == "resolved"
    assert rear["status"] == "resolved"
    assert front["candidates"][0]["source_name"] == "Uniaxial Gage 1 on S1-Ch2 microstrain"
    assert rear["candidates"][0]["source_name"] == "Uniaxial Gage 2 on S1-Ch1 microstrain"
    assert "first strain channel default" in front["candidates"][0]["reason"]
    assert "second strain channel default" in rear["candidates"][0]["reason"]
    assert {candidate["source_name"] for candidate in front["candidates"]} == {
        "Uniaxial Gage 1 on S1-Ch2 microstrain",
        "Uniaxial Gage 2 on S1-Ch1 microstrain",
    }

    width_candidates = requirements["width"]["candidates"]
    assert any(
        candidate["source_name"] == "Dimension A" and candidate["reason"] == "unit-compatible token"
        for candidate in width_candidates
    )


def test_manual_mapping_is_still_supported_and_resolution_is_recorded(source: Any, method: MethodPackage) -> None:
    mapping = load_mapping(MAPPING)
    candidates = MappingCandidateDiscovery().discover(source=source, method_package=method)
    resolution = build_mapping_resolution_report(mapping=mapping, candidate_report=candidates)

    assert mapping["schema_id"] == "method.mapping_profile.v0_2"
    assert mapping["mapping_id"] == "iso14126_manual_cag_cf_modied_ulv20_v0_1"
    assert resolution["summary"]["confirmed_total"] >= 6
    assert all(
        row["status"] == "confirmed"
        for row in resolution["resolutions"]
        if row["severity"] == "execution_critical"
    )


def test_operator_confirmed_mapping_can_be_saved_and_reused(tmp_path: Path) -> None:
    mapping = load_mapping(MAPPING)
    saved = write_mapping_profile(mapping, tmp_path / "confirmed_mapping.json")
    reloaded = load_mapping(saved)

    assert saved.exists()
    assert reloaded["schema_id"] == "method.mapping_profile.v0_2"
    assert reloaded["channels"]["load"] == "Load"
    assert reloaded["fields"]["width"] == "Width"


def test_ambiguous_execution_critical_mapping_blocks_readiness(
    tmp_path: Path,
    source: Any,
    method: MethodPackage,
) -> None:
    mapping = load_mapping(MAPPING)
    mapping["channels"]["load"] = {
        "status": "ambiguous",
        "candidates": ["Load", "Peak load"],
    }
    path = tmp_path / "ambiguous_mapping.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    report = ReadinessChecker().check(source=source, method_package=method, mapping=load_mapping(path))

    assert report.status.value == "MAPPING_REQUIRED"
    assert report.blocks_execution is True
    assert any(row["source_role"] == "load" for row in report.missing_rows())


def test_service_mapping_preview_exposes_candidates_and_resolution() -> None:
    result = MethodRunService().load_mapping(MAPPING, METHOD, INPUT)
    model = mapping_preview_view_model(result)

    assert model["compatibility_status"] == "COMPATIBLE_WITH_WARNINGS"
    assert model["candidate_summary"]["requirement_total"] >= 14
    assert model["resolution_summary"]["confirmed_total"] >= 6
    assert model["candidate_rows"]
    assert model["disambiguation_rows"]
    rows = {row["method_field"]: row for row in model["rows"]}
    assert rows["channel.load_N"]["resolution_status"] == "confirmed"
    assert rows["channel.load_N"]["candidate_count"] >= 1
    assert float(rows["channel.load_N"]["confidence"]) > 0.9
    assert "specimen.gauge_length_mm" not in rows
    assert result.summary["execution_critical_missing"] == 0


def test_mtda_contains_compatibility_mapping_artifacts_and_provenance(tmp_path: Path) -> None:
    output = tmp_path / "stage20_binding.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output,
            overwrite=True,
            generate_workbench=True,
        )
    )

    assert result.status == "completed"
    with zipfile.ZipFile(output) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        assert {
            "compatibility/schema_method_compatibility_report.json",
            "compatibility/schema_method_compatibility_summary.csv",
            "mapping/mapping_profile_used.json",
            "mapping/mapping_candidate_report.json",
            "mapping/mapping_resolution_report.json",
        } <= names
        compatibility = json.loads(archive.read("compatibility/schema_method_compatibility_report.json"))
        mapping_used = json.loads(archive.read("mapping/mapping_profile_used.json"))
        candidates = json.loads(archive.read("mapping/mapping_candidate_report.json"))
        resolution = json.loads(archive.read("mapping/mapping_resolution_report.json"))
        provenance = json.loads(archive.read("provenance.json"))
        audit = json.loads(archive.read("audit/audit_report.json"))
        trace = json.loads(archive.read("workbench/operation_trace.json"))
        summary_rows = list(
            csv.DictReader(
                io.StringIO(archive.read("compatibility/schema_method_compatibility_summary.csv").decode("utf-8"))
            )
        )

    assert compatibility["summary"]["status"] == "COMPATIBLE_WITH_WARNINGS"
    assert mapping_used["schema_id"] == "method.mapping_profile.v0_2"
    assert candidates["summary"]["requirement_total"] >= 14
    assert resolution["summary"]["confirmed_total"] >= 6
    assert summary_rows
    events = {event["event"] for event in provenance["events"]}
    assert {
        "schema_method_compatibility_checked",
        "mapping_candidates_generated",
        "mapping_profile_confirmed",
        "mapping_profile_saved",
        "readiness_checked_with_mapping",
    } <= events
    assert audit["schema_method_compatibility"]["summary"]["status"] == "COMPATIBLE_WITH_WARNINGS"
    assert audit["mapping_profile"]["resolution_summary"]["confirmed_total"] >= 6
    assert trace["mapping_candidate_report"]["summary"]["requirement_total"] >= 14
    assert trace["operation_input_mapping"]


def _bz_style_source() -> MTDPPackageInput:
    channels = {
        "Scan #": RunChannel("Scan #", None, (1.0, 2.0, 3.0)),
        "Time": RunChannel("Time", "s", (0.0, 0.1, 0.2)),
        "Uniaxial Gage 1 on S1-Ch2 microstrain": RunChannel(
            "Uniaxial Gage 1 on S1-Ch2 microstrain",
            "usn",
            (0.0, 120.0, 240.0),
        ),
        "Uniaxial Gage 2 on S1-Ch1 microstrain": RunChannel(
            "Uniaxial Gage 2 on S1-Ch1 microstrain",
            "usn",
            (0.0, 110.0, 220.0),
        ),
        "Load": RunChannel("Load", "kN", (0.0, 1.2, 2.4)),
    }
    tokens = {
        "Dimension A": RunToken("Dimension A", "10", "mm"),
        "Dimension B": RunToken("Dimension B", "2", "mm"),
    }
    run = MTDPRun(
        run_id="run_001",
        normalized_package_path="normalized/run_001.json",
        raw_package_path="raw/run_001.csv",
        original_filename="run_001.csv",
        tokens=tokens,
        channels=channels,
    )
    return MTDPPackageInput(
        path=Path("synthetic_bz_style.mtdp"),
        manifest={"schema_id": "mechanical.compression.v0.3.0"},
        schema={"schema_id": "mechanical.compression.v0.3.0", "dataset_fields": [], "run_fields": []},
        dataset={},
        provenance={},
        checksums={},
        runs=(run,),
    )
