from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path


os.environ.setdefault("MTDP_QT_API", "PySide6")

ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ROOT = (
    ROOT
    / "prototyping"
    / "compression_gui_react_seed_validated"
    / "compression_gui_react_seed_validated"
    / "desktop"
)
SRC_ROOT = ROOT / "src"
WORKFLOW_MANIFEST = ROOT / "tests" / "fixtures" / "gui_transition" / "representative_workflows.json"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(DESKTOP_ROOT))

from bridge_dispatcher import BridgeDispatcher  # noqa: E402
from gui_bridge.services.analysis_session import AnalysisSessionService  # noqa: E402
from gui_bridge.services.method_editor_session import MethodEditorSessionService  # noqa: E402
from methods.core.method_package import MethodPackage  # noqa: E402
from mtdp_enrichment.package import MTDPPackageValidator  # noqa: E402
from ui.method_run_wizard.method_registry import MethodRegistry  # noqa: E402


def _manifest() -> dict:
    payload = json.loads(WORKFLOW_MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema"] == "gui-transition-representative-workflows/v1"
    return payload


def _workflow(workflow_id: str) -> dict:
    for workflow in _manifest()["workflows"]:
        if workflow["id"] == workflow_id:
            return workflow
    raise AssertionError(f"missing representative workflow {workflow_id}")


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _ok(dispatcher: BridgeDispatcher, request: dict) -> dict:
    response = dispatcher.dispatch(request)
    json.dumps(response)
    assert response["status"] == "ok", response
    return response


def _write_temp_method_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "method_registry.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "methods:",
                "  - method_id: iso14126_2023",
                "    label: ISO 14126 Compression",
                "    version: 0.1.0",
                "    status: active",
                "    analysis_type: mechanical.compression",
                f"    method_path: {(_path('src/methods/iso14126')).as_posix()}",
                f"    default_mapping_path: {(_path('mappings/iso14126_manual.json')).as_posix()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return registry_path


def _recipe_hashes(package: MethodPackage) -> dict[str, str]:
    return {
        path.relative_to(package.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in package.recipe_files()
    }


def _wait_for_completed_run(
    dispatcher: BridgeDispatcher,
    session_id: str,
    *,
    timeout_seconds: float = 60.0,
) -> dict:
    deadline = time.time() + timeout_seconds
    current: dict | None = None
    while time.time() < deadline:
        current = _ok(
            dispatcher,
            {
                "namespace": "analysis",
                "command": "getSession",
                "payload": {"session_id": session_id},
            },
        )
        run = current["data"]["run"]
        if run["status"] in {"completed", "failed", "cancelled"}:
            return current
        time.sleep(0.1)
    raise AssertionError(f"analysis run did not finish before timeout: {current}")


def test_representative_packaging_export_feeds_analysis_readiness(tmp_path: Path) -> None:
    workflow = _workflow("packaging-export-analysis-readiness")
    output_path = tmp_path / workflow["export"]["output_name"]
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    created = _ok(dispatcher, {"namespace": "packaging", "command": "createSession", "payload": {}})
    loaded = _ok(
        dispatcher,
        {
            "namespace": "packaging",
            "command": "loadPackage",
            "payload": {
                "session_id": created["data"]["session_id"],
                "path": str(_path(workflow["input_package"])),
            },
        },
    )
    groups = loaded["data"]["bundle"]["groups"]
    assert len(groups) == workflow["expected_group_count"]
    group = groups[0]
    assert len(group["runs"]) == workflow["expected_run_count"]

    exported = _ok(
        dispatcher,
        {
            "namespace": "packaging",
            "command": "exportGroup",
            "payload": {
                "session_id": created["data"]["session_id"],
                "group_id": group["id"],
                "output_path": str(output_path),
            },
        },
    )
    assert exported["data"]["export"]["runCount"] == workflow["expected_run_count"]
    assert MTDPPackageValidator().validate(output_path).ok

    with zipfile.ZipFile(output_path) as archive:
        members = set(archive.namelist())
    assert set(workflow["export"]["required_members"]).issubset(members)

    analysis = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(output_path)},
        },
    )
    assert analysis["data"]["package_path"] == str(output_path)
    assert analysis["data"]["package"]["run_count"] == workflow["expected_run_count"]

    selected = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": analysis["data"]["session_id"],
                "method_id": workflow["analysis"]["method_id"],
            },
        },
    )
    assert selected["data"]["mapping"]["mapping_name"] == workflow["analysis"]["mapping_name"]

    ready = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"]},
        },
    )
    assert ready["data"]["readiness_status"] == workflow["analysis"]["readiness_status"]
    assert ready["data"]["run_enabled"] is workflow["analysis"]["run_enabled"]
    assert (
        ready["data"]["readiness"]["summary"]["execution_critical_missing"]
        == workflow["analysis"]["execution_critical_missing"]
    )


