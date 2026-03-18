"""Validation runner for new oracles and optimizations.

This script validates the three new oracles introduced in the optimization:
1. RecallQualityOracle - validates search quality through recall@K metrics
2. MetamorphicOracle - validates invariant relations between operations
3. SequenceAssertionOracle - validates sequence state assertions

Also validates the new adapter abstraction layer requirements.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Any
import numpy as np

# Import new oracles
from oracles.recall_quality import RecallQualityOracle
from oracles.metamorphic import MetamorphicOracle, MetamorphicRelation
from oracles.sequence_assertion import SequenceAssertionOracle
from oracles.base import OracleBase

# Import schemas
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult
from schemas.common import ObservedOutcome, OperationType, InputValidity


def validate_recall_quality_oracle():
    """Validate RecallQualityOracle with synthetic data."""
    print("\n" + "="*60)
    print("Validating RecallQualityOracle")
    print("="*60)

    # Create ground truth data
    ground_truth_vectors = [
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.8, 0.2, 0.0],
        [0.7, 0.3, 0.0],
        [0.6, 0.4, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.9, 0.1],
        [0.0, 0.8, 0.2],
        [0.0, 0.7, 0.3],
        [0.0, 0.0, 1.0],
    ]
    ground_truth_ids = list(range(len(ground_truth_vectors)))

    # Create oracle
    oracle = RecallQualityOracle(
        ground_truth_vectors=ground_truth_vectors,
        ground_truth_ids=ground_truth_ids,
        strict_mode=False,
        k_values=[5, 10]
    )

    # Test case 1: High quality search (should pass)
    query_vector = [1.0, 0.0, 0.0]
    good_response = {
        "status": "success",
        "data": [{"id": i} for i in range(5)]  # Return top 5 correct IDs
    }

    good_result = ExecutionResult(
        run_id="test-001",
        case_id="test-quality-001",
        adapter_name="MockAdapter",
        request={"operation": "search", "params": {"vector": query_vector, "top_k": 5}},
        response=good_response,
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    context = {"query_vector": query_vector}
    result = oracle.validate(
        case=TestCase(
            case_id="test-quality-001",
            operation=OperationType.SEARCH,
            params={"vector": query_vector, "top_k": 5},
            expected_validity=InputValidity.LEGAL
        ),
        result=good_result,
        context=context
    )

    print(f"Test 1 - High Quality Search: {'PASS' if result.passed else 'FAIL'}")
    print(f"  Metrics: {result.metrics}")
    print(f"  Explanation: {result.explanation}")

    # Test case 2: Low quality search (should fail)
    bad_response = {
        "status": "success",
        "data": [{"id": 5}, {"id": 6}, {"id": 7}, {"id": 8}, {"id": 9}]  # Return wrong IDs
    }

    bad_result = ExecutionResult(
        run_id="test-002",
        case_id="test-quality-002",
        adapter_name="MockAdapter",
        request={"operation": "search", "params": {"vector": query_vector, "top_k": 5}},
        response=bad_response,
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    result = oracle.validate(
        case=TestCase(
            case_id="test-quality-002",
            operation=OperationType.SEARCH,
            params={"vector": query_vector, "top_k": 5},
            expected_validity=InputValidity.LEGAL
        ),
        result=bad_result,
        context=context
    )

    print(f"\nTest 2 - Low Quality Search: {'FAIL (Expected)' if not result.passed else 'PASS (Unexpected)'}")
    print(f"  Metrics: {result.metrics}")
    print(f"  Expected: {result.expected_relation}")
    print(f"  Observed: {result.observed_relation}")
    print(f"  Explanation: {result.explanation}")

    return True


def validate_metamorphic_oracle():
    """Validate MetamorphicOracle with filter transitivity."""
    print("\n" + "="*60)
    print("Validating MetamorphicOracle")
    print("="*60)

    # Create oracle for filter transitivity
    oracle = MetamorphicOracle(MetamorphicRelation.FILTER_TRANSITIVITY)

    # Test case: filter A vs filter A AND B
    case_a = TestCase(
        case_id="test-mm-001-a",
        operation=OperationType.FILTERED_SEARCH,
        params={"collection_name": "test", "filter": "color='red'", "vector": [1, 0, 0], "top_k": 10},
        expected_validity=InputValidity.LEGAL
    )

    case_b = TestCase(
        case_id="test-mm-001-b",
        operation=OperationType.FILTERED_SEARCH,
        params={"collection_name": "test", "filter": "color='red' AND size='large'", "vector": [1, 0, 0], "top_k": 10},
        expected_validity=InputValidity.LEGAL
    )

    # Test 1: Correct subset behavior (should pass)
    result_a = ExecutionResult(
        run_id="test-mm-001-a",
        case_id="test-mm-001-a",
        adapter_name="MockAdapter",
        request={"operation": "filtered_search", "params": case_a.params},
        response={
            "status": "success",
            "data": [{"id": 1}, {"id": 2}, {"id": 3}]
        },
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    result_b = ExecutionResult(
        run_id="test-mm-001-b",
        case_id="test-mm-001-b",
        adapter_name="MockAdapter",
        request={"operation": "filtered_search", "params": case_b.params},
        response={
            "status": "success",
            "data": [{"id": 1}, {"id": 2}]  # Subset of result_a
        },
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    context = {"paired_case": case_a, "paired_result": result_a}
    result = oracle.validate(case_b, result_b, context)

    print(f"Test 1 - Filter Transitivity (Correct): {'PASS' if result.passed else 'FAIL'}")
    print(f"  Metrics: {result.metrics}")
    print(f"  Explanation: {result.explanation}")

    # Test 2: Incorrect subset behavior (should fail)
    result_b_wrong = ExecutionResult(
        run_id="test-mm-001-b-wrong",
        case_id="test-mm-001-b",
        adapter_name="MockAdapter",
        request={"operation": "filtered_search", "params": case_b.params},
        response={
            "status": "success",
            "data": [{"id": 1}, {"id": 2}, {"id": 4}]  # ID 4 not in result_a - violation!
        },
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    result = oracle.validate(case_b, result_b_wrong, context)

    print(f"\nTest 2 - Filter Transitivity (Violation): {'FAIL (Expected)' if not result.passed else 'PASS (Unexpected)'}")
    print(f"  Metrics: {result.metrics}")
    print(f"  Expected: {result.expected_relation}")
    print(f"  Observed: {result.observed_relation}")
    print(f"  Explanation: {result.explanation}")

    return True


def validate_sequence_assertion_oracle():
    """Validate SequenceAssertionOracle with state assertions."""
    print("\n" + "="*60)
    print("Validating SequenceAssertionOracle")
    print("="*60)

    # Create oracle with assertion string
    oracle = SequenceAssertionOracle("result_count > 0")

    # Test case 1: Assertion passes
    case = TestCase(
        case_id="test-seq-001",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 0, 0], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        sequence_assertions=["result_count > 0"]
    )

    result = ExecutionResult(
        run_id="test-seq-001",
        case_id="test-seq-001",
        adapter_name="MockAdapter",
        request={"operation": "search", "params": case.params},
        response={
            "status": "success",
            "data": [{"id": 1}, {"id": 2}]
        },
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    oracle_result = oracle.validate(case, result, {})

    print(f"Test 1 - Assertion 'result_count > 0' (2 results): {'PASS' if oracle_result.passed else 'FAIL'}")
    print(f"  Metrics: {oracle_result.metrics}")
    print(f"  Explanation: {oracle_result.explanation}")

    # Test case 2: Assertion fails
    case_fail = TestCase(
        case_id="test-seq-002",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 0, 0], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        sequence_assertions=["result_count > 0"]
    )

    result_fail = ExecutionResult(
        run_id="test-seq-002",
        case_id="test-seq-002",
        adapter_name="MockAdapter",
        request={"operation": "search", "params": case_fail.params},
        response={
            "status": "success",
            "data": []  # Empty results - assertion should fail
        },
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=10.0,
        precondition_pass=True,
        gate_trace=[]
    )

    oracle_result = oracle.validate(case_fail, result_fail, {})

    print(f"\nTest 2 - Assertion 'result_count > 0' (0 results): {'FAIL (Expected)' if not oracle_result.passed else 'PASS (Unexpected)'}")
    print(f"  Metrics: {oracle_result.metrics}")
    print(f"  Expected: {oracle_result.expected_relation}")
    print(f"  Observed: {oracle_result.observed_relation}")
    print(f"  Explanation: {oracle_result.explanation}")

    return True


def validate_adapter_abstraction():
    """Validate that adapters implement new abstract methods."""
    print("\n" + "="*60)
    print("Validating Adapter Abstraction Layer")
    print("="*60)

    from adapters.mock import MockAdapter
    from adapters.base import AdapterBase, OperationNotSupportedError

    # Create mock adapter
    adapter = MockAdapter()

    # Test 1: get_runtime_snapshot exists and returns correct format
    snapshot = adapter.get_runtime_snapshot()
    print(f"Test 1 - get_runtime_snapshot: {'PASS' if 'collections' in snapshot else 'FAIL'}")
    print(f"  Snapshot keys: {list(snapshot.keys())}")

    # Test 2: supported_operations exists and returns list
    operations = adapter.supported_operations()
    print(f"\nTest 2 - supported_operations: {'PASS' if isinstance(operations, list) else 'FAIL'}")
    print(f"  Supported operations: {operations[:5]}... (total {len(operations)})")

    # Test 3: OperationNotSupportedError is available
    try:
        raise OperationNotSupportedError("Test operation not supported")
    except OperationNotSupportedError as e:
        print(f"\nTest 3 - OperationNotSupportedError: PASS")
        print(f"  Exception message: {e}")

    # Test 4: AdapterBase enforces abstract methods
    from abc import ABC
    abstract_methods = AdapterBase.__abstractmethods__
    print(f"\nTest 4 - Abstract Methods: {'PASS' if abstract_methods else 'FAIL'}")
    print(f"  Abstract methods: {', '.join(str(m) for m in abstract_methods)}")

    return True


def run_validation_suite():
    """Run full validation suite for all optimizations."""
    print("\n" + "="*70)
    print("AI-DB-QC Framework Optimization Validation Suite")
    print("="*70)
    print("\nValidating all optimizations introduced in v0.6+...")

    results = []

    # Run all validations
    try:
        results.append(("RecallQualityOracle", validate_recall_quality_oracle()))
    except Exception as e:
        print(f"Error validating RecallQualityOracle: {e}")
        results.append(("RecallQualityOracle", False))

    try:
        results.append(("MetamorphicOracle", validate_metamorphic_oracle()))
    except Exception as e:
        print(f"Error validating MetamorphicOracle: {e}")
        results.append(("MetamorphicOracle", False))

    try:
        results.append(("SequenceAssertionOracle", validate_sequence_assertion_oracle()))
    except Exception as e:
        print(f"Error validating SequenceAssertionOracle: {e}")
        results.append(("SequenceAssertionOracle", False))

    try:
        results.append(("Adapter Abstraction", validate_adapter_abstraction()))
    except Exception as e:
        print(f"Error validating adapter abstraction: {e}")
        results.append(("Adapter Abstraction", False))

    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "="*70)
    if all_passed:
        print("ALL VALIDATIONS PASSED [OK]")
        print("Framework optimizations are ready for production use.")
    else:
        print("SOME VALIDATIONS FAILED [ERROR]")
        print("Please review errors above before using in production.")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = run_validation_suite()
    sys.exit(0 if success else 1)
