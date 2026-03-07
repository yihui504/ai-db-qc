"""Unit tests for Executor and E2E flow."""

import pytest
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
from pipeline.triage import Triage
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity, ObservedOutcome, BugType


# Helper function to create test executor
def _create_test_executor(adapter, runtime_context=None):
    """Create an executor with default contract/profile."""
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    if runtime_context is None:
        runtime_context = {
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = []  # No oracles for basic tests
    return Executor(adapter, precond, oracles)


def test_executor_case_success():
    """Test executing a case successfully."""
    adapter = MockAdapter(ResponseMode.SUCCESS)
    executor = _create_test_executor(adapter)

    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=[]
    )

    result = executor.execute_case(case)

    assert result.case_id == "test-001"
    assert result.observed_outcome == ObservedOutcome.SUCCESS
    assert result.precondition_pass is True
    assert result.adapter_name == "MockAdapter"


def test_executor_case_failure():
    """Test executing a case that fails."""
    adapter = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.PARTIAL)
    executor = _create_test_executor(adapter)

    case = TestCase(
        case_id="test-002",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": -1},
        expected_validity=InputValidity.ILLEGAL,
        required_preconditions=[]
    )

    result = executor.execute_case(case)

    assert result.observed_outcome == ObservedOutcome.FAILURE
    assert result.error_message is not None


def test_executor_batch():
    """Test batch execution."""
    adapter = MockAdapter(ResponseMode.SUCCESS)
    executor = _create_test_executor(adapter)

    cases = [
        TestCase(
            case_id=f"test-{i}",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )
        for i in range(5)
    ]

    results = executor.execute_batch(cases)

    assert len(results) == 5
    assert all(r.observed_outcome == ObservedOutcome.SUCCESS for r in results)


def test_precondition_pass_affects_result():
    """Test that precondition_pass affects result."""
    adapter = MockAdapter(ResponseMode.SUCCESS)
    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=[]
    )

    # Pass runtime context
    runtime_context_pass = {
        "collections": ["test"],
        "indexed_collections": ["test"],
        "loaded_collections": ["test"],
        "connected": True,
        "target_collection": "test",
        "supported_features": ["IVF_FLAT"]
    }
    executor_pass = _create_test_executor(adapter, runtime_context_pass)
    result_pass = executor_pass.execute_case(case)
    assert result_pass.precondition_pass is True

    # Fail runtime context (missing collection)
    runtime_context_fail = {
        "collections": [],  # Empty - collection missing
        "indexed_collections": ["test"],
        "loaded_collections": ["test"],
        "connected": True,
        "target_collection": "test",
        "supported_features": ["IVF_FLAT"]
    }
    executor_fail = _create_test_executor(adapter, runtime_context_fail)
    result_fail = executor_fail.execute_case(case)
    assert result_fail.precondition_pass is False


def test_triage_type_1():
    """Test Type-1 classification: illegal succeeded."""
    triage = Triage()

    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": -1},
        expected_validity=InputValidity.ILLEGAL,
        required_preconditions=[]
    )

    adapter = MockAdapter(ResponseMode.SUCCESS)
    executor = _create_test_executor(adapter)
    exec_result = executor.execute_case(case)

    triage_result = triage.classify(case, exec_result)

    assert triage_result is not None
    assert triage_result.final_type == BugType.TYPE_1


def test_triage_type_3():
    """Test Type-3 classification: legal failed with precondition_pass."""
    triage = Triage()

    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=[]
    )

    adapter = MockAdapter(ResponseMode.FAILURE)
    executor = _create_test_executor(adapter)
    result = executor.execute_case(case)

    triage_result = triage.classify(case, result)

    assert triage_result is not None
    assert triage_result.final_type == BugType.TYPE_3
    assert triage_result.precondition_pass is True  # RED-LINE verified


def test_triage_red_line_enforcement():
    """Test that Type-3/4 require precondition_pass=true."""
    triage = Triage()

    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=[]
    )

    adapter = MockAdapter(ResponseMode.FAILURE)

    # Fail runtime context (missing collection)
    runtime_context_fail = {
        "collections": [],  # Empty - collection missing
        "indexed_collections": ["test"],
        "loaded_collections": ["test"],
        "connected": True,
        "target_collection": "test",
        "supported_features": ["IVF_FLAT"]
    }
    executor = _create_test_executor(adapter, runtime_context_fail)
    result = executor.execute_case(case)

    triage_result = triage.classify(case, result)

    # Should be Type-2.PreconditionFailed, NOT Type-3
    # because precondition_pass=false
    assert triage_result.final_type == BugType.TYPE_2_PRECONDITION_FAILED


def test_e2e_template_to_triage():
    """End-to-end: template → case → execute → triage."""
    from casegen.generators.instantiator import load_templates, instantiate_all

    # Load templates
    templates = load_templates("casegen/templates/basic_templates.yaml")
    cases = instantiate_all(templates, {"collection": "test", "k": 10})

    # Set up executor
    adapter = MockAdapter(ResponseMode.SUCCESS)
    executor = _create_test_executor(adapter)

    # Execute
    results = executor.execute_batch(cases)

    # Triage
    triage = Triage()
    triage_results = [triage.classify(case, result) for case, result in zip(cases, results)]

    # Should have some Type-1 (invalid parameters that succeeded)
    type_1_count = sum(1 for t in triage_results if t and t.final_type == BugType.TYPE_1)
    assert type_1_count > 0, "Should detect Type-1 bugs (invalid parameters succeeded)"


def test_diagnostic_quality_affects_type_2_classification():
    """Test that diagnostic quality affects Type-2 classification."""
    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={"collection_name": "test", "vector": [1, 2, 3], "top_k": -1},
        expected_validity=InputValidity.ILLEGAL,
        required_preconditions=[]
    )

    triage = Triage()

    # Test with NONE quality - should be Type-2
    adapter_none = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.NONE)
    executor_none = _create_test_executor(adapter_none)
    result_none = executor_none.execute_case(case)
    triage_none = triage.classify(case, result_none)
    assert triage_none.final_type == BugType.TYPE_2

    # Test with FULL quality - should NOT be Type-2 (not a bug)
    adapter_full = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.FULL)
    executor_full = _create_test_executor(adapter_full)
    result_full = executor_full.execute_case(case)
    triage_full = triage.classify(case, result_full)
    assert triage_full is None  # Not a bug, has good diagnostics
