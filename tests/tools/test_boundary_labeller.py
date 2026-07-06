from __future__ import annotations

import csv
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import boundary_labeller as labeller


def test_load_curve_records_discovers_processed_stress_strain_curve(tmp_path: Path) -> None:
    curve_path = tmp_path / "run_001_stress_strain.csv"
    _write_curve(curve_path)

    curves = labeller.load_curve_records(curve_path, catalogue_root=tmp_path)

    assert len(curves) == 1
    curve = curves[0]
    assert curve.curve_id == "run_001_stress_strain.csv::run_001"
    assert curve.run_id == "run_001"
    assert curve.point_index == [0, 1, 2, 3, 4]
    assert curve.strain[2] == 0.002
    assert curve.stress[2] == 30.0
    assert curve.load[2] == 300.0


def test_evaluate_curve_uses_project_gate_and_boundary_operations(tmp_path: Path) -> None:
    curve_path = tmp_path / "run_001_stress_strain.csv"
    _write_curve(curve_path)
    curve = labeller.load_curve_records(curve_path, catalogue_root=tmp_path)[0]
    boundary_step = labeller.default_boundary_step()
    boundary_step["parameters"]["end_policy"] = "max_abs_load"

    result = labeller.evaluate_curve(
        curve,
        method_path=None,
        gate_step=labeller.default_gate_step(),
        boundary_step=boundary_step,
    )

    assert result.gate_start_index == 0
    assert result.gate_end_index == 4
    assert result.boundary_start_index == 0
    assert result.boundary_end_index == 2


def test_assess_labels_writes_json_and_csv_reports(tmp_path: Path) -> None:
    curve_path = tmp_path / "run_001_stress_strain.csv"
    _write_curve(curve_path)
    curve = labeller.load_curve_records(curve_path, catalogue_root=tmp_path)[0]
    boundary_step = labeller.default_boundary_step()
    boundary_step["parameters"]["end_policy"] = "max_abs_load"
    algorithm = labeller.evaluate_curve(
        curve,
        method_path=None,
        gate_step=labeller.default_gate_step(),
        boundary_step=boundary_step,
    )
    label_path = tmp_path / "labels.json"
    output_json = tmp_path / "assessment.json"
    output_csv = tmp_path / "assessment.csv"
    catalog = {"schema_id": "dev.boundary_label_catalog.v0_1", "labels": []}
    labeller.upsert_label(
        catalog,
        labeller.build_label_record(curve, start_index=0, end_index=2, algorithm=algorithm),
    )
    labeller.write_label_catalog(label_path, catalog)

    report = labeller.assess_labels(
        label_path,
        data_root=tmp_path,
        method_path=None,
        gate_step=labeller.default_gate_step(),
        boundary_step=boundary_step,
        output_json=output_json,
        output_csv=output_csv,
        start_tolerance=0,
        end_tolerance=0,
        gate_tolerance=0,
    )

    assert output_json.exists()
    assert output_csv.exists()
    assert json.loads(output_json.read_text(encoding="utf-8"))["summary"] == report["summary"]
    csv_rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))
    assert report["summary"]["assessed_count"] == 1
    assert report["summary"]["fail_count"] == 0
    assert report["summary"]["pass_count"] == 1
    assert report["summary"]["failure_categories"] == {}
    assert report["summary"]["justification_categories"] == {}
    assert report["summary"]["justified_fail_count"] == 0
    assert report["summary"]["unjustified_fail_count"] == 0
    row = report["results"][0]
    assert row["boundary_pass"] is True
    assert row["gate_pass"] is True
    assert row["boundary_end_delta"] == 0
    assert row["gate_end_delta"] == 2
    assert row["outlier_flag"] is False
    assert row["review_flags"] == ""
    assert row["failure_category"] == "none"
    assert row["justified_failure"] is False
    assert row["justification_category"] == "none"
    assert row["diagnostic_columns"]["raw_curve_human_label"] == {"start_index": 0, "end_index": 2}
    assert row["diagnostic_columns"]["gate_experiment_signal"]["start_index"] == 0
    assert row["diagnostic_columns"]["boundary_resolution"]["end_index"] == 2
    assert row["label_start_context"] == "raw_or_near_raw_start"
    csv_diagnostics = json.loads(csv_rows[0]["diagnostic_columns_json"])
    assert csv_diagnostics["raw_curve_human_label"] == {"start_index": 0, "end_index": 2}


