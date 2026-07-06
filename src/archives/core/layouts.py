from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class MTDPLayout(Protocol):
    name: str
    manifest: str
    schema: str
    dataset: str
    provenance: str
    checksums: str
    raw_prefix: str
    normalized_prefix: str

    @staticmethod
    def run_stem(member: str) -> str: ...


class MTDPLegacyLayout:
    name = "mtdp.legacy.v1"
    manifest = "manifest.json"
    schema = "schema.json"
    dataset = "dataset.json"
    provenance = "provenance.json"
    checksums = "checksums.json"
    raw_prefix = "raw/"
    normalized_prefix = "normalized/"

    @staticmethod
    def run_stem(member: str) -> str:
        return PurePosixPath(member).stem


class MTDPAlignedLayout:
    name = "mtdp.aligned.v1"
    manifest = "metadata/manifest.json"
    schema = "metadata/schema.json"
    dataset = "metadata/dataset.json"
    provenance = "metadata/provenance.json"
    checksums = "metadata/checksums.json"
    raw_prefix = "dataset/raw/"
    normalized_prefix = "dataset/normalized/"

    @staticmethod
    def run_stem(member: str) -> str:
        stem = PurePosixPath(member).stem
        for suffix in ("_normalized", "_raw"):
            if stem.endswith(suffix):
                return stem[: -len(suffix)]
        return stem


class MTDAAlignedLayout:
    name = "mtda.aligned.v1"
    index = "index.html"
    dataset_root = "dataset/"
    metadata_root = "metadata/"
    raw_prefix = "dataset/00_raw/"
    normalized_prefix = "dataset/01_normalized/"
    processed_prefix = "dataset/02_processed/"
    aggregate_prefix = "dataset/03_aggregate/"
    reports_prefix = "dataset/04_reports/"
    manifest = "metadata/manifest.json"
    schema = "metadata/schema.json"
    dataset = "metadata/dataset.json"
    provenance = "metadata/provenance.json"
    surface_manifest = "metadata/surface_manifest.json"
    checksums = "metadata/checksums.json"
    software_prefix = "metadata/software/"
    validation = "metadata/software/validation.json"
    readiness = "metadata/software/readiness.json"
    method_outputs = "metadata/software/method_outputs.json"
    removed_standard_prefixes = (
        "report/",
        "audit/",
        "software/",
        "workbench/",
        "interactive_report/",
        "compatibility/",
        "acceptance/",
        "validation/",
        "readiness/",
        "mapping/",
        "method_outputs/",
        "method_package/",
        "dataset/00_source/",
        "dataset/05_plots/",
    )
    removed_standard_members = ("archive_index.csv", "README.md")


class ExportLayout:
    manifest = "export_manifest.json"
    provenance = "export_provenance.json"
    checksums = "export_checksums.json"
    reports_prefix = "reports/"
    tables_prefix = "tables/"
    figures_prefix = "figures/"


def detect_mtdp_layout(names: set[str]) -> type[MTDPAlignedLayout] | type[MTDPLegacyLayout]:
    if MTDPAlignedLayout.manifest in names:
        return MTDPAlignedLayout
    if MTDPLegacyLayout.manifest in names:
        return MTDPLegacyLayout
    raise ValueError("MTDP archive does not contain a recognized manifest member.")


def mtdp_metadata_member(name: str, layout: type[MTDPLayout]) -> str:
    key = name.removesuffix(".json")
    members = {
        "manifest": layout.manifest,
        "schema": layout.schema,
        "dataset": layout.dataset,
        "provenance": layout.provenance,
        "checksums": layout.checksums,
    }
    try:
        return members[key]
    except KeyError as exc:
        raise KeyError(f"Unknown MTDP metadata member: {name}") from exc


def mtdp_raw_prefix(layout: type[MTDPLayout]) -> str:
    return layout.raw_prefix


def mtdp_normalized_prefix(layout: type[MTDPLayout]) -> str:
    return layout.normalized_prefix


def mtda_run_label(run_id: str, display_index: int | None = None) -> str:
    text = str(run_id or "").strip()
    if text.startswith("run_"):
        suffix = text.removeprefix("run_")
        if suffix.isdigit():
            return f"run_{int(suffix):03d}"
    if display_index is not None:
        return f"run_{display_index:03d}"
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in text).strip("_")
    return safe or "run"


def processed_run_member(run_label: str, artifact_kind: str) -> str:
    names = {
        "stress_strain_csv": f"{run_label}_stress_strain.csv",
        "stress_strain_experiment_bound_csv": f"{run_label}_stress_strain_experiment_bound.csv",
        "bending_csv": f"{run_label}_bending.csv",
        "plot_spec": f"{run_label}_plot.vl.json",
        "plot_html": f"{run_label}_plot.html",
        "plot_manifest": f"{run_label}_plot_manifest.csv",
    }
    try:
        return MTDAAlignedLayout.processed_prefix + names[artifact_kind]
    except KeyError as exc:
        raise KeyError(f"Unknown processed run artifact kind: {artifact_kind}") from exc


def aggregate_member(name: str) -> str:
    return MTDAAlignedLayout.aggregate_prefix + name.lstrip("/")


def report_member(name: str) -> str:
    return MTDAAlignedLayout.reports_prefix + name.lstrip("/")


def metadata_member(name: str) -> str:
    return MTDAAlignedLayout.metadata_root + name.lstrip("/")
