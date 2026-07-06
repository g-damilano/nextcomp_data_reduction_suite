from .schema import MTDPSchema, MetadataSection, TableColumnDefinition
from .migrator import (
    MTDPMigrator,
    MigrationIssue,
    MigrationOperation,
    MigrationPlan,
    MigrationRegistry,
    MigrationResult,
    MigrationReviewState,
)
from .validator import MTDPPackageValidator

_LAZY_EXPORTS = {
    "MTDPPackage",
    "MTDPPackageReader",
    "MTDPPackageUpdater",
    "MTDPPackageWriter",
    "RunInput",
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        from . import mtdp_package

        value = getattr(mtdp_package, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MTDPMigrator",
    "MTDPPackage",
    "MTDPPackageReader",
    "MTDPPackageUpdater",
    "MTDPPackageValidator",
    "MTDPPackageWriter",
    "MTDPSchema",
    "MetadataSection",
    "MigrationIssue",
    "MigrationOperation",
    "MigrationPlan",
    "MigrationRegistry",
    "MigrationResult",
    "MigrationReviewState",
    "RunInput",
    "TableColumnDefinition",
]
