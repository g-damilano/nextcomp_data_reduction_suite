from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from methods.core.method_run_service import MethodRunRequest, MethodRunService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a method package manually against an MTDP archive.")
    parser.add_argument("--input", required=True, help="Input .mtdp archive.")
    parser.add_argument("--method", required=True, help="Method package folder.")
    parser.add_argument("--mapping", required=True, help="Manual method mapping JSON/YAML.")
    parser.add_argument("--output", required=True, help="Output .mtda archive.")
    parser.add_argument("--workbench", action="store_true", help="Also generate a method development workbench next to the output.")
    args = parser.parse_args()

    request = MethodRunRequest(
        input_package_path=Path(args.input),
        method_path=Path(args.method),
        mapping_path=Path(args.mapping),
        output_path=Path(args.output),
        overwrite=True,
        generate_workbench=args.workbench,
    )
    service_result = MethodRunService().run(request)
    print(f"Readiness: {service_result.readiness_status}")
    if service_result.readiness_status == "READY_WITH_WARNINGS":
        print("Readiness warnings: report-completeness inputs are missing; execution will continue.")
    if service_result.status != "completed":
        print("Method run did not start because the selected package is not ready.")
        for error in service_result.errors:
            print(f"- {error}")
        return 2

    print(f"Wrote {service_result.output_path}")
    print(f"Archive members: {len(service_result.archive_members)}")
    print(f"Warnings: {len(service_result.warnings)}")
    if service_result.workbench_path:
        print(f"Workbench: {service_result.workbench_path / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
