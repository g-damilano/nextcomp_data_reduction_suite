from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "gui-transition-default-readiness-preflight/v1"
TAIL_CHARS = 4000
DEMO_QUARANTINE_PATTERNS = (
    "INITIAL_BUNDLE",
    "RUN_SEED",
    "IngestModal",
    "ingestscrim",
    "ingest__",
    "istep",
    "ifile",
)


@dataclass(frozen=True)
class Gate:
    gate_id: str
    description: str
    command: tuple[str, ...] = ()
    required_for_promotion: bool = True
    live_visual: bool = False
    builtin: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def react_project_root() -> Path:
    return repo_root() / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated"


def _python() -> str:
    return sys.executable


def _npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def command_display(command: tuple[str, ...]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    import shlex

    return shlex.join(command)


def build_gates() -> list[Gate]:
    root = repo_root()
    frontend = react_project_root()
    desktop = root / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated" / "desktop"
    return [
        Gate(
            gate_id="bridge_contract",
            description="Bridge dispatcher commands and structured errors.",
            command=(_python(), "-m", "pytest", "-q", "tests/gui_transition/test_bridge_dispatcher.py"),
        ),
        Gate(
            gate_id="representative_workflows",
            description="Representative Packaging, Method Editor, and Analysis workflows.",
            command=(_python(), "-m", "pytest", "-q", "tests/gui_transition/test_representative_workflows.py"),
        ),
        Gate(
            gate_id="visual_manifest_integrity",
            description="Committed visual baseline manifest and PNG integrity.",
            command=(_python(), "-m", "pytest", "-q", "tests/gui_transition/test_visual_baselines.py"),
        ),
        Gate(
            gate_id="frontend_tests",
            description="React/Vitest frontend suite.",
            command=(_npm(), "-C", str(frontend), "run", "-s", "test"),
        ),
        Gate(
            gate_id="frontend_build",
            description="React/Vite production build.",
            command=(_npm(), "-C", str(frontend), "run", "-s", "build"),
        ),
        Gate(
            gate_id="desktop_default_entrypoint",
            description="Packaged desktop default points to the React/PySide6 shell with a legacy fallback.",
            command=(_python(), "-m", "pytest", "-q", "tests/gui_transition/test_desktop_default_entrypoint.py"),
        ),
        Gate(
            gate_id="visual_live_verification",
            description="Live PySide6/WebEngine screenshot comparison against committed baselines.",
            command=(_python(), "tools/gui_transition/capture_visual_baselines.py", "--verify"),
            live_visual=True,
        ),
        Gate(
            gate_id="python_compile",
            description="Python compile check for backend, PySide shell, tests, and transition tools.",
            command=(
                _python(),
                "-m",
                "compileall",
                "-q",
                "src",
                str(desktop),
                "tests/gui_transition",
                "tools/gui_transition",
            ),
        ),
        Gate(
            gate_id="packaged_desktop_build",
            description="PyInstaller builds the promoted React/PySide6 desktop package.",
            command=(_python(), "-m", "PyInstaller", "--clean", "mtdp_enrichment.spec", "--noconfirm"),
        ),
        Gate(
            gate_id="demo_quarantine_scan",
            description="Production source contains no seeded Dataset Packaging ingest fallback symbols.",
            builtin="demo_quarantine_scan",
        ),
    ]


def _tail(text: str) -> str:
    if len(text) <= TAIL_CHARS:
        return text
    return text[-TAIL_CHARS:]


def _scan_demo_quarantine(root: Path) -> tuple[int, str, str]:
    search_roots = [
        root / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated" / "src" / "screens",
        root / "prototyping" / "compression_gui_react_seed_validated" / "compression_gui_react_seed_validated" / "src" / "styles",
    ]
    matches: list[str] = []
    for search_root in search_roots:
        if not search_root.exists():
            matches.append(f"missing search root: {search_root}")
            continue
        for path in search_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".jsx", ".js", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for pattern in DEMO_QUARANTINE_PATTERNS:
                    if pattern in line:
                        rel = path.relative_to(root).as_posix()
                        matches.append(f"{rel}:{line_number}: {pattern}")
    if matches:
        return 1, "", "\n".join(matches)
    return 0, "No production source seeded-ingest symbols found.\n", ""


def run_gate(gate: Gate, *, root: Path, dry_run: bool, skip_live_visual: bool) -> dict:
    command = command_display(gate.command) if gate.command else f"builtin:{gate.builtin}"
    if dry_run:
        return {
            "gate_id": gate.gate_id,
            "description": gate.description,
            "required_for_promotion": gate.required_for_promotion,
            "status": "dry-run",
            "command": command,
            "duration_seconds": 0.0,
        }
    if skip_live_visual and gate.live_visual:
        return {
            "gate_id": gate.gate_id,
            "description": gate.description,
            "required_for_promotion": gate.required_for_promotion,
            "status": "skipped",
            "skip_reason": "live visual verification skipped by request",
            "command": command,
            "duration_seconds": 0.0,
        }

    started = time.monotonic()
    if gate.builtin == "demo_quarantine_scan":
        returncode, stdout, stderr = _scan_demo_quarantine(root)
    else:
        completed = subprocess.run(gate.command, cwd=root, text=True, capture_output=True)
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    duration = time.monotonic() - started
    return {
        "gate_id": gate.gate_id,
        "description": gate.description,
        "required_for_promotion": gate.required_for_promotion,
        "status": "passed" if returncode == 0 else "failed",
        "command": command,
        "returncode": returncode,
        "duration_seconds": round(duration, 3),
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
    }


def overall_status(results: list[dict], *, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    if any(item["status"] == "failed" for item in results):
        return "failed"
    if any(item["status"] == "skipped" and item.get("required_for_promotion") for item in results):
        return "blocked"
    return "passed"


def build_report(*, results: list[dict], dry_run: bool, skip_live_visual: bool) -> dict:
    status = overall_status(results, dry_run=dry_run)
    warnings = []
    if status == "blocked":
        warnings.append("A required promotion gate was skipped; do not make the React/PySide6 shell default.")
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo_root": str(repo_root()),
        "dry_run": dry_run,
        "skip_live_visual": skip_live_visual,
        "status": status,
        "warnings": warnings,
        "gates": results,
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def print_summary(report: dict) -> None:
    print(f"GUI transition preflight: {report['status']}")
    for item in report["gates"]:
        print(f"- {item['gate_id']}: {item['status']}")
        if item.get("skip_reason"):
            print(f"  reason: {item['skip_reason']}")
        if item["status"] in {"failed", "dry-run", "skipped"}:
            print(f"  command: {item['command']}")
    for warning in report.get("warnings", []):
        print(f"warning: {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GUI transition default-readiness gates.")
    parser.add_argument("--dry-run", action="store_true", help="Print/report the gate plan without executing commands.")
    parser.add_argument(
        "--skip-live-visual",
        action="store_true",
        help="Skip the live PySide6/WebEngine screenshot verifier. The report will be blocked unless --dry-run is used.",
    )
    parser.add_argument("--report", type=Path, help="Optional JSON report path.")
    args = parser.parse_args(argv)

    root = repo_root()
    results = [
        run_gate(gate, root=root, dry_run=args.dry_run, skip_live_visual=args.skip_live_visual)
        for gate in build_gates()
    ]
    report = build_report(results=results, dry_run=args.dry_run, skip_live_visual=args.skip_live_visual)
    if args.report:
        write_report(report, args.report)
    print_summary(report)
    if report["status"] in {"passed", "dry-run"}:
        return 0
    if report["status"] == "blocked":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
