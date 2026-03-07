"""Tests for PreconditionEvaluator."""

import pytest

from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity


class TestPreconditionEvaluator:
    """Test PreconditionEvaluator contract-aware checks."""

    def test_operation_supported_legality_check(self):
        """Test legality check: operation supported."""
        # Use actual contract and profile
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
        runtime_context = {
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT", "HNSW"]
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)

        # Valid operation with all required params
        case = TestCase(
            case_id="test-1",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]  # No additional preconditions beyond contract
        )
        passed, trace = precond.evaluate(case)
        assert passed is True
        assert all(t.check_type == "legality" or t.check_type == "runtime" for t in trace)

    def test_missing_required_parameter_legality_check(self):
        """Test legality check: missing required parameter."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
        runtime_context = {}

        precond = PreconditionEvaluator(contract, profile, runtime_context)

        # INSERT requires vectors parameter - create case without it
        case = TestCase(
            case_id="test-2",
            operation=OperationType.INSERT,
            params={},  # Missing required vectors
            expected_validity=InputValidity.ILLEGAL,
            required_preconditions=[]
        )
        passed, trace = precond.evaluate(case)
        assert passed is False
        # Should have a legality trace for missing param
        legality_traces = [t for t in trace if t.check_type == "legality"]
        assert any(not t.passed for t in legality_traces)

    def test_collection_exists_runtime_check(self):
        """Test runtime check: collection_exists."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Collection exists
        runtime_context = {
            "collections": ["test", "prod"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT", "HNSW"]
        }
        precond = PreconditionEvaluator(contract, profile, runtime_context)

        case = TestCase(
            case_id="test-3",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]  # Contract already has preconditions
        )
        passed, trace = precond.evaluate(case)
        assert passed is True
        runtime_traces = [t for t in trace if t.check_type == "runtime"]
        assert all(t.passed for t in runtime_traces)

        # Collection does not exist
        runtime_context_missing = {
            "collections": ["prod"],  # "test" not in list
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }
        precond_missing = PreconditionEvaluator(contract, profile, runtime_context_missing)
        passed, trace = precond_missing.evaluate(case)
        assert passed is False
        runtime_traces = [t for t in trace if t.check_type == "runtime"]
        collection_trace = next((t for t in runtime_traces if "collection" in t.precondition_name), None)
        assert collection_trace is not None
        assert collection_trace.passed is False

    def test_has_index_runtime_check(self):
        """Test runtime check: index_built."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Has index
        runtime_context = {
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }
        precond = PreconditionEvaluator(contract, profile, runtime_context)

        case = TestCase(
            case_id="test-4",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )
        passed, trace = precond.evaluate(case)
        assert passed is True

        # No index
        runtime_context_no_index = {
            "collections": ["test"],
            "indexed_collections": [],  # "test" not indexed
            "loaded_collections": [],
            "connected": True,
            "target_collection": "test",
            "supported_features": []
        }
        precond_no_index = PreconditionEvaluator(contract, profile, runtime_context_no_index)
        passed, trace = precond_no_index.evaluate(case)
        assert passed is False

    def test_connection_active_runtime_check(self):
        """Test runtime check: connection_active."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Connected
        runtime_context = {
            "connected": True,
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }
        precond = PreconditionEvaluator(contract, profile, runtime_context)

        case = TestCase(
            case_id="test-5",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=["connection_active"]
        )
        passed, trace = precond.evaluate(case)
        assert passed is True

        # Not connected
        runtime_context_disconnected = {
            "connected": False,
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }
        precond_disconnected = PreconditionEvaluator(contract, profile, runtime_context_disconnected)
        passed, trace = precond_disconnected.evaluate(case)
        assert passed is False

    def test_unknown_precondition_fails(self):
        """Test unknown preconditions fail by default."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
        runtime_context = {}

        precond = PreconditionEvaluator(contract, profile, runtime_context)

        case = TestCase(
            case_id="test-6",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=["unknown_precondition"]
        )
        passed, trace = precond.evaluate(case)
        assert passed is False
        runtime_traces = [t for t in trace if t.check_type == "runtime"]
        # Contract has 3 required preconditions + 1 from case
        assert len(runtime_traces) == 4
        # All runtime traces should fail (empty runtime_context)
        assert all(not t.passed for t in runtime_traces)
        # unknown_precondition should be in traces
        unknown_traces = [t for t in runtime_traces if t.precondition_name == "unknown_precondition"]
        assert len(unknown_traces) == 1

    def test_check_type_field_in_gate_trace(self):
        """Test that GateTrace entries include check_type field."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
        runtime_context = {
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT"]
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)

        # Test with missing required param to get legality traces
        case = TestCase(
            case_id="test-7",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3]},  # Missing top_k
            expected_validity=InputValidity.ILLEGAL,  # Expected illegal due to missing param
            required_preconditions=[]
        )
        passed, trace = precond.evaluate(case)

        # All traces should have check_type
        for t in trace:
            assert hasattr(t, "check_type")
            assert t.check_type in ["legality", "runtime"]

        # Should have both legality and runtime traces
        legality_traces = [t for t in trace if t.check_type == "legality"]
        runtime_traces = [t for t in trace if t.check_type == "runtime"]
        assert len(legality_traces) > 0  # Missing top_k should give legality trace
        assert len(runtime_traces) > 0  # Contract has runtime preconditions

        # Verify specific trace
        param_trace = next((t for t in legality_traces if "param_top_k" in t.precondition_name), None)
        assert param_trace is not None
        assert param_trace.check_type == "legality"
        assert param_trace.passed is False
