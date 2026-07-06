from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export import ExportRequest, ExportService
from methods.core.method_run_service import MethodRunRequest, MethodRunService
from runtime.rc_manifest import build_rc_release_manifest
from runtime.resources import ResourceResolver, default_resolver
from ui.method_run_wizard.method_registry import MethodRegistry


INPUT = ROOT / "datasets" / "Packed" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


def test_resource_resolver_finds_source_mode_runtime_resources() -> None:
    resolver = default_resolver()

    assert resolver.method_registry_path().is_file()
    assert resolver.schema_library_root().is_dir()
    assert resolver.method_package_path("src/methods/iso14126").is_dir()
    assert resolver.mapping_profile_path("mappings/iso14126_manual.json").is_file()
    inventory = resolver.inventory()
    assert inventory["mode"] == "source"
    assert "iso14126/method_manifest.yaml" in inventory["method_packages"]
    assert "iso14126_manual.json" in inventory["mapping_profiles"]


def test_method_registry_uses_resolved_resources() -> None:
    registry = MethodRegistry.load()
    entry = registry.by_id("iso14126_2023")

    assert entry.method_path.is_dir()
    assert entry.default_mapping_path is not None
    assert entry.default_mapping_path.is_file()


def test_resource_resolver_supports_packaged_layout_simulation(tmp_path: Path) -> None:
    packaged = tmp_path / "packaged"
    shutil.copytree(ROOT / "config", packaged / "config")
    shutil.copytree(ROOT / "mappings", packaged / "mappings")
    shutil.copytree(ROOT / "src" / "methods", packaged / "src" / "methods")
    shutil.copytree(
        ROOT / "src" / "mtdp_enrichment" / "schema_library",
        packaged / "mtdp_enrichment" / "schema_library",
    )
    shutil.copytree(ROOT / "src" / "mtdp_enrichment" / "assets", packaged / "mtdp_enrichment" / "assets")
    resolver = ResourceResolver(source_root=ROOT, runtime_root=packaged, frozen=True)

    assert resolver.method_registry_path() == packaged / "config" / "method_registry.yaml"
    assert resolver.schema_library_root() == packaged / "mtdp_enrichment" / "schema_library"
    assert resolver.method_package_path("src/methods/iso14126").is_dir()
    assert resolver.mapping_profile_path("mappings/iso14126_manual.json").is_file()
    assert resolver.package_asset_root() == packaged / "mtdp_enrichment" / "assets"
    assert resolver.inventory()["mode"] == "frozen"


def test_resource_resolver_prefers_external_frozen_resource_folder(tmp_path: Path) -> None:
    extracted = tmp_path / "_MEIPASS"
    external = tmp_path / "appdata" / "NextCOMP" / "mtdp_enrichment"
    shutil.copytree(ROOT / "config", external / "config")
    shutil.copytree(ROOT / "mappings", external / "mappings")
    shutil.copytree(ROOT / "src" / "methods", external / "src" / "methods")
    shutil.copytree(
        ROOT / "src" / "mtdp_enrichment" / "schema_library",
        external / "mtdp_enrichment" / "schema_library",
    )
    shutil.copytree(ROOT / "src" / "mtdp_enrichment" / "assets", external / "mtdp_enrichment" / "assets")
    (extracted / "config").mkdir(parents=True)
    (extracted / "config" / "method_registry.yaml").write_text("stale: true\n", encoding="utf-8")

    resolver = ResourceResolver(source_root=ROOT, runtime_root=extracted, frozen=True, external_root=external)

    assert resolver.method_registry_path() == external / "config" / "method_registry.yaml"
    assert resolver.schema_library_root() == external / "mtdp_enrichment" / "schema_library"
    assert resolver.package_asset_root() == external / "mtdp_enrichment" / "assets"


def test_resource_resolver_discovers_frozen_external_root_in_appdata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extracted = tmp_path / "_MEIPASS"
    appdata = tmp_path / "Roaming"
    extracted.mkdir()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(extracted), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "mtdp_enrichment.exe"))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.delenv("MTDP_ENRICHMENT_RESOURCE_ROOT", raising=False)

    resolver = ResourceResolver.discover()

    assert resolver.external_root == appdata / "NextCOMP" / "mtdp_enrichment"


def test_resource_resolver_honors_resource_root_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extracted = tmp_path / "_MEIPASS"
    external = tmp_path / "custom_resources"
    extracted.mkdir()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(extracted), raising=False)
    monkeypatch.setenv("MTDP_ENRICHMENT_RESOURCE_ROOT", str(external))

    resolver = ResourceResolver.discover()

    assert resolver.external_root == external.resolve()


