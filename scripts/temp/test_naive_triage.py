"""Test naive triage mode vs diagnostic-aware mode."""

from pipeline.triage import Triage
from schemas.case import TestCase
from schemas.common import BugType, InputValidity, ObservedOutcome
from schemas.result import ExecutionResult


def test_naive_vs_diagnostic_mode():
    """Compare classification results between naive and diagnostic modes."""

    # Create test case: Illegal input
    case = TestCase(
        case_id="test_001",
        operation="search",
        params={"top_k": -1},  # Invalid: negative value
        expected_validity=InputValidity.ILLEGAL
    )

    # Create execution result: Failed with GOOD diagnostics
    # (mentions specific parameter "top_k")
    result_good_diagnostics = ExecutionResult(
        run_id="run_001",
        case_id="test_001",
        adapter_name="test_adapter",
        request={"operation": "search", "params": {"top_k": -1}},
        precondition_pass=True,
        observed_outcome=ObservedOutcome.FAILURE,
        error_message="Invalid value for parameter 'top_k': must be positive",
        response={"error_details": {"parameter": "top_k", "issue": "negative_value"}},
        latency_ms=100
    )

    # Create execution result: Failed with POOR diagnostics
    # (generic error message)
    result_poor_diagnostics = ExecutionResult(
        run_id="run_002",
        case_id="test_001",
        adapter_name="test_adapter",
        request={"operation": "search", "params": {"top_k": -1}},
        precondition_pass=True,
        observed_outcome=ObservedOutcome.FAILURE,
        error_message="Invalid parameter",
        response={},
        latency_ms=100
    )

    triage = Triage()

    print("=" * 80)
    print("TEST 1: Illegal case with GOOD diagnostics")
    print("=" * 80)

    # Diagnostic-aware mode (default)
    result_diagnostic = triage.classify(case, result_good_diagnostics, naive=False)
    print(f"\nDiagnostic-aware mode (naive=False):")
    if result_diagnostic:
        print(f"  Bug Type: {result_diagnostic.final_type.value}")
        print(f"  Rationale: {result_diagnostic.rationale}")
    else:
        print(f"  Result: None (not a bug)")

    # Naive mode
    result_naive = triage.classify(case, result_good_diagnostics, naive=True)
    print(f"\nNaive mode (naive=True):")
    if result_naive:
        print(f"  Bug Type: {result_naive.final_type.value}")
        print(f"  Rationale: {result_naive.rationale}")
    else:
        print(f"  Result: None (not a bug)")

    print("\n" + "=" * 80)
    print("TEST 2: Illegal case with POOR diagnostics")
    print("=" * 80)

    # Diagnostic-aware mode
    result_diagnostic2 = triage.classify(case, result_poor_diagnostics, naive=False)
    print(f"\nDiagnostic-aware mode (naive=False):")
    if result_diagnostic2:
        print(f"  Bug Type: {result_diagnostic2.final_type.value}")
        print(f"  Rationale: {result_diagnostic2.rationale}")
    else:
        print(f"  Result: None (not a bug)")

    # Naive mode
    result_naive2 = triage.classify(case, result_poor_diagnostics, naive=True)
    print(f"\nNaive mode (naive=True):")
    if result_naive2:
        print(f"  Bug Type: {result_naive2.final_type.value}")
        print(f"  Rationale: {result_naive2.rationale}")
    else:
        print(f"  Result: None (not a bug)")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Verify expectations
    print("\nExpected behavior:")
    print("  TEST 1 (Good diagnostics):")
    print("    - Diagnostic mode: None (not a bug, because diagnostics are good)")
    print("    - Naive mode: TYPE_2 (all illegal-fail are bugs)")
    print("  TEST 2 (Poor diagnostics):")
    print("    - Diagnostic mode: TYPE_2 (poor diagnostics)")
    print("    - Naive mode: TYPE_2 (all illegal-fail are bugs)")

    # Assertions
    print("\nActual results:")
    assert result_diagnostic is None, f"Expected None for diagnostic mode with good diagnostics, got {result_diagnostic}"
    print("  [PASS] TEST 1 Diagnostic: None as expected")

    assert result_naive is not None and result_naive.final_type == BugType.TYPE_2, \
        f"Expected TYPE_2 for naive mode with good diagnostics, got {result_naive}"
    print("  [PASS] TEST 1 Naive: TYPE_2 as expected")

    assert result_diagnostic2 is not None and result_diagnostic2.final_type == BugType.TYPE_2, \
        f"Expected TYPE_2 for diagnostic mode with poor diagnostics, got {result_diagnostic2}"
    print("  [PASS] TEST 2 Diagnostic: TYPE_2 as expected")

    assert result_naive2 is not None and result_naive2.final_type == BugType.TYPE_2, \
        f"Expected TYPE_2 for naive mode with poor diagnostics, got {result_naive2}"
    print("  [PASS] TEST 2 Naive: TYPE_2 as expected")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    test_naive_vs_diagnostic_mode()
