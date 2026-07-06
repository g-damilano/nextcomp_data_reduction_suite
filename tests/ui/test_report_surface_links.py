from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PACKAGE = ROOT / "datasets" / "Compression" / "CAG-CF-Modied-ULV20.mtdp"
METHOD = ROOT / "src" / "methods" / "iso14126"
MAPPING = ROOT / "mappings" / "iso14126_manual.json"


@pytest.fixture(scope="module")
def interaction_mtda(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from methods.core.method_run_service import MethodRunRequest, MethodRunService

    output_dir = tmp_path_factory.mktemp("ui_report_surface")
    output_path = output_dir / "canonical_interaction.mtda"
    result = MethodRunService().run(
        MethodRunRequest(
            input_package_path=PACKAGE,
            method_path=METHOD,
            mapping_path=MAPPING,
            output_path=output_path,
            overwrite=True,
            generate_workbench=True,
        )
    )
    assert result.status == "completed", result.errors
    return output_path


@pytest.fixture(scope="module")
def extracted_surfaces(interaction_mtda: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("ui_report_surfaces_extracted")
    with zipfile.ZipFile(interaction_mtda) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
    return target


def test_surface_manifest_indexes_operator_launch_surfaces(interaction_mtda: Path) -> None:
    with zipfile.ZipFile(interaction_mtda) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("metadata/surface_manifest.json"))

    assert "metadata/surface_manifest.json" in names
    assert "dataset/04_reports/test_report.html" in names
    assert "dataset/04_reports/test_report_shell.html" in names
    assert "dataset/04_reports/audit_report.html" in names
    assert "dataset/04_reports/audit_report_shell.html" in names
    assert "workbench/index.html" not in names
    assert manifest["layout_version"] == "mtda.aligned.v1"
    assert manifest["surfaces"]["test_report"]["html_member"] == "dataset/04_reports/test_report_shell.html"
    assert manifest["surfaces"]["test_report"]["raw_html_member"] == "dataset/04_reports/test_report.html"
    assert manifest["surfaces"]["audit_report"]["html_member"] == "dataset/04_reports/audit_report_shell.html"
    assert manifest["surfaces"]["audit_report"]["raw_html_member"] == "dataset/04_reports/audit_report.html"
    assert manifest["operator_handoff"]["open_test_report_member"] == "dataset/04_reports/test_report_shell.html"
    assert manifest["operator_handoff"]["open_audit_report_member"] == "dataset/04_reports/audit_report_shell.html"


def test_archive_surface_extraction_replaces_stale_temp_members(tmp_path: Path) -> None:
    from ui.method_run_wizard.controller import _extract_archive_prefix

    archive_path = tmp_path / "surface_cleanup_case.mtda"
    target = Path(tempfile.gettempdir()) / "compression_module_audit" / archive_path.stem
    try:
        target.mkdir(parents=True, exist_ok=True)
        stale = target / "boundary_resolution.json"
        stale.write_text('{"stale": true}', encoding="utf-8")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("audit/audit_report.html", "<html>fresh</html>")

        extracted = _extract_archive_prefix(archive_path, "audit")

        assert extracted == target
        assert (extracted / "audit_report.html").read_text(encoding="utf-8") == "<html>fresh</html>"
        assert not stale.exists()
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_test_report_and_audit_links_are_actionable(extracted_surfaces: Path) -> None:
    report_html = extracted_surfaces / "dataset" / "04_reports" / "test_report.html"
    audit_html = extracted_surfaces / "dataset" / "04_reports" / "audit_report.html"
    method_outputs = extracted_surfaces / "metadata" / "software" / "method_outputs.json"

    assert report_html.exists()
    assert audit_html.exists()
    assert method_outputs.exists()

    report_text = report_html.read_text(encoding="utf-8")
    audit_text = audit_html.read_text(encoding="utf-8")
    method_payload = json.loads(method_outputs.read_text(encoding="utf-8"))

    assert "../audit/audit_report.html" not in report_text
    assert "../workbench/index.html" not in report_text
    assert "Related report surfaces" not in report_text
    assert not re.search(r'href="[^"]*\.\./workbench/index\.html#[^"]*context=audit', audit_text)
    assert 'href="test_report.html"' in audit_text
    assert "operation_trace" in method_payload


def test_report_surfaces_follow_surface_specific_details_policy(extracted_surfaces: Path) -> None:
    report_paths = [
        extracted_surfaces / "dataset" / "04_reports" / "test_report.html",
    ]
    for surface_path in report_paths:
        html = surface_path.read_text(encoding="utf-8")
        detail_tags = re.findall(r"<details\b[^>]*>", html)
        assert detail_tags == []
        assert not re.search(r"<detals\b", html)

    for audit_like_path in [
        extracted_surfaces / "dataset" / "04_reports" / "audit_report.html",
    ]:
        audit_html = audit_like_path.read_text(encoding="utf-8")
        audit_detail_tags = re.findall(r"<details\b[^>]*>", audit_html)
        assert audit_detail_tags == []
        assert 'class="report-tracker"' in audit_html
        assert ".layout { display: grid; grid-template-columns: 310px minmax(0, 1fr);" in audit_html
        assert "Run-wise Evidence Packets" in audit_html
        assert "Decision Register" in audit_html
        assert not re.search(r"<detals\b", audit_html)


def test_operation_trace_is_bundled_without_standalone_workbench(extracted_surfaces: Path) -> None:
    method_outputs = extracted_surfaces / "metadata" / "software" / "method_outputs.json"
    workbench_html = extracted_surfaces / "workbench" / "index.html"

    payload = json.loads(method_outputs.read_text(encoding="utf-8"))
    trace = payload["operation_trace"]

    assert not workbench_html.exists()
    assert trace["trace_format"] == "method_development_trace"
    assert trace["trace_version"] == "0.1.0"
    assert trace["runs"]


def _browser_click_or_assert_links(source: Path, expected_url_part: str, expected_fragment_part: str) -> None:
    if not _browser_available():
        text = source.read_text(encoding="utf-8")
        assert expected_url_part in text
        assert expected_fragment_part in text
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(source.as_uri())
        page.wait_for_load_state("domcontentloaded")
        page.locator(f'a[href*="{expected_url_part}"][href*="{expected_fragment_part}"]').first.click()
        assert expected_url_part.replace("/", "\\") in page.url or expected_url_part in page.url
        assert expected_fragment_part in page.url
        browser.close()


def _browser_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False
