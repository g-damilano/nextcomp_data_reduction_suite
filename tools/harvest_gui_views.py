from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import html
import json
import os
import shutil
import sys
import time
import traceback
import zipfile
import textwrap
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


DEFAULT_INPUT_GLOBS = ("datasets/**/*.mtdp",)
DEFAULT_METHOD = ROOT / "src" / "methods" / "iso14126"
DEFAULT_MAPPING = ROOT / "mappings" / "iso14126_manual.json"
HARVEST_SCHEMA = "gui_view_harvest.v0_1"
SCREEN_IDS = (
    "package_preview",
    "method_preview",
    "mapping_preview",
    "readiness_gate",
    "validation_gate",
    "acceptance_gate",
    "acceptance_review_spotlight",
    "acceptance_diagnostic_cockpit",
    "report_authoring",
    "output_review",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run MTDP packages through the method pipeline and harvest wizard view-model/card "
            "evidence for UX review."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Input .mtdp path or glob. Can be supplied more than once. Defaults to datasets/**/*.mtdp.",
    )
    parser.add_argument("--method", default=str(DEFAULT_METHOD), help="Method package directory.")
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING), help="Mapping JSON/YAML to use.")
    parser.add_argument(
        "--output",
        default="",
        help="Harvest output directory. Defaults to artifacts/gui_view_harvest/<timestamp>.",
    )
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--limit", type=int, default=0, help="Limit number of discovered inputs for smoke runs.")
    parser.add_argument("--include-fixtures", action="store_true", help="Also include tests/fixtures/**/*.mtdp.")
    parser.add_argument("--force", action="store_true", help="Remove an existing non-empty output directory first.")
    parser.add_argument("--generate-workbench", action="store_true", help="Also generate optional workbench folders.")
    parser.add_argument("--no-snapshots", action="store_true", help="Skip generated visual snapshot artifacts.")
    parser.add_argument(
        "--snapshot-mode",
        choices=("actual", "svg", "both"),
        default="actual",
        help="Snapshot mode. actual grabs rendered Qt widgets; svg writes deterministic contact-sheet fallbacks.",
    )
    parser.add_argument(
        "--qt-platform",
        default="",
        help="Optional QT_QPA_PLATFORM override for actual snapshots. Leave empty for the normal on-screen platform.",
    )
    parser.add_argument(
        "--no-keep-mtda",
        action="store_true",
        help="Delete generated .mtda files after extracting view evidence.",
    )
    args = parser.parse_args()

    output_root = Path(args.output).resolve() if args.output else _default_output_root()
    _prepare_output_dir(output_root, force=args.force)

    input_paths = discover_inputs(args.input, include_fixtures=args.include_fixtures)
    if args.limit > 0:
        input_paths = input_paths[: args.limit]
    if not input_paths:
        print("No .mtdp inputs discovered.", file=sys.stderr)
        return 2

    method_path = Path(args.method).resolve()
    mapping_path = Path(args.mapping).resolve()
    if not method_path.exists():
        print(f"Method path does not exist: {method_path}", file=sys.stderr)
        return 2
    if not mapping_path.exists():
        print(f"Mapping path does not exist: {mapping_path}", file=sys.stderr)
        return 2

    print(f"Harvesting {len(input_paths)} package(s) with {args.workers} worker(s).")
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    worker_args = [
        {
            "input_path": str(path),
            "method_path": str(method_path),
            "mapping_path": str(mapping_path),
            "output_root": str(output_root),
            "generate_workbench": bool(args.generate_workbench),
            "keep_mtda": not bool(args.no_keep_mtda),
            "snapshot_mode": "none" if args.no_snapshots else args.snapshot_mode,
            "qt_platform": str(args.qt_platform or ""),
        }
        for path in input_paths
    ]
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(harvest_one, item) for item in worker_args]
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            status = record.get("status", "unknown")
            print(f"[{status}] {record.get('case_id')} - {record.get('input_name')}")

    records.sort(key=lambda row: str(row.get("input_path", "")))
    completed_count = sum(1 for record in records if record.get("status") == "completed")
    not_ready_count = sum(1 for record in records if record.get("status") == "not_ready")
    failed_count = sum(1 for record in records if record.get("status") == "harvest_failed")
    manifest = {
        "schema_id": HARVEST_SCHEMA,
        "created_at": _utc_now(),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "method_path": str(method_path),
        "mapping_path": str(mapping_path),
        "output_root": str(output_root),
        "input_count": len(input_paths),
        "completed_count": completed_count,
        "not_ready_count": not_ready_count,
        "failed_count": failed_count,
        "unattended_count": sum(int(record.get("unattended_count") or 0) for record in records),
        "screen_ids": list(SCREEN_IDS),
        "records": records,
    }
    _write_json(output_root / "harvest_manifest.json", manifest)
    _write_summary_csv(output_root / "summary.csv", records)
    _write_diagnostic_cards_csv(output_root / "diagnostic_cards.csv", records)
    _write_unattended_csv(output_root / "unattended_findings.csv", records)
    (output_root / "index.html").write_text(render_index_html(manifest), encoding="utf-8")
    print(f"Wrote harvest: {output_root / 'index.html'}")
    return 0 if failed_count == 0 else 1


def discover_inputs(patterns: list[str], *, include_fixtures: bool = False) -> list[Path]:
    candidates: list[Path] = []
    use_patterns = patterns or list(DEFAULT_INPUT_GLOBS)
    if include_fixtures:
        use_patterns.append("tests/fixtures/**/*.mtdp")
    for pattern in use_patterns:
        matches = glob.glob(str(ROOT / pattern) if not Path(pattern).is_absolute() else pattern, recursive=True)
        if not matches and Path(pattern).suffix.lower() == ".mtdp":
            matches = [pattern]
        for match in matches:
            path = Path(match).resolve()
            if path.is_file() and path.suffix.lower() == ".mtdp":
                candidates.append(path)
    return sorted(set(candidates), key=lambda path: str(path).casefold())


