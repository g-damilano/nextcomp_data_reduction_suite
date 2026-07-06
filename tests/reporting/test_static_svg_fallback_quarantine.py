from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from archives.core.layouts import MTDAAlignedLayout


TEST_REPORT_HTML = f"{MTDAAlignedLayout.reports_prefix}test_report.html"
STATIC_FALLBACK_SVG_RE = re.compile(
    r'<svg\b[^>]*role="img"[^>]*aria-label="(?:Aggregate plot|Bending distribution preview)"'
)


def test_formal_report_static_svgs_are_quarantined_vega_fallbacks(stage26_canonical_mtda: Path) -> None:
    html = _text_member(stage26_canonical_mtda, TEST_REPORT_HTML)
    plot_ids = re.findall(r'<div class="plot" data-vega-block="([^"]+)">', html)

    assert plot_ids
    assert "window.vegaEmbed(target, spec, {actions: false, renderer: \"svg\"})" in html
    assert 'fallback.style.display = "none";' in html

    fallback_ranges: list[tuple[int, int]] = []
    for plot_id in plot_ids:
        block_start = html.index(f'<div class="plot" data-vega-block="{plot_id}">')
        fallback_start = html.index('<div class="vega-fallback">', block_start)
        chart_start = html.index(f'<div id="{plot_id}" class="vega-chart"', block_start)
        script_token = f'<script type="application/json" id="{plot_id}-spec">'
        script_start = html.index(script_token, block_start)

        assert fallback_start < chart_start < script_start

        fallback_body_start = fallback_start + len('<div class="vega-fallback">')
        fallback_body_end = html.index("</div>", fallback_body_start)
        fallback_ranges.append((fallback_body_start, fallback_body_end))

        spec_start = script_start + len(script_token)
        spec_end = html.index("</script>", spec_start)
        spec = json.loads(html[spec_start:spec_end])
        assert spec.get("$schema", "").startswith("https://vega.github.io/schema/vega-lite/")
        assert spec.get("mark") or spec.get("layer") or spec.get("hconcat") or spec.get("vconcat")

    static_svg_positions = [match.start() for match in STATIC_FALLBACK_SVG_RE.finditer(html)]
    assert static_svg_positions
    for position in static_svg_positions:
        assert any(start <= position < end for start, end in fallback_ranges)


def _text_member(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
