from __future__ import annotations

from typing import Any

from reporting.blocks.acceptance_summary import AcceptanceSummaryBlock
from reporting.blocks.artifact_link import ArtifactLinkBlock
from reporting.blocks.base import ReportBlock
from reporting.blocks.discharge_summary import DischargeSummaryBlock
from reporting.blocks.field_table import FieldTableBlock
from reporting.blocks.missing_fields_table import MissingFieldsTableBlock
from reporting.blocks.readiness_summary import ReadinessSummaryBlock
from reporting.blocks.scalar_table import TableBlock
from reporting.blocks.summary_cards import SummaryCardsBlock
from reporting.blocks.text import TextBlock
from reporting.blocks.validation_summary import ValidationSummaryBlock
from reporting.blocks.values_used_table import ValuesUsedTableBlock
from reporting.blocks.vega_plot import VegaPlotBlock
from reporting.core.data_provider_registry import DataProviderRegistry
from reporting.core.report_context import ReportContext
from reporting.core.report_document import ReportBlockDocument


class BlockRegistry:
    """Registry of reusable recipe block implementations."""

    def __init__(self) -> None:
        self._blocks: dict[str, ReportBlock] = {}
        for block in (
            FieldTableBlock(),
            TableBlock(),
            SummaryCardsBlock(),
            ReadinessSummaryBlock(),
            ValidationSummaryBlock(),
            AcceptanceSummaryBlock(),
            DischargeSummaryBlock(),
            ValuesUsedTableBlock(),
            MissingFieldsTableBlock(),
            VegaPlotBlock(),
            TextBlock(),
            ArtifactLinkBlock(),
        ):
            self.register(block.block_type, block)

    def register(self, block_type: str, block: ReportBlock) -> None:
        self._blocks[block_type] = block

    def resolve(
        self,
        block: dict[str, Any],
        context: ReportContext,
        providers: DataProviderRegistry,
    ) -> ReportBlockDocument:
        block_type = str(block.get("type") or "table")
        try:
            implementation = self._blocks[block_type]
        except KeyError as exc:
            raise KeyError(f"Unknown report block type: {block_type}") from exc
        return implementation.resolve(block, context, providers)

    def block_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._blocks))