def test_resource_resolver_materializes_missing_external_editable_resources(tmp_path: Path) -> None:
    extracted = tmp_path / "_MEIPASS"
    external = tmp_path / "appdata" / "NextCOMP" / "mtdp_enrichment"

    (extracted / "config").mkdir(parents=True)
    (extracted / "config" / "method_registry.yaml").write_text("default: true\n", encoding="utf-8")
    (extracted / "mappings").mkdir()
    (extracted / "mappings" / "default.json").write_text("{}\n", encoding="utf-8")
    (extracted / "src" / "methods" / "iso14126").mkdir(parents=True)
    (extracted / "src" / "methods" / "iso14126" / "method_manifest.yaml").write_text(
        "method_id: iso14126_2023\n",
        encoding="utf-8",
    )
    (extracted / "src" / "methods" / "iso14126" / "__init__.py").write_text("# do not copy\n", encoding="utf-8")
    (extracted / "mtdp_enrichment" / "schema_library").mkdir(parents=True)
    (extracted / "mtdp_enrichment" / "schema_library" / "schema.yaml").write_text(
        "schema: true\n",
        encoding="utf-8",
    )
    (extracted / "mtdp_enrichment" / "assets" / "icons").mkdir(parents=True)
    (extracted / "mtdp_enrichment" / "assets" / "icons" / "icon.png").write_bytes(b"png")
    (external / "config").mkdir(parents=True)
    (external / "config" / "method_registry.yaml").write_text("edited: true\n", encoding="utf-8")

    resolver = ResourceResolver(source_root=ROOT, runtime_root=extracted, frozen=True, external_root=external)
    materialized = resolver.materialize_external_resources(strict=True)

    assert external / "mappings" in materialized
    assert external / "src" / "methods" in materialized
    assert (external / "config" / "method_registry.yaml").read_text(encoding="utf-8") == "edited: true\n"
    assert (external / "mappings" / "default.json").is_file()
    assert (external / "src" / "methods" / "iso14126" / "method_manifest.yaml").is_file()
    assert not (external / "src" / "methods" / "iso14126" / "__init__.py").exists()
    assert (external / "mtdp_enrichment" / "schema_library" / "schema.yaml").is_file()
    assert (external / "mtdp_enrichment" / "assets" / "icons" / "icon.png").is_file()


def test_pyinstaller_spec_uses_compression_module_release_shape() -> None:
    spec = (ROOT / "mtdp_enrichment.spec").read_text(encoding="utf-8")

    assert '["src/mtdp_enrichment/react_shell_app.py"]' in spec
    assert 'tree_datas_all(react_frontend / "dist", "react_gui/dist")' in spec
    assert 'tree_datas(react_frontend / "desktop", "react_gui/desktop", {".py"})' in spec
    assert 'name="mtdp_enrichment"' in spec
    assert "exclude_binaries=False" in spec
    assert "COLLECT(" not in spec


def test_rc_release_manifest_contains_required_handoff_fields() -> None:
    manifest = build_rc_release_manifest(smoke_test_status="passed")

    assert manifest["schema_id"] == "compression_module.rc_release_manifest.v0_1"
    assert manifest["app"]["version"]
    assert manifest["smoke_test_status"] == "passed"
    assert manifest["resources"]["method_registry"].endswith("config\\method_registry.yaml") or manifest["resources"]["method_registry"].endswith("config/method_registry.yaml")
    assert any(method["method_id"] == "iso14126_2023" for method in manifest["supported_method_packages"])
    assert "PDF/DOCX export deferred" in manifest["known_residuals"]


def test_build_rc_script_writes_release_candidate_manifest_and_uat_docs(tmp_path: Path) -> None:
    output = tmp_path / "release_candidate"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_rc.py"),
            "--output",
            str(output),
            "--smoke-test-status",
            "passed",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    manifest = json.loads((output / "rc_release_manifest.json").read_text(encoding="utf-8"))

    assert "RC handoff written" in completed.stdout
    assert manifest["smoke_test_status"] == "passed"
    assert (output / "docs" / "RC_UAT_SMOKE_SCRIPT.md").exists()
    assert (output / "docs" / "RC_UAT_FEEDBACK_FORM.md").exists()


def test_rc_smoke_path_does_not_mutate_input_package(tmp_path: Path) -> None:
    before = _sha256(INPUT)
    mtda = tmp_path / "smoke.mtda"
    export_dir = tmp_path / "export"

    run = MethodRunService().run(
        MethodRunRequest(
            input_package_path=INPUT,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=mtda,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert run.status == "completed"
    export = ExportService().export(ExportRequest(mtda, export_dir, "minimal"))

    assert export.status == "exported"
    assert _sha256(INPUT) == before
    assert (export_dir / "reports" / "test_report.html").exists()
    assert (export_dir / "export_manifest.json").exists()


def test_generated_artifact_policy_is_enforced_by_ignore_and_docs() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    policy = (ROOT / "docs" / "release" / "RC_BUILD_AND_HANDOFF.md").read_text(encoding="utf-8")

    assert "release_candidate/" in gitignore
    assert "*.mtda" in gitignore
    assert "*.mtdp" in gitignore
    assert "Generated Artifact Policy" in policy
    assert "temporary test directories" in policy


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
