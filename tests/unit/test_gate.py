"""Unit tests for GateStub."""

import pytest
from pipeline.gate import GateStub, PreconditionMode
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity


def test_gate_all_pass():
    """Test ALL_PASS mode."""
    gate = GateStub(PreconditionMode.ALL_PASS)
    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=["collection_exists", "index_loaded"]
    )

    passed, trace = gate.check(case)

    assert passed is True
    assert len(trace) == 2
    assert all(gt.passed for gt in trace)


def test_gate_all_fail():
    """Test ALL_FAIL mode."""
    gate = GateStub(PreconditionMode.ALL_FAIL)
    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=["collection_exists"]
    )

    passed, trace = gate.check(case)

    assert passed is False
    assert len(trace) == 1
    assert trace[0].passed is False
    assert "Not satisfied" in trace[0].reason


def test_gate_selective():
    """Test SELECTIVE mode."""
    gate = GateStub(PreconditionMode.SELECTIVE)
    case = TestCase(
        case_id="test",
        operation=OperationType.SEARCH,
        params={},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=["collection_exists", "index_loaded", "data_count"]
    )

    passed, trace = gate.check(case)

    # "exists" and "loaded" pass, "data_count" fails
    assert len(trace) == 3
    assert trace[0].passed is True  # collection_exists
    assert trace[1].passed is True  # index_loaded
    assert trace[2].passed is False  # data_count
    assert passed is False  # Not all passed


def test_gate_no_preconditions():
    """Test gate with case that has no preconditions."""
    gate = GateStub(PreconditionMode.ALL_PASS)
    case = TestCase(
        case_id="test",
        operation=OperationType.CREATE_COLLECTION,
        params={},
        expected_validity=InputValidity.LEGAL,
        required_preconditions=[]
    )

    passed, trace = gate.check(case)

    assert passed is True
    assert len(trace) == 0
