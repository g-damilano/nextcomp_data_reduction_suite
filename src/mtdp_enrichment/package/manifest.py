from __future__ import annotations

from mtdp_enrichment.package.schema import MTDPSchema

PACKAGE_FORMAT = "mtdp"
FORMAT_VERSION = "0.2.0"


def build_manifest(schema: MTDPSchema) -> dict[str, str]:
    return {
        "package_format": PACKAGE_FORMAT,
        "format_version": FORMAT_VERSION,
        "schema_id": schema.schema_id,
        "schema_version": schema.schema_version,
    }


DISALLOWED_MANIFEST_FIELDS = {"stage", "primary_data_file", "raw_files", "run_files"}
