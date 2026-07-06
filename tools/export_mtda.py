from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export import ExportRequest, ExportService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export production artifacts from an MTDA archive.")
    parser.add_argument("--input", required=True, help="Input .mtda archive")
    parser.add_argument("--output", required=True, help="Output export directory")
    parser.add_argument("--profile", default="minimal", choices=["minimal", "figures", "full_html"])
    args = parser.parse_args(argv)

    result = ExportService().export(
        ExportRequest.from_paths(
            input_path=args.input,
            output_dir=args.output,
            profile=args.profile,
        )
    )
    print(f"Exported {len(result.artifacts)} artifacts to {result.output_dir}")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
