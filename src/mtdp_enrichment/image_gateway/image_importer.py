from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from mtdp_enrichment.image_gateway.models import RunImageEvidence
from mtdp_enrichment.models import ValidationResult

if TYPE_CHECKING:
    from mtdp_enrichment.package.schema import MTDPSchema


DEFAULT_FORMATS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
DEFAULT_VIEWS = ("front", "side", "top", "failure", "scale_reference", "other")
DEFAULT_ROLES = ("audit_evidence", "future_metrology", "failure_documentation", "scale_reference")


class ImageEvidenceImporter:
    """Validate and describe run-level image evidence; no image analysis lives here."""

    def accepted_formats(self, schema: MTDPSchema) -> tuple[str, ...]:
        config = schema.image_evidence_config()
        return tuple(str(item).lower() for item in config.get("accepted_formats", DEFAULT_FORMATS))

    def accepted_views(self, schema: MTDPSchema) -> tuple[str, ...]:
        config = schema.image_evidence_config()
        views = config.get("views", ())
        if not views:
            return DEFAULT_VIEWS
        return tuple(str(item.get("id", "")).strip() for item in views if isinstance(item, dict) and item.get("id"))

    def make_evidence(
        self,
        source_path: str | Path,
        schema: MTDPSchema,
        *,
        view: str | None = None,
        role: str = "audit_evidence",
        used_for_metrology: bool = False,
        notes: str | None = None,
    ) -> tuple[RunImageEvidence | None, ValidationResult]:
        result = ValidationResult()
        path = Path(source_path)
        if path.suffix.lower() not in self.accepted_formats(schema):
            result.add_error(f"Unsupported image format: {path.suffix}", field=str(path), code="unsupported_image_format")
            return None, result

        selected_view = view or self.infer_view(path.name, self.accepted_views(schema))
        accepted_views = set(self.accepted_views(schema))
        if selected_view not in accepted_views:
            result.add_error(f"Unsupported image view: {selected_view}", field=str(path), code="unsupported_image_view")
            return None, result
        if role not in DEFAULT_ROLES:
            result.add_error(f"Unsupported image role: {role}", field=str(path), code="unsupported_image_role")
            return None, result

        return (
            RunImageEvidence(
                source_path=path,
                view=selected_view,
                role=role,
                used_for_metrology=used_for_metrology,
                notes=notes,
            ),
            result,
        )

    def infer_view(self, filename: str, accepted_views: Iterable[str]) -> str:
        accepted = tuple(accepted_views)
        text = filename.casefold()
        for view in accepted:
            if view != "other" and view.casefold() in text:
                return view
        if "fail" in text and "failure" in accepted:
            return "failure"
        if "scale" in text and "scale_reference" in accepted:
            return "scale_reference"
        return "other" if "other" in accepted else accepted[0]
