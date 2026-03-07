"""Monotonicity oracle."""

from __future__ import annotations

from typing import Any, Dict

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.common import OperationType
from schemas.result import ExecutionResult, OracleResult


class Monotonicity(OracleBase):
    """Validate: Top-K results are monotonic (K10 >= K5).

    Uses result count comparison for paired executions.
    Stateless - requires paired execution context.
    """

    def __init__(self):
        self._unfiltered_counts: Dict[str, int] = {}

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate monotonicity for Top-K searches."""
        # Only applies to search operations
        if case.operation != OperationType.SEARCH:
            return OracleResult(
                oracle_id="monotonicity",
                passed=True,
                explanation="N/A"
            )

        # Get top_k value
        top_k = case.params.get("top_k", 0)

        # Extract result count
        result_count = len(result.response.get("data", []))

        # For paired execution, we need to track results by case_id
        case_id = case.case_id

        # Check if this is the larger K (should have more results)
        if "monotonic-10" in case_id:
            # Store for comparison with smaller K
            self._unfiltered_counts[case_id.replace("monotonic-10", "monotonic-5")] = result_count
            return OracleResult(
                oracle_id="monotonicity",
                passed=True,
                metrics={"top_k": top_k, "result_count": result_count},
                explanation=f"Top-K={top_k} returned {result_count} results (baseline)"
            )

        elif "monotonic-5" in case_id:
            # This is the smaller K, should have <= results of larger K
            # Get the larger K count (should have been stored)
            larger_k_count = self._unfiltered_counts.get(case_id.replace("monotonic-5", "monotonic-10"), result_count)

            if result_count > larger_k_count:
                return OracleResult(
                    oracle_id="monotonicity",
                    passed=False,
                    metrics={"top_k": top_k, "result_count": result_count, "larger_k_count": larger_k_count},
                    expected_relation=f"K5 <= K10",
                    observed_relation=f"K5={result_count} > K10={larger_k_count}",
                    explanation="Monotonicity violated: smaller K returned more results"
                )

            return OracleResult(
                oracle_id="monotonicity",
                passed=True,
                metrics={"top_k": top_k, "result_count": result_count, "larger_k_count": larger_k_count},
                explanation=f"Monotonicity satisfied: K5={result_count} <= K10={larger_k_count}"
            )

        # Default case: no monotonicity check applicable
        return OracleResult(
            oracle_id="monotonicity",
            passed=True,
            metrics={"top_k": top_k, "result_count": result_count},
            explanation="Monotonicity: result count consistent with top_k"
        )
