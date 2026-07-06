from __future__ import annotations

from typing import Any

from reporting.renderers.html_renderer import HtmlRenderer
from reporting.renderers.json_renderer import JsonRenderer


class RendererRegistry:
    """Registry of report renderers."""

    def __init__(self) -> None:
        self._renderers: dict[str, Any] = {}
        for renderer in (HtmlRenderer(), JsonRenderer()):
            self.register(renderer.renderer_id, renderer)

    def register(self, renderer_id: str, renderer: Any) -> None:
        self._renderers[renderer_id] = renderer

    def get(self, renderer_id: str) -> Any:
        try:
            return self._renderers[renderer_id]
        except KeyError as exc:
            raise KeyError(f"Unknown report renderer: {renderer_id}") from exc

    def renderer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._renderers))
