"""Filter strictness oracle."""

from __future__ import annotations

from typing import Any, Dict

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.common import OperationType
from schemas.result import ExecutionResult, OracleResult


class FilterStrictness(OracleBase):
    """Validate: filtered results are subset of unfiltered.

    Uses ID-based subset validation (not just counts).
    Stateless - consumes unfiltered_result_ids from context.
    """

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate filter strictness."""
        # Only applies to filtered_search
        if case.operation != OperationType.FILTERED_SEARCH:
            return OracleResult(
                oracle_id="filter_strictness",
                passed=True,
                explanation="N/A"
            )

        # Get unfiltered result IDs from executor context
        # Executor populates this when running unfiltered search before filtered search
        unfiltered_ids = set(context.get("unfiltered_result_ids", []))

        # Extract IDs from filtered response
        # MockAdapter returns: {"data": [{"id": 1, ...}, ...]}
        filtered_ids = set()
        for item in result.response.get("data", []):
            if "id" in item:
                filtered_ids.add(item["id"])

        # Check subset: filtered_ids ⊆ unfiltered_ids
        if not filtered_ids.issubset(unfiltered_ids):
            unexpected_ids = filtered_ids - unfiltered_ids
            return OracleResult(
                oracle_id="filter_strictness",
                passed=False,
                metrics={
                    "unfiltered_count": len(unfiltered_ids),
                    "filtered_count": len(filtered_ids),
                    "unexpected_ids": list(unexpected_ids)
                },
                expected_relation="filtered ⊆ unfiltered",
                observed_relation=f"filtered has IDs {list(unexpected_ids)} not in unfiltered",
                explanation="Filter produced results not present in unfiltered search"
            )

        return OracleResult(
            oracle_id="filter_strictness",
            passed=True,
            metrics={
                "unfiltered_count": len(unfiltered_ids),
                "filtered_count": len(filtered_ids)
            },
            explanation="Filter strictness satisfied: all filtered results in unfiltered"
        )