def test_failure_justification_marks_remaining_strict_residual_classes() -> None:
    base = {
        "overall_status": "fail",
        "failure_category": "start_onset_delta",
        "boundary_start_pass": False,
        "boundary_end_pass": True,
        "gate_start_pass": True,
        "gate_end_pass": True,
        "gate_status": "ok",
        "gate_classifications": [],
        "boundary_confidence": "high",
        "boundary_start_delta": -3,
        "boundary_end_delta": 0,
        "gate_start_delta": -3,
        "gate_end_delta": 57,
        "label_start_context": "preload_to_load_rise",
        "start_tolerance": 2,
        "end_tolerance": 3,
    }

    category, detail = labeller._failure_justification(**base)
    assert category == "borderline_start_sampling_tolerance"
    assert "one sample beyond strict tolerance" in detail

    multistep = dict(base)
    multistep.update(
        {
            "boundary_start_delta": -13,
            "gate_start_delta": -98,
            "label_start_context": "ongoing_settling_or_reset",
        }
    )
    category, detail = labeller._failure_justification(**multistep)
    assert category == "low_priority_multistep_settling_outlier"
    assert "bespoke onset rule" in detail

    hard_gate = dict(base)
    hard_gate.update(
        {
            "boundary_start_pass": True,
            "gate_start_pass": False,
            "gate_end_pass": False,
            "gate_status": "fail",
            "gate_classifications": ["post_experiment_invalid_tail", "disconnected_high_load_fragment"],
            "boundary_confidence": "low",
            "boundary_start_delta": -2,
            "gate_start_delta": -172,
            "label_start_context": "preload_plateau_with_strain_drift",
        }
    )
    category, detail = labeller._failure_justification(**hard_gate)
    assert category == "hard_invalid_tail_gate"
    assert "post_experiment_invalid_tail" in detail


def test_assessment_summary_counts_justified_and_unjustified_failures() -> None:
    rows = [
        {"overall_status": "pass"},
        {
            "overall_status": "fail",
            "failure_category": "start_onset_delta",
            "justified_failure": True,
            "justification_category": "borderline_start_sampling_tolerance",
        },
        {
            "overall_status": "fail",
            "failure_category": "gate_window_delta",
            "justified_failure": False,
            "justification_category": "unjustified",
        },
    ]

    summary = labeller._assessment_summary(rows)

    assert summary["fail_count"] == 2
    assert summary["justified_fail_count"] == 1
    assert summary["unjustified_fail_count"] == 1
    assert summary["justification_categories"] == {
        "borderline_start_sampling_tolerance": 1,
        "unjustified": 1,
    }


def test_import_curve_files_copies_raw_file_into_catalogue_and_records_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "machine_raw.csv"
    _write_machine_raw_curve(source_path)
    database_root = tmp_path / "curve_database"

    imported = labeller.import_curve_files([source_path], database_root=database_root)

    raw_dir = database_root / "raw"
    stored_files = list(raw_dir.glob("*.csv"))
    assert len(stored_files) == 1
    assert stored_files[0].read_text(encoding="utf-8") == source_path.read_text(encoding="utf-8")
    manifest = labeller.load_database_manifest(database_root)
    assert len(manifest["files"]) == 1
    assert manifest["files"][0]["original_path"] == str(source_path.resolve())
    assert manifest["files"][0]["stored_path"].endswith(stored_files[0].name)
    assert len(imported) == 1
    assert imported[0].source_path == stored_files[0]
    assert imported[0].load == [0.0, 100.0, 250.0, 200.0]
    assert abs(imported[0].strain[1] - 15e-6) < 1e-12


def test_import_curve_files_extracts_stress_strain_curves_from_mtdp_package(tmp_path: Path) -> None:
    curve_path = tmp_path / "run_001_stress_strain.csv"
    bound_path = tmp_path / "run_001_stress_strain_experiment_bound.csv"
    package_path = tmp_path / "sample.mtdp"
    _write_curve(curve_path)
    _write_curve(bound_path)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(curve_path, "dataset/03_processed/run_001_stress_strain.csv")
        archive.write(bound_path, "dataset/03_processed/run_001_stress_strain_experiment_bound.csv")
        archive.writestr("dataset/04_aggregate/stress_strain_aligned.csv", curve_path.read_text(encoding="utf-8"))
    database_root = tmp_path / "curve_database"

    imported = labeller.import_curve_files([package_path], database_root=database_root)

    raw_files = sorted((database_root / "raw").glob("*.csv"))
    assert len(raw_files) == 1
    assert imported[0].run_id == "run_001"
    assert imported[0].source_path == raw_files[0]
    manifest = labeller.load_database_manifest(database_root)
    assert manifest["files"][0]["original_path"] == str(package_path.resolve())
    assert manifest["files"][0]["package_member"] == "dataset/03_processed/run_001_stress_strain.csv"


