from __future__ import annotations

import csv
import hashlib
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

from archives.core.layouts import MTDAAlignedLayout, aggregate_member, metadata_member, report_member
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from mtda_finalization import AmendmentPolicy, AmendmentRequest, MTDAFinalizationService
from ui.method_run_wizard.view_models.output_review import output_review_view_model


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def base_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage21_finalization") / "base.mtda"
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
    return output


def test_amendment_policy_rejects_method_impacting_changes() -> None:
    request = AmendmentRequest(mapping_profile_changes={"channels.load": "OtherLoad"})
    decision = AmendmentPolicy().classify(request)

    assert decision.accepted is False
    assert decision.new_run_required is True
    assert "mapping_profile_changes" in (decision.disallowed_changes or {})


def test_legacy_mtda_loading_without_finalization_namespace(base_mtda: Path) -> None:
    state = MTDAFinalizationService().load_state(base_mtda)

    assert state.member_count > 0
    assert state.has_finalization_namespace is False
    assert state.manifest["package_format"] == "mtda"
    assert len(state.checksum) == 64


def test_report_only_finalization_updates_report_audit_provenance_and_checksums(base_mtda: Path, tmp_path: Path) -> None:
    before_mtdp = _sha256(INPUT)
    output = tmp_path / "report_finalized.mtda"
    result = MTDAFinalizationService().finalize(
        input_path=base_mtda,
        output_path=output,
        request=AmendmentRequest(
            report_overrides=(
                {
                    "field_key": "loading_method",
                    "value": "Compression loading between calibrated platens",
                    "reason": "Completed final report metadata",
                    "reviewer": "operator",
                    "section": "test_identification",
                },
            ),
            reviewer="operator",
            reason="final report metadata completion",
        ),
    )

    assert result.status == "finalized"
    assert _sha256(INPUT) == before_mtdp
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {name.split("/", 1)[0] for name in names if not name.endswith("/")} <= {"index.html", "dataset", "metadata"}
        assert not any(name.startswith(MTDAAlignedLayout.removed_standard_prefixes) for name in names)
        assert {
            metadata_member("finalization/archive_state.json"),
            metadata_member("finalization/amendment_ledger.json"),
            metadata_member("finalization/amendment_ledger.csv"),
            metadata_member("finalization/recompute_manifest.json"),
            metadata_member("finalization/finalization_report.json"),
        } <= names
        report = json.loads(archive.read(report_member("test_report.json")))
        completion = report["report_completion_status"]
        values = report["report_values_used"]
        missing = report["missing_report_fields"]
        audit = json.loads(archive.read(report_member("audit_report.json")))
        provenance = json.loads(archive.read(MTDAAlignedLayout.provenance))
        validation = json.loads(archive.read(MTDAAlignedLayout.validation))
        checksums = json.loads(archive.read(MTDAAlignedLayout.checksums))

    assert completion["recommended_missing_count"] == 36
    assert "loading_method" not in completion["recommended_missing_fields"]
    assert any(row.get("value") == "Compression loading between calibrated platens" for row in values)
    assert "loading_method" not in {row["field"] for row in missing}
    assert report["report_completion_status"]["recommended_missing_count"] == 36
    assert report["report_values_used"]
    assert audit["report_completion"]["override_count"] == 1
    assert audit["mtda_finalization"]["mtdp_mutated"] is False
    assert validation["report_quality_gate"]["layout_version"] == MTDAAlignedLayout.name
    assert "report/report_quality_gate.json" not in checksums["files"]
    assert {"mtda_amendments_applied", "mtda_finalized"} <= {event["event"] for event in provenance["events"]}
    assert metadata_member("finalization/finalization_report.json") in checksums["files"]
    assert MTDAAlignedLayout.checksums not in checksums["files"]


def test_selection_finalization_recomputes_final_selection_and_aggregate_tables(base_mtda: Path, tmp_path: Path) -> None:
    output = tmp_path / "selection_finalized.mtda"
    result = MTDAFinalizationService().finalize(
        input_path=base_mtda,
        output_path=output,
        request=AmendmentRequest(
            human_decisions=(
                {
                    "run_id": "run_001",
                    "decision_type": "remove",
                    "reason": "Operator removed run from final report set",
                    "reviewer": "operator",
                },
            ),
            reviewer="operator",
            reason="final selection amendment",
        ),
    )

    assert result.status == "finalized"
    with zipfile.ZipFile(output) as archive:
        final_rows = _csv_member(archive, aggregate_member("run_decision_registry.csv"))
        aggregate_rows = _csv_member(archive, aggregate_member("statistics.csv"))
        aligned_rows = _csv_member(archive, aggregate_member("stress_strain_aligned.csv"))
        report = json.loads(archive.read(report_member("test_report.json")))
        audit = json.loads(archive.read(report_member("audit_report.json")))

    by_run = {row["run_id"]: row for row in final_rows}
    assert by_run["run_001"]["included"] == "False"
    assert by_run["run_001"]["human_decision"] == "remove"
    strength = next(row for row in aggregate_rows if row["metric"] == "compressive_strength_MPa")
    assert int(strength["n"]) == report["summary"]["selected_run_count"]
    assert aligned_rows[0]["selection_set"] == "final_report_runs"
    assert report["selection_source"] == "human_final"
    assert audit["acceptance"]["selection_source"] == "human_final"
    assert audit["human_overrides"]["decision_count"] == 1


def test_method_impacting_amendment_is_rejected_without_output(base_mtda: Path, tmp_path: Path) -> None:
    output = tmp_path / "rejected.mtda"
    result = MTDAFinalizationService().finalize(
        input_path=base_mtda,
        output_path=output,
        request=AmendmentRequest(method_package_changes={"version": "changed"}),
    )

    assert result.status == "rejected_new_run_required"
    assert result.new_run_required is True
    assert not output.exists()


def test_output_surface_finalization_state_model(base_mtda: Path, tmp_path: Path) -> None:
    output = tmp_path / "finalized_for_view.mtda"
    MTDAFinalizationService().finalize(
        input_path=base_mtda,
        output_path=output,
        request=AmendmentRequest(reviewer="operator", reason="final archive review"),
    )
    with zipfile.ZipFile(output) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    model = output_review_view_model(
        {
            "output_path": str(output),
            "archive_members": members,
            "finalization_status": "finalized",
            "finalization_amendment_count": 1,
        }
    )

    assert metadata_member("finalization/finalization_report.json") in model["key_artifacts"]
    assert model["status_summary"]["finalization_status"] == "finalized"
    actions = {action["action_id"]: action for action in model["actions"]}
    assert actions["finalize_mtda"]["enabled"] is True


def _csv_member(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(member).decode("utf-8"))))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
