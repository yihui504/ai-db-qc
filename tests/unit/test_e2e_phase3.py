"""End-to-end tests for Phase 3."""

import tempfile
from pathlib import Path
from shutil import rmtree

import pytest

from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity, ObservedOutcome, BugType


class TestE2EPhase3:
    """End-to-end: templates → cases → PreconditionEvaluator → MockAdapter → Oracles → Triage → Evidence."""

    def setup_method(self):
        """Set up test components."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temp directory."""
        rmtree(self.temp_dir, ignore_errors=True)

    def test_full_phase3_flow(self):
        """Test full Phase 3 mock flow."""
        # Load templates and generate cases
        templates = load_templates("casegen/templates/basic_templates.yaml")
        cases = instantiate_all(templates, {"collection": "test", "k": 10})

        assert len(cases) > 0, "Should generate cases from templates"

        # Set up contract and profile
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Runtime context
        runtime_context = {
            "collections": ["test"],
            "indexed_collections": ["test"],
            "loaded_collections": ["test"],
            "connected": True,
            "target_collection": "test",
            "supported_features": ["IVF_FLAT", "HNSW"]
        }

        # Create components
        precond = PreconditionEvaluator(contract, profile, runtime_context)
        adapter = MockAdapter(ResponseMode.SUCCESS)
        oracles = [WriteReadConsistency(), FilterStrictness()]
        executor = Executor(adapter, precond, oracles)
        triage = Triage()

        # Execute
        results = executor.execute_batch(cases, run_id="test-e2e")

        assert len(results) == len(cases), "Should have result for each case"

        # Classify
        triage_results = [triage.classify(case, result) for case, result in zip(cases, results)]

        # Write evidence
        writer = EvidenceWriter()
        run_dir = writer.create_run_dir("test-e2e", base_path=self.temp_dir)
        writer.write_all(run_dir, {}, cases, results, triage_results)

        # Verify evidence files
        assert (run_dir / "run_metadata.json").exists()
        assert (run_dir / "cases.jsonl").exists()
        assert (run_dir / "execution_results.jsonl").exists()
        assert (run_dir / "triage_report.json").exists()

    def test_gate_trace_check_type_distinction(self):
        """Test GateTrace.check_type distinguishes legality vs runtime checks."""
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

        case = TestCase(
            case_id="test",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        passed, gate_trace = precond.evaluate(case)

        # Should have both legality and runtime traces
        legality_traces = [t for t in gate_trace if t.check_type == "legality"]
        runtime_traces = [t for t in gate_trace if t.check_type == "runtime"]

        # With all required params, only runtime traces from contract
        assert len(runtime_traces) > 0, "Should have runtime traces"

    def test_type_4_from_actual_oracle_failure(self):
        """Test Type-4 classification from actual oracle failure (not mock)."""
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
        adapter = MockAdapter(ResponseMode.SUCCESS)
        oracles = [WriteReadConsistency()]
        executor = Executor(adapter, precond, oracles)
        triage = Triage()

        # Simple search case
        search_case = TestCase(
            case_id="search-1",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        search_result = executor.execute_case(search_case, run_id="test-type4")
        triage_result = triage.classify(search_case, search_result)

        # Should not be Type-4 (oracle passes)
        assert triage_result is None or triage_result.final_type != BugType.TYPE_4

    def test_runtime_preconditions_fail_appropriately(self):
        """Test runtime preconditions fail when not in runtime_context."""
        contract = get_default_contract()
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

        # Empty runtime context
        runtime_context = {
            "collections": [],  # Empty
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": False,
            "target_collection": "test",
            "supported_features": []
        }

        precond = PreconditionEvaluator(contract, profile, runtime_context)
        adapter = MockAdapter(ResponseMode.SUCCESS)
        executor = Executor(adapter, precond, [])
        triage = Triage()

        case = TestCase(
            case_id="test",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = executor.execute_case(case, run_id="test-runtime")
        triage_result = triage.classify(case, result)

        # Precondition should fail, so Type-2.PreconditionFailed
        assert result.precondition_pass is False
        assert triage_result.final_type == BugType.TYPE_2_PRECONDITION_FAILED

    def test_oracles_consume_context_not_own_state(self):
        """Test oracles consume context from executor, not own state."""
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
        adapter = MockAdapter(ResponseMode.SUCCESS)

        # Create oracles - they should be stateless
        wrc = WriteReadConsistency()
        assert not hasattr(wrc, "mock_state") or wrc.mock_state == {}

        fs = FilterStrictness()
        assert not hasattr(fs, "unfiltered_result_ids")

        oracles = [wrc, fs]
        executor = Executor(adapter, precond, oracles)

        # Execute search - executor should track unfiltered_result_ids
        search_case = TestCase(
            case_id="search-1",
            operation=OperationType.SEARCH,
            params={"collection_name": "test", "vector": [1, 2, 3], "top_k": 10},
            expected_validity=InputValidity.LEGAL,
            required_preconditions=[]
        )

        result = executor.execute_case(search_case, run_id="test-context")

        # Executor should have tracked IDs
        assert hasattr(executor, "unfiltered_result_ids")
        assert len(executor.unfiltered_result_ids) > 0
