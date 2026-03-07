"""Precondition evaluation (contract-aware)."""

from __future__ import annotations

from typing import Any, Dict, List

from contracts.core.loader import CoreContract
from contracts.db_profiles.loader import DBProfile
from schemas.case import TestCase
from schemas.common import GateTrace


class PreconditionEvaluator:
    """Formal precondition evaluation (contract-aware).

    Distinguishes between:
    - Legality: Abstract contract compliance (operation exists, params defined)
    - Runtime: Runtime readiness (collection exists, connection active)
    """

    def __init__(
        self,
        contract: CoreContract,
        profile: DBProfile,
        runtime_context: Dict[str, Any]
    ):
        self.contract = contract
        self.profile = profile
        self.runtime_context = runtime_context

    def evaluate(self, case: TestCase) -> tuple[bool, List[GateTrace]]:
        """
        Evaluate preconditions for a case.

        Returns:
            (all_passed, gate_trace)
        """
        gate_trace = []
        all_passed = True

        # Check 1: Operation supported (legality)
        op_contract = self.contract.operations.get(case.operation)
        if op_contract is None:
            gate_trace.append(GateTrace(
                precondition_name="operation_supported",
                check_type="legality",
                passed=False,
                reason=f"Operation {case.operation} not in core contract"
            ))
            return False, gate_trace

        # Check 2: Operation in profile (legality)
        if case.operation.value not in self.profile.supported_operations:
            gate_trace.append(GateTrace(
                precondition_name="operation_in_profile",
                check_type="legality",
                passed=False,
                reason=f"Operation {case.operation} not in DB profile"
            ))
            return False, gate_trace

        # Check 3: Required parameters (legality)
        for param_name, param_constraint in op_contract.parameters.items():
            if param_constraint.required and param_name not in case.params:
                gate_trace.append(GateTrace(
                    precondition_name=f"param_{param_name}",
                    check_type="legality",
                    passed=False,
                    reason=f"Required parameter '{param_name}' missing"
                ))
                all_passed = False

        # Check 4: Runtime preconditions (runtime)
        # Combine contract required preconditions with case-specific ones
        contract_preconds = op_contract.required_preconditions if hasattr(op_contract, 'required_preconditions') else []
        all_runtime_preconds = list(set(contract_preconds + case.required_preconditions))

        for precond in all_runtime_preconds:
            passed = self._check_runtime_precondition(precond, case)
            gate_trace.append(GateTrace(
                precondition_name=precond,
                check_type="runtime",
                passed=passed,
                reason="Satisfied" if passed else "Not available in runtime context"
            ))
            if not passed:
                all_passed = False

        return all_passed, gate_trace

    def _check_runtime_precondition(self, precond: str, case: TestCase) -> bool:
        """Check runtime precondition against runtime_context.

        Args:
            precond: Precondition name to check
            case: Current test case (used for case-scoped collection name)

        Returns:
            True if precondition is satisfied
        """
        # Extract collection name from case params (case-scoped)
        # Fall back to runtime_context target_collection if case doesn't specify one
        collection_name = case.params.get("collection_name")
        if not collection_name:
            collection_name = self.runtime_context.get("target_collection")

        if precond == "collection_exists":
            if not collection_name:
                return False
            available_collections = self.runtime_context.get("collections", [])
            return collection_name in available_collections

        if precond == "has_index" or precond == "index_built":
            if not collection_name:
                return False
            indexed_collections = self.runtime_context.get("indexed_collections", [])
            return collection_name in indexed_collections

        if precond == "index_loaded":
            if not collection_name:
                return False
            loaded_collections = self.runtime_context.get("loaded_collections", [])
            return collection_name in loaded_collections

        if precond == "collection_loaded":
            # Alias for index_loaded - same check
            if not collection_name:
                return False
            loaded_collections = self.runtime_context.get("loaded_collections", [])
            return collection_name in loaded_collections

        if precond == "connection_active":
            return self.runtime_context.get("connected", False)

        if precond == "min_data_count":
            # Check if collection has minimum data count
            if not collection_name:
                return False
            collection_data = self.runtime_context.get("collection_data", {})
            return collection_data.get(collection_name, 0) >= self.runtime_context.get("min_data_threshold", 1)

        if precond == "supported_features":
            # Check if required features are supported
            required_features = self.runtime_context.get("required_features", [])
            supported_features = self.runtime_context.get("supported_features", [])
            return all(f in supported_features for f in required_features)

        # Unknown precondition - assume not satisfied
        return False

    def load_runtime_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Load runtime snapshot from adapter into runtime_context.

        Adapter owns the snapshot dict; PreconditionEvaluator consumes it.
        This updates runtime_context with fresh database state.
        """
        self.runtime_context.update({
            "collections": snapshot.get("collections", []),
            "indexed_collections": snapshot.get("indexed_collections", []),
            "loaded_collections": snapshot.get("loaded_collections", []),
            "connected": snapshot.get("connected", False),
            "memory_stats": snapshot.get("memory_stats", {})
        })
