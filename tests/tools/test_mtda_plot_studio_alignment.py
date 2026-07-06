from __future__ import annotations

from pathlib import Path

from PIL import Image

import json
import zipfile

from tools.mtda_plot_studio_alignment import (
    build_handoff_data_mtda,
    build_residuals,
    handoff_plot_datasets,
    load_handoff_js_assignment,
    normalize_label,
    runtime_dom_diff,
    runtime_dom_depth_diff,
    source_dom_diff,
    source_html_inventory,
    text_present,
)


ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "docs" / "design_handoff_dataset_plot_studio"


def test_alignment_harness_normalizes_prototype_control_text() -> None:
    assert normalize_label("← Archive") == "archive"
    assert normalize_label("Stress–strain") == "stress-strain"
    assert normalize_label("Import file…") == "import file..."


def test_text_presence_uses_normalized_body_and_button_labels() -> None:
    inventory = {
        "bodyText": "Dataset aggregate plot",
        "buttons": ["Stress–strain", "Export ▾"],
        "headings": [],
    }

    assert text_present(inventory, "Stress-strain")
    assert text_present(inventory, "Export")


def test_residual_builder_tracks_required_text_without_raw_button_diff() -> None:
    states = [
        {
            "state_id": "state",
            "label": "State",
            "production": {
                "errors": [],
                "missing_required_text": [],
                "inventory": {"buttons": ["Archive", "Extra production button"], "plotMounts": 1},
            },
            "golden": {
                "errors": [],
                "missing_required_text": [],
                "inventory": {"buttons": ["← Archive", "Import file…"], "plotMounts": 1},
            },
        }
    ]

    residuals = build_residuals(states)

    assert residuals == []


def test_residual_builder_strict_visual_flags_pixel_delta(tmp_path: Path) -> None:
    production = tmp_path / "production.png"
    golden = tmp_path / "golden.png"
    production_image = Image.new("RGBA", (2, 2), (255, 255, 255, 255))
    production_image.putpixel((1, 1), (0, 0, 0, 255))
    production_image.save(production)
    Image.new("RGBA", (2, 2), (255, 255, 255, 255)).save(golden)

    diagnostics_dir = tmp_path / "diagnostics"
    residuals = build_residuals(
        [
            {
                "state_id": "state",
                "label": "State",
                "production": {
                    "errors": [],
                    "missing_required_text": [],
                    "screenshot": str(production),
                    "inventory": {"buttons": [], "plotMounts": 1},
                },
                "golden": {
                    "errors": [],
                    "missing_required_text": [],
                    "screenshot": str(golden),
                    "inventory": {"buttons": [], "plotMounts": 1},
                },
            }
        ],
        strict_visual=True,
        diagnostics_dir=diagnostics_dir,
    )

    assert residuals[0] == {
        "state": "state",
        "category": "visual",
        "detail": "strict screenshot delta: 1/4 pixels (25.0000%) differ; bbox=(1, 1, 2, 2)",
    }
    assert any(row["category"] == "visual-region" and row["detail"].startswith("shell:") for row in residuals)
    assert (diagnostics_dir / "state.diff-heatmap.png").is_file()
    assert (diagnostics_dir / "state.region-heatmap.png").is_file()
    assert (diagnostics_dir / "state.side-by-side.png").is_file()
    assert (diagnostics_dir / "state.regions.json").is_file()


def test_source_dom_diff_parses_and_reports_element_mismatches(tmp_path: Path) -> None:
    production = tmp_path / "production.html"
    golden = tmp_path / "golden.html"
    production.write_text("<main><button id='save' class='primary'>Save</button><input id='name'></main>", encoding="utf-8")
    golden.write_text("<main><button id='export'>Export</button><select id='mode'></select></main>", encoding="utf-8")

    diffs = source_dom_diff(source_html_inventory(production), source_html_inventory(golden))

    assert any("tag count deltas" in diff["detail"] and "input" in diff["detail"] for diff in diffs)
    assert any(diff["category"] == "source-control" and "button:Export" in diff["detail"] for diff in diffs)


