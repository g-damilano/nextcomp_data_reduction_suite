from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable

from archives.mtdp.models import MTDPPackageInput
from inspector.curve_inspector import CurveInspector
from methods.core.method_package import MethodPackage
from operations.core.operation_context import OperationContext, OperationRun
from operations.core.operation_registry import OperationRegistry, default_operation_registry
from operations.core.operation_result import OperationResult


@dataclass(slots=True)
class MethodRunContext:
    source: MTDPPackageInput
    method_package: MethodPackage
    mapping: dict[str, object]
    registry: OperationRegistry = field(default_factory=default_operation_registry)
    inspector: CurveInspector = field(default_factory=CurveInspector)
    runs: dict[str, OperationRun] = field(init=False)
    operation_log: list[dict[str, object]] = field(default_factory=list)
    inspections: list[dict[str, object]] = field(default_factory=list)
    warnings: list[dict[str, object]] = field(default_factory=list)
    _sequence: int = 0

    def __post_init__(self) -> None:
        self.runs = {
            run.run_id: OperationRun(
                source_run=run,
                metadata={
                    "normalized_package_path": run.normalized_package_path,
                    "raw_package_path": run.raw_package_path,
                    "original_filename": run.original_filename,
                },
            )
            for run in self.source.runs
        }

    def operation_context(self, phase: str, *, cancel_requested: Callable[[], bool] | None = None) -> OperationContext:
        return OperationContext(
            source=self.source,
            mapping=self.mapping,
            runs=self.runs,
            inspector=self.inspector,
            phase=phase,
            inspections=self.inspections,
            cancel_requested=cancel_requested,
        )

    def record(self, results: list[OperationResult]) -> None:
        for result in results:
            self._sequence += 1
            self.operation_log.append(result.to_record(self._sequence))
            for warning in result.warnings:
                self.warnings.append(
                    {
                        "sequence": self._sequence,
                        "phase": result.phase,
                        "operation": result.operation_type or result.operation_id,
                        "run_id": result.run_id,
                        "message": warning,
                    }
                )
