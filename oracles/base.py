"""Oracle base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class OracleBase(ABC):
    """Base class for semantic oracles.

    Oracles validate semantic correctness beyond basic success/failure.
    They are stateless - all state is provided via context from the executor.
    """

    @abstractmethod
    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """
        Validate semantic correctness.

        Args:
            case: Original test case
            result: Execution result
            context: Additional context (e.g., mock_state, unfiltered_result_ids)

        Returns:
            OracleResult with passed/failed, metrics, explanation
        """
        pass