def test_runtime_dom_diff_reports_visible_control_and_box_deltas() -> None:
    production = {
        "controls": [{"kind": "button", "label": "Save", "x": 10, "y": 10, "width": 80, "height": 30}],
        "boxes": [{"name": "inspector", "x": 900, "y": 40, "width": 380, "height": 860, "display": "grid"}],
    }
    golden = {
        "controls": [{"kind": "button", "label": "Export", "x": 12, "y": 12, "width": 90, "height": 30}],
        "boxes": [{"name": "inspector", "x": 1060, "y": 40, "width": 380, "height": 860, "display": "flex"}],
    }

    diffs = runtime_dom_diff(production, golden)

    assert any(diff["category"] == "dom-control" and "Export" in diff["detail"] for diff in diffs)
    assert any(diff["category"] == "dom-box" and "inspector" in diff["detail"] for diff in diffs)
    assert any(diff["category"] == "dom-style" and "display" in diff["detail"] for diff in diffs)


def test_runtime_dom_depth_diff_reports_ordered_depth_deltas() -> None:
    production = {
        "domDepth": [
            {
                "depth": 0,
                "tag": "body",
                "classes": [],
                "x": 0,
                "y": 0,
                "width": 1440,
                "height": 900,
                "selectedStyle": {"display": "block", "margin": "0px"},
            },
            {
                "depth": 1,
                "tag": "main",
                "id": "",
                "classes": ["plot-studio"],
                "x": 0,
                "y": 0,
                "width": 1440,
                "height": 900,
                "selectedStyle": {"display": "flex"},
            },
        ]
    }
    golden = {
        "domDepth": [
            {
                "depth": 0,
                "tag": "body",
                "classes": [],
                "x": 0,
                "y": 0,
                "width": 1440,
                "height": 900,
                "selectedStyle": {"display": "block", "margin": "0px"},
            },
            {
                "depth": 1,
                "tag": "x-dc",
                "id": "",
                "classes": [],
                "x": 0,
                "y": 0,
                "width": 1440,
                "height": 900,
                "selectedStyle": {"display": "block"},
            },
        ]
    }

    diffs = runtime_dom_depth_diff(production, golden)

    assert any(diff["category"] == "dom-depth" and "depth 1 node 0" in diff["detail"] for diff in diffs)
    assert any("tag production='main' golden='x-dc'" in diff["detail"] for diff in diffs)


def test_handoff_fixture_derives_reference_plot_datasets_and_archive(tmp_path: Path) -> None:
    archive_data = load_handoff_js_assignment(HANDOFF / "data" / "archive_data.js", "MTDA_DATA")
    bending_dist = load_handoff_js_assignment(HANDOFF / "data" / "bending_dist.js", "MTDA_BENDING_DIST")

    datasets = handoff_plot_datasets(archive_data, bending_dist)

    assert len(datasets["stress_aggregate"]) == 250
    assert len(datasets["replicates"]) == 10 * 250
    assert datasets["fmax_distribution"][0]["x_position"] == 100
    assert {row["bending_pattern_group"] for row in datasets["bending_summary"]} == {"PASS", "WARN", "FAIL"}

    mtda = build_handoff_data_mtda(HANDOFF, tmp_path)
    with zipfile.ZipFile(mtda) as archive:
        package = json.loads(archive.read("dataset/03_aggregate/dataset_plot.plot_package.json"))
        assert archive.read("dataset/03_aggregate/dataset_plot.html").lower().startswith(b"<!doctype html>")
        assert "Dataset report" in package["title"]
        assert "8552-IM7" in package["title"]
        assert "aggregate of 10 runs" in package["title"]
        assert package["view_data_mode"] == "embedded_rows_preferred"
        embedded = {dataset["dataset_id"]: dataset for dataset in package["embedded_datasets"]}
        assert len(embedded["stress_aggregate"]["rows"]) == 250
        assert len(embedded["dataset_001"]["rows"]) == 2500
        assert "dataset/03_aggregate/stress_strain_aligned.csv" in package["source_refs"]
