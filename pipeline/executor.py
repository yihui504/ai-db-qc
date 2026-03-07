"""Test case executor."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from adapters.base import AdapterBase
from pipeline.preconditions import PreconditionEvaluator
from schemas.case import TestCase
from schemas.common import ObservedOutcome, OperationType
from schemas.result import ExecutionResult, OracleResult


class Executor:
    """Execute test cases through precondition evaluator and adapter.

    Manages context (mock_state, write_history, unfiltered_result_ids) and passes to oracles.
    """

    def __init__(
        self,
        adapter: AdapterBase,
        precond: PreconditionEvaluator,
        oracles: List[Any]  # List of OracleBase instances
    ):
        self.adapter = adapter
        self.precond = precond
        self.oracles = oracles
        # Executor-managed state for oracles
        self.mock_state: Dict[str, List[Dict]] = {}  # collection_id -> vectors
        self.write_history: List[Dict[str, Any]] = []  # Track write operations with IDs
        self.unfiltered_result_ids: List[int] = []  # For FilterStrictness

    def execute_case(self, case: TestCase, run_id: str = "run-001") -> ExecutionResult:
        """Execute a single test case."""
        # Step 1: Precondition evaluation
        precondition_pass, gate_trace = self.precond.evaluate(case)

        # Step 2: Build canonical request with operation context
        request = {
            "operation": case.operation.value,
            "params": case.params
        }

        # Step 3: Execute through adapter
        start_time = time.time()
        raw_response = self.adapter.execute(request)
        latency_ms = (time.time() - start_time) * 1000

        # Step 4: Build ExecutionResult
        observed_outcome = self._map_outcome(raw_response)
        error_message = raw_response.get("error") if raw_response.get("status") != "success" else None

        # Step 5: Update executor state based on operation
        self._update_state_for_case(case, raw_response)

        # Step 6: Run oracles with context
        context = {
            "mock_state": self.mock_state,
            "write_history": self.write_history,
            "unfiltered_result_ids": self.unfiltered_result_ids
        }
        oracle_results = []
        for oracle in self.oracles:
            try:
                # Build temporary result for oracle validation
                temp_result = ExecutionResult(
                    run_id=run_id,
                    case_id=case.case_id,
                    adapter_name=type(self.adapter).__name__,
                    request=request,
                    response=raw_response,
                    observed_outcome=observed_outcome,
                    error_message=error_message,
                    latency_ms=latency_ms,
                    precondition_pass=precondition_pass,
                    gate_trace=gate_trace,
                    oracle_results=[]
                )
                result = oracle.validate(case, temp_result, context)
                oracle_results.append(result)
            except Exception:
                # Oracle failed - skip
                pass

        result = ExecutionResult(
            run_id=run_id,
            case_id=case.case_id,
            adapter_name=type(self.adapter).__name__,
            request=request,
            response=raw_response,
            observed_outcome=observed_outcome,
            error_message=error_message,
            latency_ms=latency_ms,
            precondition_pass=precondition_pass,
            gate_trace=gate_trace,
            oracle_results=oracle_results
        )

        return result

    def _update_state_for_case(self, case: TestCase, response: Dict) -> None:
        """Update executor state for context passing to oracles."""
        # Track inserts for WriteReadConsistency
        if case.operation == OperationType.INSERT:
            collection = case.params.get("collection_name")
            vectors = case.params.get("vectors", [])

            # Extract IDs from response for write_history
            ids = []
            if response.get("status") == "success":
                for item in response.get("data", []):
                    if "id" in item:
                        ids.append(item["id"])

            if collection:
                self.mock_state.setdefault(collection, []).extend(vectors)
                # Track write operation with IDs for Phase 4 ID validation
                self.write_history.append({
                    "collection_name": collection,
                    "ids": ids,
                    "count": len(vectors)
                })

        # Track unfiltered search results for FilterStrictness
        if case.operation == OperationType.SEARCH:
            # Extract IDs from response
            result_ids = []
            for item in response.get("data", []):
                if "id" in item:
                    result_ids.append(item["id"])
            self.unfiltered_result_ids = result_ids

    def execute_batch(
        self,
        cases: List[TestCase],
        run_id: str = "run-001"
    ) -> List[ExecutionResult]:
        """Execute multiple test cases."""
        results = []
        for case in cases:
            result = self.execute_case(case, run_id)
            results.append(result)
        return results

    def execute_pair(
        self,
        unfiltered_case: TestCase,
        filtered_case: TestCase,
        run_id: str = "run-001"
    ) -> tuple[ExecutionResult, ExecutionResult]:
        """Execute paired cases for FilterStrictness validation.

        Executes unfiltered case first, then filtered case.
        Passes unfiltered result IDs to oracle context.

        Args:
            unfiltered_case: Case without filter (or with permissive filter)
            filtered_case: Case with restrictive filter
            run_id: Run identifier

        Returns:
            Tuple of (unfiltered_result, filtered_result)
        """
        # Execute unfiltered case first
        unfiltered_result = self.execute_case(unfiltered_case, run_id)

        # Extract IDs from unfiltered result for oracle context
        # Executor already tracks this in _update_state_for_case()
        unfiltered_ids = [
            item.get("id")
            for item in unfiltered_result.response.get("data", [])
            if "id" in item
        ]

        # Execute filtered case (unfiltered_ids is now in executor state)
        filtered_result = self.execute_case(filtered_case, run_id)

        return unfiltered_result, filtered_result

    def _map_outcome(self, response: Dict[str, Any]) -> ObservedOutcome:
        """Map response to ObservedOutcome."""
        status = response.get("status", "unknown")
        if status == "success":
            return ObservedOutcome.SUCCESS
        elif status == "crash":
            return ObservedOutcome.CRASH
        elif status == "hang":
            return ObservedOutcome.HANG
        elif status == "timeout":
            return ObservedOutcome.TIMEOUT
        else:
            return ObservedOutcome.FAILURE