def test_representative_method_editor_generated_method_feeds_analysis_readiness(tmp_path: Path) -> None:
    workflow = _workflow("method-editor-generated-analysis-readiness")
    registry_path = _write_temp_method_registry(tmp_path)
    generated_root = tmp_path / "generated"
    dispatcher = BridgeDispatcher(backend_root=ROOT)
    dispatcher._method_editor_service = MethodEditorSessionService(
        registry_path=registry_path,
        generated_root=generated_root,
    )
    canonical_package = MethodPackage.load(_path("src/methods/iso14126"))
    before_hashes = _recipe_hashes(canonical_package)

    created = _ok(
        dispatcher,
        {
            "namespace": "methodEditor",
            "command": "createDraft",
            "payload": {"method_id": workflow["base_method_id"]},
        },
    )
    updated = _ok(
        dispatcher,
        {
            "namespace": "methodEditor",
            "command": "updateDraft",
            "payload": {
                "draft_id": created["data"]["draft"]["draft_id"],
                "patch": workflow["controlled_patch"],
            },
        },
    )
    assert updated["data"]["draft"]["validation"]["status"] == "valid"
    assert updated["data"]["draft"]["validation"]["loadable"] is True

    generated = _ok(
        dispatcher,
        {
            "namespace": "methodEditor",
            "command": "generateVersion",
            "payload": {
                "draft_id": created["data"]["draft"]["draft_id"],
                "target_version": workflow["target_version"],
            },
        },
    )
    generated_method = generated["data"]["generated_method"]
    generated_path = Path(generated_method["method_path"])
    assert generated_method["method_id"] == workflow["generated_method_id"]
    assert generated_method["version"] == workflow["target_version"]

    package = MethodPackage.load(generated_path)
    chord_step = next(
        step for step in package.reduce_recipe["reduce"] if step.get("id") == "reduce.chord_modulus"
    )
    assert chord_step["x1"] == workflow["controlled_patch"]["values"]["start_strain"]
    assert chord_step["x2"] == workflow["controlled_patch"]["values"]["end_strain"]

    registered = _ok(
        dispatcher,
        {
            "namespace": "methodEditor",
            "command": "registerGeneratedMethod",
            "payload": {"method_path": str(generated_path)},
        },
    )
    assert registered["data"]["registry_entry"]["method_id"] == workflow["generated_method_id"]

    dispatcher._analysis_service = AnalysisSessionService(registry=MethodRegistry.load(registry_path))
    analysis = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(_path(workflow["input_package"]))},
        },
    )
    assert workflow["generated_method_id"] in {
        item["method_id"] for item in analysis["data"]["eligible_methods"]
    }

    selected = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": analysis["data"]["session_id"],
                "method_id": workflow["generated_method_id"],
            },
        },
    )
    assert selected["data"]["selected_method"]["method_id"] == workflow["generated_method_id"]

    ready = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {"session_id": selected["data"]["session_id"]},
        },
    )
    assert ready["data"]["readiness_status"] == workflow["analysis"]["readiness_status"]
    assert ready["data"]["run_enabled"] is workflow["analysis"]["run_enabled"]
    assert (
        ready["data"]["readiness"]["summary"]["execution_critical_missing"]
        == workflow["analysis"]["execution_critical_missing"]
    )

    after_hashes = _recipe_hashes(MethodPackage.load(_path("src/methods/iso14126")))
    assert after_hashes == before_hashes