def test_import_curve_files_extracts_legacy_normalized_run_csvs_from_mtdp_package(tmp_path: Path) -> None:
    package_path = tmp_path / "legacy.mtdp"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "normalized/run_001.csv",
            "\n".join(
                [
                    "Specimen name,8552-IM7",
                    "Width,10,mm",
                    "",
                    "Scan #,Time,Uniaxial Gage 1 on S1-Ch2 microstrain,Uniaxial Gage 2 on S1-Ch1 microstrain,Load",
                    ",(s),(mm/mm),(mm/mm),(N)",
                    '"11","1100000","6e-06","-8e-06","23"',
                    '"12","1200000","8e-06","-10e-06","25"',
                ]
            )
            + "\n",
        )
        archive.writestr(
            "raw/run_001.csv",
            "\n".join(
                [
                    "Scan #,Time,Uniaxial Gage 1 on S1-Ch2 microstrain,Uniaxial Gage 2 on S1-Ch1 microstrain,Load on S1-Ch3 kN",
                    "11,1100000,6,-8,0.0230",
                ]
            )
            + "\n",
        )
    database_root = tmp_path / "curve_database"

    imported = labeller.import_curve_files([package_path], database_root=database_root)

    assert len(imported) == 1
    assert imported[0].run_id == "run_001"
    assert imported[0].point_index == [11, 12]
    assert imported[0].load == [23.0, 25.0]
    assert imported[0].strain == [7e-06, 9e-06]
    manifest = labeller.load_database_manifest(database_root)
    assert manifest["files"][0]["package_member"] == "normalized/run_001.csv"


def test_import_curve_files_extracts_dataset_normalized_run_csvs_from_mtdp_package(tmp_path: Path) -> None:
    package_path = tmp_path / "dataset_layout.mtdp"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "dataset/normalized/run_001_normalized.csv",
            "\n".join(
                [
                    "Specimen name,TEST",
                    "Width,10,mm",
                    "",
                    "Load,Displacement,Front Strain,Rear Strain,Time",
                    "(N),(mm),(mm/mm),(mm/mm),(s)",
                    '"0.14","0","2.34316e-06","1.04679e-06","0"',
                    '"4.9","0.0007","1.39706e-06","3.89905e-06","0.1"',
                ]
            )
            + "\n",
        )
        archive.writestr(
            "dataset/raw/run_001_raw.csv",
            "\n".join(
                [
                    "Force,Displacement,Front Strain,Rear Strain,Time",
                    "(kN),(mm),(usn),(usn),(s)",
                    '"0.00014","0.0000","2.34316","1.04679","0.0000"',
                ]
            )
            + "\n",
        )
    database_root = tmp_path / "curve_database"

    imported = labeller.import_curve_files([package_path], database_root=database_root)

    assert len(imported) == 1
    assert imported[0].run_id == "run_001"
    assert imported[0].point_index == [0, 1]
    assert imported[0].load == [0.14, 4.9]
    assert abs(imported[0].strain[0] - 1.694975e-06) < 1e-12
    manifest = labeller.load_database_manifest(database_root)
    assert manifest["files"][0]["package_member"] == "dataset/normalized/run_001_normalized.csv"


def test_catalogue_can_be_used_as_assessment_datasource(tmp_path: Path) -> None:
    source_path = tmp_path / "run_001_stress_strain.csv"
    _write_curve(source_path)
    database_root = tmp_path / "curve_database"
    imported = labeller.import_curve_files([source_path], database_root=database_root)
    curve = imported[0]
    boundary_step = labeller.default_boundary_step()
    boundary_step["parameters"]["end_policy"] = "max_abs_load"
    label_path = database_root / "labels.json"
    catalog = {"schema_id": "dev.boundary_label_catalog.v0_1", "labels": []}
    labeller.upsert_label(catalog, labeller.build_label_record(curve, start_index=0, end_index=2))
    labeller.write_label_catalog(label_path, catalog)

    report = labeller.assess_labels(
        label_path,
        data_root=database_root / "raw",
        method_path=None,
        gate_step=labeller.default_gate_step(),
        boundary_step=boundary_step,
    )

    assert report["summary"]["assessed_count"] == 1
    assert report["results"][0]["source_path"].endswith(".csv")


def _write_curve(path: Path) -> None:
    rows = [
        (0, 0.0000, 0.0, 0.0),
        (1, 0.0010, 10.0, 100.0),
        (2, 0.0020, 30.0, 300.0),
        (3, 0.0030, 20.0, 200.0),
        (4, 0.0040, 5.0, 50.0),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "point_index", "curve_scope", "mean_strain", "stress_MPa", "load_N", "time_s"])
        for point_index, strain, stress, load in rows:
            writer.writerow(["run_001", point_index, "full", strain, stress, load, point_index * 0.1])


def _write_machine_raw_curve(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Time", "Displacement", "Force", "Front strain", "Rear strain"])
        writer.writerow(["(s)", "(mm)", "(N)", "(usn)", "(usn)"])
        writer.writerow(["0.0", "0.0", "0.0", "0.0", "0.0"])
        writer.writerow(["0.1", "0.1", "100.0", "-10.0", "-20.0"])
        writer.writerow(["0.2", "0.2", "250.0", "-30.0", "-50.0"])
        writer.writerow(["0.3", "0.3", "200.0", "-40.0", "-60.0"])
