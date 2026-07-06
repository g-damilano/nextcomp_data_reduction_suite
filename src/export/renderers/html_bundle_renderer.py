from __future__ import annotations

import os
from typing import Any

from markupsafe import Markup

from html_renderer.context_models import ExportHtmlPageContext, ExportHtmlPageMetadataRowContext
from html_renderer.projection_planes import ProjectionPlane
from html_renderer.recipe_projection import RecipeResultKind
from html_renderer.render import render_export_html_page


def html_page(*, title: str, body: str, metadata: dict[str, Any] | None = None) -> bytes:
    if os.environ.get("MTDA_HTML_RENDERER", "jinja").casefold() == "legacy":
        return _legacy_html_page(title=title, body=body, metadata=metadata)
    return render_export_html_page(_export_html_page_context(title=title, body=body, metadata=metadata)).encode("utf-8")


def _legacy_html_page(*, title: str, body: str, metadata: dict[str, Any] | None = None) -> bytes:
    meta = metadata or {}
    rows = "".join(f"<dt>{_escape(k)}</dt><dd>{_escape(v)}</dd>" for k, v in meta.items())
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #202124; }}
    dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; }}
    dt {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{_escape(title)}</h1>
  <dl>{rows}</dl>
  {body}
</body>
</html>
"""
    return html.encode("utf-8")


def _export_html_page_context(*, title: str, body: str, metadata: dict[str, Any] | None = None) -> ExportHtmlPageContext:
    meta = metadata or {}
    return ExportHtmlPageContext(
        projection_plane=ProjectionPlane.EXPORT_BUNDLE,
        recipe_result_kind=RecipeResultKind.EXPORT_HTML_PAGE,
        title_html=Markup(_escape(title)),
        metadata_rows=tuple(
            ExportHtmlPageMetadataRowContext(key_html=Markup(_escape(key)), value_html=Markup(_escape(value)))
            for key, value in meta.items()
        ),
        body_html=Markup(body),
    )


def _escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
