from __future__ import annotations

from mtdp_enrichment.image_gateway.models import RunImageEvidence


class ImageMetrologyAdapter:
    """Future boundary for external image-assisted metrology modules."""

    adapter_name = "external_image_metrology"
    adapter_version = "0.0.0"

    def measure(self, images: tuple[RunImageEvidence, ...]) -> dict[str, object]:
        raise NotImplementedError("Image metrology is intentionally outside the v0 enrichment tool.")
