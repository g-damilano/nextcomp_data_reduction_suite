from __future__ import annotations

from pathlib import Path

import pytest

from methods.core.method_run_service import MethodRunRequest, MethodRunService


ROOT = Path(__file__).resolve().parents[1]
STAGE26_INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
STAGE26_METHOD = ROOT / "src" / "methods" / "iso14126"
STAGE26_MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="session")
def stage26_canonical_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("stage26_canonical") / "CAG-CF-Modied-ULV20.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=STAGE26_INPUT,
            method_path=STAGE26_METHOD,
            mapping_path=STAGE26_MAPPING,
            output_path=output,
            generate_workbench=True,
        )
    )
    assert result.status == "completed"
    return output
