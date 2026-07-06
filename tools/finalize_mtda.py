from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtda_finalization import AmendmentRequest, MTDAFinalizationService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize or safely amend an existing MTDA archive.")
    parser.add_argument("--input", required=True, help="Existing .mtda archive to amend")
    parser.add_argument("--output", help="Output .mtda path. Defaults to *_finalized.mtda")
    parser.add_argument("--in-place", action="store_true", help="Rewrite the input archive in place")
    parser.add_argument("--report-overrides", help="JSON file containing report-only overrides")
    parser.add_argument("--human-decisions", help="JSON file containing human acceptance decisions")
    parser.add_argument("--reviewer", default="", help="Reviewer/operator name")
    parser.add_argument("--reason", default="", help="Reason for amendment/finalization")
    args = parser.parse_args(argv)

    request = AmendmentRequest(
        report_overrides=tuple(_load_rows(args.report_overrides, "overrides")),
        human_decisions=tuple(_load_rows(args.human_decisions, "decisions")),
        reviewer=args.reviewer,
        reason=args.reason,
        source_surface="tools/finalize_mtda.py",
    )
    result = MTDAFinalizationService().finalize(
        input_path=args.input,
        output_path=args.output,
        in_place=args.in_place,
        request=request,
    )
    if result.status.startswith("rejected"):
        for error in result.errors:
            print(error, file=sys.stderr)
        return 2
    print(f"Finalized {result.input_path} -> {result.output_path}")
    print(f"Updated {len(result.artifacts_updated)} artifacts")
    return 0


def _load_rows(path: str | None, key: str) -> list[dict[str, object]]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get(key, [])
    if not isinstance(payload, list):
        raise SystemExit(f"{path} must contain a list or an object with '{key}'.")
    return [dict(item) for item in payload if isinstance(item, dict)]


if __name__ == "__main__":
    raise SystemExit(main())
