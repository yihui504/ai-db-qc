"""Integration tests for real Milvus flow."""

import pytest

from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.milvus_adapter import MilvusAdapter
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from evidence.fingerprint import capture_environment
from schemas.case import TestCase
from scripts.run_phase4 import execute_filtered_pair
from schemas.common import BugType


@pytest.mark.integration
class TestRealMilvusFlow:
    """End-to-end tests with real Milvus database."""

    def test_full_phase4_flow_with_milvus(self):
        """Test full Phase 4 flow with real Milvus."""
        # Setup
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        adapter = MilvusAdapter(connection_config)

        # Verify connection
        assert adapter.health_check() is True

        # Load contract and profile
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Capture fingerprint
        fingerprint = capture_environment(connection_config, adapter)
        assert fingerprint.milvus_version is not None

        # Load runtime snapshot
        snapshot = adapter.get_runtime_snapshot()
        snapshot_id = f"test-snapshot"
        snapshot["snapshot_id"] = snapshot_id
        snapshot["timestamp"] = "2026-03-07T12:00:00"

        # Create PreconditionEvaluator and load snapshot
        runtime_context = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "target_collection": "test_collection",
            "supported_features": []
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)
        precond.load_runtime_snapshot(snapshot)

        # Create executor and oracles
        oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness()]
        executor = Executor(adapter, precond, oracles)
        triage = Triage()
        writer = EvidenceWriter()

        # Load and execute a simple case
        case = TestCase(
            case_id="integration-001",
            operation="create_collection",
            params={
                "collection_name": "test_collection",
                "dimension": 128,
                "metric_type": "L2"
            },
            expected_validity="legal",
            required_preconditions=[]
        )

        result = executor.execute_case(case, run_id="test-integration")

        # Verify result
        assert result.case_id == "integration-001"
        assert result.adapter_name == "MilvusAdapter"

        # Cleanup
        adapter.close()

    def test_milvus_write_read_consistency(self):
        """Test WriteReadConsistency with real Milvus operations."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        adapter = MilvusAdapter(connection_config)

        # Setup executor
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        runtime_context = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "target_collection": "test_collection",
            "supported_features": []
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)
        oracles = [WriteReadConsistency(validate_ids=True)]
        executor = Executor(adapter, precond, oracles)

        # Create collection
        create_case = TestCase(
            case_id="test-001",
            operation="create_collection",
            params={
                "collection_name": "consistency_test",
                "dimension": 128,
                "metric_type": "L2"
            },
            expected_validity="legal",
            required_preconditions=[]
        )

        result = executor.execute_case(create_case, run_id="test")

        # Cleanup
        adapter.close()

        assert result.observed_outcome.value == "success"

    @pytest.mark.integration
    def test_oracle_real_db_validation(self):
        """Test oracles with real database operations."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        adapter = MilvusAdapter(connection_config)
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        runtime_context = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "target_collection": "test_collection",
            "supported_features": []
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)
        oracles = [WriteReadConsistency(), FilterStrictness()]
        executor = Executor(adapter, precond, oracles)

        # Test: Create collection (simple legal case)
        case = TestCase(
            case_id="oracle-test-001",
            operation="create_collection",
            params={
                "collection_name": "oracle_test",
                "dimension": 128,
                "metric_type": "L2"
            },
            expected_validity="legal",
            required_preconditions=[]
        )

        result = executor.execute_case(case, run_id="test-oracles")

        # Verify oracles ran
        assert len(result.oracle_results) >= 1

        # Cleanup
        adapter.close()

        assert result.observed_outcome.value == "success"