def test_representative_analysis_execution_review_and_finalization(tmp_path: Path) -> None:
    workflow = _workflow("analysis-execution-review-finalization")
    output_path = tmp_path / workflow["output_name"]
    dispatcher = BridgeDispatcher(backend_root=ROOT)

    analysis = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "createSession",
            "payload": {"initial_package_path": str(_path(workflow["input_package"]))},
        },
    )
    selected = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "selectMethod",
            "payload": {
                "session_id": analysis["data"]["session_id"],
                "method_id": workflow["method_id"],
            },
        },
    )
    ready = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "checkReadiness",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
            },
        },
    )
    assert ready["data"]["readiness_status"] == workflow["readiness_status"]
    assert ready["data"]["run_enabled"] is True

    started = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "startRun",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "output_path": str(output_path),
                "overwrite": True,
                "generate_workbench": workflow["generate_workbench"],
            },
        },
    )
    assert started["data"]["run"]["status"] == "running"

    completed = _wait_for_completed_run(dispatcher, selected["data"]["session_id"])
    run = completed["data"]["run"]
    assert run["status"] == workflow["run"]["terminal_status"]
    assert run["progress_percent"] == workflow["run"]["progress_percent"]
    assert output_path.is_file()
    assert run["result"]["output_path"] == str(output_path)
    assert set(workflow["run"]["required_events"]).issubset({event["event"] for event in run["events"]})
    with zipfile.ZipFile(output_path) as archive:
        members = set(archive.namelist())
    assert set(workflow["run"]["required_members"]).issubset(members)

    specimen_run_id = next(iter(run["result"]["acceptance_report"]["run_states"]))
    review = workflow["review"]
    decision = {
        "run_id": specimen_run_id,
        "decision": review["decision"],
        "final_included": review["final_included"],
        "default_included": review["default_included"],
        "reason": review["reason"],
        "defects": review["defects"],
        "reviewer": review["reviewer"],
    }
    updated = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "updateAcceptanceDecision",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "decision_patch": decision,
            },
        },
    )
    assert updated["data"]["review"]["status"] == "in_review"
    assert updated["data"]["acceptance_decisions"]["acceptance_keep"][specimen_run_id] is True

    confirmed = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "confirmReview",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "decisions": [decision],
                "reviewer": review["reviewer"],
                "note": review["note"],
            },
        },
    )
    assert confirmed["data"]["review"]["status"] == "confirmed"
    assert confirmed["data"]["review"]["reviewer"] == review["reviewer"]
    assert confirmed["data"]["run"]["events"][-1]["event"] == "reviewConfirmed"

    finalization = workflow["finalization"]
    finalized = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "finalizeMtda",
            "payload": {
                "session_id": selected["data"]["session_id"],
                "reviewer": finalization["reviewer"],
                "note": finalization["note"],
                "reason_kind": finalization["reason_kind"],
            },
        },
    )
    finalization_payload = finalized["data"]["finalization"]
    finalized_path = Path(finalization_payload["output_path"])
    assert finalization_payload["status"] == finalization["status"]
    assert finalization_payload["reason_kind"] == finalization["reason_kind"]
    assert finalization_payload["human_decision_count"] == finalization["human_decision_count"]
    assert finalized_path.is_file()
    assert finalized_path != output_path
    assert output_path.is_file()
    assert finalized["data"]["run"]["events"][-1]["event"] == "mtdaFinalized"
    with zipfile.ZipFile(finalized_path) as archive:
        finalized_members = set(archive.namelist())
    for suffix in finalization["required_member_suffixes"]:
        assert any(member.endswith(suffix) for member in finalized_members), suffix

    copied = _ok(
        dispatcher,
        {
            "namespace": "analysis",
            "command": "copyOutputPath",
            "payload": {"session_id": selected["data"]["session_id"]},
        },
    )
    assert copied["data"]["path"] == str(finalized_path)
    assert copied["data"]["exists"] is True

    for artifact_kind in workflow["artifacts"]:
        artifact = _ok(
            dispatcher,
            {
                "namespace": "analysis",
                "command": "openArtifact",
                "payload": {
                    "session_id": selected["data"]["session_id"],
                    "artifact_kind": artifact_kind,
                    "open": False,
                },
            },
        )
        assert artifact["data"]["kind"] == artifact_kind
        assert Path(artifact["data"]["path"]).exists()
