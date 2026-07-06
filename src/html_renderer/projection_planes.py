from __future__ import annotations

from enum import StrEnum


class ProjectionPlane(StrEnum):
    TEST = "test"
    AUDIT = "audit"
    MTDA_BUNDLE_VIEWER = "mtda_bundle_viewer"
    EXPORT_BUNDLE = "export_bundle"
