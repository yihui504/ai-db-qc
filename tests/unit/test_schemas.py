"""Unit tests for schemas."""

import pytest
from schemas import TestCase, ExecutionResult, BugType
from schemas.triage import TriageResult
from schemas.common import (
    InputValidity,
    OperationType,
    ObservedOutcome,
    BugType as BugTypeEnum,
)


def test_enum_values():
    """Test enum values exist."""
    assert InputValidity.LEGAL == "legal"
    assert InputValidity.ILLEGAL == "illegal"

    # BugType has 4 top-level types + 1 subtype
    assert BugTypeEnum.TYPE_1 == "type-1"
    assert BugTypeEnum.TYPE_2 == "type-2"
    assert BugTypeEnum.TYPE_2_PRECONDITION_FAILED == "type-2.precondition_failed"
    assert BugTypeEnum.TYPE_3 == "type-3"
    assert BugTypeEnum.TYPE_4 == "type-4"

    assert OperationType.SEARCH == "search"
    assert ObservedOutcome.SUCCESS == "success"


def test_testcase_creation():
    """Test TestCase creation with list[str] preconditions."""
    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"top_k": 10},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=["collection_exists", "index_loaded"]
    )
    assert case.case_id == "test-001"
    assert case.operation == OperationType.SEARCH
    assert len(case.required_preconditions) == 2
    assert "collection_exists" in case.required_preconditions


def test_testcase_serialization():
    """Test TestCase can serialize/deserialize."""
    case = TestCase(
        case_id="test-002",
        operation=OperationType.INSERT,
        params={"vectors": [[1.0, 2.0]]},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=["collection_exists"]
    )
    json_str = case.model_dump_json()
    assert "test-002" in json_str

    restored = TestCase.model_validate_json(json_str)
    assert restored.case_id == case.case_id


def test_execution_result_precondition_pass():
    """Test ExecutionResult has precondition_pass field."""
    result = ExecutionResult(
        run_id="run-001",
        case_id="test-001",
        adapter_name="milvus",
        request={"operation": "search"},
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=50.0,
        precondition_pass=True  # CRITICAL for red-line
    )
    assert result.precondition_pass is True
    assert result.observed_success is True


def test_execution_result_observed_success_property():
    """Test observed_success property."""
    result_success = ExecutionResult(
        run_id="run-001",
        case_id="test-001",
        adapter_name="milvus",
        request={},
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=50.0,
        precondition_pass=True
    )
    assert result_success.observed_success is True

    result_failure = ExecutionResult(
        run_id="run-001",
        case_id="test-002",
        adapter_name="milvus",
        request={},
        observed_outcome=ObservedOutcome.FAILURE,
        latency_ms=5.0,
        precondition_pass=True
    )
    assert result_failure.observed_success is False


def test_triage_result_separate():
    """Test TriageResult is in separate module."""
    triage = TriageResult(
        case_id="test-001",
        run_id="run-001",
        final_type=BugTypeEnum.TYPE_1,
        input_validity=InputValidity.ILLEGAL,
        observed_outcome=ObservedOutcome.SUCCESS,
        precondition_pass=False,
        rationale="Illegal negative top_k was accepted"
    )
    assert triage.final_type == BugTypeEnum.TYPE_1
    assert triage.precondition_pass is False
    assert triage.input_validity == InputValidity.ILLEGAL
    assert triage.observed_outcome == ObservedOutcome.SUCCESS


def test_triage_result_type_2_precondition_failed():
    """Test Type-2.PreconditionFailed is a subtype of Type-2."""
    triage = TriageResult(
        case_id="test-002",
        run_id="run-001",
        final_type=BugTypeEnum.TYPE_2_PRECONDITION_FAILED,
        input_validity=InputValidity.LEGAL,
        observed_outcome=ObservedOutcome.FAILURE,
        precondition_pass=False,  # precondition-fail
        rationale="Contract-valid but precondition-fail"
    )
    assert triage.final_type == BugTypeEnum.TYPE_2_PRECONDITION_FAILED
    # Note: PRECONDITION_FAILED contains "type-2" - it's a Type-2 subtype
    assert "type-2" in triage.final_type.value
    assert triage.input_validity == InputValidity.LEGAL


def test_redline_type_3_requires_precondition_pass():
    """Test that Type-3 classification should require precondition_pass=true."""
    # This is a convention, not enforced by schema
    # But tests document the expectation
    triage_valid = TriageResult(
        case_id="test-003",
        run_id="run-001",
        final_type=BugTypeEnum.TYPE_3,
        input_validity=InputValidity.LEGAL,
        observed_outcome=ObservedOutcome.FAILURE,
        precondition_pass=True,  # REQUIRED for Type-3
        rationale="Valid operation failed after precondition check"
    )
    assert triage_valid.precondition_pass is True
    assert triage_valid.input_validity == InputValidity.LEGAL