def harvest_one(args: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    input_path = Path(str(args["input_path"])).resolve()
    method_path = Path(str(args["method_path"])).resolve()
    mapping_path = Path(str(args["mapping_path"])).resolve()
    output_root = Path(str(args["output_root"])).resolve()
    case_id = _case_slug(input_path)
    run_dir = output_root / "runs" / case_id
    view_dir = run_dir / "view_models"
    view_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / f"{case_id}.mtda"
    errors: list[dict[str, str]] = []
    view_models: dict[str, Any] = {}
    service_payload: dict[str, Any] = {}
    archive_payload: dict[str, Any] = {}
    review_rows: list[dict[str, Any]] = []
    diagnostic_cards: list[dict[str, Any]] = []
    unattended: list[dict[str, Any]] = []
    snapshot_refs: dict[str, Any] = {}

    try:
        from methods.core.method_run_service import MethodRunRequest, MethodRunService
        from ui.method_run_wizard.view_models import (
            acceptance_gate_view_model,
            mapping_preview_view_model,
            method_preview_view_model,
            output_review_view_model,
            package_preview_view_model,
            readiness_gate_view_model,
            report_authoring_view_model_from_report_payload,
            validation_gate_view_model,
        )

        service = MethodRunService()
        try:
            view_models["package_preview"] = package_preview_view_model(service.load_package(input_path))
        except Exception as exc:  # pragma: no cover - defensive harvest path
            errors.append(_error_record("package_preview", exc))
        try:
            view_models["method_preview"] = method_preview_view_model(service.load_method(method_path))
        except Exception as exc:  # pragma: no cover - defensive harvest path
            errors.append(_error_record("method_preview", exc))
        try:
            view_models["mapping_preview"] = mapping_preview_view_model(
                service.load_mapping(mapping_path, method_path=method_path, package_path=input_path)
            )
        except Exception as exc:  # pragma: no cover - defensive harvest path
            errors.append(_error_record("mapping_preview", exc))
        request = MethodRunRequest(
            input_package_path=input_path,
            method_path=method_path,
            mapping_path=mapping_path,
            output_path=output_path,
            overwrite=True,
            generate_workbench=bool(args.get("generate_workbench")),
        )
        try:
            readiness = service.check_readiness(request)
            view_models["readiness_gate"] = readiness_gate_view_model(readiness.to_dict())
        except Exception as exc:  # pragma: no cover - defensive harvest path
            errors.append(_error_record("readiness_gate", exc))
        result = service.run(request)
        service_payload = _service_result_payload(result)
        status = str(result.status)
        if result.output_path and Path(result.output_path).exists():
            archive_payload = _archive_payload(Path(result.output_path))
            method_outputs = archive_payload.get("method_outputs", {})
            acceptance_report = (
                method_outputs.get("acceptance_report")
                if isinstance(method_outputs.get("acceptance_report"), dict)
                else result.acceptance_report
            )
            validation_report = method_outputs.get("validation_report") if isinstance(method_outputs.get("validation_report"), dict) else archive_payload.get("validation", {})
            readiness_report = method_outputs.get("readiness_report") if isinstance(method_outputs.get("readiness_report"), dict) else archive_payload.get("readiness", {})
            final_report_runs = _list_of_dicts(method_outputs.get("final_report_runs"))
            final_membership = _list_of_dicts(method_outputs.get("selection_membership"))
            view_models["readiness_gate"] = readiness_gate_view_model(readiness_report or {})
            view_models["validation_gate"] = validation_gate_view_model(validation_report or result.validation_summary)
            view_models["acceptance_gate"] = acceptance_gate_view_model(
                acceptance_report,
                final_selection_sets=_dict_or_empty(method_outputs.get("selection_sets")),
                final_membership=final_membership,
                final_report_runs=final_report_runs,
                human_decisions=_dict_or_empty(method_outputs.get("human_decisions")),
                override_ledger=_dict_or_empty(method_outputs.get("override_ledger")),
            )
            view_models["output_review"] = output_review_view_model(
                {
                    **service_payload,
                    "surface_manifest": archive_payload.get("surface_manifest", {}),
                    "archive_members": archive_payload.get("archive_members", []),
                }
            )
            if archive_payload.get("test_report"):
                view_models["report_authoring"] = report_authoring_view_model_from_report_payload(archive_payload["test_report"])
            review_rows = build_acceptance_review_rows(
                acceptance_report,
                mtda_path=Path(result.output_path),
                method_outputs=method_outputs,
            )
            diagnostic_cards = diagnostic_card_rows(case_id, review_rows)
            view_models["acceptance_review_spotlight"] = acceptance_review_spotlight_harvest_view(review_rows)
            view_models["acceptance_diagnostic_cockpit"] = acceptance_diagnostic_cockpit_harvest_view(diagnostic_cards, review_rows)
            unattended = unattended_findings(case_id, acceptance_report, review_rows, view_models, case_status=status)
        else:
            status = str(result.status or "not_ready")
            view_models["validation_gate"] = validation_gate_view_model(result.validation_summary or {})
            view_models["acceptance_gate"] = acceptance_gate_view_model(result.acceptance_report or {})
            view_models["output_review"] = output_review_view_model(service_payload)
            view_models["acceptance_review_spotlight"] = acceptance_review_spotlight_harvest_view(review_rows)
            view_models["acceptance_diagnostic_cockpit"] = acceptance_diagnostic_cockpit_harvest_view(diagnostic_cards, review_rows)
            unattended = unattended_findings(case_id, result.acceptance_report or {}, review_rows, view_models, case_status=status)

        for screen_id, payload in view_models.items():
            _write_json(view_dir / f"{screen_id}.json", payload)
        _write_json(run_dir / "service_result.json", service_payload)
        _write_json(run_dir / "acceptance_review_rows.json", review_rows)
        _write_json(run_dir / "diagnostic_cards.json", diagnostic_cards)
        _write_json(run_dir / "unattended_findings.json", unattended)
        if args.get("snapshot_mode") != "none":
            snapshot_refs = write_visual_snapshots(
                case_id,
                run_dir,
                input_path=input_path,
                method_path=method_path,
                mapping_path=mapping_path,
                output_path=output_path if output_path.exists() else None,
                service_payload=service_payload,
                readiness_report=archive_payload.get("readiness") or service_payload.get("readiness_summary") or {},
                validation_report=archive_payload.get("validation") or service_payload.get("validation_summary") or {},
                acceptance_report=archive_payload.get("method_outputs", {}).get("acceptance_report")
                if isinstance(archive_payload.get("method_outputs", {}).get("acceptance_report"), dict)
                else service_payload.get("acceptance_report") or {},
                view_models=view_models,
                review_rows=review_rows,
                diagnostic_cards=diagnostic_cards,
                unattended_findings=unattended,
                mode=str(args.get("snapshot_mode") or "both"),
                qt_platform=str(args.get("qt_platform") or ""),
            )
        if not args.get("keep_mtda") and output_path.exists():
            output_path.unlink()

        return {
            "schema_id": "gui_view_harvest.case.v0_1",
            "case_id": case_id,
            "input_path": str(input_path),
            "input_name": input_path.name,
            "run_dir": str(run_dir),
            "run_dir_ref": f"runs/{case_id}/",
            "mtda_path": str(output_path) if output_path.exists() else "",
            "status": status,
            "readiness_status": service_payload.get("readiness_status", ""),
            "elapsed_seconds": round(time.perf_counter() - start, 3),
            "screen_inventory": screen_inventory(view_models),
            "review_row_count": len(review_rows),
            "diagnostic_card_count": len(diagnostic_cards),
            "unattended_count": len(unattended),
            "errors": errors,
            "view_models": {key: f"runs/{case_id}/view_models/{key}.json" for key in sorted(view_models)},
            "diagnostic_cards": f"runs/{case_id}/diagnostic_cards.json",
            "unattended_findings": f"runs/{case_id}/unattended_findings.json",
            "snapshots": snapshot_refs,
        }
    except Exception as exc:  # pragma: no cover - defensive harvest path
        errors.append(_error_record("harvest_one", exc))
        _write_json(run_dir / "errors.json", errors)
        return {
            "schema_id": "gui_view_harvest.case.v0_1",
            "case_id": case_id,
            "input_path": str(input_path),
            "input_name": input_path.name,
            "run_dir": str(run_dir),
            "run_dir_ref": f"runs/{case_id}/",
            "mtda_path": str(output_path) if output_path.exists() else "",
            "status": "harvest_failed",
            "readiness_status": "",
            "elapsed_seconds": round(time.perf_counter() - start, 3),
            "screen_inventory": [],
            "review_row_count": 0,
            "diagnostic_card_count": 0,
            "unattended_count": 1,
            "errors": errors,
            "view_models": {},
            "diagnostic_cards": "",
            "unattended_findings": "errors.json",
            "snapshots": {},
        }


def build_acceptance_review_rows(
    acceptance_report: dict[str, Any],
    *,
    mtda_path: Path | None = None,
    method_outputs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(acceptance_report, dict):
        return []
    try:
        from ui.method_run_wizard.controller import _review_evidence_from_mtda, _row_models_from_acceptance_report
    except Exception:
        return []

    evidence_by_run: dict[str, dict[str, Any]] = {}
    if mtda_path is not None and mtda_path.exists():
        evidence_by_run.update(_review_evidence_from_mtda(mtda_path))
    evidence_by_run = _merge_evidence(evidence_by_run, _aligned_method_output_evidence(method_outputs or {}))
    models = _row_models_from_acceptance_report(acceptance_report, evidence_by_run=evidence_by_run)
    return [_run_model_payload(model) for model in models]


def diagnostic_card_rows(case_id: str, review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review in review_rows:
        for defect_index, cockpit in enumerate(_review_cockpits(review), start=1):
            for card in cockpit.get("cards", []) if isinstance(cockpit, dict) else []:
                if not isinstance(card, dict):
                    continue
                rows.append(
                    {
                        "case_id": case_id,
                        "run_id": review.get("run_id", ""),
                        "defect_index": defect_index,
                        "view_id": cockpit.get("view_id", ""),
                        "plot_kind": (cockpit.get("plot_contract") or {}).get("plot_kind", ""),
                        "evidence_key": card.get("evidence_key", ""),
                        "label": card.get("label", ""),
                        "value": card.get("value", ""),
                        "subtext": card.get("subtext", ""),
                        "state": card.get("state", ""),
                        "level": card.get("level", ""),
                        "required": card.get("required", ""),
                    }
                )
    return rows


def acceptance_review_spotlight_harvest_view(review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_name": "acceptance_review_spotlight_harvest",
        "version": "0.1.0",
        "status": "available",
        "rows": review_rows,
        "row_count": len(review_rows),
        "flagged_row_count": sum(1 for row in review_rows if row.get("acceptance_flags")),
        "excluded_row_count": sum(1 for row in review_rows if row.get("is_excluded")),
    }


def acceptance_diagnostic_cockpit_harvest_view(
    diagnostic_cards: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cockpit_ids = sorted(
        {
            str(cockpit.get("view_id") or "")
            for row in review_rows
            for cockpit in _review_cockpits(row)
        }
        - {""}
    )
    return {
        "schema_name": "acceptance_diagnostic_cockpit_harvest",
        "version": "0.1.0",
        "status": "available",
        "cards": diagnostic_cards,
        "card_count": len(diagnostic_cards),
        "cockpit_ids": cockpit_ids,
        "row_count": len(review_rows),
    }


def unattended_findings(
    case_id: str,
    acceptance_report: dict[str, Any],
    review_rows: list[dict[str, Any]],
    view_models: dict[str, Any],
    *,
    case_status: str = "completed",
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    flags = acceptance_report.get("flags") if isinstance(acceptance_report, dict) else []
    flag_count = len(flags) if isinstance(flags, list) else 0
    if flag_count and not review_rows:
        findings.append(
            _finding(
                case_id,
                "acceptance_review_spotlight",
                "acceptance_flags_not_surfaced",
                f"{flag_count} acceptance flag(s) exist but no review row was harvested.",
            )
        )
    for screen_id in SCREEN_IDS:
        payload = view_models.get(screen_id)
        if payload is None:
            if case_status != "completed" and screen_id in {"report_authoring"}:
                continue
            findings.append(_finding(case_id, screen_id, "screen_not_harvested", "No view model was harvested."))
            continue
        cards = _screen_cards(payload)
        if screen_id in {"package_preview", "method_preview", "readiness_gate", "validation_gate", "acceptance_gate"} and not cards:
            findings.append(_finding(case_id, screen_id, "screen_cards_empty", "Expected summary cards are empty."))
    for row in review_rows:
        run_id = str(row.get("run_id") or "")
        cockpits = _review_cockpits(row)
        if not cockpits:
            findings.append(_finding(case_id, "acceptance_diagnostic_cockpit", "missing_cockpit", "Review row has no diagnostic cockpit.", run_id=run_id))
            continue
        for cockpit in cockpits:
            view_id = str(cockpit.get("view_id") or "")
            if view_id.startswith("unsupported"):
                findings.append(_finding(case_id, view_id, "unsupported_diagnostic_view", "Diagnostic fell back to unsupported placeholder.", run_id=run_id))
            cards = cockpit.get("cards") if isinstance(cockpit.get("cards"), list) else []
            if not cards:
                findings.append(_finding(case_id, view_id, "diagnostic_cards_empty", "Diagnostic cockpit has no cards.", run_id=run_id))
            for card in cards:
                if isinstance(card, dict) and str(card.get("state") or "") == "gap":
                    findings.append(
                        _finding(
                            case_id,
                            view_id,
                            "diagnostic_card_evidence_gap",
                            f"{card.get('label', '')}: {card.get('subtext', '')}",
                            run_id=run_id,
                            evidence_key=str(card.get("evidence_key") or ""),
                        )
                    )
            packet = cockpit.get("evidence_packet") if isinstance(cockpit.get("evidence_packet"), dict) else {}
            missing = packet.get("missing_required_keys") if isinstance(packet.get("missing_required_keys"), list) else []
            for key in missing:
                findings.append(_finding(case_id, view_id, "missing_required_evidence", str(key), run_id=run_id, evidence_key=str(key)))
            plot_contract = cockpit.get("plot_contract") if isinstance(cockpit.get("plot_contract"), dict) else {}
            plot_missing = plot_contract.get("missing_required_keys") if isinstance(plot_contract.get("missing_required_keys"), list) else []
            for key in plot_missing:
                findings.append(_finding(case_id, view_id, "missing_plot_evidence", str(key), run_id=run_id, evidence_key=str(key)))
    return findings


def screen_inventory(view_models: dict[str, Any]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for screen_id in SCREEN_IDS:
        payload = view_models.get(screen_id)
        if payload is None:
            inventory.append({"screen_id": screen_id, "harvested": False, "card_count": 0, "row_count": 0, "status": "missing"})
            continue
        inventory.append(
            {
                "screen_id": screen_id,
                "harvested": True,
                "card_count": len(_screen_cards(payload)),
                "row_count": _screen_row_count(payload),
                "status": str(payload.get("status") or payload.get("schema_name") or "available") if isinstance(payload, dict) else "available",
            }
        )
    return inventory


def write_visual_snapshots(
    case_id: str,
    run_dir: Path,
    *,
    input_path: Path,
    method_path: Path,
    mapping_path: Path,
    output_path: Path | None,
    service_payload: dict[str, Any],
    readiness_report: dict[str, Any],
    validation_report: dict[str, Any],
    acceptance_report: dict[str, Any],
    view_models: dict[str, Any],
    review_rows: list[dict[str, Any]],
    diagnostic_cards: list[dict[str, Any]],
    unattended_findings: list[dict[str, Any]],
    mode: str = "both",
    qt_platform: str = "",
) -> dict[str, Any]:
    snapshot_dir = run_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    refs: dict[str, Any] = {"index": f"runs/{case_id}/snapshots/index.html", "actual": {}, "svg": {}, "errors": []}
    screen_payloads = dict(view_models)
    screen_payloads.setdefault("acceptance_review_spotlight", acceptance_review_spotlight_harvest_view(review_rows))
    screen_payloads.setdefault("acceptance_diagnostic_cockpit", acceptance_diagnostic_cockpit_harvest_view(diagnostic_cards, review_rows))
    if mode in {"actual", "both"}:
        try:
            refs["actual"] = write_qt_actual_snapshots(
                case_id,
                snapshot_dir,
                input_path=input_path,
                method_path=method_path,
                mapping_path=mapping_path,
                output_path=output_path,
                service_payload=service_payload,
                readiness_report=readiness_report,
                validation_report=validation_report,
                acceptance_report=acceptance_report,
                qt_platform=qt_platform,
            )
        except Exception as exc:  # pragma: no cover - platform-dependent visual fallback path
            refs["errors"].append(_error_record("qt_actual_snapshots", exc))
            _write_json(snapshot_dir / "actual_snapshot_errors.json", refs["errors"])
    if mode in {"svg", "both"} or not refs["actual"]:
        svg_refs: dict[str, str] = {}
        for screen_id in SCREEN_IDS:
            payload = screen_payloads.get(screen_id, {})
            findings = _snapshot_findings_for_screen(screen_id, unattended_findings)
            svg = render_screen_snapshot_svg(case_id, screen_id, payload, findings)
            filename = f"{screen_id}.svg"
            (snapshot_dir / filename).write_text(svg, encoding="utf-8")
            svg_refs[screen_id] = f"runs/{case_id}/snapshots/{filename}"
        refs["svg"] = svg_refs
    (snapshot_dir / "index.html").write_text(
        render_case_snapshot_gallery(case_id, actual_refs=refs["actual"], svg_refs=refs["svg"], errors=refs["errors"]),
        encoding="utf-8",
    )
    return refs


def write_qt_actual_snapshots(
    case_id: str,
    snapshot_dir: Path,
    *,
    input_path: Path,
    method_path: Path,
    mapping_path: Path,
    output_path: Path | None,
    service_payload: dict[str, Any],
    readiness_report: dict[str, Any],
    validation_report: dict[str, Any],
    acceptance_report: dict[str, Any],
    qt_platform: str = "",
) -> dict[str, str]:
    previous_platform = os.environ.get("QT_QPA_PLATFORM")
    if qt_platform:
        os.environ["QT_QPA_PLATFORM"] = qt_platform
    try:
        from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets
        from ui.method_run_wizard.controller import MethodRunController
        from ui.method_run_wizard.state import MethodRunWizardState, WizardScenario
        from ui.method_run_wizard.window import MethodRunWindow

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        actual_dir = snapshot_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)
        state = MethodRunWizardState(
            input_package_path=input_path,
            method_path=method_path,
            mapping_path=mapping_path,
            output_path=output_path,
            readiness_report=readiness_report or None,
            service_result=service_payload,
            execution_status=str(service_payload.get("status") or "not_started"),
            validation_summary=validation_report or None,
            acceptance_summary=acceptance_report or None,
            mapping_decision_made=True,
            metadata_decision_made=False,
        )
        window = MethodRunWindow(package_path=input_path)
        controller = MethodRunController(window, state)
        window.resize(1280, 820)
        window.show()
        _qt_process(app)
        refs: dict[str, str] = {}

        controller.state.scenario = WizardScenario.SETUP
        window.set_scenario(WizardScenario.SETUP)
        controller._update_setup_action_bar()
        refs["setup"] = _save_qt_snapshot(window, actual_dir / "setup.png", app, case_id)

        if output_path is not None and output_path.exists() and acceptance_report:
            controller._enter_review()
            refs["review"] = _save_qt_snapshot(window, actual_dir / "review.png", app, case_id)
            for run_id, row in sorted(window.review_spotlight.rows.items()):
                if not run_id:
                    continue
                row.set_expanded(True)
                window.scroll_area.ensureWidgetVisible(row, 20, 20)
                _qt_process(app)
                refs[f"review_{_safe_filename(run_id)}"] = _save_qt_snapshot(
                    window,
                    actual_dir / f"review_{_safe_filename(run_id)}.png",
                    app,
                    case_id,
                )
                tabs = row._detail.findChild(QtWidgets.QTabWidget, "diagnosticCockpitTabs")
                if tabs is not None and tabs.count() > 1:
                    for index in range(tabs.count()):
                        tabs.setCurrentIndex(index)
                        _qt_process(app)
                        tab_name = _safe_filename(tabs.tabText(index))
                        refs[f"review_{_safe_filename(run_id)}_defect_{index + 1}_{tab_name}"] = _save_qt_snapshot(
                            window,
                            actual_dir / f"review_{_safe_filename(run_id)}_defect_{index + 1}_{tab_name}.png",
                            app,
                            case_id,
                        )
                row.set_expanded(False)
            controller._enter_finalize()
            refs["finalize"] = _save_qt_snapshot(window, actual_dir / "finalize.png", app, case_id)

        window.close()
        window.deleteLater()
        _qt_process(app)
        return {key: f"runs/{case_id}/snapshots/actual/{Path(path).name}" for key, path in refs.items()}
    finally:
        if qt_platform:
            if previous_platform is None:
                os.environ.pop("QT_QPA_PLATFORM", None)
            else:
                os.environ["QT_QPA_PLATFORM"] = previous_platform


def render_case_snapshot_gallery(
    case_id: str,
    *,
    actual_refs: dict[str, str],
    svg_refs: dict[str, str],
    errors: list[dict[str, str]] | None = None,
) -> str:
    cards = []
    for label, ref in actual_refs.items():
        if not ref:
            continue
        filename = ref.rsplit("/", 1)[-1]
        cards.append(
            "<article>"
            f"<h2>Actual Qt: {html.escape(label)}</h2>"
            f'<a href="actual/{html.escape(filename)}"><img src="actual/{html.escape(filename)}" alt="{html.escape(label)} actual snapshot"></a>'
            "</article>"
        )
    for screen_id in SCREEN_IDS:
        ref = svg_refs.get(screen_id)
        if not ref:
            continue
        filename = ref.rsplit("/", 1)[-1]
        cards.append(
            "<article class=\"proxy\">"
            f"<h2>Fallback SVG: {html.escape(screen_id)}</h2>"
            f'<a href="{html.escape(filename)}"><img src="{html.escape(filename)}" alt="{html.escape(screen_id)} fallback snapshot"></a>'
            "</article>"
        )
    error_html = ""
    if errors:
        error_items = "".join(f"<li>{html.escape(str(row.get('message') or row))}</li>" for row in errors)
        error_html = f"<section class=\"errors\"><h2>Actual Snapshot Errors</h2><ul>{error_items}</ul></section>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(case_id)} Snapshots</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;background:#f6f8fb;color:#17202a}}
main{{max-width:1500px;margin:0 auto}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}}
article{{background:white;border:1px solid #d7dde5;border-radius:8px;padding:12px}}h1{{margin-bottom:8px}}h2{{font-size:15px;margin:0 0 10px}}
article.proxy{{border-style:dashed}}.errors{{background:#fff3cd;border:1px solid #f0c36d;border-radius:8px;padding:12px;margin:12px 0}}
img{{width:100%;height:auto;border:1px solid #e3e8ef;border-radius:6px;background:white}}
</style></head><body><main><h1>{html.escape(case_id)} Visual Snapshots</h1>
<p>Actual Qt PNGs are direct grabs of the rendered Method Run window. Fallback SVGs are a generated contact sheet from harvested data and should be treated as a proxy only.</p>
{error_html}<div class="grid">{''.join(cards)}</div></main></body></html>"""


def render_screen_snapshot_svg(
    case_id: str,
    screen_id: str,
    payload: Any,
    findings: list[dict[str, Any]] | None = None,
) -> str:
    findings = findings or []
    width = 1200
    margin = 28
    content_width = width - margin * 2
    elements: list[str] = []
    y = margin

    def rect(x: int, y0: int, w: int, h: int, fill: str, stroke: str = "#d7dde5", radius: int = 8) -> None:
        elements.append(
            f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" />'
        )

    def text(x: int, y0: int, value: Any, *, size: int = 14, fill: str = "#17202a", weight: int = 400) -> None:
        elements.append(
            f'<text x="{x}" y="{y0}" font-size="{size}" font-weight="{weight}" fill="{fill}">{_svg_escape(value)}</text>'
        )

    def wrapped_text(
        x: int,
        y0: int,
        value: Any,
        *,
        max_width: int,
        size: int = 13,
        fill: str = "#17202a",
        weight: int = 400,
        max_lines: int = 3,
    ) -> int:
        text_value = str(value or "")
        chars = max(16, int(max_width / max(size * 0.56, 1)))
        lines = textwrap.wrap(text_value, width=chars, break_long_words=False, replace_whitespace=False) or [""]
        lines = lines[:max_lines]
        for index, line in enumerate(lines):
            suffix = "..." if index == max_lines - 1 and len(textwrap.wrap(text_value, width=chars)) > max_lines else ""
            elements.append(
                f'<text x="{x}" y="{y0 + index * (size + 5)}" font-size="{size}" font-weight="{weight}" fill="{fill}">{_svg_escape(line + suffix)}</text>'
            )
        return y0 + len(lines) * (size + 5)

    rect(0, 0, width, 40, "#f3f6fa", "#f3f6fa", 0)
    text(margin, y + 4, screen_id.replace("_", " ").title(), size=24, weight=700)
    status = _snapshot_status(payload)
    badge_fill, badge_stroke, badge_text = _snapshot_palette(status)
    rect(width - 220, y - 14, 190, 32, badge_fill, badge_stroke, 16)
    text(width - 198, y + 6, status or "available", size=13, fill=badge_text, weight=700)
    y += 36
    wrapped_text(margin, y, f"{case_id} - {_snapshot_schema(payload)}", max_width=content_width, size=13, fill="#5d6876", max_lines=2)
    y += 34

    key_values = _snapshot_key_values(payload)
    if key_values:
        y = _draw_snapshot_cards(elements, key_values, margin, y, content_width, value_key="value", compact=True)
        y += 12

    cards = _snapshot_cards(payload)
    if cards:
        text(margin, y, "Cards", size=16, weight=700)
        y += 12
        y = _draw_snapshot_cards(elements, cards[:18], margin, y, content_width)
        if len(cards) > 18:
            text(margin, y + 16, f"+{len(cards) - 18} more cards", size=12, fill="#5d6876")
            y += 36
        else:
            y += 12

    if findings:
        text(margin, y, "Red-Team Findings", size=16, weight=700)
        y += 12
        y = _draw_snapshot_rows(elements, findings[:8], margin, y, content_width, force_columns=("run_id", "screen_id", "finding_type", "detail"))
        if len(findings) > 8:
            text(margin, y + 16, f"+{len(findings) - 8} more findings", size=12, fill="#5d6876")
            y += 36
        else:
            y += 12

    rows = _snapshot_rows(screen_id, payload)
    if rows:
        text(margin, y, "Rows", size=16, weight=700)
        y += 12
        y = _draw_snapshot_rows(elements, rows[:12], margin, y, content_width)
        if len(rows) > 12:
            text(margin, y + 16, f"+{len(rows) - 12} more rows", size=12, fill="#5d6876")
            y += 36
        else:
            y += 12

    if not key_values and not cards and not findings and not rows:
        rect(margin, y, content_width, 84, "#ffffff")
        text(margin + 18, y + 34, "No visual data harvested for this screen.", size=16, fill="#5d6876", weight=700)
        y += 108

    height = max(360, y + margin)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="#f6f8fb"/>'
        f'<style>text{{font-family:Segoe UI, Arial, sans-serif}}</style>'
        f'{"".join(elements)}'
        "</svg>"
    )


def _qt_process(app: Any, rounds: int = 3) -> None:
    for _ in range(rounds):
        app.processEvents()


def _save_qt_snapshot(widget: Any, path: Path, app: Any, case_id: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    _qt_process(app)
    widget.repaint()
    _qt_process(app)
    pixmap = widget.grab()
    if not pixmap.save(str(path), "PNG"):
        raise RuntimeError(f"Could not save Qt snapshot for {case_id}: {path}")
    return str(path)


def _safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in str(value)).strip("_")
    return safe or "snapshot"


def _snapshot_findings_for_screen(screen_id: str, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if screen_id == "acceptance_diagnostic_cockpit":
        return [
            finding
            for finding in findings
            if str(finding.get("screen_id") or "") not in SCREEN_IDS
            or str(finding.get("finding_type") or "") in {"diagnostic_card_evidence_gap", "missing_required_evidence", "missing_plot_evidence"}
        ]
    return [finding for finding in findings if str(finding.get("screen_id") or "") == screen_id]


def _snapshot_status(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "missing"
    for key in ("status", "readiness_status", "schema_name"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return "available"


def _snapshot_schema(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "no payload"
    return str(payload.get("schema_name") or payload.get("gate_id") or payload.get("version") or "view model")


def _snapshot_key_values(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows: list[dict[str, Any]] = []
    scalar_keys = (
        "schema_name",
        "status",
        "gate_id",
        "package_name",
        "method_name",
        "mapping_id",
        "run_count",
        "row_count",
        "card_count",
        "diagnostic_card_count",
        "source_file_count",
        "critical_bound_count",
        "next_enabled",
    )
    for key in scalar_keys:
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)) and value not in ("", None):
            rows.append({"label": key, "value": value, "status": "neutral"})
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for key, value in list(summary.items())[:8]:
        if isinstance(value, (str, int, float, bool)) and value not in ("", None):
            rows.append({"label": f"summary.{key}", "value": value, "status": "neutral"})
    final_selection = payload.get("final_selection") if isinstance(payload.get("final_selection"), dict) else {}
    for key, value in list(final_selection.items())[:4]:
        if isinstance(value, (str, int, float, bool)) and value not in ("", None):
            rows.append({"label": f"final.{key}", "value": value, "status": "neutral"})
    return rows[:12]


def _snapshot_cards(payload: Any) -> list[dict[str, Any]]:
    cards = _screen_cards(payload)
    return [dict(card) for card in cards if isinstance(card, dict)]


def _snapshot_rows(screen_id: str, payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if screen_id == "acceptance_diagnostic_cockpit":
        return [dict(row) for row in payload.get("cards", []) if isinstance(row, dict)]
    priority = (
        "attention_rows",
        "missing_rows",
        "blocking_rows",
        "run_rows",
        "rows",
        "source_files",
        "fields",
    )
    for key in priority:
        value = payload.get(key)
        if isinstance(value, list) and value:
            return [dict(row) for row in value if isinstance(row, dict)]
    groups = payload.get("groups")
    if isinstance(groups, list) and groups:
        out: list[dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            rows = group.get("rows") if isinstance(group.get("rows"), list) else []
            out.append(
                {
                    "group_id": group.get("group_id", ""),
                    "label": group.get("label", ""),
                    "status": group.get("status", ""),
                    "row_count": len(rows),
                }
            )
        return out
    return []


def _snapshot_columns(rows: list[dict[str, Any]]) -> list[str]:
    preferred = (
        "run_id",
        "label",
        "value",
        "state",
        "status",
        "severity",
        "finding_type",
        "detail",
        "method_field",
        "source",
        "mapped_source",
        "message",
        "reason",
        "default_call",
        "evidence_key",
        "screen_id",
        "group_id",
        "row_count",
    )
    present = {key for row in rows for key in row}
    columns = [key for key in preferred if key in present]
    if len(columns) < 4:
        columns.extend(key for key in sorted(present) if key not in columns)
    return columns[:5]


def _snapshot_palette(status: Any) -> tuple[str, str, str]:
    folded = str(status or "").casefold()
    if any(token in folded for token in ("fail", "err", "missing", "gap", "block", "not_ready")):
        return "#fff1f0", "#f0b8b2", "#b42318"
    if any(token in folded for token in ("warn", "review", "draft", "incomplete")):
        return "#fff8e1", "#e4c362", "#8a5a00"
    if any(token in folded for token in ("pass", "ok", "ready", "completed", "available", "active")):
        return "#ecfdf3", "#9bd6af", "#146c43"
    return "#f5f7fb", "#d7dde5", "#344054"


def _svg_escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _svg_text(
    elements: list[str],
    x: int,
    y: int,
    value: Any,
    size: int,
    fill: str,
    weight: int,
) -> None:
    elements.append(
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}">{_svg_escape(value)}</text>'
    )


def _svg_wrapped_text(
    elements: list[str],
    x: int,
    y: int,
    value: Any,
    max_width: int,
    size: int,
    fill: str,
    weight: int,
    *,
    max_lines: int,
) -> int:
    text_value = str(value if value is not None else "")
    chars = max(12, int(max_width / max(size * 0.56, 1)))
    wrapped = textwrap.wrap(text_value, width=chars, break_long_words=False, replace_whitespace=False) or [""]
    visible = wrapped[:max_lines]
    for index, line in enumerate(visible):
        suffix = "..." if index == max_lines - 1 and len(wrapped) > max_lines else ""
        _svg_text(elements, x, y + index * (size + 5), line + suffix, size, fill, weight)
    return y + len(visible) * (size + 5)


def _draw_snapshot_cards(
    elements: list[str],
    cards: list[dict[str, Any]],
    x: int,
    y: int,
    width: int,
    *,
    value_key: str = "value",
    compact: bool = False,
) -> int:
    columns = 4 if compact else 3
    gap = 12
    card_w = int((width - gap * (columns - 1)) / columns)
    card_h = 74 if compact else 92
    for index, card in enumerate(cards):
        cx = x + (index % columns) * (card_w + gap)
        cy = y + (index // columns) * (card_h + gap)
        status = str(card.get("state") or card.get("status") or card.get("level") or "")
        fill, stroke, accent = _snapshot_palette(status)
        elements.append(f'<rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="8" fill="{fill}" stroke="{stroke}" />')
        elements.append(f'<rect x="{cx}" y="{cy}" width="5" height="{card_h}" rx="3" fill="{accent}" stroke="{accent}" />')
        _svg_text(elements, cx + 16, cy + 23, card.get("label") or card.get("key") or "Card", 12, "#5d6876", 700)
        _svg_wrapped_text(elements, cx + 16, cy + 47, card.get(value_key, ""), card_w - 30, 18 if compact else 20, "#17202a", 700, max_lines=1)
        if not compact:
            _svg_wrapped_text(elements, cx + 16, cy + 71, card.get("subtext") or card.get("status") or "", card_w - 30, 12, "#5d6876", 400, max_lines=1)
    rows = (len(cards) + columns - 1) // columns
    return y + rows * card_h + max(0, rows - 1) * gap


def _draw_snapshot_rows(
    elements: list[str],
    rows: list[dict[str, Any]],
    x: int,
    y: int,
    width: int,
    *,
    force_columns: tuple[str, ...] | None = None,
) -> int:
    columns = list(force_columns or _snapshot_columns(rows))
    if not columns:
        return y
    col_w = int(width / len(columns))
    header_h = 30
    row_h = 54
    elements.append(f'<rect x="{x}" y="{y}" width="{width}" height="{header_h}" rx="6" fill="#e9eef5" stroke="#d7dde5" />')
    for index, column in enumerate(columns):
        _svg_text(elements, x + index * col_w + 10, y + 20, column, 12, "#344054", 700)
    y += header_h
    for row in rows:
        elements.append(f'<rect x="{x}" y="{y}" width="{width}" height="{row_h}" fill="#ffffff" stroke="#e3e8ef" />')
        for index, column in enumerate(columns):
            _svg_wrapped_text(elements, x + index * col_w + 10, y + 20, row.get(column, ""), col_w - 20, 12, "#17202a", 400, max_lines=2)
        y += row_h
    return y


def render_index_html(manifest: dict[str, Any]) -> str:
    records = manifest.get("records", []) if isinstance(manifest.get("records"), list) else []
    rows = "\n".join(_case_html(record) for record in records if isinstance(record, dict))
    unattended = "\n".join(
        _finding_html(record, finding)
        for record in records
        if isinstance(record, dict)
        for finding in _read_case_findings(record)
    )
    if not unattended:
        unattended = '<tr><td colspan="5">No unattended findings harvested.</td></tr>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>GUI View Harvest</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;color:#17202a;background:#f7f9fb;line-height:1.4}}
main{{max-width:1500px;margin:0 auto}}table{{width:100%;border-collapse:collapse;background:white;margin:14px 0 28px}}
th,td{{border:1px solid #d7dde5;padding:7px 9px;text-align:left;vertical-align:top;font-size:13px}}th{{background:#eef2f6}}
.card{{display:inline-block;border:1px solid #d7dde5;border-radius:8px;background:white;padding:8px 10px;margin:4px 8px 4px 0}}
.ok{{color:#146c43}}.warn{{color:#8a5a00}}.fail{{color:#b42318}}code{{font-family:Consolas,monospace;font-size:12px}}
</style></head><body><main>
<h1>GUI View Harvest</h1>
<p>Created {html.escape(str(manifest.get("created_at", "")))} from {html.escape(str(manifest.get("input_count", "")))} package(s).</p>
<div class="card">Completed: {html.escape(str(manifest.get("completed_count", 0)))}</div>
<div class="card">Not ready: {html.escape(str(manifest.get("not_ready_count", 0)))}</div>
<div class="card">Failed: {html.escape(str(manifest.get("failed_count", 0)))}</div>
<div class="card">Unattended findings: {html.escape(str(manifest.get("unattended_count", 0)))}</div>
<h2>Cases</h2>
<table><thead><tr><th>Case</th><th>Status</th><th>Readiness</th><th>Screens</th><th>Review/Card Coverage</th><th>Links</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Unattended Findings</h2>
<table><thead><tr><th>Case</th><th>Run</th><th>Screen</th><th>Finding</th><th>Detail</th></tr></thead><tbody>{unattended}</tbody></table>
</main></body></html>"""


def _case_html(record: dict[str, Any]) -> str:
    inventory = record.get("screen_inventory") if isinstance(record.get("screen_inventory"), list) else []
    screens = ", ".join(
        f"{item.get('screen_id')}:{item.get('card_count', 0)}"
        for item in inventory
        if isinstance(item, dict) and item.get("harvested")
    )
    links = []
    if record.get("diagnostic_cards"):
        links.append(f'<a href="{html.escape(str(record["diagnostic_cards"]))}">cards</a>')
    if record.get("unattended_findings"):
        links.append(f'<a href="{html.escape(str(record["unattended_findings"]))}">findings</a>')
    snapshots = record.get("snapshots") if isinstance(record.get("snapshots"), dict) else {}
    if snapshots.get("index"):
        links.append(f'<a href="{html.escape(str(snapshots["index"]))}">snapshots</a>')
    if isinstance(record.get("view_models"), dict):
        links.append(f'<a href="{html.escape(str(record.get("run_dir_ref") or record.get("run_dir", "")))}">run dir</a>')
    status_class = "ok" if record.get("status") == "completed" else "fail"
    return (
        "<tr>"
        f"<td><code>{html.escape(str(record.get('case_id', '')))}</code><br>{html.escape(str(record.get('input_name', '')))}</td>"
        f"<td class=\"{status_class}\">{html.escape(str(record.get('status', '')))}</td>"
        f"<td>{html.escape(str(record.get('readiness_status', '')))}</td>"
        f"<td>{html.escape(screens)}</td>"
        f"<td>{html.escape(str(record.get('review_row_count', 0)))} review rows / {html.escape(str(record.get('diagnostic_card_count', 0)))} cards / {html.escape(str(record.get('unattended_count', 0)))} findings</td>"
        f"<td>{' | '.join(links)}</td>"
        "</tr>"
    )


def _finding_html(record: dict[str, Any], finding: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td><code>{html.escape(str(record.get('case_id', '')))}</code></td>"
        f"<td>{html.escape(str(finding.get('run_id', '')))}</td>"
        f"<td>{html.escape(str(finding.get('screen_id', '')))}</td>"
        f"<td class=\"warn\">{html.escape(str(finding.get('finding_type', '')))}</td>"
        f"<td>{html.escape(str(finding.get('detail', '')))}</td>"
        "</tr>"
    )


def _archive_payload(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"archive_members": [], "method_outputs": {}, "surface_manifest": {}, "validation": {}, "readiness": {}, "test_report": {}}
    try:
        with zipfile.ZipFile(path) as archive:
            payload["archive_members"] = sorted(name for name in archive.namelist() if not name.endswith("/"))
            payload["method_outputs"] = _json_member(archive, "metadata/software/method_outputs.json")
            payload["surface_manifest"] = _json_member(archive, "metadata/surface_manifest.json")
            payload["validation"] = _json_member(archive, "metadata/software/validation.json")
            payload["readiness"] = _json_member(archive, "metadata/software/readiness.json")
            payload["test_report"] = _json_member(archive, "dataset/04_reports/test_report.json")
    except (OSError, zipfile.BadZipFile):
        return payload
    return payload


def _aligned_method_output_evidence(method_outputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    specimen_results = _list_of_dicts(method_outputs.get("specimen_results"))
    final_rows = [
        row for row in _list_of_dicts(method_outputs.get("final_report_runs"))
        if str(row.get("final_included", row.get("included", ""))).casefold() in {"1", "true", "yes", "y"}
    ]
    mean_load = _mean(_float_or_none(row.get("max_load_N")) for row in final_rows)
    mean_modulus = _mean(_mpa_to_gpa(_float_or_none(row.get("compressive_modulus_MPa"))) for row in final_rows)
    for row in specimen_results:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        evidence[run_id] = {
            "bending_peak": _float_or_none(row.get("bending_max_percent")),
            "bending_threshold": _float_or_none(row.get("bending_threshold_percent")),
            "bending_points_above_threshold": _int_or_none(row.get("bending_points_above_threshold")),
            "bending_assessed_points": _int_or_none(row.get("bending_point_count")),
            "bending_fraction_above_threshold": _float_or_none(row.get("bending_fraction_above_threshold")),
            "bending_longest_segment_points": _int_or_none(row.get("bending_longest_segment_points")),
            "bending_longest_segment_fraction": _float_or_none(row.get("bending_longest_segment_fraction")),
            "bending_classification": str(row.get("bending_pattern") or row.get("failure_mode") or ""),
            "peak_load_N": _float_or_none(row.get("max_load_N")),
            "kept_mean_load": mean_load,
            "modulus_GPa": _mpa_to_gpa(_float_or_none(row.get("compressive_modulus_MPa"))),
            "kept_mean_modulus": mean_modulus,
            "failure_mode": str(row.get("failure_mode") or row.get("primary_failure_mode") or ""),
            "has_bending_evidence": row.get("bending_max_percent") not in (None, ""),
        }
    return evidence


def _merge_evidence(left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = {run_id: dict(payload) for run_id, payload in left.items()}
    for run_id, payload in right.items():
        merged.setdefault(run_id, {}).update(payload)
    return merged


def _run_model_payload(model: Any) -> dict[str, Any]:
    cockpit = getattr(model, "diagnostic_cockpit", None)
    cockpits = getattr(model, "diagnostic_cockpits", None) or ([cockpit] if cockpit is not None else [])
    return {
        "run_id": getattr(model, "run_id", ""),
        "default_call": getattr(model, "default_call", ""),
        "reason": getattr(model, "reason", ""),
        "is_excluded": getattr(model, "is_excluded", False),
        "has_bending_evidence": getattr(model, "has_bending_evidence", False),
        "bending_peak": getattr(model, "bending_peak", None),
        "bending_threshold": getattr(model, "bending_threshold", None),
        "acceptance_flags": _plain_data(getattr(model, "acceptance_flags", [])),
        "diagnostic_cockpit": _plain_data(cockpit),
        "diagnostic_cockpits": _plain_data(cockpits),
    }


def _review_cockpits(review: dict[str, Any]) -> list[dict[str, Any]]:
    value = review.get("diagnostic_cockpits")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    value = review.get("diagnostic_cockpit")
    return [dict(value)] if isinstance(value, dict) else []


def _plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_data(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _service_result_payload(result: Any) -> dict[str, Any]:
    return {
        "status": getattr(result, "status", ""),
        "readiness_status": getattr(result, "readiness_status", ""),
        "output_path": str(getattr(result, "output_path", "") or ""),
        "workbench_path": str(getattr(result, "workbench_path", "") or ""),
        "validation_summary": dict(getattr(result, "validation_summary", {}) or {}),
        "acceptance_summary": dict(getattr(result, "acceptance_summary", {}) or {}),
        "acceptance_report": dict(getattr(result, "acceptance_report", {}) or {}),
        "readiness_summary": dict(getattr(result, "readiness_summary", {}) or {}),
        "warnings": list(getattr(result, "warnings", []) or []),
        "errors": list(getattr(result, "errors", []) or []),
        "archive_members": list(getattr(result, "archive_members", ()) or ()),
        "report_summary": dict(getattr(result, "report_summary", {}) or {}),
        "report_artifacts": list(getattr(result, "report_artifacts", ()) or ()),
    }


def _screen_cards(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    cards: list[Any] = []
    for key in ("summary_cards", "selection_cards", "filters", "cards"):
        value = payload.get(key)
        if isinstance(value, list):
            cards.extend(value)
    return cards


def _screen_row_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    total = 0
    for key in ("rows", "run_rows", "fields", "groups", "source_files", "attention_rows"):
        value = payload.get(key)
        if isinstance(value, list):
            total += len(value)
    return total


def _finding(
    case_id: str,
    screen_id: str,
    finding_type: str,
    detail: str,
    *,
    run_id: str = "",
    evidence_key: str = "",
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "screen_id": screen_id,
        "run_id": run_id,
        "finding_type": finding_type,
        "evidence_key": evidence_key,
        "detail": detail,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain_data(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_summary_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows = [
        {
            "case_id": record.get("case_id", ""),
            "input_path": record.get("input_path", ""),
            "status": record.get("status", ""),
            "readiness_status": record.get("readiness_status", ""),
            "review_row_count": record.get("review_row_count", 0),
            "diagnostic_card_count": record.get("diagnostic_card_count", 0),
            "unattended_count": record.get("unattended_count", 0),
            "elapsed_seconds": record.get("elapsed_seconds", 0),
        }
        for record in records
    ]
    _write_csv(path, rows)


def _write_diagnostic_cards_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for record in records:
        for card in _read_json_rows(record, "diagnostic_cards"):
            rows.append(card)
    _write_csv(path, rows)


def _write_unattended_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.extend(_read_case_findings(record))
    _write_csv(path, rows)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _read_json_rows(record: dict[str, Any], key: str) -> list[dict[str, Any]]:
    ref = record.get(key)
    run_dir = record.get("run_dir")
    if not ref or not run_dir:
        return []
    path = Path(run_dir).parents[1] / str(ref) if not Path(str(ref)).is_absolute() else Path(str(ref))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [row for row in payload if isinstance(row, dict)] if isinstance(payload, list) else []


def _read_case_findings(record: dict[str, Any]) -> list[dict[str, Any]]:
    return _read_json_rows(record, "unattended_findings")


def _json_member(archive: zipfile.ZipFile, member: str) -> dict[str, Any]:
    if member not in archive.namelist():
        return {}
    try:
        payload = json.loads(archive.read(member).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _prepare_output_dir(path: Path, *, force: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not force:
            raise SystemExit(f"Output directory already exists and is not empty: {path}\nUse --force or choose a new --output.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _default_output_root() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "artifacts" / "gui_view_harvest" / stamp


def _case_slug(path: Path) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in path.stem).strip("_") or "case"
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"{safe[:64]}-{digest}"


def _error_record(stage: str, exc: Exception) -> dict[str, str]:
    return {"stage": stage, "type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=8)}


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _mean(values: Any) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _mpa_to_gpa(value: float | None) -> float | None:
    return value / 1000.0 if value is not None else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
