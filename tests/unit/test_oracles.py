"""Tests for Oracle classes."""

import pytest

from oracles.base import OracleBase
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity, ObservedOutcome
from schemas.result import ExecutionResult, OracleResult


class TestOracleBase:
    """Test OracleBase interface."""

    def test_oracle_base_is_abstract(self):
        """Test OracleBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            OracleBase()


class TestWriteReadConsistency:
    """Test WriteReadConsistency oracle."""

    def test_stateless_no_internal_state(self):
        """Test WriteReadConsistency has no internal state."""
        oracle = WriteReadConsistency()
        # Should not have mock_state attribute
        assert not hasattr(oracle, "mock_state") or oracle.mock_state == {}

    def test_consumes_context_mock_state(self):
        """Test oracle consumes mock_state from context."""
        oracle = WriteReadConsistency()

        case = TestCase(
            case_id="test-1",
            operation=OperationType.SEARCH,
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-1",
            adapter_name="MockAdapter",
            request={"operation": "search", "params": {}},
            response={"data": [{"id": 1}, {"id": 2}]},
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        # Context with 3 written vectors
        context = {"mock_state": {"test": [{"vec": [1, 2, 3]}, {"vec": [4, 5, 6]}, {"vec": [7, 8, 9]}]}}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is True
        assert oracle_result.oracle_id == "write_read_consistency"

    def test_fails_when_more_returned_than_written(self):
        """Test oracle fails when more results returned than written."""
        oracle = WriteReadConsistency()

        case = TestCase(
            case_id="test-2",
            operation=OperationType.SEARCH,
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-2",
            adapter_name="MockAdapter",
            request={"operation": "search", "params": {}},
            response={"data": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]},
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        # Context with only 2 written vectors, but 5 results returned
        context = {"mock_state": {"test": [{"vec": [1, 2, 3]}, {"vec": [4, 5, 6]}]}}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is False
        assert oracle_result.metrics["written"] == 2
        assert oracle_result.metrics["returned"] == 5

    def test_skips_non_search_operations(self):
        """Test oracle skips non-search operations."""
        oracle = WriteReadConsistency()

        case = TestCase(
            case_id="test-3",
            operation=OperationType.INSERT,
            params={"collection_name": "test", "vectors": []},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-3",
            adapter_name="MockAdapter",
            request={"operation": "insert", "params": {}},
            response={"status": "success"},
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        context = {"mock_state": {}}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is True  # Skipped, so passes by default


class TestFilterStrictness:
    """Test FilterStrictness oracle."""

    def test_skips_non_filtered_search(self):
        """Test oracle skips non-filtered_search operations."""
        oracle = FilterStrictness()

        case = TestCase(
            case_id="test-1",
            operation=OperationType.SEARCH,  # Not FILTERED_SEARCH
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-1",
            adapter_name="MockAdapter",
            request={"operation": "search", "params": {}},
            response={"data": [{"id": 1}, {"id": 2}]},
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        context = {}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is True
        assert "N/A" in oracle_result.explanation

    def test_subset_validation_pass(self):
        """Test ID-based subset validation passes."""
        oracle = FilterStrictness()

        case = TestCase(
            case_id="test-2",
            operation=OperationType.FILTERED_SEARCH,
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-2",
            adapter_name="MockAdapter",
            request={"operation": "filtered_search", "params": {}},
            response={"data": [{"id": 2}, {"id": 4}]},  # Subset of [1,2,3,4,5]
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        context = {"unfiltered_result_ids": [1, 2, 3, 4, 5]}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is True
        assert oracle_result.metrics["unfiltered_count"] == 5
        assert oracle_result.metrics["filtered_count"] == 2

    def test_subset_validation_fail_with_unexpected_ids(self):
        """Test ID-based subset validation fails with unexpected IDs."""
        oracle = FilterStrictness()

        case = TestCase(
            case_id="test-3",
            operation=OperationType.FILTERED_SEARCH,
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = ExecutionResult(
            run_id="run-1",
            case_id="test-3",
            adapter_name="MockAdapter",
            request={"operation": "filtered_search", "params": {}},
            response={"data": [{"id": 2}, {"id": 6}]},  # 6 not in [1,2,3,4,5]
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        context = {"unfiltered_result_ids": [1, 2, 3, 4, 5]}

        oracle_result = oracle.validate(case, result, context)
        assert oracle_result.passed is False
        assert 6 in oracle_result.metrics["unexpected_ids"]
        assert oracle_result.metrics["unfiltered_count"] == 5
        assert oracle_result.metrics["filtered_count"] == 2

    def test_not_count_based(self):
        """Test oracle uses ID-based validation, not just counts."""
        oracle = FilterStrictness()

        case = TestCase(
            case_id="test-4",
            operation=OperationType.FILTERED_SEARCH,
            params={"collection_name": "test"},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        # Different IDs, same count - should fail
        result = ExecutionResult(
            run_id="run-1",
            case_id="test-4",
            adapter_name="MockAdapter",
            request={"operation": "filtered_search", "params": {}},
            response={"data": [{"id": 6}, {"id": 7}]},  # Same count (2), different IDs
            observed_outcome=ObservedOutcome.SUCCESS,
            latency_ms=10.0,
            precondition_pass=True,
            gate_trace=[]
        )

        context = {"unfiltered_result_ids": [1, 2, 3, 4, 5]}

        oracle_result = oracle.validate(case, result, context)
        # Should fail because IDs [6,7] are not subset of [1,2,3,4,5]
        # Even though count (2) <= unfiltered count (5)
        assert oracle_result.passed is False
        assert set(oracle_result.metrics["unexpected_ids"]) == {6, 7}
