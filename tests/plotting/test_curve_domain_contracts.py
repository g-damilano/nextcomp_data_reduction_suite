from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from plotting.evidence_adapters import stress_strain_reduction_request
from plotting.layout import downsample
from plotting.registry import plot_registry


def test_downsample_preserves_first_and_last_curve_rows() -> None:
    rows = [{"point_index": index} for index in range(1000)]

    sampled = downsample(rows, 650)

    assert len(sampled) <= 650
    assert sampled[0]["point_index"] == 0
    assert sampled[-1]["point_index"] == 999


def test_stress_reduction_markers_are_not_clipped_by_downsampled_curve_extent() -> None:
    rows = [
        {
            "run_id": "run_001",
            "point_index": index,
            "mean_strain": index / 79900.0,
            "stress_MPa": float(index),
            "front_strain_abs": index / 79900.0,
            "rear_strain_abs": index / 79900.0,
        }
        for index in range(800)
    ]
    request = stress_strain_reduction_request(
        plot_id="run_001_stress",
        run_id="run_001",
        bounded_rows=rows,
        block={
            "markers": {
                "experiment_start": {"index": 0},
                "experiment_end": {"index": 799},
                "max_load_strength": {"index": 799, "stress_MPa": 799.0},
            }
        },
    )

    result = plot_registry.build(request)

    assert result.status == "rendered"
    marker_layer = _layer(result.spec or {}, "analysis markers")
    marker_names = {row["marker"] for row in marker_layer["data"]["values"]}
    assert marker_names == {"start marker", "end marker (max point / failure strain)"}


def _layer(spec: dict, name: str) -> dict:
    for layer in spec.get("layer", []):
        if layer.get("name") == name:
            return layer
    raise AssertionError(f"missing layer {name!r}")
