from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from operations.core.operation_context import OperationContext
from operations.core.operation_result import OperationResult


class Operation(ABC):
    operation_id: str

    @abstractmethod
    def run(self, context: OperationContext, step: Mapping[str, Any]) -> list[OperationResult]:
        raise NotImplementedError

