from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from methods.core.method_result import MethodRunResult
from reporting.completion.report_completion_status import report_completion_status
from reporting.completion.report_field_catalog import build_report_field_catalog
from reporting.completion.report_override import ReportFieldOverride, build_override_ledger, normalize_report_overrides
from reporting.completion.report_value_resolver import ReportValueResolver


@dataclass(frozen=True, slots=True)
class ReportCompletionResult:
    field_catalog: list[dict[str, Any]]
    values_used: list[dict[str, Any]]
    missing_fields: list[dict[str, Any]]
    completion_status: dict[str, Any]
    overrides: tuple[ReportFieldOverride, ...] = ()
    override_ledger: dict[str, Any] | None = None


class ReportCompletionChecker:
    def __init__(self, resolver: ReportValueResolver | None = None) -> None:
        self.resolver = resolver or ReportValueResolver()

    def check(
        self,
        *,
        result: MethodRunResult,
        recipe: dict[str, Any],
        selection_set: str,
        selection_source: str,
        overrides: Any = None,
    ) -> ReportCompletionResult:
        normalized_overrides = normalize_report_overrides(overrides)
        catalog_entries = build_report_field_catalog(recipe, result.source.schema)
        values_used, missing_fields = self.resolver.resolve(
            result=result,
            catalog=catalog_entries,
            selection_set=selection_set,
            selection_source=selection_source,
            overrides=normalized_overrides,
        )
        return ReportCompletionResult(
            field_catalog=[entry.to_dict() for entry in catalog_entries],
            values_used=values_used,
            missing_fields=missing_fields,
            completion_status=report_completion_status(missing_fields),
            overrides=normalized_overrides,
            override_ledger=build_override_ledger(normalized_overrides),
        )
