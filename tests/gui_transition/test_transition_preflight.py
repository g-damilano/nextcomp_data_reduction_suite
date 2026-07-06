from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = ROOT / "tools" / "gui_transition" / "run_transition_preflight.py"


def _load_preflight():
    spec = importlib.util.spec_from_file_location("run_transition_preflight", PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_transition_preflight_gate_list_covers_default_readiness_commands() -> None:
    preflight = _load_preflight()
    gates = preflight.build_gates()
    gate_ids = {gate.gate_id for gate in gates}
    ordered_gate_ids = [gate.gate_id for gate in gates]

    assert gate_ids == {
        "bridge_contract",
        "representative_workflows",
        "desktop_default_entrypoint",
        "visual_manifest_integrity",
        "visual_live_verification",
        "frontend_tests",
        "frontend_build",
        "python_compile",
        "packaged_desktop_build",
        "demo_quarantine_scan",
    }
    assert next(gate for gate in gates if gate.gate_id == "visual_live_verification").live_visual
    assert ordered_gate_ids.index("frontend_build") < ordered_gate_ids.index("desktop_default_entrypoint")
    assert ordered_gate_ids.index("frontend_build") < ordered_gate_ids.index("visual_live_verification")
    assert ordered_gate_ids.index("python_compile") < ordered_gate_ids.index("packaged_desktop_build")
    commands = "\n".join(preflight.command_display(gate.command) for gate in gates if gate.command)
    assert "tests/gui_transition/test_bridge_dispatcher.py" in commands
    assert "tests/gui_transition/test_representative_workflows.py" in commands
    assert "tests/gui_transition/test_desktop_default_entrypoint.py" in commands
    assert "tests/gui_transition/test_visual_baselines.py" in commands
    assert "tools/gui_transition/capture_visual_baselines.py" in commands
    assert "compileall" in commands
    assert "PyInstaller" in commands


def test_transition_preflight_dry_run_writes_report(tmp_path: Path) -> None:
    preflight = _load_preflight()
    report_path = tmp_path / "preflight.json"

    assert preflight.main(["--dry-run", "--skip-live-visual", "--report", str(report_path)]) == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == preflight.SCHEMA
    assert report["status"] == "dry-run"
    assert report["dry_run"] is True
    assert report["skip_live_visual"] is True
    assert len(report["gates"]) == len(preflight.build_gates())
    assert {item["status"] for item in report["gates"]} == {"dry-run"}
    assert all(item["command"] for item in report["gates"])


def test_transition_preflight_demo_quarantine_scan_passes() -> None:
    preflight = _load_preflight()
    returncode, stdout, stderr = preflight._scan_demo_quarantine(ROOT)

    assert returncode == 0, stderr
    assert "No production source seeded-ingest symbols found." in stdout


def test_transition_preflight_skipped_live_visual_blocks_promotion() -> None:
    preflight = _load_preflight()
    gate = next(gate for gate in preflight.build_gates() if gate.gate_id == "visual_live_verification")

    result = preflight.run_gate(gate, root=ROOT, dry_run=False, skip_live_visual=True)
    report = preflight.build_report(results=[result], dry_run=False, skip_live_visual=True)

    assert result["status"] == "skipped"
    assert report["status"] == "blocked"
    assert report["warnings"]
