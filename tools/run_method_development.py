from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archives.core.json_io import json_text
from archives.mtdp import MTDPPackageReader
from audit.method_development_report_builder import MethodDevelopmentReportBuilder
from audit.operation_trace import build_operation_trace
from methods.core import MethodExecutor, MethodPackage


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or serve an operation-wise method development workbench.")
    parser.add_argument("--input", required=True, help="Input .mtdp archive.")
    parser.add_argument("--method", required=True, help="Method package folder.")
    parser.add_argument("--mapping", required=True, help="Manual method mapping JSON/YAML.")
    parser.add_argument("--output", required=True, help="Output directory for trace files and index.html.")
    parser.add_argument("--serve", action="store_true", help="Serve a local Python-backed workbench with recipe re-run API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    runner = DevelopmentRunner(args.input, args.method, args.mapping)
    trace = runner.run()
    output_dir = Path(args.output)
    _write_trace_bundle(output_dir, trace, api_enabled=args.serve)
    print(f"Wrote development workbench: {output_dir / 'index.html'}")
    print(f"Operation records: {len(trace.get('operations', []))}")
    if args.serve:
        _serve(args.host, args.port, output_dir, runner)
    return 0


class DevelopmentRunner:
    def __init__(self, input_path: str | Path, method_path: str | Path, mapping_path: str | Path) -> None:
        self.input_path = Path(input_path)
        self.method_path = Path(method_path)
        self.mapping_path = Path(mapping_path)
        self.source = MTDPPackageReader().read(self.input_path)
        self.method_package = MethodPackage.load(self.method_path)
        self.mapping = _load_mapping(self.mapping_path)

    def run(
        self,
        *,
        resolve_recipe_text: str | None = None,
        reduce_recipe_text: str | None = None,
    ) -> dict[str, Any]:
        method = self.method_package
        if resolve_recipe_text is not None or reduce_recipe_text is not None:
            method = MethodPackage(
                root=self.method_package.root,
                manifest=self.method_package.manifest,
                resolve_recipe=_load_yaml_text(resolve_recipe_text) if resolve_recipe_text is not None else self.method_package.resolve_recipe,
                reduce_recipe=_load_yaml_text(reduce_recipe_text) if reduce_recipe_text is not None else self.method_package.reduce_recipe,
                audit_recipe=self.method_package.audit_recipe,
                validation_recipe=self.method_package.validation_recipe,
                acceptance_recipe=self.method_package.acceptance_recipe,
                method_inputs=self.method_package.method_inputs,
            )
        result = MethodExecutor().execute(self.source, method, self.mapping)
        trace = build_operation_trace(result)
        if resolve_recipe_text is not None:
            trace["recipes"]["resolve_text"] = resolve_recipe_text
        if reduce_recipe_text is not None:
            trace["recipes"]["reduce_text"] = reduce_recipe_text
        return trace


def _write_trace_bundle(output_dir: Path, trace: dict[str, Any], *, api_enabled: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "trace_manifest.json").write_text(
        json_text(
            {
                "trace_format": trace.get("trace_format"),
                "trace_version": trace.get("trace_version"),
                "source": trace.get("source"),
                "method": trace.get("method"),
                "operation_count": len(trace.get("operations", [])),
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "operation_trace.json").write_text(json_text(trace), encoding="utf-8")
    snapshots = output_dir / "snapshots"
    snapshots.mkdir(exist_ok=True)
    (snapshots / "curve_rows_by_run.json").write_text(json_text(trace.get("curve_rows_by_run", {})), encoding="utf-8")
    html = MethodDevelopmentReportBuilder().build(trace, api_enabled=api_enabled)
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def _serve(host: str, port: int, output_dir: Path, runner: DevelopmentRunner) -> None:
    output_dir = output_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html"}:
                self._send_file(output_dir / "index.html", "text/html; charset=utf-8")
                return
            if self.path == "/operation_trace.json":
                self._send_file(output_dir / "operation_trace.json", "application/json")
                return
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/run":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                trace = runner.run(
                    resolve_recipe_text=str(payload.get("resolve_recipe", "")),
                    reduce_recipe_text=str(payload.get("reduce_recipe", "")),
                )
                _write_trace_bundle(output_dir, trace, api_enabled=True)
                body = json.dumps(trace).encode("utf-8")
            except Exception as exc:  # pragma: no cover - manual server path
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"[workbench] {self.address_string()} - {format % args}")

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.exists():
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving method development workbench at http://{host}:{port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _load_mapping(path: str | Path) -> dict[str, Any]:
    mapping_path = Path(path)
    text = mapping_path.read_text(encoding="utf-8")
    if mapping_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Mapping file must contain an object: {mapping_path}")
    return payload


def _load_yaml_text(text: str | None) -> dict[str, Any]:
    payload = yaml.safe_load(text or "")
    if not isinstance(payload, dict):
        raise ValueError("Recipe text must contain a YAML mapping.")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
