"""Metamorphic oracle for invariant relation testing.

This oracle validates invariant relationships between multiple operations
without relying on a reference system. It addresses the "self-masking"
problem of differential testing where multiple databases have the same bug.

Metamorphic Relations (MRs) defined here:
    MR1: Filter Transitivity - (A AND B) subseteq A
    MR2: Top-K Monotonicity - results(K) subseteq results(K+1)
    MR3: Delete-Count Idempotency - count decreases after delete
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Callable
from enum import Enum

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class MetamorphicRelation(Enum):
    """Metamorphic relations available for validation."""

    FILTER_TRANSITIVITY = "filter_transitivity"
    TOP_K_MONOTONICITY = "top_k_monotonicity"
    DELETE_COUNT_IDEMPOTENCY = "delete_count_idempotency"


class MetamorphicOracle(OracleBase):
    """Validate invariant relations between multiple test cases.

    Unlike traditional oracles that validate a single test case against
    ground truth, metamorphic oracles verify that pairs or sequences of
    related operations maintain semantic invariants.

    This addresses the core limitation of differential testing: if all
    databases under test have the same semantic bug, differential testing
    will miss it. Metamorphic testing can detect such bugs on a single
    database.
    """

    def __init__(self, relation: MetamorphicRelation):
        """Initialize metamorphic oracle with a specific relation.

        Args:
            relation: The metamorphic relation to validate
        """
        self.relation = relation

        # Map relations to validation functions
        self.relation_validators: Dict[MetamorphicRelation, Callable] = {
            MetamorphicRelation.FILTER_TRANSITIVITY: self._validate_filter_transitivity,
            MetamorphicRelation.TOP_K_MONOTONICITY: self._validate_top_k_monotonicity,
            MetamorphicRelation.DELETE_COUNT_IDEMPOTENCY: self._validate_delete_count_idempotency,
        }

    def _extract_result_ids(self, result: ExecutionResult) -> Set[Any]:
        """Extract IDs from a search result."""
        ids = set()
        for item in result.response.get("data", []):
            if "id" in item:
                ids.add(item["id"])
        return ids

    def _extract_result_count(self, result: ExecutionResult) -> int:
        """Extract count from a result."""
        # Search results
        if "data" in result.response:
            return len(result.response["data"])
        # Count operation
        if "count" in result.response:
            return result.response["count"]
        return 0

    def _validate_filter_transitivity(
        self,
        case_a: TestCase,
        result_a: ExecutionResult,
        case_b: TestCase,
        result_b: ExecutionResult
    ) -> OracleResult:
        """Validate MR1: (A AND B) subseteq A.

        If case_a uses filter="A" and case_b uses filter="A AND B",
        then result_b should be a subset of result_a.

        Args:
            case_a: Test case with filter A
            result_a: Result from case_a
            case_b: Test case with filter A AND B
            result_b: Result from case_b
        """
        ids_a = self._extract_result_ids(result_a)
        ids_b = self._extract_result_ids(result_b)

        if not ids_b.issubset(ids_a):
            extra_ids = ids_b - ids_a
            return OracleResult(
                oracle_id="metamorphic",
                passed=False,
                metrics={
                    "filter_a": case_a.params.get("filter", ""),
                    "filter_b": case_b.params.get("filter", ""),
                    "count_a": len(ids_a),
                    "count_b": len(ids_b),
                    "extra_ids": list(extra_ids)[:10]  # Show first 10
                },
                expected_relation="filter(A AND B) ⊆ filter(A)",
                observed_relation=f"Found {len(extra_ids)} IDs in (A AND B) not in A: {list(extra_ids)[:5]}",
                explanation="Filter transitivity violated: adding a filter condition should never expand the result set"
            )

        return OracleResult(
            oracle_id="metamorphic",
            passed=True,
            metrics={
                "filter_a": case_a.params.get("filter", ""),
                "filter_b": case_b.params.get("filter", ""),
                "count_a": len(ids_a),
                "count_b": len(ids_b)
            },
            explanation="Filter transitivity satisfied: (A AND B) ⊆ A"
        )

    def _validate_top_k_monotonicity(
        self,
        case_small: TestCase,
        result_small: ExecutionResult,
        case_large: TestCase,
        result_large: ExecutionResult
    ) -> OracleResult:
        """Validate MR2: results(K) subseteq results(K+1).

        If case_small uses top_k=K and case_large uses top_k=K+1,
        then the first K results should be identical.

        Args:
            case_small: Test case with smaller top_k
            result_small: Result from case_small
            case_large: Test case with larger top_k
            result_large: Result from case_large
        """
        k_small = case_small.params.get("top_k", 0)
        k_large = case_large.params.get("top_k", 0)

        ids_small = self._extract_result_ids(result_small)
        ids_large = self._extract_result_ids(result_large)

        # Check that small result is subset of large result
        if not ids_small.issubset(ids_large):
            missing_ids = ids_small - ids_large
            return OracleResult(
                oracle_id="metamorphic",
                passed=False,
                metrics={
                    "k_small": k_small,
                    "k_large": k_large,
                    "count_small": len(ids_small),
                    "count_large": len(ids_large),
                    "missing_ids": list(missing_ids)[:10]
                },
                expected_relation=f"results({k_small}) ⊆ results({k_large})",
                observed_relation=f"Found {len(missing_ids)} IDs in K={k_small} not in K={k_large}",
                explanation="Top-K monotonicity violated: increasing K should never remove existing results"
            )

        return OracleResult(
            oracle_id="metamorphic",
            passed=True,
            metrics={
                "k_small": k_small,
                "k_large": k_large,
                "count_small": len(ids_small),
                "count_large": len(ids_large)
            },
            explanation=f"Top-K monotonicity satisfied: results({k_small}) ⊆ results({k_large})"
        )

    def _validate_delete_count_idempotency(
        self,
        case_before: TestCase,
        result_before: ExecutionResult,
        case_after: TestCase,
        result_after: ExecutionResult
    ) -> OracleResult:
        """Validate MR3: count strictly decreases after delete.

        If case_before is a count operation and case_after is a count
        operation after deleting some items, then count_after < count_before.

        Args:
            case_before: Count operation before delete
            result_before: Result before delete
            case_after: Count operation after delete
            result_after: Result after delete
        """
        count_before = self._extract_result_count(result_before)
        count_after = self._extract_result_count(result_after)

        if count_after >= count_before:
            return OracleResult(
                oracle_id="metamorphic",
                passed=False,
                metrics={
                    "count_before": count_before,
                    "count_after": count_after,
                    "difference": count_after - count_before
                },
                expected_relation="count_after < count_before",
                observed_relation=f"count_after ({count_after}) >= count_before ({count_before})",
                explanation="Delete-count idempotency violated: deleting items should decrease count"
            )

        return OracleResult(
            oracle_id="metamorphic",
            passed=True,
            metrics={
                "count_before": count_before,
                "count_after": count_after,
                "deleted": count_before - count_after
            },
            explanation=f"Delete-count idempotency satisfied: count decreased from {count_before} to {count_after}"
        )

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate metamorphic relation.

        This method requires paired test cases in context:
        - context["paired_case"]: The related test case
        - context["paired_result"]: The result from the paired case

        Args:
            case: Primary test case
            result: Result from primary case
            context: Contains paired_case and paired_result
        """
        paired_case = context.get("paired_case")
        paired_result = context.get("paired_result")

        if paired_case is None or paired_result is None:
            return OracleResult(
                oracle_id="metamorphic",
                passed=True,
                metrics={},
                explanation="No paired case/result: metamorphic validation skipped"
            )

        validator = self.relation_validators.get(self.relation)
        if validator is None:
            return OracleResult(
                oracle_id="metamorphic",
                passed=True,
                metrics={},
                explanation=f"Metamorphic relation {self.relation} not implemented: validation skipped"
            )

        # For some relations, order of cases matters
        if self.relation == MetamorphicRelation.FILTER_TRANSITIVITY:
            # Expect case_a to be simpler filter, case_b to be compound filter
            filter_a = case.params.get("filter", "")
            filter_b = paired_case.params.get("filter", "")
            if " AND " in filter_b and " AND " not in filter_a:
                return validator(case, result, paired_case, paired_result)
            else:
                return validator(paired_case, paired_result, case, result)

        elif self.relation == MetamorphicRelation.TOP_K_MONOTONICITY:
            k_a = case.params.get("top_k", 0)
            k_b = paired_case.params.get("top_k", 0)
            if k_a < k_b:
                return validator(case, result, paired_case, paired_result)
            else:
                return validator(paired_case, paired_result, case, result)

        elif self.relation == MetamorphicRelation.DELETE_COUNT_IDEMPOTENCY:
            # Expect case_before to be before delete, case_after to be after
            return validator(paired_case, paired_result, case, result)

        return validator(case, result, paired_case, paired_result)
