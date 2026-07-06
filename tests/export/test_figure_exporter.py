from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.artifact_collector import MTDAArtifactCollector
from export.figure_exporter import FigureExporter


def test_figure_exporter_writes_standalone_vega_html(tmp_path: Path) -> None:
    archive_path = tmp_path / "input.mtda"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "dataset/03_aggregate/stress_strain_aligned.csv",
            "x_normalized,mean,std,min,max,n\n0,1,0.1,0.8,1.2,3\n1,2,0.2,1.7,2.3,3\n",
        )
        archive.writestr(
            "dataset/03_aggregate/dataset_plot.plot_package.json",
            json.dumps(
                {
                    "package_type": "compact-vegalite-workbench",
                    "plot_id": "dataset_plot",
                    "template_member": "dataset/03_aggregate/dataset_plot.template.json",
                    "datasets": [
                        {
                            "dataset_id": "dataset_001",
                            "member": "dataset/03_aggregate/dataset_plot_data/dataset_001.csv",
                        }
                    ],
                }
            ),
        )
        archive.writestr(
            "dataset/03_aggregate/dataset_plot.template.json",
            json.dumps({"mark": "line", "data": {"__compact_dataset_ref__": "dataset_001"}}),
        )
        archive.writestr("dataset/03_aggregate/dataset_plot_data/dataset_001.csv", "x,y\n0,1\n")

    files = FigureExporter().export(MTDAArtifactCollector(archive_path), profile="figures")
    spec = json.loads(files["figures/aggregate_stress_strain_vega.json"])

    assert "vegaEmbed" in files["figures/aggregate_stress_strain.html"].decode("utf-8")
    assert spec["$schema"].endswith("vega-lite/v5.json")
    assert spec["datasets"]["aggregate"][1]["analysis_progress_percent"] == 100.0
    assert "hconcat" in spec
    payload = json.dumps(spec)
    assert "Normalised strain / %" in payload
    assert "Stress / MPa" in payload
    assert "Strain (% of failure strain)" not in payload
    assert "Stress (MPa)" not in payload
    hydrated = json.loads(files["figures/dataset_plot.full_vegalite_spec_with_data.vl.json"])
    assert hydrated == {"mark": "line", "data": {"values": [{"x": "0", "y": "1"}]}}
    assert "figures/dataset_plot.vl.json" not in files
